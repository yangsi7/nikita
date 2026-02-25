"""Tests for bulk_increment_days_played in UserRepository (PR 76 F2).

Eliminates N+1 pattern: single UPDATE instead of N SELECT+flush per user.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.db.repositories.user_repository import UserRepository


class TestBulkIncrementDaysPlayed:
    """Tests for UserRepository.bulk_increment_days_played()."""

    @pytest.mark.asyncio
    async def test_bulk_increment_executes_single_update(self):
        """Bulk increment issues a single UPDATE for multiple user IDs."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.rowcount = 3
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = UserRepository(mock_session)
        user_ids = [uuid4(), uuid4(), uuid4()]

        count = await repo.bulk_increment_days_played(user_ids)

        assert count == 3
        # Should be called exactly once (single UPDATE)
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_bulk_increment_empty_list_returns_zero(self):
        """Empty user_ids list returns 0 without executing any query."""
        mock_session = AsyncMock()
        repo = UserRepository(mock_session)

        count = await repo.bulk_increment_days_played([])

        assert count == 0
        mock_session.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_bulk_increment_returns_rowcount(self):
        """Returns the actual rowcount from the UPDATE statement."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.rowcount = 7
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = UserRepository(mock_session)
        user_ids = [uuid4() for _ in range(10)]

        count = await repo.bulk_increment_days_played(user_ids)

        # rowcount may differ from len(user_ids) if some IDs don't exist
        assert count == 7
