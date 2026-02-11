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

    # Default emotional state when computation fails or no data exists (Spec 045 WP-5b)
    DEFAULT_EMOTIONAL_STATE = {
        "arousal": 0.5,
        "valence": 0.5,
        "dominance": 0.5,
        "intimacy": 0.5,
    }

    async def _run(self, ctx: PipelineContext) -> dict | None:
        """Compute 4D emotional state.

        Spec 045 WP-5b: Returns sensible defaults (0.5 for all dimensions)
        if computation fails or user has no emotional state entries.
        """
        try:
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
        except Exception as e:
            logger.warning("emotional_computation_failed, using defaults: %s", str(e))
            ctx.emotional_state = dict(self.DEFAULT_EMOTIONAL_STATE)

        # Ensure we always have a valid emotional state (Spec 045 WP-5b)
        if not ctx.emotional_state:
            ctx.emotional_state = dict(self.DEFAULT_EMOTIONAL_STATE)

        return ctx.emotional_state
