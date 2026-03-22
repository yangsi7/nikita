"""Tests for GET /portal/stats endpoint — UserStatsResponse including onboarded_at.

Verifies the portal stats endpoint returns correct user dashboard data
and populates the onboarded_at field from the user model.
"""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from nikita.api.dependencies.auth import get_current_user_id
from nikita.api.routes.portal import router
from nikita.db.database import get_async_session


class TestPortalStats:
    """Test suite for GET /portal/stats endpoint."""

    @pytest.fixture
    def mock_user_id(self):
        return uuid4()

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def mock_user(self, mock_user_id):
        """Create a mock user with standard game state."""
        user = AsyncMock()
        user.id = mock_user_id
        user.relationship_score = Decimal("62.5")
        user.chapter = 2
        user.days_played = 5
        user.game_status = "active"
        user.last_interaction_at = datetime(2026, 3, 20, 12, 0, 0, tzinfo=UTC)
        user.boss_attempts = 1
        user.onboarded_at = datetime(2026, 3, 15, 10, 30, 0, tzinfo=UTC)
        return user

    @pytest.fixture
    def mock_metrics(self):
        """Create mock user metrics."""
        metrics = AsyncMock()
        metrics.intimacy = Decimal("55.0")
        metrics.passion = Decimal("60.0")
        metrics.trust = Decimal("50.0")
        metrics.secureness = Decimal("45.0")
        return metrics

    @pytest.fixture
    def app(self, mock_user_id, mock_session):
        """Create isolated test app with dependency overrides."""
        test_app = FastAPI()
        test_app.include_router(router, prefix="/portal")
        test_app.dependency_overrides[get_current_user_id] = lambda: mock_user_id
        test_app.dependency_overrides[get_async_session] = lambda: mock_session
        return test_app

    @pytest.fixture
    def client(self, app):
        return TestClient(app)

    def test_stats_returns_200_with_valid_user(self, client, mock_user, mock_metrics):
        """Stats endpoint returns 200 with full dashboard data."""
        with (
            patch("nikita.api.routes.portal.UserRepository") as mock_user_repo_cls,
            patch("nikita.api.routes.portal.UserMetricsRepository") as mock_metrics_repo_cls,
        ):
            mock_user_repo = AsyncMock()
            mock_user_repo.get.return_value = mock_user
            mock_user_repo_cls.return_value = mock_user_repo

            mock_metrics_repo = AsyncMock()
            mock_metrics_repo.get_by_user_id.return_value = mock_metrics
            mock_metrics_repo_cls.return_value = mock_metrics_repo

            response = client.get("/portal/stats")
            assert response.status_code == 200
            data = response.json()
            assert data["chapter"] == 2
            assert data["game_status"] == "active"
            assert data["boss_attempts"] == 1
            assert data["metrics"] is not None
            assert data["metrics"]["intimacy"] == 55.0

    def test_stats_includes_onboarded_at_when_set(self, client, mock_user, mock_metrics):
        """Stats response includes onboarded_at when the user has completed onboarding."""
        with (
            patch("nikita.api.routes.portal.UserRepository") as mock_user_repo_cls,
            patch("nikita.api.routes.portal.UserMetricsRepository") as mock_metrics_repo_cls,
        ):
            mock_user_repo = AsyncMock()
            mock_user_repo.get.return_value = mock_user
            mock_user_repo_cls.return_value = mock_user_repo

            mock_metrics_repo = AsyncMock()
            mock_metrics_repo.get_by_user_id.return_value = mock_metrics
            mock_metrics_repo_cls.return_value = mock_metrics_repo

            response = client.get("/portal/stats")
            assert response.status_code == 200
            data = response.json()
            assert data["onboarded_at"] is not None
            assert "2026-03-15" in data["onboarded_at"]

    def test_stats_onboarded_at_null_when_not_onboarded(self, client, mock_user, mock_metrics):
        """Stats response returns onboarded_at=null for users who haven't onboarded."""
        mock_user.onboarded_at = None

        with (
            patch("nikita.api.routes.portal.UserRepository") as mock_user_repo_cls,
            patch("nikita.api.routes.portal.UserMetricsRepository") as mock_metrics_repo_cls,
        ):
            mock_user_repo = AsyncMock()
            mock_user_repo.get.return_value = mock_user
            mock_user_repo_cls.return_value = mock_user_repo

            mock_metrics_repo = AsyncMock()
            mock_metrics_repo.get_by_user_id.return_value = mock_metrics
            mock_metrics_repo_cls.return_value = mock_metrics_repo

            response = client.get("/portal/stats")
            assert response.status_code == 200
            data = response.json()
            assert data["onboarded_at"] is None

    def test_stats_schema_has_onboarded_at_field(self):
        """UserStatsResponse schema includes onboarded_at field."""
        from nikita.api.schemas.portal import UserStatsResponse

        fields = UserStatsResponse.model_fields
        assert "onboarded_at" in fields
        # Field should be optional (default None)
        assert fields["onboarded_at"].default is None
