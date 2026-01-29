"""Prompt layer composers for Hierarchical Prompt Composition (Spec 021).

This module contains the 6 layers of the hierarchical prompt system:
- Layer 1: Base Personality (static, cached)
- Layer 2: Chapter Layer (pre-computed per chapter)
- Layer 3: Emotional State (pre-computed from life sim)
- Layer 4: Situation Layer (computed at conversation start)
- Layer 5: Context Injection (from pre-computed package)
- Layer 6: On-the-Fly Modifications (during conversation)

Each layer has a dedicated composer class responsible for generating
its portion of the system prompt.
"""

# Layer 1: Base Personality
from nikita.context.layers.base_personality import (
    Layer1Loader,
    get_base_personality_prompt,
    get_layer1_loader,
)

# Layer 2: Chapter Layer
from nikita.context.layers.chapter import (
    Layer2Composer,
    compose_chapter_layer,
    get_layer2_composer,
)

# Layer 3: Emotional State
from nikita.context.layers.emotional_state import (
    Layer3Composer,
    compose_emotional_state_layer,
    get_layer3_composer,
)

# Layer 4: Situation
from nikita.context.layers.situation import (
    Layer4Computer,
    SituationResult,
    SituationType,
    detect_and_compose_situation,
    get_layer4_computer,
)

# Layer 5: Context Injection
from nikita.context.layers.context_injection import (
    Layer5Injector,
    get_layer5_injector,
    inject_context,
)

# Layer 6: On-the-Fly Modifications
from nikita.context.layers.on_the_fly import (
    Layer6Handler,
    ModificationType,
    PromptModification,
    get_layer6_handler,
)

__all__ = [
    # Layer 1
    "Layer1Loader",
    "get_layer1_loader",
    "get_base_personality_prompt",
    # Layer 2
    "Layer2Composer",
    "get_layer2_composer",
    "compose_chapter_layer",
    # Layer 3
    "Layer3Composer",
    "get_layer3_composer",
    "compose_emotional_state_layer",
    # Layer 4
    "Layer4Computer",
    "SituationResult",
    "SituationType",
    "get_layer4_computer",
    "detect_and_compose_situation",
    # Layer 5
    "Layer5Injector",
    "get_layer5_injector",
    "inject_context",
    # Layer 6
    "Layer6Handler",
    "ModificationType",
    "PromptModification",
    "get_layer6_handler",
]
