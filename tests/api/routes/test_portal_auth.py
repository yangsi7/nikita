"""Tests for portal_auth.dashboard_bridge endpoint (Cluster B3).

POST /api/v1/auth/dashboard-bridge

ACs:
- Unauthenticated → 401
- Authenticated user → 200 with {telegram_url, expires_at}
- telegram_url contains ?start= with a 6-char code
- create_link_code is called with the authenticated user's ID
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from nikita.api.dependencies.auth import (
    AuthenticatedUser,
    get_authenticated_user,
)
from nikita.api.routes.portal_auth import (
    user_router,
    _get_link_repo_for_request,
    _get_user_repo_for_request,
)
from nikita.db.database import get_async_session


_USER_ID = UUID("22222222-2222-2222-2222-222222222222")
_USER_EMAIL = "dash+test@example.com"


def _make_link_code(code: str = "ABC123") -> MagicMock:
    """Build a stand-in TelegramLinkCode row."""
    row = MagicMock()
    row.code = code
    row.expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    return row


def _build_app(
    *,
    user: AuthenticatedUser,
    link_code: MagicMock,
    user_row: MagicMock | None = None,
) -> FastAPI:
    """Wire FastAPI app with user_router and dependency overrides.

    user_row: the object returned by fake_user_repo.get().  Defaults to
    None, which means the already-bound guard (telegram_id IS NOT NULL)
    falls through and the mint path is exercised — preserving the
    semantics of all pre-existing tests that don't need to set telegram_id.
    """
    app = FastAPI()
    app.include_router(user_router, prefix="/api/v1")

    fake_link_repo = MagicMock()
    # No active code → force mint path (tests the mint scenario)
    fake_link_repo.get_active_for_user = AsyncMock(return_value=None)
    fake_link_repo.create_link_code = AsyncMock(return_value=link_code)

    fake_user_repo = AsyncMock()
    fake_user_repo.get = AsyncMock(return_value=user_row)

    app.dependency_overrides[get_authenticated_user] = lambda: user
    app.dependency_overrides[_get_link_repo_for_request] = lambda: fake_link_repo
    app.dependency_overrides[_get_user_repo_for_request] = lambda: fake_user_repo

    return app, fake_link_repo


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
        user = AuthenticatedUser(id=_USER_ID, email=_USER_EMAIL)
        link_code = _make_link_code("XYZABC")

        app, _ = _build_app(user=user, link_code=link_code)

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
        import re

        user = AuthenticatedUser(id=_USER_ID, email=_USER_EMAIL)
        link_code = _make_link_code("AB1234")

        app, _ = _build_app(user=user, link_code=link_code)

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
        user = AuthenticatedUser(id=_USER_ID, email=_USER_EMAIL)
        link_code = _make_link_code("AABBCC")

        app, fake_link_repo = _build_app(user=user, link_code=link_code)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            await client.post("/api/v1/auth/dashboard-bridge")

        fake_link_repo.create_link_code.assert_awaited_once_with(_USER_ID)


# ---------------------------------------------------------------------------
# Fix #1 — rate-limit: reuse unexpired code, don't mint new one each call
# ---------------------------------------------------------------------------


class TestDashboardBridgeRateLimit:
    """dashboard_bridge should reuse an unexpired code rather than minting."""

    @pytest.mark.asyncio
    async def test_reuses_existing_unexpired_code(self) -> None:
        """If an active code exists for user, return it without minting new."""
        user = AuthenticatedUser(id=_USER_ID, email=_USER_EMAIL)
        existing = _make_link_code("EXIST1")

        app, fake_link_repo = _build_app(
            user=user, link_code=_make_link_code("NEW111")
        )
        # Override the default None → simulate an already-active code
        fake_link_repo.get_active_for_user = AsyncMock(return_value=existing)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/v1/auth/dashboard-bridge")

        assert response.status_code == 200
        data = response.json()
        assert "?start=EXIST1" in data["telegram_url"]
        # create_link_code must NOT have been called (reuse path)
        fake_link_repo.create_link_code.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_mints_new_code_when_no_active_code(self) -> None:
        """If no active code exists, a new one is minted (original path)."""
        user = AuthenticatedUser(id=_USER_ID, email=_USER_EMAIL)
        new_code = _make_link_code("MINTED")

        app, fake_link_repo = _build_app(user=user, link_code=new_code)
        # _build_app already sets get_active_for_user=None; explicit for clarity
        fake_link_repo.get_active_for_user = AsyncMock(return_value=None)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/v1/auth/dashboard-bridge")

        assert response.status_code == 200
        data = response.json()
        assert "?start=MINTED" in data["telegram_url"]
        fake_link_repo.create_link_code.assert_awaited_once_with(_USER_ID)


# ---------------------------------------------------------------------------
# Spec 219 C1 — already-bound guard (R2)
# ---------------------------------------------------------------------------


class TestDashboardBridgeAlreadyBound:
    """Spec 219 C1 R2: dashboard_bridge returns already_bound status when
    the user already has telegram_id bound, so the FE can skip the CTA.

    RED: these tests fail until portal_auth.py adds UserRepository injection
    and returns {"status": "already_bound", "telegram_url": null, "expires_at": null}.
    """

    @pytest.mark.asyncio
    async def test_dashboard_bridge_returns_already_bound_status_when_bound(
        self,
    ) -> None:
        """User with telegram_id IS NOT NULL → 200 {"status": "already_bound"}.

        The FE reads status == "already_bound" and hides the "Chat on Telegram"
        CTA instead of showing a now-unnecessary deep-link.
        """
        from unittest.mock import MagicMock
        from nikita.db.models.user import User

        user = AuthenticatedUser(id=_USER_ID, email=_USER_EMAIL)

        app = FastAPI()
        app.include_router(user_router, prefix="/api/v1")

        fake_link_repo = MagicMock()
        fake_link_repo.get_active_for_user = AsyncMock(return_value=None)
        fake_link_repo.create_link_code = AsyncMock(return_value=_make_link_code())

        # User row with telegram_id already set
        bound_user = MagicMock(spec=User)
        bound_user.telegram_id = 987654321

        fake_user_repo = AsyncMock()
        fake_user_repo.get = AsyncMock(return_value=bound_user)

        app.dependency_overrides[get_authenticated_user] = lambda: user
        app.dependency_overrides[_get_link_repo_for_request] = lambda: fake_link_repo
        app.dependency_overrides[_get_user_repo_for_request] = lambda: fake_user_repo

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/v1/auth/dashboard-bridge")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "already_bound"
        assert data["telegram_url"] is None
        assert data["expires_at"] is None
        # Must NOT have created a new link code
        fake_link_repo.create_link_code.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_dashboard_bridge_mints_link_when_not_yet_bound(self) -> None:
        """User with telegram_id IS NULL → normal mint path (not already_bound)."""
        from unittest.mock import MagicMock
        from nikita.db.models.user import User

        user = AuthenticatedUser(id=_USER_ID, email=_USER_EMAIL)
        link_code = _make_link_code("FRESH1")

        app = FastAPI()
        app.include_router(user_router, prefix="/api/v1")

        fake_link_repo = MagicMock()
        fake_link_repo.get_active_for_user = AsyncMock(return_value=None)
        fake_link_repo.create_link_code = AsyncMock(return_value=link_code)

        # User row with telegram_id NOT set
        unbound_user = MagicMock(spec=User)
        unbound_user.telegram_id = None

        fake_user_repo = AsyncMock()
        fake_user_repo.get = AsyncMock(return_value=unbound_user)

        app.dependency_overrides[get_authenticated_user] = lambda: user
        app.dependency_overrides[_get_link_repo_for_request] = lambda: fake_link_repo
        app.dependency_overrides[_get_user_repo_for_request] = lambda: fake_user_repo

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/v1/auth/dashboard-bridge")

        assert response.status_code == 200
        data = response.json()
        assert data.get("status") != "already_bound"
        assert data["telegram_url"] is not None
        assert "?start=FRESH1" in data["telegram_url"]
