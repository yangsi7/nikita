"""Tests for TelegramBot client - WRITTEN FIRST (TDD Red phase).

These tests are written BEFORE implementation to verify TDD approach.
Tests should FAIL initially, proving they are valid.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from nikita.platforms.telegram.bot import TelegramBot


class TestTelegramBot:
    """Test suite for Telegram Bot API client."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing."""
        settings = MagicMock()
        settings.telegram_bot_token = "test-bot-token-123"
        return settings

    @pytest.fixture
    def bot(self, mock_settings):
        """Create TelegramBot instance with mocked settings."""
        with patch("nikita.platforms.telegram.bot.get_settings", return_value=mock_settings):
            return TelegramBot()

    @pytest.mark.asyncio
    async def test_ac_t004_1_send_message_with_parse_mode(self, bot):
        """
        AC-T004.1: send_message(chat_id, text) method with parse_mode support.

        Verifies that the bot can send text messages to users with HTML formatting.
        """
        # Arrange
        chat_id = 123456789
        text = "<b>Hello</b> from Nikita"
        parse_mode = "HTML"

        expected_response = {
            "ok": True,
            "result": {
                "message_id": 1,
                "chat": {"id": chat_id},
                "text": text
            }
        }

        # Mock the HTTP client
        bot.client = AsyncMock()
        bot.client.post = AsyncMock(return_value=MagicMock(
            status_code=200,
            json=lambda: expected_response
        ))

        # Act - escape=False to allow intentional HTML formatting
        result = await bot.send_message(chat_id, text, parse_mode=parse_mode, escape=False)

        # Assert
        assert result == expected_response
        bot.client.post.assert_called_once()
        call_kwargs = bot.client.post.call_args[1]
        assert "sendMessage" in bot.client.post.call_args[0][0]
        assert call_kwargs["json"]["chat_id"] == chat_id
        assert call_kwargs["json"]["text"] == text
        assert call_kwargs["json"]["parse_mode"] == parse_mode

    @pytest.mark.asyncio
    async def test_ac_t004_2_send_chat_action_typing(self, bot):
        """
        AC-T004.2: send_chat_action(chat_id, action) for typing indicator.

        Verifies that the bot can send typing indicators to simulate human behavior.
        """
        # Arrange
        chat_id = 123456789
        action = "typing"

        expected_response = {"ok": True}

        # Mock the HTTP client
        bot.client = AsyncMock()
        bot.client.post = AsyncMock(return_value=MagicMock(
            status_code=200,
            json=lambda: expected_response
        ))

        # Act
        result = await bot.send_chat_action(chat_id, action)

        # Assert
        assert result == expected_response
        bot.client.post.assert_called_once()
        call_kwargs = bot.client.post.call_args[1]
        assert "sendChatAction" in bot.client.post.call_args[0][0]
        assert call_kwargs["json"]["chat_id"] == chat_id
        assert call_kwargs["json"]["action"] == action

    @pytest.mark.asyncio
    async def test_ac_t004_3_set_webhook(self, bot):
        """
        AC-T004.3: set_webhook(url) to configure webhook.

        Verifies that the bot can configure its webhook URL for receiving updates.
        """
        # Arrange
        webhook_url = "https://example.com/webhook"

        expected_response = {
            "ok": True,
            "result": True,
            "description": "Webhook was set"
        }

        # Mock the HTTP client
        bot.client = AsyncMock()
        bot.client.post = AsyncMock(return_value=MagicMock(
            status_code=200,
            json=lambda: expected_response
        ))

        # Act
        result = await bot.set_webhook(webhook_url)

        # Assert
        assert result == expected_response
        bot.client.post.assert_called_once()
        call_kwargs = bot.client.post.call_args[1]
        assert "setWebhook" in bot.client.post.call_args[0][0]
        assert call_kwargs["json"]["url"] == webhook_url

    @pytest.mark.asyncio
    async def test_ac_t004_4_uses_httpx_async_client(self, bot):
        """
        AC-T004.4: Uses httpx AsyncClient for async requests.

        Verifies that the bot uses httpx for asynchronous HTTP operations.
        """
        # Assert
        from httpx import AsyncClient
        assert isinstance(bot.client, AsyncClient)
        assert hasattr(bot.client, "post")
        assert hasattr(bot.client, "get")

    @pytest.mark.asyncio
    async def test_ac_t004_5_handles_telegram_api_errors_gracefully(self, bot):
        """
        AC-T004.5: Handles Telegram API errors gracefully.

        Verifies that the bot properly handles and reports API errors.
        """
        # Arrange
        chat_id = 123456789
        text = "Test message"

        error_response = {
            "ok": False,
            "error_code": 400,
            "description": "Bad Request: chat not found"
        }

        # Mock the HTTP client to return an error
        bot.client = AsyncMock()
        bot.client.post = AsyncMock(return_value=MagicMock(
            status_code=400,
            json=lambda: error_response
        ))

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await bot.send_message(chat_id, text)

        # Verify error contains useful information
        assert "400" in str(exc_info.value) or "Bad Request" in str(exc_info.value)
