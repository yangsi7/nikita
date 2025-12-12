"""Chapter progression system for Nikita game engine."""

from nikita.engine.chapters.boss import BossStateMachine
from nikita.engine.chapters.prompts import BOSS_PROMPTS, get_boss_prompt
from nikita.engine.chapters.judgment import BossJudgment, BossResult, JudgmentResult

__all__ = [
    "BossStateMachine",
    "BOSS_PROMPTS",
    "get_boss_prompt",
    "BossJudgment",
    "BossResult",
    "JudgmentResult",
]
