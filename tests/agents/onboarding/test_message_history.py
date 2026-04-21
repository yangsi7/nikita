"""Tests for nikita.agents.onboarding.message_history (GH #382 D1).

The portal wizard sends ``ConverseRequest.conversation_history``
on every turn. Before GH #382 the endpoint discarded this history,
so the LLM saw every turn cold and repeatedly failed tool-call
schema validation. The fix hydrates Turn[] → ModelMessage[] and
passes it via ``agent.run(..., message_history=...)``.

These tests pin the hydration behavior — cover the role mapping,
empty-input edge, and the required-field invariants the endpoint
relies on.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)

from nikita.agents.onboarding.converse_contracts import Turn
from nikita.agents.onboarding.message_history import hydrate_message_history


def _make_turn(role: str, content: str, **extra) -> Turn:
    return Turn(
        role=role,  # type: ignore[arg-type]
        content=content,
        timestamp=datetime.now(UTC),
        **extra,
    )


class TestHydrateMessageHistory:
    def test_empty_returns_empty_list(self):
        """No history → empty list (caller must then omit message_history=)."""
        assert hydrate_message_history([]) == []

    def test_user_role_maps_to_model_request(self):
        """role=user → ModelRequest(parts=[UserPromptPart])"""
        turns = [_make_turn("user", "hello")]
        out = hydrate_message_history(turns)
        assert len(out) == 1
        assert isinstance(out[0], ModelRequest)
        parts = out[0].parts
        assert len(parts) == 1
        assert isinstance(parts[0], UserPromptPart)
        assert parts[0].content == "hello"

    def test_nikita_role_maps_to_model_response(self):
        """role=nikita → ModelResponse(parts=[TextPart])"""
        turns = [_make_turn("nikita", "hey. building your file.")]
        out = hydrate_message_history(turns)
        assert len(out) == 1
        assert isinstance(out[0], ModelResponse)
        parts = out[0].parts
        assert len(parts) == 1
        assert isinstance(parts[0], TextPart)
        assert parts[0].content == "hey. building your file."

    def test_alternating_turns_preserve_order(self):
        """Multi-turn history must preserve strict chronological order."""
        turns = [
            _make_turn("nikita", "where do i find you on a thursday?"),
            _make_turn("user", "Zürich, techno spots near Langstrasse"),
            _make_turn("nikita", "noted. how old are you?"),
            _make_turn("user", "32"),
        ]
        out = hydrate_message_history(turns)
        assert len(out) == 4
        assert isinstance(out[0], ModelResponse)
        assert isinstance(out[1], ModelRequest)
        assert isinstance(out[2], ModelResponse)
        assert isinstance(out[3], ModelRequest)

    def test_drops_extracted_and_source_metadata(self):
        """Turn's `extracted` dict and `source` enum are wire metadata.
        The LLM only needs role + content; internal bookkeeping is
        dropped to keep the history surface minimal."""
        turns = [
            _make_turn(
                "nikita",
                "noted.",
                source="llm",
            ),
            _make_turn(
                "user",
                "32",
                extracted={"age": 32},
            ),
        ]
        out = hydrate_message_history(turns)
        # Both turns should be represented; no exception from extra fields
        assert len(out) == 2

    def test_walk_q_regression_history_is_not_discarded(self):
        """GH #382 regression guard: given a plausible wizard history,
        the hydrator produces a non-empty ModelMessage list. This is
        the single most important invariant for the #382 fix — if
        hydration silently returned [], the endpoint fix would regress
        to the original "cold every turn" failure mode.
        """
        turns = [
            _make_turn("nikita", "hey. where do i find you?"),
            _make_turn("user", "Zürich"),
        ]
        out = hydrate_message_history(turns)
        assert len(out) == 2
        # Must carry actual content, not empty strings from a bad mapper
        assert out[0].parts[0].content == "hey. where do i find you?"
        assert out[1].parts[0].content == "Zürich"
