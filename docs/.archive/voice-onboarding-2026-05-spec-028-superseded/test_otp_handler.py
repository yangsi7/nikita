"""Tests for OTPVerificationHandler - OTP code verification in Telegram chat.

Tests verify the OTP verification flow when users enter their OTP code (6-8 digits)
after receiving it via email during Telegram onboarding.

AC Coverage: AC-T2.4.1, AC-T2.4.2, AC-T2.4.3, AC-T2.4.4, AC-T2.4.5, AC-T2.4.6
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from nikita.platforms.telegram.otp_handler import OTPVerificationHandler


class TestOTPVerificationHandler:
    """Test suite for OTP verification handler."""

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
    def mock_pending_repo(self):
        """Mock PendingRegistrationRepository for testing."""
        repo = AsyncMock()
        # Default: return attempt count of 1 (first failure)
        repo.increment_attempts.return_value = 1
        repo.delete.return_value = True
        return repo

    @pytest.fixture
    def handler(self, mock_telegram_auth, mock_bot, mock_pending_repo):
        """Create OTPVerificationHandler instance with mocked dependencies."""
        return OTPVerificationHandler(
            telegram_auth=mock_telegram_auth,
            bot=mock_bot,
            pending_repo=mock_pending_repo,
        )

    @pytest.fixture
    def mock_user(self):
        """Create a mock User object for successful verification."""
        user = MagicMock()
        user.id = "550e8400-e29b-41d4-a716-446655440000"
        return user

    @pytest.mark.asyncio
    async def test_ac_t2_4_1_class_exists(self):
        """
        AC-T2.4.1: OTPVerificationHandler class exists.

        Verifies the class can be imported and instantiated.
        """
        # The import at the top of the file confirms class exists
        # Verify it has required attributes
        assert hasattr(OTPVerificationHandler, "handle")
        assert hasattr(OTPVerificationHandler, "is_otp_code")

    @pytest.mark.asyncio
    async def test_ac_t2_4_2_handle_verifies_otp(
        self, handler, mock_telegram_auth, mock_user
    ):
        """
        AC-T2.4.2: handle(telegram_id, chat_id, code) method verifies OTP.

        Verifies that handle() calls verify_otp_code with correct parameters.
        """
        # Arrange
        telegram_id = 123456789
        chat_id = 987654321
        code = "847291"

        mock_telegram_auth.verify_otp_code.return_value = mock_user

        # Act
        result = await handler.handle(telegram_id, chat_id, code)

        # Assert
        mock_telegram_auth.verify_otp_code.assert_called_once_with(
            telegram_id, code
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_ac_t2_4_3_sends_welcome_on_success(
        self, handler, mock_telegram_auth, mock_bot, mock_user
    ):
        """
        AC-T2.4.3: On success: sends welcome message.

        Verifies that successful verification sends welcome message to user.
        """
        # Arrange
        telegram_id = 123456789
        chat_id = 987654321
        code = "123456"

        mock_telegram_auth.verify_otp_code.return_value = mock_user

        # Act
        await handler.handle(telegram_id, chat_id, code)

        # Assert
        mock_bot.send_message.assert_called_once()
        call_kwargs = mock_bot.send_message.call_args[1]
        assert call_kwargs["chat_id"] == chat_id
        assert "all set up" in call_kwargs["text"]
        assert "💕" in call_kwargs["text"]

    @pytest.mark.asyncio
    async def test_ac_t2_4_4_sends_error_on_invalid_code(
        self, handler, mock_telegram_auth, mock_bot, mock_pending_repo
    ):
        """
        AC-T2.4.4: On invalid code: sends error message with retry count.

        Verifies that invalid code sends appropriate error message with
        remaining attempts shown.
        """
        # Arrange
        telegram_id = 123456789
        chat_id = 987654321
        code = "000000"

        mock_telegram_auth.verify_otp_code.side_effect = ValueError(
            "Invalid OTP code"
        )
        # Return 1 attempt (2 remaining out of 3)
        mock_pending_repo.increment_attempts.return_value = 1

        # Act
        result = await handler.handle(telegram_id, chat_id, code)

        # Assert
        assert result is False
        mock_bot.send_message.assert_called_once()
        call_kwargs = mock_bot.send_message.call_args[1]
        assert call_kwargs["chat_id"] == chat_id
        # Check for the actual error message format
        assert "doesn't look right" in call_kwargs["text"]
        assert "attempt" in call_kwargs["text"].lower()

    @pytest.mark.asyncio
    async def test_ac_t2_4_5_sends_error_on_expired_code(
        self, handler, mock_telegram_auth, mock_bot, mock_pending_repo
    ):
        """
        AC-T2.4.5: On expired code: sends error message and clears pending.

        Verifies that expired code sends appropriate error message and
        deletes the pending registration so user can restart.
        """
        # Arrange
        telegram_id = 123456789
        chat_id = 987654321
        code = "999999"

        mock_telegram_auth.verify_otp_code.side_effect = ValueError(
            "Code has expired"
        )
        # Return 1 attempt
        mock_pending_repo.increment_attempts.return_value = 1

        # Act
        result = await handler.handle(telegram_id, chat_id, code)

        # Assert
        assert result is False
        mock_bot.send_message.assert_called_once()
        call_kwargs = mock_bot.send_message.call_args[1]
        assert call_kwargs["chat_id"] == chat_id
        assert "expired" in call_kwargs["text"]
        # Expired code should delete pending so user can restart
        mock_pending_repo.delete.assert_called_once_with(telegram_id)

    @pytest.mark.asyncio
    async def test_ac_t2_4_6_logs_verification_attempt(
        self, handler, mock_telegram_auth, mock_user
    ):
        """
        AC-T2.4.6: Logs all verification attempts.

        Verifies that verification attempts are logged.
        """
        # Arrange
        telegram_id = 123456789
        chat_id = 987654321
        code = "123456"

        mock_telegram_auth.verify_otp_code.return_value = mock_user

        # Act
        with patch("nikita.platforms.telegram.otp_handler.logger") as mock_logger:
            await handler.handle(telegram_id, chat_id, code)

            # Assert - verify logging occurred
            assert mock_logger.info.call_count >= 1
            # Check that telegram_id was logged
            log_call = mock_logger.info.call_args_list[0]
            assert "telegram_id=123456789" in str(log_call)

    @pytest.mark.asyncio
    async def test_ac_t2_4_6_logs_verification_failure(
        self, handler, mock_telegram_auth, mock_bot
    ):
        """
        AC-T2.4.6: Logs all verification attempts (failure case).

        Verifies that failed verification attempts are logged as warnings.
        """
        # Arrange
        telegram_id = 123456789
        chat_id = 987654321
        code = "000000"

        mock_telegram_auth.verify_otp_code.side_effect = ValueError(
            "Invalid code"
        )

        # Act
        with patch("nikita.platforms.telegram.otp_handler.logger") as mock_logger:
            await handler.handle(telegram_id, chat_id, code)

            # Assert - verify warning logged
            mock_logger.warning.assert_called_once()
            log_call = mock_logger.warning.call_args
            assert "telegram_id=123456789" in str(log_call)

    @pytest.mark.asyncio
    async def test_unexpected_exception_handling(
        self, handler, mock_telegram_auth, mock_bot
    ):
        """
        Verify that unexpected exceptions are caught and user-friendly message sent.
        """
        # Arrange
        telegram_id = 123456789
        chat_id = 987654321
        code = "123456"

        mock_telegram_auth.verify_otp_code.side_effect = Exception(
            "Database connection failed"
        )

        # Act
        result = await handler.handle(telegram_id, chat_id, code)

        # Assert
        assert result is False
        mock_bot.send_message.assert_called_once()
        call_kwargs = mock_bot.send_message.call_args[1]
        assert call_kwargs["chat_id"] == chat_id
        assert "/start" in call_kwargs["text"]

    @pytest.mark.asyncio
    async def test_unexpected_exception_logs_error(
        self, handler, mock_telegram_auth, mock_bot
    ):
        """
        Verify that unexpected exceptions are logged with error level.
        """
        # Arrange
        telegram_id = 123456789
        chat_id = 987654321
        code = "123456"

        mock_telegram_auth.verify_otp_code.side_effect = Exception(
            "Unexpected error"
        )

        # Act
        with patch("nikita.platforms.telegram.otp_handler.logger") as mock_logger:
            await handler.handle(telegram_id, chat_id, code)

            # Assert
            mock_logger.error.assert_called_once()


class TestIsOTPCode:
    """Test suite for is_otp_code static method."""

    def test_valid_6_digit_codes(self):
        """Verify that valid 6-digit codes are accepted."""
        valid_codes = [
            "123456",
            "000000",
            "999999",
            "847291",
            "100000",
        ]

        for code in valid_codes:
            assert OTPVerificationHandler.is_otp_code(code), f"Should accept: {code}"

    def test_valid_7_digit_codes(self):
        """Verify that valid 7-digit codes are accepted."""
        valid_codes = [
            "1234567",
            "0000000",
            "9999999",
            "8472910",
        ]

        for code in valid_codes:
            assert OTPVerificationHandler.is_otp_code(code), f"Should accept: {code}"

    def test_valid_8_digit_codes(self):
        """Verify that valid 8-digit codes are accepted (user's actual Supabase code)."""
        valid_codes = [
            "12345678",
            "00000000",
            "99999999",
            "74962285",  # Actual code from user's Supabase email
        ]

        for code in valid_codes:
            assert OTPVerificationHandler.is_otp_code(code), f"Should accept: {code}"

    def test_valid_codes_with_whitespace(self):
        """Verify that codes with leading/trailing whitespace are accepted."""
        assert OTPVerificationHandler.is_otp_code("  123456  ")
        assert OTPVerificationHandler.is_otp_code("\t847291\n")
        assert OTPVerificationHandler.is_otp_code("  12345678  ")  # 8 digits with whitespace

    def test_invalid_codes_rejected(self):
        """Verify that invalid codes are rejected."""
        invalid_codes = [
            "12345",      # Too short (5 digits)
            "123456789",  # Too long (9 digits)
            "abcdef",     # Letters
            "12345a",     # Mixed
            "",           # Empty
            "   ",        # Whitespace only
            "12 34 56",   # Spaces in middle
            "123.456",    # Decimal
            "-123456",    # Negative
        ]

        for code in invalid_codes:
            assert not OTPVerificationHandler.is_otp_code(code), f"Should reject: {code}"

    def test_non_digit_characters_rejected(self):
        """Verify that any non-digit characters cause rejection."""
        assert not OTPVerificationHandler.is_otp_code("12345!")
        assert not OTPVerificationHandler.is_otp_code("12345@")
        assert not OTPVerificationHandler.is_otp_code("hello!")
