"""Tests for VoiceCacheStage.

Verifies Stage 7.7 (voice cache invalidation) functionality:
- Successful cache invalidation
- Handling user not found
- Handling unexpected errors
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.context.pipeline_context import PipelineContext
from nikita.context.stages.voice_cache import VoiceCacheStage


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


class TestVoiceCacheStageProperties:
    """Test stage property configuration."""

    def test_stage_name(self, mock_session, mock_logger):
        """Verify stage name is 'voice_cache'."""
        with patch(
            "nikita.db.repositories.user_repository.UserRepository"
        ):
            stage = VoiceCacheStage(mock_session, mock_logger)
            assert stage.name == "voice_cache"

    def test_is_not_critical(self, mock_session, mock_logger):
        """Verify stage is non-critical."""
        with patch(
            "nikita.db.repositories.user_repository.UserRepository"
        ):
            stage = VoiceCacheStage(mock_session, mock_logger)
            assert stage.is_critical is False

    def test_timeout_seconds(self, mock_session, mock_logger):
        """Verify timeout is 5 seconds."""
        with patch(
            "nikita.db.repositories.user_repository.UserRepository"
        ):
            stage = VoiceCacheStage(mock_session, mock_logger)
            assert stage.timeout_seconds == 5.0

    def test_max_retries_is_one(self, mock_session, mock_logger):
        """Verify max retries is 1 (no retries for cache ops)."""
        with patch(
            "nikita.db.repositories.user_repository.UserRepository"
        ):
            stage = VoiceCacheStage(mock_session, mock_logger)
            assert stage.max_retries == 1


class TestVoiceCacheInvalidation:
    """Test cache invalidation functionality."""

    @pytest.mark.asyncio
    async def test_successful_invalidation(
        self, mock_session, mock_logger, pipeline_context
    ):
        """Verify successful cache invalidation."""
        with patch(
            "nikita.db.repositories.user_repository.UserRepository"
        ) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.invalidate_voice_cache = AsyncMock()
            mock_repo_cls.return_value = mock_repo

            stage = VoiceCacheStage(mock_session, mock_logger)

            user_id = uuid4()
            result = await stage._run(pipeline_context, user_id)

            assert result is None
            mock_repo.invalidate_voice_cache.assert_called_once_with(user_id)
            mock_logger.info.assert_called_with(
                "voice_cache_invalidated",
                user_id=str(user_id),
            )

    @pytest.mark.asyncio
    async def test_handles_user_not_found(
        self, mock_session, mock_logger, pipeline_context
    ):
        """Verify user not found error is handled gracefully."""
        with patch(
            "nikita.db.repositories.user_repository.UserRepository"
        ) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.invalidate_voice_cache = AsyncMock(
                side_effect=ValueError("User not found")
            )
            mock_repo_cls.return_value = mock_repo

            stage = VoiceCacheStage(mock_session, mock_logger)

            user_id = uuid4()
            # Should not raise
            result = await stage._run(pipeline_context, user_id)

            assert result is None
            mock_logger.warning.assert_called()
            # Verify the warning was about user not found
            call_args = mock_logger.warning.call_args
            assert "voice_cache_user_not_found" in call_args[0]

    @pytest.mark.asyncio
    async def test_handles_unexpected_error(
        self, mock_session, mock_logger, pipeline_context
    ):
        """Verify unexpected errors are handled gracefully."""
        with patch(
            "nikita.db.repositories.user_repository.UserRepository"
        ) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.invalidate_voice_cache = AsyncMock(
                side_effect=RuntimeError("Database connection failed")
            )
            mock_repo_cls.return_value = mock_repo

            stage = VoiceCacheStage(mock_session, mock_logger)

            user_id = uuid4()
            # Should not raise
            result = await stage._run(pipeline_context, user_id)

            assert result is None
            mock_logger.warning.assert_called()
            # Verify the warning was about invalidation failure
            call_args = mock_logger.warning.call_args
            assert "voice_cache_invalidation_failed" in call_args[0]

    @pytest.mark.asyncio
    async def test_logs_with_user_id(
        self, mock_session, mock_logger, pipeline_context
    ):
        """Verify all logs include user_id."""
        with patch(
            "nikita.db.repositories.user_repository.UserRepository"
        ) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.invalidate_voice_cache = AsyncMock()
            mock_repo_cls.return_value = mock_repo

            stage = VoiceCacheStage(mock_session, mock_logger)

            user_id = uuid4()
            await stage._run(pipeline_context, user_id)

            # Verify info log has user_id
            mock_logger.info.assert_called_once()
            call_kwargs = mock_logger.info.call_args.kwargs
            assert call_kwargs.get("user_id") == str(user_id)
