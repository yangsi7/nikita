"""Question Registry for the Spec 215 T-F2c.5 adaptive wizard.

Encodes the 6 required-slot questions as a priority-ordered registry.
The registry is the single source of truth for which question to ask next,
replacing implicit question-order rules in the static system prompt.

Option D (binding correction over recommendation §11): optional slots
(vibe, personality_archetype) are LLM-opportunistic — they are NEVER
included in ORDERED_QUESTIONS. The LLM extracts them when the user
volunteers relevant signals; the registry never routes to them.

``next_question(state)`` returns the highest-priority unfilled required
slot whose condition is met, or None if all required slots are filled.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Final

from nikita.agents.onboarding.state import WizardSlots


@dataclass(frozen=True)
class QuestionSpec:
    """Specification for a single wizard question.

    ``slot``: name of the WizardSlots field to fill.
    ``priority``: lower number = higher priority (10 is first).
    ``condition``: callable(WizardSlots) -> bool; returns True when this
        question is eligible to be asked (prerequisite slots are filled).
    ``hint``: one-line instruction injected into render_dynamic_instructions
        telling the LLM HOW to ask this question in Nikita's voice.
    """

    slot: str
    priority: int
    condition: Callable[[WizardSlots], bool]
    hint: str


ORDERED_QUESTIONS: Final[list[QuestionSpec]] = [
    QuestionSpec(
        "location",
        10,
        lambda s: True,
        "Ask the user what city they're in. Casual — 'where are you these days?'",
    ),
    QuestionSpec(
        "scene",
        20,
        lambda s: s.location is not None,
        "Ask their scene: techno, art, food, cocktails, nature. Curious, not multiple-choice.",
    ),
    QuestionSpec(
        "darkness",
        30,
        lambda s: s.scene is not None,
        "Ask 1-5 darkness rating. 'How deep are we going?'",
    ),
    QuestionSpec(
        "identity",
        40,
        lambda s: s.darkness is not None,
        "Get name+age+occupation in one warm exchange.",
    ),
    QuestionSpec(
        "backstory",
        50,
        lambda s: s.identity is not None,
        "Three numbered backstory options will be rendered upstream — invite the user to pick one.",
    ),
    QuestionSpec(
        "phone",
        60,
        lambda s: s.backstory is not None,
        "Ask preference: voice or text. Voice requires a number — see VOICE-WITHOUT-PHONE branch.",
    ),
]
"""Ordered question registry — exactly 6 entries, one per required slot.

Priority 10/20/30/40/50/60 with sequential conditions (each question
requires the previous slot to be filled). Optional slots (vibe,
personality_archetype) are never included — Option D.
"""


def next_question(state: WizardSlots) -> QuestionSpec | None:
    """Return the next required question to ask based on current wizard state.

    Filters ORDERED_QUESTIONS to candidates whose condition is met AND whose
    slot is not yet filled in ``state``. Returns the candidate with the
    lowest priority number (highest priority), or None if all required slots
    are filled.

    This is a pure function: same state always returns the same result.
    Optional slot values (vibe, personality_archetype) in state have no
    effect on the output — they are not in ORDERED_QUESTIONS.
    """
    candidates = [
        q for q in ORDERED_QUESTIONS
        if q.condition(state) and getattr(state, q.slot) is None
    ]
    return min(candidates, key=lambda q: q.priority) if candidates else None


__all__ = ["ORDERED_QUESTIONS", "QuestionSpec", "next_question"]
