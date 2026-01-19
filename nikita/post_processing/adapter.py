"""Adapter for Post-Processing Pipeline (Spec 029).

Provides interface compatibility with the old post_processor.py
while using the new PostProcessingPipeline internally.

This adapter:
1. Takes a list of conversation_ids (old interface)
2. Looks up user_id for each conversation
3. Calls the new pipeline's process() method
4. Returns results compatible with the old PipelineResult format
"""

import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.repositories.conversation_repository import ConversationRepository
from nikita.post_processing.pipeline import (
    PostProcessingPipeline,
    ProcessingResult,
    get_post_processing_pipeline,
)

logger = logging.getLogger(__name__)


@dataclass
class AdapterResult:
    """Result of post-processing a single conversation.

    Interface-compatible with the old PipelineResult from context/post_processor.py.
    """

    conversation_id: UUID
    success: bool
    stage_reached: str
    error: str | None = None

    # Extracted data
    summary: str | None = None
    emotional_tone: str | None = None
    extracted_entities: dict[str, Any] | None = None
    threads_created: int = 0
    thoughts_created: int = 0
    vice_signals_processed: int = 0

    # New fields from post_processing pipeline
    processing_result: ProcessingResult | None = None


async def process_conversations(
    session: AsyncSession,
    conversation_ids: list[UUID],
) -> list[AdapterResult]:
    """Process multiple conversations using the new pipeline.

    Interface-compatible with the old process_conversations function
    from nikita/context/post_processor.py.

    Args:
        session: Database session.
        conversation_ids: List of conversation UUIDs to process.

    Returns:
        List of AdapterResult for each conversation.
    """
    results: list[AdapterResult] = []
    conv_repo = ConversationRepository(session)
    pipeline = get_post_processing_pipeline()

    for conv_id in conversation_ids:
        try:
            # Look up conversation to get user_id
            conversation = await conv_repo.get(conv_id)
            if not conversation:
                results.append(
                    AdapterResult(
                        conversation_id=conv_id,
                        success=False,
                        stage_reached="lookup",
                        error=f"Conversation {conv_id} not found",
                    )
                )
                continue

            user_id = conversation.user_id

            # Get transcript from conversation messages
            messages = await conv_repo.get_messages(conv_id)
            transcript = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
                if msg.content
            ]

            # Run new pipeline
            processing_result = await pipeline.process(
                user_id=user_id,
                conversation_id=conv_id,
                transcript=transcript,
            )

            # Convert to AdapterResult
            result = AdapterResult(
                conversation_id=conv_id,
                success=processing_result.success,
                stage_reached=_get_stage_reached(processing_result),
                error=_get_first_error(processing_result),
                processing_result=processing_result,
            )

            # Extract summary if available
            if processing_result.package:
                result.summary = processing_result.package.today_summary

            # Count extracted entities
            for step in processing_result.steps:
                if step.name == "graph_update" and step.metadata:
                    result.extracted_entities = step.metadata
                    result.threads_created = step.metadata.get("facts_extracted", 0)

            results.append(result)

        except Exception as e:
            logger.exception(f"Failed to process conversation {conv_id}")
            results.append(
                AdapterResult(
                    conversation_id=conv_id,
                    success=False,
                    stage_reached="error",
                    error=str(e),
                )
            )

    return results


def _get_stage_reached(result: ProcessingResult) -> str:
    """Get the last successfully completed stage."""
    completed = result.completed_steps
    if not completed:
        return "none"
    return completed[-1].name


def _get_first_error(result: ProcessingResult) -> str | None:
    """Get the first error message from failed steps."""
    failed = result.failed_steps
    if not failed:
        return None
    return failed[0].error_message
