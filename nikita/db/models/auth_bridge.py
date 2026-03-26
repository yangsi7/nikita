"""Auth bridge token model for Telegram→Portal zero-click authentication.

Stores short-lived, single-use tokens that allow the Telegram bot to
create a portal URL that auto-authenticates the user without PKCE.

Flow:
1. After OTP verification, backend creates bridge token in DB
2. Telegram button links to portal/auth/bridge?token=XXX
3. Portal route exchanges token with backend → gets hashed_token
4. Portal calls verifyOtp({token_hash}) → session established
5. Token deleted after use or expiry

Follows the same pattern as telegram_link.py (TelegramLinkCode).
"""

import secrets
from datetime import datetime, timedelta

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from uuid import UUID

from nikita.db.models.base import Base


def generate_bridge_token() -> str:
    """Generate a cryptographically secure bridge token.

    Uses secrets.token_urlsafe(32) which produces a URL-safe
    base64-encoded token of ~43 characters from 32 random bytes.

    Returns:
        URL-safe base64 token string.
    """
    return secrets.token_urlsafe(32)


class AuthBridgeToken(Base):
    """Short-lived, single-use token for Telegram→Portal auth bridge.

    Replaces the broken admin.generate_link() magic link approach
    which fails due to PKCE code_verifier mismatch (server-side
    generation vs client-side exchange).

    Table: auth_bridge_tokens
    Primary Key: token (URL-safe base64, ~43 chars)
    """

    __tablename__ = "auth_bridge_tokens"

    token: Mapped[str] = mapped_column(
        Text,
        primary_key=True,
        nullable=False,
    )

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    redirect_path: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="/onboarding",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"AuthBridgeToken(token={self.token[:8]}..., user_id={self.user_id})"

    def is_expired(self) -> bool:
        """Check if token has expired."""
        from nikita.db.models.base import utc_now

        return utc_now() > self.expires_at

    @classmethod
    def create(
        cls, user_id: UUID, redirect_path: str = "/onboarding"
    ) -> "AuthBridgeToken":
        """Create a new bridge token with 5-minute expiry.

        Args:
            user_id: The user's UUID (from Supabase auth.users).
            redirect_path: Portal path to redirect to after auth.

        Returns:
            New AuthBridgeToken instance (not yet persisted).
        """
        from nikita.db.models.base import utc_now

        return cls(
            token=generate_bridge_token(),
            user_id=user_id,
            redirect_path=redirect_path,
            expires_at=utc_now() + timedelta(minutes=5),
        )
