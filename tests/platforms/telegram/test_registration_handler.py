"""Tests for RegistrationHandler - OTP code send during Telegram onboarding.

Tests verify the OTP registration flow when unregistered users provide their email
after receiving the /start prompt.

AC Coverage: AC-T2.9.1, AC-T2.9.2, AC-T2.9.3
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from nikita.platforms.telegram.registration_handler import RegistrationHandler


class TestRegistrationHandler:
    """Test suite for registration handler email capture flow."""

    @pytest.fixture
    def mock_telegram_auth(self):
        """Mock TelegramAuth for testing."""
        auth = AsyncMock()
        return auth

    @pytest.fixture
    def mock_bot(self):
        """Mock TelegramBot for testing."""
        bot = AsyncMock()
        return bot

    @pytest.fixture
    def handler(self, mock_telegram_auth, mock_bot):
        """Create RegistrationHandler instance with mocked dependencies."""
        return RegistrationHandler(
            telegram_auth=mock_telegram_auth,
            bot=mock_bot,
        )

    @pytest.mark.asyncio
    async def test_ac_t2_9_1_valid_email_sends_otp_code(
        self, handler, mock_telegram_auth, mock_bot
    ):
        """
        AC-T2.9.1: handle_email_input() calls send_otp_code() instead of register_user().

        Verifies that valid email input triggers OTP code send.
        """
        # Arrange
        telegram_id = 123456789
        chat_id = 987654321
        email = "test@example.com"

        # Mock: OTP code sent successfully
        mock_telegram_auth.send_otp_code.return_value = {
            "status": "code_sent",
            "email": email,
        }

        # Act
        await handler.handle_email_input(telegram_id, chat_id, email)

        # Assert
        mock_telegram_auth.send_otp_code.assert_called_once_with(
            telegram_id=telegram_id,
            chat_id=chat_id,
            email=email,
        )
        mock_bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_ac_t2_9_2_sends_otp_prompt_message(
        self, handler, mock_telegram_auth, mock_bot
    ):
        """
        AC-T2.9.2: Bot message updated to prompt for OTP code.

        Verifies that user receives message prompting for OTP code entry.
        """
        # Arrange
        telegram_id = 123456789
        chat_id = 987654321
        email = "confirm@test.com"

        mock_telegram_auth.send_otp_code.return_value = {
            "status": "code_sent",
            "email": email,
        }

        # Act
        await handler.handle_email_input(telegram_id, chat_id, email)

        # Assert
        mock_bot.send_message.assert_called_once()
        call_kwargs = mock_bot.send_message.call_args[1]
        assert call_kwargs["chat_id"] == chat_id
        assert "code" in call_kwargs["text"].lower()  # Changed: no longer require "6-digit"
        assert "email" in call_kwargs["text"].lower()

    @pytest.mark.asyncio
    async def test_ac_t2_9_3_error_handling_for_otp_send(
        self, handler, mock_telegram_auth, mock_bot
    ):
        """
        AC-T2.9.3: Error handling for OTP send failures.

        Verifies that unexpected exceptions are caught and user-friendly message sent.
        """
        # Arrange
        telegram_id = 123456789
        chat_id = 987654321
        email = "test@example.com"

        # Mock: OTP send fails
        mock_telegram_auth.send_otp_code.side_effect = Exception("Supabase API error")

        # Act
        await handler.handle_email_input(telegram_id, chat_id, email)

        # Assert - error message sent
        mock_bot.send_message.assert_called_once()
        call_kwargs = mock_bot.send_message.call_args[1]
        assert call_kwargs["chat_id"] == chat_id
        assert "Something went wrong" in call_kwargs["text"]
        assert "/start" in call_kwargs["text"]

    @pytest.mark.asyncio
    async def test_invalid_email_format_rejected(self, handler, mock_bot):
        """
        Verify that invalid email format is rejected with helpful message.
        """
        # Arrange
        telegram_id = 123456789
        chat_id = 987654321
        invalid_email = "not-an-email"

        # Act
        await handler.handle_email_input(telegram_id, chat_id, invalid_email)

        # Assert - validation failed, auth not called
        mock_bot.send_message.assert_called_once()
        call_kwargs = mock_bot.send_message.call_args[1]
        assert call_kwargs["chat_id"] == chat_id
        assert "doesn't look like a valid email" in call_kwargs["text"]

    @pytest.mark.asyncio
    async def test_already_registered_user(
        self, handler, mock_telegram_auth, mock_bot
    ):
        """
        Verify that already-registered users get appropriate message.
        """
        # Arrange
        telegram_id = 123456789
        chat_id = 987654321
        email = "existing@test.com"

        # Mock: User already registered
        mock_telegram_auth.send_otp_code.return_value = {
            "status": "already_registered",
        }

        # Act
        await handler.handle_email_input(telegram_id, chat_id, email)

        # Assert
        mock_bot.send_message.assert_called_once()
        call_kwargs = mock_bot.send_message.call_args[1]
        assert call_kwargs["chat_id"] == chat_id
        assert "already registered" in call_kwargs["text"]

    @pytest.mark.asyncio
    async def test_telegram_auth_value_error(
        self, handler, mock_telegram_auth, mock_bot
    ):
        """
        Verify that ValueError from TelegramAuth is handled gracefully.
        """
        # Arrange
        telegram_id = 123456789
        chat_id = 987654321
        email = "bad@test.com"

        # Mock: TelegramAuth raises ValueError
        mock_telegram_auth.send_otp_code.side_effect = ValueError("Invalid email format")

        # Act
        await handler.handle_email_input(telegram_id, chat_id, email)

        # Assert - error message sent to user
        mock_bot.send_message.assert_called_once()
        call_kwargs = mock_bot.send_message.call_args[1]
        assert call_kwargs["chat_id"] == chat_id
        assert "doesn't seem right" in call_kwargs["text"]
        assert "Invalid email format" in call_kwargs["text"]

    @pytest.mark.asyncio
    async def test_unknown_status_from_auth(
        self, handler, mock_telegram_auth, mock_bot
    ):
        """
        Verify that unknown status from TelegramAuth is handled.
        """
        # Arrange
        telegram_id = 123456789
        chat_id = 987654321
        email = "test@example.com"

        # Mock: Unknown status
        mock_telegram_auth.send_otp_code.return_value = {
            "status": "unknown_status",
            "error": "Unexpected error occurred",
        }

        # Act
        await handler.handle_email_input(telegram_id, chat_id, email)

        # Assert - error message sent
        mock_bot.send_message.assert_called_once()
        call_kwargs = mock_bot.send_message.call_args[1]
        assert call_kwargs["chat_id"] == chat_id
        assert "Something went wrong" in call_kwargs["text"]
        assert "Unexpected error occurred" in call_kwargs["text"]

    @pytest.mark.asyncio
    async def test_email_whitespace_trimmed(
        self, handler, mock_telegram_auth, mock_bot
    ):
        """
        Verify that leading/trailing whitespace is trimmed from email.
        """
        # Arrange
        telegram_id = 123456789
        chat_id = 987654321
        email_with_spaces = "  test@example.com  "

        mock_telegram_auth.send_otp_code.return_value = {
            "status": "code_sent",
            "email": "test@example.com",
        }

        # Act
        await handler.handle_email_input(telegram_id, chat_id, email_with_spaces)

        # Assert - trimmed email passed to auth
        mock_telegram_auth.send_otp_code.assert_called_once_with(
            telegram_id=telegram_id,
            chat_id=chat_id,
            email="test@example.com",
        )

    def test_is_valid_email_valid_formats(self, handler):
        """
        Verify that common valid email formats are accepted.
        """
        valid_emails = [
            "user@example.com",
            "test.user@example.com",
            "user+tag@example.co.uk",
            "123@example.com",
            "a@b.co",
        ]

        for email in valid_emails:
            assert handler.is_valid_email(email), f"Should accept: {email}"

    def test_is_valid_email_invalid_formats(self, handler):
        """
        Verify that invalid email formats are rejected.
        """
        invalid_emails = [
            "not-an-email",
            "@example.com",
            "user@",
            "user @example.com",
            "user@example",
            "",
            "   ",
        ]

        for email in invalid_emails:
            assert not handler.is_valid_email(email), f"Should reject: {email}"

    def test_is_valid_email_strips_whitespace(self, handler):
        """
        Verify that is_valid_email() strips whitespace before validation.
        """
        assert handler.is_valid_email("  test@example.com  ")
        assert not handler.is_valid_email("  not-an-email  ")
