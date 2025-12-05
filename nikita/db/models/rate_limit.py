"""Rate limiting database model for preventing message abuse."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nikita.db.models.base import Base


class RateLimit(Base):
    """
    Database-backed rate limiting for user messages.

    Tracks message counts per user per window (minute/day).
    Enables rate limiting that persists across service restarts.

    Design:
    - Per-user, per-window (minute/day) counters
    - Automatic cleanup via TTL or scheduled job
    - Supports distributed deployments (multiple Cloud Run instances)
    """

    __tablename__ = "rate_limits"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Window identifier: "minute:<timestamp_minute>" or "day:<YYYY-MM-DD>"
    window: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Message count in this window
    count: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    # Expiration timestamp for automatic cleanup
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    # Relationship (optional, for easier querying)
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        # Composite unique constraint: one record per user per window
        Index("idx_rate_limit_user_window", "user_id", "window", unique=True),
        # Index for cleanup queries
        Index("idx_rate_limit_expires", "expires_at"),
    )
