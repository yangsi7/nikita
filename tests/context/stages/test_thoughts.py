"""Tests for ThoughtsStage.

Verifies Stage 5 (thought creation) functionality:
- Creating valid thoughts
- Filtering invalid thought types
- Handling empty input
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.context.pipeline_context import PipelineContext
from nikita.context.stages.thoughts import ThoughtsInput, ThoughtsStage


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


class TestThoughtsStageProperties:
    """Test stage property configuration."""

    def test_stage_name(self, mock_session, mock_logger):
        """Verify stage name is 'thoughts'."""
        with patch(
            "nikita.db.repositories.thought_repository.NikitaThoughtRepository"
        ):
            stage = ThoughtsStage(mock_session, mock_logger)
            assert stage.name == "thoughts"

    def test_is_not_critical(self, mock_session, mock_logger):
        """Verify stage is non-critical."""
        with patch(
            "nikita.db.repositories.thought_repository.NikitaThoughtRepository"
        ):
            stage = ThoughtsStage(mock_session, mock_logger)
            assert stage.is_critical is False

    def test_timeout_seconds(self, mock_session, mock_logger):
        """Verify timeout is 10 seconds."""
        with patch(
            "nikita.db.repositories.thought_repository.NikitaThoughtRepository"
        ):
            stage = ThoughtsStage(mock_session, mock_logger)
            assert stage.timeout_seconds == 10.0


class TestThoughtsStageCreation:
    """Test thought creation functionality."""

    @pytest.mark.asyncio
    async def test_creates_valid_thoughts(
        self, mock_session, mock_logger, pipeline_context, mock_conversation
    ):
        """Verify thoughts with valid types are created."""
        with patch(
            "nikita.db.repositories.thought_repository.NikitaThoughtRepository"
        ) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.bulk_create_thoughts = AsyncMock()
            mock_repo_cls.return_value = mock_repo

            stage = ThoughtsStage(mock_session, mock_logger)

            thoughts = [
                {"type": "reflection", "content": "That was an interesting conversation"},
                {"type": "anticipation", "content": "I wonder what they'll say next"},
            ]

            input_data = ThoughtsInput(
                conversation=mock_conversation,
                thoughts=thoughts,
            )

            with patch("nikita.db.models.context.THOUGHT_TYPES", {"reflection", "anticipation", "desire", "worry"}):
                result = await stage._run(pipeline_context, input_data)

            assert result == 2
            mock_repo.bulk_create_thoughts.assert_called_once()
            call_kwargs = mock_repo.bulk_create_thoughts.call_args.kwargs
            assert len(call_kwargs["thoughts_data"]) == 2

    @pytest.mark.asyncio
    async def test_filters_invalid_thought_types(
        self, mock_session, mock_logger, pipeline_context, mock_conversation
    ):
        """Verify invalid thought types are filtered out."""
        with patch(
            "nikita.db.repositories.thought_repository.NikitaThoughtRepository"
        ) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.bulk_create_thoughts = AsyncMock()
            mock_repo_cls.return_value = mock_repo

            stage = ThoughtsStage(mock_session, mock_logger)

            thoughts = [
                {"type": "reflection", "content": "Valid thought"},
                {"type": "invalid_type", "content": "Should be filtered"},
                {"type": "anticipation", "content": "Another valid thought"},
            ]

            input_data = ThoughtsInput(
                conversation=mock_conversation,
                thoughts=thoughts,
            )

            with patch("nikita.db.models.context.THOUGHT_TYPES", {"reflection", "anticipation", "desire", "worry"}):
                result = await stage._run(pipeline_context, input_data)

            assert result == 2
            call_kwargs = mock_repo.bulk_create_thoughts.call_args.kwargs
            thought_types = [t["thought_type"] for t in call_kwargs["thoughts_data"]]
            assert "invalid_type" not in thought_types

    @pytest.mark.asyncio
    async def test_handles_empty_thoughts(
        self, mock_session, mock_logger, pipeline_context, mock_conversation
    ):
        """Verify returns 0 when no valid thoughts."""
        with patch(
            "nikita.db.repositories.thought_repository.NikitaThoughtRepository"
        ) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.bulk_create_thoughts = AsyncMock()
            mock_repo_cls.return_value = mock_repo

            stage = ThoughtsStage(mock_session, mock_logger)

            input_data = ThoughtsInput(
                conversation=mock_conversation,
                thoughts=[],
            )

            with patch("nikita.db.models.context.THOUGHT_TYPES", {"reflection", "anticipation", "desire", "worry"}):
                result = await stage._run(pipeline_context, input_data)

            assert result == 0
            mock_repo.bulk_create_thoughts.assert_not_called()

    @pytest.mark.asyncio
    async def test_filters_missing_fields(
        self, mock_session, mock_logger, pipeline_context, mock_conversation
    ):
        """Verify thoughts with missing fields are filtered."""
        with patch(
            "nikita.db.repositories.thought_repository.NikitaThoughtRepository"
        ) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.bulk_create_thoughts = AsyncMock()
            mock_repo_cls.return_value = mock_repo

            stage = ThoughtsStage(mock_session, mock_logger)

            thoughts = [
                {"type": "reflection", "content": "Valid thought"},
                {"type": "reflection"},  # Missing content
                {"content": "Missing type"},  # Missing type
                {},  # Missing both
            ]

            input_data = ThoughtsInput(
                conversation=mock_conversation,
                thoughts=thoughts,
            )

            with patch("nikita.db.models.context.THOUGHT_TYPES", {"reflection", "anticipation", "desire", "worry"}):
                result = await stage._run(pipeline_context, input_data)

            assert result == 1  # Only the first valid thought
            call_kwargs = mock_repo.bulk_create_thoughts.call_args.kwargs
            assert len(call_kwargs["thoughts_data"]) == 1
