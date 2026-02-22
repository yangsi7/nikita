"""Emotional State Models (Spec 023, T002).

Defines the EmotionalStateModel with 4D emotional dimensions plus
conflict state tracking for Nikita's emotional system.

AC-T002.1: EmotionalStateModel Pydantic model with 4 dimensions
AC-T002.2: conflict_state field with validation
AC-T002.3: Validation for 0.0-1.0 range on all dimensions
AC-T002.4: Unit tests for model validation
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class ConflictState(str, Enum):
    """Nikita's conflict state types.

    .. deprecated:: Spec 057
        This discrete enum is deprecated in favor of the continuous temperature
        gauge (0-100) in conflict_details JSONB. Use conflict_details.temperature
        when the conflict_temperature feature flag is ON.
        See: nikita/conflicts/models.py — ConflictTemperature, TemperatureZone

    These represent escalated emotional states that require
    specific handling and recovery paths.
    """

    NONE = "none"
    PASSIVE_AGGRESSIVE = "passive_aggressive"
    COLD = "cold"
    VULNERABLE = "vulnerable"
    EXPLOSIVE = "explosive"

    @staticmethod
    def temperature_from_enum(state: "ConflictState") -> float:
        """Map discrete enum state to temperature value (Spec 057 migration).

        Mapping:
            NONE -> 0, PASSIVE_AGGRESSIVE -> 40, COLD -> 50,
            VULNERABLE -> 30, EXPLOSIVE -> 85

        Args:
            state: Discrete conflict state.

        Returns:
            Equivalent temperature value (0.0-100.0).
        """
        mapping = {
            ConflictState.NONE: 0.0,
            ConflictState.PASSIVE_AGGRESSIVE: 40.0,
            ConflictState.COLD: 50.0,
            ConflictState.VULNERABLE: 30.0,
            ConflictState.EXPLOSIVE: 85.0,
        }
        return mapping.get(state, 0.0)


class EmotionalStateModel(BaseModel):
    """Extended 4-dimensional emotional state with conflict tracking.

    Extends the PAD (Pleasure-Arousal-Dominance) model with intimacy
    dimension and conflict state for relationship context.

    Attributes:
        state_id: Unique identifier for this state record.
        user_id: User this state is associated with.
        arousal: Energy level (0.0 = calm, 1.0 = excited).
        valence: Mood (0.0 = negative, 1.0 = positive).
        dominance: Control/assertiveness (0.0 = submissive, 1.0 = dominant).
        intimacy: Emotional openness (0.0 = guarded, 1.0 = vulnerable).
        conflict_state: Current conflict state if any.
        conflict_started_at: When current conflict began.
        last_updated: When state was last computed.
        metadata: Additional state information.
    """

    state_id: UUID = Field(default_factory=uuid4)
    user_id: UUID

    # 4D emotional dimensions (0.0-1.0)
    arousal: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Energy level: 0.0 (tired/calm) to 1.0 (energetic/excited)",
    )
    valence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Mood: 0.0 (sad/negative) to 1.0 (happy/positive)",
    )
    dominance: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Control: 0.0 (submissive) to 1.0 (dominant/assertive)",
    )
    intimacy: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Openness: 0.0 (guarded) to 1.0 (vulnerable/open)",
    )

    # Conflict tracking
    conflict_state: ConflictState = Field(
        default=ConflictState.NONE,
        description="Current conflict state",
    )
    conflict_started_at: datetime | None = Field(
        default=None,
        description="When current conflict began",
    )
    conflict_trigger: str | None = Field(
        default=None,
        description="What triggered the conflict",
    )
    ignored_message_count: int = Field(
        default=0,
        ge=0,
        description="Count of ignored messages (for passive-aggressive detection)",
    )

    # Timestamps
    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last state computation timestamp",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="State record creation timestamp",
    )

    # Metadata
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional state information",
    )

    @field_validator("conflict_state", mode="before")
    @classmethod
    def validate_conflict_state(cls, v: str | ConflictState) -> ConflictState:
        """Validate and convert conflict_state to enum."""
        if isinstance(v, ConflictState):
            return v
        if isinstance(v, str):
            try:
                return ConflictState(v)
            except ValueError:
                return ConflictState.NONE
        return ConflictState.NONE

    @model_validator(mode="after")
    def validate_conflict_timestamps(self) -> "EmotionalStateModel":
        """Ensure conflict_started_at is set when in conflict."""
        if self.conflict_state != ConflictState.NONE and self.conflict_started_at is None:
            self.conflict_started_at = datetime.now(timezone.utc)
        if self.conflict_state == ConflictState.NONE:
            self.conflict_started_at = None
            self.conflict_trigger = None
        return self

    def to_description(self) -> str:
        """Generate natural language description of emotional state."""
        descriptions = []

        # Arousal description
        if self.arousal < 0.3:
            descriptions.append("feeling tired and low-energy")
        elif self.arousal > 0.7:
            descriptions.append("feeling energetic and alert")
        else:
            descriptions.append("at a moderate energy level")

        # Valence description
        if self.valence < 0.3:
            descriptions.append("in a somewhat negative mood")
        elif self.valence > 0.7:
            descriptions.append("in a positive mood")
        else:
            descriptions.append("emotionally neutral")

        # Dominance description
        if self.dominance < 0.3:
            descriptions.append("feeling a bit passive")
        elif self.dominance > 0.7:
            descriptions.append("feeling assertive and in control")

        # Intimacy description
        if self.intimacy < 0.3:
            descriptions.append("being somewhat guarded")
        elif self.intimacy > 0.7:
            descriptions.append("feeling open and vulnerable")

        # Conflict state
        if self.conflict_state != ConflictState.NONE:
            conflict_desc = {
                ConflictState.PASSIVE_AGGRESSIVE: "subtly upset",
                ConflictState.COLD: "emotionally distant",
                ConflictState.VULNERABLE: "hurt and sensitive",
                ConflictState.EXPLOSIVE: "very upset",
            }
            descriptions.append(conflict_desc.get(self.conflict_state, ""))

        return ", ".join(filter(None, descriptions))

    def apply_deltas(
        self,
        arousal_delta: float = 0.0,
        valence_delta: float = 0.0,
        dominance_delta: float = 0.0,
        intimacy_delta: float = 0.0,
    ) -> "EmotionalStateModel":
        """Apply deltas to dimensions and return new state.

        Clamps all values to 0.0-1.0 range.

        Args:
            arousal_delta: Change in arousal.
            valence_delta: Change in valence.
            dominance_delta: Change in dominance.
            intimacy_delta: Change in intimacy.

        Returns:
            New EmotionalStateModel with applied deltas.
        """
        return EmotionalStateModel(
            state_id=self.state_id,
            user_id=self.user_id,
            arousal=max(0.0, min(1.0, self.arousal + arousal_delta)),
            valence=max(0.0, min(1.0, self.valence + valence_delta)),
            dominance=max(0.0, min(1.0, self.dominance + dominance_delta)),
            intimacy=max(0.0, min(1.0, self.intimacy + intimacy_delta)),
            conflict_state=self.conflict_state,
            conflict_started_at=self.conflict_started_at,
            conflict_trigger=self.conflict_trigger,
            ignored_message_count=self.ignored_message_count,
            last_updated=datetime.now(timezone.utc),
            created_at=self.created_at,
            metadata=self.metadata,
        )

    def set_conflict(
        self,
        conflict_state: ConflictState,
        trigger: str | None = None,
    ) -> "EmotionalStateModel":
        """Set conflict state and return new state.

        Args:
            conflict_state: New conflict state.
            trigger: What triggered the conflict.

        Returns:
            New EmotionalStateModel with conflict set.
        """
        started_at = (
            datetime.now(timezone.utc)
            if conflict_state != ConflictState.NONE
            else None
        )
        return EmotionalStateModel(
            state_id=self.state_id,
            user_id=self.user_id,
            arousal=self.arousal,
            valence=self.valence,
            dominance=self.dominance,
            intimacy=self.intimacy,
            conflict_state=conflict_state,
            conflict_started_at=started_at,
            conflict_trigger=trigger if conflict_state != ConflictState.NONE else None,
            ignored_message_count=self.ignored_message_count,
            last_updated=datetime.now(timezone.utc),
            created_at=self.created_at,
            metadata=self.metadata,
        )

    def model_dump_for_db(self) -> dict[str, Any]:
        """Convert to database-compatible dictionary."""
        return {
            "state_id": str(self.state_id),
            "user_id": str(self.user_id),
            "arousal": self.arousal,
            "valence": self.valence,
            "dominance": self.dominance,
            "intimacy": self.intimacy,
            "conflict_state": self.conflict_state.value,
            "conflict_started_at": (
                self.conflict_started_at.isoformat()
                if self.conflict_started_at
                else None
            ),
            "conflict_trigger": self.conflict_trigger,
            "ignored_message_count": self.ignored_message_count,
            "last_updated": self.last_updated.isoformat(),
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_db_row(cls, row: dict[str, Any]) -> "EmotionalStateModel":
        """Create instance from database row."""
        return cls(
            state_id=UUID(row["state_id"]) if isinstance(row["state_id"], str) else row["state_id"],
            user_id=UUID(row["user_id"]) if isinstance(row["user_id"], str) else row["user_id"],
            arousal=row.get("arousal", 0.5),
            valence=row.get("valence", 0.5),
            dominance=row.get("dominance", 0.5),
            intimacy=row.get("intimacy", 0.5),
            conflict_state=row.get("conflict_state", ConflictState.NONE),
            conflict_started_at=(
                datetime.fromisoformat(row["conflict_started_at"])
                if row.get("conflict_started_at")
                else None
            ),
            conflict_trigger=row.get("conflict_trigger"),
            ignored_message_count=row.get("ignored_message_count", 0),
            last_updated=(
                datetime.fromisoformat(row["last_updated"])
                if row.get("last_updated")
                else datetime.now(timezone.utc)
            ),
            created_at=(
                datetime.fromisoformat(row["created_at"])
                if row.get("created_at")
                else datetime.now(timezone.utc)
            ),
            metadata=row.get("metadata", {}),
        )
