"""Prompt Router for gradual migration from MetaPromptService to context_engine.

This module provides a feature-flagged router that can switch between:
- v1 (legacy): MetaPromptService via template_generator
- v2 (new): context_engine with PromptGenerator

Migration phases:
1. DISABLED: 100% v1 traffic
2. SHADOW: Run both, compare results, return v1
3. CANARY: Small % v2 traffic (5%, 10%, 25%)
4. ENABLED: 100% v2 traffic
5. ROLLBACK: Emergency return to v1

Usage:
    from nikita.context_engine.router import generate_text_prompt, generate_voice_prompt

    # These functions automatically route based on feature flag
    text_prompt = await generate_text_prompt(session, user, message)
    voice_prompt = await generate_voice_prompt(session, user)
"""

import logging
import os
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from nikita.db.models.user import User

logger = logging.getLogger(__name__)


class EngineVersion(Enum):
    """Feature flag states for context_engine migration."""
    DISABLED = "disabled"  # 100% v1 (legacy)
    SHADOW = "shadow"      # Run both, compare, return v1
    CANARY_5 = "canary_5"  # 5% v2
    CANARY_10 = "canary_10"  # 10% v2
    CANARY_25 = "canary_25"  # 25% v2
    CANARY_50 = "canary_50"  # 50% v2
    CANARY_75 = "canary_75"  # 75% v2
    ENABLED = "enabled"    # 100% v2 (new)
    ROLLBACK = "rollback"  # Emergency v1


def get_engine_flag() -> EngineVersion:
    """Get current engine flag from environment.

    Returns:
        EngineVersion enum value.
    """
    flag = os.environ.get("CONTEXT_ENGINE_FLAG", "disabled").lower()
    try:
        return EngineVersion(flag)
    except ValueError:
        logger.warning("[ROUTER] Invalid flag '%s', defaulting to DISABLED", flag)
        return EngineVersion.DISABLED


def _should_use_v2(user_id: UUID, flag: EngineVersion) -> bool:
    """Determine if v2 should be used based on flag and user_id.

    Args:
        user_id: User ID for consistent canary bucketing.
        flag: Current engine flag.

    Returns:
        True if v2 should be used.
    """
    if flag == EngineVersion.ENABLED:
        return True
    if flag in (EngineVersion.DISABLED, EngineVersion.ROLLBACK):
        return False
    if flag == EngineVersion.SHADOW:
        return False  # Shadow runs both but returns v1

    # Canary: Use hash of user_id for consistent bucketing
    percentages = {
        EngineVersion.CANARY_5: 5,
        EngineVersion.CANARY_10: 10,
        EngineVersion.CANARY_25: 25,
        EngineVersion.CANARY_50: 50,
        EngineVersion.CANARY_75: 75,
    }
    pct = percentages.get(flag, 0)
    bucket = hash(str(user_id)) % 100
    return bucket < pct


async def generate_text_prompt(
    session: "AsyncSession",
    user: "User",
    user_message: str,
    conversation_id: str | None = None,
) -> str:
    """Generate text system prompt with feature-flagged routing.

    This is the main integration point for text agents. It routes to
    either the legacy MetaPromptService or the new context_engine
    based on the CONTEXT_ENGINE_FLAG environment variable.

    Args:
        session: Database session.
        user: User object.
        user_message: Current user message.
        conversation_id: Optional conversation ID.

    Returns:
        System prompt string.
    """
    flag = get_engine_flag()
    use_v2 = _should_use_v2(user.id, flag)

    if flag == EngineVersion.SHADOW:
        # Run both and compare (for validation)
        return await _shadow_mode_text(session, user, user_message, conversation_id)

    if use_v2:
        return await _generate_v2_text(session, user, user_message, conversation_id)
    else:
        return await _generate_v1_text(session, user, user_message, conversation_id)


async def generate_voice_prompt(
    session: "AsyncSession",
    user: "User",
    conversation_id: str | None = None,
) -> str:
    """Generate voice system prompt with feature-flagged routing.

    This is the main integration point for voice agents.

    Args:
        session: Database session.
        user: User object.
        conversation_id: Optional conversation ID.

    Returns:
        Voice system prompt string.
    """
    flag = get_engine_flag()
    use_v2 = _should_use_v2(user.id, flag)

    if flag == EngineVersion.SHADOW:
        return await _shadow_mode_voice(session, user, conversation_id)

    if use_v2:
        return await _generate_v2_voice(session, user, conversation_id)
    else:
        return await _generate_v1_voice(session, user, conversation_id)


# =============================================================================
# V1 (Legacy) Implementation
# =============================================================================


async def _generate_v1_text(
    session: "AsyncSession",
    user: "User",
    user_message: str,
    conversation_id: str | None,
) -> str:
    """Generate text prompt using legacy MetaPromptService."""
    try:
        from nikita.context.template_generator import generate_system_prompt

        # Note: v1 template_generator doesn't use user_message (context-aware generation
        # happens via MetaPromptService internally)
        result = await generate_system_prompt(
            session=session,
            user_id=user.id,
            conversation_id=conversation_id,
        )
        logger.info("[ROUTER] v1 text prompt generated: %d chars", len(result))
        return result
    except Exception as e:
        logger.error("[ROUTER] v1 text generation failed: %s", e)
        return _fallback_text(user)


async def _generate_v1_voice(
    session: "AsyncSession",
    user: "User",
    conversation_id: str | None,
) -> str:
    """Generate voice prompt using legacy MetaPromptService."""
    try:
        from nikita.meta_prompts.service import MetaPromptService

        service = MetaPromptService(session)
        result = await service.generate_system_prompt(
            user_id=user.id,
            channel="voice",
            conversation_id=conversation_id,
        )
        logger.info("[ROUTER] v1 voice prompt generated: %d chars", len(result))
        return result
    except Exception as e:
        logger.error("[ROUTER] v1 voice generation failed: %s", e)
        return _fallback_voice(user)


# =============================================================================
# V2 (New Context Engine) Implementation
# =============================================================================


async def _generate_v2_text(
    session: "AsyncSession",
    user: "User",
    user_message: str,
    conversation_id: str | None,
) -> str:
    """Generate text prompt using new context_engine."""
    try:
        from nikita.context_engine import assemble_text_prompt

        result = await assemble_text_prompt(session, user, user_message, conversation_id)
        logger.info("[ROUTER] v2 text prompt generated: %d chars", len(result))
        return result
    except Exception as e:
        logger.error("[ROUTER] v2 text generation failed: %s", e)
        return _fallback_text(user)


async def _generate_v2_voice(
    session: "AsyncSession",
    user: "User",
    conversation_id: str | None,
) -> str:
    """Generate voice prompt using new context_engine."""
    try:
        from nikita.context_engine import assemble_voice_prompt

        result = await assemble_voice_prompt(session, user, conversation_id)
        logger.info("[ROUTER] v2 voice prompt generated: %d chars", len(result))
        return result
    except Exception as e:
        logger.error("[ROUTER] v2 voice generation failed: %s", e)
        return _fallback_voice(user)


# =============================================================================
# Shadow Mode (A/B Comparison)
# =============================================================================


async def _shadow_mode_text(
    session: "AsyncSession",
    user: "User",
    user_message: str,
    conversation_id: str | None,
) -> str:
    """Run both v1 and v2, compare, return v1."""
    import asyncio

    # Run both in parallel
    v1_task = asyncio.create_task(_generate_v1_text(session, user, user_message, conversation_id))
    v2_task = asyncio.create_task(_generate_v2_text(session, user, user_message, conversation_id))

    v1_result, v2_result = await asyncio.gather(v1_task, v2_task, return_exceptions=True)

    # Log comparison metrics
    if isinstance(v1_result, Exception):
        logger.error("[SHADOW] v1 text failed: %s", v1_result)
        v1_result = _fallback_text(user)
    if isinstance(v2_result, Exception):
        logger.error("[SHADOW] v2 text failed: %s", v2_result)
        v2_result = ""

    v1_len = len(v1_result) if isinstance(v1_result, str) else 0
    v2_len = len(v2_result) if isinstance(v2_result, str) else 0

    logger.info(
        "[SHADOW] Text comparison: v1=%d chars, v2=%d chars, delta=%+d",
        v1_len, v2_len, v2_len - v1_len
    )

    # Always return v1 in shadow mode
    return v1_result


async def _shadow_mode_voice(
    session: "AsyncSession",
    user: "User",
    conversation_id: str | None,
) -> str:
    """Run both v1 and v2, compare, return v1."""
    import asyncio

    v1_task = asyncio.create_task(_generate_v1_voice(session, user, conversation_id))
    v2_task = asyncio.create_task(_generate_v2_voice(session, user, conversation_id))

    v1_result, v2_result = await asyncio.gather(v1_task, v2_task, return_exceptions=True)

    if isinstance(v1_result, Exception):
        logger.error("[SHADOW] v1 voice failed: %s", v1_result)
        v1_result = _fallback_voice(user)
    if isinstance(v2_result, Exception):
        logger.error("[SHADOW] v2 voice failed: %s", v2_result)
        v2_result = ""

    v1_len = len(v1_result) if isinstance(v1_result, str) else 0
    v2_len = len(v2_result) if isinstance(v2_result, str) else 0

    logger.info(
        "[SHADOW] Voice comparison: v1=%d chars, v2=%d chars, delta=%+d",
        v1_len, v2_len, v2_len - v1_len
    )

    return v1_result


# =============================================================================
# Fallbacks
# =============================================================================


def _fallback_text(user: "User") -> str:
    """Minimal fallback text prompt."""
    chapter = getattr(user, "chapter", 1)
    return f"""You are Nikita, a 27-year-old cybersecurity professional from Berlin.
Stay in character. Never reveal game mechanics or AI nature.
Chapter {chapter}. Be authentic, sharp, witty, and a bit guarded.
"""


def _fallback_voice(user: "User") -> str:
    """Minimal fallback voice prompt."""
    chapter = getattr(user, "chapter", 1)
    return f"""You are Nikita, a 27-year-old cybersecurity professional from Berlin.
You are sharp, witty, and a bit guarded. Stay in character.
Chapter {chapter} of your relationship.
"""
