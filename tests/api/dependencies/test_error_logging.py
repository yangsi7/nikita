"""Tests for error logging utility - Issue #19 fixes."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.db.models.error_log import ErrorLevel, ErrorLog


class TestLogError:
    """Tests for log_error function."""

    @pytest.mark.asyncio
    async def test_log_error_creates_error_log(self):
        """Test that log_error creates an ErrorLog entry."""
        from nikita.api.dependencies.error_logging import log_error

        mock_session = AsyncMock()
        mock_session.add = MagicMock()

        result = await log_error(
            session=mock_session,
            message="Test error message",
            source="tests.test_error_logging:test_log_error",
            level=ErrorLevel.ERROR,
            commit=True,
        )

        mock_session.add.assert_called_once()
        added_log = mock_session.add.call_args[0][0]
        assert isinstance(added_log, ErrorLog)
        assert added_log.message == "Test error message"
        assert added_log.source == "tests.test_error_logging:test_log_error"
        assert added_log.level == "error"
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_error_with_exception_captures_stack_trace(self):
        """Test that log_error captures stack trace from exception."""
        from nikita.api.dependencies.error_logging import log_error

        mock_session = AsyncMock()
        mock_session.add = MagicMock()

        try:
            raise ValueError("Test exception")
        except ValueError as e:
            exception = e

        await log_error(
            session=mock_session,
            message="Error with exception",
            source="test",
            exception=exception,
            commit=True,
        )

        added_log = mock_session.add.call_args[0][0]
        assert added_log.stack_trace is not None
        assert "ValueError: Test exception" in added_log.stack_trace

    @pytest.mark.asyncio
    async def test_log_error_with_context(self):
        """Test that log_error stores context dictionary."""
        from nikita.api.dependencies.error_logging import log_error

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        user_id = uuid4()
        conv_id = uuid4()

        await log_error(
            session=mock_session,
            message="Error with context",
            source="test",
            user_id=user_id,
            conversation_id=conv_id,
            context={"request_path": "/api/test", "method": "POST"},
            commit=True,
        )

        added_log = mock_session.add.call_args[0][0]
        assert added_log.user_id == user_id
        assert added_log.conversation_id == conv_id
        assert added_log.context == {"request_path": "/api/test", "method": "POST"}


class TestLogShortcuts:
    """Tests for log_critical and log_warning shortcuts."""

    @pytest.mark.asyncio
    async def test_log_critical_uses_critical_level(self):
        """Test that log_critical sets CRITICAL level."""
        from nikita.api.dependencies.error_logging import log_critical

        mock_session = AsyncMock()
        mock_session.add = MagicMock()

        await log_critical(
            session=mock_session,
            message="Critical error",
            source="test",
            commit=True,
        )

        added_log = mock_session.add.call_args[0][0]
        assert added_log.level == "critical"

    @pytest.mark.asyncio
    async def test_log_warning_uses_warning_level(self):
        """Test that log_warning sets WARNING level."""
        from nikita.api.dependencies.error_logging import log_warning

        mock_session = AsyncMock()
        mock_session.add = MagicMock()

        await log_warning(
            session=mock_session,
            message="Warning message",
            source="test",
            commit=True,
        )

        added_log = mock_session.add.call_args[0][0]
        assert added_log.level == "warning"


class TestGetRecentErrors:
    """Tests for get_recent_errors function."""

    @pytest.mark.asyncio
    async def test_get_recent_errors_returns_list(self):
        """Test that get_recent_errors returns a list."""
        from nikita.api.dependencies.error_logging import get_recent_errors

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await get_recent_errors(session=mock_session)

        assert isinstance(result, list)
        mock_session.execute.assert_called_once()


class TestResolveError:
    """Tests for resolve_error function."""

    @pytest.mark.asyncio
    async def test_resolve_error_marks_as_resolved(self):
        """Test that resolve_error marks error as resolved."""
        from nikita.api.dependencies.error_logging import resolve_error

        mock_session = AsyncMock()
        error_id = uuid4()

        mock_error = MagicMock()
        mock_error.resolved = False
        mock_error.resolved_at = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_error
        mock_session.execute.return_value = mock_result

        result = await resolve_error(
            session=mock_session,
            error_id=error_id,
            resolution_notes="Fixed by deploying hotfix",
            commit=True,
        )

        assert mock_error.resolved is True
        assert mock_error.resolved_at is not None
        assert mock_error.resolution_notes == "Fixed by deploying hotfix"
        mock_session.commit.assert_called_once()


class TestGetErrorStats:
    """Tests for get_error_stats function."""

    @pytest.mark.asyncio
    async def test_get_error_stats_returns_dict(self):
        """Test that get_error_stats returns statistics dictionary."""
        from nikita.api.dependencies.error_logging import get_error_stats

        mock_session = AsyncMock()

        # Mock level counts query
        mock_level_result = MagicMock()
        mock_level_result.fetchall.return_value = [("error", 5), ("warning", 3)]

        # Mock source counts query
        mock_source_result = MagicMock()
        mock_source_result.fetchall.return_value = [
            ("nikita.api.routes.voice", 4),
            ("nikita.api.routes.telegram", 2),
        ]

        # Mock total count query
        mock_total_result = MagicMock()
        mock_total_result.scalar.return_value = 8

        # Mock unresolved count query
        mock_unresolved_result = MagicMock()
        mock_unresolved_result.scalar.return_value = 6

        mock_session.execute.side_effect = [
            mock_level_result,
            mock_source_result,
            mock_total_result,
            mock_unresolved_result,
        ]

        result = await get_error_stats(session=mock_session, hours=24)

        assert result["total"] == 8
        assert result["unresolved"] == 6
        assert result["by_level"] == {"error": 5, "warning": 3}
        assert len(result["top_sources"]) == 2
        assert result["time_window_hours"] == 24


class TestErrorLogModel:
    """Tests for ErrorLog model."""

    def test_error_log_repr(self):
        """Test ErrorLog string representation."""
        error = ErrorLog(
            id=uuid4(),
            level="error",
            message="Test",
            source="test.module",
        )

        repr_str = repr(error)
        assert "ErrorLog" in repr_str
        assert "[error]" in repr_str
        assert "test.module" in repr_str

    def test_error_level_enum_values(self):
        """Test ErrorLevel enum has expected values."""
        assert ErrorLevel.CRITICAL.value == "critical"
        assert ErrorLevel.ERROR.value == "error"
        assert ErrorLevel.WARNING.value == "warning"
        assert ErrorLevel.INFO.value == "info"
