"""Tests for voice API endpoints (Spec 007).

Tests for T007 acceptance criteria:
- AC-T007.1: POST /api/v1/voice/initiate returns connection params
- AC-T007.2: Validates user authentication
- AC-T007.3: Returns 403 if call not available (wrong chapter/game over)
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from nikita.api.routes.voice import router


@pytest.fixture
def app():
    """Create test FastAPI app."""
    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v1/voice")
    return test_app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def mock_user():
    """Create a mock user."""
    user = MagicMock()
    user.id = uuid4()
    user.name = "TestUser"
    user.chapter = 3
    user.game_status = "active"
    user.engagement_state = "IN_ZONE"
    user.metrics = MagicMock()
    user.metrics.relationship_score = 65.0
    return user


@pytest.fixture
def mock_voice_context():
    """Create a mock voice context."""
    from nikita.agents.voice.models import VoiceContext

    return VoiceContext(
        user_id=uuid4(),
        user_name="TestUser",
        chapter=3,
        relationship_score=65.0,
    )


class TestVoiceInitiateEndpoint:
    """Test POST /api/v1/voice/initiate endpoint - T007."""

    @pytest.mark.asyncio
    async def test_initiate_returns_connection_params(self, client, mock_user):
        """AC-T007.1: POST /api/v1/voice/initiate returns connection params."""
        user_id = str(mock_user.id)

        with patch("nikita.api.routes.voice.get_voice_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.initiate_call.return_value = {
                "agent_id": "test_agent_123",
                "signed_token": "token_abc",
                "session_id": "voice_session_xyz",
                "context": {"user_name": "TestUser"},
                "dynamic_variables": {"user_name": "TestUser"},
            }
            mock_get_service.return_value = mock_service

            response = client.post(
                "/api/v1/voice/initiate",
                json={"user_id": user_id},
            )

        assert response.status_code == 200
        data = response.json()
        assert "agent_id" in data
        assert "signed_token" in data
        assert "session_id" in data
        assert data["agent_id"] == "test_agent_123"

    @pytest.mark.asyncio
    async def test_initiate_requires_user_id(self, client):
        """AC-T007.2: Validates user authentication - user_id required."""
        response = client.post(
            "/api/v1/voice/initiate",
            json={},
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_initiate_invalid_user_id_format(self, client):
        """AC-T007.2: Validates user authentication - user_id must be valid UUID."""
        response = client.post(
            "/api/v1/voice/initiate",
            json={"user_id": "not-a-uuid"},
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_initiate_returns_403_for_game_over(self, client, mock_user):
        """AC-T007.3: Returns 403 if call not available (game_over)."""
        user_id = str(mock_user.id)

        with patch("nikita.api.routes.voice.get_voice_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.initiate_call.side_effect = ValueError(
                "Voice not available: user game_status=game_over"
            )
            mock_get_service.return_value = mock_service

            response = client.post(
                "/api/v1/voice/initiate",
                json={"user_id": user_id},
            )

        assert response.status_code == 403
        assert "not available" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_initiate_returns_404_for_unknown_user(self, client):
        """Returns 404 if user not found."""
        user_id = str(uuid4())

        with patch("nikita.api.routes.voice.get_voice_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.initiate_call.side_effect = ValueError(
                f"User {user_id} not found"
            )
            mock_get_service.return_value = mock_service

            response = client.post(
                "/api/v1/voice/initiate",
                json={"user_id": user_id},
            )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_initiate_handles_service_error(self, client, mock_user):
        """Returns 500 for unexpected service errors."""
        user_id = str(mock_user.id)

        with patch("nikita.api.routes.voice.get_voice_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.initiate_call.side_effect = RuntimeError("Unexpected error")
            mock_get_service.return_value = mock_service

            response = client.post(
                "/api/v1/voice/initiate",
                json={"user_id": user_id},
            )

        assert response.status_code == 500
        assert "error" in response.json()["detail"].lower()
