"""Shared helpers for the Telegram platform layer.

Leaf module. Do NOT import from `nikita.platforms.telegram.*` — only
from strictly lower layers (`nikita.config`, `nikita.db`). Keeps the
dependency graph one-way and prevents circular imports from handlers.

GH #233 — extracted to eliminate duplication of `_generate_portal_bridge_url`
across `otp_handler.py`, `message_handler.py`, and the delegated call in
`commands.py`. History: originally introduced in GH #187 to replace the
broken PKCE-mismatched magic-link flow; duplicated when PR #230 added the
same logic to `message_handler.py` for the slash-command path.
"""

from __future__ import annotations

import logging
from uuid import UUID

from nikita.config.settings import get_settings

logger = logging.getLogger(__name__)


async def generate_portal_bridge_url(
    user_id: str,
    redirect_path: str = "/onboarding",
) -> str | None:
    """Generate a portal bridge URL for zero-click Supabase auth.

    Creates a short-lived, single-use bridge token in the database.
    The portal exchanges the token for a Supabase session via verifyOtp
    (bypassing PKCE), then redirects to `redirect_path`.

    Args:
        user_id: User's UUID string.
        redirect_path: Portal path to redirect after auth. Defaults to
            "/onboarding" to match the most common caller.

    Returns:
        Bridge URL string, or None on any failure (callers fall back to
        the regular `/login?next=...` URL).
    """
    try:
        from nikita.db.database import get_session_maker
        from nikita.db.repositories.auth_bridge_repository import (
            AuthBridgeRepository,
        )

        # GH #374: settings.portal_url default is canonical; fallback removed.
        portal_url = get_settings().portal_url

        session_maker = get_session_maker()
        async with session_maker() as session:
            repo = AuthBridgeRepository(session)
            bridge = await repo.create_token(UUID(user_id), redirect_path)
            await session.commit()

        url = f"{portal_url}/auth/bridge?token={bridge.token}"
        logger.info(
            f"Generated bridge URL for user_id={user_id}, "
            f"redirect_path={redirect_path}"
        )
        return url

    except Exception as e:
        logger.warning(
            f"Failed to generate bridge URL for user_id={user_id}: {e}"
        )
        return None
