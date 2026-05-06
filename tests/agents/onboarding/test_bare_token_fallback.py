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
