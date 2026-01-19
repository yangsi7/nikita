"""Life Simulator - Main Orchestrator (Spec 022, T013).

Orchestrates all life simulation components to generate Nikita's daily life.

AC-T013.1: LifeSimulator class orchestrates all components
AC-T013.2: generate_next_day_events() full pipeline
AC-T013.3: get_today_events() for context injection
AC-T013.4: Handles new users (entity seeding)
AC-T013.5: Unit tests for simulator
"""

import logging
from datetime import date, timedelta
from typing import Any
from uuid import UUID

from nikita.life_simulation.entity_manager import EntityManager, get_entity_manager
from nikita.life_simulation.event_generator import EventGenerator, get_event_generator
from nikita.life_simulation.models import (
    EventDomain,
    LifeEvent,
    NarrativeArc,
)
from nikita.life_simulation.mood_calculator import MoodCalculator, MoodState, get_mood_calculator
from nikita.life_simulation.narrative_manager import NarrativeArcManager, get_narrative_manager
from nikita.life_simulation.store import EventStore, get_event_store

logger = logging.getLogger(__name__)


class LifeSimulator:
    """Main orchestrator for Nikita's life simulation.

    Coordinates event generation, entity management, narrative arcs,
    and mood computation to create Nikita's evolving daily life.

    The simulation generates 3-5 events per day across work, social,
    and personal domains. Events reference known entities and affect
    Nikita's mood through emotional impact deltas.

    Example:
        simulator = LifeSimulator()

        # Generate tomorrow's events
        events = await simulator.generate_next_day_events(user_id)

        # Get today's events for context injection
        today_events = await simulator.get_today_events(user_id)

        # Get current mood state
        mood = await simulator.get_current_mood(user_id)
    """

    def __init__(
        self,
        store: EventStore | None = None,
        entity_manager: EntityManager | None = None,
        event_generator: EventGenerator | None = None,
        narrative_manager: NarrativeArcManager | None = None,
        mood_calculator: MoodCalculator | None = None,
    ) -> None:
        """Initialize LifeSimulator with component dependencies.

        Args:
            store: Event store for persistence. Defaults to singleton.
            entity_manager: Entity manager. Defaults to singleton.
            event_generator: Event generator. Defaults to singleton.
            narrative_manager: Arc manager. Defaults to singleton.
            mood_calculator: Mood calculator. Defaults to singleton.
        """
        self._store = store or get_event_store()
        self._entity_manager = entity_manager or get_entity_manager()
        self._event_generator = event_generator or get_event_generator()
        self._narrative_manager = narrative_manager or get_narrative_manager()
        self._mood_calculator = mood_calculator or get_mood_calculator()

    async def initialize_user(self, user_id: UUID) -> bool:
        """Initialize life simulation for a new user.

        Seeds default entities (colleagues, friends, places, projects).
        Should be called once when user first starts the game.

        Args:
            user_id: User ID.

        Returns:
            True if entities were seeded, False if already existed.
        """
        existing = await self._store.get_entities(user_id)
        if existing:
            logger.info(f"User {user_id} already initialized with {len(existing)} entities")
            return False

        entities = await self._entity_manager.seed_entities(user_id)
        logger.info(f"Initialized user {user_id} with {len(entities)} entities")
        return True

    async def generate_next_day_events(
        self,
        user_id: UUID,
        target_date: date | None = None,
    ) -> list[LifeEvent]:
        """Generate events for the next day (or specified date).

        Full pipeline:
        1. Check/seed entities for new users
        2. Get active narrative arcs
        3. Get recent events for continuity
        4. Generate 3-5 events via LLM
        5. Maybe progress/resolve narrative arcs
        6. Maybe create new narrative arc
        7. Persist events

        Args:
            user_id: User ID.
            target_date: Date to generate events for. Defaults to tomorrow.

        Returns:
            List of generated LifeEvent objects.
        """
        if target_date is None:
            target_date = date.today() + timedelta(days=1)

        # Check if events already exist for this date
        existing = await self._store.get_events_for_date(user_id, target_date)
        if existing:
            logger.info(f"Events already exist for {user_id} on {target_date}")
            return existing

        # Ensure user has entities
        await self.initialize_user(user_id)

        # Get context for generation
        active_arcs = await self._narrative_manager.get_active_arcs(user_id)
        recent_events = await self._store.get_recent_events(user_id, days=7)

        # Generate events
        events = await self._event_generator.generate_events_for_day(
            user_id=user_id,
            event_date=target_date,
            active_arcs=active_arcs,
            recent_events=recent_events,
        )

        # Persist events
        await self._store.save_events(events)

        # Progress narrative arcs (may resolve some)
        resolved_arcs = await self._narrative_manager.maybe_resolve_arcs(user_id)
        if resolved_arcs:
            logger.info(f"Resolved {len(resolved_arcs)} arcs for {user_id}")

        # Maybe create new narrative arc
        new_arc = await self._narrative_manager.maybe_create_arc(user_id)
        if new_arc:
            logger.info(f"Created new arc for {user_id}: {new_arc.arc_type}")

        logger.info(f"Generated {len(events)} events for {user_id} on {target_date}")
        return events

    async def get_today_events(
        self,
        user_id: UUID,
        max_events: int = 5,
    ) -> list[LifeEvent]:
        """Get today's events for context injection.

        Returns events sorted by importance for use in prompts.

        Args:
            user_id: User ID.
            max_events: Maximum events to return.

        Returns:
            List of today's events, sorted by importance descending.
        """
        events = await self._store.get_events_for_date(user_id, date.today())

        # Sort by importance and limit
        sorted_events = sorted(events, key=lambda e: e.importance, reverse=True)
        return sorted_events[:max_events]

    async def get_recent_events(
        self,
        user_id: UUID,
        days: int = 7,
    ) -> list[LifeEvent]:
        """Get recent events for context and continuity.

        Args:
            user_id: User ID.
            days: Number of days to look back.

        Returns:
            List of recent events, sorted by date descending.
        """
        return await self._store.get_recent_events(user_id, days=days)

    async def get_current_mood(
        self,
        user_id: UUID,
        lookback_days: int = 3,
    ) -> MoodState:
        """Get Nikita's current mood based on recent events.

        Computes mood from events over the lookback period.

        Args:
            user_id: User ID.
            lookback_days: Days of events to consider.

        Returns:
            Current MoodState (arousal, valence, dominance, intimacy).
        """
        recent_events = await self._store.get_recent_events(user_id, days=lookback_days)
        return self._mood_calculator.compute_from_events(recent_events)

    async def get_active_arcs(self, user_id: UUID) -> list[NarrativeArc]:
        """Get active narrative arcs for the user.

        Args:
            user_id: User ID.

        Returns:
            List of active narrative arcs.
        """
        return await self._narrative_manager.get_active_arcs(user_id)

    async def get_events_for_context(
        self,
        user_id: UUID,
        max_today: int = 3,
        max_recent: int = 5,
    ) -> dict[str, Any]:
        """Get events formatted for context injection.

        Returns a dict with today's top events and recent events
        formatted as natural language descriptions.

        Args:
            user_id: User ID.
            max_today: Max today events.
            max_recent: Max recent events.

        Returns:
            Dict with 'today_events', 'recent_events', 'active_arcs', 'mood'.
        """
        # Get today's events
        today_events = await self.get_today_events(user_id, max_events=max_today)

        # Get recent events (excluding today)
        all_recent = await self.get_recent_events(user_id, days=7)
        recent_events = [e for e in all_recent if e.event_date != date.today()][:max_recent]

        # Get active arcs
        active_arcs = await self.get_active_arcs(user_id)

        # Get current mood
        mood = await self.get_current_mood(user_id)

        # Format for context
        return {
            "today_events": [self._format_event(e) for e in today_events],
            "recent_events": [self._format_event(e) for e in recent_events],
            "active_arcs": [self._format_arc(a) for a in active_arcs],
            "mood": {
                "arousal": mood.arousal,
                "valence": mood.valence,
                "dominance": mood.dominance,
                "intimacy": mood.intimacy,
                "summary": self._summarize_mood(mood),
            },
        }

    def _format_event(self, event: LifeEvent) -> str:
        """Format event as natural language string.

        Args:
            event: Event to format.

        Returns:
            Natural language description.
        """
        time = event.time_of_day.value if hasattr(event.time_of_day, "value") else str(event.time_of_day)
        return f"{time.capitalize()}: {event.description}"

    def _format_arc(self, arc: NarrativeArc) -> str:
        """Format arc as natural language string.

        Args:
            arc: Arc to format.

        Returns:
            Natural language description.
        """
        entities = ", ".join(arc.entities) if arc.entities else "related people"
        return f"{arc.arc_type.replace('_', ' ').title()}: {arc.current_state} (involves: {entities})"

    def _summarize_mood(self, mood: MoodState) -> str:
        """Summarize mood state as natural language.

        Args:
            mood: Mood state.

        Returns:
            Natural language summary.
        """
        parts = []

        # Valence (positive/negative)
        if mood.valence > 0.6:
            parts.append("feeling good")
        elif mood.valence < 0.4:
            parts.append("a bit down")
        else:
            parts.append("neutral mood")

        # Arousal (energy)
        if mood.arousal > 0.6:
            parts.append("energetic")
        elif mood.arousal < 0.4:
            parts.append("tired")

        # Dominance (confidence)
        if mood.dominance > 0.6:
            parts.append("confident")
        elif mood.dominance < 0.4:
            parts.append("uncertain")

        return ", ".join(parts) if parts else "neutral state"


# Module-level singleton
_default_simulator: LifeSimulator | None = None


def get_life_simulator() -> LifeSimulator:
    """Get the singleton LifeSimulator instance.

    Returns:
        Cached LifeSimulator instance.
    """
    global _default_simulator
    if _default_simulator is None:
        _default_simulator = LifeSimulator()
    return _default_simulator
