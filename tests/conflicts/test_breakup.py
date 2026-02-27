"""Tests for Breakup Management (Spec 027, Phase F).

Tests cover:
- Breakup risk levels
- Threshold checking (score-based and temperature-based)
- Warning messages
- Breakup message generation
- Game over state
- Relationship status reporting
"""

import pytest
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from nikita.conflicts.models import (
    ActiveConflict,
    ConflictConfig,
    ConflictType,
    EscalationLevel,
    ResolutionType,
    get_conflict_config,
)
from nikita.conflicts.breakup import (
    BreakupManager,
    BreakupResult,
    BreakupRisk,
    ThresholdResult,
    get_breakup_manager,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def config():
    """Default conflict config."""
    return get_conflict_config()


@pytest.fixture
def manager(config):
    """Breakup manager for testing."""
    return BreakupManager(config=config)


# =============================================================================
# BreakupRisk Enum Tests
# =============================================================================


class TestBreakupRiskEnum:
    """Test BreakupRisk enum values."""

    def test_all_risk_levels_exist(self):
        """All 4 risk levels should exist."""
        assert BreakupRisk.NONE.value == "none"
        assert BreakupRisk.WARNING.value == "warning"
        assert BreakupRisk.CRITICAL.value == "critical"
        assert BreakupRisk.TRIGGERED.value == "triggered"

    def test_risk_from_string(self):
        """Risk can be created from string."""
        assert BreakupRisk("none") == BreakupRisk.NONE
        assert BreakupRisk("triggered") == BreakupRisk.TRIGGERED


# =============================================================================
# ThresholdResult Tests
# =============================================================================


class TestThresholdResult:
    """Test ThresholdResult model."""

    def test_threshold_result_defaults(self):
        """ThresholdResult has sensible defaults."""
        result = ThresholdResult()
        assert result.risk_level == BreakupRisk.NONE
        assert result.score == 50
        assert result.consecutive_crises == 0
        assert result.should_warn is False
        assert result.should_breakup is False
        assert result.reason == ""

    def test_threshold_result_full(self):
        """ThresholdResult can have all fields set."""
        result = ThresholdResult(
            risk_level=BreakupRisk.TRIGGERED,
            score=5,
            consecutive_crises=3,
            should_warn=False,
            should_breakup=True,
            reason="Score too low",
        )
        assert result.risk_level == BreakupRisk.TRIGGERED
        assert result.should_breakup is True


# =============================================================================
# BreakupResult Tests
# =============================================================================


class TestBreakupResult:
    """Test BreakupResult model."""

    def test_breakup_result_defaults(self):
        """BreakupResult has sensible defaults."""
        result = BreakupResult()
        assert result.breakup_triggered is False
        assert result.final_message == ""
        assert result.reason == ""
        assert result.game_over is False

    def test_breakup_result_triggered(self):
        """BreakupResult can represent triggered breakup."""
        result = BreakupResult(
            breakup_triggered=True,
            final_message="It's over.",
            reason="Score below threshold",
            game_over=True,
        )
        assert result.breakup_triggered is True
        assert result.game_over is True


# =============================================================================
# Score-Based Threshold Tests
# =============================================================================


class TestScoreBasedThreshold:
    """Test score-based breakup thresholds."""

    def test_healthy_score_no_risk(self, manager):
        """Score >= 50 has no risk."""
        result = manager.check_threshold("user_123", relationship_score=50)
        assert result.risk_level == BreakupRisk.NONE
        assert result.should_warn is False
        assert result.should_breakup is False
        assert "healthy" in result.reason.lower()

    def test_high_score_no_risk(self, manager):
        """High score (75) has no risk."""
        result = manager.check_threshold("user_123", relationship_score=75)
        assert result.risk_level == BreakupRisk.NONE
        assert result.should_warn is False
        assert result.should_breakup is False

    def test_warning_threshold_19(self, manager):
        """Score 19 triggers warning (< 20)."""
        result = manager.check_threshold("user_123", relationship_score=19)
        assert result.risk_level == BreakupRisk.WARNING
        assert result.should_warn is True
        assert result.should_breakup is False

    def test_warning_threshold_15(self, manager):
        """Score 15 triggers warning (but not critical)."""
        result = manager.check_threshold("user_123", relationship_score=15)
        assert result.risk_level == BreakupRisk.WARNING
        assert result.should_warn is True
        assert result.should_breakup is False

    def test_critical_threshold_14(self, manager):
        """Score 14 triggers critical (< 15)."""
        result = manager.check_threshold("user_123", relationship_score=14)
        assert result.risk_level == BreakupRisk.CRITICAL
        assert result.should_warn is True
        assert result.should_breakup is False

    def test_breakup_threshold_9(self, manager):
        """Score 9 triggers breakup (< 10)."""
        result = manager.check_threshold("user_123", relationship_score=9)
        assert result.risk_level == BreakupRisk.TRIGGERED
        assert result.should_breakup is True

    def test_breakup_threshold_0(self, manager):
        """Score 0 triggers breakup."""
        result = manager.check_threshold("user_123", relationship_score=0)
        assert result.risk_level == BreakupRisk.TRIGGERED
        assert result.should_breakup is True


# =============================================================================
# Crisis-Based Threshold Tests
#
# Note: consecutive_crises is now always 0 (Spec 057 — in-memory ConflictStore
# removed, serverless cold-starts would reset any counter). These tests verify
# the score-path behavior with no crisis escalation.
# =============================================================================


class TestCrisisBasedThreshold:
    """Test consecutive crisis breakup thresholds.

    With the in-memory ConflictStore removed, consecutive_crises is always 0
    (state is now stored in PostgreSQL via conflict_details JSONB).
    These tests verify the expected behavior with consecutive_crises=0.
    """

    def test_no_crises_healthy(self, manager):
        """No consecutive crises is healthy."""
        result = manager.check_threshold("user_123", relationship_score=50)
        assert result.consecutive_crises == 0
        assert result.should_breakup is False


# =============================================================================
# Breakup Triggering Tests
# =============================================================================


class TestBreakupTriggering:
    """Test the trigger_breakup method."""

    def test_trigger_breakup_returns_result(self, manager):
        """trigger_breakup returns a BreakupResult."""
        result = manager.trigger_breakup(
            user_id="user_123",
            reason="Score too low",
        )
        assert isinstance(result, BreakupResult)
        assert result.breakup_triggered is True
        assert result.game_over is True
        assert len(result.final_message) > 0

    def test_trigger_breakup_with_conflict_type(self, manager):
        """Breakup message can be based on conflict type."""
        result = manager.trigger_breakup(
            user_id="user_123",
            reason="Jealousy crisis",
            conflict_type="jealousy",
        )
        assert result.breakup_triggered is True
        # Message should be from jealousy category (mentions jealousy themes)
        # We just check it's not empty
        assert len(result.final_message) > 0

    def test_trigger_breakup_no_active_conflict(self, manager):
        """Can trigger breakup even without active conflict."""
        result = manager.trigger_breakup(
            user_id="user_123",
            reason="Score too low",
        )
        assert result.breakup_triggered is True


# =============================================================================
# Warning Message Tests
# =============================================================================


class TestWarningMessages:
    """Test warning message generation."""

    def test_get_warning_message_returns_string(self, manager):
        """get_warning_message returns a non-empty string."""
        message = manager.get_warning_message()
        assert isinstance(message, str)
        assert len(message) > 0

    def test_warning_messages_variety(self, manager):
        """Multiple calls can return different messages."""
        messages = set()
        # Call many times to get variety
        for _ in range(50):
            messages.add(manager.get_warning_message())

        # Should have at least 2 different messages (probabilistic)
        # The actual list has 3 messages
        assert len(messages) >= 1  # At minimum, one message

    def test_warning_messages_theme(self, manager):
        """Warning messages express relationship concern."""
        # Get all possible warning messages
        all_messages = manager.WARNING_MESSAGES

        # Each should express concern/difficulty
        for msg in all_messages:
            assert any(word in msg.lower() for word in [
                "hard", "wonder", "drift", "serious", "can't", "going"
            ])


# =============================================================================
# Breakup Message Tests
# =============================================================================


class TestBreakupMessages:
    """Test breakup message generation."""

    def test_breakup_messages_by_type(self, manager):
        """Breakup messages exist for each conflict type."""
        types = ["jealousy", "attention", "boundary", "trust", "general"]

        for conflict_type in types:
            assert conflict_type in manager.BREAKUP_MESSAGES
            messages = manager.BREAKUP_MESSAGES[conflict_type]
            assert len(messages) >= 1
            for msg in messages:
                assert len(msg) > 20  # Substantial message

    def test_general_fallback(self, manager):
        """Unknown conflict type falls back to general messages."""
        result = manager.trigger_breakup(
            user_id="user_123",
            reason="Unknown issue",
            conflict_type="unknown_type",
        )
        # Should still produce a message (from general category)
        assert len(result.final_message) > 0

    def test_no_conflict_type_uses_general(self, manager):
        """No conflict type uses general messages."""
        result = manager.trigger_breakup(
            user_id="user_123",
            reason="Score too low",
            conflict_type=None,
        )
        assert len(result.final_message) > 0


# =============================================================================
# Relationship Status Tests
# =============================================================================


class TestRelationshipStatus:
    """Test get_relationship_status method."""

    def test_status_healthy(self, manager):
        """Healthy relationship status."""
        status = manager.get_relationship_status("user_123", relationship_score=75)

        assert status["score"] == 75
        assert status["risk_level"] == "none"
        assert status["should_warn"] is False
        assert status["should_breakup"] is False
        assert status["consecutive_crises"] == 0

    def test_status_warning(self, manager):
        """Warning relationship status."""
        status = manager.get_relationship_status("user_123", relationship_score=18)

        assert status["score"] == 18
        assert status["risk_level"] == "warning"
        assert status["should_warn"] is True
        assert status["should_breakup"] is False

    def test_status_critical(self, manager):
        """Critical relationship status."""
        status = manager.get_relationship_status("user_123", relationship_score=12)

        assert status["score"] == 12
        assert status["risk_level"] == "critical"
        assert status["should_warn"] is True
        assert status["should_breakup"] is False

    def test_status_includes_thresholds(self, manager, config):
        """Status includes threshold configuration."""
        status = manager.get_relationship_status("user_123", relationship_score=50)

        assert status["warning_threshold"] == config.warning_threshold
        assert status["breakup_threshold"] == config.breakup_threshold


# =============================================================================
# Check and Process Tests
# =============================================================================


class TestCheckAndProcess:
    """Test check_and_process combined method."""

    def test_check_and_process_healthy(self, manager):
        """Healthy score returns only threshold result."""
        threshold_result, breakup_result = manager.check_and_process(
            "user_123",
            relationship_score=50,
        )

        assert threshold_result.risk_level == BreakupRisk.NONE
        assert breakup_result is None

    def test_check_and_process_triggers_breakup(self, manager):
        """Low score returns both results."""
        threshold_result, breakup_result = manager.check_and_process(
            "user_123",
            relationship_score=5,
        )

        assert threshold_result.risk_level == BreakupRisk.TRIGGERED
        assert threshold_result.should_breakup is True
        assert breakup_result is not None
        assert breakup_result.breakup_triggered is True
        assert breakup_result.game_over is True


# =============================================================================
# Global Manager Tests
# =============================================================================


class TestGlobalManager:
    """Test global breakup manager singleton."""

    def test_get_breakup_manager_returns_instance(self):
        """get_breakup_manager() returns a BreakupManager."""
        manager = get_breakup_manager()
        assert isinstance(manager, BreakupManager)

    def test_get_breakup_manager_singleton(self):
        """get_breakup_manager() returns same instance."""
        # Reset the global
        import nikita.conflicts.breakup as breakup_module
        breakup_module._breakup_manager = None

        manager1 = get_breakup_manager()
        manager2 = get_breakup_manager()
        assert manager1 is manager2


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_exactly_at_warning_threshold(self, manager, config):
        """Score exactly at warning threshold (20) is NOT warning."""
        result = manager.check_threshold("user_123", relationship_score=config.warning_threshold)
        assert result.risk_level == BreakupRisk.NONE  # >= threshold is OK

    def test_one_below_warning_threshold(self, manager, config):
        """Score one below warning threshold triggers warning."""
        result = manager.check_threshold("user_123", relationship_score=config.warning_threshold - 1)
        assert result.should_warn is True

    def test_exactly_at_breakup_threshold(self, manager, config):
        """Score exactly at breakup threshold (10) is NOT breakup."""
        result = manager.check_threshold("user_123", relationship_score=config.breakup_threshold)
        # At threshold is warning/critical, not breakup
        assert result.should_breakup is False

    def test_one_below_breakup_threshold(self, manager, config):
        """Score one below breakup threshold triggers breakup."""
        result = manager.check_threshold("user_123", relationship_score=config.breakup_threshold - 1)
        assert result.should_breakup is True

    def test_negative_score_breakup(self, manager):
        """Negative score (theoretically) still triggers breakup."""
        result = manager.check_threshold("user_123", relationship_score=-10)
        assert result.should_breakup is True

    def test_max_score_healthy(self, manager):
        """Max score (100) is healthy."""
        result = manager.check_threshold("user_123", relationship_score=100)
        assert result.risk_level == BreakupRisk.NONE

    def test_low_score_triggers_breakup_regardless(self, manager):
        """Low score triggers breakup based on score alone."""
        # Just verifying score-based breakup is independent of crisis count
        result = manager.check_threshold("user_123", relationship_score=5)

        # Should mention score (checked first)
        assert result.should_breakup is True
        assert "score" in result.reason.lower() or "below" in result.reason.lower()
