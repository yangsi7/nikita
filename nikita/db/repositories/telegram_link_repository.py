"""Telegram link code repository for account linking operations.

Handles creation, verification, and cleanup of temporary link codes
used to connect portal accounts to Telegram accounts.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.telegram_link import TelegramLinkCode


class TelegramLinkRepository:
    """Repository for TelegramLinkCode operations.

    Provides:
    - Code creation for portal users
    - Code verification for Telegram bot
    - Cleanup of expired codes
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize TelegramLinkRepository.

        Args:
            session: Async SQLAlchemy session.
        """
        self.session = session

    async def create_link_code(self, user_id: UUID) -> TelegramLinkCode:
        """Create a new link code for a portal user.

        Deletes any existing codes for the user first to ensure
        only one active code per user.

        Args:
            user_id: The portal user's UUID.

        Returns:
            New TelegramLinkCode with generated code and 10-minute expiry.
        """
        # Delete any existing codes for this user
        await self.delete_for_user(user_id)

        # Create new code
        link_code = TelegramLinkCode.create(user_id)
        self.session.add(link_code)
        await self.session.flush()

        return link_code

    async def get_by_code(self, code: str) -> TelegramLinkCode | None:
        """Get link code by code string.

        Args:
            code: The 6-character link code.

        Returns:
            TelegramLinkCode if found, None otherwise.
        """
        stmt = select(TelegramLinkCode).where(TelegramLinkCode.code == code.upper())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def verify_code(self, code: str) -> UUID | None:
        """Verify a link code and return the associated user_id.

        If the code is valid and not expired, returns the user_id
        and deletes the code (single-use). If invalid or expired,
        returns None.

        Args:
            code: The 6-character link code to verify.

        Returns:
            User UUID if code is valid and not expired, None otherwise.
        """
        link_code = await self.get_by_code(code)

        if link_code is None:
            return None

        # Check expiry
        if link_code.is_expired():
            # Delete expired code
            await self.delete(code)
            return None

        # Valid code - get user_id and delete (single-use)
        user_id = link_code.user_id
        await self.delete(code)

        return user_id

    async def delete(self, code: str) -> bool:
        """Delete a link code.

        Args:
            code: The 6-character link code.

        Returns:
            True if code was deleted, False if not found.
        """
        stmt = delete(TelegramLinkCode).where(TelegramLinkCode.code == code.upper())
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    async def delete_for_user(self, user_id: UUID) -> int:
        """Delete all link codes for a user.

        Args:
            user_id: The user's UUID.

        Returns:
            Number of codes deleted.
        """
        stmt = delete(TelegramLinkCode).where(TelegramLinkCode.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.rowcount

    async def cleanup_expired(self) -> int:
        """Delete all expired link codes.

        Called by pg_cron to clean up expired codes.

        Returns:
            Number of codes deleted.
        """
        stmt = delete(TelegramLinkCode).where(
            TelegramLinkCode.expires_at < datetime.now(UTC)
        )
        result = await self.session.execute(stmt)
        return result.rowcount
