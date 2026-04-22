"""Tests for nikita.agents.onboarding.state_reconstruction.

AC coverage:
- AC-11d.1: Cumulative state reconstruction — elided_extracted applied FIRST,
  live conversation overrides second (last-write-wins).
- AC-11d.10: build_state_from_conversation returns WizardSlots with all
  slots correctly reconstructed from the JSONB profile structure.

Scenarios:
1. Basic reconstruction — turns only, no elision.
2. Elided-first ordering — elided_extracted is baseline; live turns override.
3. Repeated-slot handling — same slot appears in both elided and live turns;
   live turn wins.
4. No-extraction turns — turns without extracted dict contribute nothing.
5. Empty profile — returns empty WizardSlots.
6. RECONSTRUCTION_BUDGET_MS constant regression guard.
"""

from __future__ import annotations

import pytest


def _import_reconstruction():
    from nikita.agents.onboarding.state_reconstruction import (  # noqa: PLC0415
        RECONSTRUCTION_BUDGET_MS,
        build_state_from_conversation,
    )
    return RECONSTRUCTION_BUDGET_MS, build_state_from_conversation


def _import_state():
    from nikita.agents.onboarding.state import WizardSlots  # noqa: PLC0415
    return WizardSlots


# ---------------------------------------------------------------------------
# RECONSTRUCTION_BUDGET_MS regression guard (tuning-constants.md)
# ---------------------------------------------------------------------------


class TestReconstructionBudget:
    def test_reconstruction_budget_ms_is_10(self):
        """RECONSTRUCTION_BUDGET_MS must equal 10ms.

        Current value: 10ms (Spec 214 FR-11d tasks-v2.md §T8).
        Regression guard — changing this silently breaks perf assertions in
        test_state_reconstruction_perf.py (T9).
        """
        RECONSTRUCTION_BUDGET_MS, _ = _import_reconstruction()
        assert RECONSTRUCTION_BUDGET_MS == 10


# ---------------------------------------------------------------------------
# build_state_from_conversation — core reconstruction logic
# ---------------------------------------------------------------------------


class TestBuildStateFromConversation:
    def test_empty_profile_returns_empty_slots(self):
        """Empty profile dict → WizardSlots with all slots None."""
        _, build = _import_reconstruction()
        WizardSlots = _import_state()
        profile: dict = {}
        slots = build(profile)
        assert isinstance(slots, WizardSlots)
        assert slots.progress_pct == 0
        assert len(slots.missing) == 6

    def test_basic_reconstruction_from_turns_only(self):
        """Turns with extracted dicts are merged into WizardSlots."""
        _, build = _import_reconstruction()
        profile = {
            "conversation": [
                {
                    "role": "user",
                    "content": "I'm in Berlin",
                    "extracted": {"location": {"city": "Berlin"}},
                },
                {
                    "role": "user",
                    "content": "I like techno",
                    "extracted": {"scene": {"scene": "techno"}},
                },
            ],
            "elided_extracted": {},
        }
        slots = build(profile)
        assert slots.location == {"city": "Berlin"}
        assert slots.scene == {"scene": "techno"}
        assert slots.darkness is None
        assert slots.progress_pct > 0

    def test_elided_extracted_applied_first(self):
        """elided_extracted is the baseline; live turns override it (AC-11d.10)."""
        _, build = _import_reconstruction()
        # elided_extracted has old location, live turn has newer location
        profile = {
            "conversation": [
                {
                    "role": "user",
                    "content": "Actually I'm in Paris",
                    "extracted": {"location": {"city": "Paris"}},
                },
            ],
            "elided_extracted": {
                "location": {"city": "Berlin"},  # older, elided
                "scene": {"scene": "art"},
            },
        }
        slots = build(profile)
        # Live turn (Paris) must override elided (Berlin)
        assert slots.location == {"city": "Paris"}, (
            "live turn must override elided_extracted for same slot"
        )
        # Elided scene (no live override) must survive
        assert slots.scene == {"scene": "art"}

    def test_repeated_slot_live_wins(self):
        """When same slot appears multiple times in live turns, last one wins."""
        _, build = _import_reconstruction()
        profile = {
            "conversation": [
                {
                    "role": "user",
                    "content": "Berlin",
                    "extracted": {"location": {"city": "Berlin"}},
                },
                {
                    "role": "nikita",
                    "content": "Got it!",
                    "extracted": None,
                },
                {
                    "role": "user",
                    "content": "Actually Tokyo",
                    "extracted": {"location": {"city": "Tokyo"}},
                },
            ],
            "elided_extracted": {},
        }
        slots = build(profile)
        assert slots.location == {"city": "Tokyo"}

    def test_no_extraction_turns_are_skipped(self):
        """Turns without extracted (or extracted=None) do not mutate state."""
        _, build = _import_reconstruction()
        WizardSlots = _import_state()
        profile = {
            "conversation": [
                {"role": "nikita", "content": "Hello!", "extracted": None},
                {"role": "user", "content": "Hi!", "extracted": None},
            ],
            "elided_extracted": {},
        }
        slots = build(profile)
        assert slots.progress_pct == 0
        assert len(slots.missing) == 6

    def test_elided_only_no_live_turns(self):
        """elided_extracted alone populates slots when conversation is empty."""
        _, build = _import_reconstruction()
        profile = {
            "conversation": [],
            "elided_extracted": {
                "location": {"city": "NYC"},
                "scene": {"scene": "cocktails"},
            },
        }
        slots = build(profile)
        assert slots.location == {"city": "NYC"}
        assert slots.scene == {"scene": "cocktails"}
        assert slots.darkness is None

    def test_unknown_slot_key_in_extracted_is_ignored(self):
        """Unknown keys in extracted dict (e.g. 'no_extraction') are ignored."""
        _, build = _import_reconstruction()
        profile = {
            "conversation": [
                {
                    "role": "user",
                    "content": "...",
                    "extracted": {
                        "no_extraction": {"reason": "off_topic"},
                        "location": {"city": "Rome"},
                    },
                },
            ],
            "elided_extracted": {},
        }
        slots = build(profile)
        # location must be set, no_extraction must not pollute the slots model
        assert slots.location == {"city": "Rome"}
        # The WizardSlots model should not have a no_extraction attribute
        # (it only has the 6 canonical slot fields)
        assert not hasattr(slots, "no_extraction")

    def test_full_reconstruction_all_six_slots(self):
        """All 6 slots reconstructed → progress_pct == 100, is_complete True."""
        _, build = _import_reconstruction()
        profile = {
            "conversation": [
                {
                    "role": "user",
                    "content": "Berlin",
                    "extracted": {"location": {"city": "Berlin"}},
                },
                {
                    "role": "user",
                    "content": "Techno",
                    "extracted": {"scene": {"scene": "techno"}},
                },
                {
                    "role": "user",
                    "content": "Level 3",
                    "extracted": {"darkness": {"drug_tolerance": 3}},
                },
            ],
            "elided_extracted": {
                "identity": {"name": "Alex", "age": 25, "occupation": "dev"},
                "backstory": {
                    "chosen_option_id": "aabbccddeeff",
                    "cache_key": "berlin|techno|3",
                },
                "phone": {"phone_preference": "text", "phone": None},
            },
        }
        slots = build(profile)
        assert slots.progress_pct == 100
        assert len(slots.missing) == 0

    def test_missing_keys_in_profile_handled_gracefully(self):
        """Profile without 'conversation' or 'elided_extracted' keys is OK."""
        _, build = _import_reconstruction()
        # profile has neither key — should behave like empty
        profile = {"some_other_key": "value"}
        slots = build(profile)
        assert slots.progress_pct == 0

    def test_return_type_is_wizard_slots(self):
        """build_state_from_conversation always returns a WizardSlots instance."""
        _, build = _import_reconstruction()
        WizardSlots = _import_state()
        slots = build({})
        assert isinstance(slots, WizardSlots)
