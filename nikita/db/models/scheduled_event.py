"""Scheduled event model for unified text + voice message delivery.

This model supports delayed message delivery for both Telegram and voice platforms,
enabling chapter-based response timing (Ch1: 2-5min delay, Ch5: instant).

Spec: 011-background-tasks, FR-002 (Delayed Message Delivery)
Spec: 007-voice-agent, FR-013 (Unified Event Scheduling)
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nikita.db.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from nikita.db.models.conversation import Conversation
    from nikita.db.models.user import User


class EventPlatform(str, Enum):
    """Platform for scheduled event delivery."""

    TELEGRAM = "telegram"
    VOICE = "voice"


class EventStatus(str, Enum):
    """Status of a scheduled event."""

    PENDING = "pending"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    FAILED = "failed"


class EventType(str, Enum):
    """Type of scheduled event."""

    MESSAGE_DELIVERY = "message_delivery"
    CALL_REMINDER = "call_reminder"
    BOSS_PROMPT = "boss_prompt"
    FOLLOW_UP = "follow_up"


class ScheduledEvent(Base, TimestampMixin):
    """Model for scheduled events supporting both text and voice platforms.

    Supports unified event scheduling for:
    - Telegram delayed message delivery
    - Voice call reminders
    - Cross-platform follow-ups

    Attributes:
        id: Unique event identifier.
        user_id: Reference to the user this event is for.
        platform: Target platform ('telegram' or 'voice').
        event_type: Type of event ('message_delivery', 'call_reminder', etc).
        content: JSONB containing platform-specific payload.
        scheduled_at: When the event should be delivered.
        delivered_at: When the event was actually delivered (null if pending).
        status: Current status ('pending', 'delivered', 'cancelled', 'failed').
        retry_count: Number of delivery attempts.
        error_message: Error details if delivery failed.
        source_conversation_id: Optional reference to originating conversation.
    """

    __tablename__ = "scheduled_events"

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

    source_conversation_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Event metadata
    platform: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    # Payload (platform-specific)
    # For Telegram: {"chat_id": int, "text": str, "reply_markup": optional}
    # For Voice: {"voice_prompt": str, "agent_id": str}
    content: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )

    # Scheduling
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=EventStatus.PENDING.value,
    )

    retry_count: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="scheduled_events",
        lazy="selectin",
    )

    source_conversation: Mapped["Conversation | None"] = relationship(
        "Conversation",
        back_populates="scheduled_events",
        lazy="selectin",
    )

    # Indexes
    __table_args__ = (
        # Partial index for efficient pending event queries
        Index(
            "idx_scheduled_events_due",
            "status",
            "scheduled_at",
            postgresql_where=(status == EventStatus.PENDING.value),
        ),
    )

    def __repr__(self) -> str:
        return (
            f"ScheduledEvent(id={self.id!r}, "
            f"platform={self.platform!r}, "
            f"status={self.status!r}, "
            f"scheduled_at={self.scheduled_at!r})"
        )

    @property
    def is_pending(self) -> bool:
        """Check if event is still pending delivery."""
        return self.status == EventStatus.PENDING.value

    @property
    def is_due(self) -> bool:
        """Check if event is due for delivery."""
        return self.is_pending and self.scheduled_at <= datetime.now(self.scheduled_at.tzinfo)

    @property
    def can_retry(self) -> bool:
        """Check if event can be retried (max 3 attempts)."""
        return self.retry_count < 3
