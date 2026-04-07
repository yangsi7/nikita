"""Tests for onboarding API endpoints (Spec 028).

Comprehensive HTTP-level coverage for all 8 onboarding endpoints:
  - GET  /status/{user_id}      (JWT + IDOR)
  - POST /initiate/{user_id}    (JWT + IDOR)
  - POST /server-tool           (signed token)
  - POST /webhook               (HMAC signature)
  - POST /pre-call              (HMAC when configured)
  - POST /call/{user_id}        (JWT + IDOR)
  - POST /skip/{user_id}        (JWT + IDOR)
  - POST /profile               (JWT)

Closes: #215 (GAP-003), #223 (GAP-004), #224 (GAP-005), #226 (GAP-008).
"""

import hashlib
import hmac
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from nikita.api.dependencies.auth import get_current_user_id
from nikita.api.routes.onboarding import get_onboarding_handler, get_user_repo, router

TEST_WEBHOOK_SECRET = "test-webhook-secret-for-hmac"
TEST_USER_PHONE = "+41787950009"


# === Helpers ===


def _make_signed_token(user_id: str, session_id: str, secret: str) -> str:
    """Generate a valid 4-part signed token: {user_id}:{session_id}:{ts}:{sig}."""
    ts = int(time.time())
    payload = f"{user_id}:{session_id}:{ts}"
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{sig}"


def _make_elevenlabs_signature(body: str, secret: str, ts: int | None = None) -> str:
    """Generate a valid ElevenLabs webhook signature header value."""
    ts = ts or int(time.time())
    message = f"{ts}.{body}"
    sig = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    return f"t={ts},v0={sig}"


# === Fixtures ===


@pytest.fixture
def mock_user():
    """Create a mock user."""
    user = MagicMock()
    user.id = uuid4()
    user.phone = TEST_USER_PHONE
    user.onboarding_status = "pending"
    user.onboarding_profile = {"user_name": "Simon"}
    user.onboarded_at = None
    user.telegram_id = None
    return user


@pytest.fixture
def mock_user_repo(mock_user):
    """Create a mock user repository."""
    repo = AsyncMock()
    repo.get_by_phone_number.return_value = mock_user
    repo.get.return_value = mock_user
    repo.update_onboarding_status.return_value = None
    repo.update_onboarding_profile.return_value = None
    return repo


@pytest.fixture
def test_user_id():
    """Fixed test user ID for JWT override."""
    return uuid4()


@pytest.fixture
def app(mock_user_repo, test_user_id):
    """Create test FastAPI app with mocked dependencies."""
    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v1/onboarding")
    test_app.dependency_overrides[get_user_repo] = lambda: mock_user_repo
    test_app.dependency_overrides[get_current_user_id] = lambda: test_user_id
    return test_app


@pytest.fixture
def app_no_auth(mock_user_repo):
    """Create test app WITHOUT auth override (for auth-required tests)."""
    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v1/onboarding")
    test_app.dependency_overrides[get_user_repo] = lambda: mock_user_repo
    return test_app


@pytest.fixture
def client(app):
    """Create test client with auth overridden."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def client_no_auth(app_no_auth):
    """Create test client WITHOUT auth override."""
    return TestClient(app_no_auth, raise_server_exceptions=False)


@pytest.fixture
def mock_settings():
    """Create mock settings with webhook secret configured."""
    settings = MagicMock()
    settings.elevenlabs_webhook_secret = TEST_WEBHOOK_SECRET
    return settings


# === TestPreCallWebhook (existing, unchanged) ===


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
        assert "conversation_config_override" in data
        assert "Simon" in data["conversation_config_override"]["agent"]["first_message"]

    def test_pre_call_handles_unknown_phone_gracefully(self, client, mock_user_repo):
        """Pre-call webhook should handle unknown phone gracefully."""
        mock_user_repo.get_by_phone_number.return_value = None

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
        mock_user.onboarding_profile = {}
        mock_user_repo.get_by_phone_number.return_value = mock_user

        response = client.post(
            "/api/v1/onboarding/pre-call",
            json={"caller_id": mock_user.phone},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["dynamic_variables"]["user_name"] == "there"
        assert data["dynamic_variables"]["user_id"] == str(mock_user.id)

    def test_pre_call_handles_empty_request_body(self, client, mock_user_repo):
        """Pre-call should handle empty/missing caller_id."""
        mock_user_repo.get_by_phone_number.return_value = None

        response = client.post(
            "/api/v1/onboarding/pre-call",
            json={},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["dynamic_variables"]["user_id"] == ""

    def test_pre_call_finds_user_by_called_number_for_outbound(
        self, client, mock_user, mock_user_repo
    ):
        """Pre-call should find user by called_number for outbound calls."""
        mock_user_repo.get_by_phone_number.side_effect = [None, mock_user]

        response = client.post(
            "/api/v1/onboarding/pre-call",
            json={
                "caller_id": "+41445056044",
                "called_number": mock_user.phone,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "conversation_initiation_client_data"
        assert data["dynamic_variables"]["user_id"] == str(mock_user.id)
        assert mock_user_repo.get_by_phone_number.call_count == 2


# === TestServerToolAuth (existing rejection tests) ===


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


# === TestServerToolWithValidToken (GAP-003 happy path, Closes #215) ===


class TestServerToolWithValidToken:
    """Test POST /api/v1/onboarding/server-tool with valid signed token."""

    def test_server_tool_accepts_valid_token(self, app, client, mock_settings):
        """Server tool should accept a request with a valid HMAC-signed token."""
        user_id = str(uuid4())
        session_id = f"onboarding_{user_id}_{int(time.time())}"
        token = _make_signed_token(user_id, session_id, TEST_WEBHOOK_SECRET)

        mock_handler = AsyncMock()
        mock_handler.handle_request.return_value = MagicMock(
            success=True, message="Profile updated", error=None, data=None
        )
        app.dependency_overrides[get_onboarding_handler] = lambda: mock_handler

        with (
            patch(
                "nikita.api.routes.onboarding.get_settings",
                return_value=mock_settings,
            ),
            patch(
                "nikita.api.utils.webhook_auth.get_settings",
                return_value=mock_settings,
            ),
        ):
            response = client.post(
                "/api/v1/onboarding/server-tool",
                json={
                    "tool_name": "collect_profile",
                    "user_id": user_id,
                    "signed_token": token,
                    "parameters": {"field_name": "timezone", "value": "UTC"},
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_server_tool_overrides_user_id_from_token(
        self, app, client, mock_settings
    ):
        """Server tool must use the user_id from the validated token, not the request body."""
        token_user_id = str(uuid4())
        body_user_id = str(uuid4())
        session_id = "onboarding_test_123"
        token = _make_signed_token(token_user_id, session_id, TEST_WEBHOOK_SECRET)

        captured_request = {}

        async def capture_handler(req):
            captured_request["user_id"] = req.user_id
            return MagicMock(success=True, message="OK", error=None, data=None)

        mock_handler = MagicMock()
        mock_handler.handle_request = capture_handler
        app.dependency_overrides[get_onboarding_handler] = lambda: mock_handler

        with (
            patch(
                "nikita.api.routes.onboarding.get_settings",
                return_value=mock_settings,
            ),
            patch(
                "nikita.api.utils.webhook_auth.get_settings",
                return_value=mock_settings,
            ),
        ):
            response = client.post(
                "/api/v1/onboarding/server-tool",
                json={
                    "tool_name": "collect_profile",
                    "user_id": body_user_id,
                    "signed_token": token,
                    "parameters": {"field_name": "timezone", "value": "UTC"},
                },
            )

        assert response.status_code == 200
        assert captured_request["user_id"] == token_user_id

    def test_server_tool_rejects_expired_token(self, client, mock_settings):
        """Server tool must reject a token with expired timestamp."""
        user_id = str(uuid4())
        session_id = "onboarding_test"
        ts = int(time.time()) - 7200  # 2 hours ago
        payload = f"{user_id}:{session_id}:{ts}"
        sig = hmac.new(
            TEST_WEBHOOK_SECRET.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()
        expired_token = f"{payload}:{sig}"

        with (
            patch(
                "nikita.api.routes.onboarding.get_settings",
                return_value=mock_settings,
            ),
            patch(
                "nikita.api.utils.webhook_auth.get_settings",
                return_value=mock_settings,
            ),
        ):
            response = client.post(
                "/api/v1/onboarding/server-tool",
                json={
                    "tool_name": "collect_profile",
                    "user_id": user_id,
                    "signed_token": expired_token,
                    "parameters": {"field_name": "timezone", "value": "UTC"},
                },
            )

        assert response.status_code == 401


# === TestWebhookSignature (existing rejection tests) ===


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
        with patch(
            "nikita.api.routes.onboarding.get_settings",
            return_value=mock_settings,
        ):
            response = client.post(
                "/api/v1/onboarding/webhook",
                json={"type": "call_ended", "data": {}},
                headers={"elevenlabs-signature": "t=0,v0=invalid"},
            )
        assert response.status_code == 401


# === TestWebhookWithValidSignature (GAP-005 happy path, Closes #224) ===


class TestWebhookWithValidSignature:
    """Test POST /api/v1/onboarding/webhook with valid HMAC signature."""

    def test_webhook_accepts_valid_signature(self, client, mock_settings):
        """Webhook should process request with valid HMAC signature."""
        body = json.dumps(
            {"type": "call_ended", "data": {"conversation_id": "conv_123"}}
        )
        signature = _make_elevenlabs_signature(body, TEST_WEBHOOK_SECRET)

        with patch(
            "nikita.api.routes.onboarding.get_settings",
            return_value=mock_settings,
        ):
            response = client.post(
                "/api/v1/onboarding/webhook",
                content=body,
                headers={
                    "content-type": "application/json",
                    "elevenlabs-signature": signature,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["event"] == "call_ended"

    def test_webhook_rejects_stale_timestamp(self, client, mock_settings):
        """Webhook must reject signature with timestamp >5 min old."""
        body = json.dumps({"type": "call_ended", "data": {}})
        stale_ts = int(time.time()) - 600  # 10 minutes ago
        signature = _make_elevenlabs_signature(body, TEST_WEBHOOK_SECRET, ts=stale_ts)

        with patch(
            "nikita.api.routes.onboarding.get_settings",
            return_value=mock_settings,
        ):
            response = client.post(
                "/api/v1/onboarding/webhook",
                content=body,
                headers={
                    "content-type": "application/json",
                    "elevenlabs-signature": signature,
                },
            )

        assert response.status_code == 401

    def test_webhook_processes_call_started_event(self, client, mock_settings):
        """Webhook should process call_started events."""
        body = json.dumps(
            {"type": "call_started", "data": {"conversation_id": "conv_456"}}
        )
        signature = _make_elevenlabs_signature(body, TEST_WEBHOOK_SECRET)

        with patch(
            "nikita.api.routes.onboarding.get_settings",
            return_value=mock_settings,
        ):
            response = client.post(
                "/api/v1/onboarding/webhook",
                content=body,
                headers={
                    "content-type": "application/json",
                    "elevenlabs-signature": signature,
                },
            )

        assert response.status_code == 200
        assert response.json()["event"] == "call_started"


# === TestIDORProtection (existing auth-required tests) ===


class TestIDORProtection:
    """Test IDOR protection on {user_id} endpoints (SEC-004, Closes #226)."""

    def test_skip_requires_auth(self, client_no_auth):
        """Skip endpoint must require JWT auth."""
        response = client_no_auth.post(
            f"/api/v1/onboarding/skip/{uuid4()}",
        )
        assert response.status_code in (401, 403)

    def test_status_requires_auth(self, client_no_auth):
        """Status endpoint must require JWT auth."""
        response = client_no_auth.get(
            f"/api/v1/onboarding/status/{uuid4()}",
        )
        assert response.status_code in (401, 403)


# === TestIDOROwnership (GAP-004 expanded, Closes #223) ===


class TestIDOROwnership:
    """Test IDOR ownership checks -- JWT user must match path user_id."""

    def test_initiate_rejects_different_user(
        self, client, test_user_id, mock_user_repo
    ):
        """Initiate must reject when JWT user != path user_id."""
        other_user_id = uuid4()
        assert other_user_id != test_user_id

        with patch("nikita.api.routes.onboarding.get_settings") as mock_s:
            mock_s.return_value.elevenlabs_webhook_secret = TEST_WEBHOOK_SECRET
            response = client.post(
                f"/api/v1/onboarding/initiate/{other_user_id}",
                json={"user_name": "Attacker"},
            )

        assert response.status_code == 403

    def test_call_rejects_different_user(self, client, test_user_id):
        """Call endpoint must reject when JWT user != path user_id."""
        other_user_id = uuid4()
        response = client.post(
            f"/api/v1/onboarding/call/{other_user_id}",
        )
        assert response.status_code == 403

    def test_status_returns_data_for_own_user(
        self, client, test_user_id, mock_user, mock_user_repo
    ):
        """Status should return data when JWT user matches path user_id."""
        mock_user.id = test_user_id
        mock_user_repo.get.return_value = mock_user

        response = client.get(
            f"/api/v1/onboarding/status/{test_user_id}",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == str(test_user_id)
        assert data["status"] == "pending"

    def test_skip_returns_data_for_own_user(
        self, client, test_user_id, mock_user, mock_user_repo
    ):
        """Skip should succeed when JWT user matches path user_id."""
        mock_user.id = test_user_id
        mock_user_repo.get.return_value = mock_user

        response = client.post(
            f"/api/v1/onboarding/skip/{test_user_id}",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "skipped"

    def test_status_rejects_different_user(self, client, test_user_id):
        """Status must reject when JWT user != path user_id."""
        other_user_id = uuid4()
        response = client.get(
            f"/api/v1/onboarding/status/{other_user_id}",
        )
        assert response.status_code == 403

    def test_skip_rejects_different_user(self, client, test_user_id):
        """Skip must reject when JWT user != path user_id."""
        other_user_id = uuid4()
        response = client.post(
            f"/api/v1/onboarding/skip/{other_user_id}",
        )
        assert response.status_code == 403


# === TestEndpointCoverage (GAP-008 -- routes not previously tested, Closes #226) ===


class TestEndpointCoverage:
    """Test endpoints not previously covered: initiate, skip, server-tool happy path, webhook happy path, profile."""

    def test_initiate_returns_signed_token(
        self, client, test_user_id, mock_user, mock_user_repo, mock_settings
    ):
        """Initiate should return agent_id, signed_token, session_id for valid user."""
        mock_user.id = test_user_id
        mock_user.onboarding_status = "pending"
        mock_user_repo.get.return_value = mock_user

        with patch(
            "nikita.api.routes.onboarding.get_settings",
            return_value=mock_settings,
        ):
            response = client.post(
                f"/api/v1/onboarding/initiate/{test_user_id}",
                json={"user_name": "Simon"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["agent_id"] == "agent_4801kewekhxgekzap1bqdr62dxvc"
        assert "signed_token" in data
        assert data["session_id"].startswith("onboarding_")
        assert data["user_id"] == str(test_user_id)
        assert data["dynamic_variables"]["user_name"] == "Simon"

    def test_initiate_rejects_already_onboarded(
        self, client, test_user_id, mock_user, mock_user_repo
    ):
        """Initiate should reject user with status=completed."""
        mock_user.id = test_user_id
        mock_user.onboarding_status = "completed"
        mock_user_repo.get.return_value = mock_user

        response = client.post(
            f"/api/v1/onboarding/initiate/{test_user_id}",
            json={"user_name": "Simon"},
        )

        assert response.status_code == 400
        assert "already onboarded" in response.json()["detail"]

    def test_initiate_rejects_skipped_user(
        self, client, test_user_id, mock_user, mock_user_repo
    ):
        """Initiate should reject user with status=skipped."""
        mock_user.id = test_user_id
        mock_user.onboarding_status = "skipped"
        mock_user_repo.get.return_value = mock_user

        response = client.post(
            f"/api/v1/onboarding/initiate/{test_user_id}",
        )

        assert response.status_code == 400

    def test_initiate_returns_404_for_unknown_user(
        self, client, test_user_id, mock_user_repo
    ):
        """Initiate should return 404 if user not found."""
        mock_user_repo.get.return_value = None

        response = client.post(
            f"/api/v1/onboarding/initiate/{test_user_id}",
        )

        assert response.status_code == 404

    def test_skip_sets_default_profile(
        self, client, test_user_id, mock_user, mock_user_repo
    ):
        """Skip should return status=skipped with default profile values."""
        mock_user.id = test_user_id
        mock_user_repo.get.return_value = mock_user

        response = client.post(
            f"/api/v1/onboarding/skip/{test_user_id}",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "skipped"
        assert data["profile"]["darkness_level"] == 3
        assert data["profile"]["pacing_weeks"] == 4
        assert data["profile"]["conversation_style"] == "balanced"
        assert data["profile"]["skipped"] is True

    def test_skip_returns_404_for_unknown_user(
        self, client, test_user_id, mock_user_repo
    ):
        """Skip should return 404 if user not found."""
        mock_user_repo.get.return_value = None

        response = client.post(
            f"/api/v1/onboarding/skip/{test_user_id}",
        )

        assert response.status_code == 404

    def test_status_returns_profile_data(
        self, client, test_user_id, mock_user, mock_user_repo
    ):
        """Status should return profile data for known user."""
        mock_user.id = test_user_id
        mock_user.onboarding_status = "completed"
        mock_user.onboarding_profile = {"darkness_level": 4}
        mock_user.onboarded_at = MagicMock()
        mock_user.onboarded_at.isoformat.return_value = "2026-01-01T00:00:00"
        mock_user_repo.get.return_value = mock_user

        response = client.get(
            f"/api/v1/onboarding/status/{test_user_id}",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["onboarded_at"] == "2026-01-01T00:00:00"
        assert data["profile"]["darkness_level"] == 4

    def test_status_returns_404_for_unknown_user(
        self, client, test_user_id, mock_user_repo
    ):
        """Status should return 404 if user not found."""
        mock_user_repo.get.return_value = None

        response = client.get(
            f"/api/v1/onboarding/status/{test_user_id}",
        )

        assert response.status_code == 404

    def test_server_tool_collect_profile_succeeds(
        self, app, client, mock_settings
    ):
        """Server tool collect_profile should succeed with valid token and handler."""
        user_id = str(uuid4())
        token = _make_signed_token(user_id, "session_1", TEST_WEBHOOK_SECRET)

        mock_handler = AsyncMock()
        mock_handler.handle_request.return_value = MagicMock(
            success=True,
            message="Field 'timezone' saved",
            error=None,
            data={"field": "timezone"},
        )
        app.dependency_overrides[get_onboarding_handler] = lambda: mock_handler

        with (
            patch(
                "nikita.api.routes.onboarding.get_settings",
                return_value=mock_settings,
            ),
            patch(
                "nikita.api.utils.webhook_auth.get_settings",
                return_value=mock_settings,
            ),
        ):
            response = client.post(
                "/api/v1/onboarding/server-tool",
                json={
                    "tool_name": "collect_profile",
                    "user_id": user_id,
                    "signed_token": token,
                    "parameters": {
                        "field_name": "timezone",
                        "value": "Europe/Zurich",
                    },
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "timezone" in data["message"]

    def test_webhook_processes_call_ended_event(self, client, mock_settings):
        """Webhook should process call_ended event and return status ok."""
        body = json.dumps(
            {
                "type": "call_ended",
                "data": {
                    "conversation_id": "conv_789",
                    "call_duration_seconds": 120,
                },
            }
        )
        signature = _make_elevenlabs_signature(body, TEST_WEBHOOK_SECRET)

        with patch(
            "nikita.api.routes.onboarding.get_settings",
            return_value=mock_settings,
        ):
            response = client.post(
                "/api/v1/onboarding/webhook",
                content=body,
                headers={
                    "content-type": "application/json",
                    "elevenlabs-signature": signature,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["event"] == "call_ended"

    def test_profile_endpoint_requires_jwt(self, client_no_auth):
        """POST /profile must require JWT auth (no override)."""
        response = client_no_auth.post(
            "/api/v1/onboarding/profile",
            json={
                "location_city": "Zurich",
                "social_scene": "techno",
                "drug_tolerance": 3,
            },
        )
        assert response.status_code in (401, 403)

    def test_initiate_requires_auth(self, client_no_auth):
        """Initiate endpoint must require JWT auth."""
        response = client_no_auth.post(
            f"/api/v1/onboarding/initiate/{uuid4()}",
        )
        assert response.status_code in (401, 403)

    def test_call_requires_auth(self, client_no_auth):
        """Call endpoint must require JWT auth."""
        response = client_no_auth.post(
            f"/api/v1/onboarding/call/{uuid4()}",
        )
        assert response.status_code in (401, 403)
