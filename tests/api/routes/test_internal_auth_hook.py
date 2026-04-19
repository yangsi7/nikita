"""Tests for internal password-reset webhook (Spec 214 FR-11c AC-11c.12, T1.4).

POST /api/v1/internal/auth/password-reset-hook

Called by Supabase password-reset webhook to revoke all active portal
bridge tokens for the affected user. Bearer-authenticated via
TASK_AUTH_SECRET (same pattern as pg_cron endpoints in tasks.py).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from nikita.api.routes.internal import router
from nikita.db.database import get_async_session


@pytest.fixture
def app() -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/internal")
    return app


@pytest.fixture
def client(app: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


class TestPasswordResetHook:
    """AC-11c.12: Supabase password-reset → revoke all active bridge tokens.

    Security model:
    - Bearer-auth via TASK_AUTH_SECRET (same as pg_cron endpoints).
    - Wrong/missing token → 401 (no side effects).
    - Valid token + user_id → PortalBridgeTokenRepository.revoke_all_for_user
      called exactly once; response reports rows revoked.
    """

    @pytest.mark.asyncio
    async def test_missing_authorization_returns_401(
        self, app: FastAPI, client: AsyncClient
    ):
        """No Authorization header → 401. No DB call."""
        mock_repo = AsyncMock()
        fake_session = AsyncMock()

        async def _session_override():
            yield fake_session

        app.dependency_overrides[get_async_session] = _session_override
        with (
            patch(
                "nikita.api.routes.internal.PortalBridgeTokenRepository",
                return_value=mock_repo,
            ),
            patch(
                "nikita.api.routes.internal._get_task_secret",
                return_value="test-secret",
            ),
        ):
            async with client as c:
                resp = await c.post(
                    "/api/v1/internal/auth/password-reset-hook",
                    json={"user_id": str(uuid4())},
                )
        assert resp.status_code == 401
        mock_repo.revoke_all_for_user.assert_not_called()

    @pytest.mark.asyncio
    async def test_password_reset_revokes_all_active_tokens(
        self, app: FastAPI, client: AsyncClient
    ):
        """Valid Bearer + user_id → repo.revoke_all_for_user called once.

        Response body includes the row count reported by the repository.
        """
        user_id = uuid4()
        mock_repo = AsyncMock()
        mock_repo.revoke_all_for_user.return_value = 3
        fake_session = AsyncMock()

        async def _session_override():
            yield fake_session

        app.dependency_overrides[get_async_session] = _session_override
        with (
            patch(
                "nikita.api.routes.internal.PortalBridgeTokenRepository",
                return_value=mock_repo,
            ),
            patch(
                "nikita.api.routes.internal._get_task_secret",
                return_value="test-secret",
            ),
        ):
            async with client as c:
                resp = await c.post(
                    "/api/v1/internal/auth/password-reset-hook",
                    headers={"Authorization": "Bearer test-secret"},
                    json={"user_id": str(user_id)},
                )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["revoked"] == 3
        mock_repo.revoke_all_for_user.assert_awaited_once_with(user_id)
        fake_session.commit.assert_awaited_once()
