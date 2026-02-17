"""Conflict system models for Spec 027 + Spec 057 (Temperature).

Defines data structures for conflict triggers, active conflicts,
escalation levels, resolution types, and temperature gauge.
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


# ============================================================================
# Spec 057: Temperature Gauge Models
# ============================================================================


class TemperatureZone(str, Enum):
    """Temperature zones for conflict severity (Spec 057).

    Zones determine injection probability and max severity.
    """

    CALM = "calm"          # 0-25: No conflicts generated
    WARM = "warm"          # 25-50: Low probability, capped severity
    HOT = "hot"            # 50-75: Medium probability
    CRITICAL = "critical"  # 75-100: High probability, full severity


class HorsemanType(str, Enum):
    """Gottman's Four Horsemen of the Apocalypse (Spec 057).

    Toxic communication patterns that predict relationship failure.
    """

    CRITICISM = "criticism"          # Attacking character, not behavior
    CONTEMPT = "contempt"            # Superiority, mockery, disgust
    DEFENSIVENESS = "defensiveness"  # Counter-attacking, playing victim
    STONEWALLING = "stonewalling"    # Withdrawal, disengagement


class RepairRecord(BaseModel):
    """Record of a repair attempt (Spec 057).

    Attributes:
        at: When the repair was attempted.
        quality: Resolution quality (excellent, good, adequate, poor, harmful).
        temp_delta: Temperature change from this repair.
    """

    at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    quality: str = Field(description="Resolution quality")
    temp_delta: float = Field(description="Temperature change from repair")


class GottmanCounters(BaseModel):
    """Gottman ratio counters (Spec 057).

    Tracks positive/negative interactions for ratio calculation.
    Two-ratio system: 5:1 during conflict, 20:1 during normal.

    Attributes:
        positive_count: Total positive interactions in rolling window.
        negative_count: Total negative interactions in rolling window.
        session_positive: Positive interactions in current session.
        session_negative: Negative interactions in current session.
        window_start: Start of rolling 7-day window.
    """

    positive_count: int = Field(default=0, ge=0)
    negative_count: int = Field(default=0, ge=0)
    session_positive: int = Field(default=0, ge=0)
    session_negative: int = Field(default=0, ge=0)
    window_start: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def ratio(self) -> float:
        """Calculate positive/negative ratio. Returns infinity if no negatives."""
        if self.negative_count == 0:
            return float("inf") if self.positive_count > 0 else 0.0
        return self.positive_count / self.negative_count


class ConflictTemperature(BaseModel):
    """Continuous temperature gauge for conflict severity (Spec 057).

    Replaces discrete ConflictState enum with a 0-100 continuous value.
    Temperature drives injection probability, max severity, and persona tone.

    Attributes:
        value: Temperature value (0.0-100.0).
        zone: Current temperature zone.
        last_update: When temperature was last updated.
    """

    value: float = Field(default=0.0, ge=0.0, le=100.0)
    zone: TemperatureZone = Field(default=TemperatureZone.CALM)
    last_update: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("value", mode="before")
    @classmethod
    def clamp_value(cls, v: float) -> float:
        """Clamp temperature to 0-100 range."""
        return max(0.0, min(100.0, float(v)))

    def model_post_init(self, __context: Any) -> None:
        """Auto-compute zone from value after init."""
        self.zone = self._compute_zone(self.value)

    @staticmethod
    def _compute_zone(value: float) -> TemperatureZone:
        """Compute zone from temperature value."""
        if value < 25.0:
            return TemperatureZone.CALM
        elif value < 50.0:
            return TemperatureZone.WARM
        elif value < 75.0:
            return TemperatureZone.HOT
        else:
            return TemperatureZone.CRITICAL


class ConflictDetails(BaseModel):
    """Full conflict details stored as JSONB (Spec 057).

    Stored in nikita_emotional_states.conflict_details column.

    Attributes:
        temperature: Current temperature value (0-100).
        zone: Current temperature zone.
        positive_count: Gottman positive counter.
        negative_count: Gottman negative counter.
        gottman_ratio: Current Gottman ratio.
        gottman_target: Current target ratio (5.0 or 20.0).
        horsemen_detected: List of horsemen detected in current session.
        repair_attempts: History of repair attempts.
        last_temp_update: When temperature was last updated.
        session_positive: Session-scoped positive counter.
        session_negative: Session-scoped negative counter.
    """

    temperature: float = Field(default=0.0, ge=0.0, le=100.0)
    zone: str = Field(default="calm")
    positive_count: int = Field(default=0, ge=0)
    negative_count: int = Field(default=0, ge=0)
    gottman_ratio: float = Field(default=0.0, ge=0.0)
    gottman_target: float = Field(default=20.0)
    horsemen_detected: list[str] = Field(default_factory=list)
    repair_attempts: list[dict[str, Any]] = Field(default_factory=list)
    last_temp_update: str | None = Field(default=None)
    session_positive: int = Field(default=0, ge=0)
    session_negative: int = Field(default=0, ge=0)

    @classmethod
    def from_jsonb(cls, data: dict[str, Any] | None) -> "ConflictDetails":
        """Create from JSONB data with safe defaults."""
        if not data:
            return cls()
        return cls(**{k: v for k, v in data.items() if k in cls.model_fields})

    def to_jsonb(self) -> dict[str, Any]:
        """Convert to JSONB-compatible dict."""
        return self.model_dump(mode="json")
