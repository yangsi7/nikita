"""Tests for nikita.agents.onboarding.v2.message_history (GH #582).

Covers ``hydrate_v2_message_history`` — the v2 JSONB message list to
Pydantic AI ``ModelMessage`` converter used by ``handle_v2_answer``
before ``agent.run(..., message_history=...)``.

Wire shape under test:
    [
        {"role": "user",  "content": "..."},
        {"role": "agent", "content": "..."},
        ...
    ]

Per ADR-009 Hard Rule §6: official Pydantic AI multi-turn primitive.
"""

from __future__ import annotations

import pytest
from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, UserPromptPart


class TestHydrateV2MessageHistory:
    def test_empty_input_returns_empty(self):
        from nikita.agents.onboarding.v2.message_history import hydrate_v2_message_history

        assert hydrate_v2_message_history([]) == []

    def test_none_input_returns_empty(self):
        from nikita.agents.onboarding.v2.message_history import hydrate_v2_message_history

        assert hydrate_v2_message_history(None) == []

    def test_user_message_becomes_model_request(self):
        from nikita.agents.onboarding.v2.message_history import hydrate_v2_message_history

        result = hydrate_v2_message_history([{"role": "user", "content": "hello"}])

        assert len(result) == 1
        assert isinstance(result[0], ModelRequest)
        assert isinstance(result[0].parts[0], UserPromptPart)
        assert result[0].parts[0].content == "hello"

    def test_agent_message_becomes_model_response(self):
        from nikita.agents.onboarding.v2.message_history import hydrate_v2_message_history

        result = hydrate_v2_message_history([{"role": "agent", "content": "hi back"}])

        assert len(result) == 1
        assert isinstance(result[0], ModelResponse)
        assert isinstance(result[0].parts[0], TextPart)
        assert result[0].parts[0].content == "hi back"

    def test_alternating_round_trip(self):
        from nikita.agents.onboarding.v2.message_history import hydrate_v2_message_history

        result = hydrate_v2_message_history(
            [
                {"role": "user", "content": "U1"},
                {"role": "agent", "content": "A1"},
                {"role": "user", "content": "U2"},
            ]
        )

        assert len(result) == 3
        assert isinstance(result[0], ModelRequest)
        assert isinstance(result[1], ModelResponse)
        assert isinstance(result[2], ModelRequest)
        # Content preserved
        assert result[0].parts[0].content == "U1"
        assert result[1].parts[0].content == "A1"
        assert result[2].parts[0].content == "U2"

    def test_unknown_role_skipped(self):
        from nikita.agents.onboarding.v2.message_history import hydrate_v2_message_history

        result = hydrate_v2_message_history(
            [
                {"role": "user", "content": "ok"},
                {"role": "system", "content": "skipped"},
                {"role": "agent", "content": "fine"},
            ]
        )

        # "system" role unknown → skipped; 2 valid entries remain
        assert len(result) == 2
        assert isinstance(result[0], ModelRequest)
        assert isinstance(result[1], ModelResponse)

    def test_missing_role_skipped(self):
        from nikita.agents.onboarding.v2.message_history import hydrate_v2_message_history

        result = hydrate_v2_message_history([{"content": "no role here"}])

        assert result == []

    def test_non_str_content_skipped(self):
        from nikita.agents.onboarding.v2.message_history import hydrate_v2_message_history

        result = hydrate_v2_message_history([{"role": "user", "content": 42}])

        assert result == []

    def test_non_dict_entry_skipped(self):
        from nikita.agents.onboarding.v2.message_history import hydrate_v2_message_history

        result = hydrate_v2_message_history(
            ["not-a-dict", {"role": "user", "content": "valid"}]
        )

        assert len(result) == 1
        assert isinstance(result[0], ModelRequest)

    def test_regression_non_empty_produces_non_empty(self):
        """GH #582 regression guard: given a plausible v2 message list,
        the hydrator produces a non-empty ModelMessage list.

        This is the single most important invariant — if hydration silently
        returned [] the endpoint would call agent.run without message_history
        and every turn would be cold (same failure mode as GH #382 for v1).
        """
        from nikita.agents.onboarding.v2.message_history import hydrate_v2_message_history

        messages = [
            {"role": "agent", "content": "Hey, where are you based?"},
            {"role": "user", "content": "Berlin"},
        ]
        result = hydrate_v2_message_history(messages)

        assert len(result) == 2
        assert result[0].parts[0].content == "Hey, where are you based?"
        assert result[1].parts[0].content == "Berlin"
