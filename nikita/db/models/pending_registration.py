"""Pending registration model for OTP authentication flow.

Stores temporary registration data between OTP code sending and verification.
Records automatically expire after 10 minutes (handled by DB default + pg_cron).

OTP State Machine:
- 'pending': Initial state (email not yet sent)
- 'code_sent': OTP code sent to email, awaiting user input
- 'verified': Successfully verified (transient, record deleted after)
- 'expired': Code expired (for audit trail before cleanup)
"""

from datetime import datetime
from datetime import timedelta

from sqlalchemy import BigInteger, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from nikita.db.models.base import Base


class PendingRegistration(Base):
    """Pending registration awaiting OTP code verification.

    This is a transient table for the authentication flow:
    1. User provides email → record created with otp_state='pending'
    2. OTP code sent → otp_state updated to 'code_sent', chat_id stored
    3. User enters code → record deleted on success
    4. If not verified → pg_cron cleans up after expiry

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

    # Email for OTP code
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Telegram chat ID for sending messages back (needed for OTP flow)
    chat_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    # OTP state machine: 'pending', 'code_sent', 'verified', 'expired'
    otp_state: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
    )

    # Number of failed OTP verification attempts (max 3 before lockout)
    otp_attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
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
            f"email={self.email}, chat_id={self.chat_id}, "
            f"otp_state={self.otp_state}, otp_attempts={self.otp_attempts}, "
            f"expires_at={self.expires_at})"
        )

    def is_expired(self) -> bool:
        """Check if registration has expired.

        Returns:
            True if current time is past expires_at.
        """
        from nikita.db.models.base import utc_now
        return utc_now() > self.expires_at
