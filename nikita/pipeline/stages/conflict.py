"""Conflict evaluation stage (T2.8).

Non-critical: logs error on failure, continues.
Uses real ConflictDetector from emotional_state module.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from nikita.pipeline.stages.base import BaseStage

if TYPE_CHECKING:
    from nikita.pipeline.models import PipelineContext
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


class ConflictStage(BaseStage):
    """Evaluate conflict triggers using ConflictDetector.

    Non-critical: failure does not stop the pipeline.
    Builds EmotionalStateModel from ctx.emotional_state and uses
    ConflictDetector.detect_conflict_state() for detection.
    """

    name = "conflict"
    is_critical = False
    timeout_seconds = 15.0

    def __init__(self, session: AsyncSession = None, **kwargs) -> None:
        super().__init__(session=session, **kwargs)

    async def _run(self, ctx: PipelineContext) -> dict | None:
        """Evaluate whether a conflict should trigger using ConflictDetector."""
        try:
            from nikita.emotional_state.conflict import ConflictDetector
            from nikita.emotional_state.models import ConflictState, EmotionalStateModel

            detector = ConflictDetector()

            # Build EmotionalStateModel from ctx.emotional_state dict
            es = ctx.emotional_state or {}
            emotional_model = EmotionalStateModel(
                user_id=ctx.user_id,
                arousal=es.get("arousal", 0.5),
                valence=es.get("valence", 0.5),
                dominance=es.get("dominance", 0.5),
                intimacy=es.get("intimacy", 0.5),
            )

            conflict_state = detector.detect_conflict_state(state=emotional_model)

            active = conflict_state != ConflictState.NONE
            conflict_type = conflict_state.value if active else None

            ctx.active_conflict = active
            ctx.conflict_type = conflict_type

            if active:
                self._logger.info(
                    "conflict_detected",
                    conflict_type=conflict_type,
                    arousal=es.get("arousal"),
                    valence=es.get("valence"),
                    chapter=ctx.chapter,
                )

            return {"active": active, "type": conflict_type}

        except Exception as e:
            logger.error("conflict_detection_failed", exc_info=True)
            ctx.active_conflict = False
            ctx.conflict_type = None
            return {"active": False, "type": None, "error": str(e)[:100]}
