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

# Spec 100 FR-003: Max concurrent pipelines for process-conversations
MAX_CONCURRENT_PIPELINES: int = 10

router = APIRouter()


def _get_task_secret() -> str | None:
    """Get task authentication secret from settings.

    Spec 052 BACK-06: Use dedicated task_auth_secret for security isolation.
    Falls back to telegram_webhook_secret with deprecation warning for backward compat.

    Returns:
        Task secret if configured, None in development mode (logs warning).
    """
    settings = get_settings()

    # Prefer dedicated task_auth_secret (Spec 052 BACK-06)
    if settings.task_auth_secret:
        return settings.task_auth_secret

    # Fallback to telegram_webhook_secret (backward compat, deprecated)
    if settings.telegram_webhook_secret:
        logger.warning(
            "Using telegram_webhook_secret for task auth (DEPRECATED). "
            "Set TASK_AUTH_SECRET for proper security isolation."
        )
        return settings.telegram_webhook_secret

    # Development mode: no secret configured
    return None


async def verify_task_secret(
    authorization: str | None = Header(None, alias="Authorization"),
) -> None:
    """Verify internal task secret.

    Spec 052 BACK-06: Uses dedicated task_auth_secret for security isolation.
    Falls back to telegram_webhook_secret with deprecation warning.

    Args:
        authorization: Authorization header value.

    Raises:
        HTTPException: If authorization is missing or invalid.
    """
    secret = _get_task_secret()

    # Development mode: no secret configured (log warning instead of silent allow)
    if secret is None:
        logger.warning(
            "Task endpoint accessed without authentication (development mode). "
            "Set TASK_AUTH_SECRET or TELEGRAM_WEBHOOK_SECRET in production."
        )
        return

    expected = f"Bearer {secret}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


# --- Spec 043 T2.3: Daily Summary LLM Generation ---


async def _generate_summary_with_llm(
    conversations_data: list[dict],
    new_threads: list[dict],
    nikita_thoughts: list[str],
    user_chapter: int,
) -> dict:
    """Generate daily summary using Claude Haiku.

    Spec 043 T2.3: Replace deprecated placeholder with actual LLM summary.
    Falls back to basic summary on failure or missing API key.
    """
    try:
        import asyncio

        from pydantic_ai import Agent
        from pydantic_ai.models.anthropic import AnthropicModel

        settings = get_settings()
        if not settings.anthropic_api_key:
            return _fallback_summary(conversations_data)

        prompt = _build_summary_prompt(
            conversations_data, new_threads, nikita_thoughts, user_chapter
        )
        model = AnthropicModel(
            "claude-haiku-4-5-20251001", api_key=settings.anthropic_api_key
        )
        agent = Agent(model=model)

        # Timeout to prevent pg_cron job delays
        result = await asyncio.wait_for(agent.run(prompt), timeout=10.0)

        # pydantic-ai 1.x uses .output, older versions use .data
        response_text = getattr(result, "output", None) or getattr(result, "data", None)
        return _parse_summary_response(response_text)
    except Exception as e:
        logger.warning(f"LLM summary generation failed: {e}")
        return _fallback_summary(conversations_data)


def _build_summary_prompt(
    conversations_data: list[dict],
    new_threads: list[dict],
    nikita_thoughts: list[str],
    user_chapter: int,
) -> str:
    """Build prompt for daily summary generation."""
    conv_summaries = "\n".join(
        f"- {c.get('summary', 'No summary')} (tone: {c.get('emotional_tone', 'neutral')})"
        for c in conversations_data
    )

    threads_text = "\n".join(
        f"- [{t.get('type', 'general')}] {t.get('content', '')}"
        for t in new_threads
    ) if new_threads else "None"

    thoughts_text = "\n".join(f"- {t}" for t in nikita_thoughts) if nikita_thoughts else "None"

    return f"""You are Nikita, summarizing your day with the player.
Chapter: {user_chapter}/5

Today's conversations:
{conv_summaries}

New conversation threads:
{threads_text}

Your private thoughts:
{thoughts_text}

Write a brief first-person summary (2-3 sentences) of your day together.
Then identify 1-3 key moments and the overall emotional tone.

Respond in this exact format:
SUMMARY: <your summary>
KEY_MOMENTS: <moment1> | <moment2> | <moment3>
EMOTIONAL_TONE: <one word: warm, playful, tense, passionate, neutral, distant>"""


def _parse_summary_response(response_text: str) -> dict:
    """Parse structured LLM response into summary dict."""
    summary = "Had a nice day together."
    key_moments = []
    emotional_tone = "neutral"

    for line in response_text.strip().split("\n"):
        line = line.strip()
        if line.startswith("SUMMARY:"):
            summary = line[len("SUMMARY:"):].strip()
        elif line.startswith("KEY_MOMENTS:"):
            raw = line[len("KEY_MOMENTS:"):].strip()
            key_moments = [m.strip() for m in raw.split("|") if m.strip()]
        elif line.startswith("EMOTIONAL_TONE:"):
            emotional_tone = line[len("EMOTIONAL_TONE:"):].strip().lower()

    return {
        "summary_text": summary,
        "key_moments": key_moments,
        "emotional_tone": emotional_tone,
    }


def _fallback_summary(conversations_data: list[dict]) -> dict:
    """Basic summary when LLM is unavailable."""
    count = len(conversations_data)
    tones = [c.get("emotional_tone", "neutral") for c in conversations_data]
    dominant_tone = max(set(tones), key=tones.count) if tones else "neutral"

    return {
        "summary_text": f"We had {count} conversation{'s' if count != 1 else ''} today.",
        "key_moments": [],
        "emotional_tone": dominant_tone,
    }


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

        # Spec 100 FR-002: Idempotency guard — skip if recent execution within 50min
        if await job_repo.has_recent_execution(JobName.DECAY.value, window_minutes=50):
            logger.info("[DECAY] Skipped — recent execution within window")
            return {"status": "skipped", "reason": "recent_execution"}

        execution = await job_repo.start_execution(JobName.DECAY.value)
        await session.commit()

        try:
            # Initialize repositories and processor
            user_repo = UserRepository(session)
            history_repo = ScoreHistoryRepository(session)

            # Spec 049 P5: Wire notify_callback for decay game-over notifications
            async def _decay_notify(user_id, telegram_id, message):
                """Send Telegram notification when decay triggers game-over."""
                from nikita.platforms.telegram.bot import TelegramBot
                bot = TelegramBot()
                await bot.send_message(chat_id=telegram_id, text=message, escape=False)

            processor = DecayProcessor(
                session=session,
                user_repository=user_repo,
                score_history_repository=history_repo,
                notify_callback=_decay_notify,
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

    Supports both Telegram and voice platforms via unified scheduled_events table.

    Delayed delivery is based on chapter:
    - Chapter 1: 2-5 minute delays
    - Chapter 5: Instant delivery

    Returns:
        Dict with status and delivered message count.
    """
    from nikita.db.models.scheduled_event import EventPlatform
    from nikita.db.repositories.scheduled_event_repository import ScheduledEventRepository
    from nikita.platforms.telegram.bot import TelegramBot

    session_maker = get_session_maker()
    async with session_maker() as session:
        job_repo = JobExecutionRepository(session)
        execution = await job_repo.start_execution(JobName.DELIVER.value)
        await session.commit()

        try:
            event_repo = ScheduledEventRepository(session)
            bot = TelegramBot()

            # Get due events (pending, scheduled_at <= now)
            due_events = await event_repo.get_due_events(limit=50)

            delivered = 0
            failed = 0
            skipped = 0

            for event in due_events:
                try:
                    if event.platform == EventPlatform.TELEGRAM.value:
                        # Telegram message delivery
                        chat_id = event.content.get("chat_id")
                        text = event.content.get("text")

                        if not chat_id or not text:
                            await event_repo.mark_failed(
                                event.id,
                                error_message="Missing chat_id or text in content",
                                increment_retry=False,
                            )
                            failed += 1
                            continue

                        # Send message via Telegram API
                        await bot.send_message(chat_id=chat_id, text=text)

                        # Mark as delivered
                        await event_repo.mark_delivered(event.id)
                        delivered += 1

                        logger.info(
                            f"[DELIVER] Delivered telegram message to chat {chat_id}"
                        )

                    elif event.platform == EventPlatform.VOICE.value:
                        # Voice platform delivery
                        from nikita.agents.voice.service import get_voice_service

                        voice_prompt = event.content.get("voice_prompt")
                        agent_id = event.content.get("agent_id")

                        if not voice_prompt:
                            await event_repo.mark_failed(
                                event.id,
                                error_message="Missing voice_prompt in content",
                                increment_retry=False,
                            )
                            failed += 1
                            continue

                        # Get user for outbound call
                        from nikita.db.repositories.user_repository import UserRepository
                        user_repo = UserRepository(session)
                        user = await user_repo.get(event.user_id)

                        if not user:
                            await event_repo.mark_failed(
                                event.id,
                                error_message=f"User {event.user_id} not found",
                                increment_retry=False,
                            )
                            failed += 1
                            continue

                        if not user.phone:
                            await event_repo.mark_failed(
                                event.id,
                                error_message=f"No phone number for user {event.user_id}",
                                increment_retry=False,
                            )
                            failed += 1
                            continue

                        voice_service = get_voice_service()
                        config_override = None
                        if voice_prompt:
                            config_override = {"agent": {"prompt": {"prompt": voice_prompt}}}

                        call_result = await voice_service.make_outbound_call(
                            to_number=user.phone,
                            user_id=event.user_id,
                            conversation_config_override=config_override,
                        )

                        if call_result.get("success"):
                            await event_repo.mark_delivered(event.id)
                            delivered += 1
                            logger.info(
                                f"[DELIVER] Voice call initiated for user {event.user_id}: "
                                f"conversation_id={call_result.get('conversation_id')}"
                            )
                        else:
                            await event_repo.mark_failed(
                                event.id,
                                error_message=call_result.get("error", "Call failed"),
                                increment_retry=True,
                            )
                            failed += 1

                    else:
                        # Unknown platform
                        await event_repo.mark_failed(
                            event.id,
                            error_message=f"Unknown platform: {event.platform}",
                            increment_retry=False,
                        )
                        failed += 1

                except Exception as event_error:
                    # Mark individual event as failed (with retry)
                    await event_repo.mark_failed(
                        event.id,
                        error_message=str(event_error),
                        increment_retry=True,
                    )
                    failed += 1
                    logger.warning(
                        f"[DELIVER] Failed to deliver event {event.id}: {event_error}"
                    )

            await session.commit()
            await bot.close()

            result = {
                "status": "ok",
                "delivered": delivered,
                "failed": failed,
                "skipped": skipped,
            }
            await job_repo.complete_execution(execution.id, result=result)
            await session.commit()

            logger.info(
                f"[DELIVER] Processed {len(due_events)} events: "
                f"{delivered} delivered, {failed} failed, {skipped} skipped"
            )

            return result

        except Exception as e:
            logger.error(f"[DELIVER] Error: {e}", exc_info=True)
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
    # NOTE: MetaPromptService deprecated (Spec 042), summary generation moved to pipeline

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
            # meta_service deprecated (Spec 042) - summary generation moved to pipeline

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

                    # Spec 043 T2.3: Generate summary via Claude Haiku
                    summary_data = await _generate_summary_with_llm(
                        conversations_data=conversations_data,
                        new_threads=new_threads,
                        nikita_thoughts=nikita_thoughts,
                        user_chapter=user.chapter,
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

            # Spec 100 FR-003: Limit batch to MAX_CONCURRENT_PIPELINES per cycle
            batch = queued_ids[:MAX_CONCURRENT_PIPELINES]
            deferred_count = len(queued_ids) - len(batch)
            if deferred_count > 0:
                logger.info(
                    "pipeline_batch_limited total=%d batch=%d deferred=%d",
                    len(queued_ids), len(batch), deferred_count,
                )

            # Process each detected conversation through pipeline
            # Feature flag: Unified pipeline (Spec 042) vs legacy post-processing (Spec 029)
            settings = get_settings()

            if settings.unified_pipeline_enabled:
                # Spec 042: Use unified pipeline
                from nikita.pipeline.orchestrator import PipelineOrchestrator
                from nikita.db.repositories.conversation_repository import ConversationRepository

                pipeline_results = []
                for conv_id in batch:
                    # Per-conversation session: isolate failures so conv #3 crash
                    # doesn't cascade to #4-#50
                    try:
                        async with session_maker() as conv_session:
                            conv_repo = ConversationRepository(conv_session)
                            conv = await conv_repo.get(conv_id)
                            if conv:
                                # BUG-001b fix: Load user state for pipeline context
                                from nikita.db.repositories.user_repository import UserRepository
                                user_repo = UserRepository(conv_session)
                                user = await user_repo.get(conv.user_id)

                                orchestrator = PipelineOrchestrator(conv_session)
                                result = await orchestrator.process(
                                    conversation_id=conv_id,
                                    user_id=conv.user_id,
                                    platform=conv.platform or "text",
                                    conversation=conv,
                                    user=user,
                                )
                                pipeline_results.append(result)

                                # Mark conversation status based on pipeline outcome
                                if result.success:
                                    ctx = result.context
                                    await conv_repo.mark_processed(
                                        conversation_id=conv_id,
                                        summary=ctx.extraction_summary or None,
                                        emotional_tone=ctx.emotional_tone or None,
                                    )
                                else:
                                    await conv_repo.mark_failed(conv_id)

                                await conv_session.commit()
                    except Exception as e:
                        logger.warning(f"[PIPELINE] Failed for conversation {conv_id}: {e}")
                        # Mark failed in a fresh session to avoid polluted transaction
                        try:
                            async with session_maker() as err_session:
                                err_repo = ConversationRepository(err_session)
                                await err_repo.mark_failed(conv_id)
                                await err_session.commit()
                        except Exception:
                            logger.error(f"[PIPELINE] Could not mark {conv_id} as failed")

                # Count successes and failures
                processed_count = sum(1 for r in pipeline_results if r.success)
                failed_ids = [str(r.context.conversation_id) for r in pipeline_results if not r.success]
            else:
                # Spec 043 T2.1: Legacy branch is dead code since pipeline is now enabled
                # by default (Spec 043 T1.1). If someone explicitly disables the flag,
                # log an error instead of silently skipping.
                # Rollback: Set UNIFIED_PIPELINE_ENABLED=false in Cloud Run env vars
                logger.error(
                    "unified_pipeline_disabled_but_no_legacy_fallback "
                    "conversations_skipped=%d", len(batch)
                )
                processed_count = 0
                failed_ids = [str(cid) for cid in batch]

            result = {
                "status": "ok",
                "detected": len(queued_ids),
                "processed": processed_count,
                "failed": len(failed_ids),
                "deferred": deferred_count,
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


@router.post("/psyche-batch")
async def run_psyche_batch_job(
    _: None = Depends(verify_task_secret),
):
    """Run daily psyche state generation for all active users (Spec 056).

    Called by pg_cron daily at 5AM UTC. Generates PsycheState for each
    active user and stores in psyche_states table.

    Feature-flagged: returns skip when psyche_agent_enabled is OFF.

    Returns:
        Dict with status and batch statistics.
    """
    settings = get_settings()

    if not settings.psyche_agent_enabled:
        logger.info("[PSYCHE-BATCH] Feature flag OFF, skipping")
        return {"status": "skipped", "reason": "psyche_agent_enabled=false"}

    session_maker = get_session_maker()
    async with session_maker() as session:
        job_repo = JobExecutionRepository(session)
        execution = await job_repo.start_execution(JobName.PSYCHE_BATCH.value)
        await session.commit()

        try:
            from nikita.agents.psyche.batch import run_psyche_batch

            batch_result = await run_psyche_batch()

            result = {
                "status": "ok",
                "processed": batch_result.get("processed", 0),
                "failed": batch_result.get("failed", 0),
                "errors": batch_result.get("errors", [])[:5],
            }
            await job_repo.complete_execution(execution.id, result=result)
            await session.commit()

            logger.info(
                "[PSYCHE-BATCH] Processed %d users, %d failed",
                result["processed"],
                result["failed"],
            )

            return result

        except Exception as e:
            logger.error(f"[PSYCHE-BATCH] Error: {e}", exc_info=True)
            result = {"status": "error", "error": str(e)}
            await job_repo.fail_execution(execution.id, result=result)
            await session.commit()
            return result


# NOTE: First @router.post("/touchpoints") DELETED (duplicate, no job logging)
# Keeping the second one at line ~852 which has proper job_executions logging


@router.post("/detect-stuck")
async def detect_stuck_conversations(
    _: None = Depends(verify_task_secret),
):
    """Detect and handle conversations stuck in processing (Spec 031 T4.3).

    Called by pg_cron every 10 minutes.

    Finds conversations stuck in 'processing' state for >30 minutes
    and marks them as 'failed'.

    Returns:
        Dict with status and count of conversations marked failed.
    """
    raise HTTPException(
        status_code=410,
        detail="Use POST /tasks/recover — consolidated detect+recover endpoint",
    )


@router.post("/touchpoints")
async def process_touchpoints(
    _: None = Depends(verify_task_secret),
):
    """Process and deliver due proactive touchpoints (Remediation Plan T3.1).

    Called by pg_cron every 5 minutes. Evaluates eligible users and delivers
    Nikita-initiated messages based on:
    - Time triggers (morning/evening slots)
    - Gap triggers (>24h without contact)
    - Event triggers (life simulation events)

    Returns:
        Dict with status and delivery statistics.
    """
    from nikita.touchpoints.engine import TouchpointEngine

    session_maker = get_session_maker()
    async with session_maker() as session:
        job_repo = JobExecutionRepository(session)
        execution = await job_repo.start_execution("touchpoints")
        await session.commit()

        try:
            engine = TouchpointEngine(session)
            results = await engine.deliver_due_touchpoints()

            # Count successes, failures, and skipped
            delivered = sum(1 for r in results if r.success)
            failed = sum(1 for r in results if r.error)
            skipped = sum(1 for r in results if r.skipped_reason)

            await session.commit()

            result = {
                "status": "ok",
                "evaluated": len(results),
                "delivered": delivered,
                "failed": failed,
                "skipped": skipped,
            }
            await job_repo.complete_execution(execution.id, result=result)
            await session.commit()

            if delivered > 0:
                logger.info(
                    f"[TOUCHPOINTS] Delivered {delivered}/{len(results)} touchpoints"
                )

            return result

        except Exception as e:
            logger.error(f"[TOUCHPOINTS] Error: {e}", exc_info=True)
            result = {"status": "error", "error": str(e), "evaluated": 0, "delivered": 0}
            await job_repo.fail_execution(execution.id, result=result)
            await session.commit()
            return result


@router.post("/recover-stuck")
async def recover_stuck_conversations(
    _: None = Depends(verify_task_secret),
):
    """Recover conversations stuck in processing state (Remediation Plan T1.2).

    Called by pg_cron every 10 minutes. Finds conversations stuck in 'processing'
    for >30 minutes and either resets them to 'active' or marks as 'failed'.

    Returns:
        Dict with status and recovery statistics.
    """
    raise HTTPException(
        status_code=410,
        detail="Use POST /tasks/recover — consolidated detect+recover endpoint",
    )


@router.post("/boss-timeout")
async def resolve_stale_boss_fights(
    _: None = Depends(verify_task_secret),
) -> dict:
    """Resolve boss_fight states older than 24 hours (Spec 049 AC-1.1).

    Called by pg_cron every 6 hours. AFK users get their boss_fight resolved
    (treated as a failed attempt). After 3 failed attempts, game_over is triggered.

    Returns:
        Dict with status and resolution count.
    """
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import select

    from nikita.db.models.user import User
    from nikita.db.repositories.score_history_repository import ScoreHistoryRepository
    from nikita.db.repositories.user_repository import UserRepository

    session_maker = get_session_maker()
    async with session_maker() as session:
        job_repo = JobExecutionRepository(session)
        execution = await job_repo.start_execution("boss_timeout")
        await session.commit()

        try:
            user_repo = UserRepository(session)
            history_repo = ScoreHistoryRepository(session)

            # Find users stuck in boss_fight for >24h (Spec 049 AC-1.2)
            # P8: Use dedicated boss_fight_started_at timestamp instead of
            # generic updated_at (which changes on any user field update)
            cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

            stmt = select(User).where(
                User.game_status == "boss_fight",
                User.boss_fight_started_at.isnot(None),
                User.boss_fight_started_at < cutoff,
            )
            result = await session.execute(stmt)
            stale_users = result.scalars().all()

            resolved = 0
            for user in stale_users:
                # Treat as failed boss attempt (Spec 049 AC-1.3)
                user.boss_attempts = (user.boss_attempts or 0) + 1

                if user.boss_attempts >= 3:
                    # 3 failed attempts = game over (Spec 049 AC-1.4)
                    user.game_status = "game_over"
                else:
                    # Return to active, can try again
                    user.game_status = "active"

                # P8: Clear boss fight timestamp on resolution
                user.boss_fight_started_at = None

                # Log the timeout event (Spec 049 AC-1.5)
                await history_repo.log_event(
                    user_id=user.id,
                    score=Decimal(str(user.relationship_score or 50)),
                    chapter=user.chapter or 1,
                    event_type="boss_timeout",
                    event_details={
                        "boss_attempts": user.boss_attempts,
                        "new_status": user.game_status,
                        "timeout_hours": 24,
                    },
                )

                resolved += 1
                logger.info(
                    f"[BOSS-TIMEOUT] Resolved stale boss_fight: user={user.id}, "
                    f"attempts={user.boss_attempts}, new_status={user.game_status}"
                )

            await session.commit()

            result = {
                "status": "ok",
                "resolved": resolved,
            }
            await job_repo.complete_execution(execution.id, result=result)
            await session.commit()

            logger.info(f"[BOSS-TIMEOUT] Resolved {resolved} stale boss fights")

            return result

        except Exception as e:
            logger.error(f"[BOSS-TIMEOUT] Error: {e}", exc_info=True)
            result_err = {"status": "error", "error": str(e), "resolved": 0}
            await job_repo.fail_execution(execution.id, result=result_err)
            await session.commit()
            return result_err
