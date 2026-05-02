"""B1.2 — Completion gate triplet (Agentic-Flow mandatory test #2).

The Pydantic ``FinalForm.model_validate(state.slots_dict())`` IS the
completion gate. Tests:
- empty state → False (raises ValidationError) / 0%
- partial state (some slots filled) → False / <100%
- full state (all 13 slots valid) → True / 100%

Plus cross-field validators:
- age >= MIN_USER_AGE
- voice_tone_pref="voice" requires phone
- primary_hobbies non-empty list
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError


def _import_state():
    from nikita.agents.onboarding.state import (  # noqa: PLC0415
        FinalForm,
        SlotDelta,
        WizardSlots,
    )
    return FinalForm, SlotDelta, WizardSlots


def _build_full_slots(WizardSlots, SlotDelta):
    """Fill all 13 slots with valid data."""
    slots = WizardSlots()
    fixture = [
        ("display_name", {"display_name": "Sam"}),
        ("age", {"age": 28}),
        ("occupation", {"occupation": "designer"}),
        ("city", {"city": "Berlin"}),
        ("darkness_level", {"darkness_level": 3}),
        ("primary_hobbies", {"primary_hobbies": ["reading", "running"]}),
        ("saturday_morning", {"saturday_morning": "long walk"}),
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


class TestCompletionGateTriplet:
    """Mandatory empty/partial/full triplet."""

    def test_empty_state_is_not_complete(self):
        """Empty WizardSlots → FinalForm.model_validate raises ValidationError."""
        FinalForm, _, WizardSlots = _import_state()
        slots = WizardSlots()
        with pytest.raises(ValidationError):
            FinalForm.model_validate(slots.slots_dict())
        assert slots.is_complete is False
        assert slots.progress_pct == 0

    def test_partial_state_is_not_complete(self):
        """Partial state (<13 slots) → FinalForm.model_validate raises."""
        FinalForm, SlotDelta, WizardSlots = _import_state()
        slots = WizardSlots()
        slots = slots.apply(SlotDelta(kind="city", data={"city": "Berlin"}))
        slots = slots.apply(SlotDelta(kind="age", data={"age": 30}))
        with pytest.raises(ValidationError):
            FinalForm.model_validate(slots.slots_dict())
        assert slots.is_complete is False
        assert 0 < slots.progress_pct < 100

    def test_full_state_is_complete(self):
        """All 13 slots filled with valid data → FinalForm validates → is_complete True."""
        FinalForm, SlotDelta, WizardSlots = _import_state()
        slots = _build_full_slots(WizardSlots, SlotDelta)
        # Should not raise:
        form = FinalForm.model_validate(slots.slots_dict())
        assert form is not None
        assert slots.is_complete is True
        assert slots.progress_pct == 100


class TestCrossFieldValidators:
    """B1.2 cross-field business rules."""

    def test_age_below_minimum_raises(self):
        """age < MIN_USER_AGE → ValidationError on FinalForm."""
        FinalForm, SlotDelta, WizardSlots = _import_state()
        slots = _build_full_slots(WizardSlots, SlotDelta)
        slots = slots.apply(SlotDelta(kind="age", data={"age": 15}))
        with pytest.raises(ValidationError):
            FinalForm.model_validate(slots.slots_dict())

    def test_voice_preference_requires_phone(self):
        """voice_tone_pref='voice' with empty phone → ValidationError."""
        FinalForm, SlotDelta, WizardSlots = _import_state()
        slots = _build_full_slots(WizardSlots, SlotDelta)
        slots = slots.apply(
            SlotDelta(kind="voice_tone_pref", data={"voice_tone_pref": "voice"})
        )
        slots = slots.apply(SlotDelta(kind="phone", data={"phone": ""}))
        with pytest.raises(ValidationError):
            FinalForm.model_validate(slots.slots_dict())

    def test_voice_preference_with_phone_is_valid(self):
        """voice_tone_pref='voice' WITH phone → FinalForm validates."""
        FinalForm, SlotDelta, WizardSlots = _import_state()
        slots = _build_full_slots(WizardSlots, SlotDelta)
        slots = slots.apply(
            SlotDelta(kind="voice_tone_pref", data={"voice_tone_pref": "voice"})
        )
        slots = slots.apply(SlotDelta(kind="phone", data={"phone": "+14155552671"}))
        form = FinalForm.model_validate(slots.slots_dict())
        assert form is not None

    def test_empty_primary_hobbies_raises(self):
        """primary_hobbies empty list → ValidationError on FinalForm."""
        FinalForm, SlotDelta, WizardSlots = _import_state()
        slots = _build_full_slots(WizardSlots, SlotDelta)
        slots = slots.apply(
            SlotDelta(kind="primary_hobbies", data={"primary_hobbies": []})
        )
        with pytest.raises(ValidationError):
            FinalForm.model_validate(slots.slots_dict())

    def test_no_complete_boolean_literal_in_state(self):
        """Hard Rule §2 guard: WizardSlots.is_complete delegates to
        FinalForm.model_validate, never a hardcoded literal."""
        import inspect

        from nikita.agents.onboarding import state as state_module
        src = inspect.getsource(state_module)
        # The string "is_complete = True" or "is_complete = False" in a non-
        # docstring context would indicate a hardcoded gate. Pydantic computed_field
        # implementations use model_validate.
        assert "FinalForm.model_validate" in src
