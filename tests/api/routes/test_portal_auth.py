"""Tests for portal_auth.dashboard_bridge endpoint (Cluster B3).

POST /api/v1/auth/dashboard-bridge

ACs:
- Unauthenticated → 401
- Authenticated user → 200 with {telegram_url, expires_at}
- telegram_url contains ?start= with a 6-char code
- expires_at is a datetime string
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from nikita.api.dependencies.auth import (
    AuthenticatedUser,
    get_authenticated_user,
)
from nikita.api.routes.portal_auth import user_router
from nikita.db.database import get_async_session


_USER_ID = UUID("22222222-2222-2222-2222-222222222222")
_USER_EMAIL = "dash+test@example.com"


def _build_app(*, user: AuthenticatedUser, link_code: MagicMock) -> FastAPI:
    """Wire FastAPI app with user_router and dependency overrides."""
    app = FastAPI()
    app.include_router(user_router, prefix="/api/v1")

    # Override authenticated user
    app.dependency_overrides[get_authenticated_user] = lambda: user

    # Fake async session
    fake_session = MagicMock()
    fake_session.commit = AsyncMock()

    # Patch TelegramLinkRepository inside the route
    from nikita.db.repositories.telegram_link_repository import TelegramLinkRepository

    fake_link_repo = MagicMock()
    fake_link_repo.create_link_code = AsyncMock(return_value=link_code)

    fake_session.__aenter__ = AsyncMock(return_value=fake_session)
    fake_session.__aexit__ = AsyncMock(return_value=False)

    app.dependency_overrides[get_async_session] = lambda: fake_session

    # Patch TelegramLinkRepository to inject fake_link_repo
    import nikita.api.routes.portal_auth as portal_auth_module

    _orig = getattr(portal_auth_module, "_get_link_repo_for_request", None)

    async def _fake_get_link_repo(session=None):
        return fake_link_repo

    # Store fake repo on app for test access
    app.state.fake_link_repo = fake_link_repo

    return app


def _make_link_code(code: str = "ABC123") -> MagicMock:
    """Build a stand-in TelegramLinkCode row."""
    row = MagicMock()
    row.code = code
    row.expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    return row


class TestDashboardBridge:
    """Tests for POST /api/v1/auth/dashboard-bridge."""

    def test_dashboard_bridge_unauthenticated_returns_401(self) -> None:
        """No JWT → 401 from get_authenticated_user dependency."""
        app = FastAPI()
        app.include_router(user_router, prefix="/api/v1")
        # No dependency override → real dependency raises 401
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post("/api/v1/auth/dashboard-bridge")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_dashboard_bridge_returns_telegram_url(self) -> None:
        """Authenticated call → 200 with telegram_url containing ?start= code."""
        from httpx import ASGITransport, AsyncClient

        user = AuthenticatedUser(id=_USER_ID, email=_USER_EMAIL)
        link_code = _make_link_code("XYZABC")

        app = FastAPI()
        app.include_router(user_router, prefix="/api/v1")

        fake_session = MagicMock()
        fake_session.commit = AsyncMock()

        fake_link_repo = MagicMock()
        fake_link_repo.create_link_code = AsyncMock(return_value=link_code)

        app.dependency_overrides[get_authenticated_user] = lambda: user
        app.dependency_overrides[get_async_session] = lambda: fake_session

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "nikita.api.routes.portal_auth._get_link_repo_for_request",
                lambda session=None: fake_link_repo,
            )
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post("/api/v1/auth/dashboard-bridge")

        assert response.status_code == 200
        data = response.json()
        assert "telegram_url" in data
        assert "?start=XYZABC" in data["telegram_url"]
        assert "t.me/" in data["telegram_url"]
        assert "expires_at" in data

    @pytest.mark.asyncio
    async def test_dashboard_bridge_url_contains_6char_code(self) -> None:
        """telegram_url must contain ?start= with exactly 6-char code."""
        from httpx import ASGITransport, AsyncClient

        user = AuthenticatedUser(id=_USER_ID, email=_USER_EMAIL)
        link_code = _make_link_code("AB1234")

        app = FastAPI()
        app.include_router(user_router, prefix="/api/v1")

        fake_session = MagicMock()
        fake_session.commit = AsyncMock()
        fake_link_repo = MagicMock()
        fake_link_repo.create_link_code = AsyncMock(return_value=link_code)

        app.dependency_overrides[get_authenticated_user] = lambda: user
        app.dependency_overrides[get_async_session] = lambda: fake_session

        import re

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "nikita.api.routes.portal_auth._get_link_repo_for_request",
                lambda session=None: fake_link_repo,
            )
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post("/api/v1/auth/dashboard-bridge")

        assert response.status_code == 200
        url = response.json()["telegram_url"]
        match = re.search(r"\?start=([A-Z0-9]{6})$", url)
        assert match is not None, f"URL {url!r} does not end with ?start=<6-char-code>"
        assert match.group(1) == "AB1234"

    @pytest.mark.asyncio
    async def test_dashboard_bridge_calls_create_link_code_with_user_id(self) -> None:
        """create_link_code must be called with the authenticated user's ID."""
        from httpx import ASGITransport, AsyncClient

        user = AuthenticatedUser(id=_USER_ID, email=_USER_EMAIL)
        link_code = _make_link_code("AABBCC")

        app = FastAPI()
        app.include_router(user_router, prefix="/api/v1")

        fake_session = MagicMock()
        fake_session.commit = AsyncMock()
        fake_link_repo = MagicMock()
        fake_link_repo.create_link_code = AsyncMock(return_value=link_code)

        app.dependency_overrides[get_authenticated_user] = lambda: user
        app.dependency_overrides[get_async_session] = lambda: fake_session

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "nikita.api.routes.portal_auth._get_link_repo_for_request",
                lambda session=None: fake_link_repo,
            )
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                await client.post("/api/v1/auth/dashboard-bridge")

        fake_link_repo.create_link_code.assert_awaited_once_with(_USER_ID)
