"""Tests for TelegramAuth - Updated for OTP-based registration flow.

These tests verify Telegram user authentication via Supabase OTP codes.
AC Coverage: AC-FR004-001, AC-FR004-002, AC-T008.1-4, AC-T046.2-6, AC-T2.2, AC-T2.3
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from nikita.platforms.telegram.auth import TelegramAuth
from nikita.db.models.user import User
from uuid import uuid4


class TestTelegramAuth:
    """Test suite for Telegram authentication flow."""

    @pytest.fixture
    def mock_supabase_client(self):
        """Mock Supabase AsyncClient for testing."""
        client = AsyncMock()
        client.auth = AsyncMock()
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

        # Mock Supabase response (AsyncMock automatically handles await)
        mock_response = MagicMock()
        mock_response.user = None  # New user, not signed in yet
        mock_response.session = None
        mock_supabase_client.auth.sign_in_with_otp.return_value = mock_response

        # Act
        result = await auth.register_user(telegram_id, email)

        # Assert - check call was made with dict argument
        mock_supabase_client.auth.sign_in_with_otp.assert_called_once()
        call_args = mock_supabase_client.auth.sign_in_with_otp.call_args[0][0]
        assert call_args["email"] == email

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

        mock_response = MagicMock()
        mock_response.user = None
        mock_response.session = None
        mock_supabase_client.auth.sign_in_with_otp.return_value = mock_response

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

        mock_response = MagicMock()
        mock_response.user = None
        mock_response.session = None
        mock_supabase_client.auth.sign_in_with_otp.return_value = mock_response

        # Act
        await auth.register_user(telegram_id, email)

        # Assert - verify dict argument
        mock_supabase_client.auth.sign_in_with_otp.assert_called_once()
        call_args = mock_supabase_client.auth.sign_in_with_otp.call_args[0][0]
        assert call_args["email"] == email

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
        mock_response = MagicMock()
        mock_response.user = MagicMock(id=str(user_id), email=email)
        mock_response.session = MagicMock(access_token="test-token")
        mock_supabase_client.auth.verify_otp.return_value = mock_response

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

        mock_response = MagicMock()
        mock_response.user = MagicMock(id=str(user_id), email=email)
        mock_response.session = MagicMock(access_token="token123")
        mock_supabase_client.auth.verify_otp.return_value = mock_response

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
        mock_response = MagicMock()
        mock_supabase_client.auth.sign_in_with_otp.return_value = mock_response

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


class TestRedirectURLConstruction:
    """Test suite for redirect URL construction (bug fix for duplicate /api/v1/)."""

    @pytest.fixture
    def mock_supabase_client(self):
        """Mock Supabase AsyncClient for testing."""
        client = AsyncMock()
        client.auth = AsyncMock()
        return client

    @pytest.fixture
    def mock_user_repository(self):
        """Mock UserRepository for testing."""
        repo = AsyncMock()
        repo.get_by_telegram_id.return_value = None  # User doesn't exist
        return repo

    @pytest.fixture
    def mock_pending_repo(self):
        """Mock PendingRegistrationRepository for testing."""
        return AsyncMock()

    @pytest.fixture
    def auth(self, mock_supabase_client, mock_user_repository, mock_pending_repo):
        """Create TelegramAuth instance with mocked dependencies."""
        return TelegramAuth(
            supabase_client=mock_supabase_client,
            user_repository=mock_user_repository,
            pending_registration_repository=mock_pending_repo,
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "webhook_url,expected_redirect",
        [
            # Full URL with /api/v1/telegram/webhook path - the production case
            (
                "https://nikita-api-1040094048579.us-central1.run.app/api/v1/telegram/webhook",
                "https://nikita-api-1040094048579.us-central1.run.app/api/v1/telegram/auth/confirm",
            ),
            # URL with just /webhook
            (
                "https://example.com/webhook",
                "https://example.com/api/v1/telegram/auth/confirm",
            ),
            # URL with port
            (
                "https://example.com:8080/api/v1/telegram/webhook",
                "https://example.com:8080/api/v1/telegram/auth/confirm",
            ),
            # Localhost for development
            (
                "http://localhost:8000",
                "http://localhost:8000/api/v1/telegram/auth/confirm",
            ),
            # Localhost with path
            (
                "http://localhost:8000/api/v1/telegram/webhook",
                "http://localhost:8000/api/v1/telegram/auth/confirm",
            ),
        ],
    )
    async def test_redirect_url_no_duplicate_path(
        self,
        auth,
        mock_supabase_client,
        webhook_url,
        expected_redirect,
    ):
        """
        Test that redirect URL is constructed correctly without path duplication.

        This test verifies the fix for the bug where /api/v1/ was duplicated:
        - Bug: https://...run.app/api/v1/api/v1/telegram/auth/confirm
        - Fixed: https://...run.app/api/v1/telegram/auth/confirm

        The fix uses urlparse to extract only scheme+netloc, ignoring any path.
        """
        telegram_id = 123456789
        email = "test@example.com"

        # Mock settings to return our test webhook URL
        mock_settings = MagicMock()
        mock_settings.telegram_webhook_url = webhook_url
        mock_settings.portal_url = None

        mock_response = MagicMock()
        mock_supabase_client.auth.sign_in_with_otp.return_value = mock_response

        with patch(
            "nikita.config.settings.get_settings", return_value=mock_settings
        ):
            await auth.register_user(telegram_id, email)

        # Verify sign_in_with_otp was called with correct redirect URL
        mock_supabase_client.auth.sign_in_with_otp.assert_called_once()
        call_args = mock_supabase_client.auth.sign_in_with_otp.call_args[0][0]

        actual_redirect = call_args["options"]["email_redirect_to"]
        assert actual_redirect == expected_redirect, (
            f"Redirect URL mismatch!\n"
            f"  Webhook URL: {webhook_url}\n"
            f"  Expected: {expected_redirect}\n"
            f"  Actual: {actual_redirect}"
        )

    @pytest.mark.asyncio
    async def test_portal_flow_uses_portal_url(
        self, auth, mock_supabase_client
    ):
        """Test that portal registration uses portal URL for redirect."""
        telegram_id = 123456789
        email = "test@example.com"

        mock_settings = MagicMock()
        mock_settings.telegram_webhook_url = "https://api.example.com/webhook"
        mock_settings.portal_url = "https://portal.example.com"

        mock_response = MagicMock()
        mock_supabase_client.auth.sign_in_with_otp.return_value = mock_response

        with patch(
            "nikita.config.settings.get_settings", return_value=mock_settings
        ):
            await auth.register_user(telegram_id, email, registration_source="portal")

        call_args = mock_supabase_client.auth.sign_in_with_otp.call_args[0][0]
        actual_redirect = call_args["options"]["email_redirect_to"]

        assert actual_redirect == "https://portal.example.com/auth/callback"

    @pytest.mark.asyncio
    async def test_fallback_to_localhost_when_no_webhook_url(
        self, auth, mock_supabase_client
    ):
        """Test fallback to localhost when TELEGRAM_WEBHOOK_URL is not set."""
        telegram_id = 123456789
        email = "test@example.com"

        mock_settings = MagicMock()
        mock_settings.telegram_webhook_url = None  # Not configured
        mock_settings.portal_url = None

        mock_response = MagicMock()
        mock_supabase_client.auth.sign_in_with_otp.return_value = mock_response

        with patch(
            "nikita.config.settings.get_settings", return_value=mock_settings
        ):
            await auth.register_user(telegram_id, email)

        call_args = mock_supabase_client.auth.sign_in_with_otp.call_args[0][0]
        actual_redirect = call_args["options"]["email_redirect_to"]

        assert actual_redirect == "http://localhost:8000/api/v1/telegram/auth/confirm"


class TestOTPAuthFlow:
    """Test suite for OTP-based registration flow (replaces magic link).

    AC Coverage: AC-T2.2 (send_otp_code), AC-T2.3 (verify_otp_code)
    """

    @pytest.fixture
    def mock_supabase_client(self):
        """Mock Supabase AsyncClient for testing."""
        client = AsyncMock()
        client.auth = AsyncMock()
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
    async def test_ac_t2_2_1_send_otp_code_method_exists(self, auth):
        """
        AC-T2.2.1: send_otp_code(telegram_id, chat_id, email) method exists.

        Verifies the method signature is correct.
        """
        assert hasattr(auth, "send_otp_code")
        # Method should accept telegram_id, chat_id, email

    @pytest.mark.asyncio
    async def test_ac_t2_2_2_send_otp_with_redirect_for_template(
        self, auth, mock_supabase_client, mock_user_repository
    ):
        """
        AC-T2.2.2: Supabase sign_in_with_otp called WITH emailRedirectTo.

        CRITICAL: email_redirect_to is REQUIRED for Supabase email template to render.
        Without it, {{ .ConfirmationURL }} is empty and email silently fails to send.
        Users will use the OTP code from the email, not click the magic link.
        """
        # Arrange
        telegram_id = 123456789
        chat_id = 987654321
        email = "test@example.com"

        mock_user_repository.get_by_telegram_id.return_value = None
        mock_response = MagicMock()
        mock_supabase_client.auth.sign_in_with_otp.return_value = mock_response

        # Act
        await auth.send_otp_code(telegram_id, chat_id, email)

        # Assert - sign_in_with_otp called WITH email_redirect_to (required for template)
        mock_supabase_client.auth.sign_in_with_otp.assert_called_once()
        call_args = mock_supabase_client.auth.sign_in_with_otp.call_args[0][0]
        assert call_args["email"] == email
        # MUST have email_redirect_to for email template to render
        assert "email_redirect_to" in call_args.get("options", {})
        assert "/api/v1/telegram/auth/confirm" in call_args["options"]["email_redirect_to"]

    @pytest.mark.asyncio
    async def test_ac_t2_2_3_stores_pending_with_chat_id_and_state(
        self, auth, mock_supabase_client, mock_user_repository, mock_pending_repo
    ):
        """
        AC-T2.2.3: Stores pending registration with chat_id and otp_state='code_sent'.

        Verifies database storage includes new OTP fields.
        """
        # Arrange
        telegram_id = 123456789
        chat_id = 987654321
        email = "test@example.com"

        mock_user_repository.get_by_telegram_id.return_value = None
        mock_response = MagicMock()
        mock_supabase_client.auth.sign_in_with_otp.return_value = mock_response

        # Act
        await auth.send_otp_code(telegram_id, chat_id, email)

        # Assert - pending repo called with chat_id and otp_state
        mock_pending_repo.store.assert_called_once()
        call_kwargs = mock_pending_repo.store.call_args[1]
        assert call_kwargs["telegram_id"] == telegram_id
        assert call_kwargs["email"] == email
        assert call_kwargs["chat_id"] == chat_id
        assert call_kwargs["otp_state"] == "code_sent"

    @pytest.mark.asyncio
    async def test_ac_t2_2_4_returns_code_sent_status(
        self, auth, mock_supabase_client, mock_user_repository
    ):
        """
        AC-T2.2.4: Returns {"status": "code_sent", "email": email}.

        Verifies correct return format.
        """
        # Arrange
        telegram_id = 123456789
        chat_id = 987654321
        email = "test@example.com"

        mock_user_repository.get_by_telegram_id.return_value = None
        mock_response = MagicMock()
        mock_supabase_client.auth.sign_in_with_otp.return_value = mock_response

        # Act
        result = await auth.send_otp_code(telegram_id, chat_id, email)

        # Assert
        assert result["status"] == "code_sent"
        assert result["email"] == email

    @pytest.mark.asyncio
    async def test_ac_t2_3_1_verify_otp_code_method_exists(self, auth):
        """
        AC-T2.3.1: verify_otp_code(telegram_id, code) method exists.

        Verifies the method signature is correct.
        """
        assert hasattr(auth, "verify_otp_code")

    @pytest.mark.asyncio
    async def test_ac_t2_3_2_fetches_pending_registration(
        self, auth, mock_supabase_client, mock_user_repository, mock_pending_repo
    ):
        """
        AC-T2.3.2: Fetches pending registration to get email.

        Verifies pending_repo.get() is called.
        """
        # Arrange
        telegram_id = 123456789
        code = "123456"
        user_id = uuid4()

        mock_pending = MagicMock()
        mock_pending.email = "test@example.com"
        mock_pending.otp_state = "code_sent"  # Required for OTP verification
        mock_pending_repo.get.return_value = mock_pending

        mock_response = MagicMock()
        mock_response.user = MagicMock(id=str(user_id))
        mock_supabase_client.auth.verify_otp.return_value = mock_response

        mock_user_repository.get.return_value = None
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user_repository.create_with_metrics.return_value = mock_user

        # Act
        await auth.verify_otp_code(telegram_id, code)

        # Assert
        mock_pending_repo.get.assert_called_once_with(telegram_id)

    @pytest.mark.asyncio
    async def test_ac_t2_3_3_verify_otp_uses_email_type(
        self, auth, mock_supabase_client, mock_user_repository, mock_pending_repo
    ):
        """
        AC-T2.3.3: Supabase verify_otp called with type="email" (NOT "magiclink").

        Critical: type must be "email" for OTP code verification.
        """
        # Arrange
        telegram_id = 123456789
        code = "847291"
        user_id = uuid4()

        mock_pending = MagicMock()
        mock_pending.email = "test@example.com"
        mock_pending.otp_state = "code_sent"  # Required for OTP verification
        mock_pending_repo.get.return_value = mock_pending

        mock_response = MagicMock()
        mock_response.user = MagicMock(id=str(user_id))
        mock_supabase_client.auth.verify_otp.return_value = mock_response

        mock_user_repository.get.return_value = None
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user_repository.create_with_metrics.return_value = mock_user

        # Act
        await auth.verify_otp_code(telegram_id, code)

        # Assert - verify_otp called with type="email"
        mock_supabase_client.auth.verify_otp.assert_called_once()
        call_args = mock_supabase_client.auth.verify_otp.call_args[0][0]
        assert call_args["type"] == "email"
        assert call_args["token"] == code
        assert call_args["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_ac_t2_3_4_creates_user_on_success(
        self, auth, mock_supabase_client, mock_user_repository, mock_pending_repo
    ):
        """
        AC-T2.3.4: Creates user in database on successful verification.

        Verifies user_repository.create_with_metrics() is called.
        """
        # Arrange
        telegram_id = 123456789
        code = "123456"
        user_id = uuid4()

        mock_pending = MagicMock()
        mock_pending.email = "test@example.com"
        mock_pending.otp_state = "code_sent"  # Required for OTP verification
        mock_pending_repo.get.return_value = mock_pending

        mock_response = MagicMock()
        mock_response.user = MagicMock(id=str(user_id))
        mock_supabase_client.auth.verify_otp.return_value = mock_response

        mock_user_repository.get.return_value = None  # No existing user
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.telegram_id = telegram_id
        mock_user_repository.create_with_metrics.return_value = mock_user

        # Act
        result = await auth.verify_otp_code(telegram_id, code)

        # Assert
        mock_user_repository.create_with_metrics.assert_called_once()
        call_kwargs = mock_user_repository.create_with_metrics.call_args[1]
        assert call_kwargs["user_id"] == user_id
        assert call_kwargs["telegram_id"] == telegram_id
        assert result.id == user_id

    @pytest.mark.asyncio
    async def test_ac_t2_3_5_clears_pending_registration(
        self, auth, mock_supabase_client, mock_user_repository, mock_pending_repo
    ):
        """
        AC-T2.3.5: Clears pending registration after successful verification.

        Verifies pending_repo.delete() is called.
        """
        # Arrange
        telegram_id = 123456789
        code = "123456"
        user_id = uuid4()

        mock_pending = MagicMock()
        mock_pending.email = "test@example.com"
        mock_pending.otp_state = "code_sent"  # Required for OTP verification
        mock_pending_repo.get.return_value = mock_pending

        mock_response = MagicMock()
        mock_response.user = MagicMock(id=str(user_id))
        mock_supabase_client.auth.verify_otp.return_value = mock_response

        mock_user_repository.get.return_value = None
        mock_user = MagicMock()
        mock_user_repository.create_with_metrics.return_value = mock_user

        # Act
        await auth.verify_otp_code(telegram_id, code)

        # Assert
        mock_pending_repo.delete.assert_called_once_with(telegram_id)

    @pytest.mark.asyncio
    async def test_verify_otp_code_no_pending_registration(
        self, auth, mock_pending_repo
    ):
        """
        Verify that verification fails if no pending registration exists.
        """
        # Arrange
        telegram_id = 999999999
        code = "123456"

        mock_pending_repo.get.return_value = None

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await auth.verify_otp_code(telegram_id, code)

        assert "No pending registration" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_verify_otp_code_invalid_code(
        self, auth, mock_supabase_client, mock_pending_repo
    ):
        """
        Verify that invalid OTP code raises appropriate error.
        """
        # Arrange
        telegram_id = 123456789
        code = "000000"

        mock_pending = MagicMock()
        mock_pending.email = "test@example.com"
        mock_pending.otp_state = "code_sent"  # Required for OTP verification
        mock_pending_repo.get.return_value = mock_pending

        mock_supabase_client.auth.verify_otp.side_effect = Exception(
            "Invalid OTP code"
        )

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await auth.verify_otp_code(telegram_id, code)

        assert "Invalid OTP code" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_send_otp_code_already_registered(
        self, auth, mock_user_repository
    ):
        """
        Verify that already-registered users get appropriate response.
        """
        # Arrange
        telegram_id = 123456789
        chat_id = 987654321
        email = "test@example.com"

        mock_user = MagicMock()
        mock_user.telegram_id = telegram_id
        mock_user_repository.get_by_telegram_id.return_value = mock_user

        # Act
        result = await auth.send_otp_code(telegram_id, chat_id, email)

        # Assert
        assert result["status"] == "already_registered"

    @pytest.mark.asyncio
    async def test_send_otp_code_invalid_email(self, auth):
        """
        Verify that invalid email format is rejected.
        """
        # Arrange
        telegram_id = 123456789
        chat_id = 987654321
        invalid_email = "not-an-email"

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await auth.send_otp_code(telegram_id, chat_id, invalid_email)

        assert "Invalid email" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_verify_otp_links_existing_supabase_user(
        self, auth, mock_supabase_client, mock_user_repository, mock_pending_repo
    ):
        """
        Verify that existing Supabase user gets telegram_id linked.

        This handles the portal-first flow where user exists but has no telegram_id.
        """
        # Arrange
        telegram_id = 123456789
        code = "123456"
        user_id = uuid4()

        mock_pending = MagicMock()
        mock_pending.email = "test@example.com"
        mock_pending.otp_state = "code_sent"  # Required for OTP verification
        mock_pending_repo.get.return_value = mock_pending

        mock_response = MagicMock()
        mock_response.user = MagicMock(id=str(user_id))
        mock_supabase_client.auth.verify_otp.return_value = mock_response

        # Existing user without telegram_id
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.telegram_id = None
        mock_user_repository.get.return_value = mock_user

        # Act
        result = await auth.verify_otp_code(telegram_id, code)

        # Assert - user updated, not created
        mock_user_repository.update.assert_called_once_with(mock_user)
        assert mock_user.telegram_id == telegram_id
        # create_with_metrics should NOT be called
        mock_user_repository.create_with_metrics.assert_not_called()
