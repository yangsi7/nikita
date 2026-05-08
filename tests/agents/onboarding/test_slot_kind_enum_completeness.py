"""B1.18 — SlotKind enum completeness lint.

Every SlotKind member (StrEnum from question_registry) MUST appear in
ORDERED_QUESTIONS exactly once. The enum is the single source of truth;
inline ``Literal[...]`` lists are forbidden.
"""

from __future__ import annotations

import pytest


def _import_registry():
    from nikita.agents.onboarding.question_registry import (  # noqa: PLC0415
        ORDERED_QUESTIONS,
        SlotKind,
    )
    return ORDERED_QUESTIONS, SlotKind


class TestSlotKindEnumCompleteness:
    def test_slot_kind_is_str_enum(self):
        """SlotKind must be a StrEnum (not bare class, not Literal)."""
        from enum import StrEnum

        _, SlotKind = _import_registry()
        assert issubclass(SlotKind, StrEnum)

    def test_thirteen_data_members(self):
        """SlotKind has exactly 13 data slots — one per question_registry entry.

        The ``identity_pair`` member (added 217-3A.3 FR-10a) is a route-level
        pseudo-slot, NOT a wizard data slot — it decomposes into
        ``display_name`` + ``age`` at the route handler. Excluded from the
        13-member invariant.
        """
        _, SlotKind = _import_registry()
        data_members = [m for m in SlotKind if m.value != "identity_pair"]
        assert len(data_members) == 13, (
            f"SlotKind has {len(data_members)} data members, expected 13. "
            "Members: " + ", ".join(m.name for m in data_members)
        )

    def test_canonical_member_names(self):
        """All 13 expected data members are present.

        ``identity_pair`` (217-3A.3 FR-10a route-level pseudo-slot) is
        excluded — it is not a wizard data slot.
        """
        _, SlotKind = _import_registry()
        expected = {
            "display_name",
            "age",
            "occupation",
            "city",
            "darkness_level",
            "primary_hobbies",
            "saturday_morning",
            "geek_out_on",
            "together_we_could",
            "same_weird_if",
            "voice_tone_pref",
            "backstory_pick",
            "phone",
        }
        actual = {m.value for m in SlotKind if m.value != "identity_pair"}
        assert actual == expected, (
            f"SlotKind members drift. Missing: {expected - actual}; "
            f"Unexpected: {actual - expected}"
        )

    def test_every_data_slot_kind_has_a_question_entry(self):
        """Every SlotKind data member appears as ``slot`` in ORDERED_QUESTIONS.

        ``identity_pair`` is excluded — route-level pseudo-slot.
        """
        ORDERED_QUESTIONS, SlotKind = _import_registry()
        question_slots = {q.slot for q in ORDERED_QUESTIONS}
        for member in SlotKind:
            if member.value == "identity_pair":
                continue
            assert member.value in question_slots, (
                f"SlotKind.{member.name} has no entry in ORDERED_QUESTIONS"
            )

    def test_ordered_questions_uses_slot_kind_values(self):
        """ORDERED_QUESTIONS slot strings are exactly SlotKind values."""
        ORDERED_QUESTIONS, SlotKind = _import_registry()
        valid_values = {m.value for m in SlotKind}
        for q in ORDERED_QUESTIONS:
            assert q.slot in valid_values, (
                f"ORDERED_QUESTIONS entry {q.slot!r} is not a SlotKind value"
            )

    def test_ordered_questions_priorities_are_unique(self):
        """Each question has a distinct priority (deterministic ordering)."""
        ORDERED_QUESTIONS, _ = _import_registry()
        priorities = [q.priority for q in ORDERED_QUESTIONS]
        assert len(priorities) == len(set(priorities)), (
            "ORDERED_QUESTIONS priorities collide"
        )
