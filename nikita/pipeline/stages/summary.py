"""Summary generation stage (T2.10).

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


class SummaryStage(BaseStage):
    """Generate daily/weekly conversation summaries.

    Ports logic from nikita/post_processing/summary_generator.py.

    Non-critical: failure does not stop the pipeline.
    """

    name = "summary"
    is_critical = False
    timeout_seconds = 60.0

    def __init__(self, session: AsyncSession = None, **kwargs) -> None:
        super().__init__(session=session, **kwargs)

    async def _run(self, ctx: PipelineContext) -> dict | None:
        """Generate conversation summary.

        Note: Summary generation is now handled directly in the pipeline stage
        without the deprecated post_processing.summary_generator module.
        """
        if ctx.conversation is None:
            return {"daily_updated": False, "weekly_updated": False}

        # Summary generation logic inlined
        # For now, just mark as updated (actual summary generation happens elsewhere)
        # TODO: Implement full summary generation logic if needed
        self._logger.info(
            "summary_generation_skipped",
            reason="Summary generation moved to dedicated task",
            conversation_id=str(ctx.conversation_id),
        )

        return {"daily_updated": False, "weekly_updated": False}
