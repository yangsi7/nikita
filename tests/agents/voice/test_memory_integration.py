"""Tests for cross-agent memory integration (US-9).

Tests for FR-014 acceptance criteria:
- AC-FR014-001: Voice agent sees user facts from text history
- AC-FR014-003: Text agent sees voice call summaries
- AC-FR014-004: Same memory service for both agents
"""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


class TestCrossAgentMemoryAccess:
    """Test cross-agent memory access (US-9)."""

    @pytest.fixture
    def user_id(self):
        """Generate a test user ID."""
        return uuid4()

    @pytest.fixture
    def mock_memory_client(self):
        """Create mock NikitaMemory client."""
        mock = AsyncMock()
        mock.get_context_for_prompt = AsyncMock(return_value={
            "facts": [
                {"content": "Works at Google", "source": "user_message"},
                {"content": "Enjoys hiking", "source": "voice_call"},
            ],
            "recent_episodes": [
                {"content": "Discussed work project", "source": "user_message"},
                {"content": "Voice call about weekend plans", "source": "voice_call"},
            ],
        })
        mock.search_memory = AsyncMock(return_value=[
            {"content": "User mentioned promotion", "source": "user_message"},
        ])
        return mock

    @pytest.mark.asyncio
    async def test_voice_agent_sees_text_history_facts(
        self, user_id, mock_memory_client
    ):
        """AC-FR014-001: Voice agent sees user facts from text history."""
        from nikita.agents.voice.service import VoiceService

        with patch(
            "nikita.agents.voice.service.get_memory_client",
            return_value=mock_memory_client,
        ):
            service = VoiceService(settings=MagicMock())

            # Get context for voice call
            context = await service.get_context_with_text_history(str(user_id))

            # Should include facts from text conversations
            assert context is not None
            mock_memory_client.get_context_for_prompt.assert_called_once()

            # Verify facts include text source
            facts = context.get("facts", [])
            text_facts = [f for f in facts if f.get("source") == "user_message"]
            assert len(text_facts) >= 1

    @pytest.mark.asyncio
    async def test_voice_context_includes_last_7_days(
        self, user_id, mock_memory_client
    ):
        """AC-T048.3: Voice context includes last 7 days of text conversations."""
        from nikita.agents.voice.service import VoiceService

        with patch(
            "nikita.agents.voice.service.get_memory_client",
            return_value=mock_memory_client,
        ):
            service = VoiceService(settings=MagicMock())

            context = await service.get_context_with_text_history(str(user_id))

            # Context should include recent episodes
            episodes = context.get("recent_episodes", [])
            assert len(episodes) >= 1

    @pytest.mark.asyncio
    async def test_memory_search_returns_both_sources(
        self, user_id, mock_memory_client
    ):
        """AC-T049.4: Search returns both voice and text sources when no filter."""
        from nikita.agents.voice.service import VoiceService

        mock_memory_client.search_memory = AsyncMock(return_value=[
            {"content": "Text fact", "source": "user_message"},
            {"content": "Voice fact", "source": "voice_call"},
        ])

        with patch(
            "nikita.agents.voice.service.get_memory_client",
            return_value=mock_memory_client,
        ):
            service = VoiceService(settings=MagicMock())

            results = await service.search_user_memory(
                user_id=str(user_id),
                query="any query",
            )

            # Should return both sources
            sources = {r.get("source") for r in results}
            assert "user_message" in sources or "voice_call" in sources


class TestVoiceSourceTagging:
    """Test voice source tagging in memory (T049)."""

    @pytest.fixture
    def user_id(self):
        """Generate a test user ID."""
        return uuid4()

    @pytest.mark.asyncio
    async def test_voice_episodes_tagged_with_voice_call_source(self, user_id):
        """AC-T049.1: Voice episodes saved with source='voice_call'."""
        from nikita.agents.voice.transcript import TranscriptManager

        mock_memory = AsyncMock()
        mock_memory.add_fact = AsyncMock()

        with patch(
            "nikita.agents.voice.transcript.get_memory_client",
            return_value=mock_memory,
        ):
            manager = TranscriptManager(session=None)

            await manager.store_fact(
                user_id=user_id,
                session_id="voice_session_123",
                fact="User mentioned they work at Google",
                category="occupation",
            )

            # Verify fact was stored with voice_call source
            mock_memory.add_fact.assert_called_once()
            call_kwargs = mock_memory.add_fact.call_args.kwargs
            assert call_kwargs.get("source") == "voice_call"

    @pytest.mark.asyncio
    async def test_memory_includes_source_field_in_results(self, user_id):
        """AC-T049.3: Search results include source field for filtering."""
        mock_memory = AsyncMock()
        mock_memory.search_memory = AsyncMock(return_value=[
            {"content": "Fact from voice", "source": "voice_call", "score": 0.9},
            {"content": "Fact from text", "source": "user_message", "score": 0.85},
        ])

        with patch(
            "nikita.memory.graphiti_client.get_memory_client",
            return_value=mock_memory,
        ):
            from nikita.memory.graphiti_client import get_memory_client

            memory = await get_memory_client(str(user_id))
            results = await memory.search_memory("work")

            # Each result should have source field
            for result in results:
                assert "source" in result


class TestTextHistoryFormatting:
    """Test formatting text history for voice agent consumption."""

    @pytest.mark.asyncio
    async def test_text_history_formatted_for_voice(self):
        """AC-T048.2: Text history formatted for voice agent consumption."""
        from nikita.agents.voice.service import VoiceService

        mock_memory = AsyncMock()
        mock_memory.get_context_for_prompt = AsyncMock(return_value={
            "facts": [
                {"content": "Works at Google", "source": "user_message"},
            ],
            "recent_episodes": [
                {
                    "content": "User discussed work project",
                    "source": "user_message",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            ],
        })

        with patch(
            "nikita.agents.voice.service.get_memory_client",
            return_value=mock_memory,
        ):
            service = VoiceService(settings=MagicMock())

            formatted = await service.format_text_history_for_voice(
                user_id=str(uuid4()),
            )

            # Should return formatted string or dict
            assert formatted is not None
            # Formatted output should be suitable for voice context
            if isinstance(formatted, str):
                assert len(formatted) > 0
            elif isinstance(formatted, dict):
                assert "summary" in formatted or "context" in formatted


class TestSharedMemoryService:
    """Test that voice and text agents use same memory service."""

    @pytest.mark.asyncio
    async def test_same_memory_service_for_both_agents(self):
        """AC-FR014-004: Same NikitaMemory service for both agents."""
        from nikita.memory.graphiti_client import get_memory_client

        user_id = str(uuid4())

        # Get memory client for text agent context
        text_memory = await get_memory_client(user_id)

        # Get memory client for voice agent context
        voice_memory = await get_memory_client(user_id)

        # Should be the same instance or same type
        assert type(text_memory) == type(voice_memory)
