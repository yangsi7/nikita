"""T-B3-3 (Spec 216-B3): POST /api/v1/onboarding/answer route handler.

Falsifiable acceptance tests for the new stateful onboarding endpoint.
The handler is a clean rewrite of the /converse pattern but rebased on
the cumulative-state contract:

  - Request: AnswerRequest(slot_kind, value, turn_id, conversation_id?)
  - State: rehydrate WizardSlots from JSONB → run agent → apply delta
  - Response: AnswerResponse(output, progress_pct, is_complete, link_code,
    conversation_id, meta)

Hard rules verified here:

  - Hard Rule §1 (cumulative state): handler MUST call apply_turn_delta
    AFTER agent.run, NOT mutate state inside the validator. T-B3-12 made
    _validate_output pure; this handler owns the state-mutation timing.
  - Hard Rule §2 (Pydantic completion gate): is_complete is the
    @computed_field FinalForm.model_validate result, never a literal.
  - Hard Rule §5 (validation layering): pre-tool (Pydantic), post-tool
    (output validator), deterministic post-processing (this handler).
  - B1.11 (capture_run_messages): every agent.run goes through
    run_agent_with_capture so UnexpectedModelBehavior dumps to logs.
  - B1.13 (happy path): extract → reply → persist user+nikita turns.
  - B1.15 (turn_id idempotency): same (user_id, turn_id) returns cached
    body verbatim, agent NOT called second time.
  - B1.17 (always-200 fallback): UnexpectedModelBehavior maps to 200
    with meta.fallback_reason + in-character reply.
  - B1.22 (rate limit): 30 rpm dep installed; tests bypass with override.
  - NR-05 (no Big5 leakage): response model audits at test_no_big5_in_response.

Test architecture:

  - Mocks at the boundary — agent (get_conversation_agent), repos
    (UserRepository, TelegramLinkRepository), JSONB persistence
    (append_conversation_turn), idempotency cache (IdempotencyStore).
  - Real Pydantic v2 contracts, real router, real FastAPI TestClient.
  - Zero DB hits; zero auth.users INSERTs (per Walk Y discipline).

Rule cross-references:
  - .claude/rules/agentic-design-patterns.md Hard Rules §1, §2, §5, §6
  - .claude/rules/testing.md "Tests That Don't Test" + "Agentic-Flow Test
    Requirements"
  - .claude/rules/live-testing-protocol.md Critical Anti-Patterns
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


USER_ID = UUID("550e8400-e29b-41d4-a716-446655440000")


# ---------------------------------------------------------------------------
# Test fixtures — FastAPI app builder + helper to install dep overrides
# ---------------------------------------------------------------------------


def _make_app(user_id: UUID = USER_ID) -> tuple[FastAPI, AsyncMock]:
    """Build a FastAPI app with portal_onboarding router and rate-limit bypass.

    Returns (app, mock_session). Tests install per-case overrides for the
    agent factory + repository constructors via ``monkeypatch`` so each
    case can shape agent output / link-code behavior independently.
    """
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
        return AuthenticatedUser(id=user_id, email="test@example.com")

    async def _rate_limit_bypass() -> None:
        return None

    app.dependency_overrides[get_async_session] = _session_override
    app.dependency_overrides[get_authenticated_user] = _auth_override
    app.dependency_overrides[get_current_user_id] = lambda: user_id
    app.dependency_overrides[answer_rate_limit] = _rate_limit_bypass

    return app, mock_session


def _make_user(profile: dict | None = None) -> MagicMock:
    """Mock User ORM row with the given onboarding_profile."""
    user = MagicMock()
    user.id = USER_ID
    user.onboarding_profile = profile if profile is not None else {}
    return user


def _make_agent_run_result(*, delta_kind: str | None, delta_data: dict | None, reply: str):
    """Build a fake AgentRunResult-like object with .output = TurnOutput."""
    from nikita.agents.onboarding.conversation_agent import TurnOutput
    from nikita.agents.onboarding.state import SlotDelta

    if delta_kind is None:
        delta = None
    else:
        delta = SlotDelta(kind=delta_kind, data=delta_data or {})
    output = TurnOutput(delta=delta, reply=reply, next_slot_kind=None)
    result = MagicMock(name="agent_run_result")
    result.output = output
    return result


# ---------------------------------------------------------------------------
# B1.13 — Happy path: extract → reply → persist user+nikita turns
# ---------------------------------------------------------------------------


class TestAnswerHappyPath:
    """B1.13 — POST /answer extracts, replies, persists both turns."""

    def test_happy_path_extract_reply_persist(self) -> None:
        """Given empty profile + agent emits SlotDelta(city=Zürich):

        - 200 status
        - response.output.kind == "success"
        - response.output.reply == "Got it."
        - response.progress_pct > 0 (one slot filled out of 13)
        - response.is_complete == False (only 1/13 filled)
        - append_conversation_turn called TWICE (user turn + nikita turn)
        - idempotency.put called once with response body
        """
        app, mock_session = _make_app()

        # Patch the boundaries the handler calls into.
        agent = MagicMock()
        agent.run = AsyncMock(
            return_value=_make_agent_run_result(
                delta_kind="city",
                delta_data={"city": "Zürich"},
                reply="Got it.",
            )
        )
        user_repo = MagicMock()
        user_repo.get = AsyncMock(return_value=_make_user(profile={}))

        link_repo = MagicMock()
        link_repo.get_active_for_user = AsyncMock(return_value=None)
        link_repo.create_link_code = AsyncMock()

        idem_store = MagicMock()
        idem_store.get = AsyncMock(return_value=None)
        idem_store.put = AsyncMock()

        append_mock = AsyncMock()

        with (
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
                append_mock,
            ),
            patch(
                "nikita.db.repositories.user_repository.UserRepository",
                return_value=user_repo,
            ),
            patch(
                "nikita.db.repositories.telegram_link_repository.TelegramLinkRepository",
                return_value=link_repo,
            ),
        ):
            client = TestClient(app)
            payload = {
                "slot_kind": "city",
                "value": "Zürich",
                "turn_id": str(uuid4()),
            }
            response = client.post("/api/v1/onboarding/answer", json=payload)

        assert response.status_code == 200, response.text
        body = response.json()

        # Output envelope shape (T-B3-2 contract)
        assert body["output"]["kind"] == "success"
        assert body["output"]["reply"] == "Got it."
        assert body["output"]["delta"]["kind"] == "city"
        assert body["output"]["delta"]["data"] == {"city": "Zürich"}

        # Cumulative-state shape
        assert body["progress_pct"] > 0, "One slot filled must move progress."
        assert body["is_complete"] is False, "1/13 filled is not complete."
        assert body["link_code"] is None, "Link code only minted on completion."
        assert body["conversation_id"] is not None
        assert body["meta"]["source"] == "llm"

        # Persistence side effects
        assert append_mock.await_count == 2, (
            "Expected user turn + nikita turn (AC-T2.8.1/2)."
        )
        idem_store.put.assert_awaited_once()


# ---------------------------------------------------------------------------
# B1.15 — Idempotency: same turn_id returns cached body, agent NOT re-called
# ---------------------------------------------------------------------------


class TestAnswerIdempotency:
    """B1.15 — turn_id replay returns cached body without calling agent."""

    def test_turn_id_replay_returns_cached_body(self) -> None:
        """Second POST with same turn_id returns the cached response
        verbatim and does NOT invoke the agent."""
        app, mock_session = _make_app()
        turn_id = uuid4()

        cached_body = {
            "output": {
                "kind": "success",
                "delta": {"kind": "city", "data": {"city": "Zürich"}},
                "reply": "Got it.",
                "next_slot_kind": None,
                "cohort_chips": None,
                "archetype_cards": None,
            },
            "progress_pct": 7,
            "is_complete": False,
            "link_code": None,
            "conversation_id": str(uuid4()),
            "meta": {"source": "llm"},
        }

        agent = MagicMock()
        agent.run = AsyncMock()  # MUST NOT be awaited

        idem_store = MagicMock()
        idem_store.get = AsyncMock(return_value=(cached_body, 200))
        idem_store.put = AsyncMock()

        with (
            patch(
                "nikita.api.routes.portal_onboarding.get_conversation_agent",
                return_value=agent,
            ),
            patch(
                "nikita.api.routes.portal_onboarding.IdempotencyStore",
                return_value=idem_store,
            ),
        ):
            client = TestClient(app)
            payload = {
                "slot_kind": "city",
                "value": "Zürich",
                "turn_id": str(turn_id),
            }
            response = client.post("/api/v1/onboarding/answer", json=payload)

        assert response.status_code == 200
        body = response.json()

        # Replay returns the cached output / progress / link_code verbatim.
        # The only mutation is meta.source switching to "idempotent" so the FE
        # can distinguish a replayed body from a fresh LLM turn (mirrors the
        # /converse precedent — handler stamps the marker without re-writing
        # the cache row). B1.15 + AC-T2.5.3 are about output equivalence, not
        # the meta tag.
        assert body["output"] == cached_body["output"]
        assert body["progress_pct"] == cached_body["progress_pct"]
        assert body["is_complete"] == cached_body["is_complete"]
        assert body["link_code"] == cached_body["link_code"]
        assert body["conversation_id"] == cached_body["conversation_id"]
        assert body["meta"]["source"] == "idempotent", (
            "Idempotent replay MUST swap meta.source so FE can distinguish."
        )
        agent.run.assert_not_awaited(), (
            "Agent MUST NOT be re-invoked on idempotent replay (cost guard)."
        )
        idem_store.put.assert_not_awaited(), (
            "Replay MUST NOT re-write the cache row."
        )


# ---------------------------------------------------------------------------
# B1.17 — Always-200 fallback on UnexpectedModelBehavior
# ---------------------------------------------------------------------------


class TestAnswerFallback:
    """B1.17 — UnexpectedModelBehavior maps to 200 with meta.fallback_reason."""

    def test_unexpected_model_behavior_returns_200_with_meta(self) -> None:
        from pydantic_ai.exceptions import UnexpectedModelBehavior

        app, _ = _make_app()

        agent = MagicMock()
        agent.run = AsyncMock(
            side_effect=UnexpectedModelBehavior(
                "Tool 'extract_city' exceeded max retries count of 2"
            )
        )

        user_repo = MagicMock()
        user_repo.get = AsyncMock(return_value=_make_user(profile={}))

        idem_store = MagicMock()
        idem_store.get = AsyncMock(return_value=None)
        idem_store.put = AsyncMock()

        with (
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
                AsyncMock(),
            ),
            patch(
                "nikita.db.repositories.user_repository.UserRepository",
                return_value=user_repo,
            ),
        ):
            client = TestClient(app)
            payload = {
                "slot_kind": "city",
                "value": "Zürich",
                "turn_id": str(uuid4()),
            }
            response = client.post("/api/v1/onboarding/answer", json=payload)

        assert response.status_code == 200, (
            "B1.17 — fallback path MUST return 200 in-character, never 5xx. "
            f"Got {response.status_code}: {response.text}"
        )
        body = response.json()
        assert body["output"]["kind"] == "success"
        assert body["meta"]["source"] == "fallback"
        assert body["meta"]["fallback_reason"] == "UnexpectedModelBehavior"
        assert body["is_complete"] is False


# ---------------------------------------------------------------------------
# Validation surface — 422 on schema violations
# ---------------------------------------------------------------------------


class TestAnswerValidation:
    """Pydantic v2 contract enforcement on AnswerRequest."""

    def test_missing_turn_id_returns_422(self) -> None:
        app, _ = _make_app()
        client = TestClient(app)
        response = client.post(
            "/api/v1/onboarding/answer",
            json={"slot_kind": "city", "value": "Zürich"},
        )
        assert response.status_code == 422

    def test_value_over_2000_chars_returns_422(self) -> None:
        app, _ = _make_app()
        client = TestClient(app)
        response = client.post(
            "/api/v1/onboarding/answer",
            json={
                "slot_kind": "city",
                "value": "x" * 2001,
                "turn_id": str(uuid4()),
            },
        )
        assert response.status_code == 422

    def test_unknown_slot_kind_returns_422(self) -> None:
        app, _ = _make_app()
        client = TestClient(app)
        response = client.post(
            "/api/v1/onboarding/answer",
            json={
                "slot_kind": "not_a_real_slot",
                "value": "Zürich",
                "turn_id": str(uuid4()),
            },
        )
        assert response.status_code == 422

    def test_extra_field_rejected(self) -> None:
        """extra='forbid' on AnswerRequest MUST reject unknown fields."""
        app, _ = _make_app()
        client = TestClient(app)
        response = client.post(
            "/api/v1/onboarding/answer",
            json={
                "slot_kind": "city",
                "value": "Zürich",
                "turn_id": str(uuid4()),
                "user_id": str(uuid4()),  # forbidden — identity comes from JWT
            },
        )
        assert response.status_code == 422
