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
        """Generate and store conversation summary.

        Uses the extraction_summary from ExtractionStage as the base summary.
        If extraction_summary is empty, generates one from conversation messages.
        Stores the summary on the conversation object and in ctx.
        """
        summary = ctx.extraction_summary or ""

        # If extraction didn't produce a summary, try to generate one from messages
        if not summary and ctx.conversation is not None:
            messages = getattr(ctx.conversation, "messages", None) or []
            if messages:
                # Build a simple summary from the last few messages
                user_msgs = [
                    m.get("content", "") if isinstance(m, dict) else str(m)
                    for m in messages
                    if (isinstance(m, dict) and m.get("role") == "user")
                ]
                if user_msgs:
                    # Take last 3 user messages as summary seed
                    recent = user_msgs[-3:]
                    summary = "User discussed: " + "; ".join(
                        msg[:100] for msg in recent
                    )

        if summary:
            # Store summary on conversation if available
            # Note: Use try/except instead of hasattr() to avoid MissingGreenlet
            # (hasattr triggers SQLAlchemy lazy-loading in sync context)
            if ctx.conversation is not None:
                try:
                    ctx.conversation.conversation_summary = summary
                except Exception:
                    pass  # Non-critical: summary stored via mark_processed in tasks.py

            # Also store extraction summary back on ctx for mark_processed
            if not ctx.extraction_summary:
                ctx.extraction_summary = summary

            ctx.daily_summary_updated = True
            self._logger.info(
                "summary_generated",
                conversation_id=str(ctx.conversation_id),
                summary_length=len(summary),
            )
        else:
            self._logger.info(
                "summary_skipped",
                reason="no_content",
                conversation_id=str(ctx.conversation_id),
            )

        return {
            "summary": summary,
            "summary_length": len(summary),
            "daily_updated": ctx.daily_summary_updated,
        }
