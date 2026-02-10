"""Memory update stage - writes extracted facts to SupabaseMemory (T2.4).

CRITICAL stage: failure stops the pipeline.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

import structlog

from nikita.pipeline.stages.base import BaseStage, StageError
from nikita.pipeline.models import PipelineContext

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


class MemoryUpdateStage(BaseStage):
    """Write extracted facts to Supabase memory_facts table.

    Deduplicates against existing facts (similarity > 0.95).
    Classifies facts into graph_type (user/relationship/nikita).

    This is a CRITICAL stage - failure stops the pipeline.
    """

    name = "memory_update"
    is_critical = True
    timeout_seconds = 60.0

    def __init__(self, session: AsyncSession = None, **kwargs) -> None:
        super().__init__(session=session, **kwargs)

    async def _run(self, ctx: PipelineContext) -> dict | None:
        """Write extracted facts to memory_facts."""
        from nikita.config.settings import get_settings
        from nikita.memory.supabase_memory import SupabaseMemory

        if not ctx.extracted_facts:
            self._logger.info("memory_update_skipped reason=no_facts")
            return {"stored": 0, "deduplicated": 0}

        settings = get_settings()
        memory = SupabaseMemory(
            session=self._session,
            user_id=ctx.user_id,
            openai_api_key=settings.openai_api_key or "",
        )

        stored = 0
        deduplicated = 0

        for fact_item in ctx.extracted_facts:
            # BUG-003 fix: Handle both str (from ExtractionResult) and dict formats
            if isinstance(fact_item, str):
                fact_text = fact_item
                graph_type = "relationship"  # default for string facts
            elif isinstance(fact_item, dict):
                fact_text = fact_item.get("content", "") or fact_item.get("fact", "")
                graph_type = self._classify_graph_type(fact_item)
            else:
                continue
            if not fact_text:
                continue

            try:
                existing = await memory.find_similar(fact_text, threshold=0.95)
                if existing:
                    deduplicated += 1
                    continue

                await memory.add_fact(
                    fact=fact_text,
                    graph_type=graph_type,
                    source="pipeline_extraction",
                    confidence=0.85,
                )
                stored += 1
            except Exception as e:
                self._logger.warning(
                    "fact_store_failed fact=%s error=%s",
                    fact_text[:50],
                    str(e),
                )

        ctx.facts_stored = stored
        ctx.facts_deduplicated = deduplicated

        return {"stored": stored, "deduplicated": deduplicated}

    def _classify_graph_type(self, fact_dict: dict) -> str:
        """Classify a fact into user/relationship/nikita graph."""
        fact_type = fact_dict.get("type", "").lower()
        content = (fact_dict.get("content", "") or fact_dict.get("fact", "")).lower()

        if fact_type in ("nikita_event", "nikita_life"):
            return "nikita"
        if "nikita" in content and ("said" in content or "told" in content or "shared" in content):
            return "relationship"
        if any(w in fact_type for w in ("preference", "fact", "personal")):
            return "user"
        return "relationship"
