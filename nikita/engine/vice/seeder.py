"""Vice seeder — Spec 104 Story 1.

Maps onboarding darkness_level to initial vice category weights.
Called from complete_onboarding() to seed initial preferences.

3-tier mapping:
- Low (1-2): vulnerability + intellectual_dominance (gentle)
- Mid (3): moderate spread across categories
- High (4-5): dark_humor + emotional_intensity (edgy)
"""

import logging
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)

# Tier mappings: category → initial_intensity
TIER_LOW = {
    "vulnerability": 2,
    "intellectual_dominance": 2,
}

TIER_MID = {
    "vulnerability": 2,
    "intellectual_dominance": 2,
    "emotional_intensity": 2,
    "dark_humor": 1,
    "sexuality": 1,
}

TIER_HIGH = {
    "dark_humor": 3,
    "emotional_intensity": 3,
    "risk_taking": 2,
    "sexuality": 2,
    "vulnerability": 1,
}


def _get_tier(darkness_level: int) -> dict[str, int]:
    """Map darkness_level to vice tier."""
    if darkness_level <= 2:
        return TIER_LOW
    elif darkness_level == 3:
        return TIER_MID
    else:  # 4-5
        return TIER_HIGH


async def seed_vices_from_profile(
    user_id: UUID,
    profile: dict[str, Any] | None,
    vice_repo: Any,
) -> list[Any]:
    """Seed initial vice preferences from onboarding profile.

    Args:
        user_id: User's UUID.
        profile: Onboarding profile dict (must contain 'darkness_level').
        vice_repo: VicePreferenceRepository instance.

    Returns:
        List of created vice preferences.
    """
    if not profile or "darkness_level" not in profile:
        return []

    darkness_level = profile["darkness_level"]
    if not isinstance(darkness_level, int) or not 1 <= darkness_level <= 5:
        logger.warning("Invalid darkness_level=%s for user=%s", darkness_level, user_id)
        return []

    tier = _get_tier(darkness_level)
    created = []

    for category, intensity in tier.items():
        try:
            pref = await vice_repo.discover(
                user_id=user_id,
                category=category,
                initial_intensity=intensity,
            )
            created.append(pref)
        except Exception as e:
            logger.warning(
                "Failed to seed vice %s for user %s: %s",
                category,
                user_id,
                str(e),
            )

    logger.info(
        "Seeded %d vices for user %s (darkness_level=%d)",
        len(created),
        user_id,
        darkness_level,
    )
    return created
