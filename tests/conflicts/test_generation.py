"""Generation tests for Conflict Generation System (Spec 027, Phase C: T012-T015).

Tests for:
- T012: ConflictGenerator class
- T013: Severity calculation
- T014: Conflict type selection
- T015: Phase C coverage
"""

import pytest
from datetime import UTC, datetime, timedelta

from nikita.conflicts.generator import (
    ConflictGenerator,
    GenerationContext,
    GenerationResult,
    get_conflict_generator,
)
from nikita.conflicts.models import (
    ActiveConflict,
    ConflictConfig,
    ConflictTrigger,
    ConflictType,
    EscalationLevel,
    TriggerType,
)


# Fixtures


@pytest.fixture
def generator():
    """Create a ConflictGenerator for testing."""
    return ConflictGenerator()


@pytest.fixture
def basic_context():
    """Create a basic generation context."""
    return GenerationContext(
        user_id="user_123",
        chapter=3,
        relationship_score=50,
    )


@pytest.fixture
def dismissive_trigger():
    """Create a dismissive trigger."""
    return ConflictTrigger(
        trigger_id="t_dismissive",
        trigger_type=TriggerType.DISMISSIVE,
        severity=0.5,
    )


@pytest.fixture
def jealousy_trigger():
    """Create a jealousy trigger."""
    return ConflictTrigger(
        trigger_id="t_jealousy",
        trigger_type=TriggerType.JEALOUSY,
        severity=0.6,
    )


@pytest.fixture
def boundary_trigger():
    """Create a boundary trigger."""
    return ConflictTrigger(
        trigger_id="t_boundary",
        trigger_type=TriggerType.BOUNDARY,
        severity=0.7,
    )


@pytest.fixture
def trust_trigger():
    """Create a trust trigger."""
    return ConflictTrigger(
        trigger_id="t_trust",
        trigger_type=TriggerType.TRUST,
        severity=0.8,
    )


# Test GenerationContext


class TestGenerationContext:
    """Tests for GenerationContext model."""

    def test_create_basic_context(self):
        """Test creating a basic context."""
        ctx = GenerationContext(user_id="user_1")
        assert ctx.user_id == "user_1"
        assert ctx.chapter == 1  # default
        assert ctx.relationship_score == 50  # default

    def test_create_full_context(self):
        """Test creating context with all fields."""
        recent = [
            ActiveConflict(
                conflict_id="c1",
                user_id="user_1",
                conflict_type=ConflictType.JEALOUSY,
                severity=0.5,
            )
        ]
        ctx = GenerationContext(
            user_id="user_1",
            chapter=4,
            relationship_score=75,
            recent_conflicts=recent,
            days_since_last_conflict=2.5,
        )
        assert ctx.chapter == 4
        assert ctx.relationship_score == 75
        assert len(ctx.recent_conflicts) == 1
        assert ctx.days_since_last_conflict == 2.5


# Test GenerationResult


class TestGenerationResult:
    """Tests for GenerationResult model."""

    def test_empty_result(self):
        """Test result when no conflict generated."""
        result = GenerationResult()
        assert result.conflict is None
        assert not result.generated
        assert result.reason == ""

    def test_result_with_conflict(self):
        """Test result with generated conflict."""
        conflict = ActiveConflict(
            conflict_id="c1",
            user_id="user_1",
            conflict_type=ConflictType.JEALOUSY,
            severity=0.5,
        )
        trigger = ConflictTrigger(
            trigger_id="t1",
            trigger_type=TriggerType.JEALOUSY,
            severity=0.6,
        )
        result = GenerationResult(
            conflict=conflict,
            generated=True,
            reason="Conflict generated: jealousy",
            contributing_triggers=[trigger],
        )
        assert result.generated
        assert result.conflict == conflict
        assert len(result.contributing_triggers) == 1


# Test ConflictGenerator


class TestConflictGenerator:
    """Tests for ConflictGenerator class."""

    def test_create_generator(self):
        """Test creating a generator."""
        gen = ConflictGenerator()
        assert gen is not None
        assert gen._config is not None

    def test_generate_no_triggers(self, generator, basic_context):
        """Test generation with no triggers."""
        result = generator.generate([], basic_context)
        assert not result.generated
        assert "No triggers" in result.reason

    def test_generate_single_trigger(self, generator, basic_context, jealousy_trigger):
        """Test generation with single trigger."""
        result = generator.generate([jealousy_trigger], basic_context)
        assert result.generated
        assert result.conflict is not None
        assert result.conflict.conflict_type == ConflictType.JEALOUSY

    def test_generate_multiple_triggers(
        self, generator, basic_context, dismissive_trigger, jealousy_trigger
    ):
        """Test generation with multiple triggers."""
        triggers = [dismissive_trigger, jealousy_trigger]
        result = generator.generate(triggers, basic_context)
        assert result.generated
        assert result.conflict is not None
        assert len(result.contributing_triggers) >= 1

    def test_generate_stores_conflict(self, generator, basic_context, jealousy_trigger):
        """Test that generated conflict is stored."""
        result = generator.generate([jealousy_trigger], basic_context)
        assert result.generated

        # Verify conflict was generated (store is internal to generator)
        assert result.conflict is not None
        assert result.conflict.conflict_type == ConflictType.JEALOUSY


# Test Trigger Prioritization


class TestTriggerPrioritization:
    """Tests for trigger prioritization logic."""

    def test_low_severity_filtered(self, generator, basic_context):
        """Test that low severity triggers are filtered."""
        low_trigger = ConflictTrigger(
            trigger_id="t_low",
            trigger_type=TriggerType.DISMISSIVE,
            severity=0.1,  # Below threshold
        )
        result = generator.generate([low_trigger], basic_context)
        assert not result.generated
        assert "threshold" in result.reason.lower()

    def test_highest_severity_prioritized(self, generator, basic_context):
        """Test that highest severity trigger is prioritized."""
        triggers = [
            ConflictTrigger(
                trigger_id="t1",
                trigger_type=TriggerType.DISMISSIVE,
                severity=0.3,
            ),
            ConflictTrigger(
                trigger_id="t2",
                trigger_type=TriggerType.TRUST,
                severity=0.8,
            ),
        ]
        result = generator.generate(triggers, basic_context)
        assert result.generated
        # Trust should be selected (higher severity and priority)
        assert result.conflict.conflict_type == ConflictType.TRUST

    def test_max_three_triggers(self, generator, basic_context):
        """Test that at most 3 triggers are used."""
        triggers = [
            ConflictTrigger(
                trigger_id=f"t{i}",
                trigger_type=TriggerType.JEALOUSY,
                severity=0.5 + i * 0.05,
            )
            for i in range(5)
        ]
        result = generator.generate(triggers, basic_context)
        assert result.generated
        assert len(result.contributing_triggers) <= 3


# Test Severity Calculation (T013)


class TestSeverityCalculation:
    """Tests for severity calculation."""

    def test_severity_based_on_trigger_type(self, generator, basic_context):
        """Test severity varies by trigger type."""
        # Trust has higher base severity than dismissive
        trust = ConflictTrigger(
            trigger_id="t1",
            trigger_type=TriggerType.TRUST,
            severity=0.5,
        )
        dismissive = ConflictTrigger(
            trigger_id="t2",
            trigger_type=TriggerType.DISMISSIVE,
            severity=0.5,
        )

        result_trust = generator.generate([trust], basic_context)

        # Need fresh context to avoid active conflict
        ctx_dismissive = GenerationContext(
            user_id="user_456",  # Different user
            chapter=3,
            relationship_score=50,
        )
        result_dismissive = generator.generate([dismissive], ctx_dismissive)

        assert result_trust.generated and result_dismissive.generated
        assert result_trust.conflict.severity >= result_dismissive.conflict.severity

    def test_low_relationship_increases_severity(self, generator, jealousy_trigger):
        """Test that low relationship score increases severity."""
        ctx_low = GenerationContext(
            user_id="user_low",
            chapter=3,
            relationship_score=20,
        )
        ctx_high = GenerationContext(
            user_id="user_high",
            chapter=3,
            relationship_score=80,
        )

        result_low = generator.generate([jealousy_trigger], ctx_low)

        # Create new trigger for second test
        jealousy2 = ConflictTrigger(
            trigger_id="t_jealousy2",
            trigger_type=TriggerType.JEALOUSY,
            severity=0.6,
        )
        result_high = generator.generate([jealousy2], ctx_high)

        assert result_low.generated and result_high.generated
        assert result_low.conflict.severity > result_high.conflict.severity

    def test_recent_conflicts_increase_severity(self, generator, jealousy_trigger):
        """Test that recent conflicts increase severity."""
        recent = [
            ActiveConflict(
                conflict_id=f"c{i}",
                user_id="user",
                conflict_type=ConflictType.ATTENTION,
                severity=0.5,
            )
            for i in range(3)
        ]

        ctx_no_history = GenerationContext(
            user_id="user_no_hist",
            chapter=3,
            relationship_score=50,
            recent_conflicts=[],
        )
        ctx_with_history = GenerationContext(
            user_id="user_with_hist",
            chapter=3,
            relationship_score=50,
            recent_conflicts=recent,
        )

        result_no_hist = generator.generate([jealousy_trigger], ctx_no_history)

        jealousy2 = ConflictTrigger(
            trigger_id="t_jealousy2",
            trigger_type=TriggerType.JEALOUSY,
            severity=0.6,
        )
        result_with_hist = generator.generate([jealousy2], ctx_with_history)

        assert result_no_hist.generated and result_with_hist.generated
        assert result_with_hist.conflict.severity >= result_no_hist.conflict.severity

    def test_later_chapters_reduce_severity(self, generator, jealousy_trigger):
        """Test that later chapters slightly reduce severity."""
        ctx_ch1 = GenerationContext(
            user_id="user_ch1",
            chapter=1,
            relationship_score=50,
        )
        ctx_ch5 = GenerationContext(
            user_id="user_ch5",
            chapter=5,
            relationship_score=50,
        )

        result_ch1 = generator.generate([jealousy_trigger], ctx_ch1)

        jealousy2 = ConflictTrigger(
            trigger_id="t_jealousy2",
            trigger_type=TriggerType.JEALOUSY,
            severity=0.6,
        )
        result_ch5 = generator.generate([jealousy2], ctx_ch5)

        assert result_ch1.generated and result_ch5.generated
        assert result_ch1.conflict.severity >= result_ch5.conflict.severity


# Test Conflict Type Selection (T014)


class TestConflictTypeSelection:
    """Tests for conflict type selection."""

    def test_trigger_maps_to_conflict_type(self, generator, basic_context):
        """Test that triggers map to correct conflict types."""
        type_mapping = [
            (TriggerType.DISMISSIVE, ConflictType.ATTENTION),
            (TriggerType.NEGLECT, ConflictType.ATTENTION),
            (TriggerType.JEALOUSY, ConflictType.JEALOUSY),
            (TriggerType.BOUNDARY, ConflictType.BOUNDARY),
            (TriggerType.TRUST, ConflictType.TRUST),
        ]

        for i, (trigger_type, expected_conflict) in enumerate(type_mapping):
            ctx = GenerationContext(
                user_id=f"user_{i}",
                chapter=3,
                relationship_score=50,
            )
            trigger = ConflictTrigger(
                trigger_id=f"t_{i}",
                trigger_type=trigger_type,
                severity=0.5,
            )
            result = generator.generate([trigger], ctx)
            assert result.generated, f"Failed for {trigger_type}"
            assert result.conflict.conflict_type == expected_conflict, (
                f"Expected {expected_conflict} for {trigger_type}, "
                f"got {result.conflict.conflict_type}"
            )

    def test_higher_priority_type_selected(self, generator, basic_context):
        """Test that higher priority conflict types are selected."""
        # Trust (priority 4) vs Attention (priority 1)
        triggers = [
            ConflictTrigger(
                trigger_id="t1",
                trigger_type=TriggerType.DISMISSIVE,  # → ATTENTION
                severity=0.5,
            ),
            ConflictTrigger(
                trigger_id="t2",
                trigger_type=TriggerType.TRUST,  # → TRUST (higher priority)
                severity=0.5,
            ),
        ]
        result = generator.generate(triggers, basic_context)
        assert result.generated
        assert result.conflict.conflict_type == ConflictType.TRUST

    def test_avoids_same_type_in_succession(self, generator):
        """Test that same conflict type is avoided if recent."""
        recent = [
            ActiveConflict(
                conflict_id="c1",
                user_id="user",
                conflict_type=ConflictType.JEALOUSY,
                severity=0.5,
            ),
        ]
        ctx = GenerationContext(
            user_id="user_avoid",
            chapter=3,
            relationship_score=50,
            recent_conflicts=recent,
        )

        # Both triggers would map to JEALOUSY
        triggers = [
            ConflictTrigger(
                trigger_id="t1",
                trigger_type=TriggerType.JEALOUSY,
                severity=0.4,
            ),
            ConflictTrigger(
                trigger_id="t2",
                trigger_type=TriggerType.DISMISSIVE,  # → ATTENTION
                severity=0.5,
            ),
        ]
        result = generator.generate(triggers, ctx)
        assert result.generated
        # Should prefer ATTENTION since JEALOUSY was recent
        # (unless JEALOUSY severity is much higher)


# Test Cooldown and Skip Logic


class TestCooldownAndSkip:
    """Tests for cooldown and skip logic."""

    def test_cooldown_prevents_conflict(self, generator, jealousy_trigger):
        """Test that cooldown period prevents new conflicts."""
        ctx = GenerationContext(
            user_id="user_cooldown",
            chapter=3,
            relationship_score=50,
            days_since_last_conflict=0.1,  # Very recent (2.4 hours)
        )
        result = generator.generate([jealousy_trigger], ctx)
        assert not result.generated
        assert "cooldown" in result.reason.lower()

    def test_after_cooldown_allows_conflict(self, generator, jealousy_trigger):
        """Test that conflicts are allowed after cooldown."""
        ctx = GenerationContext(
            user_id="user_after_cooldown",
            chapter=3,
            relationship_score=50,
            days_since_last_conflict=1.0,  # 24 hours ago (past 4h cooldown)
        )
        result = generator.generate([jealousy_trigger], ctx)
        assert result.generated

    def test_high_relationship_prevents_minor_conflict(self, generator):
        """Test that high relationship prevents minor conflicts."""
        ctx = GenerationContext(
            user_id="user_high_rel",
            chapter=3,
            relationship_score=95,  # Very high
        )
        minor_trigger = ConflictTrigger(
            trigger_id="t_minor",
            trigger_type=TriggerType.DISMISSIVE,
            severity=0.4,  # Below 0.6 threshold for high relationship
        )
        result = generator.generate([minor_trigger], ctx)
        assert not result.generated
        assert "relationship score" in result.reason.lower()

    def test_high_relationship_allows_major_conflict(self, generator, trust_trigger):
        """Test that high severity conflicts bypass high relationship protection."""
        ctx = GenerationContext(
            user_id="user_high_rel_major",
            chapter=3,
            relationship_score=95,
        )
        result = generator.generate([trust_trigger], ctx)
        assert result.generated

    # Note: test_existing_conflict_prevents_new removed — ConflictGenerator no longer
    # tracks active conflicts in-memory (serverless: state lives in DB JSONB only).
    # Pass conflict_details={"temperature": ...} to use temperature-based generation,
    # which respects active conflict state stored in the JSONB.


# Test should_generate_conflict


class TestShouldGenerateConflict:
    """Tests for should_generate_conflict method."""

    def test_should_generate_true(self, generator, basic_context, jealousy_trigger):
        """Test should_generate returns true when conditions met."""
        should, reason = generator.should_generate_conflict([jealousy_trigger], basic_context)
        assert should
        assert "met" in reason.lower()

    def test_should_generate_false_no_triggers(self, generator, basic_context):
        """Test should_generate returns false with no triggers."""
        should, reason = generator.should_generate_conflict([], basic_context)
        assert not should
        assert "No triggers" in reason

    # Note: test_should_generate_false_existing_conflict removed — generator no longer
    # tracks active conflicts in-memory. Active conflict blocking is handled via
    # conflict_details JSONB state (loaded from DB by callers).


# Test Global Instance


class TestGlobalGenerator:
    """Tests for global generator instance."""

    def test_get_conflict_generator_returns_instance(self):
        """Test that get_conflict_generator returns instance."""
        gen = get_conflict_generator()
        assert isinstance(gen, ConflictGenerator)

    def test_get_conflict_generator_same_instance(self):
        """Test that same instance is returned."""
        gen1 = get_conflict_generator()
        gen2 = get_conflict_generator()
        assert gen1 is gen2


# Test Edge Cases


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_trigger_list(self, generator, basic_context):
        """Test handling empty trigger list."""
        result = generator.generate([], basic_context)
        assert not result.generated

    def test_all_triggers_below_threshold(self, generator, basic_context):
        """Test when all triggers are below threshold."""
        triggers = [
            ConflictTrigger(
                trigger_id=f"t{i}",
                trigger_type=TriggerType.DISMISSIVE,
                severity=0.1,  # All below 0.25 threshold
            )
            for i in range(3)
        ]
        result = generator.generate(triggers, basic_context)
        assert not result.generated

    def test_severity_clamped_to_one(self, generator):
        """Test that severity is clamped to 1.0 max."""
        ctx = GenerationContext(
            user_id="user_high_sev",
            chapter=1,  # Higher modifier
            relationship_score=10,  # Higher modifier
            recent_conflicts=[
                ActiveConflict(
                    conflict_id=f"c{i}",
                    user_id="user",
                    conflict_type=ConflictType.ATTENTION,
                    severity=0.5,
                )
                for i in range(5)
            ],  # Higher modifier
        )
        trigger = ConflictTrigger(
            trigger_id="t1",
            trigger_type=TriggerType.TRUST,
            severity=0.99,  # Very high
        )
        result = generator.generate([trigger], ctx)
        assert result.generated
        assert result.conflict.severity <= 1.0
