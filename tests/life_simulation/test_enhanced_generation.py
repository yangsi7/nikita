"""Tests for Spec 055: Life Simulation Enhanced.

Tests for:
- T001: WeeklyRoutine and DayRoutine models
- T002: routine.yaml loading
- T005: Routine context in EventGenerator prompt
- T007: Mood context in EventGenerator prompt
- T008: Bidirectional mood flow in simulator
- T012: NPC state updates from life events
- T019: Integration test — full enhanced generation
"""

import pytest
from datetime import date, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from nikita.life_simulation.models import (
    DayRoutine,
    WeeklyRoutine,
    LifeEvent,
    EventDomain,
    EventType,
    TimeOfDay,
    EmotionalImpact,
)
from nikita.life_simulation.event_generator import (
    EventGenerator,
    GeneratedEventList,
    GeneratedEvent,
)
from nikita.life_simulation.mood_calculator import MoodState
from nikita.life_simulation.simulator import LifeSimulator


# ==================== T001: DayRoutine Model Tests ====================


class TestDayRoutine:
    """Tests for DayRoutine Pydantic model."""

    def test_valid_day_routine(self):
        """AC-T001.1: DayRoutine with all fields."""
        routine = DayRoutine(
            day_of_week="monday",
            wake_time="07:30",
            activities=["work", "gym"],
            work_schedule="office",
            energy_pattern="normal",
            social_availability="low",
        )
        assert routine.day_of_week == "monday"
        assert routine.work_schedule == "office"
        assert routine.energy_pattern == "normal"
        assert routine.social_availability == "low"
        assert routine.activities == ["work", "gym"]

    def test_day_of_week_validation(self):
        """AC-T001.3: Validation for day_of_week values."""
        with pytest.raises(ValueError, match="Invalid day_of_week"):
            DayRoutine(day_of_week="notaday")

    def test_day_of_week_case_insensitive(self):
        """Day names are normalized to lowercase."""
        routine = DayRoutine(day_of_week="Monday")
        assert routine.day_of_week == "monday"

    def test_work_schedule_validation(self):
        """Validates work_schedule enum."""
        with pytest.raises(ValueError, match="Invalid work_schedule"):
            DayRoutine(day_of_week="monday", work_schedule="hybrid")

    def test_energy_pattern_validation(self):
        """Validates energy_pattern enum."""
        with pytest.raises(ValueError, match="Invalid energy_pattern"):
            DayRoutine(day_of_week="monday", energy_pattern="extreme")

    def test_social_availability_validation(self):
        """Validates social_availability enum."""
        with pytest.raises(ValueError, match="Invalid social_availability"):
            DayRoutine(day_of_week="monday", social_availability="none")

    def test_defaults(self):
        """Default values are applied correctly."""
        routine = DayRoutine(day_of_week="tuesday")
        assert routine.wake_time == "08:00"
        assert routine.work_schedule == "office"
        assert routine.energy_pattern == "normal"
        assert routine.social_availability == "moderate"
        assert routine.activities == []

    def test_format_for_prompt(self):
        """format_for_prompt() produces readable string."""
        routine = DayRoutine(
            day_of_week="saturday",
            wake_time="09:30",
            work_schedule="off",
            activities=["errands", "hobby"],
            energy_pattern="high",
            social_availability="high",
        )
        prompt = routine.format_for_prompt()
        assert "Saturday" in prompt
        assert "09:30" in prompt
        assert "off" in prompt
        assert "errands, hobby" in prompt
        assert "high" in prompt


# ==================== T001: WeeklyRoutine Model Tests ====================


class TestWeeklyRoutine:
    """Tests for WeeklyRoutine Pydantic model."""

    def test_valid_weekly_routine(self):
        """AC-T001.2: WeeklyRoutine with days dict and timezone."""
        routine = WeeklyRoutine(
            days={
                "monday": DayRoutine(day_of_week="monday"),
                "friday": DayRoutine(day_of_week="friday"),
            },
            timezone="Europe/Berlin",
        )
        assert len(routine.days) == 2
        assert routine.timezone == "Europe/Berlin"

    def test_get_day(self):
        """get_day() returns correct DayRoutine."""
        routine = WeeklyRoutine(
            days={"monday": DayRoutine(day_of_week="monday", work_schedule="remote")}
        )
        day = routine.get_day("monday")
        assert day is not None
        assert day.work_schedule == "remote"

    def test_get_day_not_found(self):
        """get_day() returns None for missing day."""
        routine = WeeklyRoutine(days={})
        assert routine.get_day("monday") is None

    def test_get_day_for_date(self):
        """AC-T001.5: get_day_for_date() maps date to day of week."""
        # 2026-02-18 is a Wednesday
        routine = WeeklyRoutine(
            days={"wednesday": DayRoutine(day_of_week="wednesday", work_schedule="remote")}
        )
        day = routine.get_day_for_date(date(2026, 2, 18))
        assert day is not None
        assert day.work_schedule == "remote"

    def test_default_routine(self):
        """AC-T001.4: default() returns all 7 days."""
        routine = WeeklyRoutine.default()
        assert len(routine.days) == 7
        assert "monday" in routine.days
        assert "sunday" in routine.days
        assert routine.timezone == "Europe/Berlin"

    def test_default_weekday_vs_weekend(self):
        """Default routine differentiates weekday from weekend."""
        routine = WeeklyRoutine.default()
        monday = routine.get_day("monday")
        saturday = routine.get_day("saturday")
        assert monday is not None and saturday is not None
        assert monday.work_schedule in ("office", "remote")
        assert saturday.work_schedule == "off"

    def test_invalid_day_key(self):
        """Validates day keys in dict."""
        with pytest.raises(ValueError, match="Invalid day key"):
            WeeklyRoutine(
                days={"notaday": DayRoutine(day_of_week="monday")}
            )


# ==================== T002: routine.yaml Loading ====================


class TestRoutineYaml:
    """Tests for routine.yaml config file."""

    def test_routine_yaml_exists(self):
        """AC-T002.1: routine.yaml file exists."""
        config_path = (
            Path(__file__).parent.parent.parent
            / "nikita"
            / "config_data"
            / "life_simulation"
            / "routine.yaml"
        )
        assert config_path.exists(), f"routine.yaml not found at {config_path}"

    def test_routine_yaml_loads(self):
        """AC-T002.4: routine.yaml is parseable by WeeklyRoutine.from_yaml()."""
        config_path = (
            Path(__file__).parent.parent.parent
            / "nikita"
            / "config_data"
            / "life_simulation"
            / "routine.yaml"
        )
        routine = WeeklyRoutine.from_yaml(config_path)
        assert len(routine.days) == 7
        assert routine.timezone == "Europe/Berlin"

    def test_routine_yaml_weekend_off(self):
        """AC-T002.3: Weekend days have work_schedule 'off'."""
        config_path = (
            Path(__file__).parent.parent.parent
            / "nikita"
            / "config_data"
            / "life_simulation"
            / "routine.yaml"
        )
        routine = WeeklyRoutine.from_yaml(config_path)
        saturday = routine.get_day("saturday")
        sunday = routine.get_day("sunday")
        assert saturday is not None and saturday.work_schedule == "off"
        assert sunday is not None and sunday.work_schedule == "off"

    def test_from_yaml_not_found(self):
        """from_yaml() raises FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            WeeklyRoutine.from_yaml(Path("/nonexistent/routine.yaml"))


# ==================== T005: Routine Context in Prompt ====================


class TestEventGeneratorRoutine:
    """Tests for routine context in event generation prompt."""

    def _make_generator(self):
        """Create EventGenerator with mocked entity manager."""
        entity_mgr = MagicMock()
        entity_mgr.get_entity_names = AsyncMock(return_value={
            "colleague": ["Lisa"],
            "friend": ["Lena"],
            "place": ["the office"],
            "project": ["the redesign"],
        })
        return EventGenerator(entity_manager=entity_mgr)

    def test_prompt_without_routine(self):
        """AC-T005.4: Without routine param, prompt is unchanged."""
        gen = self._make_generator()
        prompt = gen._build_generation_prompt(
            event_date=date(2026, 2, 18),
            entity_names={"colleague": ["Lisa"], "friend": [], "place": [], "project": []},
            active_arcs=[],
            recent_events=[],
        )
        assert "Nikita's Schedule Today" not in prompt
        assert "Generate 3-5 realistic" in prompt

    def test_prompt_with_routine(self):
        """AC-T005.2: Prompt includes routine section when provided."""
        gen = self._make_generator()
        routine = DayRoutine(
            day_of_week="saturday",
            work_schedule="off",
            activities=["errands", "hobby"],
            energy_pattern="high",
            social_availability="high",
        )
        prompt = gen._build_generation_prompt(
            event_date=date(2026, 2, 21),  # Saturday
            entity_names={"colleague": [], "friend": [], "place": [], "project": []},
            active_arcs=[],
            recent_events=[],
            routine=routine,
        )
        assert "Nikita's Schedule Today" in prompt
        assert "off" in prompt
        assert "errands, hobby" in prompt


# ==================== T007: Mood Context in Prompt ====================


class TestEventGeneratorMood:
    """Tests for mood context in event generation prompt."""

    def _make_generator(self):
        entity_mgr = MagicMock()
        entity_mgr.get_entity_names = AsyncMock(return_value={
            "colleague": [], "friend": [], "place": [], "project": [],
        })
        return EventGenerator(entity_manager=entity_mgr)

    def test_prompt_without_mood(self):
        """AC-T007.5: Without mood_state, prompt is unchanged."""
        gen = self._make_generator()
        prompt = gen._build_generation_prompt(
            event_date=date(2026, 2, 18),
            entity_names={"colleague": [], "friend": [], "place": [], "project": []},
            active_arcs=[],
            recent_events=[],
        )
        assert "Current Mood" not in prompt

    def test_prompt_low_mood(self):
        """AC-T007.3: Low valence biases toward stress events."""
        gen = self._make_generator()
        mood = MoodState(valence=0.3, arousal=0.4)
        prompt = gen._build_generation_prompt(
            event_date=date(2026, 2, 18),
            entity_names={"colleague": [], "friend": [], "place": [], "project": []},
            active_arcs=[],
            recent_events=[],
            mood_state=mood,
        )
        assert "Current Mood" in prompt
        assert "LOW mood" in prompt
        assert "stress" in prompt.lower() or "setback" in prompt.lower()

    def test_prompt_high_mood(self):
        """AC-T007.4: High valence biases toward positive events."""
        gen = self._make_generator()
        mood = MoodState(valence=0.7, arousal=0.6)
        prompt = gen._build_generation_prompt(
            event_date=date(2026, 2, 18),
            entity_names={"colleague": [], "friend": [], "place": [], "project": []},
            active_arcs=[],
            recent_events=[],
            mood_state=mood,
        )
        assert "Current Mood" in prompt
        assert "GOOD mood" in prompt

    def test_prompt_neutral_mood(self):
        """Neutral mood generates balanced prompt."""
        gen = self._make_generator()
        mood = MoodState(valence=0.5, arousal=0.5)
        prompt = gen._build_generation_prompt(
            event_date=date(2026, 2, 18),
            entity_names={"colleague": [], "friend": [], "place": [], "project": []},
            active_arcs=[],
            recent_events=[],
            mood_state=mood,
        )
        assert "Current Mood" in prompt
        assert "NEUTRAL mood" in prompt


# ==================== T008 + T012: Simulator Enhanced Flow ====================


class TestSimulatorEnhanced:
    """Tests for enhanced simulator flow (mood, routine, NPC updates)."""

    def _make_mocks(self):
        """Create mocked simulator dependencies."""
        store = MagicMock()
        store.get_events_for_date = AsyncMock(return_value=[])
        store.get_entities = AsyncMock(return_value=[])
        store.get_recent_events = AsyncMock(return_value=[])
        store.save_events = AsyncMock(return_value=[])
        store.save_entities = AsyncMock(return_value=[])
        store.update_npc_state = AsyncMock(return_value=True)

        entity_mgr = MagicMock()
        entity_mgr.seed_entities = AsyncMock(return_value=[])
        entity_mgr.get_entity_names = AsyncMock(return_value={
            "colleague": [], "friend": [], "place": [], "project": [],
        })

        event_gen = MagicMock()
        generated_events = [
            LifeEvent(
                user_id=uuid4(),
                event_date=date(2026, 2, 19),
                time_of_day=TimeOfDay.MORNING,
                domain=EventDomain.WORK,
                event_type=EventType.MEETING,
                description="Had a design review meeting with Lisa about the redesign",
                entities=["Lisa", "Lena"],
                emotional_impact=EmotionalImpact(valence_delta=0.2, arousal_delta=0.1),
                importance=0.5,
            ),
        ]
        event_gen.generate_events_for_day = AsyncMock(return_value=generated_events)

        narrative_mgr = MagicMock()
        narrative_mgr.get_active_arcs = AsyncMock(return_value=[])
        narrative_mgr.maybe_resolve_arcs = AsyncMock(return_value=[])
        narrative_mgr.maybe_create_arc = AsyncMock(return_value=None)

        mood_calc = MagicMock()
        mood_calc.compute_from_events = MagicMock(return_value=MoodState(valence=0.6, arousal=0.5))

        return store, entity_mgr, event_gen, narrative_mgr, mood_calc

    @pytest.mark.asyncio
    async def test_enhanced_passes_mood_to_generator(self):
        """AC-T008.2: Mood state passed to EventGenerator when flag ON."""
        store, entity_mgr, event_gen, narrative_mgr, mood_calc = self._make_mocks()
        simulator = LifeSimulator(
            store=store,
            entity_manager=entity_mgr,
            event_generator=event_gen,
            narrative_manager=narrative_mgr,
            mood_calculator=mood_calc,
        )

        with patch.object(simulator, '_is_enhanced', return_value=True):
            await simulator.generate_next_day_events(
                user_id=uuid4(),
                target_date=date(2026, 2, 19),
            )

        # Verify mood_state was passed
        call_kwargs = event_gen.generate_events_for_day.call_args
        assert call_kwargs.kwargs.get("mood_state") is not None

    @pytest.mark.asyncio
    async def test_enhanced_passes_routine_to_generator(self):
        """AC-T006.2: Routine passed to EventGenerator when flag ON."""
        store, entity_mgr, event_gen, narrative_mgr, mood_calc = self._make_mocks()
        simulator = LifeSimulator(
            store=store,
            entity_manager=entity_mgr,
            event_generator=event_gen,
            narrative_manager=narrative_mgr,
            mood_calculator=mood_calc,
        )

        with patch.object(simulator, '_is_enhanced', return_value=True):
            await simulator.generate_next_day_events(
                user_id=uuid4(),
                target_date=date(2026, 2, 19),  # Thursday
            )

        call_kwargs = event_gen.generate_events_for_day.call_args
        assert call_kwargs.kwargs.get("routine") is not None

    @pytest.mark.asyncio
    async def test_flag_off_no_mood_or_routine(self):
        """AC-T006.3/T008.5: Flag OFF — no mood/routine passed."""
        store, entity_mgr, event_gen, narrative_mgr, mood_calc = self._make_mocks()
        simulator = LifeSimulator(
            store=store,
            entity_manager=entity_mgr,
            event_generator=event_gen,
            narrative_manager=narrative_mgr,
            mood_calculator=mood_calc,
        )

        with patch.object(simulator, '_is_enhanced', return_value=False):
            await simulator.generate_next_day_events(
                user_id=uuid4(),
                target_date=date(2026, 2, 19),
            )

        call_kwargs = event_gen.generate_events_for_day.call_args
        assert call_kwargs.kwargs.get("mood_state") is None
        assert call_kwargs.kwargs.get("routine") is None

    @pytest.mark.asyncio
    async def test_npc_state_updated_on_enhanced(self):
        """AC-T012.1/T012.2: NPC states updated after event generation."""
        store, entity_mgr, event_gen, narrative_mgr, mood_calc = self._make_mocks()
        simulator = LifeSimulator(
            store=store,
            entity_manager=entity_mgr,
            event_generator=event_gen,
            narrative_manager=narrative_mgr,
            mood_calculator=mood_calc,
        )

        with patch.object(simulator, '_is_enhanced', return_value=True):
            await simulator.generate_next_day_events(
                user_id=uuid4(),
                target_date=date(2026, 2, 19),
            )

        # Should have called update_npc_state for each entity in each event
        assert store.update_npc_state.call_count >= 1

    @pytest.mark.asyncio
    async def test_npc_state_not_updated_flag_off(self):
        """NPC states NOT updated when flag OFF."""
        store, entity_mgr, event_gen, narrative_mgr, mood_calc = self._make_mocks()
        simulator = LifeSimulator(
            store=store,
            entity_manager=entity_mgr,
            event_generator=event_gen,
            narrative_manager=narrative_mgr,
            mood_calculator=mood_calc,
        )

        with patch.object(simulator, '_is_enhanced', return_value=False):
            await simulator.generate_next_day_events(
                user_id=uuid4(),
                target_date=date(2026, 2, 19),
            )

        store.update_npc_state.assert_not_called()


# ==================== T012: Sentiment Computation ====================


class TestSentimentComputation:
    """Tests for sentiment computation from events."""

    def test_positive_sentiment(self):
        """AC-T012.4: valence_delta > 0.1 = positive."""
        event = LifeEvent(
            user_id=uuid4(),
            event_date=date(2026, 2, 18),
            time_of_day=TimeOfDay.MORNING,
            domain=EventDomain.SOCIAL,
            event_type=EventType.FRIEND_HANGOUT,
            description="Had a great coffee with Lena, she was in a good mood",
            emotional_impact=EmotionalImpact(valence_delta=0.2),
        )
        assert LifeSimulator._compute_sentiment(event) == "positive"

    def test_negative_sentiment(self):
        """AC-T012.4: valence_delta < -0.1 = negative."""
        event = LifeEvent(
            user_id=uuid4(),
            event_date=date(2026, 2, 18),
            time_of_day=TimeOfDay.MORNING,
            domain=EventDomain.WORK,
            event_type=EventType.SETBACK,
            description="Got some harsh feedback from David on the redesign",
            emotional_impact=EmotionalImpact(valence_delta=-0.2),
        )
        assert LifeSimulator._compute_sentiment(event) == "negative"

    def test_neutral_sentiment(self):
        """AC-T012.4: small valence = neutral."""
        event = LifeEvent(
            user_id=uuid4(),
            event_date=date(2026, 2, 18),
            time_of_day=TimeOfDay.AFTERNOON,
            domain=EventDomain.PERSONAL,
            event_type=EventType.ERRAND,
            description="Ran some errands around the neighborhood, nothing special",
            emotional_impact=EmotionalImpact(valence_delta=0.05),
        )
        assert LifeSimulator._compute_sentiment(event) == "neutral"
