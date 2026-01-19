"""Tests for ElevenLabs webhook endpoint (US-10: Post-Call Processing).

Tests for T053-T054 acceptance criteria:
- AC-FR015-001: Transcript stored when post_call_transcription received
- AC-FR015-005: Only accepts webhooks with valid HMAC signature
- AC-T053.1-4: Webhook handler for post_call_transcription
- AC-T054.1-4: HMAC signature validation
"""

import hashlib
import hmac
import time
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
def webhook_secret():
    """Test webhook secret."""
    return "test_webhook_secret_123"


@pytest.fixture
def mock_settings(webhook_secret):
    """Create mock settings with webhook secret."""
    settings = MagicMock()
    settings.elevenlabs_webhook_secret = webhook_secret
    return settings


def create_webhook_signature(payload: str, secret: str, timestamp: int | None = None) -> str:
    """Create valid HMAC signature for testing."""
    timestamp = timestamp or int(time.time())
    message = f"{timestamp}.{payload}"
    signature = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"t={timestamp},v0={signature}"


class TestWebhookSignatureValidation:
    """Test HMAC signature validation (T054)."""

    def test_valid_signature_accepted(self, client, webhook_secret):
        """AC-T054.1: Valid signature format accepted."""
        payload = '{"type": "post_call_transcription", "data": {}}'
        signature = create_webhook_signature(payload, webhook_secret)

        with patch("nikita.api.routes.voice.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.elevenlabs_webhook_secret = webhook_secret
            mock_get_settings.return_value = mock_settings

            with patch(
                "nikita.api.routes.voice._process_webhook_event", new_callable=AsyncMock
            ) as mock_process:
                mock_process.return_value = {"status": "processed"}

                response = client.post(
                    "/api/v1/voice/webhook",
                    content=payload,
                    headers={
                        "elevenlabs-signature": signature,
                        "content-type": "application/json",
                    },
                )

        # Should not return 401 (signature valid)
        assert response.status_code != 401

    def test_missing_signature_rejected(self, client):
        """AC-T054.4: Missing signature returns 401."""
        payload = '{"type": "post_call_transcription", "data": {}}'

        response = client.post(
            "/api/v1/voice/webhook",
            content=payload,
            headers={"content-type": "application/json"},
        )

        assert response.status_code == 401
        assert "signature" in response.json()["detail"].lower()

    def test_invalid_signature_rejected(self, client, webhook_secret):
        """AC-T054.3: Invalid signature returns 401."""
        payload = '{"type": "post_call_transcription", "data": {}}'
        bad_signature = "t=1234567890,v0=invalid_signature_hash"

        with patch("nikita.api.routes.voice.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.elevenlabs_webhook_secret = webhook_secret
            mock_get_settings.return_value = mock_settings

            response = client.post(
                "/api/v1/voice/webhook",
                content=payload,
                headers={
                    "elevenlabs-signature": bad_signature,
                    "content-type": "application/json",
                },
            )

        assert response.status_code == 401

    def test_expired_timestamp_rejected(self, client, webhook_secret):
        """AC-T054.2: Timestamps older than 5 minutes rejected."""
        payload = '{"type": "post_call_transcription", "data": {}}'
        old_timestamp = int(time.time()) - 600  # 10 minutes ago
        signature = create_webhook_signature(payload, webhook_secret, old_timestamp)

        with patch("nikita.api.routes.voice.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.elevenlabs_webhook_secret = webhook_secret
            mock_get_settings.return_value = mock_settings

            response = client.post(
                "/api/v1/voice/webhook",
                content=payload,
                headers={
                    "elevenlabs-signature": signature,
                    "content-type": "application/json",
                },
            )

        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()


class TestWebhookHandler:
    """Test webhook event handling (T053)."""

    def test_post_call_transcription_stored(self, client, webhook_secret):
        """AC-FR015-001: Transcript stored when post_call_transcription received."""
        session_id = f"voice_session_{uuid4()}"
        payload = f'''{{
            "type": "post_call_transcription",
            "event_timestamp": 1739537297,
            "data": {{
                "conversation_id": "{session_id}",
                "transcript": [{{"role": "agent", "message": "Hello!", "time_in_call_secs": 0}}, {{"role": "user", "message": "Hi!", "time_in_call_secs": 2}}],
                "conversation_initiation_client_data": {{
                    "dynamic_variables": {{
                        "secret__user_id": "test-user-id"
                    }}
                }}
            }}
        }}'''
        signature = create_webhook_signature(payload, webhook_secret)

        with patch("nikita.api.routes.voice.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.elevenlabs_webhook_secret = webhook_secret
            mock_get_settings.return_value = mock_settings

            with patch(
                "nikita.api.routes.voice._process_webhook_event", new_callable=AsyncMock
            ) as mock_process:
                mock_process.return_value = {"status": "processed", "transcript_stored": True}

                response = client.post(
                    "/api/v1/voice/webhook",
                    content=payload,
                    headers={
                        "elevenlabs-signature": signature,
                        "content-type": "application/json",
                    },
                )

        assert response.status_code == 200
        mock_process.assert_called_once()

    def test_call_initiation_failure_logged(self, client, webhook_secret):
        """AC-T053.4: call_initiation_failure events logged."""
        payload = '''{
            "type": "call_initiation_failure",
            "event_timestamp": 1739537297,
            "data": {
                "conversation_id": "test-conv-id",
                "failure_reason": "agent_busy"
            }
        }'''
        signature = create_webhook_signature(payload, webhook_secret)

        with patch("nikita.api.routes.voice.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.elevenlabs_webhook_secret = webhook_secret
            mock_get_settings.return_value = mock_settings

            with patch(
                "nikita.api.routes.voice._process_webhook_event", new_callable=AsyncMock
            ) as mock_process:
                mock_process.return_value = {"status": "logged", "event_type": "call_initiation_failure"}

                response = client.post(
                    "/api/v1/voice/webhook",
                    content=payload,
                    headers={
                        "elevenlabs-signature": signature,
                        "content-type": "application/json",
                    },
                )

        assert response.status_code == 200

    def test_extracts_session_metadata(self, client, webhook_secret):
        """AC-T053.3: Extracts transcript and session metadata."""
        conversation_id = f"conv_{uuid4()}"
        payload = f'''{{
            "type": "post_call_transcription",
            "event_timestamp": 1739537297,
            "data": {{
                "conversation_id": "{conversation_id}",
                "transcript": [{{"role": "user", "message": "Hi there!", "time_in_call_secs": 0}}],
                "metadata": {{
                    "call_duration_secs": 120,
                    "turn_count": 5
                }},
                "conversation_initiation_client_data": {{
                    "dynamic_variables": {{
                        "secret__user_id": "test-user-id"
                    }}
                }}
            }}
        }}'''
        signature = create_webhook_signature(payload, webhook_secret)

        with patch("nikita.api.routes.voice.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.elevenlabs_webhook_secret = webhook_secret
            mock_get_settings.return_value = mock_settings

            with patch(
                "nikita.api.routes.voice._process_webhook_event", new_callable=AsyncMock
            ) as mock_process:
                mock_process.return_value = {"status": "processed"}

                response = client.post(
                    "/api/v1/voice/webhook",
                    content=payload,
                    headers={
                        "elevenlabs-signature": signature,
                        "content-type": "application/json",
                    },
                )

        # Verify the event data was passed to the processor
        call_args = mock_process.call_args
        assert call_args is not None
        event_data = call_args[0][0]  # First positional arg
        # ElevenLabs nests data under "data" key (Issue #12 fix)
        data = event_data.get("data", {})
        assert data.get("conversation_id") == conversation_id
        assert len(data.get("transcript", [])) == 1
        assert data.get("transcript")[0]["message"] == "Hi there!"

    def test_unknown_event_type_handled(self, client, webhook_secret):
        """Unknown event types should be logged but not cause errors."""
        payload = '{"type": "unknown_event_type", "data": {}}'
        signature = create_webhook_signature(payload, webhook_secret)

        with patch("nikita.api.routes.voice.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.elevenlabs_webhook_secret = webhook_secret
            mock_get_settings.return_value = mock_settings

            with patch(
                "nikita.api.routes.voice._process_webhook_event", new_callable=AsyncMock
            ) as mock_process:
                mock_process.return_value = {"status": "ignored", "reason": "unknown_event_type"}

                response = client.post(
                    "/api/v1/voice/webhook",
                    content=payload,
                    headers={
                        "elevenlabs-signature": signature,
                        "content-type": "application/json",
                    },
                )

        assert response.status_code == 200
