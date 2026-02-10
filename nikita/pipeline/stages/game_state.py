"""Game state stage - scoring, chapters, decay (T2.7).

Non-critical: logs error on failure, continues.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

import structlog

from nikita.pipeline.stages.base import BaseStage
from nikita.pipeline.models import PipelineContext

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


class GameStateStage(BaseStage):
    """Update game state: scoring, chapter transitions, decay.

    Non-critical: failure does not stop the pipeline.
    """

    name = "game_state"
    is_critical = False
    timeout_seconds = 30.0

    def __init__(self, session: AsyncSession = None, **kwargs) -> None:
        super().__init__(session=session, **kwargs)

    async def _run(self, ctx: PipelineContext) -> dict | None:
        """Compute score deltas and check chapter transitions."""
        result = {
            "score_delta": Decimal("0"),
            "events": [],
            "chapter_changed": False,
            "decay_applied": False,
        }

        # Score calculation would require ResponseAnalysis from extraction
        # For now, this is a wrapper that will be wired in Phase 4
        if ctx.extraction_summary:
            self._logger.info(
                "game_state_evaluation has_extraction=True chapter=%s",
                ctx.chapter,
            )

        ctx.score_delta = result["score_delta"]
        ctx.score_events = result["events"]
        ctx.chapter_changed = result["chapter_changed"]
        ctx.decay_applied = result["decay_applied"]

        return result
