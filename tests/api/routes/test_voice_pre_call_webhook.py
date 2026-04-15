"""Voice pre-call webhook payload shape tests — Spec 213 PR 213-5.

AC-7.1: POST /api/v1/voice/pre-call returns conversation_initiation_client_data.
AC-7.2: Payload includes OnboardingV2ProfileResponse shape fields
        (name, age, occupation, phone) in dynamic_variables.
        [XFAIL: Spec 214 scope — handler currently returns VoiceService fields only]
AC-7.3: With BACKSTORY_HOOK_PROBABILITY=1.0, venue name appears in voice prompt;
        with 0.0, absent.
        [XFAIL: Spec 214 scope — backstory injection into voice config is Spec 214]

The xfail marker documents the contract expectation without blocking the current
PR. Spec 214 (portal-onboarding-wizard) owns the chosen_option write path that
would pass the selected BackstoryOption into the pre-call override.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from nikita.api.routes.voice import router


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def app() -> FastAPI:
    """Create test FastAPI app with voice router."""
    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v1/voice")
    return test_app


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    """Create test client (no exception propagation for HTTP error tests)."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture()
def webhook_secret() -> str:
    return "test_pre_call_secret"


@pytest.fixture()
def mock_settings(webhook_secret: str) -> MagicMock:
    settings = MagicMock()
    settings.elevenlabs_webhook_secret = webhook_secret
    return settings


@pytest.fixture()
def pre_call_body() -> dict:
    return {
        "caller_id": "+14155551234",
        "agent_id": "agent_test_001",
        "called_number": "+18005551234",
        "call_sid": "CAtest123abc",
    }


# ---------------------------------------------------------------------------
# AC-7.1: basic pre-call response shape
# ---------------------------------------------------------------------------


def test_pre_call_returns_conversation_initiation_client_data(
    client: TestClient,
    pre_call_body: dict,
    mock_settings: MagicMock,
    webhook_secret: str,
) -> None:
    """AC-7.1: POST /pre-call returns type='conversation_initiation_client_data'."""
    mock_handler = AsyncMock()
    mock_handler.handle_incoming_call.return_value = {
        "accept_call": True,
        "dynamic_variables": {"user_id": str(uuid4())},
        "conversation_config_override": None,
    }

    with patch("nikita.api.routes.voice.get_settings", return_value=mock_settings), \
         patch("nikita.agents.voice.inbound.get_inbound_handler", return_value=mock_handler), \
         patch("nikita.api.routes.voice.voice_rate_limit", return_value=None):
        response = client.post(
            "/api/v1/voice/pre-call",
            content=json.dumps(pre_call_body),
            headers={
                "Content-Type": "application/json",
                "x-webhook-secret": webhook_secret,
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "conversation_initiation_client_data"


def test_pre_call_rejects_missing_secret(
    client: TestClient,
    pre_call_body: dict,
    mock_settings: MagicMock,
) -> None:
    """AC-7.1: missing x-webhook-secret returns 401."""
    with patch("nikita.api.routes.voice.get_settings", return_value=mock_settings), \
         patch("nikita.api.routes.voice.voice_rate_limit", return_value=None):
        response = client.post(
            "/api/v1/voice/pre-call",
            content=json.dumps(pre_call_body),
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# AC-7.2: OnboardingV2ProfileResponse shape in dynamic_variables (Spec 214)
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    reason=(
        "Spec 214 scope: handler currently returns VoiceService fields only. "
        "OnboardingV2ProfileResponse shape (name/age/occupation/phone) injected "
        "into dynamic_variables is owned by Spec 214 portal-onboarding-wizard."
    ),
    strict=False,
)
def test_payload_includes_v2_profile_response(
    client: TestClient,
    pre_call_body: dict,
    mock_settings: MagicMock,
    webhook_secret: str,
) -> None:
    """AC-7.2: dynamic_variables includes OnboardingV2ProfileResponse shape fields.

    Expected fields: name, age, occupation, phone (from Spec 213 contracts.py).
    This is a contract expectation — currently not met; Spec 214 owns the fix.
    """
    from nikita.onboarding.contracts import OnboardingV2ProfileResponse

    user_id = uuid4()
    mock_handler = AsyncMock()
    mock_handler.handle_incoming_call.return_value = {
        "accept_call": True,
        "dynamic_variables": {
            "user_id": str(user_id),
            # Fields from OnboardingV2ProfileResponse shape that Spec 214 must add:
            "name": "Anna",
            "age": "28",
            "occupation": "architect",
            "phone": "+14155551234",
        },
        "conversation_config_override": None,
    }

    with patch("nikita.api.routes.voice.get_settings", return_value=mock_settings), \
         patch("nikita.agents.voice.inbound.get_inbound_handler", return_value=mock_handler), \
         patch("nikita.api.routes.voice.voice_rate_limit", return_value=None):
        response = client.post(
            "/api/v1/voice/pre-call",
            content=json.dumps(pre_call_body),
            headers={
                "Content-Type": "application/json",
                "x-webhook-secret": webhook_secret,
            },
        )

    assert response.status_code == 200
    dv = response.json().get("dynamic_variables", {})

    # Assert OnboardingV2ProfileResponse shape fields present
    for field in ("name", "age", "occupation", "phone"):
        assert field in dv, (
            f"OnboardingV2ProfileResponse field '{field}' missing from dynamic_variables"
        )


# ---------------------------------------------------------------------------
# AC-7.3: backstory venue in voice prompt (Spec 214)
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    reason=(
        "Spec 214 scope: backstory injection into conversation_config_override "
        "first_message requires chosen_option write path (Spec 214 D5). "
        "BACKSTORY_HOOK_PROBABILITY gating is only wired for Telegram text path "
        "in Spec 213 PR 213-5."
    ),
    strict=False,
)
def test_voice_prompt_includes_backstory_when_probability_one(
    client: TestClient,
    pre_call_body: dict,
    mock_settings: MagicMock,
    webhook_secret: str,
) -> None:
    """AC-7.3: with BACKSTORY_HOOK_PROBABILITY=1.0, venue name appears in voice prompt.

    When the user has a chosen backstory option with venue='Berghain', the
    pre-call override first_message should reference 'Berghain'.
    Currently not implemented — Spec 214 owns this path.
    """
    mock_handler = AsyncMock()
    mock_handler.handle_incoming_call.return_value = {
        "accept_call": True,
        "dynamic_variables": {"user_id": str(uuid4())},
        "conversation_config_override": {
            "agent": {
                "first_message": "Hey... I was at Berghain when you called, you know.",
            }
        },
    }

    with patch("nikita.api.routes.voice.get_settings", return_value=mock_settings), \
         patch("nikita.agents.voice.inbound.get_inbound_handler", return_value=mock_handler), \
         patch("nikita.api.routes.voice.voice_rate_limit", return_value=None), \
         patch("nikita.onboarding.tuning.BACKSTORY_HOOK_PROBABILITY", 1.0):
        response = client.post(
            "/api/v1/voice/pre-call",
            content=json.dumps(pre_call_body),
            headers={
                "Content-Type": "application/json",
                "x-webhook-secret": webhook_secret,
            },
        )

    assert response.status_code == 200
    override = response.json().get("conversation_config_override") or {}
    first_msg = (override.get("agent") or {}).get("first_message", "")
    assert "Berghain" in first_msg, (
        f"Expected 'Berghain' in voice first_message, got: {first_msg!r}"
    )


@pytest.mark.xfail(
    reason="Spec 214 scope — same as test_voice_prompt_includes_backstory_when_probability_one",
    strict=False,
)
def test_voice_prompt_excludes_backstory_when_probability_zero(
    client: TestClient,
    pre_call_body: dict,
    mock_settings: MagicMock,
    webhook_secret: str,
) -> None:
    """AC-7.3: with BACKSTORY_HOOK_PROBABILITY=0.0, venue name absent from voice prompt."""
    mock_handler = AsyncMock()
    mock_handler.handle_incoming_call.return_value = {
        "accept_call": True,
        "dynamic_variables": {"user_id": str(uuid4())},
        "conversation_config_override": {
            "agent": {
                "first_message": "Hey, who is this?",  # No venue
            }
        },
    }

    with patch("nikita.api.routes.voice.get_settings", return_value=mock_settings), \
         patch("nikita.agents.voice.inbound.get_inbound_handler", return_value=mock_handler), \
         patch("nikita.api.routes.voice.voice_rate_limit", return_value=None), \
         patch("nikita.onboarding.tuning.BACKSTORY_HOOK_PROBABILITY", 0.0):
        response = client.post(
            "/api/v1/voice/pre-call",
            content=json.dumps(pre_call_body),
            headers={
                "Content-Type": "application/json",
                "x-webhook-secret": webhook_secret,
            },
        )

    assert response.status_code == 200
    override = response.json().get("conversation_config_override") or {}
    first_msg = (override.get("agent") or {}).get("first_message", "")
    assert "Berghain" not in first_msg
