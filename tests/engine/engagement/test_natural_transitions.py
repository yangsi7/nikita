"""Integration tests for engagement state natural transitions (GH #147).

Tests multi-step score-based journeys through the FSM via evaluate/update(),
verifying that transition history accumulates correctly across a full journey.

Covers:
- CALIBRATING -> IN_ZONE (score enters zone)
- IN_ZONE -> DRIFTING (score starts declining)
- DRIFTING -> OUT_OF_ZONE (score drops below threshold)
- OUT_OF_ZONE -> IN_ZONE (score recovers via CALIBRATING)
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from nikita.config.enums import EngagementState
from nikita.engine.engagement.models import CalibrationResult, StateTransition
from nikita.engine.engagement.state_machine import EngagementStateMachine


def _make_result(score: str, suggested: EngagementState) -> CalibrationResult:
    """Helper to build a CalibrationResult with uniform components."""
    s = Decimal(score)
    return CalibrationResult(
        score=s,
        frequency_component=s,
        timing_component=s,
        content_component=s,
        suggested_state=suggested,
    )


# ============================================================================
# Full journey: CALIBRATING → IN_ZONE → DRIFTING → OUT_OF_ZONE → CALIBRATING → IN_ZONE
# ============================================================================


class TestFullNaturalJourney:
    """End-to-end journey through the 6-state FSM using score-based transitions."""

    def test_calibrating_to_in_zone_via_consecutive_high_scores(self):
        """CALIBRATING -> IN_ZONE requires 3+ consecutive scores >= 0.8."""
        sm = EngagementStateMachine()
        high = _make_result("0.85", EngagementState.IN_ZONE)

        # First two high scores: still calibrating
        assert sm.update(high) is None
        assert sm.current_state == EngagementState.CALIBRATING
        assert sm.update(high) is None
        assert sm.current_state == EngagementState.CALIBRATING

        # Third consecutive high score: transition fires
        transition = sm.update(high)
        assert transition is not None
        assert transition.from_state == EngagementState.CALIBRATING
        assert transition.to_state == EngagementState.IN_ZONE
        assert sm.current_state == EngagementState.IN_ZONE

    def test_in_zone_to_drifting_on_single_low_score(self):
        """IN_ZONE -> DRIFTING on a single score < 0.6."""
        sm = EngagementStateMachine(initial_state=EngagementState.IN_ZONE)
        low = _make_result("0.55", EngagementState.DRIFTING)

        transition = sm.update(low)
        assert transition is not None
        assert transition.from_state == EngagementState.IN_ZONE
        assert transition.to_state == EngagementState.DRIFTING
        assert sm.current_state == EngagementState.DRIFTING

    def test_drifting_to_in_zone_via_recovery(self):
        """DRIFTING -> IN_ZONE requires 2+ consecutive scores >= 0.7."""
        sm = EngagementStateMachine(initial_state=EngagementState.DRIFTING)
        recovery = _make_result("0.75", EngagementState.IN_ZONE)

        # First recovery score: still drifting
        assert sm.update(recovery) is None
        assert sm.current_state == EngagementState.DRIFTING

        # Second consecutive recovery: transition fires
        transition = sm.update(recovery)
        assert transition is not None
        assert transition.from_state == EngagementState.DRIFTING
        assert transition.to_state == EngagementState.IN_ZONE

    def test_drifting_to_out_of_zone_via_distant(self):
        """DRIFTING -> DISTANT -> OUT_OF_ZONE via prolonged neglect."""
        sm = EngagementStateMachine(initial_state=EngagementState.DRIFTING)
        low = _make_result("0.35", EngagementState.DISTANT)

        # 2 consecutive days of neglect: DRIFTING -> DISTANT
        sm.update(low, is_neglecting=True, is_new_day=True)
        assert sm.current_state == EngagementState.DRIFTING
        sm.update(low, is_neglecting=True, is_new_day=True)
        assert sm.current_state == EngagementState.DISTANT

        # 5 more consecutive distant days: DISTANT -> OUT_OF_ZONE
        for _ in range(4):
            sm.update(low, is_neglecting=True, is_new_day=True)
            assert sm.current_state == EngagementState.DISTANT
        sm.update(low, is_neglecting=True, is_new_day=True)
        assert sm.current_state == EngagementState.OUT_OF_ZONE

    def test_out_of_zone_to_in_zone_via_recovery_and_calibration(self):
        """OUT_OF_ZONE -> CALIBRATING (recovery) -> IN_ZONE (3 high scores)."""
        sm = EngagementStateMachine(initial_state=EngagementState.OUT_OF_ZONE)
        recovery = _make_result("0.65", EngagementState.CALIBRATING)
        high = _make_result("0.85", EngagementState.IN_ZONE)

        # Recovery complete: OUT_OF_ZONE -> CALIBRATING
        transition = sm.update(recovery, recovery_complete=True)
        assert transition is not None
        assert transition.from_state == EngagementState.OUT_OF_ZONE
        assert transition.to_state == EngagementState.CALIBRATING
        assert sm.current_state == EngagementState.CALIBRATING

        # 3 consecutive high scores: CALIBRATING -> IN_ZONE
        sm.update(high)
        sm.update(high)
        transition = sm.update(high)
        assert transition is not None
        assert transition.to_state == EngagementState.IN_ZONE
        assert sm.current_state == EngagementState.IN_ZONE

    def test_full_round_trip_journey(self):
        """Complete journey: CALIBRATING->IN_ZONE->DRIFTING->DISTANT->OUT_OF_ZONE->CALIBRATING->IN_ZONE."""
        sm = EngagementStateMachine()

        # Phase 1: CALIBRATING -> IN_ZONE (3 high scores)
        high = _make_result("0.85", EngagementState.IN_ZONE)
        sm.update(high)
        sm.update(high)
        sm.update(high)
        assert sm.current_state == EngagementState.IN_ZONE

        # Phase 2: IN_ZONE -> DRIFTING (1 low score)
        low = _make_result("0.45", EngagementState.DRIFTING)
        sm.update(low)
        assert sm.current_state == EngagementState.DRIFTING

        # Phase 3: DRIFTING -> DISTANT (2 days neglect)
        neglect = _make_result("0.35", EngagementState.DISTANT)
        sm.update(neglect, is_neglecting=True, is_new_day=True)
        sm.update(neglect, is_neglecting=True, is_new_day=True)
        assert sm.current_state == EngagementState.DISTANT

        # Phase 4: DISTANT -> OUT_OF_ZONE (5 days neglect)
        for _ in range(5):
            sm.update(neglect, is_neglecting=True, is_new_day=True)
        assert sm.current_state == EngagementState.OUT_OF_ZONE

        # Phase 5: OUT_OF_ZONE -> CALIBRATING (recovery)
        recovery = _make_result("0.60", EngagementState.CALIBRATING)
        sm.update(recovery, recovery_complete=True)
        assert sm.current_state == EngagementState.CALIBRATING

        # Phase 6: CALIBRATING -> IN_ZONE (3 high scores)
        sm.update(high)
        sm.update(high)
        sm.update(high)
        assert sm.current_state == EngagementState.IN_ZONE

        # Verify full history captured all transitions
        history = sm.get_history()
        assert len(history) == 6

        expected_path = [
            (EngagementState.CALIBRATING, EngagementState.IN_ZONE),
            (EngagementState.IN_ZONE, EngagementState.DRIFTING),
            (EngagementState.DRIFTING, EngagementState.DISTANT),
            (EngagementState.DISTANT, EngagementState.OUT_OF_ZONE),
            (EngagementState.OUT_OF_ZONE, EngagementState.CALIBRATING),
            (EngagementState.CALIBRATING, EngagementState.IN_ZONE),
        ]
        for i, (from_s, to_s) in enumerate(expected_path):
            assert history[i].from_state == from_s, f"history[{i}].from_state"
            assert history[i].to_state == to_s, f"history[{i}].to_state"


# ============================================================================
# Transition history recording
# ============================================================================


class TestTransitionHistoryRecording:
    """Verify transition history is recorded with correct metadata."""

    def test_history_records_calibration_score(self):
        """Each transition records the calibration score at time of transition."""
        sm = EngagementStateMachine(initial_state=EngagementState.IN_ZONE)
        low = _make_result("0.55", EngagementState.DRIFTING)

        transition = sm.update(low)
        assert transition is not None
        assert transition.calibration_score == Decimal("0.55")

    def test_history_records_reason_string(self):
        """Each transition includes a human-readable reason."""
        sm = EngagementStateMachine(initial_state=EngagementState.IN_ZONE)
        low = _make_result("0.50", EngagementState.DRIFTING)

        transition = sm.update(low)
        assert transition is not None
        assert isinstance(transition.reason, str)
        assert len(transition.reason) > 0

    def test_no_transition_returns_none(self):
        """When score stays in range, update returns None (no transition)."""
        sm = EngagementStateMachine(initial_state=EngagementState.IN_ZONE)
        # Score 0.65 is >= 0.6 threshold, so no drift
        ok = _make_result("0.65", EngagementState.IN_ZONE)

        result = sm.update(ok)
        assert result is None
        assert sm.current_state == EngagementState.IN_ZONE
        assert len(sm.get_history()) == 0

    def test_multiple_transitions_accumulate_in_history(self):
        """Multiple transitions all appear in get_history()."""
        sm = EngagementStateMachine()

        # CALIBRATING -> DRIFTING (2 low scores)
        low = _make_result("0.40", EngagementState.DRIFTING)
        sm.update(low)
        sm.update(low)
        assert sm.current_state == EngagementState.DRIFTING
        assert len(sm.get_history()) == 1

        # DRIFTING -> IN_ZONE (2 recovery scores)
        recovery = _make_result("0.75", EngagementState.IN_ZONE)
        sm.update(recovery)
        sm.update(recovery)
        assert sm.current_state == EngagementState.IN_ZONE
        assert len(sm.get_history()) == 2

        # IN_ZONE -> DRIFTING (1 low score)
        low2 = _make_result("0.50", EngagementState.DRIFTING)
        sm.update(low2)
        assert sm.current_state == EngagementState.DRIFTING
        assert len(sm.get_history()) == 3

    def test_history_is_a_copy_not_reference(self):
        """get_history() returns a copy; mutating it doesn't affect the FSM."""
        sm = EngagementStateMachine(initial_state=EngagementState.IN_ZONE)
        low = _make_result("0.50", EngagementState.DRIFTING)
        sm.update(low)

        history = sm.get_history()
        history.clear()

        # Original internal history should still have the transition
        assert len(sm.get_history()) == 1


# ============================================================================
# Interrupted streak — counter reset behavior
# ============================================================================


class TestCounterResetOnInterruptedStreak:
    """Verify consecutive counters reset when a non-matching score arrives."""

    def test_high_score_streak_broken_resets_counter(self):
        """2 high scores + 1 medium score resets the high counter, so the
        next 2 high scores don't trigger transition (need 3 fresh consecutive)."""
        sm = EngagementStateMachine()
        high = _make_result("0.85", EngagementState.IN_ZONE)
        medium = _make_result("0.65", EngagementState.CALIBRATING)

        sm.update(high)
        sm.update(high)
        # Interrupt the streak
        sm.update(medium)
        assert sm.current_state == EngagementState.CALIBRATING

        # Now 2 more high scores: not enough (counter reset)
        sm.update(high)
        sm.update(high)
        assert sm.current_state == EngagementState.CALIBRATING

        # Third consecutive after reset: NOW it triggers
        sm.update(high)
        assert sm.current_state == EngagementState.IN_ZONE

    def test_recovery_streak_broken_resets_counter(self):
        """In DRIFTING, recovery streak must be consecutive."""
        sm = EngagementStateMachine(initial_state=EngagementState.DRIFTING)
        recovery = _make_result("0.75", EngagementState.IN_ZONE)
        low = _make_result("0.55", EngagementState.DRIFTING)

        sm.update(recovery)
        assert sm.current_state == EngagementState.DRIFTING

        # Interrupt with a lower score
        sm.update(low)
        assert sm.current_state == EngagementState.DRIFTING

        # Need 2 fresh consecutive recovery scores
        sm.update(recovery)
        assert sm.current_state == EngagementState.DRIFTING
        sm.update(recovery)
        assert sm.current_state == EngagementState.IN_ZONE


# ============================================================================
# Chapter change resets
# ============================================================================


class TestChapterChangeResetsJourney:
    """Verify chapter changes reset state and counters mid-journey."""

    def test_chapter_change_during_in_zone_resets_to_calibrating(self):
        """Chapter change from IN_ZONE resets to CALIBRATING."""
        sm = EngagementStateMachine(initial_state=EngagementState.IN_ZONE)
        transition = sm.on_chapter_change(new_chapter=3)

        assert sm.current_state == EngagementState.CALIBRATING
        assert transition.from_state == EngagementState.IN_ZONE
        assert transition.to_state == EngagementState.CALIBRATING

    def test_chapter_change_resets_counters_allowing_fresh_journey(self):
        """After chapter change, a fresh 3 high scores → IN_ZONE works."""
        sm = EngagementStateMachine()
        high = _make_result("0.85", EngagementState.IN_ZONE)

        # Build up 2 high scores
        sm.update(high)
        sm.update(high)

        # Chapter change resets everything
        sm.on_chapter_change(new_chapter=2)
        assert sm.current_state == EngagementState.CALIBRATING

        # Need 3 fresh consecutive
        sm.update(high)
        assert sm.current_state == EngagementState.CALIBRATING
        sm.update(high)
        assert sm.current_state == EngagementState.CALIBRATING
        sm.update(high)
        assert sm.current_state == EngagementState.IN_ZONE

    def test_chapter_change_appears_in_history(self):
        """Chapter change transition is recorded in history."""
        sm = EngagementStateMachine(initial_state=EngagementState.DRIFTING)

        # Score-based transition
        low = _make_result("0.35", EngagementState.DISTANT)
        sm.update(low, is_neglecting=True, is_new_day=True)
        sm.update(low, is_neglecting=True, is_new_day=True)
        assert sm.current_state == EngagementState.DISTANT

        # Chapter change
        sm.on_chapter_change(new_chapter=4)

        history = sm.get_history()
        assert len(history) == 2
        assert history[0].to_state == EngagementState.DISTANT
        assert history[1].to_state == EngagementState.CALIBRATING
        assert "chapter" in history[1].reason.lower()


# ============================================================================
# Clingy path
# ============================================================================


class TestClingyPathTransitions:
    """Journey through the clingy path: DRIFTING -> CLINGY -> OUT_OF_ZONE."""

    def test_drifting_to_clingy_to_out_of_zone(self):
        """DRIFTING->CLINGY (2 clingy days)->OUT_OF_ZONE (3 more clingy days)."""
        sm = EngagementStateMachine(initial_state=EngagementState.DRIFTING)
        clingy_low = _make_result("0.40", EngagementState.CLINGY)

        # 2 clingy days: DRIFTING -> CLINGY
        sm.update(clingy_low, is_clingy=True, is_new_day=True)
        assert sm.current_state == EngagementState.DRIFTING
        sm.update(clingy_low, is_clingy=True, is_new_day=True)
        assert sm.current_state == EngagementState.CLINGY

        # 3 more clingy days: CLINGY -> OUT_OF_ZONE
        sm.update(clingy_low, is_clingy=True, is_new_day=True)
        assert sm.current_state == EngagementState.CLINGY
        sm.update(clingy_low, is_clingy=True, is_new_day=True)
        assert sm.current_state == EngagementState.CLINGY
        sm.update(clingy_low, is_clingy=True, is_new_day=True)
        assert sm.current_state == EngagementState.OUT_OF_ZONE

        history = sm.get_history()
        assert len(history) == 2
        assert history[0].to_state == EngagementState.CLINGY
        assert history[1].to_state == EngagementState.OUT_OF_ZONE

    def test_clingy_recovery_to_drifting(self):
        """CLINGY -> DRIFTING (2 good days)."""
        sm = EngagementStateMachine(initial_state=EngagementState.CLINGY)
        good = _make_result("0.60", EngagementState.DRIFTING)

        sm.update(good, is_clingy=False, is_new_day=True)
        assert sm.current_state == EngagementState.CLINGY
        sm.update(good, is_clingy=False, is_new_day=True)
        assert sm.current_state == EngagementState.DRIFTING
