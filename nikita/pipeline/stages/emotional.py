"""Emotional state stage - computes 4D mood (T2.6).

Non-critical: logs error on failure, continues.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from nikita.pipeline.stages.base import BaseStage
from nikita.pipeline.models import PipelineContext

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


class EmotionalStage(BaseStage):
    """Compute emotional state from conversation and life events.

    Non-critical: failure does not stop the pipeline.
    """

    name = "emotional"
    is_critical = False
    timeout_seconds = 30.0

    def __init__(self, session: AsyncSession = None, **kwargs) -> None:
        super().__init__(session=session, **kwargs)

    async def _run(self, ctx: PipelineContext) -> dict | None:
        """Compute 4D emotional state."""
        from nikita.emotional_state.computer import StateComputer, EmotionalStateModel

        computer = StateComputer()

        # Build base state from defaults
        base = EmotionalStateModel(user_id=ctx.user_id)

        state = computer.compute(
            user_id=ctx.user_id,
            current_state=base,
            life_events=ctx.life_events or None,
            chapter=ctx.chapter,
            relationship_score=float(ctx.relationship_score),
        )

        ctx.emotional_state = {
            "arousal": state.arousal,
            "valence": state.valence,
            "dominance": state.dominance,
            "intimacy": state.intimacy,
        }

        return ctx.emotional_state
