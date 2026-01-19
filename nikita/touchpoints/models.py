"""Pydantic models for Proactive Touchpoint System (Spec 025, Phase A: T002).

Models:
- TriggerType: Enum for trigger types (time, event, gap)
- TriggerContext: Context for what triggered the touchpoint
- TouchpointConfig: Configuration for chapter-specific rates
- ScheduledTouchpoint: Main model for scheduled touchpoints
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class TriggerType(str, Enum):
    """Type of trigger that initiated the touchpoint.

    Values:
        TIME: Time-based trigger (morning/evening slots)
        EVENT: Life event trigger (from 022)
        GAP: Gap-based trigger (>24h without contact)
    """

    TIME = "time"
    EVENT = "event"
    GAP = "gap"


class TriggerContext(BaseModel):
    """Context for what triggered the touchpoint.

    Attributes:
        trigger_type: Type of trigger (time/event/gap)
        time_slot: Time slot name (morning/evening) for time triggers
        event_id: Event ID for event triggers
        event_type: Event type for event triggers
        event_description: Event description for event triggers
        hours_since_contact: Hours since last contact for gap triggers
        chapter: User's current chapter when triggered
        emotional_state: User's emotional state snapshot
    """

    trigger_type: TriggerType
    time_slot: str | None = None
    event_id: str | None = None
    event_type: str | None = None
    event_description: str | None = None
    hours_since_contact: float | None = None
    chapter: int = 1
    emotional_state: dict[str, Any] = Field(default_factory=dict)

    @field_validator("time_slot")
    @classmethod
    def validate_time_slot_value(cls, v: str | None) -> str | None:
        """Validate time_slot values."""
        if v is not None and v not in ("morning", "evening"):
            raise ValueError("time_slot must be 'morning' or 'evening'")
        return v

    @model_validator(mode="after")
    def validate_time_slot_required(self) -> "TriggerContext":
        """Validate time_slot is required for TIME triggers."""
        if self.trigger_type == TriggerType.TIME and self.time_slot is None:
            raise ValueError("time_slot is required for TIME triggers")
        return self

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return self.model_dump()


class TouchpointConfig(BaseModel):
    """Configuration for touchpoint rates by chapter.

    Attributes:
        initiation_rate_min: Minimum initiation rate (0.0-1.0)
        initiation_rate_max: Maximum initiation rate (0.0-1.0)
        strategic_silence_rate: Rate of intentional skips (0.0-1.0)
        morning_slot_start: Start hour for morning slot (user timezone)
        morning_slot_end: End hour for morning slot (user timezone)
        evening_slot_start: Start hour for evening slot (user timezone)
        evening_slot_end: End hour for evening slot (user timezone)
        min_gap_hours: Minimum hours between touchpoints
        gap_trigger_hours: Hours without contact to trigger gap touchpoint
    """

    initiation_rate_min: float = Field(ge=0.0, le=1.0, default=0.15)
    initiation_rate_max: float = Field(ge=0.0, le=1.0, default=0.20)
    strategic_silence_rate: float = Field(ge=0.0, le=1.0, default=0.20)
    morning_slot_start: int = Field(ge=0, le=23, default=8)
    morning_slot_end: int = Field(ge=0, le=23, default=10)
    evening_slot_start: int = Field(ge=0, le=23, default=19)
    evening_slot_end: int = Field(ge=0, le=23, default=21)
    min_gap_hours: float = Field(ge=0.0, default=4.0)
    gap_trigger_hours: float = Field(ge=0.0, default=24.0)

    @field_validator("initiation_rate_max")
    @classmethod
    def validate_rate_max(cls, v: float, info) -> float:
        """Ensure max >= min."""
        min_rate = info.data.get("initiation_rate_min", 0.0)
        if v < min_rate:
            raise ValueError("initiation_rate_max must be >= initiation_rate_min")
        return v


# Chapter-specific configs (FR-002)
CHAPTER_CONFIGS: dict[int, TouchpointConfig] = {
    1: TouchpointConfig(
        initiation_rate_min=0.15,
        initiation_rate_max=0.20,
        strategic_silence_rate=0.20,
    ),
    2: TouchpointConfig(
        initiation_rate_min=0.20,
        initiation_rate_max=0.25,
        strategic_silence_rate=0.15,
    ),
    3: TouchpointConfig(
        initiation_rate_min=0.25,
        initiation_rate_max=0.30,
        strategic_silence_rate=0.10,
    ),
    4: TouchpointConfig(
        initiation_rate_min=0.25,
        initiation_rate_max=0.30,
        strategic_silence_rate=0.10,
    ),
    5: TouchpointConfig(
        initiation_rate_min=0.25,
        initiation_rate_max=0.30,
        strategic_silence_rate=0.10,
    ),
}


def get_config_for_chapter(chapter: int) -> TouchpointConfig:
    """Get touchpoint configuration for a given chapter.

    Args:
        chapter: Chapter number (1-5)

    Returns:
        TouchpointConfig for the chapter
    """
    return CHAPTER_CONFIGS.get(chapter, CHAPTER_CONFIGS[1])


class ScheduledTouchpoint(BaseModel):
    """Model for a scheduled proactive touchpoint.

    Represents a Nikita-initiated message that has been scheduled for delivery.

    Attributes:
        touchpoint_id: Unique identifier
        user_id: User this touchpoint is for
        trigger_type: Type of trigger (time/event/gap)
        trigger_context: Context for the trigger
        message_content: Generated message content
        delivery_at: When to deliver the message
        delivered: Whether the message has been delivered
        skipped: Whether this was strategically skipped
        skip_reason: Reason for skip (if skipped)
        created_at: When the touchpoint was scheduled
        delivered_at: When the message was delivered (if delivered)
    """

    touchpoint_id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    trigger_type: TriggerType
    trigger_context: TriggerContext
    message_content: str = ""
    delivery_at: datetime
    delivered: bool = False
    skipped: bool = False
    skip_reason: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    delivered_at: datetime | None = None

    @property
    def id(self) -> UUID:
        """Alias for touchpoint_id for convenience."""
        return self.touchpoint_id

    @property
    def chapter(self) -> int:
        """Get chapter from trigger context."""
        return self.trigger_context.chapter

    @property
    def is_due(self) -> bool:
        """Check if touchpoint is due for delivery."""
        if self.delivered or self.skipped:
            return False
        return datetime.now(timezone.utc) >= self.delivery_at

    def mark_delivered(self) -> "ScheduledTouchpoint":
        """Mark touchpoint as delivered."""
        return self.model_copy(
            update={
                "delivered": True,
                "delivered_at": datetime.now(timezone.utc),
            }
        )

    def mark_skipped(self, reason: str) -> "ScheduledTouchpoint":
        """Mark touchpoint as strategically skipped."""
        return self.model_copy(
            update={
                "skipped": True,
                "skip_reason": reason,
            }
        )
