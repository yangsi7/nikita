"""Reconstruct cumulative WizardSlots from a JSONB onboarding_profile.

Loads the user's ``onboarding_profile`` JSONB and reconstructs the
cumulative ``WizardSlots`` by applying:

1. ``elided_extracted`` FIRST — the accumulated baseline from elided turns.
2. Live ``conversation`` turns in order — newer extractions override older
   elided values for the same slot (last-write-wins per slot key).

Spec 216-B1+B2 update: the slot vocabulary is the 13 SlotKind values
(display_name, age, occupation, city, darkness_level, primary_hobbies,
saturday_morning, geek_out_on, together_we_could, same_weird_if,
voice_tone_pref, backstory_pick, phone). Old slot keys
(location/scene/darkness/identity/backstory) from prior schemas are
dropped silently — pre-216 JSONB rows resolve to empty WizardSlots which
the wizard re-collects on the next conversation.

Two extraction-dict formats are supported in JSONB:

- **Kind-discriminated** (current portal_onboarding format):
  ``{"kind": "phone", "phone": "+14155552671", ...}`` — the ``kind`` key
  identifies the slot; the whole dict is stored as slot data.

- **Slot-keyed** (test-fixture / legacy format):
  ``{"city": {"city": "Berlin"}, "age": {"age": 28}}`` — each top-level
  key IS a slot name; the value is the slot data dict.

``build_state_from_conversation`` handles both formats transparently.

Performance budget: ``RECONSTRUCTION_BUDGET_MS`` (10ms). The function is
synchronous and O(n) in turn count.
"""

from __future__ import annotations

from typing import Any, Final

from nikita.agents.onboarding.question_registry import SlotKind
from nikita.agents.onboarding.state import SlotDelta, WizardSlots

# ---------------------------------------------------------------------------
# Tuning constant (regression guard — tuning-constants.md)
# ---------------------------------------------------------------------------

RECONSTRUCTION_BUDGET_MS: Final[int] = 10
"""Soft performance budget for build_state_from_conversation (milliseconds).

Current value: 10ms (Spec 214 FR-11d, tasks-v2.md §T8). Carried over to
Spec 216-B1+B2 unchanged — reconstruction surface is unchanged in shape,
only the slot vocabulary changes.

Rationale: reconstruction runs inside every onboarding turn; 10ms headroom
keeps p95 end-to-end under the 200ms ceiling.
"""

# Canonical slot names — derived from SlotKind (single source of truth).
_SLOT_NAMES: frozenset[str] = frozenset(m.value for m in SlotKind)


def _apply_extracted_dict(
    slots: WizardSlots, extracted: dict[str, Any]
) -> WizardSlots:
    """Apply one extracted dict to slots, handling both storage formats.

    Format 1 — kind-discriminated (current storage):
        {"kind": "phone", "phone": "+14155552671", ...}
        The "kind" key identifies the slot; the whole dict is stored
        as slot data.

    Format 2 — slot-keyed (test fixtures / legacy):
        {"city": {"city": "Berlin"}, "age": {"age": 28}}
        Each top-level key IS a slot name; value is the slot data dict.

    Detection: if "kind" is present and its value is a known SlotKind,
    treat as format 1. Otherwise look for SlotKind keys (format 2).
    Unknown slot names (e.g. legacy 'location'/'scene') are silently
    skipped — the wizard re-collects them.
    """
    kind = extracted.get("kind")
    if isinstance(kind, str) and kind in _SLOT_NAMES:
        # Format 1: kind-discriminated
        slots = slots.apply(SlotDelta(kind=kind, data=extracted))
    else:
        # Format 2: slot-keyed
        for slot_name, slot_data in extracted.items():
            if slot_name in _SLOT_NAMES and isinstance(slot_data, dict):
                slots = slots.apply(SlotDelta(kind=slot_name, data=slot_data))
    return slots


def build_state_from_conversation(
    profile: dict[str, Any],
) -> WizardSlots:
    """Reconstruct WizardSlots from a user's onboarding_profile JSONB.

    Args:
        profile: The ``users.onboarding_profile`` dict. Expected keys:
            - ``elided_extracted``: dict — slots accumulated from elided turns.
              Supports both kind-discriminated and slot-keyed formats.
            - ``conversation``: list[Turn dict] — live turns, each optionally
              carrying an ``extracted`` dict.

    Returns:
        WizardSlots with cumulative slots applied. Pre-216 slot names
        ('location', 'scene', etc.) are silently dropped; the new wizard
        re-collects from scratch.
    """
    slots = WizardSlots()

    # Step 1: apply elided_extracted as the baseline.
    elided: dict[str, Any] = profile.get("elided_extracted") or {}
    if elided:
        slots = _apply_extracted_dict(slots, elided)

    # Step 2: apply live conversation turns in order (overrides elided).
    conversation: list[dict[str, Any]] = profile.get("conversation") or []
    for turn in conversation:
        extracted: dict[str, Any] | None = turn.get("extracted")
        if not extracted:
            continue
        slots = _apply_extracted_dict(slots, extracted)

    return slots


__all__ = [
    "RECONSTRUCTION_BUDGET_MS",
    "build_state_from_conversation",
]
