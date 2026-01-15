"""Tests for onboarding API endpoints (Spec 028).

Tests for pre-call webhook endpoint that provides dynamic variables
to ElevenLabs server tools.
"""

from unittest.mock import AsyncMock, MagicMock
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
