"""B1.1 / B1.12 — Cumulative state monotonicity (Agentic-Flow mandatory test #1).

Tests that ``WizardSlots`` accumulates 13 slots monotonically: progress_pct
never regresses across a ≥13-turn fixture. ``model_copy`` semantics enforce
immutability — each ``apply()`` returns a new WizardSlots.

Hard Rule §1 (cumulative state) + Hard Rule §4 (monotonic progress).
"""

from __future__ import annotations

import pytest


def _import_state():
    """Deferred import so collection succeeds even before module is rewritten."""
    from nikita.agents.onboarding.state import (  # noqa: PLC0415
        TOTAL_SLOTS,
        SlotDelta,
        WizardSlots,
    )
    return TOTAL_SLOTS, SlotDelta, WizardSlots


# Canonical 13-slot fill sequence — one per question_registry entry.
# Each tuple = (slot_kind, data_payload).
_THIRTEEN_TURN_FIXTURE: list[tuple[str, dict]] = [
    ("display_name", {"display_name": "Sam"}),
    ("age", {"age": 28}),
    ("occupation", {"occupation": "designer"}),
    ("city", {"city": "Berlin"}),
    ("darkness_level", {"darkness_level": 3}),
    ("primary_hobbies", {"primary_hobbies": ["reading", "running"]}),
    ("saturday_morning", {"saturday_morning": "long walk + coffee"}),
    ("geek_out_on", {"geek_out_on": "ergonomic keyboards"}),
    ("together_we_could", {"together_we_could": "drive to nowhere"}),
    ("same_weird_if", {"same_weird_if": "we both reread the same book"}),
    ("voice_tone_pref", {"voice_tone_pref": "text"}),
    ("backstory_pick", {"backstory_pick": {"chosen_option_id": "abc123def456", "cache_key": "berlin|techno|3"}}),
    ("phone", {"phone": "+14155552671"}),
]


class TestCumulativeStateMonotonicity:
    def test_progress_never_decreases_across_thirteen_turns(self):
        """Progress_pct is monotonic non-decreasing (Agentic-Flow mandatory)."""
        TOTAL_SLOTS, SlotDelta, WizardSlots = _import_state()
        slots = WizardSlots()
        progresses: list[int] = [slots.progress_pct]
        for kind, data in _THIRTEEN_TURN_FIXTURE:
            slots = slots.apply(SlotDelta(kind=kind, data=data))
            progresses.append(slots.progress_pct)
        # 14 readings (initial + 13 turns); each must be >= the prior reading.
        for i in range(1, len(progresses)):
            assert progresses[i] >= progresses[i - 1], (
                f"progress regressed at turn {i}: {progresses[i-1]} -> {progresses[i]}"
            )

    def test_total_slots_constant_is_thirteen(self):
        """TOTAL_SLOTS regression guard — must equal 13 (B1.beta lock-in)."""
        TOTAL_SLOTS, _, _ = _import_state()
        assert TOTAL_SLOTS == 13, (
            f"TOTAL_SLOTS drifted from 13 (got {TOTAL_SLOTS}). "
            "B1.beta lock-in: 13 slots (12 visual screens, identity split into "
            "display_name+age+occupation). Update FinalForm + this test together."
        )

    def test_apply_is_immutable_original_unchanged(self):
        """model_copy semantics: original WizardSlots is unchanged after apply."""
        _, SlotDelta, WizardSlots = _import_state()
        slots = WizardSlots()
        delta = SlotDelta(kind="city", data={"city": "Paris"})
        slots2 = slots.apply(delta)
        # original must be unmodified
        assert slots.city is None
        assert slots2.city is not None

    def test_progress_reaches_100_after_all_13_slots_filled(self):
        """After all 13 slots applied, progress_pct == 100."""
        _, SlotDelta, WizardSlots = _import_state()
        slots = WizardSlots()
        for kind, data in _THIRTEEN_TURN_FIXTURE:
            slots = slots.apply(SlotDelta(kind=kind, data=data))
        assert slots.progress_pct == 100

    def test_no_extraction_does_not_advance_progress(self):
        """A no_extraction delta leaves progress unchanged."""
        _, SlotDelta, WizardSlots = _import_state()
        slots = WizardSlots()
        slots = slots.apply(SlotDelta(kind="city", data={"city": "Tokyo"}))
        before = slots.progress_pct
        slots = slots.apply(SlotDelta(kind="no_extraction", data={}))
        assert slots.progress_pct == before
