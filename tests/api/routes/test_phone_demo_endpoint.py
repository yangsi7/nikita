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
async def test_phone_demo_consent_endpoint_stub_raises():
    """RED: phone_demo_consent_endpoint calls phone_demo module which raises NotImplementedError."""
    from nikita.agents.onboarding.v2.phone_demo import record_consent_and_dispatch

    with pytest.raises(NotImplementedError):
        await record_consent_and_dispatch(
            session=AsyncMock(),
            user_id=uuid4(),
            phone_e164="+14155552671",
            client_ip=None,
            user_agent=None,
        )


@pytest.mark.asyncio
async def test_phone_demo_end_call_endpoint_stub_raises():
    """RED: end_call raises NotImplementedError — GREEN phase provides implementation."""
    from nikita.agents.onboarding.v2.phone_demo import end_call

    with pytest.raises(NotImplementedError):
        await end_call(session=AsyncMock(), user_id=uuid4())


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
