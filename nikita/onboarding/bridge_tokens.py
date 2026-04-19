"""Portal bridge URL generator for Spec 214 FR-11c.

Produces the URL shown on the Telegram `/start` reply inline button.
Two modes per AC-11c.12:

- E1 (new user, unknown telegram_id): `user_id=None, reason=None` →
  returns the bare `{portal_url}/onboarding/auth` (no token, no query
  params). The portal page renders the magic-link entry form.
- E3-E6 (onboarded or limbo): `user_id + reason` → mints a
  single-use `PortalBridgeToken` and returns
  `{portal_url}/onboarding/auth?bridge=<token>`. The portal consumes
  `?bridge=` via `POST /api/v1/portal/onboarding/auth/bridge` (AC-T1.2.3)
  to establish a session cookie without showing the magic-link form.

DISTINCT from the legacy helper at `nikita/platforms/telegram/utils.py`
(same name, different module), which creates `auth_bridge_tokens` rows.
The two helpers have incompatible signatures:

- legacy: `generate_portal_bridge_url(user_id: str, redirect_path: str)`
- this module: `generate_portal_bridge_url(user_id=None, reason=None)`

Always import by fully-qualified module name to disambiguate.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from nikita.config.settings import get_settings
from nikita.db.database import get_session_maker
from nikita.db.models.base import utc_now
from nikita.db.repositories.portal_bridge_token_repository import (
    PortalBridgeTokenRepository,
)

# Reuse threshold (review finding): if the most-recent active token for
# `user_id`+`reason` has at least this much TTL remaining, return its URL
# instead of minting a new row. Prevents unbounded mint pressure when a
# user taps `/start` multiple times.
REUSE_MIN_REMAINING: timedelta = timedelta(hours=1)

logger = logging.getLogger(__name__)

# Mirror of PortalBridgeReason from the model. Duplicated here so
# callers don't have to import the model just to type-annotate.
BridgeReason = Literal["resume", "re-onboard"]


def _portal_base_url() -> str:
    """Resolve the portal base URL from settings."""
    settings = get_settings()
    # Fall back to the canonical production URL if settings lack it; the
    # same fallback the legacy helper uses. In practice settings always
    # carry portal_url in deployed environments.
    return (
        settings.portal_url
        or "https://portal-phi-orcin.vercel.app"
    )


async def _mint_or_reuse_bridge_token(
    user_uuid: UUID,
    reason: BridgeReason,
    session: AsyncSession,
) -> str:
    """Mint or reuse an active portal bridge token for `user_uuid`+`reason`.

    Shared core for both call paths (injected session vs self-opened).
    The caller is responsible for committing `session` when the mint
    path runs. This helper never commits — keeps DI-friendly: if a
    request-scoped session is injected, the request manager commits.
    If we opened our own session, the outer wrapper commits.

    Returns the token string. Logs whether it was minted or reused.
    """
    repo = PortalBridgeTokenRepository(session)
    existing = await repo.get_active_for_user(user_uuid, reason)
    if existing is not None and (
        existing.expires_at - utc_now() >= REUSE_MIN_REMAINING
    ):
        token = existing.token
        minted = False
    else:
        token = await repo.mint(user_uuid, reason)
        minted = True
    # No user_id or token material in the log line: token is a credential,
    # and user_id is PII-adjacent in this scope. Log only the fact + reason.
    logger.info(
        "portal_bridge_url: %s token for reason=%s (TTL per matrix)",
        "minted" if minted else "reused active",
        reason,
    )
    return token


async def generate_portal_bridge_url(
    user_id: str | None = None,
    reason: BridgeReason | None = None,
    *,
    session: AsyncSession | None = None,
) -> str:
    """Generate the portal URL for a Telegram `/start` inline button.

    Arguments are intentionally both-or-neither for (user_id, reason):

    - Both None (E1 new user): returns bare `{portal}/onboarding/auth`.
      No DB write. Caller guarantees there is no existing DB user to
      bridge into (AC-11c.1). `session` is ignored.
    - Both provided (E3-E6): mints a single-use token for `user_id`
      with TTL per `reason` matrix (24h resume, 1h re-onboard). Returns
      `{portal}/onboarding/auth?bridge=<token>`.

    Session handling (DI):
    - `session is None` (default): helper opens its own session via
      `get_session_maker()` and commits on successful mint. Backward-
      compat path for scripts / places without a session to thread.
    - `session` provided: helper uses the injected session and does NOT
      commit — the caller's unit-of-work owns commit/rollback. This is
      the path MessageHandler takes (shares the request-scoped session
      already attached to its repositories) and the path unit tests
      rely on to avoid bootstrapping a real DB engine.

    Raises:
        ValueError: if exactly one of (user_id, reason) is provided.
    """
    if user_id is None and reason is None:
        return f"{_portal_base_url()}/onboarding/auth"

    if user_id is None or reason is None:
        raise ValueError(
            "generate_portal_bridge_url requires either BOTH user_id and "
            "reason (mint bridge token) or NEITHER (E1 bare URL)"
        )

    user_uuid = UUID(user_id)

    if session is not None:
        # DI path: caller owns the unit of work. We never commit here.
        token = await _mint_or_reuse_bridge_token(user_uuid, reason, session)
    else:
        # Self-opened path: we own commit for the mint branch.
        session_maker = get_session_maker()
        async with session_maker() as owned_session:
            token = await _mint_or_reuse_bridge_token(
                user_uuid, reason, owned_session
            )
            await owned_session.commit()

    return f"{_portal_base_url()}/onboarding/auth?bridge={token}"
