"""Tests for PendingRegistrationRepository.

Verifies database operations for pending registrations.
AC Coverage: AC-T046.2, AC-T046.5
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from nikita.db.models.pending_registration import PendingRegistration
from nikita.db.repositories.pending_registration_repository import (
    PendingRegistrationRepository,
)


class TestPendingRegistrationRepository:
    """Test suite for PendingRegistrationRepository."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session):
        """Create repository with mocked session."""
        return PendingRegistrationRepository(mock_session)

    @pytest.mark.asyncio
    async def test_ac_t046_2_store_creates_pending_registration(
        self, repository, mock_session
    ):
        """
        AC-T046.2: Create PendingRegistrationRepository class with store method.

        Verifies that store() inserts/upserts a pending registration.
        """
        # Arrange
        telegram_id = 123456789
        email = "test@example.com"

        # Mock the execute result
        mock_result = MagicMock()
        mock_registration = PendingRegistration(
            telegram_id=telegram_id,
            email=email,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(minutes=10),
        )
        mock_result.scalar_one.return_value = mock_registration
        mock_session.execute.return_value = mock_result

        # Act
        with patch("nikita.db.repositories.pending_registration_repository.utc_now") as mock_now:
            mock_now.return_value = datetime(2025, 1, 1, 12, 0, 0)
            result = await repository.store(telegram_id, email)

        # Assert
        mock_session.execute.assert_called_once()
        assert result.telegram_id == telegram_id
        assert result.email == email

    @pytest.mark.asyncio
    async def test_get_returns_registration_if_exists(
        self, repository, mock_session
    ):
        """
        Verify get() returns registration when found and not expired.
        """
        # Arrange
        telegram_id = 123456789

        mock_registration = MagicMock(spec=PendingRegistration)
        mock_registration.telegram_id = telegram_id
        mock_registration.email = "test@example.com"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_registration
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.get(telegram_id)

        # Assert
        mock_session.execute.assert_called_once()
        assert result == mock_registration

    @pytest.mark.asyncio
    async def test_get_returns_none_if_not_found(
        self, repository, mock_session
    ):
        """
        Verify get() returns None when registration not found.
        """
        # Arrange
        telegram_id = 999999999

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.get(telegram_id)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_email_returns_email_string(
        self, repository, mock_session
    ):
        """
        Verify get_email() returns just the email string.
        """
        # Arrange
        telegram_id = 123456789
        expected_email = "test@example.com"

        mock_registration = MagicMock(spec=PendingRegistration)
        mock_registration.email = expected_email

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_registration
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.get_email(telegram_id)

        # Assert
        assert result == expected_email

    @pytest.mark.asyncio
    async def test_get_email_returns_none_if_not_found(
        self, repository, mock_session
    ):
        """
        Verify get_email() returns None when registration not found.
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.get_email(999999999)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_removes_registration(
        self, repository, mock_session
    ):
        """
        Verify delete() removes the pending registration.
        """
        # Arrange
        telegram_id = 123456789

        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.delete(telegram_id)

        # Assert
        mock_session.execute.assert_called_once()
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_returns_false_if_not_found(
        self, repository, mock_session
    ):
        """
        Verify delete() returns False when registration not found.
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.delete(999999999)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_ac_t046_5_cleanup_expired_deletes_old_registrations(
        self, repository, mock_session
    ):
        """
        AC-T046.5: Automatic cleanup of expired registrations (>10 minutes old).

        Verifies that cleanup_expired() removes old registrations.
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.rowcount = 5  # 5 expired registrations deleted
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.cleanup_expired()

        # Assert
        mock_session.execute.assert_called_once()
        assert result == 5

    @pytest.mark.asyncio
    async def test_store_with_custom_expiry(
        self, repository, mock_session
    ):
        """
        Verify store() accepts custom expiry time.
        """
        # Arrange
        telegram_id = 123456789
        email = "test@example.com"
        custom_expiry = datetime(2025, 12, 31, 23, 59, 59)

        mock_registration = MagicMock(spec=PendingRegistration)
        mock_registration.expires_at = custom_expiry

        mock_result = MagicMock()
        mock_result.scalar_one.return_value = mock_registration
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.store(telegram_id, email, expires_at=custom_expiry)

        # Assert
        mock_session.execute.assert_called_once()
        assert result.expires_at == custom_expiry
