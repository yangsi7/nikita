"""Scoring engine models (spec 003).

This module defines Pydantic models for the scoring engine:
- MetricDeltas: Per-interaction score changes (-10 to +10)
- ResponseAnalysis: Full LLM analysis result with behaviors
- ConversationContext: Context data for LLM analysis
- ScoreChangeEvent: Threshold events (boss, critical, game-over)
"""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class MetricDeltas(BaseModel):
    """Per-interaction metric deltas with bounds validation.

    All deltas are bounded to [-10, +10] per interaction.
    These are applied to the four relationship metrics.
    """

    intimacy: Decimal = Field(
        default=Decimal("0"),
        description="Change to intimacy score (-10 to +10)",
    )
    passion: Decimal = Field(
        default=Decimal("0"),
        description="Change to passion score (-10 to +10)",
    )
    trust: Decimal = Field(
        default=Decimal("0"),
        description="Change to trust score (-10 to +10)",
    )
    secureness: Decimal = Field(
        default=Decimal("0"),
        description="Change to secureness score (-10 to +10)",
    )

    @field_validator("intimacy", "passion", "trust", "secureness")
    @classmethod
    def validate_delta_bounds(cls, v: Decimal, info) -> Decimal:
        """Ensure delta is within [-10, +10] bounds."""
        if v < Decimal("-10"):
            raise ValueError(f"{info.field_name} delta cannot be less than -10")
        if v > Decimal("10"):
            raise ValueError(f"{info.field_name} delta cannot exceed +10")
        return v

    @property
    def total(self) -> Decimal:
        """Sum of all deltas."""
        return self.intimacy + self.passion + self.trust + self.secureness

    @property
    def is_positive(self) -> bool:
        """Whether total delta is positive (> 0)."""
        return self.total > Decimal("0")


class ResponseAnalysis(BaseModel):
    """Full LLM analysis result for a conversation interaction.

    Contains metric deltas, explanation, identified behaviors,
    and confidence score from the LLM analysis.
    """

    deltas: MetricDeltas = Field(
        description="Metric changes from this interaction",
    )
    explanation: str = Field(
        default="",
        description="LLM explanation of why these deltas were assigned",
    )
    behaviors_identified: list[str] = Field(
        default_factory=list,
        description="Behaviors detected in the interaction",
    )
    confidence: Decimal = Field(
        default=Decimal("1.0"),
        ge=Decimal("0"),
        le=Decimal("1"),
        description="LLM confidence in the analysis (0-1)",
    )

    @field_validator("confidence")
    @classmethod
    def validate_confidence_bounds(cls, v: Decimal) -> Decimal:
        """Ensure confidence is within [0, 1] bounds."""
        if v < Decimal("0"):
            raise ValueError("confidence cannot be less than 0")
        if v > Decimal("1"):
            raise ValueError("confidence cannot exceed 1")
        return v


class ConversationContext(BaseModel):
    """Context data for LLM analysis of conversations.

    Provides the LLM with information about the current game state
    to inform scoring decisions.
    """

    chapter: int = Field(
        ge=1,
        le=5,
        description="Current chapter (1-5)",
    )
    relationship_score: Decimal = Field(
        ge=Decimal("0"),
        le=Decimal("100"),
        description="Current relationship score (0-100)",
    )
    recent_messages: list[tuple[str, str]] = Field(
        default_factory=list,
        description="Recent messages as (role, content) tuples",
    )
    relationship_state: str = Field(
        default="stable",
        description="Current relationship state",
    )
    engagement_state: str | None = Field(
        default=None,
        description="Current engagement state from 014 module",
    )
    last_message_hours_ago: float | None = Field(
        default=None,
        description="Hours since last message",
    )


# Valid event types for score change events
ScoreEventType = Literal[
    "boss_threshold_reached",
    "critical_low",
    "recovery_from_critical",
    "game_over",
]


class ScoreChangeEvent(BaseModel):
    """Event emitted when score crosses significant thresholds.

    Used for boss encounters, critical low warnings, and game over.
    """

    event_type: ScoreEventType = Field(
        description="Type of threshold event",
    )
    chapter: int = Field(
        ge=1,
        le=5,
        description="Chapter when event occurred",
    )
    score_before: Decimal = Field(
        description="Score before the change",
    )
    score_after: Decimal = Field(
        description="Score after the change",
    )
    threshold: Decimal | None = Field(
        default=None,
        description="Threshold that was crossed (if applicable)",
    )
    details: dict | None = Field(
        default=None,
        description="Additional event details",
    )
