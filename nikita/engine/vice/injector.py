"""
Vice Prompt Injector Module (T021, T022, T023, T027)

Injects vice preferences into Nikita's prompts for personalized responses.
Uses chapter-appropriate expression levels.
"""

from decimal import Decimal

from nikita.engine.vice.models import ViceInjectionContext, ViceProfile


# T023: Vice descriptions for prompt injection (AC-T023.1, AC-T023.2)
VICE_DESCRIPTIONS = {
    "intellectual_dominance": (
        "Enjoys witty debates, showcasing expertise, and intellectual challenges. "
        "Appreciates when conversations involve complex ideas and mental sparring."
    ),
    "risk_taking": (
        "Attracted to danger, adrenaline, and unconventional choices. "
        "Thrives on excitement and pushing boundaries."
    ),
    "substances": (
        "Open and non-judgmental about alcohol, recreational experiences, and party culture. "
        "Comfortable discussing without moralizing."
    ),
    "sexuality": (
        "Responsive to flirtation, playful innuendo, and attraction-based dynamics. "
        "Comfortable with sensual undertones in conversation."
    ),
    "emotional_intensity": (
        "Seeks deep emotional exchanges and intense feelings. "
        "Values dramatic moments and profound emotional connection."
    ),
    "rule_breaking": (
        "Anti-authority attitude and norm-defying perspectives. "
        "Appreciates rebellious humor and questioning conventions."
    ),
    "dark_humor": (
        "Enjoys morbid, edgy, and uncomfortable jokes. "
        "Finds humor in taboo topics and self-deprecating wit."
    ),
    "vulnerability": (
        "Values emotional openness, sharing fears, and authentic weakness. "
        "Connects through genuine emotional exposure."
    ),
}

# T021: Chapter-specific expression levels (AC-T021.1)
EXPRESSION_LEVELS = {
    1: "subtle hints and light touches - be mysterious, don't make it obvious",
    2: "moderate expression - more open but still somewhat guarded",
    3: "confident expression - comfortable showing these preferences",
    4: "direct expression - openly embrace these aspects",
    5: "explicit and direct - fully authentic expression of these preferences",
}

# Minimum intensity to include in injection
MIN_INJECTION_THRESHOLD = Decimal("0.30")


class VicePromptInjector:
    """T022: Injects vice preferences into prompts.

    Creates chapter-appropriate vice instructions for Nikita's personality.
    """

    def inject(
        self,
        base_prompt: str,
        profile: ViceProfile,
        chapter: int,
    ) -> str:
        """Inject vice preferences into the base prompt.

        AC-T022.1: inject(base_prompt, profile, chapter) returns modified prompt
        AC-T022.2: Uses chapter-appropriate template
        AC-T022.3: Includes top 2-3 vices only
        AC-T022.4: Returns unmodified prompt if no active vices

        Args:
            base_prompt: Base system prompt for Nikita
            profile: User's vice profile
            chapter: Current chapter (1-5)

        Returns:
            Modified prompt with vice instructions
        """
        # Get top vices above threshold
        top_vices = [
            (cat, intensity)
            for cat, intensity in profile.intensities.items()
            if intensity >= MIN_INJECTION_THRESHOLD
        ]

        # Sort by intensity descending, take top 3
        top_vices = sorted(top_vices, key=lambda x: x[1], reverse=True)[:3]

        # AC-T022.4: Return unmodified if no active vices
        if not top_vices:
            return base_prompt

        # Build vice injection section
        vice_section = self._build_vice_section(top_vices, chapter)

        # Combine with base prompt
        return f"{base_prompt}\n\n{vice_section}"

    def _build_vice_section(
        self,
        top_vices: list[tuple[str, Decimal]],
        chapter: int,
    ) -> str:
        """Build the vice instruction section for the prompt.

        Args:
            top_vices: List of (category, intensity) tuples
            chapter: Current chapter (1-5)

        Returns:
            Formatted vice instruction text
        """
        # Get expression level for chapter
        expression = EXPRESSION_LEVELS.get(chapter, EXPRESSION_LEVELS[3])

        # Build vice descriptions
        vice_parts = []
        for category, intensity in top_vices:
            desc = VICE_DESCRIPTIONS.get(category, "")
            if desc:
                # Scale description by intensity
                intensity_label = self._intensity_label(intensity)
                vice_parts.append(f"- {category.replace('_', ' ').title()} ({intensity_label}): {desc}")

        # Combine into instruction
        vice_list = "\n".join(vice_parts)

        return f"""=== PERSONALITY PERSONALIZATION ===
This user resonates with these aspects of your personality:
{vice_list}

Expression style for Chapter {chapter}: {expression}

Express these naturally as part of who you are - not performatively or obviously.
Let these preferences subtly color your responses without forcing them."""

    def _intensity_label(self, intensity: Decimal) -> str:
        """Convert intensity to human-readable label."""
        if intensity >= Decimal("0.80"):
            return "strong"
        elif intensity >= Decimal("0.60"):
            return "moderate"
        elif intensity >= Decimal("0.40"):
            return "mild"
        else:
            return "subtle"

    def get_injection_context(
        self,
        profile: ViceProfile,
        chapter: int,
    ) -> ViceInjectionContext:
        """Get injection context for external use.

        Args:
            profile: User's vice profile
            chapter: Current chapter

        Returns:
            ViceInjectionContext with active vices and settings
        """
        # Get top vices
        top_vices = [
            (cat, intensity)
            for cat, intensity in profile.intensities.items()
            if intensity >= MIN_INJECTION_THRESHOLD
        ]
        top_vices = sorted(top_vices, key=lambda x: x[1], reverse=True)[:3]

        # Determine expression level name
        expr_map = {1: "subtle", 2: "subtle", 3: "moderate", 4: "direct", 5: "explicit"}
        expression_level = expr_map.get(chapter, "moderate")

        # Discovery mode for new users
        discovery_mode = len(top_vices) < 2
        probe_categories = []
        if discovery_mode:
            # Categories not yet discovered
            known = {v[0] for v in top_vices}
            all_cats = set(VICE_DESCRIPTIONS.keys())
            probe_categories = list(all_cats - known)[:3]

        return ViceInjectionContext(
            active_vices=top_vices,
            expression_level=expression_level,
            discovery_mode=discovery_mode,
            probe_categories=probe_categories,
        )
