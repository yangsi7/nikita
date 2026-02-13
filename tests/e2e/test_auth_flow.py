"""
E2E Tests for Auth Confirm Endpoint (DEPRECATED)

The auth/confirm endpoint was deprecated in SF-1 (2026-02-12) and now returns 410 Gone.
OTP code entry in Telegram chat is the only supported auth method.

This file validates the deprecation response is correctly returned.
"""

import os

import pytest

# Test configuration
BACKEND_URL = os.getenv(
    "NIKITA_BACKEND_URL",
    "https://nikita-api-1040094048579.us-central1.run.app",
)
AUTH_CONFIRM_URL = f"{BACKEND_URL}/api/v1/telegram/auth/confirm"


@pytest.fixture
def page():
    """Provide a simple HTTP client for testing the deprecated endpoint."""
    import httpx

    client = httpx.Client(timeout=10, follow_redirects=True)
    yield client
    client.close()


class TestAuthConfirmDeprecated:
    """Verify auth/confirm endpoint returns 410 Gone after deprecation (SF-1)."""

    def test_auth_confirm_returns_410_gone(self, page):
        """Deprecated auth/confirm returns 410 with deprecation message."""
        response = page.get(AUTH_CONFIRM_URL)
        assert response.status_code == 410
        data = response.json()
        assert data["status"] == "gone"
        assert "deprecated" in data["message"].lower()

    def test_auth_confirm_with_params_returns_410(self, page):
        """Even with query params, returns 410 Gone."""
        response = page.get(f"{AUTH_CONFIRM_URL}?error_code=otp_expired")
        assert response.status_code == 410
        data = response.json()
        assert data["status"] == "gone"

    def test_auth_confirm_with_fragment_returns_410(self, page):
        """Even with JWT fragment, returns 410 Gone (fragment not sent to server)."""
        # Note: fragments (#...) are NOT sent to the server, so this is equivalent
        # to the base URL request
        response = page.get(AUTH_CONFIRM_URL)
        assert response.status_code == 410
