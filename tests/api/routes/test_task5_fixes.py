"""Tests for Task 5 fixes - pipeline names and deprecated routes."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


class TestDeprecatedPipelineHealth:
    """Tests for deprecated GET /admin/pipeline-health endpoint."""

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

    def test_pipeline_health_returns_410_gone(self, client):
        """Test deprecated pipeline-health endpoint returns 410 Gone."""
        response = client.get("/admin/pipeline-health")

        assert response.status_code == 410
        assert "deprecated" in response.json()["detail"].lower()
        assert "unified-pipeline-health" in response.json()["detail"].lower()


class TestPipelineStageNames:
    """Tests for correct pipeline stage names in admin_debug."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async database session."""
        return AsyncMock()

    @pytest.fixture
    def app(self, mock_session):
        """Create isolated test app."""
        from nikita.api.routes.admin_debug import router, get_current_admin_user
        from nikita.db.database import get_async_session

        test_app = FastAPI()
        test_app.include_router(router, prefix="/admin/debug")

        async def mock_admin_auth():
            return uuid4()

        async def mock_get_session():
            return mock_session

        test_app.dependency_overrides[get_current_admin_user] = mock_admin_auth
        test_app.dependency_overrides[get_async_session] = mock_get_session

        return test_app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_stage_names_match_orchestrator_definitions(self):
        """Test that stage names in code match PipelineOrchestrator.STAGE_DEFINITIONS."""
        from nikita.pipeline.orchestrator import PipelineOrchestrator

        expected_names = [name for name, _, _ in PipelineOrchestrator.STAGE_DEFINITIONS]

        # Expected: extraction, memory_update, life_sim, emotional, game_state,
        #           conflict, touchpoint, summary, prompt_builder
        assert "extraction" in expected_names
        assert "memory_update" in expected_names
        assert "life_sim" in expected_names
        assert "emotional" in expected_names
        assert "game_state" in expected_names
        assert "conflict" in expected_names
        assert "touchpoint" in expected_names
        assert "summary" in expected_names
        assert "prompt_builder" in expected_names

        # Old names should NOT be present
        assert "Ingestion" not in expected_names
        assert "Entity Extraction" not in expected_names
        assert "Thread Resolution" not in expected_names
        assert "Thought Generation" not in expected_names
        assert "Graph Updates" not in expected_names
        assert "Summary Rollups" not in expected_names
        assert "Vice Processing" not in expected_names
        assert "Finalization" not in expected_names
