"""Tests for job execution idempotency — PR 76 Review R6.

Verifies has_recent_execution uses completed_at (not started_at).
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


class TestHasRecentExecutionSemantics:
    """Verify has_recent_execution checks completed_at, not started_at."""

    @pytest.mark.asyncio
    async def test_completed_within_window_returns_true(self):
        """R6: Job completed 10 minutes ago within 50-minute window -> True."""
        from nikita.db.repositories.job_execution_repository import JobExecutionRepository

        mock_session = AsyncMock()
        repo = JobExecutionRepository(mock_session)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock()  # found a job
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repo.has_recent_execution("decay", window_minutes=50)
        assert result is True

        # Verify the SQL uses completed_at (not started_at) in the WHERE clause
        execute_call = mock_session.execute.call_args[0][0]
        # The compiled SQL should reference completed_at
        compiled = str(execute_call.compile(compile_kwargs={"literal_binds": False}))
        assert "completed_at" in compiled
        assert "started_at" not in compiled.split("WHERE")[1] if "WHERE" in compiled else True

    @pytest.mark.asyncio
    async def test_no_recent_completion_returns_false(self):
        """R6: No completed jobs in window -> False."""
        from nikita.db.repositories.job_execution_repository import JobExecutionRepository

        mock_session = AsyncMock()
        repo = JobExecutionRepository(mock_session)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # no job found
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repo.has_recent_execution("decay", window_minutes=50)
        assert result is False
