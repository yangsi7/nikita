"""Unit Tests: State Computation (Spec 023, T005-T010).

Tests StateComputer and all computation methods:
- Base state calculation (time/day factors)
- Life event delta application
- Conversation delta detection
- Relationship modifier application
- Full compute() orchestration

AC-T005: Base state calculation
AC-T006: Life event delta application
AC-T007: Conversation delta detection
AC-T008: Relationship modifier
AC-T009: StateComputer.compute() orchestration
AC-T010: Coverage tests
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from nikita.emotional_state.computer import (
    ConversationTone,
    DayOfWeek,
    LifeEventImpact,
    StateComputer,
    TimeOfDay,
    get_state_computer,
)
from nikita.emotional_state.models import ConflictState, EmotionalStateModel


@pytest.fixture
def user_id():
    """Generate test user ID."""
    return uuid4()


@pytest.fixture
def computer():
    """Create StateComputer instance."""
    return StateComputer()


class TestBaseStateCalculation:
    """AC-T005: Base state calculation tests."""

    def test_morning_increases_arousal(self, computer):
        """AC-T005.2: Morning should increase arousal."""
        # 9 AM on Monday
        morning = datetime(2026, 1, 12, 9, 0, 0, tzinfo=timezone.utc)
        base = computer._compute_base_state(morning)

        assert base["arousal"] > 0.5  # Morning boost

    def test_night_decreases_arousal(self, computer):
        """AC-T005.2: Night should decrease arousal."""
        # 10 PM
        night = datetime(2026, 1, 12, 22, 0, 0, tzinfo=timezone.utc)
        base = computer._compute_base_state(night)

        assert base["arousal"] < 0.5  # Night decrease

    def test_late_night_low_arousal(self, computer):
        """Late night (2 AM) should have lowest arousal."""
        late_night = datetime(2026, 1, 12, 2, 0, 0, tzinfo=timezone.utc)
        base = computer._compute_base_state(late_night)

        assert base["arousal"] < 0.4  # Very low

    def test_weekend_increases_valence(self, computer):
        """AC-T005.3: Weekend should increase valence."""
        # Saturday at noon
        saturday = datetime(2026, 1, 11, 12, 0, 0, tzinfo=timezone.utc)  # Jan 11, 2026 is Saturday
        base = computer._compute_base_state(saturday)

        assert base["valence"] > 0.5  # Weekend boost

    def test_friday_anticipation(self, computer):
        """Friday should have anticipation boost."""
        # Friday at 5 PM
        friday = datetime(2026, 1, 9, 17, 0, 0, tzinfo=timezone.utc)  # Jan 9, 2026 is Friday... wait let me check
        # Actually need to verify the day. Let me use a known Friday
        friday = datetime(2026, 1, 10, 17, 0, 0, tzinfo=timezone.utc)  # Jan 10, 2026 should be Saturday, so Jan 9 is Friday
        friday = datetime(2026, 1, 9, 17, 0, 0, tzinfo=timezone.utc)

        # Jan 9 2026 weekday check: datetime(2026, 1, 9).weekday() = ?
        # Let me just compute it dynamically
        from datetime import date
        # Jan 1 2026 is Thursday (weekday 3), so Jan 9 = 3 + 8 = 11 % 7 = 4 = Friday
        base = computer._compute_base_state(friday)

        assert base["valence"] >= 0.5  # Friday boost
        assert base["arousal"] >= 0.5  # Anticipation

    def test_weekday_neutral_valence(self, computer):
        """Weekday should have neutral valence."""
        # Wednesday at noon
        wednesday = datetime(2026, 1, 7, 12, 0, 0, tzinfo=timezone.utc)
        base = computer._compute_base_state(wednesday)

        # Should be close to neutral
        assert 0.45 <= base["valence"] <= 0.55

    def test_all_dimensions_returned(self, computer):
        """Base state should return all 4 dimensions."""
        now = datetime.now(timezone.utc)
        base = computer._compute_base_state(now)

        assert "arousal" in base
        assert "valence" in base
        assert "dominance" in base
        assert "intimacy" in base

    def test_values_clamped_to_range(self, computer):
        """All values should be in 0.0-1.0 range."""
        # Test extreme times
        times = [
            datetime(2026, 1, 12, 3, 0, 0, tzinfo=timezone.utc),  # Late night
            datetime(2026, 1, 12, 9, 0, 0, tzinfo=timezone.utc),  # Morning
            datetime(2026, 1, 12, 22, 0, 0, tzinfo=timezone.utc),  # Night
        ]

        for ts in times:
            base = computer._compute_base_state(ts)
            for dim, val in base.items():
                assert 0.0 <= val <= 1.0, f"{dim} out of range: {val}"


class TestLifeEventDeltas:
    """AC-T006: Life event delta application tests."""

    def test_positive_event_increases_valence(self, computer):
        """Positive event should increase valence."""
        events = [
            LifeEventImpact(valence_delta=0.2, arousal_delta=0.1),
        ]

        deltas = computer._apply_life_event_deltas(events)

        assert deltas["valence_delta"] > 0
        assert deltas["arousal_delta"] > 0

    def test_negative_event_decreases_valence(self, computer):
        """Negative event should decrease valence."""
        events = [
            LifeEventImpact(valence_delta=-0.15, dominance_delta=-0.1),
        ]

        deltas = computer._apply_life_event_deltas(events)

        assert deltas["valence_delta"] < 0
        assert deltas["dominance_delta"] < 0

    def test_multiple_events_combined(self, computer):
        """Multiple events should be combined."""
        events = [
            LifeEventImpact(valence_delta=0.1),
            LifeEventImpact(valence_delta=0.1),
            LifeEventImpact(valence_delta=-0.05),
        ]

        deltas = computer._apply_life_event_deltas(events)

        assert deltas["valence_delta"] == pytest.approx(0.15)

    def test_deltas_clamped(self, computer):
        """Deltas should be clamped to prevent extreme swings."""
        events = [
            LifeEventImpact(valence_delta=0.5),
            LifeEventImpact(valence_delta=0.5),
        ]

        deltas = computer._apply_life_event_deltas(events)

        # Should be clamped to 0.3 max
        assert deltas["valence_delta"] <= 0.3

    def test_empty_events_no_change(self, computer):
        """Empty events list should return zero deltas."""
        deltas = computer._apply_life_event_deltas([])

        assert deltas["arousal_delta"] == 0.0
        assert deltas["valence_delta"] == 0.0
        assert deltas["dominance_delta"] == 0.0
        assert deltas["intimacy_delta"] == 0.0


class TestConversationDeltas:
    """AC-T007: Conversation delta detection tests."""

    def test_supportive_increases_valence_intimacy(self, computer):
        """AC-T007.4: Supportive tone increases valence and intimacy."""
        tones = [ConversationTone.SUPPORTIVE]
        deltas = computer._apply_conversation_deltas(tones)

        assert deltas["valence_delta"] > 0
        assert deltas["intimacy_delta"] > 0

    def test_dismissive_decreases_valence_intimacy(self, computer):
        """AC-T007.4: Dismissive tone decreases valence and intimacy."""
        tones = [ConversationTone.DISMISSIVE]
        deltas = computer._apply_conversation_deltas(tones)

        assert deltas["valence_delta"] < 0
        assert deltas["intimacy_delta"] < 0

    def test_romantic_increases_intimacy(self, computer):
        """Romantic tone should increase intimacy significantly."""
        tones = [ConversationTone.ROMANTIC]
        deltas = computer._apply_conversation_deltas(tones)

        assert deltas["intimacy_delta"] >= 0.15
        assert deltas["valence_delta"] > 0

    def test_cold_decreases_intimacy(self, computer):
        """Cold tone should decrease intimacy."""
        tones = [ConversationTone.COLD]
        deltas = computer._apply_conversation_deltas(tones)

        assert deltas["intimacy_delta"] < 0
        assert deltas["valence_delta"] < 0

    def test_playful_increases_arousal(self, computer):
        """Playful tone should increase arousal."""
        tones = [ConversationTone.PLAYFUL]
        deltas = computer._apply_conversation_deltas(tones)

        assert deltas["arousal_delta"] > 0
        assert deltas["valence_delta"] > 0

    def test_anxious_increases_arousal_decreases_dominance(self, computer):
        """Anxious tone affects arousal and dominance."""
        tones = [ConversationTone.ANXIOUS]
        deltas = computer._apply_conversation_deltas(tones)

        assert deltas["arousal_delta"] > 0
        assert deltas["dominance_delta"] < 0

    def test_neutral_no_effect(self, computer):
        """Neutral tone should have minimal effect."""
        tones = [ConversationTone.NEUTRAL]
        deltas = computer._apply_conversation_deltas(tones)

        assert deltas["valence_delta"] == 0.0
        assert deltas["arousal_delta"] == 0.0

    def test_multiple_tones_combined(self, computer):
        """Multiple tones should be combined."""
        tones = [ConversationTone.SUPPORTIVE, ConversationTone.PLAYFUL]
        deltas = computer._apply_conversation_deltas(tones)

        # Both increase valence
        assert deltas["valence_delta"] > 0.2

    def test_conversation_deltas_clamped(self, computer):
        """Conversation deltas should be clamped."""
        # Many romantic tones
        tones = [ConversationTone.ROMANTIC] * 5
        deltas = computer._apply_conversation_deltas(tones)

        # Should be clamped
        assert deltas["intimacy_delta"] <= 0.4


class TestRelationshipModifier:
    """AC-T008: Relationship modifier tests."""

    def test_chapter_1_lower_intimacy(self, computer):
        """AC-T008.2: Chapter 1 has lower baseline intimacy."""
        mods = computer._apply_relationship_modifier(chapter=1, relationship_score=0.5)

        # Chapter 1 = guarded
        assert mods["intimacy_delta"] == 0.0

    def test_chapter_5_higher_intimacy(self, computer):
        """AC-T008.2: Chapter 5 has higher baseline intimacy."""
        mods = computer._apply_relationship_modifier(chapter=5, relationship_score=0.5)

        # Chapter 5 = very open
        assert mods["intimacy_delta"] > 0.1

    def test_high_score_positive_valence(self, computer):
        """AC-T008.3: High relationship score increases valence."""
        mods = computer._apply_relationship_modifier(chapter=3, relationship_score=0.8)

        assert mods["valence_delta"] > 0

    def test_low_score_negative_valence(self, computer):
        """AC-T008.3: Low relationship score decreases valence."""
        mods = computer._apply_relationship_modifier(chapter=3, relationship_score=0.2)

        assert mods["valence_delta"] < 0

    def test_neutral_score_no_valence_change(self, computer):
        """Neutral score (0.5) should have no valence effect."""
        mods = computer._apply_relationship_modifier(chapter=3, relationship_score=0.5)

        assert mods["valence_delta"] == pytest.approx(0.0, abs=0.05)


class TestStateComputerOrchestration:
    """AC-T009: StateComputer.compute() orchestration tests."""

    def test_compute_with_no_inputs(self, computer, user_id):
        """Should compute base state with no additional inputs."""
        state = computer.compute(user_id=user_id)

        assert state.user_id == user_id
        assert 0.0 <= state.arousal <= 1.0
        assert 0.0 <= state.valence <= 1.0
        assert 0.0 <= state.dominance <= 1.0
        assert 0.0 <= state.intimacy <= 1.0

    def test_compute_with_current_state(self, computer, user_id):
        """Should modify existing state."""
        current = EmotionalStateModel(
            user_id=user_id,
            arousal=0.3,
            valence=0.4,
            dominance=0.5,
            intimacy=0.6,
        )

        state = computer.compute(
            user_id=user_id,
            current_state=current,
            life_events=[LifeEventImpact(valence_delta=0.2)],
        )

        # Valence should be increased from current
        assert state.valence > current.valence

    def test_compute_with_life_events(self, computer, user_id):
        """Should apply life event deltas."""
        events = [
            LifeEventImpact(arousal_delta=0.1, valence_delta=0.15),
        ]

        state = computer.compute(user_id=user_id, life_events=events)

        # Base + event deltas
        assert state.valence > 0.5

    def test_compute_with_conversation_tones(self, computer, user_id):
        """Should apply conversation tone deltas."""
        tones = [ConversationTone.ROMANTIC]

        state = computer.compute(user_id=user_id, conversation_tones=tones)

        # Romantic increases intimacy
        assert state.intimacy > 0.5

    def test_compute_with_relationship_modifier(self, computer, user_id):
        """Should apply relationship modifiers."""
        state = computer.compute(
            user_id=user_id,
            chapter=5,
            relationship_score=0.9,
        )

        # High chapter + high score = boosted intimacy and valence
        assert state.intimacy > 0.5
        assert state.valence > 0.5

    def test_compute_combines_all_sources(self, computer, user_id):
        """AC-T009.2: Should combine all sources."""
        state = computer.compute(
            user_id=user_id,
            life_events=[LifeEventImpact(valence_delta=0.1)],
            conversation_tones=[ConversationTone.SUPPORTIVE],
            chapter=3,
            relationship_score=0.7,
        )

        # All positive influences
        assert state.valence > 0.6

    def test_compute_preserves_conflict_state(self, computer, user_id):
        """Should preserve conflict state from current."""
        current = EmotionalStateModel(
            user_id=user_id,
            conflict_state=ConflictState.COLD,
            conflict_trigger="Distance",
        )

        state = computer.compute(user_id=user_id, current_state=current)

        assert state.conflict_state == ConflictState.COLD
        assert state.conflict_trigger == "Distance"

    def test_compute_clamps_all_dimensions(self, computer, user_id):
        """AC-T009.3: All dimensions should be clamped to 0.0-1.0."""
        # Extreme positive inputs
        state = computer.compute(
            user_id=user_id,
            life_events=[LifeEventImpact(valence_delta=1.0)] * 5,
            conversation_tones=[ConversationTone.ROMANTIC] * 5,
            chapter=5,
            relationship_score=1.0,
        )

        assert state.arousal <= 1.0
        assert state.valence <= 1.0
        assert state.dominance <= 1.0
        assert state.intimacy <= 1.0

    def test_compute_with_specific_timestamp(self, computer, user_id):
        """Should use provided timestamp for base state."""
        # Morning timestamp
        morning = datetime(2026, 1, 12, 9, 0, 0, tzinfo=timezone.utc)

        state = computer.compute(user_id=user_id, timestamp=morning)

        # Morning should have higher arousal
        assert state.arousal >= 0.5


class TestGetStateComputer:
    """Tests for singleton get_state_computer()."""

    def test_returns_state_computer(self):
        """Should return StateComputer instance."""
        computer = get_state_computer()
        assert isinstance(computer, StateComputer)

    def test_singleton_same_instance(self):
        """Should return same instance."""
        c1 = get_state_computer()
        c2 = get_state_computer()
        assert c1 is c2
