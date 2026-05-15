"""Spec 218 Slice 218-3/218-4/218-5 — v2 decorator agent factory (extended).

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

Slice-218-4 extension:
  - output_type now also emits ChipMultiAsk + PhoneAsk.
  - COVERED_IN_SLICE extends to 8 slots:
      {display_name, age, city, occupation,
       primary_hobbies, hangouts_personalized, voice_or_text, phone}
  - inject_v2_per_turn_context adds branches for the 4 new targets.
  - _SHAPE_BY_TARGET extended with 4 new slot → shape mappings.

Slice-218-5 extension:
  - output_type now also emits SliderAsk + TextLongAsk.
  - COVERED_IN_SLICE extends to 11 slots (full Phase-1 coverage):
      {display_name, age, city, occupation,
       primary_hobbies, hangouts_personalized, voice_or_text, phone,
       saturday_morning, darkness_level, geek_out_on}
  - inject_v2_per_turn_context adds branches for the 3 new targets.
  - _SHAPE_BY_TARGET extended with 3 new slot → shape mappings.

Three deliberate differences from the v1 emission agent (deleted in PR-218-8)
per spec 218 §18 P3 + plan R3:

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

from nikita.agents.onboarding.v2.cohort_cities import (
    CITY_OPTIONS,
    HANGOUT_OPTIONS,
    HOBBY_OPTIONS,
)
from nikita.agents.onboarding.v2.envelope import (
    CalendarAsk,
    ChipMultiAsk,
    PhoneAsk,
    SingleSelectAsk,
    SliderAsk,
    TextLongAsk,
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


CHIP_MULTI_MAX_PICK: Final[int] = 5
"""Server-side cap on chip_multi submissions (primary_hobbies, hangouts_personalized).
Aligned with portal_onboarding_v2._slot_payload's len(items) > 5 rejection."""


SLIDER_MIN_VAL: Final[int] = 0
SLIDER_MAX_VAL: Final[int] = 10
"""Server-side bounds for slider slots (saturday_morning, darkness_level).
Aligned with portal_onboarding_v2._slot_payload's 0 <= value <= 10 check.
Validator rejects SliderAsk emissions outside this window to keep agent
prompt + FE renderer + server cap aligned (slice-218-5 BOUND-DRIFT precedent
mirrors CHIP_MULTI_MAX_PICK pattern from slice 218-4)."""


TEXT_LONG_MAX_CHARS: Final[int] = 1000
"""Server-side cap on text_long submissions (geek_out_on).
Aligned with portal_onboarding_v2._slot_payload's len(stripped) > 1000 rejection.
Validator rejects TextLongAsk emissions with max_chars > TEXT_LONG_MAX_CHARS
so the FE textarea cannot allow over-cap input that the route silently rejects."""


COVERED_IN_SLICE: Final[frozenset[str]] = frozenset(
    {
        SlotKindV2.display_name.value,
        SlotKindV2.age.value,
        SlotKindV2.city.value,
        SlotKindV2.occupation.value,
        SlotKindV2.primary_hobbies.value,
        SlotKindV2.hangouts_personalized.value,
        SlotKindV2.voice_or_text.value,
        SlotKindV2.phone.value,
        SlotKindV2.saturday_morning.value,
        SlotKindV2.darkness_level.value,
        SlotKindV2.geek_out_on.value,
    }
)
"""Slots covered by v2 in slice 218-5 (full Phase-1 coverage = 11 slots).

Slice 218-8 deleted ``HandlerHandoffAsk`` with all v1 code.  Any target
outside this set raises ``ValueError`` (not handoff) — all 11 Phase-1
slots are in the set so this branch is never reached in production.
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


def _hobby_option_lines() -> str:
    """Render ``HOBBY_OPTIONS`` as a one-per-line prompt fragment."""
    return "\n".join(f"  - {opt.value!r}: {opt.label}" for opt in HOBBY_OPTIONS)


def _hangout_option_lines() -> str:
    """Render ``HANGOUT_OPTIONS`` as a one-per-line prompt fragment."""
    return "\n".join(f"  - {opt.value!r}: {opt.label}" for opt in HANGOUT_OPTIONS)


def inject_v2_per_turn_context(ctx: RunContext[V2Deps]) -> str:
    """Per-turn dynamic instructions for the v2 decorator agent.

    Injects the current target slot and the still-missing slot list so
    the agent emits the correct shape for the target OR (when the
    target falls outside the slice's covered set) a ``HandlerHandoffAsk``
    to the v1 wizard.

    NEVER bake routing rules into a static system prompt — that is the
    anti-pattern called out in ADR-009.
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
    if target == SlotKindV2.primary_hobbies.value:
        return (
            f"{base} Ask the user about their hobbies/interests. "
            "Emit ``ChipMultiAsk`` with slot='primary_hobbies', "
            f"min_pick=1, max_pick={CHIP_MULTI_MAX_PICK}, "
            f"and these options:\n{_hobby_option_lines()}\n"
            "Do NOT add or remove options; do NOT reorder."
        )
    if target == SlotKindV2.hangouts_personalized.value:
        return (
            f"{base} Ask the user which types of spots they like to hang "
            "out at. Emit ``ChipMultiAsk`` with "
            "slot='hangouts_personalized', "
            f"min_pick=1, max_pick={CHIP_MULTI_MAX_PICK}, "
            f"and these options:\n{_hangout_option_lines()}\n"
            "Do NOT add or remove options; do NOT reorder."
        )
    if target == SlotKindV2.voice_or_text.value:
        return (
            f"{base} Ask the user whether they prefer voice calls or text "
            "messages. Emit ``SingleSelectAsk`` with slot='voice_or_text' "
            "and exactly two options: "
            "{value='voice', label='Voice calls'}, "
            "{value='text', label='Text messages'}."
        )
    if target == SlotKindV2.phone.value:
        return (
            f"{base} Ask the user for their phone number (for the demo "
            "call). Emit ``PhoneAsk`` with slot='phone', "
            "default_country='US', demo_call_after_submit=True."
        )
    if target == SlotKindV2.saturday_morning.value:
        return (
            f"{base} Ask the user how active they are on Saturday mornings. "
            "Emit ``SliderAsk`` with slot='saturday_morning', min_val=0, "
            "max_val=10, step=1, labels={0: 'Total couch potato', "
            "5: 'Balanced', 10: 'Up at 6am + gym'}."
        )
    if target == SlotKindV2.darkness_level.value:
        return (
            f"{base} Ask the user how dark their sense of humour is. "
            "Emit ``SliderAsk`` with slot='darkness_level', min_val=0, "
            "max_val=10, step=1, labels={0: 'Light and breezy', "
            "5: 'Medium roast', 10: 'Pitch black'}."
        )
    if target == SlotKindV2.geek_out_on.value:
        return (
            f"{base} Ask the user what topic they could talk about for "
            "hours. Emit ``TextLongAsk`` with slot='geek_out_on', "
            "max_chars=1000, placeholder='e.g. vintage synthesizers, "
            "the Byzantine Empire, competitive Tetris…'."
        )
    # All 11 Phase-1 slots are covered (PR-218-8). Unreachable in production;
    # raise to surface any accidental gap in COVERED_IN_SLICE.
    raise ValueError(
        f"Target slot {target!r} is not in COVERED_IN_SLICE. "
        "Update COVERED_IN_SLICE in decorator_agent.py."
    )


# ---------------------------------------------------------------------------
# Output validator (Hard Rule §5 — three layers of validation)
# ---------------------------------------------------------------------------


_SHAPE_BY_TARGET: Final[dict[str, type]] = {
    SlotKindV2.display_name.value: TextShortAsk,
    SlotKindV2.age.value: CalendarAsk,
    SlotKindV2.city.value: SingleSelectAsk,
    SlotKindV2.occupation.value: TextShortAsk,
    SlotKindV2.primary_hobbies.value: ChipMultiAsk,
    SlotKindV2.hangouts_personalized.value: ChipMultiAsk,
    SlotKindV2.voice_or_text.value: SingleSelectAsk,
    SlotKindV2.phone.value: PhoneAsk,
    SlotKindV2.saturday_morning.value: SliderAsk,
    SlotKindV2.darkness_level.value: SliderAsk,
    SlotKindV2.geek_out_on.value: TextLongAsk,
}
"""Expected output type per covered target slot.

Validator raises ``ModelRetry`` when the agent emits a shape that is
not the configured type for the target. Slice 218-5 adds slider/text_long
mappings; slice 218-8 is the terminal (v1 removed).

Notes:
- ``display_name`` and ``occupation`` BOTH map to ``TextShortAsk``.
  The validator ALSO asserts ``output.slot == target`` to disambiguate.
- ``primary_hobbies`` and ``hangouts_personalized`` BOTH map to
  ``ChipMultiAsk``. Same slot-field assertion disambiguates.
- ``city`` and ``voice_or_text`` BOTH map to ``SingleSelectAsk``.
  Same slot-field assertion disambiguates.
- ``phone`` maps to ``PhoneAsk``; ``PhoneAsk.slot`` is always
  Literal["phone"] so the slot-field check always agrees for this target.
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

        # All 11 Phase-1 slots are covered (PR-218-8); is_covered is always True.
        if is_covered:
            expected = _SHAPE_BY_TARGET[target]
            if not isinstance(output, expected):
                raise ModelRetry(
                    f"Wrong shape for target {target!r}: got "
                    f"{type(output).__name__}, expected {expected.__name__}."
                )
            # For per-shape slot field, also assert the slot field matches
            # the target (TextShortAsk + CalendarAsk + SingleSelectAsk all
            # carry a ``slot`` attribute). CompleteAsk is not in
            # ``_SHAPE_BY_TARGET`` so it bypasses this check naturally.
            # If a future shape WITHOUT a slot field is ever added to
            # ``_SHAPE_BY_TARGET``, this guard must be tightened (e.g.,
            # raise ModelRetry when slot field is required-by-spec but
            # absent on the output).
            slot_attr = getattr(output, "slot", None)
            if slot_attr is not None and slot_attr != target:
                raise ModelRetry(
                    f"Envelope slot {slot_attr!r} does not match target "
                    f"{target!r}. Re-emit for the correct slot."
                )
            # max_pick guard (slice 218-4): the envelope Pydantic default is 8,
            # but the server-side _slot_payload caps chip submissions at 5
            # (CHIP_MULTI_MAX_PICK). If the agent emits a higher max_pick the FE
            # would allow over-cap selections that the route silently rejects.
            # Catch the drift here so the LLM self-corrects via ModelRetry.
            if isinstance(output, ChipMultiAsk) and output.max_pick > CHIP_MULTI_MAX_PICK:
                raise ModelRetry(
                    f"ChipMultiAsk.max_pick={output.max_pick} exceeds "
                    f"CHIP_MULTI_MAX_PICK={CHIP_MULTI_MAX_PICK}. "
                    f"Emit max_pick={CHIP_MULTI_MAX_PICK}."
                )
            # SliderAsk bounds guard (slice 218-5): saturday_morning + darkness_level
            # are int 0-10 server-side. Reject emissions outside the SLIDER_MIN_VAL /
            # SLIDER_MAX_VAL window so the LLM doesn't drift the prompt + FE renderer
            # away from what _slot_payload accepts.
            if isinstance(output, SliderAsk) and (
                output.min_val != SLIDER_MIN_VAL or output.max_val != SLIDER_MAX_VAL
            ):
                raise ModelRetry(
                    f"SliderAsk min/max=({output.min_val},{output.max_val}) does not "
                    f"match required bounds ({SLIDER_MIN_VAL},{SLIDER_MAX_VAL}). "
                    f"Emit min_val={SLIDER_MIN_VAL}, max_val={SLIDER_MAX_VAL}."
                )
            # TextLongAsk max_chars guard (slice 218-5): the envelope Pydantic
            # default is 500 (envelope.py, le=2000), but the server-side _slot_payload
            # caps text_long submissions at TEXT_LONG_MAX_CHARS=1000. If the agent
            # emits a higher max_chars, the FE textarea would allow over-cap input
            # that the route silently rejects.
            if isinstance(output, TextLongAsk) and output.max_chars > TEXT_LONG_MAX_CHARS:
                raise ModelRetry(
                    f"TextLongAsk.max_chars={output.max_chars} exceeds "
                    f"TEXT_LONG_MAX_CHARS={TEXT_LONG_MAX_CHARS}. "
                    f"Emit max_chars={TEXT_LONG_MAX_CHARS}."
                )
            return output

        # Uncovered target: raise ValueError (PR-218-8: all 11 Phase-1 slots
        # are covered; this branch is a hard guard against future drift).
        raise ValueError(
            f"Target {target!r} not in COVERED_IN_SLICE; "
            f"add it before extending the decorator output union."
        )

    return _validator


# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------


def _create_decorator_agent() -> Agent[V2Deps, Any]:
    """Build the v2 decorator agent.

    Slice 218-8 output union (HandlerHandoffAsk removed with all v1 code):
    TextShortAsk + CalendarAsk + SingleSelectAsk + ChipMultiAsk +
    PhoneAsk + SliderAsk + TextLongAsk.

    Per spec 218 §18 P3 + plan R3 + ADR-009:
      - ``output_type=[ToolOutput(...), ...]`` per covered shape
      - ``output_retries=3``  (vs v1's 2; wider union, looser tail)
      - Dynamic ``instructions(callable)`` injecting state.missing + target
      - ``@agent.output_validator`` wrong-component → ``ModelRetry``
      - ``deps_type=V2Deps``
    """
    agent: Agent[V2Deps, Any] = Agent(
        _MODEL_NAME,
        deps_type=V2Deps,
        output_type=[
            ToolOutput(TextShortAsk, name="ask_text_short"),
            ToolOutput(CalendarAsk, name="ask_calendar"),
            ToolOutput(SingleSelectAsk, name="ask_single_select"),
            ToolOutput(ChipMultiAsk, name="ask_chip_multi"),
            ToolOutput(PhoneAsk, name="ask_phone"),
            ToolOutput(SliderAsk, name="ask_slider"),
            ToolOutput(TextLongAsk, name="ask_text_long"),
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
    ``COVERED_IN_SLICE`` + ``_SHAPE_BY_TARGET`` + ``CHIP_MULTI_MAX_PICK``
    + ``SLIDER_MIN_VAL`` + ``SLIDER_MAX_VAL`` + ``TEXT_LONG_MAX_CHARS``
    + closures captured at factory time. Tests that monkey-patch these module-level constants
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
