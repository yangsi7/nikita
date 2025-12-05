"""Integration tests for Engagement System (spec 014 Phase 6).

T6.4: Integration tests for full engagement flow.
Tests the complete engagement system working together.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from nikita.config.enums import EngagementState
from nikita.engine.engagement import (
    CalibrationCalculator,
    ClinginessDetector,
    EngagementStateMachine,
    NeglectDetector,
    OptimalFrequencyCalculator,
    RecoveryManager,
    map_score_to_state,
)


# ==============================================================================
# T6.4: Integration Tests
# ==============================================================================


class TestFullMessageFlow:
    """AC-6.4.1: Test full flow: message → metrics → state → multiplier."""

    def test_new_user_calibrating_flow(self):
        """New user starts in CALIBRATING with 0.9x multiplier."""
        # Initialize components
        freq_calc = OptimalFrequencyCalculator()
        calib_calc = CalibrationCalculator()
        state_machine = EngagementStateMachine()

        # User just started - 5 messages, chapter 1, day 0 (Monday)
        chapter = 1
        day_of_week = 0
        actual_messages = 5
        avg_response_seconds = 300  # 5 min
        avg_message_length = 50
        optimal = freq_calc.get_optimal(chapter, day_of_week)

        # Calculate calibration score
        result = calib_calc.compute(
            actual_messages=actual_messages,
            optimal_messages=optimal,
            avg_response_seconds=avg_response_seconds,
            avg_message_length=avg_message_length,
            needy_score=Decimal("0.0"),
            distracted_score=Decimal("0.0"),
        )

        # State should still be CALIBRATING (not enough consecutive scores yet)
        assert state_machine.current_state == EngagementState.CALIBRATING
        assert state_machine.current_multiplier == Decimal("0.9")

    def test_user_reaches_in_zone_after_good_scores(self):
        """User transitions to IN_ZONE after 3 consecutive high scores."""
        state_machine = EngagementStateMachine()
        calib_calc = CalibrationCalculator()
        freq_calc = OptimalFrequencyCalculator()

        chapter = 1
        optimal = freq_calc.get_optimal(chapter, 0)

        # Simulate 3 high-scoring sessions
        for i in range(3):
            result = calib_calc.compute(
                actual_messages=optimal,  # Perfect frequency
                optimal_messages=optimal,
                avg_response_seconds=300,  # 5 min response
                avg_message_length=100,  # Good length
                needy_score=Decimal("0.0"),
                distracted_score=Decimal("0.0"),
            )

            # Should have high score
            assert result.score >= Decimal("0.8"), f"Iteration {i}: score={result.score}"

            state_machine.update(result)

        # After 3 high scores, should be IN_ZONE
        assert state_machine.current_state == EngagementState.IN_ZONE
        assert state_machine.current_multiplier == Decimal("1.0")

    def test_clingy_detection_affects_state(self):
        """Clingy behavior triggers state change with multiplier reduction."""
        state_machine = EngagementStateMachine(initial_state=EngagementState.DRIFTING)
        clingy_detector = ClinginessDetector()
        calib_calc = CalibrationCalculator()
        freq_calc = OptimalFrequencyCalculator()

        chapter = 1
        optimal = freq_calc.get_optimal(chapter, 0)

        # Simulate clingy behavior - messaging way too much
        clingy_result = clingy_detector.detect(
            messages_per_day=optimal * 3,  # 3x optimal
            optimal_frequency=optimal,
            consecutive_messages=5,
            total_exchanges=20,
            avg_response_seconds=10,  # Very fast responses
            user_avg_length=200,
            nikita_avg_length=50,  # Much longer than Nikita
            needy_score=Decimal("0.8"),
            chapter=chapter,
        )

        assert clingy_result.is_clingy is True

        # Simulate 2 clingy days - create proper CalibrationResult
        for day in range(2):
            result = calib_calc.compute(
                actual_messages=optimal * 3,
                optimal_messages=optimal,
                avg_response_seconds=10,
                avg_message_length=200,
                needy_score=Decimal("0.8"),
                distracted_score=Decimal("0.0"),
            )
            state_machine.update(
                result,
                is_clingy=True,
                is_neglecting=False,
                is_new_day=True,
            )

        # Should be CLINGY now
        assert state_machine.current_state == EngagementState.CLINGY
        assert state_machine.current_multiplier == Decimal("0.5")

    def test_neglect_detection_affects_state(self):
        """Neglect behavior triggers DISTANT state."""
        state_machine = EngagementStateMachine(initial_state=EngagementState.DRIFTING)
        neglect_detector = NeglectDetector()
        calib_calc = CalibrationCalculator()
        freq_calc = OptimalFrequencyCalculator()

        chapter = 2
        optimal = freq_calc.get_optimal(chapter, 0)

        # Simulate neglect - barely messaging
        neglect_result = neglect_detector.detect(
            messages_per_day=1,  # Way below optimal
            optimal_frequency=optimal,
            avg_response_seconds=86400,  # 24 hour response time
            avg_message_length=10,  # Very short messages
            abrupt_endings=5,
            total_conversations=10,
            distracted_score=Decimal("0.7"),
            chapter=chapter,
        )

        assert neglect_result.is_neglecting is True

        # Simulate 2 neglectful days
        for day in range(2):
            result = calib_calc.compute(
                actual_messages=1,
                optimal_messages=optimal,
                avg_response_seconds=86400,
                avg_message_length=10,
                needy_score=Decimal("0.0"),
                distracted_score=Decimal("0.7"),
            )
            state_machine.update(
                result,
                is_clingy=False,
                is_neglecting=True,
                is_new_day=True,
            )

        # Should be DISTANT now
        assert state_machine.current_state == EngagementState.DISTANT
        assert state_machine.current_multiplier == Decimal("0.6")


class TestChapterTransitionFlow:
    """AC-6.4.2: Test chapter transition flow."""

    def test_chapter_change_resets_engagement(self):
        """Chapter change resets engagement to CALIBRATING."""
        state_machine = EngagementStateMachine(initial_state=EngagementState.IN_ZONE)

        # User was IN_ZONE with 1.0x multiplier
        assert state_machine.current_state == EngagementState.IN_ZONE
        assert state_machine.current_multiplier == Decimal("1.0")

        # Chapter advances (e.g., from Chapter 1 to 2)
        transition = state_machine.on_chapter_change(new_chapter=2)

        # Should reset to CALIBRATING
        assert transition.from_state == EngagementState.IN_ZONE
        assert transition.to_state == EngagementState.CALIBRATING
        assert state_machine.current_state == EngagementState.CALIBRATING
        assert state_machine.current_multiplier == Decimal("0.9")

    def test_chapter_change_from_clingy_resets(self):
        """Even CLINGY state resets on chapter change."""
        state_machine = EngagementStateMachine(initial_state=EngagementState.CLINGY)

        assert state_machine.current_multiplier == Decimal("0.5")

        transition = state_machine.on_chapter_change(new_chapter=3)

        assert transition.from_state == EngagementState.CLINGY
        assert transition.to_state == EngagementState.CALIBRATING
        assert state_machine.current_multiplier == Decimal("0.9")

    def test_optimal_frequency_changes_per_chapter(self):
        """Optimal frequency decreases as chapters progress."""
        freq_calc = OptimalFrequencyCalculator()

        ch1_optimal = freq_calc.get_optimal(1, 0)  # Chapter 1, Monday
        ch3_optimal = freq_calc.get_optimal(3, 0)  # Chapter 3, Monday
        ch5_optimal = freq_calc.get_optimal(5, 0)  # Chapter 5, Monday

        # Optimal frequency should decrease with relationship maturity
        assert ch1_optimal > ch3_optimal > ch5_optimal


class TestRecoveryFlow:
    """AC-6.4.3: Test recovery flow."""

    def test_full_clingy_recovery_flow(self):
        """Complete flow: CLINGY → recovery action → check → transition."""
        state_machine = EngagementStateMachine(initial_state=EngagementState.CLINGY)
        recovery_manager = RecoveryManager()
        calib_calc = CalibrationCalculator()

        # 1. Get recovery action
        action = recovery_manager.get_recovery_action(EngagementState.CLINGY)
        assert action is not None
        assert action.duration_hours == 24

        # 2. Simulate user gives space (24h elapsed, few messages)
        result = recovery_manager.check_recovery_complete(
            state=EngagementState.CLINGY,
            recovery_started_at=datetime.now(timezone.utc) - timedelta(hours=25),
            messages_since_recovery=3,  # Gave space
        )
        assert result.is_complete is True

        # 3. User demonstrates good behavior for 2 days
        for day in range(2):
            calibration = calib_calc.compute(
                actual_messages=10,
                optimal_messages=15,
                avg_response_seconds=300,
                avg_message_length=60,
                needy_score=Decimal("0.1"),
                distracted_score=Decimal("0.0"),
            )
            state_machine.update(
                calibration,
                is_clingy=False,  # No longer clingy
                is_neglecting=False,
                is_new_day=True,
            )

        # Should transition to DRIFTING
        assert state_machine.current_state == EngagementState.DRIFTING

    def test_out_of_zone_recovery_to_calibrating(self):
        """OUT_OF_ZONE recovers back to CALIBRATING."""
        state_machine = EngagementStateMachine(initial_state=EngagementState.OUT_OF_ZONE)
        recovery_manager = RecoveryManager()
        calib_calc = CalibrationCalculator()

        # Check recovery (needs 48h and good engagement)
        result = recovery_manager.check_recovery_complete(
            state=EngagementState.OUT_OF_ZONE,
            recovery_started_at=datetime.now(timezone.utc) - timedelta(hours=50),
            messages_since_recovery=15,  # Good volume
            avg_message_length=60,  # Good quality
        )
        assert result.is_complete is True

        # Trigger recovery complete in state machine
        calibration = calib_calc.compute(
            actual_messages=10,
            optimal_messages=15,
            avg_response_seconds=300,
            avg_message_length=60,
            needy_score=Decimal("0.0"),
            distracted_score=Decimal("0.0"),
        )
        transition = state_machine.update(
            calibration,
            is_clingy=False,
            is_neglecting=False,
            is_new_day=True,
            recovery_complete=True,
        )

        assert transition is not None
        assert transition.to_state == EngagementState.CALIBRATING
        assert state_machine.current_state == EngagementState.CALIBRATING


class TestMultiDaySimulation:
    """AC-6.4.4: Test multi-day simulation."""

    def test_week_of_good_engagement(self):
        """Simulate a week of good engagement - reach IN_ZONE."""
        state_machine = EngagementStateMachine()
        freq_calc = OptimalFrequencyCalculator()
        calib_calc = CalibrationCalculator()

        chapter = 1

        # Simulate 7 days of good engagement
        for day in range(7):
            day_of_week = day % 7
            optimal = freq_calc.get_optimal(chapter, day_of_week)

            result = calib_calc.compute(
                actual_messages=optimal,
                optimal_messages=optimal,
                avg_response_seconds=300,
                avg_message_length=80,
                needy_score=Decimal("0.1"),
                distracted_score=Decimal("0.1"),
            )

            state_machine.update(
                result,
                is_clingy=False,
                is_neglecting=False,
                is_new_day=True,
            )

        # After a week of good engagement, should be IN_ZONE
        assert state_machine.current_state == EngagementState.IN_ZONE

    def test_week_of_clingy_behavior_triggers_game_over_warning(self):
        """5 consecutive clingy days triggers warning (7 = game over)."""
        # Start directly in CLINGY to test consecutive day counting
        state_machine = EngagementStateMachine(initial_state=EngagementState.CLINGY)
        recovery_manager = RecoveryManager()

        # We need to track consecutive clingy days manually (as would be done in the service layer)
        consecutive_clingy_days = 5  # Simulate 5 days in CLINGY state

        # Check game over warning
        game_over = recovery_manager.check_point_of_no_return(
            state=EngagementState.CLINGY,
            consecutive_days=consecutive_clingy_days,
        )

        # Should have warning (2 days remaining until game over)
        assert game_over.is_game_over is False
        assert game_over.days_remaining == 2  # 7 - 5 = 2

    def test_gradual_score_decline_simulation(self):
        """Simulate gradual decline: IN_ZONE → DRIFTING → recovery."""
        state_machine = EngagementStateMachine()
        calib_calc = CalibrationCalculator()

        # Phase 1: Get to IN_ZONE with 3 high scores
        for i in range(3):
            result = calib_calc.compute(
                actual_messages=15,
                optimal_messages=15,
                avg_response_seconds=300,
                avg_message_length=100,
                needy_score=Decimal("0.0"),
                distracted_score=Decimal("0.0"),
            )
            state_machine.update(result)

        assert state_machine.current_state == EngagementState.IN_ZONE

        # Phase 2: Score drops - transition to DRIFTING
        result = calib_calc.compute(
            actual_messages=3,  # Low engagement
            optimal_messages=15,
            avg_response_seconds=3600,  # Slow response
            avg_message_length=20,  # Short messages
            needy_score=Decimal("0.0"),
            distracted_score=Decimal("0.5"),
        )
        transition = state_machine.update(result)

        assert transition is not None
        assert transition.to_state == EngagementState.DRIFTING
        assert state_machine.current_state == EngagementState.DRIFTING

        # Phase 3: Recovery with 2 consecutive high scores
        for i in range(2):
            result = calib_calc.compute(
                actual_messages=12,
                optimal_messages=15,
                avg_response_seconds=300,
                avg_message_length=80,
                needy_score=Decimal("0.1"),
                distracted_score=Decimal("0.1"),
            )
            state_machine.update(result)

        # Should be back IN_ZONE
        assert state_machine.current_state == EngagementState.IN_ZONE

    def test_transition_history_captures_journey(self):
        """Verify transition history captures full journey."""
        state_machine = EngagementStateMachine()
        calib_calc = CalibrationCalculator()

        # CALIBRATING → IN_ZONE
        for i in range(3):
            result = calib_calc.compute(
                actual_messages=15, optimal_messages=15,
                avg_response_seconds=300, avg_message_length=100,
                needy_score=Decimal("0.0"), distracted_score=Decimal("0.0"),
            )
            state_machine.update(result)

        # IN_ZONE → DRIFTING
        result = calib_calc.compute(
            actual_messages=3, optimal_messages=15,
            avg_response_seconds=3600, avg_message_length=20,
            needy_score=Decimal("0.0"), distracted_score=Decimal("0.5"),
        )
        state_machine.update(result)

        # DRIFTING → IN_ZONE
        for i in range(2):
            result = calib_calc.compute(
                actual_messages=12, optimal_messages=15,
                avg_response_seconds=300, avg_message_length=80,
                needy_score=Decimal("0.1"), distracted_score=Decimal("0.1"),
            )
            state_machine.update(result)

        history = state_machine.get_history()

        # Should have 3 transitions
        assert len(history) == 3
        assert history[0].from_state == EngagementState.CALIBRATING
        assert history[0].to_state == EngagementState.IN_ZONE
        assert history[1].from_state == EngagementState.IN_ZONE
        assert history[1].to_state == EngagementState.DRIFTING
        assert history[2].from_state == EngagementState.DRIFTING
        assert history[2].to_state == EngagementState.IN_ZONE


class TestMapScoreToState:
    """Test the map_score_to_state helper function integration.

    Note: map_score_to_state prioritizes score first. Clingy/neglecting flags
    only affect the result in the 0.3-0.5 score range. The state machine
    handles flag-based transitions independently.
    """

    def test_high_score_maps_to_in_zone(self):
        """High score without clingy/neglect → IN_ZONE."""
        state = map_score_to_state(
            score=Decimal("0.85"),
            is_clingy=False,
            is_neglecting=False,
        )
        assert state == EngagementState.IN_ZONE

    def test_clingy_flag_with_low_score_maps_to_clingy(self):
        """Clingy flag with score 0.3-0.5 → CLINGY."""
        state = map_score_to_state(
            score=Decimal("0.4"),  # Low score in range
            is_clingy=True,  # Clingy flag
            is_neglecting=False,
        )
        assert state == EngagementState.CLINGY

    def test_neglecting_flag_with_low_score_maps_to_distant(self):
        """Neglecting flag with score 0.3-0.5 → DISTANT."""
        state = map_score_to_state(
            score=Decimal("0.4"),  # Low score in range
            is_clingy=False,
            is_neglecting=True,  # Neglecting flag
        )
        assert state == EngagementState.DISTANT

    def test_mid_score_maps_to_drifting(self):
        """Mid score without flags → DRIFTING."""
        state = map_score_to_state(
            score=Decimal("0.65"),  # Mid range score
            is_clingy=False,
            is_neglecting=False,
        )
        assert state == EngagementState.DRIFTING

    def test_very_low_score_maps_to_out_of_zone(self):
        """Very low score → OUT_OF_ZONE."""
        state = map_score_to_state(
            score=Decimal("0.25"),  # Below 0.3
            is_clingy=False,
            is_neglecting=False,
        )
        assert state == EngagementState.OUT_OF_ZONE
