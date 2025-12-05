"""Decay system models (spec 005).

This module defines Pydantic models for the decay system:
- DecayResult: Result of a decay calculation with audit trail
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class DecayResult(BaseModel):
    """Result of a decay calculation for a user.

    Contains all fields needed for audit trail and logging.
    Used by DecayCalculator and DecayProcessor.
    """

    user_id: UUID = Field(
        description="User ID for this decay result",
    )
    decay_amount: Decimal = Field(
        ge=Decimal("0"),
        description="Amount of decay applied (must be >= 0)",
    )
    score_before: Decimal = Field(
        description="User's score before decay was applied",
    )
    score_after: Decimal = Field(
        ge=Decimal("0"),
        description="User's score after decay (floors at 0)",
    )
    hours_overdue: float = Field(
        ge=0.0,
        description="Hours past grace period when decay was calculated",
    )
    chapter: int = Field(
        ge=1,
        le=5,
        description="User's chapter at time of decay (1-5)",
    )
    timestamp: datetime = Field(
        description="When the decay was calculated/applied",
    )
    game_over_triggered: bool = Field(
        default=False,
        description="Whether this decay caused a game over (score reached 0)",
    )
    decay_reason: str | None = Field(
        default=None,
        description="Optional reason for decay (e.g., 'inactivity')",
    )

    @model_validator(mode="after")
    def validate_score_relationship(self) -> "DecayResult":
        """Validate that score_after <= score_before (decay doesn't increase score)."""
        if self.score_after > self.score_before:
            raise ValueError(
                f"score_after ({self.score_after}) cannot exceed "
                f"score_before ({self.score_before}) - decay cannot increase score"
            )
        return self
