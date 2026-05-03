"""Spec 216-E E1.2 — always-fetch-something directive.

When ``state.city`` has been collected and ``fetch_invocations_this_turn``
is 0, the dynamic-instructions block injected into the agent's system
prompt MUST include the always-fetch directive. When city is absent, the
directive is suppressed (turn 0).

This test exercises ``inject_per_turn_context`` directly — the LLM tool
selection itself is mocked elsewhere; what we assert here is the system
prompt contract that drives the agent toward fetch invocation.
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from nikita.agents.onboarding.conversation_agent import ConverseDeps
from nikita.agents.onboarding.conversation_prompts import inject_per_turn_context
from nikita.agents.onboarding.state import SlotDelta, WizardSlots


def _ctx(deps: ConverseDeps) -> SimpleNamespace:
    return SimpleNamespace(deps=deps)


def _deps_with_city(city_value: str = "Berlin") -> ConverseDeps:
    slots = WizardSlots().apply(SlotDelta(kind="city", data={"city": city_value}))
    return ConverseDeps(
        user_id=uuid4(),
        conversation_id=uuid4(),
        state=slots,
        state_summary="",
        last_slot_kind=None,
        last_value=None,
        next_slot_kind=None,
        next_slot_hint=None,
        cost_budget_remaining_usd=1.0,
        fetch_invocations_this_turn=0,
        fetch_cost_cumulative=0.0,
        cohort_cache={},
        big5_confidence={},
        traceparent="",
    )


def _deps_without_city() -> ConverseDeps:
    return ConverseDeps(
        user_id=uuid4(),
        conversation_id=uuid4(),
        state=WizardSlots(),
        state_summary="",
        last_slot_kind=None,
        last_value=None,
        next_slot_kind=None,
        next_slot_hint=None,
        cost_budget_remaining_usd=1.0,
        fetch_invocations_this_turn=0,
        fetch_cost_cumulative=0.0,
        cohort_cache={},
        big5_confidence={},
        traceparent="",
    )


def test_directive_present_when_city_set_and_no_fetch_yet():
    deps = _deps_with_city()
    rendered = inject_per_turn_context(_ctx(deps))
    assert "fetch_" in rendered
    # The fingerprint phrase MUST be in the dynamic block.
    assert "invoke ONE fetch_*" in rendered or "invoke ONE fetch_*" in rendered.lower()


def test_directive_absent_when_city_unset_turn_zero():
    deps = _deps_without_city()
    rendered = inject_per_turn_context(_ctx(deps))
    # No always-fetch directive on turn 0 (city missing).
    assert "invoke ONE fetch_*" not in rendered


def test_directive_absent_when_a_fetch_already_fired_this_turn():
    deps = _deps_with_city()
    deps.fetch_invocations_this_turn = 1
    rendered = inject_per_turn_context(_ctx(deps))
    # Directive suppressed once the per-turn fetch has fired (E1.3 cap).
    assert "invoke ONE fetch_*" not in rendered


def test_directive_runs_for_all_subsequent_turns_with_city_present():
    """E1.2 — across N>=2 turns, every turn after city collection sees
    the directive (when no fetch has fired yet). This is the durable
    contract that lets the agent honor "always fetch something."""
    for _ in range(12):
        deps = _deps_with_city()  # fresh per-turn deps
        rendered = inject_per_turn_context(_ctx(deps))
        assert "invoke ONE fetch_*" in rendered
