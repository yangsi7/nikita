"""Nikita Text Agent - Pydantic AI powered conversational agent.

This module implements the core Nikita text agent using Pydantic AI
with Claude Sonnet. The agent combines:
- Base persona (NIKITA_PERSONA)
- Chapter-specific behavior (CHAPTER_BEHAVIORS)
- Dynamic memory context (NikitaMemory)
"""

import logging
import time
from functools import lru_cache
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

from pydantic_ai import Agent, RunContext

from nikita.agents.text.deps import NikitaDeps
from nikita.engine.constants import CHAPTER_BEHAVIORS
from nikita.prompts.nikita_persona import NIKITA_PERSONA

if TYPE_CHECKING:
    from nikita.db.models.user import User
    from nikita.memory.graphiti_client import NikitaMemory


# Model name constant for configuration and testing
# Updated 2025-12-02: Latest Claude 4.5 for +15-20% capability improvement
MODEL_NAME = "anthropic:claude-sonnet-4-5-20250929"


def _create_nikita_agent() -> Agent[NikitaDeps, str]:
    """
    Create and configure the Nikita text agent.

    Creates the agent with all registered tools.

    Returns:
        Configured Pydantic AI Agent with NikitaDeps and tools
    """
    start_time = time.time()
    logger.info(f"[TIMING] _create_nikita_agent START")

    from nikita.agents.text.tools import format_memory_results
    logger.info(f"[TIMING] Tools imported: {time.time() - start_time:.2f}s")

    agent = Agent(
        MODEL_NAME,
        deps_type=NikitaDeps,
        output_type=str,
        instructions=NIKITA_PERSONA,  # Base persona as static instructions
    )
    logger.info(f"[TIMING] Agent object created: {time.time() - start_time:.2f}s")

    # Dynamic instructions based on user's chapter
    @agent.instructions
    def add_chapter_behavior(ctx: RunContext[NikitaDeps]) -> str:
        """Add chapter-specific behavior overlay."""
        chapter = ctx.deps.user.chapter
        chapter_behavior = CHAPTER_BEHAVIORS.get(chapter, CHAPTER_BEHAVIORS[1])
        return f"\n\n## CURRENT CHAPTER BEHAVIOR\n{chapter_behavior}"

    # Inject personalized prompt from MetaPromptService (Spec 012 Phase 4)
    @agent.instructions
    def add_personalized_context(ctx: RunContext[NikitaDeps]) -> str:
        """
        Inject personalized prompt context from MetaPromptService.

        This injects the dynamically generated prompt that includes:
        - Vice preferences (what user enjoys)
        - Engagement state (calibration hints)
        - Memory context (facts, threads, thoughts)
        - Temporal context (time of day, Nikita's mood)
        - User backstory (if onboarding complete)

        If generated_prompt is None, no additional context is injected
        (falls back to static NIKITA_PERSONA + chapter behavior).
        """
        if ctx.deps.generated_prompt:
            return f"\n\n## PERSONALIZED CONTEXT\n{ctx.deps.generated_prompt}"
        return ""

    # Register the recall_memory tool with retries
    @agent.tool(retries=2)
    async def recall_memory(ctx: RunContext[NikitaDeps], query: str) -> str:
        """
        Search memory for relevant information about a topic.

        Use this when you need to recall specific details about:
        - The person you're talking to (their job, interests, history)
        - Your shared history together (past conversations, inside jokes)
        - Your own life events (work projects, mood, recent events)

        Args:
            ctx: Run context with dependencies
            query: What to search for in memory

        Returns:
            Relevant memories formatted as text
        """
        if ctx.deps.memory is None:
            return "Memory system is not available right now."
        try:
            results = await ctx.deps.memory.search_memory(query, limit=5)
            return format_memory_results(results)
        except Exception as e:
            # Gracefully degrade when memory operations fail (e.g., OpenAI quota exceeded)
            logger.warning(f"[MEMORY] recall_memory failed: {type(e).__name__}: {e}")
            return "Memory is temporarily unavailable. I'll work with what I know."

    # Register the note_user_fact tool
    @agent.tool
    async def note_user_fact(ctx: RunContext[NikitaDeps], fact: str, confidence: float) -> str:
        """
        Record a fact about the person you're talking to.

        Use this when you learn something new about them:
        - Explicit facts (high confidence 0.85-0.95): Things they directly tell you
          e.g., "I work at Tesla" → fact="User works at Tesla", confidence=0.9
        - Implicit facts (lower confidence 0.5-0.75): Things you infer from context
          e.g., "Work has been crazy" → fact="User may be stressed", confidence=0.65

        Args:
            ctx: Run context with dependencies
            fact: The fact statement (start with "User...")
            confidence: How confident you are (0-1)

        Returns:
            Confirmation that the fact was noted
        """
        if ctx.deps.memory is None:
            return "Memory system is not available right now, but I'll remember this."
        try:
            await ctx.deps.memory.add_user_fact(fact, confidence)
            return f"Noted: {fact}"
        except Exception as e:
            # Gracefully degrade when memory operations fail (e.g., OpenAI quota exceeded)
            logger.warning(f"[MEMORY] note_user_fact failed: {type(e).__name__}: {e}")
            return f"Couldn't save to memory right now, but I'll remember: {fact}"

    logger.info(f"[TIMING] Tools registered: {time.time() - start_time:.2f}s")
    return agent


@lru_cache(maxsize=1)
def get_nikita_agent() -> Agent[NikitaDeps, str]:
    """
    Get or create the Nikita text agent singleton.

    Uses lazy initialization to avoid API key errors during import/testing.

    Returns:
        Configured Pydantic AI Agent with NikitaDeps
    """
    return _create_nikita_agent()


# Lazy accessor - only evaluates when accessed at runtime
class _AgentProxy:
    """Proxy to lazily initialize the agent."""

    _agent: Agent[NikitaDeps, str] | None = None

    @property
    def _real_agent(self) -> Agent[NikitaDeps, str]:
        if self._agent is None:
            self._agent = get_nikita_agent()
        return self._agent

    def __getattr__(self, name: str):
        return getattr(self._real_agent, name)


# Export proxy as nikita_agent for backward compatibility
nikita_agent = _AgentProxy()


async def build_system_prompt(
    memory: "NikitaMemory | None",
    user: "User",
    user_message: str,
) -> str:
    """
    Build the complete system prompt for Nikita.

    Now uses MetaPromptService for intelligent prompt generation.
    Falls back to legacy static templates if meta-prompt fails.

    Args:
        memory: NikitaMemory instance for context retrieval
        user: User model with current chapter
        user_message: The user's message (for memory search)

    Returns:
        Complete system prompt string (~4000 tokens)
    """
    import logging

    from nikita.db.database import get_session_maker

    logger = logging.getLogger(__name__)

    try:
        # Use MetaPromptService via context module
        session_maker = get_session_maker()
        async with session_maker() as session:
            from nikita.context.template_generator import generate_system_prompt

            result = await generate_system_prompt(session, user.id)
            # Commit to persist the generated_prompts log entry
            await session.commit()
            return result

    except Exception as e:
        logger.warning(
            f"MetaPromptService failed, using legacy prompt: {e}",
            extra={"user_id": str(user.id)},
        )

        # Fallback to legacy static templates
        return await _build_system_prompt_legacy(memory, user, user_message)


async def _build_system_prompt_legacy(
    memory: "NikitaMemory | None",
    user: "User",
    user_message: str,
) -> str:
    """
    Legacy system prompt builder using static templates.

    DEPRECATED: Use MetaPromptService via build_system_prompt().

    Args:
        memory: NikitaMemory instance for context retrieval (None if unavailable)
        user: User model with current chapter
        user_message: The user's message (for memory search)

    Returns:
        Complete system prompt string
    """
    # Get chapter-specific behavior overlay
    chapter_behavior = CHAPTER_BEHAVIORS.get(user.chapter, CHAPTER_BEHAVIORS[1])

    # Get relevant memory context (skip if memory unavailable)
    if memory is not None:
        memory_context = await memory.get_context_for_prompt(user_message)
    else:
        memory_context = "Memory system temporarily unavailable."

    # Build the complete prompt
    prompt_parts = [
        NIKITA_PERSONA,
        "\n\n## CURRENT CHAPTER BEHAVIOR\n",
        chapter_behavior,
        "\n\n## RELEVANT MEMORIES\n",
        memory_context if memory_context else "No relevant memories found.",
    ]

    return "".join(prompt_parts)


async def generate_response(
    deps: NikitaDeps,
    user_message: str,
) -> str:
    """
    Generate a Nikita response to a user message.

    This is the main entry point for generating responses.
    Uses Pydantic AI's instructions decorator for dynamic prompts.

    Spec 012 Phase 4: Now calls build_system_prompt() to generate
    personalized context that is injected via @agent.instructions.

    Args:
        deps: NikitaDeps containing memory, user, and settings
        user_message: The user's message to respond to

    Returns:
        Nikita's response string
    """
    logger.info(
        f"[LLM-DEBUG] generate_response called: user_id={deps.user.id}, "
        f"message_len={len(user_message)}"
    )

    # Spec 012: Generate personalized prompt via MetaPromptService
    # This includes vices, engagement state, memory, temporal context, backstory
    try:
        start_time = time.time()
        generated = await build_system_prompt(deps.memory, deps.user, user_message)
        prompt_time_ms = (time.time() - start_time) * 1000
        deps.generated_prompt = generated
        logger.info(
            f"[PROMPT-DEBUG] Personalized prompt generated: "
            f"{len(generated)} chars, {prompt_time_ms:.0f}ms"
        )
    except Exception as e:
        # Graceful degradation: if prompt generation fails, continue with static
        logger.warning(
            f"[PROMPT-DEBUG] Failed to generate personalized prompt: {e}. "
            f"Using static NIKITA_PERSONA only."
        )
        deps.generated_prompt = None

    # Run the agent - instructions are built dynamically via @agent.instructions
    # The add_personalized_context() decorator injects deps.generated_prompt
    logger.info(f"[LLM-DEBUG] Calling nikita_agent.run() with model={MODEL_NAME}")
    result = await nikita_agent.run(
        user_message,
        deps=deps,
    )
    logger.info(
        f"[LLM-DEBUG] LLM response received: {len(result.output)} chars"
    )

    return result.output
