"""Conflict system models for Spec 027.

Defines data structures for conflict triggers, active conflicts,
escalation levels, and resolution types.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class TriggerType(str, Enum):
    """Types of conflict triggers."""

    DISMISSIVE = "dismissive"  # Short responses, topic changes
    NEGLECT = "neglect"  # Long gaps without explanation
    JEALOUSY = "jealousy"  # Mentions of other people
    BOUNDARY = "boundary"  # Pushy behavior, going too fast
    TRUST = "trust"  # Inconsistencies, lies


class ConflictType(str, Enum):
    """Types of conflicts that can arise."""

    JEALOUSY = "jealousy"  # Mentions of others positively
    ATTENTION = "attention"  # Feeling ignored
    BOUNDARY = "boundary"  # Pushing too fast
    TRUST = "trust"  # Catching inconsistencies


class EscalationLevel(int, Enum):
    """Escalation levels for conflicts."""

    SUBTLE = 1  # Subtle hints, can prevent escalation
    DIRECT = 2  # Direct confrontation, requires acknowledgment
    CRISIS = 3  # Crisis level, requires significant action


class ResolutionType(str, Enum):
    """Types of conflict resolution."""

    FULL = "full"  # Conflict fully resolved
    PARTIAL = "partial"  # Severity reduced but not resolved
    FAILED = "failed"  # Resolution attempt failed
    NATURAL = "natural"  # Resolved naturally without intervention


class ConflictTrigger(BaseModel):
    """A detected trigger that may lead to a conflict.

    Attributes:
        trigger_id: Unique identifier for this trigger.
        trigger_type: Type of trigger detected.
        severity: Severity score (0.0-1.0).
        detected_at: When the trigger was detected.
        context: Additional context about the trigger.
        user_messages: Messages that contributed to detection.
    """

    trigger_id: str = Field(description="Unique trigger identifier")
    trigger_type: TriggerType = Field(description="Type of trigger")
    severity: float = Field(description="Severity score (0.0-1.0), clamped to range")
    detected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    context: dict[str, Any] = Field(default_factory=dict)
    user_messages: list[str] = Field(default_factory=list)

    @field_validator("severity", mode="before")
    @classmethod
    def validate_severity(cls, v: float) -> float:
        """Clamp severity to valid range 0.0-1.0."""
        return max(0.0, min(1.0, v))


class ActiveConflict(BaseModel):
    """An active conflict in the relationship.

    Attributes:
        conflict_id: Unique identifier for this conflict.
        user_id: User involved in the conflict.
        conflict_type: Type of conflict.
        severity: Current severity level.
        escalation_level: Current escalation level (1-3).
        triggered_at: When the conflict started.
        last_escalated: When the conflict last escalated.
        resolution_attempts: Number of resolution attempts.
        resolved: Whether the conflict is resolved.
        resolution_type: How the conflict was resolved (if resolved).
        trigger_ids: IDs of triggers that contributed to this conflict.
    """

    conflict_id: str = Field(description="Unique conflict identifier")
    user_id: str = Field(description="User ID")
    conflict_type: ConflictType = Field(description="Type of conflict")
    severity: float = Field(description="Current severity (0.0-1.0), clamped to range")
    escalation_level: EscalationLevel = Field(
        default=EscalationLevel.SUBTLE,
        description="Current escalation level"
    )
    triggered_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_escalated: datetime | None = Field(default=None)
    resolution_attempts: int = Field(default=0, ge=0)
    resolved: bool = Field(default=False)
    resolution_type: ResolutionType | None = Field(default=None)
    trigger_ids: list[str] = Field(default_factory=list)

    @field_validator("severity", mode="before")
    @classmethod
    def validate_severity(cls, v: float) -> float:
        """Clamp severity to valid range 0.0-1.0."""
        return max(0.0, min(1.0, v))


class ConflictConfig(BaseModel):
    """Configuration for the conflict system.

    Attributes:
        escalation_time_subtle_to_direct_hours: Hours before level 1→2.
        escalation_time_direct_to_crisis_hours: Hours before level 2→3.
        natural_resolution_probability_level_1: Probability of natural resolution at level 1.
        natural_resolution_probability_level_2: Probability at level 2.
        natural_resolution_probability_level_3: Probability at level 3.
        warning_threshold: Relationship score triggering warning.
        breakup_threshold: Relationship score triggering breakup.
        consecutive_crises_for_breakup: Number of unresolved crises for breakup.
    """

    # Escalation timing
    escalation_time_subtle_to_direct_hours: tuple[int, int] = Field(
        default=(2, 6),
        description="Hours range for level 1→2 escalation"
    )
    escalation_time_direct_to_crisis_hours: tuple[int, int] = Field(
        default=(12, 24),
        description="Hours range for level 2→3 escalation"
    )

    # Natural resolution probabilities
    natural_resolution_probability_level_1: float = Field(
        default=0.30,
        ge=0.0,
        le=1.0,
        description="30% chance at level 1"
    )
    natural_resolution_probability_level_2: float = Field(
        default=0.10,
        ge=0.0,
        le=1.0,
        description="10% chance at level 2"
    )
    natural_resolution_probability_level_3: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="0% chance at level 3"
    )

    # Breakup thresholds
    warning_threshold: int = Field(
        default=20,
        ge=0,
        le=100,
        description="Score triggering warning"
    )
    breakup_threshold: int = Field(
        default=10,
        ge=0,
        le=100,
        description="Score triggering breakup"
    )
    consecutive_crises_for_breakup: int = Field(
        default=3,
        ge=1,
        description="Number of unresolved crises"
    )

    # Severity ranges per conflict type
    severity_ranges: dict[str, tuple[float, float]] = Field(
        default={
            "jealousy": (0.3, 0.8),
            "attention": (0.2, 0.6),
            "boundary": (0.4, 0.9),
            "trust": (0.5, 1.0),
        }
    )


class ConflictSummary(BaseModel):
    """Summary of a user's conflict history.

    Attributes:
        user_id: User ID.
        total_conflicts: Total number of conflicts.
        resolved_conflicts: Number of resolved conflicts.
        unresolved_crises: Number of unresolved crisis-level conflicts.
        current_conflict: Currently active conflict (if any).
        last_conflict_at: When the last conflict occurred.
    """

    user_id: str
    total_conflicts: int = 0
    resolved_conflicts: int = 0
    unresolved_crises: int = 0
    current_conflict: ActiveConflict | None = None
    last_conflict_at: datetime | None = None

    @property
    def resolution_rate(self) -> float:
        """Calculate resolution rate."""
        if self.total_conflicts == 0:
            return 1.0
        return self.resolved_conflicts / self.total_conflicts


# Default configuration
DEFAULT_CONFLICT_CONFIG = ConflictConfig()


def get_conflict_config() -> ConflictConfig:
    """Get the default conflict configuration.

    Returns:
        ConflictConfig instance.
    """
    return DEFAULT_CONFLICT_CONFIG


# Trigger type to conflict type mapping
TRIGGER_TO_CONFLICT_MAP: dict[TriggerType, ConflictType] = {
    TriggerType.DISMISSIVE: ConflictType.ATTENTION,
    TriggerType.NEGLECT: ConflictType.ATTENTION,
    TriggerType.JEALOUSY: ConflictType.JEALOUSY,
    TriggerType.BOUNDARY: ConflictType.BOUNDARY,
    TriggerType.TRUST: ConflictType.TRUST,
}


def trigger_to_conflict_type(trigger_type: TriggerType) -> ConflictType:
    """Map a trigger type to its corresponding conflict type.

    Args:
        trigger_type: The trigger type.

    Returns:
        Corresponding conflict type.
    """
    return TRIGGER_TO_CONFLICT_MAP.get(trigger_type, ConflictType.ATTENTION)
