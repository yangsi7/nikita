"""Tests for EventStore (Spec 022, T004).

AC-T004.1: EventStore class with CRUD operations
AC-T004.2: get_events_for_date() method
AC-T004.3: get_recent_events() method (7-day lookback)
AC-T004.4: Unit tests for store
"""

from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
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
from nikita.life_simulation.store import EventStore, get_event_store


class TestEventStore:
    """Tests for EventStore class (AC-T004.1)."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.fixture
    def mock_session_factory(self, mock_session):
        """Create mock session factory."""

        class MockContextManager:
            async def __aenter__(self):
                return mock_session

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        def factory():
            return MockContextManager()

        return factory

    @pytest.fixture
    def store(self, mock_session_factory):
        """Create store with mock session."""
        return EventStore(session_factory=mock_session_factory)

    @pytest.fixture
    def user_id(self):
        """Test user ID."""
        return uuid4()

    @pytest.fixture
    def sample_event(self, user_id):
        """Create sample life event."""
        return LifeEvent(
            user_id=user_id,
            event_date=date.today(),
            time_of_day=TimeOfDay.MORNING,
            domain=EventDomain.WORK,
            event_type=EventType.MEETING,
            description="Had a productive meeting with the team about the project",
            entities=["team", "the project"],
            emotional_impact=EmotionalImpact(valence_delta=0.1),
        )

    @pytest.fixture
    def sample_arc(self, user_id):
        """Create sample narrative arc."""
        return NarrativeArc(
            user_id=user_id,
            domain=EventDomain.WORK,
            arc_type="project_deadline",
            start_date=date.today(),
            entities=["the project", "Lisa"],
            current_state="Project is on track",
        )

    @pytest.fixture
    def sample_entity(self, user_id):
        """Create sample entity."""
        return NikitaEntity(
            user_id=user_id,
            entity_type=EntityType.COLLEAGUE,
            name="Sarah",
            description="Works in marketing",
            relationship="Friendly colleague",
        )

    # ==================== EVENT TESTS ====================

    @pytest.mark.asyncio
    async def test_save_event(self, store, mock_session, sample_event):
        """Save event executes insert."""
        result = await store.save_event(sample_event)

        assert result == sample_event
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_events(self, store, mock_session, user_id):
        """Save multiple events."""
        events = [
            LifeEvent(
                user_id=user_id,
                event_date=date.today(),
                time_of_day=TimeOfDay.MORNING,
                domain=EventDomain.WORK,
                event_type=EventType.MEETING,
                description="Morning meeting with the team about priorities",
            ),
            LifeEvent(
                user_id=user_id,
                event_date=date.today(),
                time_of_day=TimeOfDay.AFTERNOON,
                domain=EventDomain.PERSONAL,
                event_type=EventType.GYM,
                description="Afternoon gym session to clear my head",
            ),
        ]

        result = await store.save_events(events)

        assert len(result) == 2
        assert mock_session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_get_event(self, store, mock_session, sample_event):
        """Get single event by ID (AC-T004.2)."""
        # Mock the database response
        mock_result = MagicMock()
        mock_mappings = MagicMock()
        mock_mappings.first.return_value = {
            "event_id": str(sample_event.event_id),
            "user_id": str(sample_event.user_id),
            "event_date": sample_event.event_date,
            "time_of_day": "morning",
            "domain": "work",
            "event_type": "meeting",
            "description": sample_event.description,
            "entities": ["team", "the project"],
            "emotional_impact": {"arousal_delta": 0, "valence_delta": 0.1, "dominance_delta": 0, "intimacy_delta": 0},
            "importance": 0.5,
            "narrative_arc_id": None,
            "created_at": datetime.now(timezone.utc),
        }
        mock_result.mappings.return_value = mock_mappings
        mock_session.execute.return_value = mock_result

        result = await store.get_event(sample_event.event_id)

        assert result is not None
        assert result.event_id == sample_event.event_id

    @pytest.mark.asyncio
    async def test_get_event_not_found(self, store, mock_session):
        """Get event returns None if not found."""
        mock_result = MagicMock()
        mock_mappings = MagicMock()
        mock_mappings.first.return_value = None
        mock_result.mappings.return_value = mock_mappings
        mock_session.execute.return_value = mock_result

        result = await store.get_event(uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_get_events_for_date(self, store, mock_session, user_id):
        """Get events for specific date (AC-T004.2)."""
        event_date = date.today()

        # Mock response with multiple events
        mock_result = MagicMock()
        mock_mappings = MagicMock()
        mock_mappings.all.return_value = [
            {
                "event_id": str(uuid4()),
                "user_id": str(user_id),
                "event_date": event_date,
                "time_of_day": "morning",
                "domain": "work",
                "event_type": "meeting",
                "description": "Morning standup with the team about priorities",
                "entities": [],
                "emotional_impact": {},
                "importance": 0.5,
                "narrative_arc_id": None,
                "created_at": datetime.now(timezone.utc),
            },
            {
                "event_id": str(uuid4()),
                "user_id": str(user_id),
                "event_date": event_date,
                "time_of_day": "afternoon",
                "domain": "personal",
                "event_type": "gym",
                "description": "Quick gym session to clear my head",
                "entities": [],
                "emotional_impact": {},
                "importance": 0.5,
                "narrative_arc_id": None,
                "created_at": datetime.now(timezone.utc),
            },
        ]
        mock_result.mappings.return_value = mock_mappings
        mock_session.execute.return_value = mock_result

        result = await store.get_events_for_date(user_id, event_date)

        assert len(result) == 2
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_recent_events(self, store, mock_session, user_id):
        """Get events from last 7 days (AC-T004.3)."""
        mock_result = MagicMock()
        mock_mappings = MagicMock()
        mock_mappings.all.return_value = []
        mock_result.mappings.return_value = mock_mappings
        mock_session.execute.return_value = mock_result

        result = await store.get_recent_events(user_id, days=7)

        assert result == []
        # Verify the query included date filter
        call_args = mock_session.execute.call_args
        assert "cutoff_date" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_get_events_by_domain(self, store, mock_session, user_id):
        """Get events filtered by domain."""
        mock_result = MagicMock()
        mock_mappings = MagicMock()
        mock_mappings.all.return_value = []
        mock_result.mappings.return_value = mock_mappings
        mock_session.execute.return_value = mock_result

        result = await store.get_events_by_domain(user_id, EventDomain.WORK)

        assert result == []
        call_args = mock_session.execute.call_args
        assert call_args[0][1]["domain"] == "work"

    @pytest.mark.asyncio
    async def test_delete_old_events(self, store, mock_session, user_id):
        """Delete events older than specified days."""
        mock_result = MagicMock()
        mock_result.rowcount = 5
        mock_session.execute.return_value = mock_result

        count = await store.delete_old_events(user_id, days_to_keep=7)

        assert count == 5
        mock_session.commit.assert_called_once()

    # ==================== ARC TESTS ====================

    @pytest.mark.asyncio
    async def test_save_arc(self, store, mock_session, sample_arc):
        """Save narrative arc."""
        result = await store.save_arc(sample_arc)

        assert result == sample_arc
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_active_arcs(self, store, mock_session, user_id):
        """Get active narrative arcs."""
        mock_result = MagicMock()
        mock_mappings = MagicMock()
        mock_mappings.all.return_value = [
            {
                "arc_id": str(uuid4()),
                "user_id": str(user_id),
                "domain": "work",
                "arc_type": "project_deadline",
                "status": "active",
                "start_date": date.today(),
                "entities": [],
                "current_state": "In progress",
                "possible_outcomes": [],
                "created_at": datetime.now(timezone.utc),
                "resolved_at": None,
            }
        ]
        mock_result.mappings.return_value = mock_mappings
        mock_session.execute.return_value = mock_result

        result = await store.get_active_arcs(user_id)

        assert len(result) == 1
        assert result[0].status == ArcStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_update_arc_status(self, store, mock_session):
        """Update arc status."""
        arc_id = uuid4()
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        success = await store.update_arc_status(
            arc_id,
            ArcStatus.RESOLVED,
            resolved_at=datetime.now(timezone.utc),
        )

        assert success is True
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_arc_state(self, store, mock_session):
        """Update arc current state."""
        arc_id = uuid4()
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        success = await store.update_arc_state(
            arc_id, "Project deadline extended by 2 weeks"
        )

        assert success is True

    # ==================== ENTITY TESTS ====================

    @pytest.mark.asyncio
    async def test_save_entity(self, store, mock_session, sample_entity):
        """Save entity."""
        result = await store.save_entity(sample_entity)

        assert result == sample_entity
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_entities(self, store, mock_session, user_id):
        """Save multiple entities."""
        entities = [
            NikitaEntity(
                user_id=user_id,
                entity_type=EntityType.COLLEAGUE,
                name="Sarah",
            ),
            NikitaEntity(
                user_id=user_id,
                entity_type=EntityType.FRIEND,
                name="Ana",
            ),
        ]

        result = await store.save_entities(entities)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_entities(self, store, mock_session, user_id):
        """Get all entities for user."""
        mock_result = MagicMock()
        mock_mappings = MagicMock()
        mock_mappings.all.return_value = [
            {
                "entity_id": str(uuid4()),
                "user_id": str(user_id),
                "entity_type": "colleague",
                "name": "Sarah",
                "description": "Marketing",
                "relationship": "Friendly",
                "created_at": datetime.now(timezone.utc),
            }
        ]
        mock_result.mappings.return_value = mock_mappings
        mock_session.execute.return_value = mock_result

        result = await store.get_entities(user_id)

        assert len(result) == 1
        assert result[0].name == "Sarah"

    @pytest.mark.asyncio
    async def test_get_entities_by_type(self, store, mock_session, user_id):
        """Get entities filtered by type."""
        mock_result = MagicMock()
        mock_mappings = MagicMock()
        mock_mappings.all.return_value = []
        mock_result.mappings.return_value = mock_mappings
        mock_session.execute.return_value = mock_result

        result = await store.get_entities_by_type(user_id, EntityType.COLLEAGUE)

        assert result == []
        call_args = mock_session.execute.call_args
        assert call_args[0][1]["entity_type"] == "colleague"

    @pytest.mark.asyncio
    async def test_entity_exists(self, store, mock_session, user_id):
        """Check if entity exists."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1
        mock_session.execute.return_value = mock_result

        exists = await store.entity_exists(user_id, "Sarah")

        assert exists is True

    @pytest.mark.asyncio
    async def test_entity_not_exists(self, store, mock_session, user_id):
        """Check entity doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_session.execute.return_value = mock_result

        exists = await store.entity_exists(user_id, "Unknown")

        assert exists is False


class TestGetEventStore:
    """Tests for singleton factory."""

    def setup_method(self):
        import nikita.life_simulation.store as store_module
        store_module._default_store = None

    def teardown_method(self):
        import nikita.life_simulation.store as store_module
        store_module._default_store = None

    def test_singleton_pattern(self):
        """get_event_store returns same instance."""
        from unittest.mock import patch

        with patch("nikita.life_simulation.store.get_session_maker"):
            store1 = get_event_store()
            store2 = get_event_store()

            assert store1 is store2
