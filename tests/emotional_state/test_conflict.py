"""Unit Tests: Conflict Detection (Spec 023, T011-T014).

Tests ConflictDetector class and all conflict detection methods:
- Threshold trigger detection
- State transition validation
- Escalation/de-escalation paths
- Conflict state management

AC-T011: ConflictDetector class with threshold maps
AC-T012: Trigger threshold detection
AC-T013: Conflict state transitions
AC-T014: Coverage tests
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from nikita.emotional_state.conflict import (
    ConflictDetector,
    get_conflict_detector,
)
from nikita.emotional_state.models import ConflictState, EmotionalStateModel


@pytest.fixture
def user_id():
    """Generate test user ID."""
    return uuid4()


@pytest.fixture
def detector():
    """Create ConflictDetector instance."""
    return ConflictDetector()


class TestConflictDetectorClass:
    """AC-T011: ConflictDetector class tests."""

    def test_has_threshold_maps(self, detector):
        """AC-T011.1: Should have threshold maps."""
        assert hasattr(detector, "THRESHOLDS")
        assert "passive_aggressive" in detector.THRESHOLDS
        assert "cold" in detector.THRESHOLDS
        assert "vulnerable" in detector.THRESHOLDS
        assert "explosive" in detector.THRESHOLDS

    def test_has_detect_method(self, detector):
        """AC-T011.2: Should have detect_conflict_state method."""
        assert hasattr(detector, "detect_conflict_state")
        assert callable(detector.detect_conflict_state)

    def test_supports_four_conflict_states(self, detector):
        """AC-T011.3: Should support 4 conflict states."""
        assert len(detector.THRESHOLDS) == 4

    def test_has_valid_transitions(self, detector):
        """Should have valid transitions map."""
        assert hasattr(detector, "VALID_TRANSITIONS")
        assert ConflictState.NONE in detector.VALID_TRANSITIONS
        assert ConflictState.EXPLOSIVE in detector.VALID_TRANSITIONS


class TestPassiveAggressiveDetection:
    """AC-T012.1: Passive-aggressive threshold detection."""

    def test_no_ignored_messages(self, detector, user_id):
        """Should not detect passive-aggressive with 0 ignored messages."""
        state = EmotionalStateModel(
            user_id=user_id,
            ignored_message_count=0,
        )
        result = detector.detect_conflict_state(state)
        assert result != ConflictState.PASSIVE_AGGRESSIVE

    def test_one_ignored_message(self, detector, user_id):
        """Should not detect passive-aggressive with 1 ignored message."""
        state = EmotionalStateModel(
            user_id=user_id,
            ignored_message_count=1,
        )
        result = detector.detect_conflict_state(state)
        assert result != ConflictState.PASSIVE_AGGRESSIVE

    def test_two_ignored_messages_triggers(self, detector, user_id):
        """AC-T012.1: Should detect passive-aggressive with 2+ ignored messages."""
        state = EmotionalStateModel(
            user_id=user_id,
            ignored_message_count=2,
        )
        result = detector.detect_conflict_state(state)
        assert result == ConflictState.PASSIVE_AGGRESSIVE

    def test_many_ignored_messages(self, detector, user_id):
        """Should detect passive-aggressive with many ignored messages."""
        state = EmotionalStateModel(
            user_id=user_id,
            ignored_message_count=5,
        )
        result = detector.detect_conflict_state(state)
        # May escalate to cold if valence is also low
        assert result in [ConflictState.PASSIVE_AGGRESSIVE, ConflictState.COLD]


class TestColdDetection:
    """AC-T012.2: Cold threshold detection."""

    def test_high_valence_not_cold(self, detector, user_id):
        """Should not detect cold with high valence."""
        state = EmotionalStateModel(
            user_id=user_id,
            valence=0.7,
        )
        result = detector.detect_conflict_state(state)
        assert result != ConflictState.COLD

    def test_neutral_valence_not_cold(self, detector, user_id):
        """Should not detect cold with neutral valence."""
        state = EmotionalStateModel(
            user_id=user_id,
            valence=0.5,
        )
        result = detector.detect_conflict_state(state)
        assert result != ConflictState.COLD

    def test_threshold_valence_not_cold(self, detector, user_id):
        """Should not detect cold at exactly 0.3 valence."""
        state = EmotionalStateModel(
            user_id=user_id,
            valence=0.3,
        )
        result = detector.detect_conflict_state(state)
        assert result != ConflictState.COLD

    def test_low_valence_triggers_cold(self, detector, user_id):
        """AC-T012.2: Should detect cold with valence < 0.3."""
        state = EmotionalStateModel(
            user_id=user_id,
            valence=0.2,
        )
        result = detector.detect_conflict_state(state)
        assert result == ConflictState.COLD

    def test_very_low_valence(self, detector, user_id):
        """Should detect cold with very low valence."""
        state = EmotionalStateModel(
            user_id=user_id,
            valence=0.1,
        )
        result = detector.detect_conflict_state(state)
        # Could be cold or explosive depending on arousal
        assert result in [ConflictState.COLD, ConflictState.EXPLOSIVE]


class TestVulnerableDetection:
    """AC-T012.3: Vulnerable threshold detection."""

    def test_no_intimacy_drop(self, detector, user_id):
        """Should not detect vulnerable without intimacy drop."""
        current = EmotionalStateModel(user_id=user_id, intimacy=0.5)
        previous = EmotionalStateModel(user_id=user_id, intimacy=0.5)

        result = detector.detect_conflict_state(current, previous)
        assert result != ConflictState.VULNERABLE

    def test_small_intimacy_drop(self, detector, user_id):
        """Should not detect vulnerable with small intimacy drop."""
        current = EmotionalStateModel(user_id=user_id, intimacy=0.4)
        previous = EmotionalStateModel(user_id=user_id, intimacy=0.5)

        result = detector.detect_conflict_state(current, previous)
        assert result != ConflictState.VULNERABLE

    def test_threshold_intimacy_drop(self, detector, user_id):
        """AC-T012.3: Should detect vulnerable with intimacy drop >= 0.2."""
        current = EmotionalStateModel(user_id=user_id, intimacy=0.3)
        previous = EmotionalStateModel(user_id=user_id, intimacy=0.5)

        result = detector.detect_conflict_state(current, previous)
        assert result == ConflictState.VULNERABLE

    def test_large_intimacy_drop(self, detector, user_id):
        """Should detect vulnerable with large intimacy drop."""
        current = EmotionalStateModel(user_id=user_id, intimacy=0.2)
        previous = EmotionalStateModel(user_id=user_id, intimacy=0.7)

        result = detector.detect_conflict_state(current, previous)
        assert result == ConflictState.VULNERABLE


class TestExplosiveDetection:
    """AC-T012.4: Explosive threshold detection."""

    def test_high_arousal_only_not_explosive(self, detector, user_id):
        """Should not detect explosive with only high arousal."""
        state = EmotionalStateModel(
            user_id=user_id,
            arousal=0.9,
            valence=0.5,
        )
        result = detector.detect_conflict_state(state)
        assert result != ConflictState.EXPLOSIVE

    def test_low_valence_only_not_explosive(self, detector, user_id):
        """Should not detect explosive with only low valence."""
        state = EmotionalStateModel(
            user_id=user_id,
            arousal=0.5,
            valence=0.2,
        )
        result = detector.detect_conflict_state(state)
        assert result == ConflictState.COLD  # Cold, not explosive

    def test_explosive_requires_both_conditions(self, detector, user_id):
        """AC-T012.4: Should detect explosive with arousal >= 0.8 AND valence < 0.3."""
        # Set current conflict state to COLD to allow transition
        state = EmotionalStateModel(
            user_id=user_id,
            arousal=0.9,
            valence=0.2,
            conflict_state=ConflictState.COLD,
        )
        result = detector.detect_conflict_state(state)
        assert result == ConflictState.EXPLOSIVE

    def test_explosive_boundary_conditions(self, detector, user_id):
        """Should not detect explosive at exactly boundary."""
        state = EmotionalStateModel(
            user_id=user_id,
            arousal=0.8,
            valence=0.3,
            conflict_state=ConflictState.COLD,
        )
        result = detector.detect_conflict_state(state)
        # At boundary - arousal exactly 0.8 qualifies but valence 0.3 doesn't
        assert result != ConflictState.EXPLOSIVE

    def test_explosive_requires_valid_transition(self, detector, user_id):
        """Should not jump to explosive from NONE."""
        state = EmotionalStateModel(
            user_id=user_id,
            arousal=0.95,
            valence=0.1,
            conflict_state=ConflictState.NONE,  # Cannot jump to explosive
        )
        result = detector.detect_conflict_state(state)
        # Should be COLD since can't jump to explosive
        assert result == ConflictState.COLD


class TestStateTransitions:
    """AC-T013: Conflict state transitions."""

    def test_none_to_passive_aggressive_valid(self, detector):
        """Can transition from NONE to PASSIVE_AGGRESSIVE."""
        assert detector.can_transition_to(
            ConflictState.NONE, ConflictState.PASSIVE_AGGRESSIVE
        )

    def test_none_to_cold_valid(self, detector):
        """Can transition from NONE to COLD."""
        assert detector.can_transition_to(ConflictState.NONE, ConflictState.COLD)

    def test_none_to_vulnerable_valid(self, detector):
        """Can transition from NONE to VULNERABLE."""
        assert detector.can_transition_to(ConflictState.NONE, ConflictState.VULNERABLE)

    def test_none_to_explosive_invalid(self, detector):
        """AC-T013.2: Cannot jump from NONE to EXPLOSIVE."""
        assert not detector.can_transition_to(
            ConflictState.NONE, ConflictState.EXPLOSIVE
        )

    def test_cold_to_explosive_valid(self, detector):
        """Can escalate from COLD to EXPLOSIVE."""
        assert detector.can_transition_to(ConflictState.COLD, ConflictState.EXPLOSIVE)

    def test_vulnerable_to_explosive_valid(self, detector):
        """Can escalate from VULNERABLE to EXPLOSIVE."""
        assert detector.can_transition_to(
            ConflictState.VULNERABLE, ConflictState.EXPLOSIVE
        )

    def test_explosive_to_none_invalid(self, detector):
        """Cannot de-escalate directly from EXPLOSIVE to NONE."""
        assert not detector.can_transition_to(
            ConflictState.EXPLOSIVE, ConflictState.NONE
        )

    def test_explosive_to_cold_valid(self, detector):
        """AC-T013.3: Can de-escalate from EXPLOSIVE to COLD."""
        assert detector.can_transition_to(ConflictState.EXPLOSIVE, ConflictState.COLD)

    def test_cold_to_none_valid(self, detector):
        """Can de-escalate from COLD to NONE."""
        assert detector.can_transition_to(ConflictState.COLD, ConflictState.NONE)

    def test_same_state_valid(self, detector):
        """Staying in same state is valid."""
        for state in ConflictState:
            assert detector.can_transition_to(state, state)


class TestApplyTransition:
    """Tests for apply_transition method."""

    def test_apply_valid_transition(self, detector, user_id):
        """Should apply valid transition."""
        state = EmotionalStateModel(
            user_id=user_id,
            conflict_state=ConflictState.NONE,
        )

        result = detector.apply_transition(
            state, ConflictState.COLD, trigger="Low mood"
        )

        assert result.conflict_state == ConflictState.COLD
        assert result.conflict_trigger == "Low mood"

    def test_apply_invalid_transition_raises(self, detector, user_id):
        """Should raise ValueError for invalid transition."""
        state = EmotionalStateModel(
            user_id=user_id,
            conflict_state=ConflictState.NONE,
        )

        with pytest.raises(ValueError, match="Invalid transition"):
            detector.apply_transition(state, ConflictState.EXPLOSIVE)


class TestCheckEscalation:
    """Tests for check_escalation method."""

    def test_no_escalation_needed(self, detector, user_id):
        """Should not escalate when no conflict detected."""
        state = EmotionalStateModel(
            user_id=user_id,
            valence=0.7,
            arousal=0.5,
            conflict_state=ConflictState.NONE,
        )

        should_escalate, target, trigger = detector.check_escalation(state)

        assert not should_escalate
        assert target is None
        assert trigger is None

    def test_escalation_detected(self, detector, user_id):
        """Should detect escalation when triggers met."""
        state = EmotionalStateModel(
            user_id=user_id,
            valence=0.2,
            conflict_state=ConflictState.NONE,
        )

        should_escalate, target, trigger = detector.check_escalation(state)

        assert should_escalate
        assert target == ConflictState.COLD
        assert trigger is not None

    def test_escalation_from_cold_to_explosive(self, detector, user_id):
        """Should escalate from cold to explosive when conditions met."""
        state = EmotionalStateModel(
            user_id=user_id,
            arousal=0.9,
            valence=0.1,
            conflict_state=ConflictState.COLD,
        )

        should_escalate, target, trigger = detector.check_escalation(state)

        assert should_escalate
        assert target == ConflictState.EXPLOSIVE


class TestCheckDeEscalation:
    """Tests for check_de_escalation method."""

    def test_no_de_escalation_from_none(self, detector, user_id):
        """Should not de-escalate from NONE."""
        state = EmotionalStateModel(
            user_id=user_id,
            conflict_state=ConflictState.NONE,
        )

        should_de_escalate, target, reason = detector.check_de_escalation(state)

        assert not should_de_escalate

    def test_de_escalation_from_explosive(self, detector, user_id):
        """Should de-escalate from EXPLOSIVE with positive interaction."""
        state = EmotionalStateModel(
            user_id=user_id,
            valence=0.5,
            conflict_state=ConflictState.EXPLOSIVE,
        )

        should_de_escalate, target, reason = detector.check_de_escalation(
            state, positive_interaction=True
        )

        assert should_de_escalate
        assert target == ConflictState.COLD

    def test_de_escalation_from_cold(self, detector, user_id):
        """Should de-escalate from COLD with positive interaction and high valence."""
        state = EmotionalStateModel(
            user_id=user_id,
            valence=0.5,
            conflict_state=ConflictState.COLD,
        )

        should_de_escalate, target, reason = detector.check_de_escalation(
            state, positive_interaction=True
        )

        assert should_de_escalate
        assert target == ConflictState.NONE

    def test_de_escalation_from_vulnerable(self, detector, user_id):
        """Should de-escalate from VULNERABLE with support."""
        state = EmotionalStateModel(
            user_id=user_id,
            intimacy=0.6,
            conflict_state=ConflictState.VULNERABLE,
        )

        should_de_escalate, target, reason = detector.check_de_escalation(
            state, positive_interaction=True
        )

        assert should_de_escalate
        assert target == ConflictState.NONE

    def test_de_escalation_from_passive_aggressive(self, detector, user_id):
        """Should de-escalate from PASSIVE_AGGRESSIVE with engagement."""
        state = EmotionalStateModel(
            user_id=user_id,
            ignored_message_count=0,
            conflict_state=ConflictState.PASSIVE_AGGRESSIVE,
        )

        should_de_escalate, target, reason = detector.check_de_escalation(
            state, positive_interaction=True
        )

        assert should_de_escalate
        assert target == ConflictState.NONE

    def test_no_de_escalation_without_positive_interaction(self, detector, user_id):
        """Should not de-escalate without positive interaction (in most cases)."""
        state = EmotionalStateModel(
            user_id=user_id,
            valence=0.3,
            conflict_state=ConflictState.COLD,
        )

        should_de_escalate, target, reason = detector.check_de_escalation(
            state, positive_interaction=False
        )

        # Cold requires both high valence AND positive interaction
        assert not should_de_escalate


class TestGetConflictDetector:
    """Tests for singleton get_conflict_detector()."""

    def test_returns_conflict_detector(self):
        """Should return ConflictDetector instance."""
        detector = get_conflict_detector()
        assert isinstance(detector, ConflictDetector)

    def test_singleton_same_instance(self):
        """Should return same instance."""
        d1 = get_conflict_detector()
        d2 = get_conflict_detector()
        assert d1 is d2


class TestSeverityOrder:
    """Tests for severity ordering."""

    def test_severity_order_exists(self, detector):
        """Should have severity order."""
        assert hasattr(detector, "SEVERITY_ORDER")
        assert len(detector.SEVERITY_ORDER) == 5

    def test_none_is_lowest_severity(self, detector):
        """NONE should be lowest severity."""
        assert detector.SEVERITY_ORDER[0] == ConflictState.NONE

    def test_explosive_is_highest_severity(self, detector):
        """EXPLOSIVE should be highest severity."""
        assert detector.SEVERITY_ORDER[-1] == ConflictState.EXPLOSIVE

    def test_get_severity_method(self, detector):
        """Should get correct severity levels."""
        assert detector._get_severity(ConflictState.NONE) == 0
        assert detector._get_severity(ConflictState.EXPLOSIVE) == 4


class TestTriggerReasons:
    """Tests for trigger reason generation."""

    def test_passive_aggressive_trigger_reason(self, detector, user_id):
        """Should generate passive-aggressive trigger reason."""
        state = EmotionalStateModel(user_id=user_id, ignored_message_count=3)
        reason = detector._get_trigger_reason(state, ConflictState.PASSIVE_AGGRESSIVE)
        assert "3" in reason
        assert "ignored" in reason.lower() or "message" in reason.lower()

    def test_cold_trigger_reason(self, detector, user_id):
        """Should generate cold trigger reason."""
        state = EmotionalStateModel(user_id=user_id, valence=0.2)
        reason = detector._get_trigger_reason(state, ConflictState.COLD)
        assert "valence" in reason.lower() or "mood" in reason.lower()

    def test_explosive_trigger_reason(self, detector, user_id):
        """Should generate explosive trigger reason."""
        state = EmotionalStateModel(user_id=user_id, arousal=0.9, valence=0.1)
        reason = detector._get_trigger_reason(state, ConflictState.EXPLOSIVE)
        assert "arousal" in reason.lower() or "tension" in reason.lower()
