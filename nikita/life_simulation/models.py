"""Data models for Life Simulation Engine (Spec 022, T002; Spec 055 Enhanced).

AC-T002.1: LifeEvent Pydantic model with all fields
AC-T002.2: NarrativeArc Pydantic model
AC-T002.3: Validation for domains and event types
AC-T002.4: Unit tests for models (in tests/life_simulation/test_models.py)

Spec 055 additions:
- DayRoutine: Per-day routine model
- WeeklyRoutine: Full week routine with YAML loading
"""

from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import yaml
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


# ==================== Spec 055: Routine Models ====================

VALID_DAYS = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
VALID_WORK_SCHEDULES = {"office", "remote", "off"}
VALID_ENERGY_PATTERNS = {"high", "normal", "low"}
VALID_SOCIAL_AVAILABILITY = {"high", "moderate", "low"}


class DayRoutine(BaseModel):
    """Routine for a single day of the week (Spec 055).

    Defines Nikita's schedule, energy level, and availability for a given day.
    Used by EventGenerator to create contextually appropriate events.
    """

    day_of_week: str = Field(description="Day name: monday-sunday")
    wake_time: str = Field(default="08:00", description="Wake time in HH:MM Berlin time")
    activities: list[str] = Field(default_factory=list, description="Planned activities for the day")
    work_schedule: str = Field(default="office", description="office | remote | off")
    energy_pattern: str = Field(default="normal", description="high | normal | low")
    social_availability: str = Field(default="moderate", description="high | moderate | low")

    @field_validator("day_of_week")
    @classmethod
    def validate_day(cls, v: str) -> str:
        """Validate day_of_week is a valid day name."""
        v_lower = v.lower()
        if v_lower not in VALID_DAYS:
            raise ValueError(f"Invalid day_of_week '{v}'. Must be one of: {VALID_DAYS}")
        return v_lower

    @field_validator("work_schedule")
    @classmethod
    def validate_work_schedule(cls, v: str) -> str:
        """Validate work_schedule value."""
        v_lower = v.lower()
        if v_lower not in VALID_WORK_SCHEDULES:
            raise ValueError(f"Invalid work_schedule '{v}'. Must be one of: {VALID_WORK_SCHEDULES}")
        return v_lower

    @field_validator("energy_pattern")
    @classmethod
    def validate_energy(cls, v: str) -> str:
        """Validate energy_pattern value."""
        v_lower = v.lower()
        if v_lower not in VALID_ENERGY_PATTERNS:
            raise ValueError(f"Invalid energy_pattern '{v}'. Must be one of: {VALID_ENERGY_PATTERNS}")
        return v_lower

    @field_validator("social_availability")
    @classmethod
    def validate_social(cls, v: str) -> str:
        """Validate social_availability value."""
        v_lower = v.lower()
        if v_lower not in VALID_SOCIAL_AVAILABILITY:
            raise ValueError(f"Invalid social_availability '{v}'. Must be one of: {VALID_SOCIAL_AVAILABILITY}")
        return v_lower

    def format_for_prompt(self) -> str:
        """Format routine for injection into event generation prompt."""
        activities_str = ", ".join(self.activities) if self.activities else "no specific plans"
        return (
            f"Day: {self.day_of_week.capitalize()}\n"
            f"Wake time: {self.wake_time}\n"
            f"Work: {self.work_schedule}\n"
            f"Energy: {self.energy_pattern}\n"
            f"Social availability: {self.social_availability}\n"
            f"Activities: {activities_str}"
        )


class WeeklyRoutine(BaseModel):
    """Nikita's weekly routine (Spec 055).

    Defines the full week schedule loaded from YAML config or user preferences.
    """

    days: dict[str, DayRoutine] = Field(default_factory=dict)
    timezone: str = Field(default="Europe/Berlin")

    @field_validator("days")
    @classmethod
    def validate_days_keys(cls, v: dict[str, DayRoutine]) -> dict[str, DayRoutine]:
        """Validate all day keys are valid day names."""
        for key in v:
            if key.lower() not in VALID_DAYS:
                raise ValueError(f"Invalid day key '{key}'. Must be one of: {VALID_DAYS}")
        return {k.lower(): val for k, val in v.items()}

    def get_day(self, day_name: str) -> DayRoutine | None:
        """Get routine for a specific day.

        Args:
            day_name: Day name (e.g., 'monday').

        Returns:
            DayRoutine for that day, or None if not defined.
        """
        return self.days.get(day_name.lower())

    def get_day_for_date(self, target_date: date) -> DayRoutine | None:
        """Get routine for a specific date based on its day of week.

        Args:
            target_date: The date to get routine for.

        Returns:
            DayRoutine for that date's day of week, or None.
        """
        day_name = target_date.strftime("%A").lower()
        return self.get_day(day_name)

    @classmethod
    def from_yaml(cls, path: Path) -> "WeeklyRoutine":
        """Load weekly routine from a YAML file.

        Args:
            path: Path to YAML file.

        Returns:
            WeeklyRoutine instance.

        Raises:
            FileNotFoundError: If file doesn't exist.
            ValueError: If YAML is invalid.
        """
        if not path.exists():
            raise FileNotFoundError(f"Routine config not found at {path}")

        with open(path) as f:
            data = yaml.safe_load(f)

        if not data or "days" not in data:
            raise ValueError(f"Invalid routine config at {path}: missing 'days' key")

        # Convert day dicts to DayRoutine objects
        days = {}
        for day_name, day_config in data["days"].items():
            day_config["day_of_week"] = day_name
            days[day_name.lower()] = DayRoutine(**day_config)

        return cls(
            days=days,
            timezone=data.get("timezone", "Europe/Berlin"),
        )

    @classmethod
    def default(cls) -> "WeeklyRoutine":
        """Get the default weekly routine.

        Loads from the bundled routine.yaml config file.
        Falls back to a minimal hardcoded default if file not found.

        Returns:
            WeeklyRoutine instance.
        """
        config_path = Path(__file__).parent.parent / "config_data" / "life_simulation" / "routine.yaml"
        try:
            return cls.from_yaml(config_path)
        except (FileNotFoundError, ValueError):
            # Minimal fallback
            return cls(
                days={
                    "monday": DayRoutine(day_of_week="monday", work_schedule="office", energy_pattern="normal"),
                    "tuesday": DayRoutine(day_of_week="tuesday", work_schedule="office", energy_pattern="normal"),
                    "wednesday": DayRoutine(day_of_week="wednesday", work_schedule="remote", energy_pattern="normal"),
                    "thursday": DayRoutine(day_of_week="thursday", work_schedule="office", energy_pattern="high"),
                    "friday": DayRoutine(day_of_week="friday", work_schedule="office", energy_pattern="high"),
                    "saturday": DayRoutine(day_of_week="saturday", work_schedule="off", energy_pattern="high", social_availability="high"),
                    "sunday": DayRoutine(day_of_week="sunday", work_schedule="off", energy_pattern="low", social_availability="moderate"),
                },
                timezone="Europe/Berlin",
            )
