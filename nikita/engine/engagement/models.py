"""Pydantic models for the engagement system (spec 014).

These models represent engagement state snapshots, detection results,
and other data structures used by the engagement engine.
"""

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from nikita.config.enums import EngagementState


class EngagementSnapshot(BaseModel):
    """Current engagement state snapshot for a user.

    Represents a point-in-time view of the user's engagement state,
    including calibration score and consecutive day counters.
    """

    state: EngagementState = Field(
        default=EngagementState.CALIBRATING,
        description="Current engagement state",
    )
    calibration_score: Decimal = Field(
        default=Decimal("0.5"),
        ge=Decimal("0"),
        le=Decimal("1"),
        description="Calibration score from 0-1",
    )
    consecutive_in_zone: int = Field(
        default=0,
        ge=0,
        description="Consecutive exchanges in zone",
    )
    consecutive_clingy_days: int = Field(
        default=0,
        ge=0,
        description="Consecutive days in clingy state",
    )
    consecutive_distant_days: int = Field(
        default=0,
        ge=0,
        description="Consecutive days in distant state",
    )

    @property
    def multiplier(self) -> Decimal:
        """Get the scoring multiplier for current state."""
        return self.state.get_multiplier()

    model_config = {"arbitrary_types_allowed": True}


class ClinginessResult(BaseModel):
    """Result of clinginess detection analysis.

    Contains the composite score and individual signal breakdown.
    is_clingy is True when score exceeds 0.7 threshold.
    """

    score: Decimal = Field(
        ge=Decimal("0"),
        le=Decimal("1"),
        description="Composite clinginess score (0-1)",
    )
    is_clingy: bool = Field(
        description="True if score > 0.7 threshold",
    )
    signals: dict[str, Any] = Field(
        default_factory=dict,
        description="Individual signal breakdown",
    )

    model_config = {"arbitrary_types_allowed": True}


class NeglectResult(BaseModel):
    """Result of neglect detection analysis.

    Contains the composite score and individual signal breakdown.
    is_neglecting is True when score exceeds 0.6 threshold.
    """

    score: Decimal = Field(
        ge=Decimal("0"),
        le=Decimal("1"),
        description="Composite neglect score (0-1)",
    )
    is_neglecting: bool = Field(
        description="True if score > 0.6 threshold",
    )
    signals: dict[str, Any] = Field(
        default_factory=dict,
        description="Individual signal breakdown",
    )

    model_config = {"arbitrary_types_allowed": True}


class CalibrationResult(BaseModel):
    """Result of calibration score calculation.

    Contains the composite calibration score and component breakdown.
    """

    score: Decimal = Field(
        ge=Decimal("0"),
        le=Decimal("1"),
        description="Composite calibration score (0-1)",
    )
    frequency_component: Decimal = Field(
        ge=Decimal("0"),
        le=Decimal("1"),
        description="Frequency component (40% weight)",
    )
    timing_component: Decimal = Field(
        ge=Decimal("0"),
        le=Decimal("1"),
        description="Timing component (30% weight)",
    )
    content_component: Decimal = Field(
        ge=Decimal("0"),
        le=Decimal("1"),
        description="Content component (30% weight)",
    )
    suggested_state: EngagementState = Field(
        description="Suggested state based on score",
    )

    model_config = {"arbitrary_types_allowed": True}


class StateTransition(BaseModel):
    """Represents a state transition in the engagement state machine."""

    from_state: EngagementState
    to_state: EngagementState
    reason: str = Field(description="Reason for the transition")
    calibration_score: Decimal = Field(
        ge=Decimal("0"),
        le=Decimal("1"),
        description="Calibration score at time of transition",
    )

    model_config = {"arbitrary_types_allowed": True}
