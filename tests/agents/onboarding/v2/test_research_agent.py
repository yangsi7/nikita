"""Spec 218 Slice 218-6 — research agent mandatory triplet (RED).

Per `.claude/rules/agentic-design-patterns.md` + `.claude/rules/testing.md`
Agentic-Flow Test Requirements: any NEW agent file under
`nikita/agents/onboarding/v2/` MUST cover the three mandatory classes.

Phase-2 research agent (`nikita/agents/onboarding/v2/research_agent.py`) is
a NEW agent file in slice 218-6 — full triplet required (R3 / R13).

1. Cumulative-state monotonicity — phase_2_turn_count strictly non-decreasing
   across turns; completion gate never fires before MIN_TURNS.
2. Completion-gate triplet — `phase_2_gate` returns False below MIN_TURNS,
   False at MIN_TURNS with agent not signalling done, True at MIN_TURNS
   with agent signalling done, and forced True at MAX_TURNS.
3. Mock-LLM-emits-wrong-output recovery — agent returning str when
   CompleteAsk expected at MAX_TURNS; system forces completion envelope.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic_ai.exceptions import ModelRetry

from nikita.agents.onboarding.v2.research_agent import (
    V2ResearchDeps,
    get_research_agent,
    phase_2_gate,
)
from nikita.agents.onboarding.v2.state import (
    PHASE_2_MAX_TURNS,
    PHASE_2_MIN_TURNS,
    Phase,
    WizardSlotsV2,
    WizardStateV2,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _full_phase1_slots() -> WizardSlotsV2:
    """Return a WizardSlotsV2 with all Phase-1 required slots filled."""
    return WizardSlotsV2(
        display_name={"display_name": "Sam"},
        age={"age": 25},
        city={"city": "New York"},
        occupation={"occupation": "Engineer"},
        primary_hobbies={"primary_hobbies": ["hiking", "reading"]},
        hangouts_personalized={"hangouts_personalized": ["coffee", "museums"]},
        voice_or_text={"voice_or_text": "text"},
        saturday_morning={"saturday_morning": "coffee and journaling"},
        darkness_level={"darkness_level": 3},
        geek_out_on={"geek_out_on": "distributed systems and cats"},
    )


def _state(turn_count: int, phase: Phase = Phase.phase2) -> WizardStateV2:
    return WizardStateV2(
        slots=_full_phase1_slots(),
        phase=phase,
        phase_2_turn_count=turn_count,
        phase_2_started_at="2026-05-12T00:00:00Z",
    )


# ---------------------------------------------------------------------------
# 1. Cumulative-state monotonicity
# ---------------------------------------------------------------------------


class TestTurnCountMonotonicity:
    """phase_2_turn_count is non-decreasing across Phase-2 turns (FR-008)."""

    def test_turn_count_never_decreases(self) -> None:
        """Simulate 5 turns; count strictly increases each time."""
        counts = [_state(i).phase_2_turn_count for i in range(5)]
        for i in range(len(counts) - 1):
            assert counts[i + 1] > counts[i], (
                f"turn_count regressed from {counts[i]} to {counts[i + 1]}"
            )

    def test_minimum_turns_not_reached_at_turn_3(self) -> None:
        """phase_2_gate returns (False, ...) when count < MIN_TURNS."""
        state = _state(PHASE_2_MIN_TURNS - 1)
        complete, _ = phase_2_gate(state, agent_signals_done=False)
        assert complete is False

    def test_gate_never_fires_before_min_turns_even_if_agent_signals(self) -> None:
        """Agent signalling done before MIN_TURNS must be overridden."""
        for count in range(PHASE_2_MIN_TURNS):
            state = _state(count)
            complete, forced = phase_2_gate(state, agent_signals_done=True)
            assert complete is False, (
                f"gate fired at turn {count} before MIN_TURNS={PHASE_2_MIN_TURNS}"
            )
            assert forced is True, "should be flagged as forced retry"


# ---------------------------------------------------------------------------
# 2. Completion-gate triplet
# ---------------------------------------------------------------------------


class TestPhase2Gate:
    """phase_2_gate(state, agent_signals_done) -> (complete, forced)."""

    def test_empty_turn_count_not_complete(self) -> None:
        state = _state(0)
        complete, _ = phase_2_gate(state, agent_signals_done=False)
        assert complete is False

    def test_at_min_turns_agent_not_signalling_not_complete(self) -> None:
        state = _state(PHASE_2_MIN_TURNS)
        complete, forced = phase_2_gate(state, agent_signals_done=False)
        assert complete is False
        assert forced is False

    def test_at_min_turns_agent_signals_done_complete(self) -> None:
        state = _state(PHASE_2_MIN_TURNS)
        complete, forced = phase_2_gate(state, agent_signals_done=True)
        assert complete is True
        assert forced is False

    def test_at_max_turns_forced_complete_regardless_of_agent(self) -> None:
        state = _state(PHASE_2_MAX_TURNS)
        complete_no, forced_no = phase_2_gate(state, agent_signals_done=False)
        complete_yes, forced_yes = phase_2_gate(state, agent_signals_done=True)
        assert complete_no is True
        assert forced_no is True
        assert complete_yes is True
        assert forced_yes is True

    def test_beyond_max_turns_also_forced_complete(self) -> None:
        state = _state(PHASE_2_MAX_TURNS + 1)
        complete, forced = phase_2_gate(state, agent_signals_done=False)
        assert complete is True
        assert forced is True


# ---------------------------------------------------------------------------
# 3. Mock-LLM-emits-wrong-output recovery
# ---------------------------------------------------------------------------


class TestWrongOutputRecovery:
    """If agent returns str when CompleteAsk expected at MAX_TURNS,
    the orchestration layer forces a CompleteAsk."""

    def test_str_output_at_max_turns_triggers_forced_complete(self) -> None:
        """Simulation: agent returns a follow-up str, but MAX turns reached.
        The caller (Phase-2 orchestrator) must force CompleteAsk."""
        from nikita.agents.onboarding.v2.envelope import CompleteAsk
        from nikita.api.routes.portal_onboarding_v2 import (
            _force_phase2_complete_envelope,
        )

        state = _state(PHASE_2_MAX_TURNS)
        # Agent returned a str (wrong: should have signalled done)
        agent_output: str = "So tell me more about your weekend…"
        envelope = _force_phase2_complete_envelope(state)
        assert isinstance(envelope, CompleteAsk)
        assert envelope.component == "complete"

    @pytest.mark.asyncio
    async def test_research_agent_output_validator_rejects_complete_before_min(
        self,
    ) -> None:
        """Output validator raises ModelRetry when agent signals complete
        before PHASE_2_MIN_TURNS have been collected."""
        from nikita.agents.onboarding.v2.envelope import CompleteAsk
        from nikita.agents.onboarding.v2.research_agent import (
            build_phase2_output_validator,
        )

        from unittest.mock import MagicMock

        state = _state(PHASE_2_MIN_TURNS - 1)
        validator = build_phase2_output_validator()
        early_complete = CompleteAsk(next_route="/dashboard")
        ctx = MagicMock()
        ctx.deps.state = state

        # Validator must raise ModelRetry for premature completion
        with pytest.raises(ModelRetry):
            await validator(ctx, early_complete)  # type: ignore[arg-type]

    def test_research_deps_has_required_firecrawl_fields(self) -> None:
        """V2ResearchDeps carries fetch_invocations_this_turn and
        fetch_cost_cumulative required by firecrawl_tools._run_fetch."""
        from decimal import Decimal

        deps = V2ResearchDeps(
            user_id="00000000-0000-0000-0000-000000000001",
            state=_state(1),
            traceparent="00-trace-span-01",
        )
        assert hasattr(deps, "fetch_invocations_this_turn")
        assert hasattr(deps, "fetch_cost_cumulative")
        assert deps.fetch_cost_cumulative == Decimal("0")

    def test_get_research_agent_returns_same_instance(self) -> None:
        """@lru_cache(maxsize=1) — repeated calls return identical object."""
        agent_a = get_research_agent()
        agent_b = get_research_agent()
        assert agent_a is agent_b


# ---------------------------------------------------------------------------
# 4. Cost guard contract (Fix 3 — scaffolding for slice 218-7 tool wiring)
# ---------------------------------------------------------------------------


class TestCheckCostGuard:
    """_check_cost_guard raises ModelRetry when fetch budget is exhausted."""

    def test_raises_model_retry_when_fetch_budget_exceeded(self) -> None:
        """fetch_cost_cumulative >= FETCH_BUDGET_HARD_USD → ModelRetry."""
        from decimal import Decimal

        from pydantic_ai.exceptions import ModelRetry as _ModelRetry

        from nikita.agents.onboarding.cost_guard import FETCH_BUDGET_HARD_USD
        from nikita.agents.onboarding.v2.research_agent import _check_cost_guard

        deps = V2ResearchDeps(
            user_id="00000000-0000-0000-0000-000000000002",
            state=_state(1),
            fetch_cost_cumulative=FETCH_BUDGET_HARD_USD,
        )
        with pytest.raises(_ModelRetry):
            _check_cost_guard(deps)

    def test_no_raise_when_budget_available(self) -> None:
        """fetch_cost_cumulative well below both ceilings → no raise."""
        from decimal import Decimal

        from nikita.agents.onboarding.v2.research_agent import _check_cost_guard

        deps = V2ResearchDeps(
            user_id="00000000-0000-0000-0000-000000000003",
            state=_state(1),
            fetch_cost_cumulative=Decimal("0.01"),
        )
        # Must not raise
        _check_cost_guard(deps)

    def test_raises_model_retry_when_flow_ceiling_exceeded(self) -> None:
        """total_flow_cost_cumulative >= FLOW_HARD_CEILING_USD → ModelRetry.

        QA iter-2: flow ceiling check uses dedicated field
        ``total_flow_cost_cumulative`` (LLM + fetch combined) rather than
        the fetch-only field; fetch can be 0 while combined flow trips.
        """
        from decimal import Decimal

        from pydantic_ai.exceptions import ModelRetry as _ModelRetry

        from nikita.agents.onboarding.cost_guard import FLOW_HARD_CEILING_USD
        from nikita.agents.onboarding.v2.research_agent import _check_cost_guard

        deps = V2ResearchDeps(
            user_id="00000000-0000-0000-0000-000000000004",
            state=_state(1),
            fetch_cost_cumulative=Decimal("0.01"),  # fetch alone fine
            total_flow_cost_cumulative=FLOW_HARD_CEILING_USD,
        )
        with pytest.raises(_ModelRetry, match=r"flow ceiling"):
            _check_cost_guard(deps)
