"""Tests for nikita.agents.onboarding.state — 13-slot schema (Spec 216-B1+B2).

Covers: WizardSlots immutable apply, SlotDelta kind validation, FinalForm
cross-field validators, WizardState envelope.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from nikita.agents.onboarding.state import (
    FinalForm,
    SlotDelta,
    TOTAL_SLOTS,
    WizardSlots,
    WizardState,
)


def _full_slots() -> WizardSlots:
    """Build a WizardSlots with all 13 slots filled validly."""
    slots = WizardSlots()
    fixture = [
        ("display_name", {"display_name": "Sam"}),
        ("age", {"age": 28}),
        ("occupation", {"occupation": "designer"}),
        ("city", {"city": "Berlin"}),
        ("darkness_level", {"darkness_level": 3}),
        ("primary_hobbies", {"primary_hobbies": ["reading", "running"]}),
        ("saturday_morning", {"saturday_morning": "long walks"}),
        ("geek_out_on", {"geek_out_on": "keyboards"}),
        ("together_we_could", {"together_we_could": "drive somewhere"}),
        ("same_weird_if", {"same_weird_if": "same book twice"}),
        ("voice_tone_pref", {"voice_tone_pref": "text"}),
        ("backstory_pick", {"backstory_pick": {"chosen_option_id": "abc123def456", "cache_key": "berlin|techno|3"}}),
        ("phone", {"phone": "+14155552671"}),
    ]
    for kind, data in fixture:
        slots = slots.apply(SlotDelta(kind=kind, data=data))
    return slots


class TestSlotDelta:
    def test_valid_kinds_accepted(self):
        for kind in (
            "display_name", "age", "occupation", "city", "darkness_level",
            "primary_hobbies", "saturday_morning", "geek_out_on",
            "together_we_could", "same_weird_if", "voice_tone_pref",
            "backstory_pick", "phone", "no_extraction",
        ):
            d = SlotDelta(kind=kind, data={})
            assert d.kind == kind

    def test_invalid_kind_rejected(self):
        with pytest.raises(ValidationError):
            SlotDelta(kind="not_a_real_slot", data={})


class TestWizardSlotsBasics:
    def test_empty_slots_progress_zero(self):
        slots = WizardSlots()
        assert slots.progress_pct == 0
        assert len(slots.missing) == TOTAL_SLOTS

    def test_apply_no_extraction_unchanged(self):
        slots = WizardSlots()
        slots = slots.apply(SlotDelta(kind="city", data={"city": "X"}))
        before_missing = list(slots.missing)
        slots = slots.apply(SlotDelta(kind="no_extraction", data={}))
        assert list(slots.missing) == before_missing

    def test_apply_is_immutable(self):
        slots = WizardSlots()
        slots2 = slots.apply(SlotDelta(kind="city", data={"city": "Berlin"}))
        assert slots.city is None
        assert slots2.city == {"city": "Berlin"}

    def test_progress_increases_monotonically(self):
        slots = WizardSlots()
        prior = slots.progress_pct
        slots = slots.apply(SlotDelta(kind="city", data={"city": "X"}))
        assert slots.progress_pct >= prior

    def test_slots_dict_includes_only_filled(self):
        slots = WizardSlots()
        slots = slots.apply(SlotDelta(kind="city", data={"city": "Berlin"}))
        d = slots.slots_dict()
        assert d == {"city": {"city": "Berlin"}}

    def test_agent_context_dict_aliases_slots_dict(self):
        slots = WizardSlots()
        slots = slots.apply(SlotDelta(kind="age", data={"age": 30}))
        assert slots.agent_context_dict() == slots.slots_dict()


class TestFinalForm:
    def test_full_state_validates(self):
        slots = _full_slots()
        form = FinalForm.model_validate(slots.slots_dict())
        assert form is not None

    def test_partial_state_raises(self):
        slots = WizardSlots().apply(SlotDelta(kind="city", data={"city": "X"}))
        with pytest.raises(ValidationError):
            FinalForm.model_validate(slots.slots_dict())

    def test_voice_with_phone_validates(self):
        slots = _full_slots()
        slots = slots.apply(SlotDelta(kind="voice_tone_pref", data={"voice_tone_pref": "voice"}))
        slots = slots.apply(SlotDelta(kind="phone", data={"phone": "+14155552671"}))
        form = FinalForm.model_validate(slots.slots_dict())
        assert form is not None

    def test_voice_without_phone_raises(self):
        slots = _full_slots()
        slots = slots.apply(SlotDelta(kind="voice_tone_pref", data={"voice_tone_pref": "voice"}))
        slots = slots.apply(SlotDelta(kind="phone", data={"phone": ""}))
        with pytest.raises(ValidationError):
            FinalForm.model_validate(slots.slots_dict())


class TestWizardStateEnvelope:
    def test_default_is_not_complete(self):
        state = WizardState()
        assert state.is_complete is False

    def test_full_state_is_complete(self):
        state = WizardState(slots=_full_slots())
        assert state.is_complete is True
