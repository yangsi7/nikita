"""Shared portal bridge URL generation utility.

GH #233: Extracted from duplicated code in message_handler.py and otp_handler.py.
Generates time-limited, single-use bridge tokens for zero-click portal auth.
"""

import logging
from uuid import UUID

from nikita.config.settings import get_settings

logger = logging.getLogger(__name__)


async def generate_portal_bridge_url(
    user_id: str,
    redirect_path: str = "/onboarding",
) -> str | None:
    """Generate a time-limited bridge token URL for zero-click portal auth.

    GH #187: Replaces magic link approach which failed due to PKCE mismatch
    (server-side generate_link -> client-side exchangeCodeForSession requires
    code_verifier that doesn't exist in the user's browser).

    Creates a short-lived, single-use bridge token in the database.
    When the user clicks the URL, the portal exchanges the token
    for a Supabase session via verifyOtp (bypassing PKCE).

    Args:
        user_id: User's UUID string.
        redirect_path: Portal path to redirect after auth.

    Returns:
        Bridge URL string, or None on failure.
    """
    try:
        from nikita.db.database import get_session_maker
        from nikita.db.repositories.auth_bridge_repository import (
            AuthBridgeRepository,
        )

        settings = get_settings()
        portal_url = settings.portal_url or "https://portal-phi-orcin.vercel.app"

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
