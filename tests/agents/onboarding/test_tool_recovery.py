"""T-B-7 — Mock-LLM-emits-wrong-tool recovery (Agentic-Flow mandatory test #3).

Output validator + ModelRetry self-correcting loop:
- Reply too long → ModelRetry
- Mirror-echo (name * 2 in reply) → ModelRetry

The validator is the second layer of the three-layer validation stack
(Hard Rule §5).
"""

from __future__ import annotations

from uuid import uuid4

import pytest


def _imports():
    from pydantic_ai import ModelRetry  # noqa: PLC0415

    from nikita.agents.onboarding.conversation_agent import (  # noqa: PLC0415
        ConverseDeps,
        TurnFailure,
        TurnOutput,
        _validate_output,
    )
    from nikita.agents.onboarding.question_registry import SlotKind  # noqa: PLC0415
    from nikita.agents.onboarding.state import SlotDelta, WizardSlots  # noqa: PLC0415
    return ModelRetry, ConverseDeps, TurnFailure, TurnOutput, _validate_output, SlotKind, SlotDelta, WizardSlots


class _MockCtx:
    def __init__(self, deps):
        self.deps = deps


def _make_deps(ConverseDeps, slots, **overrides):
    defaults = {
        "state": slots,
        "state_summary": "",
        "last_slot_kind": None,
        "last_value": None,
        "next_slot_kind": None,
        "next_slot_hint": None,
        "cost_budget_remaining_usd": 1.0,
        "fetch_invocations_this_turn": 0,
        "fetch_cost_cumulative": 0.0,
        "cohort_cache": {},
        "big5_confidence": {},
        "traceparent": "",
        "user_id": uuid4(),
        "conversation_id": uuid4(),
    }
    defaults.update(overrides)
    return ConverseDeps(**defaults)


class TestOutputValidator:
    def test_reply_under_length_passes(self):
        """Short reply under 140 chars passes the validator."""
        _, ConverseDeps, _, TurnOutput, validate, _, _, WizardSlots = _imports()
        deps = _make_deps(ConverseDeps, WizardSlots())
        ctx = _MockCtx(deps)
        output = TurnOutput(delta=None, reply="hey, where are you?", next_slot_kind=None)
        result = validate(ctx, output)
        assert result.reply == "hey, where are you?"

    def test_reply_over_140_chars_raises_model_retry(self):
        """Reply > 140 chars triggers ModelRetry (B1.5)."""
        ModelRetry, ConverseDeps, _, TurnOutput, validate, _, _, WizardSlots = _imports()
        deps = _make_deps(ConverseDeps, WizardSlots())
        ctx = _MockCtx(deps)
        long_reply = "x" * 141
        output = TurnOutput(delta=None, reply=long_reply, next_slot_kind=None)
        with pytest.raises(ModelRetry):
            validate(ctx, output)

    def test_mirror_echo_name_repeat_raises_model_retry(self):
        """Mirror echo: last_value repeated twice in reply triggers ModelRetry (closes #443)."""
        ModelRetry, ConverseDeps, _, TurnOutput, validate, SlotKind, _, WizardSlots = _imports()
        deps = _make_deps(
            ConverseDeps, WizardSlots(),
            last_slot_kind=SlotKind.display_name,
            last_value="Sam",
        )
        ctx = _MockCtx(deps)
        # Reply contains "sam" twice (mirror echo)
        output = TurnOutput(
            delta=None,
            reply="hi sam, sam, lovely to meet you.",
            next_slot_kind=None,
        )
        with pytest.raises(ModelRetry):
            validate(ctx, output)

    def test_mirror_echo_single_use_passes(self):
        """Single use of last_value in reply is fine (not mirror echo)."""
        _, ConverseDeps, _, TurnOutput, validate, SlotKind, _, WizardSlots = _imports()
        deps = _make_deps(
            ConverseDeps, WizardSlots(),
            last_slot_kind=SlotKind.display_name,
            last_value="Sam",
        )
        ctx = _MockCtx(deps)
        output = TurnOutput(
            delta=None,
            reply="hi sam, where are you these days?",
            next_slot_kind=None,
        )
        result = validate(ctx, output)
        assert result is not None

    def test_turn_failure_passes_through(self):
        """TurnFailure outputs bypass mirror-echo / length validators."""
        _, ConverseDeps, TurnFailure, _, validate, _, _, WizardSlots = _imports()
        deps = _make_deps(ConverseDeps, WizardSlots())
        ctx = _MockCtx(deps)
        failure = TurnFailure(
            explanation="I cannot continue with that input.",
            last_slot_kind=None,
        )
        result = validate(ctx, failure)
        assert result is failure

    def test_validator_applies_delta_to_state(self):
        """Validator merges output.delta into ctx.deps.state (Hard Rule §1 wiring)."""
        _, ConverseDeps, _, TurnOutput, validate, _, SlotDelta, WizardSlots = _imports()
        deps = _make_deps(ConverseDeps, WizardSlots())
        ctx = _MockCtx(deps)
        delta = SlotDelta(kind="city", data={"city": "Berlin"})
        output = TurnOutput(delta=delta, reply="got it.", next_slot_kind=None)
        result = validate(ctx, output)
        assert result is not None
        assert ctx.deps.state.city == {"city": "Berlin"}
