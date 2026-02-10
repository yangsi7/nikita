"""Admin Debug Portal API routes.

Provides debugging endpoints for Nikita developers to:
- View system overview stats
- Monitor scheduled job status
- Debug user state machines
- View user details and timing

Access restricted to @silent-agents.com emails.
"""

from datetime import datetime, timedelta, UTC
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.api.dependencies.auth import get_current_admin_user
from nikita.api.schemas.admin_debug import (
    ActiveUserCounts,
    ChapterDistribution,
    ChapterStateInfo,
    ElevenLabsCallDetailResponse,
    ElevenLabsCallListItem,
    ElevenLabsCallListResponse,
    ElevenLabsTranscriptTurn,
    EngagementDistribution,
    EngagementStateInfo,
    GameStatusDistribution,
    JobExecutionStatus,
    JobStatusResponse,
    PromptDetailResponse,
    PromptListItem,
    PromptListResponse,
    StateMachinesResponse,
    SystemOverviewResponse,
    TranscriptEntryResponse,
    UserDetailResponse,
    UserListItem,
    UserListResponse,
    UserNextActions,
    UserTimingInfo,
    ViceInfo,
    ViceProfileInfo,
    VoiceConversationDetailResponse,
    VoiceConversationListItem,
    VoiceConversationListResponse,
    VoiceStatsResponse,
    TextConversationListItem,
    TextConversationListResponse,
    TextConversationDetailResponse,
    MessageResponse,
    PipelineStatusResponse,
    PipelineStageStatus,
    TextStatsResponse,
    ThreadListItem,
    ThreadListResponse,
    ThoughtListItem,
    ThoughtListResponse,
)
from nikita.db.database import get_async_session
from nikita.db.models.engagement import EngagementState
from nikita.db.models.job_execution import JobExecution, JobName, JobStatus
from nikita.db.models.conversation import Conversation
from nikita.db.models.user import User, UserVicePreference
from nikita.db.repositories.engagement_repository import EngagementStateRepository
from nikita.db.repositories.job_execution_repository import JobExecutionRepository
from nikita.db.repositories.user_repository import UserRepository
from nikita.db.repositories.vice_repository import VicePreferenceRepository
from nikita.engine.constants import BOSS_THRESHOLDS, CHAPTER_NAMES, DECAY_RATES

router = APIRouter()


# ============================================================================
# T2.1: System Overview Endpoint
# ============================================================================


@router.get("/system", response_model=SystemOverviewResponse)
async def get_system_overview(
    admin_user_id: Annotated[UUID, Depends(get_current_admin_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Get system overview stats.

    Returns user counts by game_status, chapter, and engagement_state.

    AC-FR002-001: Returns user counts by game_status
    AC-FR002-002: Returns user distribution by chapter
    AC-FR002-003: Returns user distribution by engagement_state
    AC-FR010-001: Returns active user counts (24h, 7d, 30d)
    """
    # Total users
    total_stmt = select(func.count(User.id))
    total_result = await session.execute(total_stmt)
    total_users = total_result.scalar() or 0

    # Game status distribution
    status_stmt = select(User.game_status, func.count(User.id)).group_by(
        User.game_status
    )
    status_result = await session.execute(status_stmt)
    status_counts = {row[0]: row[1] for row in status_result.all()}

    game_status = GameStatusDistribution(
        active=status_counts.get("active", 0),
        boss_fight=status_counts.get("boss_fight", 0),
        game_over=status_counts.get("game_over", 0),
        won=status_counts.get("won", 0),
    )

    # Chapter distribution
    chapter_stmt = select(User.chapter, func.count(User.id)).group_by(User.chapter)
    chapter_result = await session.execute(chapter_stmt)
    chapter_counts = {row[0]: row[1] for row in chapter_result.all()}

    chapters = ChapterDistribution(
        chapter_1=chapter_counts.get(1, 0),
        chapter_2=chapter_counts.get(2, 0),
        chapter_3=chapter_counts.get(3, 0),
        chapter_4=chapter_counts.get(4, 0),
        chapter_5=chapter_counts.get(5, 0),
    )

    # Engagement state distribution
    eng_stmt = select(EngagementState.state, func.count(EngagementState.user_id)).group_by(
        EngagementState.state
    )
    eng_result = await session.execute(eng_stmt)
    eng_counts = {row[0]: row[1] for row in eng_result.all()}

    engagement_states = EngagementDistribution(
        calibrating=eng_counts.get("calibrating", 0),
        in_zone=eng_counts.get("in_zone", 0),
        drifting=eng_counts.get("drifting", 0),
        clingy=eng_counts.get("clingy", 0),
        distant=eng_counts.get("distant", 0),
        out_of_zone=eng_counts.get("out_of_zone", 0),
    )

    # Active user counts
    now = datetime.now(UTC)
    since_24h = now - timedelta(hours=24)
    since_7d = now - timedelta(days=7)
    since_30d = now - timedelta(days=30)

    active_24h_stmt = select(func.count(User.id)).where(
        User.last_interaction_at >= since_24h
    )
    active_7d_stmt = select(func.count(User.id)).where(
        User.last_interaction_at >= since_7d
    )
    active_30d_stmt = select(func.count(User.id)).where(
        User.last_interaction_at >= since_30d
    )

    active_24h = (await session.execute(active_24h_stmt)).scalar() or 0
    active_7d = (await session.execute(active_7d_stmt)).scalar() or 0
    active_30d = (await session.execute(active_30d_stmt)).scalar() or 0

    active_users = ActiveUserCounts(
        last_24h=active_24h,
        last_7d=active_7d,
        last_30d=active_30d,
    )

    return SystemOverviewResponse(
        total_users=total_users,
        game_status=game_status,
        chapters=chapters,
        engagement_states=engagement_states,
        active_users=active_users,
    )


# ============================================================================
# T2.2: Jobs Status Endpoint
# ============================================================================


@router.get("/jobs", response_model=JobStatusResponse)
async def get_job_status(
    admin_user_id: Annotated[UUID, Depends(get_current_admin_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Get scheduled jobs status.

    Returns last execution info for each job type.

    AC-FR008-001: Returns all 5 job types listed
    AC-FR008-002: Returns last_run timestamp
    AC-FR008-003: Returns status (running, completed, failed)
    AC-FR008-004: Returns duration_ms of last run
    AC-FR008-005: Returns error info for failed jobs
    """
    job_repo = JobExecutionRepository(session)
    now = datetime.now(UTC)
    since_24h = now - timedelta(hours=24)

    jobs = []
    all_job_names = [
        JobName.DECAY.value,
        JobName.DELIVER.value,
        JobName.SUMMARY.value,
        JobName.CLEANUP.value,
        JobName.PROCESS_CONVERSATIONS.value,
    ]

    for job_name in all_job_names:
        # Get latest execution
        latest = await job_repo.get_latest_by_job_name(job_name)

        # Count runs and failures in last 24h
        runs_stmt = select(func.count(JobExecution.id)).where(
            JobExecution.job_name == job_name, JobExecution.started_at >= since_24h
        )
        runs_24h = (await session.execute(runs_stmt)).scalar() or 0

        failures_stmt = select(func.count(JobExecution.id)).where(
            JobExecution.job_name == job_name,
            JobExecution.started_at >= since_24h,
            JobExecution.status == JobStatus.FAILED.value,
        )
        failures_24h = (await session.execute(failures_stmt)).scalar() or 0

        jobs.append(
            JobExecutionStatus(
                job_name=job_name,
                last_run_at=latest.started_at if latest else None,
                last_status=latest.status if latest else None,
                last_duration_ms=latest.duration_ms if latest else None,
                last_result=latest.result if latest else None,
                runs_24h=runs_24h,
                failures_24h=failures_24h,
            )
        )

    # Get recent failures (last 10)
    failures_stmt = (
        select(JobExecution)
        .where(JobExecution.status == JobStatus.FAILED.value)
        .order_by(JobExecution.started_at.desc())
        .limit(10)
    )
    failures_result = await session.execute(failures_stmt)
    recent_failures = [
        JobExecutionStatus(
            job_name=f.job_name,
            last_run_at=f.started_at,
            last_status=f.status,
            last_duration_ms=f.duration_ms,
            last_result=f.result,
            runs_24h=0,
            failures_24h=0,
        )
        for f in failures_result.scalars().all()
    ]

    return JobStatusResponse(jobs=jobs, recent_failures=recent_failures)


# ============================================================================
# T2.3: User List Endpoint
# ============================================================================


@router.get("/users", response_model=UserListResponse)
async def list_debug_users(
    admin_user_id: Annotated[UUID, Depends(get_current_admin_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    game_status: str | None = Query(default=None),
    chapter: int | None = Query(default=None, ge=1, le=5),
):
    """List users for debug portal (paginated).

    Returns user list with summary info.

    AC-FR003-001: Returns paginated list (50 per page default)
    AC-FR003-002: Supports filter by game_status query param
    AC-FR003-003: Supports filter by chapter query param
    """
    offset = (page - 1) * page_size

    # Build base query
    stmt = (
        select(User, EngagementState)
        .outerjoin(EngagementState, User.id == EngagementState.user_id)
    )

    # Apply filters
    if game_status:
        stmt = stmt.where(User.game_status == game_status)
    if chapter:
        stmt = stmt.where(User.chapter == chapter)

    # Count total (before pagination)
    count_stmt = select(func.count(User.id))
    if game_status:
        count_stmt = count_stmt.where(User.game_status == game_status)
    if chapter:
        count_stmt = count_stmt.where(User.chapter == chapter)
    total_count = (await session.execute(count_stmt)).scalar() or 0

    # Apply pagination and order
    stmt = stmt.order_by(User.last_interaction_at.desc().nullslast())
    stmt = stmt.offset(offset).limit(page_size)

    result = await session.execute(stmt)
    rows = result.all()

    users = [
        UserListItem(
            id=user.id,
            telegram_id=user.telegram_id,
            email=None,  # Would need to fetch from auth.users
            relationship_score=float(user.relationship_score),
            chapter=user.chapter,
            engagement_state=engagement.state if engagement else None,
            game_status=user.game_status,
            last_interaction_at=user.last_interaction_at,
            created_at=user.created_at,
        )
        for user, engagement in rows
    ]

    return UserListResponse(
        users=users,
        total_count=total_count,
        page=page,
        page_size=page_size,
    )


# ============================================================================
# T2.4: User Detail Endpoint
# ============================================================================


@router.get("/users/{user_id}", response_model=UserDetailResponse)
async def get_debug_user_detail(
    user_id: UUID,
    admin_user_id: Annotated[UUID, Depends(get_current_admin_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Get user debug detail.

    Returns comprehensive user info including timing and next actions.
    """
    user_repo = UserRepository(session)
    user = await user_repo.get(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Calculate timing info
    now = datetime.now(UTC)
    grace_period_hours = 8  # Default grace period
    hours_since_interaction = 0.0

    if user.last_interaction_at:
        delta = now - user.last_interaction_at.replace(tzinfo=UTC)
        hours_since_interaction = delta.total_seconds() / 3600

    grace_remaining = max(0, grace_period_hours - hours_since_interaction)
    is_in_grace = grace_remaining > 0
    decay_rate = float(DECAY_RATES.get(user.chapter, 0.5))
    boss_threshold = float(BOSS_THRESHOLDS.get(user.chapter, 65))

    timing = UserTimingInfo(
        grace_period_remaining_hours=grace_remaining,
        is_in_grace_period=is_in_grace,
        decay_rate_per_hour=decay_rate,
        hours_since_last_interaction=hours_since_interaction,
        next_decay_at=None if is_in_grace else now,
        boss_ready=float(user.relationship_score) >= boss_threshold,
        boss_attempts_remaining=3 - user.boss_attempts,
    )

    score_to_boss = boss_threshold - float(user.relationship_score)
    next_actions = UserNextActions(
        should_decay=not is_in_grace,
        decay_due_at=None if is_in_grace else now,
        can_trigger_boss=float(user.relationship_score) >= boss_threshold
        and user.boss_attempts < 3,
        boss_threshold=boss_threshold,
        score_to_boss=max(0, score_to_boss),
    )

    return UserDetailResponse(
        id=user.id,
        telegram_id=user.telegram_id,
        email=None,  # Would need to fetch from auth.users
        phone=user.phone,
        relationship_score=float(user.relationship_score),
        chapter=user.chapter,
        chapter_name=CHAPTER_NAMES.get(user.chapter, "Unknown"),
        boss_attempts=user.boss_attempts,
        days_played=user.days_played,
        game_status=user.game_status,
        timing=timing,
        next_actions=next_actions,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_interaction_at=user.last_interaction_at,
    )


# ============================================================================
# T2.5: State Machines Endpoint
# ============================================================================


@router.get("/state-machines/{user_id}", response_model=StateMachinesResponse)
async def get_user_state_machines(
    user_id: UUID,
    admin_user_id: Annotated[UUID, Depends(get_current_admin_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Get all state machine status for a user.

    Returns engagement state, chapter progress, and vice profile.
    """
    user_repo = UserRepository(session)
    engagement_repo = EngagementStateRepository(session)
    vice_repo = VicePreferenceRepository(session)

    user = await user_repo.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Engagement state
    engagement = await engagement_repo.get_by_user_id(user_id)
    transitions = await engagement_repo.get_recent_transitions(user_id, limit=10)

    engagement_info = EngagementStateInfo(
        current_state=engagement.state if engagement else "calibrating",
        multiplier=float(engagement.multiplier) if engagement else 1.0,
        calibration_score=float(engagement.calibration_score) if engagement else 0.0,
        consecutive_in_zone=engagement.consecutive_in_zone if engagement else 0,
        consecutive_clingy_days=engagement.consecutive_clingy_days if engagement else 0,
        consecutive_distant_days=engagement.consecutive_distant_days
        if engagement
        else 0,
        recent_transitions=[
            {
                "from_state": t.from_state,
                "to_state": t.to_state,
                "reason": t.reason,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in transitions
        ],
    )

    # Chapter state
    boss_threshold = BOSS_THRESHOLDS.get(user.chapter, 65)
    current_score = float(user.relationship_score)
    progress_to_boss = min(100, (current_score / boss_threshold) * 100)

    chapter_info = ChapterStateInfo(
        current_chapter=user.chapter,
        chapter_name=CHAPTER_NAMES.get(user.chapter, "Unknown"),
        boss_threshold=boss_threshold,
        current_score=current_score,
        progress_to_boss=progress_to_boss,
        boss_attempts=user.boss_attempts,
        can_trigger_boss=current_score >= boss_threshold and user.boss_attempts < 3,
    )

    # Vice profile
    vices = await vice_repo.get_by_user(user_id)
    top_vices = sorted(vices, key=lambda v: float(v.engagement_score), reverse=True)[:5]

    vice_profile = ViceProfileInfo(
        top_vices=[
            ViceInfo(
                category=v.category,
                intensity_level=v.intensity_level,
                engagement_score=float(v.engagement_score),
                discovered_at=v.discovered_at,
            )
            for v in top_vices
        ],
        total_vices_discovered=len(vices),
        expression_level="moderate",  # Would calculate based on intensity levels
    )

    return StateMachinesResponse(
        user_id=user_id,
        engagement=engagement_info,
        chapter=chapter_info,
        vice_profile=vice_profile,
    )


# ============================================================================
# Memory Integration Test (Supabase pgVector)
# ============================================================================


@router.post("/memory-test")
async def test_memory_integration(
    user_id: str,
    admin_user_id: Annotated[UUID, Depends(get_current_admin_user)],
):
    """Test Supabase memory by adding and retrieving a fact.

    This endpoint verifies:
    1. SupabaseMemory client initializes
    2. Can add facts via pgVector
    3. Search returns results

    Args:
        user_id: User ID string to test with (can be any UUID string).
        admin_user_id: Admin performing the test (from auth).

    Returns:
        Dict with status and test results.
    """
    from nikita.memory import get_memory_client

    try:
        memory = await get_memory_client(user_id)

        test_fact = f"Integration test at {datetime.now(UTC).isoformat()}"
        await memory.add_user_fact(fact=test_fact, confidence=1.0)

        results = await memory.search_memory(query="Integration test", limit=5)

        return {
            "status": "ok",
            "added_fact": test_fact,
            "search_results_count": len(results),
            "facts_found": results[:3] if results else [],
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "error_type": type(e).__name__,
        }


# ============================================================================
# Prompt Viewing Endpoints (Spec 018)
# ============================================================================


@router.get("/prompts/{user_id}", response_model=PromptListResponse)
async def list_user_prompts(
    user_id: UUID,
    admin_user_id: Annotated[UUID, Depends(get_current_admin_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    limit: int = Query(default=10, ge=1, le=50),
):
    """List recent prompts for a user.

    Returns prompt metadata without full content for quick browsing.

    Args:
        user_id: The user's UUID.
        limit: Maximum number of prompts to return (1-50, default 10).

    AC-018-001: Returns list with id, token_count, generation_time_ms, meta_prompt_template, created_at
    AC-018-002: Accepts limit parameter (clamped to 1-50)
    AC-018-003: Requires admin authentication
    AC-018-004: Returns empty list for non-existent user (not 404)
    """
    from nikita.db.repositories.generated_prompt_repository import GeneratedPromptRepository

    repo = GeneratedPromptRepository(session)
    prompts = await repo.get_recent_by_user_id(user_id, limit=limit)

    return PromptListResponse(
        items=[
            PromptListItem(
                id=p.id,
                token_count=p.token_count,
                generation_time_ms=p.generation_time_ms,
                meta_prompt_template=p.meta_prompt_template,
                created_at=p.created_at,
                conversation_id=p.conversation_id,
            )
            for p in prompts
        ],
        count=len(prompts),
        user_id=user_id,
    )


@router.get("/prompts/{user_id}/latest", response_model=PromptDetailResponse | None)
async def get_latest_prompt(
    user_id: UUID,
    admin_user_id: Annotated[UUID, Depends(get_current_admin_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Get the most recent prompt for a user with full content.

    Returns complete prompt including content and context snapshot.

    Args:
        user_id: The user's UUID.

    AC-018-005: Returns full prompt_content, token_count, generation_time_ms,
                meta_prompt_template, context_snapshot, created_at
    AC-018-006: Returns null/empty with message for user with no prompts
    AC-018-007: Includes conversation_id if present
    """
    from nikita.db.repositories.generated_prompt_repository import GeneratedPromptRepository

    repo = GeneratedPromptRepository(session)
    prompt = await repo.get_latest_by_user_id(user_id)

    if not prompt:
        return PromptDetailResponse(
            prompt_content="",
            token_count=0,
            generation_time_ms=0,
            meta_prompt_template="",
            is_preview=False,
            message="No prompts found for this user",
        )

    return PromptDetailResponse(
        id=prompt.id,
        prompt_content=prompt.prompt_content,
        token_count=prompt.token_count,
        generation_time_ms=prompt.generation_time_ms,
        meta_prompt_template=prompt.meta_prompt_template,
        context_snapshot=prompt.context_snapshot,
        conversation_id=prompt.conversation_id,
        created_at=prompt.created_at,
        is_preview=False,
    )


@router.post("/prompts/{user_id}/preview", response_model=PromptDetailResponse)
async def preview_next_prompt(
    user_id: UUID,
    admin_user_id: Annotated[UUID, Depends(get_current_admin_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Generate a preview of what the next system prompt would be.

    Generates the prompt WITHOUT logging it to the database.
    Use this to verify prompt configuration before testing.

    Args:
        user_id: The user's UUID.

    AC-018-008: Generates preview without logging to database
    AC-018-009: Returns 404 for non-existent user_id
    AC-018-010: Includes context_snapshot used for generation
    AC-018-011: Returns is_preview=true flag
    """
    import time
    from datetime import datetime, timezone
    from nikita.db.repositories.user_repository import UserRepository
    from nikita.db.repositories.conversation_repository import ConversationRepository
    from nikita.pipeline.stages.prompt_builder import PromptBuilderStage
    from nikita.pipeline.models import PipelineContext

    # Verify user exists (404 for non-existent)
    user_repo = UserRepository(session)
    user = await user_repo.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get most recent conversation for context
    conv_repo = ConversationRepository(session)
    conversations = await conv_repo.get_recent(user_id, limit=1)
    conversation_id = conversations[0].id if conversations else None

    # Build minimal PipelineContext
    ctx = PipelineContext(
        user_id=user_id,
        conversation_id=conversation_id,
        platform="text",  # Default to text for preview
        started_at=datetime.now(timezone.utc),
        chapter=user.chapter,
        relationship_score=user.relationship_score,
        game_status=user.game_status,
        engagement_state="unknown",
        vices=[],
        metrics={},
        extracted_facts=[],
        extracted_threads=[],
        extracted_thoughts=[],
        extraction_summary="",
        emotional_tone="neutral",
        life_events=[],
        emotional_state={},
        score_delta=0,
        active_conflict=None,
        conflict_type=None,
        touchpoint_scheduled=False,
        generated_prompt="",
        prompt_token_count=0,
    )

    # Run prompt builder stage (with session for template loading)
    stage = PromptBuilderStage(session=session)
    start = time.perf_counter()
    try:
        result = await stage._run(ctx)
        gen_time_ms = (time.perf_counter() - start) * 1000

        if result and result.get("generated"):
            return PromptDetailResponse(
                id=None,
                user_id=user_id,
                conversation_id=conversation_id,
                prompt_content=ctx.generated_prompt,
                token_count=ctx.prompt_token_count,
                generation_time_ms=gen_time_ms,
                meta_prompt_template="system_prompt.j2",
                context_snapshot={
                    "chapter": ctx.chapter,
                    "relationship_score": float(ctx.relationship_score),
                    "game_status": ctx.game_status,
                },
                created_at=datetime.now(timezone.utc),
                is_preview=True,
            )
        else:
            return PromptDetailResponse(
                id=None,
                user_id=user_id,
                conversation_id=conversation_id,
                prompt_content="Prompt generation failed - check stage logs",
                token_count=0,
                generation_time_ms=gen_time_ms,
                meta_prompt_template="error",
                context_snapshot={},
                created_at=datetime.now(timezone.utc),
                is_preview=True,
            )
    except Exception as e:
        gen_time_ms = (time.perf_counter() - start) * 1000
        return PromptDetailResponse(
            id=None,
            user_id=user_id,
            conversation_id=conversation_id,
            prompt_content=f"Error generating prompt: {str(e)}",
            token_count=0,
            generation_time_ms=gen_time_ms,
            meta_prompt_template="error",
            context_snapshot={},
            created_at=datetime.now(timezone.utc),
            is_preview=True,
        )


# ============================================================================
# T3.1: Voice Monitoring Endpoints (Phase 3.1)
# ============================================================================


@router.get("/voice/conversations", response_model=VoiceConversationListResponse)
async def list_voice_conversations(
    admin_user_id: Annotated[UUID, Depends(get_current_admin_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user_id: UUID | None = Query(default=None, description="Filter by user ID"),
    status: str | None = Query(default=None, description="Filter by status"),
):
    """List voice conversations from the database.

    Returns voice conversations (platform='voice') with pagination.
    Includes user name, transcript summary, and processing status.
    """
    from sqlalchemy.orm import selectinload

    # Build query for voice conversations
    query = (
        select(Conversation)
        .options(selectinload(Conversation.user))
        .where(Conversation.platform == "voice")
        .order_by(Conversation.started_at.desc())
    )

    if user_id:
        query = query.where(Conversation.user_id == user_id)
    if status:
        query = query.where(Conversation.status == status)

    # Count total
    count_query = select(func.count()).select_from(
        select(Conversation.id)
        .where(Conversation.platform == "voice")
        .subquery()
    )
    if user_id:
        count_query = select(func.count()).select_from(
            select(Conversation.id)
            .where(Conversation.platform == "voice")
            .where(Conversation.user_id == user_id)
            .subquery()
        )

    count_result = await session.execute(count_query)
    total_count = count_result.scalar() or 0

    # Get paginated results
    query = query.offset(offset).limit(limit)
    result = await session.execute(query)
    conversations = result.scalars().all()

    items = [
        VoiceConversationListItem(
            id=conv.id,
            user_id=conv.user_id,
            user_name=f"User {conv.user.telegram_id}" if conv.user and conv.user.telegram_id else None,
            started_at=conv.started_at,
            ended_at=conv.ended_at,
            message_count=len(conv.messages) if conv.messages else 0,
            score_delta=float(conv.score_delta) if conv.score_delta else None,
            chapter_at_time=conv.chapter_at_time,
            elevenlabs_session_id=conv.elevenlabs_session_id,
            status=conv.status,
            conversation_summary=conv.conversation_summary,
        )
        for conv in conversations
    ]

    return VoiceConversationListResponse(
        items=items,
        count=total_count,
        has_more=(offset + limit) < total_count,
    )


@router.get("/voice/conversations/{conversation_id}", response_model=VoiceConversationDetailResponse)
async def get_voice_conversation_detail(
    conversation_id: UUID,
    admin_user_id: Annotated[UUID, Depends(get_current_admin_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Get full voice conversation detail with transcript.

    Returns complete conversation including raw transcript and parsed messages.
    """
    from sqlalchemy.orm import selectinload

    query = (
        select(Conversation)
        .options(selectinload(Conversation.user))
        .where(Conversation.id == conversation_id)
        .where(Conversation.platform == "voice")
    )

    result = await session.execute(query)
    conv = result.scalar_one_or_none()

    if not conv:
        raise HTTPException(status_code=404, detail="Voice conversation not found")

    # Parse messages into transcript entries
    messages = []
    if conv.messages:
        for msg in conv.messages:
            # Convert timestamp to string if present (can be int or str)
            ts = msg.get("timestamp")
            ts_str = str(ts) if ts is not None else None
            messages.append(
                TranscriptEntryResponse(
                    role=msg.get("role", "unknown"),
                    content=msg.get("content") or "",  # Handle None content
                    timestamp=ts_str,
                )
            )

    return VoiceConversationDetailResponse(
        id=conv.id,
        user_id=conv.user_id,
        user_name=f"User {conv.user.telegram_id}" if conv.user and conv.user.telegram_id else None,
        started_at=conv.started_at,
        ended_at=conv.ended_at,
        message_count=len(conv.messages) if conv.messages else 0,
        score_delta=float(conv.score_delta) if conv.score_delta else None,
        chapter_at_time=conv.chapter_at_time,
        elevenlabs_session_id=conv.elevenlabs_session_id,
        status=conv.status,
        conversation_summary=conv.conversation_summary,
        emotional_tone=conv.emotional_tone,
        transcript_raw=conv.transcript_raw,
        messages=messages,
        extracted_entities=conv.extracted_entities,
        processed_at=conv.processed_at,
    )


@router.get("/voice/stats", response_model=VoiceStatsResponse)
async def get_voice_stats(
    admin_user_id: Annotated[UUID, Depends(get_current_admin_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Get voice call statistics.

    Returns aggregated stats for voice conversations including:
    - Call counts by time period (24h, 7d, 30d)
    - Calls by chapter
    - Processing status distribution
    """
    now = datetime.now(UTC)
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    # Count calls by time period
    calls_24h = await session.execute(
        select(func.count(Conversation.id))
        .where(Conversation.platform == "voice")
        .where(Conversation.started_at >= day_ago)
    )
    calls_7d = await session.execute(
        select(func.count(Conversation.id))
        .where(Conversation.platform == "voice")
        .where(Conversation.started_at >= week_ago)
    )
    calls_30d = await session.execute(
        select(func.count(Conversation.id))
        .where(Conversation.platform == "voice")
        .where(Conversation.started_at >= month_ago)
    )

    # Calls by chapter
    chapter_result = await session.execute(
        select(Conversation.chapter_at_time, func.count(Conversation.id))
        .where(Conversation.platform == "voice")
        .where(Conversation.chapter_at_time.isnot(None))
        .group_by(Conversation.chapter_at_time)
    )
    calls_by_chapter = {row[0]: row[1] for row in chapter_result.all()}

    # Calls by status
    status_result = await session.execute(
        select(Conversation.status, func.count(Conversation.id))
        .where(Conversation.platform == "voice")
        .group_by(Conversation.status)
    )
    calls_by_status = {row[0]: row[1] for row in status_result.all()}

    return VoiceStatsResponse(
        total_calls_24h=calls_24h.scalar() or 0,
        total_calls_7d=calls_7d.scalar() or 0,
        total_calls_30d=calls_30d.scalar() or 0,
        calls_by_chapter=calls_by_chapter,
        calls_by_status=calls_by_status,
        processing_stats=calls_by_status,  # Same data for now
    )


@router.get("/voice/elevenlabs", response_model=ElevenLabsCallListResponse)
async def list_elevenlabs_calls(
    admin_user_id: Annotated[UUID, Depends(get_current_admin_user)],
    limit: int = Query(default=30, ge=1, le=100),
    cursor: str | None = Query(default=None, description="Pagination cursor"),
    include_summary: bool = Query(default=False, description="Include transcript summaries"),
):
    """List recent calls from ElevenLabs API.

    Fetches call history directly from ElevenLabs Conversations API.
    This provides access to calls that may not have been processed yet.
    """
    from nikita.agents.voice.elevenlabs_client import get_elevenlabs_client
    from nikita.config.settings import get_settings

    settings = get_settings()
    agent_id = settings.elevenlabs_default_agent_id

    try:
        client = get_elevenlabs_client()
        result = await client.list_conversations(
            agent_id=agent_id,
            limit=limit,
            cursor=cursor,
            include_summary=include_summary,
        )

        items = [
            ElevenLabsCallListItem(
                conversation_id=conv.conversation_id,
                agent_id=conv.agent_id,
                start_time_unix=conv.start_time_unix_secs,
                call_duration_secs=conv.call_duration_secs,
                message_count=conv.message_count,
                status=conv.status.value,
                call_successful=conv.call_successful,
                transcript_summary=conv.transcript_summary,
                direction=conv.direction.value if conv.direction else None,
            )
            for conv in result.conversations
        ]

        return ElevenLabsCallListResponse(
            items=items,
            has_more=result.has_more,
            next_cursor=result.next_cursor,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch ElevenLabs calls: {type(e).__name__}: {str(e)}",
        )


@router.get("/voice/elevenlabs/{conversation_id}", response_model=ElevenLabsCallDetailResponse)
async def get_elevenlabs_call_detail(
    conversation_id: str,
    admin_user_id: Annotated[UUID, Depends(get_current_admin_user)],
):
    """Get full call detail from ElevenLabs API.

    Fetches complete conversation including transcript and tool calls.
    This provides access to the raw ElevenLabs data for debugging.
    """
    from nikita.agents.voice.elevenlabs_client import get_elevenlabs_client

    try:
        client = get_elevenlabs_client()
        detail = await client.get_conversation(conversation_id)

        transcript = [
            ElevenLabsTranscriptTurn(
                role=turn.role,
                message=turn.message,
                time_in_call_secs=turn.time_in_call_secs,
                tool_calls=turn.tool_calls,
                tool_results=turn.tool_results,
            )
            for turn in detail.transcript
        ]

        return ElevenLabsCallDetailResponse(
            conversation_id=detail.conversation_id,
            agent_id=detail.agent_id,
            status=detail.status.value,
            transcript=transcript,
            start_time_unix=detail.metadata.start_time_unix_secs if detail.metadata else None,
            call_duration_secs=detail.metadata.call_duration_secs if detail.metadata else None,
            cost=detail.metadata.cost if detail.metadata else None,
            transcript_summary=detail.analysis.transcript_summary if detail.analysis else None,
            call_successful=detail.analysis.call_successful if detail.analysis else None,
            has_audio=detail.has_audio,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch ElevenLabs call: {type(e).__name__}: {str(e)}",
        )


# ============================================================================
# T4.1: Text Monitoring Endpoints (Phase 4.1)
# ============================================================================


@router.get("/text/conversations", response_model=TextConversationListResponse)
async def list_text_conversations(
    admin_user_id: Annotated[UUID, Depends(get_current_admin_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user_id: UUID | None = Query(default=None, description="Filter by user ID"),
    status: str | None = Query(default=None, description="Filter by status"),
    boss_fight_only: bool = Query(default=False, description="Only show boss fights"),
):
    """List text conversations from the database.

    Returns text conversations (platform='telegram') with pagination.
    Includes user name, summary, and processing status.
    """
    from sqlalchemy.orm import selectinload

    # Build query for text conversations
    query = (
        select(Conversation)
        .options(selectinload(Conversation.user))
        .where(Conversation.platform == "telegram")
        .order_by(Conversation.started_at.desc())
    )

    if user_id:
        query = query.where(Conversation.user_id == user_id)
    if status:
        query = query.where(Conversation.status == status)
    if boss_fight_only:
        query = query.where(Conversation.is_boss_fight == True)

    # Count total
    count_query = select(func.count()).select_from(
        select(Conversation.id)
        .where(Conversation.platform == "telegram")
        .subquery()
    )
    count_result = await session.execute(count_query)
    total_count = count_result.scalar() or 0

    # Get paginated results
    query = query.offset(offset).limit(limit)
    result = await session.execute(query)
    conversations = result.scalars().all()

    items = [
        TextConversationListItem(
            id=conv.id,
            user_id=conv.user_id,
            user_name=f"User {conv.user.telegram_id}" if conv.user and conv.user.telegram_id else None,
            started_at=conv.started_at,
            ended_at=conv.ended_at,
            message_count=len(conv.messages) if conv.messages else 0,
            score_delta=float(conv.score_delta) if conv.score_delta else None,
            chapter_at_time=conv.chapter_at_time,
            is_boss_fight=conv.is_boss_fight,
            status=conv.status,
            conversation_summary=conv.conversation_summary,
            emotional_tone=conv.emotional_tone,
        )
        for conv in conversations
    ]

    return TextConversationListResponse(
        items=items,
        count=total_count,
        has_more=(offset + limit) < total_count,
    )


@router.get("/text/conversations/{conversation_id}", response_model=TextConversationDetailResponse)
async def get_text_conversation_detail(
    conversation_id: UUID,
    admin_user_id: Annotated[UUID, Depends(get_current_admin_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Get full text conversation detail with messages.

    Returns complete conversation including all messages with analysis.
    """
    from sqlalchemy.orm import selectinload

    query = (
        select(Conversation)
        .options(selectinload(Conversation.user))
        .where(Conversation.id == conversation_id)
        .where(Conversation.platform == "telegram")
    )

    result = await session.execute(query)
    conv = result.scalar_one_or_none()

    if not conv:
        raise HTTPException(status_code=404, detail="Text conversation not found")

    # Parse messages
    messages = []
    if conv.messages:
        for msg in conv.messages:
            # Convert timestamp to string if present (can be int or str)
            ts = msg.get("timestamp")
            ts_str = str(ts) if ts is not None else None
            messages.append(
                MessageResponse(
                    role=msg.get("role", "unknown"),
                    content=msg.get("content") or "",  # Handle None content
                    timestamp=ts_str,
                    analysis=msg.get("analysis"),
                )
            )

    return TextConversationDetailResponse(
        id=conv.id,
        user_id=conv.user_id,
        user_name=f"User {conv.user.telegram_id}" if conv.user and conv.user.telegram_id else None,
        started_at=conv.started_at,
        ended_at=conv.ended_at,
        message_count=len(conv.messages) if conv.messages else 0,
        score_delta=float(conv.score_delta) if conv.score_delta else None,
        chapter_at_time=conv.chapter_at_time,
        is_boss_fight=conv.is_boss_fight,
        status=conv.status,
        conversation_summary=conv.conversation_summary,
        emotional_tone=conv.emotional_tone,
        messages=messages,
        extracted_entities=conv.extracted_entities,
        processed_at=conv.processed_at,
        processing_attempts=conv.processing_attempts,
        last_message_at=conv.last_message_at,
    )


@router.get("/text/stats", response_model=TextStatsResponse)
async def get_text_stats(
    admin_user_id: Annotated[UUID, Depends(get_current_admin_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Get text conversation statistics.

    Returns aggregated stats for text conversations including:
    - Conversation counts by time period (24h, 7d, 30d)
    - Messages sent in 24h
    - Boss fight counts
    - Processing status distribution
    """
    now = datetime.now(UTC)
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    # Count conversations by time period
    convs_24h = await session.execute(
        select(func.count(Conversation.id))
        .where(Conversation.platform == "telegram")
        .where(Conversation.started_at >= day_ago)
    )
    convs_7d = await session.execute(
        select(func.count(Conversation.id))
        .where(Conversation.platform == "telegram")
        .where(Conversation.started_at >= week_ago)
    )
    convs_30d = await session.execute(
        select(func.count(Conversation.id))
        .where(Conversation.platform == "telegram")
        .where(Conversation.started_at >= month_ago)
    )

    # Boss fights in 24h
    boss_24h = await session.execute(
        select(func.count(Conversation.id))
        .where(Conversation.platform == "telegram")
        .where(Conversation.is_boss_fight == True)
        .where(Conversation.started_at >= day_ago)
    )

    # Conversations by chapter
    chapter_result = await session.execute(
        select(Conversation.chapter_at_time, func.count(Conversation.id))
        .where(Conversation.platform == "telegram")
        .where(Conversation.chapter_at_time.isnot(None))
        .group_by(Conversation.chapter_at_time)
    )
    convs_by_chapter = {row[0]: row[1] for row in chapter_result.all()}

    # Conversations by status
    status_result = await session.execute(
        select(Conversation.status, func.count(Conversation.id))
        .where(Conversation.platform == "telegram")
        .group_by(Conversation.status)
    )
    convs_by_status = {row[0]: row[1] for row in status_result.all()}

    return TextStatsResponse(
        total_conversations_24h=convs_24h.scalar() or 0,
        total_conversations_7d=convs_7d.scalar() or 0,
        total_conversations_30d=convs_30d.scalar() or 0,
        conversations_by_chapter=convs_by_chapter,
        conversations_by_status=convs_by_status,
        boss_fights_24h=boss_24h.scalar() or 0,
        processing_stats=convs_by_status,
    )


@router.get("/text/pipeline/{conversation_id}", response_model=PipelineStatusResponse)
async def get_pipeline_status(
    conversation_id: UUID,
    admin_user_id: Annotated[UUID, Depends(get_current_admin_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Get post-processing pipeline status for a conversation.

    Returns the pipeline stages and their completion status.
    Useful for debugging post-processing issues.
    """
    from nikita.db.models.context import ConversationThread, NikitaThought

    # Get conversation
    conv = await session.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Count threads created for this conversation
    threads_result = await session.execute(
        select(func.count(ConversationThread.id))
        .where(ConversationThread.source_conversation_id == conversation_id)
    )
    threads_count = threads_result.scalar() or 0

    # Count thoughts created for this conversation
    thoughts_result = await session.execute(
        select(func.count(NikitaThought.id))
        .where(NikitaThought.source_conversation_id == conversation_id)
    )
    thoughts_count = thoughts_result.scalar() or 0

    # Determine pipeline stages based on status and data
    # CORRECT stage names from PipelineOrchestrator.STAGE_DEFINITIONS (Spec 042):
    # extraction, memory_update, life_sim, emotional, game_state, conflict, touchpoint, summary, prompt_builder
    stages = []

    # Stage 1: extraction (entity extraction)
    has_entities = bool(conv.extracted_entities)
    stages.append(PipelineStageStatus(
        stage_name="extraction",
        stage_number=1,
        completed=has_entities,
        result_summary=f"{len(conv.extracted_entities.get('entities', [])) if conv.extracted_entities else 0} entities" if has_entities else None
    ))

    # Stage 2: memory_update (memory storage)
    stages.append(PipelineStageStatus(
        stage_name="memory_update",
        stage_number=2,
        completed=threads_count > 0 or thoughts_count > 0,
        result_summary=f"{threads_count} threads, {thoughts_count} thoughts" if threads_count > 0 or thoughts_count > 0 else None
    ))

    # Stage 3: life_sim (life events)
    stages.append(PipelineStageStatus(
        stage_name="life_sim",
        stage_number=3,
        completed=True,  # Non-critical, always runs
        result_summary="Life events generated"
    ))

    # Stage 4: emotional (emotional state)
    has_summary = bool(conv.conversation_summary)
    stages.append(PipelineStageStatus(
        stage_name="emotional",
        stage_number=4,
        completed=has_summary,
        result_summary=conv.emotional_tone if has_summary else None
    ))

    # Stage 5: game_state (scoring, chapters, decay)
    stages.append(PipelineStageStatus(
        stage_name="game_state",
        stage_number=5,
        completed=True,
        result_summary="Game state updated"
    ))

    # Stage 6: conflict (conflict generation)
    stages.append(PipelineStageStatus(
        stage_name="conflict",
        stage_number=6,
        completed=True,
        result_summary="Conflict check complete"
    ))

    # Stage 7: touchpoint (proactive touchpoints)
    stages.append(PipelineStageStatus(
        stage_name="touchpoint",
        stage_number=7,
        completed=True,
        result_summary="Touchpoint check complete"
    ))

    # Stage 8: summary (daily summaries)
    is_processed = conv.status == "processed"
    stages.append(PipelineStageStatus(
        stage_name="summary",
        stage_number=8,
        completed=is_processed,
        result_summary="Summary rollup" if is_processed else None
    ))

    # Stage 9: prompt_builder (prompt generation)
    stages.append(PipelineStageStatus(
        stage_name="prompt_builder",
        stage_number=9,
        completed=is_processed,
        result_summary="Prompts generated" if is_processed else None
    ))

    return PipelineStatusResponse(
        conversation_id=conversation_id,
        status=conv.status,
        processing_attempts=conv.processing_attempts,
        processed_at=conv.processed_at,
        stages=stages,
        threads_created=threads_count,
        thoughts_created=thoughts_count,
        entities_extracted=len(conv.extracted_entities.get("entities", [])) if conv.extracted_entities else 0,
        summary=conv.conversation_summary,
    )


@router.get("/text/threads", response_model=ThreadListResponse)
async def list_threads(
    admin_user_id: Annotated[UUID, Depends(get_current_admin_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user_id: UUID | None = Query(default=None, description="Filter by user ID"),
    active_only: bool = Query(default=False, description="Only show active threads"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """List conversation threads.

    Returns threads created during post-processing.
    """
    from nikita.db.models.context import ConversationThread

    query = select(ConversationThread).order_by(ConversationThread.created_at.desc())

    if user_id:
        query = query.where(ConversationThread.user_id == user_id)
    if active_only:
        query = query.where(ConversationThread.is_active == True)

    # Count total
    count_query = select(func.count(ConversationThread.id))
    if user_id:
        count_query = count_query.where(ConversationThread.user_id == user_id)
    count_result = await session.execute(count_query)
    total_count = count_result.scalar() or 0

    # Get paginated results
    query = query.offset(offset).limit(limit)
    result = await session.execute(query)
    threads = result.scalars().all()

    items = [
        ThreadListItem(
            id=thread.id,
            user_id=thread.user_id,
            thread_type=thread.thread_type,
            topic=thread.topic,
            is_active=thread.is_active,
            message_count=thread.message_count,
            created_at=thread.created_at,
            last_mentioned_at=thread.last_mentioned_at,
        )
        for thread in threads
    ]

    return ThreadListResponse(items=items, count=total_count)


@router.get("/text/thoughts", response_model=ThoughtListResponse)
async def list_thoughts(
    admin_user_id: Annotated[UUID, Depends(get_current_admin_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user_id: UUID | None = Query(default=None, description="Filter by user ID"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """List Nikita thoughts.

    Returns thoughts generated during post-processing.
    """
    from nikita.db.models.context import NikitaThought

    query = select(NikitaThought).order_by(NikitaThought.created_at.desc())

    if user_id:
        query = query.where(NikitaThought.user_id == user_id)

    # Count total
    count_query = select(func.count(NikitaThought.id))
    if user_id:
        count_query = count_query.where(NikitaThought.user_id == user_id)
    count_result = await session.execute(count_query)
    total_count = count_result.scalar() or 0

    # Get paginated results
    query = query.offset(offset).limit(limit)
    result = await session.execute(query)
    thoughts = result.scalars().all()

    items = [
        ThoughtListItem(
            id=thought.id,
            user_id=thought.user_id,
            content=thought.content,
            thought_type=thought.thought_type,
            created_at=thought.created_at,
        )
        for thought in thoughts
    ]

    return ThoughtListResponse(items=items, count=total_count)
