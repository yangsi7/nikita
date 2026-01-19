"""Integration tests for Life Simulation Engine (Spec 022, T016).

AC-T016.1: Test full event generation pipeline
AC-T016.2: Test context package population
AC-T016.3: Test mood derivation from events
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
    NarrativeArc,
    TimeOfDay,
)
from nikita.life_simulation.mood_calculator import MoodCalculator, MoodState
from nikita.life_simulation.simulator import LifeSimulator
from nikita.post_processing.layer_composer import LayerComposer
from nikita.post_processing.pipeline import PostProcessingPipeline


class TestFullEventGenerationPipeline:
    """AC-T016.1: Test full event generation pipeline."""

    @pytest.mark.asyncio
    async def test_pipeline_generates_events_and_stores(self):
        """Full pipeline: generate events, store, retrieve."""
        user_id = uuid4()
        target_date = date.today() + timedelta(days=1)

        # Mock dependencies
        mock_store = AsyncMock()
        mock_store.get_events_for_date.return_value = []  # No existing events
        mock_store.get_entities.return_value = []  # New user
        mock_store.get_recent_events.return_value = []

        mock_entity_manager = AsyncMock()
        mock_entity_manager.seed_entities.return_value = [
            MagicMock(name="colleague_1"),
            MagicMock(name="colleague_2"),
        ]

        mock_event_generator = AsyncMock()
        generated_events = [
            LifeEvent(
                event_id=uuid4(),
                user_id=user_id,
                event_date=target_date,
                time_of_day=TimeOfDay.MORNING,
                domain=EventDomain.WORK,
                event_type=EventType.PROJECT_UPDATE,
                description="Had a productive team standup meeting",
                entities=["colleague_1"],
                importance=0.6,
            ),
            LifeEvent(
                event_id=uuid4(),
                user_id=user_id,
                event_date=target_date,
                time_of_day=TimeOfDay.AFTERNOON,
                domain=EventDomain.SOCIAL,
                event_type=EventType.FRIEND_HANGOUT,
                description="Coffee chat with Alex at the cafe",
                entities=["colleague_2"],
                importance=0.5,
            ),
            LifeEvent(
                event_id=uuid4(),
                user_id=user_id,
                event_date=target_date,
                time_of_day=TimeOfDay.EVENING,
                domain=EventDomain.PERSONAL,
                event_type=EventType.SELF_CARE,
                description="Journaled about the day and meditated",
                entities=[],
                importance=0.4,
            ),
        ]
        mock_event_generator.generate_events_for_day.return_value = generated_events

        mock_narrative_manager = AsyncMock()
        mock_narrative_manager.get_active_arcs.return_value = []
        mock_narrative_manager.maybe_resolve_arcs.return_value = []
        mock_narrative_manager.maybe_create_arc.return_value = None

        mock_mood_calculator = MagicMock()

        simulator = LifeSimulator(
            store=mock_store,
            entity_manager=mock_entity_manager,
            event_generator=mock_event_generator,
            narrative_manager=mock_narrative_manager,
            mood_calculator=mock_mood_calculator,
        )

        # Execute
        events = await simulator.generate_next_day_events(user_id, target_date)

        # Verify
        assert len(events) == 3
        mock_store.save_events.assert_called_once_with(generated_events)
        mock_entity_manager.seed_entities.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_pipeline_handles_existing_events(self):
        """Pipeline returns existing events instead of regenerating."""
        user_id = uuid4()
        target_date = date.today() + timedelta(days=1)

        existing_events = [
            LifeEvent(
                event_id=uuid4(),
                user_id=user_id,
                event_date=target_date,
                time_of_day=TimeOfDay.MORNING,
                domain=EventDomain.WORK,
                event_type=EventType.MEETING,
                description="Already generated event from morning",
                entities=[],
                importance=0.5,
            ),
        ]

        mock_store = AsyncMock()
        mock_store.get_events_for_date.return_value = existing_events

        mock_event_generator = AsyncMock()

        simulator = LifeSimulator(
            store=mock_store,
            event_generator=mock_event_generator,
        )

        events = await simulator.generate_next_day_events(user_id, target_date)

        assert events == existing_events
        mock_event_generator.generate_events_for_day.assert_not_called()

    @pytest.mark.asyncio
    async def test_pipeline_with_narrative_arcs(self):
        """Pipeline includes active arcs in event generation."""
        user_id = uuid4()
        target_date = date.today() + timedelta(days=1)

        active_arc = NarrativeArc(
            arc_id=uuid4(),
            user_id=user_id,
            arc_type="work_project",
            domain=EventDomain.WORK,
            start_date=date.today() - timedelta(days=3),
            current_state="building",
            entities=["project_alpha"],
        )

        mock_store = AsyncMock()
        mock_store.get_events_for_date.return_value = []
        mock_store.get_entities.return_value = [MagicMock()]  # Has entities
        mock_store.get_recent_events.return_value = []

        mock_event_generator = AsyncMock()
        mock_event_generator.generate_events_for_day.return_value = []

        mock_narrative_manager = AsyncMock()
        mock_narrative_manager.get_active_arcs.return_value = [active_arc]
        mock_narrative_manager.maybe_resolve_arcs.return_value = []
        mock_narrative_manager.maybe_create_arc.return_value = None

        simulator = LifeSimulator(
            store=mock_store,
            event_generator=mock_event_generator,
            narrative_manager=mock_narrative_manager,
        )

        await simulator.generate_next_day_events(user_id, target_date)

        # Verify arcs were passed to event generator
        mock_event_generator.generate_events_for_day.assert_called_once()
        call_args = mock_event_generator.generate_events_for_day.call_args
        assert call_args.kwargs["active_arcs"] == [active_arc]


class TestContextPackagePopulation:
    """AC-T016.2: Test context package population."""

    @pytest.fixture
    def mock_session_context(self):
        """Create mock session context manager."""

        class MockSessionContext:
            def __init__(self, session):
                self.session = session

            async def __aenter__(self):
                return self.session

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        return MockSessionContext

    @pytest.fixture
    def mock_layer_composers(self):
        """Create mock layer composers."""
        mock_layer2 = MagicMock()
        mock_layer2.compose.return_value = "chapter layer text"

        mock_layer3 = MagicMock()
        mock_layer3.compose.return_value = "emotional state layer text"

        mock_layer4 = MagicMock()
        mock_situation = MagicMock()
        mock_situation.situation_type.value = "normal"
        mock_layer4.detect_and_compose.return_value = mock_situation

        mock_layer5 = MagicMock()

        return mock_layer2, mock_layer3, mock_layer4, mock_layer5

    @pytest.mark.asyncio
    async def test_context_package_gets_life_events(
        self, mock_session_context, mock_layer_composers
    ):
        """LayerComposer populates life_events_today from LifeSimulator."""
        user_id = uuid4()
        mock_layer2, mock_layer3, mock_layer4, mock_layer5 = mock_layer_composers

        # Mock life simulator with events
        mock_life_simulator = AsyncMock()
        today_events = [
            MagicMock(
                time_of_day=TimeOfDay.MORNING,
                description="Had a great meeting",
                importance=0.8,
            ),
            MagicMock(
                time_of_day=TimeOfDay.AFTERNOON,
                description="Lunch with a friend",
                importance=0.6,
            ),
            MagicMock(
                time_of_day=TimeOfDay.EVENING,
                description="Watched a movie",
                importance=0.4,
            ),
        ]
        mock_life_simulator.get_today_events.return_value = today_events
        mock_life_simulator.get_current_mood.return_value = MoodState()

        # Mock other dependencies
        mock_session = AsyncMock()
        mock_user = MagicMock()
        mock_user.chapter = 1
        mock_user.updated_at = datetime.now(timezone.utc)
        mock_user.relationship_score = 50

        # Create mock session factory
        mock_session_factory = lambda: mock_session_context(mock_session)

        with patch(
            "nikita.post_processing.layer_composer.UserRepository"
        ) as MockUserRepo:
            MockUserRepo.return_value.get = AsyncMock(return_value=mock_user)

            with patch(
                "nikita.post_processing.layer_composer.ConversationThreadRepository"
            ) as MockThreadRepo:
                MockThreadRepo.return_value.list_open = AsyncMock(return_value=[])

                with patch(
                    "nikita.post_processing.layer_composer.NikitaThoughtRepository"
                ) as MockThoughtRepo:
                    MockThoughtRepo.return_value.list_active = AsyncMock(
                        return_value=[]
                    )

                    with patch(
                        "nikita.post_processing.layer_composer.DailySummaryRepository"
                    ) as MockSummaryRepo:
                        MockSummaryRepo.return_value.get_by_date = AsyncMock(
                            return_value=None
                        )
                        MockSummaryRepo.return_value.get_range = AsyncMock(
                            return_value=[]
                        )

                        composer = LayerComposer(
                            session_factory=mock_session_factory,
                            layer2_composer=mock_layer2,
                            layer3_composer=mock_layer3,
                            layer4_computer=mock_layer4,
                            layer5_injector=mock_layer5,
                            life_simulator=mock_life_simulator,
                        )

                        package = await composer.compose(user_id)

        # Verify life events were formatted
        assert len(package.life_events_today) == 3
        assert "Morning: Had a great meeting" in package.life_events_today
        assert "Afternoon: Lunch with a friend" in package.life_events_today
        assert "Evening: Watched a movie" in package.life_events_today

    @pytest.mark.asyncio
    async def test_context_package_limits_to_top_3(
        self, mock_session_context, mock_layer_composers
    ):
        """LayerComposer gets top 3 events by importance."""
        user_id = uuid4()
        mock_layer2, mock_layer3, mock_layer4, mock_layer5 = mock_layer_composers

        mock_life_simulator = AsyncMock()
        # Return exactly 3 events (already sorted by importance)
        mock_life_simulator.get_today_events.return_value = [
            MagicMock(time_of_day=TimeOfDay.MORNING, description="Important 1"),
            MagicMock(time_of_day=TimeOfDay.AFTERNOON, description="Important 2"),
            MagicMock(time_of_day=TimeOfDay.EVENING, description="Important 3"),
        ]
        mock_life_simulator.get_current_mood.return_value = MoodState()

        mock_session = AsyncMock()
        mock_user = MagicMock()
        mock_user.chapter = 1
        mock_user.updated_at = datetime.now(timezone.utc)
        mock_user.relationship_score = 50

        mock_session_factory = lambda: mock_session_context(mock_session)

        with patch(
            "nikita.post_processing.layer_composer.UserRepository"
        ) as MockUserRepo:
            MockUserRepo.return_value.get = AsyncMock(return_value=mock_user)

            with patch(
                "nikita.post_processing.layer_composer.ConversationThreadRepository"
            ) as MockThreadRepo:
                MockThreadRepo.return_value.list_open = AsyncMock(return_value=[])

                with patch(
                    "nikita.post_processing.layer_composer.NikitaThoughtRepository"
                ) as MockThoughtRepo:
                    MockThoughtRepo.return_value.list_active = AsyncMock(
                        return_value=[]
                    )

                    with patch(
                        "nikita.post_processing.layer_composer.DailySummaryRepository"
                    ) as MockSummaryRepo:
                        MockSummaryRepo.return_value.get_by_date = AsyncMock(
                            return_value=None
                        )
                        MockSummaryRepo.return_value.get_range = AsyncMock(
                            return_value=[]
                        )

                        composer = LayerComposer(
                            session_factory=mock_session_factory,
                            layer2_composer=mock_layer2,
                            layer3_composer=mock_layer3,
                            layer4_computer=mock_layer4,
                            layer5_injector=mock_layer5,
                            life_simulator=mock_life_simulator,
                        )

                        await composer.compose(user_id)

        # Verify get_today_events was called with max_events=3 (at least once)
        # Note: With Spec 023 integration, get_today_events may be called multiple times:
        # 1. For StateComputer (emotional state computation)
        # 2. For life_events_today field in context package
        mock_life_simulator.get_today_events.assert_any_call(
            user_id=user_id,
            max_events=3,
        )


class TestMoodDerivation:
    """AC-T016.3: Test mood derivation from events."""

    @pytest.mark.asyncio
    async def test_mood_derived_from_recent_events(self):
        """LifeSimulator derives mood from recent events."""
        user_id = uuid4()

        # Create events with positive emotional impact
        recent_events = [
            LifeEvent(
                event_id=uuid4(),
                user_id=user_id,
                event_date=date.today(),
                time_of_day=TimeOfDay.MORNING,
                domain=EventDomain.WORK,
                event_type=EventType.WIN,
                description="Got promoted at work today!",
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
        mock_store.get_recent_events.return_value = recent_events

        mood_calculator = MoodCalculator()

        simulator = LifeSimulator(
            store=mock_store,
            mood_calculator=mood_calculator,
        )

        mood = await simulator.get_current_mood(user_id, lookback_days=3)

        # Verify mood was affected by positive event
        assert mood.valence > 0.5  # Positive valence from achievement
        assert mood.arousal > 0.5  # High arousal from achievement

    @pytest.mark.asyncio
    async def test_mood_summarized_as_natural_language(self):
        """LifeSimulator generates mood summary."""
        user_id = uuid4()

        mock_store = AsyncMock()
        mock_store.get_events_for_date.return_value = []
        mock_store.get_recent_events.return_value = []
        mock_store.get_active_arcs.return_value = []

        mock_narrative_manager = AsyncMock()
        mock_narrative_manager.get_active_arcs.return_value = []

        mood_calculator = MoodCalculator()

        simulator = LifeSimulator(
            store=mock_store,
            mood_calculator=mood_calculator,
            narrative_manager=mock_narrative_manager,
        )

        context = await simulator.get_events_for_context(user_id)

        # Verify mood summary exists
        assert "mood" in context
        assert "summary" in context["mood"]
        assert isinstance(context["mood"]["summary"], str)
        assert len(context["mood"]["summary"]) > 0

    @pytest.fixture
    def mock_session_context(self):
        """Create mock session context manager."""

        class MockSessionContext:
            def __init__(self, session):
                self.session = session

            async def __aenter__(self):
                return self.session

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        return MockSessionContext

    @pytest.fixture
    def mock_layer_composers(self):
        """Create mock layer composers."""
        mock_layer2 = MagicMock()
        mock_layer2.compose.return_value = "chapter layer text"

        mock_layer3 = MagicMock()
        mock_layer3.compose.return_value = "emotional state layer text"

        mock_layer4 = MagicMock()
        mock_situation = MagicMock()
        mock_situation.situation_type.value = "normal"
        mock_layer4.detect_and_compose.return_value = mock_situation

        mock_layer5 = MagicMock()

        return mock_layer2, mock_layer3, mock_layer4, mock_layer5

    @pytest.mark.asyncio
    async def test_context_package_mood_from_simulator(
        self, mock_session_context, mock_layer_composers
    ):
        """LayerComposer computes mood via StateComputer (Spec 023).

        With Spec 023 integration, mood is now computed by StateComputer
        from life events, not directly from get_current_mood().
        """
        user_id = uuid4()
        mock_layer2, mock_layer3, mock_layer4, mock_layer5 = mock_layer_composers

        # Mock life simulator with empty events
        mock_life_simulator = AsyncMock()
        mock_life_simulator.get_today_events.return_value = []
        # Note: get_current_mood is deprecated with Spec 023 - mood computed by StateComputer
        mock_life_simulator.get_current_mood.return_value = MoodState(
            arousal=0.7,
            valence=0.8,
            dominance=0.6,
            intimacy=0.5,
        )

        mock_session = AsyncMock()
        mock_user = MagicMock()
        mock_user.chapter = 1
        mock_user.updated_at = datetime.now(timezone.utc)
        mock_user.relationship_score = 50

        mock_session_factory = lambda: mock_session_context(mock_session)

        with patch(
            "nikita.post_processing.layer_composer.UserRepository"
        ) as MockUserRepo:
            MockUserRepo.return_value.get = AsyncMock(return_value=mock_user)

            with patch(
                "nikita.post_processing.layer_composer.ConversationThreadRepository"
            ) as MockThreadRepo:
                MockThreadRepo.return_value.list_open = AsyncMock(return_value=[])

                with patch(
                    "nikita.post_processing.layer_composer.NikitaThoughtRepository"
                ) as MockThoughtRepo:
                    MockThoughtRepo.return_value.list_active = AsyncMock(
                        return_value=[]
                    )

                    with patch(
                        "nikita.post_processing.layer_composer.DailySummaryRepository"
                    ) as MockSummaryRepo:
                        MockSummaryRepo.return_value.get_by_date = AsyncMock(
                            return_value=None
                        )
                        MockSummaryRepo.return_value.get_range = AsyncMock(
                            return_value=[]
                        )

                        composer = LayerComposer(
                            session_factory=mock_session_factory,
                            layer2_composer=mock_layer2,
                            layer3_composer=mock_layer3,
                            layer4_computer=mock_layer4,
                            layer5_injector=mock_layer5,
                            life_simulator=mock_life_simulator,
                        )

                        package = await composer.compose(user_id)

        # Verify mood was computed (by StateComputer with Spec 023)
        # With empty events, base state depends on time-of-day and relationship modifiers
        assert 0.0 <= package.nikita_mood.arousal <= 1.0
        assert 0.0 <= package.nikita_mood.valence <= 1.0
        assert 0.0 <= package.nikita_mood.dominance <= 1.0
        assert 0.0 <= package.nikita_mood.intimacy <= 1.0
        assert package.nikita_energy == package.nikita_mood.arousal  # Energy derived from arousal


class TestPipelineIntegrationWithLifeSimulation:
    """Integration tests for full pipeline with life simulation."""

    @pytest.mark.asyncio
    async def test_full_pipeline_includes_life_simulation_step(self):
        """PostProcessingPipeline includes life simulation step."""
        mock_graph_updater = AsyncMock()
        mock_graph_updater.update.return_value = (1, 1)

        mock_summary_generator = AsyncMock()
        mock_summary_generator.generate.return_value = (True, False)

        mock_life_simulator = AsyncMock()
        mock_life_simulator.generate_next_day_events.return_value = [
            MagicMock(),
            MagicMock(),
        ]

        mock_layer_composer = AsyncMock()
        mock_layer_composer.compose.return_value = ContextPackage(
            user_id=uuid4(),
            created_at=datetime.now(timezone.utc),
        )

        mock_package_store = AsyncMock()

        pipeline = PostProcessingPipeline(
            graph_updater=mock_graph_updater,
            summary_generator=mock_summary_generator,
            life_simulator=mock_life_simulator,
            layer_composer=mock_layer_composer,
            package_store=mock_package_store,
        )

        result = await pipeline.process(
            user_id=uuid4(),
            conversation_id=uuid4(),
        )

        # Verify life simulation step was executed
        assert any(s.name == "life_simulation" for s in result.steps)
        life_sim_step = next(s for s in result.steps if s.name == "life_simulation")
        assert life_sim_step.metadata.get("events_generated") == 2
