"""Tests for IngestionStage.

Spec 037 T2.5: Tests for Stage 1 - conversation loading.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.context.pipeline_context import PipelineContext
from nikita.context.stages.ingestion import IngestionStage
from nikita.context.stages.base import StageError


@pytest.fixture
def mock_session():
    """Create mock database session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


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
    conv.messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]
    return conv


class TestIngestionStage:
    """Tests for IngestionStage."""

    @pytest.mark.asyncio
    async def test_stage_properties(self, mock_session):
        """AC-T2.5.1, AC-T2.5.2: Verify stage properties."""
        stage = IngestionStage(mock_session)

        assert stage.name == "ingestion"
        assert stage.is_critical is True
        assert stage.timeout_seconds == 10.0

    @pytest.mark.asyncio
    async def test_successful_load(
        self, mock_session, pipeline_context, mock_conversation
    ):
        """Test successful conversation loading."""
        stage = IngestionStage(mock_session)

        with patch.object(stage._repo, "get", return_value=mock_conversation):
            result = await stage.execute(pipeline_context, pipeline_context.conversation_id)

        assert result.success is True
        assert result.data is mock_conversation
        assert pipeline_context.conversation is mock_conversation

    @pytest.mark.asyncio
    async def test_conversation_not_found(self, mock_session, pipeline_context):
        """AC-T2.5.3: Raises StageError if conversation not found."""
        stage = IngestionStage(mock_session)

        with patch.object(stage._repo, "get", return_value=None):
            result = await stage.execute(pipeline_context, pipeline_context.conversation_id)

        assert result.success is False
        assert "not found" in result.error

    @pytest.mark.asyncio
    async def test_empty_messages(self, mock_session, pipeline_context):
        """AC-T2.5.4: Raises StageError if messages empty."""
        mock_conv = MagicMock()
        mock_conv.id = pipeline_context.conversation_id
        mock_conv.messages = []  # Empty messages

        stage = IngestionStage(mock_session)

        with patch.object(stage._repo, "get", return_value=mock_conv):
            result = await stage.execute(pipeline_context, pipeline_context.conversation_id)

        assert result.success is False
        assert "no messages" in result.error

    @pytest.mark.asyncio
    async def test_timeout_returns_failed_result(self, mock_session, pipeline_context):
        """Test timeout handling."""
        stage = IngestionStage(mock_session)
        stage.timeout_seconds = 0.001  # Very short timeout

        async def slow_get(*args, **kwargs):
            import asyncio
            await asyncio.sleep(1)
            return None

        with patch.object(stage._repo, "get", side_effect=slow_get):
            result = await stage.execute(pipeline_context, pipeline_context.conversation_id)

        assert result.success is False
        assert "timed out" in result.error.lower()
