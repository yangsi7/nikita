"""Tests for deprecated Telegram auth_confirm endpoint.

The magic link auth flow has been removed (GH #59, #60).
The endpoint now returns 410 Gone for all requests.
"""

import pytest
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient


class TestAuthConfirmDeprecated:
    """Test suite for deprecated /auth/confirm endpoint — returns 410 Gone."""

    @pytest.fixture
    def app(self):
        """Create test FastAPI app with mocked dependencies."""
        from nikita.api.routes.telegram import create_telegram_router
        from nikita.platforms.telegram.bot import TelegramBot

        app = FastAPI()
        mock_bot = MagicMock(spec=TelegramBot)
        app.state.telegram_bot = mock_bot

        router = create_telegram_router(bot=mock_bot)
        app.include_router(router, prefix="/api/v1/telegram")
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_auth_confirm_returns_410_gone(self, client):
        """GET /auth/confirm with no params returns 410 Gone."""
        response = client.get("/api/v1/telegram/auth/confirm")

        assert response.status_code == 410
        body = response.json()
        assert body["status"] == "gone"
        assert "deprecated" in body["message"].lower()

    def test_auth_confirm_with_code_returns_410(self, client):
        """GET /auth/confirm?code=xyz still returns 410 (ignores params)."""
        response = client.get(
            "/api/v1/telegram/auth/confirm",
            params={"code": "some_pkce_code"},
        )

        assert response.status_code == 410
        body = response.json()
        assert body["status"] == "gone"

    def test_auth_confirm_with_access_token_returns_410(self, client):
        """GET /auth/confirm?access_token=jwt still returns 410."""
        response = client.get(
            "/api/v1/telegram/auth/confirm",
            params={"access_token": "eyJhbGciOiJIUzI1NiJ9.fake"},
        )

        assert response.status_code == 410
        body = response.json()
        assert body["status"] == "gone"

    def test_auth_confirm_with_error_params_returns_410(self, client):
        """GET /auth/confirm?error=access_denied still returns 410."""
        response = client.get(
            "/api/v1/telegram/auth/confirm",
            params={
                "error": "access_denied",
                "error_code": "otp_expired",
                "error_description": "The magic link has expired",
            },
        )

        assert response.status_code == 410
        body = response.json()
        assert body["status"] == "gone"

    def test_auth_confirm_response_body_has_otp_message(self, client):
        """Response body instructs users to use OTP in Telegram."""
        response = client.get("/api/v1/telegram/auth/confirm")

        body = response.json()
        assert "OTP" in body["message"]
        assert "Telegram" in body["message"]

    def test_auth_confirm_content_type_is_json(self, client):
        """Response content-type is JSON, not HTML."""
        response = client.get("/api/v1/telegram/auth/confirm")

        assert "application/json" in response.headers["content-type"]
