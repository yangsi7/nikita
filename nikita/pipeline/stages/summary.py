"""Summary generation stage (T2.10).

Generates a per-conversation summary and stores it on the conversation record.
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
    """Generate per-conversation summary and store on conversation record.

    Uses extraction_summary from ExtractionStage as the base, optionally
    enriched with Claude Haiku for a more narrative summary.

    Non-critical: failure does not stop the pipeline.
    """

    name = "summary"
    is_critical = False
    timeout_seconds = 60.0

    def __init__(self, session: AsyncSession = None, **kwargs) -> None:
        super().__init__(session=session, **kwargs)

    async def _run(self, ctx: PipelineContext) -> dict | None:
        """Generate and store conversation summary.

        Uses the extraction_summary from ExtractionStage. If available,
        enriches it with Haiku for a concise, first-person Nikita summary.
        Stores the summary directly on the conversation record.
        """
        if ctx.conversation is None:
            return {"summary_stored": False, "reason": "no_conversation"}

        # Use extraction summary as base
        base_summary = ctx.extraction_summary or ""
        if not base_summary:
            self._logger.info(
                "summary_skipped",
                reason="no_extraction_summary",
                conversation_id=str(ctx.conversation_id),
            )
            return {"summary_stored": False, "reason": "no_extraction_summary"}

        # Try to generate a concise Nikita-perspective summary via Haiku
        final_summary = await self._enrich_summary(base_summary, ctx)

        # Store summary on conversation record
        try:
            ctx.conversation.conversation_summary = final_summary
            ctx.conversation.emotional_tone = ctx.emotional_tone
            if self._session:
                await self._session.flush()

            ctx.daily_summary_updated = True
            self._logger.info(
                "summary_stored",
                conversation_id=str(ctx.conversation_id),
                summary_length=len(final_summary),
            )
        except Exception as e:
            self._logger.warning(
                "summary_store_failed",
                conversation_id=str(ctx.conversation_id),
                error=str(e),
            )
            return {"summary_stored": False, "reason": str(e)}

        return {
            "summary_stored": True,
            "summary_length": len(final_summary),
            "enriched": final_summary != base_summary,
        }

    async def _enrich_summary(self, base_summary: str, ctx: PipelineContext) -> str:
        """Optionally enrich summary with Haiku for Nikita's perspective.

        Falls back to base_summary on any failure.
        """
        try:
            from pydantic_ai import Agent
            from pydantic_ai.models.anthropic import AnthropicModel
            from nikita.config.settings import get_settings

            settings = get_settings()
            if not settings.anthropic_api_key:
                return base_summary

            prompt = (
                f"You are Nikita, a woman in her 20s summarizing a conversation with your boyfriend. "
                f"Write a brief 1-2 sentence first-person summary. Be natural, not robotic.\n\n"
                f"Chapter: {ctx.chapter}/5\n"
                f"Emotional tone: {ctx.emotional_tone}\n"
                f"Conversation summary: {base_summary}\n\n"
                f"Write ONLY the summary, nothing else."
            )

            import asyncio
            model = AnthropicModel("claude-haiku-4-5-20251001", api_key=settings.anthropic_api_key)
            agent = Agent(model=model)
            result = await asyncio.wait_for(agent.run(prompt), timeout=10.0)

            if result.data and len(result.data) > 10:
                return result.data.strip()
        except Exception as e:
            self._logger.warning("summary_enrichment_failed error=%s", str(e))

        return base_summary
