"""Extraction stage - extracts entities/facts/threads from conversation (T2.3).

CRITICAL stage: failure stops the pipeline.
Uses Pydantic AI with Claude to extract structured data from conversations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog
from pydantic import BaseModel
from pydantic_ai import Agent

from nikita.pipeline.stages.base import BaseStage, StageError
from nikita.pipeline.models import PipelineContext

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


class ExtractionResult(BaseModel):
    """Structured extraction result from LLM."""
    facts: list[str] = []
    threads: list[str] = []
    thoughts: list[str] = []
    summary: str = ""
    emotional_tone: str = "neutral"


class ExtractionStage(BaseStage):
    """Extract entities, facts, threads, and thoughts from a conversation.

    Uses Pydantic AI (Claude) to analyze conversation messages and extract
    structured data for downstream stages.

    This is a CRITICAL stage - failure stops the pipeline.
    """

    name = "extraction"
    is_critical = True
    timeout_seconds = 120.0

    def __init__(self, session: AsyncSession = None, **kwargs) -> None:
        super().__init__(session=session, **kwargs)
        self._agent = None

    def _get_agent(self) -> Agent:
        """Lazy-load extraction agent to avoid import overhead."""
        if self._agent is None:
            self._agent = Agent(
                model="anthropic:claude-sonnet-4-5-20250929",
                result_type=ExtractionResult,
                system_prompt=(
                    "You are an AI assistant that extracts structured information from conversations. "
                    "Extract:\n"
                    "- facts: Concrete facts about the user (what they said, did, believe)\n"
                    "- threads: Ongoing conversation topics or unresolved points\n"
                    "- thoughts: Nikita's potential internal thoughts/observations\n"
                    "- summary: Brief summary of the conversation\n"
                    "- emotional_tone: Overall emotional tone (positive/neutral/negative/mixed)\n"
                ),
            )
        return self._agent

    async def _run(self, ctx: PipelineContext) -> dict | None:
        """Extract entities and facts from conversation.

        Populates ctx.extracted_facts, extracted_threads,
        extracted_thoughts, extraction_summary, emotional_tone.
        """
        if ctx.conversation is None:
            raise StageError(self.name, "No conversation loaded in context")

        messages = []
        if hasattr(ctx.conversation, "messages"):
            messages = ctx.conversation.messages or []

        if not messages:
            self._logger.info("extraction_skipped", reason="no messages")
            return {"facts": [], "threads": [], "thoughts": [], "summary": "", "tone": "neutral"}

        # Format conversation for LLM (messages are JSONB dicts, not objects)
        conversation_text = "\n".join([
            f"{msg.get('role', 'unknown')}: {msg.get('content', '')}"
            for msg in messages
            if isinstance(msg, dict) and msg.get('content')
        ])

        try:
            agent = self._get_agent()
            result = await agent.run(
                f"Extract information from this conversation:\n\n{conversation_text}"
            )
            extraction_data = result.data
        except Exception as e:
            raise StageError(
                self.name,
                f"Extraction LLM call failed: {type(e).__name__}: {e}",
                recoverable=False,
            )

        # Populate context
        ctx.extracted_facts = extraction_data.facts
        ctx.extracted_threads = extraction_data.threads
        ctx.extracted_thoughts = extraction_data.thoughts
        ctx.extraction_summary = extraction_data.summary
        ctx.emotional_tone = extraction_data.emotional_tone

        return {
            "facts": extraction_data.facts,
            "threads": extraction_data.threads,
            "thoughts": extraction_data.thoughts,
            "summary": extraction_data.summary,
            "emotional_tone": extraction_data.emotional_tone,
        }
