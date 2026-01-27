"""Tests for SummaryRollupsStage.

Verifies Stage 7 (summary rollup) functionality:
- Creating new daily summaries
- Updating existing daily summaries
- Handling database errors
"""

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.context.pipeline_context import PipelineContext
from nikita.context.stages.summary_rollups import SummaryRollupsInput, SummaryRollupsStage


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


@pytest.fixture
def mock_extraction():
    """Create mock extraction result."""
    extraction = MagicMock()
    extraction.summary = "Had a great conversation about work"
    extraction.key_moments = ["discussed project deadline", "shared lunch plans"]
    extraction.emotional_tone = "positive"
    return extraction


class TestSummaryRollupsStageProperties:
    """Test stage property configuration."""

    def test_stage_name(self, mock_session, mock_logger):
        """Verify stage name is 'summary_rollups'."""
        with patch(
            "nikita.db.repositories.summary_repository.DailySummaryRepository"
        ):
            stage = SummaryRollupsStage(mock_session, mock_logger)
            assert stage.name == "summary_rollups"

    def test_is_not_critical(self, mock_session, mock_logger):
        """Verify stage is non-critical."""
        with patch(
            "nikita.db.repositories.summary_repository.DailySummaryRepository"
        ):
            stage = SummaryRollupsStage(mock_session, mock_logger)
            assert stage.is_critical is False

    def test_timeout_seconds(self, mock_session, mock_logger):
        """Verify timeout is 15 seconds."""
        with patch(
            "nikita.db.repositories.summary_repository.DailySummaryRepository"
        ):
            stage = SummaryRollupsStage(mock_session, mock_logger)
            assert stage.timeout_seconds == 15.0

    def test_max_retries(self, mock_session, mock_logger):
        """Verify max retries is 2."""
        with patch(
            "nikita.db.repositories.summary_repository.DailySummaryRepository"
        ):
            stage = SummaryRollupsStage(mock_session, mock_logger)
            assert stage.max_retries == 2


class TestSummaryCreation:
    """Test daily summary creation."""

    @pytest.mark.asyncio
    async def test_creates_new_summary_when_none_exists(
        self,
        mock_session,
        mock_logger,
        pipeline_context,
        mock_conversation,
        mock_extraction,
    ):
        """Verify new summary created when no existing summary for today."""
        with patch(
            "nikita.db.repositories.summary_repository.DailySummaryRepository"
        ) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_for_date = AsyncMock(return_value=None)
            mock_repo.create_summary = AsyncMock()
            mock_repo_cls.return_value = mock_repo

            stage = SummaryRollupsStage(mock_session, mock_logger)

            input_data = SummaryRollupsInput(
                conversation=mock_conversation,
                extraction=mock_extraction,
            )

            result = await stage._run(pipeline_context, input_data)

            assert result is None
            mock_repo.create_summary.assert_called_once()
            call_kwargs = mock_repo.create_summary.call_args.kwargs
            assert call_kwargs["user_id"] == mock_conversation.user_id
            assert call_kwargs["summary_text"] == mock_extraction.summary
            assert len(call_kwargs["key_moments"]) == 1
            assert call_kwargs["key_moments"][0]["source"] == str(mock_conversation.id)
            assert call_kwargs["emotional_tone"] == mock_extraction.emotional_tone
            mock_logger.info.assert_called_with(
                "daily_summary_created",
                user_id=str(mock_conversation.user_id),
                date=str(datetime.now(UTC).date()),
            )


class TestSummaryUpdate:
    """Test daily summary update."""

    @pytest.mark.asyncio
    async def test_updates_existing_summary(
        self,
        mock_session,
        mock_logger,
        pipeline_context,
        mock_conversation,
        mock_extraction,
    ):
        """Verify existing summary is updated with new conversation data."""
        with patch(
            "nikita.db.repositories.summary_repository.DailySummaryRepository"
        ) as mock_repo_cls:
            # Mock existing summary
            existing_summary = MagicMock()
            existing_summary.id = uuid4()
            existing_summary.summary_text = "Earlier conversation about morning routine"
            existing_summary.key_moments = [
                {"source": str(uuid4()), "moments": ["woke up early"]}
            ]

            mock_repo = AsyncMock()
            mock_repo.get_for_date = AsyncMock(return_value=existing_summary)
            mock_repo.update_summary = AsyncMock()
            mock_repo_cls.return_value = mock_repo

            stage = SummaryRollupsStage(mock_session, mock_logger)

            input_data = SummaryRollupsInput(
                conversation=mock_conversation,
                extraction=mock_extraction,
            )

            result = await stage._run(pipeline_context, input_data)

            assert result is None
            mock_repo.update_summary.assert_called_once()
            call_kwargs = mock_repo.update_summary.call_args.kwargs
            assert call_kwargs["summary_id"] == existing_summary.id
            assert mock_extraction.summary in call_kwargs["summary_text"]
            assert len(call_kwargs["key_moments"]) == 2  # Original + new

    @pytest.mark.asyncio
    async def test_handles_empty_existing_summary_text(
        self,
        mock_session,
        mock_logger,
        pipeline_context,
        mock_conversation,
        mock_extraction,
    ):
        """Verify handles case when existing summary has no text."""
        with patch(
            "nikita.db.repositories.summary_repository.DailySummaryRepository"
        ) as mock_repo_cls:
            existing_summary = MagicMock()
            existing_summary.id = uuid4()
            existing_summary.summary_text = None
            existing_summary.key_moments = None

            mock_repo = AsyncMock()
            mock_repo.get_for_date = AsyncMock(return_value=existing_summary)
            mock_repo.update_summary = AsyncMock()
            mock_repo_cls.return_value = mock_repo

            stage = SummaryRollupsStage(mock_session, mock_logger)

            input_data = SummaryRollupsInput(
                conversation=mock_conversation,
                extraction=mock_extraction,
            )

            result = await stage._run(pipeline_context, input_data)

            assert result is None
            call_kwargs = mock_repo.update_summary.call_args.kwargs
            # Should strip leading newlines when existing text is None
            assert call_kwargs["summary_text"] == mock_extraction.summary


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_propagates_database_errors(
        self,
        mock_session,
        mock_logger,
        pipeline_context,
        mock_conversation,
        mock_extraction,
    ):
        """Verify database errors are propagated for retry."""
        with patch(
            "nikita.db.repositories.summary_repository.DailySummaryRepository"
        ) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_for_date = AsyncMock(
                side_effect=RuntimeError("Database connection failed")
            )
            mock_repo_cls.return_value = mock_repo

            stage = SummaryRollupsStage(mock_session, mock_logger)

            input_data = SummaryRollupsInput(
                conversation=mock_conversation,
                extraction=mock_extraction,
            )

            with pytest.raises(RuntimeError, match="Database connection failed"):
                await stage._run(pipeline_context, input_data)
