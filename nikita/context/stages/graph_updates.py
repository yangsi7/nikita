"""Graph Updates Stage - Update Neo4j knowledge graphs.

Spec 037 T2.7: Stage 6 of post-processing pipeline.
Updates Neo4j with extracted facts and relationship episodes.
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from nikita.context.pipeline_context import PipelineContext
from nikita.context.stages.base import PipelineStage, StageError
from nikita.context.stages.circuit_breaker import CircuitBreaker
from nikita.context.stages.extraction import ExtractionResult
from nikita.db.models.conversation import Conversation


# Shared circuit breaker for Neo4j (module-level singleton)
_neo4j_circuit_breaker = CircuitBreaker(
    name="neo4j",
    failure_threshold=2,  # Lower threshold for slower recovery
    recovery_timeout=180.0,  # 3 minutes (Neo4j cold start can be 60s+)
    half_open_max_calls=2,
)


class GraphUpdatesStage(PipelineStage[tuple[Conversation, ExtractionResult], None]):
    """Stage 6: Update Neo4j knowledge graphs.

    Spec 037 T2.7:
    - AC-T2.7.1: is_critical = False (non-critical, continues on failure)
    - AC-T2.7.2: timeout_seconds = 90.0
    - AC-T2.7.3: Uses circuit breaker (threshold=2, recovery=180s)
    - AC-T2.7.4: Batch updates for atomicity
    """

    name = "graph_updates"
    is_critical = False  # Non-critical, continues on failure
    timeout_seconds = 90.0  # Neo4j cold start can be slow
    max_retries = 2

    def __init__(self, session: AsyncSession):
        """Initialize with database session.

        Args:
            session: SQLAlchemy async session
        """
        super().__init__(session)

    async def _run(
        self,
        context: PipelineContext,
        input: tuple[Conversation, ExtractionResult],
    ) -> None:
        """Update Neo4j graphs with extracted data.

        Uses context manager for NikitaMemory to ensure cleanup.

        Args:
            context: Pipeline context
            input: Tuple of (Conversation, ExtractionResult)
        """
        from nikita.memory.graphiti_client import get_memory_client

        conversation, extraction = input

        self._logger.info(
            "starting_graph_updates",
            conversation_id=str(context.conversation_id),
            facts_count=len(extraction.facts),
        )

        # Use context manager for proper resource cleanup
        async with await get_memory_client(str(conversation.user_id)) as memory:
            # Batch all updates for atomicity
            async def batch_update():
                # Add user facts
                for fact in extraction.facts:
                    content = fact.get("content", "")
                    if content:
                        await memory.add_user_fact(content)

                # Add relationship episode (summary)
                if extraction.summary:
                    await memory.add_relationship_episode(
                        description=extraction.summary,
                        episode_type="conversation",
                    )

                # Add thoughts as Nikita events (limit to 2 to avoid spam)
                for thought in extraction.thoughts[:2]:
                    content = thought.get("content", "")
                    if content:
                        await memory.add_nikita_event(
                            description=content,
                            event_type="thought",
                        )

            # Execute through circuit breaker
            try:
                await _neo4j_circuit_breaker.call(batch_update)
            except Exception as e:
                # Record error in context but don't fail the stage
                context.stage_errors[self.name] = str(e)
                self._logger.error(
                    "graph_update_failed",
                    error=str(e),
                    exc_info=True,
                )
                raise StageError(
                    stage_name=self.name,
                    message=f"Graph update failed: {e}",
                    recoverable=True,
                ) from e

        self._logger.info(
            "graph_updates_complete",
            conversation_id=str(context.conversation_id),
        )
