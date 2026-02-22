"""Tests for /tasks/psyche-batch endpoint (Spec 056 T12).

AC coverage: AC-6.5, AC-6.6
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from nikita.api.routes.tasks import router


@pytest.fixture
def app():
    """Create test FastAPI app with tasks router."""
    app = FastAPI()
    app.include_router(router, prefix="/tasks")
    return app


@pytest.fixture
async def client(app):
    """Create async HTTP client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestPsycheBatchEndpoint:
    """Test /tasks/psyche-batch endpoint."""

    @pytest.mark.asyncio
    async def test_flag_off_returns_skip(self, client):
        """AC-6.6: Feature flag OFF returns skip response."""
        mock_settings = MagicMock()
        mock_settings.psyche_agent_enabled = False
        mock_settings.task_auth_secret = None
        mock_settings.telegram_webhook_secret = None

        with patch("nikita.api.routes.tasks.get_settings", return_value=mock_settings):
            response = await client.post("/tasks/psyche-batch")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "skipped"
        assert "psyche_agent_enabled" in data.get("reason", "")

    @pytest.mark.asyncio
    async def test_flag_on_runs_batch(self, client):
        """AC-6.5: Endpoint runs batch when flag ON."""
        mock_settings = MagicMock()
        mock_settings.psyche_agent_enabled = True
        mock_settings.task_auth_secret = None
        mock_settings.telegram_webhook_secret = None

        mock_session = AsyncMock()
        mock_session_maker = MagicMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session_maker.return_value = mock_session_ctx

        mock_job_repo = AsyncMock()
        mock_execution = MagicMock()
        mock_execution.id = "test-id"
        mock_job_repo.start_execution.return_value = mock_execution

        with (
            patch("nikita.api.routes.tasks.get_settings", return_value=mock_settings),
            patch(
                "nikita.api.routes.tasks.get_session_maker",
                return_value=mock_session_maker,
            ),
            patch(
                "nikita.api.routes.tasks.JobExecutionRepository",
                return_value=mock_job_repo,
            ),
            patch(
                "nikita.agents.psyche.batch.run_psyche_batch",
                return_value={"processed": 5, "failed": 1, "errors": ["test"]},
            ),
        ):
            response = await client.post("/tasks/psyche-batch")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["processed"] == 5
        assert data["failed"] == 1

    @pytest.mark.asyncio
    async def test_auth_required_in_production(self, client):
        """AC-6.5: Auth required when task_auth_secret is set."""
        mock_settings = MagicMock()
        mock_settings.psyche_agent_enabled = True
        mock_settings.task_auth_secret = "test-secret"
        mock_settings.telegram_webhook_secret = None

        with patch("nikita.api.routes.tasks.get_settings", return_value=mock_settings):
            # No Authorization header
            response = await client.post("/tasks/psyche-batch")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_auth_passes_with_correct_secret(self, client):
        """AC-6.5: Auth passes with correct Bearer token."""
        mock_settings = MagicMock()
        mock_settings.psyche_agent_enabled = False  # Use flag OFF for simplicity
        mock_settings.task_auth_secret = "test-secret"
        mock_settings.telegram_webhook_secret = None

        with patch("nikita.api.routes.tasks.get_settings", return_value=mock_settings):
            response = await client.post(
                "/tasks/psyche-batch",
                headers={"Authorization": "Bearer test-secret"},
            )

        assert response.status_code == 200
