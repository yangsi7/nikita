"""Spec 218 Slice 218-2 — v2 decorator agent factory.

Mirrors ``_create_emission_agent`` at
``nikita/agents/onboarding/conversation_agent.py:377-438`` with three
deliberate differences per spec 218 §18 P3 + plan R3:

  1. ``output_type`` is the v2 ``AskUnion`` decorated via ``ToolOutput``
     wrappers (slice-2 union currently: ``TextShortAsk`` +
     ``HandlerHandoffAsk``; subsequent slices extend).
  2. ``output_retries=3`` (vs v1's ``=2``) per spec recommendation.
  3. Dynamic ``instructions`` injects ``state.missing`` + current target
     slot per turn (Hard Rule §3 + §6) via a v2-specific callable.

The decorator agent NEVER persists. The route handler dispatches on
the agent's output and persists exactly once per accepted slot.

R12 / R15: mid-failure (Pydantic AI exception, model timeout, retries
exhausted) is the caller's responsibility — the route handler converts
exceptions into the ``v2_decorator_failure`` 500 envelope. The agent
itself does not catch.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any
from uuid import UUID, uuid4

from pydantic_ai import Agent, ModelRetry, RunContext, ToolOutput

from nikita.agents.onboarding.v2.envelope import HandlerHandoffAsk, TextShortAsk
from nikita.agents.onboarding.v2.state import SlotKindV2, WizardSlotsV2
from nikita.config.models import Models


_MODEL_NAME = Models.sonnet()
"""Same model family as the v1 emission agent for voice consistency.

Slice-2 uses Sonnet for the decorator; slice 218-6 will introduce the
research agent (Phase-2) which may use a different model (Gemini deep
research synthesis pending). Re-evaluation gated by spec 218 §18 P3.
"""


OUTPUT_RETRIES: int = 3
"""Output-validator retry budget. Tuning-constant regression-guarded.

Current value: 3 (Spec 218 Slice 218-2, plan R12).
Prior values: none (new in PR-218-2).
Rationale: Spec 218 §18 P3 recommends 3 (vs v1 emission union which uses
2) because v2 union is wider — wrong-tool failures are more frequent
during slice rollout. Exhaustion triggers route-level 500 + R15 retry
endpoint, not silent fallback (per plan R12).
"""


# ---------------------------------------------------------------------------
# V2Deps — per-run dependencies for the decorator agent
# ---------------------------------------------------------------------------


@dataclass
class V2Deps:
    """Per-run deps for the v2 decorator agent.

    ``slots`` is the cumulative v2 state at the start of the turn.
    ``target_slot`` is the slot the router picked for this turn
    (``pick_next_target(slots)`` output); the decorator's instructions
    callable injects this so the LLM knows what to ask.
    """

    user_id: UUID
    conversation_id: UUID = field(default_factory=uuid4)
    slots: WizardSlotsV2 = field(default_factory=WizardSlotsV2)
    target_slot: str = SlotKindV2.display_name.value


# ---------------------------------------------------------------------------
# Dynamic instructions callable (Hard Rule §3 + §6)
# ---------------------------------------------------------------------------


def inject_v2_per_turn_context(ctx: RunContext[V2Deps]) -> str:
    """Per-turn dynamic instructions for the v2 decorator agent.

    Injects the current target slot and the still-missing slot list so
    the agent emits a ``TextShortAsk`` for the right slot OR (when the
    target falls outside the slice's covered set) a ``HandlerHandoffAsk``
    to the v1 wizard.

    NEVER bake routing rules into a static system prompt — that is the
    anti-pattern called out in ADR-009 + plan R14.
    """
    deps = ctx.deps
    missing = ", ".join(deps.slots.missing) if deps.slots.missing else "(none)"
    target = deps.target_slot

    # Slice 218-2 covers display_name only. When the router picks any
    # other slot, the decorator MUST emit HandlerHandoffAsk so the FE
    # mounts the v1 wizard for the remainder.
    covered_in_slice = {SlotKindV2.display_name.value}

    if target in covered_in_slice:
        return (
            "You are the v2 wizard decorator. Ask the user for their "
            f"preferred display name. Emit a ``TextShortAsk`` with "
            f"slot='display_name'. Reply length ≤140 chars. "
            f"Missing slots: {missing}. Target: {target}."
        )
    return (
        "You are the v2 wizard decorator, but the current target slot "
        f"({target!r}) is not yet covered by this slice. Emit a "
        "``HandlerHandoffAsk`` with handler='v1' and "
        "next_url='/api/v1/converse/onboarding' so the FE mounts the v1 "
        f"wizard for remainder. Missing: {missing}."
    )


# ---------------------------------------------------------------------------
# Output validator (Hard Rule §5 — three layers of validation)
# ---------------------------------------------------------------------------


def build_decorator_output_validator() -> Any:
    """Return a callable that raises ``ModelRetry`` when the emitted shape
    does not match the current target slot.

    The validator IS the wrong-tool recovery gate per Hard Rule §5 +
    plan R3 #3. Wrong-component recovery is the third mandatory triplet
    test.
    """

    def _validator(ctx: RunContext[V2Deps], output: Any) -> Any:
        target = ctx.deps.target_slot
        if isinstance(output, TextShortAsk):
            if output.slot != target:
                raise ModelRetry(
                    f"TextShortAsk slot {output.slot!r} does not match "
                    f"target {target!r}. Re-emit for the correct slot."
                )
            return output
        if isinstance(output, HandlerHandoffAsk):
            # Handoff is only valid when target is NOT covered by this
            # slice. Slice 218-2 covers display_name only.
            covered = {SlotKindV2.display_name.value}
            if target in covered:
                raise ModelRetry(
                    f"HandlerHandoffAsk emitted but target {target!r} IS "
                    f"covered by this slice. Emit a TextShortAsk instead."
                )
            return output
        raise ModelRetry(
            f"Unsupported output type {type(output).__name__}. "
            "Emit TextShortAsk or HandlerHandoffAsk."
        )

    return _validator


# ---------------------------------------------------------------------------
# Agent factory (mirrors _create_emission_agent at conversation_agent.py:377-438)
# ---------------------------------------------------------------------------


def _create_decorator_agent() -> Agent[V2Deps, Any]:
    """Build the v2 decorator agent (Slice 218-2 scope: text_short + handoff).

    Per spec 218 §18 P3 + plan R3 + ADR-009:
      - ``output_type=[ToolOutput(TextShortAsk, ...), ToolOutput(HandlerHandoffAsk, ...)]``
      - ``output_retries=3``  (vs v1's 2; wider union, looser tail)
      - Dynamic ``instructions(callable)`` injecting state.missing + target
      - ``@agent.output_validator`` wrong-component → ``ModelRetry``
      - ``deps_type=V2Deps``

    Slices 218-3 through 218-5 will extend ``output_type`` to add more
    shapes as their slots come online.
    """
    agent: Agent[V2Deps, Any] = Agent(
        _MODEL_NAME,
        deps_type=V2Deps,
        output_type=[
            ToolOutput(TextShortAsk, name="ask_text_short"),
            ToolOutput(HandlerHandoffAsk, name="handoff_to_v1"),
        ],
        output_retries=OUTPUT_RETRIES,
    )

    agent.instructions(inject_v2_per_turn_context)

    validator_fn = build_decorator_output_validator()

    @agent.output_validator
    def _wrapped(ctx: RunContext[V2Deps], output: Any) -> Any:
        return validator_fn(ctx, output)

    return agent


@lru_cache(maxsize=1)
def get_decorator_agent() -> Agent[V2Deps, Any]:
    """Return the cached v2 decorator agent singleton."""
    return _create_decorator_agent()


__all__ = [
    "OUTPUT_RETRIES",
    "V2Deps",
    "_create_decorator_agent",
    "build_decorator_output_validator",
    "get_decorator_agent",
    "inject_v2_per_turn_context",
]
