"""Graph Updater for Post-Processing Pipeline (Spec 021, T021).

Wraps existing Graphiti integration to update knowledge graphs
after conversation ends.

AC-T021.1: GraphUpdater class wraps existing Graphiti integration
AC-T021.2: Updates user_graph, relationship_graph after conversation
AC-T021.3: Extracts facts from conversation
AC-T021.4: Unit tests for updater
"""

import logging
from collections.abc import Callable
from uuid import UUID

from nikita.memory.graphiti_client import NikitaMemory, get_memory_client

logger = logging.getLogger(__name__)


class GraphUpdater:
    """Updates knowledge graphs after conversation ends.

    Wraps the NikitaMemory Graphiti client to:
    - Extract user facts from conversation transcript
    - Extract relationship events (shared moments, jokes, milestones)
    - Update the appropriate knowledge graphs

    Attributes:
        memory_client_factory: Factory function to get memory client.
    """

    def __init__(
        self,
        memory_client_factory: Callable | None = None,
    ) -> None:
        """Initialize GraphUpdater.

        Args:
            memory_client_factory: Optional factory to create memory clients.
                                   Defaults to get_memory_client.
        """
        self._memory_client_factory = memory_client_factory or get_memory_client

    async def update(
        self,
        user_id: UUID,
        conversation_id: UUID,
        transcript: list[dict[str, str]] | None = None,
    ) -> tuple[int, int]:
        """Update knowledge graphs from conversation.

        Args:
            user_id: User ID to update graphs for.
            conversation_id: Conversation ID for reference.
            transcript: Optional list of message dicts with 'role' and 'content'.

        Returns:
            Tuple of (facts_extracted, events_extracted).
        """
        if not transcript:
            logger.info(f"No transcript provided for user {user_id}, skipping graph update")
            return 0, 0

        memory = await self._memory_client_factory(str(user_id))

        facts_count = 0
        events_count = 0

        # Process each message in transcript
        for message in transcript:
            role = message.get("role", "")
            content = message.get("content", "")

            if not content:
                continue

            if role == "user":
                # User messages go to user graph and relationship graph
                await self._process_user_message(memory, content, conversation_id)
                facts_count += 1

            elif role == "assistant":
                # Nikita responses go to relationship graph
                await self._process_assistant_message(memory, content, conversation_id)
                events_count += 1

        logger.info(
            f"Graph update complete for user {user_id}: "
            f"{facts_count} facts, {events_count} events"
        )

        return facts_count, events_count

    async def _process_user_message(
        self,
        memory: NikitaMemory,
        content: str,
        conversation_id: UUID,
    ) -> None:
        """Process a user message and update graphs.

        Args:
            memory: NikitaMemory instance.
            content: User message content.
            conversation_id: Conversation ID for reference.
        """
        try:
            # Add to user graph (what Nikita knows about user)
            await memory.add_episode(
                content=content,
                source="user_message",
                graph_type="user",
                metadata={"conversation_id": str(conversation_id)},
            )

            # Add to relationship graph (shared history)
            await memory.add_episode(
                content=f"User said: {content}",
                source="user_message",
                graph_type="relationship",
                metadata={"conversation_id": str(conversation_id)},
            )
        except Exception as e:
            logger.exception(f"Failed to process user message: {e}")

    async def _process_assistant_message(
        self,
        memory: NikitaMemory,
        content: str,
        conversation_id: UUID,
    ) -> None:
        """Process an assistant message and update graphs.

        Args:
            memory: NikitaMemory instance.
            content: Assistant message content.
            conversation_id: Conversation ID for reference.
        """
        try:
            # Add to relationship graph (shared history)
            await memory.add_episode(
                content=f"Nikita said: {content}",
                source="nikita_response",
                graph_type="relationship",
                metadata={"conversation_id": str(conversation_id)},
            )
        except Exception as e:
            logger.exception(f"Failed to process assistant message: {e}")

    async def add_user_fact(
        self,
        user_id: UUID,
        fact: str,
        confidence: float = 0.8,
    ) -> None:
        """Add a specific user fact to the graph.

        Args:
            user_id: User ID.
            fact: Fact to add.
            confidence: Confidence level (0-1).
        """
        memory = await self._memory_client_factory(str(user_id))
        await memory.add_user_fact(fact, confidence=confidence)

    async def add_relationship_event(
        self,
        user_id: UUID,
        description: str,
        event_type: str = "general",
    ) -> None:
        """Add a relationship event to the graph.

        Args:
            user_id: User ID.
            description: Event description.
            event_type: Type of event (e.g., "inside_joke", "milestone").
        """
        memory = await self._memory_client_factory(str(user_id))
        await memory.add_relationship_episode(description, episode_type=event_type)


# Module-level singleton
_default_updater: GraphUpdater | None = None


def get_graph_updater() -> GraphUpdater:
    """Get the singleton GraphUpdater instance.

    Returns:
        Cached GraphUpdater instance.
    """
    global _default_updater
    if _default_updater is None:
        _default_updater = GraphUpdater()
    return _default_updater
