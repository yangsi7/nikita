"""Persistence stage — write extracted thoughts/threads to DB (Spec 067).

Non-critical: DB write failure must not stop the pipeline.
Runs after memory_update, before life_sim.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from nikita.pipeline.stages.base import BaseStage

if TYPE_CHECKING:
    from nikita.pipeline.models import PipelineContext
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


class PersistenceStage(BaseStage):
    """Persist extracted thoughts and threads to database tables.

    Writes ctx.extracted_thoughts → nikita_thoughts table
    Writes ctx.extracted_threads → conversation_threads table

    Non-critical: failure logs and continues pipeline.
    """

    name = "persistence"
    is_critical = False
    timeout_seconds = 15.0

    def __init__(self, session: AsyncSession = None, **kwargs) -> None:
        super().__init__(session=session, **kwargs)

    async def _run(self, ctx: PipelineContext) -> dict | None:
        """Persist extracted thoughts and threads to DB."""
        if not self._session:
            self._logger.warning("persistence_no_session")
            return {"thoughts_persisted": 0, "threads_persisted": 0, "skipped": True}

        thoughts_persisted = 0
        threads_persisted = 0

        # Persist thoughts
        if ctx.extracted_thoughts:
            thoughts_persisted = await self._persist_thoughts(ctx)

        # Persist threads
        if ctx.extracted_threads:
            threads_persisted = await self._persist_threads(ctx)

        # Spec 104 Story 3: Thought auto-resolution
        thoughts_resolved = 0
        if ctx.extracted_facts and self._session:
            try:
                from nikita.db.repositories.thought_repository import NikitaThoughtRepository
                thought_repo = NikitaThoughtRepository(self._session)
                fact_strings = [
                    f if isinstance(f, str) else f.get("fact", str(f))
                    for f in ctx.extracted_facts
                ]
                thoughts_resolved = await thought_repo.resolve_matching_thoughts(
                    user_id=ctx.user_id, facts=fact_strings
                )
            except Exception as e:
                self._logger.warning("thought_resolution_failed error=%s", str(e))

        # Record counts on context
        ctx.thoughts_persisted = thoughts_persisted
        ctx.threads_persisted = threads_persisted

        self._logger.info(
            "persistence_complete thoughts=%d threads=%d",
            thoughts_persisted,
            threads_persisted,
        )

        return {
            "thoughts_persisted": thoughts_persisted,
            "threads_persisted": threads_persisted,
        }

    async def _persist_thoughts(self, ctx: PipelineContext) -> int:
        """Persist extracted thoughts to nikita_thoughts table.

        ExtractionStage produces list[str] (from ExtractionResult.thoughts),
        but PipelineContext types it as list[dict[str, Any]].
        Handle both runtime types.
        """
        try:
            from nikita.db.repositories.thought_repository import NikitaThoughtRepository

            repo = NikitaThoughtRepository(self._session)

            # Map extracted data to bulk_create format
            # ExtractionStage actually produces list[str], not list[dict]
            thoughts_data = []
            for item in ctx.extracted_thoughts:
                if isinstance(item, str):
                    thoughts_data.append({
                        "thought_type": "reflection",  # Default type for extracted thoughts
                        "content": item,
                    })
                elif isinstance(item, dict):
                    thoughts_data.append({
                        "thought_type": item.get("thought_type", "reflection"),
                        "content": item.get("content", str(item)),
                    })

            if not thoughts_data:
                return 0

            created = await repo.bulk_create_thoughts(
                user_id=ctx.user_id,
                thoughts_data=thoughts_data,
                source_conversation_id=ctx.conversation_id,
            )
            return len(created)

        except Exception as e:
            self._logger.warning("persist_thoughts_failed error=%s", str(e))
            return 0

    async def _persist_threads(self, ctx: PipelineContext) -> int:
        """Persist extracted threads to conversation_threads table.

        Same type handling as thoughts — ExtractionStage produces list[str].
        """
        try:
            from nikita.db.repositories.thread_repository import ConversationThreadRepository

            repo = ConversationThreadRepository(self._session)

            # Map extracted data to bulk_create format
            threads_data = []
            for item in ctx.extracted_threads:
                if isinstance(item, str):
                    threads_data.append({
                        "thread_type": "unresolved",  # Default type for extracted threads
                        "content": item,
                    })
                elif isinstance(item, dict):
                    threads_data.append({
                        "thread_type": item.get("thread_type", "unresolved"),
                        "content": item.get("content", str(item)),
                    })

            if not threads_data:
                return 0

            created = await repo.bulk_create_threads(
                user_id=ctx.user_id,
                threads_data=threads_data,
                source_conversation_id=ctx.conversation_id,
            )
            return len(created)

        except Exception as e:
            self._logger.warning("persist_threads_failed error=%s", str(e))
            return 0
