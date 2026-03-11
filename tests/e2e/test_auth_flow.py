"""
E2E Tests for Auth Confirm Endpoint (DEPRECATED)

Validates the deprecated auth/confirm endpoint returns 410 Gone.
Uses ASGI transport (no live Cloud Run dependency).
"""

import pytest
from httpx import ASGITransport, AsyncClient

from nikita.api.main import app

pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]


class TestAuthConfirmDeprecated:
    """Verify auth/confirm endpoint returns 410 Gone after deprecation (SF-1)."""

    async def test_auth_confirm_returns_410_gone(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/telegram/auth/confirm")
            assert response.status_code == 410
            data = response.json()
            assert data["status"] == "gone"
            assert "deprecated" in data["message"].lower()

    async def test_auth_confirm_with_params_returns_410(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/telegram/auth/confirm?error_code=otp_expired")
            assert response.status_code == 410

    async def test_auth_confirm_post_returns_method_not_allowed(self):
        """POST is not supported — only GET was defined for the deprecated endpoint."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/telegram/auth/confirm", json={"code": "123456"})
            assert response.status_code == 405
