"""Tests for onboarding API endpoints (Spec 028).

Tests for pre-call webhook endpoint that provides dynamic variables
to ElevenLabs server tools.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from nikita.api.routes.onboarding import get_user_repo, router


@pytest.fixture
def mock_user():
    """Create a mock user."""
    user = MagicMock()
    user.id = uuid4()
    user.phone = "+41787950009"
    user.onboarding_status = "pending"
    user.onboarding_profile = {"user_name": "Simon"}
    return user


@pytest.fixture
def mock_user_repo(mock_user):
    """Create a mock user repository."""
    repo = AsyncMock()
    repo.get_by_phone_number.return_value = mock_user
    return repo


@pytest.fixture
def app(mock_user_repo):
    """Create test FastAPI app with mocked dependencies."""
    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v1/onboarding")
    # Override dependency
    test_app.dependency_overrides[get_user_repo] = lambda: mock_user_repo
    return test_app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app, raise_server_exceptions=False)


class TestPreCallWebhook:
    """Test POST /api/v1/onboarding/pre-call endpoint."""

    def test_pre_call_returns_user_id_for_known_phone(
        self, client, mock_user, mock_user_repo
    ):
        """Pre-call webhook should return user_id for server tools."""
        mock_user_repo.get_by_phone_number.return_value = mock_user

        response = client.post(
            "/api/v1/onboarding/pre-call",
            json={"caller_id": mock_user.phone},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "conversation_initiation_client_data"
        assert data["dynamic_variables"]["user_id"] == str(mock_user.id)
        assert data["dynamic_variables"]["user_name"] == "Simon"
        # Should have personalized first message
        assert "conversation_config_override" in data
        assert "Simon" in data["conversation_config_override"]["agent"]["first_message"]

    def test_pre_call_handles_unknown_phone_gracefully(self, client, mock_user_repo):
        """Pre-call webhook should handle unknown phone gracefully."""
        mock_user_repo.get_by_phone_number.return_value = None  # No user found

        response = client.post(
            "/api/v1/onboarding/pre-call",
            json={"caller_id": "+19999999999"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "conversation_initiation_client_data"
        assert data["dynamic_variables"]["user_id"] == ""
        assert data["dynamic_variables"]["user_name"] == "there"

    def test_pre_call_with_user_without_name(self, client, mock_user, mock_user_repo):
        """Pre-call should use default name if user has no name in profile."""
        mock_user.onboarding_profile = {}  # Empty profile, no user_name
        mock_user_repo.get_by_phone_number.return_value = mock_user

        response = client.post(
            "/api/v1/onboarding/pre-call",
            json={"caller_id": mock_user.phone},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["dynamic_variables"]["user_name"] == "there"
        # Should still have user_id
        assert data["dynamic_variables"]["user_id"] == str(mock_user.id)

    def test_pre_call_handles_empty_request_body(self, client, mock_user_repo):
        """Pre-call should handle empty/missing caller_id."""
        mock_user_repo.get_by_phone_number.return_value = None

        response = client.post(
            "/api/v1/onboarding/pre-call",
            json={},  # No caller_id
        )

        assert response.status_code == 200
        data = response.json()
        assert data["dynamic_variables"]["user_id"] == ""

    def test_pre_call_finds_user_by_called_number_for_outbound(
        self, client, mock_user, mock_user_repo
    ):
        """Pre-call should find user by called_number for outbound calls.

        For outbound calls:
        - caller_id = Meta-Nikita's phone (not the user)
        - called_number = User's phone
        """
        # First call with caller_id (Meta-Nikita's phone) returns None
        # Second call with called_number (user's phone) returns user
        mock_user_repo.get_by_phone_number.side_effect = [None, mock_user]

        response = client.post(
            "/api/v1/onboarding/pre-call",
            json={
                "caller_id": "+41445056044",  # Meta-Nikita's phone
                "called_number": mock_user.phone,  # User's phone
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "conversation_initiation_client_data"
        assert data["dynamic_variables"]["user_id"] == str(mock_user.id)
        # Verify both phone numbers were tried
        assert mock_user_repo.get_by_phone_number.call_count == 2


class TestServerToolAuth:
    """Test POST /api/v1/onboarding/server-tool auth (SEC-001, Closes #220)."""

    def test_rejects_request_without_token(self, client):
        """Server tool must reject requests without signed token."""
        response = client.post(
            "/api/v1/onboarding/server-tool",
            json={
                "tool_name": "collect_profile",
                "user_id": str(uuid4()),
                "parameters": {"field_name": "timezone", "value": "UTC"},
            },
        )
        assert response.status_code == 401

    def test_rejects_invalid_token(self, client):
        """Server tool must reject requests with invalid token."""
        response = client.post(
            "/api/v1/onboarding/server-tool",
            json={
                "tool_name": "collect_profile",
                "user_id": str(uuid4()),
                "signed_token": "invalid:token:format",
                "parameters": {"field_name": "timezone", "value": "UTC"},
            },
        )
        assert response.status_code == 401


class TestWebhookSignature:
    """Test POST /api/v1/onboarding/webhook signature enforcement (SEC-003, Closes #225)."""

    def test_rejects_missing_signature(self, client):
        """Webhook must reject requests without signature header."""
        response = client.post(
            "/api/v1/onboarding/webhook",
            json={"type": "call_ended", "data": {}},
        )
        assert response.status_code == 401

    def test_rejects_invalid_signature(self, client):
        """Webhook must reject requests with invalid signature."""
        mock_settings = MagicMock()
        mock_settings.elevenlabs_webhook_secret = "test-secret"
        with patch("nikita.api.routes.onboarding.get_settings", return_value=mock_settings):
            response = client.post(
                "/api/v1/onboarding/webhook",
                json={"type": "call_ended", "data": {}},
                headers={"elevenlabs-signature": "t=0,v0=invalid"},
            )
        assert response.status_code == 401


class TestIDORProtection:
    """Test IDOR protection on {user_id} endpoints (SEC-004, Closes #226)."""

    def test_skip_requires_auth(self, client):
        """Skip endpoint must require JWT auth."""
        response = client.post(
            f"/api/v1/onboarding/skip/{uuid4()}",
        )
        # Should get 401/403 since no JWT provided
        assert response.status_code in (401, 403)

    def test_status_requires_auth(self, client):
        """Status endpoint must require JWT auth."""
        response = client.get(
            f"/api/v1/onboarding/status/{uuid4()}",
        )
        assert response.status_code in (401, 403)
