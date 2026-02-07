"""Telegram link code model for portal-to-telegram account linking.

Stores temporary link codes that users generate in the portal
and verify via the Telegram bot /link command.
"""

import secrets
import string
from datetime import datetime, timedelta

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from uuid import UUID

from nikita.db.models.base import Base


def generate_link_code(length: int = 6) -> str:
    """Generate a random alphanumeric link code.

    Args:
        length: Length of the code (default 6).

    Returns:
        Uppercase alphanumeric code.
    """
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


class TelegramLinkCode(Base):
    """Temporary code for linking portal account to Telegram.

    Flow:
    1. User clicks "Link Telegram" in portal → code generated
    2. Code displayed with instructions to send /link CODE to bot
    3. User sends /link CODE to bot → bot verifies and links accounts
    4. Code deleted after use or expiry

    Table: telegram_link_codes
    Primary Key: code (6-char alphanumeric)
    """

    __tablename__ = "telegram_link_codes"

    # 6-character alphanumeric code as primary key
    code: Mapped[str] = mapped_column(
        String(6),
        primary_key=True,
        nullable=False,
    )

    # User who generated the code (portal auth user)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # When code was generated
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # When code expires (10 minutes from creation)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"TelegramLinkCode(code={self.code}, user_id={self.user_id}, expires_at={self.expires_at})"

    def is_expired(self) -> bool:
        """Check if link code has expired.

        Returns:
            True if current time is past expires_at.
        """
        from nikita.db.models.base import utc_now

        return utc_now() > self.expires_at

    @classmethod
    def create(cls, user_id: UUID) -> "TelegramLinkCode":
        """Create a new link code for a user.

        Args:
            user_id: The portal user's UUID.

        Returns:
            New TelegramLinkCode instance with generated code and 10-minute expiry.
        """
        from nikita.db.models.base import utc_now

        return cls(
            code=generate_link_code(),
            user_id=user_id,
            expires_at=utc_now() + timedelta(minutes=10),
        )
