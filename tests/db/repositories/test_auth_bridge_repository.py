"""Tests for AuthBridgeRepository."""

import pytest
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from nikita.db.models.auth_bridge import AuthBridgeToken
from nikita.db.repositories.auth_bridge_repository import AuthBridgeRepository


@pytest.fixture
def mock_session():
    """Create a mock async session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def repo(mock_session):
    """Create repository with mock session."""
    return AuthBridgeRepository(mock_session)


class TestCreateToken:
    """Tests for create_token()."""

    @pytest.mark.asyncio
    async def test_creates_token_for_user(self, repo, mock_session):
        """Should create a token, delete existing, add to session, and flush."""
        user_id = uuid4()
        # Mock the delete query result
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        token = await repo.create_token(user_id, "/onboarding")

        assert token.user_id == user_id
        assert token.redirect_path == "/onboarding"
        assert token.token  # Not empty
        mock_session.add.assert_called_once_with(token)
        mock_session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_deletes_existing_tokens_first(self, repo, mock_session):
        """Should delete existing tokens for user before creating new one."""
        user_id = uuid4()
        mock_result = MagicMock()
        mock_result.rowcount = 1  # Had an existing token
        mock_session.execute.return_value = mock_result

        await repo.create_token(user_id, "/onboarding")

        # execute called at least once for delete_for_user
        assert mock_session.execute.await_count >= 1

    @pytest.mark.asyncio
    async def test_default_redirect_path(self, repo, mock_session):
        """Default redirect_path should be /onboarding."""
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        token = await repo.create_token(uuid4())

        assert token.redirect_path == "/onboarding"


class TestVerifyToken:
    """Tests for verify_token()."""

    @pytest.mark.asyncio
    async def test_valid_token_returns_user_id_and_path(self, repo, mock_session):
        """Valid, non-expired token should return (user_id, redirect_path) and be deleted."""
        user_id = uuid4()
        bridge = AuthBridgeToken.create(user_id, "/onboarding")

        # Mock get_by_token
        mock_get_result = MagicMock()
        mock_get_result.scalar_one_or_none.return_value = bridge
        # Mock delete
        mock_delete_result = MagicMock()
        mock_delete_result.rowcount = 1

        mock_session.execute.side_effect = [mock_get_result, mock_delete_result]

        result = await repo.verify_token(bridge.token)

        assert result == (user_id, "/onboarding")
        # Should have called execute twice: get + delete
        assert mock_session.execute.await_count == 2

    @pytest.mark.asyncio
    async def test_expired_token_returns_none(self, repo, mock_session):
        """Expired token should return None and be deleted."""
        user_id = uuid4()
        bridge = AuthBridgeToken.create(user_id, "/onboarding")
        bridge.expires_at = datetime.now(UTC) - timedelta(minutes=1)

        # Mock get_by_token
        mock_get_result = MagicMock()
        mock_get_result.scalar_one_or_none.return_value = bridge
        # Mock delete
        mock_delete_result = MagicMock()
        mock_delete_result.rowcount = 1

        mock_session.execute.side_effect = [mock_get_result, mock_delete_result]

        result = await repo.verify_token(bridge.token)

        assert result is None

    @pytest.mark.asyncio
    async def test_unknown_token_returns_none(self, repo, mock_session):
        """Non-existent token should return None."""
        mock_get_result = MagicMock()
        mock_get_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_get_result

        result = await repo.verify_token("nonexistent-token")

        assert result is None

    @pytest.mark.asyncio
    async def test_single_use_deletes_after_verify(self, repo, mock_session):
        """Token should be deleted after successful verification (single-use)."""
        user_id = uuid4()
        bridge = AuthBridgeToken.create(user_id, "/dashboard")

        mock_get_result = MagicMock()
        mock_get_result.scalar_one_or_none.return_value = bridge
        mock_delete_result = MagicMock()
        mock_delete_result.rowcount = 1

        mock_session.execute.side_effect = [mock_get_result, mock_delete_result]

        result = await repo.verify_token(bridge.token)

        assert result == (user_id, "/dashboard")
        # Second execute call should be the delete
        assert mock_session.execute.await_count == 2


class TestCleanupExpired:
    """Tests for cleanup_expired()."""

    @pytest.mark.asyncio
    async def test_deletes_expired_tokens(self, repo, mock_session):
        """Should delete all expired tokens and return count."""
        mock_result = MagicMock()
        mock_result.rowcount = 5
        mock_session.execute.return_value = mock_result

        count = await repo.cleanup_expired()

        assert count == 5
        mock_session.execute.assert_awaited_once()


class TestDeleteForUser:
    """Tests for delete_for_user()."""

    @pytest.mark.asyncio
    async def test_deletes_all_tokens_for_user(self, repo, mock_session):
        """Should delete all tokens for a given user_id."""
        user_id = uuid4()
        mock_result = MagicMock()
        mock_result.rowcount = 2
        mock_session.execute.return_value = mock_result

        count = await repo.delete_for_user(user_id)

        assert count == 2
