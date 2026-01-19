"""Life Simulation Engine (Spec 022).

Generates daily events for Nikita across work, social, and personal domains.
Derives mood from events and makes them available for natural conversation references.

Key Components:
- LifeSimulator: Main orchestrator
- EventGenerator: LLM-based event creation
- NarrativeArcManager: Arc lifecycle management
- EntityManager: Recurring people, places, projects
- MoodCalculator: Event → mood contribution
- EventStore: Supabase persistence

Usage:
    from nikita.life_simulation import LifeSimulator, LifeEvent

    simulator = await get_life_simulator()
    events = await simulator.generate_next_day_events(user_id)
    mood = await simulator.get_mood_from_events(events)
"""

# Models (always available)
from nikita.life_simulation.models import (
    LifeEvent,
    NarrativeArc,
    NikitaEntity,
    EventDomain,
    EventType,
    ArcStatus,
    TimeOfDay,
    EmotionalImpact,
    EntityType,
    DOMAIN_EVENT_TYPES,
)

__all__ = [
    # Models
    "LifeEvent",
    "NarrativeArc",
    "NikitaEntity",
    "EventDomain",
    "EventType",
    "ArcStatus",
    "TimeOfDay",
    "EmotionalImpact",
    "EntityType",
    "DOMAIN_EVENT_TYPES",
]

# Lazy imports for components (added as they're implemented)
def __getattr__(name: str):
    """Lazy import for components."""
    if name == "MoodCalculator":
        from nikita.life_simulation.mood_calculator import MoodCalculator
        return MoodCalculator
    elif name == "EventStore":
        from nikita.life_simulation.store import EventStore
        return EventStore
    elif name == "get_event_store":
        from nikita.life_simulation.store import get_event_store
        return get_event_store
    elif name == "EntityManager":
        from nikita.life_simulation.entity_manager import EntityManager
        return EntityManager
    elif name == "get_entity_manager":
        from nikita.life_simulation.entity_manager import get_entity_manager
        return get_entity_manager
    elif name == "EventGenerator":
        from nikita.life_simulation.event_generator import EventGenerator
        return EventGenerator
    elif name == "get_event_generator":
        from nikita.life_simulation.event_generator import get_event_generator
        return get_event_generator
    elif name == "NarrativeArcManager":
        from nikita.life_simulation.narrative_manager import NarrativeArcManager
        return NarrativeArcManager
    elif name == "get_narrative_manager":
        from nikita.life_simulation.narrative_manager import get_narrative_manager
        return get_narrative_manager
    elif name == "LifeSimulator":
        from nikita.life_simulation.simulator import LifeSimulator
        return LifeSimulator
    elif name == "get_life_simulator":
        from nikita.life_simulation.simulator import get_life_simulator
        return get_life_simulator
    raise AttributeError(f"module 'nikita.life_simulation' has no attribute '{name}'")
