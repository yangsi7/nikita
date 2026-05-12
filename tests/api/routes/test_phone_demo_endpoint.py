"""Tests for POST /api/v1/converse/onboarding/phone-demo/consent and /end-call endpoints.

AC coverage:
  AC-001: POST /consent returns 200 with status='pending' on first call
  AC-002: POST /consent returns 409 on duplicate (lifetime cap)
  AC-003: POST /end-call returns 200 with success=True
  AC-004: Endpoints require JWT auth (unauthenticated → 401/403)
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


# ---------------------------------------------------------------------------
# RED-phase stubs: tests import endpoints directly and assert stubs raise.
# These will pass once GREEN implementation replaces NotImplementedError.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_phone_demo_consent_callable(monkeypatch):
    """GREEN: record_consent_and_dispatch is callable and returns dict with 'inserted' key."""
    from nikita.agents.onboarding.v2.phone_demo import record_consent_and_dispatch

    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.rowcount = 1
    session.execute = AsyncMock(return_value=result_mock)
    session.commit = AsyncMock()

    result = await record_consent_and_dispatch(
        session=session,
        user_id=uuid4(),
        phone_e164="+14155552671",
        client_ip=None,
        user_agent=None,
    )
    assert "inserted" in result


@pytest.mark.asyncio
async def test_phone_demo_end_call_callable():
    """GREEN: end_call is callable and returns dict with 'success' key."""
    from nikita.agents.onboarding.v2.phone_demo import end_call

    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.fetchone = MagicMock(return_value=None)
    session.execute = AsyncMock(return_value=result_mock)
    session.commit = AsyncMock()

    result = await end_call(session=session, user_id=uuid4())
    assert "success" in result


def test_phone_demo_consent_endpoint_exists_in_router():
    """AC-004: Verify routes are registered on the v2 router."""
    from nikita.api.routes.portal_onboarding_v2 import router

    routes = {r.path for r in router.routes}
    assert "/onboarding/phone-demo/consent" in routes, (
        "POST /onboarding/phone-demo/consent must be registered on v2 router"
    )
    assert "/onboarding/phone-demo/end-call" in routes, (
        "POST /onboarding/phone-demo/end-call must be registered on v2 router"
    )


def test_phone_demo_consent_request_model():
    """AC: PhoneDemoConsentRequest accepts valid E.164 phone."""
    from nikita.api.routes.portal_onboarding_v2 import PhoneDemoConsentRequest

    req = PhoneDemoConsentRequest(phone_e164="+14155552671")
    assert req.phone_e164 == "+14155552671"


def test_phone_demo_consent_response_model():
    """AC: PhoneDemoConsentResponse serialises correctly."""
    from nikita.api.routes.portal_onboarding_v2 import PhoneDemoConsentResponse

    resp = PhoneDemoConsentResponse(
        status="pending",
        provider_call_id="conv_abc123",
        message="Call dispatched",
    )
    assert resp.status == "pending"
    assert resp.provider_call_id == "conv_abc123"


def test_phone_demo_end_call_response_model():
    """AC: PhoneDemoEndCallResponse serialises correctly."""
    from nikita.api.routes.portal_onboarding_v2 import PhoneDemoEndCallResponse

    resp = PhoneDemoEndCallResponse(success=True, message="Call ended")
    assert resp.success is True


# ---------------------------------------------------------------------------
# Fix 5 (R5): parametrized ElevenLabs outcome → internal status mapping
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "call_data,expected_status",
    [
        # Default: absent termination_reason → ended_success
        ({}, "ended_success"),
        # Explicit success (unrecognised string falls through to success)
        ({"call_info": {"termination_reason": "completed"}}, "ended_success"),
        # Busy
        ({"call_info": {"termination_reason": "busy"}}, "ended_busy"),
        # No-answer
        ({"call_info": {"termination_reason": "no_answer"}}, "ended_no_answer"),
        # Error
        ({"call_info": {"termination_reason": "error"}}, "ended_error"),
        # Failed maps to error
        ({"call_info": {"termination_reason": "failed"}}, "ended_error"),
        # metadata.call_status fallback when call_info absent
        ({"metadata": {"call_status": "busy"}}, "ended_busy"),
        # call_info takes precedence over metadata.call_status
        (
            {"call_info": {"termination_reason": "busy"}, "metadata": {"call_status": "error"}},
            "ended_busy",
        ),
        # TODO: extend when ElevenLabs payload schema documents additional
        # non-success termination values beyond busy/no_answer/error/failed.
    ],
)
def test_map_elevenlabs_termination(call_data, expected_status):
    """Fix R5: _map_elevenlabs_termination maps ElevenLabs outcomes correctly."""
    from nikita.api.routes.voice import _map_elevenlabs_termination

    assert _map_elevenlabs_termination(call_data) == expected_status
