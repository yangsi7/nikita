"""Tests for MoodCalculator (Spec 022, T005).

AC-T005.1: MoodCalculator class
AC-T005.2: compute_from_events() returns mood dict
AC-T005.3: Mood dimensions: arousal, valence, dominance, intimacy
AC-T005.4: Correct delta application per event
AC-T005.5: Unit tests for calculator
"""

from datetime import date
from uuid import uuid4

import pytest

from nikita.life_simulation.models import (
    EmotionalImpact,
    EventDomain,
    EventType,
    LifeEvent,
    TimeOfDay,
)
from nikita.life_simulation.mood_calculator import (
    MoodCalculator,
    MoodState,
    get_mood_calculator,
)


class TestMoodState:
    """Tests for MoodState dataclass."""

    def test_default_values(self):
        """Default mood is neutral (0.5)."""
        mood = MoodState()
        assert mood.arousal == 0.5
        assert mood.valence == 0.5
        assert mood.dominance == 0.5
        assert mood.intimacy == 0.5

    def test_custom_values(self):
        """Custom mood values are accepted."""
        mood = MoodState(arousal=0.8, valence=0.3)
        assert mood.arousal == 0.8
        assert mood.valence == 0.3

    def test_clamping_high(self):
        """Values above 1.0 are clamped."""
        mood = MoodState(arousal=1.5, valence=2.0)
        assert mood.arousal == 1.0
        assert mood.valence == 1.0

    def test_clamping_low(self):
        """Values below 0.0 are clamped."""
        mood = MoodState(arousal=-0.5, valence=-1.0)
        assert mood.arousal == 0.0
        assert mood.valence == 0.0

    def test_to_dict(self):
        """Convert to dictionary."""
        mood = MoodState(arousal=0.7, valence=0.4)
        result = mood.to_dict()
        assert result["arousal"] == 0.7
        assert result["valence"] == 0.4
        assert "dominance" in result
        assert "intimacy" in result


class TestMoodCalculator:
    """Tests for MoodCalculator class (AC-T005.1)."""

    @pytest.fixture
    def calculator(self):
        """Create calculator instance."""
        return MoodCalculator()

    @pytest.fixture
    def user_id(self):
        """Test user ID."""
        return uuid4()

    @pytest.fixture
    def bad_meeting_event(self, user_id):
        """Create bad meeting event (negative valence)."""
        return LifeEvent(
            user_id=user_id,
            event_date=date.today(),
            time_of_day=TimeOfDay.MORNING,
            domain=EventDomain.WORK,
            event_type=EventType.MEETING,
            description="Had a tough meeting with my manager about the redesign deadline",
            entities=["Lisa", "the redesign"],
            emotional_impact=EmotionalImpact(
                arousal_delta=0.2,
                valence_delta=-0.3,
                dominance_delta=-0.2,
            ),
            importance=0.8,
        )

    @pytest.fixture
    def coffee_with_friend_event(self, user_id):
        """Create coffee with friend event (positive valence)."""
        return LifeEvent(
            user_id=user_id,
            event_date=date.today(),
            time_of_day=TimeOfDay.AFTERNOON,
            domain=EventDomain.SOCIAL,
            event_type=EventType.FRIEND_HANGOUT,
            description="Grabbed coffee with Ana, she's going through a breakup but we had a good talk",
            entities=["Ana"],
            emotional_impact=EmotionalImpact(
                arousal_delta=0.1,
                valence_delta=0.2,
                dominance_delta=0.0,
            ),
        )

    @pytest.fixture
    def gym_event(self, user_id):
        """Create gym event (positive arousal and valence)."""
        return LifeEvent(
            user_id=user_id,
            event_date=date.today(),
            time_of_day=TimeOfDay.EVENING,
            domain=EventDomain.PERSONAL,
            event_type=EventType.GYM,
            description="Finally hit the gym after skipping all week, feeling great",
            emotional_impact=EmotionalImpact(
                arousal_delta=0.2,
                valence_delta=0.1,
                dominance_delta=0.1,
            ),
        )

    def test_empty_events_returns_neutral(self, calculator):
        """Empty event list returns neutral mood (AC-T005.2)."""
        mood = calculator.compute_from_events([])
        assert mood.arousal == 0.5
        assert mood.valence == 0.5
        assert mood.dominance == 0.5
        assert mood.intimacy == 0.5

    def test_single_negative_event(self, calculator, bad_meeting_event):
        """Single negative event lowers valence (AC-T005.4)."""
        mood = calculator.compute_from_events([bad_meeting_event])
        # Base 0.5 + delta -0.3 = 0.2
        assert mood.valence == pytest.approx(0.2, abs=0.01)
        # Base 0.5 + delta 0.2 = 0.7
        assert mood.arousal == pytest.approx(0.7, abs=0.01)
        # Base 0.5 + delta -0.2 = 0.3
        assert mood.dominance == pytest.approx(0.3, abs=0.01)

    def test_single_positive_event(self, calculator, coffee_with_friend_event):
        """Single positive event raises valence (AC-T005.4)."""
        mood = calculator.compute_from_events([coffee_with_friend_event])
        # Base 0.5 + delta 0.2 = 0.7
        assert mood.valence == pytest.approx(0.7, abs=0.01)
        # Base 0.5 + delta 0.1 = 0.6
        assert mood.arousal == pytest.approx(0.6, abs=0.01)

    def test_multiple_events_cumulative(
        self, calculator, bad_meeting_event, coffee_with_friend_event, gym_event
    ):
        """Multiple events have cumulative effect (AC-T005.4)."""
        events = [bad_meeting_event, coffee_with_friend_event, gym_event]
        mood = calculator.compute_from_events(events)

        # Valence: 0.5 + (-0.3) + 0.2 + 0.1 = 0.5
        assert mood.valence == pytest.approx(0.5, abs=0.01)

        # Arousal: 0.5 + 0.2 + 0.1 + 0.2 = 1.0
        assert mood.arousal == pytest.approx(1.0, abs=0.01)

        # Dominance: 0.5 + (-0.2) + 0.0 + 0.1 = 0.4
        assert mood.dominance == pytest.approx(0.4, abs=0.01)

    def test_mood_dimensions_exist(self, calculator, gym_event):
        """All 4 mood dimensions are returned (AC-T005.3)."""
        mood = calculator.compute_from_events([gym_event])
        mood_dict = mood.to_dict()
        assert "arousal" in mood_dict
        assert "valence" in mood_dict
        assert "dominance" in mood_dict
        assert "intimacy" in mood_dict

    def test_compute_from_single_event(self, calculator, gym_event):
        """compute_from_event convenience method works."""
        mood = calculator.compute_from_event(gym_event)
        assert mood.arousal > 0.5  # Gym increases arousal

    def test_clamping_prevents_overflow(self, calculator, user_id):
        """Cumulative deltas are clamped to valid range."""
        # Create event with max positive impact
        event = LifeEvent(
            user_id=user_id,
            event_date=date.today(),
            time_of_day=TimeOfDay.MORNING,
            domain=EventDomain.WORK,
            event_type=EventType.WIN,
            description="Got promoted! Best day ever at work, feeling on top of the world",
            emotional_impact=EmotionalImpact(
                arousal_delta=0.3,
                valence_delta=0.3,
                dominance_delta=0.2,
            ),
        )

        # Apply same event multiple times
        events = [event, event, event, event]  # 4 times
        mood = calculator.compute_from_events(events)

        # Should be clamped at 1.0
        assert mood.arousal == 1.0
        assert mood.valence == 1.0
        assert mood.dominance == 1.0

    def test_clamping_prevents_underflow(self, calculator, user_id):
        """Cumulative negative deltas are clamped."""
        event = LifeEvent(
            user_id=user_id,
            event_date=date.today(),
            time_of_day=TimeOfDay.MORNING,
            domain=EventDomain.WORK,
            event_type=EventType.SETBACK,
            description="Project cancelled after all that work, feeling really down",
            emotional_impact=EmotionalImpact(
                arousal_delta=-0.2,
                valence_delta=-0.3,
                dominance_delta=-0.2,
            ),
        )

        events = [event, event, event, event]
        mood = calculator.compute_from_events(events)

        # Should be clamped at 0.0
        assert mood.valence == 0.0

    def test_custom_base_mood(self, user_id):
        """Calculator can use custom base mood."""
        base = MoodState(arousal=0.7, valence=0.3, dominance=0.6, intimacy=0.4)
        calculator = MoodCalculator(base_mood=base)

        event = LifeEvent(
            user_id=user_id,
            event_date=date.today(),
            time_of_day=TimeOfDay.MORNING,
            domain=EventDomain.PERSONAL,
            event_type=EventType.GYM,
            description="Morning gym session to start the day right",
            emotional_impact=EmotionalImpact(valence_delta=0.1),
        )

        mood = calculator.compute_from_events([event])
        # Base 0.3 + delta 0.1 = 0.4
        assert mood.valence == pytest.approx(0.4, abs=0.01)


class TestMoodDescriptions:
    """Tests for mood description generation."""

    @pytest.fixture
    def calculator(self):
        """Create calculator instance."""
        return MoodCalculator()

    def test_describe_neutral(self, calculator):
        """Neutral mood description."""
        mood = MoodState()
        description = calculator.describe_mood(mood)
        assert description == "neutral"

    def test_describe_happy_energetic(self, calculator):
        """Happy and energetic mood description."""
        mood = MoodState(arousal=0.8, valence=0.8)
        description = calculator.describe_mood(mood)
        assert "energetic" in description
        assert "happy" in description

    def test_describe_tired_upset(self, calculator):
        """Tired and upset mood description."""
        mood = MoodState(arousal=0.2, valence=0.2)
        description = calculator.describe_mood(mood)
        assert "tired" in description
        assert "upset" in description

    def test_describe_confident(self, calculator):
        """Confident mood description."""
        mood = MoodState(dominance=0.8)
        description = calculator.describe_mood(mood)
        assert "confident" in description

    def test_describe_guarded(self, calculator):
        """Guarded mood description."""
        mood = MoodState(intimacy=0.2)
        description = calculator.describe_mood(mood)
        assert "guarded" in description


class TestGetMoodCalculator:
    """Tests for singleton factory."""

    def test_singleton_pattern(self):
        """get_mood_calculator returns same instance."""
        import nikita.life_simulation.mood_calculator as calc_module
        calc_module._default_calculator = None

        calc1 = get_mood_calculator()
        calc2 = get_mood_calculator()

        assert calc1 is calc2
