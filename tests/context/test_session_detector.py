"""Tests for SessionDetector class.

TDD Tests for context engineering (spec 012) - Session detection

Acceptance Criteria:
- AC-1: get_stale_sessions() returns conversation IDs that timed out
- AC-2: get_stale_sessions() respects timeout minutes
- AC-3: get_stale_sessions() respects limit
- AC-4: mark_for_processing() returns True when successful
- AC-5: mark_for_processing() returns False when not found
- AC-6: detect_and_queue() combines detection and marking
- AC-7: convenience function works correctly
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.conversation import Conversation


class TestSessionDetector:
    """Test suite for SessionDetector."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock AsyncSession."""
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        return session

    # ========================================
    # AC-1: get_stale_sessions() returns conversation IDs
    # ========================================
    @pytest.mark.asyncio
    async def test_get_stale_sessions_returns_ids(self, mock_session: AsyncMock):
        """AC-1: get_stale_sessions() returns UUIDs of stale conversations."""
        from nikita.context.session_detector import SessionDetector

        conv1 = MagicMock()
        conv1.id = uuid4()
        conv2 = MagicMock()
        conv2.id = uuid4()

        # Mock the repository call
        detector = SessionDetector(mock_session)

        with patch.object(
            detector._conversation_repo,
            "get_stale_active_conversations",
            return_value=[conv1, conv2],
        ):
            result = await detector.get_stale_sessions(limit=50)

        assert len(result) == 2
        assert conv1.id in result
        assert conv2.id in result

    # ========================================
    # AC-2: get_stale_sessions() respects timeout_minutes
    # ========================================
    @pytest.mark.asyncio
    async def test_get_stale_sessions_respects_timeout(self, mock_session: AsyncMock):
        """AC-2: get_stale_sessions() passes timeout to repository."""
        from nikita.context.session_detector import SessionDetector

        custom_timeout = 30  # 30 minutes

        detector = SessionDetector(mock_session, timeout_minutes=custom_timeout)

        with patch.object(
            detector._conversation_repo,
            "get_stale_active_conversations",
            return_value=[],
        ) as mock_get:
            await detector.get_stale_sessions()

            mock_get.assert_called_once_with(
                timeout_minutes=custom_timeout,
                max_attempts=3,
                limit=50,
            )

    # ========================================
    # AC-3: get_stale_sessions() respects limit
    # ========================================
    @pytest.mark.asyncio
    async def test_get_stale_sessions_respects_limit(self, mock_session: AsyncMock):
        """AC-3: get_stale_sessions() passes limit to repository."""
        from nikita.context.session_detector import SessionDetector

        detector = SessionDetector(mock_session)

        with patch.object(
            detector._conversation_repo,
            "get_stale_active_conversations",
            return_value=[],
        ) as mock_get:
            await detector.get_stale_sessions(limit=10)

            mock_get.assert_called_once()
            _, kwargs = mock_get.call_args
            assert kwargs["limit"] == 10

    @pytest.mark.asyncio
    async def test_get_stale_sessions_skips_high_attempts(self, mock_session: AsyncMock):
        """AC-3b: get_stale_sessions() uses max_attempts=3."""
        from nikita.context.session_detector import SessionDetector

        detector = SessionDetector(mock_session)

        with patch.object(
            detector._conversation_repo,
            "get_stale_active_conversations",
            return_value=[],
        ) as mock_get:
            await detector.get_stale_sessions()

            _, kwargs = mock_get.call_args
            assert kwargs["max_attempts"] == 3

    # ========================================
    # AC-4: mark_for_processing() returns True when successful
    # ========================================
    @pytest.mark.asyncio
    async def test_mark_for_processing_returns_true(self, mock_session: AsyncMock):
        """AC-4: mark_for_processing() returns True on success."""
        from nikita.context.session_detector import SessionDetector

        conv_id = uuid4()
        detector = SessionDetector(mock_session)

        with patch.object(
            detector._conversation_repo,
            "mark_processing",
            return_value=None,  # No exception = success
        ):
            result = await detector.mark_for_processing(conv_id)

        assert result is True

    # ========================================
    # AC-5: mark_for_processing() returns False when not found
    # ========================================
    @pytest.mark.asyncio
    async def test_mark_for_processing_not_found_returns_false(
        self, mock_session: AsyncMock
    ):
        """AC-5: mark_for_processing() returns False when conversation not found."""
        from nikita.context.session_detector import SessionDetector

        conv_id = uuid4()
        detector = SessionDetector(mock_session)

        with patch.object(
            detector._conversation_repo,
            "mark_processing",
            side_effect=ValueError(f"Conversation {conv_id} not found"),
        ):
            result = await detector.mark_for_processing(conv_id)

        assert result is False

    # ========================================
    # AC-6: detect_and_queue() combines detection and marking
    # ========================================
    @pytest.mark.asyncio
    async def test_detect_and_queue_marks_all_found(self, mock_session: AsyncMock):
        """AC-6: detect_and_queue() detects and marks all stale sessions."""
        from nikita.context.session_detector import SessionDetector

        conv1_id = uuid4()
        conv2_id = uuid4()

        detector = SessionDetector(mock_session)

        async def mock_get_stale(limit):
            return [conv1_id, conv2_id]

        async def mock_mark(conv_id):
            return True

        with patch.object(detector, "get_stale_sessions", side_effect=mock_get_stale):
            with patch.object(detector, "mark_for_processing", side_effect=mock_mark):
                result = await detector.detect_and_queue(limit=50)

        assert len(result) == 2
        assert conv1_id in result
        assert conv2_id in result

    @pytest.mark.asyncio
    async def test_detect_and_queue_empty_when_none_stale(self, mock_session: AsyncMock):
        """AC-6b: detect_and_queue() returns empty list when no stale sessions."""
        from nikita.context.session_detector import SessionDetector

        detector = SessionDetector(mock_session)

        with patch.object(detector, "get_stale_sessions", return_value=[]):
            result = await detector.detect_and_queue()

        assert result == []

    @pytest.mark.asyncio
    async def test_detect_and_queue_skips_failed_marks(self, mock_session: AsyncMock):
        """AC-6c: detect_and_queue() skips conversations that fail to mark."""
        from nikita.context.session_detector import SessionDetector

        conv1_id = uuid4()
        conv2_id = uuid4()

        detector = SessionDetector(mock_session)

        async def mock_mark(conv_id):
            # First one fails, second succeeds
            return conv_id == conv2_id

        with patch.object(detector, "get_stale_sessions", return_value=[conv1_id, conv2_id]):
            with patch.object(detector, "mark_for_processing", side_effect=mock_mark):
                result = await detector.detect_and_queue()

        assert len(result) == 1
        assert conv2_id in result
        assert conv1_id not in result

    # ========================================
    # AC-7: Convenience function works correctly
    # ========================================
    @pytest.mark.asyncio
    async def test_convenience_function_detect_stale_sessions(
        self, mock_session: AsyncMock
    ):
        """AC-7: detect_stale_sessions() convenience function works."""
        from nikita.context.session_detector import detect_stale_sessions

        conv_id = uuid4()

        with patch(
            "nikita.context.session_detector.SessionDetector"
        ) as MockDetector:
            mock_detector_instance = MagicMock()
            mock_detector_instance.detect_and_queue = AsyncMock(return_value=[conv_id])
            MockDetector.return_value = mock_detector_instance

            result = await detect_stale_sessions(
                session=mock_session,
                timeout_minutes=20,
                limit=25,
            )

        assert len(result) == 1
        assert conv_id in result
        MockDetector.assert_called_once_with(mock_session, 20)
        mock_detector_instance.detect_and_queue.assert_called_once_with(limit=25)
