"""Hand-crafted similarity-pair fixtures locking the MIRROR_THRESHOLD.

Per Spec 217-3A AC-7.4: 5 near-duplicate pairs (expected ratio > 0.85)
plus 5 distinct pairs (expected ratio < 0.85). Used by
``test_validators.py::TestMirrorThresholdCalibration`` to verify that
``MIRROR_THRESHOLD = 0.85`` cleanly separates "mirror" from "distinct".

The threshold is LOCKED by this fixture; raising or lowering it without
re-running this calibration is a tuning-constants.md violation.

Each entry is a tuple ``(question_a, question_b, expected_above_threshold)``
where ``expected_above_threshold`` is True if the pair should be flagged
as a mirror (ratio > 0.85), False otherwise. Ratio is computed via
``difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()``.

The pairs simulate realistic LLM "mirror-of-next" failures where the
agent re-asks the deterministic question text in slightly different
wording. Distinct pairs vary the angle (texture, scene, motivation)
which is what the FollowUpQuestion validator wants to enforce.
"""

from __future__ import annotations

from typing import Final

# 5 near-duplicate pairs — expected ratio > 0.85 (rejection territory).
NEAR_DUPLICATES: Final[list[tuple[str, str, bool]]] = [
    # Verbatim with trailing-space drift.
    ("what's your name?", "what's your name? ", True),
    # Capitalization-only difference (case-insensitive ratio still high).
    ("how old are you?", "How old are you?", True),
    # Punctuation drift.
    ("what do you do for work?", "what do you do for work", True),
    # Synonym swap that preserves >85% characters.
    ("what's your occupation?", "what is your occupation?", True),
    # Tight rewording — single-word swap on a long base preserves ratio >0.85.
    (
        "what city are you living in right now?",
        "what city are you staying in right now?",
        True,
    ),
]

# 5 distinct pairs — expected ratio < 0.85 (pass territory).
DISTINCT_PAIRS: Final[list[tuple[str, str, bool]]] = [
    # Same slot, different angle (texture vs identity).
    ("what's your name?", "tell me about the texture of your morning", False),
    # Different slot entirely.
    ("what city are you in?", "describe your favorite Saturday morning", False),
    # Same slot, scene-based rephrase.
    ("how old are you?", "what does your typical workday look like", False),
    # Same slot, motivation angle.
    ("what do you do for work?", "what gets you out of bed in the morning", False),
    # Distinct topic.
    ("what's your occupation?", "where do you spend most of your weekends", False),
]

CALIBRATION_PAIRS: Final[list[tuple[str, str, bool]]] = (
    NEAR_DUPLICATES + DISTINCT_PAIRS
)

__all__ = [
    "CALIBRATION_PAIRS",
    "DISTINCT_PAIRS",
    "NEAR_DUPLICATES",
]
