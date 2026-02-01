"""Context Engine Validators (Spec 039).

Output validators for PromptGenerator:

1. CoverageValidator - Required sections present in text prompt
2. GuardrailsValidator - No stage directions, meta terms, etc.
3. SpeakabilityValidator - Voice block is speakable (no emojis, reasonable length)
"""

from nikita.context_engine.validators.coverage import (
    CORE_SECTIONS,
    CoverageResult,
    CoverageValidator,
    MINIMUM_COVERAGE_PERCENTAGE,
    OPTIONAL_SECTIONS,
    REQUIRED_SECTIONS_TEXT,
)
from nikita.context_engine.validators.guardrails import (
    BANNED_PATTERNS,
    GuardrailsResult,
    GuardrailsValidator,
    GuardrailViolation,
)
from nikita.context_engine.validators.speakability import (
    SpeakabilityIssue,
    SpeakabilityResult,
    SpeakabilityValidator,
)

__all__ = [
    # Coverage
    "CORE_SECTIONS",
    "CoverageResult",
    "CoverageValidator",
    "MINIMUM_COVERAGE_PERCENTAGE",
    "OPTIONAL_SECTIONS",
    "REQUIRED_SECTIONS_TEXT",
    # Guardrails
    "BANNED_PATTERNS",
    "GuardrailsResult",
    "GuardrailsValidator",
    "GuardrailViolation",
    # Speakability
    "SpeakabilityIssue",
    "SpeakabilityResult",
    "SpeakabilityValidator",
]
