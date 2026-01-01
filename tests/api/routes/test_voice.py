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


class TestVoiceAvailabilityEndpoint:
    """Test GET /api/v1/voice/availability/{user_id} endpoint - T034."""

    def test_availability_returns_status(self, client, mock_user):
        """AC-T034.1: Returns availability status with reason."""
        user_id = str(mock_user.id)

        with patch(
            "nikita.api.routes.voice.get_session_maker"
        ) as mock_session_maker, patch(
            "nikita.api.routes.voice.get_availability_service"
        ) as mock_availability:
            # Mock session
            mock_session = AsyncMock()
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_session_maker.return_value = MagicMock(return_value=mock_session)

            # Mock repository
            mock_repo = AsyncMock()
            mock_repo.get.return_value = mock_user

            with patch(
                "nikita.api.routes.voice.UserRepository", return_value=mock_repo
            ):
                # Mock availability service
                mock_avail = MagicMock()
                mock_avail.is_available.return_value = (True, "Nikita is available.")
                mock_avail.get_availability_rate.return_value = 0.8
                mock_availability.return_value = mock_avail

                response = client.get(f"/api/v1/voice/availability/{user_id}")

        assert response.status_code == 200
        data = response.json()
        assert "available" in data
        assert "reason" in data
        assert "chapter" in data
        assert "availability_rate" in data
        assert data["available"] is True

    def test_availability_returns_chapter_rate(self, client, mock_user):
        """AC-T034.2: Returns chapter-based availability rate."""
        user_id = str(mock_user.id)

        with patch(
            "nikita.api.routes.voice.get_session_maker"
        ) as mock_session_maker, patch(
            "nikita.api.routes.voice.get_availability_service"
        ) as mock_availability:
            mock_session = AsyncMock()
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_session_maker.return_value = MagicMock(return_value=mock_session)

            mock_repo = AsyncMock()
            mock_repo.get.return_value = mock_user

            with patch(
                "nikita.api.routes.voice.UserRepository", return_value=mock_repo
            ):
                mock_avail = MagicMock()
                mock_avail.is_available.return_value = (True, "Available")
                mock_avail.get_availability_rate.return_value = 0.8  # Chapter 3 rate
                mock_availability.return_value = mock_avail

                response = client.get(f"/api/v1/voice/availability/{user_id}")

        data = response.json()
        assert data["chapter"] == 3
        assert data["availability_rate"] == 0.8

    def test_availability_returns_404_for_unknown_user(self, client):
        """Returns 404 if user not found."""
        user_id = str(uuid4())

        with patch(
            "nikita.api.routes.voice.get_session_maker"
        ) as mock_session_maker:
            mock_session = AsyncMock()
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_session_maker.return_value = MagicMock(return_value=mock_session)

            mock_repo = AsyncMock()
            mock_repo.get.return_value = None  # User not found

            with patch(
                "nikita.api.routes.voice.UserRepository", return_value=mock_repo
            ):
                response = client.get(f"/api/v1/voice/availability/{user_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_availability_shows_game_over_blocked(self, client):
        """AC-T034.3: Game over status blocks calls."""
        game_over_user = MagicMock()
        game_over_user.id = uuid4()
        game_over_user.chapter = 3
        game_over_user.game_status = "game_over"

        user_id = str(game_over_user.id)

        with patch(
            "nikita.api.routes.voice.get_session_maker"
        ) as mock_session_maker, patch(
            "nikita.api.routes.voice.get_availability_service"
        ) as mock_availability:
            mock_session = AsyncMock()
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_session_maker.return_value = MagicMock(return_value=mock_session)

            mock_repo = AsyncMock()
            mock_repo.get.return_value = game_over_user

            with patch(
                "nikita.api.routes.voice.UserRepository", return_value=mock_repo
            ):
                mock_avail = MagicMock()
                mock_avail.is_available.return_value = (
                    False,
                    "Game is over. Nikita has moved on.",
                )
                mock_avail.get_availability_rate.return_value = 0.8
                mock_availability.return_value = mock_avail

                response = client.get(f"/api/v1/voice/availability/{user_id}")

        data = response.json()
        assert data["available"] is False
        assert "over" in data["reason"].lower()

    def test_availability_shows_boss_fight_available(self, client):
        """AC-T034.3: Boss fight status always allows calls."""
        boss_user = MagicMock()
        boss_user.id = uuid4()
        boss_user.chapter = 2
        boss_user.game_status = "boss_fight"

        user_id = str(boss_user.id)

        with patch(
            "nikita.api.routes.voice.get_session_maker"
        ) as mock_session_maker, patch(
            "nikita.api.routes.voice.get_availability_service"
        ) as mock_availability:
            mock_session = AsyncMock()
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_session_maker.return_value = MagicMock(return_value=mock_session)

            mock_repo = AsyncMock()
            mock_repo.get.return_value = boss_user

            with patch(
                "nikita.api.routes.voice.UserRepository", return_value=mock_repo
            ):
                mock_avail = MagicMock()
                mock_avail.is_available.return_value = (
                    True,
                    "Nikita wants to talk - this is important. (Boss encounter)",
                )
                mock_avail.get_availability_rate.return_value = 0.4
                mock_availability.return_value = mock_avail

                response = client.get(f"/api/v1/voice/availability/{user_id}")

        data = response.json()
        assert data["available"] is True
        assert "boss" in data["reason"].lower()

    def test_availability_invalid_uuid_format(self, client):
        """Returns 422 for invalid UUID format."""
        response = client.get("/api/v1/voice/availability/not-a-uuid")

        assert response.status_code == 422
