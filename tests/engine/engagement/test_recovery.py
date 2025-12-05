"""Tests for Engagement Recovery System Phase 5.

TDD tests for spec 014 - T5.1 through T5.2.
Tests written FIRST, implementation follows.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from nikita.config.enums import EngagementState


# ==============================================================================
# T5.1: RecoveryManager Tests
# ==============================================================================


class TestRecoveryManagerClass:
    """Tests for RecoveryManager class structure (AC-5.1.1)."""

    def test_ac_5_1_1_class_exists_in_recovery_module(self):
        """AC-5.1.1: RecoveryManager class in recovery.py."""
        from nikita.engine.engagement.recovery import RecoveryManager

        assert RecoveryManager is not None

    def test_recovery_manager_has_get_recovery_action_method(self):
        """RecoveryManager has get_recovery_action() method."""
        from nikita.engine.engagement.recovery import RecoveryManager

        manager = RecoveryManager()
        assert hasattr(manager, "get_recovery_action")
        assert callable(manager.get_recovery_action)


class TestGetRecoveryAction:
    """Tests for get_recovery_action() method (AC-5.1.2, AC-5.1.3, AC-5.1.4)."""

    def test_ac_5_1_2_get_recovery_action_returns_required_action(self):
        """AC-5.1.2: get_recovery_action(state) returns required action."""
        from nikita.engine.engagement.recovery import RecoveryAction, RecoveryManager

        manager = RecoveryManager()
        action = manager.get_recovery_action(EngagementState.CLINGY)

        assert isinstance(action, RecoveryAction)
        assert hasattr(action, "description")
        assert hasattr(action, "duration_hours")

    def test_ac_5_1_3_clingy_recovery_give_space_24h(self):
        """AC-5.1.3: CLINGY recovery: Give space for 24 hours."""
        from nikita.engine.engagement.recovery import RecoveryManager

        manager = RecoveryManager()
        action = manager.get_recovery_action(EngagementState.CLINGY)

        assert "space" in action.description.lower() or "24" in action.description
        assert action.duration_hours == 24

    def test_ac_5_1_4_distant_recovery_engage_12h(self):
        """AC-5.1.4: DISTANT recovery: Engage meaningfully within 12 hours."""
        from nikita.engine.engagement.recovery import RecoveryManager

        manager = RecoveryManager()
        action = manager.get_recovery_action(EngagementState.DISTANT)

        assert "engage" in action.description.lower() or "meaningful" in action.description.lower()
        assert action.duration_hours == 12

    def test_out_of_zone_recovery_action(self):
        """OUT_OF_ZONE has specific recovery action."""
        from nikita.engine.engagement.recovery import RecoveryManager

        manager = RecoveryManager()
        action = manager.get_recovery_action(EngagementState.OUT_OF_ZONE)

        assert action.duration_hours > 0
        assert len(action.description) > 0

    def test_healthy_states_have_no_recovery(self):
        """Healthy states (CALIBRATING, IN_ZONE) return None."""
        from nikita.engine.engagement.recovery import RecoveryManager

        manager = RecoveryManager()

        calibrating_action = manager.get_recovery_action(EngagementState.CALIBRATING)
        in_zone_action = manager.get_recovery_action(EngagementState.IN_ZONE)

        assert calibrating_action is None
        assert in_zone_action is None


class TestCheckRecoveryComplete:
    """Tests for check_recovery_complete() method (AC-5.1.5, AC-5.1.6)."""

    def test_ac_5_1_5_check_recovery_complete_method_exists(self):
        """AC-5.1.5: check_recovery_complete(user_id) validates action taken."""
        from nikita.engine.engagement.recovery import RecoveryManager

        manager = RecoveryManager()
        assert hasattr(manager, "check_recovery_complete")
        assert callable(manager.check_recovery_complete)

    def test_clingy_recovery_complete_after_24h_silence(self):
        """CLINGY recovery complete after 24h without excessive messaging."""
        from nikita.engine.engagement.recovery import RecoveryManager

        manager = RecoveryManager()

        # Simulate user who gave space (low message count in 24h)
        result = manager.check_recovery_complete(
            state=EngagementState.CLINGY,
            recovery_started_at=datetime.now(timezone.utc) - timedelta(hours=25),
            messages_since_recovery=2,
        )

        assert result.is_complete is True

    def test_clingy_recovery_not_complete_if_still_messaging_too_much(self):
        """CLINGY recovery not complete if still messaging excessively."""
        from nikita.engine.engagement.recovery import RecoveryManager

        manager = RecoveryManager()

        # Simulate user who didn't give space (too many messages)
        result = manager.check_recovery_complete(
            state=EngagementState.CLINGY,
            recovery_started_at=datetime.now(timezone.utc) - timedelta(hours=25),
            messages_since_recovery=20,
        )

        assert result.is_complete is False

    def test_distant_recovery_complete_with_meaningful_engagement(self):
        """DISTANT recovery complete with meaningful engagement in 12h."""
        from nikita.engine.engagement.recovery import RecoveryManager

        manager = RecoveryManager()

        # Simulate user who engaged meaningfully
        result = manager.check_recovery_complete(
            state=EngagementState.DISTANT,
            recovery_started_at=datetime.now(timezone.utc) - timedelta(hours=6),
            messages_since_recovery=8,
            avg_message_length=80,
        )

        assert result.is_complete is True

    def test_distant_recovery_not_complete_with_terse_messages(self):
        """DISTANT recovery not complete with only terse messages."""
        from nikita.engine.engagement.recovery import RecoveryManager

        manager = RecoveryManager()

        # Simulate user with only terse messages
        result = manager.check_recovery_complete(
            state=EngagementState.DISTANT,
            recovery_started_at=datetime.now(timezone.utc) - timedelta(hours=6),
            messages_since_recovery=8,
            avg_message_length=10,  # Too short
        )

        assert result.is_complete is False

    def test_ac_5_1_6_grace_period_enforced(self):
        """AC-5.1.6: Grace period enforced before state reset."""
        from nikita.engine.engagement.recovery import RecoveryManager

        manager = RecoveryManager()

        # Recovery started only 2 hours ago (not enough for CLINGY's 24h)
        result = manager.check_recovery_complete(
            state=EngagementState.CLINGY,
            recovery_started_at=datetime.now(timezone.utc) - timedelta(hours=2),
            messages_since_recovery=0,
        )

        assert result.is_complete is False
        assert result.reason == "Grace period not elapsed"


# ==============================================================================
# T5.2: Game Over Triggers Tests
# ==============================================================================


class TestCheckPointOfNoReturn:
    """Tests for game over triggers (AC-5.2.1 through AC-5.2.5)."""

    def test_ac_5_2_1_check_point_of_no_return_method_exists(self):
        """AC-5.2.1: check_point_of_no_return(user_id) method."""
        from nikita.engine.engagement.recovery import RecoveryManager

        manager = RecoveryManager()
        assert hasattr(manager, "check_point_of_no_return")
        assert callable(manager.check_point_of_no_return)

    def test_ac_5_2_2_clingy_7_days_game_over(self):
        """AC-5.2.2: Clingy: 7 consecutive days → GAME_OVER."""
        from nikita.engine.engagement.recovery import GameOverResult, RecoveryManager

        manager = RecoveryManager()

        result = manager.check_point_of_no_return(
            state=EngagementState.CLINGY,
            consecutive_days=7,
        )

        assert isinstance(result, GameOverResult)
        assert result.is_game_over is True
        assert result.reason == "nikita_dumped_clingy"

    def test_clingy_6_days_not_game_over(self):
        """6 consecutive clingy days is not game over yet."""
        from nikita.engine.engagement.recovery import RecoveryManager

        manager = RecoveryManager()

        result = manager.check_point_of_no_return(
            state=EngagementState.CLINGY,
            consecutive_days=6,
        )

        assert result.is_game_over is False

    def test_ac_5_2_3_distant_10_days_game_over(self):
        """AC-5.2.3: Distant: 10 consecutive days → GAME_OVER."""
        from nikita.engine.engagement.recovery import GameOverResult, RecoveryManager

        manager = RecoveryManager()

        result = manager.check_point_of_no_return(
            state=EngagementState.DISTANT,
            consecutive_days=10,
        )

        assert isinstance(result, GameOverResult)
        assert result.is_game_over is True
        assert result.reason == "nikita_dumped_distant"

    def test_distant_9_days_not_game_over(self):
        """9 consecutive distant days is not game over yet."""
        from nikita.engine.engagement.recovery import RecoveryManager

        manager = RecoveryManager()

        result = manager.check_point_of_no_return(
            state=EngagementState.DISTANT,
            consecutive_days=9,
        )

        assert result.is_game_over is False

    def test_out_of_zone_extends_game_over_threshold(self):
        """OUT_OF_ZONE state has its own game over trigger."""
        from nikita.engine.engagement.recovery import RecoveryManager

        manager = RecoveryManager()

        # OUT_OF_ZONE for extended period
        result = manager.check_point_of_no_return(
            state=EngagementState.OUT_OF_ZONE,
            consecutive_days=14,
        )

        # OUT_OF_ZONE has 14 day threshold
        assert result.is_game_over is True

    def test_healthy_states_never_game_over(self):
        """Healthy states never trigger game over."""
        from nikita.engine.engagement.recovery import RecoveryManager

        manager = RecoveryManager()

        # Even with many days, healthy states don't trigger
        result_calibrating = manager.check_point_of_no_return(
            state=EngagementState.CALIBRATING,
            consecutive_days=100,
        )
        result_in_zone = manager.check_point_of_no_return(
            state=EngagementState.IN_ZONE,
            consecutive_days=100,
        )

        assert result_calibrating.is_game_over is False
        assert result_in_zone.is_game_over is False


class TestGameOverResult:
    """Tests for GameOverResult data class."""

    def test_ac_5_2_4_game_over_triggers_status(self):
        """AC-5.2.4: Game over triggers game_status = 'game_over'."""
        from nikita.engine.engagement.recovery import GameOverResult

        result = GameOverResult(
            is_game_over=True,
            reason="nikita_dumped_clingy",
        )

        # Result should include info for setting game_status
        assert result.is_game_over is True
        assert "clingy" in result.reason.lower() or "distant" in result.reason.lower() or "out_of_zone" in result.reason.lower()

    def test_ac_5_2_5_game_over_reason_stored(self):
        """AC-5.2.5: Game over reason stored."""
        from nikita.engine.engagement.recovery import GameOverResult

        clingy_result = GameOverResult(
            is_game_over=True,
            reason="nikita_dumped_clingy",
        )

        distant_result = GameOverResult(
            is_game_over=True,
            reason="nikita_dumped_distant",
        )

        assert clingy_result.reason == "nikita_dumped_clingy"
        assert distant_result.reason == "nikita_dumped_distant"


class TestRecoveryIntegration:
    """Integration tests for recovery system."""

    def test_full_clingy_recovery_flow(self):
        """Full flow: CLINGY → recovery action → check complete → reset."""
        from nikita.engine.engagement.recovery import RecoveryManager

        manager = RecoveryManager()

        # 1. Get recovery action
        action = manager.get_recovery_action(EngagementState.CLINGY)
        assert action.duration_hours == 24

        # 2. User follows advice (gives space)
        result = manager.check_recovery_complete(
            state=EngagementState.CLINGY,
            recovery_started_at=datetime.now(timezone.utc) - timedelta(hours=25),
            messages_since_recovery=2,
        )
        assert result.is_complete is True

    def test_full_distant_recovery_flow(self):
        """Full flow: DISTANT → recovery action → check complete → reset."""
        from nikita.engine.engagement.recovery import RecoveryManager

        manager = RecoveryManager()

        # 1. Get recovery action
        action = manager.get_recovery_action(EngagementState.DISTANT)
        assert action.duration_hours == 12

        # 2. User follows advice (engages meaningfully)
        result = manager.check_recovery_complete(
            state=EngagementState.DISTANT,
            recovery_started_at=datetime.now(timezone.utc) - timedelta(hours=6),
            messages_since_recovery=10,
            avg_message_length=80,
        )
        assert result.is_complete is True

    def test_approaching_game_over_warning(self):
        """Check if approaching game over (5 of 7 clingy days)."""
        from nikita.engine.engagement.recovery import RecoveryManager

        manager = RecoveryManager()

        result = manager.check_point_of_no_return(
            state=EngagementState.CLINGY,
            consecutive_days=5,
        )

        assert result.is_game_over is False
        assert result.days_remaining == 2  # 7 - 5 = 2 days left
