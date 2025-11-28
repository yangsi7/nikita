"""Agent tools for Nikita text agent.

This module defines tools that the Nikita agent can use during conversations
to interact with the memory system and other services.
"""

from typing import TYPE_CHECKING, Any

from pydantic_ai import RunContext

from nikita.agents.text.deps import NikitaDeps

if TYPE_CHECKING:
    pass


def format_memory_results(results: list[dict[str, Any]]) -> str:
    """
    Format memory search results into a readable string.

    Args:
        results: List of memory results from search_memory

    Returns:
        Formatted string suitable for the agent to use
    """
    if not results:
        return "No relevant memories found."

    # Map graph types to human-readable labels
    graph_labels = {
        "nikita": "My life",
        "user": "About them",
        "relationship": "Our history",
    }

    formatted_parts = []
    for memory in results:
        # Format date if available
        created_at = memory.get("created_at")
        if created_at:
            date_str = created_at.strftime("%Y-%m-%d")
        else:
            date_str = "Unknown date"

        # Get human-readable graph label
        graph_type = memory.get("graph_type", "unknown")
        label = graph_labels.get(graph_type, graph_type)

        # Format the memory entry
        fact = memory.get("fact", "")
        formatted_parts.append(f"[{date_str}] ({label}) {fact}")

    return "\n".join(formatted_parts)


async def recall_memory(ctx: RunContext[NikitaDeps], query: str) -> str:
    """
    Search memory for relevant information about a topic.

    This tool allows Nikita to actively search her memory during
    a conversation when she needs to recall specific information
    about the user, their history together, or her own life.

    Args:
        ctx: Pydantic AI run context with NikitaDeps
        query: Search query to find relevant memories

    Returns:
        Formatted string of relevant memory results
    """
    # Search memory with limit of 5 results
    results = await ctx.deps.memory.search_memory(query, limit=5)

    # Format and return results
    return format_memory_results(results)


async def note_user_fact(ctx: RunContext[NikitaDeps], fact: str, confidence: float) -> str:
    """
    Record a fact about the user to memory.

    This tool allows Nikita to proactively note something she learned
    about the user during a conversation. Facts are stored in the
    user knowledge graph for future reference.

    Args:
        ctx: Pydantic AI run context with NikitaDeps
        fact: The fact statement about the user (e.g., "User works at Tesla")
        confidence: Confidence level from 0-1 (0.8+ for explicit, 0.5-0.8 for implicit)

    Returns:
        Confirmation string indicating the fact was recorded
    """
    # Store the fact in the user knowledge graph
    await ctx.deps.memory.add_user_fact(fact, confidence)

    # Return confirmation
    return f"Noted: {fact}"


# Note: The @agent.tool decorator is applied when registering tools
# with the agent, not at function definition time. This allows for
# better testability and flexibility.
#
# Registration happens in agent.py:
#
# @nikita_agent.tool(retries=2)
# async def recall_memory(...):
#     return await _recall_memory(ctx, query)
#
# For now, this module exports the raw functions which can be
# tested independently and then registered with the agent.
