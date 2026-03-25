"""Auth bridge token repository.

Handles creation, verification (single-use), and cleanup of bridge tokens
used for Telegram→Portal zero-click authentication.

Follows the same pattern as telegram_link_repository.py.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.auth_bridge import AuthBridgeToken


class AuthBridgeRepository:
    """Repository for AuthBridgeToken operations.

    Provides:
    - Token creation for Telegram OTP handler
    - Token verification (single-use) for portal bridge route
    - Cleanup of expired tokens (for pg_cron)
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with async SQLAlchemy session."""
        self.session = session

    async def create_token(
        self, user_id: UUID, redirect_path: str = "/onboarding"
    ) -> AuthBridgeToken:
        """Create a new bridge token. Deletes any existing tokens for the user first.

        Args:
            user_id: The user's UUID.
            redirect_path: Portal path to redirect to after auth.

        Returns:
            New AuthBridgeToken with generated token and 5-minute expiry.
        """
        await self.delete_for_user(user_id)
        token = AuthBridgeToken.create(user_id, redirect_path)
        self.session.add(token)
        await self.session.flush()
        return token

    async def get_by_token(self, token: str) -> AuthBridgeToken | None:
        """Get bridge token by token string.

        Args:
            token: The bridge token string.

        Returns:
            AuthBridgeToken if found, None otherwise.
        """
        stmt = select(AuthBridgeToken).where(AuthBridgeToken.token == token)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def verify_token(self, token: str) -> tuple[UUID, str] | None:
        """Verify and consume a bridge token (single-use).

        If valid and not expired, returns (user_id, redirect_path)
        and deletes the token. If invalid or expired, returns None.

        Args:
            token: The bridge token to verify.

        Returns:
            Tuple of (user_id, redirect_path) if valid, None otherwise.
        """
        bridge = await self.get_by_token(token)
        if bridge is None:
            return None

        if bridge.is_expired():
            await self.delete(token)
            return None

        # Extract data before deleting (single-use)
        user_id = bridge.user_id
        redirect_path = bridge.redirect_path
        await self.delete(token)
        return (user_id, redirect_path)

    async def delete(self, token: str) -> bool:
        """Delete a bridge token.

        Args:
            token: The bridge token string.

        Returns:
            True if token was deleted, False if not found.
        """
        stmt = delete(AuthBridgeToken).where(AuthBridgeToken.token == token)
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    async def delete_for_user(self, user_id: UUID) -> int:
        """Delete all bridge tokens for a user.

        Args:
            user_id: The user's UUID.

        Returns:
            Number of tokens deleted.
        """
        stmt = delete(AuthBridgeToken).where(AuthBridgeToken.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.rowcount

    async def cleanup_expired(self) -> int:
        """Delete all expired bridge tokens.

        Called by pg_cron or task endpoint to clean up.

        Returns:
            Number of tokens deleted.
        """
        stmt = delete(AuthBridgeToken).where(
            AuthBridgeToken.expires_at < datetime.now(UTC)
        )
        result = await self.session.execute(stmt)
        return result.rowcount
