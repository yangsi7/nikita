"""Tests for Resolution Management (Spec 027, Phase E).

Tests cover:
- Resolution quality evaluation (rule-based)
- Resolution type determination
- Score change calculations
- Escalation level multipliers
- Conflict resolution application
"""

import pytest
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from nikita.conflicts.models import (
    ActiveConflict,
    ConflictConfig,
    ConflictType,
    EscalationLevel,
    ResolutionType,
    get_conflict_config,
)
from nikita.conflicts.resolution import (
    ResolutionContext,
    ResolutionEvaluation,
    ResolutionManager,
    ResolutionQuality,
    get_resolution_manager,
)
from nikita.conflicts.store import ConflictStore


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def store():
    """Fresh conflict store."""
    return ConflictStore()


@pytest.fixture
def config():
    """Default conflict config."""
    return get_conflict_config()


@pytest.fixture
def manager(store, config):
    """Resolution manager with LLM disabled for testing."""
    return ResolutionManager(store=store, config=config, llm_enabled=False)


@pytest.fixture
def active_conflict(store):
    """Create an active conflict for testing."""
    return store.create_conflict(
        user_id="user_123",
        conflict_type=ConflictType.ATTENTION,
        trigger_ids=["trigger_123"],
        severity=0.5,
    )


# =============================================================================
# ResolutionQuality Enum Tests
# =============================================================================


class TestResolutionQualityEnum:
    """Test ResolutionQuality enum values."""

    def test_all_quality_levels_exist(self):
        """All 5 quality levels should exist."""
        assert ResolutionQuality.EXCELLENT.value == "excellent"
        assert ResolutionQuality.GOOD.value == "good"
        assert ResolutionQuality.ADEQUATE.value == "adequate"
        assert ResolutionQuality.POOR.value == "poor"
        assert ResolutionQuality.HARMFUL.value == "harmful"

    def test_quality_from_string(self):
        """Quality can be created from string."""
        assert ResolutionQuality("excellent") == ResolutionQuality.EXCELLENT
        assert ResolutionQuality("harmful") == ResolutionQuality.HARMFUL


# =============================================================================
# ResolutionContext Tests
# =============================================================================


class TestResolutionContext:
    """Test ResolutionContext model."""

    def test_context_creation(self, active_conflict):
        """Context can be created with required fields."""
        context = ResolutionContext(
            conflict=active_conflict,
            user_message="I'm so sorry, I didn't mean to hurt you.",
        )
        assert context.user_message == "I'm so sorry, I didn't mean to hurt you."
        assert context.previous_attempts == 0
        assert context.relationship_score == 50

    def test_context_with_history(self, active_conflict):
        """Context can track previous attempts."""
        context = ResolutionContext(
            conflict=active_conflict,
            user_message="Please forgive me",
            previous_attempts=2,
            relationship_score=35,
        )
        assert context.previous_attempts == 2
        assert context.relationship_score == 35


# =============================================================================
# ResolutionEvaluation Tests
# =============================================================================


class TestResolutionEvaluation:
    """Test ResolutionEvaluation model."""

    def test_evaluation_defaults(self):
        """Evaluation has sensible defaults."""
        eval = ResolutionEvaluation(
            quality=ResolutionQuality.ADEQUATE,
            resolution_type=ResolutionType.PARTIAL,
        )
        assert eval.severity_reduction == 0.0
        assert eval.score_change == 0
        assert eval.reasoning == ""

    def test_evaluation_full(self):
        """Evaluation can have all fields."""
        eval = ResolutionEvaluation(
            quality=ResolutionQuality.EXCELLENT,
            resolution_type=ResolutionType.FULL,
            severity_reduction=1.0,
            score_change=10,
            reasoning="Sincere apology with understanding",
        )
        assert eval.severity_reduction == 1.0
        assert eval.score_change == 10


# =============================================================================
# Rule-Based Evaluation Tests
# =============================================================================


class TestRuleBasedEvaluation:
    """Test rule-based resolution evaluation."""

    def test_excellent_apology(self, manager, active_conflict):
        """Sincere apology with understanding = EXCELLENT."""
        context = ResolutionContext(
            conflict=active_conflict,
            user_message="I'm so sorry, I was wrong. I understand why you're upset. Let me make it up to you.",
        )
        result = manager.evaluate_sync(context)
        assert result.quality == ResolutionQuality.EXCELLENT
        assert result.score_change == 10

    def test_good_apology(self, manager, active_conflict):
        """Thoughtful apology = GOOD."""
        context = ResolutionContext(
            conflict=active_conflict,
            user_message="I'm sorry, I didn't realize how that made you feel. It won't happen again.",
        )
        result = manager.evaluate_sync(context)
        assert result.quality == ResolutionQuality.GOOD
        assert result.score_change == 5

    def test_adequate_acknowledgment(self, manager, active_conflict):
        """Minimal acknowledgment = ADEQUATE."""
        context = ResolutionContext(
            conflict=active_conflict,
            user_message="Sorry about that, I'll try to do better.",  # One good keyword = ADEQUATE
        )
        result = manager.evaluate_sync(context)
        assert result.quality == ResolutionQuality.ADEQUATE
        assert result.score_change == 1

    def test_poor_dismissive(self, manager, active_conflict):
        """Dismissive response = POOR."""
        context = ResolutionContext(
            conflict=active_conflict,
            user_message="Fine.",
        )
        result = manager.evaluate_sync(context)
        assert result.quality == ResolutionQuality.POOR
        assert result.score_change == -2

    def test_poor_short_message(self, manager, active_conflict):
        """Very short message = POOR."""
        context = ResolutionContext(
            conflict=active_conflict,
            user_message="ok",
        )
        result = manager.evaluate_sync(context)
        assert result.quality == ResolutionQuality.POOR

    def test_harmful_blaming(self, manager, active_conflict):
        """Blaming response = HARMFUL."""
        context = ResolutionContext(
            conflict=active_conflict,
            user_message="It's your fault for being so paranoid. You're overreacting.",
        )
        result = manager.evaluate_sync(context)
        assert result.quality == ResolutionQuality.HARMFUL
        assert result.score_change == -10

    def test_harmful_gaslighting(self, manager, active_conflict):
        """Gaslighting response = HARMFUL."""
        context = ResolutionContext(
            conflict=active_conflict,
            user_message="You're crazy, this isn't a big deal. Get over it.",
        )
        result = manager.evaluate_sync(context)
        assert result.quality == ResolutionQuality.HARMFUL

    def test_longer_message_without_keywords_adequate(self, manager, active_conflict):
        """Longer message without clear indicators = ADEQUATE."""
        context = ResolutionContext(
            conflict=active_conflict,
            user_message="I've been thinking about what happened between us and I want to talk about it more. Maybe we can figure out how to move forward together.",
        )
        result = manager.evaluate_sync(context)
        assert result.quality == ResolutionQuality.ADEQUATE


# =============================================================================
# Resolution Type Determination Tests
# =============================================================================


class TestResolutionTypeDetermination:
    """Test how quality maps to resolution type."""

    def test_excellent_gives_full_resolution(self, manager, active_conflict):
        """EXCELLENT quality = FULL resolution."""
        context = ResolutionContext(
            conflict=active_conflict,
            user_message="I'm so sorry, I was wrong. I love you and understand why you're upset.",
        )
        result = manager.evaluate_sync(context)
        assert result.quality == ResolutionQuality.EXCELLENT
        assert result.resolution_type == ResolutionType.FULL

    def test_good_gives_partial_resolution(self, manager, active_conflict):
        """GOOD quality = PARTIAL resolution."""
        context = ResolutionContext(
            conflict=active_conflict,
            user_message="I'm sorry, I apologize for what I did. I didn't realize.",
        )
        result = manager.evaluate_sync(context)
        assert result.quality == ResolutionQuality.GOOD
        assert result.resolution_type == ResolutionType.PARTIAL

    def test_adequate_gives_partial_resolution(self, manager, active_conflict):
        """ADEQUATE quality = PARTIAL resolution."""
        context = ResolutionContext(
            conflict=active_conflict,
            user_message="Sorry about that, I'll keep that in mind.",  # One good keyword = ADEQUATE
        )
        result = manager.evaluate_sync(context)
        assert result.quality == ResolutionQuality.ADEQUATE
        assert result.resolution_type == ResolutionType.PARTIAL

    def test_poor_gives_failed_resolution(self, manager, active_conflict):
        """POOR quality = FAILED resolution."""
        context = ResolutionContext(
            conflict=active_conflict,
            user_message="fine",
        )
        result = manager.evaluate_sync(context)
        assert result.quality == ResolutionQuality.POOR
        assert result.resolution_type == ResolutionType.FAILED

    def test_harmful_gives_failed_resolution(self, manager, active_conflict):
        """HARMFUL quality = FAILED resolution."""
        context = ResolutionContext(
            conflict=active_conflict,
            user_message="Your fault, you're overreacting, not a big deal",
        )
        result = manager.evaluate_sync(context)
        assert result.quality == ResolutionQuality.HARMFUL
        assert result.resolution_type == ResolutionType.FAILED


# =============================================================================
# Escalation Level Multiplier Tests
# =============================================================================


class TestEscalationLevelMultipliers:
    """Test how escalation level affects resolution."""

    def test_subtle_level_full_multiplier(self, manager, store):
        """SUBTLE level has 1.0 multiplier."""
        # Conflicts start at SUBTLE by default
        conflict = store.create_conflict(
            user_id="user_123",
            conflict_type=ConflictType.ATTENTION,
            trigger_ids=["trigger_123"],
            severity=0.5,
        )
        context = ResolutionContext(
            conflict=conflict,
            user_message="I'm sorry, I apologize for that.",
        )
        result = manager.evaluate_sync(context)
        # GOOD quality at SUBTLE = 0.6 * 1.0 = 0.6 severity reduction
        assert result.severity_reduction == 0.6

    def test_direct_level_reduced_multiplier(self, manager, store):
        """DIRECT level has 0.8 multiplier."""
        conflict = store.create_conflict(
            user_id="user_123",
            conflict_type=ConflictType.ATTENTION,
            trigger_ids=["trigger_123"],
            severity=0.5,
        )
        # Escalate to DIRECT
        store.escalate_conflict(conflict.conflict_id, EscalationLevel.DIRECT)
        conflict = store.get_conflict(conflict.conflict_id)

        context = ResolutionContext(
            conflict=conflict,
            user_message="I'm sorry, I apologize for that.",
        )
        result = manager.evaluate_sync(context)
        # GOOD quality at DIRECT = 0.6 * 0.8 = 0.48 severity reduction
        assert result.severity_reduction == pytest.approx(0.48)

    def test_crisis_level_lowest_multiplier(self, manager, store):
        """CRISIS level has 0.5 multiplier."""
        conflict = store.create_conflict(
            user_id="user_123",
            conflict_type=ConflictType.ATTENTION,
            trigger_ids=["trigger_123"],
            severity=0.8,
        )
        # Escalate to CRISIS
        store.escalate_conflict(conflict.conflict_id, EscalationLevel.CRISIS)
        conflict = store.get_conflict(conflict.conflict_id)

        context = ResolutionContext(
            conflict=conflict,
            user_message="I'm sorry, I apologize for that.",
        )
        result = manager.evaluate_sync(context)
        # GOOD quality at CRISIS = 0.6 * 0.5 = 0.3 severity reduction
        assert result.severity_reduction == pytest.approx(0.3)

    def test_crisis_only_excellent_resolves_fully(self, manager, store):
        """At CRISIS level, only EXCELLENT quality resolves fully."""
        conflict = store.create_conflict(
            user_id="user_123",
            conflict_type=ConflictType.ATTENTION,
            trigger_ids=["trigger_123"],
            severity=0.8,
        )
        # Escalate to CRISIS
        store.escalate_conflict(conflict.conflict_id, EscalationLevel.CRISIS)
        conflict = store.get_conflict(conflict.conflict_id)

        # GOOD at CRISIS = PARTIAL (not FULL)
        context_good = ResolutionContext(
            conflict=conflict,
            user_message="I'm sorry, I apologize for what I did.",
        )
        result_good = manager.evaluate_sync(context_good)
        assert result_good.resolution_type == ResolutionType.PARTIAL

        # EXCELLENT at CRISIS = FULL
        context_excellent = ResolutionContext(
            conflict=conflict,
            user_message="I'm so sorry, I was wrong. I understand why you're upset. I love you.",
        )
        result_excellent = manager.evaluate_sync(context_excellent)
        assert result_excellent.resolution_type == ResolutionType.FULL


# =============================================================================
# Severity Reduction Mapping Tests
# =============================================================================


class TestSeverityReductionMapping:
    """Test quality to severity reduction mapping."""

    def test_excellent_full_reduction(self, manager, active_conflict):
        """EXCELLENT = 1.0 (full) severity reduction."""
        context = ResolutionContext(
            conflict=active_conflict,
            user_message="I'm so sorry, I was wrong. I understand why you're upset. I love you.",
        )
        result = manager.evaluate_sync(context)
        assert result.severity_reduction == 1.0

    def test_good_moderate_reduction(self, manager, active_conflict):
        """GOOD = 0.6 severity reduction."""
        context = ResolutionContext(
            conflict=active_conflict,
            user_message="I'm sorry, I apologize for what happened.",
        )
        result = manager.evaluate_sync(context)
        assert result.severity_reduction == 0.6

    def test_adequate_small_reduction(self, manager, active_conflict):
        """ADEQUATE = 0.3 severity reduction."""
        context = ResolutionContext(
            conflict=active_conflict,
            user_message="Sorry about that, I'll think about it.",  # One good keyword = ADEQUATE
        )
        result = manager.evaluate_sync(context)
        assert result.severity_reduction == 0.3

    def test_poor_no_reduction(self, manager, active_conflict):
        """POOR = 0.0 severity reduction."""
        context = ResolutionContext(
            conflict=active_conflict,
            user_message="fine",
        )
        result = manager.evaluate_sync(context)
        assert result.severity_reduction == 0.0

    def test_harmful_negative_reduction(self, manager, active_conflict):
        """HARMFUL = -0.2 (increases severity)."""
        context = ResolutionContext(
            conflict=active_conflict,
            user_message="Your fault, you're overreacting.",
        )
        result = manager.evaluate_sync(context)
        assert result.severity_reduction == -0.2


# =============================================================================
# Resolve Method Tests
# =============================================================================


class TestResolveMethod:
    """Test the resolve() method that applies resolution to conflicts."""

    def test_resolve_reduces_severity(self, manager, store, active_conflict):
        """resolve() reduces conflict severity."""
        initial_severity = active_conflict.severity

        evaluation = ResolutionEvaluation(
            quality=ResolutionQuality.GOOD,
            resolution_type=ResolutionType.PARTIAL,
            severity_reduction=0.6,
            score_change=5,
        )

        result = manager.resolve(active_conflict.conflict_id, evaluation)

        assert result is not None
        assert result.severity < initial_severity
        assert result.resolution_attempts == 1

    def test_resolve_full_marks_resolved(self, manager, store, active_conflict):
        """FULL resolution marks conflict as resolved."""
        evaluation = ResolutionEvaluation(
            quality=ResolutionQuality.EXCELLENT,
            resolution_type=ResolutionType.FULL,
            severity_reduction=1.0,
            score_change=10,
        )

        result = manager.resolve(active_conflict.conflict_id, evaluation)

        assert result.resolved is True
        assert result.resolution_type == ResolutionType.FULL

    def test_resolve_harmful_increases_severity(self, manager, store, active_conflict):
        """HARMFUL response increases severity."""
        initial_severity = active_conflict.severity

        evaluation = ResolutionEvaluation(
            quality=ResolutionQuality.HARMFUL,
            resolution_type=ResolutionType.FAILED,
            severity_reduction=-0.2,
            score_change=-10,
        )

        result = manager.resolve(active_conflict.conflict_id, evaluation)

        assert result is not None
        assert result.severity > initial_severity

    def test_resolve_increments_attempts(self, manager, store, active_conflict):
        """Each resolution attempt increments counter."""
        evaluation = ResolutionEvaluation(
            quality=ResolutionQuality.ADEQUATE,
            resolution_type=ResolutionType.PARTIAL,
            severity_reduction=0.3,
            score_change=1,
        )

        manager.resolve(active_conflict.conflict_id, evaluation)
        conflict = store.get_conflict(active_conflict.conflict_id)
        assert conflict.resolution_attempts == 1

        manager.resolve(active_conflict.conflict_id, evaluation)
        conflict = store.get_conflict(active_conflict.conflict_id)
        assert conflict.resolution_attempts == 2

    def test_resolve_nonexistent_returns_none(self, manager):
        """Resolving nonexistent conflict returns None."""
        evaluation = ResolutionEvaluation(
            quality=ResolutionQuality.GOOD,
            resolution_type=ResolutionType.PARTIAL,
            severity_reduction=0.6,
            score_change=5,
        )

        result = manager.resolve("nonexistent_id", evaluation)
        assert result is None

    def test_resolve_already_resolved_returns_none(self, manager, store, active_conflict):
        """Can't resolve already resolved conflict."""
        # First resolve it fully
        store.resolve_conflict(active_conflict.conflict_id, ResolutionType.FULL)

        evaluation = ResolutionEvaluation(
            quality=ResolutionQuality.GOOD,
            resolution_type=ResolutionType.PARTIAL,
            severity_reduction=0.6,
            score_change=5,
        )

        result = manager.resolve(active_conflict.conflict_id, evaluation)
        assert result is None

    def test_partial_resolution_at_zero_severity_resolves(self, manager, store):
        """Partial resolution that reduces severity to 0 resolves conflict."""
        conflict = store.create_conflict(
            user_id="user_123",
            conflict_type=ConflictType.ATTENTION,
            trigger_ids=["trigger_123"],
            severity=0.2,  # Low severity
        )

        evaluation = ResolutionEvaluation(
            quality=ResolutionQuality.GOOD,
            resolution_type=ResolutionType.PARTIAL,
            severity_reduction=0.6,  # Enough to reduce below 0
            score_change=5,
        )

        result = manager.resolve(conflict.conflict_id, evaluation)

        assert result.severity <= 0
        assert result.resolved is True
        assert result.resolution_type == ResolutionType.PARTIAL


# =============================================================================
# Global Manager Tests
# =============================================================================


class TestGlobalManager:
    """Test global resolution manager singleton."""

    def test_get_resolution_manager_returns_instance(self, monkeypatch):
        """get_resolution_manager() returns a ResolutionManager."""
        # Ensure no LLM is created (needs API key)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-for-testing")

        import nikita.conflicts.resolution as resolution_module
        resolution_module._resolution_manager = None

        manager = get_resolution_manager()
        assert isinstance(manager, ResolutionManager)

    def test_get_resolution_manager_singleton(self, monkeypatch):
        """get_resolution_manager() returns same instance."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-for-testing")

        # Reset the global
        import nikita.conflicts.resolution as resolution_module
        resolution_module._resolution_manager = None

        manager1 = get_resolution_manager()
        manager2 = get_resolution_manager()
        assert manager1 is manager2


# =============================================================================
# Async Evaluation Tests (with mocked LLM)
# =============================================================================


class TestAsyncEvaluation:
    """Test async evaluation with mocked LLM."""

    @pytest.mark.asyncio
    async def test_async_evaluate_falls_back_to_rules(self, store, config):
        """async evaluate falls back to rules when LLM disabled."""
        manager = ResolutionManager(store=store, config=config, llm_enabled=False)

        conflict = store.create_conflict(
            user_id="user_123",
            conflict_type=ConflictType.ATTENTION,
            trigger_ids=["trigger_123"],
            severity=0.5,
        )

        context = ResolutionContext(
            conflict=conflict,
            user_message="I'm so sorry, I was wrong. I understand.",
        )

        result = await manager.evaluate(context)
        assert result.quality == ResolutionQuality.EXCELLENT

    @pytest.mark.asyncio
    async def test_async_evaluate_with_llm_error_falls_back(self, store, config):
        """async evaluate falls back to rules on LLM error."""
        # Create with llm_enabled=False to avoid API key requirement
        manager = ResolutionManager(store=store, config=config, llm_enabled=False)

        # Manually enable LLM mode and mock the agent
        manager._llm_enabled = True
        manager._agent = MagicMock()
        manager._agent.run = AsyncMock(side_effect=Exception("LLM Error"))

        conflict = store.create_conflict(
            user_id="user_123",
            conflict_type=ConflictType.ATTENTION,
            trigger_ids=["trigger_123"],
            severity=0.5,
        )

        context = ResolutionContext(
            conflict=conflict,
            user_message="I'm so sorry, I understand why you're upset.",
        )

        result = await manager.evaluate(context)
        # Should fall back to rules
        assert result.quality in list(ResolutionQuality)
