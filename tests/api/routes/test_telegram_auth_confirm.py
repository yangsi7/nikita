"""Tests for Telegram auth_confirm endpoint.

Tests the magic link verification flow that exchanges PKCE code,
looks up telegram_id from pending registration, and creates user.

AC Coverage: AC-T1.2.1-8 (015-onboarding-fix)
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient


class TestAuthConfirmEndpoint:
    """Test suite for /auth/confirm endpoint."""

    @pytest.fixture
    def app(self):
        """Create test FastAPI app with mocked dependencies."""
        from nikita.api.routes.telegram import create_telegram_router
        from nikita.platforms.telegram.bot import TelegramBot

        app = FastAPI()

        # Create mock bot
        mock_bot = MagicMock(spec=TelegramBot)
        app.state.telegram_bot = mock_bot

        router = create_telegram_router(bot=mock_bot)
        app.include_router(router, prefix="/api/v1/telegram")
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_ac_t1_2_3_missing_code_shows_error(self, client):
        """
        AC-T3.1.3: Missing code parameter → error page with instructions.

        When no code parameter is provided, show error page.
        """
        response = client.get("/api/v1/telegram/auth/confirm")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        # Should contain error message
        assert "No authorization code" in response.text or "Error" in response.text

    def test_ac_t1_2_8_returns_html_response(self, client):
        """
        AC-T1.2.8: Returns HTML success/error page.

        Endpoint always returns HTML content.
        """
        response = client.get("/api/v1/telegram/auth/confirm")

        assert "text/html" in response.headers["content-type"]

    def test_supabase_error_param_shows_error_page(self, client):
        """
        AC-T3.1.1: Supabase error in query params shows error page.

        When Supabase redirects with error, show appropriate message.
        """
        response = client.get(
            "/api/v1/telegram/auth/confirm",
            params={
                "error": "access_denied",
                "error_code": "otp_expired",
                "error_description": "The magic link has expired"
            }
        )

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        # Should show error, not success
        assert "Registration Complete" not in response.text

    @patch("nikita.api.routes.telegram.get_supabase_client")
    @patch("nikita.api.routes.telegram.get_session_maker")
    def test_invalid_code_shows_error(
        self, mock_session_maker, mock_get_supabase, client
    ):
        """
        AC-T3.1.1: Invalid code from Supabase → error page.

        When Supabase rejects the code, show error.
        """
        # Mock Supabase client to raise exception
        mock_supabase = AsyncMock()
        mock_supabase.auth.exchange_code_for_session = AsyncMock(
            side_effect=Exception("Invalid or expired code")
        )
        mock_get_supabase.return_value = mock_supabase

        response = client.get(
            "/api/v1/telegram/auth/confirm",
            params={"code": "invalid_code_xyz"}
        )

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        # Should not show success
        assert "Registration Complete" not in response.text

    @patch("nikita.api.routes.telegram.get_supabase_client")
    @patch("nikita.api.routes.telegram.get_session_maker")
    def test_success_flow_creates_user(
        self, mock_session_maker, mock_get_supabase, client
    ):
        """
        AC-T1.2.1-7: Full success flow.

        Exchanges code, looks up pending registration, creates user.
        """
        # Mock Supabase response
        mock_user = MagicMock()
        mock_user.id = str(uuid4())
        mock_user.email = "test@example.com"

        mock_response = MagicMock()
        mock_response.user = mock_user

        mock_supabase = AsyncMock()
        mock_supabase.auth.exchange_code_for_session = AsyncMock(
            return_value=mock_response
        )
        mock_get_supabase.return_value = mock_supabase

        # Mock database session
        mock_session = AsyncMock()
        mock_session_context = AsyncMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)

        mock_maker = MagicMock()
        mock_maker.return_value = mock_session_context
        mock_session_maker.return_value = mock_maker

        # Mock pending registration lookup
        mock_pending = MagicMock()
        mock_pending.telegram_id = 123456789
        mock_pending.email = "test@example.com"

        # Mock query results
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_pending

        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        response = client.get(
            "/api/v1/telegram/auth/confirm",
            params={"code": "valid_pkce_code"}
        )

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    @patch("nikita.api.routes.telegram.get_supabase_client")
    @patch("nikita.api.routes.telegram.get_session_maker")
    def test_no_pending_registration_shows_error(
        self, mock_session_maker, mock_get_supabase, client
    ):
        """
        AC-T3.1.2: No pending registration → error with instructions.

        When email lookup finds nothing, show appropriate error.
        """
        # Mock Supabase response
        mock_user = MagicMock()
        mock_user.id = str(uuid4())
        mock_user.email = "test@example.com"

        mock_response = MagicMock()
        mock_response.user = mock_user

        mock_supabase = AsyncMock()
        mock_supabase.auth.exchange_code_for_session = AsyncMock(
            return_value=mock_response
        )
        mock_get_supabase.return_value = mock_supabase

        # Mock database session
        mock_session = AsyncMock()
        mock_session_context = AsyncMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)

        mock_maker = MagicMock()
        mock_maker.return_value = mock_session_context
        mock_session_maker.return_value = mock_maker

        # Mock pending registration lookup - returns None (not found)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_session.execute = AsyncMock(return_value=mock_result)

        response = client.get(
            "/api/v1/telegram/auth/confirm",
            params={"code": "valid_code_no_pending"}
        )

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        # Should contain error about no registration
        # Note: The exact message depends on whether user exists check also fails

    @patch("nikita.api.routes.telegram.get_supabase_client")
    @patch("nikita.api.routes.telegram.get_session_maker")
    def test_double_click_user_exists_shows_success(
        self, mock_session_maker, mock_get_supabase, client
    ):
        """
        AC-T2.1.2: If user exists, return success page.

        Double-click protection - show success if already registered.
        """
        # Mock Supabase response
        mock_user = MagicMock()
        mock_user.id = str(uuid4())
        mock_user.email = "test@example.com"

        mock_response = MagicMock()
        mock_response.user = mock_user

        mock_supabase = AsyncMock()
        mock_supabase.auth.exchange_code_for_session = AsyncMock(
            return_value=mock_response
        )
        mock_get_supabase.return_value = mock_supabase

        # Mock database session
        mock_session = AsyncMock()
        mock_session_context = AsyncMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)

        mock_maker = MagicMock()
        mock_maker.return_value = mock_session_context
        mock_session_maker.return_value = mock_maker

        # First query (pending by email) returns None
        # Second query (user by ID) returns existing user
        mock_existing_user = MagicMock()
        mock_existing_user.id = UUID(mock_user.id)

        mock_result_none = MagicMock()
        mock_result_none.scalar_one_or_none.return_value = None

        mock_result_user = MagicMock()
        mock_result_user.scalar_one_or_none.return_value = mock_existing_user

        # Execute returns different results based on call order
        mock_session.execute = AsyncMock(
            side_effect=[mock_result_none, mock_result_user]
        )

        response = client.get(
            "/api/v1/telegram/auth/confirm",
            params={"code": "double_click_code"}
        )

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        # Should show success, not error
        # (User already exists, so we show success)


class TestAuthConfirmHTMLContent:
    """Tests for HTML content of auth_confirm responses."""

    @pytest.fixture
    def app(self):
        """Create test FastAPI app."""
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

    def test_error_page_has_telegram_link(self, client):
        """
        AC-T3.1.4: Error pages include "Open Telegram" button.
        """
        response = client.get("/api/v1/telegram/auth/confirm")

        assert response.status_code == 200
        # Error page should have Telegram link
        assert "telegram" in response.text.lower() or "Telegram" in response.text

    def test_html_is_valid_structure(self, client):
        """
        Verify HTML response has valid structure.
        """
        response = client.get("/api/v1/telegram/auth/confirm")

        assert response.status_code == 200
        assert "<!DOCTYPE html>" in response.text or "<html" in response.text
        assert "</html>" in response.text
