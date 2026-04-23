"""Reconstruct cumulative WizardSlots from a JSONB onboarding_profile.

Implements AC-11d.10: ``build_state_from_conversation`` loads the user's
``onboarding_profile`` JSONB and reconstructs the cumulative ``WizardSlots``
by applying:

1. ``elided_extracted`` FIRST — the accumulated baseline from elided turns.
2. Live ``conversation`` turns in order — newer extractions override older
   elided values for the same slot (last-write-wins per slot key).

This ordering guarantees that the most recent user intent always wins while
preserving slot signals that were elided by ``conversation_persistence.py``
when the cap (``CONVERSATION_TURN_CAP = 100``) was hit.

Extraction dict formats
-----------------------
Two formats exist in the JSONB depending on whether the turn was written by
the current codebase or a prior version:

- **Kind-discriminated** (current portal_onboarding.py format):
  ``{"kind": "phone", "confidence": 0.97, "phone_preference": "text", ...}``
  The ``kind`` key identifies the slot; the whole dict is slot data.

- **Slot-keyed** (plan-v2.md target format, used in test fixtures):
  ``{"location": {"city": "Berlin"}, "scene": {"scene": "techno"}}``
  The key IS the slot name; the value is slot data.

``build_state_from_conversation`` handles both formats transparently.

``elided_extracted`` produced by ``conversation_persistence.py`` (line 69-70)
is a flat merge of all extracted dicts — it inherits the kind-discriminated
format. The ``kind`` key in ``elided_extracted`` identifies the slot type.

Performance budget: ``RECONSTRUCTION_BUDGET_MS`` (10ms). The function is
synchronous and O(n) in turn count. The p95 latency gate is enforced in
``tests/agents/onboarding/test_state_reconstruction_perf.py`` (T9).

``RECONSTRUCTION_BUDGET_MS: Final[int] = 10``
Current value: 10ms (Spec 214 FR-11d, tasks-v2.md §T8).
Prior values: N/A — new constant.
Rationale: reconstruction runs on every POST /converse; 10ms is the budget
that keeps end-to-end p95 under the 200ms tech-spec ceiling.
"""

from __future__ import annotations

from typing import Any, Final

from nikita.agents.onboarding.state import SlotDelta, WizardSlots

# ---------------------------------------------------------------------------
# Tuning constant (regression guard — tuning-constants.md)
# ---------------------------------------------------------------------------

RECONSTRUCTION_BUDGET_MS: Final[int] = 10
"""Soft performance budget for build_state_from_conversation (milliseconds).

Current value: 10ms (Spec 214 FR-11d, tasks-v2.md §T8).
Prior values: N/A — introduced here.

Rationale: reconstruction is synchronous and runs inside every POST /converse
request; 10ms headroom keeps the p95 end-to-end under the 200ms ceiling.
Enforced as a p95 assertion in test_state_reconstruction_perf.py (T9).
"""

# Canonical slot names — keep in sync with WizardSlots fields and TOTAL_SLOTS.
_SLOT_NAMES = frozenset(
    {"location", "scene", "darkness", "identity", "backstory", "phone"}
)


def _apply_extracted_dict(
    slots: WizardSlots, extracted: dict[str, Any]
) -> WizardSlots:
    """Apply one extracted dict to slots, handling both storage formats.

    Format 1 — kind-discriminated (current storage from portal_onboarding.py):
        {"kind": "phone", "confidence": 0.97, "phone_preference": "text", "phone": null}
        The "kind" key identifies the slot; the whole dict is stored as slot data.

    Format 2 — slot-keyed (plan-v2.md target / test fixtures):
        {"location": {"city": "Berlin"}, "scene": {"scene": "techno"}}
        Each key IS a slot name; the value is the slot data dict.

    Detection: if "kind" is present and its value is a known slot name,
    treat as format 1.  Otherwise look for slot-name keys (format 2).
    """
    kind = extracted.get("kind")
    if isinstance(kind, str) and kind in _SLOT_NAMES:
        # Format 1: kind-discriminated (existing storage format)
        slots = slots.apply(
            SlotDelta(kind=kind, data=extracted)  # type: ignore[arg-type]
        )
    else:
        # Format 2: slot-keyed (plan-v2.md target / test fixtures)
        for slot_name, slot_data in extracted.items():
            if slot_name in _SLOT_NAMES and isinstance(slot_data, dict):
                slots = slots.apply(
                    SlotDelta(kind=slot_name, data=slot_data)  # type: ignore[arg-type]
                )
    return slots


def build_state_from_conversation(
    profile: dict[str, Any],
) -> WizardSlots:
    """Reconstruct WizardSlots from a user's onboarding_profile JSONB.

    Args:
        profile: The ``users.onboarding_profile`` dict.  Expected keys:
            - ``elided_extracted``: dict — slots accumulated from elided turns
              by conversation_persistence.py.  Supports both kind-discriminated
              and slot-keyed formats (see module docstring).
            - ``conversation``: list[Turn dict] — live turns, each optionally
              carrying an ``extracted`` dict.

    Returns:
        WizardSlots with cumulative slots applied:
        elided_extracted baseline → live turns in order (last-write-wins).
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
