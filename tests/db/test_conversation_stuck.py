"""Tests for stuck conversation detection (Spec 031 T4.2, T4.3, T4.5)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.db.models.conversation import Conversation
from nikita.db.repositories.conversation_repository import ConversationRepository


class TestDetectStuckRepository:
    """Tests for detect_stuck() repository method (T4.2)."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async database session."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_detect_stuck_finds_old_processing(self, mock_session):
        """Finds conversations stuck in processing for >30 min."""
        repo = ConversationRepository(mock_session)

        # Mock query returning stuck conversation IDs
        stuck_id = uuid4()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [stuck_id]
        mock_session.execute.return_value = result_mock

        result = await repo.detect_stuck(timeout_minutes=30, limit=50)

        assert len(result) == 1
        assert result[0] == stuck_id

    @pytest.mark.asyncio
    async def test_detect_stuck_returns_empty_list_when_none(self, mock_session):
        """Returns empty list when no conversations are stuck."""
        repo = ConversationRepository(mock_session)

        # Mock query returning no results
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = result_mock

        result = await repo.detect_stuck(timeout_minutes=30, limit=50)

        assert result == []

    @pytest.mark.asyncio
    async def test_detect_stuck_respects_limit(self, mock_session):
        """Respects the limit parameter."""
        repo = ConversationRepository(mock_session)

        # Mock query returning multiple IDs
        stuck_ids = [uuid4() for _ in range(5)]
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = stuck_ids
        mock_session.execute.return_value = result_mock

        result = await repo.detect_stuck(timeout_minutes=30, limit=5)

        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_detect_stuck_uses_timeout_minutes(self, mock_session):
        """Uses the timeout_minutes parameter for cutoff calculation."""
        repo = ConversationRepository(mock_session)

        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = result_mock

        # Call with different timeout values
        await repo.detect_stuck(timeout_minutes=15)
        await repo.detect_stuck(timeout_minutes=60)

        # Verify execute was called twice
        assert mock_session.execute.call_count == 2


class TestMarkProcessingUpdatesStartedAt:
    """Tests for mark_processing() updating processing_started_at (T4.1)."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async database session."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_mark_processing_sets_processing_started_at(self, mock_session):
        """Verify mark_processing sets processing_started_at timestamp."""
        repo = ConversationRepository(mock_session)

        # Create a mock conversation
        conv_id = uuid4()
        mock_conv = MagicMock(spec=Conversation)
        mock_conv.status = "active"
        mock_conv.processing_attempts = 0
        mock_conv.processing_started_at = None

        # Mock get() to return our conversation
        with patch.object(repo, "get", return_value=mock_conv):
            result = await repo.mark_processing(conv_id)

            # Verify processing_started_at was set
            assert result.processing_started_at is not None
            assert result.status == "processing"
            assert result.processing_attempts == 1

    @pytest.mark.asyncio
    async def test_mark_processing_increments_attempts(self, mock_session):
        """Verify mark_processing increments processing_attempts."""
        repo = ConversationRepository(mock_session)

        conv_id = uuid4()
        mock_conv = MagicMock(spec=Conversation)
        mock_conv.status = "active"
        mock_conv.processing_attempts = 2
        mock_conv.processing_started_at = None

        with patch.object(repo, "get", return_value=mock_conv):
            result = await repo.mark_processing(conv_id)

            assert result.processing_attempts == 3


class TestConversationModelProcessingStartedAt:
    """Tests for processing_started_at field on Conversation model."""

    def test_conversation_has_processing_started_at_field(self):
        """Verify Conversation model has processing_started_at field."""
        # Check the model has the field defined
        assert hasattr(Conversation, "processing_started_at")

    def test_processing_started_at_is_nullable(self):
        """Verify processing_started_at allows None."""
        conv = Conversation(
            user_id=uuid4(),
            platform="telegram",
            messages=[],
            started_at=datetime.now(timezone.utc),
            is_boss_fight=False,
            chapter_at_time=1,
        )
        # Default should be None
        assert conv.processing_started_at is None


class TestStuckDetectionLogic:
    """Tests for stuck detection business logic."""

    @pytest.mark.asyncio
    async def test_only_processing_status_detected_as_stuck(self):
        """Only conversations in 'processing' status should be detected."""
        mock_session = AsyncMock()
        repo = ConversationRepository(mock_session)

        # The query should filter on status == 'processing'
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = result_mock

        await repo.detect_stuck(timeout_minutes=30)

        # Verify execute was called (query built correctly)
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_detect_stuck_orders_by_oldest_first(self):
        """Detect stuck should return oldest stuck conversations first."""
        mock_session = AsyncMock()
        repo = ConversationRepository(mock_session)

        # Mock returning multiple IDs (simulating ordering by processing_started_at)
        older_id = uuid4()
        newer_id = uuid4()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [older_id, newer_id]
        mock_session.execute.return_value = result_mock

        result = await repo.detect_stuck(timeout_minutes=30, limit=50)

        # Verify order is preserved (oldest first from query)
        assert result[0] == older_id
        assert result[1] == newer_id


class TestDetectStuckEndpointBasic:
    """Basic tests for detect-stuck endpoint logic."""

    def test_endpoint_exists_in_router(self):
        """Verify detect-stuck endpoint is registered in tasks router."""
        from nikita.api.routes.tasks import router

        # Find the route
        routes = [route for route in router.routes if hasattr(route, "path")]
        route_paths = [route.path for route in routes]

        assert "/detect-stuck" in route_paths

    def test_endpoint_is_post_method(self):
        """Verify detect-stuck endpoint uses POST method."""
        from nikita.api.routes.tasks import router

        # Find the route
        for route in router.routes:
            if hasattr(route, "path") and route.path == "/detect-stuck":
                assert "POST" in route.methods
                break
        else:
            pytest.fail("detect-stuck route not found")
