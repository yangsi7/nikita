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

from nikita.config.settings import get_settings
from nikita.db.database import get_async_session, get_supabase_client
from nikita.db.repositories.telegram_signup_session_repository import (
    ExpiredOrConcurrentError,
    TelegramSignupSessionRepository,
)
from nikita.monitoring.events import (
    SignupMagicLinkMintedEvent,
    email_hash,
    emit_signup_magic_link_minted,
    telegram_id_hash,
)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Portal Auth Admin"])
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
    summary="Mint a magic-link action_link for a Telegram-verified email",
    description=(
        "Service-role only. Calls supabase.auth.admin.generate_link, "
        "persists the hashed_token on the telegram_signup_sessions row, "
        "and returns the action_link for delivery via Telegram. The "
        "verification_type field is forwarded verbatim from Supabase."
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

        return GenerateMagiclinkResponse(
            action_link=str(props.action_link),
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
