"""Tests for UserRepository.update_phone (Spec 212 PR B, T012).

Verifies:
- session.flush called after phone update
- user.phone set to the validated value
- Non-empty user fixture (non-empty data per testing.md rule)

Failing until T016 (update_phone implementation) is committed.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

TEST_PHONE = "+41791234567"


class TestUserRepositoryUpdatePhone:
    """Unit tests for update_phone method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock AsyncSession."""
        session = AsyncMock(spec=AsyncSession)
        session.get = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def mock_user(self):
        """Non-empty user fixture with an existing phone=None."""
        from nikita.db.models.user import User

        user = MagicMock(spec=User)
        user.id = uuid4()
        user.phone = None
        return user

    @pytest.mark.asyncio
    async def test_update_phone_sets_user_phone(self, mock_session, mock_user):
        """update_phone sets user.phone to the provided value."""
        from nikita.db.repositories.user_repository import UserRepository

        user_id = mock_user.id

        # get() uses session.execute — return the mock user
        mock_result = MagicMock()
        mock_result.unique.return_value.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        await repo.update_phone(user_id, TEST_PHONE)

        assert mock_user.phone == TEST_PHONE

    @pytest.mark.asyncio
    async def test_update_phone_calls_session_flush(self, mock_session, mock_user):
        """update_phone calls session.flush() to persist within transaction."""
        from nikita.db.repositories.user_repository import UserRepository

        user_id = mock_user.id

        mock_result = MagicMock()
        mock_result.unique.return_value.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        await repo.update_phone(user_id, TEST_PHONE)

        mock_session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_phone_noop_when_user_not_found(self, mock_session):
        """update_phone does nothing (no flush) when user is not found."""
        from nikita.db.repositories.user_repository import UserRepository

        user_id = uuid4()

        mock_result = MagicMock()
        mock_result.unique.return_value.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        await repo.update_phone(user_id, TEST_PHONE)

        mock_session.flush.assert_not_awaited()
