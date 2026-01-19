"""Tests for Life Simulation data models (Spec 022, T002).

AC-T002.1: LifeEvent Pydantic model with all fields
AC-T002.2: NarrativeArc Pydantic model
AC-T002.3: Validation for domains and event types
AC-T002.4: Unit tests for models
"""

from datetime import date, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

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
    DOMAIN_EVENT_TYPES,
)


class TestEventDomain:
    """Tests for EventDomain enum."""

    def test_all_domains_exist(self):
        """All three domains exist."""
        assert EventDomain.WORK == "work"
        assert EventDomain.SOCIAL == "social"
        assert EventDomain.PERSONAL == "personal"

    def test_domain_count(self):
        """Exactly 3 domains."""
        assert len(EventDomain) == 3


class TestEventType:
    """Tests for EventType enum."""

    def test_work_event_types(self):
        """Work domain has correct event types."""
        work_types = DOMAIN_EVENT_TYPES[EventDomain.WORK]
        assert EventType.PROJECT_UPDATE in work_types
        assert EventType.MEETING in work_types
        assert EventType.COLLEAGUE_INTERACTION in work_types
        assert EventType.DEADLINE in work_types
        assert EventType.WIN in work_types
        assert EventType.SETBACK in work_types
        assert len(work_types) == 6

    def test_social_event_types(self):
        """Social domain has correct event types."""
        social_types = DOMAIN_EVENT_TYPES[EventDomain.SOCIAL]
        assert EventType.FRIEND_HANGOUT in social_types
        assert EventType.FRIEND_DRAMA in social_types
        assert EventType.PLANS_MADE in social_types
        assert EventType.PLANS_CANCELLED in social_types
        assert EventType.NEW_PERSON in social_types
        assert len(social_types) == 5

    def test_personal_event_types(self):
        """Personal domain has correct event types."""
        personal_types = DOMAIN_EVENT_TYPES[EventDomain.PERSONAL]
        assert EventType.GYM in personal_types
        assert EventType.ERRAND in personal_types
        assert EventType.HOBBY_ACTIVITY in personal_types
        assert EventType.SELF_CARE in personal_types
        assert EventType.HEALTH in personal_types
        assert EventType.TRAVEL in personal_types
        assert len(personal_types) == 6


class TestEmotionalImpact:
    """Tests for EmotionalImpact model."""

    def test_default_values(self):
        """Default impact is zero."""
        impact = EmotionalImpact()
        assert impact.arousal_delta == 0.0
        assert impact.valence_delta == 0.0
        assert impact.dominance_delta == 0.0
        assert impact.intimacy_delta == 0.0

    def test_valid_positive_impact(self):
        """Positive impacts within bounds."""
        impact = EmotionalImpact(
            arousal_delta=0.2,
            valence_delta=0.3,
            dominance_delta=0.1,
            intimacy_delta=0.1,
        )
        assert impact.arousal_delta == 0.2
        assert impact.valence_delta == 0.3

    def test_valid_negative_impact(self):
        """Negative impacts within bounds."""
        impact = EmotionalImpact(
            arousal_delta=-0.2,
            valence_delta=-0.3,
            dominance_delta=-0.2,
            intimacy_delta=-0.1,
        )
        assert impact.valence_delta == -0.3

    def test_arousal_out_of_bounds(self):
        """Arousal delta must be within -0.3 to 0.3."""
        with pytest.raises(ValidationError):
            EmotionalImpact(arousal_delta=0.5)

    def test_intimacy_out_of_bounds(self):
        """Intimacy delta must be within -0.1 to 0.1."""
        with pytest.raises(ValidationError):
            EmotionalImpact(intimacy_delta=0.2)

    def test_to_dict(self):
        """Convert to dictionary."""
        impact = EmotionalImpact(arousal_delta=0.1, valence_delta=-0.2)
        result = impact.to_dict()
        assert result["arousal_delta"] == 0.1
        assert result["valence_delta"] == -0.2
        assert "dominance_delta" in result


class TestLifeEvent:
    """Tests for LifeEvent model (AC-T002.1)."""

    @pytest.fixture
    def user_id(self):
        """Test user ID."""
        return uuid4()

    def test_create_work_event(self, user_id):
        """Create a work domain event."""
        event = LifeEvent(
            user_id=user_id,
            event_date=date.today(),
            time_of_day=TimeOfDay.MORNING,
            domain=EventDomain.WORK,
            event_type=EventType.MEETING,
            description="Had a tough meeting with my manager about the redesign",
            entities=["Lisa", "the redesign"],
            importance=0.7,
        )
        assert event.domain == EventDomain.WORK
        assert event.event_type == EventType.MEETING
        assert "Lisa" in event.entities

    def test_create_social_event(self, user_id):
        """Create a social domain event."""
        event = LifeEvent(
            user_id=user_id,
            event_date=date.today(),
            time_of_day=TimeOfDay.EVENING,
            domain=EventDomain.SOCIAL,
            event_type=EventType.FRIEND_HANGOUT,
            description="Grabbed coffee with Ana, she's going through a breakup",
            entities=["Ana"],
        )
        assert event.domain == EventDomain.SOCIAL
        assert event.event_type == EventType.FRIEND_HANGOUT

    def test_create_personal_event(self, user_id):
        """Create a personal domain event."""
        event = LifeEvent(
            user_id=user_id,
            event_date=date.today(),
            time_of_day=TimeOfDay.AFTERNOON,
            domain=EventDomain.PERSONAL,
            event_type=EventType.GYM,
            description="Finally hit the gym after skipping all week, feeling great",
        )
        assert event.domain == EventDomain.PERSONAL
        assert event.event_type == EventType.GYM

    def test_event_type_domain_validation(self, user_id):
        """Event type must match domain (AC-T002.3)."""
        with pytest.raises(ValidationError) as exc_info:
            LifeEvent(
                user_id=user_id,
                event_date=date.today(),
                time_of_day=TimeOfDay.MORNING,
                domain=EventDomain.WORK,
                event_type=EventType.GYM,  # Personal event in work domain
                description="This should fail validation check",
            )
        assert "not valid for domain" in str(exc_info.value)

    def test_description_min_length(self, user_id):
        """Description must be at least 10 characters."""
        with pytest.raises(ValidationError):
            LifeEvent(
                user_id=user_id,
                event_date=date.today(),
                time_of_day=TimeOfDay.MORNING,
                domain=EventDomain.WORK,
                event_type=EventType.MEETING,
                description="Too short",
            )

    def test_importance_bounds(self, user_id):
        """Importance must be between 0.0 and 1.0."""
        with pytest.raises(ValidationError):
            LifeEvent(
                user_id=user_id,
                event_date=date.today(),
                time_of_day=TimeOfDay.MORNING,
                domain=EventDomain.WORK,
                event_type=EventType.MEETING,
                description="A description that is long enough to pass validation",
                importance=1.5,
            )

    def test_default_importance(self, user_id):
        """Default importance is 0.5."""
        event = LifeEvent(
            user_id=user_id,
            event_date=date.today(),
            time_of_day=TimeOfDay.MORNING,
            domain=EventDomain.WORK,
            event_type=EventType.MEETING,
            description="A description that is long enough to pass validation",
        )
        assert event.importance == 0.5

    def test_event_id_auto_generated(self, user_id):
        """Event ID is auto-generated if not provided."""
        event = LifeEvent(
            user_id=user_id,
            event_date=date.today(),
            time_of_day=TimeOfDay.MORNING,
            domain=EventDomain.WORK,
            event_type=EventType.MEETING,
            description="A description that is long enough to pass validation",
        )
        assert event.event_id is not None

    def test_model_dump_for_db(self, user_id):
        """Convert to database-compatible dictionary."""
        event = LifeEvent(
            user_id=user_id,
            event_date=date.today(),
            time_of_day=TimeOfDay.MORNING,
            domain=EventDomain.WORK,
            event_type=EventType.MEETING,
            description="A description that is long enough to pass validation",
            entities=["Lisa"],
            emotional_impact=EmotionalImpact(valence_delta=-0.2),
        )
        db_dict = event.model_dump_for_db()
        assert db_dict["user_id"] == str(user_id)
        assert db_dict["domain"] == "work"
        assert db_dict["event_type"] == "meeting"
        assert db_dict["emotional_impact"]["valence_delta"] == -0.2


class TestNarrativeArc:
    """Tests for NarrativeArc model (AC-T002.2)."""

    @pytest.fixture
    def user_id(self):
        """Test user ID."""
        return uuid4()

    def test_create_arc(self, user_id):
        """Create a narrative arc."""
        arc = NarrativeArc(
            user_id=user_id,
            domain=EventDomain.WORK,
            arc_type="project_deadline",
            start_date=date.today(),
            entities=["the redesign", "Lisa"],
            current_state="Project is behind schedule, Lisa is stressed",
            possible_outcomes=["Complete on time", "Request extension", "Project fails"],
        )
        assert arc.status == ArcStatus.ACTIVE
        assert arc.domain == EventDomain.WORK
        assert "the redesign" in arc.entities

    def test_arc_status_transitions(self, user_id):
        """Arc status can be updated."""
        arc = NarrativeArc(
            user_id=user_id,
            domain=EventDomain.SOCIAL,
            arc_type="friend_drama",
            start_date=date.today(),
            status=ArcStatus.RESOLVED,
            resolved_at=datetime.now(),
        )
        assert arc.status == ArcStatus.RESOLVED
        assert arc.resolved_at is not None

    def test_arc_type_min_length(self, user_id):
        """Arc type must be at least 3 characters."""
        with pytest.raises(ValidationError):
            NarrativeArc(
                user_id=user_id,
                domain=EventDomain.WORK,
                arc_type="ab",  # Too short
                start_date=date.today(),
            )

    def test_model_dump_for_db(self, user_id):
        """Convert to database-compatible dictionary."""
        arc = NarrativeArc(
            user_id=user_id,
            domain=EventDomain.WORK,
            arc_type="project_deadline",
            start_date=date.today(),
        )
        db_dict = arc.model_dump_for_db()
        assert db_dict["user_id"] == str(user_id)
        assert db_dict["domain"] == "work"
        assert db_dict["status"] == "active"


class TestNikitaEntity:
    """Tests for NikitaEntity model."""

    @pytest.fixture
    def user_id(self):
        """Test user ID."""
        return uuid4()

    def test_create_colleague(self, user_id):
        """Create a colleague entity."""
        entity = NikitaEntity(
            user_id=user_id,
            entity_type=EntityType.COLLEAGUE,
            name="Sarah",
            description="Works in marketing",
            relationship="Colleague, sometimes annoying but mostly nice",
        )
        assert entity.entity_type == EntityType.COLLEAGUE
        assert entity.name == "Sarah"

    def test_create_friend(self, user_id):
        """Create a friend entity."""
        entity = NikitaEntity(
            user_id=user_id,
            entity_type=EntityType.FRIEND,
            name="Ana",
            description="Best friend since college",
            relationship="Best friend, always there for me",
        )
        assert entity.entity_type == EntityType.FRIEND

    def test_create_place(self, user_id):
        """Create a place entity."""
        entity = NikitaEntity(
            user_id=user_id,
            entity_type=EntityType.PLACE,
            name="Cafe Luna",
            description="Coffee shop near work",
        )
        assert entity.entity_type == EntityType.PLACE

    def test_create_project(self, user_id):
        """Create a project entity."""
        entity = NikitaEntity(
            user_id=user_id,
            entity_type=EntityType.PROJECT,
            name="The redesign",
            description="Major website redesign project",
        )
        assert entity.entity_type == EntityType.PROJECT

    def test_name_required(self, user_id):
        """Name is required."""
        with pytest.raises(ValidationError):
            NikitaEntity(
                user_id=user_id,
                entity_type=EntityType.COLLEAGUE,
                name="",  # Empty name
            )

    def test_model_dump_for_db(self, user_id):
        """Convert to database-compatible dictionary."""
        entity = NikitaEntity(
            user_id=user_id,
            entity_type=EntityType.COLLEAGUE,
            name="Mike",
        )
        db_dict = entity.model_dump_for_db()
        assert db_dict["user_id"] == str(user_id)
        assert db_dict["entity_type"] == "colleague"
        assert db_dict["name"] == "Mike"


class TestTimeOfDay:
    """Tests for TimeOfDay enum."""

    def test_all_times_exist(self):
        """All four times of day exist."""
        assert TimeOfDay.MORNING == "morning"
        assert TimeOfDay.AFTERNOON == "afternoon"
        assert TimeOfDay.EVENING == "evening"
        assert TimeOfDay.NIGHT == "night"


class TestArcStatus:
    """Tests for ArcStatus enum."""

    def test_all_statuses_exist(self):
        """All arc statuses exist."""
        assert ArcStatus.ACTIVE == "active"
        assert ArcStatus.RESOLVED == "resolved"
        assert ArcStatus.ABANDONED == "abandoned"
        assert ArcStatus.ESCALATED == "escalated"
