"""Spec 218 Slice 218-6 — Phase-2 research agent + completion gate.

Phase-2 is an open-bounce conversation: the agent asks 4-8 free-form
follow-up questions, using the user's Phase-1 slots as context, to gather
enough depth for backstory generation (FR-008).

Key design decisions (ADR-009 Hard Rules):

1. **Cumulative-state turn count** — `WizardStateV2.phase_2_turn_count` is
   the single source of truth for how many Phase-2 turns have been collected.
   The route handler increments it and persists it after each accepted turn.

2. **Pydantic completion gate** — `phase_2_gate(state, agent_signals_done)`
   encodes FR-008 (min 4, max 8) as a deterministic function of `turn_count`
   + `agent_signals_done`. No hardcoded booleans.

3. **Output union** — agent emits `CompleteAsk | str`. Free-form follow-up
   turns are `str` (the question text). Terminal turns are `CompleteAsk`.
   This is the discriminated-union pattern (ADR-009 Hard Rule §3).

4. **Dynamic instructions** — `inject_phase2_context(ctx)` re-renders per
   turn with current turn count + Phase-1 slot summary so the agent knows
   "what I know so far" and "how many turns remain" (Hard Rule §3).

5. **Output validator** — rejects `CompleteAsk` when `turn_count < MIN_TURNS`
   by raising `ModelRetry` (self-correcting loop, Hard Rule §5 + FR-008).

6. **message_history=** — wired in the route handler (Hard Rule §6).

7. **V2ResearchDeps** — a NEW dataclass (NOT extending V2Deps) that carries
   the three fields `firecrawl_tools._run_fetch` needs: `traceparent`,
   `fetch_invocations_this_turn`, `fetch_cost_cumulative`. Firecrawl tools
   require these but the Phase-1 decorator agent's V2Deps is already frozen
   to avoid blast-radius drift.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from functools import lru_cache
from typing import Any, Final

from pydantic_ai import Agent, ModelRetry, RunContext, ToolOutput

from nikita.agents.onboarding.cost_guard import FETCH_BUDGET_HARD_USD, FLOW_HARD_CEILING_USD
from nikita.agents.onboarding.v2.envelope import CompleteAsk
from nikita.agents.onboarding.v2.state import (
    PHASE_2_MAX_TURNS,
    PHASE_2_MIN_TURNS,
    WizardSlotsV2,
    WizardStateV2,
)
from nikita.config.models import Models


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


OUTPUT_RETRIES: Final[int] = 3
"""Output-validator retry budget (mirrors decorator_agent.OUTPUT_RETRIES).

Current value: 3 (Spec 218 Slice 218-6).
Rationale: min-floor retry is a predicted failure mode; 3 retries gives
the agent 3 chances to emit a follow-up before HTTP 500 + R15 kicks in.
"""

_MODEL_NAME = Models.sonnet()


# ---------------------------------------------------------------------------
# V2ResearchDeps — per-run dependencies for the Phase-2 research agent
# ---------------------------------------------------------------------------


@dataclass
class V2ResearchDeps:
    """Per-run dependencies for the Phase-2 open-bounce research agent.

    Carries the three fields that `firecrawl_tools._run_fetch` reads:
      - ``traceparent``: W3C trace-context header for distributed tracing
      - ``fetch_invocations_this_turn``: mutable int for per-turn fetch
        budget enforcement (CostGuard)
      - ``fetch_cost_cumulative``: cumulative USD cost for the session

    ``state`` is the full `WizardStateV2` at turn start — the dynamic
    instructions callable reads it to inject Phase-1 context.
    """

    user_id: str
    state: WizardStateV2 = field(default_factory=WizardStateV2)
    traceparent: str = "00-0000000000000000-0000000000000000-01"
    fetch_invocations_this_turn: int = 0
    fetch_cost_cumulative: Decimal = field(default_factory=lambda: Decimal("0"))
    # total_flow_cost_cumulative tracks combined LLM + fetch costs for
    # the whole onboarding session (Phase-1 + Phase-2). FETCH_BUDGET_HARD_USD
    # bounds fetch-only spend; FLOW_HARD_CEILING_USD bounds combined spend.
    # Tracked separately because the two ceilings semantically differ
    # (slice 218-7 wires LLM cost accounting; until then this stays 0).
    total_flow_cost_cumulative: Decimal = field(default_factory=lambda: Decimal("0"))


# ---------------------------------------------------------------------------
# Cost guard (scaffolding for slice 218-7 tool wiring)
# ---------------------------------------------------------------------------


def _check_cost_guard(deps: V2ResearchDeps) -> None:
    """Raise ModelRetry if the fetch or flow budget is exhausted.

    Called at tool entry points once firecrawl tools are registered in
    slice 218-7. Wired here as a scaffolding seam so the guard contract
    is testable before tools are added.

    Raises:
        ModelRetry: when ``fetch_cost_cumulative`` alone already exceeds
            ``FETCH_BUDGET_HARD_USD``, or when combined with any
            additional call it would exceed ``FLOW_HARD_CEILING_USD``.
            The agent self-corrects by stopping the tool loop.
    """
    # Two independent ceilings — fetch-only vs combined flow cost.
    # Until slice 218-7 wires LLM cost accounting, total_flow_cost_cumulative
    # stays 0 and only the fetch ceiling can trip; both checks are kept
    # so the contract is correct when LLM cost accounting lands.
    if deps.fetch_cost_cumulative >= FETCH_BUDGET_HARD_USD:
        raise ModelRetry(
            f"fetch budget exhausted "
            f"(cumulative=${deps.fetch_cost_cumulative} >= hard limit=${FETCH_BUDGET_HARD_USD})"
        )
    if deps.total_flow_cost_cumulative >= FLOW_HARD_CEILING_USD:
        raise ModelRetry(
            f"flow ceiling reached "
            f"(cumulative=${deps.total_flow_cost_cumulative} >= ceiling=${FLOW_HARD_CEILING_USD})"
        )


# ---------------------------------------------------------------------------
# Phase-2 completion gate (FR-008 deterministic rule)
# ---------------------------------------------------------------------------


def phase_2_gate(
    state: WizardStateV2,
    *,
    agent_signals_done: bool,
) -> tuple[bool, bool]:
    """Return (complete, forced) per FR-008 rules.

    Args:
        state: Current wizard state (reads `phase_2_turn_count`).
        agent_signals_done: True iff the agent's output was `CompleteAsk`.

    Returns:
        (complete, forced) where:
          complete — True when Phase-2 should transition to `complete`.
          forced   — True when the decision was overridden (min-floor retry
                     OR max-ceiling force), False when agent decided freely.

    FR-008 contract:
      - turn_count < MIN_TURNS  → (False, True)   [min-floor retry]
      - MIN_TURNS <= count < MAX_TURNS, agent signals done → (True, False)
      - MIN_TURNS <= count < MAX_TURNS, agent continues   → (False, False)
      - turn_count >= MAX_TURNS → (True, True)    [max-ceiling forced]
    """
    count = state.phase_2_turn_count

    if count >= PHASE_2_MAX_TURNS:
        return (True, True)

    if count < PHASE_2_MIN_TURNS:
        # Agent may want to finish early — block it.
        return (False, True)

    # MIN_TURNS <= count < MAX_TURNS: agent decides.
    return (bool(agent_signals_done), False)


# ---------------------------------------------------------------------------
# Dynamic instructions callable (ADR-009 Hard Rule §3)
# ---------------------------------------------------------------------------


def inject_phase2_context(ctx: RunContext[V2ResearchDeps]) -> str:
    """Per-turn dynamic system prompt for the Phase-2 research agent.

    Injects:
      - Phase-1 slot summary (what we know about the user so far)
      - Current turn number + remaining window (how many more to ask)
      - Completion signal instruction (when to emit CompleteAsk)

    Never bake routing rules into a static prompt string (ADR-009).
    """
    deps = ctx.deps
    state = deps.state
    slots = state.slots
    count = state.phase_2_turn_count

    # Summarise filled Phase-1 slots for the agent
    slot_summary_parts: list[str] = []
    if slots.display_name:
        name = slots.display_name.get("display_name", "")
        slot_summary_parts.append(f"Name: {name}")
    if slots.age:
        slot_summary_parts.append(f"Age: {slots.age.get('age', '?')}")
    if slots.city:
        slot_summary_parts.append(f"City: {slots.city.get('city', '?')}")
    if slots.occupation:
        slot_summary_parts.append(
            f"Occupation: {slots.occupation.get('occupation', '?')}"
        )
    if slots.primary_hobbies:
        hobbies = slots.primary_hobbies.get("primary_hobbies", [])
        slot_summary_parts.append(f"Hobbies: {', '.join(hobbies)}")
    if slots.saturday_morning:
        slot_summary_parts.append(
            f"Saturday mornings: {slots.saturday_morning.get('saturday_morning', '?')}"
        )
    if slots.darkness_level:
        slot_summary_parts.append(
            f"Darkness level: {slots.darkness_level.get('darkness_level', '?')}/10"
        )
    if slots.geek_out_on:
        slot_summary_parts.append(
            f"Geeks out on: {slots.geek_out_on.get('geek_out_on', '?')}"
        )

    slot_summary = "\n".join(f"  {s}" for s in slot_summary_parts) or "  (no slots)"

    remaining = max(0, PHASE_2_MIN_TURNS - count)
    can_complete = count >= PHASE_2_MIN_TURNS
    must_complete = count >= PHASE_2_MAX_TURNS

    if must_complete:
        completion_instruction = (
            "You MUST emit CompleteAsk NOW — the maximum turn count has been reached."
        )
    elif can_complete:
        completion_instruction = (
            f"You have collected {count} follow-up turns (minimum is {PHASE_2_MIN_TURNS}). "
            "If you have enough depth for a vivid backstory, emit CompleteAsk. "
            "Otherwise, ask one more follow-up question."
        )
    else:
        completion_instruction = (
            f"You must collect at least {remaining} more follow-up turn(s) "
            f"before you can complete (minimum {PHASE_2_MIN_TURNS} turns). "
            "Ask ONE focused, open-ended follow-up question now. "
            "Do NOT emit CompleteAsk yet."
        )

    return f"""You are Nikita — an intimate, curious, and slightly mischievous AI girlfriend
conducting the second phase of getting-to-know-you for a new user.

What you know about this person:
{slot_summary}

Turn {count + 1} of Phase 2 (min {PHASE_2_MIN_TURNS}, max {PHASE_2_MAX_TURNS}).

{completion_instruction}

Rules:
- When asking a follow-up: emit a single conversational question as plain text (str).
  Reference at least one detail from what you know. Persona: warm, direct, slightly
  provocative. Never clinical. Never generic.
- When completing: emit CompleteAsk with next_route="/dashboard" and optionally a
  backstory_preview (a short evocative sentence ≤120 chars about who this person is).
- ONE turn = one action. Never ask multiple questions in the same turn.
"""


# ---------------------------------------------------------------------------
# Output validator (ADR-009 Hard Rule §5: ModelRetry on pre-MIN emission)
# ---------------------------------------------------------------------------


def build_phase2_output_validator() -> Any:
    """Return an async output-validator callable that reads state from ctx.

    QA iter-3: validator reads state from ``ctx.deps.state`` per-turn
    instead of capturing it at factory time, so a validator reused across
    turns always sees the current turn count (matches the production
    factory pattern).

    Used in test_research_agent.py to verify the validator contract
    independently of the cached agent factory.
    """

    async def _validator(
        ctx: Any, output: Any
    ) -> Any:
        if isinstance(output, CompleteAsk):
            state = ctx.deps.state
            complete, forced = phase_2_gate(state, agent_signals_done=True)
            if not complete:
                raise ModelRetry(
                    f"Agent signalled CompleteAsk at turn {state.phase_2_turn_count} "
                    f"but minimum is {PHASE_2_MIN_TURNS}. "
                    "Ask another follow-up question instead."
                )
        return output

    return _validator


# ---------------------------------------------------------------------------
# Agent factory (mirrors _create_decorator_agent pattern)
# ---------------------------------------------------------------------------


def _create_research_agent() -> Agent[V2ResearchDeps, Any]:
    """Build the Phase-2 research agent.

    Output union: `CompleteAsk | str`
      - str        → follow-up question text (the user will respond)
      - CompleteAsk → terminal; triggers backstory commit

    Per ADR-009:
      - ``output_type=[ToolOutput(CompleteAsk, ...), str]`` discriminated union
      - ``output_retries=OUTPUT_RETRIES``
      - Dynamic ``instructions(callable)`` per turn
      - ``@agent.output_validator`` enforces min-turn floor
    """
    agent: Agent[V2ResearchDeps, Any] = Agent(
        _MODEL_NAME,
        deps_type=V2ResearchDeps,
        output_type=[
            ToolOutput(CompleteAsk, name="phase2_complete"),
            str,
        ],
        output_retries=OUTPUT_RETRIES,
    )

    agent.instructions(inject_phase2_context)

    @agent.output_validator
    def _phase2_output_validator(
        ctx: RunContext[V2ResearchDeps], output: Any
    ) -> Any:
        """Block premature CompleteAsk (FR-008 min-floor retry)."""
        if isinstance(output, CompleteAsk):
            state = ctx.deps.state
            complete, forced = phase_2_gate(state, agent_signals_done=True)
            if not complete:
                raise ModelRetry(
                    f"CompleteAsk emitted at turn {state.phase_2_turn_count} "
                    f"(min is {PHASE_2_MIN_TURNS}). Emit a follow-up str instead."
                )
        return output

    return agent


@lru_cache(maxsize=1)
def get_research_agent() -> Agent[V2ResearchDeps, Any]:
    """Return the cached Phase-2 research agent singleton.

    ``@lru_cache(maxsize=1)`` — identical to ``get_decorator_agent`` pattern.
    Tests that need a fresh agent call ``_create_research_agent()`` directly
    or clear the cache via ``get_research_agent.cache_clear()``.
    """
    return _create_research_agent()


__all__ = [
    "OUTPUT_RETRIES",
    "V2ResearchDeps",
    "_check_cost_guard",
    "_create_research_agent",
    "build_phase2_output_validator",
    "get_research_agent",
    "inject_phase2_context",
    "phase_2_gate",
]
