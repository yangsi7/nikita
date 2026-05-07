"""Sub-PR 217-2c (GH #555 + #556): ModelHTTPError retry + structured logging.

These tests pin the new behavior introduced by 217-2c on the
``POST /api/v1/onboarding/answer`` route:

  1. ``ModelHTTPError`` (Anthropic 4xx/5xx) raised by the conversation
     agent is caught BEFORE the existing ``except (UnexpectedModelBehavior,
     UsageLimitExceeded, UserError)`` tuple, with rich structured logging
     (`status_code`, `model_name`, `body`).
  2. Bounded exponential-backoff retry on a documented set of transient
     status codes (429, 502, 503, 504, 529): 3 attempts max, sleeps
     keyed by ``RETRY_BACKOFF_MS = (250, 750, 1750)``. Non-retryable
     statuses (e.g. 500) fall through to fallback on the first failure.
  3. Three new structured log events emit on the documented
     boundaries: ``answer_agent_retry_attempt``,
     ``answer_agent_model_http_error``, ``answer_agent_fallback_envelope``.
  4. Tuning constants are locked: regression-guard tests assert the
     exact values per ``.claude/rules/tuning-constants.md``.

Patches the helper at the route's import namespace
(``nikita.api.routes.portal_onboarding.run_agent_with_capture``) so
retry call-count is controllable per test. ``asyncio.sleep`` is
no-op'd to keep wall-clock < 1 s.

Cross-references:
  - Spike: ``docs-to-process/20260508-gh555-be-archetype-timeout-spike.md``
  - GH #555 (HIGH), GH #556 (MEDIUM)
  - .claude/rules/tuning-constants.md (regression-guard tests)
  - .claude/rules/testing.md (no zero-assertion shells, patch source)
"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic_ai.exceptions import ModelHTTPError
from sqlalchemy.ext.asyncio import AsyncSession


USER_ID = UUID("550e8400-e29b-41d4-a716-446655440042")


# ---------------------------------------------------------------------------
# Fixtures — mirror tests/api/routes/test_onboarding_answer.py shape so the
# retry/fallback semantics are exercised against the real router & contracts.
# ---------------------------------------------------------------------------


def _make_app(user_id: UUID = USER_ID) -> tuple[FastAPI, AsyncMock]:
    from nikita.api.dependencies.auth import (
        AuthenticatedUser,
        get_authenticated_user,
        get_current_user_id,
    )
    from nikita.api.middleware.rate_limit import answer_rate_limit
    from nikita.api.routes.portal_onboarding import router
    from nikita.db.database import get_async_session

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/onboarding")

    mock_session = AsyncMock(spec=AsyncSession)

    async def _session_override():
        return mock_session

    async def _auth_override() -> AuthenticatedUser:
        return AuthenticatedUser(id=user_id, email="test+217-2c@example.com")

    async def _rate_limit_bypass() -> None:
        return None

    app.dependency_overrides[get_async_session] = _session_override
    app.dependency_overrides[get_authenticated_user] = _auth_override
    app.dependency_overrides[get_current_user_id] = lambda: user_id
    app.dependency_overrides[answer_rate_limit] = _rate_limit_bypass

    return app, mock_session


def _make_user(profile: dict | None = None) -> MagicMock:
    user = MagicMock()
    user.id = USER_ID
    user.onboarding_profile = profile if profile is not None else {}
    return user


def _make_run_result(*, reply: str = "Got it.") -> MagicMock:
    """Successful agent-run result with a non-extracting TurnOutput."""
    from nikita.agents.onboarding.conversation_agent import TurnOutput

    output = TurnOutput(delta=None, reply=reply, next_slot_kind=None)
    result = MagicMock(name="agent_run_result")
    result.output = output
    return result


def _post_payload() -> dict:
    return {
        "slot_kind": "city",
        "value": "Zürich",
        "turn_id": str(uuid4()),
    }


def _no_op_sleep_patch():
    """Patch asyncio.sleep so retry loops don't spend wall-clock."""
    return patch(
        "nikita.api.routes.portal_onboarding.asyncio.sleep",
        new=AsyncMock(return_value=None),
    )


def _common_route_patches(*, run_capture_mock: AsyncMock) -> list:
    """Install the boundary mocks every retry/fallback test needs."""
    user_repo = MagicMock()
    user_repo.get = AsyncMock(return_value=_make_user(profile={}))
    idem_store = MagicMock()
    idem_store.get = AsyncMock(return_value=None)
    idem_store.put = AsyncMock()
    agent = MagicMock()
    agent.run = AsyncMock(return_value=_make_run_result())  # not used; safety net

    return [
        patch(
            "nikita.api.routes.portal_onboarding.run_agent_with_capture",
            new=run_capture_mock,
        ),
        patch(
            "nikita.api.routes.portal_onboarding.get_conversation_agent",
            return_value=agent,
        ),
        patch(
            "nikita.api.routes.portal_onboarding.IdempotencyStore",
            return_value=idem_store,
        ),
        patch(
            "nikita.api.routes.portal_onboarding.append_conversation_turn",
            new=AsyncMock(),
        ),
        patch(
            "nikita.db.repositories.user_repository.UserRepository",
            return_value=user_repo,
        ),
    ]


# ---------------------------------------------------------------------------
# Test 1 — 429 retries twice then succeeds (200 OK, normal envelope)
# ---------------------------------------------------------------------------


class TestModelHttpRetryThenSucceed:
    def test_429_retries_then_succeeds(self, caplog) -> None:
        """Two transient 429s, then a successful run = 200 normal envelope.

        Asserts:
          - 200 OK with non-fallback envelope (meta.source != "fallback")
          - run_agent_with_capture awaited exactly 3 times
          - 2 ``answer_agent_retry_attempt`` log records
          - 0 ``answer_agent_model_http_error`` records (final attempt OK)
          - 0 ``answer_agent_fallback_envelope`` records
        """
        run_capture = AsyncMock(
            side_effect=[
                ModelHTTPError(429, "claude-sonnet-4-5", body={"error": "rate_limited"}),
                ModelHTTPError(429, "claude-sonnet-4-5", body={"error": "rate_limited"}),
                _make_run_result(reply="Got it."),
            ]
        )

        app, _ = _make_app()
        with _no_op_sleep_patch():
            with caplog.at_level(logging.INFO, logger="nikita.api.routes.portal_onboarding"):
                stack_ctxs = _common_route_patches(run_capture_mock=run_capture)
                with stack_ctxs[0], stack_ctxs[1], stack_ctxs[2], stack_ctxs[3], stack_ctxs[4]:
                    client = TestClient(app)
                    response = client.post(
                        "/api/v1/onboarding/answer", json=_post_payload()
                    )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["meta"]["source"] != "fallback", (
            "Successful retry must NOT route through the fallback envelope. "
            f"Got meta={body['meta']}"
        )
        assert run_capture.await_count == 3, (
            f"Expected 3 attempts (2 retries + success); got {run_capture.await_count}"
        )

        retry_records = [
            r for r in caplog.records if r.message and "answer_agent_retry_attempt" in r.message
        ]
        err_records = [
            r for r in caplog.records if r.message and "answer_agent_model_http_error" in r.message
        ]
        fb_records = [
            r for r in caplog.records if r.message and "answer_agent_fallback_envelope" in r.message
        ]
        assert len(retry_records) == 2, (
            f"Expected 2 retry-attempt logs; got {len(retry_records)}"
        )
        assert len(err_records) == 0, (
            f"Expected 0 model_http_error logs (final attempt succeeded); got {len(err_records)}"
        )
        assert len(fb_records) == 0, (
            f"Expected 0 fallback envelope logs (no fallback fired); got {len(fb_records)}"
        )


# ---------------------------------------------------------------------------
# Test 2 — 500 (non-retryable) falls back without retry
# ---------------------------------------------------------------------------


class TestModelHttpNonRetryableFallback:
    def test_500_no_retry_falls_back(self, caplog) -> None:
        """500 is NOT in the retry set → 1 attempt, fallback envelope.

        Asserts:
          - 200 OK with fallback envelope (meta.source == "fallback")
          - meta.fallback_reason == "model_http_500"
          - run_agent_with_capture awaited exactly once (no retries)
          - 1 ``answer_agent_model_http_error`` log (status_code=500)
          - 1 ``answer_agent_fallback_envelope`` log
          - 0 ``answer_agent_retry_attempt`` logs
        """
        run_capture = AsyncMock(
            side_effect=ModelHTTPError(500, "claude-sonnet-4-5", body={"error": "internal"})
        )

        app, _ = _make_app()
        with _no_op_sleep_patch():
            with caplog.at_level(logging.INFO, logger="nikita.api.routes.portal_onboarding"):
                stack_ctxs = _common_route_patches(run_capture_mock=run_capture)
                with stack_ctxs[0], stack_ctxs[1], stack_ctxs[2], stack_ctxs[3], stack_ctxs[4]:
                    client = TestClient(app)
                    response = client.post(
                        "/api/v1/onboarding/answer", json=_post_payload()
                    )

        assert response.status_code == 200
        body = response.json()
        assert body["meta"]["source"] == "fallback"
        assert body["meta"]["fallback_reason"] == "model_http_500", (
            f"Expected fallback_reason='model_http_500'; got {body['meta']}"
        )
        assert run_capture.await_count == 1, (
            f"500 is non-retryable; expected 1 attempt got {run_capture.await_count}"
        )

        retry_records = [
            r for r in caplog.records if r.message and "answer_agent_retry_attempt" in r.message
        ]
        err_records = [
            r for r in caplog.records if r.message and "answer_agent_model_http_error" in r.message
        ]
        fb_records = [
            r for r in caplog.records if r.message and "answer_agent_fallback_envelope" in r.message
        ]
        assert len(retry_records) == 0, (
            f"Non-retryable status MUST NOT log retry attempts; got {len(retry_records)}"
        )
        assert len(err_records) == 1
        # Verify status_code carried into structured log via `extra=`
        assert getattr(err_records[0], "status_code", None) == 500, (
            "ModelHTTPError log MUST carry status_code in extra= for GH #556"
        )
        assert len(fb_records) == 1
        assert getattr(fb_records[0], "fallback_reason", None) == "model_http_500"


# ---------------------------------------------------------------------------
# Test 3 — 429 exhausts all 3 attempts → fallback
# ---------------------------------------------------------------------------


class TestModelHttpRetryExhausted:
    def test_429_exhausts_retries_falls_back(self, caplog) -> None:
        """All 3 attempts raise 429 → fallback envelope with retry logs.

        Asserts:
          - 200 OK with fallback envelope
          - meta.fallback_reason == "model_http_429"
          - run_agent_with_capture awaited exactly 3 times
          - 2 ``answer_agent_retry_attempt`` logs (between attempts 1→2 and 2→3)
          - 1 ``answer_agent_model_http_error`` log (final 429)
          - 1 ``answer_agent_fallback_envelope`` log
        """
        run_capture = AsyncMock(
            side_effect=[
                ModelHTTPError(429, "claude-sonnet-4-5", body={"error": "rate_limited"}),
                ModelHTTPError(429, "claude-sonnet-4-5", body={"error": "rate_limited"}),
                ModelHTTPError(429, "claude-sonnet-4-5", body={"error": "rate_limited"}),
            ]
        )

        app, _ = _make_app()
        with _no_op_sleep_patch():
            with caplog.at_level(logging.INFO, logger="nikita.api.routes.portal_onboarding"):
                stack_ctxs = _common_route_patches(run_capture_mock=run_capture)
                with stack_ctxs[0], stack_ctxs[1], stack_ctxs[2], stack_ctxs[3], stack_ctxs[4]:
                    client = TestClient(app)
                    response = client.post(
                        "/api/v1/onboarding/answer", json=_post_payload()
                    )

        assert response.status_code == 200
        body = response.json()
        assert body["meta"]["source"] == "fallback"
        assert body["meta"]["fallback_reason"] == "model_http_429"
        assert run_capture.await_count == 3, (
            f"Exhaust = 3 attempts; got {run_capture.await_count}"
        )

        retry_records = [
            r for r in caplog.records if r.message and "answer_agent_retry_attempt" in r.message
        ]
        err_records = [
            r for r in caplog.records if r.message and "answer_agent_model_http_error" in r.message
        ]
        fb_records = [
            r for r in caplog.records if r.message and "answer_agent_fallback_envelope" in r.message
        ]
        # 2 retry logs between attempts; 1 terminal model_http_error; 1 fallback
        assert len(retry_records) == 2
        assert len(err_records) == 1
        assert getattr(err_records[0], "status_code", None) == 429
        assert len(fb_records) == 1
        assert getattr(fb_records[0], "fallback_reason", None) == "model_http_429"


# ---------------------------------------------------------------------------
# Test 4 — Non-ModelHTTPError falls through to existing fallback arm
# ---------------------------------------------------------------------------


class TestNonModelHttpFallthrough:
    def test_value_error_falls_through_to_existing_arm(self, caplog) -> None:
        """ValueError from the helper must NOT trigger ModelHTTPError handling.

        Asserts:
          - 200 OK with fallback envelope (existing-arm semantics preserved)
          - run_agent_with_capture awaited exactly once (no retry)
          - 0 ``answer_agent_retry_attempt`` records
          - 0 ``answer_agent_model_http_error`` records
          - meta.fallback_reason matches the existing arm contract (NOT
            a ``model_http_*`` value); existing routes log
            ``ValueError`` as ``type(exc).__name__`` per L1610-1620.
        """
        run_capture = AsyncMock(side_effect=ValueError("synthetic non-HTTP failure"))

        app, _ = _make_app()
        with _no_op_sleep_patch():
            with caplog.at_level(logging.INFO, logger="nikita.api.routes.portal_onboarding"):
                stack_ctxs = _common_route_patches(run_capture_mock=run_capture)
                with stack_ctxs[0], stack_ctxs[1], stack_ctxs[2], stack_ctxs[3], stack_ctxs[4]:
                    client = TestClient(app)
                    response = client.post(
                        "/api/v1/onboarding/answer", json=_post_payload()
                    )

        assert response.status_code == 200
        body = response.json()
        assert body["meta"]["source"] == "fallback"
        # Existing arm logs `type(exc).__name__` as the fallback_reason.
        assert body["meta"]["fallback_reason"] == "ValueError", (
            f"Non-HTTP exception MUST go through existing arm; got {body['meta']}"
        )
        assert run_capture.await_count == 1
        retry_records = [
            r for r in caplog.records if r.message and "answer_agent_retry_attempt" in r.message
        ]
        http_err_records = [
            r for r in caplog.records if r.message and "answer_agent_model_http_error" in r.message
        ]
        assert len(retry_records) == 0
        assert len(http_err_records) == 0


# ---------------------------------------------------------------------------
# Test 5 — Tuning-constants regression guard (per .claude/rules/tuning-constants.md)
# ---------------------------------------------------------------------------


class TestTuningConstantsLocked:
    """Pin the retry tuning per GH #555. Drift requires an explicit edit."""

    def test_retry_status_codes_constant_locked(self) -> None:
        # GH #555: 429 (rate-limit) + 502/503/504 (gateway/service unavailable/
        # gateway-timeout) + 529 (Anthropic overload). Drift requires
        # editing this test AND the constant in lockstep.
        from nikita.api.routes.portal_onboarding import RETRY_STATUS_CODES

        assert RETRY_STATUS_CODES == frozenset({429, 502, 503, 504, 529}), (
            f"GH #555 retry set drifted; got {RETRY_STATUS_CODES}"
        )

    def test_retry_backoff_constant_locked(self) -> None:
        # GH #555: 3-attempt expo backoff with jitter. Worst-case 2.75 s
        # added latency on full exhaustion. Drift requires this test edit.
        from nikita.api.routes.portal_onboarding import RETRY_BACKOFF_MS

        assert RETRY_BACKOFF_MS == (250, 750, 1750), (
            f"GH #555 backoff schedule drifted; got {RETRY_BACKOFF_MS}"
        )
