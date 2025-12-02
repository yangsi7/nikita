"""Tests for background task API routes.

T3.7: Tests for pg_cron task endpoints.
AC Coverage: Task route authentication and basic functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from nikita.api.routes.tasks import router, verify_task_secret


class TestTaskRouteAuth:
    """Test suite for task route authentication."""

    @pytest.fixture
    def app(self):
        """Create test FastAPI app with task routes."""
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/tasks")
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_decay_endpoint_exists(self, client):
        """Verify POST /decay endpoint exists."""
        # Without auth (dev mode - no secret configured)
        with patch("nikita.api.routes.tasks._get_task_secret", return_value=None):
            response = client.post("/api/v1/tasks/decay")
            assert response.status_code == 200

    def test_deliver_endpoint_exists(self, client):
        """Verify POST /deliver endpoint exists."""
        with patch("nikita.api.routes.tasks._get_task_secret", return_value=None):
            response = client.post("/api/v1/tasks/deliver")
            assert response.status_code == 200

    def test_summary_endpoint_exists(self, client):
        """Verify POST /summary endpoint exists."""
        with patch("nikita.api.routes.tasks._get_task_secret", return_value=None):
            response = client.post("/api/v1/tasks/summary")
            assert response.status_code == 200

    def test_cleanup_endpoint_exists(self, client):
        """Verify POST /cleanup endpoint exists."""
        with patch("nikita.api.routes.tasks._get_task_secret", return_value=None):
            with patch(
                "nikita.db.database.get_session_maker"
            ) as mock_session_maker:
                # Create proper async context manager mock
                mock_session = AsyncMock()
                mock_session.commit = AsyncMock()

                async_cm = AsyncMock()
                async_cm.__aenter__.return_value = mock_session
                async_cm.__aexit__.return_value = None

                mock_session_maker.return_value = MagicMock(return_value=async_cm)

                with patch(
                    "nikita.db.repositories.pending_registration_repository.PendingRegistrationRepository"
                ) as mock_repo_class:
                    mock_repo = MagicMock()
                    mock_repo.cleanup_expired = AsyncMock(return_value=5)
                    mock_repo_class.return_value = mock_repo

                    response = client.post("/api/v1/tasks/cleanup")
                    assert response.status_code == 200

    def test_auth_required_when_secret_configured(self, client):
        """Verify endpoints require auth when secret is configured."""
        with patch(
            "nikita.api.routes.tasks._get_task_secret",
            return_value="test-secret",
        ):
            # No auth header - should fail
            response = client.post("/api/v1/tasks/decay")
            assert response.status_code == 401
            assert response.json()["detail"] == "Unauthorized"

    def test_auth_succeeds_with_valid_bearer(self, client):
        """Verify auth succeeds with correct bearer token."""
        with patch(
            "nikita.api.routes.tasks._get_task_secret",
            return_value="test-secret",
        ):
            response = client.post(
                "/api/v1/tasks/decay",
                headers={"Authorization": "Bearer test-secret"},
            )
            assert response.status_code == 200

    def test_auth_fails_with_wrong_bearer(self, client):
        """Verify auth fails with incorrect bearer token."""
        with patch(
            "nikita.api.routes.tasks._get_task_secret",
            return_value="test-secret",
        ):
            response = client.post(
                "/api/v1/tasks/decay",
                headers={"Authorization": "Bearer wrong-secret"},
            )
            assert response.status_code == 401


class TestDecayEndpoint:
    """Test suite for /decay endpoint."""

    @pytest.fixture
    def app(self):
        """Create test FastAPI app."""
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/tasks")
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_decay_returns_expected_format(self, client):
        """Verify /decay returns expected response format."""
        with patch("nikita.api.routes.tasks._get_task_secret", return_value=None):
            response = client.post("/api/v1/tasks/decay")

            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert data["status"] == "ok"
            assert "affected_users" in data
            assert isinstance(data["affected_users"], int)


class TestDeliverEndpoint:
    """Test suite for /deliver endpoint."""

    @pytest.fixture
    def app(self):
        """Create test FastAPI app."""
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/tasks")
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_deliver_returns_expected_format(self, client):
        """Verify /deliver returns expected response format."""
        with patch("nikita.api.routes.tasks._get_task_secret", return_value=None):
            response = client.post("/api/v1/tasks/deliver")

            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert data["status"] == "ok"
            assert "delivered" in data
            assert isinstance(data["delivered"], int)


class TestSummaryEndpoint:
    """Test suite for /summary endpoint."""

    @pytest.fixture
    def app(self):
        """Create test FastAPI app."""
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/tasks")
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_summary_returns_expected_format(self, client):
        """Verify /summary returns expected response format."""
        with patch("nikita.api.routes.tasks._get_task_secret", return_value=None):
            response = client.post("/api/v1/tasks/summary")

            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert data["status"] == "ok"
            assert "summaries_generated" in data
            assert isinstance(data["summaries_generated"], int)


class TestCleanupEndpoint:
    """Test suite for /cleanup endpoint."""

    @pytest.fixture
    def app(self):
        """Create test FastAPI app."""
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/tasks")
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_cleanup_returns_expected_format(self, client):
        """Verify /cleanup returns expected response format on success."""
        with patch("nikita.api.routes.tasks._get_task_secret", return_value=None):
            with patch(
                "nikita.db.database.get_session_maker"
            ) as mock_session_maker:
                # Create proper async context manager mock
                mock_session = AsyncMock()
                mock_session.commit = AsyncMock()

                async_cm = AsyncMock()
                async_cm.__aenter__.return_value = mock_session
                async_cm.__aexit__.return_value = None

                mock_session_maker.return_value = MagicMock(return_value=async_cm)

                with patch(
                    "nikita.db.repositories.pending_registration_repository.PendingRegistrationRepository"
                ) as mock_repo_class:
                    mock_repo = MagicMock()
                    mock_repo.cleanup_expired = AsyncMock(return_value=3)
                    mock_repo_class.return_value = mock_repo

                    response = client.post("/api/v1/tasks/cleanup")

                    assert response.status_code == 200
                    data = response.json()
                    assert "status" in data
                    assert data["status"] == "ok"
                    assert "cleaned_up" in data
                    assert data["cleaned_up"] == 3

    def test_cleanup_handles_errors_gracefully(self, client):
        """Verify /cleanup handles errors gracefully."""
        with patch("nikita.api.routes.tasks._get_task_secret", return_value=None):
            with patch(
                "nikita.db.database.get_session_maker",
                side_effect=Exception("DB connection failed"),
            ):
                response = client.post("/api/v1/tasks/cleanup")

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "error"
                assert "error" in data
                assert "cleaned_up" in data
                assert data["cleaned_up"] == 0
