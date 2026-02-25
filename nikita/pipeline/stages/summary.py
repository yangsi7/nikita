"""Summary generation stage (T2.10).

Non-critical: logs error on failure, continues.
Uses LLM summarization when extraction_summary is unavailable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from nikita.config.models import Models
from nikita.pipeline.stages.base import BaseStage

if TYPE_CHECKING:
    from nikita.pipeline.models import PipelineContext
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


class SummaryStage(BaseStage):
    """Generate daily/weekly conversation summaries.

    Uses extraction_summary from ExtractionStage if available. Falls back
    to LLM summarization via Pydantic AI (same pattern as ExtractionStage).

    Non-critical: failure does not stop the pipeline.
    """

    name = "summary"
    is_critical = False
    timeout_seconds = 60.0

    def __init__(self, session: AsyncSession = None, **kwargs) -> None:
        super().__init__(session=session, **kwargs)

    async def _run(self, ctx: PipelineContext) -> dict | None:
        """Generate and store conversation summary.

        Priority:
        1. Use extraction_summary from ExtractionStage (already LLM-generated)
        2. Fall back to LLM summarization of raw messages
        3. Return empty summary if no content available
        """
        summary = ctx.extraction_summary or ""

        # Spec 104 Story 2: Load active arcs for summary
        active_arcs: list[str] = []
        if self._session:
            try:
                from nikita.db.repositories.thought_repository import NikitaThoughtRepository
                thought_repo = NikitaThoughtRepository(self._session)
                active_arcs = await thought_repo.get_active_arcs(user_id=ctx.user_id)
            except Exception as e:
                self._logger.warning("load_arcs_failed error=%s", str(e))

        # If extraction didn't produce a summary, try LLM summarization
        if not summary and ctx.conversation is not None:
            messages = getattr(ctx.conversation, "messages", None) or []
            if messages:
                summary = await self._summarize_with_llm(messages, active_arcs=active_arcs)

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
                source="extraction" if ctx.extraction_summary else "llm",
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

    async def _summarize_with_llm(self, messages: list, active_arcs: list[str] | None = None) -> str:
        """Generate summary using LLM via Pydantic AI.

        Uses the same pattern as ExtractionStage for consistency.
        Takes last 10 messages to stay within token limits.

        Args:
            messages: Conversation messages (JSONB dicts or objects).
            active_arcs: Optional list of active narrative arc strings.

        Returns:
            Summary string, or empty string on failure.
        """
        try:
            from pydantic_ai import Agent

            system_parts = [
                "You are a summarizer. Summarize the conversation in 1-2 sentences "
                "focusing on topics discussed and emotional tone. Be concise."
            ]

            # Arc awareness
            if active_arcs:
                arcs_text = "\n".join(f"- {arc}" for arc in active_arcs)
                system_parts.append(
                    f"\n\nActive storylines to reference if relevant:\n{arcs_text}"
                )

            agent = Agent(
                model=Models.sonnet(),
                output_type=str,
                system_prompt="".join(system_parts),
            )

            # Format messages for summarization (last 10 max)
            text = "\n".join(
                f"{m.get('role', 'user')}: {m.get('content', '')}"
                for m in messages[-10:]
                if isinstance(m, dict) and m.get("content")
            )

            if not text:
                return ""

            result = await agent.run(
                f"Summarize this conversation:\n\n{text}"
            )
            # pydantic-ai 1.x uses .output, older uses .data
            output = getattr(result, "output", None) or getattr(result, "data", "")
            return output or ""

        except Exception as e:
            self._logger.warning(
                "llm_summary_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            return ""
