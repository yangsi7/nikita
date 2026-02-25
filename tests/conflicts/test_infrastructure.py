"""Infrastructure tests for Conflict Generation System (Spec 027, Phase A: T001-T005).

Tests for:
- T001: Module structure
- T002: Models (ConflictTrigger, ActiveConflict)
- T003: Database migration (deferred to DB layer)
- T005: Phase A coverage

Note: T004 (ConflictStore) tests removed — ConflictStore deleted in Spec 057
refactor. State is now stored in PostgreSQL via conflict_details JSONB.
"""

import pytest
from datetime import UTC, datetime, timedelta
from pydantic import ValidationError

from nikita.conflicts import (
    ActiveConflict,
    ConflictConfig,
    ConflictSummary,
    ConflictTrigger,
    ConflictType,
    EscalationLevel,
    ResolutionType,
    TriggerType,
    get_conflict_config,
    trigger_to_conflict_type,
)


class TestModuleStructure:
    """Test T001: Module structure."""

    def test_module_imports(self):
        """AC-T001.1: Module imports work."""
        from nikita import conflicts
        assert hasattr(conflicts, "ActiveConflict")
        assert hasattr(conflicts, "ConflictTrigger")
        assert hasattr(conflicts, "TriggerType")
        assert hasattr(conflicts, "ConflictType")

    def test_models_importable(self):
        """AC-T001.2: Models are importable."""
        from nikita.conflicts.models import (
            ActiveConflict,
            ConflictConfig,
            ConflictTrigger,
        )
        assert ActiveConflict is not None
        assert ConflictConfig is not None
        assert ConflictTrigger is not None


class TestTriggerType:
    """Test TriggerType enum."""

    def test_all_trigger_types_defined(self):
        """All trigger types are defined."""
        assert TriggerType.DISMISSIVE == "dismissive"
        assert TriggerType.NEGLECT == "neglect"
        assert TriggerType.JEALOUSY == "jealousy"
        assert TriggerType.BOUNDARY == "boundary"
        assert TriggerType.TRUST == "trust"

    def test_trigger_type_values(self):
        """Trigger types have correct values."""
        assert len(TriggerType) == 5


class TestConflictType:
    """Test ConflictType enum."""

    def test_all_conflict_types_defined(self):
        """All conflict types are defined."""
        assert ConflictType.JEALOUSY == "jealousy"
        assert ConflictType.ATTENTION == "attention"
        assert ConflictType.BOUNDARY == "boundary"
        assert ConflictType.TRUST == "trust"

    def test_conflict_type_values(self):
        """Conflict types have correct values."""
        assert len(ConflictType) == 4


class TestEscalationLevel:
    """Test EscalationLevel enum."""

    def test_all_levels_defined(self):
        """All escalation levels are defined."""
        assert EscalationLevel.SUBTLE == 1
        assert EscalationLevel.DIRECT == 2
        assert EscalationLevel.CRISIS == 3

    def test_level_order(self):
        """Levels are in correct order."""
        assert EscalationLevel.SUBTLE < EscalationLevel.DIRECT
        assert EscalationLevel.DIRECT < EscalationLevel.CRISIS


class TestResolutionType:
    """Test ResolutionType enum."""

    def test_all_resolution_types_defined(self):
        """All resolution types are defined."""
        assert ResolutionType.FULL == "full"
        assert ResolutionType.PARTIAL == "partial"
        assert ResolutionType.FAILED == "failed"
        assert ResolutionType.NATURAL == "natural"


class TestConflictTrigger:
    """Test T002: ConflictTrigger model."""

    def test_create_trigger(self):
        """AC-T002.1: ConflictTrigger model works."""
        trigger = ConflictTrigger(
            trigger_id="t1",
            trigger_type=TriggerType.JEALOUSY,
            severity=0.5,
        )

        assert trigger.trigger_id == "t1"
        assert trigger.trigger_type == TriggerType.JEALOUSY
        assert trigger.severity == 0.5

    def test_trigger_defaults(self):
        """Trigger has sensible defaults."""
        trigger = ConflictTrigger(
            trigger_id="t2",
            trigger_type=TriggerType.NEGLECT,
            severity=0.3,
        )

        assert trigger.context == {}
        assert trigger.user_messages == []
        assert trigger.detected_at is not None

    def test_trigger_with_context(self):
        """Trigger accepts context."""
        trigger = ConflictTrigger(
            trigger_id="t3",
            trigger_type=TriggerType.DISMISSIVE,
            severity=0.4,
            context={"message_length": 5},
            user_messages=["k"],
        )

        assert trigger.context["message_length"] == 5
        assert "k" in trigger.user_messages

    def test_severity_validation(self):
        """AC-T002.3: Severity is validated."""
        # Should clamp to valid range
        trigger = ConflictTrigger(
            trigger_id="t4",
            trigger_type=TriggerType.TRUST,
            severity=1.5,  # Over max
        )
        assert trigger.severity == 1.0

        trigger2 = ConflictTrigger(
            trigger_id="t5",
            trigger_type=TriggerType.TRUST,
            severity=-0.5,  # Under min
        )
        assert trigger2.severity == 0.0


class TestActiveConflict:
    """Test T002: ActiveConflict model."""

    def test_create_conflict(self):
        """AC-T002.2: ActiveConflict model works."""
        conflict = ActiveConflict(
            conflict_id="c1",
            user_id="u1",
            conflict_type=ConflictType.JEALOUSY,
            severity=0.6,
        )

        assert conflict.conflict_id == "c1"
        assert conflict.user_id == "u1"
        assert conflict.conflict_type == ConflictType.JEALOUSY
        assert conflict.severity == 0.6

    def test_conflict_defaults(self):
        """Conflict has sensible defaults."""
        conflict = ActiveConflict(
            conflict_id="c2",
            user_id="u1",
            conflict_type=ConflictType.ATTENTION,
            severity=0.4,
        )

        assert conflict.escalation_level == EscalationLevel.SUBTLE
        assert conflict.resolution_attempts == 0
        assert conflict.resolved is False
        assert conflict.resolution_type is None
        assert conflict.last_escalated is None
        assert conflict.trigger_ids == []

    def test_conflict_with_all_fields(self):
        """Conflict accepts all fields."""
        now = datetime.now(UTC)
        conflict = ActiveConflict(
            conflict_id="c3",
            user_id="u1",
            conflict_type=ConflictType.BOUNDARY,
            severity=0.8,
            escalation_level=EscalationLevel.DIRECT,
            triggered_at=now,
            last_escalated=now,
            resolution_attempts=2,
            resolved=True,
            resolution_type=ResolutionType.FULL,
            trigger_ids=["t1", "t2"],
        )

        assert conflict.escalation_level == EscalationLevel.DIRECT
        assert conflict.resolution_attempts == 2
        assert conflict.resolved is True
        assert conflict.resolution_type == ResolutionType.FULL
        assert len(conflict.trigger_ids) == 2


class TestConflictConfig:
    """Test ConflictConfig model."""

    def test_default_config(self):
        """Default config has correct values."""
        config = get_conflict_config()

        assert config.warning_threshold == 20
        assert config.breakup_threshold == 10
        assert config.consecutive_crises_for_breakup == 3

    def test_escalation_times(self):
        """Escalation times are correct."""
        config = get_conflict_config()

        assert config.escalation_time_subtle_to_direct_hours == (2, 6)
        assert config.escalation_time_direct_to_crisis_hours == (12, 24)

    def test_natural_resolution_probabilities(self):
        """Natural resolution probabilities are correct."""
        config = get_conflict_config()

        assert config.natural_resolution_probability_level_1 == 0.30
        assert config.natural_resolution_probability_level_2 == 0.10
        assert config.natural_resolution_probability_level_3 == 0.0

    def test_severity_ranges(self):
        """Severity ranges are defined."""
        config = get_conflict_config()

        assert "jealousy" in config.severity_ranges
        assert "attention" in config.severity_ranges
        assert "boundary" in config.severity_ranges
        assert "trust" in config.severity_ranges


class TestConflictSummary:
    """Test ConflictSummary model."""

    def test_summary_defaults(self):
        """Summary has correct defaults."""
        summary = ConflictSummary(user_id="u1")

        assert summary.total_conflicts == 0
        assert summary.resolved_conflicts == 0
        assert summary.unresolved_crises == 0
        assert summary.current_conflict is None

    def test_resolution_rate(self):
        """Resolution rate calculated correctly."""
        summary = ConflictSummary(
            user_id="u1",
            total_conflicts=10,
            resolved_conflicts=7,
        )

        assert summary.resolution_rate == 0.7

    def test_resolution_rate_zero_conflicts(self):
        """Resolution rate is 1.0 with no conflicts."""
        summary = ConflictSummary(user_id="u1")
        assert summary.resolution_rate == 1.0


class TestTriggerToConflictMapping:
    """Test trigger to conflict type mapping."""

    def test_dismissive_maps_to_attention(self):
        """Dismissive triggers map to attention conflicts."""
        assert trigger_to_conflict_type(TriggerType.DISMISSIVE) == ConflictType.ATTENTION

    def test_neglect_maps_to_attention(self):
        """Neglect triggers map to attention conflicts."""
        assert trigger_to_conflict_type(TriggerType.NEGLECT) == ConflictType.ATTENTION

    def test_jealousy_maps_to_jealousy(self):
        """Jealousy triggers map to jealousy conflicts."""
        assert trigger_to_conflict_type(TriggerType.JEALOUSY) == ConflictType.JEALOUSY

    def test_boundary_maps_to_boundary(self):
        """Boundary triggers map to boundary conflicts."""
        assert trigger_to_conflict_type(TriggerType.BOUNDARY) == ConflictType.BOUNDARY

    def test_trust_maps_to_trust(self):
        """Trust triggers map to trust conflicts."""
        assert trigger_to_conflict_type(TriggerType.TRUST) == ConflictType.TRUST
