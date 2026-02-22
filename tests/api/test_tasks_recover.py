"""Tests for Spec 100 Story 1: Consolidated Stuck Recovery.

T1.4: Tests for recover endpoint and deprecated endpoints.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.api.routes.tasks import (
    detect_stuck_conversations,
    recover_stuck_conversations,
)


class TestDeprecatedEndpoints:
    """Spec 100 FR-001: Old endpoints return deprecation message."""

    @pytest.mark.asyncio
    async def test_detect_stuck_deprecated(self):
        """AC: Old detect-stuck returns deprecation message."""
        result = await detect_stuck_conversations()
        assert result["status"] == "deprecated"
        assert "recover" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_recover_stuck_deprecated(self):
        """AC: Old recover-stuck returns deprecation message."""
        result = await recover_stuck_conversations()
        assert result["status"] == "deprecated"
        assert "recover" in result["message"].lower()


class TestHasRecentExecution:
    """Spec 100 T1.1: has_recent_execution() repository method."""

    @pytest.mark.asyncio
    async def test_has_recent_execution_returns_true(self):
        """AC: Returns True if completed execution within window."""
        from nikita.db.repositories.job_execution_repository import (
            JobExecutionRepository,
        )

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = uuid4()
        session.execute = AsyncMock(return_value=mock_result)

        repo = JobExecutionRepository(session)
        result = await repo.has_recent_execution("decay", window_minutes=50)
        assert result is True

    @pytest.mark.asyncio
    async def test_has_recent_execution_returns_false(self):
        """AC: Returns False if no completed execution within window."""
        from nikita.db.repositories.job_execution_repository import (
            JobExecutionRepository,
        )

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        repo = JobExecutionRepository(session)
        result = await repo.has_recent_execution("decay", window_minutes=50)
        assert result is False
