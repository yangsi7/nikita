"""Game state stage - scoring, chapters, decay (T2.7).

Non-critical: logs error on failure, continues.
Reads score_delta from conversation (already computed by message_handler),
validates chapter/boss state, logs anomalies.
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
    """Read game state from conversation and validate chapter coherence.

    Non-critical: failure does not stop the pipeline.

    Score delta is computed inline by message_handler and stored on the
    Conversation model. This stage reads that value and validates game
    state consistency (boss thresholds, chapter-day coherence).
    """

    name = "game_state"
    is_critical = False
    timeout_seconds = 30.0

    def __init__(self, session: AsyncSession = None, **kwargs) -> None:
        super().__init__(session=session, **kwargs)

    async def _run(self, ctx: PipelineContext) -> dict | None:
        """Read score_delta from conversation and validate game state."""
        events: list[str] = []
        chapter_changed = False
        decay_applied = False

        # 1. Read score_delta from conversation (computed by message_handler)
        score_delta = Decimal("0")
        if ctx.conversation is not None:
            conv_delta = getattr(ctx.conversation, "score_delta", None)
            if conv_delta is not None:
                score_delta = Decimal(str(conv_delta))

        # 2. Check boss threshold proximity
        try:
            from nikita.engine.constants import BOSS_THRESHOLDS

            threshold = BOSS_THRESHOLDS.get(ctx.chapter, Decimal("75"))
            current = ctx.relationship_score
            distance = threshold - current

            if distance <= Decimal("5") and distance > Decimal("0"):
                events.append("boss_threshold_near")
                self._logger.info(
                    "boss_threshold_near",
                    chapter=ctx.chapter,
                    score=float(current),
                    threshold=float(threshold),
                    distance=float(distance),
                )
            elif current >= threshold:
                events.append("boss_threshold_reached")
                self._logger.info(
                    "boss_threshold_reached",
                    chapter=ctx.chapter,
                    score=float(current),
                    threshold=float(threshold),
                )
        except Exception as e:
            self._logger.debug("boss_check_skipped", error=str(e))

        # 3. Validate chapter-day coherence
        try:
            from nikita.engine.constants import CHAPTER_NAMES

            if ctx.chapter not in CHAPTER_NAMES:
                self._logger.warning(
                    "invalid_chapter",
                    chapter=ctx.chapter,
                    valid_chapters=list(CHAPTER_NAMES.keys()),
                )
                events.append("invalid_chapter")
        except Exception as e:
            self._logger.debug("chapter_validation_skipped", error=str(e))

        # 4. Log score delta
        if score_delta != Decimal("0"):
            self._logger.info(
                "score_delta_read",
                delta=float(score_delta),
                chapter=ctx.chapter,
                relationship_score=float(ctx.relationship_score),
            )

        # Populate context
        ctx.score_delta = score_delta
        ctx.score_events = events
        ctx.chapter_changed = chapter_changed
        ctx.decay_applied = decay_applied

        return {
            "score_delta": score_delta,
            "events": events,
            "chapter_changed": chapter_changed,
            "decay_applied": decay_applied,
        }
