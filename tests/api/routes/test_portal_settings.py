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

from nikita.api.routes.portal import router


class TestPortalSettings:
    """Test suite for portal settings endpoints (T44)."""

    @pytest.fixture
    def app(self):
        """Create isolated test app with portal router."""
        test_app = FastAPI()
        test_app.include_router(router, prefix="/portal")
        return test_app

    @pytest.fixture
    def client(self, app):
        """Create test client with isolated app."""
        return TestClient(app)

    @pytest.fixture
    def mock_user_id(self):
        """Create a mock user ID."""
        return uuid4()

    @pytest.fixture
    def mock_user(self, mock_user_id):
        """Create a mock user with settings."""
        user = AsyncMock()
        user.id = mock_user_id
        user.timezone = "Europe/Zurich"
        user.notifications_enabled = True
        # Mock email from auth token or Supabase
        return user

    def test_get_settings_endpoint_exists(self, client):
        """Settings endpoint is registered at /portal/settings."""
        response = client.get("/portal/settings")
        # Should return 401/403 without auth, not 404
        assert response.status_code in [401, 403]

    def test_get_settings_requires_auth(self, client):
        """GET /settings requires authentication."""
        response = client.get("/portal/settings")
        assert response.status_code in [401, 403]

    def test_get_settings_returns_preferences(self, client, mock_user_id, mock_user):
        """AC-T44.1: GET /settings returns user timezone and notification preferences."""
        with patch(
            "nikita.api.dependencies.auth.get_settings"
        ) as mock_settings:
            mock_settings.return_value.supabase_jwt_secret = "test-secret"

            with patch(
                "nikita.api.dependencies.auth.jwt.decode"
            ) as mock_decode:
                mock_decode.return_value = {
                    "sub": str(mock_user_id),
                    "email": "user@example.com",
                }

                with patch(
                    "nikita.api.routes.portal.UserRepository"
                ) as mock_repo_class:
                    mock_repo = AsyncMock()
                    mock_repo.get.return_value = mock_user
                    mock_repo_class.return_value = mock_repo

                    response = client.get(
                        "/portal/settings",
                        headers={"Authorization": "Bearer fake-token"},
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert data["timezone"] == "Europe/Zurich"
                    assert data["notifications_enabled"] is True

    def test_update_settings_endpoint_exists(self, client):
        """Update settings endpoint is registered at PUT /portal/settings."""
        response = client.put("/portal/settings", json={})
        # Should return 401/403 without auth, not 404/405
        assert response.status_code in [401, 403, 422]

    def test_update_settings_requires_auth(self, client):
        """PUT /settings requires authentication."""
        response = client.put("/portal/settings", json={"timezone": "UTC"})
        assert response.status_code in [401, 403]

    def test_update_timezone_valid(self, client, mock_user_id, mock_user):
        """AC-T44.2: User can update timezone from dropdown."""
        with patch(
            "nikita.api.dependencies.auth.get_settings"
        ) as mock_settings:
            mock_settings.return_value.supabase_jwt_secret = "test-secret"

            with patch(
                "nikita.api.dependencies.auth.jwt.decode"
            ) as mock_decode:
                mock_decode.return_value = {
                    "sub": str(mock_user_id),
                    "email": "user@example.com",
                }

                with patch(
                    "nikita.api.routes.portal.UserRepository"
                ) as mock_repo_class:
                    mock_repo = AsyncMock()
                    mock_repo.get.return_value = mock_user
                    mock_repo.update_settings = AsyncMock(return_value=mock_user)
                    mock_repo_class.return_value = mock_repo

                    response = client.put(
                        "/portal/settings",
                        headers={"Authorization": "Bearer fake-token"},
                        json={"timezone": "America/New_York"},
                    )

                    assert response.status_code == 200
                    # Verify update_settings was called
                    mock_repo.update_settings.assert_called_once()

    def test_update_notifications_toggle(self, client, mock_user_id, mock_user):
        """AC-T44.3: User can toggle notifications on/off."""
        with patch(
            "nikita.api.dependencies.auth.get_settings"
        ) as mock_settings:
            mock_settings.return_value.supabase_jwt_secret = "test-secret"

            with patch(
                "nikita.api.dependencies.auth.jwt.decode"
            ) as mock_decode:
                mock_decode.return_value = {
                    "sub": str(mock_user_id),
                    "email": "user@example.com",
                }

                with patch(
                    "nikita.api.routes.portal.UserRepository"
                ) as mock_repo_class:
                    mock_repo = AsyncMock()
                    mock_repo.get.return_value = mock_user
                    mock_repo.update_settings = AsyncMock(return_value=mock_user)
                    mock_repo_class.return_value = mock_repo

                    response = client.put(
                        "/portal/settings",
                        headers={"Authorization": "Bearer fake-token"},
                        json={"notifications_enabled": False},
                    )

                    assert response.status_code == 200

    def test_update_timezone_invalid(self, client, mock_user_id, mock_user):
        """Invalid timezone should return 422 validation error."""
        with patch(
            "nikita.api.dependencies.auth.get_settings"
        ) as mock_settings:
            mock_settings.return_value.supabase_jwt_secret = "test-secret"

            with patch(
                "nikita.api.dependencies.auth.jwt.decode"
            ) as mock_decode:
                mock_decode.return_value = {
                    "sub": str(mock_user_id),
                    "email": "user@example.com",
                }

                with patch(
                    "nikita.api.routes.portal.UserRepository"
                ) as mock_repo_class:
                    mock_repo = AsyncMock()
                    mock_repo.get.return_value = mock_user
                    mock_repo_class.return_value = mock_repo

                    response = client.put(
                        "/portal/settings",
                        headers={"Authorization": "Bearer fake-token"},
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
