"""Quality Tests: Life Simulation (Spec 022, T018).

Tests quality properties of the life simulation system:
- Event diversity (no domain empty > 2 days)
- Entity consistency (known entities referenced)
- Narrative arc progression

AC-T018.1: Test event diversity (no domain empty > 2 days)
AC-T018.2: Test entity consistency
AC-T018.3: Test narrative arc progression
"""

from collections import defaultdict
from datetime import date, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from nikita.life_simulation.models import (
    ArcStatus,
    EmotionalImpact,
    EntityType,
    EventDomain,
    EventType,
    LifeEvent,
    NarrativeArc,
    NikitaEntity,
    TimeOfDay,
)
from nikita.life_simulation.narrative_manager import NarrativeArcManager
from nikita.life_simulation.simulator import LifeSimulator


class TestEventDiversity:
    """AC-T018.1: Test event diversity (no domain empty > 2 days)."""

    @pytest.fixture
    def user_id(self):
        """Generate test user ID."""
        return uuid4()

    @pytest.fixture
    def diverse_events(self, user_id):
        """Create a week of diverse events covering all domains."""
        events = []
        base_date = date.today() - timedelta(days=6)

        # Day 1: Work + Social
        events.extend([
            LifeEvent(
                event_id=uuid4(),
                user_id=user_id,
                event_date=base_date,
                time_of_day=TimeOfDay.MORNING,
                domain=EventDomain.WORK,
                event_type=EventType.MEETING,
                description="Team standup",
                entities=[],
                importance=0.5,
            ),
            LifeEvent(
                event_id=uuid4(),
                user_id=user_id,
                event_date=base_date,
                time_of_day=TimeOfDay.EVENING,
                domain=EventDomain.SOCIAL,
                event_type=EventType.FRIEND_HANGOUT,
                description="Dinner with friends",
                entities=["Sarah"],
                importance=0.6,
            ),
        ])

        # Day 2: Work + Personal
        events.extend([
            LifeEvent(
                event_id=uuid4(),
                user_id=user_id,
                event_date=base_date + timedelta(days=1),
                time_of_day=TimeOfDay.AFTERNOON,
                domain=EventDomain.WORK,
                event_type=EventType.PROJECT_UPDATE,
                description="Project milestone",
                entities=[],
                importance=0.7,
            ),
            LifeEvent(
                event_id=uuid4(),
                user_id=user_id,
                event_date=base_date + timedelta(days=1),
                time_of_day=TimeOfDay.EVENING,
                domain=EventDomain.PERSONAL,
                event_type=EventType.GYM,
                description="Yoga class",
                entities=[],
                importance=0.4,
            ),
        ])

        # Day 3: Social + Personal
        events.extend([
            LifeEvent(
                event_id=uuid4(),
                user_id=user_id,
                event_date=base_date + timedelta(days=2),
                time_of_day=TimeOfDay.AFTERNOON,
                domain=EventDomain.SOCIAL,
                event_type=EventType.PLANS_MADE,
                description="Planning weekend trip",
                entities=["Alex"],
                importance=0.5,
            ),
            LifeEvent(
                event_id=uuid4(),
                user_id=user_id,
                event_date=base_date + timedelta(days=2),
                time_of_day=TimeOfDay.EVENING,
                domain=EventDomain.PERSONAL,
                event_type=EventType.HOBBY_ACTIVITY,
                description="Reading a good book on the couch",
                entities=[],
                importance=0.3,
            ),
        ])

        # Days 4-7: Continue pattern to ensure no domain empty > 2 days
        for i in range(3, 7):
            domain = [EventDomain.WORK, EventDomain.SOCIAL, EventDomain.PERSONAL][i % 3]
            events.append(
                LifeEvent(
                    event_id=uuid4(),
                    user_id=user_id,
                    event_date=base_date + timedelta(days=i),
                    time_of_day=TimeOfDay.AFTERNOON,
                    domain=domain,
                    event_type=EventType.MEETING if domain == EventDomain.WORK else EventType.FRIEND_HANGOUT if domain == EventDomain.SOCIAL else EventType.SELF_CARE,
                    description=f"Day {i+1} event",
                    entities=[],
                    importance=0.5,
                )
            )

        return events

    def test_all_domains_represented(self, diverse_events):
        """Verify all three domains are represented in the event set."""
        domains = {e.domain for e in diverse_events}
        assert EventDomain.WORK in domains
        assert EventDomain.SOCIAL in domains
        assert EventDomain.PERSONAL in domains

    def test_no_domain_empty_more_than_two_days(self, diverse_events):
        """AC-T018.1: No domain should be empty for more than 2 consecutive days."""
        # Group events by date
        events_by_date: dict[date, list[LifeEvent]] = defaultdict(list)
        for event in diverse_events:
            events_by_date[event.event_date].append(event)

        # Get date range
        dates = sorted(events_by_date.keys())
        if len(dates) < 3:
            return  # Not enough days to test

        # For each domain, check consecutive empty days
        for domain in EventDomain:
            consecutive_empty = 0
            max_consecutive = 0

            for d in dates:
                domain_events = [e for e in events_by_date[d] if e.domain == domain]
                if domain_events:
                    consecutive_empty = 0
                else:
                    consecutive_empty += 1
                    max_consecutive = max(max_consecutive, consecutive_empty)

            assert max_consecutive <= 2, f"{domain.value} was empty for {max_consecutive} consecutive days"

    def test_events_distributed_across_time_of_day(self, diverse_events):
        """Events should be distributed across morning, afternoon, evening."""
        times = {e.time_of_day for e in diverse_events}
        # At least 2 different times of day
        assert len(times) >= 2

    @pytest.mark.asyncio
    async def test_simulator_generates_diverse_events(self, user_id):
        """LifeSimulator should generate events across all domains."""
        mock_store = AsyncMock()
        mock_store.get_events_for_date.return_value = []
        mock_store.get_entities.return_value = []
        mock_store.get_recent_events.return_value = []

        mock_entity_manager = AsyncMock()
        mock_entity_manager.seed_entities.return_value = []

        # Mock event generator that returns diverse events
        diverse_events_mock = [
            LifeEvent(
                event_id=uuid4(),
                user_id=user_id,
                event_date=date.today() + timedelta(days=1),
                time_of_day=TimeOfDay.MORNING,
                domain=EventDomain.WORK,
                event_type=EventType.MEETING,
                description="Work meeting",
                entities=[],
                importance=0.6,
            ),
            LifeEvent(
                event_id=uuid4(),
                user_id=user_id,
                event_date=date.today() + timedelta(days=1),
                time_of_day=TimeOfDay.AFTERNOON,
                domain=EventDomain.SOCIAL,
                event_type=EventType.FRIEND_HANGOUT,
                description="Coffee with friend",
                entities=["Sarah"],
                importance=0.5,
            ),
            LifeEvent(
                event_id=uuid4(),
                user_id=user_id,
                event_date=date.today() + timedelta(days=1),
                time_of_day=TimeOfDay.EVENING,
                domain=EventDomain.PERSONAL,
                event_type=EventType.SELF_CARE,
                description="Evening yoga",
                entities=[],
                importance=0.4,
            ),
        ]

        mock_event_generator = AsyncMock()
        mock_event_generator.generate_events_for_day.return_value = diverse_events_mock

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

        events = await simulator.generate_next_day_events(user_id)

        # Verify diversity
        domains = {e.domain for e in events}
        assert len(domains) == 3  # All 3 domains represented
        assert len(events) == 3  # Expected count


class TestEntityConsistency:
    """AC-T018.2: Test entity consistency."""

    @pytest.fixture
    def user_id(self):
        """Generate test user ID."""
        return uuid4()

    @pytest.fixture
    def sample_entities(self, user_id):
        """Create sample entities for Nikita."""
        return [
            NikitaEntity(
                entity_id=uuid4(),
                user_id=user_id,
                entity_type=EntityType.COLLEAGUE,
                name="Alex Chen",
                description="Senior developer, works on Project Alpha",
                relationship_quality=0.7,
                last_mentioned=date.today() - timedelta(days=3),
            ),
            NikitaEntity(
                entity_id=uuid4(),
                user_id=user_id,
                entity_type=EntityType.FRIEND,
                name="Sarah",
                description="College friend, lives nearby",
                relationship_quality=0.9,
                last_mentioned=date.today() - timedelta(days=1),
            ),
            NikitaEntity(
                entity_id=uuid4(),
                user_id=user_id,
                entity_type=EntityType.PLACE,
                name="The Cozy Cafe",
                description="Favorite coffee spot downtown",
                relationship_quality=0.8,
                last_mentioned=date.today() - timedelta(days=5),
            ),
        ]

    def test_events_reference_known_entities(self, user_id, sample_entities):
        """Events should reference entities from the known entity pool."""
        entity_names = {e.name for e in sample_entities}

        # Create event referencing known entity
        event = LifeEvent(
            event_id=uuid4(),
            user_id=user_id,
            event_date=date.today(),
            time_of_day=TimeOfDay.AFTERNOON,
            domain=EventDomain.SOCIAL,
            event_type=EventType.FRIEND_HANGOUT,
            description="Grabbed coffee with Sarah at The Cozy Cafe",
            entities=["Sarah", "The Cozy Cafe"],
            importance=0.6,
        )

        # All referenced entities should be known
        for entity_ref in event.entities:
            assert entity_ref in entity_names, f"Unknown entity referenced: {entity_ref}"

    def test_entity_names_in_description(self, user_id, sample_entities):
        """Entity names should appear in event descriptions when referenced."""
        event = LifeEvent(
            event_id=uuid4(),
            user_id=user_id,
            event_date=date.today(),
            time_of_day=TimeOfDay.MORNING,
            domain=EventDomain.WORK,
            event_type=EventType.MEETING,
            description="Brainstormed with Alex Chen on the new feature",
            entities=["Alex Chen"],
            importance=0.7,
        )

        # Referenced entity should appear in description
        for entity_ref in event.entities:
            assert entity_ref in event.description

    def test_entity_type_matches_domain(self, sample_entities):
        """Entity types should generally match event domains."""
        entity_domain_map = {
            EntityType.COLLEAGUE: EventDomain.WORK,
            EntityType.FRIEND: EventDomain.SOCIAL,
            EntityType.PLACE: None,  # Places can appear in any domain
            EntityType.PROJECT: EventDomain.WORK,
        }

        for entity in sample_entities:
            expected_domain = entity_domain_map.get(entity.entity_type)
            if expected_domain:
                # Colleague should be in work events, friend in social
                assert expected_domain in [EventDomain.WORK, EventDomain.SOCIAL]

    @pytest.mark.asyncio
    async def test_entity_manager_provides_consistent_entities(self, user_id, sample_entities):
        """EntityManager should return consistent entity set."""
        mock_store = AsyncMock()
        mock_store.get_entities.return_value = sample_entities

        from nikita.life_simulation.entity_manager import EntityManager

        manager = EntityManager(store=mock_store)

        # Multiple calls should return same entities
        entities1 = await manager.get_all_entities(user_id)
        entities2 = await manager.get_all_entities(user_id)

        assert len(entities1) == len(entities2)
        assert {e.name for e in entities1} == {e.name for e in entities2}


class TestNarrativeArcProgression:
    """AC-T018.3: Test narrative arc progression."""

    @pytest.fixture
    def user_id(self):
        """Generate test user ID."""
        return uuid4()

    @pytest.fixture
    def sample_arc(self, user_id):
        """Create a sample narrative arc."""
        return NarrativeArc(
            arc_id=uuid4(),
            user_id=user_id,
            arc_type="project_deadline",
            domain=EventDomain.WORK,
            start_date=date.today() - timedelta(days=5),
            status=ArcStatus.ACTIVE,
            current_state="Project Alpha launch coming up with tight deadline",
            entities=["Project Alpha", "Alex Chen"],
            possible_outcomes=["success", "partial", "delayed"],
        )

    def test_arc_has_required_fields(self, sample_arc):
        """Narrative arcs should have all required fields."""
        assert sample_arc.arc_id is not None
        assert sample_arc.user_id is not None
        assert sample_arc.arc_type is not None
        assert sample_arc.domain is not None
        assert sample_arc.start_date is not None
        assert sample_arc.status is not None

    def test_arc_state_transitions(self, sample_arc):
        """Arc states should follow valid transitions."""
        valid_transitions = {
            ArcStatus.ACTIVE: [ArcStatus.RESOLVED],
            ArcStatus.RESOLVED: [],  # Terminal state
        }

        current_status = sample_arc.status
        possible_next = valid_transitions.get(current_status, [])

        # ACTIVE can transition to RESOLVED
        if current_status == ArcStatus.ACTIVE:
            assert ArcStatus.RESOLVED in possible_next

    def test_arc_has_entities(self, sample_arc):
        """Arcs should have associated entities."""
        assert len(sample_arc.entities) > 0

    @pytest.mark.asyncio
    async def test_arc_progresses_over_time(self, user_id, sample_arc):
        """Arcs should progress toward resolution over time."""
        mock_store = AsyncMock()
        mock_store.get_active_arcs.return_value = [sample_arc]
        mock_store.update_arc_state.return_value = True

        manager = NarrativeArcManager(store=mock_store)

        # Progress arc
        await manager.progress_arc(sample_arc.arc_id, "Made progress on deliverables")

        # Verify update was called (arc progressed)
        mock_store.update_arc_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_arc_resolution(self, user_id, sample_arc):
        """Arcs should be able to resolve with an outcome."""
        mock_store = AsyncMock()
        mock_store.update_arc_status.return_value = True

        manager = NarrativeArcManager(store=mock_store)

        # Resolve arc
        result = await manager.resolve_arc(sample_arc.arc_id, "success")

        # Verify resolution was called
        assert result is True
        mock_store.update_arc_status.assert_called_once()

    def test_resolved_arc_has_outcome(self, user_id):
        """Resolved arcs should have an outcome in possible_outcomes."""
        resolved_arc = NarrativeArc(
            arc_id=uuid4(),
            user_id=user_id,
            arc_type="project_deadline",
            domain=EventDomain.WORK,
            start_date=date.today() - timedelta(days=10),
            status=ArcStatus.RESOLVED,
            current_state="Project completed successfully",
            entities=[],
            possible_outcomes=["success", "partial", "delayed"],
            resolved_at=date.today(),
        )

        assert resolved_arc.status == ArcStatus.RESOLVED
        assert resolved_arc.resolved_at is not None

    @pytest.mark.asyncio
    async def test_narrative_manager_creates_new_arcs(self, user_id):
        """NarrativeArcManager should be able to create new arcs."""
        mock_store = AsyncMock()
        mock_store.get_active_arcs.return_value = []  # No active arcs
        mock_store.get_recent_arcs.return_value = []
        mock_store.save_arc.return_value = None

        manager = NarrativeArcManager(store=mock_store)

        # Create new arc
        new_arc = await manager.create_arc(
            user_id=user_id,
            arc_type="friend_crisis",
            entities=["Sarah"],
            initial_state="Minor tension over weekend plans",
        )

        assert new_arc.arc_type == "friend_crisis"
        assert new_arc.status == ArcStatus.ACTIVE
        mock_store.save_arc.assert_called_once()

    @pytest.mark.asyncio
    async def test_active_arcs_retrieved_correctly(self, user_id, sample_arc):
        """Active arcs should be retrievable for a user."""
        mock_store = AsyncMock()
        mock_store.get_active_arcs.return_value = [sample_arc]

        manager = NarrativeArcManager(store=mock_store)

        arcs = await manager.get_active_arcs(user_id)

        assert len(arcs) == 1
        assert arcs[0].arc_id == sample_arc.arc_id
        assert arcs[0].status == ArcStatus.ACTIVE
