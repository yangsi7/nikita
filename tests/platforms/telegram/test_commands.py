"""Tests for CommandHandler - WRITTEN FIRST (TDD Red phase).

These tests verify command routing and handling for Telegram bot commands.
AC Coverage: AC-FR003-001, AC-T009.1-5
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from nikita.platforms.telegram.commands import CommandHandler
from nikita.db.models.user import User
from decimal import Decimal
from uuid import uuid4


class TestCommandHandler:
    """Test suite for Telegram command handler."""

    @pytest.fixture
    def mock_user_repository(self):
        """Mock UserRepository for testing."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_telegram_auth(self):
        """Mock TelegramAuth for testing."""
        auth = AsyncMock()
        return auth

    @pytest.fixture
    def mock_bot(self):
        """Mock TelegramBot for testing."""
        bot = AsyncMock()
        bot.send_message = AsyncMock()
        return bot

    @pytest.fixture
    def handler(self, mock_user_repository, mock_telegram_auth, mock_bot):
        """Create CommandHandler instance with mocked dependencies."""
        return CommandHandler(
            user_repository=mock_user_repository,
            telegram_auth=mock_telegram_auth,
            bot=mock_bot,
        )

    @pytest.mark.asyncio
    async def test_ac_t009_1_routes_commands_by_name(self, handler):
        """
        AC-T009.1: Routes commands by name (start, help, status, call).

        Verifies that the handler correctly routes commands to their handlers.
        """
        # Arrange
        start_message = {
            "message_id": 1,
            "from": {"id": 123456789, "first_name": "Test"},
            "chat": {"id": 123456789, "type": "private"},
            "text": "/start",
        }

        help_message = {**start_message, "text": "/help"}
        status_message = {**start_message, "text": "/status"}
        call_message = {**start_message, "text": "/call"}

        # Act & Assert - verify each command is routed
        with patch.object(handler, '_handle_start') as mock_start:
            await handler.handle(start_message)
            mock_start.assert_called_once()

        with patch.object(handler, '_handle_help') as mock_help:
            await handler.handle(help_message)
            mock_help.assert_called_once()

        with patch.object(handler, '_handle_status') as mock_status:
            await handler.handle(status_message)
            mock_status.assert_called_once()

        with patch.object(handler, '_handle_call') as mock_call:
            await handler.handle(call_message)
            mock_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_ac_fr003_001_start_command_new_user(
        self, handler, mock_user_repository, mock_bot
    ):
        """
        AC-FR003-001: Given new Telegram user, When they send /start,
        Then welcome message and email prompt.

        Verifies that new users are prompted for email registration.
        """
        # Arrange
        telegram_id = 123456789
        chat_id = 123456789
        message = {
            "message_id": 1,
            "from": {"id": telegram_id, "first_name": "Alex"},
            "chat": {"id": chat_id, "type": "private"},
            "text": "/start",
        }

        # Mock: User doesn't exist
        mock_user_repository.get_by_telegram_id.return_value = None

        # Act
        await handler.handle(message)

        # Assert
        mock_user_repository.get_by_telegram_id.assert_called_once_with(telegram_id)
        mock_bot.send_message.assert_called_once()

        # Verify message content includes welcome and email prompt
        sent_message = mock_bot.send_message.call_args[1]["text"]
        assert "welcome" in sent_message.lower() or "hey" in sent_message.lower()
        assert "email" in sent_message.lower()

    @pytest.mark.asyncio
    async def test_ac_t009_2_handle_start_existing_user(
        self, handler, mock_user_repository, mock_bot
    ):
        """
        AC-T009.2: _handle_start() checks if user exists, initiates registration.

        Verifies that existing users get welcome back message.
        """
        # Arrange
        telegram_id = 123456789
        chat_id = 123456789
        message = {
            "message_id": 1,
            "from": {"id": telegram_id, "first_name": "Alex"},
            "chat": {"id": chat_id, "type": "private"},
            "text": "/start",
        }

        # Mock: User exists
        mock_user = MagicMock(spec=User)
        mock_user.id = uuid4()
        mock_user.telegram_id = telegram_id
        mock_user.chapter = 2
        mock_user_repository.get_by_telegram_id.return_value = mock_user

        # Act
        await handler.handle(message)

        # Assert
        mock_user_repository.get_by_telegram_id.assert_called_once_with(telegram_id)
        mock_bot.send_message.assert_called_once()

        # Verify message is a welcome back (not registration prompt)
        sent_message = mock_bot.send_message.call_args[1]["text"]
        assert "back" in sent_message.lower() or "again" in sent_message.lower()

    @pytest.mark.asyncio
    async def test_ac_t009_3_handle_help_returns_commands(self, handler, mock_bot):
        """
        AC-T009.3: _handle_help() returns available commands.

        Verifies that help command lists all available bot commands.
        """
        # Arrange
        message = {
            "message_id": 1,
            "from": {"id": 123456789, "first_name": "Test"},
            "chat": {"id": 123456789, "type": "private"},
            "text": "/help",
        }

        # Act
        await handler.handle(message)

        # Assert
        mock_bot.send_message.assert_called_once()
        help_text = mock_bot.send_message.call_args[1]["text"]

        # Verify all commands are listed
        assert "/start" in help_text
        assert "/help" in help_text
        assert "/status" in help_text
        assert "/call" in help_text

    @pytest.mark.asyncio
    async def test_ac_t009_4_handle_status_returns_chapter_score(
        self, handler, mock_user_repository, mock_bot
    ):
        """
        AC-T009.4: _handle_status() returns chapter/score hint.

        Verifies that status command shows current game state.
        """
        # Arrange
        telegram_id = 123456789
        chat_id = 123456789
        message = {
            "message_id": 1,
            "from": {"id": telegram_id, "first_name": "Test"},
            "chat": {"id": chat_id, "type": "private"},
            "text": "/status",
        }

        # Mock: User exists with specific state
        mock_user = MagicMock(spec=User)
        mock_user.id = uuid4()
        mock_user.telegram_id = telegram_id
        mock_user.chapter = 3
        mock_user.relationship_score = Decimal("75.50")
        mock_user_repository.get_by_telegram_id.return_value = mock_user

        # Act
        await handler.handle(message)

        # Assert
        mock_bot.send_message.assert_called_once()
        status_text = mock_bot.send_message.call_args[1]["text"]

        # Verify chapter mentioned
        assert "3" in status_text or "chapter 3" in status_text.lower()

        # Should include score hint (not exact number, per game design)
        assert any(
            word in status_text.lower()
            for word in ["good", "great", "strong", "solid", "warm", "hot"]
        )

    @pytest.mark.asyncio
    async def test_ac_t009_5_unknown_commands_handled_gracefully(
        self, handler, mock_bot
    ):
        """
        AC-T009.5: Unknown commands handled gracefully.

        Verifies that unrecognized commands get helpful response.
        """
        # Arrange
        message = {
            "message_id": 1,
            "from": {"id": 123456789, "first_name": "Test"},
            "chat": {"id": 123456789, "type": "private"},
            "text": "/unknown_command",
        }

        # Act
        await handler.handle(message)

        # Assert
        mock_bot.send_message.assert_called_once()
        response = mock_bot.send_message.call_args[1]["text"]

        # Should be helpful, not error message
        assert any(
            word in response.lower()
            for word in ["help", "try", "command", "don't", "what"]
        )

    @pytest.mark.asyncio
    async def test_command_with_bot_username(self, handler):
        """
        Verify commands work with @botname suffix (e.g., /start@NikitaBot).

        Telegram allows commands like /start@botname in group chats.
        """
        # Arrange
        message = {
            "message_id": 1,
            "from": {"id": 123456789, "first_name": "Test"},
            "chat": {"id": 123456789, "type": "private"},
            "text": "/start@NikitaBot",
        }

        # Act
        with patch.object(handler, '_handle_start') as mock_start:
            await handler.handle(message)

            # Assert - should route to start handler despite @botname
            mock_start.assert_called_once()

    @pytest.mark.asyncio
    async def test_status_command_unregistered_user(
        self, handler, mock_user_repository, mock_bot
    ):
        """
        Verify /status for unregistered user prompts registration.
        """
        # Arrange
        telegram_id = 123456789
        message = {
            "message_id": 1,
            "from": {"id": telegram_id, "first_name": "Test"},
            "chat": {"id": telegram_id, "type": "private"},
            "text": "/status",
        }

        # Mock: User doesn't exist
        mock_user_repository.get_by_telegram_id.return_value = None

        # Act
        await handler.handle(message)

        # Assert
        mock_bot.send_message.assert_called_once()
        response = mock_bot.send_message.call_args[1]["text"]

        # Should prompt to start registration
        assert "/start" in response or "register" in response.lower()
