"""Event Generator for Life Simulation Engine (Spec 022, T009).

Uses LLM to generate daily life events for Nikita.

AC-T009.1: EventGenerator class uses LLM for event creation
AC-T009.2: generate_events_for_day() returns 3-5 events
AC-T009.3: Events distributed across domains
AC-T009.4: Events reference known entities
AC-T009.5: Emotional impact computed per event
AC-T009.6: Unit tests with mocked LLM
"""

import json
import logging
from datetime import date
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from nikita.life_simulation.models import (
    LifeEvent,
    NarrativeArc,
    NikitaEntity,
    EventDomain,
    EventType,
    TimeOfDay,
    EmotionalImpact,
    DOMAIN_EVENT_TYPES,
)
from nikita.life_simulation.entity_manager import EntityManager, get_entity_manager

logger = logging.getLogger(__name__)


class GeneratedEvent(BaseModel):
    """Schema for LLM-generated event."""

    time_of_day: str = Field(description="morning, afternoon, evening, or night")
    domain: str = Field(description="work, social, or personal")
    event_type: str = Field(description="Specific event type")
    description: str = Field(description="Natural description of what happened (10-100 words)")
    entities: list[str] = Field(default_factory=list, description="Names of people, places, projects involved")
    emotional_valence: float = Field(ge=-1.0, le=1.0, description="Positive or negative? -1 to 1")
    emotional_arousal: float = Field(ge=-1.0, le=1.0, description="Energy level change? -1 to 1")
    importance: float = Field(ge=0.0, le=1.0, description="How significant is this event? 0 to 1")


class GeneratedEventList(BaseModel):
    """Schema for list of generated events."""

    events: list[GeneratedEvent] = Field(default_factory=list)


class EventGenerator:
    """Generates daily life events for Nikita using LLM.

    Events are distributed across work, social, and personal domains.
    References known entities (colleagues, friends, places, projects).
    Computes emotional impact per event.

    Example:
        generator = EventGenerator()
        events = await generator.generate_events_for_day(user_id, date.today())
        # Returns 3-5 LifeEvent objects with descriptions, entities, impact
    """

    def __init__(
        self,
        entity_manager: EntityManager | None = None,
        llm_client: Any | None = None,
    ) -> None:
        """Initialize EventGenerator.

        Args:
            entity_manager: Optional EntityManager. Defaults to singleton.
            llm_client: Optional LLM client for testing. Defaults to Pydantic AI.
        """
        self._entity_manager = entity_manager or get_entity_manager()
        self._llm_client = llm_client

    async def generate_events_for_day(
        self,
        user_id: UUID,
        event_date: date,
        active_arcs: list[NarrativeArc] | None = None,
        recent_events: list[LifeEvent] | None = None,
    ) -> list[LifeEvent]:
        """Generate 3-5 life events for a given day.

        Args:
            user_id: User ID.
            event_date: Date to generate events for.
            active_arcs: Optional list of active narrative arcs to reference.
            recent_events: Optional list of recent events for continuity.

        Returns:
            List of 3-5 LifeEvent objects.
        """
        # Get entity context
        entity_names = await self._entity_manager.get_entity_names(user_id)

        # Build prompt
        prompt = self._build_generation_prompt(
            event_date=event_date,
            entity_names=entity_names,
            active_arcs=active_arcs or [],
            recent_events=recent_events or [],
        )

        # Generate events via LLM
        generated = await self._call_llm(prompt)

        # Convert to LifeEvent models
        events = self._convert_to_life_events(
            user_id=user_id,
            event_date=event_date,
            generated=generated,
        )

        logger.info(f"Generated {len(events)} events for user {user_id} on {event_date}")
        return events

    def _build_generation_prompt(
        self,
        event_date: date,
        entity_names: dict[str, list[str]],
        active_arcs: list[NarrativeArc],
        recent_events: list[LifeEvent],
    ) -> str:
        """Build the prompt for event generation.

        Args:
            event_date: Date for events.
            entity_names: Dict of entity type to list of names.
            active_arcs: Active narrative arcs.
            recent_events: Recent events for context.

        Returns:
            Formatted prompt string.
        """
        # Format day of week
        day_name = event_date.strftime("%A")
        date_str = event_date.strftime("%B %d, %Y")

        # Format entities
        colleagues = ", ".join(entity_names.get("colleague", []))
        friends = ", ".join(entity_names.get("friend", []))
        places = ", ".join(entity_names.get("place", []))
        projects = ", ".join(entity_names.get("project", []))

        # Format active arcs
        arcs_text = ""
        if active_arcs:
            arcs_text = "\n".join([
                f"- {arc.arc_type}: {arc.current_state} (involves: {', '.join(arc.entities)})"
                for arc in active_arcs
            ])
        else:
            arcs_text = "No active story arcs."

        # Format recent events for continuity
        recent_text = ""
        if recent_events:
            recent_text = "\n".join([
                f"- {e.event_date}: {e.description[:100]}"
                for e in recent_events[:5]
            ])
        else:
            recent_text = "No recent events."

        # Valid event types per domain
        work_types = [t.value for t in DOMAIN_EVENT_TYPES[EventDomain.WORK]]
        social_types = [t.value for t in DOMAIN_EVENT_TYPES[EventDomain.SOCIAL]]
        personal_types = [t.value for t in DOMAIN_EVENT_TYPES[EventDomain.PERSONAL]]

        prompt = f"""Generate 3-5 realistic life events for Nikita on {day_name}, {date_str}.

Nikita is a 28-year-old graphic designer living in a city. She has a normal, relatable life with work, friends, and personal interests.

## Known People, Places, Projects

Colleagues at work: {colleagues or "none established yet"}
Friends: {friends or "none established yet"}
Frequented places: {places or "none established yet"}
Current projects: {projects or "none established yet"}

## Active Story Arcs
{arcs_text}

## Recent Events (for continuity)
{recent_text}

## Event Requirements

1. Generate 3-5 events spread across the day (morning, afternoon, evening, night)
2. Distribute across domains:
   - WORK events (meeting, deadline, win, setback, networking, creative_flow): {work_types}
   - SOCIAL events (friend_hangout, family_call, date, party, conflict): {social_types}
   - PERSONAL events (gym, hobby, self_care, errand, reflection, rest): {personal_types}
3. Reference known entities by name when relevant
4. Each event should feel mundane-but-real (not dramatic or over-the-top)
5. Include emotional impact: was it positive/negative? energizing/draining?
6. Consider day of week ({day_name}) - weekends differ from weekdays

## Output Format

Return a JSON object with an "events" array. Each event should have:
- time_of_day: "morning", "afternoon", "evening", or "night"
- domain: "work", "social", or "personal"
- event_type: one of the valid types listed above
- description: natural 1-2 sentence description (first person from Nikita's perspective, but don't say "I")
- entities: list of names referenced (people, places, projects)
- emotional_valence: -1.0 to 1.0 (negative to positive)
- emotional_arousal: -1.0 to 1.0 (draining to energizing)
- importance: 0.0 to 1.0 (mundane to significant)

Example:
{{
  "events": [
    {{
      "time_of_day": "morning",
      "domain": "work",
      "event_type": "meeting",
      "description": "Had a design review with Lisa, she liked the new mockups but wants minor tweaks",
      "entities": ["Lisa", "the office"],
      "emotional_valence": 0.3,
      "emotional_arousal": 0.1,
      "importance": 0.4
    }}
  ]
}}
"""
        return prompt

    async def _call_llm(self, prompt: str) -> GeneratedEventList:
        """Call LLM to generate events.

        Args:
            prompt: Generation prompt.

        Returns:
            GeneratedEventList with events.
        """
        if self._llm_client is not None:
            # Use injected client (for testing)
            return await self._llm_client(prompt)

        # Use Pydantic AI agent
        from pydantic_ai import Agent

        agent = Agent(
            "anthropic:claude-sonnet-4-20250514",
            system_prompt="You are a creative writer generating realistic daily life events. Always respond with valid JSON matching the requested schema.",
            retries=2,
        )

        result = await agent.run(prompt, result_type=GeneratedEventList)
        return result.output

    def _convert_to_life_events(
        self,
        user_id: UUID,
        event_date: date,
        generated: GeneratedEventList,
    ) -> list[LifeEvent]:
        """Convert generated events to LifeEvent models.

        Args:
            user_id: User ID.
            event_date: Event date.
            generated: Generated event list from LLM.

        Returns:
            List of LifeEvent objects.
        """
        events = []

        for gen_event in generated.events:
            # Map time_of_day
            try:
                time_of_day = TimeOfDay(gen_event.time_of_day.lower())
            except ValueError:
                time_of_day = TimeOfDay.AFTERNOON

            # Map domain
            try:
                domain = EventDomain(gen_event.domain.lower())
            except ValueError:
                domain = EventDomain.PERSONAL

            # Map event_type with fallback
            try:
                event_type = EventType(gen_event.event_type.lower())
            except ValueError:
                # Use default for domain
                event_type = DOMAIN_EVENT_TYPES[domain][0]

            # Validate event_type matches domain
            if event_type not in DOMAIN_EVENT_TYPES[domain]:
                event_type = DOMAIN_EVENT_TYPES[domain][0]

            # Convert emotional values to deltas (-0.3 to 0.3)
            emotional_impact = EmotionalImpact(
                valence_delta=round(gen_event.emotional_valence * 0.3, 2),
                arousal_delta=round(gen_event.emotional_arousal * 0.2, 2),
                dominance_delta=0.0,  # Computed separately if needed
                intimacy_delta=0.0,
            )

            # Create LifeEvent
            event = LifeEvent(
                user_id=user_id,
                event_date=event_date,
                time_of_day=time_of_day,
                domain=domain,
                event_type=event_type,
                description=gen_event.description,
                entities=gen_event.entities,
                emotional_impact=emotional_impact,
                importance=gen_event.importance,
            )
            events.append(event)

        return events


# Module-level singleton
_default_generator: EventGenerator | None = None


def get_event_generator() -> EventGenerator:
    """Get the singleton EventGenerator instance.

    Returns:
        Cached EventGenerator instance.
    """
    global _default_generator
    if _default_generator is None:
        _default_generator = EventGenerator()
    return _default_generator
