"""Pending registration model for magic link authentication flow.

Stores temporary registration data between magic link sending and verification.
Records automatically expire after 10 minutes (handled by DB default + pg_cron).
"""

from datetime import datetime
from datetime import timedelta

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from nikita.db.models.base import Base


class PendingRegistration(Base):
    """Pending registration awaiting magic link verification.

    This is a transient table for the authentication flow:
    1. User provides email → record created
    2. User verifies magic link → record deleted
    3. If not verified → pg_cron cleans up after expiry

    Table: pending_registrations
    Primary Key: telegram_id (not UUID - one pending registration per user)
    """

    __tablename__ = "pending_registrations"

    # Telegram ID as primary key (one pending registration per telegram user)
    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        nullable=False,
    )

    # Email for magic link
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # When registration was initiated
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # When registration expires (10 minutes from creation)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now() + timedelta(minutes=10),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"PendingRegistration(telegram_id={self.telegram_id}, "
            f"email={self.email}, expires_at={self.expires_at})"
        )

    def is_expired(self) -> bool:
        """Check if registration has expired.

        Returns:
            True if current time is past expires_at.
        """
        from nikita.db.models.base import utc_now
        return utc_now() > self.expires_at
