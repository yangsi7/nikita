"""Tests for T-F2c.5 — Question Registry (nikita.agents.onboarding.question_registry).

Covers:
- ORDERED_QUESTIONS has exactly 6 entries (required slots only — Option D)
- Unique slot names, strictly ascending priorities
- next_question() routing for empty/partial/full state
- F2 invariant: optional slots filled but identity missing → returns identity
- QuestionSpec frozen (mutation raises FrozenInstanceError)
- Pure function: twice-call returns same result
- Conditions use only required-slot state
"""
from __future__ import annotations

import dataclasses

import pytest


def _import_registry():
    from nikita.agents.onboarding.question_registry import (  # noqa: PLC0415
        ORDERED_QUESTIONS,
        QuestionSpec,
        next_question,
    )
    return ORDERED_QUESTIONS, QuestionSpec, next_question


def _import_slots():
    from nikita.agents.onboarding.state import SlotDelta, WizardSlots  # noqa: PLC0415
    return SlotDelta, WizardSlots


def _full_slots():
    """Return WizardSlots with all 6 required slots filled."""
    SlotDelta, WizardSlots = _import_slots()
    slots = WizardSlots()
    for delta in [
        SlotDelta(kind="location", data={"city": "Berlin"}),
        SlotDelta(kind="scene", data={"scene": "techno"}),
        SlotDelta(kind="darkness", data={"drug_tolerance": 3}),
        SlotDelta(kind="identity", data={"name": "Sam", "age": 28, "occupation": "artist"}),
        SlotDelta(kind="backstory", data={"chosen_option_id": "abc", "cache_key": "berlin|techno|3"}),
        SlotDelta(kind="phone", data={"phone_preference": "text", "phone": None}),
    ]:
        slots = slots.apply(delta)
    return slots


# ---------------------------------------------------------------------------
# ORDERED_QUESTIONS structure
# ---------------------------------------------------------------------------


class TestOrderedQuestionsStructure:
    def test_ordered_questions_exactly_six_entries(self):
        """ORDERED_QUESTIONS must have exactly 6 entries (required slots, Option D)."""
        ORDERED_QUESTIONS, _, _ = _import_registry()
        assert len(ORDERED_QUESTIONS) == 6, (
            f"Expected exactly 6 entries, got {len(ORDERED_QUESTIONS)}. "
            "Option D: optional slots (vibe, personality_archetype) are never in the registry."
        )

    def test_ordered_questions_unique_slot_names(self):
        """No duplicate slot names in ORDERED_QUESTIONS."""
        ORDERED_QUESTIONS, _, _ = _import_registry()
        slot_names = [q.slot for q in ORDERED_QUESTIONS]
        assert len(slot_names) == len(set(slot_names)), (
            f"Duplicate slot names found: {slot_names}"
        )

    def test_ordered_questions_strictly_ascending_priorities(self):
        """Priorities in ORDERED_QUESTIONS must be strictly ascending."""
        ORDERED_QUESTIONS, _, _ = _import_registry()
        priorities = [q.priority for q in ORDERED_QUESTIONS]
        for i in range(1, len(priorities)):
            assert priorities[i] > priorities[i - 1], (
                f"Priority not strictly ascending at index {i}: {priorities}"
            )

    def test_ordered_questions_required_slots_only(self):
        """ORDERED_QUESTIONS contains only required slot names."""
        ORDERED_QUESTIONS, _, _ = _import_registry()
        required = {"location", "scene", "darkness", "identity", "backstory", "phone"}
        optional = {"vibe", "personality_archetype"}
        for q in ORDERED_QUESTIONS:
            assert q.slot in required, (
                f"Optional slot '{q.slot}' found in ORDERED_QUESTIONS — violates Option D"
            )
            assert q.slot not in optional, (
                f"Optional slot '{q.slot}' in ORDERED_QUESTIONS — must be removed"
            )

    def test_ordered_questions_priorities_are_10_20_30_40_50_60(self):
        """Priorities must be exactly 10/20/30/40/50/60 as specified."""
        ORDERED_QUESTIONS, _, _ = _import_registry()
        priorities = [q.priority for q in ORDERED_QUESTIONS]
        assert priorities == [10, 20, 30, 40, 50, 60]

    def test_ordered_questions_slot_order(self):
        """Slot order must be location → scene → darkness → identity → backstory → phone."""
        ORDERED_QUESTIONS, _, _ = _import_registry()
        slots = [q.slot for q in ORDERED_QUESTIONS]
        assert slots == ["location", "scene", "darkness", "identity", "backstory", "phone"]


# ---------------------------------------------------------------------------
# QuestionSpec shape
# ---------------------------------------------------------------------------


class TestQuestionSpecShape:
    def test_question_spec_is_frozen(self):
        """QuestionSpec is a frozen dataclass — mutation raises FrozenInstanceError."""
        _, QuestionSpec, _ = _import_registry()
        _, WizardSlots = _import_slots()
        spec = QuestionSpec(
            slot="location",
            priority=10,
            condition=lambda s: True,
            hint="Where are you?",
        )
        with pytest.raises((dataclasses.FrozenInstanceError, TypeError, AttributeError)):
            spec.slot = "scene"  # type: ignore[misc]

    def test_question_spec_has_hint_field(self):
        """QuestionSpec.hint must be a non-empty string."""
        ORDERED_QUESTIONS, _, _ = _import_registry()
        for q in ORDERED_QUESTIONS:
            assert isinstance(q.hint, str) and q.hint, (
                f"QuestionSpec for '{q.slot}' has empty or missing hint"
            )


# ---------------------------------------------------------------------------
# next_question routing
# ---------------------------------------------------------------------------


class TestNextQuestion:
    def test_empty_state_returns_location(self):
        """next_question(empty_state) returns the location spec (priority 10)."""
        ORDERED_QUESTIONS, _, next_question = _import_registry()
        _, WizardSlots = _import_slots()
        slots = WizardSlots()
        result = next_question(slots)
        assert result is not None
        assert result.slot == "location"

    def test_location_filled_returns_scene(self):
        """next_question returns scene after location is filled."""
        _, _, next_question = _import_registry()
        SlotDelta, WizardSlots = _import_slots()
        slots = WizardSlots()
        slots = slots.apply(SlotDelta(kind="location", data={"city": "Berlin"}))
        result = next_question(slots)
        assert result is not None
        assert result.slot == "scene"

    def test_location_scene_filled_returns_darkness(self):
        """next_question returns darkness after location + scene filled."""
        _, _, next_question = _import_registry()
        SlotDelta, WizardSlots = _import_slots()
        slots = WizardSlots()
        slots = slots.apply(SlotDelta(kind="location", data={"city": "Berlin"}))
        slots = slots.apply(SlotDelta(kind="scene", data={"scene": "techno"}))
        result = next_question(slots)
        assert result is not None
        assert result.slot == "darkness"

    def test_all_required_filled_returns_none(self):
        """next_question returns None when all 6 required slots are filled."""
        _, _, next_question = _import_registry()
        result = next_question(_full_slots())
        assert result is None

    def test_f2_invariant_optional_slots_cannot_override_required(self):
        """F2 invariant: location+scene+darkness filled + vibe/personality_archetype set
        but identity=None → next_question returns identity (not vibe or personality_archetype).

        Proves Option D: optional slots are never in the registry, so they can
        never win against a required slot.
        """
        _, _, next_question = _import_registry()
        SlotDelta, WizardSlots = _import_slots()
        slots = WizardSlots()
        slots = slots.apply(SlotDelta(kind="location", data={"city": "Berlin"}))
        slots = slots.apply(SlotDelta(kind="scene", data={"scene": "techno"}))
        slots = slots.apply(SlotDelta(kind="darkness", data={"drug_tolerance": 3}))
        # Set optional slots — should NOT influence registry routing
        slots = slots.apply(SlotDelta(kind="vibe", data={"aesthetic": "edgy", "confidence": 0.8}))
        slots = slots.apply(SlotDelta(kind="personality_archetype", data={"archetype": "adventurer", "confidence": 0.7}))
        # identity is still None
        assert slots.identity is None
        result = next_question(slots)
        assert result is not None
        assert result.slot == "identity", (
            f"Expected identity (required), got '{result.slot}'. "
            "Optional slots must never override required-slot registry."
        )

    def test_varying_optional_slots_does_not_change_next_question(self):
        """Optional slot state has zero effect on next_question output."""
        _, _, next_question = _import_registry()
        SlotDelta, WizardSlots = _import_slots()
        slots_base = WizardSlots()
        slots_base = slots_base.apply(SlotDelta(kind="location", data={"city": "Berlin"}))
        # Without optionals
        result_without = next_question(slots_base)

        # With optionals set
        slots_with_opts = slots_base.apply(
            SlotDelta(kind="vibe", data={"aesthetic": "edgy", "confidence": 0.9})
        )
        result_with = next_question(slots_with_opts)

        assert result_without is not None and result_with is not None
        assert result_without.slot == result_with.slot

    def test_next_question_pure_same_result_on_repeated_call(self):
        """next_question is a pure function — calling twice returns same result."""
        _, _, next_question = _import_registry()
        _, WizardSlots = _import_slots()
        slots = WizardSlots()
        result1 = next_question(slots)
        result2 = next_question(slots)
        assert result1 is result2 or (
            result1 is not None
            and result2 is not None
            and result1.slot == result2.slot
        )

    def test_conditions_gate_sequencing(self):
        """scene condition: s.location is not None; darkness: s.scene is not None."""
        _, _, next_question = _import_registry()
        SlotDelta, WizardSlots = _import_slots()
        # Only location filled: scene should be next (condition: location is not None)
        slots = WizardSlots()
        slots = slots.apply(SlotDelta(kind="location", data={"city": "Tokyo"}))
        result = next_question(slots)
        assert result is not None
        assert result.slot == "scene"

        # Empty state: scene condition fails (location is None), so only location is candidate
        slots_empty = WizardSlots()
        result_empty = next_question(slots_empty)
        assert result_empty is not None
        assert result_empty.slot == "location"
