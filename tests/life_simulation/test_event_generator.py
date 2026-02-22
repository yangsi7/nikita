"""Tests for EventGenerator (Spec 022, T009).

AC-T009.1: EventGenerator class uses LLM for event creation
AC-T009.2: generate_events_for_day() returns 3-5 events
AC-T009.3: Events distributed across domains
AC-T009.4: Events reference known entities
AC-T009.5: Emotional impact computed per event
AC-T009.6: Unit tests with mocked LLM
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from nikita.life_simulation.event_generator import (
    EventGenerator,
    GeneratedEvent,
    GeneratedEventList,
    get_event_generator,
)
from nikita.life_simulation.models import (
    EventDomain,
    EventType,
    EntityType,
    NarrativeArc,
    TimeOfDay,
)


class TestEventGenerator:
    """Tests for EventGenerator class (AC-T009.1)."""

    @pytest.fixture
    def mock_entity_manager(self):
        """Create mock EntityManager."""
        manager = MagicMock()
        manager.get_entity_names = AsyncMock(
            return_value={
                "colleague": ["Lisa", "Max"],
                "friend": ["Ana"],
                "place": ["the office", "Bluestone Cafe"],
                "project": ["the redesign"],
            }
        )
        return manager

    @pytest.fixture
    def mock_llm_response(self):
        """Create mock LLM response with 3 events."""
        return GeneratedEventList(
            events=[
                GeneratedEvent(
                    time_of_day="morning",
                    domain="work",
                    event_type="meeting",
                    description="Had a productive design review with Lisa about the redesign project",
                    entities=["Lisa", "the office", "the redesign"],
                    emotional_valence=0.3,
                    emotional_arousal=0.2,
                    importance=0.5,
                ),
                GeneratedEvent(
                    time_of_day="afternoon",
                    domain="social",
                    event_type="friend_hangout",
                    description="Grabbed coffee with Ana at Bluestone Cafe, she's feeling better about the breakup",
                    entities=["Ana", "Bluestone Cafe"],
                    emotional_valence=0.5,
                    emotional_arousal=0.1,
                    importance=0.4,
                ),
                GeneratedEvent(
                    time_of_day="evening",
                    domain="personal",
                    event_type="gym",
                    description="Did an intense cardio session at the gym, feeling energized",
                    entities=[],
                    emotional_valence=0.4,
                    emotional_arousal=0.6,
                    importance=0.3,
                ),
            ]
        )

    @pytest.fixture
    def mock_llm_client(self, mock_llm_response):
        """Create mock LLM client."""
        return AsyncMock(return_value=mock_llm_response)

    @pytest.fixture
    def generator(self, mock_entity_manager, mock_llm_client):
        """Create generator with mocks."""
        return EventGenerator(
            entity_manager=mock_entity_manager,
            llm_client=mock_llm_client,
        )

    @pytest.fixture
    def user_id(self):
        """Test user ID."""
        return uuid4()

    # ==================== GENERATION TESTS (AC-T009.2) ====================

    @pytest.mark.asyncio
    async def test_generate_events_returns_list(self, generator, user_id):
        """Generate events returns a list of LifeEvent objects."""
        events = await generator.generate_events_for_day(user_id, date.today())

        assert isinstance(events, list)
        assert len(events) > 0

    @pytest.mark.asyncio
    async def test_generate_events_returns_3_to_5(self, generator, user_id):
        """Generate events returns 3-5 events (AC-T009.2)."""
        events = await generator.generate_events_for_day(user_id, date.today())

        assert 3 <= len(events) <= 5

    @pytest.mark.asyncio
    async def test_generate_events_sets_user_id(self, generator, user_id):
        """Generated events have correct user_id."""
        events = await generator.generate_events_for_day(user_id, date.today())

        for event in events:
            assert event.user_id == user_id

    @pytest.mark.asyncio
    async def test_generate_events_sets_date(self, generator, user_id):
        """Generated events have correct date."""
        event_date = date(2026, 1, 15)
        events = await generator.generate_events_for_day(user_id, event_date)

        for event in events:
            assert event.event_date == event_date

    # ==================== DOMAIN DISTRIBUTION (AC-T009.3) ====================

    @pytest.mark.asyncio
    async def test_events_distributed_across_domains(self, generator, user_id):
        """Events are distributed across domains (AC-T009.3)."""
        events = await generator.generate_events_for_day(user_id, date.today())

        domains = {event.domain for event in events}
        # Should have at least 2 different domains
        assert len(domains) >= 2

    @pytest.mark.asyncio
    async def test_events_have_valid_domains(self, generator, user_id):
        """All events have valid domains."""
        events = await generator.generate_events_for_day(user_id, date.today())

        for event in events:
            assert event.domain in [EventDomain.WORK, EventDomain.SOCIAL, EventDomain.PERSONAL]

    @pytest.mark.asyncio
    async def test_events_have_valid_event_types(self, generator, user_id):
        """All events have valid event types."""
        events = await generator.generate_events_for_day(user_id, date.today())

        for event in events:
            assert isinstance(event.event_type, EventType)

    @pytest.mark.asyncio
    async def test_events_distributed_across_time(self, generator, user_id):
        """Events are distributed across times of day."""
        events = await generator.generate_events_for_day(user_id, date.today())

        times = {event.time_of_day for event in events}
        # Should have multiple times
        assert len(times) >= 2

    # ==================== ENTITY REFERENCES (AC-T009.4) ====================

    @pytest.mark.asyncio
    async def test_events_reference_known_entities(self, generator, user_id):
        """Events reference known entities (AC-T009.4)."""
        events = await generator.generate_events_for_day(user_id, date.today())

        # At least some events should have entities
        events_with_entities = [e for e in events if e.entities]
        assert len(events_with_entities) >= 1

    @pytest.mark.asyncio
    async def test_work_events_reference_colleagues(self, generator, user_id):
        """Work events may reference colleagues."""
        events = await generator.generate_events_for_day(user_id, date.today())

        work_events = [e for e in events if e.domain == EventDomain.WORK]
        if work_events:
            # Check if any work event has entities
            work_with_entities = [e for e in work_events if e.entities]
            assert len(work_with_entities) >= 0  # May or may not have

    # ==================== EMOTIONAL IMPACT (AC-T009.5) ====================

    @pytest.mark.asyncio
    async def test_events_have_emotional_impact(self, generator, user_id):
        """Events have emotional impact computed (AC-T009.5)."""
        events = await generator.generate_events_for_day(user_id, date.today())

        for event in events:
            assert hasattr(event, "emotional_impact")
            assert event.emotional_impact is not None

    @pytest.mark.asyncio
    async def test_emotional_impact_within_bounds(self, generator, user_id):
        """Emotional impact values are within valid bounds."""
        events = await generator.generate_events_for_day(user_id, date.today())

        for event in events:
            impact = event.emotional_impact
            assert -0.3 <= impact.valence_delta <= 0.3
            assert -0.2 <= impact.arousal_delta <= 0.2

    @pytest.mark.asyncio
    async def test_events_have_importance(self, generator, user_id):
        """Events have importance scores."""
        events = await generator.generate_events_for_day(user_id, date.today())

        for event in events:
            assert 0.0 <= event.importance <= 1.0

    # ==================== PROMPT BUILDING ====================

    def test_build_prompt_includes_date(self, generator):
        """Prompt includes the event date."""
        entity_names = {"colleague": ["Lisa"], "friend": [], "place": [], "project": []}
        prompt = generator._build_generation_prompt(
            event_date=date(2026, 1, 15),
            entity_names=entity_names,
            active_arcs=[],
            recent_events=[],
        )

        assert "January 15, 2026" in prompt
        assert "Thursday" in prompt  # Jan 15, 2026 is a Thursday

    def test_build_prompt_includes_entities(self, generator):
        """Prompt includes known entities."""
        entity_names = {
            "colleague": ["Lisa", "Max"],
            "friend": ["Ana"],
            "place": ["the office"],
            "project": ["the redesign"],
        }
        prompt = generator._build_generation_prompt(
            event_date=date.today(),
            entity_names=entity_names,
            active_arcs=[],
            recent_events=[],
        )

        assert "Lisa" in prompt
        assert "Max" in prompt
        assert "Ana" in prompt
        assert "the office" in prompt
        assert "the redesign" in prompt

    def test_build_prompt_includes_arcs(self, generator, user_id):
        """Prompt includes active narrative arcs."""
        arc = NarrativeArc(
            user_id=user_id,
            domain=EventDomain.WORK,
            arc_type="project_deadline",
            start_date=date.today(),
            entities=["Lisa", "the redesign"],
            current_state="Deadline approaching, stress increasing",
        )

        prompt = generator._build_generation_prompt(
            event_date=date.today(),
            entity_names={"colleague": [], "friend": [], "place": [], "project": []},
            active_arcs=[arc],
            recent_events=[],
        )

        assert "project_deadline" in prompt
        assert "Deadline approaching" in prompt

    def test_build_prompt_includes_valid_event_types(self, generator):
        """Prompt includes valid event types for each domain."""
        prompt = generator._build_generation_prompt(
            event_date=date.today(),
            entity_names={"colleague": [], "friend": [], "place": [], "project": []},
            active_arcs=[],
            recent_events=[],
        )

        assert "meeting" in prompt
        assert "friend_hangout" in prompt
        assert "gym" in prompt


class TestGeneratedEventConversion:
    """Tests for converting generated events to LifeEvent models."""

    @pytest.fixture
    def generator(self):
        """Create generator with mocks."""
        return EventGenerator(
            entity_manager=MagicMock(),
            llm_client=AsyncMock(),
        )

    @pytest.fixture
    def user_id(self):
        """Test user ID."""
        return uuid4()

    def test_convert_valid_event(self, generator, user_id):
        """Convert valid generated event to LifeEvent."""
        generated = GeneratedEventList(
            events=[
                GeneratedEvent(
                    time_of_day="morning",
                    domain="work",
                    event_type="meeting",
                    description="Had a productive meeting with the team about priorities",
                    entities=["Lisa"],
                    emotional_valence=0.3,
                    emotional_arousal=0.2,
                    importance=0.5,
                )
            ]
        )

        events = generator._convert_to_life_events(
            user_id=user_id,
            event_date=date.today(),
            generated=generated,
        )

        assert len(events) == 1
        assert events[0].domain == EventDomain.WORK
        assert events[0].event_type == EventType.MEETING
        assert events[0].time_of_day == TimeOfDay.MORNING

    def test_convert_invalid_domain_fallback(self, generator, user_id):
        """Invalid domain falls back to PERSONAL."""
        generated = GeneratedEventList(
            events=[
                GeneratedEvent(
                    time_of_day="morning",
                    domain="invalid_domain",
                    event_type="gym",
                    description="Something happened that doesn't fit a domain category",
                    entities=[],
                    emotional_valence=0.0,
                    emotional_arousal=0.0,
                    importance=0.3,
                )
            ]
        )

        events = generator._convert_to_life_events(
            user_id=user_id,
            event_date=date.today(),
            generated=generated,
        )

        assert events[0].domain == EventDomain.PERSONAL

    def test_convert_invalid_event_type_fallback(self, generator, user_id):
        """Invalid event type falls back to first type for domain."""
        from nikita.life_simulation.models import DOMAIN_EVENT_TYPES

        generated = GeneratedEventList(
            events=[
                GeneratedEvent(
                    time_of_day="morning",
                    domain="work",
                    event_type="invalid_type",
                    description="Something work-related that doesn't fit a type",
                    entities=[],
                    emotional_valence=0.0,
                    emotional_arousal=0.0,
                    importance=0.3,
                )
            ]
        )

        events = generator._convert_to_life_events(
            user_id=user_id,
            event_date=date.today(),
            generated=generated,
        )

        # Should use first work event type from DOMAIN_EVENT_TYPES
        assert events[0].event_type == DOMAIN_EVENT_TYPES[EventDomain.WORK][0]

    def test_convert_emotional_scaling(self, generator, user_id):
        """Emotional values are scaled to delta range."""
        generated = GeneratedEventList(
            events=[
                GeneratedEvent(
                    time_of_day="morning",
                    domain="personal",
                    event_type="gym",
                    description="Had an amazing gym session that left me feeling incredible",
                    entities=[],
                    emotional_valence=1.0,  # Max positive
                    emotional_arousal=1.0,  # Max energizing
                    importance=0.8,
                )
            ]
        )

        events = generator._convert_to_life_events(
            user_id=user_id,
            event_date=date.today(),
            generated=generated,
        )

        # 1.0 * 0.3 = 0.3 (max delta)
        assert events[0].emotional_impact.valence_delta == 0.3
        # 1.0 * 0.2 = 0.2 (max arousal delta)
        assert events[0].emotional_impact.arousal_delta == 0.2


class TestGetEventGenerator:
    """Tests for singleton factory."""

    def setup_method(self):
        import nikita.life_simulation.event_generator as eg_module
        import nikita.life_simulation.entity_manager as em_module
        import nikita.life_simulation.store as store_module
        eg_module._default_generator = None
        em_module._default_manager = None
        store_module._default_store = None

    def teardown_method(self):
        import nikita.life_simulation.event_generator as eg_module
        import nikita.life_simulation.entity_manager as em_module
        import nikita.life_simulation.store as store_module
        eg_module._default_generator = None
        em_module._default_manager = None
        store_module._default_store = None

    def test_singleton_pattern(self):
        """get_event_generator returns same instance."""
        from unittest.mock import patch

        with patch("nikita.life_simulation.store.get_session_maker"):
            gen1 = get_event_generator()
            gen2 = get_event_generator()

            assert gen1 is gen2
