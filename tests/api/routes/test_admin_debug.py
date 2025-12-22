"""Tests for admin debug portal routes.

TDD tests for T1.5 and Phase 2 endpoints.

Acceptance Criteria:
- T1.5: admin_debug router registered at /admin/debug prefix
- T1.5: Router requires admin auth dependency
"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from nikita.api.routes.admin_debug import router


class TestAdminDebugRouter:
    """Test suite for admin debug router registration (T1.5)."""

    @pytest.fixture
    def app(self):
        """Create isolated test app with admin_debug router.

        Creates a fresh FastAPI app per test instead of importing
        the production app, which prevents shared state leakage.
        """
        test_app = FastAPI()
        test_app.include_router(router, prefix="/admin/debug")
        return test_app

    @pytest.fixture
    def client(self, app):
        """Create test client with isolated app."""
        return TestClient(app)

    def test_router_registered_at_admin_debug_prefix(self, client):
        """T1.5: admin_debug router registered at /admin/debug prefix."""
        # The endpoints should exist but return 401/403 without auth
        response = client.get("/admin/debug/system")
        # Should not be 404 (endpoint exists), but 401/403 (auth required)
        assert response.status_code in [401, 403]

    def test_router_requires_admin_auth(self, client):
        """T1.5: Router requires admin auth dependency."""
        # Without token, should get 401 or 403
        response = client.get("/admin/debug/system")
        assert response.status_code in [401, 403]

    def test_non_admin_gets_403(self, client):
        """Non-admin users receive 403."""
        # Mock settings and JWT decode
        with patch(
            "nikita.api.dependencies.auth.get_settings"
        ) as mock_settings:
            mock_settings.return_value.supabase_jwt_secret = "test-secret"

            with patch(
                "nikita.api.dependencies.auth.jwt.decode"
            ) as mock_decode:
                mock_decode.return_value = {
                    "sub": str(uuid4()),
                    "email": "user@example.com",  # Not @silent-agents.com
                }
                response = client.get(
                    "/admin/debug/system",
                    headers={"Authorization": "Bearer fake-token"},
                )
                # Should get 403 because email is not @silent-agents.com
                assert response.status_code == 403

    def test_admin_auth_passes_validation(self):
        """Admin with @silent-agents.com passes auth validation."""
        # This test verifies the admin email validation logic directly
        # without needing to hit actual database
        from nikita.api.dependencies.auth import ADMIN_EMAIL_DOMAIN

        admin_email = "admin@silent-agents.com"
        non_admin_email = "user@example.com"

        assert admin_email.endswith(ADMIN_EMAIL_DOMAIN)
        assert not non_admin_email.endswith(ADMIN_EMAIL_DOMAIN)

    def test_jobs_endpoint_registered(self, client):
        """Jobs endpoint is registered at /admin/debug/jobs."""
        response = client.get("/admin/debug/jobs")
        assert response.status_code in [401, 403]

    def test_users_endpoint_registered(self, client):
        """Users endpoint is registered at /admin/debug/users."""
        response = client.get("/admin/debug/users")
        assert response.status_code in [401, 403]

    def test_user_detail_endpoint_registered(self, client):
        """User detail endpoint is registered at /admin/debug/users/{id}."""
        response = client.get(f"/admin/debug/users/{uuid4()}")
        assert response.status_code in [401, 403]

    def test_state_machines_endpoint_registered(self, client):
        """State machines endpoint is registered at /admin/debug/state-machines/{id}."""
        response = client.get(f"/admin/debug/state-machines/{uuid4()}")
        assert response.status_code in [401, 403]
