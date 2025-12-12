"""Vice discovery system for Nikita game engine.

This module provides:
- Vice detection and analysis from conversations (LLM-based)
- User vice profile management and persistence
- Prompt injection for personalized responses
- Ethical boundary enforcement
"""

from nikita.engine.vice.models import (
    ViceAnalysisResult,
    ViceInjectionContext,
    ViceProfile,
    ViceSignal,
)
from nikita.engine.vice.analyzer import ViceAnalyzer
from nikita.engine.vice.scorer import ViceScorer
from nikita.engine.vice.injector import VicePromptInjector, VICE_DESCRIPTIONS, EXPRESSION_LEVELS
from nikita.engine.vice.boundaries import ViceBoundaryEnforcer, CATEGORY_LIMITS
from nikita.engine.vice.service import ViceService

__all__ = [
    # Models
    "ViceSignal",
    "ViceAnalysisResult",
    "ViceProfile",
    "ViceInjectionContext",
    # Services
    "ViceAnalyzer",
    "ViceScorer",
    "VicePromptInjector",
    "ViceBoundaryEnforcer",
    "ViceService",
    # Constants
    "VICE_DESCRIPTIONS",
    "EXPRESSION_LEVELS",
    "CATEGORY_LIMITS",
]
