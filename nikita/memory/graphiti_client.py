"""Graphiti client for temporal knowledge graphs using Neo4j Aura.

Spec 036 T2.2: Connection pooling via singleton Graphiti instance.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from graphiti_core import Graphiti
from graphiti_core.llm_client.anthropic_client import AnthropicClient
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.embedder import OpenAIEmbedder
from graphiti_core.embedder.openai import OpenAIEmbedderConfig
from graphiti_core.nodes import EpisodeType

from nikita.config.settings import get_settings

logger = logging.getLogger(__name__)

# Spec 036 T2.2: Singleton Graphiti instance for connection pooling
_graphiti_singleton: Graphiti | None = None
_graphiti_lock = asyncio.Lock()


# Map our source strings to Graphiti's EpisodeType enum
SOURCE_TYPE_MAP: dict[str, EpisodeType] = {
    "user_message": EpisodeType.message,
    "nikita_response": EpisodeType.message,
    "system_event": EpisodeType.text,
    "test_message": EpisodeType.message,
}


async def _get_graphiti_singleton() -> Graphiti:
    """
    Get or create the singleton Graphiti instance.

    Spec 036 T2.2: Connection pooling via singleton pattern.
    This ensures warm connections are reused, avoiding Neo4j cold start
    on every query (~61s → <5s for subsequent queries).

    Returns:
        Shared Graphiti instance configured with Neo4j Aura.
    """
    global _graphiti_singleton

    async with _graphiti_lock:
        if _graphiti_singleton is None:
            logger.info("[NEO4J] Creating singleton Graphiti connection pool...")
            settings = get_settings()

            llm_config = LLMConfig(
                api_key=settings.anthropic_api_key,
                model=settings.anthropic_model,
            )
            embedder_config = OpenAIEmbedderConfig(
                api_key=settings.openai_api_key,
                embedding_model=settings.embedding_model,
            )

            _graphiti_singleton = Graphiti(
                uri=settings.neo4j_uri,
                user=settings.neo4j_username,
                password=settings.neo4j_password,
                llm_client=AnthropicClient(config=llm_config),
                embedder=OpenAIEmbedder(config=embedder_config),
            )
            logger.info("[NEO4J] Singleton Graphiti connection pool created")

        return _graphiti_singleton


class NikitaMemory:
    """
    Memory system using Graphiti temporal knowledge graphs.

    Manages three separate knowledge graphs:
    - Nikita Graph: Her simulated life, work, opinions
    - User Graph: What Nikita knows about the player
    - Relationship Graph: Shared history, episodes, inside jokes

    Spec 036 T2.2: Uses singleton Graphiti for connection pooling.
    Spec 037 T1.1: Supports async context manager for resource safety.

    Usage:
        async with await get_memory_client(user_id) as memory:
            await memory.add_user_fact("User likes coffee")
    """

    def __init__(self, user_id: str, graphiti: Graphiti | None = None):
        """
        Initialize memory system for a specific user.

        Args:
            user_id: Unique identifier for the user
            graphiti: Optional pre-configured Graphiti instance (for testing or pooling)
        """
        self.user_id = user_id
        self._graphiti = graphiti  # Will be set in initialize() if None
        self._closed = False

    async def __aenter__(self) -> "NikitaMemory":
        """Enter async context manager.

        Spec 037 T1.1 AC-T1.1.1: Returns self for use in async with statement.

        Returns:
            Self for method chaining
        """
        if not self._graphiti:
            await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Exit async context manager.

        Spec 037 T1.1 AC-T1.1.2: Marks the client as closed.
        Note: Actual Neo4j connections are managed by the singleton Graphiti
        instance for connection pooling, so we don't close them here.

        Spec 037 T1.1 AC-T1.1.3: Exceptions are logged but not raised.

        Returns:
            False to not suppress exceptions
        """
        self._closed = True
        if exc_type is not None:
            logger.warning(
                "[MEMORY] Context manager exiting with exception: %s: %s",
                exc_type.__name__,
                exc_val,
            )
        return False  # Don't suppress exceptions

    async def close(self) -> None:
        """Close the memory client (for non-context-manager usage).

        Note: The underlying Neo4j connections are pooled via singleton,
        so this just marks this instance as closed.
        """
        self._closed = True

    @property
    def graphiti(self) -> Graphiti:
        """Get the Graphiti instance (lazy access for backward compatibility)."""
        if self._graphiti is None:
            raise RuntimeError(
                "NikitaMemory must be initialized with initialize() or via get_memory_client()"
            )
        return self._graphiti

    async def initialize(self) -> None:
        """Initialize the knowledge graph indices and constraints.

        Spec 036 T2.2: Uses singleton Graphiti for connection pooling.
        Note: Silently ignores "index already exists" errors since they
        indicate the database is already properly configured.
        """
        # Get singleton if not provided
        if self._graphiti is None:
            self._graphiti = await _get_graphiti_singleton()

        try:
            await self.graphiti.build_indices_and_constraints()
        except Exception as e:
            # Neo4j raises error if indices already exist, which is fine
            error_str = str(e).lower()
            if "equivalent" in error_str and "already exists" in error_str:
                # Indices already exist - database is configured
                pass
            else:
                raise

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
        # Map source string to EpisodeType enum (default to message)
        episode_type = SOURCE_TYPE_MAP.get(source, EpisodeType.message)

        await self.graphiti.add_episode(
            name=group_id,
            episode_body=content,
            source=episode_type,
            reference_time=datetime.now(timezone.utc),
            group_id=group_id,
            source_description=f"Nikita game - {graph_type} graph - {source}",
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
                    "source_node_uuid": str(edge.source_node_uuid),
                    "target_node_uuid": str(edge.target_node_uuid),
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

    async def get_relationship_episodes(self, limit: int = 50) -> list[str]:
        """
        Get relationship episodes from the shared history graph.

        Returns a list of episode descriptions from the relationship
        graph, including shared moments, inside jokes, and milestones.

        Args:
            limit: Maximum number of episodes to retrieve

        Returns:
            List of episode descriptions from the relationship graph
        """
        group_id = self._get_group_id("relationship")

        try:
            edges = await self.graphiti.search(
                query="relationship episodes history shared moments",
                group_ids=[group_id],
                num_results=limit,
            )
            return [edge.fact for edge in edges if hasattr(edge, "fact")]
        except Exception:
            # Return empty list if search fails (e.g., no episodes yet)
            return []

    async def get_nikita_events(self, limit: int = 50) -> list[str]:
        """
        Get Nikita's life events from her personal graph.

        Returns a list of event descriptions from Nikita's graph,
        including work projects, life events, and opinions.

        Args:
            limit: Maximum number of events to retrieve

        Returns:
            List of event descriptions from Nikita's personal graph
        """
        group_id = self._get_group_id("nikita")

        try:
            edges = await self.graphiti.search(
                query="nikita life events work opinions",
                group_ids=[group_id],
                num_results=limit,
            )
            return [edge.fact for edge in edges if hasattr(edge, "fact")]
        except Exception:
            # Return empty list if search fails (e.g., no events yet)
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
