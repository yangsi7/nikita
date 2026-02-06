"""Touchpoint scheduling stage (T2.9).

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


class TouchpointStage(BaseStage):
    """Evaluate and schedule proactive touchpoints.

    Non-critical: failure does not stop the pipeline.
    """

    name = "touchpoint"
    is_critical = False
    timeout_seconds = 30.0

    def __init__(self, session: AsyncSession = None, **kwargs) -> None:
        super().__init__(session=session, **kwargs)

    async def _run(self, ctx: PipelineContext) -> dict | None:
        """Evaluate touchpoint triggers and schedule if needed."""
        from nikita.touchpoints.engine import TouchpointEngine

        try:
            engine = TouchpointEngine(session=self._session)
            result = await engine.evaluate_and_schedule_for_user(ctx.user_id)
            ctx.touchpoint_scheduled = result is not None
        except Exception:
            self._logger.warning("touchpoint_evaluation_failed", exc_info=True)
            ctx.touchpoint_scheduled = False

        return {"scheduled": ctx.touchpoint_scheduled}
