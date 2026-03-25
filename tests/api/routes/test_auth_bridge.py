"""Tests for auth bridge token exchange endpoint.

POST /api/v1/auth/exchange-bridge-token
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from nikita.api.routes.auth_bridge import router


@pytest.fixture
def app():
    """Create test FastAPI app with auth bridge router."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return app


@pytest.fixture
def client(app):
    """Create async test client."""
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    )


class TestExchangeBridgeToken:
    """Tests for POST /api/v1/auth/exchange-bridge-token."""

    @pytest.mark.asyncio
    async def test_valid_token_returns_hashed_token(self, client):
        """Valid bridge token should return hashed_token + email."""
        user_id = uuid4()

        # Mock bridge repo via dependency override
        mock_repo = AsyncMock()
        mock_repo.verify_token.return_value = (user_id, "/onboarding")

        from nikita.api.routes.auth_bridge import get_bridge_repo

        client._transport.app.dependency_overrides[get_bridge_repo] = (
            lambda: mock_repo
        )

        # Mock supabase client
        mock_supabase = AsyncMock()
        mock_auth_user = MagicMock()
        mock_auth_user.user.email = "test@example.com"
        mock_supabase.auth.admin.get_user_by_id.return_value = mock_auth_user

        mock_link_result = MagicMock()
        mock_link_result.properties.hashed_token = "abc123hash"
        mock_supabase.auth.admin.generate_link.return_value = mock_link_result

        with patch(
            "nikita.api.routes.auth_bridge.get_supabase_client",
            return_value=mock_supabase,
        ):
            response = await client.post(
                "/api/v1/auth/exchange-bridge-token",
                json={"token": "valid-bridge-token"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["hashed_token"] == "abc123hash"
        assert data["email"] == "test@example.com"
        assert data["redirect_path"] == "/onboarding"

        client._transport.app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_invalid_token_returns_401(self, client):
        """Invalid/expired bridge token should return 401."""
        mock_repo = AsyncMock()
        mock_repo.verify_token.return_value = None

        from nikita.api.routes.auth_bridge import get_bridge_repo

        client._transport.app.dependency_overrides[get_bridge_repo] = (
            lambda: mock_repo
        )

        response = await client.post(
            "/api/v1/auth/exchange-bridge-token",
            json={"token": "invalid-token"},
        )

        assert response.status_code == 401
        assert "Invalid or expired" in response.json()["detail"]

        client._transport.app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_missing_token_returns_422(self, client):
        """Missing token field should return 422."""
        response = await client.post(
            "/api/v1/auth/exchange-bridge-token",
            json={},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_empty_body_returns_422(self, client):
        """Empty request body should return 422."""
        response = await client.post(
            "/api/v1/auth/exchange-bridge-token",
            content=b"",
            headers={"content-type": "application/json"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_supabase_error_returns_500(self, client):
        """Supabase failure should return 500."""
        user_id = uuid4()
        mock_repo = AsyncMock()
        mock_repo.verify_token.return_value = (user_id, "/onboarding")

        from nikita.api.routes.auth_bridge import get_bridge_repo

        client._transport.app.dependency_overrides[get_bridge_repo] = (
            lambda: mock_repo
        )

        with patch(
            "nikita.api.routes.auth_bridge.get_supabase_client"
        ) as mock_get_sb:
            mock_supabase = AsyncMock()
            mock_supabase.auth.admin.get_user_by_id.side_effect = Exception(
                "Supabase down"
            )
            mock_get_sb.return_value = mock_supabase

            response = await client.post(
                "/api/v1/auth/exchange-bridge-token",
                json={"token": "valid-token"},
            )

            assert response.status_code == 500

        client._transport.app.dependency_overrides.clear()
