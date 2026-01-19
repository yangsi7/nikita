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


class TestWebhookPostProcessing:
    """Tests for webhook post-processing pipeline (Phase A)."""

    @pytest.fixture
    def mock_user(self):
        """Create a mock user."""
        user = MagicMock()
        user.id = uuid4()
        user.name = "TestUser"
        user.chapter = 3
        user.game_status = "active"
        return user

    @pytest.fixture
    def valid_signature(self):
        """Create valid HMAC signature for testing."""
        import hashlib
        import hmac
        import json
        import time

        payload = {
            "type": "post_call_transcription",
            "event_timestamp": 1739537297,
            "data": {
                "conversation_id": "test_session_123",
                "transcript": [
                    {"role": "user", "message": "Hi Nikita"},
                    {"role": "agent", "message": "Hey babe, how are you?"},
                ],
                "conversation_initiation_client_data": {
                    "dynamic_variables": {
                        "secret__user_id": str(uuid4())
                    }
                }
            }
        }
        payload_str = json.dumps(payload)
        timestamp = int(time.time())
        secret = "test_secret"

        signature = hmac.new(
            secret.encode(),
            f"{timestamp}.{payload_str}".encode(),
            hashlib.sha256,
        ).hexdigest()

        return payload, f"t={timestamp},v0={signature}", secret

    def test_webhook_processes_transcript(self, client, mock_user):
        """AC-FR015-001: Webhook stores transcript and triggers post-processing."""
        import hashlib
        import hmac
        import json
        import time

        user_id = str(mock_user.id)
        payload = {
            "type": "post_call_transcription",
            "event_timestamp": 1739537297,
            "data": {
                "conversation_id": "test_session_123",
                "transcript": [
                    {"role": "user", "message": "Hi Nikita"},
                    {"role": "agent", "message": "Hey babe, how are you?"},
                ],
                "conversation_initiation_client_data": {
                    "dynamic_variables": {
                        "secret__user_id": user_id
                    }
                }
            }
        }
        payload_str = json.dumps(payload)
        timestamp = int(time.time())
        secret = "test_secret"

        signature = hmac.new(
            secret.encode(),
            f"{timestamp}.{payload_str}".encode(),
            hashlib.sha256,
        ).hexdigest()

        with patch("nikita.api.routes.voice.get_settings") as mock_settings, \
             patch("nikita.db.database.get_session_maker") as mock_session_maker:

            mock_settings.return_value.elevenlabs_webhook_secret = secret

            # Mock the session for conversation creation
            mock_session = AsyncMock()
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_session.add = MagicMock()
            mock_session.flush = AsyncMock()
            mock_session.refresh = AsyncMock()
            mock_session.commit = AsyncMock()
            mock_session_maker.return_value = MagicMock(return_value=mock_session)

            with patch("nikita.db.repositories.user_repository.UserRepository") as mock_repo_class, \
                 patch("nikita.context.post_processor.PostProcessor") as mock_processor_class:

                # Mock user lookup
                mock_repo = AsyncMock()
                mock_repo.get.return_value = mock_user
                mock_repo_class.return_value = mock_repo

                # Mock post-processor
                mock_result = MagicMock()
                mock_result.success = True
                mock_result.stage_reached = "complete"
                mock_result.threads_created = 2
                mock_result.thoughts_created = 3
                mock_result.summary = "A nice conversation about the day"
                mock_processor = AsyncMock()
                mock_processor.process_conversation.return_value = mock_result
                mock_processor_class.return_value = mock_processor

                response = client.post(
                    "/api/v1/voice/webhook",
                    content=payload_str,
                    headers={
                        "Content-Type": "application/json",
                        "elevenlabs-signature": f"t={timestamp},v0={signature}",
                    },
                )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processed"

    def test_webhook_skips_without_user_id(self, client):
        """Webhook skips processing if no user_id in metadata."""
        import hashlib
        import hmac
        import json
        import time

        payload = {
            "type": "post_call_transcription",
            "event_timestamp": 1739537297,
            "data": {
                "conversation_id": "test_session_123",
                "transcript": [
                    {"role": "user", "message": "Hi Nikita"},
                ],
                "conversation_initiation_client_data": {
                    "dynamic_variables": {}  # No secret__user_id
                }
            }
        }
        payload_str = json.dumps(payload)
        timestamp = int(time.time())
        secret = "test_secret"

        signature = hmac.new(
            secret.encode(),
            f"{timestamp}.{payload_str}".encode(),
            hashlib.sha256,
        ).hexdigest()

        with patch("nikita.api.routes.voice.get_settings") as mock_settings:
            mock_settings.return_value.elevenlabs_webhook_secret = secret

            response = client.post(
                "/api/v1/voice/webhook",
                content=payload_str,
                headers={
                    "Content-Type": "application/json",
                    "elevenlabs-signature": f"t={timestamp},v0={signature}",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "skipped"

    def test_webhook_handles_unknown_user(self, client):
        """Webhook skips processing if user not found."""
        import hashlib
        import hmac
        import json
        import time

        user_id = str(uuid4())
        payload = {
            "type": "post_call_transcription",
            "event_timestamp": 1739537297,
            "data": {
                "conversation_id": "test_session_123",
                "transcript": [
                    {"role": "user", "message": "Hi Nikita"},
                ],
                "conversation_initiation_client_data": {
                    "dynamic_variables": {
                        "secret__user_id": user_id
                    }
                }
            }
        }
        payload_str = json.dumps(payload)
        timestamp = int(time.time())
        secret = "test_secret"

        signature = hmac.new(
            secret.encode(),
            f"{timestamp}.{payload_str}".encode(),
            hashlib.sha256,
        ).hexdigest()

        with patch("nikita.api.routes.voice.get_settings") as mock_settings, \
             patch("nikita.db.database.get_session_maker") as mock_session_maker:

            mock_settings.return_value.elevenlabs_webhook_secret = secret

            # Mock the session
            mock_session = AsyncMock()
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_session_maker.return_value = MagicMock(return_value=mock_session)

            with patch("nikita.db.repositories.user_repository.UserRepository") as mock_repo_class:
                # User not found
                mock_repo = AsyncMock()
                mock_repo.get.return_value = None
                mock_repo_class.return_value = mock_repo

                response = client.post(
                    "/api/v1/voice/webhook",
                    content=payload_str,
                    headers={
                        "Content-Type": "application/json",
                        "elevenlabs-signature": f"t={timestamp},v0={signature}",
                    },
                )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "skipped"
        assert data["message"] == "user_not_found"

    def test_webhook_normalizes_agent_role(self, client, mock_user):
        """Webhook normalizes 'agent' role to 'nikita'."""
        import hashlib
        import hmac
        import json
        import time

        user_id = str(mock_user.id)
        payload = {
            "type": "post_call_transcription",
            "event_timestamp": 1739537297,
            "data": {
                "conversation_id": "test_session_123",
                "transcript": [
                    {"role": "user", "message": "Hi"},
                    {"role": "agent", "message": "Hello"},  # 'agent' should become 'nikita'
                ],
                "conversation_initiation_client_data": {
                    "dynamic_variables": {
                        "secret__user_id": user_id
                    }
                }
            }
        }
        payload_str = json.dumps(payload)
        timestamp = int(time.time())
        secret = "test_secret"

        signature = hmac.new(
            secret.encode(),
            f"{timestamp}.{payload_str}".encode(),
            hashlib.sha256,
        ).hexdigest()

        captured_conversation = None

        def capture_add(conv):
            nonlocal captured_conversation
            # Check the messages to verify role normalization
            if hasattr(conv, 'messages'):
                captured_conversation = conv

        with patch("nikita.api.routes.voice.get_settings") as mock_settings, \
             patch("nikita.db.database.get_session_maker") as mock_session_maker:

            mock_settings.return_value.elevenlabs_webhook_secret = secret

            mock_session = AsyncMock()
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_session.add = capture_add
            mock_session.flush = AsyncMock()
            mock_session.refresh = AsyncMock()
            mock_session.commit = AsyncMock()
            mock_session_maker.return_value = MagicMock(return_value=mock_session)

            with patch("nikita.db.repositories.user_repository.UserRepository") as mock_repo_class, \
                 patch("nikita.context.post_processor.PostProcessor") as mock_processor_class:

                mock_repo = AsyncMock()
                mock_repo.get.return_value = mock_user
                mock_repo_class.return_value = mock_repo

                mock_result = MagicMock()
                mock_result.success = True
                mock_result.stage_reached = "complete"
                mock_result.threads_created = 0
                mock_result.thoughts_created = 0
                mock_result.summary = None
                mock_processor = AsyncMock()
                mock_processor.process_conversation.return_value = mock_result
                mock_processor_class.return_value = mock_processor

                response = client.post(
                    "/api/v1/voice/webhook",
                    content=payload_str,
                    headers={
                        "Content-Type": "application/json",
                        "elevenlabs-signature": f"t={timestamp},v0={signature}",
                    },
                )

        assert response.status_code == 200

        # Verify the role was normalized
        if captured_conversation:
            messages = captured_conversation.messages
            nikita_messages = [m for m in messages if m.get("role") == "nikita"]
            assert len(nikita_messages) == 1
            assert nikita_messages[0]["content"] == "Hello"

    def test_webhook_caches_prompt_for_next_call(self, client, mock_user):
        """FR-034: Webhook caches voice prompt for next call after post-processing.

        After successful post-processing, MetaPromptService.generate_system_prompt()
        should be called and the result stored in user.cached_voice_prompt.
        """
        import hashlib
        import hmac
        import json
        import time
        from unittest.mock import PropertyMock

        user_id = str(mock_user.id)
        payload = {
            "type": "post_call_transcription",
            "event_timestamp": 1739537297,
            "data": {
                "conversation_id": "test_session_caching",
                "transcript": [
                    {"role": "user", "message": "Hi Nikita, how are you?"},
                    {"role": "agent", "message": "Hey babe, I'm great! How was your day?"},
                ],
                "conversation_initiation_client_data": {
                    "dynamic_variables": {
                        "secret__user_id": user_id
                    }
                }
            }
        }
        payload_str = json.dumps(payload)
        timestamp = int(time.time())
        secret = "test_secret"

        signature = hmac.new(
            secret.encode(),
            f"{timestamp}.{payload_str}".encode(),
            hashlib.sha256,
        ).hexdigest()

        cached_prompt_value = None

        def capture_cached_prompt(val):
            nonlocal cached_prompt_value
            cached_prompt_value = val

        # Make cached_voice_prompt a settable property
        type(mock_user).cached_voice_prompt = property(
            lambda self: cached_prompt_value,
            lambda self, val: capture_cached_prompt(val)
        )

        with patch("nikita.api.routes.voice.get_settings") as mock_settings, \
             patch("nikita.db.database.get_session_maker") as mock_session_maker:

            mock_settings.return_value.elevenlabs_webhook_secret = secret

            mock_session = AsyncMock()
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_session.add = MagicMock()
            mock_session.flush = AsyncMock()
            mock_session.refresh = AsyncMock()
            mock_session.commit = AsyncMock()
            mock_session_maker.return_value = MagicMock(return_value=mock_session)

            with patch("nikita.db.repositories.user_repository.UserRepository") as mock_repo_class, \
                 patch("nikita.context.post_processor.PostProcessor") as mock_processor_class, \
                 patch("nikita.meta_prompts.service.MetaPromptService") as mock_meta_class:

                # Mock user lookup
                mock_repo = AsyncMock()
                mock_repo.get.return_value = mock_user
                mock_repo_class.return_value = mock_repo

                # Mock post-processor - SUCCESS
                mock_result = MagicMock()
                mock_result.success = True
                mock_result.stage_reached = "complete"
                mock_result.threads_created = 1
                mock_result.thoughts_created = 2
                mock_result.summary = "A nice conversation"
                mock_processor = AsyncMock()
                mock_processor.process_conversation.return_value = mock_result
                mock_processor_class.return_value = mock_processor

                # Mock MetaPromptService
                mock_prompt_result = MagicMock()
                mock_prompt_result.content = "Generated prompt for next call..."
                mock_meta_instance = AsyncMock()
                mock_meta_instance.generate_system_prompt.return_value = mock_prompt_result
                mock_meta_class.return_value = mock_meta_instance

                response = client.post(
                    "/api/v1/voice/webhook",
                    content=payload_str,
                    headers={
                        "Content-Type": "application/json",
                        "elevenlabs-signature": f"t={timestamp},v0={signature}",
                    },
                )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processed"

        # FR-034: MetaPromptService should have been called to generate prompt
        mock_meta_instance.generate_system_prompt.assert_called_once()

        # FR-034: The generated prompt should be cached on the user
        assert cached_prompt_value == "Generated prompt for next call..."


class TestPreCallWebhook:
    """Tests for POST /api/v1/voice/pre-call endpoint (T078).

    CRITICAL: This tests the actual API endpoint, not just InboundCallHandler.
    ElevenLabs calls this endpoint for inbound calls via Twilio.
    """

    def test_pre_call_returns_conversation_initiation_data(self, client, mock_user):
        """AC-T078.1: POST /api/v1/voice/pre-call handles pre-call webhook."""
        with patch("nikita.agents.voice.inbound.get_inbound_handler") as mock_get_handler:
            mock_handler = AsyncMock()
            mock_handler.handle_incoming_call.return_value = {
                "accept_call": True,
                "dynamic_variables": {
                    "user_name": "TestUser",
                    "chapter": "3",
                    "relationship_score": "65.0",
                    "engagement_state": "IN_ZONE",
                    "nikita_mood": "playful",
                    "nikita_energy": "medium",
                    "time_of_day": "afternoon",
                    "recent_topics": "",
                    "open_threads": "",
                },
                "conversation_config_override": {
                    "tts": {"stability": 0.55},
                    "agent": {"first_message": "Hey TestUser!"},
                },
            }
            mock_get_handler.return_value = mock_handler

            response = client.post(
                "/api/v1/voice/pre-call",
                json={
                    "caller_id": "+41787950009",
                    "agent_id": "agent_test123",
                    "called_number": "+41445056044",
                    "call_sid": "CA123456789",
                },
            )

        assert response.status_code == 200
        data = response.json()

        # Verify response format
        assert data["type"] == "conversation_initiation_client_data"
        assert "dynamic_variables" in data
        assert "conversation_config_override" in data

        # Verify ALL 9 dynamic_variables
        dv = data["dynamic_variables"]
        assert dv["user_name"] == "TestUser"
        assert dv["chapter"] == "3"
        assert dv["relationship_score"] == "65.0"
        assert dv["engagement_state"] == "IN_ZONE"
        assert dv["nikita_mood"] == "playful"
        assert dv["nikita_energy"] == "medium"
        assert dv["time_of_day"] == "afternoon"
        assert "recent_topics" in dv
        assert "open_threads" in dv

    def test_pre_call_unknown_caller_returns_dynamic_variables(self, client):
        """AC-T078.3: Unknown callers still get dynamic_variables (not null).

        CRITICAL: ElevenLabs requires dynamic_variables even for rejected calls.
        """
        with patch("nikita.agents.voice.inbound.get_inbound_handler") as mock_get_handler:
            mock_handler = AsyncMock()
            mock_handler.handle_incoming_call.return_value = {
                "accept_call": False,
                "message": "Number not registered",
                "dynamic_variables": {
                    "user_name": "stranger",
                    "chapter": "1",
                    "relationship_score": "0",
                    "engagement_state": "UNKNOWN",
                    "nikita_mood": "neutral",
                    "nikita_energy": "low",
                    "time_of_day": "afternoon",
                    "recent_topics": "",
                    "open_threads": "",
                },
                "conversation_config_override": {
                    "agent": {"first_message": "Sorry, I don't recognize this number."},
                },
            }
            mock_get_handler.return_value = mock_handler

            response = client.post(
                "/api/v1/voice/pre-call",
                json={
                    "caller_id": "+15551234567",  # Unknown number
                    "agent_id": "agent_test123",
                    "called_number": "+41445056044",
                    "call_sid": "CA987654321",
                },
            )

        assert response.status_code == 200
        data = response.json()

        # CRITICAL: dynamic_variables must NOT be null
        assert data["dynamic_variables"] is not None
        assert data["dynamic_variables"]["user_name"] == "stranger"
        assert data["dynamic_variables"]["chapter"] == "1"

        # conversation_config_override must also NOT be null
        assert data["conversation_config_override"] is not None

    def test_pre_call_unavailable_user_returns_dynamic_variables(self, client, mock_user):
        """Unavailable users still get dynamic_variables (not null).

        CRITICAL: ElevenLabs requires ALL dynamic_variables in response,
        even when the user is unavailable (e.g., chapter-based availability).
        """
        with patch("nikita.agents.voice.inbound.get_inbound_handler") as mock_get_handler:
            mock_handler = AsyncMock()
            mock_handler.handle_incoming_call.return_value = {
                "accept_call": False,
                "message": "Nikita is busy right now",
                "user_id": str(mock_user.id),
                "dynamic_variables": {
                    "user_name": "TestUser",
                    "chapter": "3",
                    "relationship_score": "65.0",
                    "engagement_state": "IN_ZONE",
                    "nikita_mood": "playful",
                    "nikita_energy": "medium",
                    "time_of_day": "afternoon",
                    "recent_topics": "work",
                    "open_threads": "weekend plans",
                },
                "conversation_config_override": {
                    "agent": {"first_message": "Nikita is busy right now"},
                },
            }
            mock_get_handler.return_value = mock_handler

            response = client.post(
                "/api/v1/voice/pre-call",
                json={
                    "caller_id": "+41787950009",
                    "agent_id": "agent_test123",
                    "called_number": "+41445056044",
                    "call_sid": "CA111222333",
                },
            )

        assert response.status_code == 200
        data = response.json()

        # CRITICAL: dynamic_variables must NOT be null even when unavailable
        assert data["dynamic_variables"] is not None
        assert len(data["dynamic_variables"]) == 9

    def test_pre_call_validates_request_schema(self, client):
        """Validates ElevenLabs sends all required fields (caller_id, agent_id, etc.)."""
        # Missing caller_id
        response = client.post(
            "/api/v1/voice/pre-call",
            json={
                "agent_id": "agent_test123",
                "called_number": "+41445056044",
                "call_sid": "CA123456789",
            },
        )
        assert response.status_code == 422  # Validation error

        # Missing agent_id
        response = client.post(
            "/api/v1/voice/pre-call",
            json={
                "caller_id": "+41787950009",
                "called_number": "+41445056044",
                "call_sid": "CA123456789",
            },
        )
        assert response.status_code == 422

        # Missing call_sid
        response = client.post(
            "/api/v1/voice/pre-call",
            json={
                "caller_id": "+41787950009",
                "agent_id": "agent_test123",
                "called_number": "+41445056044",
            },
        )
        assert response.status_code == 422

    def test_pre_call_response_format(self, client, mock_user):
        """Verify response format is exactly what ElevenLabs expects.

        Response MUST contain ONLY:
        - type: "conversation_initiation_client_data"
        - dynamic_variables: dict
        - conversation_config_override: dict
        """
        with patch("nikita.agents.voice.inbound.get_inbound_handler") as mock_get_handler:
            mock_handler = AsyncMock()
            mock_handler.handle_incoming_call.return_value = {
                "accept_call": True,
                "dynamic_variables": {"user_name": "Test"},
                "conversation_config_override": {"tts": {}},
            }
            mock_get_handler.return_value = mock_handler

            response = client.post(
                "/api/v1/voice/pre-call",
                json={
                    "caller_id": "+41787950009",
                    "agent_id": "agent_test123",
                    "called_number": "+41445056044",
                    "call_sid": "CA123456789",
                },
            )

        data = response.json()

        # EXACT format ElevenLabs expects
        assert "type" in data
        assert data["type"] == "conversation_initiation_client_data"
        assert "dynamic_variables" in data
        assert "conversation_config_override" in data

        # NO extra fields that could confuse ElevenLabs
        assert set(data.keys()) == {"type", "dynamic_variables", "conversation_config_override"}
