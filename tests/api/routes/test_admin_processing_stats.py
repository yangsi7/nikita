"""Tests for GET /admin/processing-stats endpoint (Spec 031 T3.3)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from nikita.api.routes.admin import router, get_current_admin_user_id
from nikita.api.schemas.admin import ProcessingStatsResponse
from nikita.db.database import get_async_session
from nikita.db.models.job_execution import JobExecution, JobName, JobStatus


class TestProcessingStatsEndpoint:
    """Tests for processing stats endpoint."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async database session."""
        return AsyncMock()

    @pytest.fixture
    def app(self, mock_session):
        """Create isolated test app with admin router and mocked dependencies."""
        test_app = FastAPI()
        test_app.include_router(router, prefix="/admin")

        # Override admin auth to return a mock admin ID
        async def mock_admin_auth():
            return uuid4()

        # Override async session to return our mock
        async def mock_get_session():
            return mock_session

        test_app.dependency_overrides[get_current_admin_user_id] = mock_admin_auth
        test_app.dependency_overrides[get_async_session] = mock_get_session

        return test_app

    @pytest.fixture
    def client(self, app):
        """Create test client with mocked dependencies."""
        return TestClient(app)

    def test_returns_zero_stats_when_no_jobs(self, mock_session, client):
        """Returns zeroed stats when no post-processing jobs exist."""
        # Mock job stats query result (all zeros)
        job_result_mock = MagicMock()
        job_result_mock.one.return_value = MagicMock(
            total=0, success=0, failed=0, avg_duration=None
        )

        # Mock pending/stuck count results
        pending_result_mock = MagicMock()
        pending_result_mock.scalar.return_value = 0
        stuck_result_mock = MagicMock()
        stuck_result_mock.scalar.return_value = 0

        # Configure execute to return different results for different queries
        mock_session.execute.side_effect = [
            job_result_mock,
            pending_result_mock,
            stuck_result_mock,
        ]

        response = client.get("/admin/processing-stats")

        assert response.status_code == 200
        data = response.json()
        assert data["success_rate"] == 0.0
        assert data["avg_duration_ms"] == 0
        assert data["total_processed"] == 0
        assert data["success_count"] == 0
        assert data["failed_count"] == 0

    def test_calculates_success_rate(self, mock_session, client):
        """Calculates correct success rate from 24h jobs."""
        # Mock job stats query result (80% success rate: 8 success, 2 failed)
        job_result_mock = MagicMock()
        job_result_mock.one.return_value = MagicMock(
            total=10, success=8, failed=2, avg_duration=3500
        )

        # Mock pending/stuck count results
        pending_result_mock = MagicMock()
        pending_result_mock.scalar.return_value = 0
        stuck_result_mock = MagicMock()
        stuck_result_mock.scalar.return_value = 0

        mock_session.execute.side_effect = [
            job_result_mock,
            pending_result_mock,
            stuck_result_mock,
        ]

        response = client.get("/admin/processing-stats")

        assert response.status_code == 200
        data = response.json()
        assert data["success_rate"] == 80.0
        assert data["total_processed"] == 10
        assert data["success_count"] == 8
        assert data["failed_count"] == 2

    def test_calculates_avg_duration(self, mock_session, client):
        """Calculates average duration in milliseconds."""
        # Mock job stats: avg 2000ms
        job_result_mock = MagicMock()
        job_result_mock.one.return_value = MagicMock(
            total=3, success=3, failed=0, avg_duration=2000.0
        )

        # Mock pending/stuck counts
        pending_result_mock = MagicMock()
        pending_result_mock.scalar.return_value = 0
        stuck_result_mock = MagicMock()
        stuck_result_mock.scalar.return_value = 0

        mock_session.execute.side_effect = [
            job_result_mock,
            pending_result_mock,
            stuck_result_mock,
        ]

        response = client.get("/admin/processing-stats")

        assert response.status_code == 200
        data = response.json()
        assert data["avg_duration_ms"] == 2000

    def test_counts_pending_conversations(self, mock_session, client):
        """Counts conversations pending processing."""
        # Mock job stats
        job_result_mock = MagicMock()
        job_result_mock.one.return_value = MagicMock(
            total=5, success=5, failed=0, avg_duration=1000.0
        )

        # Mock pending count (3 pending)
        pending_result_mock = MagicMock()
        pending_result_mock.scalar.return_value = 3

        # Mock stuck count
        stuck_result_mock = MagicMock()
        stuck_result_mock.scalar.return_value = 0

        mock_session.execute.side_effect = [
            job_result_mock,
            pending_result_mock,
            stuck_result_mock,
        ]

        response = client.get("/admin/processing-stats")

        assert response.status_code == 200
        data = response.json()
        assert data["pending_count"] == 3

    def test_counts_stuck_conversations(self, mock_session, client):
        """Counts conversations stuck in processing."""
        # Mock job stats
        job_result_mock = MagicMock()
        job_result_mock.one.return_value = MagicMock(
            total=10, success=8, failed=2, avg_duration=5000.0
        )

        # Mock pending count
        pending_result_mock = MagicMock()
        pending_result_mock.scalar.return_value = 1

        # Mock stuck count (2 stuck)
        stuck_result_mock = MagicMock()
        stuck_result_mock.scalar.return_value = 2

        mock_session.execute.side_effect = [
            job_result_mock,
            pending_result_mock,
            stuck_result_mock,
        ]

        response = client.get("/admin/processing-stats")

        assert response.status_code == 200
        data = response.json()
        assert data["stuck_count"] == 2

    def test_response_model_validation(self, mock_session, client):
        """Response validates against ProcessingStatsResponse schema."""
        # Mock all query results
        job_result_mock = MagicMock()
        job_result_mock.one.return_value = MagicMock(
            total=100, success=95, failed=5, avg_duration=3500.5
        )

        pending_result_mock = MagicMock()
        pending_result_mock.scalar.return_value = 7

        stuck_result_mock = MagicMock()
        stuck_result_mock.scalar.return_value = 1

        mock_session.execute.side_effect = [
            job_result_mock,
            pending_result_mock,
            stuck_result_mock,
        ]

        response = client.get("/admin/processing-stats")

        assert response.status_code == 200
        data = response.json()

        # Verify all expected fields are present
        expected_fields = [
            "success_rate",
            "avg_duration_ms",
            "total_processed",
            "success_count",
            "failed_count",
            "pending_count",
            "stuck_count",
        ]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"

        # Verify response can be parsed
        stats = ProcessingStatsResponse(**data)
        assert stats.success_rate == 95.0
        assert stats.avg_duration_ms == 3500
        assert stats.total_processed == 100
        assert stats.success_count == 95
        assert stats.failed_count == 5
        assert stats.pending_count == 7
        assert stats.stuck_count == 1

    def test_handles_100_percent_success_rate(self, mock_session, client):
        """Handles 100% success rate correctly."""
        # Mock 100% success
        job_result_mock = MagicMock()
        job_result_mock.one.return_value = MagicMock(
            total=50, success=50, failed=0, avg_duration=2500.0
        )

        pending_result_mock = MagicMock()
        pending_result_mock.scalar.return_value = 0
        stuck_result_mock = MagicMock()
        stuck_result_mock.scalar.return_value = 0

        mock_session.execute.side_effect = [
            job_result_mock,
            pending_result_mock,
            stuck_result_mock,
        ]

        response = client.get("/admin/processing-stats")

        assert response.status_code == 200
        data = response.json()
        assert data["success_rate"] == 100.0
        assert data["failed_count"] == 0
