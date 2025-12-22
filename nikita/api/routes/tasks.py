"""Background task routes for pg_cron triggers.

These endpoints are called by pg_cron + Supabase Edge Functions:
- POST /tasks/decay - Apply daily decay to all active users
- POST /tasks/deliver - Process pending message deliveries
- POST /tasks/summary - Generate daily summaries

AC Coverage: Phase 3 background task infrastructure
"""

import logging
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Header

logger = logging.getLogger(__name__)

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
    _: None = Depends(verify_task_secret),
):
    """Apply hourly decay to all active users.

    Called by pg_cron hourly (game is compressed timeline).

    Decay rates vary by chapter (per hour):
    - Chapter 1: -0.8%/hr, 8hr grace
    - Chapter 2: -0.6%/hr, 16hr grace
    - Chapter 3: -0.4%/hr, 24hr grace
    - Chapter 4: -0.3%/hr, 48hr grace
    - Chapter 5: -0.2%/hr, 72hr grace

    Returns:
        Dict with status and decay statistics.
    """
    from nikita.db.repositories.score_history_repository import ScoreHistoryRepository
    from nikita.db.repositories.user_repository import UserRepository
    from nikita.engine.decay.processor import DecayProcessor

    session_maker = get_session_maker()
    async with session_maker() as session:
        job_repo = JobExecutionRepository(session)
        execution = await job_repo.start_execution(JobName.DECAY.value)
        await session.commit()

        try:
            # Initialize repositories and processor
            user_repo = UserRepository(session)
            history_repo = ScoreHistoryRepository(session)
            processor = DecayProcessor(
                session=session,
                user_repository=user_repo,
                score_history_repository=history_repo,
            )

            # Process decay for all active users
            summary = await processor.process_all()
            await session.commit()

            result = {
                "status": "ok",
                "processed": summary["processed"],
                "decayed": summary["decayed"],
                "game_overs": summary["game_overs"],
            }
            await job_repo.complete_execution(execution.id, result=result)
            await session.commit()

            logger.info(
                f"[DECAY] Processed {summary['processed']} users: "
                f"{summary['decayed']} decayed, {summary['game_overs']} game overs"
            )

            return result

        except Exception as e:
            logger.error(f"[DECAY] Error: {e}", exc_info=True)
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
    from datetime import date as date_type
    from datetime import timedelta

    from sqlalchemy import func, select

    from nikita.db.models.context import ConversationThread, NikitaThought
    from nikita.db.repositories.conversation_repository import ConversationRepository
    from nikita.db.repositories.score_history_repository import ScoreHistoryRepository
    from nikita.db.repositories.summary_repository import DailySummaryRepository
    from nikita.db.repositories.user_repository import UserRepository
    from nikita.meta_prompts.service import MetaPromptService

    session_maker = get_session_maker()
    async with session_maker() as session:
        job_repo = JobExecutionRepository(session)
        execution = await job_repo.start_execution(JobName.SUMMARY.value)
        await session.commit()

        try:
            # Initialize repositories
            user_repo = UserRepository(session)
            conv_repo = ConversationRepository(session)
            score_repo = ScoreHistoryRepository(session)
            summary_repo_local = DailySummaryRepository(session)
            meta_service = MetaPromptService(session)

            # Get all active users
            active_users = await user_repo.get_active_users_for_decay()

            # Process summary for today (or yesterday if running near midnight)
            summary_date = date_type.today()
            summaries_generated = 0
            errors = []

            for user in active_users:
                try:
                    # Check if summary already exists for this date
                    existing = await summary_repo_local.get_by_date(
                        user_id=user.id,
                        summary_date=summary_date,
                    )
                    if existing:
                        continue  # Skip if already generated

                    # Get score stats for today
                    daily_stats = await score_repo.get_daily_stats(
                        user_id=user.id,
                        target_date=summary_date,
                    )

                    # Get processed conversations for today (1 day = today only)
                    conversations = await conv_repo.get_processed_conversations(
                        user_id=user.id,
                        days=1,
                        limit=20,
                    )

                    # Filter to only today's conversations
                    today_convs = [
                        c for c in conversations
                        if c.started_at.date() == summary_date
                    ]

                    # Skip users with no conversations today
                    if not today_convs:
                        continue

                    # Build conversation data for LLM
                    conversations_data = []
                    conversation_ids = []
                    for conv in today_convs:
                        conversations_data.append({
                            "summary": conv.summary or "No summary",
                            "emotional_tone": conv.emotional_tone or "neutral",
                            "key_moment": None,  # Could extract from metadata if available
                        })
                        conversation_ids.append(conv.id)

                    # Get threads created today (from these conversations)
                    threads_stmt = (
                        select(ConversationThread)
                        .where(ConversationThread.user_id == user.id)
                        .where(ConversationThread.source_conversation_id.in_(conversation_ids))
                    )
                    threads_result = await session.execute(threads_stmt)
                    threads = list(threads_result.scalars().all())
                    new_threads = [
                        {"type": t.thread_type, "content": t.content}
                        for t in threads
                    ]

                    # Get thoughts created today (from these conversations)
                    thoughts_stmt = (
                        select(NikitaThought)
                        .where(NikitaThought.user_id == user.id)
                        .where(NikitaThought.source_conversation_id.in_(conversation_ids))
                    )
                    thoughts_result = await session.execute(thoughts_stmt)
                    thoughts = list(thoughts_result.scalars().all())
                    nikita_thoughts = [t.content for t in thoughts]

                    # Calculate decay applied today from score history
                    decay_applied = Decimal("0")
                    if daily_stats.get("events_by_type"):
                        decay_count = daily_stats["events_by_type"].get("decay", 0)
                        # Estimate: each decay event is typically chapter-based
                        # This is rough - actual decay amount is in event_details
                        decay_applied = Decimal(str(decay_count * 0.5))  # Rough estimate

                    # Get score values (use current score if no history)
                    score_start = daily_stats.get("score_start") or user.relationship_score
                    score_end = daily_stats.get("score_end") or user.relationship_score

                    # Generate LLM summary
                    summary_data = await meta_service.generate_daily_summary(
                        user_id=user.id,
                        summary_date=summary_date,
                        score_start=score_start,
                        score_end=score_end,
                        decay_applied=decay_applied,
                        conversations_data=conversations_data,
                        new_facts=[],  # Facts not easily accessible here
                        new_threads=new_threads,
                        nikita_thoughts=nikita_thoughts,
                    )

                    # Store the summary
                    await summary_repo_local.create_summary(
                        user_id=user.id,
                        summary_date=summary_date,
                        score_start=score_start,
                        score_end=score_end,
                        decay_applied=decay_applied,
                        conversations_count=len(today_convs),
                        nikita_summary_text=summary_data.get("summary_text"),
                        key_events=summary_data.get("key_moments"),
                        summary_text=summary_data.get("summary_text"),
                        key_moments=summary_data.get("key_moments"),
                        emotional_tone=summary_data.get("emotional_tone"),
                        engagement_score=summary_data.get("engagement_score"),
                    )

                    summaries_generated += 1

                except Exception as user_error:
                    errors.append(f"User {user.id}: {str(user_error)}")
                    logger.warning(f"Failed to generate summary for user {user.id}: {user_error}")

            await session.commit()

            result = {
                "status": "ok",
                "summaries_generated": summaries_generated,
                "users_checked": len(active_users),
                "errors": errors[:5] if errors else [],  # First 5 errors
            }
            await job_repo.complete_execution(execution.id, result=result)
            await session.commit()

            logger.info(
                f"[SUMMARY] Generated {summaries_generated} summaries "
                f"for {len(active_users)} active users"
            )

            return result

        except Exception as e:
            logger.error(f"[SUMMARY] Error: {e}", exc_info=True)
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

            # Process each detected conversation through post-processing pipeline
            from nikita.context.post_processor import process_conversations

            pipeline_results = await process_conversations(
                session=session,
                conversation_ids=queued_ids,
            )
            await session.commit()

            # Count successes and failures
            processed_count = sum(1 for r in pipeline_results if r.success)
            failed_ids = [str(r.conversation_id) for r in pipeline_results if not r.success]

            result = {
                "status": "ok",
                "detected": len(queued_ids),
                "processed": processed_count,
                "failed": len(failed_ids),
            }

            # Log failures for debugging
            if failed_ids:
                logger.warning(
                    f"Post-processing failed for {len(failed_ids)} conversations: {failed_ids[:5]}"
                )

            await job_repo.complete_execution(execution.id, result=result)
            await session.commit()
            return result

        except Exception as e:
            result = {"status": "error", "error": str(e), "detected": 0, "processed": 0}
            await job_repo.fail_execution(execution.id, result=result)
            await session.commit()
            return result
