"""Unit Tests: Emotional State Models (Spec 023, T002).

Tests EmotionalStateModel and ConflictState validation:
- 4D emotional dimensions (arousal, valence, dominance, intimacy)
- Conflict state enum and transitions
- Boundary validation (0.0-1.0 range)
- Helper methods (apply_deltas, set_conflict, to_description)

AC-T002.1: EmotionalStateModel Pydantic model with 4 dimensions
AC-T002.2: conflict_state field with validation
AC-T002.3: Validation for 0.0-1.0 range on all dimensions
AC-T002.4: Unit tests for model validation
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from nikita.emotional_state.models import (
    ConflictState,
    EmotionalStateModel,
)


class TestConflictState:
    """Tests for ConflictState enum."""

    def test_conflict_state_values(self):
        """ConflictState should have 5 distinct states."""
        assert ConflictState.NONE.value == "none"
        assert ConflictState.PASSIVE_AGGRESSIVE.value == "passive_aggressive"
        assert ConflictState.COLD.value == "cold"
        assert ConflictState.VULNERABLE.value == "vulnerable"
        assert ConflictState.EXPLOSIVE.value == "explosive"

    def test_conflict_state_count(self):
        """Should have exactly 5 conflict states."""
        assert len(ConflictState) == 5

    def test_conflict_state_from_string(self):
        """ConflictState should be creatable from string."""
        assert ConflictState("none") == ConflictState.NONE
        assert ConflictState("cold") == ConflictState.COLD
        assert ConflictState("explosive") == ConflictState.EXPLOSIVE


class TestEmotionalStateModelCreation:
    """Tests for EmotionalStateModel creation and defaults."""

    @pytest.fixture
    def user_id(self):
        """Generate test user ID."""
        return uuid4()

    def test_create_with_defaults(self, user_id):
        """Should create with default values (0.5 for all dimensions)."""
        state = EmotionalStateModel(user_id=user_id)

        assert state.user_id == user_id
        assert state.arousal == 0.5
        assert state.valence == 0.5
        assert state.dominance == 0.5
        assert state.intimacy == 0.5
        assert state.conflict_state == ConflictState.NONE
        assert state.conflict_started_at is None
        assert state.ignored_message_count == 0

    def test_create_with_custom_dimensions(self, user_id):
        """Should create with custom dimension values."""
        state = EmotionalStateModel(
            user_id=user_id,
            arousal=0.8,
            valence=0.3,
            dominance=0.9,
            intimacy=0.2,
        )

        assert state.arousal == 0.8
        assert state.valence == 0.3
        assert state.dominance == 0.9
        assert state.intimacy == 0.2

    def test_create_with_conflict_state(self, user_id):
        """Should create with conflict state and auto-set timestamp."""
        state = EmotionalStateModel(
            user_id=user_id,
            conflict_state=ConflictState.COLD,
            conflict_trigger="User ignored messages",
        )

        assert state.conflict_state == ConflictState.COLD
        assert state.conflict_started_at is not None  # Auto-set by validator
        assert state.conflict_trigger == "User ignored messages"

    def test_conflict_state_from_string(self, user_id):
        """Should accept conflict_state as string."""
        state = EmotionalStateModel(
            user_id=user_id,
            conflict_state="passive_aggressive",
        )

        assert state.conflict_state == ConflictState.PASSIVE_AGGRESSIVE

    def test_invalid_conflict_state_defaults_to_none(self, user_id):
        """Invalid conflict_state string should default to NONE."""
        state = EmotionalStateModel(
            user_id=user_id,
            conflict_state="invalid_state",
        )

        assert state.conflict_state == ConflictState.NONE

    def test_state_id_auto_generated(self, user_id):
        """state_id should be auto-generated if not provided."""
        state = EmotionalStateModel(user_id=user_id)
        assert state.state_id is not None

    def test_timestamps_auto_set(self, user_id):
        """Timestamps should be auto-set to now."""
        before = datetime.now(timezone.utc)
        state = EmotionalStateModel(user_id=user_id)
        after = datetime.now(timezone.utc)

        assert before <= state.created_at <= after
        assert before <= state.last_updated <= after


class TestEmotionalStateModelValidation:
    """AC-T002.3: Validation for 0.0-1.0 range on all dimensions."""

    @pytest.fixture
    def user_id(self):
        """Generate test user ID."""
        return uuid4()

    def test_arousal_below_zero_rejected(self, user_id):
        """Arousal below 0.0 should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            EmotionalStateModel(user_id=user_id, arousal=-0.1)
        assert "arousal" in str(exc_info.value)

    def test_arousal_above_one_rejected(self, user_id):
        """Arousal above 1.0 should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            EmotionalStateModel(user_id=user_id, arousal=1.1)
        assert "arousal" in str(exc_info.value)

    def test_valence_below_zero_rejected(self, user_id):
        """Valence below 0.0 should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            EmotionalStateModel(user_id=user_id, valence=-0.5)
        assert "valence" in str(exc_info.value)

    def test_valence_above_one_rejected(self, user_id):
        """Valence above 1.0 should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            EmotionalStateModel(user_id=user_id, valence=2.0)
        assert "valence" in str(exc_info.value)

    def test_dominance_below_zero_rejected(self, user_id):
        """Dominance below 0.0 should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            EmotionalStateModel(user_id=user_id, dominance=-1.0)
        assert "dominance" in str(exc_info.value)

    def test_dominance_above_one_rejected(self, user_id):
        """Dominance above 1.0 should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            EmotionalStateModel(user_id=user_id, dominance=1.5)
        assert "dominance" in str(exc_info.value)

    def test_intimacy_below_zero_rejected(self, user_id):
        """Intimacy below 0.0 should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            EmotionalStateModel(user_id=user_id, intimacy=-0.01)
        assert "intimacy" in str(exc_info.value)

    def test_intimacy_above_one_rejected(self, user_id):
        """Intimacy above 1.0 should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            EmotionalStateModel(user_id=user_id, intimacy=1.001)
        assert "intimacy" in str(exc_info.value)

    def test_boundary_values_accepted(self, user_id):
        """Boundary values 0.0 and 1.0 should be accepted."""
        state_min = EmotionalStateModel(
            user_id=user_id,
            arousal=0.0,
            valence=0.0,
            dominance=0.0,
            intimacy=0.0,
        )
        state_max = EmotionalStateModel(
            user_id=user_id,
            arousal=1.0,
            valence=1.0,
            dominance=1.0,
            intimacy=1.0,
        )

        assert state_min.arousal == 0.0
        assert state_max.arousal == 1.0

    def test_ignored_message_count_non_negative(self, user_id):
        """ignored_message_count should not be negative."""
        with pytest.raises(ValidationError) as exc_info:
            EmotionalStateModel(user_id=user_id, ignored_message_count=-1)
        assert "ignored_message_count" in str(exc_info.value)


class TestEmotionalStateModelConflictValidation:
    """Tests for conflict state timestamp validation."""

    @pytest.fixture
    def user_id(self):
        """Generate test user ID."""
        return uuid4()

    def test_conflict_started_at_auto_set_when_in_conflict(self, user_id):
        """conflict_started_at should be auto-set when entering conflict."""
        state = EmotionalStateModel(
            user_id=user_id,
            conflict_state=ConflictState.EXPLOSIVE,
        )

        assert state.conflict_started_at is not None
        assert isinstance(state.conflict_started_at, datetime)

    def test_conflict_started_at_cleared_when_none(self, user_id):
        """conflict_started_at should be cleared when conflict is NONE."""
        # First create a state with conflict
        state = EmotionalStateModel(
            user_id=user_id,
            conflict_state=ConflictState.COLD,
            conflict_started_at=datetime.now(timezone.utc),
            conflict_trigger="Test trigger",
        )

        # Now update to NONE (simulated by creating new state)
        cleared_state = EmotionalStateModel(
            user_id=user_id,
            conflict_state=ConflictState.NONE,
            conflict_started_at=datetime.now(timezone.utc),  # Should be cleared
            conflict_trigger="Should be cleared",
        )

        assert cleared_state.conflict_started_at is None
        assert cleared_state.conflict_trigger is None


class TestApplyDeltas:
    """Tests for apply_deltas() method."""

    @pytest.fixture
    def user_id(self):
        """Generate test user ID."""
        return uuid4()

    @pytest.fixture
    def base_state(self, user_id):
        """Create a base state at midpoint values."""
        return EmotionalStateModel(
            user_id=user_id,
            arousal=0.5,
            valence=0.5,
            dominance=0.5,
            intimacy=0.5,
        )

    def test_apply_positive_deltas(self, base_state):
        """Should apply positive deltas correctly."""
        new_state = base_state.apply_deltas(
            arousal_delta=0.2,
            valence_delta=0.1,
            dominance_delta=0.15,
            intimacy_delta=0.3,
        )

        assert new_state.arousal == 0.7
        assert new_state.valence == 0.6
        assert new_state.dominance == 0.65
        assert new_state.intimacy == 0.8

    def test_apply_negative_deltas(self, base_state):
        """Should apply negative deltas correctly."""
        new_state = base_state.apply_deltas(
            arousal_delta=-0.3,
            valence_delta=-0.4,
            dominance_delta=-0.1,
            intimacy_delta=-0.2,
        )

        assert new_state.arousal == pytest.approx(0.2)
        assert new_state.valence == pytest.approx(0.1)
        assert new_state.dominance == pytest.approx(0.4)
        assert new_state.intimacy == pytest.approx(0.3)

    def test_deltas_clamped_to_max(self, base_state):
        """Deltas should be clamped at 1.0 max."""
        new_state = base_state.apply_deltas(
            arousal_delta=0.8,  # Would be 1.3
            valence_delta=1.0,  # Would be 1.5
        )

        assert new_state.arousal == 1.0
        assert new_state.valence == 1.0

    def test_deltas_clamped_to_min(self, base_state):
        """Deltas should be clamped at 0.0 min."""
        new_state = base_state.apply_deltas(
            arousal_delta=-0.8,  # Would be -0.3
            valence_delta=-1.0,  # Would be -0.5
        )

        assert new_state.arousal == 0.0
        assert new_state.valence == 0.0

    def test_apply_deltas_preserves_conflict_state(self, user_id):
        """apply_deltas should preserve conflict state."""
        state = EmotionalStateModel(
            user_id=user_id,
            conflict_state=ConflictState.VULNERABLE,
            conflict_trigger="Past hurt",
        )

        new_state = state.apply_deltas(arousal_delta=0.1)

        assert new_state.conflict_state == ConflictState.VULNERABLE
        assert new_state.conflict_trigger == "Past hurt"

    def test_apply_deltas_preserves_ids(self, base_state):
        """apply_deltas should preserve state_id and user_id."""
        new_state = base_state.apply_deltas(valence_delta=0.1)

        assert new_state.state_id == base_state.state_id
        assert new_state.user_id == base_state.user_id

    def test_apply_deltas_updates_timestamp(self, base_state):
        """apply_deltas should update last_updated timestamp."""
        new_state = base_state.apply_deltas(valence_delta=0.1)

        assert new_state.last_updated >= base_state.last_updated


class TestSetConflict:
    """Tests for set_conflict() method."""

    @pytest.fixture
    def user_id(self):
        """Generate test user ID."""
        return uuid4()

    @pytest.fixture
    def neutral_state(self, user_id):
        """Create a neutral state with no conflict."""
        return EmotionalStateModel(user_id=user_id)

    def test_set_conflict_state(self, neutral_state):
        """Should set conflict state correctly."""
        new_state = neutral_state.set_conflict(
            ConflictState.COLD,
            trigger="User was distant",
        )

        assert new_state.conflict_state == ConflictState.COLD
        assert new_state.conflict_trigger == "User was distant"
        assert new_state.conflict_started_at is not None

    def test_set_conflict_none_clears_fields(self, user_id):
        """Setting conflict to NONE should clear related fields."""
        in_conflict = EmotionalStateModel(
            user_id=user_id,
            conflict_state=ConflictState.EXPLOSIVE,
            conflict_trigger="Big argument",
        )

        cleared = in_conflict.set_conflict(ConflictState.NONE)

        assert cleared.conflict_state == ConflictState.NONE
        assert cleared.conflict_started_at is None
        assert cleared.conflict_trigger is None

    def test_set_conflict_preserves_dimensions(self, user_id):
        """set_conflict should preserve emotional dimensions."""
        state = EmotionalStateModel(
            user_id=user_id,
            arousal=0.8,
            valence=0.2,
            dominance=0.9,
            intimacy=0.1,
        )

        new_state = state.set_conflict(ConflictState.PASSIVE_AGGRESSIVE)

        assert new_state.arousal == 0.8
        assert new_state.valence == 0.2
        assert new_state.dominance == 0.9
        assert new_state.intimacy == 0.1


class TestToDescription:
    """Tests for to_description() method."""

    @pytest.fixture
    def user_id(self):
        """Generate test user ID."""
        return uuid4()

    def test_low_arousal_description(self, user_id):
        """Low arousal should describe as tired/low-energy."""
        state = EmotionalStateModel(user_id=user_id, arousal=0.1)
        desc = state.to_description()
        assert "tired" in desc.lower() or "low-energy" in desc.lower()

    def test_high_arousal_description(self, user_id):
        """High arousal should describe as energetic."""
        state = EmotionalStateModel(user_id=user_id, arousal=0.9)
        desc = state.to_description()
        assert "energetic" in desc.lower() or "alert" in desc.lower()

    def test_low_valence_description(self, user_id):
        """Low valence should describe as negative mood."""
        state = EmotionalStateModel(user_id=user_id, valence=0.1)
        desc = state.to_description()
        assert "negative" in desc.lower()

    def test_high_valence_description(self, user_id):
        """High valence should describe as positive mood."""
        state = EmotionalStateModel(user_id=user_id, valence=0.9)
        desc = state.to_description()
        assert "positive" in desc.lower()

    def test_conflict_state_in_description(self, user_id):
        """Conflict state should be included in description."""
        state = EmotionalStateModel(
            user_id=user_id,
            conflict_state=ConflictState.COLD,
        )
        desc = state.to_description()
        assert "distant" in desc.lower()

    def test_explosive_conflict_description(self, user_id):
        """Explosive conflict should mention upset."""
        state = EmotionalStateModel(
            user_id=user_id,
            conflict_state=ConflictState.EXPLOSIVE,
        )
        desc = state.to_description()
        assert "upset" in desc.lower()


class TestDatabaseSerialization:
    """Tests for model_dump_for_db() and from_db_row()."""

    @pytest.fixture
    def user_id(self):
        """Generate test user ID."""
        return uuid4()

    def test_model_dump_for_db(self, user_id):
        """Should convert to database-compatible dict."""
        state_id = uuid4()
        now = datetime.now(timezone.utc)

        state = EmotionalStateModel(
            state_id=state_id,
            user_id=user_id,
            arousal=0.7,
            valence=0.3,
            dominance=0.8,
            intimacy=0.4,
            conflict_state=ConflictState.VULNERABLE,
            conflict_trigger="Feeling hurt",
            ignored_message_count=2,
            last_updated=now,
            created_at=now,
        )

        db_dict = state.model_dump_for_db()

        assert db_dict["state_id"] == str(state_id)
        assert db_dict["user_id"] == str(user_id)
        assert db_dict["arousal"] == 0.7
        assert db_dict["conflict_state"] == "vulnerable"
        assert db_dict["conflict_trigger"] == "Feeling hurt"
        assert isinstance(db_dict["last_updated"], str)  # ISO format

    def test_from_db_row(self, user_id):
        """Should create instance from database row."""
        state_id = uuid4()
        now = datetime.now(timezone.utc)

        row = {
            "state_id": str(state_id),
            "user_id": str(user_id),
            "arousal": 0.6,
            "valence": 0.4,
            "dominance": 0.7,
            "intimacy": 0.3,
            "conflict_state": "cold",
            "conflict_started_at": now.isoformat(),
            "conflict_trigger": "Distance",
            "ignored_message_count": 5,
            "last_updated": now.isoformat(),
            "created_at": now.isoformat(),
            "metadata": {"source": "test"},
        }

        state = EmotionalStateModel.from_db_row(row)

        assert state.state_id == state_id
        assert state.user_id == user_id
        assert state.arousal == 0.6
        assert state.conflict_state == ConflictState.COLD
        assert state.ignored_message_count == 5

    def test_roundtrip_serialization(self, user_id):
        """Should survive roundtrip through DB format."""
        original = EmotionalStateModel(
            user_id=user_id,
            arousal=0.65,
            valence=0.35,
            dominance=0.75,
            intimacy=0.45,
            conflict_state=ConflictState.PASSIVE_AGGRESSIVE,
            conflict_trigger="Subtle frustration",
            ignored_message_count=3,
            metadata={"test": "value"},
        )

        db_dict = original.model_dump_for_db()
        restored = EmotionalStateModel.from_db_row(db_dict)

        assert restored.arousal == original.arousal
        assert restored.valence == original.valence
        assert restored.dominance == original.dominance
        assert restored.intimacy == original.intimacy
        assert restored.conflict_state == original.conflict_state
        assert restored.conflict_trigger == original.conflict_trigger
        assert restored.ignored_message_count == original.ignored_message_count
