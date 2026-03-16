"""Opening selector — matches user profile to the best opening template."""

from __future__ import annotations

import logging
import random

from nikita.agents.voice.openings.models import Opening
from nikita.agents.voice.openings.registry import OpeningRegistry

logger = logging.getLogger(__name__)


class OpeningSelector:
    """Selects the best opening based on user's onboarding profile.

    Selection algorithm:
    1. Filter by darkness_range (drug_tolerance must be in range)
    2. Filter by scene_tags overlap (if opening has tags)
    3. Filter by life_stage_tags overlap (if opening has tags)
    4. Among matches, weighted random by `weight`
    5. Fallback: opening with is_fallback=True or 'warm_intro'
    """

    def __init__(self, registry: OpeningRegistry) -> None:
        self._registry = registry

    def select(
        self,
        drug_tolerance: int = 3,
        scene: str | None = None,
        life_stage: str | None = None,
    ) -> Opening:
        """Select the best opening for a user profile.

        Args:
            drug_tolerance: 1-5 scale from onboarding
            scene: Social scene preference (techno, art, food, etc.)
            life_stage: Career/life stage tag

        Returns:
            Best matching Opening, or fallback if no match.
        """
        candidates = self._filter(drug_tolerance, scene, life_stage)

        if not candidates:
            fallback = self._registry.get_fallback()
            if fallback:
                logger.info(
                    f"No opening matched (darkness={drug_tolerance}, scene={scene}), "
                    f"using fallback: {fallback.id}"
                )
                return fallback
            # This should never happen if templates are properly loaded
            msg = "No opening templates available and no fallback defined"
            raise ValueError(msg)

        # Weighted random selection
        weights = [c.weight for c in candidates]
        selected = random.choices(candidates, weights=weights, k=1)[0]
        logger.info(
            f"Selected opening '{selected.id}' for profile "
            f"(darkness={drug_tolerance}, scene={scene})"
        )
        return selected

    def _filter(
        self,
        drug_tolerance: int,
        scene: str | None,
        life_stage: str | None,
    ) -> list[Opening]:
        """Filter openings by profile criteria."""
        matched: list[Opening] = []

        for opening in self._registry.get_all():
            # Skip fallback from normal matching
            if opening.is_fallback:
                continue

            # 1. Darkness range must contain drug_tolerance
            low, high = opening.darkness_range
            if not (low <= drug_tolerance <= high):
                continue

            # 2. Scene tags — if opening has tags, at least one must match
            if opening.scene_tags and scene:
                if scene.lower() not in [t.lower() for t in opening.scene_tags]:
                    continue
            elif opening.scene_tags and not scene:
                # Opening requires specific scene but user has none — skip
                continue

            # 3. Life stage tags — same logic
            if opening.life_stage_tags and life_stage:
                if life_stage.lower() not in [t.lower() for t in opening.life_stage_tags]:
                    continue
            elif opening.life_stage_tags and not life_stage:
                continue

            matched.append(opening)

        return matched
