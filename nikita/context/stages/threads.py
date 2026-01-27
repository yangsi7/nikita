"""Threads creation stage for pipeline.

Stage 4 in the post-processing pipeline. Extracts and creates
conversation threads from LLM-identified unresolved topics,
questions, and promises.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.context.stages.base import PipelineStage, StageError

if TYPE_CHECKING:
    from nikita.context.pipeline_context import PipelineContext
    from nikita.db.models.conversation import Conversation


@dataclass
class ThreadsInput:
    """Input for ThreadsStage.

    Attributes:
        conversation: Source conversation model.
        threads: Extracted thread data with 'type' and 'content' keys.
        resolved_ids: Thread UUIDs to mark as resolved.
    """

    conversation: Conversation
    threads: list[dict[str, str]]
    resolved_ids: list[UUID]


class ThreadsStage(PipelineStage[ThreadsInput, int]):
    """Stage 4: Create conversation threads.

    Handles:
    - Resolving existing threads that were addressed in this conversation
    - Creating new threads from LLM extraction (follow_ups, questions, promises, topics)
    - Filtering invalid thread types (only accepts THREAD_TYPES)

    Non-critical: Pipeline continues if this stage fails.
    """

    name = "threads"
    is_critical = False
    timeout_seconds = 10.0
    max_retries = 2

    def __init__(
        self,
        session: AsyncSession,
        logger: structlog.BoundLogger | None = None,
    ):
        """Initialize ThreadsStage.

        Args:
            session: Database session.
            logger: Optional pre-bound logger.
        """
        super().__init__(session, logger)
        # Lazy import to avoid circular dependency
        from nikita.db.repositories.thread_repository import ConversationThreadRepository

        self._thread_repo = ConversationThreadRepository(session)

    async def _run(
        self,
        context: PipelineContext,
        input: ThreadsInput,
    ) -> int:
        """Execute thread creation stage.

        Args:
            context: Pipeline context with conversation data.
            input: ThreadsInput with conversation, threads, and resolved_ids.

        Returns:
            Number of threads created.

        Raises:
            StageError: If thread creation fails unexpectedly.
        """
        conversation = input.conversation
        threads = input.threads
        resolved_ids = input.resolved_ids

        # Step 1: Resolve existing threads with enhanced logging
        resolved_count = 0
        for thread_id in resolved_ids:
            start_time = time.perf_counter()
            try:
                # Get thread to calculate age before resolving
                thread = await self._thread_repo.get(thread_id)
                if thread is None:
                    self._logger.info(
                        "thread_resolve_skipped",
                        thread_id=str(thread_id),
                        resolution_reason="not_found",
                    )
                    continue

                # Calculate thread age in hours
                thread_age_hours = 0.0
                if thread.created_at:
                    age_delta = datetime.now(UTC) - thread.created_at
                    thread_age_hours = age_delta.total_seconds() / 3600

                # Resolve the thread
                await self._thread_repo.resolve_thread(thread_id)
                resolution_time_ms = (time.perf_counter() - start_time) * 1000
                resolved_count += 1

                self._logger.info(
                    "thread_resolved",
                    thread_id=str(thread_id),
                    resolution_reason="user_addressed",
                    resolution_time_ms=round(resolution_time_ms, 2),
                    thread_age_hours=round(thread_age_hours, 2),
                    thread_type=thread.thread_type if hasattr(thread, "thread_type") else None,
                )
            except ValueError as e:
                resolution_time_ms = (time.perf_counter() - start_time) * 1000
                # Thread not found or already resolved - log with reason
                self._logger.info(
                    "thread_resolve_skipped",
                    thread_id=str(thread_id),
                    resolution_reason="already_resolved",
                    resolution_time_ms=round(resolution_time_ms, 2),
                    error=str(e),
                )
            except Exception as e:
                resolution_time_ms = (time.perf_counter() - start_time) * 1000
                # Log failed resolutions with error details
                self._logger.warning(
                    "thread_resolve_failed",
                    thread_id=str(thread_id),
                    resolution_reason="error",
                    resolution_time_ms=round(resolution_time_ms, 2),
                    error=str(e),
                    exc_info=True,
                )

        # Step 2: Filter and create new threads
        from nikita.db.models.context import THREAD_TYPES

        threads_data = [
            {"thread_type": t["type"], "content": t["content"]}
            for t in threads
            if "type" in t and "content" in t and t["type"] in THREAD_TYPES
        ]

        if not threads_data:
            self._logger.debug("no_valid_threads", raw_count=len(threads))
            return 0

        # Step 3: Bulk create threads
        await self._thread_repo.bulk_create_threads(
            user_id=conversation.user_id,
            threads_data=threads_data,
            source_conversation_id=conversation.id,
        )

        self._logger.info(
            "threads_created",
            count=len(threads_data),
            resolved_count=resolved_count,
            resolve_attempted=len(resolved_ids),
            conversation_id=str(conversation.id),
        )

        return len(threads_data)
