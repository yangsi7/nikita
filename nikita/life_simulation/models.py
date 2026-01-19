"""Data models for Life Simulation Engine (Spec 022, T002).

AC-T002.1: LifeEvent Pydantic model with all fields
AC-T002.2: NarrativeArc Pydantic model
AC-T002.3: Validation for domains and event types
AC-T002.4: Unit tests for models (in tests/life_simulation/test_models.py)
"""

from datetime import date, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class EventDomain(str, Enum):
    """Domains for Nikita's life events."""

    WORK = "work"
    SOCIAL = "social"
    PERSONAL = "personal"


class EventType(str, Enum):
    """Types of life events per domain.

    Work: project_update, meeting, colleague_interaction, deadline, win, setback
    Social: friend_hangout, friend_drama, plans_made, plans_cancelled, new_person
    Personal: gym, errand, hobby_activity, self_care, health, travel
    """

    # Work events
    PROJECT_UPDATE = "project_update"
    MEETING = "meeting"
    COLLEAGUE_INTERACTION = "colleague_interaction"
    DEADLINE = "deadline"
    WIN = "win"
    SETBACK = "setback"

    # Social events
    FRIEND_HANGOUT = "friend_hangout"
    FRIEND_DRAMA = "friend_drama"
    PLANS_MADE = "plans_made"
    PLANS_CANCELLED = "plans_cancelled"
    NEW_PERSON = "new_person"

    # Personal events
    GYM = "gym"
    ERRAND = "errand"
    HOBBY_ACTIVITY = "hobby_activity"
    SELF_CARE = "self_care"
    HEALTH = "health"
    TRAVEL = "travel"


# Domain to event type mapping for validation
DOMAIN_EVENT_TYPES: dict[EventDomain, list[EventType]] = {
    EventDomain.WORK: [
        EventType.PROJECT_UPDATE,
        EventType.MEETING,
        EventType.COLLEAGUE_INTERACTION,
        EventType.DEADLINE,
        EventType.WIN,
        EventType.SETBACK,
    ],
    EventDomain.SOCIAL: [
        EventType.FRIEND_HANGOUT,
        EventType.FRIEND_DRAMA,
        EventType.PLANS_MADE,
        EventType.PLANS_CANCELLED,
        EventType.NEW_PERSON,
    ],
    EventDomain.PERSONAL: [
        EventType.GYM,
        EventType.ERRAND,
        EventType.HOBBY_ACTIVITY,
        EventType.SELF_CARE,
        EventType.HEALTH,
        EventType.TRAVEL,
    ],
}


class TimeOfDay(str, Enum):
    """Time of day for events."""

    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    NIGHT = "night"


class ArcStatus(str, Enum):
    """Status of a narrative arc."""

    ACTIVE = "active"
    RESOLVED = "resolved"
    ABANDONED = "abandoned"
    ESCALATED = "escalated"


class EntityType(str, Enum):
    """Types of recurring entities in Nikita's life."""

    COLLEAGUE = "colleague"
    FRIEND = "friend"
    PLACE = "place"
    PROJECT = "project"


class EmotionalImpact(BaseModel):
    """Emotional impact of an event on Nikita's mood.

    Each dimension ranges from -0.3 to +0.3 (except intimacy: -0.1 to +0.1).
    """

    arousal_delta: float = Field(default=0.0, ge=-0.3, le=0.3)
    valence_delta: float = Field(default=0.0, ge=-0.3, le=0.3)
    dominance_delta: float = Field(default=0.0, ge=-0.2, le=0.2)
    intimacy_delta: float = Field(default=0.0, ge=-0.1, le=0.1)

    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary."""
        return {
            "arousal_delta": self.arousal_delta,
            "valence_delta": self.valence_delta,
            "dominance_delta": self.dominance_delta,
            "intimacy_delta": self.intimacy_delta,
        }


class LifeEvent(BaseModel):
    """A single life event for Nikita.

    Events are generated daily and represent things that happen in her
    simulated life across work, social, and personal domains.
    """

    event_id: UUID = Field(default_factory=uuid4)
    user_id: UUID  # Events are per-user for personalization
    event_date: date
    time_of_day: TimeOfDay
    domain: EventDomain
    event_type: EventType
    description: str = Field(min_length=10, max_length=500)
    entities: list[str] = Field(default_factory=list)
    emotional_impact: EmotionalImpact = Field(default_factory=EmotionalImpact)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    narrative_arc_id: UUID | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now())

    @field_validator("event_type")
    @classmethod
    def validate_event_type_matches_domain(
        cls, v: EventType, info: Any
    ) -> EventType:
        """Ensure event_type is valid for the domain."""
        domain = info.data.get("domain")
        if domain and v not in DOMAIN_EVENT_TYPES.get(domain, []):
            raise ValueError(
                f"Event type '{v}' is not valid for domain '{domain}'"
            )
        return v

    def model_dump_for_db(self) -> dict[str, Any]:
        """Convert to database-compatible dictionary."""
        return {
            "event_id": str(self.event_id),
            "user_id": str(self.user_id),
            "event_date": self.event_date.isoformat(),
            "time_of_day": self.time_of_day.value,
            "domain": self.domain.value,
            "event_type": self.event_type.value,
            "description": self.description,
            "entities": self.entities,
            "emotional_impact": self.emotional_impact.to_dict(),
            "importance": self.importance,
            "narrative_arc_id": str(self.narrative_arc_id) if self.narrative_arc_id else None,
            "created_at": self.created_at.isoformat(),
        }


class NarrativeArc(BaseModel):
    """A narrative arc that spans multiple days.

    Arcs represent ongoing storylines like a work project, colleague conflict,
    or friend drama. They evolve over time and eventually resolve.
    """

    arc_id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    domain: EventDomain
    arc_type: str = Field(min_length=3, max_length=50)
    status: ArcStatus = ArcStatus.ACTIVE
    start_date: date
    entities: list[str] = Field(default_factory=list)
    current_state: str = Field(default="", max_length=500)
    possible_outcomes: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    resolved_at: datetime | None = None

    def model_dump_for_db(self) -> dict[str, Any]:
        """Convert to database-compatible dictionary."""
        return {
            "arc_id": str(self.arc_id),
            "user_id": str(self.user_id),
            "domain": self.domain.value,
            "arc_type": self.arc_type,
            "status": self.status.value,
            "start_date": self.start_date.isoformat(),
            "entities": self.entities,
            "current_state": self.current_state,
            "possible_outcomes": self.possible_outcomes,
            "created_at": self.created_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }


class NikitaEntity(BaseModel):
    """A recurring entity in Nikita's life.

    Entities are people, places, or projects that appear repeatedly
    in Nikita's life events for consistency and authenticity.
    """

    entity_id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    entity_type: EntityType
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    relationship: str | None = None  # How Nikita relates to this entity
    created_at: datetime = Field(default_factory=lambda: datetime.now())

    def model_dump_for_db(self) -> dict[str, Any]:
        """Convert to database-compatible dictionary."""
        return {
            "entity_id": str(self.entity_id),
            "user_id": str(self.user_id),
            "entity_type": self.entity_type.value,
            "name": self.name,
            "description": self.description,
            "relationship": self.relationship,
            "created_at": self.created_at.isoformat(),
        }
