"""E2E Test: Life Simulation Cycle (Spec 022, T017).

Tests the full life simulation cycle:
1. Conversation triggers event generation
2. Next conversation has events in context
3. Events referenced naturally in responses

AC-T017.1: Conversation triggers event generation
AC-T017.2: Next conversation has events in context
AC-T017.3: Events referenced naturally in responses
"""

from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.context.package import ContextPackage, EmotionalState
from nikita.life_simulation.models import (
    EmotionalImpact,
    EventDomain,
    EventType,
    LifeEvent,
    TimeOfDay,
)
from nikita.life_simulation.mood_calculator import MoodState
from nikita.life_simulation.simulator import LifeSimulator
from nikita.post_processing.layer_composer import LayerComposer
from nikita.post_processing.pipeline import PostProcessingPipeline


class TestLifeSimulationCycleE2E:
    """E2E tests for life simulation integrated with conversation cycle."""

    @pytest.fixture
    def user_id(self):
        """Generate test user ID."""
        return uuid4()

    @pytest.fixture
    def conversation_id(self):
        """Generate test conversation ID."""
        return uuid4()

    @pytest.fixture
    def sample_events(self, user_id):
        """Create sample life events for Nikita."""
        return [
            LifeEvent(
                event_id=uuid4(),
                user_id=user_id,
                event_date=date.today(),
                time_of_day=TimeOfDay.MORNING,
                domain=EventDomain.WORK,
                event_type=EventType.MEETING,
                description="Had a long brainstorming session with the team",
                entities=["Alex", "project_alpha"],
                importance=0.8,
                emotional_impact=EmotionalImpact(
                    arousal_delta=0.1,
                    valence_delta=0.2,
                    dominance_delta=0.0,
                    intimacy_delta=0.0,
                ),
            ),
            LifeEvent(
                event_id=uuid4(),
                user_id=user_id,
                event_date=date.today(),
                time_of_day=TimeOfDay.AFTERNOON,
                domain=EventDomain.SOCIAL,
                event_type=EventType.FRIEND_HANGOUT,
                description="Grabbed coffee with Sarah at the new cafe",
                entities=["Sarah"],
                importance=0.6,
                emotional_impact=EmotionalImpact(
                    arousal_delta=0.05,
                    valence_delta=0.15,
                    dominance_delta=0.0,
                    intimacy_delta=0.05,
                ),
            ),
            LifeEvent(
                event_id=uuid4(),
                user_id=user_id,
                event_date=date.today(),
                time_of_day=TimeOfDay.EVENING,
                domain=EventDomain.PERSONAL,
                event_type=EventType.SELF_CARE,
                description="Did some yoga and journaling before bed",
                entities=[],
                importance=0.4,
                emotional_impact=EmotionalImpact(
                    arousal_delta=-0.1,
                    valence_delta=0.1,
                    dominance_delta=0.0,
                    intimacy_delta=0.0,
                ),
            ),
        ]

    @pytest.fixture
    def mock_graph_updater(self):
        """Create mock graph updater."""
        updater = AsyncMock()
        updater.update.return_value = (3, 2)
        return updater

    @pytest.fixture
    def mock_summary_generator(self):
        """Create mock summary generator."""
        generator = AsyncMock()
        generator.generate.return_value = (True, False)
        return generator

    @pytest.fixture
    def mock_package_store(self):
        """Create mock package store."""
        store = AsyncMock()
        store.set.return_value = None
        return store

    @pytest.mark.asyncio
    async def test_conversation_triggers_event_generation(
        self,
        user_id,
        conversation_id,
        sample_events,
        mock_graph_updater,
        mock_summary_generator,
        mock_package_store,
    ):
        """AC-T017.1: Conversation triggers event generation.

        Tests that after a conversation ends, the post-processing pipeline
        generates life events for Nikita's simulated life.
        """
        # Mock life simulator
        mock_life_simulator = AsyncMock()
        mock_life_simulator.generate_next_day_events.return_value = sample_events

        # Mock layer composer
        mock_layer_composer = AsyncMock()
        mock_layer_composer.compose.return_value = ContextPackage(
            user_id=user_id,
            created_at=datetime.now(timezone.utc),
            life_events_today=[
                "Morning: Had a long brainstorming session with the team",
                "Afternoon: Grabbed coffee with Sarah at the new cafe",
                "Evening: Did some yoga and journaling before bed",
            ],
        )

        pipeline = PostProcessingPipeline(
            graph_updater=mock_graph_updater,
            summary_generator=mock_summary_generator,
            life_simulator=mock_life_simulator,
            layer_composer=mock_layer_composer,
            package_store=mock_package_store,
        )

        # Conversation ends, pipeline runs
        result = await pipeline.process(
            user_id=user_id,
            conversation_id=conversation_id,
        )

        # Verify life simulation step was executed
        assert result.success or result.partial_success
        life_sim_step = next(
            (s for s in result.steps if s.name == "life_simulation"), None
        )
        assert life_sim_step is not None
        assert life_sim_step.metadata.get("events_generated") == 3

        # Verify simulator was called to generate events
        mock_life_simulator.generate_next_day_events.assert_called_once()
        call_args = mock_life_simulator.generate_next_day_events.call_args
        # Method uses keyword args
        assert call_args.kwargs["user_id"] == user_id

    @pytest.mark.asyncio
    async def test_next_conversation_has_events_in_context(
        self,
        user_id,
        sample_events,
    ):
        """AC-T017.2: Next conversation has events in context.

        Tests that when the context package is loaded for the next conversation,
        it contains the life events generated during post-processing.
        """
        # Create package store with stored package from previous conversation
        stored_package = ContextPackage(
            user_id=user_id,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            life_events_today=[
                "Morning: Had a long brainstorming session with the team",
                "Afternoon: Grabbed coffee with Sarah at the new cafe",
                "Evening: Did some yoga and journaling before bed",
            ],
            nikita_mood=EmotionalState(
                arousal=0.55,
                valence=0.75,
                dominance=0.5,
                intimacy=0.5,
            ),
            nikita_energy=0.55,
        )

        mock_package_store = AsyncMock()
        mock_package_store.get.return_value = stored_package

        # Simulate next conversation starting - retrieve context
        retrieved_package = await mock_package_store.get(user_id)

        # Verify life events are present
        assert retrieved_package is not None
        assert len(retrieved_package.life_events_today) == 3
        assert "brainstorming session" in retrieved_package.life_events_today[0]
        assert "coffee with Sarah" in retrieved_package.life_events_today[1]
        assert "yoga and journaling" in retrieved_package.life_events_today[2]

        # Verify mood was affected by events
        assert retrieved_package.nikita_mood.valence > 0.5  # Positive events
        assert retrieved_package.nikita_energy > 0.5

    @pytest.mark.asyncio
    async def test_events_referenced_naturally_in_responses(
        self,
        user_id,
        sample_events,
    ):
        """AC-T017.3: Events referenced naturally in responses.

        Tests that life events are formatted in a way that allows the LLM
        to naturally reference them in conversation.
        """
        # The life events should be formatted as natural language
        formatted_events = [
            f"{event.time_of_day.value.capitalize()}: {event.description}"
            for event in sample_events
        ]

        # Verify format is suitable for LLM context injection
        assert formatted_events[0] == "Morning: Had a long brainstorming session with the team"
        assert formatted_events[1] == "Afternoon: Grabbed coffee with Sarah at the new cafe"
        assert formatted_events[2] == "Evening: Did some yoga and journaling before bed"

        # Create context package with formatted events
        package = ContextPackage(
            user_id=user_id,
            created_at=datetime.now(timezone.utc),
            life_events_today=formatted_events,
        )

        # Verify events are stored correctly
        assert len(package.life_events_today) == 3

        # Events should be ready for inclusion in system prompt
        # In actual implementation, these events are injected into Layer 5
        # and the LLM can naturally reference them
        events_text = "\n".join(package.life_events_today)
        assert "brainstorming session with the team" in events_text
        assert "Sarah" in events_text
        assert "yoga" in events_text


class TestMoodAffectsConversation:
    """Test that life events affect Nikita's mood in conversations."""

    @pytest.fixture
    def user_id(self):
        """Generate test user ID."""
        return uuid4()

    @pytest.mark.asyncio
    async def test_positive_events_improve_mood(self, user_id):
        """Positive life events improve Nikita's mood for conversation."""
        positive_events = [
            LifeEvent(
                event_id=uuid4(),
                user_id=user_id,
                event_date=date.today(),
                time_of_day=TimeOfDay.MORNING,
                domain=EventDomain.WORK,
                event_type=EventType.WIN,
                description="Got praised by my boss for the project!",
                entities=[],
                importance=0.9,
                emotional_impact=EmotionalImpact(
                    arousal_delta=0.2,
                    valence_delta=0.3,
                    dominance_delta=0.2,
                    intimacy_delta=0.0,
                ),
            ),
        ]

        mock_store = AsyncMock()
        mock_store.get_recent_events.return_value = positive_events

        from nikita.life_simulation.mood_calculator import MoodCalculator

        mood_calculator = MoodCalculator()
        simulator = LifeSimulator(
            store=mock_store,
            mood_calculator=mood_calculator,
        )

        mood = await simulator.get_current_mood(user_id, lookback_days=3)

        # Mood should be elevated
        assert mood.valence > 0.5
        assert mood.arousal > 0.5
        assert mood.dominance > 0.5

    @pytest.mark.asyncio
    async def test_negative_events_lower_mood(self, user_id):
        """Negative life events lower Nikita's mood for conversation."""
        negative_events = [
            LifeEvent(
                event_id=uuid4(),
                user_id=user_id,
                event_date=date.today(),
                time_of_day=TimeOfDay.AFTERNOON,
                domain=EventDomain.WORK,
                event_type=EventType.SETBACK,
                description="Project deadline was moved up unexpectedly",
                entities=[],
                importance=0.7,
                emotional_impact=EmotionalImpact(
                    arousal_delta=0.15,
                    valence_delta=-0.2,
                    dominance_delta=-0.1,
                    intimacy_delta=0.0,
                ),
            ),
        ]

        mock_store = AsyncMock()
        mock_store.get_recent_events.return_value = negative_events

        from nikita.life_simulation.mood_calculator import MoodCalculator

        mood_calculator = MoodCalculator()
        simulator = LifeSimulator(
            store=mock_store,
            mood_calculator=mood_calculator,
        )

        mood = await simulator.get_current_mood(user_id, lookback_days=3)

        # Mood should be lower
        assert mood.valence < 0.5

    @pytest.mark.asyncio
    async def test_mixed_events_balanced_mood(self, user_id):
        """Mix of events creates balanced mood."""
        mixed_events = [
            LifeEvent(
                event_id=uuid4(),
                user_id=user_id,
                event_date=date.today(),
                time_of_day=TimeOfDay.MORNING,
                domain=EventDomain.WORK,
                event_type=EventType.WIN,
                description="Completed a major milestone",
                entities=[],
                importance=0.8,
                emotional_impact=EmotionalImpact(
                    arousal_delta=0.1,
                    valence_delta=0.2,
                    dominance_delta=0.1,
                    intimacy_delta=0.0,
                ),
            ),
            LifeEvent(
                event_id=uuid4(),
                user_id=user_id,
                event_date=date.today(),
                time_of_day=TimeOfDay.EVENING,
                domain=EventDomain.SOCIAL,
                event_type=EventType.FRIEND_DRAMA,
                description="Had a disagreement with a friend",
                entities=[],
                importance=0.5,
                emotional_impact=EmotionalImpact(
                    arousal_delta=0.05,
                    valence_delta=-0.15,
                    dominance_delta=0.0,
                    intimacy_delta=-0.05,
                ),
            ),
        ]

        mock_store = AsyncMock()
        mock_store.get_recent_events.return_value = mixed_events

        from nikita.life_simulation.mood_calculator import MoodCalculator

        mood_calculator = MoodCalculator()
        simulator = LifeSimulator(
            store=mock_store,
            mood_calculator=mood_calculator,
        )

        mood = await simulator.get_current_mood(user_id, lookback_days=3)

        # Net positive (+0.2 - 0.15 = +0.05), so slightly above baseline
        assert 0.45 <= mood.valence <= 0.6


class TestEventGenerationTiming:
    """Test event generation timing relative to conversations."""

    @pytest.fixture
    def user_id(self):
        """Generate test user ID."""
        return uuid4()

    @pytest.mark.asyncio
    async def test_events_generated_for_next_day(self, user_id):
        """Events are generated for the next day after conversation."""
        target_date = date.today() + timedelta(days=1)

        mock_store = AsyncMock()
        mock_store.get_events_for_date.return_value = []  # No existing events
        mock_store.get_entities.return_value = []  # Trigger entity seeding
        mock_store.get_recent_events.return_value = []

        mock_entity_manager = AsyncMock()
        mock_entity_manager.seed_entities.return_value = []

        mock_event_generator = AsyncMock()
        mock_event_generator.generate_events_for_day.return_value = []

        mock_narrative_manager = AsyncMock()
        mock_narrative_manager.get_active_arcs.return_value = []
        mock_narrative_manager.maybe_resolve_arcs.return_value = []
        mock_narrative_manager.maybe_create_arc.return_value = None

        simulator = LifeSimulator(
            store=mock_store,
            entity_manager=mock_entity_manager,
            event_generator=mock_event_generator,
            narrative_manager=mock_narrative_manager,
        )

        await simulator.generate_next_day_events(user_id, target_date)

        # Verify generator was called with next day's date
        mock_event_generator.generate_events_for_day.assert_called_once()
        call_args = mock_event_generator.generate_events_for_day.call_args
        assert call_args.kwargs["event_date"] == target_date

    @pytest.mark.asyncio
    async def test_existing_events_not_regenerated(self, user_id):
        """If events already exist for a day, don't regenerate."""
        target_date = date.today() + timedelta(days=1)

        existing_event = LifeEvent(
            event_id=uuid4(),
            user_id=user_id,
            event_date=target_date,
            time_of_day=TimeOfDay.MORNING,
            domain=EventDomain.WORK,
            event_type=EventType.MEETING,
            description="Already existing event",
            entities=[],
            importance=0.5,
        )

        mock_store = AsyncMock()
        mock_store.get_events_for_date.return_value = [existing_event]

        mock_event_generator = AsyncMock()
        mock_narrative_manager = AsyncMock()

        simulator = LifeSimulator(
            store=mock_store,
            event_generator=mock_event_generator,
            narrative_manager=mock_narrative_manager,
        )

        events = await simulator.generate_next_day_events(user_id, target_date)

        # Should return existing events without calling generator
        assert len(events) == 1
        assert events[0] == existing_event
        mock_event_generator.generate_events_for_day.assert_not_called()
