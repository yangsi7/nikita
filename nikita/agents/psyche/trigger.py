"""3-tier trigger detector for psyche analysis routing (Spec 056 T13).

Rule-based routing (<5ms) that classifies messages into:
- Tier 1 (CACHED, ~90%): Read cached psyche state, no LLM call
- Tier 2 (QUICK, ~8%): Sonnet quick analysis for moderate triggers
- Tier 3 (DEEP, ~2%): Opus deep analysis for critical moments

Circuit breaker: max 5 Tier 3 calls per user per day.
"""

from __future__ import annotations

import logging
from enum import IntEnum
from typing import Any

logger = logging.getLogger(__name__)

# Max Tier 3 (deep analysis) calls per user per day (AC-3.5)
MAX_TIER3_PER_DAY = 5

# Keywords for trigger detection (rule-based, no LLM)
TIER3_EMOTIONAL_KEYWORDS = frozenset({
    "i can't do this anymore",
    "i'm breaking down",
    "i want to die",
    "suicidal",
    "i hate myself",
    "nobody loves me",
    "i'm worthless",
    "i give up",
    "ending it",
    "self-harm",
    "panic attack",
    "crisis",
})

TIER2_EMOTIONAL_KEYWORDS = frozenset({
    "i miss you",
    "i need you",
    "i'm scared",
    "i'm sad",
    "i'm lonely",
    "i love you",
    "i'm hurt",
    "i'm anxious",
    "depressed",
    "overwhelmed",
    "heartbroken",
    "crying",
    "stressed",
    "therapy",
    "nightmare",
})


class TriggerTier(IntEnum):
    """Trigger detection tier for psyche analysis routing."""

    CACHED = 1  # Read cached state (no LLM)
    QUICK = 2   # Sonnet quick analysis
    DEEP = 3    # Opus deep analysis


def detect_trigger_tier(
    message: str,
    score_delta: float = 0.0,
    conflict_state: dict[str, Any] | None = None,
    is_first_message_today: bool = False,
    game_status: str = "active",
) -> TriggerTier:
    """Detect which analysis tier a message requires.

    Pure function, rule-based, <5ms execution.

    Args:
        message: User's message text.
        score_delta: Score change from last interaction (negative = drop).
        conflict_state: Current conflict state dict (may contain horseman info).
        is_first_message_today: Whether this is the user's first message today.
        game_status: Current game status (active, boss_fight, etc.).

    Returns:
        TriggerTier indicating required analysis depth.
    """
    message_lower = message.lower().strip()

    # --- Tier 3 checks (critical moments) ---

    # Horseman detected in conflict state
    if conflict_state:
        horseman = conflict_state.get("horseman")
        if horseman and horseman != "none":
            return TriggerTier.DEEP

    # Boss adjacent
    if game_status == "boss_fight":
        return TriggerTier.DEEP

    # Explicit emotional crisis keywords
    for keyword in TIER3_EMOTIONAL_KEYWORDS:
        if keyword in message_lower:
            return TriggerTier.DEEP

    # --- Tier 2 checks (moderate triggers) ---

    # First message of the day
    if is_first_message_today:
        return TriggerTier.QUICK

    # Score drop > 5 points
    if score_delta < -5.0:
        return TriggerTier.QUICK

    # Moderate emotional keywords
    for keyword in TIER2_EMOTIONAL_KEYWORDS:
        if keyword in message_lower:
            return TriggerTier.QUICK

    # --- Default: Tier 1 (cached read) ---
    return TriggerTier.CACHED


async def check_tier3_circuit_breaker(
    user_id,
    session,
) -> bool:
    """Check if Tier 3 analysis is allowed for this user today.

    Circuit breaker: max MAX_TIER3_PER_DAY Tier 3 calls per user per day.

    Args:
        user_id: User UUID.
        session: Database session.

    Returns:
        True if Tier 3 is allowed, False if circuit breaker triggered.
    """
    try:
        from nikita.db.repositories.psyche_state_repository import (
            PsycheStateRepository,
        )

        repo = PsycheStateRepository(session)
        count = await repo.get_tier3_count_today(user_id)
        allowed = count < MAX_TIER3_PER_DAY

        if not allowed:
            logger.warning(
                "[PSYCHE] Tier 3 circuit breaker triggered: user_id=%s count=%d limit=%d",
                str(user_id),
                count,
                MAX_TIER3_PER_DAY,
            )

        return allowed
    except Exception as e:
        logger.warning("[PSYCHE] Circuit breaker check failed: %s, allowing Tier 3", e)
        return True  # Fail open
