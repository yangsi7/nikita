"""Background task routes for pg_cron triggers.

These endpoints are called by pg_cron + Supabase Edge Functions:
- POST /tasks/decay - Apply daily decay to all active users
- POST /tasks/deliver - Process pending message deliveries
- POST /tasks/summary - Generate daily summaries

AC Coverage: Phase 3 background task infrastructure
"""

import logging
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import JSONResponse, Response
from sqlalchemy import text as sql_text

logger = logging.getLogger(__name__)

from nikita.config.models import Models
from nikita.config.settings import get_settings
from nikita.db.database import get_session_maker
# SummaryRepoDep, UserRepoDep removed (DC-002 — unused in this module)
from nikita.db.models.job_execution import JobName
from nikita.db.repositories.job_execution_repository import JobExecutionRepository

# Spec 100 FR-003: Max concurrent pipelines for process-conversations
MAX_CONCURRENT_PIPELINES: int = 10

router = APIRouter()


def _get_task_secret() -> str | None:
    """Get task authentication secret from settings.

    Spec 052 BACK-06 / BKD-003: Use dedicated task_auth_secret only.
    telegram_webhook_secret must NOT be used as a fallback (security isolation).

    Returns:
        Task secret if configured, None in development mode (logs warning).
    """
    settings = get_settings()
    return settings.task_auth_secret  # None if not configured


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

        settings = get_settings()
        if not settings.anthropic_api_key:
            return _fallback_summary(conversations_data)

        prompt = _build_summary_prompt(
            conversations_data, new_threads, nikita_thoughts, user_chapter
        )
        agent = Agent(model=Models.haiku())

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

                        # GH #248 defense-in-depth: legacy rows and any
                        # future producer bug that omits chat_id fall back
                        # to the owning user's telegram_id (auto-loaded via
                        # ScheduledEvent.user selectin relationship). The
                        # WARNING log makes producer regressions observable
                        # without breaking delivery.
                        if not chat_id:
                            fallback = (
                                event.user.telegram_id
                                if getattr(event, "user", None)
                                else None
                            )
                            if fallback:
                                logger.warning(
                                    "[DELIVER] scheduled_event %s missing chat_id "
                                    "in content; fell back to user.telegram_id",
                                    event.id,
                                )
                                chat_id = fallback

                        if not chat_id or not text:
                            await event_repo.mark_failed(
                                event.id,
                                error_message=(
                                    "Missing chat_id (or user.telegram_id) "
                                    "and/or text in content"
                                ),
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
                        # Spec 108 fix: full override (TTS + first_message +
                        # secret tokens) via the canonical scheduling helper.
                        # Bare prompt-only overrides silently dropped the
                        # chapter-specific TTS settings and the audio-tagged
                        # first_message in production.
                        from nikita.agents.voice.scheduling_overrides import (
                            build_scheduled_outbound_override,
                        )

                        config_override, dynamic_variables = (
                            await build_scheduled_outbound_override(
                                user_id=event.user_id,
                                voice_prompt=voice_prompt,
                            )
                        )

                        call_result = await voice_service.make_outbound_call(
                            to_number=user.phone,
                            user_id=event.user_id,
                            conversation_config_override=config_override,
                            dynamic_variables=dynamic_variables,
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
    6. Memory Updates - Update pgVector memory facts
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

                # Count successes, pipeline failures, and non-critical stage errors (MP-006)
                processed_count = sum(1 for r in pipeline_results if r.success)
                failed_ids = [str(r.context.conversation_id) for r in pipeline_results if not r.success]
                stage_errors_count = sum(len(r.context.stage_errors) for r in pipeline_results)
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
                "stage_errors": stage_errors_count,  # MP-006: non-critical stage failures
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


@router.post("/refresh-voice-prompts")
async def refresh_voice_prompts(
    _: None = Depends(verify_task_secret),
) -> dict:
    """Refresh stale voice prompts for active users (Spec 209 FR-005).

    Called by pg_cron every 6 hours. Regenerates ready_prompts via pipeline
    for users whose cached_voice_prompt_at is NULL or >6h old.

    50-user batch cap, sequential processing, per-user error isolation.
    """
    from uuid import uuid4

    from nikita.db.repositories.user_repository import UserRepository
    from nikita.pipeline.orchestrator import PipelineOrchestrator

    session_maker = get_session_maker()
    async with session_maker() as session:
        job_repo = JobExecutionRepository(session)

        # Idempotency guard: skip if recent execution within 300 min
        if await job_repo.has_recent_execution(
            JobName.REFRESH_VOICE_PROMPTS.value, window_minutes=300
        ):
            logger.info("[VOICE-REFRESH] Skipped — recent execution within window")
            return {"status": "skipped", "reason": "recent_execution"}

        execution = await job_repo.start_execution(JobName.REFRESH_VOICE_PROMPTS.value)
        await session.commit()

        try:
            user_repo = UserRepository(session)
            total_stale = await user_repo.count_users_with_stale_voice_prompts(stale_hours=6)
            stale_users = await user_repo.get_users_with_stale_voice_prompts(
                stale_hours=6, limit=50
            )

            refreshed = 0
            errors = 0

            for user in stale_users:
                try:
                    async with session_maker() as conv_session:
                        orchestrator = PipelineOrchestrator(conv_session)
                        await orchestrator.process(
                            conversation_id=uuid4(),
                            user_id=user.id,
                            platform="voice",
                            user=user,
                        )
                    refreshed += 1
                except Exception as e:
                    errors += 1
                    logger.warning(
                        "[VOICE-REFRESH] Failed for user %s: %s", user.id, e
                    )

            deferred = max(0, total_stale - len(stale_users))

            result = {
                "status": "ok",
                "refreshed": refreshed,
                "errors": errors,
                "deferred": deferred,
            }
            await job_repo.complete_execution(execution.id, result=result)
            await session.commit()

            logger.info(
                "[VOICE-REFRESH] Refreshed %d, errors %d, deferred %d",
                refreshed, errors, deferred,
            )

            return result

        except Exception as e:
            logger.error("[VOICE-REFRESH] Error: %s", e, exc_info=True)
            result = {"status": "error", "error": str(e)}
            await job_repo.fail_execution(execution.id, result=result)
            await session.commit()
            return result


# NOTE: First @router.post("/touchpoints") DELETED (duplicate, no job logging)
# Keeping the second one below which has proper job_executions logging


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


# ----------------------------------------------------------------------------
# Spec 215 PR 215-D — Heartbeat Engine API endpoints (US-1 + US-2)
# ----------------------------------------------------------------------------
#
# These endpoints are pg_cron-driven (registration lives in 215-E):
#   POST /tasks/heartbeat            — every hour (FR-005 safety-net floor)
#   POST /tasks/generate-daily-arcs  — once per day at 5 AM UTC
#
# Both mirror /refresh-voice-prompts above for auth + idempotency-guard pattern.
# Brief constraints (Plan v6.3 P2 + spec.md):
#   R1 / FR-007: heartbeat MUST NOT write scheduled_events directly — it
#                delegates to TouchpointEngine.evaluate_and_schedule_for_user.
#   R2 / FR-009: idempotency via JobExecutionRepository.has_recent_execution.
#   R3 / FR-010: per-user pg_advisory_lock(hashtext(user_id::text)::bigint)
#                with explicit pg_advisory_unlock in try/finally (session-scoped,
#                NOT xact-scoped — released per-user, not piled across the tick).
#   R4         : fan-out cap = 40 per tick (leaves 10-row /tasks/deliver headroom).
#   G1 / FR-008: filter active|boss_fight + telegram_id + recent interaction.
#   FR-014     : daily-arc handler engages a 503 + Retry-After breaker when
#                today's aggregate cost crosses the configured ceiling.
#   FR-015     : error envelopes are redacted — never leak str(exception).
#   FR-020     : feature flag heartbeat_engine_enabled gates all work.

# Heartbeat fan-out cap per safety-net tick (FR-005 + R4).
# Leaves headroom for /tasks/deliver (10 row chunk, separate cron).
_HEARTBEAT_FAN_OUT_CAP: int = 40

# Idempotency window for the hourly heartbeat tick (AC-FR9-001 + contracts.md
# Contract 3). Set < 60min so consecutive hour-boundary cron fires (e.g. 12:00
# + 12:55) do NOT short-circuit each other unnecessarily.
_HEARTBEAT_IDEMPOTENCY_WINDOW_MINUTES: int = 55

# Idempotency window for the daily-arc generator (contracts.md Contract 3).
_DAILY_ARC_IDEMPOTENCY_WINDOW_MINUTES: int = 1440


def _build_redacted_error_envelope(error_code: str) -> dict:
    """FR-015: structured envelope with NO raw exception string.

    Exception details get logged server-side (with exc_info=True) but the
    response body MUST stay opaque to avoid leaking PII-adjacent payloads
    (per-player parameters, prompt bodies, internal state).
    """
    return {
        "status": "error",
        "error": error_code,
        "detail": "internal error; see server logs",
    }


@router.post("/heartbeat")
async def heartbeat_tick(
    _: None = Depends(verify_task_secret),
) -> dict:
    """Hourly safety-net heartbeat tick (Spec 215 FR-005, US-2).

    Iterates over active heartbeat-eligible users and delegates each to
    TouchpointEngine.evaluate_and_schedule_for_user, which decides whether
    to schedule a proactive touchpoint. Per FR-007/R1 the handler NEVER
    writes scheduled_events directly — that responsibility lives in the
    touchpoint engine + dispatcher.

    Idempotency: 55-min window via JobExecutionRepository.has_recent_execution
    (R2 / AC-FR9-001).

    Concurrency: per-user ``pg_try_advisory_lock`` (non-blocking) +
    ``pg_advisory_unlock`` in try/finally serializes simultaneous operations
    against the same user. Best-effort per FR-007: if the lock is currently
    held (slow concurrent tick still working that user), the user is SKIPPED
    on this tick and picked up on the next tick when the lock frees. This
    prevents one slow user from serializing the entire 40-user fan-out and
    inflating per-user wait time (GH #337 / B3, supersedes blocking
    ``pg_advisory_lock`` from PR #334 iter-1).

    Fan-out cap: 40 users per tick (R4) — overflow surfaces as
    ``deferred`` for next-tick processing.

    Response envelope: ``{status, processed, errors, skipped, deferred}``
    where ``skipped`` counts users whose advisory lock could not be acquired
    this tick (will retry next tick).
    """
    # Inline import: TouchpointEngine pulls in agents/voice deps; keep cold-start
    # of /tasks/decay etc. unaffected. UserRepository is also inline for symmetry.
    from nikita.db.repositories.user_repository import UserRepository
    from nikita.touchpoints.engine import TouchpointEngine

    settings = get_settings()

    # FR-020: feature flag short-circuit (no DB writes when disabled).
    if not settings.heartbeat_engine_enabled:
        logger.info("[HEARTBEAT] Skipped — heartbeat_engine_enabled=false")
        return {"status": "disabled", "reason": "feature_flag_off"}

    session_maker = get_session_maker()
    async with session_maker() as session:
        job_repo = JobExecutionRepository(session)

        # R2 / AC-FR9-001: idempotency guard. Window < 60min so back-to-back
        # cron fires don't suppress each other unnecessarily.
        if await job_repo.has_recent_execution(
            JobName.HEARTBEAT.value,
            window_minutes=_HEARTBEAT_IDEMPOTENCY_WINDOW_MINUTES,
        ):
            logger.info("[HEARTBEAT] Skipped — recent execution within 55 min")
            return {"status": "skipped", "reason": "recent_execution"}

        execution = await job_repo.start_execution(JobName.HEARTBEAT.value)
        await session.commit()

        try:
            user_repo = UserRepository(session)
            # G1: active|boss_fight + telegram_id + recent interaction
            eligible = await user_repo.get_active_users_for_heartbeat()

            # R4: fan-out cap. Anything over the cap is deferred to next tick.
            to_process = eligible[:_HEARTBEAT_FAN_OUT_CAP]
            deferred = max(0, len(eligible) - len(to_process))

            engine = TouchpointEngine(session)
            processed = 0
            errors = 0
            skipped = 0

            for user in to_process:
                # R3 / AC-FR10-001 + GH #337 (B3): serialize concurrent ops
                # against the same user using NON-BLOCKING pg_try_advisory_lock.
                # UUID → bigint via hashtext(). If the lock is held (slow
                # concurrent tick still working that user), skip this user and
                # let the next tick pick them up — never block the whole
                # 40-user fan-out behind one slow user (FR-007 best-effort).
                lock_key_row = await session.execute(
                    sql_text("SELECT hashtext(:uid)::bigint AS k"),
                    {"uid": str(user.id)},
                )
                lock_key = lock_key_row.scalar_one()
                lock_acquired_row = await session.execute(
                    sql_text("SELECT pg_try_advisory_lock(:k) AS acquired"),
                    {"k": lock_key},
                )
                lock_acquired = bool(lock_acquired_row.scalar_one())
                if not lock_acquired:
                    skipped += 1
                    # PII discipline: log only user_id; never include user
                    # state, narrative content, or other fields.
                    logger.info(
                        "[HEARTBEAT] Skipped user %s (advisory lock held; will retry next tick)",
                        user.id,
                    )
                    continue
                try:
                    # R1 / FR-007: delegate; never write scheduled_events here.
                    await engine.evaluate_and_schedule_for_user(user_id=user.id)
                    processed += 1
                except Exception as user_err:
                    errors += 1
                    # PII discipline: log only the user_id and class name; never
                    # full str(user_err) which may include arc/narrative content.
                    logger.warning(
                        "[HEARTBEAT] Per-user failure for %s: %s",
                        user.id,
                        type(user_err).__name__,
                    )
                finally:
                    # Release lock immediately after this user's work; do NOT
                    # wait until end-of-tick (would serialize all 40 users
                    # against any concurrent tick that arrived mid-loop).
                    await session.execute(
                        sql_text("SELECT pg_advisory_unlock(:k)"),
                        {"k": lock_key},
                    )

            await session.commit()

            result = {
                "status": "ok",
                "processed": processed,
                "errors": errors,
                "skipped": skipped,
                "deferred": deferred,
            }
            await job_repo.complete_execution(execution.id, result=result)
            await session.commit()

            logger.info(
                "[HEARTBEAT] Processed %d, errors %d, skipped %d, deferred %d",
                processed, errors, skipped, deferred,
            )
            return result

        except Exception as e:
            # FR-015: redact for response; full trace lives in server logs.
            logger.error("[HEARTBEAT] Catastrophic error: %s", e, exc_info=True)
            envelope = _build_redacted_error_envelope("heartbeat_failed")
            await job_repo.fail_execution(
                execution.id,
                result={"status": "error", "error": "heartbeat_failed"},
            )
            await session.commit()
            return envelope


@router.post("/generate-daily-arcs", response_model=None)
async def generate_daily_arcs(
    _: None = Depends(verify_task_secret),
) -> dict | Response:
    """Daily-arc generation for all heartbeat-eligible users (Spec 215 US-1).

    Calls the LLM-driven planner (``nikita.heartbeat.planner.generate_daily_arc``)
    once per active user per day and persists the result via
    ``NikitaDailyPlanRepository.upsert_plan``.

    Storage contract is FROZEN per ``specs/215-heartbeat-engine/contracts.md``
    Contract 1 (locked 2026-04-18). The Pydantic field ``DailyArc.narrative``
    maps to the repo kwarg ``narrative_text`` (intentional divergence — see
    contracts.md for rationale).

    Cost guard (FR-014): if today's aggregate USD cost crosses
    ``settings.heartbeat_cost_circuit_breaker_usd_per_day``, returns HTTP 503
    with a Retry-After header pointing to the next midnight UTC reset.

    Returns ``dict`` on success/skip and ``JSONResponse`` (subclass of
    ``Response``) on circuit-breaker engagement.

    Idempotency: 1440-min daily window per contracts.md Contract 3.
    """
    # Inline import: pulls in heartbeat planner Pydantic AI Agent factory;
    # keep tasks.py module-import cheap for cron endpoints that don't use it.
    from nikita.db.repositories.heartbeat_repository import (
        NikitaDailyPlanRepository,
    )
    from nikita.db.repositories.user_repository import UserRepository
    from nikita.heartbeat import planner as planner_module

    settings = get_settings()

    if not settings.heartbeat_engine_enabled:
        logger.info("[DAILY-ARCS] Skipped — heartbeat_engine_enabled=false")
        return {"status": "disabled", "reason": "feature_flag_off"}

    session_maker = get_session_maker()
    async with session_maker() as session:
        job_repo = JobExecutionRepository(session)

        # Daily idempotency guard (contracts.md Contract 3 — 1440 min window).
        if await job_repo.has_recent_execution(
            JobName.GENERATE_DAILY_ARCS.value,
            window_minutes=_DAILY_ARC_IDEMPOTENCY_WINDOW_MINUTES,
        ):
            logger.info("[DAILY-ARCS] Skipped — recent execution within 24h")
            return {"status": "skipped", "reason": "recent_execution"}

        # FR-014 cost circuit breaker (GH #336 — armed in Spec 215 B2): query
        # today's aggregate spend via JobExecutionRepository.get_today_cost_usd
        # and 503 if it has reached the configured per-day ceiling.
        ceiling = float(settings.heartbeat_cost_circuit_breaker_usd_per_day)
        try:
            today_cost = float(await job_repo.get_today_cost_usd())
        except Exception as cost_err:  # noqa: BLE001 - never block runs on a ledger read failure
            logger.warning(
                "[DAILY-ARCS] cost_ledger_read_failed (%s); treating today_cost as $0",
                type(cost_err).__name__,
            )
            today_cost = 0.0

        if today_cost >= ceiling:
            # FR-014(a): structured 503 + Retry-After to next midnight UTC.
            now_utc = datetime.now(UTC)
            tomorrow = (now_utc + timedelta(days=1)).date()
            next_reset = datetime.combine(tomorrow, time(0, 0), tzinfo=UTC)
            retry_after_seconds = max(1, int((next_reset - now_utc).total_seconds()))
            logger.warning(
                "[DAILY-ARCS] circuit_breaker_engaged — today_cost=%.2f USD "
                "ceiling=%.2f USD; deferring %d s",
                today_cost, ceiling, retry_after_seconds,
            )
            return JSONResponse(
                status_code=503,
                headers={"Retry-After": str(retry_after_seconds)},
                content={
                    "status": "throttled",
                    "reason": "cost_circuit_breaker_engaged",
                },
            )

        execution = await job_repo.start_execution(
            JobName.GENERATE_DAILY_ARCS.value
        )
        await session.commit()

        try:
            user_repo = UserRepository(session)
            plan_repo = NikitaDailyPlanRepository(session)

            # Reuse the same G1 filter as the heartbeat tick — same eligibility
            # criteria; users in game_over / won are excluded (FR-008 + OD4).
            eligible = await user_repo.get_active_users_for_heartbeat()
            today = datetime.now(UTC).date()

            generated = 0
            errors = 0

            for user in eligible:
                try:
                    arc = await planner_module.generate_daily_arc(
                        user=user, plan_date=today, session=session,
                    )
                    # Storage contract per contracts.md Contract 1 (FROZEN):
                    #   arc_json wraps steps under {"steps": [...]}
                    #   narrative_text repo kwarg = arc.narrative Pydantic field
                    #   model_used pass-through
                    await plan_repo.upsert_plan(
                        user_id=user.id,
                        plan_date=today,
                        arc_json={
                            "steps": [step.model_dump() for step in arc.steps]
                        },
                        narrative_text=arc.narrative,
                        model_used=arc.model_used,
                    )
                    generated += 1
                except Exception as user_err:
                    errors += 1
                    logger.warning(
                        "[DAILY-ARCS] Per-user planner failure for %s: %s",
                        user.id,
                        type(user_err).__name__,
                    )

            await session.commit()

            result = {
                "status": "ok",
                "generated": generated,
                "errors": errors,
            }
            await job_repo.complete_execution(execution.id, result=result)
            await session.commit()

            logger.info(
                "[DAILY-ARCS] Generated %d arcs, %d errors",
                generated, errors,
            )
            return result

        except Exception as e:
            logger.error("[DAILY-ARCS] Catastrophic error: %s", e, exc_info=True)
            envelope = _build_redacted_error_envelope("generate_daily_arcs_failed")
            await job_repo.fail_execution(
                execution.id,
                result={"status": "error", "error": "generate_daily_arcs_failed"},
            )
            await session.commit()
            return envelope
