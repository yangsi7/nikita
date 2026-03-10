"""Tests for portal settings endpoints.

TDD tests for T44: Settings page.

Acceptance Criteria:
- AC-T44.1: User can view current timezone, notifications preference
- AC-T44.2: User can update timezone from dropdown
- AC-T44.3: User can toggle notifications on/off
- AC-T44.4: Changes persist across sessions
"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from nikita.api.dependencies.auth import AuthenticatedUser, get_authenticated_user, get_current_user_id
from nikita.api.routes.portal import router
from nikita.db.database import get_async_session


class TestPortalSettings:
    """Test suite for portal settings endpoints (T44)."""

    @pytest.fixture
    def mock_user_id(self):
        """Create a mock user ID."""
        return uuid4()

    @pytest.fixture
    def mock_session(self):
        """Create mock async session."""
        session = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.fixture
    def mock_user(self, mock_user_id):
        """Create a mock user with settings."""
        user = AsyncMock()
        user.id = mock_user_id
        user.timezone = "Europe/Zurich"
        user.notifications_enabled = True
        user.telegram_id = None
        return user

    @pytest.fixture
    def mock_user_with_telegram(self, mock_user_id):
        """Create a mock user with Telegram linked."""
        user = AsyncMock()
        user.id = mock_user_id
        user.timezone = "UTC"
        user.notifications_enabled = True
        user.telegram_id = 123456789
        return user

    @pytest.fixture
    def mock_auth(self, mock_user_id):
        """Create mock authenticated user with email."""
        return AuthenticatedUser(id=mock_user_id, email="player@example.com")

    @pytest.fixture
    def app(self, mock_user_id, mock_session, mock_auth):
        """Create isolated test app with dependency overrides."""
        test_app = FastAPI()
        test_app.include_router(router, prefix="/portal")
        test_app.dependency_overrides[get_current_user_id] = lambda: mock_user_id
        test_app.dependency_overrides[get_authenticated_user] = lambda: mock_auth
        test_app.dependency_overrides[get_async_session] = lambda: mock_session
        return test_app

    @pytest.fixture
    def unauthed_app(self):
        """Create test app without auth override (for auth tests)."""
        test_app = FastAPI()
        test_app.include_router(router, prefix="/portal")
        return test_app

    @pytest.fixture
    def client(self, app):
        """Create test client with dependency overrides."""
        return TestClient(app)

    @pytest.fixture
    def unauthed_client(self, unauthed_app):
        """Create test client without auth override."""
        return TestClient(unauthed_app)

    def test_get_settings_endpoint_exists(self, unauthed_client):
        """Settings endpoint is registered at /portal/settings."""
        response = unauthed_client.get("/portal/settings")
        # Should return 401/403 without auth, not 404
        assert response.status_code in [401, 403]

    def test_get_settings_requires_auth(self, unauthed_client):
        """GET /settings requires authentication."""
        response = unauthed_client.get("/portal/settings")
        assert response.status_code in [401, 403]

    def test_get_settings_returns_preferences(self, client, mock_user):
        """AC-T44.1: GET /settings returns user timezone and notification preferences."""
        with patch(
            "nikita.api.routes.portal.UserRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get.return_value = mock_user
            mock_repo_class.return_value = mock_repo

            response = client.get("/portal/settings")

            assert response.status_code == 200
            data = response.json()
            assert data["timezone"] == "Europe/Zurich"
            assert data["notifications_enabled"] is True

    def test_update_settings_endpoint_exists(self, unauthed_client):
        """Update settings endpoint is registered at PUT /portal/settings."""
        response = unauthed_client.put("/portal/settings", json={})
        # Should return 401/403 without auth, not 404/405
        assert response.status_code in [401, 403, 422]

    def test_update_settings_requires_auth(self, unauthed_client):
        """PUT /settings requires authentication."""
        response = unauthed_client.put("/portal/settings", json={"timezone": "UTC"})
        assert response.status_code in [401, 403]

    def test_update_timezone_valid(self, client, mock_user):
        """AC-T44.2: User can update timezone from dropdown."""
        with patch(
            "nikita.api.routes.portal.UserRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get.return_value = mock_user
            mock_repo.update_settings = AsyncMock(return_value=mock_user)
            mock_repo_class.return_value = mock_repo

            response = client.put(
                "/portal/settings",
                json={"timezone": "America/New_York"},
            )

            assert response.status_code == 200
            mock_repo.update_settings.assert_called_once()

    def test_update_notifications_toggle(self, client, mock_user):
        """AC-T44.3: User can toggle notifications on/off."""
        with patch(
            "nikita.api.routes.portal.UserRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get.return_value = mock_user
            mock_repo.update_settings = AsyncMock(return_value=mock_user)
            mock_repo_class.return_value = mock_repo

            response = client.put(
                "/portal/settings",
                json={"notifications_enabled": False},
            )

            assert response.status_code == 200

    def test_get_settings_returns_email_from_jwt(self, client, mock_user):
        """GH #105: GET /settings returns email extracted from JWT token."""
        with patch(
            "nikita.api.routes.portal.UserRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get.return_value = mock_user
            mock_repo_class.return_value = mock_repo

            response = client.get("/portal/settings")

            assert response.status_code == 200
            data = response.json()
            assert data["email"] == "player@example.com"

    def test_get_settings_telegram_linked(self, client, mock_user_with_telegram):
        """GH #99: GET /settings returns telegram_linked=True when user has telegram_id."""
        with patch(
            "nikita.api.routes.portal.UserRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get.return_value = mock_user_with_telegram
            mock_repo_class.return_value = mock_repo

            response = client.get("/portal/settings")

            assert response.status_code == 200
            data = response.json()
            assert data["telegram_linked"] is True
            assert data["telegram_username"] is None

    def test_get_settings_telegram_not_linked(self, client, mock_user):
        """GH #99: GET /settings returns telegram_linked=False when no telegram_id."""
        with patch(
            "nikita.api.routes.portal.UserRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get.return_value = mock_user
            mock_repo_class.return_value = mock_repo

            response = client.get("/portal/settings")

            assert response.status_code == 200
            data = response.json()
            assert data["telegram_linked"] is False

    def test_update_settings_returns_telegram_linked(self, client, mock_session, mock_user_with_telegram):
        """GH #113 review: PUT /settings returns fresh telegram_linked status and refreshes session."""
        with patch("nikita.api.routes.portal.UserRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get.return_value = mock_user_with_telegram
            mock_repo.update_settings = AsyncMock(return_value=mock_user_with_telegram)
            mock_repo_class.return_value = mock_repo

            response = client.put("/portal/settings", json={"timezone": "UTC"})

            assert response.status_code == 200
            data = response.json()
            assert data["telegram_linked"] is True
            mock_session.refresh.assert_awaited_once_with(mock_user_with_telegram)

    def test_update_timezone_invalid(self, client, mock_user):
        """Invalid timezone should return 422 validation error."""
        with patch(
            "nikita.api.routes.portal.UserRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get.return_value = mock_user
            mock_repo_class.return_value = mock_repo

            response = client.put(
                "/portal/settings",
                json={"timezone": "Invalid/Timezone"},
            )

            # Should return 422 for invalid timezone
            assert response.status_code == 422


class TestSettingsSchema:
    """Test settings request/response schemas."""

    def test_valid_timezones(self):
        """Common timezones should be accepted."""
        from nikita.api.schemas.portal import UpdateSettingsRequest

        valid_timezones = [
            "UTC",
            "Europe/Zurich",
            "America/New_York",
            "Asia/Tokyo",
            "Europe/London",
        ]

        for tz in valid_timezones:
            req = UpdateSettingsRequest(timezone=tz)
            assert req.timezone == tz

    def test_settings_response_has_required_fields(self):
        """UserSettingsResponse has all required fields."""
        from nikita.api.schemas.portal import UserSettingsResponse

        response = UserSettingsResponse(
            notifications_enabled=True,
            timezone="UTC",
            email="test@example.com",
        )

        assert response.notifications_enabled is True
        assert response.timezone == "UTC"
        assert response.email == "test@example.com"

    def test_settings_response_telegram_linked_defaults(self):
        """UserSettingsResponse defaults telegram_linked=False."""
        from nikita.api.schemas.portal import UserSettingsResponse

        response = UserSettingsResponse(
            notifications_enabled=True,
            timezone="UTC",
            email=None,
        )

        assert response.telegram_linked is False
        assert response.telegram_username is None

    def test_settings_response_telegram_linked_true(self):
        """UserSettingsResponse accepts telegram_linked=True."""
        from nikita.api.schemas.portal import UserSettingsResponse

        response = UserSettingsResponse(
            notifications_enabled=True,
            timezone="UTC",
            email=None,
            telegram_linked=True,
            telegram_username=None,
        )

        assert response.telegram_linked is True
