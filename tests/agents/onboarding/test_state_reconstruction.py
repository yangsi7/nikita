"""Tests for nikita.agents.onboarding.state_reconstruction (13-slot schema).

Covers build_state_from_conversation: empty profile → empty slots; turns
applied in order; elided_extracted baseline; format-1 (kind-keyed) and
format-2 (slot-keyed) extracted dicts; pre-216 legacy slot names dropped.
"""

from __future__ import annotations

import pytest

from nikita.agents.onboarding.state import WizardSlots
from nikita.agents.onboarding.state_reconstruction import build_state_from_conversation


class TestBuildState:
    def test_empty_profile_returns_empty(self):
        slots = build_state_from_conversation({})
        assert slots == WizardSlots()

    def test_kind_keyed_format_basic(self):
        profile = {
            "conversation": [
                {"extracted": {"kind": "city", "city": "Berlin"}},
                {"extracted": {"kind": "age", "age": 30}},
            ]
        }
        slots = build_state_from_conversation(profile)
        assert slots.city == {"kind": "city", "city": "Berlin"}
        assert slots.age == {"kind": "age", "age": 30}

    def test_slot_keyed_format_basic(self):
        profile = {
            "conversation": [
                {"extracted": {"city": {"city": "Tokyo"}}},
                {"extracted": {"display_name": {"display_name": "Sam"}}},
            ]
        }
        slots = build_state_from_conversation(profile)
        assert slots.city == {"city": "Tokyo"}
        assert slots.display_name == {"display_name": "Sam"}

    def test_elided_extracted_applied_first(self):
        profile = {
            "elided_extracted": {"city": {"city": "Paris"}},
            "conversation": [
                {"extracted": {"city": {"city": "Berlin"}}},
            ],
        }
        slots = build_state_from_conversation(profile)
        # Live turn wins over elided baseline
        assert slots.city == {"city": "Berlin"}

    def test_legacy_slot_names_silently_dropped(self):
        """Pre-216 slot names ('location', 'scene', 'darkness', 'identity',
        'backstory') in JSONB are dropped — wizard re-collects."""
        profile = {
            "conversation": [
                {"extracted": {"location": {"city": "old"}}},
                {"extracted": {"scene": {"scene": "techno"}}},
            ]
        }
        slots = build_state_from_conversation(profile)
        # No fields filled; the legacy keys aren't in the new vocabulary
        assert slots.missing == [m.value for m in __import__(
            "nikita.agents.onboarding.question_registry",
            fromlist=["SlotKind"]
        ).SlotKind]

    def test_no_extraction_field_skipped(self):
        profile = {
            "conversation": [
                {"extracted": None},
                {"extracted": {}},
                {"role": "user", "content": "hi"},
            ]
        }
        slots = build_state_from_conversation(profile)
        assert slots == WizardSlots()
