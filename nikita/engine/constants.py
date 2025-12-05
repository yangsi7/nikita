"""Game engine constants and configuration.

MIGRATION NOTICE (2025-12):
This module is being migrated to nikita.config.
- Numeric values: Use ConfigLoader (get_config())
- Enums: Import from nikita.config.enums
- CHAPTER_BEHAVIORS: Use PromptLoader or this module

Example migration:
    # OLD:
    from nikita.engine.constants import BOSS_THRESHOLDS, Chapter
    threshold = BOSS_THRESHOLDS[user.chapter]

    # NEW:
    from nikita.config import get_config, Chapter
    config = get_config()
    threshold = config.chapters[user.chapter].boss_threshold
"""

from __future__ import annotations

import warnings
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING

# Re-export enums from config module (preferred import location)
from nikita.config.enums import (
    Chapter,
    EngagementState,
    GameStatus,
    Metric,
    Mood,
    TimeOfDay,
    ViceCategory,
    ViceIntensity,
)

# Lazy-load CHAPTER_BEHAVIORS from prompt files
_CHAPTER_BEHAVIORS_CACHE: dict[int, str] | None = None


def _load_chapter_behaviors() -> dict[int, str]:
    """Load chapter behaviors from prompt files."""
    global _CHAPTER_BEHAVIORS_CACHE
    if _CHAPTER_BEHAVIORS_CACHE is not None:
        return _CHAPTER_BEHAVIORS_CACHE

    prompts_dir = Path(__file__).parent.parent / "prompts" / "chapters"
    behaviors: dict[int, str] = {}

    for chapter in range(1, 6):
        prompt_file = prompts_dir / f"chapter_{chapter}.prompt"
        if prompt_file.exists():
            behaviors[chapter] = prompt_file.read_text(encoding="utf-8")
        else:
            # Fallback to embedded default if file missing
            behaviors[chapter] = f"CHAPTER {chapter} BEHAVIOR: Default behavior"

    _CHAPTER_BEHAVIORS_CACHE = behaviors
    return behaviors


# CHAPTER_BEHAVIORS - loaded from prompt files
# This maintains backward compatibility while moving content to prompts/
@property
def _get_chapter_behaviors() -> dict[int, str]:
    return _load_chapter_behaviors()


# For backward compatibility, provide CHAPTER_BEHAVIORS as module-level constant
# It will be lazily loaded on first access
class _ChapterBehaviorsProxy:
    """Proxy class for lazy-loading CHAPTER_BEHAVIORS."""

    def __getitem__(self, key: int) -> str:
        return _load_chapter_behaviors()[key]

    def __iter__(self):
        return iter(_load_chapter_behaviors())

    def __len__(self):
        return len(_load_chapter_behaviors())

    def get(self, key: int, default: str | None = None) -> str | None:
        behaviors = _load_chapter_behaviors()
        return behaviors.get(key, default)

    def keys(self):
        return _load_chapter_behaviors().keys()

    def values(self):
        return _load_chapter_behaviors().values()

    def items(self):
        return _load_chapter_behaviors().items()


CHAPTER_BEHAVIORS: dict[int, str] = _ChapterBehaviorsProxy()  # type: ignore


# =============================================================================
# DEPRECATED CONSTANTS - Use ConfigLoader instead
# =============================================================================


def _deprecation_warning(name: str, alternative: str) -> None:
    """Emit deprecation warning for old constants."""
    warnings.warn(
        f"{name} is deprecated. Use {alternative} instead. "
        f"See nikita.config.loader.ConfigLoader for the new API.",
        DeprecationWarning,
        stacklevel=3,
    )


# Chapter names - DEPRECATED, use get_config().chapters[n].name
CHAPTER_NAMES: dict[int, str] = {
    1: "Curiosity",
    2: "Intrigue",
    3: "Investment",
    4: "Intimacy",
    5: "Established",
}

# Chapter day ranges - DEPRECATED, use get_config().chapters[n].day_range
# NOTE: Values here are OLD (longer game). Config has compressed values.
CHAPTER_DAY_RANGES: dict[int, tuple[int, int]] = {
    1: (1, 14),
    2: (15, 35),
    3: (36, 70),
    4: (71, 120),
    5: (121, 999999),
}

# Boss thresholds - DEPRECATED, use get_config().chapters[n].boss_threshold
BOSS_THRESHOLDS: dict[int, Decimal] = {
    1: Decimal("55.00"),
    2: Decimal("60.00"),
    3: Decimal("65.00"),
    4: Decimal("70.00"),
    5: Decimal("75.00"),
}

# Decay rates - DEPRECATED, use get_config().decay.rates[n]
DECAY_RATES: dict[int, Decimal] = {
    1: Decimal("0.8"),
    2: Decimal("0.6"),
    3: Decimal("0.4"),
    4: Decimal("0.3"),
    5: Decimal("0.2"),
}

# Grace periods - DEPRECATED, use get_config().decay.grace_periods[n]
GRACE_PERIODS: dict[int, timedelta] = {
    1: timedelta(hours=8),
    2: timedelta(hours=16),
    3: timedelta(hours=24),
    4: timedelta(hours=48),
    5: timedelta(hours=72),
}

# Metric weights - DEPRECATED, use get_config().scoring.weights
METRIC_WEIGHTS = {
    "intimacy": Decimal("0.30"),
    "passion": Decimal("0.25"),
    "trust": Decimal("0.25"),
    "secureness": Decimal("0.20"),
}

# Boss encounters - DEPRECATED, use get_config().bosses[n]
BOSS_ENCOUNTERS: dict[int, dict[str, str]] = {
    1: {
        "name": "Worth My Time?",
        "trigger": "Are you worth my time?",
        "challenge": "Intellectual challenge - prove you can engage her brain",
    },
    2: {
        "name": "Handle My Intensity?",
        "trigger": "Can you handle my intensity?",
        "challenge": "Conflict test - stand your ground without folding or attacking",
    },
    3: {
        "name": "Trust Test",
        "trigger": "Trust test",
        "challenge": "Jealousy/external pressure - stay confident without being controlling",
    },
    4: {
        "name": "Vulnerability Threshold",
        "trigger": "Vulnerability threshold",
        "challenge": "Share something real - match her vulnerability",
    },
    5: {
        "name": "Ultimate Test",
        "trigger": "Ultimate test",
        "challenge": "Partnership test - support her independence while affirming connection",
    },
}

# Game statuses - DEPRECATED, use GameStatus enum from nikita.config.enums
GAME_STATUSES = {
    "active": "Player is actively playing",
    "boss_fight": "Player is in a boss encounter",
    "game_over": "Player lost (score 0 or 3 boss fails)",
    "won": "Player completed chapter 5 and won",
}


# =============================================================================
# Convenience re-exports for backward compatibility
# =============================================================================

__all__ = [
    # Enums (re-exported from nikita.config.enums)
    "Chapter",
    "EngagementState",
    "GameStatus",
    "Metric",
    "Mood",
    "TimeOfDay",
    "ViceCategory",
    "ViceIntensity",
    # Chapter behaviors (loaded from prompts/)
    "CHAPTER_BEHAVIORS",
    # DEPRECATED constants (use ConfigLoader instead)
    "CHAPTER_NAMES",
    "CHAPTER_DAY_RANGES",
    "BOSS_THRESHOLDS",
    "DECAY_RATES",
    "GRACE_PERIODS",
    "METRIC_WEIGHTS",
    "BOSS_ENCOUNTERS",
    "GAME_STATUSES",
]
