"""Integration tests for the post-processing pipeline.

Spec 037 T5.2: Full pipeline E2E tests verifying stage isolation,
data flow, and performance characteristics.
"""

import asyncio
import time
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.context.pipeline_context import PipelineContext
from nikita.context.post_processor import PostProcessor


@pytest.fixture
def mock_session():
    """Create mock database session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def mock_conversation():
    """Create mock conversation with messages."""
    conv = MagicMock()
    conv.id = uuid4()
    conv.user_id = uuid4()
    conv.messages = [
        {"role": "user", "content": "Hey Nikita, how are you?"},
        {"role": "assistant", "content": "I'm doing great! Just thinking about you."},
        {"role": "user", "content": "That's sweet. I had a busy day at work."},
        {"role": "assistant", "content": "Tell me about it, babe. What happened?"},
    ]
    return conv


@pytest.fixture
def mock_extraction_result():
    """Create mock extraction result."""
    result = MagicMock()
    result.summary = "User shared about their busy day at work"
    result.emotional_tone = "positive"
    result.facts = [{"type": "work", "content": "User had a busy day"}]
    result.entities = []
    result.preferences = []
    result.key_moments = ["User opened up about work"]
    result.how_it_ended = "good_note"
    result.threads = [{"type": "follow_up", "content": "Ask about work details"}]
    result.resolved_threads = []
    result.thoughts = [{"type": "thinking", "content": "He seems stressed"}]
    return result


class TestPipelineIntegration:
    """Integration tests for pipeline behavior."""

    @pytest.mark.asyncio
    async def test_full_pipeline_success(
        self, mock_session, mock_conversation, mock_extraction_result
    ):
        """Verify all stages complete successfully in sequence."""
        processor = PostProcessor(mock_session)
        conversation_id = mock_conversation.id

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

            mock_ingestion.return_value = mock_conversation
            mock_extraction.return_value = mock_extraction_result
            mock_psychology.return_value = (MagicMock(), MagicMock())
            mock_arcs.return_value = {}
            mock_threads.return_value = 1
            mock_thoughts.return_value = 1
            mock_graph.return_value = None
            mock_summary.return_value = None
            mock_vice.return_value = 0

            with patch.object(processor._job_repo, "start_execution") as mock_start, \
                 patch.object(processor._job_repo, "complete_execution"), \
                 patch.object(processor._conversation_repo, "mark_processed"):

                mock_job = MagicMock()
                mock_job.id = uuid4()
                mock_start.return_value = mock_job

                result = await processor.process_conversation(conversation_id)

            assert result.success is True
            assert result.stage_reached == "complete"
            assert result.error is None

    @pytest.mark.asyncio
    async def test_pipeline_isolation_non_critical_failures(
        self, mock_session, mock_conversation, mock_extraction_result
    ):
        """Verify non-critical stage failures don't affect other stages."""
        processor = PostProcessor(mock_session)
        conversation_id = mock_conversation.id

        stages_called = []

        def track_stage(stage_name):
            async def wrapper(*args, **kwargs):
                stages_called.append(stage_name)
                if stage_name in ["threads", "graph_updates"]:
                    raise Exception(f"{stage_name} failed")
                return 0
            return wrapper

        with patch.object(processor, "_stage_ingestion") as mock_ingestion, \
             patch.object(processor, "_stage_extraction") as mock_extraction, \
             patch.object(processor, "_analyze_psychology") as mock_psychology, \
             patch.object(processor, "_update_narrative_arcs") as mock_arcs, \
             patch.object(processor, "_stage_create_threads", side_effect=track_stage("threads")), \
             patch.object(processor, "_stage_create_thoughts", side_effect=track_stage("thoughts")), \
             patch.object(processor, "_stage_graph_updates", side_effect=track_stage("graph_updates")), \
             patch.object(processor, "_stage_summary_rollups", side_effect=track_stage("summary")), \
             patch.object(processor, "_stage_vice_processing", side_effect=track_stage("vice")), \
             patch.object(processor, "_invalidate_voice_cache", side_effect=track_stage("voice_cache")):

            mock_ingestion.return_value = mock_conversation
            mock_extraction.return_value = mock_extraction_result
            # Psychology returns tuple of (insight, health)
            mock_psychology.return_value = (MagicMock(), MagicMock())
            mock_arcs.return_value = {}

            with patch.object(processor._job_repo, "start_execution") as mock_start, \
                 patch.object(processor._job_repo, "complete_execution"), \
                 patch.object(processor._conversation_repo, "mark_processed"):

                mock_job = MagicMock()
                mock_job.id = uuid4()
                mock_start.return_value = mock_job

                result = await processor.process_conversation(conversation_id)

            # Pipeline should complete despite non-critical failures
            assert result.success is True
            assert result.stage_reached == "complete"

            # Errors should be recorded
            assert "threads" in result.stage_errors
            assert "graph_updates" in result.stage_errors

            # Non-critical stages should have been attempted
            assert "threads" in stages_called
            assert "graph_updates" in stages_called

    @pytest.mark.asyncio
    async def test_pipeline_critical_stage_stops_execution(
        self, mock_session, mock_conversation
    ):
        """Verify critical stage failure stops pipeline and marks as failed."""
        processor = PostProcessor(mock_session)
        conversation_id = mock_conversation.id

        with patch.object(processor, "_stage_ingestion") as mock_ingestion:
            # Ingestion is critical - failure should stop pipeline early
            mock_ingestion.return_value = None  # Conversation not found

            with patch.object(processor._job_repo, "start_execution") as mock_start, \
                 patch.object(processor._job_repo, "fail_execution") as mock_fail:

                mock_job = MagicMock()
                mock_job.id = uuid4()
                mock_start.return_value = mock_job

                result = await processor.process_conversation(conversation_id)

            # Pipeline should fail
            assert result.success is False
            assert result.stage_reached == "ingestion"
            assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_pipeline_data_flow_between_stages(
        self, mock_session, mock_conversation, mock_extraction_result
    ):
        """Verify data flows correctly between dependent stages."""
        processor = PostProcessor(mock_session)
        conversation_id = mock_conversation.id

        captured_thread_input = None
        captured_thought_input = None

        async def capture_threads(**kwargs):
            nonlocal captured_thread_input
            captured_thread_input = kwargs
            return 1

        async def capture_thoughts(**kwargs):
            nonlocal captured_thought_input
            captured_thought_input = kwargs
            return 1

        with patch.object(processor, "_stage_ingestion") as mock_ingestion, \
             patch.object(processor, "_stage_extraction") as mock_extraction, \
             patch.object(processor, "_analyze_psychology") as mock_psychology, \
             patch.object(processor, "_update_narrative_arcs") as mock_arcs, \
             patch.object(processor, "_stage_create_threads", side_effect=capture_threads), \
             patch.object(processor, "_stage_create_thoughts", side_effect=capture_thoughts), \
             patch.object(processor, "_stage_graph_updates") as mock_graph, \
             patch.object(processor, "_stage_summary_rollups") as mock_summary, \
             patch.object(processor, "_stage_vice_processing") as mock_vice, \
             patch.object(processor, "_invalidate_voice_cache") as mock_voice:

            mock_ingestion.return_value = mock_conversation
            mock_extraction.return_value = mock_extraction_result
            mock_psychology.return_value = (MagicMock(), MagicMock())
            mock_arcs.return_value = {}
            mock_graph.return_value = None
            mock_summary.return_value = None
            mock_vice.return_value = 0

            with patch.object(processor._job_repo, "start_execution") as mock_start, \
                 patch.object(processor._job_repo, "complete_execution"), \
                 patch.object(processor._conversation_repo, "mark_processed"):

                mock_job = MagicMock()
                mock_job.id = uuid4()
                mock_start.return_value = mock_job

                await processor.process_conversation(conversation_id)

            # Verify threads stage received extraction data
            assert captured_thread_input is not None
            assert captured_thread_input["threads"] == mock_extraction_result.threads
            assert captured_thread_input["resolved_ids"] == mock_extraction_result.resolved_threads

            # Verify thoughts stage received extraction data
            assert captured_thought_input is not None
            assert captured_thought_input["thoughts"] == mock_extraction_result.thoughts

    @pytest.mark.asyncio
    async def test_pipeline_performance_under_mock(
        self, mock_session, mock_conversation, mock_extraction_result
    ):
        """Verify pipeline completes quickly with mocked stages."""
        processor = PostProcessor(mock_session)
        conversation_id = mock_conversation.id

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

            mock_ingestion.return_value = mock_conversation
            mock_extraction.return_value = mock_extraction_result
            mock_psychology.return_value = (MagicMock(), MagicMock())
            mock_arcs.return_value = {}
            mock_threads.return_value = 0
            mock_thoughts.return_value = 0
            mock_graph.return_value = None
            mock_summary.return_value = None
            mock_vice.return_value = 0

            with patch.object(processor._job_repo, "start_execution") as mock_start, \
                 patch.object(processor._job_repo, "complete_execution"), \
                 patch.object(processor._conversation_repo, "mark_processed"):

                mock_job = MagicMock()
                mock_job.id = uuid4()
                mock_start.return_value = mock_job

                start_time = time.perf_counter()
                result = await processor.process_conversation(conversation_id)
                duration = time.perf_counter() - start_time

            assert result.success is True
            # With mocks, should complete in under 1 second
            assert duration < 1.0, f"Pipeline took {duration:.2f}s, expected <1s"

    @pytest.mark.asyncio
    async def test_pipeline_context_accumulates_stage_results(
        self, mock_session, mock_conversation, mock_extraction_result
    ):
        """Verify pipeline context tracks results from all stages."""
        processor = PostProcessor(mock_session)
        conversation_id = mock_conversation.id

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

            mock_ingestion.return_value = mock_conversation
            mock_extraction.return_value = mock_extraction_result
            mock_psychology.return_value = (MagicMock(), MagicMock())
            mock_arcs.return_value = {"arc_1": "active"}
            mock_threads.return_value = 2
            mock_thoughts.return_value = 1
            mock_graph.return_value = None
            mock_summary.return_value = None
            mock_vice.return_value = 3

            with patch.object(processor._job_repo, "start_execution") as mock_start, \
                 patch.object(processor._job_repo, "complete_execution"), \
                 patch.object(processor._conversation_repo, "mark_processed"):

                mock_job = MagicMock()
                mock_job.id = uuid4()
                mock_start.return_value = mock_job

                result = await processor.process_conversation(conversation_id)

            # Verify result contains stage counts
            assert result.success is True
            assert result.threads_created == 2
            assert result.thoughts_created == 1
            assert result.vice_signals_processed == 3


class TestPipelineContextIntegration:
    """Test PipelineContext integration with stages."""

    def test_context_preserves_conversation_reference(self):
        """Verify conversation is accessible throughout pipeline."""
        context = PipelineContext(
            conversation_id=uuid4(),
            user_id=uuid4(),
            started_at=datetime.now(UTC),
        )

        mock_conv = MagicMock()
        mock_conv.id = context.conversation_id
        context.update_from_result("ingestion", mock_conv)

        assert context.conversation is mock_conv
        assert context.metadata["ingestion_success"] is True

    def test_context_preserves_extraction_result(self):
        """Verify extraction result is accessible for downstream stages."""
        context = PipelineContext(
            conversation_id=uuid4(),
            user_id=uuid4(),
            started_at=datetime.now(UTC),
        )

        mock_extraction = MagicMock()
        mock_extraction.threads = [{"type": "follow_up", "content": "test"}]
        context.update_from_result("extraction", mock_extraction)

        assert context.extraction_result is mock_extraction
        assert context.extraction_result.threads == mock_extraction.threads

    def test_context_accumulates_errors(self):
        """Verify multiple stage errors are accumulated."""
        context = PipelineContext(
            conversation_id=uuid4(),
            user_id=uuid4(),
            started_at=datetime.now(UTC),
        )

        context.update_from_result("threads", None, success=False, error="Thread error")
        context.update_from_result("graph_updates", None, success=False, error="Graph error")

        assert len(context.stage_errors) == 2
        assert "threads" in context.stage_errors
        assert "graph_updates" in context.stage_errors
