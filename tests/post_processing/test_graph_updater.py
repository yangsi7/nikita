"""Tests for GraphUpdater (Spec 021, T021).

AC-T021.1: GraphUpdater class wraps existing Graphiti integration
AC-T021.2: Updates user_graph, relationship_graph after conversation
AC-T021.3: Extracts facts from conversation
AC-T021.4: Unit tests for updater
"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from nikita.post_processing.graph_updater import (
    GraphUpdater,
    get_graph_updater,
)


class TestGraphUpdater:
    """Tests for GraphUpdater class."""

    @pytest.fixture
    def mock_memory(self):
        """Create mock memory client."""
        memory = AsyncMock()
        memory.add_episode = AsyncMock()
        memory.add_user_fact = AsyncMock()
        memory.add_relationship_episode = AsyncMock()
        return memory

    @pytest.fixture
    def mock_memory_factory(self, mock_memory):
        """Create mock memory factory."""
        async def factory(user_id: str):
            return mock_memory
        return factory

    @pytest.mark.asyncio
    async def test_update_with_transcript(self, mock_memory_factory, mock_memory):
        """AC-T021.3: Extracts facts from conversation."""
        updater = GraphUpdater(memory_client_factory=mock_memory_factory)
        user_id = uuid4()
        conversation_id = uuid4()

        transcript = [
            {"role": "user", "content": "I work as a software engineer"},
            {"role": "assistant", "content": "That's cool! What do you work on?"},
            {"role": "user", "content": "I build web apps"},
        ]

        facts, events = await updater.update(
            user_id=user_id,
            conversation_id=conversation_id,
            transcript=transcript,
        )

        # Should have processed user messages as facts
        assert facts == 2  # Two user messages
        assert events == 1  # One assistant message

        # Verify add_episode was called for each message
        # 2 user msgs * 2 calls each (user + relationship graph) = 4
        # 1 assistant msg * 1 call (relationship graph) = 1
        # Total = 5
        assert mock_memory.add_episode.call_count == 5

    @pytest.mark.asyncio
    async def test_update_without_transcript(self, mock_memory_factory, mock_memory):
        """Update with no transcript returns zeros."""
        updater = GraphUpdater(memory_client_factory=mock_memory_factory)
        user_id = uuid4()
        conversation_id = uuid4()

        facts, events = await updater.update(
            user_id=user_id,
            conversation_id=conversation_id,
            transcript=None,
        )

        assert facts == 0
        assert events == 0
        mock_memory.add_episode.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_empty_transcript(self, mock_memory_factory, mock_memory):
        """Update with empty transcript returns zeros."""
        updater = GraphUpdater(memory_client_factory=mock_memory_factory)
        user_id = uuid4()
        conversation_id = uuid4()

        facts, events = await updater.update(
            user_id=user_id,
            conversation_id=conversation_id,
            transcript=[],
        )

        assert facts == 0
        assert events == 0

    @pytest.mark.asyncio
    async def test_process_user_message(self, mock_memory_factory, mock_memory):
        """AC-T021.2: Updates user_graph with user messages."""
        updater = GraphUpdater(memory_client_factory=mock_memory_factory)
        user_id = uuid4()
        conversation_id = uuid4()

        transcript = [
            {"role": "user", "content": "I love hiking"},
        ]

        await updater.update(
            user_id=user_id,
            conversation_id=conversation_id,
            transcript=transcript,
        )

        # Check that add_episode was called with user graph
        calls = mock_memory.add_episode.call_args_list
        user_graph_calls = [
            c for c in calls if c.kwargs.get("graph_type") == "user"
        ]
        assert len(user_graph_calls) >= 1

    @pytest.mark.asyncio
    async def test_process_assistant_message(self, mock_memory_factory, mock_memory):
        """AC-T021.2: Updates relationship_graph with assistant messages."""
        updater = GraphUpdater(memory_client_factory=mock_memory_factory)
        user_id = uuid4()
        conversation_id = uuid4()

        transcript = [
            {"role": "assistant", "content": "I had a great day too!"},
        ]

        await updater.update(
            user_id=user_id,
            conversation_id=conversation_id,
            transcript=transcript,
        )

        # Check that add_episode was called with relationship graph
        calls = mock_memory.add_episode.call_args_list
        relationship_calls = [
            c for c in calls if c.kwargs.get("graph_type") == "relationship"
        ]
        assert len(relationship_calls) >= 1

    @pytest.mark.asyncio
    async def test_add_user_fact(self, mock_memory_factory, mock_memory):
        """add_user_fact method works correctly."""
        updater = GraphUpdater(memory_client_factory=mock_memory_factory)
        user_id = uuid4()

        await updater.add_user_fact(
            user_id=user_id,
            fact="User enjoys cooking",
            confidence=0.9,
        )

        mock_memory.add_user_fact.assert_called_once_with(
            "User enjoys cooking",
            confidence=0.9,
        )

    @pytest.mark.asyncio
    async def test_add_relationship_event(self, mock_memory_factory, mock_memory):
        """add_relationship_event method works correctly."""
        updater = GraphUpdater(memory_client_factory=mock_memory_factory)
        user_id = uuid4()

        await updater.add_relationship_event(
            user_id=user_id,
            description="We shared our first inside joke",
            event_type="inside_joke",
        )

        mock_memory.add_relationship_episode.assert_called_once_with(
            "We shared our first inside joke",
            episode_type="inside_joke",
        )

    @pytest.mark.asyncio
    async def test_error_handling_continues(self, mock_memory_factory, mock_memory):
        """Errors in one message don't stop processing of others."""
        # First call fails, second succeeds
        mock_memory.add_episode.side_effect = [
            Exception("First call failed"),
            None,  # Success
            None,  # Success
            None,  # Success
        ]

        updater = GraphUpdater(memory_client_factory=mock_memory_factory)
        user_id = uuid4()
        conversation_id = uuid4()

        transcript = [
            {"role": "user", "content": "Message 1"},
            {"role": "assistant", "content": "Response 1"},
        ]

        # Should not raise, continues processing
        facts, events = await updater.update(
            user_id=user_id,
            conversation_id=conversation_id,
            transcript=transcript,
        )

        # All messages should still be counted
        assert facts == 1
        assert events == 1


class TestGetGraphUpdater:
    """Tests for get_graph_updater singleton."""

    def test_singleton_pattern(self):
        """get_graph_updater returns same instance."""
        import nikita.post_processing.graph_updater as updater_module
        updater_module._default_updater = None

        updater1 = get_graph_updater()
        updater2 = get_graph_updater()

        assert updater1 is updater2
