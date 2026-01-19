"""Behavioral Meta-Instructions Module (Spec 024).

Provides directional behavioral guidance for Nikita without over-specifying responses.
Uses high-level decision trees and meta-instructions to nudge LLM behavior.

Architecture:
- SituationDetector: Detects current conversational situation
- InstructionSelector: Selects relevant meta-instructions
- MetaInstructionEngine: Orchestrates detection → selection → formatting

Situation Types (priority order):
1. conflict - User is in conflict state (from Spec 023)
2. after_gap - >6 hours since last message
3. time_based - Morning (6-11am), Evening (6-10pm)
4. mid_conversation - Active conversation, no special situation

Example Usage:
    from nikita.behavioral import MetaInstructionEngine

    engine = MetaInstructionEngine()
    instructions = await engine.get_instructions_for_context(
        user_id=user_id,
        conflict_state=conflict_state,
        hours_since_last=hours,
        chapter=chapter,
    )
"""

from nikita.behavioral.detector import SituationDetector
from nikita.behavioral.engine import MetaInstructionEngine
from nikita.behavioral.models import (
    InstructionSet,
    MetaInstruction,
    SituationCategory,
    SituationContext,
    SituationType,
)
from nikita.behavioral.selector import InstructionSelector

__all__ = [
    "InstructionSelector",
    "InstructionSet",
    "MetaInstruction",
    "MetaInstructionEngine",
    "SituationCategory",
    "SituationContext",
    "SituationDetector",
    "SituationType",
]
