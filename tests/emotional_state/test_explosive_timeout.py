"""Tests for EXPLOSIVE conflict timeout de-escalation (Spec 101 FR-004).

AC-T4.1: EXPLOSIVE_TIMEOUT_HOURS constant = 6
AC-T4.2: Auto de-escalation EXPLOSIVE → COLD after 6 hours
AC-T4.3: No timeout for non-EXPLOSIVE states
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from nikita.emotional_state.conflict import ConflictDetector, EXPLOSIVE_TIMEOUT_HOURS
from nikita.emotional_state.models import ConflictState, EmotionalStateModel


def _make_state(
    *,
    conflict_state: ConflictState = ConflictState.EXPLOSIVE,
    conflict_started_at: datetime | None = None,
    valence: float = 0.2,
    arousal: float = 0.9,
) -> EmotionalStateModel:
    """Create an EmotionalStateModel with given conflict state."""
    return EmotionalStateModel(
        user_id=uuid4(),
        arousal=arousal,
        valence=valence,
        dominance=0.5,
        intimacy=0.5,
        conflict_state=conflict_state,
        conflict_started_at=conflict_started_at,
        conflict_trigger="test",
    )


class TestExplosiveTimeoutConstant:
    """Test EXPLOSIVE_TIMEOUT_HOURS constant."""

    def test_timeout_is_6_hours(self):
        """AC-T4.1: Constant equals 6."""
        assert EXPLOSIVE_TIMEOUT_HOURS == 6


class TestExplosiveTimeoutDeEscalation:
    """Test auto de-escalation of EXPLOSIVE after timeout."""

    def test_explosive_past_timeout_de_escalates_to_cold(self):
        """AC-T4.2: EXPLOSIVE > 6h → auto COLD."""
        detector = ConflictDetector()
        started = datetime.now(timezone.utc) - timedelta(hours=7)
        state = _make_state(
            conflict_state=ConflictState.EXPLOSIVE,
            conflict_started_at=started,
        )

        should_de, target, reason = detector.check_de_escalation(state)

        assert should_de is True
        assert target == ConflictState.COLD
        assert "timeout" in reason.lower()

    def test_explosive_at_exactly_6h_de_escalates(self):
        """AC-T4.2: Exactly 6h boundary triggers timeout."""
        detector = ConflictDetector()
        started = datetime.now(timezone.utc) - timedelta(hours=6, seconds=1)
        state = _make_state(
            conflict_state=ConflictState.EXPLOSIVE,
            conflict_started_at=started,
        )

        should_de, target, reason = detector.check_de_escalation(state)

        assert should_de is True
        assert target == ConflictState.COLD

    def test_explosive_within_timeout_no_auto_de_escalation(self):
        """AC-T4.2: EXPLOSIVE < 6h does NOT auto de-escalate (without positive interaction)."""
        detector = ConflictDetector()
        started = datetime.now(timezone.utc) - timedelta(hours=3)
        state = _make_state(
            conflict_state=ConflictState.EXPLOSIVE,
            conflict_started_at=started,
            valence=0.2,  # Still low valence
        )

        should_de, target, reason = detector.check_de_escalation(state)

        assert should_de is False

    def test_explosive_within_timeout_positive_interaction_still_works(self):
        """Positive interaction de-escalation still works within timeout."""
        detector = ConflictDetector()
        started = datetime.now(timezone.utc) - timedelta(hours=2)
        state = _make_state(
            conflict_state=ConflictState.EXPLOSIVE,
            conflict_started_at=started,
            valence=0.5,  # Above 0.4 threshold
        )

        should_de, target, reason = detector.check_de_escalation(
            state, positive_interaction=True,
        )

        assert should_de is True
        assert target == ConflictState.COLD

    def test_explosive_no_started_at_no_timeout(self):
        """EXPLOSIVE with no conflict_started_at skips timeout (fallback)."""
        detector = ConflictDetector()
        state = _make_state(
            conflict_state=ConflictState.EXPLOSIVE,
            conflict_started_at=None,
            valence=0.2,
        )

        should_de, target, reason = detector.check_de_escalation(state)

        # Without started_at and without positive_interaction/high valence,
        # no de-escalation
        assert should_de is False


class TestNonExplosiveTimeoutUnaffected:
    """Test that timeout only applies to EXPLOSIVE state."""

    @pytest.mark.parametrize(
        "conflict_state",
        [
            ConflictState.COLD,
            ConflictState.PASSIVE_AGGRESSIVE,
            ConflictState.VULNERABLE,
        ],
    )
    def test_non_explosive_states_ignore_timeout(self, conflict_state: ConflictState):
        """AC-T4.3: Non-EXPLOSIVE states don't auto de-escalate via timeout."""
        detector = ConflictDetector()
        started = datetime.now(timezone.utc) - timedelta(hours=10)

        # Build state manually to avoid model_validator overwriting conflict_started_at
        state = EmotionalStateModel(
            user_id=uuid4(),
            arousal=0.5,
            valence=0.2,
            dominance=0.5,
            intimacy=0.5,
            conflict_state=conflict_state,
            conflict_started_at=started,
            conflict_trigger="test",
        )

        should_de, target, reason = detector.check_de_escalation(state)

        # Non-explosive states should NOT de-escalate just from timeout
        # (they need positive interaction + threshold met)
        assert should_de is False

    def test_none_state_unaffected(self):
        """NONE state returns no de-escalation regardless."""
        detector = ConflictDetector()
        state = _make_state(
            conflict_state=ConflictState.NONE,
            conflict_started_at=None,
            valence=0.5,
        )

        should_de, target, reason = detector.check_de_escalation(state)

        assert should_de is False
