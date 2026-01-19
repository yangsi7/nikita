"""Context engineering module for Nikita.

This module implements context engineering (Spec 012) and hierarchical prompt
composition (Spec 021):

Spec 012 Components:
- Session detection (15 min timeout for text, call end for voice)
- Post-processing pipeline (9 stages)
- System prompt generation via MetaPromptService

Spec 021 Components (Hierarchical Prompt Composition):
- ContextPackage: Pre-computed context for fast conversation startup
- PackageStore: JSONB storage with 24h TTL
- 6 prompt layers (in layers/ submodule)
- HierarchicalPromptComposer: Assembles layers into system prompt

Architecture:
- PRE-CONVERSATION: Load context package, compose 6-layer prompt (~150ms)
- DURING CONVERSATION: Pure LLM conversation with optional retrieval (NO memory writes)
- POST-CONVERSATION: Async pipeline extracts facts, updates graphs, stores package

See: nikita/meta_prompts/ for the meta-prompt implementation.
See: nikita/context/layers/ for individual layer composers.
"""

from nikita.context.composer import (
    HierarchicalPromptComposer,
    compose_hierarchical_prompt,
    get_prompt_composer,
)
from nikita.context.package import (
    ActiveThread,
    ComposedPrompt,
    ContextPackage,
    EmotionalState,
    ProcessingResult,
)
from nikita.context.post_processor import PostProcessor, process_conversations
from nikita.context.session_detector import SessionDetector
from nikita.context.store import PackageStore, get_package_store, set_default_package_store
from nikita.context.template_generator import TemplateGenerator, generate_system_prompt
from nikita.context.validation import (
    TokenValidator,
    ValidationResult,
    count_tokens,
    get_token_validator,
    validate_prompt,
)

__all__ = [
    # Spec 012 components
    "SessionDetector",
    "PostProcessor",
    "process_conversations",
    "TemplateGenerator",
    "generate_system_prompt",
    # Spec 021 components
    "ContextPackage",
    "EmotionalState",
    "ActiveThread",
    "ComposedPrompt",
    "ProcessingResult",
    "PackageStore",
    "get_package_store",
    "set_default_package_store",
    # Hierarchical Prompt Composer
    "HierarchicalPromptComposer",
    "get_prompt_composer",
    "compose_hierarchical_prompt",
    # Token Validation
    "TokenValidator",
    "ValidationResult",
    "get_token_validator",
    "count_tokens",
    "validate_prompt",
]
