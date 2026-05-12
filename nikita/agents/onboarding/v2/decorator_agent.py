"""Spec 218 Slice 218-3 — v2 decorator agent factory (extended).

Slice-218-2 baseline: TextShortAsk + HandlerHandoffAsk output union;
covered_in_slice = {display_name}.

Slice-218-3 extension:
  - output_type now also emits CalendarAsk + SingleSelectAsk.
  - COVERED_IN_SLICE = {display_name, age, city, occupation}.
  - inject_v2_per_turn_context dispatches per-target prompt strings.
  - build_decorator_output_validator enforces shape ↔ target pairing:
      display_name | occupation -> TextShortAsk
      age                       -> CalendarAsk
      city                      -> SingleSelectAsk
      uncovered target          -> HandlerHandoffAsk

Mirrors ``_create_emission_agent`` at
``nikita/agents/onboarding/conversation_agent.py:377-438`` with three
deliberate differences per spec 218 §18 P3 + plan R3:

  1. ``output_type`` is the v2 ``AskUnion`` decorated via ``ToolOutput``
     wrappers.
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
from typing import Any, Final
from uuid import UUID, uuid4

from pydantic_ai import Agent, ModelRetry, RunContext, ToolOutput

from nikita.agents.onboarding.v2.cohort_cities import CITY_OPTIONS
from nikita.agents.onboarding.v2.envelope import (
    CalendarAsk,
    HandlerHandoffAsk,
    SingleSelectAsk,
    TextShortAsk,
)
from nikita.agents.onboarding.v2.state import SlotKindV2, WizardSlotsV2
from nikita.config.models import Models


_MODEL_NAME = Models.sonnet()
"""Same model family as the v1 emission agent for voice consistency.

Slice-2 / 3 use Sonnet for the decorator; slice 218-6 will introduce
the research agent (Phase-2) which may use a different model (Gemini
deep research synthesis pending). Re-evaluation gated by spec 218 §18 P3.
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


COVERED_IN_SLICE: Final[frozenset[str]] = frozenset(
    {
        SlotKindV2.display_name.value,
        SlotKindV2.age.value,
        SlotKindV2.city.value,
        SlotKindV2.occupation.value,
    }
)
"""Slots covered by v2 in slice 218-3.

When the router picks a target NOT in this set, the decorator MUST
emit ``HandlerHandoffAsk`` so the FE mounts the v1 wizard for the
remainder of the session (per plan R14).

Slice 218-4 extends with voice_or_text / phone / hangouts_personalized
(and chip_multi shape). Slice 218-5 extends with saturday_morning /
darkness_level / geek_out_on (and slider / text_long shapes). Slice
218-8 deletes ``HandlerHandoffAsk`` atomically with v1.
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


def _city_option_lines() -> str:
    """Render ``CITY_OPTIONS`` as a one-per-line prompt fragment."""
    return "\n".join(f"  - {opt.value!r}: {opt.label}" for opt in CITY_OPTIONS)


def inject_v2_per_turn_context(ctx: RunContext[V2Deps]) -> str:
    """Per-turn dynamic instructions for the v2 decorator agent.

    Injects the current target slot and the still-missing slot list so
    the agent emits the correct shape for the target OR (when the
    target falls outside the slice's covered set) a ``HandlerHandoffAsk``
    to the v1 wizard.

    NEVER bake routing rules into a static system prompt — that is the
    anti-pattern called out in ADR-009 + plan R14.
    """
    deps = ctx.deps
    missing = ", ".join(deps.slots.missing) if deps.slots.missing else "(none)"
    target = deps.target_slot

    base = (
        "You are the v2 wizard decorator. Emit exactly one envelope for "
        f"the current target slot. Missing slots: {missing}. "
        f"Target: {target}."
    )

    if target == SlotKindV2.display_name.value:
        return (
            f"{base} Ask the user for their preferred display name. "
            "Emit ``TextShortAsk`` with slot='display_name'. "
            "Reply length ≤140 chars."
        )
    if target == SlotKindV2.age.value:
        return (
            f"{base} Ask the user for their date of birth (we compute "
            "age server-side). Emit ``CalendarAsk`` with slot='age'. "
            "Optionally set min_date='1900-01-01' and max_date set to "
            "today's date string."
        )
    if target == SlotKindV2.city.value:
        return (
            f"{base} Ask the user which city they are in. Emit "
            "``SingleSelectAsk`` with slot='city' and the following "
            f"options (value : label):\n{_city_option_lines()}\n"
            "Do NOT add new options; do NOT reorder."
        )
    if target == SlotKindV2.occupation.value:
        return (
            f"{base} Ask the user what they do for a living. Emit "
            "``TextShortAsk`` with slot='occupation'."
        )
    return (
        f"{base} This target slot ({target!r}) is not yet covered by "
        "this slice. Emit ``HandlerHandoffAsk`` with handler='v1' and "
        "next_url='/api/v1/converse/onboarding' so the FE mounts the "
        "v1 wizard for the remainder."
    )


# ---------------------------------------------------------------------------
# Output validator (Hard Rule §5 — three layers of validation)
# ---------------------------------------------------------------------------


_SHAPE_BY_TARGET: Final[dict[str, type]] = {
    SlotKindV2.display_name.value: TextShortAsk,
    SlotKindV2.age.value: CalendarAsk,
    SlotKindV2.city.value: SingleSelectAsk,
    SlotKindV2.occupation.value: TextShortAsk,
}
"""Expected output type per covered target slot.

Validator raises ``ModelRetry`` when the agent emits a shape that is
not the configured type for the target. Slice 218-4 / 218-5 extend
this mapping (chip_multi, slider, text_long, phone).

Note: ``display_name`` and ``occupation`` BOTH map to ``TextShortAsk``.
The shape-identity check passes for either target, so the validator
ALSO asserts ``output.slot == target`` (the slot-field assertion just
below) to disambiguate. A TextShortAsk with slot='occupation' emitted
when target='display_name' raises ModelRetry on the slot mismatch even
though the shape matches.
"""


def build_decorator_output_validator() -> Any:
    """Return a callable that raises ``ModelRetry`` when the emitted shape
    does not match the current target slot.

    The validator IS the wrong-tool recovery gate per Hard Rule §5 +
    plan R3 #3. Wrong-component recovery is the third mandatory triplet
    test.
    """

    def _validator(ctx: RunContext[V2Deps], output: Any) -> Any:
        target = ctx.deps.target_slot
        is_covered = target in COVERED_IN_SLICE

        # Handoff path: only valid when target is NOT covered by this slice.
        if isinstance(output, HandlerHandoffAsk):
            if is_covered:
                raise ModelRetry(
                    f"HandlerHandoffAsk emitted but target {target!r} IS "
                    f"covered by this slice. Emit the per-target shape."
                )
            return output

        # Covered path: shape must match the configured type for the target.
        if is_covered:
            expected = _SHAPE_BY_TARGET[target]
            if not isinstance(output, expected):
                raise ModelRetry(
                    f"Wrong shape for target {target!r}: got "
                    f"{type(output).__name__}, expected {expected.__name__}."
                )
            # For per-shape slot field, also assert the slot field matches
            # the target (TextShortAsk + CalendarAsk + SingleSelectAsk all
            # carry a `slot` attribute).
            slot_attr = getattr(output, "slot", None)
            if slot_attr is not None and slot_attr != target:
                raise ModelRetry(
                    f"Envelope slot {slot_attr!r} does not match target "
                    f"{target!r}. Re-emit for the correct slot."
                )
            return output

        # Uncovered target + non-handoff shape: invalid.
        raise ModelRetry(
            f"Target {target!r} is uncovered; emit HandlerHandoffAsk, "
            f"not {type(output).__name__}."
        )

    return _validator


# ---------------------------------------------------------------------------
# Agent factory (mirrors _create_emission_agent at conversation_agent.py:377-438)
# ---------------------------------------------------------------------------


def _create_decorator_agent() -> Agent[V2Deps, Any]:
    """Build the v2 decorator agent.

    Slice 218-3 output union: TextShortAsk + CalendarAsk +
    SingleSelectAsk + HandlerHandoffAsk.

    Per spec 218 §18 P3 + plan R3 + ADR-009:
      - ``output_type=[ToolOutput(...), ...]`` per covered shape
      - ``output_retries=3``  (vs v1's 2; wider union, looser tail)
      - Dynamic ``instructions(callable)`` injecting state.missing + target
      - ``@agent.output_validator`` wrong-component → ``ModelRetry``
      - ``deps_type=V2Deps``

    Slices 218-4 and 218-5 will extend ``output_type`` with chip_multi /
    slider / text_long / phone shapes as their slots come online.
    """
    agent: Agent[V2Deps, Any] = Agent(
        _MODEL_NAME,
        deps_type=V2Deps,
        output_type=[
            ToolOutput(TextShortAsk, name="ask_text_short"),
            ToolOutput(CalendarAsk, name="ask_calendar"),
            ToolOutput(SingleSelectAsk, name="ask_single_select"),
            ToolOutput(HandlerHandoffAsk, name="handoff_to_v1"),
        ],
        output_retries=OUTPUT_RETRIES,
    )

    agent.instructions(inject_v2_per_turn_context)

    validator_fn = build_decorator_output_validator()

    @agent.output_validator
    def v2_decorator_output_validator(
        ctx: RunContext[V2Deps], output: Any
    ) -> Any:
        # Descriptive name surfaces in Pydantic AI logging /
        # ModelRetry error messages — `_wrapped` would be ambiguous.
        return validator_fn(ctx, output)

    return agent


@lru_cache(maxsize=1)
def get_decorator_agent() -> Agent[V2Deps, Any]:
    """Return the cached v2 decorator agent singleton.

    Test isolation caveat: the agent is built once with the values of
    ``COVERED_IN_SLICE`` + ``_SHAPE_BY_TARGET`` + closures captured at
    factory time. Tests that monkey-patch these module-level constants
    AFTER the first ``get_decorator_agent()`` call will see no effect
    because the cached agent's validator closure was already bound.
    All slice-218-3 route tests mock ``get_decorator_agent`` directly
    (see ``test_portal_onboarding_v2_slice3.py``) so this is harmless
    now. Future tests that exercise the validator end-to-end should
    either bypass the cache via ``_create_decorator_agent()`` or call
    ``get_decorator_agent.cache_clear()`` in fixture teardown.
    """
    return _create_decorator_agent()


__all__ = [
    "COVERED_IN_SLICE",
    "OUTPUT_RETRIES",
    "V2Deps",
    "_create_decorator_agent",
    "build_decorator_output_validator",
    "get_decorator_agent",
    "inject_v2_per_turn_context",
]
