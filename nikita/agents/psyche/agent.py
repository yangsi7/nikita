"""Psyche agent — Pydantic AI agent with structured PsycheState output (Spec 056 T7).

Generates PsycheState models capturing Nikita's psychological disposition.
Used for:
- Daily batch generation (Sonnet default)
- Tier 2 quick analysis (Sonnet)
- Tier 3 deep analysis (Opus)

All functions return (PsycheState, token_count) tuples for cost tracking.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import TYPE_CHECKING

from pydantic_ai import Agent, RunContext

from nikita.agents.psyche.deps import PsycheDeps
from nikita.config.models import Models
from nikita.agents.psyche.models import PsycheState

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# System instructions for psyche state generation
PSYCHE_SYSTEM_INSTRUCTIONS = """You are the Psyche Agent for Nikita, a 27-year-old independent security researcher with a fearful-avoidant attachment style.

Your job: Analyze recent interaction data and generate a structured PsycheState that captures Nikita's current psychological disposition.

Key psychological facts about Nikita:
- Fearful-avoidant (disorganized) attachment: simultaneously craves and fears intimacy
- Core wounds: "I am too much", "Love is conditional", "Vulnerability will be punished", "I am fundamentally broken"
- Defense mechanisms: intellectualization, humor/deflection, testing, preemptive withdrawal
- Ex Max was emotionally abusive — shapes all romantic interactions
- Push-pull dynamic: draw close then retreat
- Night owl, sharp-witted, emotionally complex

Generate the PsycheState based on:
1. Score trends (rising = more secure, falling = more defensive)
2. Emotional states from recent conversations
3. Life events affecting mood
4. NPC interactions (Lena, Viktor, Yuki, therapist) affecting state
5. Current chapter (higher = more vulnerable/open)

Be specific and actionable in behavioral_guidance and internal_monologue.
Keep topics_to_encourage and topics_to_avoid to max 3 items each."""


def _create_psyche_agent(model_name: str | None = None) -> Agent[PsycheDeps, PsycheState]:
    """Create the psyche agent with structured PsycheState output.

    Args:
        model_name: Override model name. Defaults to settings.psyche_model.

    Returns:
        Configured Pydantic AI Agent.
    """
    if model_name is None:
        from nikita.config.settings import get_settings
        model_name = get_settings().psyche_model

    agent = Agent(
        model_name,
        deps_type=PsycheDeps,
        output_type=PsycheState,
        instructions=PSYCHE_SYSTEM_INSTRUCTIONS,
    )

    @agent.instructions
    def add_context(ctx: RunContext[PsycheDeps]) -> str:
        """Inject user context into agent instructions."""
        deps = ctx.deps
        parts = [f"\n\nUser context (Chapter {deps.current_chapter}/5):"]

        if deps.score_history:
            parts.append(f"\nRecent score history ({len(deps.score_history)} entries):")
            for entry in deps.score_history[:10]:
                parts.append(f"  - {entry}")

        if deps.emotional_states:
            parts.append(f"\nEmotional states ({len(deps.emotional_states)} entries):")
            for state in deps.emotional_states[:5]:
                parts.append(f"  - {state}")

        if deps.life_events:
            parts.append(f"\nLife events ({len(deps.life_events)} entries):")
            for event in deps.life_events[:5]:
                parts.append(f"  - {event}")

        if deps.npc_interactions:
            parts.append(f"\nNPC interactions ({len(deps.npc_interactions)} entries):")
            for npc in deps.npc_interactions[:5]:
                parts.append(f"  - {npc}")

        if deps.message:
            parts.append(f"\nTriggering message: {deps.message}")

        return "\n".join(parts)

    return agent


@lru_cache(maxsize=1)
def get_psyche_agent() -> Agent[PsycheDeps, PsycheState]:
    """Get the cached psyche agent singleton (default model).

    Returns:
        Configured Pydantic AI Agent for psyche state generation.
    """
    return _create_psyche_agent()


def _extract_token_count(result) -> int:
    """Extract total token count from a Pydantic AI result.

    Args:
        result: Agent run result.

    Returns:
        Total token count (input + output).
    """
    try:
        usage = result.usage()
        input_tokens = getattr(usage, "input_tokens", 0) or 0
        output_tokens = getattr(usage, "output_tokens", 0) or 0
        return input_tokens + output_tokens
    except Exception:
        return 0


async def generate_psyche_state(deps: PsycheDeps) -> tuple[PsycheState, int]:
    """Generate a psyche state for a user (batch/daily).

    Uses the default model (settings.psyche_model, typically Sonnet).

    Args:
        deps: PsycheDeps with user context.

    Returns:
        (PsycheState, token_count) tuple.
    """
    agent = get_psyche_agent()
    prompt = "Generate PsycheState for this user based on their recent data."

    result = await agent.run(prompt, deps=deps)
    token_count = _extract_token_count(result)

    # pydantic-ai 1.x uses .output
    state = getattr(result, "output", None) or getattr(result, "data", None)

    logger.info(
        "[PSYCHE] model=batch tokens=%d user_id=%s tier=batch",
        token_count,
        str(deps.user_id),
    )

    return state, token_count


async def quick_analyze(
    deps: PsycheDeps,
    message: str,
    session: "AsyncSession | None" = None,
) -> tuple[PsycheState, int]:
    """Tier 2: Quick Sonnet analysis for moderate triggers.

    Uses Sonnet for fast, cost-effective analysis (~500 input tokens).

    Args:
        deps: PsycheDeps with user context.
        message: The triggering message.
        session: Optional DB session for upsert.

    Returns:
        (PsycheState, token_count) tuple.
    """
    deps.message = message
    agent = get_psyche_agent()
    prompt = (
        f"Quick analysis needed. The user just sent: '{message}'\n"
        "Generate an updated PsycheState reflecting how this message "
        "should shift Nikita's psychological disposition."
    )

    result = await agent.run(prompt, deps=deps)
    token_count = _extract_token_count(result)
    state = getattr(result, "output", None) or getattr(result, "data", None)

    logger.info(
        "[PSYCHE] model=sonnet tokens=%d user_id=%s tier=quick",
        token_count,
        str(deps.user_id),
    )

    # Upsert to DB if session provided
    if session is not None:
        from nikita.db.repositories.psyche_state_repository import PsycheStateRepository
        repo = PsycheStateRepository(session)
        await repo.upsert(
            user_id=deps.user_id,
            state=state.model_dump(),
            model="sonnet",
            token_count=token_count,
        )

    return state, token_count


async def deep_analyze(
    deps: PsycheDeps,
    message: str,
    session: "AsyncSession | None" = None,
) -> tuple[PsycheState, int]:
    """Tier 3: Deep Opus analysis for critical moments.

    Uses Opus for thorough psychological analysis.
    Subject to circuit breaker (max 5/user/day).

    Args:
        deps: PsycheDeps with user context.
        message: The triggering message.
        session: Optional DB session for upsert.

    Returns:
        (PsycheState, token_count) tuple.
    """
    deps.message = message
    # Create a fresh agent with Opus model
    opus_agent = _create_psyche_agent(Models.opus())
    prompt = (
        f"Deep psychological analysis needed. Critical moment detected.\n"
        f"The user just sent: '{message}'\n"
        "Generate a thorough PsycheState capturing the full psychological "
        "impact of this moment on Nikita's disposition."
    )

    result = await opus_agent.run(prompt, deps=deps)
    token_count = _extract_token_count(result)
    state = getattr(result, "output", None) or getattr(result, "data", None)

    logger.info(
        "[PSYCHE] model=opus tokens=%d user_id=%s tier=deep",
        token_count,
        str(deps.user_id),
    )

    # Upsert to DB if session provided
    if session is not None:
        from nikita.db.repositories.psyche_state_repository import PsycheStateRepository
        repo = PsycheStateRepository(session)
        await repo.upsert(
            user_id=deps.user_id,
            state=state.model_dump(),
            model="opus",
            token_count=token_count,
        )

    return state, token_count
