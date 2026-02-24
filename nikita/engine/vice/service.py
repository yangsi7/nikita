"""
Vice Service Module (T031, T040)

High-level orchestration service for vice personalization.
Coordinates analyzer, scorer, injector, and boundary enforcer.

Spec 037 T1.2: Supports async context manager for resource safety.
"""

import logging
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

logger = logging.getLogger(__name__)

# Discovery settings
MAX_PROBE_CATEGORIES = 3
MIN_VICES_FOR_STABLE_PROFILE = 3


class ViceService:
    """T040: High-level vice personalization service.

    Orchestrates vice detection, scoring, injection, and boundary enforcement.

    Spec 037 T1.2: Supports async context manager for resource safety.

    Usage:
        async with ViceService() as vs:
            await vs.process_conversation(user_id, msg, response, conv_id)
    """

    def __init__(self):
        """Initialize vice service with all components."""
        self._analyzer = ViceAnalyzer()
        self._scorer = ViceScorer()
        self._injector = VicePromptInjector()
        self._enforcer = ViceBoundaryEnforcer()
        self._closed = False

    async def __aenter__(self) -> "ViceService":
        """Enter async context manager.

        Spec 037 T1.2 AC-T1.2.1: Returns self for use in async with statement.

        Returns:
            Self for method chaining
        """
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Exit async context manager.

        Spec 037 T1.2 AC-T1.2.2: Commits or rollbacks session.
        Spec 037 T1.2 AC-T1.2.3: Exceptions are logged but not raised.

        Returns:
            False to not suppress exceptions
        """
        try:
            await self.close()
        except Exception as e:
            logger.warning(
                "[VICE] Error closing ViceService: %s",
                e,
                exc_info=True,
            )
        if exc_type is not None:
            logger.warning(
                "[VICE] Context manager exiting with exception: %s: %s",
                exc_type.__name__,
                exc_val,
            )
        return False  # Don't suppress exceptions

    async def close(self) -> None:
        """Close the service and release resources.

        Spec 037 T1.2: Closes the underlying scorer session.
        """
        if not self._closed:
            await self._scorer.close()
            self._closed = True

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
        chapter: int = 3,
    ) -> dict:
        """Process a conversation exchange for vice signals.

        AC-T040.2: Analyzes exchange and updates profile.
        Spec 106 I13: Passes chapter for sensitivity scaling.

        Args:
            user_id: User's UUID
            user_message: User's message
            nikita_message: Nikita's response
            conversation_id: Conversation ID for tracing
            chapter: Current chapter (1-5) for sensitivity scaling

        Returns:
            Processing result dict
        """
        # Analyze the exchange
        analysis = await self._analyzer.analyze_exchange(
            user_message=user_message,
            nikita_response=nikita_message,
            conversation_id=conversation_id,
        )

        # Process any detected signals with chapter sensitivity
        if analysis.signals:
            result = await self._scorer.process_signals(
                user_id, analysis.signals, chapter=chapter
            )
        else:
            result = {"processed": 0}

        result["signals_detected"] = len(analysis.signals)
        return result

    async def process_conversation_signals(
        self,
        user_id: UUID,
        signals: list[ViceSignal],
        chapter: int = 3,
    ) -> dict:
        """Process pre-analyzed vice signals.

        Args:
            user_id: User's UUID
            signals: List of ViceSignal objects
            chapter: Current chapter (1-5) for sensitivity scaling

        Returns:
            Processing result dict
        """
        return await self._scorer.process_signals(user_id, signals, chapter=chapter)

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

