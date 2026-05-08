"""AC-9.1, AC-9.2, AC-9.3 — /answer route emission dispatch (217-3A.3).

One test per emission kind asserts the route returns the matching
discriminated-union envelope. Plus an OpenAPI ``oneOf`` shape assertion
verifying all 6 ``kind`` discriminators are advertised.

Hard rules verified here:
  - AC-9.1: dispatch on isinstance(emission, ReactionOnly | FollowUpQuestion |
    TurnFailure) → ReactionResponse / FollowUpResponse / TurnFailureResponse.
  - AC-9.1bis: AnswerResponse is a 6-branch discriminated union; OpenAPI
    emits a ``oneOf`` schema with all 6 ``kind`` literal values.
  - AC-9.2: completion gate is ``FinalForm.model_validate(state.slots_dict)``
    UNCHANGED — never a hardcoded literal.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

USER_ID = UUID("550e8400-e29b-41d4-a716-446655440000")


def _make_app(user_id: UUID = USER_ID) -> tuple[FastAPI, AsyncMock]:
    """Build a FastAPI app with portal_onboarding router + bypassed auth/rate-limit."""
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

    app.dependency_overrides[get_async_session] = _session_override
    app.dependency_overrides[get_authenticated_user] = _auth_override
    app.dependency_overrides[get_current_user_id] = lambda: user_id
    app.dependency_overrides[answer_rate_limit] = lambda: None
    return app, mock_session


def _make_user(profile: dict | None = None) -> MagicMock:
    user = MagicMock()
    user.id = USER_ID
    user.onboarding_profile = profile if profile is not None else {}
    user.big5_vector = {}
    return user


class _MockAgentResult:
    def __init__(self, output):
        self.output = output


def _patches(emission, *, profile=None):
    """Return context-manager-stack equivalents for the common mocks."""
    user_repo = MagicMock()
    user_repo.get = AsyncMock(return_value=_make_user(profile=profile))

    idempotency_get = AsyncMock(return_value=None)
    idempotency_put = AsyncMock(return_value=None)

    agent_mock = MagicMock()
    agent_mock.run = AsyncMock(return_value=_MockAgentResult(emission))

    return user_repo, idempotency_get, idempotency_put, agent_mock


def _post_answer(app: FastAPI, *, slot_kind: str = "city", value="Zürich"):
    client = TestClient(app)
    return client.post(
        "/api/v1/onboarding/answer",
        json={
            "slot_kind": slot_kind,
            "value": value,
            "turn_id": str(uuid4()),
        },
    )


class TestEmissionDispatch:
    """AC-9.1 — one test per emission kind."""

    def test_reaction_only_with_valid_delta_advances_with_reaction(self) -> None:
        """GH #568 fix: ReactionOnly + valid deterministic delta → wire
        ``{kind: "deterministic_advance", reaction_text, progress_pct, ...}``.

        Walk B3v2/B4 surfaced that the legacy ReactionOnly handler blocked
        deterministic-card advance — wizard stuck at the name turn. The fix
        re-routes ReactionOnly + valid delta through the deterministic_advance
        branch, attaching reaction_text as narrator color over the flow.
        Per `.claude/rules/agentic-design-patterns.md` Hard Rule §1
        (cumulative state advances based on validated input, not LLM
        judgment).
        """
        from nikita.agents.onboarding.converse_contracts import ReactionOnly

        emission = ReactionOnly(reaction_text="okay, noted.")
        app, _ = _make_app()
        user_repo, idem_get, idem_put, agent_mock = _patches(emission)
        persist_mock = AsyncMock(return_value=None)
        with (
            patch(
                "nikita.db.repositories.user_repository.UserRepository",
                return_value=user_repo,
            ),
            patch(
                "nikita.onboarding.idempotency.IdempotencyStore.get",
                idem_get,
            ),
            patch(
                "nikita.onboarding.idempotency.IdempotencyStore.put",
                idem_put,
            ),
            patch(
                "nikita.api.routes.portal_onboarding.get_emission_agent",
                return_value=agent_mock,
            ),
            patch(
                "nikita.api.routes.portal_onboarding.clear_pending_followup",
                AsyncMock(return_value=None),
            ),
            patch(
                "nikita.api.routes.portal_onboarding.append_conversation_turn",
                AsyncMock(return_value=None),
            ),
            patch(
                "nikita.api.routes.portal_onboarding._persist_state_to_profile",
                persist_mock,
            ),
        ):
            response = _post_answer(app)
        assert response.status_code == 200, response.text
        body = response.json()
        # GH #568 fix: ReactionOnly with valid delta now routes through
        # deterministic_advance branch (was: reaction; slot NOT advanced).
        assert body["kind"] == "deterministic_advance"
        assert body["reaction_text"] == "okay, noted."
        # progress_pct must reflect the advance (city slot filled).
        assert body["progress_pct"] > 0
        # State persistence MUST be invoked (advances cumulative state).
        persist_mock.assert_awaited_once()

    def test_followup_question_returns_followup_response(self) -> None:
        """Agent emits FollowUpQuestion → ``{kind: "followup", question_text, target_slot}``;
        sidecar persisted."""
        from nikita.agents.onboarding.converse_contracts import FollowUpQuestion

        emission = FollowUpQuestion(
            question_text="which city specifically?",
            target_slot="city",
        )
        app, _ = _make_app()
        user_repo, idem_get, idem_put, agent_mock = _patches(emission)
        with (
            patch(
                "nikita.db.repositories.user_repository.UserRepository",
                return_value=user_repo,
            ),
            patch(
                "nikita.onboarding.idempotency.IdempotencyStore.get",
                idem_get,
            ),
            patch(
                "nikita.onboarding.idempotency.IdempotencyStore.put",
                idem_put,
            ),
            patch(
                "nikita.api.routes.portal_onboarding.get_emission_agent",
                return_value=agent_mock,
            ),
            patch(
                "nikita.api.routes.portal_onboarding.persist_pending_followup",
                AsyncMock(return_value=None),
            ),
            patch(
                "nikita.api.routes.portal_onboarding.append_conversation_turn",
                AsyncMock(return_value=None),
            ),
            patch(
                "nikita.api.routes.portal_onboarding._persist_state_to_profile",
                AsyncMock(return_value=None),
            ),
        ):
            response = _post_answer(app)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["kind"] == "followup"
        assert body["question_text"] == "which city specifically?"
        assert body["target_slot"] == "city"

    def test_turn_failure_returns_turn_failure_response(self) -> None:
        """Agent emits TurnFailure → ``{kind: "turn_failure", explanation}``."""
        from nikita.agents.onboarding.converse_contracts import (
            TurnFailure as EmissionTurnFailure,
        )

        emission = EmissionTurnFailure(explanation="eighteen and up only.")
        app, _ = _make_app()
        user_repo, idem_get, idem_put, agent_mock = _patches(emission)
        with (
            patch(
                "nikita.db.repositories.user_repository.UserRepository",
                return_value=user_repo,
            ),
            patch(
                "nikita.onboarding.idempotency.IdempotencyStore.get",
                idem_get,
            ),
            patch(
                "nikita.onboarding.idempotency.IdempotencyStore.put",
                idem_put,
            ),
            patch(
                "nikita.api.routes.portal_onboarding.get_emission_agent",
                return_value=agent_mock,
            ),
            patch(
                "nikita.api.routes.portal_onboarding.clear_pending_followup",
                AsyncMock(return_value=None),
            ),
            patch(
                "nikita.api.routes.portal_onboarding.append_conversation_turn",
                AsyncMock(return_value=None),
            ),
        ):
            response = _post_answer(app)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["kind"] == "turn_failure"
        assert body["explanation"] == "eighteen and up only."

    def test_agent_exception_returns_turn_failure_response(self) -> None:
        """UnexpectedModelBehavior in agent.run is caught; route emits
        TurnFailureResponse so the wizard surface stays usable (always-200)."""
        from pydantic_ai.exceptions import UnexpectedModelBehavior

        app, _ = _make_app()
        user_repo, idem_get, idem_put, agent_mock = _patches(emission=None)
        agent_mock.run = AsyncMock(
            side_effect=UnexpectedModelBehavior("retries exhausted")
        )

        with (
            patch(
                "nikita.db.repositories.user_repository.UserRepository",
                return_value=user_repo,
            ),
            patch(
                "nikita.onboarding.idempotency.IdempotencyStore.get",
                idem_get,
            ),
            patch(
                "nikita.onboarding.idempotency.IdempotencyStore.put",
                idem_put,
            ),
            patch(
                "nikita.api.routes.portal_onboarding.get_emission_agent",
                return_value=agent_mock,
            ),
            patch(
                "nikita.api.routes.portal_onboarding.clear_pending_followup",
                AsyncMock(return_value=None),
            ),
            patch(
                "nikita.api.routes.portal_onboarding.append_conversation_turn",
                AsyncMock(return_value=None),
            ),
        ):
            response = _post_answer(app)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["kind"] == "turn_failure"
        # Falls back to a route-supplied explanation when agent raises.
        assert isinstance(body["explanation"], str)
        assert len(body["explanation"]) > 0


class TestCompletionRouteDispatch:
    """GH #564 — end-to-end completion-route-dispatch coverage.

    The 6th branch of AnswerResponse (`kind="completion"`) was previously
    only exercised at the WizardSlots-level (`test_completion_gate.py`) and
    via the OpenAPI shape test. This class POSTs to `/answer` with a
    near-complete WizardSlots fixture so applying the final slot tips
    `state.is_complete` and the route emits CompletionResponse.

    AMENDED 2026-05-09 (GH #568 fix): the test also asserts
    `reaction_text` is preserved on the terminal turn when the agent
    emits ReactionOnly.
    """

    def _near_complete_slots(self):
        """Return a WizardSlots fixture with 12 of 13 slots filled (phone empty)."""
        from nikita.agents.onboarding.state import SlotDelta, WizardSlots

        slots = WizardSlots()
        fixture = [
            ("display_name", {"display_name": "Sam"}),
            ("age", {"age": 28}),
            ("occupation", {"occupation": "designer"}),
            ("city", {"city": "Berlin"}),
            ("darkness_level", {"darkness_level": 3}),
            ("primary_hobbies", {"primary_hobbies": ["reading", "running"]}),
            ("saturday_morning", {"saturday_morning": "long walk"}),
            ("geek_out_on", {"geek_out_on": "keyboards"}),
            ("together_we_could", {"together_we_could": "drive somewhere"}),
            ("same_weird_if", {"same_weird_if": "same book twice"}),
            ("voice_tone_pref", {"voice_tone_pref": "text"}),
            ("backstory_pick", {
                "backstory_pick": {
                    "chosen_option_id": "abc123def456",
                    "cache_key": "berlin|techno|3",
                }
            }),
        ]
        for kind, data in fixture:
            slots = slots.apply(SlotDelta(kind=kind, data=data))
        return slots

    def test_completion_emitted_when_state_complete(self) -> None:
        """ReactionOnly + final-slot delta → state.is_complete → CompletionResponse.

        Submits slot=phone with valid E.164; with all other slots pre-filled,
        applying the delta tips `is_complete=True`. Per GH #568 fix, the
        ReactionOnly emission is preserved on `reaction_text`.
        """
        from nikita.agents.onboarding.converse_contracts import ReactionOnly

        emission = ReactionOnly(reaction_text="you're cleared.")
        app, _ = _make_app()
        user_repo, idem_get, idem_put, agent_mock = _patches(emission)

        near_complete = self._near_complete_slots()

        link_repo_mock = MagicMock()
        link_repo_mock.get_active_for_user = AsyncMock(return_value=None)
        minted = MagicMock()
        minted.code = "LINK1234"
        link_repo_mock.create_link_code = AsyncMock(return_value=minted)

        with (
            patch(
                "nikita.db.repositories.user_repository.UserRepository",
                return_value=user_repo,
            ),
            patch(
                "nikita.onboarding.idempotency.IdempotencyStore.get",
                idem_get,
            ),
            patch(
                "nikita.onboarding.idempotency.IdempotencyStore.put",
                idem_put,
            ),
            patch(
                "nikita.api.routes.portal_onboarding.get_emission_agent",
                return_value=agent_mock,
            ),
            patch(
                "nikita.api.routes.portal_onboarding.build_state_from_conversation",
                return_value=near_complete,
            ),
            patch(
                "nikita.api.routes.portal_onboarding.clear_pending_followup",
                AsyncMock(return_value=None),
            ),
            patch(
                "nikita.api.routes.portal_onboarding.append_conversation_turn",
                AsyncMock(return_value=None),
            ),
            patch(
                "nikita.api.routes.portal_onboarding._persist_state_to_profile",
                AsyncMock(return_value=None),
            ),
            patch(
                "nikita.db.repositories.telegram_link_repository.TelegramLinkRepository",
                return_value=link_repo_mock,
            ),
        ):
            response = _post_answer(app, slot_kind="phone", value="+14155552671")
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["kind"] == "completion", body
        assert body["is_complete"] is True
        assert body["progress_pct"] == 100
        assert body["link_code"] == "LINK1234"
        # GH #568 fix: terminal-turn reaction is preserved.
        assert body["reaction_text"] == "you're cleared."
        # Sanity check: conversation_id is a non-empty string (UUID form).
        assert isinstance(body["conversation_id"], str) and body["conversation_id"]


class TestOpenAPIDiscriminatedUnion:
    """AC-9.1bis — OpenAPI advertises a 6-branch ``oneOf`` for /answer 200."""

    def test_openapi_oneof_includes_all_six_kinds(self) -> None:
        """GET /openapi.json — the /answer 200 schema is a discriminated union
        with 6 ``kind`` literal values: reaction, followup, field_error,
        turn_failure, deterministic_advance, completion."""
        app, _ = _make_app()
        client = TestClient(app)
        spec = client.get("/openapi.json").json()
        # Walk the spec to find /answer 200 schema.
        post_op = spec["paths"]["/api/v1/onboarding/answer"]["post"]
        ok_content = post_op["responses"]["200"]["content"]["application/json"]
        # Resolve $ref into components.schemas.
        ref = ok_content["schema"].get("$ref") or ok_content["schema"].get("oneOf")
        assert ref is not None, "Expected a $ref or oneOf at the /answer 200 schema"

        # Collect all schema names referenced in the union — either inline
        # ``oneOf`` (FastAPI 0.x style) or one alias resolved via $ref.
        all_kinds: set[str] = set()
        defs = spec.get("components", {}).get("schemas", {})

        def _gather(node):
            if isinstance(node, dict):
                if "oneOf" in node:
                    for sub in node["oneOf"]:
                        _gather(sub)
                elif "$ref" in node:
                    name = node["$ref"].split("/")[-1]
                    sub_schema = defs.get(name, {})
                    _gather(sub_schema)
                else:
                    props = node.get("properties", {})
                    kind_def = props.get("kind", {})
                    const = kind_def.get("const")
                    if const:
                        all_kinds.add(const)
                    enum = kind_def.get("enum")
                    if enum:
                        all_kinds.update(enum)

        _gather(ok_content["schema"])
        expected = {
            "reaction",
            "followup",
            "field_error",
            "turn_failure",
            "deterministic_advance",
            "completion",
        }
        assert expected.issubset(all_kinds), (
            f"Expected all 6 discriminator kinds in OpenAPI, "
            f"missing: {expected - all_kinds}; got: {all_kinds}"
        )


class TestRetrySemantics:
    """217-2c (PR #558) retry coverage — re-wired for the emission agent
    in 217-3A.3. Restores the 6 retry surfaces that lived in the deleted
    ``test_portal_onboarding_answer_failure.py``.
    """

    def test_retry_status_codes_tuning_lock(self) -> None:
        """``.claude/rules/tuning-constants.md`` regression guard.

        The retry-eligible HTTP status set is a tuning constant — silent
        drift from the GH #555 baseline is the anti-pattern. Pin the
        exact frozenset so any change requires an intentional edit + PR.
        """
        from nikita.api.routes.portal_onboarding import RETRY_STATUS_CODES

        assert RETRY_STATUS_CODES == frozenset({429, 502, 503, 504, 529})

    def test_retry_backoff_ms_tuning_lock(self) -> None:
        """Per-attempt base delay schedule is a tuning constant; pin it."""
        from nikita.api.routes.portal_onboarding import RETRY_BACKOFF_MS

        assert RETRY_BACKOFF_MS == (250, 750, 1750)

    def test_retry_429_then_success(self) -> None:
        """ModelHTTPError 429 on attempt 1 → backoff → attempt 2 succeeds.
        ``run_agent_with_capture`` called twice; happy-path envelope returned.

        AMENDED 2026-05-09 (GH #568 fix): ReactionOnly with valid delta now
        routes through deterministic_advance branch (was: reaction).
        """
        from pydantic_ai.exceptions import ModelHTTPError

        from nikita.agents.onboarding.converse_contracts import ReactionOnly

        emission = ReactionOnly(reaction_text="okay, noted.")
        app, _ = _make_app()
        user_repo, idem_get, idem_put, _ = _patches(emission)

        first_call_done = {"v": False}

        async def _fake_run(*args, **kwargs):
            if not first_call_done["v"]:
                first_call_done["v"] = True
                raise ModelHTTPError(
                    status_code=429, model_name="test", body="overloaded"
                )
            return _MockAgentResult(emission)

        with (
            patch(
                "nikita.db.repositories.user_repository.UserRepository",
                return_value=user_repo,
            ),
            patch(
                "nikita.onboarding.idempotency.IdempotencyStore.get",
                idem_get,
            ),
            patch(
                "nikita.onboarding.idempotency.IdempotencyStore.put",
                idem_put,
            ),
            patch(
                "nikita.api.routes.portal_onboarding.run_agent_with_capture",
                side_effect=_fake_run,
            ) as mock_run,
            patch(
                "nikita.api.routes.portal_onboarding.asyncio.sleep",
                AsyncMock(return_value=None),
            ),
            patch(
                "nikita.api.routes.portal_onboarding.clear_pending_followup",
                AsyncMock(return_value=None),
            ),
            patch(
                "nikita.api.routes.portal_onboarding.append_conversation_turn",
                AsyncMock(return_value=None),
            ),
            patch(
                "nikita.api.routes.portal_onboarding._persist_state_to_profile",
                AsyncMock(return_value=None),
            ),
        ):
            response = _post_answer(app)
        assert response.status_code == 200, response.text
        body = response.json()
        # GH #568 fix: ReactionOnly + valid delta → deterministic_advance.
        assert body["kind"] == "deterministic_advance"
        assert body["reaction_text"] == "okay, noted."
        assert mock_run.call_count == 2, (
            f"Expected 2 agent calls (1 retry), got {mock_run.call_count}"
        )

    def test_retry_503_exhausted_emits_turn_failure(self) -> None:
        """ModelHTTPError 503 on all 3 attempts → fallback TurnFailureResponse."""
        from pydantic_ai.exceptions import ModelHTTPError

        app, _ = _make_app()
        user_repo, idem_get, idem_put, _ = _patches(emission=None)

        async def _always_503(*args, **kwargs):
            raise ModelHTTPError(
                status_code=503, model_name="test", body="unavailable"
            )

        with (
            patch(
                "nikita.db.repositories.user_repository.UserRepository",
                return_value=user_repo,
            ),
            patch(
                "nikita.onboarding.idempotency.IdempotencyStore.get",
                idem_get,
            ),
            patch(
                "nikita.onboarding.idempotency.IdempotencyStore.put",
                idem_put,
            ),
            patch(
                "nikita.api.routes.portal_onboarding.run_agent_with_capture",
                side_effect=_always_503,
            ) as mock_run,
            patch(
                "nikita.api.routes.portal_onboarding.asyncio.sleep",
                AsyncMock(return_value=None),
            ),
            patch(
                "nikita.api.routes.portal_onboarding.clear_pending_followup",
                AsyncMock(return_value=None),
            ),
            patch(
                "nikita.api.routes.portal_onboarding.append_conversation_turn",
                AsyncMock(return_value=None),
            ),
        ):
            response = _post_answer(app)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["kind"] == "turn_failure"
        assert isinstance(body["explanation"], str) and body["explanation"]
        assert mock_run.call_count == 3, (
            f"Expected 3 attempts (full exhaustion), got {mock_run.call_count}"
        )

    def test_no_retry_on_500_immediate_fallback(self) -> None:
        """ModelHTTPError 500 NOT in RETRY_STATUS_CODES → no retry, immediate
        fallback to TurnFailureResponse on first attempt."""
        from pydantic_ai.exceptions import ModelHTTPError

        app, _ = _make_app()
        user_repo, idem_get, idem_put, _ = _patches(emission=None)

        async def _raise_500(*args, **kwargs):
            raise ModelHTTPError(
                status_code=500, model_name="test", body="internal"
            )

        with (
            patch(
                "nikita.db.repositories.user_repository.UserRepository",
                return_value=user_repo,
            ),
            patch(
                "nikita.onboarding.idempotency.IdempotencyStore.get",
                idem_get,
            ),
            patch(
                "nikita.onboarding.idempotency.IdempotencyStore.put",
                idem_put,
            ),
            patch(
                "nikita.api.routes.portal_onboarding.run_agent_with_capture",
                side_effect=_raise_500,
            ) as mock_run,
            patch(
                "nikita.api.routes.portal_onboarding.asyncio.sleep",
                AsyncMock(return_value=None),
            ),
            patch(
                "nikita.api.routes.portal_onboarding.clear_pending_followup",
                AsyncMock(return_value=None),
            ),
            patch(
                "nikita.api.routes.portal_onboarding.append_conversation_turn",
                AsyncMock(return_value=None),
            ),
        ):
            response = _post_answer(app)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["kind"] == "turn_failure"
        assert mock_run.call_count == 1, (
            f"500 must NOT retry; got {mock_run.call_count} attempts"
        )

    def test_retry_logs_emit_structured_events(self, caplog) -> None:
        """Pin the structured-log event names emitted on the retry boundary
        so observability cannot drift silently."""
        import logging

        from pydantic_ai.exceptions import ModelHTTPError

        app, _ = _make_app()
        user_repo, idem_get, idem_put, _ = _patches(emission=None)

        async def _always_429(*args, **kwargs):
            raise ModelHTTPError(
                status_code=429, model_name="test", body="rate"
            )

        with (
            caplog.at_level(logging.INFO),
            patch(
                "nikita.db.repositories.user_repository.UserRepository",
                return_value=user_repo,
            ),
            patch(
                "nikita.onboarding.idempotency.IdempotencyStore.get",
                idem_get,
            ),
            patch(
                "nikita.onboarding.idempotency.IdempotencyStore.put",
                idem_put,
            ),
            patch(
                "nikita.api.routes.portal_onboarding.run_agent_with_capture",
                side_effect=_always_429,
            ),
            patch(
                "nikita.api.routes.portal_onboarding.asyncio.sleep",
                AsyncMock(return_value=None),
            ),
            patch(
                "nikita.api.routes.portal_onboarding.clear_pending_followup",
                AsyncMock(return_value=None),
            ),
            patch(
                "nikita.api.routes.portal_onboarding.append_conversation_turn",
                AsyncMock(return_value=None),
            ),
        ):
            response = _post_answer(app)
        assert response.status_code == 200
        assert response.json()["kind"] == "turn_failure"
        events = [r.message for r in caplog.records]
        assert any("answer_agent_retry_attempt" in m for m in events), (
            f"Expected ``answer_agent_retry_attempt`` log; got: {events}"
        )
        assert any("answer_agent_model_http_error" in m for m in events), (
            f"Expected ``answer_agent_model_http_error`` log; got: {events}"
        )


class TestCompletionGateUnchanged:
    """AC-9.2 — completion gate is FinalForm.model_validate, never literal."""

    def test_progress_pct_is_computed_field(self) -> None:
        """WizardSlots.progress_pct is a @computed_field of cumulative state.

        Asserts the progress_pct value DERIVES from the slot count, not a
        per-turn snapshot — Walk V regression guard.
        """
        from nikita.agents.onboarding.state import SlotDelta, WizardSlots

        s = WizardSlots()
        assert s.progress_pct == 0
        s = s.apply(SlotDelta(kind="city", data={"city": "Zürich"}))
        assert s.progress_pct > 0
        s = s.apply(SlotDelta(kind="age", data={"age": 25}))
        assert s.progress_pct > 7  # at least 2 slots filled

    def test_is_complete_uses_finalform_model_validate(self) -> None:
        """is_complete evaluates FinalForm.model_validate(slots_dict);
        empty state → False, never a hardcoded literal."""
        from nikita.agents.onboarding.state import WizardSlots

        empty = WizardSlots()
        assert empty.is_complete is False
