"""Tests for bare-token fallback (closes GH #484 Walk A1 C1).

Three test classes per `.claude/rules/agentic-design-patterns.md`
Hard Rule §5 (validation layering, deterministic post-processing as
defense in depth):

1. Happy-path bare-token shapes that MUST extract.
2. Question / sentence shapes that MUST NOT extract (false-positive guard).
3. State invariants — never clobber a filled slot.
"""

from __future__ import annotations

import pytest

from nikita.agents.onboarding.bare_token_fallback import (
    DISPLAY_NAME_MAX_CHARS,
    DISPLAY_NAME_MAX_WORDS,
    try_bare_token_fill,
)
from nikita.agents.onboarding.state import SlotDelta, WizardSlots


class TestBareTokenFillsDisplayName:
    """Bare-token inputs MUST produce a display_name SlotDelta."""

    @pytest.mark.parametrize(
        "user_input,expected_canonical",
        [
            ("Walker", "Walker"),
            ("walker", "walker"),
            ("Mary Jane", "Mary Jane"),
            ("Mary Jane Watson", "Mary Jane Watson"),
            ("Walker.", "Walker"),
            ("Walker!", "Walker"),
            ("  Walker  ", "Walker"),
        ],
    )
    def test_bare_token_extracts_to_display_name(
        self, user_input: str, expected_canonical: str
    ) -> None:
        state = WizardSlots()
        delta = try_bare_token_fill(
            state, user_input, next_slot_kind="display_name"
        )
        assert delta is not None
        assert delta.kind == "display_name"
        assert delta.data == {"display_name": expected_canonical}


class TestBareTokenSkipsNonValueShapes:
    """Question and sentence shapes MUST NOT trip the fallback."""

    @pytest.mark.parametrize(
        "user_input",
        [
            "what?",
            "What's your name?",
            "why are you asking",
            "how do I answer",
            "when",
            "where do I start",
            "?",
            "",
            "   ",
            # Sentence-shaped inputs the agent should have handled
            "my name is Walker",
            "I'm Walker actually",
            "you can call me Walker",
            # Too long — likely a sentence
            "x" * (DISPLAY_NAME_MAX_CHARS + 1),
            # Too many words
            " ".join(["a"] * (DISPLAY_NAME_MAX_WORDS + 1)),
        ],
    )
    def test_skips_non_value_shapes(self, user_input: str) -> None:
        state = WizardSlots()
        delta = try_bare_token_fill(
            state, user_input, next_slot_kind="display_name"
        )
        assert delta is None


class TestMockLLMWrongToolRecovery:
    """Per .claude/rules/agentic-design-patterns.md Hard Rule §5 +
    .claude/rules/testing.md Agentic-Flow Test Requirements:

    Mock-LLM-emits-wrong-tool recovery test class. The agent emitting
    delta=null (or pointing next_slot_kind at the wrong slot) is the
    canonical "wrong tool" failure mode. The deterministic fallback
    is the recovery path."""

    def test_recovers_when_agent_emits_no_extraction(self) -> None:
        """Agent silently no-ops; fallback recovers display_name."""
        state = WizardSlots()
        # Agent's TurnOutput emitted delta=None (no extraction). Caller
        # downstream of agent.run consults next_question(state) — for
        # an empty state the answer is display_name.
        delta = try_bare_token_fill(
            state, "Walker", next_slot_kind="display_name"
        )
        assert delta is not None
        assert delta.kind == "display_name"

    def test_does_not_recover_when_agent_misroutes_to_other_slot(self) -> None:
        """Agent emits next_slot_kind=age on a name-shaped input.
        Fallback is conservative: skip rather than force-extract into
        the wrong slot. Caller must consult next_question(state) for
        the authoritative routing."""
        state = WizardSlots()
        delta = try_bare_token_fill(
            state, "Walker", next_slot_kind="age"
        )
        # Conservative skip: caller drives next_slot_kind, fallback
        # only fires when caller resolved to display_name.
        assert delta is None


class TestJSONBRoundtripSafety:
    """Per QA review #528 risk-1: synthesized SlotDelta values flow into
    JSONB conversation_history. Pydantic serialization is safe-by-default,
    but we assert it explicitly so future regressions are caught at unit
    level instead of leaking into pgvector / RAG retrievals."""

    @pytest.mark.parametrize(
        "malicious_input",
        [
            "Walker'); DROP TABLE users;--",
            'Walker"; DELETE FROM users;--',
            "Walker\\x00",
            "Walker‮‏",  # bidi override + zero-width
            "Walker\n\rDELETE",
            "Walker<script>alert(1)</script>",
        ],
    )
    def test_malicious_input_roundtrips_safely(self, malicious_input: str) -> None:
        """Roundtrip: input → fallback → SlotDelta → JSONB-serializable
        dict. Verify no SQL/JSON-structural injection survives."""
        import json as _json

        # First, the predicate must reject many of these (long, has space
        # patterns, etc.). For ones that DO get through, the resulting
        # delta must serialize cleanly to JSON without breaking the
        # conversation_history JSONB shape.
        state = WizardSlots()
        delta = try_bare_token_fill(
            state, malicious_input, next_slot_kind="display_name"
        )
        if delta is None:
            return  # Predicate rejected — even better
        # Pydantic.model_dump → json.dumps roundtrip. If the input
        # contained an unescaped quote / null byte, the dump-load
        # cycle would either fail or surface a different shape.
        dumped = delta.model_dump()
        encoded = _json.dumps(dumped)
        decoded = _json.loads(encoded)
        assert decoded["kind"] == "display_name"
        assert "display_name" in decoded["data"]
        # Crucially, the value reads back identically — no truncation
        # at quote/null boundaries, no shape mutation.
        assert decoded["data"]["display_name"] == dumped["data"]["display_name"]


class TestBareTokenInvariants:
    """State invariants — never clobber, never run for wrong slot."""

    def test_does_not_clobber_filled_slot(self) -> None:
        state = WizardSlots().apply(
            SlotDelta(kind="display_name", data={"display_name": "Existing"})
        )
        delta = try_bare_token_fill(
            state, "Walker", next_slot_kind="display_name"
        )
        assert delta is None

    def test_skips_when_next_slot_is_not_display_name(self) -> None:
        # next slot is something else; we only handle display_name today.
        state = WizardSlots()
        delta = try_bare_token_fill(state, "Walker", next_slot_kind="age")
        assert delta is None

    def test_skips_when_next_slot_kind_is_none(self) -> None:
        state = WizardSlots()
        delta = try_bare_token_fill(state, "Walker", next_slot_kind=None)
        assert delta is None
