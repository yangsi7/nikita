"""Repository for pending registration operations.

Handles storage and retrieval of pending registrations during
the OTP authentication flow.
"""

from datetime import datetime, timedelta

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.base import utc_now
from nikita.db.models.pending_registration import PendingRegistration


class PendingRegistrationRepository:
    """Repository for pending registration operations.

    Note: This doesn't inherit from BaseRepository because:
    - Primary key is telegram_id (bigint), not UUID
    - Simple CRUD operations only
    - No relationships or eager loading needed
    """

    # Default expiry time in minutes
    DEFAULT_EXPIRY_MINUTES = 10

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: Async SQLAlchemy session for database operations.
        """
        self._session = session

    @property
    def session(self) -> AsyncSession:
        """Access the database session."""
        return self._session

    async def store(
        self,
        telegram_id: int,
        email: str,
        chat_id: int | None = None,
        otp_state: str = "pending",
        expires_at: datetime | None = None,
    ) -> PendingRegistration:
        """Store a pending registration.

        Uses upsert (INSERT ON CONFLICT UPDATE) to handle case where
        user re-requests OTP code before verifying previous one.

        Args:
            telegram_id: Telegram user ID.
            email: Email address for OTP code.
            chat_id: Telegram chat ID for sending messages back.
            otp_state: OTP state machine state ('pending', 'code_sent', 'verified', 'expired').
            expires_at: Optional custom expiry time. Defaults to 10 minutes from now.

        Returns:
            The created/updated PendingRegistration.
        """
        if expires_at is None:
            expires_at = utc_now() + timedelta(minutes=self.DEFAULT_EXPIRY_MINUTES)

        # Use upsert to handle re-registration
        # Reset otp_attempts to 0 on new registration
        stmt = insert(PendingRegistration).values(
            telegram_id=telegram_id,
            email=email,
            chat_id=chat_id,
            otp_state=otp_state,
            otp_attempts=0,
            created_at=utc_now(),
            expires_at=expires_at,
        ).on_conflict_do_update(
            index_elements=["telegram_id"],
            set_={
                "email": email,
                "chat_id": chat_id,
                "otp_state": otp_state,
                "otp_attempts": 0,  # Reset attempts on re-registration
                "created_at": utc_now(),
                "expires_at": expires_at,
            },
        ).returning(PendingRegistration)

        result = await self._session.execute(stmt)
        registration = result.scalar_one()

        return registration

    async def get(self, telegram_id: int) -> PendingRegistration | None:
        """Get pending registration by Telegram ID.

        Only returns non-expired registrations.

        Args:
            telegram_id: Telegram user ID to look up.

        Returns:
            PendingRegistration if found and not expired, None otherwise.
        """
        stmt = select(PendingRegistration).where(
            PendingRegistration.telegram_id == telegram_id,
            PendingRegistration.expires_at > utc_now(),  # Not expired
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_email(self, telegram_id: int) -> str | None:
        """Get pending email for Telegram ID.

        Convenience method that returns just the email string.

        Args:
            telegram_id: Telegram user ID to look up.

        Returns:
            Email if found and not expired, None otherwise.
        """
        registration = await self.get(telegram_id)
        return registration.email if registration else None

    async def get_by_email(self, email: str) -> PendingRegistration | None:
        """Get pending registration by email address.

        Used during magic link verification when we have email from Supabase
        but need to recover telegram_id to complete registration.

        Args:
            email: Email address to look up.

        Returns:
            PendingRegistration if found and not expired, None otherwise.
        """
        stmt = select(PendingRegistration).where(
            PendingRegistration.email == email,
            PendingRegistration.expires_at > utc_now(),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email_any(self, email: str) -> PendingRegistration | None:
        """Get pending registration by email, including expired ones.

        Used when Supabase has already verified the email via magic link.
        In this case, we should honor the pending registration even if our
        internal 10-minute window has passed, since Supabase magic links
        typically last longer.

        Args:
            email: Email address to look up.

        Returns:
            PendingRegistration if found (regardless of expiration), None otherwise.
        """
        stmt = select(PendingRegistration).where(
            PendingRegistration.email == email,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete(self, telegram_id: int) -> bool:
        """Delete pending registration by Telegram ID.

        Args:
            telegram_id: Telegram user ID to delete.

        Returns:
            True if registration was found and deleted, False if not found.
        """
        stmt = delete(PendingRegistration).where(
            PendingRegistration.telegram_id == telegram_id
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def increment_attempts(self, telegram_id: int) -> int:
        """Atomically increment OTP attempt counter and return new count.

        Uses atomic SQL increment to prevent race conditions when multiple
        requests arrive simultaneously. This is critical for security -
        without atomic increment, attackers could bypass MAX_OTP_ATTEMPTS
        by sending parallel requests.

        Args:
            telegram_id: Telegram user ID.

        Returns:
            New attempt count after increment, or -1 if record not found.
        """
        # Use atomic SQL increment to prevent TOCTOU race condition
        # This ensures concurrent requests can't both read attempts=0
        stmt = (
            update(PendingRegistration)
            .where(PendingRegistration.telegram_id == telegram_id)
            .values(otp_attempts=PendingRegistration.otp_attempts + 1)
            .returning(PendingRegistration.otp_attempts)
        )
        result = await self._session.execute(stmt)
        await self._session.commit()

        row = result.fetchone()
        if row is None:
            return -1  # Record not found (was deleted or expired)

        return row[0]

    async def cleanup_expired(self) -> int:
        """Delete all expired registrations.

        Called by pg_cron job to clean up stale registrations.

        Returns:
            Number of expired registrations deleted.
        """
        stmt = delete(PendingRegistration).where(
            PendingRegistration.expires_at <= utc_now()
        )
        result = await self._session.execute(stmt)
        return result.rowcount
