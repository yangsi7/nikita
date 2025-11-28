"""Nikita Text Agent - Pydantic AI powered conversational agent.

This module implements the core Nikita text agent using Pydantic AI
with Claude Sonnet. The agent combines:
- Base persona (NIKITA_PERSONA)
- Chapter-specific behavior (CHAPTER_BEHAVIORS)
- Dynamic memory context (NikitaMemory)
"""

from functools import lru_cache
from typing import TYPE_CHECKING

from pydantic_ai import Agent, RunContext

from nikita.agents.text.deps import NikitaDeps
from nikita.engine.constants import CHAPTER_BEHAVIORS
from nikita.prompts.nikita_persona import NIKITA_PERSONA

if TYPE_CHECKING:
    from nikita.db.models.user import User
    from nikita.memory.graphiti_client import NikitaMemory


# Model name constant for configuration and testing
MODEL_NAME = "anthropic:claude-sonnet-4-20250514"


def _create_nikita_agent() -> Agent[NikitaDeps, str]:
    """
    Create and configure the Nikita text agent.

    Creates the agent with all registered tools.

    Returns:
        Configured Pydantic AI Agent with NikitaDeps and tools
    """
    from nikita.agents.text.tools import format_memory_results

    agent = Agent(
        MODEL_NAME,
        deps_type=NikitaDeps,
        result_type=str,
    )

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
        results = await ctx.deps.memory.search_memory(query, limit=5)
        return format_memory_results(results)

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
        await ctx.deps.memory.add_user_fact(fact, confidence)
        return f"Noted: {fact}"

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
    memory: "NikitaMemory",
    user: "User",
    user_message: str,
) -> str:
    """
    Build the complete system prompt for Nikita.

    Combines:
    1. Base persona (NIKITA_PERSONA)
    2. Chapter-specific behavior (CHAPTER_BEHAVIORS)
    3. Relevant memory context

    Args:
        memory: NikitaMemory instance for context retrieval
        user: User model with current chapter
        user_message: The user's message (for memory search)

    Returns:
        Complete system prompt string
    """
    # Get chapter-specific behavior overlay
    chapter_behavior = CHAPTER_BEHAVIORS.get(user.chapter, CHAPTER_BEHAVIORS[1])

    # Get relevant memory context
    memory_context = await memory.get_context_for_prompt(user_message)

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
    It builds the system prompt dynamically and invokes the agent.

    Args:
        deps: NikitaDeps containing memory, user, and settings
        user_message: The user's message to respond to

    Returns:
        Nikita's response string
    """
    # Build dynamic system prompt
    system_prompt = await build_system_prompt(
        deps.memory,
        deps.user,
        user_message,
    )

    # Run the agent with dynamic system prompt
    result = await nikita_agent.run(
        user_message,
        deps=deps,
        system_prompt=system_prompt,
    )

    return result.data
