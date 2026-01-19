"""Pipeline Trigger for Post-Processing (Spec 021, T024).

Provides integration points to trigger the post-processing pipeline
after conversations end.

AC-T024.1: ConversationRepository.save() triggers pipeline via BackgroundTasks
AC-T024.2: Pipeline runs async (non-blocking)
AC-T024.3: Logging for pipeline trigger
AC-T024.4: Feature flag `enable_post_processing_pipeline`
"""

import logging
from uuid import UUID

from nikita.config.settings import get_settings
from nikita.post_processing.pipeline import (
    PostProcessingPipeline,
    ProcessingResult,
    get_post_processing_pipeline,
)

logger = logging.getLogger(__name__)


def is_pipeline_enabled() -> bool:
    """Check if post-processing pipeline is enabled.

    Returns:
        True if pipeline is enabled via feature flag.
    """
    settings = get_settings()
    return getattr(settings, "enable_post_processing_pipeline", True)


async def trigger_pipeline(
    user_id: UUID,
    conversation_id: UUID,
    transcript: list[dict[str, str]] | None = None,
) -> ProcessingResult | None:
    """Trigger post-processing pipeline for a conversation.

    This function is designed to be called from BackgroundTasks
    or directly after a conversation ends.

    Args:
        user_id: User ID to process for.
        conversation_id: Conversation that ended.
        transcript: Optional conversation transcript.

    Returns:
        ProcessingResult if pipeline ran, None if disabled.
    """
    if not is_pipeline_enabled():
        logger.debug(
            f"Post-processing pipeline disabled, skipping for user {user_id}"
        )
        return None

    logger.info(
        f"Triggering post-processing pipeline for user {user_id}, "
        f"conversation {conversation_id}"
    )

    try:
        pipeline = get_post_processing_pipeline()
        result = await pipeline.process(
            user_id=user_id,
            conversation_id=conversation_id,
            transcript=transcript,
        )

        if result.success:
            logger.info(
                f"Post-processing complete for user {user_id}: "
                f"all {len(result.completed_steps)} steps succeeded"
            )
        elif result.partial_success:
            logger.warning(
                f"Post-processing partial success for user {user_id}: "
                f"{len(result.completed_steps)} completed, "
                f"{len(result.failed_steps)} failed"
            )
        else:
            logger.error(
                f"Post-processing failed for user {user_id}: "
                f"all {len(result.failed_steps)} steps failed"
            )

        return result

    except Exception as e:
        logger.exception(
            f"Unexpected error in post-processing pipeline for user {user_id}: {e}"
        )
        return None


async def trigger_pipeline_background(
    user_id: UUID,
    conversation_id: UUID,
    transcript: list[dict[str, str]] | None = None,
) -> None:
    """Background-safe wrapper for trigger_pipeline.

    Catches all exceptions to prevent background task failures
    from affecting the main application.

    Args:
        user_id: User ID to process for.
        conversation_id: Conversation that ended.
        transcript: Optional conversation transcript.
    """
    try:
        await trigger_pipeline(user_id, conversation_id, transcript)
    except Exception as e:
        # Log but don't re-raise to prevent background task failure
        logger.exception(
            f"Background pipeline trigger failed for user {user_id}: {e}"
        )


def add_pipeline_trigger_to_background_tasks(
    background_tasks: any,
    user_id: UUID,
    conversation_id: UUID,
    transcript: list[dict[str, str]] | None = None,
) -> None:
    """Add pipeline trigger to FastAPI BackgroundTasks.

    This is the recommended way to trigger the pipeline from
    API endpoints.

    Args:
        background_tasks: FastAPI BackgroundTasks instance.
        user_id: User ID to process for.
        conversation_id: Conversation that ended.
        transcript: Optional conversation transcript.

    Example:
        @router.post("/conversations/{conversation_id}/close")
        async def close_conversation(
            conversation_id: UUID,
            background_tasks: BackgroundTasks,
        ):
            # ... close conversation logic ...

            add_pipeline_trigger_to_background_tasks(
                background_tasks,
                user_id=user.id,
                conversation_id=conversation_id,
            )

            return {"status": "closed"}
    """
    if not is_pipeline_enabled():
        logger.debug("Post-processing pipeline disabled, not adding to background tasks")
        return

    background_tasks.add_task(
        trigger_pipeline_background,
        user_id=user_id,
        conversation_id=conversation_id,
        transcript=transcript,
    )
    logger.debug(
        f"Added pipeline trigger to background tasks for user {user_id}"
    )
