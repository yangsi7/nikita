"""Tests for portal psyche-tips endpoint (Spec 059).

Acceptance Criteria:
- AC-2.1: GET /portal/psyche-tips returns psyche state data
- AC-2.3: Returns defaults when no psyche state exists
- AC-2.6: Requires Supabase JWT auth
- AC-2.7: Backend test covers happy path, default, schema
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from nikita.api.dependencies.auth import get_current_user_id
from nikita.api.routes.portal import router
from nikita.db.database import get_async_session


UTC = timezone.utc

# Patch target: lazy import inside the endpoint function
REPO_PATCH = "nikita.db.repositories.psyche_state_repository.PsycheStateRepository"


class TestPsycheTips:
    """Test suite for GET /portal/psyche-tips (Spec 059)."""

    @pytest.fixture
    def mock_user_id(self):
        return uuid4()

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.fixture
    def app(self, mock_user_id, mock_session):
        test_app = FastAPI()
        test_app.include_router(router, prefix="/portal")
        test_app.dependency_overrides[get_current_user_id] = lambda: mock_user_id
        test_app.dependency_overrides[get_async_session] = lambda: mock_session
        return test_app

    @pytest.fixture
    def unauthed_app(self):
        test_app = FastAPI()
        test_app.include_router(router, prefix="/portal")
        return test_app

    @pytest.fixture
    def client(self, app):
        return TestClient(app)

    @pytest.fixture
    def unauthed_client(self, unauthed_app):
        return TestClient(unauthed_app)

    def test_psyche_tips_requires_auth(self, unauthed_client):
        """AC-2.6: GET /psyche-tips requires authentication."""
        response = unauthed_client.get("/portal/psyche-tips")
        assert response.status_code in [401, 403]

    def test_psyche_tips_returns_defaults_when_no_state(self, client, mock_user_id):
        """AC-2.3: Returns default PsycheState values when no record exists."""
        with patch(REPO_PATCH) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_current.return_value = None
            mock_repo_class.return_value = mock_repo

            response = client.get("/portal/psyche-tips")

            assert response.status_code == 200
            data = response.json()
            assert data["attachment_style"] == "secure"
            assert data["defense_mode"] == "open"
            assert data["emotional_tone"] == "warm"
            assert data["vulnerability_level"] == 0.3
            assert len(data["behavioral_tips"]) > 0
            assert data["topics_to_encourage"] == ["getting to know each other"]
            assert data["topics_to_avoid"] == []
            assert data["generated_at"] is None

    def test_psyche_tips_returns_actual_state(self, client, mock_user_id):
        """AC-2.1, AC-2.7: Returns psyche state from DB record."""
        now = datetime.now(UTC)
        mock_record = MagicMock()
        mock_record.state = {
            "attachment_activation": "anxious",
            "defense_mode": "guarded",
            "behavioral_guidance": "Be patient with her. Don't push too hard.",
            "internal_monologue": "Something feels off today.",
            "vulnerability_level": 0.6,
            "emotional_tone": "serious",
            "topics_to_encourage": ["feelings", "future plans"],
            "topics_to_avoid": ["ex-boyfriend"],
        }
        mock_record.generated_at = now

        with patch(REPO_PATCH) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_current.return_value = mock_record
            mock_repo_class.return_value = mock_repo

            response = client.get("/portal/psyche-tips")

            assert response.status_code == 200
            data = response.json()
            assert data["attachment_style"] == "anxious"
            assert data["defense_mode"] == "guarded"
            assert data["emotional_tone"] == "serious"
            assert data["vulnerability_level"] == 0.6
            assert "Be patient with her" in data["behavioral_tips"][0]
            assert data["topics_to_encourage"] == ["feelings", "future plans"]
            assert data["topics_to_avoid"] == ["ex-boyfriend"]
            assert data["internal_monologue"] == "Something feels off today."
            assert data["generated_at"] is not None

    def test_psyche_tips_handles_corrupt_state_json(self, client, mock_user_id):
        """AC-2.7: Falls back to defaults if JSONB is corrupt."""
        mock_record = MagicMock()
        mock_record.state = {"invalid": "data"}  # Missing required fields
        mock_record.generated_at = datetime.now(UTC)

        with patch(REPO_PATCH) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_current.return_value = mock_record
            mock_repo_class.return_value = mock_repo

            response = client.get("/portal/psyche-tips")

            assert response.status_code == 200
            data = response.json()
            # Should fall back to defaults
            assert data["attachment_style"] == "secure"
            assert data["defense_mode"] == "open"

    def test_psyche_tips_response_schema_complete(self, client, mock_user_id):
        """AC-2.2: Response contains all expected fields."""
        with patch(REPO_PATCH) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_current.return_value = None
            mock_repo_class.return_value = mock_repo

            response = client.get("/portal/psyche-tips")

            assert response.status_code == 200
            data = response.json()
            expected_fields = {
                "attachment_style",
                "defense_mode",
                "emotional_tone",
                "vulnerability_level",
                "behavioral_tips",
                "topics_to_encourage",
                "topics_to_avoid",
                "internal_monologue",
                "generated_at",
            }
            assert set(data.keys()) == expected_fields
