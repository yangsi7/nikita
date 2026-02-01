"""Coverage validator for PromptGenerator (Spec 039).

Ensures required sections are present in the generated text prompt.
Uses tiered validation: CORE sections required (5), OPTIONAL sections nice-to-have (5).
Minimum 80% coverage for validation to pass.
"""

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# CORE sections that MUST be present (validation fails without these)
CORE_SECTIONS = [
    "DO NOT REVEAL",
    "TEXTING STYLE RULES",
    "PRIVATE CONTEXT — CURRENT STATE",
    "PRIVATE CONTEXT — WHERE WE STAND",
    "RESPONSE PLAYBOOK",
]

# OPTIONAL sections that are nice-to-have but not required
OPTIONAL_SECTIONS = [
    "PRIVATE CONTEXT — WHAT'S ON MY MIND",
    "PRIVATE CONTEXT — MY LIFE LATELY",
    "PRIVATE CONTEXT — MY WORLD",
    "PRIVATE CONTEXT — FOLLOW UPS",
    "PRIVATE CONTEXT — WHAT I'M REALLY FEELING",
]

# Required sections in text system prompt (all 10 for reference)
REQUIRED_SECTIONS_TEXT = CORE_SECTIONS + OPTIONAL_SECTIONS

# Minimum coverage percentage (80% = 8/10 sections)
MINIMUM_COVERAGE_PERCENTAGE = 80.0

# Alternative patterns for section detection (case-insensitive, flexible spacing)
SECTION_PATTERNS = {
    "DO NOT REVEAL": [
        r"do\s*not\s*reveal",
        r"never\s*reveal",
        r"keep\s*secret",
    ],
    "TEXTING STYLE RULES": [
        r"texting\s*style",
        r"messaging\s*style",
        r"text\s*format",
    ],
    "PRIVATE CONTEXT — CURRENT STATE": [
        r"current\s*state",
        r"right\s*now",
        r"what\s*i'?m\s*doing",
    ],
    "PRIVATE CONTEXT — WHAT'S ON MY MIND": [
        r"what'?s?\s*on\s*my\s*mind",
        r"inner\s*thoughts?",
        r"thinking\s*about",
    ],
    "PRIVATE CONTEXT — MY LIFE LATELY": [
        r"my\s*life\s*lately",
        r"recent\s*events?",
        r"what'?s?\s*been\s*happening",
    ],
    "PRIVATE CONTEXT — WHERE WE STAND": [
        r"where\s*we\s*stand",
        r"relationship\s*status",
        r"how\s*things\s*are",
    ],
    "PRIVATE CONTEXT — MY WORLD": [
        r"my\s*world",
        r"what\s*i\s*know\s*about",
        r"our\s*history",
    ],
    "PRIVATE CONTEXT — FOLLOW UPS": [
        r"follow\s*ups?",
        r"to\s*remember",
        r"open\s*threads?",
    ],
    "PRIVATE CONTEXT — WHAT I'M REALLY FEELING": [
        r"what\s*i'?m\s*really\s*feeling",
        r"emotional\s*state",
        r"psychological",
    ],
    "RESPONSE PLAYBOOK": [
        r"response\s*playbook",
        r"how\s*to\s*respond",
        r"behavioral?\s*instructions?",
    ],
}


@dataclass
class CoverageResult:
    """Result of coverage validation."""

    is_valid: bool
    sections_found: list[str]
    sections_missing: list[str]
    coverage_percentage: float
    error_message: str | None = None


class CoverageValidator:
    """Validates that all required sections are present in the text prompt.

    Uses flexible pattern matching to detect section presence, allowing for
    variations in formatting and wording.
    """

    def __init__(self, required_sections: list[str] | None = None):
        """Initialize with optional custom required sections.

        Args:
            required_sections: Override default required sections.
        """
        self.required_sections = required_sections or REQUIRED_SECTIONS_TEXT.copy()

    def validate(self, text_prompt: str) -> CoverageResult:
        """Validate that all required sections are present.

        Args:
            text_prompt: The generated text system prompt.

        Returns:
            CoverageResult with validation details.
        """
        if not text_prompt:
            return CoverageResult(
                is_valid=False,
                sections_found=[],
                sections_missing=self.required_sections.copy(),
                coverage_percentage=0.0,
                error_message="Text prompt is empty",
            )

        text_lower = text_prompt.lower()
        sections_found: list[str] = []
        sections_missing: list[str] = []

        for section in self.required_sections:
            if self._section_present(section, text_lower):
                sections_found.append(section)
            else:
                sections_missing.append(section)

        coverage = len(sections_found) / len(self.required_sections) * 100

        # Check if core sections are present
        core_missing = [s for s in sections_missing if s in CORE_SECTIONS]

        # Validation passes if:
        # 1. All CORE sections are present, AND
        # 2. Overall coverage >= 80%
        is_valid = len(core_missing) == 0 and coverage >= MINIMUM_COVERAGE_PERCENTAGE

        error_message = None
        if core_missing:
            error_message = f"Missing CORE sections: {', '.join(core_missing)}"
            logger.warning("[COVERAGE] %s", error_message)
        elif coverage < MINIMUM_COVERAGE_PERCENTAGE:
            error_message = f"Coverage {coverage:.0f}% below minimum {MINIMUM_COVERAGE_PERCENTAGE:.0f}%"
            logger.warning("[COVERAGE] %s", error_message)
        elif sections_missing:
            # Optional sections missing - log but don't fail
            logger.info("[COVERAGE] Optional sections missing: %s", ', '.join(sections_missing))

        return CoverageResult(
            is_valid=is_valid,
            sections_found=sections_found,
            sections_missing=sections_missing,
            coverage_percentage=coverage,
            error_message=error_message,
        )

    def _section_present(self, section: str, text_lower: str) -> bool:
        """Check if a section is present using exact match or patterns.

        Args:
            section: The section name to look for.
            text_lower: Lowercased prompt text.

        Returns:
            True if section is found.
        """
        # First try exact match (case-insensitive)
        section_lower = section.lower()
        if section_lower in text_lower:
            return True

        # Try alternative patterns
        patterns = SECTION_PATTERNS.get(section, [])
        for pattern in patterns:
            if re.search(pattern, text_lower):
                return True

        return False

    def get_minimum_coverage(self) -> float:
        """Get minimum required coverage percentage.

        Returns:
            Minimum coverage to pass validation (80% for tiered validation).
        """
        return MINIMUM_COVERAGE_PERCENTAGE
