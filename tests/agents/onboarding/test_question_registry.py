"""Tests for nikita.agents.onboarding.question_registry — 13-slot schema.

Covers: SlotKind StrEnum membership, ORDERED_QUESTIONS shape, next_question
ordering and gating predicates.
"""

from __future__ import annotations

import pytest

from nikita.agents.onboarding.question_registry import (
    ORDERED_QUESTIONS,
    QuestionSpec,
    SlotKind,
    next_question,
)
from nikita.agents.onboarding.state import SlotDelta, WizardSlots


class TestOrderedQuestionsStructure:
    def test_thirteen_entries(self):
        assert len(ORDERED_QUESTIONS) == 13

    def test_priorities_unique_and_sequential(self):
        priorities = [q.priority for q in ORDERED_QUESTIONS]
        assert priorities == sorted(priorities)
        assert len(set(priorities)) == 13

    def test_first_priority_is_display_name(self):
        first = min(ORDERED_QUESTIONS, key=lambda q: q.priority)
        assert first.slot == SlotKind.display_name.value

    def test_last_priority_is_phone(self):
        last = max(ORDERED_QUESTIONS, key=lambda q: q.priority)
        assert last.slot == SlotKind.phone.value


class TestNextQuestion:
    def test_empty_state_returns_display_name(self):
        slots = WizardSlots()
        nq = next_question(slots)
        assert nq is not None
        assert nq.slot == "display_name"

    def test_after_display_name_returns_age(self):
        slots = WizardSlots().apply(SlotDelta(kind="display_name", data={"display_name": "Sam"}))
        nq = next_question(slots)
        assert nq is not None
        assert nq.slot == "age"

    def test_full_state_returns_none(self):
        slots = WizardSlots()
        for kind in [m.value for m in SlotKind]:
            slots = slots.apply(SlotDelta(kind=kind, data={kind: "x"}))
        assert next_question(slots) is None

    def test_pure_function(self):
        slots = WizardSlots()
        a = next_question(slots)
        b = next_question(slots)
        assert a == b
