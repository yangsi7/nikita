"""
Vice Service Module (T031, T040)

High-level orchestration service for vice personalization.
Coordinates analyzer, scorer, injector, and boundary enforcer.
"""

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from nikita.config.enums import ViceCategory
from nikita.engine.vice.analyzer import ViceAnalyzer
from nikita.engine.vice.boundaries import ViceBoundaryEnforcer
from nikita.engine.vice.injector import VicePromptInjector
from nikita.engine.vice.models import ViceInjectionContext, ViceProfile, ViceSignal
from nikita.engine.vice.scorer import ViceScorer

if TYPE_CHECKING:
    from nikita.engine.vice.models import ViceAnalysisResult


# Discovery settings
MAX_PROBE_CATEGORIES = 3
MIN_VICES_FOR_STABLE_PROFILE = 3


class ViceService:
    """T040: High-level vice personalization service.

    Orchestrates vice detection, scoring, injection, and boundary enforcement.
    """

    def __init__(self):
        """Initialize vice service with all components."""
        self._analyzer = ViceAnalyzer()
        self._scorer = ViceScorer()
        self._injector = VicePromptInjector()
        self._enforcer = ViceBoundaryEnforcer()

    async def get_prompt_context(
        self,
        profile: ViceProfile,
        chapter: int,
    ) -> ViceInjectionContext:
        """Get vice injection context for prompt generation.

        AC-T040.1: Returns ViceInjectionContext for prompt building.

        Args:
            profile: User's vice profile
            chapter: Current chapter (1-5)

        Returns:
            ViceInjectionContext with active vices and settings
        """
        # Apply boundary caps to intensities
        capped_vices: list[tuple[str, Decimal]] = []
        for cat, intensity in profile.intensities.items():
            capped = self._enforcer.apply_cap(cat, intensity, chapter)
            if capped >= Decimal("0.30"):  # Only include significant vices
                capped_vices.append((cat, capped))

        # Sort by intensity and take top 3
        capped_vices = sorted(capped_vices, key=lambda x: x[1], reverse=True)[:3]

        # Determine discovery mode
        discovered_count = sum(1 for v in profile.intensities.values() if v > Decimal("0"))
        discovery_mode = discovered_count < MIN_VICES_FOR_STABLE_PROFILE

        # Get probe categories if in discovery mode
        probe_categories = []
        if discovery_mode:
            probe_categories = self.get_probe_categories(profile)

        # Expression level based on chapter
        expr_map = {1: "subtle", 2: "subtle", 3: "moderate", 4: "direct", 5: "explicit"}
        expression_level = expr_map.get(chapter, "moderate")

        return ViceInjectionContext(
            active_vices=capped_vices,
            expression_level=expression_level,
            discovery_mode=discovery_mode,
            probe_categories=probe_categories,
        )

    async def process_conversation(
        self,
        user_id: UUID,
        user_message: str,
        nikita_message: str,
        conversation_id: UUID,
    ) -> dict:
        """Process a conversation exchange for vice signals.

        AC-T040.2: Analyzes exchange and updates profile.

        Args:
            user_id: User's UUID
            user_message: User's message
            nikita_message: Nikita's response
            conversation_id: Conversation ID for tracing

        Returns:
            Processing result dict
        """
        # Analyze the exchange
        analysis = await self._analyzer.analyze_exchange(
            user_message=user_message,
            nikita_response=nikita_message,
            conversation_id=conversation_id,
        )

        # Process any detected signals
        if analysis.signals:
            result = await self._scorer.process_signals(user_id, analysis.signals)
        else:
            result = {"processed": 0}

        result["signals_detected"] = len(analysis.signals)
        return result

    async def process_conversation_signals(
        self,
        user_id: UUID,
        signals: list[ViceSignal],
    ) -> dict:
        """Process pre-analyzed vice signals.

        Args:
            user_id: User's UUID
            signals: List of ViceSignal objects

        Returns:
            Processing result dict
        """
        return await self._scorer.process_signals(user_id, signals)

    def get_probe_categories(self, profile: ViceProfile) -> list[str]:
        """Get vice categories to probe for discovery.

        AC-T031.1: New users get varied hints
        AC-T031.2: Unexplored categories get probed
        AC-T031.3: Probe frequency decreases as profile stabilizes

        Args:
            profile: User's current vice profile

        Returns:
            List of category names to probe
        """
        # Get all categories
        all_categories = {vc.value for vc in ViceCategory}

        # Find discovered categories (intensity > 0)
        discovered = {
            cat for cat, intensity in profile.intensities.items()
            if intensity > Decimal("0")
        }

        # Unexplored categories
        unexplored = all_categories - discovered

        # Limit based on profile maturity
        if len(discovered) >= MIN_VICES_FOR_STABLE_PROFILE:
            # Stable profile - fewer probes
            max_probes = 1
        else:
            # New profile - more probes
            max_probes = MAX_PROBE_CATEGORIES

        return list(unexplored)[:max_probes]

    def inject_vices_into_prompt(
        self,
        base_prompt: str,
        profile: ViceProfile,
        chapter: int,
    ) -> str:
        """Inject vice preferences into a base prompt.

        Convenience method wrapping injector.

        Args:
            base_prompt: Base system prompt
            profile: User's vice profile
            chapter: Current chapter

        Returns:
            Modified prompt with vice injection
        """
        return self._injector.inject(base_prompt, profile, chapter)

    async def get_user_profile(self, user_id: UUID) -> ViceProfile:
        """Get a user's vice profile.

        Args:
            user_id: User's UUID

        Returns:
            User's ViceProfile
        """
        return await self._scorer.get_profile(user_id)

    async def close(self):
        """Cleanup resources."""
        await self._scorer.close()
