"""Tests for TranscriptManager (US-5: Cross-Modality Memory).

Tests for T024-T028 acceptance criteria:
- AC-FR009-001: Voice transcripts persisted to conversations table with platform='voice'
- AC-FR010-001: Facts extracted from voice transcripts stored to Graphiti with source='voice_call'
"""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.agents.voice.models import TranscriptData, TranscriptEntry


class TestTranscriptManager:
    """Test TranscriptManager - T024, T025."""

    @pytest.fixture
    def sample_transcript(self):
        """Create a sample transcript."""
        return TranscriptData(
            session_id="voice_abc123_1735000000",
            entries=[
                TranscriptEntry(
                    speaker="user",
                    text="Hey Nikita, how are you?",
                    timestamp=datetime.now(timezone.utc),
                    duration_ms=2500,
                    confidence=0.95,
                ),
                TranscriptEntry(
                    speaker="nikita",
                    text="Hey you! I've been waiting for your call. What's going on?",
                    timestamp=datetime.now(timezone.utc),
                    duration_ms=3200,
                    confidence=0.98,
                ),
                TranscriptEntry(
                    speaker="user",
                    text="I just got promoted at work today!",
                    timestamp=datetime.now(timezone.utc),
                    duration_ms=2100,
                    confidence=0.97,
                ),
                TranscriptEntry(
                    speaker="nikita",
                    text="Oh my god, that's amazing! I'm so proud of you. Tell me everything!",
                    timestamp=datetime.now(timezone.utc),
                    duration_ms=3500,
                    confidence=0.96,
                ),
            ],
            total_duration_ms=11300,
            user_turns=2,
            nikita_turns=2,
        )

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        session = AsyncMock()
        session.commit = AsyncMock()
        session.add = MagicMock()
        return session

    @pytest.mark.asyncio
    async def test_persist_transcript_creates_conversation(
        self, sample_transcript, mock_session
    ):
        """AC-FR009-001: Transcript persisted with platform='voice'."""
        from nikita.agents.voice.transcript import TranscriptManager

        user_id = uuid4()
        manager = TranscriptManager(session=mock_session)

        # Persist transcript
        result = await manager.persist_transcript(
            user_id=user_id,
            transcript=sample_transcript,
        )

        # Should create conversation record
        assert result is not None
        assert result.get("conversation_id") is not None

    @pytest.mark.asyncio
    async def test_persist_transcript_platform_voice(
        self, sample_transcript, mock_session
    ):
        """Conversation record should have platform='voice'."""
        from nikita.agents.voice.transcript import TranscriptManager

        user_id = uuid4()
        manager = TranscriptManager(session=mock_session)

        result = await manager.persist_transcript(
            user_id=user_id,
            transcript=sample_transcript,
        )

        # Verify platform field
        assert result.get("platform") == "voice"

    @pytest.mark.asyncio
    async def test_persist_transcript_stores_all_entries(
        self, sample_transcript, mock_session
    ):
        """All transcript entries should be stored."""
        from nikita.agents.voice.transcript import TranscriptManager

        user_id = uuid4()
        manager = TranscriptManager(session=mock_session)

        result = await manager.persist_transcript(
            user_id=user_id,
            transcript=sample_transcript,
        )

        # Should store all entries
        assert result.get("entries_stored") == 4
        assert result.get("user_turns") == 2
        assert result.get("nikita_turns") == 2

    def test_convert_to_exchange_pairs(self, sample_transcript):
        """Convert transcript to (user, nikita) exchange pairs."""
        from nikita.agents.voice.transcript import TranscriptManager

        manager = TranscriptManager(session=None)
        pairs = manager.convert_to_exchange_pairs(sample_transcript)

        # Should have 2 pairs
        assert len(pairs) == 2

        # First pair
        user_msg, nikita_msg = pairs[0]
        assert "Hey Nikita" in user_msg
        assert "I've been waiting" in nikita_msg

        # Second pair
        user_msg2, nikita_msg2 = pairs[1]
        assert "promoted" in user_msg2
        assert "proud of you" in nikita_msg2

    def test_handle_incomplete_pairs(self):
        """Handle transcripts that don't end with nikita response."""
        from nikita.agents.voice.transcript import TranscriptManager

        # Transcript ends with user message
        transcript = TranscriptData(
            session_id="test_123",
            entries=[
                TranscriptEntry(
                    speaker="user",
                    text="Hey Nikita",
                    timestamp=datetime.now(timezone.utc),
                ),
                TranscriptEntry(
                    speaker="nikita",
                    text="Hey!",
                    timestamp=datetime.now(timezone.utc),
                ),
                TranscriptEntry(
                    speaker="user",
                    text="Goodbye",
                    timestamp=datetime.now(timezone.utc),
                ),
            ],
        )

        manager = TranscriptManager(session=None)
        pairs = manager.convert_to_exchange_pairs(transcript)

        # Should have 1 complete pair, orphan user message dropped
        assert len(pairs) == 1
        assert "Hey Nikita" in pairs[0][0]


class TestTranscriptMemoryIntegration:
    """Test transcript → memory integration (T026, T027)."""

    @pytest.fixture
    def sample_transcript(self):
        """Create transcript with extractable facts."""
        return TranscriptData(
            session_id="voice_mem_test",
            entries=[
                TranscriptEntry(
                    speaker="user",
                    text="I work at Google as a software engineer.",
                    timestamp=datetime.now(timezone.utc),
                ),
                TranscriptEntry(
                    speaker="nikita",
                    text="That's really cool! What kind of projects do you work on?",
                    timestamp=datetime.now(timezone.utc),
                ),
            ],
        )

    @pytest.mark.asyncio
    async def test_extract_facts_from_transcript(self, sample_transcript):
        """AC-FR010-001: Facts extracted from voice transcript."""
        from nikita.agents.voice.transcript import TranscriptManager

        manager = TranscriptManager(session=None)

        # Mock the fact extraction (would normally use LLM)
        with patch.object(
            manager, "_extract_facts_via_llm"
        ) as mock_extract:
            mock_extract.return_value = [
                {"fact": "Works at Google", "category": "occupation"},
                {"fact": "Software engineer", "category": "occupation"},
            ]

            facts = await manager.extract_facts(sample_transcript)

            assert len(facts) == 2
            assert any("Google" in f["fact"] for f in facts)

    @pytest.mark.asyncio
    async def test_store_facts_with_voice_source(self, sample_transcript):
        """Facts stored to Graphiti with source='voice_call'."""
        from nikita.agents.voice.transcript import TranscriptManager

        user_id = uuid4()
        session_id = "voice_test_123"
        manager = TranscriptManager(session=None)

        # Mock memory client
        mock_memory = AsyncMock()
        mock_memory.add_fact = AsyncMock()

        with patch(
            "nikita.memory.get_memory_client",
            return_value=mock_memory,
        ):
            await manager.store_fact(
                user_id=user_id,
                session_id=session_id,
                fact="Works at Google as a software engineer",
                category="occupation",
            )

            # Verify fact was stored with source
            mock_memory.add_fact.assert_called_once()
            call_kwargs = mock_memory.add_fact.call_args.kwargs
            assert call_kwargs.get("source") == "voice_call"

    @pytest.mark.asyncio
    async def test_batch_store_facts(self, sample_transcript):
        """Store multiple facts in batch."""
        from nikita.agents.voice.transcript import TranscriptManager

        user_id = uuid4()
        session_id = "voice_batch_test"
        manager = TranscriptManager(session=None)

        facts = [
            {"fact": "Works at Google", "category": "occupation"},
            {"fact": "Enjoys hiking", "category": "hobby"},
            {"fact": "Lives in San Francisco", "category": "location"},
        ]

        mock_memory = AsyncMock()
        mock_memory.add_fact = AsyncMock()

        with patch(
            "nikita.memory.get_memory_client",
            return_value=mock_memory,
        ):
            result = await manager.store_facts_batch(
                user_id=user_id,
                session_id=session_id,
                facts=facts,
            )

            assert result["facts_stored"] == 3
            assert mock_memory.add_fact.call_count == 3


class TestTranscriptSummary:
    """Test transcript summarization (for cross-agent context)."""

    @pytest.fixture
    def long_transcript(self):
        """Create a longer transcript for summarization."""
        entries = []
        topics = [
            ("How was your day?", "It was great, I finished a big project."),
            ("Tell me about the project.", "I built a new recommendation system."),
            ("That sounds technical.", "Yeah, it uses machine learning."),
            ("What's your favorite part?", "Seeing users benefit from it."),
        ]

        for user_msg, nikita_msg in topics:
            entries.append(
                TranscriptEntry(
                    speaker="user",
                    text=user_msg,
                    timestamp=datetime.now(timezone.utc),
                )
            )
            entries.append(
                TranscriptEntry(
                    speaker="nikita",
                    text=nikita_msg,
                    timestamp=datetime.now(timezone.utc),
                )
            )

        return TranscriptData(
            session_id="voice_long_test",
            entries=entries,
            total_duration_ms=120000,
            user_turns=4,
            nikita_turns=4,
        )

    @pytest.mark.asyncio
    async def test_generate_summary(self, long_transcript):
        """Generate summary of voice conversation."""
        from nikita.agents.voice.transcript import TranscriptManager

        manager = TranscriptManager(session=None)

        # Mock summarization
        with patch.object(
            manager, "_summarize_via_llm"
        ) as mock_summarize:
            mock_summarize.return_value = (
                "Voice call about user's work project - "
                "a recommendation system using ML."
            )

            summary = await manager.generate_summary(long_transcript)

            assert summary is not None
            assert len(summary) > 20
            assert "project" in summary.lower() or "recommendation" in summary.lower()

    def test_summary_for_text_agent(self, long_transcript):
        """Format summary for text agent context."""
        from nikita.agents.voice.transcript import TranscriptManager

        manager = TranscriptManager(session=None)

        summary = manager.format_for_text_agent(
            transcript_summary="Discussed user's ML project at work.",
            duration_seconds=120,
        )

        # Should include duration context
        assert "voice call" in summary.lower() or "call" in summary.lower()
        assert "2" in summary  # 2 minutes


class TestLLMFactExtraction:
    """Tests for P0-4: LLM-based fact extraction from transcripts."""

    @pytest.mark.asyncio
    async def test_extract_facts_llm_returns_structured_facts(self):
        """P0-4: LLM extraction returns structured facts with categories."""
        from unittest.mock import AsyncMock, MagicMock
        from nikita.agents.voice.transcript import TranscriptManager

        manager = TranscriptManager(session=None)

        # Create a mock result that matches PydanticAI output format
        mock_fact1 = MagicMock()
        mock_fact1.fact = "Works as a software engineer at Google"
        mock_fact1.category = "occupation"

        mock_fact2 = MagicMock()
        mock_fact2.fact = "Enjoys hiking on weekends"
        mock_fact2.category = "hobby"

        mock_result = MagicMock()
        mock_result.data = MagicMock()
        mock_result.data.facts = [mock_fact1, mock_fact2]

        # Patch Pydantic AI Agent
        with patch("pydantic_ai.Agent") as MockAgent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.run = AsyncMock(return_value=mock_result)
            MockAgent.return_value = mock_agent_instance

            facts = await manager._extract_facts_via_llm(
                "I work at Google as a software engineer. On weekends I love hiking."
            )

            assert len(facts) == 2
            assert facts[0]["fact"] == "Works as a software engineer at Google"
            assert facts[0]["category"] == "occupation"
            assert facts[1]["fact"] == "Enjoys hiking on weekends"
            assert facts[1]["category"] == "hobby"

    @pytest.mark.asyncio
    async def test_extract_facts_llm_handles_error_gracefully(self):
        """P0-4: LLM extraction returns empty list on error."""
        from nikita.agents.voice.transcript import TranscriptManager

        manager = TranscriptManager(session=None)

        # Patch Pydantic AI Agent to raise an exception
        with patch("pydantic_ai.Agent") as MockAgent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.run = AsyncMock(side_effect=Exception("LLM error"))
            MockAgent.return_value = mock_agent_instance

            facts = await manager._extract_facts_via_llm("Some transcript text")

            # Should return empty list, not raise exception
            assert facts == []

    @pytest.mark.asyncio
    async def test_extract_facts_llm_empty_text(self):
        """P0-4: LLM extraction handles empty text."""
        from nikita.agents.voice.transcript import TranscriptManager

        manager = TranscriptManager(session=None)

        # Empty text should be caught before LLM call in extract_facts
        transcript = TranscriptData(
            session_id="test",
            entries=[],
        )

        facts = await manager.extract_facts(transcript)
        assert facts == []
