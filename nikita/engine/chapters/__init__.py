"""Chapter progression system for Nikita game engine."""

from nikita.engine.chapters.boss import BossPhase, BossPhaseState, BossStateMachine
from nikita.engine.chapters.phase_manager import BossPhaseManager
from nikita.engine.chapters.prompts import BOSS_PROMPTS, get_boss_phase_prompt, get_boss_prompt
from nikita.engine.chapters.judgment import BossJudgment, BossResult, JudgmentResult

__all__ = [
    "BossStateMachine",
    "BOSS_PROMPTS",
    "get_boss_prompt",
    "BossJudgment",
    "BossResult",
    "JudgmentResult",
    # Spec 058 exports
    "BossPhase",
    "BossPhaseState",
    "BossPhaseManager",
    "get_boss_phase_prompt",
]


def is_multi_phase_boss_enabled() -> bool:
    """Check if multi-phase boss encounters are enabled (Spec 058).

    Returns:
        True if multi_phase_boss_enabled flag is ON in settings.
    """
    from nikita.config.settings import get_settings

    return get_settings().multi_phase_boss_enabled
