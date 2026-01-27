"""Tests for FinalizationStage.

Verifies Stage 8 (finalization) functionality:
- Marking conversations as processed
- Marking conversations as failed
- Force update fallback
- Error handling
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.context.pipeline_context import PipelineContext
from nikita.context.stages.finalization import (
    FinalizationInput,
    FinalizationResult,
    FinalizationStage,
)


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
    logger.critical = MagicMock()
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
def mock_extraction():
    """Create mock extraction result."""
    extraction = MagicMock()
    extraction.summary = "Great conversation about work"
    extraction.emotional_tone = "positive"
    return extraction


class TestFinalizationStageProperties:
    """Test stage property configuration."""

    def test_stage_name(self, mock_session, mock_logger):
        """Verify stage name is 'finalization'."""
        with patch(
            "nikita.db.repositories.conversation_repository.ConversationRepository"
        ):
            stage = FinalizationStage(mock_session, mock_logger)
            assert stage.name == "finalization"

    def test_is_critical(self, mock_session, mock_logger):
        """Verify stage is critical."""
        with patch(
            "nikita.db.repositories.conversation_repository.ConversationRepository"
        ):
            stage = FinalizationStage(mock_session, mock_logger)
            assert stage.is_critical is True

    def test_timeout_seconds(self, mock_session, mock_logger):
        """Verify timeout is 10 seconds."""
        with patch(
            "nikita.db.repositories.conversation_repository.ConversationRepository"
        ):
            stage = FinalizationStage(mock_session, mock_logger)
            assert stage.timeout_seconds == 10.0

    def test_max_retries(self, mock_session, mock_logger):
        """Verify max retries is 3."""
        with patch(
            "nikita.db.repositories.conversation_repository.ConversationRepository"
        ):
            stage = FinalizationStage(mock_session, mock_logger)
            assert stage.max_retries == 3


class TestSuccessFinalization:
    """Test successful finalization scenarios."""

    @pytest.mark.asyncio
    async def test_marks_processed_on_success(
        self,
        mock_session,
        mock_logger,
        pipeline_context,
        mock_extraction,
    ):
        """Verify conversation marked processed when no critical failures."""
        with patch(
            "nikita.db.repositories.conversation_repository.ConversationRepository"
        ) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.mark_processed = AsyncMock()
            mock_repo_cls.return_value = mock_repo

            stage = FinalizationStage(mock_session, mock_logger)

            conversation_id = uuid4()
            input_data = FinalizationInput(
                conversation_id=conversation_id,
                critical_stage_failed=False,
                extraction=mock_extraction,
                extracted_entities={"facts": ["works in tech"]},
            )

            result = await stage._run(pipeline_context, input_data)

            assert result.success is True
            assert result.final_status == "processed"
            assert result.force_updated is False
            mock_repo.mark_processed.assert_called_once()
            call_kwargs = mock_repo.mark_processed.call_args.kwargs
            assert call_kwargs["conversation_id"] == conversation_id
            assert call_kwargs["summary"] == mock_extraction.summary

    @pytest.mark.asyncio
    async def test_marks_failed_on_critical_failure(
        self,
        mock_session,
        mock_logger,
        pipeline_context,
        mock_extraction,
    ):
        """Verify conversation marked failed when critical stage failed."""
        with patch(
            "nikita.db.repositories.conversation_repository.ConversationRepository"
        ) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.mark_failed = AsyncMock()
            mock_repo_cls.return_value = mock_repo

            stage = FinalizationStage(mock_session, mock_logger)

            conversation_id = uuid4()
            input_data = FinalizationInput(
                conversation_id=conversation_id,
                critical_stage_failed=True,
                extraction=mock_extraction,
            )

            result = await stage._run(pipeline_context, input_data)

            assert result.success is False
            assert result.final_status == "failed"
            mock_repo.mark_failed.assert_called_once_with(conversation_id)


class TestForceUpdate:
    """Test force update fallback."""

    @pytest.mark.asyncio
    async def test_uses_force_update_on_normal_failure(
        self,
        mock_session,
        mock_logger,
        pipeline_context,
        mock_extraction,
    ):
        """Verify force update used when normal update fails."""
        with patch(
            "nikita.db.repositories.conversation_repository.ConversationRepository"
        ) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.mark_processed = AsyncMock(
                side_effect=RuntimeError("ORM error")
            )
            mock_repo.force_status_update = AsyncMock(return_value=True)
            mock_repo_cls.return_value = mock_repo

            stage = FinalizationStage(mock_session, mock_logger)

            conversation_id = uuid4()
            input_data = FinalizationInput(
                conversation_id=conversation_id,
                critical_stage_failed=False,
                extraction=mock_extraction,
            )

            result = await stage._run(pipeline_context, input_data)

            assert result.success is True
            assert result.final_status == "processed"
            assert result.force_updated is True
            mock_repo.force_status_update.assert_called_once_with(
                conversation_id=conversation_id,
                status="processed",
            )

    @pytest.mark.asyncio
    async def test_force_update_with_critical_failure(
        self,
        mock_session,
        mock_logger,
        pipeline_context,
    ):
        """Verify force update marks as failed when critical stage failed."""
        with patch(
            "nikita.db.repositories.conversation_repository.ConversationRepository"
        ) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.mark_failed = AsyncMock(
                side_effect=RuntimeError("ORM error")
            )
            mock_repo.force_status_update = AsyncMock(return_value=True)
            mock_repo_cls.return_value = mock_repo

            stage = FinalizationStage(mock_session, mock_logger)

            conversation_id = uuid4()
            input_data = FinalizationInput(
                conversation_id=conversation_id,
                critical_stage_failed=True,
                extraction=None,
            )

            result = await stage._run(pipeline_context, input_data)

            assert result.success is False
            assert result.final_status == "failed"
            assert result.force_updated is True


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_raises_when_force_update_fails(
        self,
        mock_session,
        mock_logger,
        pipeline_context,
        mock_extraction,
    ):
        """Verify raises when both normal and force update fail."""
        with patch(
            "nikita.db.repositories.conversation_repository.ConversationRepository"
        ) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.mark_processed = AsyncMock(
                side_effect=RuntimeError("ORM error")
            )
            mock_repo.force_status_update = AsyncMock(
                side_effect=RuntimeError("Raw SQL error")
            )
            mock_repo_cls.return_value = mock_repo

            stage = FinalizationStage(mock_session, mock_logger)

            conversation_id = uuid4()
            input_data = FinalizationInput(
                conversation_id=conversation_id,
                critical_stage_failed=False,
                extraction=mock_extraction,
            )

            with pytest.raises(RuntimeError, match="may be stuck"):
                await stage._run(pipeline_context, input_data)

            mock_logger.critical.assert_called()

    @pytest.mark.asyncio
    async def test_handles_none_extraction(
        self,
        mock_session,
        mock_logger,
        pipeline_context,
    ):
        """Verify handles None extraction gracefully."""
        with patch(
            "nikita.db.repositories.conversation_repository.ConversationRepository"
        ) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.mark_processed = AsyncMock()
            mock_repo_cls.return_value = mock_repo

            stage = FinalizationStage(mock_session, mock_logger)

            conversation_id = uuid4()
            input_data = FinalizationInput(
                conversation_id=conversation_id,
                critical_stage_failed=False,
                extraction=None,
            )

            result = await stage._run(pipeline_context, input_data)

            assert result.success is True
            call_kwargs = mock_repo.mark_processed.call_args.kwargs
            assert call_kwargs["summary"] is None
            assert call_kwargs["emotional_tone"] is None
