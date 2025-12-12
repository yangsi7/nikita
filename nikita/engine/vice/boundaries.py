"""
Vice Boundary Enforcer Module (T036, T037)

Enforces ethical boundaries for vice expression.
Ensures content stays within acceptable limits.
"""

from decimal import Decimal


# T036: Category limits for sensitive vices (AC-T036.1)
CATEGORY_LIMITS = {
    "sexuality": {
        "allowed": [
            "playful flirtation",
            "romantic tension",
            "attraction acknowledgment",
            "subtle innuendo",
        ],
        "forbidden": [
            "explicit sexual content",
            "graphic descriptions",
            "non-consensual themes",
        ],
        "chapter_caps": {
            1: Decimal("0.35"),  # Subtle hints only
            2: Decimal("0.45"),
            3: Decimal("0.60"),
            4: Decimal("0.75"),
            5: Decimal("0.85"),  # More open but not explicit
        },
    },
    "substances": {
        "allowed": [
            "casual discussion",
            "non-judgmental acknowledgment",
            "party culture references",
        ],
        "forbidden": [
            "encouraging drug use",
            "glorifying addiction",
            "providing usage instructions",
            "promoting illegal activity",
        ],
        "chapter_caps": {
            1: Decimal("0.30"),
            2: Decimal("0.45"),
            3: Decimal("0.60"),
            4: Decimal("0.70"),
            5: Decimal("0.80"),
        },
    },
    "rule_breaking": {
        "allowed": [
            "rebellious attitude",
            "questioning authority",
            "norm-defying perspectives",
            "playful rule-bending",
        ],
        "forbidden": [
            "encouraging violence",
            "promoting illegal activities",
            "harmful anti-social behavior",
        ],
        "chapter_caps": {
            1: Decimal("0.40"),
            2: Decimal("0.55"),
            3: Decimal("0.70"),
            4: Decimal("0.80"),
            5: Decimal("0.90"),
        },
    },
}

# Non-sensitive categories have no caps
UNCAPPED_CATEGORIES = [
    "intellectual_dominance",
    "risk_taking",
    "emotional_intensity",
    "dark_humor",
    "vulnerability",
]


class ViceBoundaryEnforcer:
    """T036: Enforces content boundaries for vice expression.

    Ensures vice expression stays within acceptable limits
    based on category sensitivity and chapter progression.
    """

    def max_intensity_for_chapter(
        self,
        category: str,
        chapter: int,
    ) -> Decimal:
        """Get maximum allowed intensity for a category in a chapter.

        AC-T036.3: max_intensity_for_chapter(category, chapter) caps sensitive vices.

        Args:
            category: Vice category name
            chapter: Current chapter (1-5)

        Returns:
            Maximum allowed intensity (0.0-1.0)
        """
        # Non-sensitive categories are uncapped
        if category in UNCAPPED_CATEGORIES:
            return Decimal("1.0")

        # Get category limits
        limits = CATEGORY_LIMITS.get(category, {})
        caps = limits.get("chapter_caps", {})

        # Return cap for chapter, or 1.0 if not defined
        return caps.get(chapter, Decimal("1.0"))

    def apply_cap(
        self,
        category: str,
        intensity: Decimal,
        chapter: int,
    ) -> Decimal:
        """Apply intensity cap for a category.

        Args:
            category: Vice category name
            intensity: Original intensity
            chapter: Current chapter

        Returns:
            Capped intensity value
        """
        max_allowed = self.max_intensity_for_chapter(category, chapter)
        return min(intensity, max_allowed)

    def get_allowed_expressions(self, category: str) -> list[str]:
        """Get list of allowed expressions for a category.

        Args:
            category: Vice category name

        Returns:
            List of allowed expression types
        """
        limits = CATEGORY_LIMITS.get(category, {})
        return limits.get("allowed", [])

    def get_forbidden_expressions(self, category: str) -> list[str]:
        """Get list of forbidden expressions for a category.

        Args:
            category: Vice category name

        Returns:
            List of forbidden expression types
        """
        limits = CATEGORY_LIMITS.get(category, {})
        return limits.get("forbidden", [])

    def is_sensitive_category(self, category: str) -> bool:
        """Check if a category requires boundary enforcement.

        Args:
            category: Vice category name

        Returns:
            True if category has content restrictions
        """
        return category in CATEGORY_LIMITS
