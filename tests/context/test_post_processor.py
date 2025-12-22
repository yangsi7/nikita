"""Tests for PostProcessor class.

TDD Tests for context engineering (spec 012) - Post-processing pipeline

Acceptance Criteria:
- AC-1: process_conversation() runs full pipeline on success
- AC-2: process_conversation() fails gracefully when conversation not found
- AC-3: process_conversation() fails gracefully when no messages
- AC-4: _stage_ingestion() loads conversation correctly
- AC-5: _stage_extraction() parses LLM response correctly
- AC-6: _stage_extraction() handles parse errors gracefully
- AC-7: _stage_create_threads() creates threads from extraction
- AC-8: _stage_create_thoughts() creates thoughts from extraction
- AC-9: _stage_summary_rollups() creates new summary
- AC-10: _stage_summary_rollups() updates existing summary
- AC-11: Pipeline marks conversation as processed on success
- AC-12: Pipeline marks conversation as failed on error
- AC-13: Convenience function processes multiple conversations
"""

import json
from datetime import UTC, datetime, date
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.conversation import Conversation
from nikita.db.models.game import DailySummary


# ============================================
# Mock for MetaPromptService
# ============================================
@pytest.fixture
def mock_meta_prompt_service():
    """Mock MetaPromptService to avoid API key requirement.

    Returns a function that creates a context manager patching MetaPromptService
    at the actual import location (nikita.meta_prompts.MetaPromptService), since
    post_processor.py uses a local import: `from nikita.meta_prompts import MetaPromptService`.
    """
    def _mock_generator(extract_result: dict | None = None):
        """Create mock with specified extract_entities result."""
        default_result = {
            "user_facts": [{"category": "work", "content": "User is a software engineer"}],
            "threads": [{"thread_type": "follow_up", "topic": "Ask about how the deadline went"}],
            "emotional_markers": [{"emotion_type": "connection", "intensity": 0.8, "context": "work discussion"}],
            "nikita_thoughts": [{"thought_type": "thinking", "content": "Hope his deadline goes well"}],
            "summary": "Casual morning chat about work stress and upcoming deadline.",
        }
        # Use `is None` check, not `or`, since empty dict {} is valid but falsy
        result = default_result if extract_result is None else extract_result

        # Patch at the actual module location, not the import alias
        mock_mps = patch('nikita.meta_prompts.MetaPromptService')
        mock_class = mock_mps.start()
        mock_instance = MagicMock()
        mock_instance.extract_entities = AsyncMock(return_value=result)
        mock_class.return_value = mock_instance
        return mock_mps, mock_instance
    return _mock_generator


class TestPostProcessorBasics:
    """Test suite for basic PostProcessor functionality."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock AsyncSession."""
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def mock_conversation(self) -> MagicMock:
        """Create a mock Conversation with messages."""
        conv = MagicMock(spec=Conversation)
        conv.id = uuid4()
        conv.user_id = uuid4()
        conv.messages = [
            {"role": "user", "content": "Hey Nikita, how are you?"},
            {"role": "assistant", "content": "Hey! I'm doing great, just had some coffee. How's your day going?"},
            {"role": "user", "content": "Pretty good, got a big deadline at work tomorrow."},
            {"role": "assistant", "content": "Oh interesting! What are you working on?"},
            {"role": "user", "content": "A new feature for our app. I'm a software engineer."},
            {"role": "assistant", "content": "That's cool! I bet you'll nail it 💪"},
        ]
        conv.status = "processing"
        conv.created_at = datetime.now(UTC)
        return conv

    @pytest.fixture
    def mock_extraction_response(self) -> str:
        """Create a mock LLM extraction response."""
        return json.dumps({
            "facts": [
                {"type": "explicit", "content": "User is a software engineer"},
                {"type": "implicit", "content": "User works under deadlines"},
            ],
            "entities": [
                {"type": "event", "name": "work deadline", "context": "tomorrow"},
            ],
            "preferences": [],
            "summary": "Casual morning chat about work stress and upcoming deadline.",
            "emotional_tone": "positive",
            "key_moments": ["User shared about work deadline", "Nikita was supportive"],
            "how_it_ended": "good_note",
            "threads": [
                {"type": "follow_up", "content": "Ask about how the deadline went"},
            ],
            "thoughts": [
                {"type": "thinking", "content": "Hope his deadline goes well"},
                {"type": "wants_to_share", "content": "That productivity tip I read about"},
            ],
        })

    # ========================================
    # AC-1: process_conversation() runs full pipeline on success
    # ========================================
    @pytest.mark.asyncio
    async def test_process_conversation_full_pipeline_success(
        self,
        mock_session: AsyncMock,
        mock_conversation: MagicMock,
        mock_meta_prompt_service,
    ):
        """AC-1: process_conversation() runs all 8 stages on success."""
        from nikita.context.post_processor import PostProcessor

        # MetaPromptService returns format with deadline topic
        extract_result = {
            "user_facts": [
                {"category": "work", "content": "User is a software engineer"},
                {"category": "work", "content": "User has a deadline tomorrow"},
            ],
            "threads": [{"thread_type": "follow_up", "topic": "Ask about how the deadline went"}],
            "emotional_markers": [{"emotion_type": "connection", "intensity": 0.8, "context": "work discussion"}],
            "nikita_thoughts": [
                {"thought_type": "thinking", "content": "Hope his deadline goes well"},
                {"thought_type": "wants_to_share", "content": "That productivity tip I read about"},
            ],
            "summary": "Casual morning chat about work stress and upcoming deadline.",
        }
        mock_mps, _ = mock_meta_prompt_service(extract_result)

        try:
            processor = PostProcessor(mock_session)

            # Mock conversation repository
            with patch.object(
                processor._conversation_repo, "get", return_value=mock_conversation
            ):
                with patch.object(
                    processor._conversation_repo, "mark_processed", return_value=None
                ):
                    # Mock thread/thought repos
                    with patch.object(
                        processor._thread_repo, "get_open_threads", return_value=[]
                    ):
                        with patch.object(
                            processor._thread_repo, "bulk_create_threads", return_value=[]
                        ):
                            with patch.object(
                                processor._thought_repo, "bulk_create_thoughts", return_value=[]
                            ):
                                # Mock summary repo
                                with patch.object(
                                    processor._summary_repo, "get_for_date", return_value=None
                                ):
                                    with patch.object(
                                        processor._summary_repo, "create_summary", return_value=None
                                    ):
                                        result = await processor.process_conversation(
                                            mock_conversation.id
                                        )
        finally:
            mock_mps.stop()

        assert result.success is True
        assert result.stage_reached == "complete"
        assert result.error is None
        assert result.summary is not None
        assert "deadline" in result.summary.lower()
        assert result.threads_created == 1
        assert result.thoughts_created == 2

    # ========================================
    # AC-2: process_conversation() fails when conversation not found
    # ========================================
    @pytest.mark.asyncio
    async def test_process_conversation_not_found_fails(
        self, mock_session: AsyncMock
    ):
        """AC-2: process_conversation() fails gracefully when not found."""
        from nikita.context.post_processor import PostProcessor

        processor = PostProcessor(mock_session)

        with patch.object(processor._conversation_repo, "get", return_value=None):
            result = await processor.process_conversation(uuid4())

        assert result.success is False
        assert result.stage_reached == "ingestion"
        assert "not found" in result.error.lower()

    # ========================================
    # AC-3: process_conversation() fails when no messages
    # ========================================
    @pytest.mark.asyncio
    async def test_process_conversation_no_messages_fails(
        self, mock_session: AsyncMock
    ):
        """AC-3: process_conversation() fails when conversation has no messages."""
        from nikita.context.post_processor import PostProcessor

        conv = MagicMock(spec=Conversation)
        conv.id = uuid4()
        conv.messages = []  # Empty messages

        processor = PostProcessor(mock_session)

        with patch.object(processor._conversation_repo, "get", return_value=conv):
            result = await processor.process_conversation(conv.id)

        assert result.success is False
        assert result.stage_reached == "ingestion"

    # ========================================
    # AC-4: _stage_ingestion() loads conversation correctly
    # ========================================
    @pytest.mark.asyncio
    async def test_stage_ingestion_loads_conversation(
        self, mock_session: AsyncMock, mock_conversation: MagicMock
    ):
        """AC-4: _stage_ingestion() returns conversation when found."""
        from nikita.context.post_processor import PostProcessor

        processor = PostProcessor(mock_session)

        with patch.object(
            processor._conversation_repo, "get", return_value=mock_conversation
        ):
            result = await processor._stage_ingestion(mock_conversation.id)

        assert result is not None
        assert result.id == mock_conversation.id
        assert len(result.messages) > 0


class TestExtractionStage:
    """Test _stage_extraction and related methods."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def mock_conversation(self) -> MagicMock:
        conv = MagicMock(spec=Conversation)
        conv.id = uuid4()
        conv.user_id = uuid4()
        conv.messages = [
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        return conv

    # ========================================
    # AC-5: _stage_extraction() parses LLM response correctly
    # ========================================
    @pytest.mark.asyncio
    async def test_stage_extraction_parses_llm_response(
        self, mock_session: AsyncMock, mock_conversation: MagicMock, mock_meta_prompt_service
    ):
        """AC-5: _stage_extraction() correctly parses structured JSON response."""
        from nikita.context.post_processor import PostProcessor

        # MetaPromptService returns format
        extract_result = {
            "user_facts": [{"category": "greeting", "content": "User said hello"}],
            "threads": [],
            "emotional_markers": [{"emotion_type": "connection", "intensity": 0.8, "context": "Initial greeting"}],
            "nikita_thoughts": [{"thought_type": "feeling", "content": "Happy to chat"}],
            "summary": "Brief greeting exchange.",
        }
        mock_mps, _ = mock_meta_prompt_service(extract_result)

        try:
            processor = PostProcessor(mock_session)
            # Mock get_open_threads to return empty list (no open threads)
            with patch.object(processor._thread_repo, "get_open_threads", return_value=[]):
                result = await processor._stage_extraction(mock_conversation)
        finally:
            mock_mps.stop()

        assert result.summary == "Brief greeting exchange."
        assert result.emotional_tone == "positive"  # connection -> positive
        assert len(result.facts) == 1
        assert result.facts[0]["content"] == "User said hello"
        assert len(result.thoughts) == 1
        assert result.thoughts[0]["type"] == "feeling"

    # ========================================
    # AC-6: _stage_extraction() handles parse errors gracefully
    # ========================================
    @pytest.mark.asyncio
    async def test_stage_extraction_handles_parse_error(
        self, mock_session: AsyncMock, mock_conversation: MagicMock, mock_meta_prompt_service
    ):
        """AC-6: _stage_extraction() returns defaults when extraction returns empty data."""
        from nikita.context.post_processor import PostProcessor

        # MetaPromptService returns empty/malformed response
        extract_result = {}  # Empty dict simulates missing/malformed data
        mock_mps, _ = mock_meta_prompt_service(extract_result)

        try:
            processor = PostProcessor(mock_session)
            # Mock get_open_threads to return empty list (no open threads)
            with patch.object(processor._thread_repo, "get_open_threads", return_value=[]):
                result = await processor._stage_extraction(mock_conversation)
        finally:
            mock_mps.stop()

        # Should return defaults, not crash
        assert result.summary == "Conversation occurred."
        assert result.emotional_tone == "neutral"
        assert result.facts == []
        assert result.threads == []

    def test_format_messages(self, mock_session: AsyncMock):
        """Test _format_messages correctly formats conversation."""
        from nikita.context.post_processor import PostProcessor

        processor = PostProcessor(mock_session)

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
            {"role": "user", "content": "How are you?"},
        ]

        formatted = processor._format_messages(messages)

        assert "User: Hello" in formatted
        assert "Nikita: Hi!" in formatted
        assert "User: How are you?" in formatted


class TestThreadAndThoughtCreation:
    """Test thread and thought creation stages."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def mock_conversation(self) -> MagicMock:
        conv = MagicMock(spec=Conversation)
        conv.id = uuid4()
        conv.user_id = uuid4()
        return conv

    # ========================================
    # AC-7: _stage_create_threads() creates threads from extraction
    # ========================================
    @pytest.mark.asyncio
    async def test_stage_create_threads_creates_from_extraction(
        self, mock_session: AsyncMock, mock_conversation: MagicMock
    ):
        """AC-7: _stage_create_threads() creates threads from extraction data."""
        from nikita.context.post_processor import PostProcessor

        threads = [
            {"type": "follow_up", "content": "Ask about work project"},
            {"type": "question", "content": "What's his favorite food?"},
            {"type": "promise", "content": "Send him that article"},
        ]

        processor = PostProcessor(mock_session)

        with patch.object(
            processor._thread_repo, "bulk_create_threads", return_value=[]
        ) as mock_bulk:
            with patch.object(
                processor._thread_repo, "resolve_thread", return_value=None
            ):
                count = await processor._stage_create_threads(
                    conversation=mock_conversation,
                    threads=threads,
                    resolved_ids=[],
                )

        assert count == 3
        mock_bulk.assert_called_once()
        call_kwargs = mock_bulk.call_args[1]
        assert len(call_kwargs["threads_data"]) == 3
        assert call_kwargs["user_id"] == mock_conversation.user_id

    @pytest.mark.asyncio
    async def test_stage_create_threads_resolves_existing(
        self, mock_session: AsyncMock, mock_conversation: MagicMock
    ):
        """AC-7b: _stage_create_threads() resolves marked thread IDs."""
        from nikita.context.post_processor import PostProcessor

        resolved_id = uuid4()

        processor = PostProcessor(mock_session)

        with patch.object(
            processor._thread_repo, "bulk_create_threads", return_value=[]
        ):
            with patch.object(
                processor._thread_repo, "resolve_thread", return_value=None
            ) as mock_resolve:
                await processor._stage_create_threads(
                    conversation=mock_conversation,
                    threads=[],
                    resolved_ids=[resolved_id],
                )

        mock_resolve.assert_called_once_with(resolved_id)

    # ========================================
    # AC-8: _stage_create_thoughts() creates thoughts from extraction
    # ========================================
    @pytest.mark.asyncio
    async def test_stage_create_thoughts_creates_from_extraction(
        self, mock_session: AsyncMock, mock_conversation: MagicMock
    ):
        """AC-8: _stage_create_thoughts() creates thoughts from extraction data."""
        from nikita.context.post_processor import PostProcessor

        thoughts = [
            {"type": "thinking", "content": "What he said about work..."},
            {"type": "feeling", "content": "Excited about where this is going"},
        ]

        processor = PostProcessor(mock_session)

        with patch.object(
            processor._thought_repo, "bulk_create_thoughts", return_value=[]
        ) as mock_bulk:
            count = await processor._stage_create_thoughts(
                conversation=mock_conversation,
                thoughts=thoughts,
            )

        assert count == 2
        mock_bulk.assert_called_once()
        call_kwargs = mock_bulk.call_args[1]
        assert len(call_kwargs["thoughts_data"]) == 2
        assert call_kwargs["user_id"] == mock_conversation.user_id


class TestSummaryRollups:
    """Test summary rollup stage."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def mock_conversation(self) -> MagicMock:
        conv = MagicMock(spec=Conversation)
        conv.id = uuid4()
        conv.user_id = uuid4()
        return conv

    @pytest.fixture
    def mock_extraction_result(self):
        """Create a mock ExtractionResult."""
        from nikita.context.post_processor import ExtractionResult

        return ExtractionResult(
            facts=[],
            entities=[],
            preferences=[],
            summary="Great conversation about travel.",
            emotional_tone="positive",
            key_moments=["Shared travel stories", "Made plans for weekend"],
            how_it_ended="good_note",
            threads=[],
            resolved_threads=[],
            thoughts=[],
        )

    # ========================================
    # AC-9: _stage_summary_rollups() creates new summary
    # ========================================
    @pytest.mark.asyncio
    async def test_stage_summary_rollups_creates_new(
        self,
        mock_session: AsyncMock,
        mock_conversation: MagicMock,
        mock_extraction_result,
    ):
        """AC-9: _stage_summary_rollups() creates new daily summary when none exists."""
        from nikita.context.post_processor import PostProcessor

        processor = PostProcessor(mock_session)

        with patch.object(
            processor._summary_repo, "get_for_date", return_value=None
        ):
            with patch.object(
                processor._summary_repo, "create_summary", return_value=None
            ) as mock_create:
                await processor._stage_summary_rollups(
                    conversation=mock_conversation,
                    extraction=mock_extraction_result,
                )

        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["user_id"] == mock_conversation.user_id
        assert call_kwargs["summary_text"] == "Great conversation about travel."
        assert call_kwargs["emotional_tone"] == "positive"

    # ========================================
    # AC-10: _stage_summary_rollups() updates existing summary
    # ========================================
    @pytest.mark.asyncio
    async def test_stage_summary_rollups_updates_existing(
        self,
        mock_session: AsyncMock,
        mock_conversation: MagicMock,
        mock_extraction_result,
    ):
        """AC-10: _stage_summary_rollups() updates existing daily summary."""
        from nikita.context.post_processor import PostProcessor

        existing_summary = MagicMock(spec=DailySummary)
        existing_summary.id = uuid4()
        existing_summary.summary_text = "Morning chat about coffee."
        existing_summary.key_moments = [
            {"source": str(uuid4()), "moments": ["Discussed coffee preferences"]}
        ]

        processor = PostProcessor(mock_session)

        with patch.object(
            processor._summary_repo, "get_for_date", return_value=existing_summary
        ):
            with patch.object(
                processor._summary_repo, "update_summary", return_value=None
            ) as mock_update:
                await processor._stage_summary_rollups(
                    conversation=mock_conversation,
                    extraction=mock_extraction_result,
                )

        mock_update.assert_called_once()
        call_kwargs = mock_update.call_args[1]
        # Summary should be appended
        assert "Morning chat about coffee." in call_kwargs["summary_text"]
        assert "Great conversation about travel." in call_kwargs["summary_text"]
        # Key moments should be extended
        assert len(call_kwargs["key_moments"]) == 2


class TestPipelineStatusMarking:
    """Test pipeline status marking on success/failure."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        session = AsyncMock(spec=AsyncSession)
        return session

    # ========================================
    # AC-11: Pipeline marks conversation as processed on success
    # ========================================
    @pytest.mark.asyncio
    async def test_pipeline_marks_processed_on_success(self, mock_session: AsyncMock, mock_meta_prompt_service):
        """AC-11: Pipeline calls mark_processed on successful completion."""
        from nikita.context.post_processor import PostProcessor

        conv = MagicMock(spec=Conversation)
        conv.id = uuid4()
        conv.user_id = uuid4()
        conv.messages = [{"role": "user", "content": "Hello"}]

        # MetaPromptService returns format (no thoughts)
        extract_result = {
            "user_facts": [],
            "threads": [],
            "emotional_markers": [],
            "nikita_thoughts": [],
            "summary": "Short greeting.",
        }
        mock_mps, _ = mock_meta_prompt_service(extract_result)

        try:
            processor = PostProcessor(mock_session)

            with patch.object(processor._conversation_repo, "get", return_value=conv):
                with patch.object(
                    processor._conversation_repo, "mark_processed", return_value=None
                ) as mock_mark:
                    with patch.object(
                        processor._thread_repo, "get_open_threads", return_value=[]
                    ):
                        with patch.object(
                            processor._thread_repo, "bulk_create_threads", return_value=[]
                        ):
                            with patch.object(
                                processor._thought_repo, "bulk_create_thoughts", return_value=[]
                            ):
                                with patch.object(
                                    processor._summary_repo, "get_for_date", return_value=None
                                ):
                                    with patch.object(
                                        processor._summary_repo, "create_summary", return_value=None
                                    ):
                                        result = await processor.process_conversation(conv.id)
        finally:
            mock_mps.stop()

        assert result.success is True
        mock_mark.assert_called_once_with(
            conversation_id=conv.id,
            summary="Short greeting.",
            emotional_tone="neutral",  # No markers -> neutral
            extracted_entities={
                "facts": [],
                "entities": [],
                "preferences": [],
                "key_moments": [],
                "how_it_ended": "neutral",  # neutral tone -> neutral ending
            },
        )

    # ========================================
    # AC-12: Pipeline marks conversation as failed on error
    # ========================================
    @pytest.mark.asyncio
    async def test_pipeline_marks_failed_on_error(self, mock_session: AsyncMock):
        """AC-12: Pipeline calls mark_failed when an error occurs."""
        from nikita.context.post_processor import PostProcessor

        conv = MagicMock(spec=Conversation)
        conv.id = uuid4()
        conv.user_id = uuid4()
        conv.messages = [{"role": "user", "content": "Hello"}]

        # Mock MetaPromptService to raise an exception during extraction
        # Patch at actual import location since post_processor uses local import
        mock_mps = patch('nikita.meta_prompts.MetaPromptService')
        mock_class = mock_mps.start()
        mock_instance = MagicMock()
        mock_instance.extract_entities = AsyncMock(side_effect=Exception("LLM unavailable"))
        mock_class.return_value = mock_instance

        try:
            processor = PostProcessor(mock_session)

            with patch.object(processor._conversation_repo, "get", return_value=conv):
                with patch.object(
                    processor._thread_repo, "get_open_threads", return_value=[]
                ):
                    with patch.object(
                        processor._conversation_repo, "mark_failed", return_value=None
                    ) as mock_mark_failed:
                        result = await processor.process_conversation(conv.id)
        finally:
            mock_mps.stop()

        assert result.success is False
        assert result.stage_reached == "extraction"
        assert "LLM unavailable" in result.error
        mock_mark_failed.assert_called_once_with(conv.id)


class TestConvenienceFunction:
    """Test the process_conversations convenience function."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        session = AsyncMock(spec=AsyncSession)
        return session

    # ========================================
    # AC-13: Convenience function processes multiple conversations
    # ========================================
    @pytest.mark.asyncio
    async def test_convenience_function_processes_multiple(
        self, mock_session: AsyncMock
    ):
        """AC-13: process_conversations() processes list of conversation IDs."""
        from nikita.context.post_processor import (
            PipelineResult,
            process_conversations,
        )

        conv_id_1 = uuid4()
        conv_id_2 = uuid4()
        conv_id_3 = uuid4()

        results = [
            PipelineResult(
                conversation_id=conv_id_1,
                success=True,
                stage_reached="complete",
            ),
            PipelineResult(
                conversation_id=conv_id_2,
                success=False,
                stage_reached="extraction",
                error="LLM error",
            ),
            PipelineResult(
                conversation_id=conv_id_3,
                success=True,
                stage_reached="complete",
            ),
        ]

        with patch(
            "nikita.context.post_processor.PostProcessor"
        ) as MockProcessor:
            mock_instance = MagicMock()
            mock_instance.process_conversation = AsyncMock(side_effect=results)
            MockProcessor.return_value = mock_instance

            actual_results = await process_conversations(
                session=mock_session,
                conversation_ids=[conv_id_1, conv_id_2, conv_id_3],
            )

        assert len(actual_results) == 3
        assert actual_results[0].success is True
        assert actual_results[1].success is False
        assert actual_results[2].success is True

        # Verify all conversations were processed
        assert mock_instance.process_conversation.call_count == 3


class TestPipelineDataclasses:
    """Test dataclass behaviors."""

    def test_pipeline_result_defaults(self):
        """Test PipelineResult has correct defaults."""
        from nikita.context.post_processor import PipelineResult

        result = PipelineResult(
            conversation_id=uuid4(),
            success=False,
            stage_reached="init",
        )

        assert result.error is None
        assert result.summary is None
        assert result.emotional_tone is None
        assert result.extracted_entities is None
        assert result.threads_created == 0
        assert result.thoughts_created == 0

    def test_extraction_result_structure(self):
        """Test ExtractionResult structure."""
        from nikita.context.post_processor import ExtractionResult

        result = ExtractionResult(
            facts=[{"type": "explicit", "content": "Test fact"}],
            entities=[{"type": "person", "name": "John"}],
            preferences=[],
            summary="Test summary.",
            emotional_tone="positive",
            key_moments=["Moment 1"],
            how_it_ended="good_note",
            threads=[{"type": "follow_up", "content": "Test thread"}],
            resolved_threads=[],
            thoughts=[{"type": "thinking", "content": "Test thought"}],
        )

        assert len(result.facts) == 1
        assert result.summary == "Test summary."
        assert result.emotional_tone == "positive"


class TestThreadTypeValidation:
    """Test that invalid thread_types are filtered before DB insert.

    TDD Tests for post-processing fix: Invalid thread type filtering
    Fixes the error: Invalid thread_type: curiosity
    """

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def mock_conversation(self) -> MagicMock:
        conv = MagicMock(spec=Conversation)
        conv.id = uuid4()
        conv.user_id = uuid4()
        return conv

    @pytest.mark.asyncio
    async def test_stage_create_threads_filters_invalid_types(
        self, mock_session: AsyncMock, mock_conversation: MagicMock
    ):
        """AC-T3.1: Invalid thread_types are filtered out."""
        from nikita.context.post_processor import PostProcessor
        from nikita.db.models.context import THREAD_TYPES

        processor = PostProcessor(mock_session)

        # Mix of valid and invalid thread types (as generated by LLM)
        # Note: "curiosity" is now VALID (MetaPrompt type)
        threads = [
            {"type": "follow_up", "content": "Valid: Ask about work project"},
            {"type": "curiosity", "content": "Valid: MetaPrompt type"},
            {"type": "question", "content": "Valid: What's his favorite food?"},
            {"type": "excitement", "content": "Invalid: Should be filtered"},
            {"type": "promise", "content": "Valid: Send him that article"},
            {"type": "love", "content": "Invalid: Should be filtered"},
        ]

        with patch.object(
            processor._thread_repo, "bulk_create_threads", new=AsyncMock()
        ) as mock_bulk:
            with patch.object(
                processor._thread_repo, "resolve_thread", return_value=None
            ):
                count = await processor._stage_create_threads(
                    conversation=mock_conversation,
                    threads=threads,
                    resolved_ids=[],
                )

        # Should only pass valid types to bulk_create_threads
        mock_bulk.assert_called_once()
        call_kwargs = mock_bulk.call_args[1]
        threads_data = call_kwargs["threads_data"]

        # 4 valid threads should be passed (curiosity is now valid)
        assert len(threads_data) == 4
        assert all(t["thread_type"] in THREAD_TYPES for t in threads_data)

        # Verify the valid types made it through
        thread_types = [t["thread_type"] for t in threads_data]
        assert "follow_up" in thread_types
        assert "question" in thread_types
        assert "promise" in thread_types
        assert "curiosity" in thread_types  # Now valid (MetaPrompt type)

        # Verify invalid types were filtered
        assert "excitement" not in thread_types
        assert "love" not in thread_types

    @pytest.mark.asyncio
    @pytest.mark.parametrize("invalid_type", [
        # "curiosity" is now VALID (MetaPrompt type)
        "excitement",
        "love",
        "interest",
        "random",
        "empathy",
        "",
        "FOLLOW_UP",  # Wrong case
    ])
    async def test_invalid_thread_types_never_reach_db(
        self, mock_session: AsyncMock, mock_conversation: MagicMock, invalid_type: str
    ):
        """AC-T3.2: Parametrized test for various invalid thread types."""
        from nikita.context.post_processor import PostProcessor

        processor = PostProcessor(mock_session)

        threads = [{"type": invalid_type, "content": "Should be filtered"}]

        with patch.object(
            processor._thread_repo, "bulk_create_threads", new=AsyncMock()
        ) as mock_bulk:
            with patch.object(
                processor._thread_repo, "resolve_thread", return_value=None
            ):
                count = await processor._stage_create_threads(
                    conversation=mock_conversation,
                    threads=threads,
                    resolved_ids=[],
                )

        # Should pass empty list or not call at all
        if mock_bulk.called:
            call_kwargs = mock_bulk.call_args[1]
            threads_data = call_kwargs["threads_data"]
            assert len(threads_data) == 0

    @pytest.mark.asyncio
    async def test_valid_thread_types_pass_through(
        self, mock_session: AsyncMock, mock_conversation: MagicMock
    ):
        """AC-T3.3: Valid thread_types pass through correctly."""
        from nikita.context.post_processor import PostProcessor
        from nikita.db.models.context import THREAD_TYPES

        processor = PostProcessor(mock_session)

        # All valid thread types
        threads = [
            {"type": "follow_up", "content": "Follow up content"},
            {"type": "question", "content": "Question content"},
            {"type": "promise", "content": "Promise content"},
            {"type": "topic", "content": "Topic content"},
        ]

        with patch.object(
            processor._thread_repo, "bulk_create_threads", new=AsyncMock()
        ) as mock_bulk:
            with patch.object(
                processor._thread_repo, "resolve_thread", return_value=None
            ):
                count = await processor._stage_create_threads(
                    conversation=mock_conversation,
                    threads=threads,
                    resolved_ids=[],
                )

        # All 4 should pass through
        mock_bulk.assert_called_once()
        call_kwargs = mock_bulk.call_args[1]
        threads_data = call_kwargs["threads_data"]
        assert len(threads_data) == 4


class TestThoughtTypeValidation:
    """Test that invalid thought_types are filtered before DB insert.

    TDD Tests for post-processing fix: Invalid thought type filtering
    """

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def mock_conversation(self) -> MagicMock:
        conv = MagicMock(spec=Conversation)
        conv.id = uuid4()
        conv.user_id = uuid4()
        return conv

    @pytest.mark.asyncio
    async def test_stage_create_thoughts_filters_invalid_types(
        self, mock_session: AsyncMock, mock_conversation: MagicMock
    ):
        """AC-T4.1: Invalid thought_types are filtered out."""
        from nikita.context.post_processor import PostProcessor
        from nikita.db.models.context import THOUGHT_TYPES

        processor = PostProcessor(mock_session)

        # Mix of valid and invalid thought types (as generated by LLM)
        thoughts = [
            {"type": "thinking", "content": "Valid: What he said about work..."},
            {"type": "happiness", "content": "Invalid: Should be filtered"},
            {"type": "feeling", "content": "Valid: Excited about where this is going"},
            {"type": "sadness", "content": "Invalid: Should be filtered"},
            {"type": "missing_him", "content": "Valid: Wish he'd text me"},
            {"type": "love", "content": "Invalid: Should be filtered"},
        ]

        with patch.object(
            processor._thought_repo, "bulk_create_thoughts", new=AsyncMock()
        ) as mock_bulk:
            count = await processor._stage_create_thoughts(
                conversation=mock_conversation,
                thoughts=thoughts,
            )

        # Should only pass valid types to bulk_create_thoughts
        mock_bulk.assert_called_once()
        call_kwargs = mock_bulk.call_args[1]
        thoughts_data = call_kwargs["thoughts_data"]

        # Only 3 valid thoughts should be passed
        assert len(thoughts_data) == 3
        assert all(t["thought_type"] in THOUGHT_TYPES for t in thoughts_data)

        # Verify the valid types made it through
        thought_types = [t["thought_type"] for t in thoughts_data]
        assert "thinking" in thought_types
        assert "feeling" in thought_types
        assert "missing_him" in thought_types

        # Verify invalid types were filtered
        assert "happiness" not in thought_types
        assert "sadness" not in thought_types
        assert "love" not in thought_types

    @pytest.mark.asyncio
    @pytest.mark.parametrize("invalid_type", [
        "happiness",
        "sadness",
        "love",
        # "curiosity" is now VALID (MetaPrompt type)
        "excitement",
        "random_emotion",
        "",
        "THINKING",  # Wrong case
    ])
    async def test_invalid_thought_types_never_reach_db(
        self, mock_session: AsyncMock, mock_conversation: MagicMock, invalid_type: str
    ):
        """AC-T4.2: Parametrized test for various invalid thought types."""
        from nikita.context.post_processor import PostProcessor

        processor = PostProcessor(mock_session)

        thoughts = [{"type": invalid_type, "content": "Should be filtered"}]

        with patch.object(
            processor._thought_repo, "bulk_create_thoughts", new=AsyncMock()
        ) as mock_bulk:
            count = await processor._stage_create_thoughts(
                conversation=mock_conversation,
                thoughts=thoughts,
            )

        # Should pass empty list or not call at all
        if mock_bulk.called:
            call_kwargs = mock_bulk.call_args[1]
            thoughts_data = call_kwargs["thoughts_data"]
            assert len(thoughts_data) == 0

    @pytest.mark.asyncio
    async def test_valid_thought_types_pass_through(
        self, mock_session: AsyncMock, mock_conversation: MagicMock
    ):
        """AC-T4.3: Valid thought_types pass through correctly."""
        from nikita.context.post_processor import PostProcessor
        from nikita.db.models.context import THOUGHT_TYPES

        processor = PostProcessor(mock_session)

        # All valid thought types
        thoughts = [
            {"type": "thinking", "content": "Thinking content"},
            {"type": "wants_to_share", "content": "Wants to share content"},
            {"type": "question", "content": "Question content"},
            {"type": "feeling", "content": "Feeling content"},
            {"type": "missing_him", "content": "Missing him content"},
        ]

        with patch.object(
            processor._thought_repo, "bulk_create_thoughts", new=AsyncMock()
        ) as mock_bulk:
            count = await processor._stage_create_thoughts(
                conversation=mock_conversation,
                thoughts=thoughts,
            )

        # All 5 should pass through
        mock_bulk.assert_called_once()
        call_kwargs = mock_bulk.call_args[1]
        thoughts_data = call_kwargs["thoughts_data"]
        assert len(thoughts_data) == 5


class TestMetaPromptThreadTypeAcceptance:
    """TDD tests for MetaPrompt thread types acceptance.

    These tests verify that thread types returned by entity_extraction.meta.md
    are accepted by the post-processing pipeline.

    MetaPrompt types: unresolved, cliffhanger, promise, curiosity, callback
    """

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def mock_conversation(self) -> MagicMock:
        conv = MagicMock(spec=Conversation)
        conv.id = uuid4()
        conv.user_id = uuid4()
        return conv

    @pytest.mark.asyncio
    @pytest.mark.parametrize("thread_type", [
        "unresolved",   # MetaPrompt: Question asked but not fully answered
        "cliffhanger",  # MetaPrompt: Story started but not finished
        "promise",      # MetaPrompt: Something to do/discuss later
        "curiosity",    # MetaPrompt: Topic Nikita should ask more about
        "callback",     # MetaPrompt: Reference to revisit for continuity
    ])
    async def test_metaprompt_thread_types_are_valid(
        self, mock_session: AsyncMock, mock_conversation: MagicMock, thread_type: str
    ):
        """AC-T3.4: MetaPrompt thread types are accepted by THREAD_TYPES."""
        from nikita.db.models.context import THREAD_TYPES

        # This assertion will FAIL until THREAD_TYPES is updated
        assert thread_type in THREAD_TYPES, (
            f"MetaPrompt thread type '{thread_type}' not in THREAD_TYPES. "
            f"Valid types: {THREAD_TYPES}"
        )

    @pytest.mark.asyncio
    async def test_all_metaprompt_thread_types_pass_through_pipeline(
        self, mock_session: AsyncMock, mock_conversation: MagicMock
    ):
        """AC-T3.5: All 5 MetaPrompt thread types pass through post-processor."""
        from nikita.context.post_processor import PostProcessor
        from nikita.db.models.context import THREAD_TYPES

        processor = PostProcessor(mock_session)

        # All MetaPrompt thread types from entity_extraction.meta.md
        threads = [
            {"type": "unresolved", "content": "What's his plan for the weekend?"},
            {"type": "cliffhanger", "content": "He started telling me about his trip..."},
            {"type": "promise", "content": "He said he'd show me that restaurant"},
            {"type": "curiosity", "content": "He mentioned his sister - want to know more"},
            {"type": "callback", "content": "His favorite coffee shop from last week"},
        ]

        with patch.object(
            processor._thread_repo, "bulk_create_threads", new=AsyncMock()
        ) as mock_bulk:
            with patch.object(
                processor._thread_repo, "resolve_thread", return_value=None
            ):
                count = await processor._stage_create_threads(
                    conversation=mock_conversation,
                    threads=threads,
                    resolved_ids=[],
                )

        # All 5 MetaPrompt types should pass through (not be filtered)
        mock_bulk.assert_called_once()
        call_kwargs = mock_bulk.call_args[1]
        threads_data = call_kwargs["threads_data"]

        # This assertion will FAIL until THREAD_TYPES is updated
        assert len(threads_data) == 5, (
            f"Expected 5 threads, got {len(threads_data)}. "
            f"MetaPrompt types are being filtered out."
        )


class TestMetaPromptThoughtTypeAcceptance:
    """TDD tests for MetaPrompt thought types acceptance.

    These tests verify that thought types returned by entity_extraction.meta.md
    are accepted by the post-processing pipeline.

    MetaPrompt types: worry, curiosity, anticipation, reflection, desire
    """

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def mock_conversation(self) -> MagicMock:
        conv = MagicMock(spec=Conversation)
        conv.id = uuid4()
        conv.user_id = uuid4()
        return conv

    @pytest.mark.asyncio
    @pytest.mark.parametrize("thought_type", [
        "worry",        # MetaPrompt: Something concerning about the user
        "curiosity",    # MetaPrompt: Something she wants to know more about
        "anticipation", # MetaPrompt: Something she's looking forward to
        "reflection",   # MetaPrompt: Something that made her think
        "desire",       # MetaPrompt: Something she wants from/with the user
    ])
    async def test_metaprompt_thought_types_are_valid(
        self, mock_session: AsyncMock, mock_conversation: MagicMock, thought_type: str
    ):
        """AC-T4.4: MetaPrompt thought types are accepted by THOUGHT_TYPES."""
        from nikita.db.models.context import THOUGHT_TYPES

        # This assertion will FAIL until THOUGHT_TYPES is updated
        assert thought_type in THOUGHT_TYPES, (
            f"MetaPrompt thought type '{thought_type}' not in THOUGHT_TYPES. "
            f"Valid types: {THOUGHT_TYPES}"
        )

    @pytest.mark.asyncio
    async def test_all_metaprompt_thought_types_pass_through_pipeline(
        self, mock_session: AsyncMock, mock_conversation: MagicMock
    ):
        """AC-T4.5: All 5 MetaPrompt thought types pass through post-processor."""
        from nikita.context.post_processor import PostProcessor
        from nikita.db.models.context import THOUGHT_TYPES

        processor = PostProcessor(mock_session)

        # All MetaPrompt thought types from entity_extraction.meta.md
        thoughts = [
            {"type": "worry", "content": "He seemed stressed, hope he's okay"},
            {"type": "curiosity", "content": "What's his relationship with his boss like?"},
            {"type": "anticipation", "content": "Can't wait for our weekend plans"},
            {"type": "reflection", "content": "What he said about trust made me think..."},
            {"type": "desire", "content": "I want him to open up more to me"},
        ]

        with patch.object(
            processor._thought_repo, "bulk_create_thoughts", new=AsyncMock()
        ) as mock_bulk:
            count = await processor._stage_create_thoughts(
                conversation=mock_conversation,
                thoughts=thoughts,
            )

        # All 5 MetaPrompt types should pass through (not be filtered)
        mock_bulk.assert_called_once()
        call_kwargs = mock_bulk.call_args[1]
        thoughts_data = call_kwargs["thoughts_data"]

        # This assertion will FAIL until THOUGHT_TYPES is updated
        assert len(thoughts_data) == 5, (
            f"Expected 5 thoughts, got {len(thoughts_data)}. "
            f"MetaPrompt types are being filtered out."
        )


class TestThoughtTypeKeyExtraction:
    """TDD test for thought_type key extraction fix.

    The MetaPrompt returns thoughts with 'thought_type' key, but post_processor.py
    was reading 'type' key instead, causing all thoughts to default to 'thinking'.
    """

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def mock_conversation(self) -> MagicMock:
        conv = MagicMock(spec=Conversation)
        conv.id = uuid4()
        conv.user_id = uuid4()
        conv.messages = [
            {"role": "user", "content": "Hi!"},
            {"role": "assistant", "content": "Hey!"},
        ]
        return conv

    @pytest.mark.asyncio
    async def test_extraction_reads_thought_type_key_not_type(
        self, mock_session: AsyncMock, mock_conversation: MagicMock
    ):
        """Regression test: post_processor reads 'thought_type' key from MetaPrompt.

        Bug: post_processor.py line 327 used t.get("type") instead of t.get("thought_type")
        This caused all thoughts to fallback to default 'thinking' type.
        """
        from nikita.context.post_processor import PostProcessor

        processor = PostProcessor(mock_session)

        # Mock MetaPromptService.extract_entities to return data with thought_type key
        # (matching the actual MetaPrompt template output format)
        metaprompt_result = {
            "user_facts": [],
            "threads": [],
            "emotional_markers": [],
            "nikita_thoughts": [
                {"thought_type": "worry", "content": "Hope he's not too stressed"},
                {"thought_type": "curiosity", "content": "Want to know more about his work"},
            ],
            "summary": "Brief chat about the day.",
        }

        with patch("nikita.meta_prompts.MetaPromptService") as mock_mps_class:
            mock_mps = MagicMock()
            mock_mps.extract_entities = AsyncMock(return_value=metaprompt_result)
            mock_mps_class.return_value = mock_mps

            # Mock get_open_threads to return empty list
            with patch.object(processor._thread_repo, "get_open_threads", return_value=[]):
                result = await processor._stage_extraction(mock_conversation)

        # Verify that thoughts have the correct types (not all defaulting to 'thinking')
        assert len(result.thoughts) == 2

        thought_types = [t["type"] for t in result.thoughts]

        # This assertion will FAIL until post_processor.py is fixed to use thought_type key
        assert "worry" in thought_types, (
            f"Expected 'worry' in thought types, got {thought_types}. "
            f"Bug: post_processor reads 'type' key instead of 'thought_type' key."
        )
        assert "curiosity" in thought_types, (
            f"Expected 'curiosity' in thought types, got {thought_types}. "
            f"Bug: post_processor reads 'type' key instead of 'thought_type' key."
        )


class TestThreadResolutionDetection:
    """Test suite for thread resolution detection feature (C-2)."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def mock_conversation(self) -> MagicMock:
        """Create a mock Conversation."""
        conv = MagicMock(spec=Conversation)
        conv.id = uuid4()
        conv.user_id = uuid4()
        conv.messages = [
            {"role": "user", "content": "Hey, I finished that project we talked about!"},
            {"role": "nikita", "content": "Oh that's great! How did the deadline go?"},
            {"role": "user", "content": "Met it with time to spare!"},
        ]
        conv.status = "processing"
        conv.created_at = datetime.now(UTC)
        return conv

    @pytest.mark.asyncio
    async def test_extraction_passes_open_threads_to_meta_service(
        self, mock_session: AsyncMock, mock_conversation: MagicMock
    ):
        """Test that open threads are loaded and passed to MetaPromptService."""
        from nikita.context.post_processor import PostProcessor

        processor = PostProcessor(mock_session)

        # Create mock open threads (simulating threads from previous conversations)
        thread_id = uuid4()
        mock_thread = MagicMock()
        mock_thread.id = thread_id
        mock_thread.thread_type = "follow_up"
        mock_thread.content = "Ask about the work deadline"

        # Mock the meta service response including resolved_thread_ids
        metaprompt_result = {
            "user_facts": [],
            "threads": [],
            "resolved_thread_ids": [str(thread_id)],  # LLM says this thread was resolved
            "emotional_markers": [],
            "nikita_thoughts": [],
            "summary": "User finished project, deadline was met.",
        }

        with patch("nikita.meta_prompts.MetaPromptService") as mock_mps_class:
            mock_mps = MagicMock()
            mock_mps.extract_entities = AsyncMock(return_value=metaprompt_result)
            mock_mps_class.return_value = mock_mps

            # Mock get_open_threads to return our thread
            with patch.object(processor._thread_repo, "get_open_threads", return_value=[mock_thread]) as mock_get:
                result = await processor._stage_extraction(mock_conversation)

        # Verify get_open_threads was called
        mock_get.assert_called_once_with(user_id=mock_conversation.user_id, limit=20)

        # Verify extract_entities was called with open_threads parameter
        call_kwargs = mock_mps.extract_entities.call_args.kwargs
        assert "open_threads" in call_kwargs
        assert len(call_kwargs["open_threads"]) == 1
        assert call_kwargs["open_threads"][0]["id"] == str(thread_id)
        assert call_kwargs["open_threads"][0]["type"] == "follow_up"
        assert call_kwargs["open_threads"][0]["content"] == "Ask about the work deadline"

    @pytest.mark.asyncio
    async def test_extraction_parses_resolved_thread_ids(
        self, mock_session: AsyncMock, mock_conversation: MagicMock
    ):
        """Test that resolved_thread_ids from LLM are parsed and returned."""
        from nikita.context.post_processor import PostProcessor

        processor = PostProcessor(mock_session)

        thread_id_1 = uuid4()
        thread_id_2 = uuid4()

        metaprompt_result = {
            "user_facts": [],
            "threads": [],
            "resolved_thread_ids": [str(thread_id_1), str(thread_id_2)],
            "emotional_markers": [],
            "nikita_thoughts": [],
            "summary": "Multiple threads were resolved.",
        }

        with patch("nikita.meta_prompts.MetaPromptService") as mock_mps_class:
            mock_mps = MagicMock()
            mock_mps.extract_entities = AsyncMock(return_value=metaprompt_result)
            mock_mps_class.return_value = mock_mps

            with patch.object(processor._thread_repo, "get_open_threads", return_value=[]):
                result = await processor._stage_extraction(mock_conversation)

        # Verify resolved_threads contains the UUIDs
        assert len(result.resolved_threads) == 2
        assert thread_id_1 in result.resolved_threads
        assert thread_id_2 in result.resolved_threads

    @pytest.mark.asyncio
    async def test_extraction_handles_invalid_thread_ids_gracefully(
        self, mock_session: AsyncMock, mock_conversation: MagicMock
    ):
        """Test that invalid UUID strings in resolved_thread_ids are skipped."""
        from nikita.context.post_processor import PostProcessor

        processor = PostProcessor(mock_session)

        valid_id = uuid4()

        metaprompt_result = {
            "user_facts": [],
            "threads": [],
            "resolved_thread_ids": [
                str(valid_id),
                "not-a-valid-uuid",  # Invalid
                "",  # Empty string
                None,  # None value
            ],
            "emotional_markers": [],
            "nikita_thoughts": [],
            "summary": "Test summary.",
        }

        with patch("nikita.meta_prompts.MetaPromptService") as mock_mps_class:
            mock_mps = MagicMock()
            mock_mps.extract_entities = AsyncMock(return_value=metaprompt_result)
            mock_mps_class.return_value = mock_mps

            with patch.object(processor._thread_repo, "get_open_threads", return_value=[]):
                result = await processor._stage_extraction(mock_conversation)

        # Should only have the valid UUID
        assert len(result.resolved_threads) == 1
        assert valid_id in result.resolved_threads
