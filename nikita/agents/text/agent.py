"""Nikita Text Agent - Pydantic AI powered conversational agent.

This module implements the core Nikita text agent using Pydantic AI
with Claude Sonnet. The agent combines:
- Base persona (NIKITA_PERSONA)
- Chapter-specific behavior (CHAPTER_BEHAVIORS)
- Dynamic memory context (NikitaMemory)
"""

import asyncio
import logging
import time
from functools import lru_cache
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

from pydantic_ai import Agent, RunContext, UsageLimits

from nikita.agents.text.deps import NikitaDeps
from nikita.agents.text.persona import NIKITA_PERSONA
from nikita.engine.constants import CHAPTER_BEHAVIORS

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from nikita.db.models.user import User
    from nikita.memory.supabase_memory import SupabaseMemory


# Model name constant for configuration and testing
# Updated 2025-12-02: Latest Claude 4.5 for +15-20% capability improvement
MODEL_NAME = "anthropic:claude-sonnet-4-5-20250929"

# LLM timeout in seconds (Spec 036 T1.2)
# Set to 120s to allow for Neo4j cold start (~60s) + LLM processing (~30s) + buffer
LLM_TIMEOUT_SECONDS = 120.0

# Usage limits to prevent runaway token usage (Spec 041 T2.6)
# These limits protect against infinite loops and excessive costs
DEFAULT_USAGE_LIMITS = UsageLimits(
    output_tokens_limit=4000,  # Max output tokens per response (~1000 words)
    request_limit=10,  # Max API round-trips (prevents infinite tool loops)
    tool_calls_limit=20,  # Max tool invocations per run
)

# Graceful fallback message when LLM times out (Spec 036 T1.2)
LLM_TIMEOUT_FALLBACK_MESSAGE = (
    "Sorry, I'm having trouble thinking right now. "
    "Let me get back to you in a moment!"
)


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
        """Add chapter-specific behavior overlay.

        Spec 060 P3: When pipeline prompt (generated_prompt) is available,
        the template already includes chapter behavior (Section 10).
        Skip injection to avoid duplicating ~300 tokens.
        """
        if ctx.deps.generated_prompt:
            return ""
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


async def _try_load_ready_prompt(
    user_id: "UUID",
    session: "AsyncSession | None",
) -> str | None:
    """
    Try to load pre-built prompt from ready_prompts table (Spec 042 T4.1).

    Args:
        user_id: User UUID to load prompt for
        session: Optional database session

    Returns:
        Pre-built prompt text or None if not found/error
    """
    import logging

    from nikita.db.database import get_session_maker

    logger = logging.getLogger(__name__)

    try:
        from nikita.db.repositories.ready_prompt_repository import (
            ReadyPromptRepository,
        )

        # Use provided session or create new one
        if session is not None:
            repo = ReadyPromptRepository(session)
            prompt = await repo.get_current(user_id, "text")
            if prompt:
                logger.info(
                    "loaded_ready_prompt user_id=%s tokens=%d",
                    str(user_id),
                    prompt.token_count,
                    extra={"user_id": str(user_id), "token_count": prompt.token_count},
                )
                return prompt.prompt_text
            return None
        else:
            # Create temporary session for backwards compatibility
            session_maker = get_session_maker()
            async with session_maker() as new_session:
                repo = ReadyPromptRepository(new_session)
                prompt = await repo.get_current(user_id, "text")
                if prompt:
                    logger.info(
                        "loaded_ready_prompt user_id=%s tokens=%d",
                        str(user_id),
                        prompt.token_count,
                        extra={
                            "user_id": str(user_id),
                            "token_count": prompt.token_count,
                        },
                    )
                    return prompt.prompt_text
                return None

    except Exception as e:
        logger.warning(
            "ready_prompt_load_failed user_id=%s error=%s",
            str(user_id),
            str(e),
            extra={"user_id": str(user_id), "error": str(e)},
        )
        return None


async def build_system_prompt(
    memory: "NikitaMemory | None",
    user: "User",
    user_message: str,
    conversation_id: "UUID | None" = None,
    session: "AsyncSession | None" = None,  # Spec 038: Session propagation
) -> str:
    """
    Build the complete system prompt for Nikita.

    Spec 042 T4.1: When unified pipeline is enabled, reads from ready_prompts
    table for pre-built prompts. Falls back to on-the-fly generation if
    no prompt exists.

    Legacy path uses MetaPromptService for intelligent prompt generation.
    Falls back to legacy static templates if meta-prompt fails.

    Spec 038: When session is provided, uses it directly to avoid FK
    constraint violations. When None, creates a new session for
    backwards compatibility.

    Args:
        memory: NikitaMemory instance for context retrieval
        user: User model with current chapter
        user_message: The user's message (for memory search)
        conversation_id: Optional conversation UUID for logging
        session: Optional database session for session propagation

    Returns:
        Complete system prompt string (~4000 tokens)
    """
    import logging

    from nikita.config.settings import get_settings
    from nikita.db.database import get_session_maker

    logger = logging.getLogger(__name__)
    settings = get_settings()

    # Spec 042 T4.1: Check unified pipeline flag
    if settings.is_unified_pipeline_enabled_for_user(user.id):
        # Try to load pre-built prompt from ready_prompts
        prompt = await _try_load_ready_prompt(user.id, session)
        if prompt:
            return prompt
        # Fallback: generate on-the-fly, log warning
        logger.warning(
            "no_ready_prompt user_id=%s falling_back_to_basic_prompt",
            str(user.id),
            extra={"user_id": str(user.id)},
        )

    # Fallback to basic static prompt (legacy path deprecated)
    logger.warning(
        "unified_pipeline_disabled falling_back_to_basic_prompt",
        extra={"user_id": str(user.id)},
    )
    return await _build_system_prompt_legacy(memory, user, user_message)


async def _build_system_prompt_legacy(
    memory: "SupabaseMemory | None",
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

    Spec 030: Implements message_history injection for conversation continuity.
    Critical: message_history is None for new sessions to trigger @agent.instructions.
    For subsequent messages, history is loaded to provide conversation context.

    Args:
        deps: NikitaDeps containing memory, user, settings, and conversation_messages
        user_message: The user's message to respond to

    Returns:
        Nikita's response string
    """
    from nikita.agents.text.history import load_message_history

    logger.info(
        f"[LLM-DEBUG] generate_response called: user_id={deps.user.id}, "
        f"message_len={len(user_message)}, conversation_id={deps.conversation_id}"
    )

    # Spec 030: Load message history for conversation continuity
    # Critical: Returns None for new sessions (empty conversation_messages)
    # This ensures @agent.instructions decorators are called for fresh prompts
    message_history = None
    try:
        if deps.conversation_messages:
            # Mid-conversation: load history for continuity
            message_history = await load_message_history(
                conversation_messages=deps.conversation_messages,
                conversation_id=deps.conversation_id,
                limit=80,  # Max 80 turns
                token_budget=3000,  # 1.5-3K tokens for history tier
            )
            if message_history:
                logger.info(
                    f"[HISTORY-DEBUG] Loaded {len(message_history)} messages for continuity"
                )
            else:
                logger.debug(
                    "[HISTORY-DEBUG] No valid history loaded, using fresh prompt"
                )
        else:
            # New session: let @agent.instructions generate fresh prompt
            logger.debug(
                "[HISTORY-DEBUG] New session (no conversation_messages), "
                "using fresh prompt generation"
            )
    except Exception as e:
        # Graceful degradation: continue without history
        logger.warning(
            f"[HISTORY-DEBUG] Failed to load message history: {e}. "
            "Continuing without history."
        )
        message_history = None

    # Spec 012: Generate personalized prompt via MetaPromptService
    # CRITICAL: Generate fresh prompt when:
    # 1. message_history is None (new session), OR
    # 2. message_history contains only user messages (no Nikita responses yet)
    # This handles the case where user's first message is saved before agent runs
    needs_fresh_prompt = message_history is None
    if message_history is not None:
        # Spec 038 T1.2: Use isinstance() for type-safe message detection
        # Previously used fragile string check: "Response" in msg.__class__.__name__
        from pydantic_ai.messages import ModelResponse as _ModelResponse

        # Check if history has any assistant/Nikita responses
        has_assistant_response = any(
            hasattr(msg, "parts") and any(
                hasattr(part, "content") and not hasattr(part, "tool_name")
                for part in getattr(msg, "parts", [])
            )
            for msg in message_history
            if isinstance(msg, _ModelResponse)
        )
        if not has_assistant_response:
            logger.info(
                "[PROMPT-DEBUG] History has no Nikita responses, treating as new session"
            )
            needs_fresh_prompt = True

    if needs_fresh_prompt:
        try:
            start_time = time.time()
            # Spec 038: Pass session for session propagation
            generated = await build_system_prompt(
                deps.memory, deps.user, user_message, deps.conversation_id, deps.session
            )
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
    else:
        # Message history includes system prompt, skip regeneration
        logger.debug(
            "[PROMPT-DEBUG] Using existing system prompt from message_history"
        )
        deps.generated_prompt = None  # Explicitly None - prompt is in history

    # Run the agent - instructions are built dynamically via @agent.instructions
    # The add_personalized_context() decorator injects deps.generated_prompt
    # Spec 030: message_history enables conversation continuity
    # Spec 036 T1.2: Wrap in timeout to handle Neo4j cold start + LLM delays
    logger.info(
        f"[LLM-DEBUG] Calling nikita_agent.run() with model={MODEL_NAME}, "
        f"message_history={'present' if message_history else 'None'}, "
        f"timeout={LLM_TIMEOUT_SECONDS}s"
    )

    try:
        result = await asyncio.wait_for(
            nikita_agent.run(
                user_message,
                deps=deps,
                message_history=message_history,  # Spec 030: Conversation continuity
                usage_limits=DEFAULT_USAGE_LIMITS,  # Spec 041 T2.6: Token/request limits
            ),
            timeout=LLM_TIMEOUT_SECONDS,
        )
        logger.info(
            f"[LLM-DEBUG] LLM response received: {len(result.output)} chars"
        )
        return result.output

    except asyncio.TimeoutError:
        # Spec 036 T1.2: Graceful timeout handling
        logger.error(
            f"[LLM-TIMEOUT] LLM call timed out after {LLM_TIMEOUT_SECONDS}s "
            f"for user {deps.user.id}, conversation {deps.conversation_id}",
            extra={
                "user_id": str(deps.user.id),
                "conversation_id": str(deps.conversation_id),
                "timeout_seconds": LLM_TIMEOUT_SECONDS,
            },
        )
        return LLM_TIMEOUT_FALLBACK_MESSAGE
