"""Life simulation stage - generates daily events for Nikita (T2.5).

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


class LifeSimStage(BaseStage):
    """Run life simulation to generate daily events for Nikita.

    Non-critical: failure does not stop the pipeline.
    """

    name = "life_sim"
    is_critical = False
    timeout_seconds = 60.0

    def __init__(self, session: AsyncSession = None, **kwargs) -> None:
        super().__init__(session=session, **kwargs)

    async def _run(self, ctx: PipelineContext) -> dict | None:
        """Generate life events via LifeSimulator."""
        from nikita.life_simulation import LifeSimulator

        simulator = LifeSimulator()
        events = await simulator.generate_next_day_events(
            user_id=ctx.user_id,
        )

        ctx.life_events = events
        return {"events_generated": len(events)}
