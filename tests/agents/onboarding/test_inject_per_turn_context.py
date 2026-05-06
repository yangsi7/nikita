"""B1.4 — inject_per_turn_context callable per-turn rendering.

The callable reads ConverseDeps and renders a per-turn instruction block
that names the next slot, missing slots, last value, and state summary.
The static system_prompt is REMOVED for routing rules — all per-turn
guidance flows through this callable.
"""

from __future__ import annotations

from uuid import uuid4

import pytest


def _imports():
    from nikita.agents.onboarding.conversation_agent import ConverseDeps  # noqa: PLC0415
    from nikita.agents.onboarding.conversation_prompts import (  # noqa: PLC0415
        inject_per_turn_context,
    )
    from nikita.agents.onboarding.question_registry import SlotKind  # noqa: PLC0415
    from nikita.agents.onboarding.state import WizardSlots  # noqa: PLC0415
    return ConverseDeps, inject_per_turn_context, SlotKind, WizardSlots


class _MockCtx:
    """Minimal RunContext stand-in carrying ``deps``."""
    def __init__(self, deps):
        self.deps = deps


def _make_deps(ConverseDeps, slots, **overrides):
    """Build a ConverseDeps with sensible defaults for the unspecified fields."""
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


class TestInjectPerTurnContext:
    def test_callable_returns_string(self):
        """inject_per_turn_context must return a non-empty string."""
        ConverseDeps, inject, _, WizardSlots = _imports()
        deps = _make_deps(ConverseDeps, WizardSlots())
        ctx = _MockCtx(deps)
        result = inject(ctx)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_references_state_missing(self):
        """Callable references state.missing — anti-static-prompt guard."""
        ConverseDeps, inject, _, WizardSlots = _imports()
        deps = _make_deps(ConverseDeps, WizardSlots())
        ctx = _MockCtx(deps)
        result = inject(ctx)
        # At least one of the unfilled slot names should appear in output
        assert any(
            slot_name in result for slot_name in deps.state.missing
        ) or "missing" in result.lower()

    def test_includes_next_slot_kind_when_present(self):
        """When next_slot_kind is set, it appears in the rendered context."""
        ConverseDeps, inject, SlotKind, WizardSlots = _imports()
        deps = _make_deps(
            ConverseDeps, WizardSlots(),
            next_slot_kind=SlotKind.city,
            next_slot_hint="Ask their city.",
        )
        ctx = _MockCtx(deps)
        result = inject(ctx)
        assert "city" in result.lower() or "Ask their city" in result

    def test_complete_state_skips_next_slot_block(self):
        """When state has no missing slots, callable does NOT emit a NEXT SLOT
        routing instruction (the wizard is done)."""
        ConverseDeps, inject, _, WizardSlots = _imports()
        # Build a fully-filled state via direct construction
        from nikita.agents.onboarding.state import SlotDelta
        slots = WizardSlots()
        for kind in [
            "display_name", "age", "occupation", "city", "darkness_level",
            "primary_hobbies", "saturday_morning", "geek_out_on",
            "together_we_could", "same_weird_if", "voice_tone_pref",
            "backstory_pick", "phone",
        ]:
            slots = slots.apply(SlotDelta(kind=kind, data={kind: "x"}))
        deps = _make_deps(ConverseDeps, slots)
        ctx = _MockCtx(deps)
        result = inject(ctx)
        # When complete: no NEXT SLOT directive, no STILL MISSING block.
        assert "NEXT SLOT" not in result
        assert "STILL MISSING" not in result
        # The base instructions are still rendered (cacheable prefix is stable).
        assert "Nikita" in result

    def test_bare_token_rule_emitted_when_next_slot_present(self):
        """GH #484: when next_slot_kind is set, dynamic instructions
        carry an explicit BARE-TOKEN RULE telling the agent to commit
        a SlotDelta on 1-3 word user inputs instead of clarifying."""
        ConverseDeps, inject, SlotKind, WizardSlots = _imports()
        deps = _make_deps(
            ConverseDeps, WizardSlots(),
            next_slot_kind=SlotKind.display_name,
            next_slot_hint="Ask their name.",
        )
        ctx = _MockCtx(deps)
        result = inject(ctx)
        assert "BARE-TOKEN" in result
        # Slot is named in the rule (not just elsewhere in prompt)
        assert result.count("display_name") >= 2

    def test_bare_token_rule_skipped_when_state_complete(self):
        """When state has no missing slots, no NEXT SLOT block, hence
        no BARE-TOKEN RULE block — wizard is done, agent should just
        acknowledge."""
        ConverseDeps, inject, _, WizardSlots = _imports()
        from nikita.agents.onboarding.state import SlotDelta
        slots = WizardSlots()
        for kind in [
            "display_name", "age", "occupation", "city", "darkness_level",
            "primary_hobbies", "saturday_morning", "geek_out_on",
            "together_we_could", "same_weird_if", "voice_tone_pref",
            "backstory_pick", "phone",
        ]:
            slots = slots.apply(SlotDelta(kind=kind, data={kind: "x"}))
        deps = _make_deps(ConverseDeps, slots)
        ctx = _MockCtx(deps)
        result = inject(ctx)
        assert "BARE-TOKEN" not in result

    def test_includes_last_value_when_present(self):
        """When last_slot_kind/last_value set, they appear in the context."""
        ConverseDeps, inject, SlotKind, WizardSlots = _imports()
        deps = _make_deps(
            ConverseDeps, WizardSlots(),
            last_slot_kind=SlotKind.display_name,
            last_value="Sam",
        )
        ctx = _MockCtx(deps)
        result = inject(ctx)
        # We expect display_name reference or value present
        assert "display_name" in result.lower() or "Sam" in result
