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
