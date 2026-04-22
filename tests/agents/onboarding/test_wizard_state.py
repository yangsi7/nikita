"""Tests for nikita.agents.onboarding.state — WizardSlots, FinalForm, SlotDelta.

AC coverage:
- AC-11d.1: Cumulative server-side state — WizardSlots merges via model_copy,
  progress_pct is a computed_field, never regresses across turns.
- AC-11d.3: FinalForm completion gate — empty/partial/full triplet;
  FinalForm.model_validate raises ValidationError on incomplete state.

Agentic-Flow mandatory test classes (testing.md § "Agentic-Flow Test
Requirements"):
1. Cumulative-state monotonicity — ≥3 turns, progress never regresses.
2. Completion-gate triplet — empty → False/0%, partial → False/<100%,
   full → True/100%.
3. Mock-LLM-emits-wrong-tool recovery is covered in test_regex_fallback.py
   (AC-11d.4, T5).

Tuning-constant regression guard (tuning-constants.md): TOTAL_SLOTS == 6.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# Import guards — these imports must FAIL before T2 GREEN ships state.py.
# ---------------------------------------------------------------------------


def _import_state():
    """Deferred import so collection succeeds even before module exists."""
    from nikita.agents.onboarding.state import (  # noqa: PLC0415
        FinalForm,
        SlotDelta,
        TOTAL_SLOTS,
        WizardSlots,
    )
    return FinalForm, SlotDelta, TOTAL_SLOTS, WizardSlots


# ---------------------------------------------------------------------------
# Tuning-constant regression guard (tuning-constants.md, GH #spec-214)
# ---------------------------------------------------------------------------


class TestTuningConstants:
    def test_total_slots_constant_is_six(self):
        """TOTAL_SLOTS must equal 6 — one per extraction schema.

        Regression guard: silent drift in this value cascades to progress_pct
        arithmetic, FinalForm gate, and frontend progress bar.
        Current value: 6 (set in Spec 214 FR-11d, tasks-v2.md §T2).
        """
        _, _, TOTAL_SLOTS, _ = _import_state()
        assert TOTAL_SLOTS == 6, (
            "TOTAL_SLOTS drifted from 6. "
            "Update FinalForm required fields AND this test intentionally."
        )


# ---------------------------------------------------------------------------
# WizardSlots — cumulative merge + computed fields
# ---------------------------------------------------------------------------


class TestWizardSlots:
    def test_empty_slots_progress_is_zero(self):
        """Empty WizardSlots has progress_pct == 0."""
        _, _, _, WizardSlots = _import_state()
        slots = WizardSlots()
        assert slots.progress_pct == 0

    def test_empty_slots_missing_is_all_slots(self):
        """Empty WizardSlots has all slot names in .missing."""
        _, _, TOTAL_SLOTS, WizardSlots = _import_state()
        slots = WizardSlots()
        assert len(slots.missing) == TOTAL_SLOTS

    def test_single_slot_fill_progress_increases(self):
        """Filling one slot raises progress_pct above 0."""
        _, SlotDelta, _, WizardSlots = _import_state()
        slots = WizardSlots()
        delta = SlotDelta(kind="location", data={"city": "Berlin"})
        slots2 = slots.apply(delta)
        assert slots2.progress_pct > 0

    def test_merge_is_immutable_original_unchanged(self):
        """model_copy semantics: original WizardSlots is unchanged after apply."""
        _, SlotDelta, _, WizardSlots = _import_state()
        slots = WizardSlots()
        delta = SlotDelta(kind="location", data={"city": "Paris"})
        slots2 = slots.apply(delta)
        # original must be unmodified
        assert slots.location is None
        assert slots2.location is not None

    def test_progress_pct_monotonic_across_three_turns(self):
        """Agentic-Flow mandatory: progress never regresses over ≥3 turns.

        Turn 1: location extracted.
        Turn 2: scene extracted.
        Turn 3: darkness extracted.
        Progress must be non-decreasing at each step.
        """
        _, SlotDelta, _, WizardSlots = _import_state()
        slots = WizardSlots()
        progress_history = [slots.progress_pct]

        # Turn 1: location
        d1 = SlotDelta(kind="location", data={"city": "Tokyo"})
        slots = slots.apply(d1)
        progress_history.append(slots.progress_pct)

        # Turn 2: scene
        d2 = SlotDelta(kind="scene", data={"scene": "techno"})
        slots = slots.apply(d2)
        progress_history.append(slots.progress_pct)

        # Turn 3: darkness
        d3 = SlotDelta(kind="darkness", data={"drug_tolerance": 3})
        slots = slots.apply(d3)
        progress_history.append(slots.progress_pct)

        for i in range(1, len(progress_history)):
            assert progress_history[i] >= progress_history[i - 1], (
                f"progress regressed at turn {i}: "
                f"{progress_history[i - 1]} → {progress_history[i]}"
            )

    def test_progress_pct_monotonic_no_extraction_turn(self):
        """NoExtraction turns must not decrease progress_pct.

        This catches the per-turn snapshot anti-pattern where
        a turn with no extraction resets progress to 0.
        """
        _, SlotDelta, _, WizardSlots = _import_state()
        slots = WizardSlots()

        # Fill location first
        slots = slots.apply(SlotDelta(kind="location", data={"city": "NYC"}))
        before = slots.progress_pct

        # NoExtraction turn — progress must NOT drop
        slots = slots.apply(SlotDelta(kind="no_extraction", data={}))
        after = slots.progress_pct

        assert after >= before, (
            "progress dropped on no_extraction turn — "
            "this is the per-turn snapshot anti-pattern"
        )

    def test_full_slots_progress_is_100(self):
        """All 6 slots filled → progress_pct == 100."""
        _, SlotDelta, _, WizardSlots = _import_state()
        slots = WizardSlots()
        deltas = [
            SlotDelta(kind="location", data={"city": "Berlin"}),
            SlotDelta(kind="scene", data={"scene": "art"}),
            SlotDelta(kind="darkness", data={"drug_tolerance": 2}),
            SlotDelta(
                kind="identity",
                data={"name": "Alex", "age": 25, "occupation": "dev"},
            ),
            SlotDelta(
                kind="backstory",
                data={
                    "chosen_option_id": "aabbccddeeff",
                    "cache_key": "berlin|art|2",
                },
            ),
            SlotDelta(
                kind="phone",
                data={"phone_preference": "text", "phone": None},
            ),
        ]
        for delta in deltas:
            slots = slots.apply(delta)

        assert slots.progress_pct == 100
        assert len(slots.missing) == 0

    def test_duplicate_slot_does_not_increase_progress_beyond_100(self):
        """Applying the same slot twice must not push progress above 100."""
        _, SlotDelta, _, WizardSlots = _import_state()
        slots = WizardSlots()
        d = SlotDelta(kind="location", data={"city": "London"})
        slots = slots.apply(d)
        first_progress = slots.progress_pct
        slots = slots.apply(d)
        second_progress = slots.progress_pct
        assert second_progress == first_progress
        assert second_progress <= 100

    def test_slots_dict_contains_filled_slots(self):
        """slots_dict() returns a plain dict with non-None slot values."""
        _, SlotDelta, _, WizardSlots = _import_state()
        slots = WizardSlots()
        slots = slots.apply(SlotDelta(kind="location", data={"city": "Madrid"}))
        d = slots.slots_dict()
        assert isinstance(d, dict)
        assert "location" in d
        assert d["location"]["city"] == "Madrid"


# ---------------------------------------------------------------------------
# FinalForm — completion gate (Agentic-Flow mandatory: completion-gate triplet)
# ---------------------------------------------------------------------------


class TestFinalForm:
    def test_empty_state_raises_validation_error(self):
        """Completion-gate triplet — empty state: FinalForm raises ValidationError."""
        FinalForm, _, _, WizardSlots = _import_state()
        slots = WizardSlots()
        with pytest.raises(ValidationError):
            FinalForm.model_validate(slots.slots_dict())

    def test_partial_state_raises_validation_error(self):
        """Completion-gate triplet — partial state: FinalForm raises ValidationError."""
        FinalForm, SlotDelta, _, WizardSlots = _import_state()
        slots = WizardSlots()
        slots = slots.apply(SlotDelta(kind="location", data={"city": "Vienna"}))
        slots = slots.apply(SlotDelta(kind="scene", data={"scene": "food"}))
        with pytest.raises(ValidationError):
            FinalForm.model_validate(slots.slots_dict())

    def test_full_state_validates_successfully(self):
        """Completion-gate triplet — full state: FinalForm.model_validate succeeds."""
        FinalForm, SlotDelta, _, WizardSlots = _import_state()
        slots = WizardSlots()
        slots = slots.apply(
            SlotDelta(kind="location", data={"city": "Berlin"})
        )
        slots = slots.apply(
            SlotDelta(kind="scene", data={"scene": "techno"})
        )
        slots = slots.apply(
            SlotDelta(kind="darkness", data={"drug_tolerance": 4})
        )
        slots = slots.apply(
            SlotDelta(
                kind="identity",
                data={"name": "Sam", "age": 28, "occupation": "artist"},
            )
        )
        slots = slots.apply(
            SlotDelta(
                kind="backstory",
                data={
                    "chosen_option_id": "aabbccddeeff",
                    "cache_key": "berlin|techno|4",
                },
            )
        )
        slots = slots.apply(
            SlotDelta(
                kind="phone",
                data={"phone_preference": "text", "phone": None},
            )
        )
        # Must not raise
        form = FinalForm.model_validate(slots.slots_dict())
        assert form is not None

    def test_conversation_complete_false_for_empty(self):
        """Completion gate returns False for empty state — no hardcoded bool."""
        FinalForm, _, _, WizardSlots = _import_state()
        slots = WizardSlots()
        try:
            FinalForm.model_validate(slots.slots_dict())
            complete = True
        except ValidationError:
            complete = False
        assert complete is False

    def test_conversation_complete_true_for_full(self):
        """Completion gate returns True for all slots filled."""
        FinalForm, SlotDelta, _, WizardSlots = _import_state()
        slots = WizardSlots()
        for delta in [
            SlotDelta(kind="location", data={"city": "Oslo"}),
            SlotDelta(kind="scene", data={"scene": "nature"}),
            SlotDelta(kind="darkness", data={"drug_tolerance": 1}),
            SlotDelta(
                kind="identity",
                data={"name": "Jo", "age": 22, "occupation": "nurse"},
            ),
            SlotDelta(
                kind="backstory",
                data={
                    "chosen_option_id": "112233445566",
                    "cache_key": "oslo|nature|1",
                },
            ),
            SlotDelta(
                kind="phone",
                data={"phone_preference": "text", "phone": None},
            ),
        ]:
            slots = slots.apply(delta)

        try:
            FinalForm.model_validate(slots.slots_dict())
            complete = True
        except ValidationError:
            complete = False
        assert complete is True

    def test_age_under_18_is_rejected_by_final_form(self):
        """FinalForm must enforce age >= 18 (AC-11d.9 cross-field validation)."""
        FinalForm, SlotDelta, _, WizardSlots = _import_state()
        slots = WizardSlots()
        # Inject raw dict with underage identity bypassing IdentityExtraction
        # to test FinalForm's own cross-field validator
        raw = {
            "location": {"city": "NYC"},
            "scene": {"scene": "techno"},
            "darkness": {"drug_tolerance": 2},
            "identity": {"name": "Kid", "age": 16, "occupation": "student"},
            "backstory": {
                "chosen_option_id": "aabbccddeeff",
                "cache_key": "nyc|techno|2",
            },
            "phone": {"phone_preference": "text", "phone": None},
        }
        with pytest.raises(ValidationError):
            FinalForm.model_validate(raw)


# ---------------------------------------------------------------------------
# SlotDelta — input model validation
# ---------------------------------------------------------------------------


class TestSlotDelta:
    def test_slot_delta_requires_kind(self):
        """SlotDelta must have a kind field — wrong kind raises ValidationError."""
        _, SlotDelta, _, _ = _import_state()
        with pytest.raises((ValidationError, TypeError)):
            SlotDelta(data={"city": "Rome"})  # missing kind

    def test_slot_delta_unknown_kind_rejected(self):
        """SlotDelta with unknown kind must be rejected at construction."""
        _, SlotDelta, _, _ = _import_state()
        with pytest.raises((ValidationError, ValueError)):
            SlotDelta(kind="TOTALLY_UNKNOWN", data={})

    def test_slot_delta_valid_kinds_accepted(self):
        """All 6 canonical slot kinds + no_extraction are accepted."""
        _, SlotDelta, _, _ = _import_state()
        valid_kinds = [
            "location",
            "scene",
            "darkness",
            "identity",
            "backstory",
            "phone",
            "no_extraction",
        ]
        for kind in valid_kinds:
            # Just check construction succeeds
            delta = SlotDelta(kind=kind, data={})
            assert delta.kind == kind
