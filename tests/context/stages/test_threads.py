"""Tests for ThreadsStage.

Verifies Stage 4 (thread creation) functionality:
- Resolving existing threads
- Creating new threads with valid types
- Filtering invalid thread types
- Handling empty input
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.context.pipeline_context import PipelineContext
from nikita.context.stages.threads import ThreadsInput, ThreadsStage


# Correct patch path for repository imported in __init__
REPO_PATCH_PATH = "nikita.db.repositories.thread_repository.ConversationThreadRepository"


@pytest.fixture
def mock_session():
    """Create mock database session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def mock_logger():
    """Create mock structlog logger."""
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    logger.info = MagicMock()
    logger.debug = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    return logger


@pytest.fixture
def pipeline_context():
    """Create test pipeline context."""
    return PipelineContext(
        conversation_id=uuid4(),
        user_id=uuid4(),
        started_at=datetime.now(UTC),
    )


@pytest.fixture
def mock_conversation():
    """Create mock conversation."""
    conv = MagicMock()
    conv.id = uuid4()
    conv.user_id = uuid4()
    return conv


class TestThreadsStageProperties:
    """Test stage property configuration."""

    def test_stage_name(self, mock_session, mock_logger):
        """Verify stage name is 'threads'."""
        with patch(REPO_PATCH_PATH):
            stage = ThreadsStage(mock_session, mock_logger)
            assert stage.name == "threads"

    def test_is_not_critical(self, mock_session, mock_logger):
        """Verify stage is non-critical."""
        with patch(REPO_PATCH_PATH):
            stage = ThreadsStage(mock_session, mock_logger)
            assert stage.is_critical is False

    def test_timeout_seconds(self, mock_session, mock_logger):
        """Verify timeout is 10 seconds."""
        with patch(REPO_PATCH_PATH):
            stage = ThreadsStage(mock_session, mock_logger)
            assert stage.timeout_seconds == 10.0


class TestThreadsStageCreation:
    """Test thread creation functionality."""

    @pytest.mark.asyncio
    async def test_creates_valid_threads(
        self, mock_session, mock_logger, pipeline_context, mock_conversation
    ):
        """Verify threads with valid types are created."""
        with patch(REPO_PATCH_PATH) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.bulk_create_threads = AsyncMock()
            mock_repo_cls.return_value = mock_repo

            stage = ThreadsStage(mock_session, mock_logger)

            threads = [
                {"type": "follow_up", "content": "We should talk about this more"},
                {"type": "question", "content": "What do you think about X?"},
            ]

            input_data = ThreadsInput(
                conversation=mock_conversation,
                threads=threads,
                resolved_ids=[],
            )

            with patch("nikita.db.models.context.THREAD_TYPES", {"follow_up", "question", "promise", "topic"}):
                result = await stage._run(pipeline_context, input_data)

            assert result == 2
            mock_repo.bulk_create_threads.assert_called_once()
            call_kwargs = mock_repo.bulk_create_threads.call_args.kwargs
            assert len(call_kwargs["threads_data"]) == 2

    @pytest.mark.asyncio
    async def test_filters_invalid_thread_types(
        self, mock_session, mock_logger, pipeline_context, mock_conversation
    ):
        """Verify invalid thread types are filtered out."""
        with patch(REPO_PATCH_PATH) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.bulk_create_threads = AsyncMock()
            mock_repo_cls.return_value = mock_repo

            stage = ThreadsStage(mock_session, mock_logger)

            threads = [
                {"type": "follow_up", "content": "Valid thread"},
                {"type": "invalid_type", "content": "Should be filtered"},
                {"type": "question", "content": "Another valid thread"},
            ]

            input_data = ThreadsInput(
                conversation=mock_conversation,
                threads=threads,
                resolved_ids=[],
            )

            with patch("nikita.db.models.context.THREAD_TYPES", {"follow_up", "question", "promise", "topic"}):
                result = await stage._run(pipeline_context, input_data)

            assert result == 2
            call_kwargs = mock_repo.bulk_create_threads.call_args.kwargs
            thread_types = [t["thread_type"] for t in call_kwargs["threads_data"]]
            assert "invalid_type" not in thread_types

    @pytest.mark.asyncio
    async def test_handles_empty_threads(
        self, mock_session, mock_logger, pipeline_context, mock_conversation
    ):
        """Verify returns 0 when no valid threads."""
        with patch(REPO_PATCH_PATH) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.bulk_create_threads = AsyncMock()
            mock_repo_cls.return_value = mock_repo

            stage = ThreadsStage(mock_session, mock_logger)

            input_data = ThreadsInput(
                conversation=mock_conversation,
                threads=[],
                resolved_ids=[],
            )

            with patch("nikita.db.models.context.THREAD_TYPES", {"follow_up", "question", "promise", "topic"}):
                result = await stage._run(pipeline_context, input_data)

            assert result == 0
            mock_repo.bulk_create_threads.assert_not_called()


class TestThreadResolution:
    """Test thread resolution functionality."""

    @pytest.mark.asyncio
    async def test_resolves_existing_threads(
        self, mock_session, mock_logger, pipeline_context, mock_conversation
    ):
        """Verify existing threads are resolved."""
        with patch(REPO_PATCH_PATH) as mock_repo_cls:
            mock_repo = AsyncMock()
            # Mock get returns a thread for age calculation
            mock_thread = MagicMock()
            mock_thread.created_at = datetime.now(UTC)
            mock_thread.thread_type = "follow_up"
            mock_repo.get = AsyncMock(return_value=mock_thread)
            mock_repo.resolve_thread = AsyncMock()
            mock_repo.bulk_create_threads = AsyncMock()
            mock_repo_cls.return_value = mock_repo

            stage = ThreadsStage(mock_session, mock_logger)

            thread_ids = [uuid4(), uuid4()]
            input_data = ThreadsInput(
                conversation=mock_conversation,
                threads=[],
                resolved_ids=thread_ids,
            )

            with patch("nikita.db.models.context.THREAD_TYPES", {"follow_up", "question", "promise", "topic"}):
                await stage._run(pipeline_context, input_data)

            assert mock_repo.resolve_thread.call_count == 2

    @pytest.mark.asyncio
    async def test_handles_resolution_errors(
        self, mock_session, mock_logger, pipeline_context, mock_conversation
    ):
        """Verify resolution errors are handled gracefully."""
        with patch(REPO_PATCH_PATH) as mock_repo_cls:
            mock_repo = AsyncMock()
            # Mock get returns a thread, then resolve raises ValueError
            mock_thread = MagicMock()
            mock_thread.created_at = datetime.now(UTC)
            mock_thread.thread_type = "follow_up"
            mock_repo.get = AsyncMock(return_value=mock_thread)
            mock_repo.resolve_thread = AsyncMock(
                side_effect=[None, ValueError("Thread not found")]
            )
            mock_repo.bulk_create_threads = AsyncMock()
            mock_repo_cls.return_value = mock_repo

            stage = ThreadsStage(mock_session, mock_logger)

            thread_ids = [uuid4(), uuid4()]
            input_data = ThreadsInput(
                conversation=mock_conversation,
                threads=[],
                resolved_ids=thread_ids,
            )

            with patch("nikita.db.models.context.THREAD_TYPES", {"follow_up", "question", "promise", "topic"}):
                # Should not raise, should continue
                result = await stage._run(pipeline_context, input_data)

            assert result == 0  # No threads created
            assert mock_repo.resolve_thread.call_count == 2


class TestThreadResolutionLogging:
    """Test enhanced thread resolution logging (T3.3)."""

    @pytest.mark.asyncio
    async def test_logs_resolution_with_reason_and_time(
        self, mock_session, mock_logger, pipeline_context, mock_conversation
    ):
        """Verify thread_resolved logs include resolution_reason and resolution_time_ms."""
        with patch(REPO_PATCH_PATH) as mock_repo_cls:
            mock_repo = AsyncMock()
            # Mock thread with created_at for age calculation
            mock_thread = MagicMock()
            mock_thread.created_at = datetime.now(UTC)
            mock_thread.thread_type = "follow_up"
            mock_repo.get = AsyncMock(return_value=mock_thread)
            mock_repo.resolve_thread = AsyncMock()
            mock_repo.bulk_create_threads = AsyncMock()
            mock_repo_cls.return_value = mock_repo

            stage = ThreadsStage(mock_session, mock_logger)

            thread_id = uuid4()
            input_data = ThreadsInput(
                conversation=mock_conversation,
                threads=[],
                resolved_ids=[thread_id],
            )

            with patch("nikita.db.models.context.THREAD_TYPES", {"follow_up", "question", "promise", "topic"}):
                await stage._run(pipeline_context, input_data)

            # Find the thread_resolved log call
            resolved_calls = [
                call for call in mock_logger.info.call_args_list
                if call[0][0] == "thread_resolved"
            ]
            assert len(resolved_calls) == 1

            log_kwargs = resolved_calls[0][1]
            assert log_kwargs["resolution_reason"] == "user_addressed"
            assert "resolution_time_ms" in log_kwargs
            assert log_kwargs["resolution_time_ms"] >= 0
            assert log_kwargs["thread_type"] == "follow_up"

    @pytest.mark.asyncio
    async def test_logs_thread_age_in_hours(
        self, mock_session, mock_logger, pipeline_context, mock_conversation
    ):
        """Verify thread_resolved logs include thread_age_hours."""
        from datetime import timedelta

        with patch(REPO_PATCH_PATH) as mock_repo_cls:
            mock_repo = AsyncMock()
            # Mock thread created 2 hours ago
            mock_thread = MagicMock()
            mock_thread.created_at = datetime.now(UTC) - timedelta(hours=2)
            mock_thread.thread_type = "question"
            mock_repo.get = AsyncMock(return_value=mock_thread)
            mock_repo.resolve_thread = AsyncMock()
            mock_repo.bulk_create_threads = AsyncMock()
            mock_repo_cls.return_value = mock_repo

            stage = ThreadsStage(mock_session, mock_logger)

            thread_id = uuid4()
            input_data = ThreadsInput(
                conversation=mock_conversation,
                threads=[],
                resolved_ids=[thread_id],
            )

            with patch("nikita.db.models.context.THREAD_TYPES", {"follow_up", "question", "promise", "topic"}):
                await stage._run(pipeline_context, input_data)

            resolved_calls = [
                call for call in mock_logger.info.call_args_list
                if call[0][0] == "thread_resolved"
            ]
            assert len(resolved_calls) == 1

            log_kwargs = resolved_calls[0][1]
            assert "thread_age_hours" in log_kwargs
            # Should be approximately 2 hours (allow some tolerance)
            assert 1.9 <= log_kwargs["thread_age_hours"] <= 2.1

    @pytest.mark.asyncio
    async def test_logs_skipped_for_not_found_thread(
        self, mock_session, mock_logger, pipeline_context, mock_conversation
    ):
        """Verify thread_resolve_skipped logs when thread not found."""
        with patch(REPO_PATCH_PATH) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get = AsyncMock(return_value=None)  # Thread not found
            mock_repo.bulk_create_threads = AsyncMock()
            mock_repo_cls.return_value = mock_repo

            stage = ThreadsStage(mock_session, mock_logger)

            thread_id = uuid4()
            input_data = ThreadsInput(
                conversation=mock_conversation,
                threads=[],
                resolved_ids=[thread_id],
            )

            with patch("nikita.db.models.context.THREAD_TYPES", {"follow_up", "question", "promise", "topic"}):
                await stage._run(pipeline_context, input_data)

            skipped_calls = [
                call for call in mock_logger.info.call_args_list
                if call[0][0] == "thread_resolve_skipped"
            ]
            assert len(skipped_calls) == 1

            log_kwargs = skipped_calls[0][1]
            assert log_kwargs["resolution_reason"] == "not_found"

    @pytest.mark.asyncio
    async def test_logs_failure_with_error_details(
        self, mock_session, mock_logger, pipeline_context, mock_conversation
    ):
        """Verify thread_resolve_failed logs include error details."""
        with patch(REPO_PATCH_PATH) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_thread = MagicMock()
            mock_thread.created_at = datetime.now(UTC)
            mock_thread.thread_type = "follow_up"
            mock_repo.get = AsyncMock(return_value=mock_thread)
            mock_repo.resolve_thread = AsyncMock(
                side_effect=Exception("Database connection error")
            )
            mock_repo.bulk_create_threads = AsyncMock()
            mock_repo_cls.return_value = mock_repo

            stage = ThreadsStage(mock_session, mock_logger)

            thread_id = uuid4()
            input_data = ThreadsInput(
                conversation=mock_conversation,
                threads=[],
                resolved_ids=[thread_id],
            )

            with patch("nikita.db.models.context.THREAD_TYPES", {"follow_up", "question", "promise", "topic"}):
                await stage._run(pipeline_context, input_data)

            failed_calls = [
                call for call in mock_logger.warning.call_args_list
                if call[0][0] == "thread_resolve_failed"
            ]
            assert len(failed_calls) == 1

            log_kwargs = failed_calls[0][1]
            assert log_kwargs["resolution_reason"] == "error"
            assert "Database connection error" in log_kwargs["error"]
            assert log_kwargs["exc_info"] is True
