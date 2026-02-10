"""Tests for new admin mutation endpoints (Task 6 - FR-029)."""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


class TestTriggerPipeline:
    """Tests for POST /admin/users/{user_id}/trigger-pipeline."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async database session."""
        return AsyncMock()

    @pytest.fixture
    def app(self, mock_session):
        """Create isolated test app."""
        from nikita.api.routes.admin import router, get_current_admin_user_id
        from nikita.db.database import get_async_session

        test_app = FastAPI()
        test_app.include_router(router, prefix="/admin")

        async def mock_admin_auth():
            return uuid4()

        async def mock_get_session():
            return mock_session

        test_app.dependency_overrides[get_current_admin_user_id] = mock_admin_auth
        test_app.dependency_overrides[get_async_session] = mock_get_session

        return test_app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    @patch("nikita.pipeline.orchestrator.PipelineOrchestrator")
    @patch("nikita.api.routes.admin.ConversationRepository")
    @patch("nikita.api.routes.admin.UserRepository")
    def test_trigger_pipeline_with_specific_conversation(
        self, mock_user_repo_class, mock_conv_repo_class, mock_orchestrator_class, mock_session, client
    ):
        """Test triggering pipeline with specific conversation_id."""
        user_id = uuid4()
        conversation_id = uuid4()

        # Mock user
        mock_user = MagicMock()
        mock_user.id = user_id

        mock_user_repo = AsyncMock()
        mock_user_repo.get.return_value = mock_user
        mock_user_repo_class.return_value = mock_user_repo

        # Mock conversation lookup
        mock_conv = MagicMock()
        mock_conv.id = conversation_id
        mock_conv.platform = "text"
        mock_conv_repo = AsyncMock()
        mock_conv_repo.get.return_value = mock_conv
        mock_conv_repo_class.return_value = mock_conv_repo

        # Mock pipeline result
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.total_duration_ms = 1234

        mock_orchestrator = AsyncMock()
        mock_orchestrator.process.return_value = mock_result
        mock_orchestrator_class.return_value = mock_orchestrator

        response = client.post(
            f"/admin/users/{user_id}/trigger-pipeline",
            json={"conversation_id": str(conversation_id)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "completed" in data["message"]

    @patch("nikita.pipeline.orchestrator.PipelineOrchestrator")
    @patch("nikita.api.routes.admin.ConversationRepository")
    @patch("nikita.api.routes.admin.UserRepository")
    def test_trigger_pipeline_uses_most_recent_conversation(
        self, mock_user_repo_class, mock_conv_repo_class, mock_orchestrator_class, mock_session, client
    ):
        """Test triggering pipeline without conversation_id uses most recent."""
        user_id = uuid4()
        conversation_id = uuid4()

        # Mock user
        mock_user = MagicMock()
        mock_user.id = user_id

        mock_user_repo = AsyncMock()
        mock_user_repo.get.return_value = mock_user
        mock_user_repo_class.return_value = mock_user_repo

        # Mock conversation
        mock_conv = MagicMock()
        mock_conv.id = conversation_id
        mock_conv.platform = "text"

        mock_conv_repo = AsyncMock()
        mock_conv_repo.get_recent.return_value = [mock_conv]
        mock_conv_repo.get.return_value = mock_conv
        mock_conv_repo_class.return_value = mock_conv_repo

        # Mock pipeline
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.total_duration_ms = 500

        mock_orchestrator = AsyncMock()
        mock_orchestrator.process.return_value = mock_result
        mock_orchestrator_class.return_value = mock_orchestrator

        response = client.post(f"/admin/users/{user_id}/trigger-pipeline")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    @patch("nikita.api.routes.admin.UserRepository")
    def test_trigger_pipeline_404_when_user_not_found(
        self, mock_user_repo_class, mock_session, client
    ):
        """Test 404 when user doesn't exist."""
        user_id = uuid4()

        mock_user_repo = AsyncMock()
        mock_user_repo.get.return_value = None
        mock_user_repo_class.return_value = mock_user_repo

        response = client.post(f"/admin/users/{user_id}/trigger-pipeline")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @patch("nikita.api.routes.admin.ConversationRepository")
    @patch("nikita.api.routes.admin.UserRepository")
    def test_trigger_pipeline_error_when_no_conversations(
        self, mock_user_repo_class, mock_conv_repo_class, mock_session, client
    ):
        """Test error response when user has no conversations."""
        user_id = uuid4()

        # Mock user
        mock_user = MagicMock()
        mock_user.id = user_id

        mock_user_repo = AsyncMock()
        mock_user_repo.get.return_value = mock_user
        mock_user_repo_class.return_value = mock_user_repo

        # Mock empty conversations
        mock_conv_repo = AsyncMock()
        mock_conv_repo.get_recent.return_value = []
        mock_conv_repo_class.return_value = mock_conv_repo

        response = client.post(f"/admin/users/{user_id}/trigger-pipeline")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert "No conversations" in data["message"]


class TestPipelineHistory:
    """Tests for GET /admin/users/{user_id}/pipeline-history."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async database session."""
        return AsyncMock()

    @pytest.fixture
    def app(self, mock_session):
        """Create isolated test app."""
        from nikita.api.routes.admin import router, get_current_admin_user_id
        from nikita.db.database import get_async_session

        test_app = FastAPI()
        test_app.include_router(router, prefix="/admin")

        async def mock_admin_auth():
            return uuid4()

        async def mock_get_session():
            return mock_session

        test_app.dependency_overrides[get_current_admin_user_id] = mock_admin_auth
        test_app.dependency_overrides[get_async_session] = mock_get_session

        return test_app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_pipeline_history_returns_paginated_results(self, mock_session, client):
        """Test pipeline history returns paginated job executions."""
        user_id = uuid4()

        # Mock count
        count_result = MagicMock()
        count_result.scalar.return_value = 10

        # Mock job executions
        mock_jobs = []
        for i in range(3):
            job = MagicMock()
            job.id = uuid4()
            job.job_name = f"post_processing_{uuid4()}"
            job.status = "completed"
            job.duration_ms = 1000 + i * 100
            job.started_at = datetime.now(timezone.utc)
            job.completed_at = datetime.now(timezone.utc)
            job.result = {"status": "ok"}
            mock_jobs.append(job)

        jobs_result = MagicMock()
        jobs_result.scalars.return_value.all.return_value = mock_jobs

        mock_session.execute.side_effect = [jobs_result, count_result]

        response = client.get(f"/admin/users/{user_id}/pipeline-history?page=1&page_size=50")

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 10
        assert data["page"] == 1
        assert data["page_size"] == 50
        assert len(data["items"]) == 3
        assert data["items"][0]["status"] == "completed"

    def test_pipeline_history_includes_error_messages(self, mock_session, client):
        """Test pipeline history includes error messages for failed jobs."""
        user_id = uuid4()

        # Mock count
        count_result = MagicMock()
        count_result.scalar.return_value = 1

        # Mock failed job
        mock_job = MagicMock()
        mock_job.id = uuid4()
        mock_job.job_name = f"post_processing_{uuid4()}"
        mock_job.status = "failed"
        mock_job.duration_ms = 500
        mock_job.started_at = datetime.now(timezone.utc)
        mock_job.completed_at = datetime.now(timezone.utc)
        mock_job.result = {"error": "Pipeline stage extraction failed"}

        jobs_result = MagicMock()
        jobs_result.scalars.return_value.all.return_value = [mock_job]

        mock_session.execute.side_effect = [jobs_result, count_result]

        response = client.get(f"/admin/users/{user_id}/pipeline-history")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["status"] == "failed"
        assert "extraction failed" in data["items"][0]["error_message"]


class TestSetMetrics:
    """Tests for PUT /admin/users/{user_id}/metrics."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async database session."""
        session = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.fixture
    def app(self, mock_session):
        """Create isolated test app."""
        from nikita.api.routes.admin import router, get_current_admin_user_id
        from nikita.db.database import get_async_session

        test_app = FastAPI()
        test_app.include_router(router, prefix="/admin")

        async def mock_admin_auth():
            return uuid4()

        async def mock_get_session():
            return mock_session

        test_app.dependency_overrides[get_current_admin_user_id] = mock_admin_auth
        test_app.dependency_overrides[get_async_session] = mock_get_session

        return test_app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    @patch("nikita.api.routes.admin.UserMetricsRepository")
    def test_set_metrics_updates_specified_fields(
        self, mock_metrics_repo_class, mock_session, client
    ):
        """Test setting metrics updates only specified fields."""
        user_id = uuid4()

        # Mock metrics
        mock_metrics = MagicMock()
        mock_metrics.intimacy = Decimal("50.0")
        mock_metrics.passion = Decimal("60.0")
        mock_metrics.trust = Decimal("70.0")
        mock_metrics.secureness = Decimal("80.0")

        mock_repo = AsyncMock()
        mock_repo.get.return_value = mock_metrics
        mock_metrics_repo_class.return_value = mock_repo

        response = client.put(
            f"/admin/users/{user_id}/metrics",
            json={
                "intimacy": "75.5",
                "passion": "65.5",
                "reason": "Testing metrics adjustment",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "intimacy" in data["message"]
        assert "passion" in data["message"]
        assert mock_metrics.intimacy == Decimal("75.5")
        assert mock_metrics.passion == Decimal("65.5")

    @patch("nikita.api.routes.admin.UserMetricsRepository")
    def test_set_metrics_404_when_not_found(
        self, mock_metrics_repo_class, mock_session, client
    ):
        """Test 404 when metrics don't exist."""
        user_id = uuid4()

        mock_repo = AsyncMock()
        mock_repo.get.return_value = None
        mock_metrics_repo_class.return_value = mock_repo

        response = client.put(
            f"/admin/users/{user_id}/metrics",
            json={
                "intimacy": "75.5",
                "reason": "Test",
            },
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @patch("nikita.api.routes.admin.UserMetricsRepository")
    def test_set_metrics_error_when_no_fields(
        self, mock_metrics_repo_class, mock_session, client
    ):
        """Test error when no metrics provided."""
        user_id = uuid4()

        # Mock metrics
        mock_metrics = MagicMock()
        mock_repo = AsyncMock()
        mock_repo.get.return_value = mock_metrics
        mock_metrics_repo_class.return_value = mock_repo

        response = client.put(
            f"/admin/users/{user_id}/metrics",
            json={"reason": "Test"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "No metrics provided" in data["message"]

    @patch("nikita.api.routes.admin.UserMetricsRepository")
    def test_set_metrics_updates_all_four_fields(
        self, mock_metrics_repo_class, mock_session, client
    ):
        """Test updating all four metric fields."""
        user_id = uuid4()

        # Mock metrics
        mock_metrics = MagicMock()
        mock_metrics.intimacy = Decimal("50.0")
        mock_metrics.passion = Decimal("50.0")
        mock_metrics.trust = Decimal("50.0")
        mock_metrics.secureness = Decimal("50.0")

        mock_repo = AsyncMock()
        mock_repo.get.return_value = mock_metrics
        mock_metrics_repo_class.return_value = mock_repo

        response = client.put(
            f"/admin/users/{user_id}/metrics",
            json={
                "intimacy": "80.0",
                "passion": "85.0",
                "trust": "90.0",
                "secureness": "95.0",
                "reason": "Full metrics reset",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "intimacy" in data["message"]
        assert "passion" in data["message"]
        assert "trust" in data["message"]
        assert "secureness" in data["message"]
        assert mock_metrics.intimacy == Decimal("80.0")
        assert mock_metrics.passion == Decimal("85.0")
        assert mock_metrics.trust == Decimal("90.0")
        assert mock_metrics.secureness == Decimal("95.0")
