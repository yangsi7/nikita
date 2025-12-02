"""Tests for TelegramAuth - Updated for database-backed pending registrations.

These tests verify Telegram user authentication via Supabase magic links.
AC Coverage: AC-FR004-001, AC-FR004-002, AC-T008.1-4, AC-T046.2-6
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from nikita.platforms.telegram.auth import TelegramAuth
from nikita.db.models.user import User
from uuid import uuid4


class TestTelegramAuth:
    """Test suite for Telegram authentication flow."""

    @pytest.fixture
    def mock_supabase_client(self):
        """Mock Supabase client for testing."""
        client = MagicMock()
        client.auth = MagicMock()
        return client

    @pytest.fixture
    def mock_user_repository(self):
        """Mock UserRepository for testing."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_pending_repo(self):
        """Mock PendingRegistrationRepository for testing."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def auth(self, mock_supabase_client, mock_user_repository, mock_pending_repo):
        """Create TelegramAuth instance with mocked dependencies."""
        return TelegramAuth(
            supabase_client=mock_supabase_client,
            user_repository=mock_user_repository,
            pending_registration_repository=mock_pending_repo,
        )

    @pytest.mark.asyncio
    async def test_ac_fr004_001_valid_email_sends_magic_link(
        self, auth, mock_supabase_client, mock_user_repository
    ):
        """
        AC-FR004-001: Given user provides email, When valid format,
        Then magic link is sent.

        Verifies that valid email triggers magic link delivery.
        """
        # Arrange
        telegram_id = 123456789
        email = "test@example.com"

        # Mock: User doesn't exist yet
        mock_user_repository.get_by_telegram_id.return_value = None

        # Mock Supabase response
        mock_supabase_client.auth.sign_in_with_otp.return_value = MagicMock(
            user=None,  # New user, not signed in yet
            session=None,
        )

        # Act
        result = await auth.register_user(telegram_id, email)

        # Assert
        mock_supabase_client.auth.sign_in_with_otp.assert_called_once()
        call_kwargs = mock_supabase_client.auth.sign_in_with_otp.call_args[1]
        assert call_kwargs["email"] == email

        # Verify result indicates success
        assert result["status"] == "magic_link_sent"
        assert result["email"] == email

    @pytest.mark.asyncio
    async def test_ac_t008_1_register_user_creates_pending_registration(
        self, auth, mock_supabase_client, mock_user_repository, mock_pending_repo
    ):
        """
        AC-T008.1: register_user(telegram_id, email) creates pending registration.
        AC-T046.2: PendingRegistrationRepository.store() is called.

        Verifies that registration request is stored in database.
        """
        # Arrange
        telegram_id = 123456789
        email = "test@example.com"

        # Mock: User doesn't exist yet
        mock_user_repository.get_by_telegram_id.return_value = None

        mock_supabase_client.auth.sign_in_with_otp.return_value = MagicMock(
            user=None,
            session=None,
        )

        # Act
        await auth.register_user(telegram_id, email)

        # Assert - pending registration stored in database
        mock_pending_repo.store.assert_called_once_with(telegram_id, email)

    @pytest.mark.asyncio
    async def test_ac_t008_2_sends_magic_link_via_supabase(
        self, auth, mock_supabase_client, mock_user_repository
    ):
        """
        AC-T008.2: Sends magic link email via Supabase auth.

        Verifies Supabase sign_in_with_otp is called correctly.
        """
        # Arrange
        telegram_id = 123456789
        email = "user@test.com"

        # Mock: User doesn't exist yet
        mock_user_repository.get_by_telegram_id.return_value = None

        mock_supabase_client.auth.sign_in_with_otp.return_value = MagicMock(
            user=None,
            session=None,
        )

        # Act
        await auth.register_user(telegram_id, email)

        # Assert
        mock_supabase_client.auth.sign_in_with_otp.assert_called_once_with(
            email=email
        )

    @pytest.mark.asyncio
    async def test_ac_fr004_002_valid_link_creates_account(
        self, auth, mock_supabase_client, mock_user_repository, mock_pending_repo
    ):
        """
        AC-FR004-002: Given user clicks magic link, When valid,
        Then account is created and confirmed.
        AC-T046.3: TelegramAuth.register_user() uses database.
        AC-T046.4: TelegramAuth.verify_magic_link() queries database.

        Verifies that clicking magic link completes registration.
        """
        # Arrange
        telegram_id = 123456789
        email = "test@example.com"
        otp_token = "123456"
        user_id = uuid4()

        # Setup: Pending registration exists in database
        mock_pending_repo.get_email.return_value = email

        # Mock: Supabase verifies OTP successfully
        mock_supabase_client.auth.verify_otp.return_value = MagicMock(
            user=MagicMock(id=str(user_id), email=email),
            session=MagicMock(access_token="test-token"),
        )

        # Mock: User created in database
        mock_user = MagicMock(spec=User)
        mock_user.id = user_id
        mock_user.telegram_id = telegram_id
        mock_user_repository.create_with_metrics.return_value = mock_user

        # Act
        result = await auth.verify_magic_link(telegram_id, otp_token)

        # Assert
        mock_pending_repo.get_email.assert_called_once_with(telegram_id)
        mock_supabase_client.auth.verify_otp.assert_called_once()
        mock_user_repository.create_with_metrics.assert_called_once()

        # Verify user created with correct telegram_id
        create_call = mock_user_repository.create_with_metrics.call_args[1]
        assert create_call["user_id"] == user_id
        assert create_call["telegram_id"] == telegram_id

        # Verify pending registration cleared from database
        mock_pending_repo.delete.assert_called_once_with(telegram_id)

        # Result should be the created user
        assert result.id == user_id
        assert result.telegram_id == telegram_id

    @pytest.mark.asyncio
    async def test_ac_t008_3_verify_magic_link_completes_registration(
        self, auth, mock_supabase_client, mock_user_repository, mock_pending_repo
    ):
        """
        AC-T008.3: verify_magic_link(token) completes registration.

        Verifies full verification flow from OTP to user creation.
        """
        # Arrange
        telegram_id = 999888777
        email = "verify@test.com"
        otp_token = "654321"
        user_id = uuid4()

        # Pending registration exists in database
        mock_pending_repo.get_email.return_value = email

        mock_supabase_client.auth.verify_otp.return_value = MagicMock(
            user=MagicMock(id=str(user_id), email=email),
            session=MagicMock(access_token="token123"),
        )

        mock_user = MagicMock(spec=User)
        mock_user.id = user_id
        mock_user.telegram_id = telegram_id
        mock_user_repository.create_with_metrics.return_value = mock_user

        # Act
        result = await auth.verify_magic_link(telegram_id, otp_token)

        # Assert - complete flow executed
        assert mock_supabase_client.auth.verify_otp.called
        assert mock_user_repository.create_with_metrics.called
        assert result.telegram_id == telegram_id

    @pytest.mark.asyncio
    async def test_ac_t008_4_link_telegram_updates_user_record(
        self, auth, mock_user_repository
    ):
        """
        AC-T008.4: link_telegram(user_id, telegram_id) updates user record.

        Verifies that Telegram ID can be linked to existing user.
        """
        # Arrange
        user_id = uuid4()
        telegram_id = 555444333

        mock_user = MagicMock(spec=User)
        mock_user.id = user_id
        mock_user.telegram_id = None
        mock_user_repository.get.return_value = mock_user

        # Act
        await auth.link_telegram(user_id, telegram_id)

        # Assert
        mock_user_repository.get.assert_called_once_with(user_id)
        assert mock_user.telegram_id == telegram_id
        mock_user_repository.update.assert_called_once_with(mock_user)

    @pytest.mark.asyncio
    async def test_register_user_already_linked(self, auth, mock_user_repository):
        """
        Verify that registering with already-linked telegram_id returns error.
        """
        # Arrange
        telegram_id = 123456789
        email = "test@example.com"

        # Mock: telegram_id already exists
        mock_user = MagicMock(spec=User)
        mock_user.telegram_id = telegram_id
        mock_user_repository.get_by_telegram_id.return_value = mock_user

        # Act
        result = await auth.register_user(telegram_id, email)

        # Assert
        assert result["status"] == "already_registered"
        assert "user" in result

    @pytest.mark.asyncio
    async def test_verify_otp_invalid_token(
        self, auth, mock_supabase_client, mock_pending_repo
    ):
        """
        Verify that invalid OTP token raises appropriate error.
        """
        # Arrange
        telegram_id = 123456789
        invalid_token = "000000"

        # Pending registration exists in database
        mock_pending_repo.get_email.return_value = "test@example.com"

        # Mock: Supabase rejects OTP
        mock_supabase_client.auth.verify_otp.side_effect = Exception(
            "Invalid or expired OTP"
        )

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await auth.verify_magic_link(telegram_id, invalid_token)

        assert "Invalid or expired OTP" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_verify_without_pending_registration(
        self, auth, mock_pending_repo
    ):
        """
        Verify that verification fails if no pending registration exists.
        AC-T046.4: Query returns None for non-existent registration.
        """
        # Arrange
        telegram_id = 999999999
        otp_token = "123456"

        # No pending registration in database
        mock_pending_repo.get_email.return_value = None

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await auth.verify_magic_link(telegram_id, otp_token)

        assert "No pending registration" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invalid_email_format(self, auth):
        """
        Verify that invalid email format is rejected.
        """
        # Arrange
        telegram_id = 123456789
        invalid_email = "not-an-email"

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await auth.register_user(telegram_id, invalid_email)

        assert "Invalid email" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_link_telegram_user_not_found(self, auth, mock_user_repository):
        """
        Verify that linking fails if user doesn't exist.
        """
        # Arrange
        user_id = uuid4()
        telegram_id = 123456789

        mock_user_repository.get.return_value = None

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await auth.link_telegram(user_id, telegram_id)

        assert "User not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_ac_t046_6_persistence_across_restarts(
        self, mock_supabase_client, mock_user_repository, mock_pending_repo
    ):
        """
        AC-T046.6: Tests verify persistence across "restarts".

        Verifies that pending registrations persist even when
        TelegramAuth instance is recreated (simulating server restart).
        """
        # Arrange - First instance stores registration
        telegram_id = 123456789
        email = "persist@test.com"

        # Simulate database persistence
        stored_email = None

        async def store_impl(tid, em):
            nonlocal stored_email
            stored_email = em

        async def get_email_impl(tid):
            if tid == telegram_id:
                return stored_email
            return None

        mock_pending_repo.store.side_effect = store_impl
        mock_pending_repo.get_email.side_effect = get_email_impl

        # Create first auth instance
        auth1 = TelegramAuth(
            supabase_client=mock_supabase_client,
            user_repository=mock_user_repository,
            pending_registration_repository=mock_pending_repo,
        )

        mock_user_repository.get_by_telegram_id.return_value = None
        mock_supabase_client.auth.sign_in_with_otp.return_value = MagicMock()

        # Register user with first instance
        await auth1.register_user(telegram_id, email)

        # Create NEW auth instance (simulates restart)
        # Uses same mock_pending_repo which simulates DB persistence
        auth2 = TelegramAuth(
            supabase_client=mock_supabase_client,
            user_repository=mock_user_repository,
            pending_registration_repository=mock_pending_repo,
        )

        # Act - Try to get pending email from second instance
        result = await auth2.get_pending_email(telegram_id)

        # Assert - Email should be retrievable from "database"
        assert result == email
