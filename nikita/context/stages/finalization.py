"""Finalization stage for pipeline.

Stage 8 in the post-processing pipeline. Marks conversation as
processed/failed and ensures no conversations get stuck.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.context.stages.base import PipelineStage

if TYPE_CHECKING:
    from nikita.context.pipeline_context import PipelineContext
    from nikita.context.stages.extraction import ExtractionResult


@dataclass
class FinalizationInput:
    """Input for FinalizationStage."""

    conversation_id: UUID
    critical_stage_failed: bool
    extraction: "ExtractionResult | None"
    extracted_entities: dict[str, Any] = field(default_factory=dict)
    stage_errors: dict[str, str] = field(default_factory=dict)


@dataclass
class FinalizationResult:
    """Result from finalization stage."""

    success: bool = False
    force_updated: bool = False
    final_status: str = "unknown"


class FinalizationStage(PipelineStage[FinalizationInput, FinalizationResult]):
    """Stage 8: Mark conversation as processed/failed.

    This is a safety-net stage that ensures conversations never
    get stuck in 'processing' state. It runs regardless of
    earlier stage failures.

    Critical: Pipeline cannot complete without marking status.
    """

    name = "finalization"
    is_critical = True  # Must mark conversation status
    timeout_seconds = 10.0
    max_retries = 3  # Extra retries for this safety-critical stage

    def __init__(
        self,
        session: AsyncSession,
        logger: structlog.BoundLogger | None = None,
    ):
        """Initialize FinalizationStage.

        Args:
            session: Database session.
            logger: Optional pre-bound logger.
        """
        super().__init__(session, logger)
        # Lazy import to avoid circular dependency
        from nikita.db.repositories.conversation_repository import (
            ConversationRepository,
        )

        self._conversation_repo = ConversationRepository(session)

    async def _run(
        self,
        context: PipelineContext,
        input_data: FinalizationInput,
    ) -> FinalizationResult:
        """Execute finalization.

        Marks the conversation as processed or failed. If the normal
        update fails, attempts a force update via raw SQL.

        Args:
            context: Pipeline context with conversation data.
            input_data: Finalization parameters.

        Returns:
            FinalizationResult with status information.
        """
        result = FinalizationResult()
        conversation_id = input_data.conversation_id
        critical_stage_failed = input_data.critical_stage_failed
        extraction = input_data.extraction

        try:
            if critical_stage_failed:
                # Critical failure - mark as failed
                await self._conversation_repo.mark_failed(conversation_id)
                result.success = False
                result.final_status = "failed"
            else:
                # Success (possibly with non-critical errors) - mark as processed
                await self._conversation_repo.mark_processed(
                    conversation_id=conversation_id,
                    summary=extraction.summary if extraction else None,
                    emotional_tone=extraction.emotional_tone if extraction else None,
                    extracted_entities=input_data.extracted_entities,
                )
                result.success = True
                result.final_status = "processed"

            self._logger.info(
                "conversation_finalized",
                conversation_id=str(conversation_id),
                status=result.final_status,
            )
            return result

        except Exception as e:
            self._logger.error(
                "finalization_failed",
                conversation_id=str(conversation_id),
                error=str(e),
                exc_info=True,
            )

            # LAST RESORT: Force update status via raw SQL
            try:
                final_status = "failed" if critical_stage_failed else "processed"
                force_success = await self._conversation_repo.force_status_update(
                    conversation_id=conversation_id,
                    status=final_status,
                )
                if force_success:
                    result.force_updated = True
                    result.success = not critical_stage_failed
                    result.final_status = final_status
                    self._logger.info(
                        "conversation_force_updated",
                        conversation_id=str(conversation_id),
                        status=final_status,
                    )
                    return result
            except Exception as force_err:
                self._logger.critical(
                    "conversation_stuck_in_processing",
                    conversation_id=str(conversation_id),
                    error=str(force_err),
                    exc_info=True,
                )
                raise RuntimeError(
                    f"Conversation {conversation_id} may be stuck in 'processing': {force_err}"
                ) from force_err

            # If force update didn't work, re-raise original error
            raise
