"""Infrastructure tests for Conflict Generation System (Spec 027, Phase A: T001-T005).

Tests for:
- T001: Module structure
- T002: Models (ConflictTrigger, ActiveConflict)
- T003: Database migration (deferred to DB layer)
- T004: ConflictStore
- T005: Phase A coverage
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
from nikita.conflicts.store import ConflictStore, get_conflict_store


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

    def test_store_importable(self):
        """Store is importable."""
        from nikita.conflicts.store import ConflictStore
        assert ConflictStore is not None


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


class TestConflictStore:
    """Test T004: ConflictStore class."""

    @pytest.fixture
    def store(self):
        """Create fresh store for each test."""
        return ConflictStore()

    def test_create_trigger(self, store):
        """AC-T004.1: Create trigger works."""
        trigger = store.create_trigger(
            user_id="u1",
            trigger_type=TriggerType.JEALOUSY,
            severity=0.5,
        )

        assert trigger.trigger_id is not None
        assert trigger.trigger_type == TriggerType.JEALOUSY
        assert trigger.severity == 0.5

    def test_get_trigger(self, store):
        """Get trigger works."""
        trigger = store.create_trigger(
            user_id="u1",
            trigger_type=TriggerType.NEGLECT,
            severity=0.3,
        )

        retrieved = store.get_trigger(trigger.trigger_id)
        assert retrieved == trigger

    def test_get_trigger_not_found(self, store):
        """Get trigger returns None for missing."""
        assert store.get_trigger("nonexistent") is None

    def test_get_user_triggers(self, store):
        """Get user triggers works."""
        store.create_trigger("u1", TriggerType.JEALOUSY, 0.5)
        store.create_trigger("u1", TriggerType.NEGLECT, 0.3)
        store.create_trigger("u2", TriggerType.TRUST, 0.7)

        triggers = store.get_user_triggers("u1")
        assert len(triggers) == 2

    def test_get_user_triggers_since(self, store):
        """Get user triggers filters by time."""
        # Create old trigger
        trigger1 = store.create_trigger("u1", TriggerType.JEALOUSY, 0.5)

        # Create new trigger
        trigger2 = store.create_trigger("u1", TriggerType.NEGLECT, 0.3)

        # Get only recent
        since = datetime.now(UTC) - timedelta(seconds=1)
        triggers = store.get_user_triggers("u1", since=since)
        assert len(triggers) == 2  # Both should be recent

    def test_delete_trigger(self, store):
        """Delete trigger works."""
        trigger = store.create_trigger("u1", TriggerType.JEALOUSY, 0.5)
        assert store.delete_trigger(trigger.trigger_id) is True
        assert store.get_trigger(trigger.trigger_id) is None

    def test_delete_trigger_not_found(self, store):
        """Delete returns False for missing."""
        assert store.delete_trigger("nonexistent") is False

    def test_create_conflict(self, store):
        """AC-T004.3: Create conflict works."""
        conflict = store.create_conflict(
            user_id="u1",
            conflict_type=ConflictType.JEALOUSY,
            severity=0.6,
        )

        assert conflict.conflict_id is not None
        assert conflict.user_id == "u1"
        assert conflict.conflict_type == ConflictType.JEALOUSY

    def test_get_conflict(self, store):
        """Get conflict works."""
        conflict = store.create_conflict(
            user_id="u1",
            conflict_type=ConflictType.ATTENTION,
            severity=0.4,
        )

        retrieved = store.get_conflict(conflict.conflict_id)
        assert retrieved == conflict

    def test_get_conflict_not_found(self, store):
        """Get conflict returns None for missing."""
        assert store.get_conflict("nonexistent") is None

    def test_get_active_conflict(self, store):
        """AC-T004.2: Get active conflict works."""
        # Create resolved conflict
        resolved = store.create_conflict("u1", ConflictType.JEALOUSY, 0.5)
        store.resolve_conflict(resolved.conflict_id, ResolutionType.FULL)

        # Create active conflict
        active = store.create_conflict("u1", ConflictType.ATTENTION, 0.4)

        # Should return active one
        result = store.get_active_conflict("u1")
        assert result.conflict_id == active.conflict_id

    def test_get_active_conflict_none(self, store):
        """Get active conflict returns None when all resolved."""
        conflict = store.create_conflict("u1", ConflictType.JEALOUSY, 0.5)
        store.resolve_conflict(conflict.conflict_id, ResolutionType.FULL)

        assert store.get_active_conflict("u1") is None

    def test_get_user_conflicts(self, store):
        """Get user conflicts works."""
        store.create_conflict("u1", ConflictType.JEALOUSY, 0.5)
        store.create_conflict("u1", ConflictType.ATTENTION, 0.4)
        store.create_conflict("u2", ConflictType.TRUST, 0.7)

        conflicts = store.get_user_conflicts("u1")
        assert len(conflicts) == 2

    def test_get_user_conflicts_filtered(self, store):
        """Get user conflicts filters by resolved."""
        conflict1 = store.create_conflict("u1", ConflictType.JEALOUSY, 0.5)
        store.resolve_conflict(conflict1.conflict_id, ResolutionType.FULL)
        store.create_conflict("u1", ConflictType.ATTENTION, 0.4)

        resolved = store.get_user_conflicts("u1", resolved=True)
        unresolved = store.get_user_conflicts("u1", resolved=False)

        assert len(resolved) == 1
        assert len(unresolved) == 1

    def test_update_conflict(self, store):
        """Update conflict works."""
        conflict = store.create_conflict("u1", ConflictType.JEALOUSY, 0.5)
        updated = store.update_conflict(conflict.conflict_id, severity=0.8)

        assert updated.severity == 0.8

    def test_escalate_conflict(self, store):
        """Escalate conflict works."""
        conflict = store.create_conflict("u1", ConflictType.JEALOUSY, 0.5)
        escalated = store.escalate_conflict(
            conflict.conflict_id,
            EscalationLevel.DIRECT,
        )

        assert escalated.escalation_level == EscalationLevel.DIRECT
        assert escalated.last_escalated is not None

    def test_resolve_conflict(self, store):
        """AC-T004.4: Resolve conflict works."""
        conflict = store.create_conflict("u1", ConflictType.JEALOUSY, 0.5)
        resolved = store.resolve_conflict(
            conflict.conflict_id,
            ResolutionType.FULL,
        )

        assert resolved.resolved is True
        assert resolved.resolution_type == ResolutionType.FULL

    def test_increment_resolution_attempts(self, store):
        """Increment resolution attempts works."""
        conflict = store.create_conflict("u1", ConflictType.JEALOUSY, 0.5)
        assert conflict.resolution_attempts == 0

        updated = store.increment_resolution_attempts(conflict.conflict_id)
        assert updated.resolution_attempts == 1

        updated2 = store.increment_resolution_attempts(conflict.conflict_id)
        assert updated2.resolution_attempts == 2

    def test_reduce_severity(self, store):
        """Reduce severity works."""
        conflict = store.create_conflict("u1", ConflictType.JEALOUSY, 0.8)
        reduced = store.reduce_severity(conflict.conflict_id, 0.3)

        assert reduced.severity == 0.5

    def test_reduce_severity_minimum_zero(self, store):
        """Reduce severity doesn't go below zero."""
        conflict = store.create_conflict("u1", ConflictType.JEALOUSY, 0.3)
        reduced = store.reduce_severity(conflict.conflict_id, 0.5)

        assert reduced.severity == 0.0

    def test_get_conflict_summary(self, store):
        """Get conflict summary works."""
        # Create and resolve some conflicts
        c1 = store.create_conflict("u1", ConflictType.JEALOUSY, 0.5)
        store.resolve_conflict(c1.conflict_id, ResolutionType.FULL)

        c2 = store.create_conflict("u1", ConflictType.ATTENTION, 0.4)
        store.resolve_conflict(c2.conflict_id, ResolutionType.PARTIAL)

        # Leave one unresolved
        store.create_conflict("u1", ConflictType.TRUST, 0.7)

        summary = store.get_conflict_summary("u1")
        assert summary.total_conflicts == 3
        assert summary.resolved_conflicts == 2
        assert summary.current_conflict is not None

    def test_count_consecutive_unresolved_crises(self, store):
        """Count consecutive unresolved crises works."""
        # Create a resolved conflict
        c1 = store.create_conflict("u1", ConflictType.JEALOUSY, 0.5)
        store.resolve_conflict(c1.conflict_id, ResolutionType.FULL)

        # Create unresolved crisis
        c2 = store.create_conflict("u1", ConflictType.ATTENTION, 0.8)
        store.escalate_conflict(c2.conflict_id, EscalationLevel.CRISIS)

        # Another unresolved crisis
        c3 = store.create_conflict("u1", ConflictType.TRUST, 0.9)
        store.escalate_conflict(c3.conflict_id, EscalationLevel.CRISIS)

        count = store.count_consecutive_unresolved_crises("u1")
        assert count == 2

    def test_clear_user_data(self, store):
        """Clear user data works."""
        store.create_trigger("u1", TriggerType.JEALOUSY, 0.5)
        store.create_conflict("u1", ConflictType.JEALOUSY, 0.5)

        store.clear_user_data("u1")

        assert len(store.get_user_triggers("u1")) == 0
        assert len(store.get_user_conflicts("u1")) == 0


class TestGlobalStore:
    """Test global store instance."""

    def test_get_conflict_store_returns_instance(self):
        """get_conflict_store returns instance."""
        store = get_conflict_store()
        assert isinstance(store, ConflictStore)

    def test_get_conflict_store_same_instance(self):
        """get_conflict_store returns same instance."""
        store1 = get_conflict_store()
        store2 = get_conflict_store()
        assert store1 is store2
