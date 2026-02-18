"""Adversarial tests for LifeSimulator enhanced features (DA-08).

Targets: nikita/life_simulation/simulator.py — Spec 055 enhanced mode.

Edge cases tested:
- _is_enhanced() resilience to various exception types
- _load_weekly_routine() failure handling in generate_next_day_events
- _update_npc_states() with missing NPCs, empty events, empty entities
- get_current_mood() with zero events
"""

import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from uuid import uuid4

from nikita.life_simulation.simulator import LifeSimulator
from nikita.life_simulation.models import (
    DayRoutine,
    EventDomain,
    EventType,
    LifeEvent,
    TimeOfDay,
    WeeklyRoutine,
    EmotionalImpact,
)
from nikita.life_simulation.mood_calculator import MoodState


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def mock_store():
    """Create a mock EventStore with all async methods."""
    store = MagicMock()
    store.get_entities = AsyncMock(return_value=[])
    store.get_events_for_date = AsyncMock(return_value=[])
    store.get_recent_events = AsyncMock(return_value=[])
    store.save_events = AsyncMock()
    store.update_npc_state = AsyncMock()
    return store


@pytest.fixture
def mock_entity_manager():
    mgr = MagicMock()
    mgr.seed_entities = AsyncMock(return_value=[])
    return mgr


@pytest.fixture
def mock_event_generator():
    gen = MagicMock()
    gen.generate_events_for_day = AsyncMock(return_value=[])
    return gen


@pytest.fixture
def mock_narrative_manager():
    mgr = MagicMock()
    mgr.get_active_arcs = AsyncMock(return_value=[])
    mgr.maybe_resolve_arcs = AsyncMock(return_value=[])
    mgr.maybe_create_arc = AsyncMock(return_value=None)
    return mgr


@pytest.fixture
def mock_mood_calculator():
    calc = MagicMock()
    calc.compute_from_events = MagicMock(
        return_value=MoodState(arousal=0.5, valence=0.5, dominance=0.5, intimacy=0.5)
    )
    return calc


@pytest.fixture
def simulator(mock_store, mock_entity_manager, mock_event_generator, mock_narrative_manager, mock_mood_calculator):
    return LifeSimulator(
        store=mock_store,
        entity_manager=mock_entity_manager,
        event_generator=mock_event_generator,
        narrative_manager=mock_narrative_manager,
        mood_calculator=mock_mood_calculator,
    )


def _make_event(user_id, entities=None, valence_delta=0.0) -> LifeEvent:
    """Helper to create a minimal LifeEvent."""
    return LifeEvent(
        user_id=user_id,
        event_date=date(2026, 2, 18),
        time_of_day=TimeOfDay.MORNING,
        domain=EventDomain.WORK,
        event_type=EventType.MEETING,
        description="A meeting about quarterly goals and objectives",
        entities=entities or [],
        emotional_impact=EmotionalImpact(valence_delta=valence_delta),
    )


# =============================================================================
# TestIsEnhancedAdversarial
# =============================================================================


class TestIsEnhancedAdversarial:
    """_is_enhanced() must return False on ANY exception, True only when flag is True."""

    def test_import_error_returns_false(self, simulator):
        """get_settings() raises ImportError -> returns False."""
        with patch("nikita.life_simulation.simulator.LifeSimulator._is_enhanced") as mock_enhanced:
            # Test the real method by unpatching and testing directly
            pass

        # Test the actual method with import error
        with patch("nikita.config.settings.get_settings", side_effect=ImportError("no module")):
            # _is_enhanced imports get_settings inside the method body
            result = simulator._is_enhanced()
            assert result is False

    def test_runtime_error_returns_false(self, simulator):
        """get_settings() raises RuntimeError -> returns False."""
        with patch("nikita.config.settings.get_settings", side_effect=RuntimeError("boom")):
            result = simulator._is_enhanced()
            assert result is False

    def test_attribute_error_returns_false(self, simulator):
        """get_settings() returns object without life_sim_enhanced attr -> returns False."""
        mock_settings = MagicMock(spec=[])  # Empty spec = no attributes
        # Accessing .life_sim_enhanced will raise AttributeError
        with patch("nikita.config.settings.get_settings", return_value=mock_settings):
            result = simulator._is_enhanced()
            assert result is False

    def test_flag_true_returns_true(self, simulator):
        """get_settings().life_sim_enhanced = True -> returns True."""
        mock_settings = MagicMock()
        mock_settings.life_sim_enhanced = True
        with patch("nikita.config.settings.get_settings", return_value=mock_settings):
            result = simulator._is_enhanced()
            assert result is True

    def test_flag_false_returns_false(self, simulator):
        """get_settings().life_sim_enhanced = False -> returns False."""
        mock_settings = MagicMock()
        mock_settings.life_sim_enhanced = False
        with patch("nikita.config.settings.get_settings", return_value=mock_settings):
            result = simulator._is_enhanced()
            assert result is False

    def test_type_error_returns_false(self, simulator):
        """get_settings() raises TypeError -> returns False."""
        with patch("nikita.config.settings.get_settings", side_effect=TypeError("bad type")):
            result = simulator._is_enhanced()
            assert result is False

    def test_value_error_returns_false(self, simulator):
        """get_settings() raises ValueError -> returns False."""
        with patch("nikita.config.settings.get_settings", side_effect=ValueError("bad value")):
            result = simulator._is_enhanced()
            assert result is False


# =============================================================================
# TestLoadWeeklyRoutineAdversarial
# =============================================================================


class TestLoadWeeklyRoutineAdversarial:
    """_load_weekly_routine() calls WeeklyRoutine.default(). Failure should be
    caught in generate_next_day_events (wrapped in try/except)."""

    def test_normal_load(self, simulator):
        """WeeklyRoutine.default() works -> returns WeeklyRoutine."""
        result = simulator._load_weekly_routine()
        assert isinstance(result, WeeklyRoutine)

    @pytest.mark.asyncio
    async def test_routine_load_failure_caught_in_pipeline(
        self, simulator, mock_store, mock_event_generator, user_id
    ):
        """If WeeklyRoutine.default() raises in generate_next_day_events,
        routine should be None and pipeline continues."""
        mock_store.get_events_for_date.return_value = []
        mock_event_generator.generate_events_for_day.return_value = []

        with patch.object(simulator, "_is_enhanced", return_value=True), \
             patch.object(simulator, "_load_weekly_routine", side_effect=RuntimeError("YAML corrupt")), \
             patch.object(simulator, "get_current_mood", new_callable=AsyncMock, return_value=MoodState(arousal=0.5, valence=0.5, dominance=0.5, intimacy=0.5)):
            # Should NOT raise — the try/except in generate_next_day_events catches it
            events = await simulator.generate_next_day_events(user_id, target_date=date(2026, 3, 1))
            # Pipeline completes (returns whatever event_generator returns)
            assert isinstance(events, list)

    @pytest.mark.asyncio
    async def test_routine_file_not_found_caught(
        self, simulator, mock_store, mock_event_generator, user_id
    ):
        """FileNotFoundError from routine loading -> caught, pipeline continues."""
        mock_store.get_events_for_date.return_value = []
        mock_event_generator.generate_events_for_day.return_value = []

        with patch.object(simulator, "_is_enhanced", return_value=True), \
             patch.object(simulator, "_load_weekly_routine", side_effect=FileNotFoundError("routine.yaml")), \
             patch.object(simulator, "get_current_mood", new_callable=AsyncMock, return_value=MoodState(arousal=0.5, valence=0.5, dominance=0.5, intimacy=0.5)):
            events = await simulator.generate_next_day_events(user_id, target_date=date(2026, 3, 1))
            assert isinstance(events, list)


# =============================================================================
# TestUpdateNpcStatesAdversarial
# =============================================================================


class TestUpdateNpcStatesAdversarial:
    """_update_npc_states() should handle missing NPCs, empty lists gracefully."""

    @pytest.mark.asyncio
    async def test_unknown_entity_caught(self, simulator, mock_store, user_id):
        """Entity name that doesn't match any NPC -> store raises -> caught, continues."""
        mock_store.update_npc_state.side_effect = Exception("NPC not found: Ghost")
        events = [_make_event(user_id, entities=["Ghost", "Phantom"])]

        # Should NOT raise — exception is caught per entity
        await simulator._update_npc_states(user_id, events)
        assert mock_store.update_npc_state.call_count == 2

    @pytest.mark.asyncio
    async def test_empty_events_list(self, simulator, mock_store, user_id):
        """Empty events list -> no crash, no store calls."""
        await simulator._update_npc_states(user_id, [])
        mock_store.update_npc_state.assert_not_called()

    @pytest.mark.asyncio
    async def test_event_with_empty_entities(self, simulator, mock_store, user_id):
        """Event with empty entities list -> no iterations, no crash."""
        events = [_make_event(user_id, entities=[])]
        await simulator._update_npc_states(user_id, events)
        mock_store.update_npc_state.assert_not_called()

    @pytest.mark.asyncio
    async def test_mixed_success_and_failure(self, simulator, mock_store, user_id):
        """Some entities succeed, some fail -> continues processing all."""
        call_count = 0

        async def side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if kwargs.get("npc_name") == "BadNPC":
                raise Exception("DB error")
            return None

        mock_store.update_npc_state = AsyncMock(side_effect=side_effect)
        events = [
            _make_event(user_id, entities=["GoodNPC", "BadNPC", "AnotherGood"]),
        ]

        await simulator._update_npc_states(user_id, events)
        assert call_count == 3  # All three attempted

    @pytest.mark.asyncio
    async def test_multiple_events_all_entities_processed(self, simulator, mock_store, user_id):
        """Multiple events with multiple entities -> all processed."""
        events = [
            _make_event(user_id, entities=["Alice", "Bob"]),
            _make_event(user_id, entities=["Charlie"]),
            _make_event(user_id, entities=["Diana", "Eve", "Frank"]),
        ]
        await simulator._update_npc_states(user_id, events)
        assert mock_store.update_npc_state.call_count == 6


# =============================================================================
# TestMoodWithZeroEvents
# =============================================================================


class TestMoodWithZeroEvents:
    """get_current_mood() with no recent events must handle empty list gracefully."""

    @pytest.mark.asyncio
    async def test_zero_events_returns_mood(self, simulator, mock_store, mock_mood_calculator, user_id):
        """get_recent_events returns [] -> compute_from_events([]) -> valid MoodState."""
        mock_store.get_recent_events.return_value = []
        mock_mood_calculator.compute_from_events.return_value = MoodState(
            arousal=0.5, valence=0.5, dominance=0.5, intimacy=0.5
        )

        mood = await simulator.get_current_mood(user_id, lookback_days=3)
        assert isinstance(mood, MoodState)
        mock_mood_calculator.compute_from_events.assert_called_once_with([])

    @pytest.mark.asyncio
    async def test_mood_calculator_raises_on_empty(self, simulator, mock_store, mock_mood_calculator, user_id):
        """If mood_calculator.compute_from_events raises on [], exception propagates.

        NOTE: This tests whether LifeSimulator.get_current_mood catches exceptions.
        Looking at the source, it does NOT wrap in try/except (only generate_next_day_events does).
        """
        mock_store.get_recent_events.return_value = []
        mock_mood_calculator.compute_from_events.side_effect = ZeroDivisionError("empty division")

        with pytest.raises(ZeroDivisionError):
            await simulator.get_current_mood(user_id, lookback_days=3)

    @pytest.mark.asyncio
    async def test_mood_failure_caught_in_pipeline(
        self, simulator, mock_store, mock_event_generator, mock_mood_calculator, user_id
    ):
        """Mood failure in generate_next_day_events -> caught by try/except, mood=None, pipeline continues."""
        mock_store.get_events_for_date.return_value = []
        mock_event_generator.generate_events_for_day.return_value = []
        mock_mood_calculator.compute_from_events.side_effect = RuntimeError("mood crash")

        with patch.object(simulator, "_is_enhanced", return_value=True):
            events = await simulator.generate_next_day_events(user_id, target_date=date(2026, 3, 1))
            assert isinstance(events, list)

    @pytest.mark.asyncio
    async def test_zero_lookback_days(self, simulator, mock_store, mock_mood_calculator, user_id):
        """lookback_days=0 -> get_recent_events(days=0) -> likely empty -> valid mood."""
        mock_store.get_recent_events.return_value = []
        mock_mood_calculator.compute_from_events.return_value = MoodState(
            arousal=0.5, valence=0.5, dominance=0.5, intimacy=0.5
        )

        mood = await simulator.get_current_mood(user_id, lookback_days=0)
        assert isinstance(mood, MoodState)
        mock_store.get_recent_events.assert_called_once_with(user_id, days=0)


# =============================================================================
# TestComputeSentiment
# =============================================================================


class TestComputeSentiment:
    """Edge cases for _compute_sentiment static method."""

    def test_exact_positive_boundary(self):
        """valence_delta=0.1 -> neutral (not > 0.1)."""
        event = _make_event(uuid4(), valence_delta=0.1)
        result = LifeSimulator._compute_sentiment(event)
        # 0.1 is NOT > 0.1, so it's neutral
        # NOTE: May fail if source uses >= 0.1
        assert result == "neutral"

    def test_above_positive_boundary(self):
        """valence_delta=0.11 -> positive."""
        event = _make_event(uuid4(), valence_delta=0.11)
        result = LifeSimulator._compute_sentiment(event)
        assert result == "positive"

    def test_exact_negative_boundary(self):
        """valence_delta=-0.1 -> neutral (not < -0.1)."""
        event = _make_event(uuid4(), valence_delta=-0.1)
        result = LifeSimulator._compute_sentiment(event)
        # -0.1 is NOT < -0.1, so it's neutral
        assert result == "neutral"

    def test_below_negative_boundary(self):
        """valence_delta=-0.11 -> negative."""
        event = _make_event(uuid4(), valence_delta=-0.11)
        result = LifeSimulator._compute_sentiment(event)
        assert result == "negative"

    def test_zero_valence(self):
        """valence_delta=0.0 -> neutral."""
        event = _make_event(uuid4(), valence_delta=0.0)
        result = LifeSimulator._compute_sentiment(event)
        assert result == "neutral"
