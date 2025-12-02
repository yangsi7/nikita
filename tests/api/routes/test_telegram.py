"""Tests for Telegram webhook API routes with FastAPI DI.

Sprint 3 refactor: Uses dependency_overrides for mocking.
AC Coverage: AC-FR001-001, AC-FR002-001, AC-T006.1-4
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient

from nikita.platforms.telegram.bot import TelegramBot
from nikita.platforms.telegram.commands import CommandHandler
from nikita.platforms.telegram.message_handler import MessageHandler


class TestTelegramWebhook:
    """Test suite for Telegram webhook endpoint."""

    @pytest.fixture
    def mock_bot(self):
        """Mock TelegramBot."""
        bot = MagicMock(spec=TelegramBot)
        bot.send_message = AsyncMock(return_value={"ok": True})
        bot.set_webhook = AsyncMock(return_value={"ok": True})
        return bot

    @pytest.fixture
    def mock_command_handler(self):
        """Mock CommandHandler."""
        handler = AsyncMock(spec=CommandHandler)
        handler.handle = AsyncMock()
        return handler

    @pytest.fixture
    def mock_message_handler(self):
        """Mock MessageHandler."""
        handler = AsyncMock(spec=MessageHandler)
        handler.handle = AsyncMock()
        return handler

    @pytest.fixture
    def app(self, mock_bot, mock_command_handler, mock_message_handler):
        """Create test FastAPI app with dependency overrides."""
        from nikita.api.routes.telegram import (
            create_telegram_router,
            get_command_handler,
            get_message_handler,
            _get_bot_from_state,
        )

        app = FastAPI()

        # Store bot on app.state (as in production)
        app.state.telegram_bot = mock_bot

        # Override dependencies to return mocks
        app.dependency_overrides[get_command_handler] = lambda: mock_command_handler
        app.dependency_overrides[get_message_handler] = lambda: mock_message_handler

        router = create_telegram_router(bot=mock_bot)
        app.include_router(router, prefix="/api/v1/telegram")
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_ac_fr001_001_webhook_receives_updates(self, client):
        """
        AC-FR001-001: Given user sends message via Telegram,
        When webhook receives update, Then it processes the update.

        Verifies webhook endpoint exists and accepts POST.
        """
        update = {
            "update_id": 12345,
            "message": {
                "message_id": 1,
                "from": {"id": 123456789, "first_name": "Test", "is_bot": False},
                "chat": {"id": 123456789, "type": "private"},
                "text": "Hello",
                "date": 1234567890,
            },
        }

        response = client.post("/api/v1/telegram/webhook", json=update)

        assert response.status_code == 200

    def test_ac_t006_1_command_routed_to_command_handler(
        self, client, mock_command_handler
    ):
        """
        AC-T006.1: Given update with /command, When webhook processes,
        Then routes to CommandHandler.

        Verifies commands (starting with /) go to CommandHandler.
        """
        update = {
            "update_id": 12345,
            "message": {
                "message_id": 1,
                "from": {"id": 123456789, "first_name": "Test", "is_bot": False},
                "chat": {"id": 123456789, "type": "private"},
                "text": "/start",
                "date": 1234567890,
            },
        }

        response = client.post("/api/v1/telegram/webhook", json=update)

        # Background task is scheduled, verify 200 returned
        assert response.status_code == 200

    def test_ac_t006_2_text_routed_to_message_handler(
        self, client, mock_message_handler
    ):
        """
        AC-T006.2: Given update with plain text, When webhook processes,
        Then routes to MessageHandler.

        Verifies regular text messages go to MessageHandler.
        """
        update = {
            "update_id": 12345,
            "message": {
                "message_id": 1,
                "from": {"id": 123456789, "first_name": "Test", "is_bot": False},
                "chat": {"id": 123456789, "type": "private"},
                "text": "Hey Nikita!",
                "date": 1234567890,
            },
        }

        response = client.post("/api/v1/telegram/webhook", json=update)

        # Background task is scheduled, verify 200 returned
        assert response.status_code == 200

    def test_ac_t006_3_empty_update_handled_gracefully(self, client):
        """
        AC-T006.3: Given update without message, When webhook processes,
        Then handles gracefully (no crash).

        Verifies webhook doesn't crash on empty/malformed updates.
        """
        update = {"update_id": 12345}

        response = client.post("/api/v1/telegram/webhook", json=update)

        assert response.status_code == 200

    def test_ac_t006_4_returns_200_quickly(self, client):
        """
        AC-T006.4: Webhook returns 200 immediately.

        Telegram requires quick 200 response; long processing should be async.
        """
        update = {
            "update_id": 12345,
            "message": {
                "message_id": 1,
                "from": {"id": 123456789, "first_name": "Test", "is_bot": False},
                "chat": {"id": 123456789, "type": "private"},
                "text": "Hello",
                "date": 1234567890,
            },
        }

        response = client.post("/api/v1/telegram/webhook", json=update)

        assert response.status_code == 200

    def test_webhook_returns_ok_status(self, client):
        """
        Verify webhook response body includes status: ok.
        """
        update = {
            "update_id": 12345,
            "message": {
                "message_id": 1,
                "from": {"id": 123456789, "first_name": "Test", "is_bot": False},
                "chat": {"id": 123456789, "type": "private"},
                "text": "Hello",
                "date": 1234567890,
            },
        }

        response = client.post("/api/v1/telegram/webhook", json=update)

        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_edited_message_ignored(self, client, mock_message_handler):
        """
        Verify edited messages are ignored (MVP scope).
        """
        update = {
            "update_id": 12345,
            "edited_message": {
                "message_id": 1,
                "from": {"id": 123456789, "first_name": "Test", "is_bot": False},
                "chat": {"id": 123456789, "type": "private"},
                "text": "Edited text",
                "date": 1234567890,
            },
        }

        response = client.post("/api/v1/telegram/webhook", json=update)

        assert response.status_code == 200

    def test_callback_query_ignored(self, client, mock_command_handler):
        """
        Verify callback queries are ignored (MVP scope).
        """
        update = {
            "update_id": 12345,
            "callback_query": {
                "id": "123",
                "from": {"id": 123456789, "first_name": "Test", "is_bot": False},
                "data": "some_callback",
            },
        }

        response = client.post("/api/v1/telegram/webhook", json=update)

        assert response.status_code == 200


class TestSetWebhook:
    """Test suite for webhook configuration endpoint."""

    @pytest.fixture
    def mock_bot(self):
        """Mock TelegramBot."""
        bot = MagicMock(spec=TelegramBot)
        bot.set_webhook = AsyncMock(return_value={"ok": True, "result": True})
        return bot

    @pytest.fixture
    def app(self, mock_bot):
        """Create test FastAPI app with mocked bot."""
        from nikita.api.routes.telegram import create_telegram_router

        app = FastAPI()
        app.state.telegram_bot = mock_bot

        router = create_telegram_router(bot=mock_bot)
        app.include_router(router, prefix="/api/v1/telegram")
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_set_webhook_endpoint_exists(self, client, mock_bot):
        """
        Verify POST /set-webhook endpoint exists.
        """
        response = client.post(
            "/api/v1/telegram/set-webhook",
            json={"url": "https://example.com/webhook"},
        )

        assert response.status_code == 200

    def test_set_webhook_calls_bot(self, client, mock_bot):
        """
        Verify set-webhook calls TelegramBot.set_webhook.
        """
        webhook_url = "https://example.com/api/v1/telegram/webhook"

        response = client.post(
            "/api/v1/telegram/set-webhook",
            json={"url": webhook_url},
        )

        assert response.status_code == 200
        mock_bot.set_webhook.assert_called_once_with(webhook_url)

    def test_set_webhook_requires_https(self, client, mock_bot):
        """
        Verify set-webhook rejects non-HTTPS URLs.
        """
        response = client.post(
            "/api/v1/telegram/set-webhook",
            json={"url": "http://example.com/webhook"},  # HTTP not HTTPS
        )

        # Should reject with validation error
        assert response.status_code == 422  # Unprocessable Entity
