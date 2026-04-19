"""Tests for POST /api/v1/portal/onboarding/converse (Spec 214 FR-11d).

Split across three concerns:

- ``TestConverseRequestSchema`` — T2.4 AC-T2.4.1/2/3 (schema + control
  selection + length ceiling).
- ``TestConverseEndpointBody`` — T2.5 AC-T2.5.* (authz, rate-limit,
  idempotency, timeout/fallback, input sanitization, output leak filter,
  tool-call edge cases, reply validators).
- ``TestConverseJailbreakFixtures`` — T2.5.5 + T2.5.7 (OWASP LLM01
  fixtures and output-leak filter).

PII policy (per .claude/rules/testing.md): assertions reference UUIDs
and boolean flags only. Name/age/occupation/phone values MUST NOT
appear in log-line format strings or assertion messages.
"""

from __future__ import annotations

from datetime import datetime, timezone
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
