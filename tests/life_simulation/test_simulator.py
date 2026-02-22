"""Tests for LifeSimulator (Spec 022, T013).

AC-T013.1: LifeSimulator class orchestrates all components
AC-T013.2: generate_next_day_events() full pipeline
AC-T013.3: get_today_events() for context injection
AC-T013.4: Handles new users (entity seeding)
AC-T013.5: Unit tests for simulator
"""

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.life_simulation.models import (
    ArcStatus,
    EventDomain,
    EventType,
    LifeEvent,
    NarrativeArc,
    NikitaEntity,
    TimeOfDay,
    EmotionalImpact,
    EntityType,
)
from nikita.life_simulation.mood_calculator import MoodState
from nikita.life_simulation.simulator import (
    LifeSimulator,
    get_life_simulator,
)


class TestLifeSimulatorInitialization:
    """Tests for LifeSimulator initialization (AC-T013.1)."""

    def test_creates_with_defaults(self):
        """LifeSimulator creates with default singletons."""
        simulator = LifeSimulator()

        assert simulator._store is not None
        assert simulator._entity_manager is not None
        assert simulator._event_generator is not None
        assert simulator._narrative_manager is not None
        assert simulator._mood_calculator is not None

    def test_accepts_custom_dependencies(self):
        """LifeSimulator accepts custom dependencies."""
        mock_store = MagicMock()
        mock_entity = MagicMock()
        mock_generator = MagicMock()
        mock_narrative = MagicMock()
        mock_mood = MagicMock()

        simulator = LifeSimulator(
            store=mock_store,
            entity_manager=mock_entity,
            event_generator=mock_generator,
            narrative_manager=mock_narrative,
            mood_calculator=mock_mood,
        )

        assert simulator._store is mock_store
        assert simulator._entity_manager is mock_entity
        assert simulator._event_generator is mock_generator
        assert simulator._narrative_manager is mock_narrative
        assert simulator._mood_calculator is mock_mood


class TestInitializeUser:
    """Tests for user initialization (AC-T013.4)."""

    @pytest.fixture
    def mock_store(self):
        """Create mock store."""
        store = MagicMock()
        store.get_entities = AsyncMock(return_value=[])
        return store

    @pytest.fixture
    def mock_entity_manager(self):
        """Create mock entity manager."""
        manager = MagicMock()
        manager.seed_entities = AsyncMock(return_value=[MagicMock() for _ in range(5)])
        return manager

    @pytest.fixture
    def simulator(self, mock_store, mock_entity_manager):
        """Create simulator with mocks."""
        return LifeSimulator(
            store=mock_store,
            entity_manager=mock_entity_manager,
        )

    @pytest.fixture
    def user_id(self):
        """Test user ID."""
        return uuid4()

    @pytest.mark.asyncio
    async def test_initialize_new_user(self, simulator, mock_store, mock_entity_manager, user_id):
        """Initialize user seeds entities for new users."""
        result = await simulator.initialize_user(user_id)

        assert result is True
        mock_entity_manager.seed_entities.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_initialize_existing_user(self, simulator, mock_store, user_id):
        """Initialize user returns False for existing users."""
        mock_store.get_entities.return_value = [MagicMock()]  # Already has entities

        result = await simulator.initialize_user(user_id)

        assert result is False


class TestGenerateNextDayEvents:
    """Tests for generate_next_day_events (AC-T013.2)."""

    @pytest.fixture
    def user_id(self):
        """Test user ID."""
        return uuid4()

    @pytest.fixture
    def mock_event(self, user_id):
        """Create mock event."""
        return LifeEvent(
            user_id=user_id,
            event_date=date.today() + timedelta(days=1),
            time_of_day=TimeOfDay.MORNING,
            domain=EventDomain.WORK,
            event_type=EventType.MEETING,
            description="Had a design review with Lisa",
            entities=["Lisa"],
            emotional_impact=EmotionalImpact(
                valence_delta=0.1, arousal_delta=0.1, dominance_delta=0.0, intimacy_delta=0.0
            ),
            importance=0.5,
        )

    @pytest.fixture
    def mock_store(self, mock_event):
        """Create mock store."""
        store = MagicMock()
        store.get_entities = AsyncMock(return_value=[])
        store.get_events_for_date = AsyncMock(return_value=[])
        store.get_recent_events = AsyncMock(return_value=[])
        store.save_events = AsyncMock()
        return store

    @pytest.fixture
    def mock_entity_manager(self):
        """Create mock entity manager."""
        manager = MagicMock()
        manager.seed_entities = AsyncMock(return_value=[])
        return manager

    @pytest.fixture
    def mock_event_generator(self, mock_event):
        """Create mock event generator."""
        generator = MagicMock()
        generator.generate_events_for_day = AsyncMock(return_value=[mock_event])
        return generator

    @pytest.fixture
    def mock_narrative_manager(self):
        """Create mock narrative manager."""
        manager = MagicMock()
        manager.get_active_arcs = AsyncMock(return_value=[])
        manager.maybe_resolve_arcs = AsyncMock(return_value=[])
        manager.maybe_create_arc = AsyncMock(return_value=None)
        return manager

    @pytest.fixture
    def simulator(self, mock_store, mock_entity_manager, mock_event_generator, mock_narrative_manager):
        """Create simulator with mocks."""
        return LifeSimulator(
            store=mock_store,
            entity_manager=mock_entity_manager,
            event_generator=mock_event_generator,
            narrative_manager=mock_narrative_manager,
        )

    @pytest.mark.asyncio
    async def test_generates_events(self, simulator, user_id, mock_event):
        """Generate next day events returns events."""
        events = await simulator.generate_next_day_events(user_id)

        assert len(events) == 1
        assert events[0].description == mock_event.description

    @pytest.mark.asyncio
    async def test_uses_specified_date(self, simulator, mock_event_generator, user_id):
        """Generate events uses specified date."""
        target_date = date(2026, 2, 1)

        await simulator.generate_next_day_events(user_id, target_date=target_date)

        call_args = mock_event_generator.generate_events_for_day.call_args
        assert call_args[1]["event_date"] == target_date

    @pytest.mark.asyncio
    async def test_defaults_to_tomorrow(self, simulator, mock_event_generator, user_id):
        """Generate events defaults to tomorrow."""
        await simulator.generate_next_day_events(user_id)

        call_args = mock_event_generator.generate_events_for_day.call_args
        assert call_args[1]["event_date"] == date.today() + timedelta(days=1)

    @pytest.mark.asyncio
    async def test_skips_if_events_exist(self, simulator, mock_store, mock_event, user_id):
        """Generate events skips if events already exist."""
        mock_store.get_events_for_date.return_value = [mock_event]

        events = await simulator.generate_next_day_events(user_id)

        assert events == [mock_event]

    @pytest.mark.asyncio
    async def test_initializes_new_user(self, simulator, mock_store, mock_entity_manager, user_id):
        """Generate events initializes new users."""
        mock_store.get_entities.return_value = []

        await simulator.generate_next_day_events(user_id)

        mock_entity_manager.seed_entities.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_passes_active_arcs(self, simulator, mock_store, mock_narrative_manager, mock_event_generator, user_id):
        """Generate events passes active arcs to generator."""
        mock_arc = MagicMock()
        mock_narrative_manager.get_active_arcs.return_value = [mock_arc]

        await simulator.generate_next_day_events(user_id)

        call_args = mock_event_generator.generate_events_for_day.call_args
        assert call_args[1]["active_arcs"] == [mock_arc]

    @pytest.mark.asyncio
    async def test_passes_recent_events(self, simulator, mock_store, mock_event_generator, mock_event, user_id):
        """Generate events passes recent events for continuity."""
        mock_store.get_recent_events.return_value = [mock_event]

        await simulator.generate_next_day_events(user_id)

        call_args = mock_event_generator.generate_events_for_day.call_args
        assert call_args[1]["recent_events"] == [mock_event]

    @pytest.mark.asyncio
    async def test_saves_events(self, simulator, mock_store, mock_event, user_id):
        """Generate events saves to store."""
        await simulator.generate_next_day_events(user_id)

        mock_store.save_events.assert_called_once()

    @pytest.mark.asyncio
    async def test_maybe_resolves_arcs(self, simulator, mock_narrative_manager, user_id):
        """Generate events may resolve narrative arcs."""
        await simulator.generate_next_day_events(user_id)

        mock_narrative_manager.maybe_resolve_arcs.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_maybe_creates_new_arc(self, simulator, mock_narrative_manager, user_id):
        """Generate events may create new narrative arc."""
        await simulator.generate_next_day_events(user_id)

        mock_narrative_manager.maybe_create_arc.assert_called_once_with(user_id)


class TestGetTodayEvents:
    """Tests for get_today_events (AC-T013.3)."""

    @pytest.fixture
    def user_id(self):
        """Test user ID."""
        return uuid4()

    @pytest.fixture
    def mock_events(self, user_id):
        """Create mock events with varying importance."""
        return [
            LifeEvent(
                user_id=user_id,
                event_date=date.today(),
                time_of_day=TimeOfDay.MORNING,
                domain=EventDomain.WORK,
                event_type=EventType.MEETING,
                description="Low importance event",
                entities=[],
                emotional_impact=EmotionalImpact(),
                importance=0.2,
            ),
            LifeEvent(
                user_id=user_id,
                event_date=date.today(),
                time_of_day=TimeOfDay.AFTERNOON,
                domain=EventDomain.SOCIAL,
                event_type=EventType.FRIEND_HANGOUT,
                description="High importance event",
                entities=[],
                emotional_impact=EmotionalImpact(),
                importance=0.8,
            ),
            LifeEvent(
                user_id=user_id,
                event_date=date.today(),
                time_of_day=TimeOfDay.EVENING,
                domain=EventDomain.PERSONAL,
                event_type=EventType.GYM,
                description="Medium importance event",
                entities=[],
                emotional_impact=EmotionalImpact(),
                importance=0.5,
            ),
        ]

    @pytest.fixture
    def mock_store(self, mock_events):
        """Create mock store."""
        store = MagicMock()
        store.get_events_for_date = AsyncMock(return_value=mock_events)
        return store

    @pytest.fixture
    def simulator(self, mock_store):
        """Create simulator with mock."""
        return LifeSimulator(store=mock_store)

    @pytest.mark.asyncio
    async def test_returns_today_events(self, simulator, user_id, mock_events):
        """Get today events returns events for today."""
        events = await simulator.get_today_events(user_id)

        assert len(events) == 3

    @pytest.mark.asyncio
    async def test_sorts_by_importance(self, simulator, user_id):
        """Get today events sorts by importance descending."""
        events = await simulator.get_today_events(user_id)

        assert events[0].importance == 0.8
        assert events[1].importance == 0.5
        assert events[2].importance == 0.2

    @pytest.mark.asyncio
    async def test_respects_max_events(self, simulator, user_id):
        """Get today events respects max_events limit."""
        events = await simulator.get_today_events(user_id, max_events=2)

        assert len(events) == 2
        assert events[0].importance == 0.8
        assert events[1].importance == 0.5


class TestGetCurrentMood:
    """Tests for get_current_mood."""

    @pytest.fixture
    def user_id(self):
        """Test user ID."""
        return uuid4()

    @pytest.fixture
    def mock_events(self, user_id):
        """Create events with emotional impact."""
        return [
            LifeEvent(
                user_id=user_id,
                event_date=date.today(),
                time_of_day=TimeOfDay.MORNING,
                domain=EventDomain.WORK,
                event_type=EventType.MEETING,
                description="Good meeting",
                entities=[],
                emotional_impact=EmotionalImpact(valence_delta=0.1, arousal_delta=0.1),
                importance=0.5,
            ),
        ]

    @pytest.fixture
    def mock_store(self, mock_events):
        """Create mock store."""
        store = MagicMock()
        store.get_recent_events = AsyncMock(return_value=mock_events)
        return store

    @pytest.fixture
    def mock_mood_calculator(self):
        """Create mock mood calculator."""
        calc = MagicMock()
        calc.compute_from_events = MagicMock(
            return_value=MoodState(arousal=0.6, valence=0.6, dominance=0.5, intimacy=0.5)
        )
        return calc

    @pytest.fixture
    def simulator(self, mock_store, mock_mood_calculator):
        """Create simulator with mocks."""
        return LifeSimulator(store=mock_store, mood_calculator=mock_mood_calculator)

    @pytest.mark.asyncio
    async def test_returns_mood_state(self, simulator, user_id):
        """Get current mood returns MoodState."""
        mood = await simulator.get_current_mood(user_id)

        assert isinstance(mood, MoodState)

    @pytest.mark.asyncio
    async def test_uses_lookback_days(self, simulator, mock_store, user_id):
        """Get current mood uses specified lookback days."""
        await simulator.get_current_mood(user_id, lookback_days=5)

        mock_store.get_recent_events.assert_called_once_with(user_id, days=5)


class TestGetEventsForContext:
    """Tests for get_events_for_context."""

    @pytest.fixture
    def user_id(self):
        """Test user ID."""
        return uuid4()

    @pytest.fixture
    def mock_today_events(self, user_id):
        """Create today's events."""
        return [
            LifeEvent(
                user_id=user_id,
                event_date=date.today(),
                time_of_day=TimeOfDay.MORNING,
                domain=EventDomain.WORK,
                event_type=EventType.MEETING,
                description="Design review with Lisa",
                entities=["Lisa"],
                emotional_impact=EmotionalImpact(),
                importance=0.7,
            ),
        ]

    @pytest.fixture
    def mock_recent_events(self, user_id, mock_today_events):
        """Create recent events including today and yesterday."""
        yesterday_event = LifeEvent(
            user_id=user_id,
            event_date=date.today() - timedelta(days=1),
            time_of_day=TimeOfDay.AFTERNOON,
            domain=EventDomain.SOCIAL,
            event_type=EventType.FRIEND_HANGOUT,
            description="Coffee with Ana",
            entities=["Ana"],
            emotional_impact=EmotionalImpact(),
            importance=0.5,
        )
        return mock_today_events + [yesterday_event]

    @pytest.fixture
    def mock_arc(self, user_id):
        """Create mock arc."""
        return NarrativeArc(
            user_id=user_id,
            domain=EventDomain.WORK,
            arc_type="project_deadline",
            start_date=date.today() - timedelta(days=5),
            entities=["Lisa", "the redesign"],
            current_state="Deadline approaching",
        )

    @pytest.fixture
    def mock_store(self, mock_today_events, mock_recent_events):
        """Create mock store."""
        store = MagicMock()
        store.get_events_for_date = AsyncMock(return_value=mock_today_events)
        store.get_recent_events = AsyncMock(return_value=mock_recent_events)
        return store

    @pytest.fixture
    def mock_narrative_manager(self, mock_arc):
        """Create mock narrative manager."""
        manager = MagicMock()
        manager.get_active_arcs = AsyncMock(return_value=[mock_arc])
        return manager

    @pytest.fixture
    def mock_mood_calculator(self):
        """Create mock mood calculator."""
        calc = MagicMock()
        calc.compute_from_events = MagicMock(
            return_value=MoodState(arousal=0.6, valence=0.7, dominance=0.5, intimacy=0.5)
        )
        return calc

    @pytest.fixture
    def simulator(self, mock_store, mock_narrative_manager, mock_mood_calculator):
        """Create simulator with mocks."""
        return LifeSimulator(
            store=mock_store,
            narrative_manager=mock_narrative_manager,
            mood_calculator=mock_mood_calculator,
        )

    @pytest.mark.asyncio
    async def test_returns_context_dict(self, simulator, user_id):
        """Get events for context returns dict."""
        context = await simulator.get_events_for_context(user_id)

        assert isinstance(context, dict)
        assert "today_events" in context
        assert "recent_events" in context
        assert "active_arcs" in context
        assert "mood" in context

    @pytest.mark.asyncio
    async def test_formats_today_events(self, simulator, user_id):
        """Today events are formatted as strings."""
        context = await simulator.get_events_for_context(user_id)

        assert len(context["today_events"]) == 1
        assert "Morning: Design review with Lisa" in context["today_events"][0]

    @pytest.mark.asyncio
    async def test_excludes_today_from_recent(self, simulator, user_id):
        """Recent events exclude today's events."""
        context = await simulator.get_events_for_context(user_id)

        # Should have yesterday's event, not today's
        assert len(context["recent_events"]) == 1
        assert "Coffee with Ana" in context["recent_events"][0]

    @pytest.mark.asyncio
    async def test_formats_active_arcs(self, simulator, user_id):
        """Active arcs are formatted as strings."""
        context = await simulator.get_events_for_context(user_id)

        assert len(context["active_arcs"]) == 1
        assert "Project Deadline" in context["active_arcs"][0]
        assert "Deadline approaching" in context["active_arcs"][0]

    @pytest.mark.asyncio
    async def test_includes_mood_summary(self, simulator, user_id):
        """Context includes mood summary."""
        context = await simulator.get_events_for_context(user_id)

        assert "summary" in context["mood"]
        assert context["mood"]["valence"] == 0.7
        assert context["mood"]["arousal"] == 0.6


class TestMoodSummary:
    """Tests for mood summary generation."""

    @pytest.fixture
    def simulator(self):
        """Create simulator."""
        return LifeSimulator()

    def test_positive_valence(self, simulator):
        """High valence returns 'feeling good'."""
        mood = MoodState(arousal=0.5, valence=0.8, dominance=0.5, intimacy=0.5)

        summary = simulator._summarize_mood(mood)

        assert "feeling good" in summary

    def test_negative_valence(self, simulator):
        """Low valence returns 'a bit down'."""
        mood = MoodState(arousal=0.5, valence=0.2, dominance=0.5, intimacy=0.5)

        summary = simulator._summarize_mood(mood)

        assert "bit down" in summary

    def test_high_arousal(self, simulator):
        """High arousal returns 'energetic'."""
        mood = MoodState(arousal=0.8, valence=0.5, dominance=0.5, intimacy=0.5)

        summary = simulator._summarize_mood(mood)

        assert "energetic" in summary

    def test_low_arousal(self, simulator):
        """Low arousal returns 'tired'."""
        mood = MoodState(arousal=0.2, valence=0.5, dominance=0.5, intimacy=0.5)

        summary = simulator._summarize_mood(mood)

        assert "tired" in summary

    def test_high_dominance(self, simulator):
        """High dominance returns 'confident'."""
        mood = MoodState(arousal=0.5, valence=0.5, dominance=0.8, intimacy=0.5)

        summary = simulator._summarize_mood(mood)

        assert "confident" in summary

    def test_low_dominance(self, simulator):
        """Low dominance returns 'uncertain'."""
        mood = MoodState(arousal=0.5, valence=0.5, dominance=0.2, intimacy=0.5)

        summary = simulator._summarize_mood(mood)

        assert "uncertain" in summary


class TestGetLifeSimulator:
    """Tests for singleton factory."""

    def setup_method(self):
        import nikita.life_simulation.simulator as sim_module
        import nikita.life_simulation.store as store_module
        sim_module._default_simulator = None
        store_module._default_store = None

    def teardown_method(self):
        import nikita.life_simulation.simulator as sim_module
        import nikita.life_simulation.store as store_module
        sim_module._default_simulator = None
        store_module._default_store = None

    def test_singleton_pattern(self):
        """get_life_simulator returns same instance."""
        from unittest.mock import patch

        with patch("nikita.life_simulation.store.get_session_maker"):
            sim1 = get_life_simulator()
            sim2 = get_life_simulator()

            assert sim1 is sim2
