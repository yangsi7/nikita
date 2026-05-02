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

    def test_thirteen_members(self):
        """SlotKind has exactly 13 members — one per question_registry entry."""
        _, SlotKind = _import_registry()
        members = list(SlotKind)
        assert len(members) == 13, (
            f"SlotKind has {len(members)} members, expected 13. "
            "Members: " + ", ".join(m.name for m in members)
        )

    def test_canonical_member_names(self):
        """All 13 expected members are present."""
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
        actual = {m.value for m in SlotKind}
        assert actual == expected, (
            f"SlotKind members drift. Missing: {expected - actual}; "
            f"Unexpected: {actual - expected}"
        )

    def test_every_slot_kind_has_a_question_entry(self):
        """Every SlotKind member appears as ``slot`` in ORDERED_QUESTIONS."""
        ORDERED_QUESTIONS, SlotKind = _import_registry()
        question_slots = {q.slot for q in ORDERED_QUESTIONS}
        for member in SlotKind:
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
