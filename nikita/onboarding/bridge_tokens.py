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
from typing import Literal
from uuid import UUID

from nikita.config.settings import get_settings
from nikita.db.database import get_session_maker
from nikita.db.repositories.portal_bridge_token_repository import (
    PortalBridgeTokenRepository,
)

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


async def generate_portal_bridge_url(
    user_id: str | None = None,
    reason: BridgeReason | None = None,
) -> str:
    """Generate the portal URL for a Telegram `/start` inline button.

    Arguments are intentionally both-or-neither:

    - Both None (E1 new user): returns bare `{portal}/onboarding/auth`.
      No DB write. Caller guarantees there is no existing DB user to
      bridge into (AC-11c.1).
    - Both provided (E3-E6): mints a single-use token for `user_id`
      with TTL per `reason` matrix (24h resume, 1h re-onboard). Returns
      `{portal}/onboarding/auth?bridge=<token>`.

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

    session_maker = get_session_maker()
    async with session_maker() as session:
        repo = PortalBridgeTokenRepository(session)
        token = await repo.mint(UUID(user_id), reason)
        await session.commit()

    url = f"{_portal_base_url()}/onboarding/auth?bridge={token}"
    # No user_id or token material in the log line: token is a credential,
    # and user_id is PII-adjacent in this scope. Log only the fact + reason.
    logger.info(
        "portal_bridge_url: minted token for reason=%s (TTL per matrix)",
        reason,
    )
    return url
