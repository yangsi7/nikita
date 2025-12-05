"""Tests for Engagement State Machine Phase 4.

TDD tests for spec 014 - T4.1 through T4.3.
Tests written FIRST, implementation follows.
"""

from decimal import Decimal
from uuid import uuid4

import pytest

from nikita.config.enums import EngagementState
from nikita.engine.engagement.models import CalibrationResult, StateTransition


# ==============================================================================
# T4.1: EngagementStateMachine Tests
# ==============================================================================


class TestEngagementStateMachineClass:
    """Tests for EngagementStateMachine class structure (AC-4.1.1)."""

    def test_ac_4_1_1_class_exists_in_state_machine_module(self):
        """AC-4.1.1: EngagementStateMachine class in state_machine.py."""
        from nikita.engine.engagement.state_machine import EngagementStateMachine

        assert EngagementStateMachine is not None

    def test_state_machine_has_update_method(self):
        """EngagementStateMachine has update() method."""
        from nikita.engine.engagement.state_machine import EngagementStateMachine

        sm = EngagementStateMachine()
        assert hasattr(sm, "update")
        assert callable(sm.update)


class TestCurrentStateProperty:
    """Tests for current_state property (AC-4.1.3)."""

    def test_ac_4_1_3_current_state_property(self):
        """AC-4.1.3: current_state property returns EngagementState."""
        from nikita.engine.engagement.state_machine import EngagementStateMachine

        sm = EngagementStateMachine()
        assert hasattr(sm, "current_state")
        assert isinstance(sm.current_state, EngagementState)

    def test_default_state_is_calibrating(self):
        """Default state is CALIBRATING."""
        from nikita.engine.engagement.state_machine import EngagementStateMachine

        sm = EngagementStateMachine()
        assert sm.current_state == EngagementState.CALIBRATING


class TestCurrentMultiplierProperty:
    """Tests for current_multiplier property (AC-4.1.4)."""

    def test_ac_4_1_4_current_multiplier_property(self):
        """AC-4.1.4: current_multiplier property returns Decimal."""
        from nikita.engine.engagement.state_machine import EngagementStateMachine

        sm = EngagementStateMachine()
        assert hasattr(sm, "current_multiplier")
        assert isinstance(sm.current_multiplier, Decimal)

    def test_calibrating_multiplier_is_0_9(self):
        """CALIBRATING state has multiplier 0.9."""
        from nikita.engine.engagement.state_machine import EngagementStateMachine

        sm = EngagementStateMachine()
        assert sm.current_multiplier == Decimal("0.9")


class TestUpdateMethod:
    """Tests for update() method (AC-4.1.5)."""

    def test_ac_4_1_5_update_evaluates_transitions(self):
        """AC-4.1.5: update(calibration_result) evaluates transitions."""
        from nikita.engine.engagement.state_machine import EngagementStateMachine

        sm = EngagementStateMachine()

        # High score should potentially transition
        result = CalibrationResult(
            score=Decimal("0.85"),
            frequency_component=Decimal("0.9"),
            timing_component=Decimal("0.8"),
            content_component=Decimal("0.85"),
            suggested_state=EngagementState.IN_ZONE,
        )

        transition = sm.update(result)

        # Should return StateTransition or None
        assert transition is None or isinstance(transition, StateTransition)

    def test_update_returns_transition_when_state_changes(self):
        """update() returns StateTransition when state changes."""
        from nikita.engine.engagement.state_machine import EngagementStateMachine

        sm = EngagementStateMachine()

        # Simulate 3+ consecutive high scores to trigger transition
        high_result = CalibrationResult(
            score=Decimal("0.85"),
            frequency_component=Decimal("0.9"),
            timing_component=Decimal("0.8"),
            content_component=Decimal("0.85"),
            suggested_state=EngagementState.IN_ZONE,
        )

        # First few updates build up consecutive count
        sm.update(high_result)
        sm.update(high_result)
        transition = sm.update(high_result)  # Should trigger on 3rd

        if transition:
            assert isinstance(transition, StateTransition)
            assert transition.from_state == EngagementState.CALIBRATING
            assert transition.to_state == EngagementState.IN_ZONE


# ==============================================================================
# T4.2: Transition Rules Tests
# ==============================================================================


class TestCalibratingToInZone:
    """Tests for CALIBRATING → IN_ZONE transition (AC-4.2.1)."""

    def test_ac_4_2_1_calibrating_to_in_zone_after_3_consecutive(self):
        """AC-4.2.1: CALIBRATING → IN_ZONE: score >= 0.8 for 3+ consecutive."""
        from nikita.engine.engagement.state_machine import EngagementStateMachine

        sm = EngagementStateMachine()
        assert sm.current_state == EngagementState.CALIBRATING

        high_result = CalibrationResult(
            score=Decimal("0.85"),
            frequency_component=Decimal("0.9"),
            timing_component=Decimal("0.85"),
            content_component=Decimal("0.8"),
            suggested_state=EngagementState.IN_ZONE,
        )

        # Need 3 consecutive high scores
        sm.update(high_result)
        assert sm.current_state == EngagementState.CALIBRATING  # Not yet
        sm.update(high_result)
        assert sm.current_state == EngagementState.CALIBRATING  # Not yet
        sm.update(high_result)
        assert sm.current_state == EngagementState.IN_ZONE  # Now!


class TestCalibratingToDrifting:
    """Tests for CALIBRATING → DRIFTING transition (AC-4.2.2)."""

    def test_ac_4_2_2_calibrating_to_drifting_after_2_low_scores(self):
        """AC-4.2.2: CALIBRATING → DRIFTING: score < 0.5 for 2+ consecutive."""
        from nikita.engine.engagement.state_machine import EngagementStateMachine

        sm = EngagementStateMachine()

        low_result = CalibrationResult(
            score=Decimal("0.4"),
            frequency_component=Decimal("0.3"),
            timing_component=Decimal("0.4"),
            content_component=Decimal("0.5"),
            suggested_state=EngagementState.DRIFTING,
        )

        sm.update(low_result)
        assert sm.current_state == EngagementState.CALIBRATING  # Not yet
        sm.update(low_result)
        assert sm.current_state == EngagementState.DRIFTING  # Now!


class TestInZoneToDrifting:
    """Tests for IN_ZONE → DRIFTING transition (AC-4.2.3)."""

    def test_ac_4_2_3_in_zone_to_drifting_on_low_score(self):
        """AC-4.2.3: IN_ZONE → DRIFTING: score < 0.6 for 1+ exchange."""
        from nikita.engine.engagement.state_machine import EngagementStateMachine

        sm = EngagementStateMachine(initial_state=EngagementState.IN_ZONE)

        low_result = CalibrationResult(
            score=Decimal("0.5"),
            frequency_component=Decimal("0.4"),
            timing_component=Decimal("0.5"),
            content_component=Decimal("0.6"),
            suggested_state=EngagementState.DRIFTING,
        )

        sm.update(low_result)
        assert sm.current_state == EngagementState.DRIFTING


class TestDriftingToInZone:
    """Tests for DRIFTING → IN_ZONE transition (AC-4.2.4)."""

    def test_ac_4_2_4_drifting_to_in_zone_after_2_high_scores(self):
        """AC-4.2.4: DRIFTING → IN_ZONE: score >= 0.7 for 2+ exchanges."""
        from nikita.engine.engagement.state_machine import EngagementStateMachine

        sm = EngagementStateMachine(initial_state=EngagementState.DRIFTING)

        high_result = CalibrationResult(
            score=Decimal("0.75"),
            frequency_component=Decimal("0.8"),
            timing_component=Decimal("0.7"),
            content_component=Decimal("0.75"),
            suggested_state=EngagementState.IN_ZONE,
        )

        sm.update(high_result)
        assert sm.current_state == EngagementState.DRIFTING  # Not yet
        sm.update(high_result)
        assert sm.current_state == EngagementState.IN_ZONE  # Now!


class TestDriftingToClingy:
    """Tests for DRIFTING → CLINGY transition (AC-4.2.5)."""

    def test_ac_4_2_5_drifting_to_clingy_after_2_days(self):
        """AC-4.2.5: DRIFTING → CLINGY: clinginess > 0.7 for 2+ days."""
        from nikita.engine.engagement.state_machine import EngagementStateMachine

        sm = EngagementStateMachine(initial_state=EngagementState.DRIFTING)

        clingy_result = CalibrationResult(
            score=Decimal("0.4"),
            frequency_component=Decimal("0.3"),
            timing_component=Decimal("0.4"),
            content_component=Decimal("0.5"),
            suggested_state=EngagementState.CLINGY,
        )

        # Simulate 2 days of clingy behavior
        sm.update(clingy_result, is_clingy=True, is_new_day=True)
        assert sm.current_state == EngagementState.DRIFTING  # Day 1
        sm.update(clingy_result, is_clingy=True, is_new_day=True)
        assert sm.current_state == EngagementState.CLINGY  # Day 2


class TestDriftingToDistant:
    """Tests for DRIFTING → DISTANT transition (AC-4.2.6)."""

    def test_ac_4_2_6_drifting_to_distant_after_2_days(self):
        """AC-4.2.6: DRIFTING → DISTANT: neglect > 0.6 for 2+ days."""
        from nikita.engine.engagement.state_machine import EngagementStateMachine

        sm = EngagementStateMachine(initial_state=EngagementState.DRIFTING)

        neglect_result = CalibrationResult(
            score=Decimal("0.4"),
            frequency_component=Decimal("0.3"),
            timing_component=Decimal("0.4"),
            content_component=Decimal("0.5"),
            suggested_state=EngagementState.DISTANT,
        )

        # Simulate 2 days of neglect
        sm.update(neglect_result, is_neglecting=True, is_new_day=True)
        assert sm.current_state == EngagementState.DRIFTING  # Day 1
        sm.update(neglect_result, is_neglecting=True, is_new_day=True)
        assert sm.current_state == EngagementState.DISTANT  # Day 2


class TestClingyToDrifting:
    """Tests for CLINGY → DRIFTING transition (AC-4.2.7)."""

    def test_ac_4_2_7_clingy_to_drifting_after_2_good_days(self):
        """AC-4.2.7: CLINGY → DRIFTING: clinginess < 0.5 for 2+ days."""
        from nikita.engine.engagement.state_machine import EngagementStateMachine

        sm = EngagementStateMachine(initial_state=EngagementState.CLINGY)

        better_result = CalibrationResult(
            score=Decimal("0.6"),
            frequency_component=Decimal("0.6"),
            timing_component=Decimal("0.6"),
            content_component=Decimal("0.6"),
            suggested_state=EngagementState.DRIFTING,
        )

        # Simulate 2 days of better behavior
        sm.update(better_result, is_clingy=False, is_new_day=True)
        assert sm.current_state == EngagementState.CLINGY  # Day 1
        sm.update(better_result, is_clingy=False, is_new_day=True)
        assert sm.current_state == EngagementState.DRIFTING  # Day 2


class TestClingyToOutOfZone:
    """Tests for CLINGY → OUT_OF_ZONE transition (AC-4.2.8)."""

    def test_ac_4_2_8_clingy_to_out_of_zone_after_3_days(self):
        """AC-4.2.8: CLINGY → OUT_OF_ZONE: clingy 3+ consecutive days."""
        from nikita.engine.engagement.state_machine import EngagementStateMachine

        sm = EngagementStateMachine(initial_state=EngagementState.CLINGY)

        clingy_result = CalibrationResult(
            score=Decimal("0.3"),
            frequency_component=Decimal("0.2"),
            timing_component=Decimal("0.3"),
            content_component=Decimal("0.4"),
            suggested_state=EngagementState.CLINGY,
        )

        # 3 consecutive clingy days
        sm.update(clingy_result, is_clingy=True, is_new_day=True)
        assert sm.current_state == EngagementState.CLINGY  # Day 1
        sm.update(clingy_result, is_clingy=True, is_new_day=True)
        assert sm.current_state == EngagementState.CLINGY  # Day 2
        sm.update(clingy_result, is_clingy=True, is_new_day=True)
        assert sm.current_state == EngagementState.OUT_OF_ZONE  # Day 3


class TestDistantToDrifting:
    """Tests for DISTANT → DRIFTING transition (AC-4.2.9)."""

    def test_ac_4_2_9_distant_to_drifting_after_1_day(self):
        """AC-4.2.9: DISTANT → DRIFTING: neglect < 0.4 for 1+ day."""
        from nikita.engine.engagement.state_machine import EngagementStateMachine

        sm = EngagementStateMachine(initial_state=EngagementState.DISTANT)

        better_result = CalibrationResult(
            score=Decimal("0.6"),
            frequency_component=Decimal("0.6"),
            timing_component=Decimal("0.6"),
            content_component=Decimal("0.6"),
            suggested_state=EngagementState.DRIFTING,
        )

        sm.update(better_result, is_neglecting=False, is_new_day=True)
        assert sm.current_state == EngagementState.DRIFTING


class TestDistantToOutOfZone:
    """Tests for DISTANT → OUT_OF_ZONE transition (AC-4.2.10)."""

    def test_ac_4_2_10_distant_to_out_of_zone_after_5_days(self):
        """AC-4.2.10: DISTANT → OUT_OF_ZONE: distant 5+ consecutive days."""
        from nikita.engine.engagement.state_machine import EngagementStateMachine

        sm = EngagementStateMachine(initial_state=EngagementState.DISTANT)

        distant_result = CalibrationResult(
            score=Decimal("0.3"),
            frequency_component=Decimal("0.2"),
            timing_component=Decimal("0.3"),
            content_component=Decimal("0.4"),
            suggested_state=EngagementState.DISTANT,
        )

        for day in range(4):
            sm.update(distant_result, is_neglecting=True, is_new_day=True)
            assert sm.current_state == EngagementState.DISTANT

        sm.update(distant_result, is_neglecting=True, is_new_day=True)
        assert sm.current_state == EngagementState.OUT_OF_ZONE  # Day 5


class TestOutOfZoneToCalibrating:
    """Tests for OUT_OF_ZONE → CALIBRATING transition (AC-4.2.11)."""

    def test_ac_4_2_11_out_of_zone_to_calibrating_on_recovery(self):
        """AC-4.2.11: OUT_OF_ZONE → CALIBRATING: recovery + grace period."""
        from nikita.engine.engagement.state_machine import EngagementStateMachine

        sm = EngagementStateMachine(initial_state=EngagementState.OUT_OF_ZONE)

        recovery_result = CalibrationResult(
            score=Decimal("0.6"),
            frequency_component=Decimal("0.6"),
            timing_component=Decimal("0.6"),
            content_component=Decimal("0.6"),
            suggested_state=EngagementState.CALIBRATING,
        )

        sm.update(recovery_result, recovery_complete=True)
        assert sm.current_state == EngagementState.CALIBRATING


class TestTransitionLogging:
    """Tests for transition logging (AC-4.2.12)."""

    def test_ac_4_2_12_transitions_return_state_transition(self):
        """AC-4.2.12: Each transition returns StateTransition for logging."""
        from nikita.engine.engagement.state_machine import EngagementStateMachine

        sm = EngagementStateMachine(initial_state=EngagementState.IN_ZONE)

        low_result = CalibrationResult(
            score=Decimal("0.5"),
            frequency_component=Decimal("0.4"),
            timing_component=Decimal("0.5"),
            content_component=Decimal("0.6"),
            suggested_state=EngagementState.DRIFTING,
        )

        transition = sm.update(low_result)

        assert transition is not None
        assert isinstance(transition, StateTransition)
        assert transition.from_state == EngagementState.IN_ZONE
        assert transition.to_state == EngagementState.DRIFTING
        assert len(transition.reason) > 0


# ==============================================================================
# T4.3: Chapter Reset Tests
# ==============================================================================


class TestChapterReset:
    """Tests for chapter reset behavior (AC-4.3.1 through AC-4.3.6)."""

    def test_ac_4_3_1_on_chapter_change_method_exists(self):
        """AC-4.3.1: on_chapter_change(new_chapter) method defined."""
        from nikita.engine.engagement.state_machine import EngagementStateMachine

        sm = EngagementStateMachine()
        assert hasattr(sm, "on_chapter_change")
        assert callable(sm.on_chapter_change)

    def test_ac_4_3_2_state_reset_to_calibrating(self):
        """AC-4.3.2: State reset to CALIBRATING on chapter change."""
        from nikita.engine.engagement.state_machine import EngagementStateMachine

        sm = EngagementStateMachine(initial_state=EngagementState.IN_ZONE)
        sm.on_chapter_change(new_chapter=2)

        assert sm.current_state == EngagementState.CALIBRATING

    def test_ac_4_3_3_consecutive_counters_reset(self):
        """AC-4.3.3: Consecutive counters reset to 0."""
        from nikita.engine.engagement.state_machine import EngagementStateMachine

        sm = EngagementStateMachine(initial_state=EngagementState.IN_ZONE)
        sm._consecutive_in_zone = 5
        sm._consecutive_clingy_days = 2

        sm.on_chapter_change(new_chapter=2)

        assert sm._consecutive_in_zone == 0
        assert sm._consecutive_clingy_days == 0

    def test_ac_4_3_4_multiplier_set_to_0_9(self):
        """AC-4.3.4: Multiplier set to 0.9 (calibrating default)."""
        from nikita.engine.engagement.state_machine import EngagementStateMachine

        sm = EngagementStateMachine(initial_state=EngagementState.IN_ZONE)
        sm.on_chapter_change(new_chapter=2)

        assert sm.current_multiplier == Decimal("0.9")

    def test_chapter_change_returns_transition(self):
        """Chapter change returns StateTransition for history."""
        from nikita.engine.engagement.state_machine import EngagementStateMachine

        sm = EngagementStateMachine(initial_state=EngagementState.IN_ZONE)
        transition = sm.on_chapter_change(new_chapter=2)

        assert isinstance(transition, StateTransition)
        assert transition.from_state == EngagementState.IN_ZONE
        assert transition.to_state == EngagementState.CALIBRATING
        assert "chapter" in transition.reason.lower()


class TestTransitionHistory:
    """Tests for transition history tracking."""

    def test_get_history_returns_list(self):
        """get_history() returns list of StateTransitions."""
        from nikita.engine.engagement.state_machine import EngagementStateMachine

        sm = EngagementStateMachine()
        history = sm.get_history()

        assert isinstance(history, list)

    def test_history_captures_transitions(self):
        """History captures all state transitions."""
        from nikita.engine.engagement.state_machine import EngagementStateMachine

        sm = EngagementStateMachine(initial_state=EngagementState.IN_ZONE)

        low_result = CalibrationResult(
            score=Decimal("0.5"),
            frequency_component=Decimal("0.4"),
            timing_component=Decimal("0.5"),
            content_component=Decimal("0.6"),
            suggested_state=EngagementState.DRIFTING,
        )

        sm.update(low_result)
        history = sm.get_history()

        assert len(history) == 1
        assert history[0].from_state == EngagementState.IN_ZONE
        assert history[0].to_state == EngagementState.DRIFTING
