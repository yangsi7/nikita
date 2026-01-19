"""Scheduled touchpoint model for proactive Nikita initiations (Spec 025).

This model stores touchpoints that Nikita will initiate - messages she sends
without user prompting, based on time, life events, or conversation gaps.

Different from ScheduledEvent which is for delayed delivery of responses.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nikita.db.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from nikita.db.models.user import User


class ScheduledTouchpoint(Base, TimestampMixin):
    """Model for scheduled proactive touchpoints.

    Represents Nikita-initiated messages scheduled for delivery based on:
    - Time triggers (morning/evening slots)
    - Event triggers (life events from 022)
    - Gap triggers (>24h without contact)

    Attributes:
        id: Unique touchpoint identifier.
        user_id: Reference to the user this touchpoint is for.
        trigger_type: Type of trigger ('time', 'event', 'gap').
        trigger_context: JSONB with trigger-specific context.
        message_content: Generated message text.
        delivery_at: When the touchpoint should be delivered.
        delivered: Whether message has been delivered.
        delivered_at: When message was delivered (null if pending).
        skipped: Whether touchpoint was strategically skipped.
        skip_reason: Reason for skip (if skipped).
    """

    __tablename__ = "scheduled_touchpoints"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Foreign keys
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Trigger metadata
    trigger_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    trigger_context: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Message content
    message_content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )

    # Scheduling
    delivery_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    delivered: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Strategic silence
    skipped: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    skip_reason: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="scheduled_touchpoints",
        lazy="selectin",
    )

    # Indexes
    __table_args__ = (
        # Partial index for efficient due touchpoint queries
        Index(
            "idx_scheduled_touchpoints_due",
            "delivered",
            "skipped",
            "delivery_at",
            postgresql_where=(delivered.is_(False) & skipped.is_(False)),
        ),
    )

    def __repr__(self) -> str:
        return (
            f"ScheduledTouchpoint(id={self.id!r}, "
            f"trigger_type={self.trigger_type!r}, "
            f"delivered={self.delivered!r}, "
            f"delivery_at={self.delivery_at!r})"
        )

    @property
    def is_pending(self) -> bool:
        """Check if touchpoint is still pending delivery."""
        return not self.delivered and not self.skipped

    @property
    def is_due(self) -> bool:
        """Check if touchpoint is due for delivery."""
        return (
            self.is_pending
            and self.delivery_at <= datetime.now(self.delivery_at.tzinfo)
        )
