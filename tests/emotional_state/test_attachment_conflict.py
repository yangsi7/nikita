"""Tests for backstory-aware conflict detection — Spec 104 Story 6.

Attachment style affects conflict thresholds.
"""

import pytest
from uuid import uuid4

from nikita.emotional_state.models import ConflictState, EmotionalStateModel


def test_anxious_lowers_explosive_threshold():
    """Anxious attachment → lower EXPLOSIVE arousal threshold (easier to trigger)."""
    from nikita.emotional_state.conflict import ConflictDetector

    detector = ConflictDetector()

    # Build state just below normal EXPLOSIVE threshold (arousal_min=0.8)
    # With anxious modifier (-0.1), effective threshold becomes 0.7
    state = EmotionalStateModel(
        user_id=uuid4(),
        valence=0.1,   # Low valence (< 0.3) required for explosive
        arousal=0.75,  # Above 0.7 (anxious threshold) but below 0.8 (normal)
        conflict_state=ConflictState.COLD,  # Must be in COLD to escalate to EXPLOSIVE
    )

    # Without attachment — arousal 0.75 < 0.8, should NOT escalate to EXPLOSIVE
    result_normal = detector.detect_conflict_state(state)
    # COLD is detected since valence=0.1 < 0.3
    assert result_normal == ConflictState.COLD

    # With anxious attachment — effective threshold = 0.7, arousal 0.75 >= 0.7
    result_anxious = detector.detect_conflict_state(state, attachment_style="anxious")
    assert result_anxious == ConflictState.EXPLOSIVE


def test_avoidant_no_special_explosive():
    """Avoidant attachment → no EXPLOSIVE threshold change."""
    from nikita.emotional_state.conflict import ConflictDetector

    detector = ConflictDetector()

    state = EmotionalStateModel(
        user_id=uuid4(),
        valence=0.1,
        arousal=0.75,
        conflict_state=ConflictState.COLD,
    )

    # Avoidant has 0.0 modifier on explosive — same as normal
    result = detector.detect_conflict_state(state, attachment_style="avoidant")
    assert result == ConflictState.COLD  # Not explosive (0.75 < 0.8)


def test_secure_no_threshold_change():
    """Secure attachment → no threshold modification."""
    from nikita.emotional_state.conflict import ConflictDetector

    detector = ConflictDetector()

    state = EmotionalStateModel(
        user_id=uuid4(),
        valence=0.5,
        arousal=0.5,
        conflict_state=ConflictState.NONE,
    )

    result_normal = detector.detect_conflict_state(state)
    result_secure = detector.detect_conflict_state(state, attachment_style="secure")

    assert result_normal == result_secure


def test_disorganized_no_threshold_change():
    """Disorganized attachment → no threshold modification."""
    from nikita.emotional_state.conflict import ConflictDetector

    detector = ConflictDetector()

    state = EmotionalStateModel(
        user_id=uuid4(),
        valence=0.5,
        arousal=0.5,
        conflict_state=ConflictState.NONE,
    )

    result_normal = detector.detect_conflict_state(state)
    result_disorganized = detector.detect_conflict_state(state, attachment_style="disorganized")

    assert result_normal == result_disorganized
