"""Life Simulation Engine (Spec 022 + Spec 035 Deep Humanization).

Generates daily events for Nikita across work, social, and personal domains.
Derives mood from events and makes them available for natural conversation references.

Key Components:
- LifeSimulator: Main orchestrator
- EventGenerator: LLM-based event creation
- NarrativeArcManager: Arc lifecycle management
- EntityManager: Recurring people, places, projects
- MoodCalculator: Event → mood contribution
- EventStore: Supabase persistence

Spec 035 Deep Humanization Additions:
- SocialCircleGenerator: Personalized social circle based on user onboarding
- NarrativeArcSystem: Multi-conversation narrative arcs with named characters
- PsychologyMapper: Event → psychological response mapping

Usage:
    from nikita.life_simulation import LifeSimulator, LifeEvent

    simulator = await get_life_simulator()
    events = await simulator.generate_next_day_events(user_id)
    mood = await simulator.get_mood_from_events(events)

    # Spec 035: Social circle generation
    from nikita.life_simulation import SocialCircleGenerator
    generator = SocialCircleGenerator()
    circle = generator.generate_social_circle_for_user(user_id, "Berlin", ["hacking"], "tech", "conference")

    # Spec 035: Narrative arcs
    from nikita.life_simulation import NarrativeArcSystem
    arc_system = NarrativeArcSystem()
    arc = arc_system.start_arc("viktor_resurfaces", user_id)

    # Spec 035: Psychology mapping
    from nikita.life_simulation import PsychologyMapper
    mapper = PsychologyMapper()
    psych_state = mapper.analyze_event("setback", ["Viktor"], "Project failed")
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
    # Spec 055: Routine models
    DayRoutine,
    WeeklyRoutine,
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
    # Spec 055: Routine models
    "DayRoutine",
    "WeeklyRoutine",
    # Spec 035: Social Circle
    "SocialCircleGenerator",
    "FriendCharacter",
    "SocialCircle",
    "generate_social_circle_for_user",
    "get_social_generator",
    # Spec 035: Narrative Arcs (enhanced)
    "NarrativeArcSystem",
    "ArcTemplate",
    "ArcCategory",
    "ArcStage",
    "get_arc_system",
    # Spec 035: Psychology Mapper
    "PsychologyMapper",
    "PsychologicalState",
    "CoreWound",
    "DefenseMechanism",
    "TraumaTrigger",
    "get_psychology_mapper",
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
    # Spec 035: Social Circle Generator
    elif name == "SocialCircleGenerator":
        from nikita.life_simulation.social_generator import SocialCircleGenerator
        return SocialCircleGenerator
    elif name == "FriendCharacter":
        from nikita.life_simulation.social_generator import FriendCharacter
        return FriendCharacter
    elif name == "SocialCircle":
        from nikita.life_simulation.social_generator import SocialCircle
        return SocialCircle
    elif name == "generate_social_circle_for_user":
        from nikita.life_simulation.social_generator import generate_social_circle_for_user
        return generate_social_circle_for_user
    elif name == "get_social_generator":
        from nikita.life_simulation.social_generator import get_social_generator
        return get_social_generator
    # Spec 035: Narrative Arc System (enhanced)
    elif name == "NarrativeArcSystem":
        from nikita.life_simulation.arcs import NarrativeArcSystem
        return NarrativeArcSystem
    elif name == "ArcTemplate":
        from nikita.life_simulation.arcs import ArcTemplate
        return ArcTemplate
    elif name == "ArcCategory":
        from nikita.life_simulation.arcs import ArcCategory
        return ArcCategory
    elif name == "ArcStage":
        from nikita.life_simulation.arcs import ArcStage
        return ArcStage
    elif name == "get_arc_system":
        from nikita.life_simulation.arcs import get_arc_system
        return get_arc_system
    # Spec 035: Psychology Mapper
    elif name == "PsychologyMapper":
        from nikita.life_simulation.psychology_mapper import PsychologyMapper
        return PsychologyMapper
    elif name == "PsychologicalState":
        from nikita.life_simulation.psychology_mapper import PsychologicalState
        return PsychologicalState
    elif name == "CoreWound":
        from nikita.life_simulation.psychology_mapper import CoreWound
        return CoreWound
    elif name == "DefenseMechanism":
        from nikita.life_simulation.psychology_mapper import DefenseMechanism
        return DefenseMechanism
    elif name == "TraumaTrigger":
        from nikita.life_simulation.psychology_mapper import TraumaTrigger
        return TraumaTrigger
    elif name == "get_psychology_mapper":
        from nikita.life_simulation.psychology_mapper import get_psychology_mapper
        return get_psychology_mapper
    raise AttributeError(f"module 'nikita.life_simulation' has no attribute '{name}'")
