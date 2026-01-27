"""Summary rollups stage for pipeline.

Stage 7 in the post-processing pipeline. Updates daily summaries
with conversation data for context continuity.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.context.stages.base import PipelineStage
from nikita.db.models.conversation import Conversation

if TYPE_CHECKING:
    from nikita.context.pipeline_context import PipelineContext
    from nikita.context.stages.extraction import ExtractionResult


@dataclass
class SummaryRollupsInput:
    """Input for SummaryRollupsStage."""

    conversation: Conversation
    extraction: "ExtractionResult"


class SummaryRollupsStage(PipelineStage[SummaryRollupsInput, None]):
    """Stage 7: Update daily summaries.

    Maintains daily summary records for each user, aggregating
    conversation summaries and key moments across the day.

    Non-critical: Pipeline continues if this stage fails.
    """

    name = "summary_rollups"
    is_critical = False
    timeout_seconds = 15.0
    max_retries = 2

    def __init__(
        self,
        session: AsyncSession,
        logger: structlog.BoundLogger | None = None,
    ):
        """Initialize SummaryRollupsStage.

        Args:
            session: Database session.
            logger: Optional pre-bound logger.
        """
        super().__init__(session, logger)
        # Lazy import to avoid circular dependency
        from nikita.db.repositories.summary_repository import DailySummaryRepository

        self._summary_repo = DailySummaryRepository(session)

    async def _run(
        self,
        context: PipelineContext,
        input_data: SummaryRollupsInput,
    ) -> None:
        """Execute summary rollup.

        Args:
            context: Pipeline context with conversation data.
            input_data: Conversation and extraction data.

        Returns:
            None on success.
        """
        conversation = input_data.conversation
        extraction = input_data.extraction

        # Get today's date in UTC
        today = datetime.now(UTC).date()

        # Get existing summary for today
        summary = await self._summary_repo.get_for_date(
            user_id=conversation.user_id,
            summary_date=today,
        )

        if summary is None:
            # Create new daily summary
            await self._summary_repo.create_summary(
                user_id=conversation.user_id,
                summary_date=today,
                summary_text=extraction.summary,
                key_moments=[
                    {
                        "source": str(conversation.id),
                        "moments": extraction.key_moments,
                    }
                ],
                emotional_tone=extraction.emotional_tone,
            )
            self._logger.info(
                "daily_summary_created",
                user_id=str(conversation.user_id),
                date=str(today),
            )
        else:
            # Update existing summary - append conversation data
            existing_moments = summary.key_moments or []
            existing_moments.append(
                {
                    "source": str(conversation.id),
                    "moments": extraction.key_moments,
                }
            )

            # Combine summary texts
            combined_text = (
                f"{summary.summary_text or ''}\n\n{extraction.summary}".strip()
            )

            await self._summary_repo.update_summary(
                summary_id=summary.id,
                summary_text=combined_text,
                key_moments=existing_moments,
            )
            self._logger.info(
                "daily_summary_updated",
                user_id=str(conversation.user_id),
                date=str(today),
                conversation_count=len(existing_moments),
            )

        return None
