"""Background task routes for pg_cron triggers.

These endpoints are called by pg_cron + Supabase Edge Functions:
- POST /tasks/decay - Apply daily decay to all active users
- POST /tasks/deliver - Process pending message deliveries
- POST /tasks/summary - Generate daily summaries

AC Coverage: Phase 3 background task infrastructure
"""

from fastapi import APIRouter, Depends, HTTPException, Header

from nikita.config.settings import get_settings
from nikita.db.database import get_session_maker
from nikita.db.dependencies import SummaryRepoDep, UserRepoDep
from nikita.db.models.job_execution import JobName
from nikita.db.repositories.job_execution_repository import JobExecutionRepository

router = APIRouter()


def _get_task_secret() -> str | None:
    """Get task authentication secret from settings."""
    settings = get_settings()
    return settings.telegram_webhook_secret


async def verify_task_secret(
    authorization: str | None = Header(None, alias="Authorization"),
) -> None:
    """Verify internal task secret.

    Uses same secret as Telegram webhook for simplicity.
    Can be upgraded to service account auth later.

    Args:
        authorization: Authorization header value.

    Raises:
        HTTPException: If authorization is missing or invalid.
    """
    secret = _get_task_secret()

    # If no secret configured, allow requests (development mode)
    if secret is None:
        return

    expected = f"Bearer {secret}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.post("/decay")
async def apply_daily_decay(
    user_repo: UserRepoDep,
    _: None = Depends(verify_task_secret),
):
    """Apply daily decay to all active users.

    Called by pg_cron daily at midnight UTC.

    Decay rates vary by chapter:
    - Chapter 1: -0.5/day
    - Chapter 2: -1.0/day
    - Chapter 3: -1.5/day
    - Chapter 4: -2.0/day
    - Chapter 5: -2.5/day

    Returns:
        Dict with status and affected user count.
    """
    session_maker = get_session_maker()
    async with session_maker() as session:
        job_repo = JobExecutionRepository(session)
        execution = await job_repo.start_execution(JobName.DECAY.value)
        await session.commit()

        try:
            # TODO: Implement when scoring engine ready (Phase 3)
            # affected = await user_repo.apply_decay_to_all()
            affected_users = 0

            result = {"status": "ok", "affected_users": affected_users}
            await job_repo.complete_execution(execution.id, result=result)
            await session.commit()
            return result

        except Exception as e:
            result = {"status": "error", "error": str(e)}
            await job_repo.fail_execution(execution.id, result=result)
            await session.commit()
            return result


@router.post("/deliver")
async def deliver_pending_messages(
    _: None = Depends(verify_task_secret),
):
    """Process pending message deliveries.

    Called by pg_cron every minute to check for scheduled messages.

    Delayed delivery is based on chapter:
    - Chapter 1: 2-5 minute delays
    - Chapter 5: Instant delivery

    Returns:
        Dict with status and delivered message count.
    """
    session_maker = get_session_maker()
    async with session_maker() as session:
        job_repo = JobExecutionRepository(session)
        execution = await job_repo.start_execution(JobName.DELIVER.value)
        await session.commit()

        try:
            # TODO: Implement when scheduled_events table ready (Phase 3)
            delivered = 0

            result = {"status": "ok", "delivered": delivered}
            await job_repo.complete_execution(execution.id, result=result)
            await session.commit()
            return result

        except Exception as e:
            result = {"status": "error", "error": str(e)}
            await job_repo.fail_execution(execution.id, result=result)
            await session.commit()
            return result


@router.post("/summary")
async def generate_daily_summaries(
    summary_repo: SummaryRepoDep,
    _: None = Depends(verify_task_secret),
):
    """Generate daily summaries for all users.

    Called by pg_cron daily at 23:59 UTC.

    Creates a daily_summary record with:
    - Score start/end
    - Decay applied
    - Conversation count
    - Nikita's summary text (LLM generated)

    Returns:
        Dict with status and generated summary count.
    """
    session_maker = get_session_maker()
    async with session_maker() as session:
        job_repo = JobExecutionRepository(session)
        execution = await job_repo.start_execution(JobName.SUMMARY.value)
        await session.commit()

        try:
            # TODO: Implement when LLM summary generation ready (Phase 3)
            summaries_generated = 0

            result = {"status": "ok", "summaries_generated": summaries_generated}
            await job_repo.complete_execution(execution.id, result=result)
            await session.commit()
            return result

        except Exception as e:
            result = {"status": "error", "error": str(e)}
            await job_repo.fail_execution(execution.id, result=result)
            await session.commit()
            return result


@router.post("/cleanup")
async def cleanup_expired_registrations(
    _: None = Depends(verify_task_secret),
):
    """Clean up expired pending registrations.

    Called by pg_cron hourly.

    Removes pending_registrations older than 10 minutes.

    Returns:
        Dict with status and cleaned up count.
    """
    from nikita.db.repositories.pending_registration_repository import (
        PendingRegistrationRepository,
    )

    session_maker = get_session_maker()
    async with session_maker() as session:
        job_repo = JobExecutionRepository(session)
        execution = await job_repo.start_execution(JobName.CLEANUP.value)
        await session.commit()

        try:
            repo = PendingRegistrationRepository(session)
            cleaned = await repo.cleanup_expired()
            await session.commit()

            result = {"status": "ok", "cleaned_up": cleaned}
            await job_repo.complete_execution(execution.id, result=result)
            await session.commit()
            return result

        except Exception as e:
            result = {"status": "error", "error": str(e), "cleaned_up": 0}
            await job_repo.fail_execution(execution.id, result=result)
            await session.commit()
            return result


@router.post("/process-conversations")
async def process_stale_conversations(
    _: None = Depends(verify_task_secret),
):
    """Detect and process stale conversations.

    Called by pg_cron every minute.

    Finds text conversations with no messages for 15+ minutes
    and triggers the post-processing pipeline for each.

    Pipeline stages:
    1. Ingestion - Mark as processing
    2. Entity & Fact Extraction - Extract facts from transcript
    3. Conversation Analysis - Summarize, detect tone
    4. Thread Extraction - Find unresolved topics
    5. Inner Life Generation - Simulate Nikita's thoughts
    6. Graph Updates - Update Neo4j knowledge graphs
    7. Summary Rollups - Update daily summaries
    8. Cache Invalidation - Clear cached prompts

    Returns:
        Dict with status and processed conversation count.
    """
    from nikita.context.session_detector import detect_stale_sessions

    session_maker = get_session_maker()
    async with session_maker() as session:
        job_repo = JobExecutionRepository(session)
        execution = await job_repo.start_execution(
            JobName.PROCESS_CONVERSATIONS.value
        )
        await session.commit()

        try:
            # Detect stale sessions and mark them for processing
            queued_ids = await detect_stale_sessions(
                session=session,
                timeout_minutes=15,
                limit=50,
            )
            await session.commit()

            # TODO: Trigger actual post-processing pipeline for each
            # This will be implemented in CTX-06
            # For now, just return the count of detected sessions

            result = {
                "status": "ok",
                "detected": len(queued_ids),
                "processed": 0,  # Will be updated when pipeline is ready
            }
            await job_repo.complete_execution(execution.id, result=result)
            await session.commit()
            return result

        except Exception as e:
            result = {"status": "error", "error": str(e), "detected": 0, "processed": 0}
            await job_repo.fail_execution(execution.id, result=result)
            await session.commit()
            return result
