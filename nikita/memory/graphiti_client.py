"""Graphiti client for temporal knowledge graphs using FalkorDB."""

from datetime import datetime, timezone
from typing import Any

from graphiti_core import Graphiti
from graphiti_core.llm_client import AnthropicClient
from graphiti_core.embedder import OpenAIEmbedder

from nikita.config.settings import get_settings


class NikitaMemory:
    """
    Memory system using Graphiti temporal knowledge graphs.

    Manages three separate knowledge graphs:
    - Nikita Graph: Her simulated life, work, opinions
    - User Graph: What Nikita knows about the player
    - Relationship Graph: Shared history, episodes, inside jokes
    """

    def __init__(self, user_id: str):
        """
        Initialize memory system for a specific user.

        Args:
            user_id: Unique identifier for the user
        """
        self.user_id = user_id
        settings = get_settings()

        # Initialize Graphiti with FalkorDB
        self.graphiti = Graphiti(
            uri=settings.falkordb_url,
            llm_client=AnthropicClient(
                api_key=settings.anthropic_api_key,
                model=settings.anthropic_model,
            ),
            embedder=OpenAIEmbedder(
                api_key=settings.openai_api_key,
                model=settings.embedding_model,
            ),
        )

    async def initialize(self) -> None:
        """Initialize the knowledge graph indices and constraints."""
        await self.graphiti.build_indices_and_constraints()

    def _get_group_id(self, graph_type: str) -> str:
        """Get the group ID for a specific graph type."""
        return f"{graph_type}_{self.user_id}"

    async def add_episode(
        self,
        content: str,
        source: str,
        graph_type: str = "relationship",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Add a new episode to the appropriate knowledge graph.

        Args:
            content: The episode content to add
            source: Source of the episode (user_message, nikita_response, system_event)
            graph_type: Which graph to add to (nikita, user, relationship)
            metadata: Optional additional metadata
        """
        group_id = self._get_group_id(graph_type)

        await self.graphiti.add_episode(
            name=group_id,
            episode_body=content,
            source=source,
            reference_time=datetime.now(timezone.utc),
            group_id=group_id,
            source_description=f"Nikita game - {graph_type} graph",
        )

    async def search_memory(
        self,
        query: str,
        graph_types: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Search across knowledge graphs using hybrid search.

        Args:
            query: Search query
            graph_types: List of graph types to search (nikita, user, relationship)
            limit: Maximum results per graph

        Returns:
            List of search results with facts and metadata
        """
        if graph_types is None:
            graph_types = ["nikita", "user", "relationship"]

        results = []
        for graph_type in graph_types:
            group_id = self._get_group_id(graph_type)
            edges = await self.graphiti.search(
                query=query,
                group_ids=[group_id],
                num_results=limit,
            )
            for edge in edges:
                results.append({
                    "graph_type": graph_type,
                    "fact": edge.fact,
                    "created_at": edge.created_at,
                    "source": edge.source,
                    "relevance_score": getattr(edge, "score", None),
                })

        return results

    async def get_context_for_prompt(
        self,
        user_message: str,
        max_memories: int = 5,
    ) -> str:
        """
        Build context string for LLM prompt injection.

        Searches all graphs and formats relevant memories
        for inclusion in the system prompt.

        Args:
            user_message: The user's message to find relevant context for
            max_memories: Maximum number of memories to include

        Returns:
            Formatted context string for prompt injection
        """
        memories = await self.search_memory(user_message, limit=max_memories)

        if not memories:
            return "No relevant memories found."

        # Sort by relevance if scores available
        memories_with_scores = [m for m in memories if m.get("relevance_score")]
        memories_without_scores = [m for m in memories if not m.get("relevance_score")]
        sorted_memories = sorted(
            memories_with_scores,
            key=lambda x: x.get("relevance_score", 0),
            reverse=True,
        ) + memories_without_scores

        # Format for prompt
        context_parts = []
        for memory in sorted_memories[:max_memories]:
            date_str = memory["created_at"].strftime("%Y-%m-%d") if memory.get("created_at") else "Unknown"
            graph_label = {
                "nikita": "My life",
                "user": "About them",
                "relationship": "Our history",
            }.get(memory["graph_type"], memory["graph_type"])

            context_parts.append(f"[{date_str}] ({graph_label}) {memory['fact']}")

        return "\n".join(context_parts)

    async def add_user_fact(
        self,
        fact: str,
        confidence: float = 0.8,
        source_message: str | None = None,
    ) -> None:
        """
        Add a fact learned about the user.

        Args:
            fact: The fact to store
            confidence: Confidence level (0-1)
            source_message: The message that revealed this fact
        """
        content = f"Learned about user: {fact}"
        if source_message:
            content += f" (from: '{source_message[:100]}...')"

        await self.add_episode(
            content=content,
            source="user_message",
            graph_type="user",
            metadata={"confidence": confidence},
        )

    async def get_user_facts(self, limit: int = 50) -> list[str]:
        """
        Get existing user facts for deduplication during fact extraction.

        Returns a list of fact strings already known about the user,
        which is used to avoid extracting duplicate facts.

        Args:
            limit: Maximum number of facts to retrieve

        Returns:
            List of fact strings about the user
        """
        # Search user graph with broad query to get existing facts
        group_id = self._get_group_id("user")

        try:
            edges = await self.graphiti.search(
                query="user facts information",
                group_ids=[group_id],
                num_results=limit,
            )
            # Extract the fact strings
            return [edge.fact for edge in edges if hasattr(edge, "fact")]
        except Exception:
            # Return empty list if search fails (e.g., no facts yet)
            return []

    async def add_relationship_episode(
        self,
        description: str,
        episode_type: str = "general",
    ) -> None:
        """
        Add a shared episode to the relationship graph.

        Args:
            description: Description of the episode
            episode_type: Type of episode (general, milestone, conflict, inside_joke)
        """
        await self.add_episode(
            content=f"[{episode_type}] {description}",
            source="system_event",
            graph_type="relationship",
            metadata={"episode_type": episode_type},
        )

    async def add_nikita_event(
        self,
        description: str,
        event_type: str = "life_event",
    ) -> None:
        """
        Add an event to Nikita's personal graph.

        Args:
            description: Description of the event
            event_type: Type of event (work_project, life_event, opinion, memory)
        """
        await self.add_episode(
            content=f"[{event_type}] {description}",
            source="system_event",
            graph_type="nikita",
            metadata={"event_type": event_type},
        )


async def get_memory_client(user_id: str) -> NikitaMemory:
    """
    Factory function to get an initialized memory client.

    Args:
        user_id: User ID for the memory system

    Returns:
        Initialized NikitaMemory instance
    """
    client = NikitaMemory(user_id)
    await client.initialize()
    return client
