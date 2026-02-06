"""Context engineering module for Nikita.

NOTE: This module is mostly deprecated as of Spec 042 (unified pipeline).

The legacy context_engine/, meta_prompts/, post_processing/, and context/stages/
directories have been removed. All prompt generation and post-processing now
happens in the unified pipeline at nikita/pipeline/.

Remaining components:
- package.py: ContextPackage models (still used)
- session_detector.py: Session detection (still used)
- validation.py: Token validation (still used)

Deprecated components (removed):
- composer.py (deleted)
- post_processor.py (deleted)
- template_generator.py (deleted)
- stages/ directory (deleted)
- layers/ directory (deleted)
"""

from nikita.context.package import (
    ActiveThread,
    ComposedPrompt,
    ContextPackage,
    EmotionalState,
    ProcessingResult,
)
from nikita.context.session_detector import SessionDetector
from nikita.context.store import PackageStore, get_package_store, set_default_package_store
from nikita.context.validation import (
    TokenValidator,
    ValidationResult,
    count_tokens,
    get_token_validator,
    validate_prompt,
)

__all__ = [
    # Session Detection
    "SessionDetector",
    # Package Models
    "ContextPackage",
    "EmotionalState",
    "ActiveThread",
    "ComposedPrompt",
    "ProcessingResult",
    "PackageStore",
    "get_package_store",
    "set_default_package_store",
    # Token Validation
    "TokenValidator",
    "ValidationResult",
    "get_token_validator",
    "count_tokens",
    "validate_prompt",
]
