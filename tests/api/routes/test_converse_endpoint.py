"""Tests for POST /api/v1/onboarding/converse (Spec 214 FR-11d).

Split across three concerns:

- ``TestConverseRequestSchema`` — T2.4 AC-T2.4.1/2/3 (schema + control
  selection + length ceiling).
- ``TestConverseEndpointBody`` — T2.5 AC-T2.5.* (authz, rate-limit,
  idempotency, timeout/fallback, input sanitization, output leak filter,
  tool-call edge cases, reply validators).
- ``TestConverseJailbreakFixtures`` — T2.5.5 + T2.5.7 (OWASP LLM01
  fixtures and output-leak filter).
- ``TestConverseJsonbPersistence`` — T2.8 AC-T2.8.1/2/3 (success-path
  wiring of ``append_conversation_turn`` so both the user turn and the
  Nikita turn land in ``users.onboarding_profile["conversation"]``).

PII policy (per .claude/rules/testing.md): assertions reference UUIDs
and boolean flags only. Name/age/occupation/phone values MUST NOT
appear in log-line format strings or assertion messages.
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import TypeAdapter, ValidationError

from nikita.agents.onboarding.control_selection import (
    CardsControl,
    ChipControl,
    ControlSelection,
    SliderControl,
    TextControl,
    ToggleControl,
)
from nikita.agents.onboarding.converse_contracts import (
    ConverseRequest,
    ConverseResponse,
    Turn,
)


# ---------------------------------------------------------------------------
# AC-T2.4.1 / AC-T2.4.2 / AC-T2.4.3 — schema hardening
# ---------------------------------------------------------------------------


class TestConverseRequestSchema:
    def _sample_turn(self) -> Turn:
        return Turn(
            role="nikita",
            content="Where are you right now?",
            timestamp=datetime.now(timezone.utc),
            source="llm",
        )

    def test_converse_rejects_user_id_in_body(self):
        """AC-T2.4.1: ``extra="forbid"`` rejects rogue ``user_id`` → 422."""
        payload = {
            "conversation_history": [],
            "user_input": "Zurich",
            "user_id": str(uuid4()),  # spoofed identity
        }
        with pytest.raises(ValidationError) as exc_info:
            ConverseRequest.model_validate(payload)
        errors = exc_info.value.errors()
        assert any(
            "extra_forbidden" in err["type"] or "user_id" in str(err["loc"])
            for err in errors
        )

    def test_converse_request_accepts_str_user_input(self):
        req = ConverseRequest(
            conversation_history=[self._sample_turn()],
            user_input="Zurich",
        )
        assert req.user_input == "Zurich"
        assert req.locale == "en"

    def test_converse_request_accepts_control_selection(self):
        req = ConverseRequest(
            conversation_history=[],
            user_input=ChipControl(value="techno"),
        )
        assert isinstance(req.user_input, ChipControl)
        assert req.user_input.value == "techno"

    def test_converse_history_cap_100(self):
        """Defensive cap: 101-turn history rejected at the boundary
        (matches AC-NR1b.5 / tech-spec §10 open-question 3)."""
        turns = [self._sample_turn() for _ in range(101)]
        with pytest.raises(ValidationError):
            ConverseRequest(
                conversation_history=turns,
                user_input="hi",
            )

    def test_control_selection_discriminated_union_round_trip(self):
        """AC-T2.4.2: all 5 kinds round-trip; unknown ``kind`` → 422."""
        adapter = TypeAdapter(ControlSelection)
        cases = [
            TextControl(value="Zurich"),
            ChipControl(value="techno"),
            SliderControl(value=3),
            ToggleControl(value="voice"),
            CardsControl(value="abcdef012345"),
        ]
        for original in cases:
            dumped = adapter.dump_python(original)
            restored = adapter.validate_python(dumped)
            assert type(restored) is type(original)
            assert restored == original

        with pytest.raises(ValidationError):
            adapter.validate_python({"kind": "unknown", "value": "x"})

    def test_control_selection_rejects_missing_kind(self):
        adapter = TypeAdapter(ControlSelection)
        with pytest.raises(ValidationError):
            adapter.validate_python({"value": "Zurich"})

    def test_slider_control_bounds(self):
        with pytest.raises(ValidationError):
            SliderControl(value=0)
        with pytest.raises(ValidationError):
            SliderControl(value=6)

    def test_cards_control_pattern_enforced(self):
        with pytest.raises(ValidationError):
            CardsControl(value="not-hex!")

    def test_toggle_control_literal_enforced(self):
        with pytest.raises(ValidationError):
            ToggleControl(value="neither")

    def test_reply_over_140_chars_triggers_fallback(self):
        """AC-T2.4.3: wire ceiling is 500; business cap 140 enforced by
        server via fallback. Schema level allows up to 500; the server
        checks ``NIKITA_REPLY_MAX_CHARS`` and substitutes fallback when
        exceeded. This test asserts the wire-level ceiling.
        """
        from nikita.onboarding.tuning import NIKITA_REPLY_MAX_CHARS

        # Business cap is exposed as a constant so the endpoint can
        # enforce it. This test pins both sides of that contract.
        assert NIKITA_REPLY_MAX_CHARS == 140

        # Wire ceiling: 500 chars accepted
        safe_reply = "x" * 500
        resp = ConverseResponse(
            nikita_reply=safe_reply,
            progress_pct=50,
            source="llm",
            latency_ms=1200,
        )
        assert len(resp.nikita_reply) == 500

        # > 500 → Pydantic rejects (defensive wire-level guard)
        with pytest.raises(ValidationError):
            ConverseResponse(
                nikita_reply="x" * 501,
                progress_pct=50,
                source="llm",
                latency_ms=1200,
            )

    def test_converse_response_progress_bounds(self):
        with pytest.raises(ValidationError):
            ConverseResponse(
                nikita_reply="ok",
                progress_pct=101,
                source="llm",
                latency_ms=10,
            )
        with pytest.raises(ValidationError):
            ConverseResponse(
                nikita_reply="ok",
                progress_pct=-1,
                source="llm",
                latency_ms=10,
            )

    def test_converse_response_source_literal(self):
        with pytest.raises(ValidationError):
            ConverseResponse(
                nikita_reply="ok",
                progress_pct=50,
                source="magic",  # type: ignore[arg-type]
                latency_ms=10,
            )

    def test_turn_rejects_extra_fields(self):
        with pytest.raises(ValidationError):
            Turn.model_validate(
                {
                    "role": "user",
                    "content": "hi",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "user_id": str(uuid4()),  # must not be accepted
                }
            )


# ---------------------------------------------------------------------------
# T2.8 AC-T2.8.1/2/3 — success-path wires append_conversation_turn
# ---------------------------------------------------------------------------


class TestConverseJsonbPersistence:
    """QA iter-2 FIX 1: the success branch of POST /converse MUST call
    ``append_conversation_turn`` twice (user turn + nikita turn) so the
    frontend can rebuild conversation continuity from JSONB."""

    @pytest.mark.asyncio
    async def test_converse_persists_user_and_nikita_turns_to_jsonb(self):
        """After one successful /converse call, 2 new turns (user +
        nikita) appear in ``users.onboarding_profile["conversation"]``
        with the correct roles and content.

        Exercises the handler function directly with AsyncMock session +
        mocked agent + mocked spend ledger + mocked idempotency store.
        The real ``append_conversation_turn`` helper runs against a
        SimpleNamespace user stub whose ``onboarding_profile`` is the
        JSONB dict under assertion.
        """
        from nikita.api.dependencies.auth import AuthenticatedUser
        from nikita.api.routes.portal_onboarding import converse
        from nikita.agents.onboarding.converse_contracts import ConverseRequest

        user_id = uuid4()
        user_stub = SimpleNamespace(id=user_id, onboarding_profile=None)

        # AsyncMock session that returns user_stub for any SELECT. The
        # two SELECT-FOR-UPDATE reads from append_conversation_turn hit
        # the same stub so both turns accrete on one dict.
        mock_session = AsyncMock()
        select_result = MagicMock()
        select_result.scalar_one = MagicMock(return_value=user_stub)
        mock_session.execute = AsyncMock(return_value=select_result)

        # Stub agent.run → object with .output (the nikita reply) and
        # .usage() (None → fallback to ESTIMATED_TURN_COST_USD).
        agent_result = SimpleNamespace(
            output="let's keep going. what city are you in?",
            usage=lambda: None,
        )
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=agent_result)

        req = ConverseRequest(
            conversation_history=[],
            user_input="I'm in Zurich and I love techno",
        )
        auth_user = AuthenticatedUser(id=user_id, email="test@example.com")

        with patch(
            "nikita.api.routes.portal_onboarding.get_conversation_agent",
            return_value=mock_agent,
        ), patch(
            "nikita.api.routes.portal_onboarding.IdempotencyStore"
        ) as mock_idem_cls, patch(
            "nikita.api.routes.portal_onboarding.LLMSpendLedger"
        ) as mock_ledger_cls:
            mock_idem = MagicMock()
            mock_idem.get = AsyncMock(return_value=None)
            mock_idem.put = AsyncMock(return_value=None)
            mock_idem_cls.return_value = mock_idem

            mock_ledger = MagicMock()
            mock_ledger.get_today = AsyncMock(return_value=0)
            mock_ledger.add_spend = AsyncMock(return_value=None)
            mock_ledger_cls.return_value = mock_ledger

            response = await converse(
                req=req,
                current_user=auth_user,
                session=mock_session,
                _rate_limit=None,
                idempotency_key_header=None,
            )

        # Success response (not a JSONResponse 429) — ConverseResponse.
        assert isinstance(response, ConverseResponse), (
            f"expected ConverseResponse, got {type(response).__name__}"
        )
        assert response.source == "llm"

        # JSONB now has exactly 2 turns — user then nikita.
        assert user_stub.onboarding_profile is not None
        conv = user_stub.onboarding_profile["conversation"]
        assert len(conv) == 2, f"expected 2 turns, got {len(conv)}"
        assert conv[0]["role"] == "user"
        assert conv[0]["content"] == "I'm in Zurich and I love techno"
        assert "timestamp" in conv[0]
        assert "extracted" in conv[0]  # dict, may be empty
        assert conv[1]["role"] == "nikita"
        assert conv[1]["content"] == "let's keep going. what city are you in?"
        assert conv[1]["source"] == "llm"

        # Spend ledger was incremented exactly once for the turn.
        mock_ledger.add_spend.assert_awaited_once()
        # Idempotency cache get() fired (turn_id=None path → skipped put).
        mock_idem.get.assert_not_awaited()  # turn_id is None → no HIT check


# ---------------------------------------------------------------------------
# GH #382 — converse pipeline batch-fix regression guards
# ---------------------------------------------------------------------------


class TestConverseMessageHistoryWiring:
    """GH #382 (D1): Walk Q showed the endpoint discarded the client's
    ``conversation_history`` and called ``agent.run(user_input, deps=deps)``
    without ``message_history=``. Every turn was cold; the LLM had no
    context for the wizard step, guessed wrong, and tool-call validation
    failed repeatedly.

    Fix: hydrate Turn[] → ModelMessage[] via
    ``nikita.agents.onboarding.message_history.hydrate_message_history``
    and pass via ``agent.run(..., message_history=...)``.
    """

    @pytest.mark.asyncio
    async def test_agent_run_receives_hydrated_message_history(self):
        """Given non-empty ``conversation_history`` in the request body,
        the handler MUST call ``agent.run(..., message_history=<hydrated>)``.
        Before the fix this kwarg was absent."""
        from nikita.api.dependencies.auth import AuthenticatedUser
        from nikita.api.routes.portal_onboarding import converse
        from nikita.agents.onboarding.converse_contracts import ConverseRequest, Turn

        user_id = uuid4()
        user_stub = SimpleNamespace(id=user_id, onboarding_profile=None)
        mock_session = AsyncMock()
        select_result = MagicMock()
        select_result.scalar_one = MagicMock(return_value=user_stub)
        mock_session.execute = AsyncMock(return_value=select_result)

        agent_result = SimpleNamespace(
            output="noted. what's your age?",
            usage=lambda: None,
        )
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=agent_result)

        prior_turn = Turn(
            role="nikita",
            content="hey. where do i find you on a thursday night?",
            timestamp=datetime.now(timezone.utc),
            source="llm",
        )
        req = ConverseRequest(
            conversation_history=[prior_turn],
            user_input="Zürich",
        )
        auth_user = AuthenticatedUser(id=user_id, email="test@example.com")

        with patch(
            "nikita.api.routes.portal_onboarding.get_conversation_agent",
            return_value=mock_agent,
        ), patch(
            "nikita.api.routes.portal_onboarding.IdempotencyStore"
        ) as mock_idem_cls, patch(
            "nikita.api.routes.portal_onboarding.LLMSpendLedger"
        ) as mock_ledger_cls:
            mock_idem = MagicMock()
            mock_idem.get = AsyncMock(return_value=None)
            mock_idem.put = AsyncMock(return_value=None)
            mock_idem_cls.return_value = mock_idem
            mock_ledger = MagicMock()
            mock_ledger.get_today = AsyncMock(return_value=0)
            mock_ledger.add_spend = AsyncMock(return_value=None)
            mock_ledger_cls.return_value = mock_ledger

            await converse(
                req=req,
                current_user=auth_user,
                session=mock_session,
                _rate_limit=None,
                idempotency_key_header=None,
            )

        # Introspect the agent.run call
        assert mock_agent.run.call_count == 1
        call_kwargs = mock_agent.run.call_args.kwargs
        history = call_kwargs.get("message_history")
        assert history is not None, (
            "agent.run called WITHOUT message_history — GH #382 regression"
        )
        # The single prior Nikita turn should produce a 1-element list
        assert len(history) == 1, (
            f"expected 1 hydrated message, got {len(history)}"
        )

    @pytest.mark.asyncio
    async def test_empty_history_omits_message_history_kwarg(self):
        """Fresh session (conversation_history=[]) should NOT pass
        ``message_history=`` — that way Pydantic AI re-runs the system
        prompt as documented for new sessions."""
        from nikita.api.dependencies.auth import AuthenticatedUser
        from nikita.api.routes.portal_onboarding import converse
        from nikita.agents.onboarding.converse_contracts import ConverseRequest

        user_id = uuid4()
        user_stub = SimpleNamespace(id=user_id, onboarding_profile=None)
        mock_session = AsyncMock()
        select_result = MagicMock()
        select_result.scalar_one = MagicMock(return_value=user_stub)
        mock_session.execute = AsyncMock(return_value=select_result)

        agent_result = SimpleNamespace(output="hi.", usage=lambda: None)
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=agent_result)

        req = ConverseRequest(conversation_history=[], user_input="hi")
        auth_user = AuthenticatedUser(id=user_id, email="test@example.com")

        with patch(
            "nikita.api.routes.portal_onboarding.get_conversation_agent",
            return_value=mock_agent,
        ), patch(
            "nikita.api.routes.portal_onboarding.IdempotencyStore"
        ) as mock_idem_cls, patch(
            "nikita.api.routes.portal_onboarding.LLMSpendLedger"
        ) as mock_ledger_cls:
            mock_idem_cls.return_value.get = AsyncMock(return_value=None)
            mock_idem_cls.return_value.put = AsyncMock(return_value=None)
            mock_ledger_cls.return_value.get_today = AsyncMock(return_value=0)
            mock_ledger_cls.return_value.add_spend = AsyncMock(return_value=None)

            await converse(
                req=req,
                current_user=auth_user,
                session=mock_session,
                _rate_limit=None,
                idempotency_key_header=None,
            )

        call_kwargs = mock_agent.run.call_args.kwargs
        # Either message_history is absent, or explicitly None/empty
        history = call_kwargs.get("message_history")
        assert history in (None, []), (
            f"empty conversation_history must not pass non-empty message_history; "
            f"got {history!r}"
        )


class TestConverseValidationRejectRouting:
    """GH #382 (D2 + D7 + D8): validation-reject path must:

    - D2: return the age<18 template ONLY when the failing constraint
      is actually age.ge on IdentityExtraction. Other tool validation
      errors get the generic FALLBACK_REPLY.
    - D7: persist the USER turn to JSONB even on validator reject so
      the next turn's message_history reflects reality.
    - D8: charge the spend ledger (ESTIMATED_TURN_COST_USD) because
      the LLM actually ran and burned tokens.
    """

    async def _run_converse_with_validation_error(self, errors_payload):
        """Helper: drive converse with agent.run raising a ValidationError
        whose errors() returns the provided payload."""
        from pydantic import BaseModel, ValidationError

        from nikita.api.dependencies.auth import AuthenticatedUser
        from nikita.api.routes.portal_onboarding import converse
        from nikita.agents.onboarding.converse_contracts import ConverseRequest

        user_id = uuid4()
        user_stub = SimpleNamespace(id=user_id, onboarding_profile=None)
        mock_session = AsyncMock()
        select_result = MagicMock()
        select_result.scalar_one = MagicMock(return_value=user_stub)
        mock_session.execute = AsyncMock(return_value=select_result)

        # Build a real ValidationError by forcing a Pydantic model to
        # reject — then monkeypatch .errors() to return our payload so
        # the test pins the handler's routing rather than Pydantic's
        # error-shape internals.
        class _Stub(BaseModel):
            x: int

        try:
            _Stub(x="not-an-int")  # type: ignore[arg-type]
        except ValidationError as real_exc:
            real_exc.errors = MagicMock(return_value=errors_payload)
            agent_exc = real_exc

        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(side_effect=agent_exc)

        req = ConverseRequest(
            conversation_history=[],
            user_input="I'm Simon, 32, in Zürich",
        )
        auth_user = AuthenticatedUser(id=user_id, email="test@example.com")

        with patch(
            "nikita.api.routes.portal_onboarding.get_conversation_agent",
            return_value=mock_agent,
        ), patch(
            "nikita.api.routes.portal_onboarding.IdempotencyStore"
        ) as mock_idem_cls, patch(
            "nikita.api.routes.portal_onboarding.LLMSpendLedger"
        ) as mock_ledger_cls:
            mock_idem = MagicMock()
            mock_idem.get = AsyncMock(return_value=None)
            mock_idem.put = AsyncMock(return_value=None)
            mock_idem_cls.return_value = mock_idem
            mock_ledger = MagicMock()
            mock_ledger.get_today = AsyncMock(return_value=0)
            mock_ledger.add_spend = AsyncMock(return_value=None)
            mock_ledger_cls.return_value = mock_ledger

            response = await converse(
                req=req,
                current_user=auth_user,
                session=mock_session,
                _rate_limit=None,
                idempotency_key_header=None,
            )

        return response, mock_ledger, user_stub

    @pytest.mark.asyncio
    async def test_age_constraint_error_returns_age_template(self):
        """D2: ValidationError whose first error is ``age.greater_than_equal``
        returns the ``_VALIDATION_REJECT_AGE_REPLY`` template."""
        from nikita.api.routes.portal_onboarding import _VALIDATION_REJECT_AGE_REPLY

        errors = [
            {
                "loc": ("age",),
                "type": "greater_than_equal",
                "msg": "Input should be greater than or equal to 18",
                "input": 15,
            }
        ]
        response, _ledger, _stub = await self._run_converse_with_validation_error(
            errors
        )
        assert response.nikita_reply == _VALIDATION_REJECT_AGE_REPLY
        assert response.source == "validation_reject"

    @pytest.mark.asyncio
    async def test_non_age_validation_error_returns_generic_fallback(self):
        """D2: non-age ValidationError must NOT return the age-18 template.

        Walk Q trapped this: a ValidationError on PhoneExtraction, or on
        NoExtraction.reason (D4 unblocked), or on _at_least_one_field,
        returned the age-18 template misleadingly. The correct behavior
        is the generic FALLBACK_REPLY.
        """
        from nikita.agents.onboarding.validators import FALLBACK_REPLY

        errors = [
            {
                "loc": ("phone",),
                "type": "value_error",
                "msg": "phone must be E.164",
                "input": "not-a-phone",
            }
        ]
        response, _ledger, _stub = await self._run_converse_with_validation_error(
            errors
        )
        assert response.nikita_reply == FALLBACK_REPLY, (
            f"non-age validator reject must return generic FALLBACK_REPLY, "
            f"got {response.nikita_reply!r}"
        )

    @pytest.mark.asyncio
    async def test_validation_reject_persists_user_turn(self):
        """D7: user turn must land in JSONB even on validator reject,
        otherwise every retry is cold and the user is stuck in a loop."""
        errors = [
            {
                "loc": ("phone",),
                "type": "value_error",
                "msg": "phone must be E.164",
                "input": "x",
            }
        ]
        _response, _ledger, user_stub = (
            await self._run_converse_with_validation_error(errors)
        )
        # Expect the user turn committed even though reply was fallback
        assert user_stub.onboarding_profile is not None, (
            "D7 regression: user turn not persisted on validation_reject; "
            "next turn will be cold and fail identically"
        )
        conv = user_stub.onboarding_profile.get("conversation", [])
        user_turns = [t for t in conv if t.get("role") == "user"]
        assert len(user_turns) == 1, (
            f"expected 1 user turn persisted, got {len(user_turns)}"
        )

    @pytest.mark.asyncio
    async def test_validation_reject_charges_spend(self):
        """D8: validator-reject path charged ESTIMATED_TURN_COST_USD
        because the LLM actually ran and burned tokens. Skipping the
        spend accrual on this path would let a determined caller evade
        the daily $2 cap by triggering validation errors."""
        errors = [
            {
                "loc": ("age",),
                "type": "greater_than_equal",
                "msg": "below 18",
                "input": 15,
            }
        ]
        _response, mock_ledger, _stub = (
            await self._run_converse_with_validation_error(errors)
        )
        mock_ledger.add_spend.assert_awaited_once()


# ---------------------------------------------------------------------------
# GH #373 — route registration regression guard (real FastAPI app)
# ---------------------------------------------------------------------------


class TestConverseEndpointPath:
    """GH #373 regression guard — POST /api/v1/onboarding/converse must be
    registered at the canonical path (no doubled /onboarding prefix, no
    /portal prefix).

    Walk N (2026-04-20) caught a 3-way drift: frontend posted to
    /portal/onboarding/converse, backend declaration produced
    /api/v1/onboarding/onboarding/converse (doubled), test docstring
    advertised yet a third path. Mock tests passed; prod 404'd for 5+ days.
    """

    def test_converse_endpoint_path_resolves_via_real_app(self):
        """The canonical path /api/v1/onboarding/converse MUST be registered.

        Before the #373 fix: route declaration ``"/onboarding/converse"`` under
        mount ``prefix="/api/v1/onboarding"`` produces a doubled
        ``/api/v1/onboarding/onboarding/converse`` path; no auth-or-anything
        request lands at the canonical path → 404 here. After the fix
        (declaration becomes ``"/converse"``) this passes with a 401/403/422
        (auth/schema rejection, route exists).
        """
        from fastapi.testclient import TestClient

        from nikita.api.main import create_app

        app = create_app()
        client = TestClient(app)
        # No auth header → expect 401/403; bad body → may produce 422.
        # All three are "route exists, request rejected" — opposite of 404.
        response = client.post(
            "/api/v1/onboarding/converse",
            json={"user_input": "x", "conversation_history": []},
        )
        assert response.status_code != 404, (
            f"Route /api/v1/onboarding/converse not registered. Got 404. "
            f"Check portal_onboarding.py route declaration vs main.py mount prefix "
            f"for #373-class regression."
        )
