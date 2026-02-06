"""Conflict evaluation stage (T2.8).

Non-critical: logs error on failure, continues.
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
    """Evaluate conflict triggers based on score/chapter/engagement.

    Non-critical: failure does not stop the pipeline.
    """

    name = "conflict"
    is_critical = False
    timeout_seconds = 15.0

    def __init__(self, session: AsyncSession = None, **kwargs) -> None:
        super().__init__(session=session, **kwargs)

    async def _run(self, ctx: PipelineContext) -> dict | None:
        """Evaluate whether a conflict should trigger."""
        # Conflict evaluation based on game state
        active = False
        conflict_type = None

        # Basic conflict detection based on score
        if ctx.relationship_score < 30:
            active = True
            conflict_type = "low_score"
        elif ctx.emotional_tone == "cold" and ctx.chapter >= 3:
            active = True
            conflict_type = "emotional_distance"

        ctx.active_conflict = active
        ctx.conflict_type = conflict_type

        return {"active": active, "type": conflict_type}
