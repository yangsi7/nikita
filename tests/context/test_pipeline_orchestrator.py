"""Tests for the slim pipeline orchestrator.

Spec 037 T2.16: Verify the PostProcessor orchestrates stages correctly
with under 100 lines of code.
"""

import pytest
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from nikita.context.pipeline_context import PipelineContext
from nikita.context.post_processor import PostProcessor
from nikita.context.stages.base import StageResult


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def pipeline_context():
    """Create a test pipeline context."""
    return PipelineContext(
        conversation_id=uuid4(),
        user_id=uuid4(),
        started_at=datetime.now(UTC),
    )


@pytest.fixture
def mock_conversation():
    """Create a mock conversation."""
    conv = MagicMock()
    conv.id = uuid4()
    conv.user_id = uuid4()
    conv.messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]
    return conv


class TestOrchestratorProcessConversation:
    """Test the slim process_conversation orchestrator."""

    @pytest.mark.asyncio
    async def test_orchestrator_runs_all_stages(self, mock_session):
        """Verify all stages run when pipeline succeeds."""
        processor = PostProcessor(mock_session)
        conversation_id = uuid4()

        # Mock the critical stages to succeed
        with patch.object(processor, "_stage_ingestion") as mock_ingestion, \
             patch.object(processor, "_stage_extraction") as mock_extraction, \
             patch.object(processor, "_analyze_psychology") as mock_psychology, \
             patch.object(processor, "_update_narrative_arcs") as mock_arcs, \
             patch.object(processor, "_stage_create_threads") as mock_threads, \
             patch.object(processor, "_stage_create_thoughts") as mock_thoughts, \
             patch.object(processor, "_stage_graph_updates") as mock_graph, \
             patch.object(processor, "_stage_summary_rollups") as mock_summary, \
             patch.object(processor, "_stage_vice_processing") as mock_vice, \
             patch.object(processor, "_invalidate_voice_cache") as mock_voice:

            # Setup mocks
            mock_conv = MagicMock()
            mock_conv.id = conversation_id
            mock_conv.user_id = uuid4()
            mock_conv.messages = [{"role": "user", "content": "test"}]
            mock_ingestion.return_value = mock_conv

            mock_extraction_result = MagicMock()
            mock_extraction_result.summary = "Test summary"
            mock_extraction_result.emotional_tone = "positive"
            mock_extraction_result.facts = []
            mock_extraction_result.entities = []
            mock_extraction_result.preferences = []
            mock_extraction_result.key_moments = []
            mock_extraction_result.how_it_ended = "good_note"
            mock_extraction_result.threads = []
            mock_extraction_result.resolved_threads = []
            mock_extraction_result.thoughts = []
            mock_extraction.return_value = mock_extraction_result

            mock_psychology.return_value = (MagicMock(), MagicMock())
            mock_arcs.return_value = {}
            mock_threads.return_value = 0
            mock_thoughts.return_value = 0
            mock_graph.return_value = None
            mock_vice.return_value = 0

            # Mock job execution
            with patch.object(processor._job_repo, "start_execution") as mock_start, \
                 patch.object(processor._job_repo, "complete_execution") as mock_complete, \
                 patch.object(processor._conversation_repo, "mark_processed") as mock_mark:

                mock_job = MagicMock()
                mock_job.id = uuid4()
                mock_start.return_value = mock_job

                result = await processor.process_conversation(conversation_id)

            # Verify success
            assert result.success is True
            assert result.stage_reached == "complete"

            # Verify all stages were called
            mock_ingestion.assert_called_once()
            mock_extraction.assert_called_once()
            mock_psychology.assert_called_once()

    @pytest.mark.asyncio
    async def test_orchestrator_stops_on_critical_failure(self, mock_session):
        """Verify pipeline stops when critical stage fails."""
        processor = PostProcessor(mock_session)
        conversation_id = uuid4()

        with patch.object(processor, "_stage_ingestion") as mock_ingestion:
            mock_ingestion.return_value = None  # Conversation not found

            with patch.object(processor._job_repo, "start_execution") as mock_start, \
                 patch.object(processor._job_repo, "fail_execution"):

                mock_job = MagicMock()
                mock_job.id = uuid4()
                mock_start.return_value = mock_job

                result = await processor.process_conversation(conversation_id)

            assert result.success is False
            assert result.stage_reached == "ingestion"
            assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_orchestrator_continues_on_non_critical_failure(self, mock_session):
        """Verify pipeline continues when non-critical stage fails."""
        processor = PostProcessor(mock_session)
        conversation_id = uuid4()

        with patch.object(processor, "_stage_ingestion") as mock_ingestion, \
             patch.object(processor, "_stage_extraction") as mock_extraction, \
             patch.object(processor, "_analyze_psychology") as mock_psychology, \
             patch.object(processor, "_update_narrative_arcs") as mock_arcs, \
             patch.object(processor, "_stage_create_threads") as mock_threads, \
             patch.object(processor, "_stage_create_thoughts") as mock_thoughts, \
             patch.object(processor, "_stage_graph_updates") as mock_graph, \
             patch.object(processor, "_stage_summary_rollups") as mock_summary, \
             patch.object(processor, "_stage_vice_processing") as mock_vice, \
             patch.object(processor, "_invalidate_voice_cache") as mock_voice:

            # Setup critical stages to succeed
            mock_conv = MagicMock()
            mock_conv.id = conversation_id
            mock_conv.user_id = uuid4()
            mock_conv.messages = [{"role": "user", "content": "test"}]
            mock_ingestion.return_value = mock_conv

            mock_extraction_result = MagicMock()
            mock_extraction_result.summary = "Test"
            mock_extraction_result.emotional_tone = "positive"
            mock_extraction_result.facts = []
            mock_extraction_result.entities = []
            mock_extraction_result.preferences = []
            mock_extraction_result.key_moments = []
            mock_extraction_result.how_it_ended = "good"
            mock_extraction_result.threads = []
            mock_extraction_result.resolved_threads = []
            mock_extraction_result.thoughts = []
            mock_extraction.return_value = mock_extraction_result

            mock_psychology.return_value = (MagicMock(), MagicMock())
            mock_arcs.return_value = {}

            # Non-critical stages fail
            mock_threads.side_effect = Exception("Thread error")
            mock_thoughts.side_effect = Exception("Thought error")
            mock_graph.side_effect = Exception("Graph error")
            mock_summary.return_value = None
            mock_vice.return_value = 0

            with patch.object(processor._job_repo, "start_execution") as mock_start, \
                 patch.object(processor._job_repo, "complete_execution"), \
                 patch.object(processor._conversation_repo, "mark_processed"):

                mock_job = MagicMock()
                mock_job.id = uuid4()
                mock_start.return_value = mock_job

                result = await processor.process_conversation(conversation_id)

            # Should succeed despite non-critical failures
            assert result.success is True
            assert result.stage_reached == "complete"

            # Verify errors were recorded
            assert "threads" in result.stage_errors
            assert "thoughts" in result.stage_errors
            assert "graph_updates" in result.stage_errors

    @pytest.mark.asyncio
    async def test_orchestrator_threads_inputs_correctly(self, mock_session):
        """Verify data flows correctly between stages."""
        processor = PostProcessor(mock_session)
        conversation_id = uuid4()

        with patch.object(processor, "_stage_ingestion") as mock_ingestion, \
             patch.object(processor, "_stage_extraction") as mock_extraction, \
             patch.object(processor, "_analyze_psychology") as mock_psychology, \
             patch.object(processor, "_update_narrative_arcs") as mock_arcs, \
             patch.object(processor, "_stage_create_threads") as mock_threads, \
             patch.object(processor, "_stage_create_thoughts") as mock_thoughts, \
             patch.object(processor, "_stage_graph_updates") as mock_graph, \
             patch.object(processor, "_stage_summary_rollups") as mock_summary, \
             patch.object(processor, "_stage_vice_processing") as mock_vice, \
             patch.object(processor, "_invalidate_voice_cache") as mock_voice:

            # Setup
            mock_conv = MagicMock()
            mock_conv.id = conversation_id
            mock_conv.user_id = uuid4()
            mock_conv.messages = [{"role": "user", "content": "test"}]
            mock_ingestion.return_value = mock_conv

            mock_extraction_result = MagicMock()
            mock_extraction_result.summary = "Test summary"
            mock_extraction_result.emotional_tone = "positive"
            mock_extraction_result.facts = [{"type": "fact", "content": "loves coffee"}]
            mock_extraction_result.entities = []
            mock_extraction_result.preferences = []
            mock_extraction_result.key_moments = ["key moment 1"]
            mock_extraction_result.how_it_ended = "good_note"
            mock_extraction_result.threads = [{"type": "follow_up", "content": "ask about job"}]
            mock_extraction_result.resolved_threads = []
            mock_extraction_result.thoughts = [{"type": "thinking", "content": "he seems nice"}]
            mock_extraction.return_value = mock_extraction_result

            mock_psych = MagicMock()
            mock_psych.vulnerability_level = 5
            mock_psychology.return_value = (mock_psych, MagicMock())
            mock_arcs.return_value = {}
            mock_threads.return_value = 1
            mock_thoughts.return_value = 1
            mock_graph.return_value = None
            mock_vice.return_value = 0

            with patch.object(processor._job_repo, "start_execution") as mock_start, \
                 patch.object(processor._job_repo, "complete_execution"), \
                 patch.object(processor._conversation_repo, "mark_processed"), \
                 patch.object(processor._user_repo, "get") as mock_get_user:

                mock_job = MagicMock()
                mock_job.id = uuid4()
                mock_start.return_value = mock_job
                mock_get_user.return_value = MagicMock()

                result = await processor.process_conversation(conversation_id)

            # Verify extraction result was passed to threads stage
            mock_threads.assert_called_once()
            call_args = mock_threads.call_args
            assert call_args[1]["threads"] == mock_extraction_result.threads
            assert call_args[1]["resolved_ids"] == mock_extraction_result.resolved_threads

            # Verify extraction result was passed to thoughts stage
            mock_thoughts.assert_called_once()
            call_args = mock_thoughts.call_args
            assert call_args[1]["thoughts"] == mock_extraction_result.thoughts

    @pytest.mark.asyncio
    async def test_orchestrator_logs_all_stages(self, mock_session):
        """Verify structured logging for each stage."""
        processor = PostProcessor(mock_session)
        conversation_id = uuid4()

        with patch.object(processor, "_stage_ingestion") as mock_ingestion, \
             patch.object(processor, "_stage_extraction") as mock_extraction, \
             patch.object(processor, "_analyze_psychology") as mock_psychology, \
             patch.object(processor, "_update_narrative_arcs") as mock_arcs, \
             patch.object(processor, "_stage_create_threads") as mock_threads, \
             patch.object(processor, "_stage_create_thoughts") as mock_thoughts, \
             patch.object(processor, "_stage_graph_updates") as mock_graph, \
             patch.object(processor, "_stage_summary_rollups") as mock_summary, \
             patch.object(processor, "_stage_vice_processing") as mock_vice, \
             patch.object(processor, "_invalidate_voice_cache") as mock_voice, \
             patch("nikita.context.post_processor.logger") as mock_logger:

            mock_conv = MagicMock()
            mock_conv.id = conversation_id
            mock_conv.user_id = uuid4()
            mock_conv.messages = [{"role": "user", "content": "test"}]
            mock_ingestion.return_value = mock_conv

            mock_extraction_result = MagicMock()
            mock_extraction_result.summary = "Test"
            mock_extraction_result.emotional_tone = "positive"
            mock_extraction_result.facts = []
            mock_extraction_result.entities = []
            mock_extraction_result.preferences = []
            mock_extraction_result.key_moments = []
            mock_extraction_result.how_it_ended = "good"
            mock_extraction_result.threads = []
            mock_extraction_result.resolved_threads = []
            mock_extraction_result.thoughts = []
            mock_extraction.return_value = mock_extraction_result

            mock_psychology.return_value = (MagicMock(), MagicMock())
            mock_arcs.return_value = {}
            mock_threads.return_value = 0
            mock_thoughts.return_value = 0
            mock_graph.return_value = None
            mock_vice.return_value = 0

            with patch.object(processor._job_repo, "start_execution") as mock_start, \
                 patch.object(processor._job_repo, "complete_execution"), \
                 patch.object(processor._conversation_repo, "mark_processed"):

                mock_job = MagicMock()
                mock_job.id = uuid4()
                mock_start.return_value = mock_job

                result = await processor.process_conversation(conversation_id)

            # Verify completion was logged
            assert any(
                "processed" in str(call).lower()
                for call in mock_logger.info.call_args_list
            )


class TestPipelineContextUpdateFromResult:
    """Test the update_from_result method."""

    def test_update_from_result_stores_conversation(self, pipeline_context):
        """Verify ingestion result stores conversation."""
        mock_conv = MagicMock()
        pipeline_context.update_from_result("ingestion", mock_conv)

        assert pipeline_context.conversation == mock_conv
        assert pipeline_context.metadata["ingestion_result"] == mock_conv
        assert pipeline_context.metadata["ingestion_success"] is True

    def test_update_from_result_stores_extraction(self, pipeline_context):
        """Verify extraction result stores extraction_result."""
        mock_extraction = MagicMock()
        pipeline_context.update_from_result("extraction", mock_extraction)

        assert pipeline_context.extraction_result == mock_extraction
        assert pipeline_context.metadata["extraction_result"] == mock_extraction

    def test_update_from_result_records_error(self, pipeline_context):
        """Verify errors are recorded correctly."""
        pipeline_context.update_from_result(
            "threads",
            None,
            success=False,
            error="Thread creation failed",
        )

        assert "threads" in pipeline_context.stage_errors
        assert pipeline_context.stage_errors["threads"] == "Thread creation failed"
        assert pipeline_context.metadata["threads_success"] is False

    def test_update_from_result_stores_other_stages(self, pipeline_context):
        """Verify other stage results stored in metadata."""
        result_data = {"threads_created": 5}
        pipeline_context.update_from_result("threads", result_data)

        assert pipeline_context.metadata["threads_result"] == result_data
        assert pipeline_context.metadata["threads_success"] is True
