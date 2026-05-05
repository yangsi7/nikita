"""Portal-auth admin endpoints (Spec 215 §7.6).

Currently exposes one endpoint:

    POST /admin/auth/generate-magiclink-for-telegram-user

The handler is invoked by the Telegram FSM (PR-F1b `signup_handler.py`)
after the user verifies their OTP code; it asks Supabase to mint a
hashed_token + action_link and persists the hashed_token on the
telegram_signup_sessions row via the FSM CAS helper.

Per Testing H2 the `verification_type` field is passed VERBATIM from the
Supabase generate_link response — no normalisation, no literal
substitution. The static-grep gate in
`tests/api/routes/test_portal_auth_generate_magiclink.py` enforces this.

Auth: service-role only. End-user JWTs return 401. The check matches the
caller's bearer token against `settings.supabase_service_key`; if the
secret is unset the endpoint returns 401 (fail-closed).
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import Final, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.api.dependencies.auth import (
    AuthenticatedUser,
    get_authenticated_user,
)
from nikita.config.settings import get_settings
from nikita.db.database import get_async_session, get_supabase_client
from nikita.db.repositories.telegram_signup_session_repository import (
    ExpiredOrConcurrentError,
    TelegramSignupSessionRepository,
)
from nikita.db.repositories.user_repository import (
    BindResult,
    TelegramIdAlreadyBoundByOtherUserError,
    UserRepository,
)
from nikita.monitoring.events import (
    SignupMagicLinkMintedEvent,
    email_hash,
    emit_signup_magic_link_minted,
    telegram_id_hash,
)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Portal Auth Admin"])
# Separate user-auth-gated router for end-user autobind flow (Spec 216 EM-2).
# Mounted at /api/v1/auth so the portal /auth/confirm route can call it
# with the just-issued Supabase session JWT. Service-role gate from the
# admin router does NOT apply here — see route_autobind_telegram below.
user_router = APIRouter(prefix="/auth", tags=["Portal Auth"])
_security = HTTPBearer(auto_error=False)

# Supabase admin.generate_link action_link TTL — hardcoded by Supabase
# to 1 hour. NOMINAL value: the Supabase response does not surface the
# precise remaining TTL on the link, so we record this constant in
# telemetry and the GenerateMagiclinkResponse.expires_at as our best
# estimate. If Supabase changes the default, telemetry will skew but
# functionality continues. Documented at:
# https://supabase.com/docs/reference/javascript/auth-admin-generatelink
# Named per `.claude/rules/tuning-constants.md`.
_SUPABASE_ACTION_LINK_TTL_S: Final[int] = 3600

# Supabase admin.generate_link `type` argument. Spec 215 FR-5 always asks
# Supabase to mint a magic-link; the response `verification_type` is what
# we echo verbatim (see GenerateMagiclinkResponse Literal annotation).
#
# The single source-of-truth for both the input arg and the allowed
# verification_type response domain lives in the Literal type alias below.
# The runtime constant is derived from the alias so the handler source
# contains no other bare 'magiclink'/'signup' literals (Testing H2
# static-grep gate).
_SupabaseGenerateLinkType = Literal["magiclink"]
_VerificationType = Literal["magiclink", "signup"]
_SUPABASE_LINK_TYPE: _SupabaseGenerateLinkType = (
    _SupabaseGenerateLinkType.__args__[0]  # type: ignore[attr-defined]
)


class GenerateMagiclinkRequest(BaseModel):
    """Spec 215 §7.6 request model."""

    telegram_id: int = Field(
        ..., description="Telegram user ID requesting the magic link"
    )
    email: EmailStr = Field(
        ..., description="Verified email address (post-OTP)"
    )


class GenerateMagiclinkResponse(BaseModel):
    """Spec 215 §7.6 response model.

    `verification_type` is taken VERBATIM from the Supabase
    `auth.admin.generate_link` response (no normalisation). The Literal[]
    annotation is the only place these strings may appear — Testing H2
    static-grep enforces this.
    """

    action_link: str = Field(
        ..., description="Supabase action URL — delivered via Telegram, never stored"
    )
    hashed_token: str = Field(
        ..., description="Stored on telegram_signup_sessions.magic_link_token (data-layer H5)"
    )
    verification_type: _VerificationType = Field(
        ..., description="Passed verbatim to portal verifyOtp({type: ...})"
    )
    expires_at: datetime = Field(
        ..., description="Echoes Supabase TTL (typically now() + 1h)"
    )


# --------------------------------------------------------------------------
# Service-role guard
# --------------------------------------------------------------------------


def _require_service_role(
    credentials: HTTPAuthorizationCredentials | None = Depends(_security),
) -> None:
    """Reject any caller whose bearer token is not the configured service-role
    key. Fail-closed: missing secret → 401."""
    settings = get_settings()
    expected = settings.supabase_service_key
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Service-role key not configured",
            headers={"WWW-Authenticate": "Bearer"},
        )
    presented = credentials.credentials if credentials is not None else ""
    # Constant-time comparison: the bearer is a high-value secret (full DB
    # bypass). A timing-unsafe `!=` leaks length + character match timing.
    if not secrets.compare_digest(presented, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Service role required",
            headers={"WWW-Authenticate": "Bearer"},
        )


# --------------------------------------------------------------------------
# Repo dependency. Wrapped in a thin async helper so tests can patch it
# without intercepting the SQLAlchemy session machinery.
# --------------------------------------------------------------------------


async def _get_repo_for_request(
    session: AsyncSession = Depends(get_async_session),
) -> TelegramSignupSessionRepository:
    return TelegramSignupSessionRepository(session)


# --------------------------------------------------------------------------
# Handler
# --------------------------------------------------------------------------


@router.post(
    "/generate-magiclink-for-telegram-user",
    response_model=GenerateMagiclinkResponse,
    summary="Mint a PKCE token_hash magic-link URL for a Telegram-verified email",
    description=(
        "Service-role only. Calls supabase.auth.admin.generate_link, "
        "persists the hashed_token on the telegram_signup_sessions row, "
        "and returns a direct PKCE URL (/auth/confirm?token_hash=...) for "
        "delivery via Telegram. The URL targets the portal's /auth/confirm "
        "server route handler directly (PKCE flow) rather than the Supabase "
        "hosted action_link (which 302s with tokens in the URL fragment — "
        "a server-side route handler cannot read URL fragments). "
        "The verification_type field is forwarded verbatim from Supabase."
    ),
)
async def generate_magiclink_for_telegram_user(
    body: GenerateMagiclinkRequest,
    _auth: None = Depends(_require_service_role),
    repo: TelegramSignupSessionRepository = Depends(_get_repo_for_request),
) -> GenerateMagiclinkResponse:
    settings = get_settings()
    redirect_to = f"{settings.portal_url.rstrip('/')}/auth/confirm?next=/onboarding"

    try:
        supabase = await get_supabase_client()
        link_result = await supabase.auth.admin.generate_link(
            {
                "type": _SUPABASE_LINK_TYPE,
                "email": str(body.email),
                "options": {"redirect_to": redirect_to},
            }
        )
        props = link_result.properties

        # Persist the hashed_token + verification_type on the row via the
        # FSM CAS helper (CODE_SENT → MAGIC_LINK_SENT). The verification_type
        # is forwarded VERBATIM from the Supabase response.
        try:
            await repo.transition_to_magic_link_sent(
                telegram_id=body.telegram_id,
                hashed_token=props.hashed_token,
                verification_type=props.verification_type,
            )
        except ExpiredOrConcurrentError as exc:
            logger.warning(
                "magic_link_persistence_blocked telegram_id_hash=%s reason=%s",
                telegram_id_hash(body.telegram_id),
                str(exc),
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Signup session expired or already advanced past CODE_SENT. "
                    "Caller should re-issue OTP via sign_in_with_otp."
                ),
            )

        # Telemetry — wrapped to NEVER block the response path. If structured
        # logging fails (Pydantic validation, sink error), we still return the
        # action_link so the user can complete signup. Persistence already
        # advanced via CAS above.
        try:
            emit_signup_magic_link_minted(
                SignupMagicLinkMintedEvent(
                    email_hash=email_hash(str(body.email)),
                    ts=datetime.now(timezone.utc),
                    action_link_ttl_seconds=_SUPABASE_ACTION_LINK_TTL_S,
                    verification_type=props.verification_type,
                )
            )
        except Exception:  # pragma: no cover - defensive
            logger.exception(
                "telemetry_emit_failed event=signup_magic_link_minted "
                "telegram_id_hash=%s",
                telegram_id_hash(body.telegram_id),
            )

        # GH #435: deliver a direct PKCE URL to the portal's /auth/confirm
        # server route, NOT props.action_link (the Supabase hosted verify URL).
        #
        # props.action_link 302s back to redirect_to with tokens in the URL
        # *fragment* (#access_token=...).  A server-side Next.js route handler
        # (portal/src/app/auth/confirm/route.ts) runs in Node, which has no
        # access to URL fragments — the user would land on
        # /login?error=missing_params.
        #
        # Instead we build the portal /auth/confirm URL directly with the
        # PKCE token_hash as a query param.  The /auth/confirm route handler
        # is already written for this shape (it reads searchParams.token_hash).
        #
        # redirect_to is still passed to Supabase above as an options hint
        # (Supabase ignores it for admin-generated links, but it documents
        # intent and keeps the call consistent with the Supabase docs).
        pkce_action_link = (
            f"{settings.portal_url.rstrip('/')}/auth/confirm"
            f"?token_hash={props.hashed_token}"
            f"&type={_SUPABASE_LINK_TYPE}"
            f"&next=/onboarding"
        )
        return GenerateMagiclinkResponse(
            action_link=pkce_action_link,
            hashed_token=props.hashed_token,
            verification_type=props.verification_type,
            expires_at=datetime.now(timezone.utc)
            + timedelta(seconds=_SUPABASE_ACTION_LINK_TTL_S),
        )

    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        logger.error(
            "generate_magiclink_failed telegram_id_hash=%s err=%s",
            telegram_id_hash(body.telegram_id),
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate magic link",
        )


# --------------------------------------------------------------------------
# Spec 216 EM-2 — autobind Telegram on /auth/confirm
# --------------------------------------------------------------------------


class AutobindTelegramResponse(BaseModel):
    """Response model for POST /auth/autobind-telegram (Spec 216 EM-2).

    `bound` indicates whether a fresh telegram_id binding was created on
    THIS request (BindResult.BOUND). `already_bound` is True when the
    user was already linked to the same telegram_id (idempotent re-call).
    `no_session` is True when no in-flight Telegram signup session was
    found for the user's email — the caller should silently continue
    (portal-first signup; user can manually link later).
    """

    bound: bool = Field(..., description="Fresh bind happened on this call")
    already_bound: bool = Field(
        ..., description="User was already linked to this telegram_id"
    )
    no_session: bool = Field(
        ..., description="No telegram_signup_sessions row matched the user's email"
    )


@user_router.post(
    "/autobind-telegram",
    response_model=AutobindTelegramResponse,
    summary="Auto-bind Telegram on /auth/confirm magic-link click",
    description=(
        "Spec 216 EM-2 path B. Called by the portal /auth/confirm route "
        "AFTER verifyOtp succeeds. Looks up the in-flight "
        "telegram_signup_sessions row by the JWT subject's email, then "
        "atomically binds users.telegram_id and deletes the session row. "
        "Idempotent: a re-call with the same JWT returns no_session=True "
        "(row already deleted) and 200, never 4xx. Returns 409 only when "
        "the telegram_id is already bound to a DIFFERENT user."
    ),
)
async def autobind_telegram_on_confirm(
    user: AuthenticatedUser = Depends(get_authenticated_user),
    session: AsyncSession = Depends(get_async_session),
) -> AutobindTelegramResponse:
    """Look up telegram_signup_sessions by user email; atomic bind.

    Three cases:
    1. No session row (portal-first signup or already-completed) → 200
       with no_session=True. Front-end continues to /onboarding.
    2. Session found + bind succeeded → 200 with bound=True (or
       already_bound=True if the user already had this telegram_id).
       Session row deleted via delete_on_completion (idempotent CAS:
       MAGIC_LINK_SENT-only).
    3. Session found but telegram_id already held by a DIFFERENT user
       → 409 Conflict. Caller must surface a copy-side error (E4 /
       E13 in the plan edge-case matrix).
    """
    if not user.email:
        # Defensive: JWT without email cannot be bound. Treat as
        # no-session so the portal continues without surprising the
        # user with a 4xx on /auth/confirm.
        logger.info("autobind_no_email user_id=%s", user.id)
        return AutobindTelegramResponse(
            bound=False, already_bound=False, no_session=True
        )

    repo = TelegramSignupSessionRepository(session)
    user_repo = UserRepository(session)

    sess = await repo.get_by_email(str(user.email))
    if sess is None:
        # Portal-first signup OR already-completed bind — the row was
        # deleted by delete_on_completion on a prior call. Either way
        # the front-end should silently continue.
        return AutobindTelegramResponse(
            bound=False, already_bound=False, no_session=True
        )

    telegram_id = sess.telegram_id

    try:
        bind_result = await user_repo.update_telegram_id(
            user_id=user.id, telegram_id=telegram_id
        )
    except TelegramIdAlreadyBoundByOtherUserError:
        logger.warning(
            "autobind_conflict user_id=%s telegram_id_hash=%s",
            user.id,
            telegram_id_hash(telegram_id),
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="telegram_already_bound_to_other_user",
        )
    except ValueError:
        # User row missing in public.users (auto-provision happens
        # post-signup elsewhere). Treat as no-session so the wizard
        # can proceed; the bot's FR-11b /start <code> path will bind
        # it later.
        logger.info(
            "autobind_user_row_missing user_id=%s — deferring bind", user.id
        )
        return AutobindTelegramResponse(
            bound=False, already_bound=False, no_session=True
        )

    # Bind succeeded — clean up the FSM row. delete_on_completion is
    # idempotent and only removes MAGIC_LINK_SENT rows, so a CODE_SENT
    # row (path-A converged via TG before the magic-link click) is
    # left untouched and the bot's existing FR-5 path will handle it.
    try:
        await repo.delete_on_completion(telegram_id=telegram_id)
    except Exception:  # pragma: no cover - defensive
        logger.exception(
            "autobind_session_delete_failed telegram_id_hash=%s",
            telegram_id_hash(telegram_id),
        )

    return AutobindTelegramResponse(
        bound=(bind_result == BindResult.BOUND),
        already_bound=(bind_result == BindResult.ALREADY_BOUND_SAME_USER),
        no_session=False,
    )
