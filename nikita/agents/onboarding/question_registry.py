"""Question Registry for the Spec 216-B1 13-slot agentic wizard.

Single source of truth for the wizard slot taxonomy. ``SlotKind`` is a
StrEnum (B1.18) used by ``WizardSlots`` field names, ``SlotDelta.kind``
discriminator, and ``TurnOutput.next_slot_kind``. ``ORDERED_QUESTIONS``
is the priority-ordered registry of 13 entries — one per fixed root.

Per ``.claude/rules/agentic-design-patterns.md``: routing rules MUST
live in ``inject_per_turn_context`` (a callable injected via
``Agent(instructions=callable)``), NEVER in a static system prompt.
This registry is consulted by that callable to surface ``next_slot_hint``
each turn.

Per ``.claude/rules/tuning-constants.md``: constants are named, documented,
and regression-guarded. The 13-member shape is locked in
``test_slot_kind_enum_completeness.py``; any change requires updating
both the enum AND the test.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Callable, Final


class SlotKind(StrEnum):
    """Canonical wizard slot kinds — 13 members (B1.beta lock-in).

    Used by:
    - ``WizardSlots`` field names (state.py)
    - ``SlotDelta.kind`` discriminator value
    - ``TurnOutput.next_slot_kind`` typed enum
    - ``ORDERED_QUESTIONS`` registry (priority-ordered)

    Membership change requires a synchronized update to FinalForm required
    fields, ORDERED_QUESTIONS, follow_up_registry.yaml, and the lint test
    in ``test_slot_kind_enum_completeness.py``.
    """

    display_name = "display_name"
    age = "age"
    occupation = "occupation"
    city = "city"
    darkness_level = "darkness_level"
    primary_hobbies = "primary_hobbies"
    saturday_morning = "saturday_morning"
    geek_out_on = "geek_out_on"
    together_we_could = "together_we_could"
    same_weird_if = "same_weird_if"
    voice_tone_pref = "voice_tone_pref"
    backstory_pick = "backstory_pick"
    phone = "phone"


@dataclass(frozen=True)
class QuestionSpec:
    """Specification for one wizard question.

    ``slot``: name of the WizardSlots field to fill (must be a SlotKind value).
    ``priority``: lower number = higher priority. 10/20/30/.../130 sequential.
    ``condition``: callable(WizardSlots) -> bool; eligibility predicate.
    ``hint``: one-line instruction surfaced to the LLM via
        ``inject_per_turn_context`` to guide HOW to ask this question.
    """

    slot: str
    priority: int
    condition: Callable[[object], bool]
    hint: str


def _always(_: object) -> bool:
    return True


def _after(slot_name: str) -> Callable[[object], bool]:
    """Return a condition predicate that fires when ``slot_name`` is filled."""
    def _cond(state: object) -> bool:
        return getattr(state, slot_name, None) is not None
    return _cond


ORDERED_QUESTIONS: Final[list[QuestionSpec]] = [
    QuestionSpec(
        SlotKind.display_name.value, 10, _always,
        "Ask a name. Casual. 'what do I call you?'",
    ),
    QuestionSpec(
        SlotKind.age.value, 20, _after("display_name"),
        "Ask their age. Plain question. Must be 18+.",
    ),
    QuestionSpec(
        SlotKind.occupation.value, 30, _after("age"),
        "Ask what they do. Day job, hustle, whatever pays.",
    ),
    QuestionSpec(
        SlotKind.city.value, 40, _after("occupation"),
        "Ask their city. 'where are you these days?'",
    ),
    QuestionSpec(
        SlotKind.darkness_level.value, 50, _after("city"),
        "Ask 1-5 darkness rating. 'how deep are we going?'",
    ),
    QuestionSpec(
        SlotKind.primary_hobbies.value, 60, _after("darkness_level"),
        "Ask what they actually do for fun. Multi-select prose ok.",
    ),
    QuestionSpec(
        SlotKind.saturday_morning.value, 70, _after("primary_hobbies"),
        "Ask what a perfect saturday morning looks like.",
    ),
    QuestionSpec(
        SlotKind.geek_out_on.value, 80, _after("saturday_morning"),
        "Ask what they geek out on. The thing nobody else cares about.",
    ),
    QuestionSpec(
        SlotKind.together_we_could.value, 90, _after("geek_out_on"),
        "Ask what we could do together. Open-ended; one line is fine.",
    ),
    QuestionSpec(
        SlotKind.same_weird_if.value, 100, _after("together_we_could"),
        "Ask what would make us the same kind of weird.",
    ),
    QuestionSpec(
        SlotKind.voice_tone_pref.value, 110, _after("same_weird_if"),
        "Ask: voice or text? Voice requires a number next.",
    ),
    QuestionSpec(
        SlotKind.backstory_pick.value, 120, _after("voice_tone_pref"),
        "Three numbered backstory options will be rendered upstream — invite a pick.",
    ),
    QuestionSpec(
        SlotKind.phone.value, 130, _after("backstory_pick"),
        "Ask for phone in E.164 format. Required if voice; optional otherwise.",
    ),
]
"""Ordered question registry — exactly 13 entries, one per SlotKind member.

Priority 10/20/.../130 sequential. Each question's ``condition`` predicate
references the prior slot so the registry returns a sensible "next slot"
even when extractions arrive out of order.
"""


def next_question(state: object) -> QuestionSpec | None:
    """Return the next required question to ask based on current wizard state.

    Filters ORDERED_QUESTIONS to entries whose ``condition`` is met AND whose
    ``slot`` is not yet filled in ``state``. Returns the candidate with the
    lowest priority number, or None if all 13 slots are filled.

    Pure function: same state always returns the same result.
    """
    candidates = [
        q for q in ORDERED_QUESTIONS
        if q.condition(state) and getattr(state, q.slot, None) is None
    ]
    return min(candidates, key=lambda q: q.priority) if candidates else None


__all__ = ["ORDERED_QUESTIONS", "QuestionSpec", "SlotKind", "next_question"]
