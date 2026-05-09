"""Deterministic Phase 1 slot router (Spec 218 FR-003 + FR-006 + FR-007).

The agent does NOT pick which slot to ask next in Phase 1. A non-LLM
component does — this module. Walk V (2026-04-22) precedent: LLM
tool-selection bias makes agent-picked slots unreliable.

Public API:

  ``REQUIRED_ORDER`` — fixed ordering of the 11 Phase 1 slots.
  ``pick_next_target(state)`` -> ``SlotKindV2 | None`` — next slot to
    ask, or ``None`` if Phase 1 is complete (caller transitions to Phase 2).
  ``dag_invalidate(state, edited_slot)`` -> ``(new_state, invalidated)``
    — apply DAG invalidation per FR-007 and return the new state plus
    list of slot names that were null-ed out.

Conditional logic:

  - ``phone`` is skipped when ``voice_or_text == "text"`` (FR-007 +
    FinalForm cross-field validator).
  - All other slots are always required in Phase 1.

Caller contract: ``pick_next_target`` walks ``REQUIRED_ORDER`` and
returns the first slot whose value is ``None`` (and which is not
filtered out by the conditional logic). Returns ``None`` when every
required-slot has a non-None value, signalling Phase 2 transition.
"""

from __future__ import annotations

from typing import Final

from nikita.agents.onboarding.v2.state import (
    SLOT_DEPENDENCIES,
    SlotKindV2,
    WizardSlotsV2,
)


REQUIRED_ORDER: Final[tuple[SlotKindV2, ...]] = (
    SlotKindV2.display_name,
    SlotKindV2.age,
    SlotKindV2.city,
    SlotKindV2.occupation,
    SlotKindV2.primary_hobbies,
    SlotKindV2.hangouts_personalized,
    SlotKindV2.voice_or_text,
    SlotKindV2.phone,
    SlotKindV2.saturday_morning,
    SlotKindV2.darkness_level,
    SlotKindV2.geek_out_on,
)
"""Phase 1 slot ordering per FR-006.

Length MUST equal ``PHASE_1_REQUIRED_SLOTS`` (11). Order MUST be
DAG-respecting: dependencies declared in ``SLOT_DEPENDENCIES`` must
appear earlier in this tuple than the slot that depends on them.
``test_router_v2.py::test_required_order_respects_dag`` enforces this.
"""


def pick_next_target(state: WizardSlotsV2) -> SlotKindV2 | None:
    """Return the next Phase 1 slot to ask, or ``None`` when complete.

    Walks ``REQUIRED_ORDER`` in declaration order and returns the first
    slot that is unfilled AND not filtered out by conditional logic.
    Returns ``None`` when every required slot is filled (caller emits
    Phase 2 transition).

    Conditional skip:
      - ``phone`` is skipped when the user has already chosen
        ``voice_or_text == "text"`` (no phone needed for text-only flow).

    Determinism: same input ``state`` always returns the same output;
    no LLM, no randomness, no time-of-day branching.
    """
    for slot in REQUIRED_ORDER:
        if _should_skip(slot, state):
            continue
        if getattr(state, slot.value) is None:
            return slot
    return None


def _should_skip(slot: SlotKindV2, state: WizardSlotsV2) -> bool:
    """Conditional-skip predicate for FR-006 / FR-007.

    Currently only ``phone`` is conditional — skipped when
    ``voice_or_text == "text"``. Extend here if future slots add
    conditional logic.
    """
    if slot is SlotKindV2.phone:
        vot = state.voice_or_text
        if isinstance(vot, dict) and vot.get("voice_or_text") == "text":
            return True
    return False


def dag_invalidate(
    state: WizardSlotsV2, edited_slot: str
) -> tuple[WizardSlotsV2, list[str]]:
    """Apply FR-007 DAG invalidation for a back-edit on ``edited_slot``.

    Returns ``(new_state, invalidated)``:
      - ``new_state`` is a new ``WizardSlotsV2`` with downstream filled
        slots null-ed out.
      - ``invalidated`` is the list of slot names that were null-ed out.

    The caller is responsible for the user-facing confirmation modal
    BEFORE invoking this helper (per FR-007 step 1). This helper
    performs state mutation only.

    Example::

        edited = "city"
        new_slots, invalidated = dag_invalidate(slots, edited)
        # invalidated == ["hangouts_personalized"]   if hangouts was filled
    """
    if edited_slot not in SLOT_DEPENDENCIES:
        # Unknown slot — no-op rather than raise; the caller may pass
        # arbitrary strings during back-edit replay.
        return state, []
    return state.invalidate_dependents(edited_slot)


__all__ = [
    "REQUIRED_ORDER",
    "dag_invalidate",
    "pick_next_target",
]
