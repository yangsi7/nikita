"""Tests for T-F2c.2 — optional slot extension to WizardSlots.

Covers:
- vibe and personality_archetype optional fields on WizardSlots
- SlotDelta.kind Literal includes "vibe" and "personality_archetype"
- agent_context_dict() returns union of filled required+optional slots
- slots_dict() still returns required-only
- missing/progress_pct/is_complete are unaffected by optional slot state
- Cumulative-state monotonicity over 7 turns (includes optional slots)
- Completion-gate triplet still holds with optionals set
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError


def _import_state():
    from nikita.agents.onboarding.state import (  # noqa: PLC0415
        FinalForm,
        SlotDelta,
        TOTAL_SLOTS,
        WizardSlots,
    )
    return FinalForm, SlotDelta, TOTAL_SLOTS, WizardSlots


def _full_required_deltas():
    """Return SlotDelta list filling all 6 required slots."""
    from nikita.agents.onboarding.state import SlotDelta  # noqa: PLC0415
    return [
        SlotDelta(kind="location", data={"city": "Berlin"}),
        SlotDelta(kind="scene", data={"scene": "techno"}),
        SlotDelta(kind="darkness", data={"drug_tolerance": 3}),
        SlotDelta(
            kind="identity",
            data={"name": "Sam", "age": 28, "occupation": "artist"},
        ),
        SlotDelta(
            kind="backstory",
            data={
                "chosen_option_id": "aabbccddeeff",
                "cache_key": "berlin|techno|3",
            },
        ),
        SlotDelta(
            kind="phone",
            data={"phone_preference": "text", "phone": None},
        ),
    ]


# ---------------------------------------------------------------------------
# Optional slot defaults
# ---------------------------------------------------------------------------


class TestOptionalSlotDefaults:
    def test_vibe_defaults_to_none(self):
        """WizardSlots.vibe is None by default."""
        _, _, _, WizardSlots = _import_state()
        slots = WizardSlots()
        assert slots.vibe is None

    def test_personality_archetype_defaults_to_none(self):
        """WizardSlots.personality_archetype is None by default."""
        _, _, _, WizardSlots = _import_state()
        slots = WizardSlots()
        assert slots.personality_archetype is None


# ---------------------------------------------------------------------------
# SlotDelta accepts new kinds
# ---------------------------------------------------------------------------


class TestSlotDeltaNewKinds:
    def test_slot_delta_accepts_vibe_kind(self):
        """SlotDelta accepts kind='vibe'."""
        _, SlotDelta, _, _ = _import_state()
        delta = SlotDelta(kind="vibe", data={"aesthetic": "edgy", "confidence": 0.8})
        assert delta.kind == "vibe"

    def test_slot_delta_accepts_personality_archetype_kind(self):
        """SlotDelta accepts kind='personality_archetype'."""
        _, SlotDelta, _, _ = _import_state()
        delta = SlotDelta(kind="personality_archetype", data={"archetype": "adventurer", "confidence": 0.7})
        assert delta.kind == "personality_archetype"

    def test_slot_delta_unknown_kind_still_rejected(self):
        """SlotDelta still rejects unknown kinds after optional-kind extension."""
        _, SlotDelta, _, _ = _import_state()
        with pytest.raises((ValidationError, ValueError)):
            SlotDelta(kind="UNKNOWN_SLOT", data={})

    def test_slot_delta_all_valid_kinds_accepted(self):
        """All canonical kinds (required + optional + no_extraction) are accepted."""
        _, SlotDelta, _, _ = _import_state()
        all_kinds = [
            "location", "scene", "darkness", "identity", "backstory", "phone",
            "vibe", "personality_archetype",
            "no_extraction",
        ]
        for kind in all_kinds:
            delta = SlotDelta(kind=kind, data={})
            assert delta.kind == kind


# ---------------------------------------------------------------------------
# apply() for optional slots
# ---------------------------------------------------------------------------


class TestApplyOptionalSlots:
    def test_apply_vibe_delta_populates_vibe(self):
        """apply(SlotDelta(kind='vibe', ...)) populates WizardSlots.vibe."""
        _, SlotDelta, _, WizardSlots = _import_state()
        slots = WizardSlots()
        delta = SlotDelta(kind="vibe", data={"aesthetic": "edgy", "confidence": 0.8})
        slots2 = slots.apply(delta)
        assert slots2.vibe == {"aesthetic": "edgy", "confidence": 0.8}

    def test_apply_personality_archetype_delta_populates_field(self):
        """apply(SlotDelta(kind='personality_archetype', ...)) populates the field."""
        _, SlotDelta, _, WizardSlots = _import_state()
        slots = WizardSlots()
        delta = SlotDelta(kind="personality_archetype", data={"archetype": "adventurer", "confidence": 0.7})
        slots2 = slots.apply(delta)
        assert slots2.personality_archetype == {"archetype": "adventurer", "confidence": 0.7}

    def test_apply_optional_is_immutable(self):
        """Applying an optional slot leaves original WizardSlots unchanged."""
        _, SlotDelta, _, WizardSlots = _import_state()
        slots = WizardSlots()
        delta = SlotDelta(kind="vibe", data={"aesthetic": "chill", "confidence": 0.6})
        slots2 = slots.apply(delta)
        assert slots.vibe is None
        assert slots2.vibe is not None


# ---------------------------------------------------------------------------
# missing / progress_pct unaffected by optional slots
# ---------------------------------------------------------------------------


class TestMissingExcludesOptional:
    def test_missing_excludes_vibe(self):
        """missing does not include 'vibe' even when vibe is None."""
        _, _, _, WizardSlots = _import_state()
        slots = WizardSlots()
        assert "vibe" not in slots.missing

    def test_missing_excludes_personality_archetype(self):
        """missing does not include 'personality_archetype' even when None."""
        _, _, _, WizardSlots = _import_state()
        slots = WizardSlots()
        assert "personality_archetype" not in slots.missing

    def test_progress_pct_unaffected_by_optional_slots(self):
        """progress_pct only counts the 6 required slots."""
        _, SlotDelta, _, WizardSlots = _import_state()
        slots = WizardSlots()
        # Fill vibe only
        slots2 = slots.apply(SlotDelta(kind="vibe", data={"aesthetic": "edgy", "confidence": 0.9}))
        # Progress must still be 0 (vibe is optional, not required)
        assert slots2.progress_pct == 0

    def test_total_slots_constant_unchanged(self):
        """TOTAL_SLOTS must remain 6 — required-only denominator."""
        _, _, TOTAL_SLOTS, _ = _import_state()
        assert TOTAL_SLOTS == 6


# ---------------------------------------------------------------------------
# slots_dict() — required-only
# ---------------------------------------------------------------------------


class TestSlotsDictRequiredOnly:
    def test_slots_dict_does_not_include_vibe(self):
        """slots_dict() never includes 'vibe' key even when vibe is set."""
        _, SlotDelta, _, WizardSlots = _import_state()
        slots = WizardSlots()
        slots = slots.apply(SlotDelta(kind="vibe", data={"aesthetic": "cozy", "confidence": 0.5}))
        d = slots.slots_dict()
        assert "vibe" not in d

    def test_slots_dict_does_not_include_personality_archetype(self):
        """slots_dict() never includes 'personality_archetype' key."""
        _, SlotDelta, _, WizardSlots = _import_state()
        slots = WizardSlots()
        slots = slots.apply(SlotDelta(kind="personality_archetype", data={"archetype": "romantic", "confidence": 0.8}))
        d = slots.slots_dict()
        assert "personality_archetype" not in d


# ---------------------------------------------------------------------------
# agent_context_dict() — union (required + optional, non-None)
# ---------------------------------------------------------------------------


class TestAgentContextDict:
    def test_agent_context_dict_includes_required_slot(self):
        """agent_context_dict() includes filled required slot."""
        _, SlotDelta, _, WizardSlots = _import_state()
        slots = WizardSlots()
        slots = slots.apply(SlotDelta(kind="location", data={"city": "Tokyo"}))
        ctx = slots.agent_context_dict()
        assert "location" in ctx
        assert ctx["location"]["city"] == "Tokyo"

    def test_agent_context_dict_includes_vibe_when_set(self):
        """agent_context_dict() includes vibe when it has been set."""
        _, SlotDelta, _, WizardSlots = _import_state()
        slots = WizardSlots()
        slots = slots.apply(SlotDelta(kind="vibe", data={"aesthetic": "edgy", "confidence": 0.8}))
        ctx = slots.agent_context_dict()
        assert "vibe" in ctx
        assert ctx["vibe"]["aesthetic"] == "edgy"

    def test_agent_context_dict_includes_personality_archetype_when_set(self):
        """agent_context_dict() includes personality_archetype when set."""
        _, SlotDelta, _, WizardSlots = _import_state()
        slots = WizardSlots()
        slots = slots.apply(SlotDelta(kind="personality_archetype", data={"archetype": "caretaker", "confidence": 0.75}))
        ctx = slots.agent_context_dict()
        assert "personality_archetype" in ctx

    def test_agent_context_dict_excludes_none_values(self):
        """agent_context_dict() only returns non-None slots."""
        _, _, _, WizardSlots = _import_state()
        slots = WizardSlots()
        ctx = slots.agent_context_dict()
        # Empty slots → empty dict
        assert ctx == {}

    def test_agent_context_dict_union_both_required_and_optional(self):
        """agent_context_dict() contains both required and optional when set."""
        _, SlotDelta, _, WizardSlots = _import_state()
        slots = WizardSlots()
        slots = slots.apply(SlotDelta(kind="location", data={"city": "Paris"}))
        slots = slots.apply(SlotDelta(kind="vibe", data={"aesthetic": "romantic", "confidence": 0.9}))
        ctx = slots.agent_context_dict()
        assert "location" in ctx
        assert "vibe" in ctx
        assert "scene" not in ctx  # not filled, so not in output


# ---------------------------------------------------------------------------
# Completion gate — optionals do not affect completion
# ---------------------------------------------------------------------------


class TestCompletionGateWithOptionals:
    def test_is_complete_false_when_only_optionals_set(self):
        """is_complete is False when only optional slots are set."""
        _, SlotDelta, _, WizardSlots = _import_state()
        slots = WizardSlots()
        slots = slots.apply(SlotDelta(kind="vibe", data={"aesthetic": "edgy", "confidence": 0.8}))
        slots = slots.apply(SlotDelta(kind="personality_archetype", data={"archetype": "adventurer", "confidence": 0.7}))
        assert slots.is_complete is False

    def test_is_complete_true_when_all_required_set_regardless_of_optionals(self):
        """is_complete is True when all 6 required slots are filled (optionals don't matter)."""
        _, SlotDelta, _, WizardSlots = _import_state()
        slots = WizardSlots()
        # All required
        for delta in _full_required_deltas():
            slots = slots.apply(delta)
        # Optional NOT set
        assert slots.personality_archetype is None
        assert slots.vibe is None
        assert slots.is_complete is True

    def test_is_complete_true_with_optionals_also_set(self):
        """is_complete is True when required + optional slots both filled."""
        _, SlotDelta, _, WizardSlots = _import_state()
        slots = WizardSlots()
        for delta in _full_required_deltas():
            slots = slots.apply(delta)
        slots = slots.apply(SlotDelta(kind="vibe", data={"aesthetic": "chill", "confidence": 0.6}))
        slots = slots.apply(SlotDelta(kind="personality_archetype", data={"archetype": "pragmatist", "confidence": 0.8}))
        assert slots.is_complete is True

    def test_final_form_unchanged_with_optional_slots_set(self):
        """FinalForm.model_validate ignores optional slot keys in slots_dict."""
        FinalForm, SlotDelta, _, WizardSlots = _import_state()
        slots = WizardSlots()
        for delta in _full_required_deltas():
            slots = slots.apply(delta)
        slots = slots.apply(SlotDelta(kind="vibe", data={"aesthetic": "edgy", "confidence": 0.8}))
        # slots_dict() must NOT include vibe, so FinalForm validates without error
        d = slots.slots_dict()
        form = FinalForm.model_validate(d)
        assert form is not None


# ---------------------------------------------------------------------------
# Cumulative-state monotonicity over 7 turns (agentic-flow mandatory)
# ---------------------------------------------------------------------------


class TestCumulativeMonotonicitySevenTurns:
    def test_progress_pct_monotonic_over_seven_turns_including_optional(self):
        """progress_pct never regresses over 7 turns that include optional-slot turns.

        Turn order: location → vibe (optional) → scene → personality_archetype (optional)
                    → darkness → identity → backstory
        Optional-slot turns must not regress progress.
        """
        _, SlotDelta, _, WizardSlots = _import_state()
        slots = WizardSlots()
        progress_history = [slots.progress_pct]  # 0

        turns = [
            SlotDelta(kind="location", data={"city": "NYC"}),
            SlotDelta(kind="vibe", data={"aesthetic": "edgy", "confidence": 0.8}),  # optional
            SlotDelta(kind="scene", data={"scene": "art"}),
            SlotDelta(kind="personality_archetype", data={"archetype": "adventurer", "confidence": 0.7}),  # optional
            SlotDelta(kind="darkness", data={"drug_tolerance": 4}),
            SlotDelta(kind="identity", data={"name": "Alex", "age": 30, "occupation": "dev"}),
            SlotDelta(kind="backstory", data={"chosen_option_id": "abc123", "cache_key": "nyc|art|4"}),
        ]

        for turn in turns:
            slots = slots.apply(turn)
            progress_history.append(slots.progress_pct)

        for i in range(1, len(progress_history)):
            assert progress_history[i] >= progress_history[i - 1], (
                f"progress regressed at turn {i}: "
                f"{progress_history[i - 1]} → {progress_history[i]}"
            )
