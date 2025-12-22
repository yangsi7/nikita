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
    UserDetailResponse,
    UserListItem,
    UserListResponse,
    UserNextActions,
    UserTimingInfo,
    ViceInfo,
    ViceProfileInfo,
)
from nikita.db.database import get_async_session
from nikita.db.models.engagement import EngagementState
from nikita.db.models.job_execution import JobExecution, JobName, JobStatus
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
# Neo4j/Graphiti Integration Test
# ============================================================================


@router.post("/neo4j-test")
async def test_neo4j_integration(
    user_id: str,
    admin_user_id: Annotated[UUID, Depends(get_current_admin_user)],
):
    """Test Neo4j connection by adding and retrieving a fact.

    This endpoint verifies:
    1. Neo4j credentials are configured
    2. Connection to Neo4j Aura works
    3. NikitaMemory can add facts
    4. Search returns results

    Args:
        user_id: User ID string to test with (can be any UUID string).
        admin_user_id: Admin performing the test (from auth).

    Returns:
        Dict with status and test results.
    """
    from nikita.config.settings import get_settings
    from nikita.memory.graphiti_client import get_memory_client

    settings = get_settings()

    # Check if Neo4j is configured
    if not settings.neo4j_uri:
        return {
            "status": "error",
            "message": "NEO4J_URI not configured",
            "configured": False,
        }

    if not settings.neo4j_password:
        return {
            "status": "error",
            "message": "NEO4J_PASSWORD not configured",
            "configured": False,
        }

    try:
        # Initialize memory client
        memory = await get_memory_client(user_id)

        # Add test fact
        test_fact = f"Integration test at {datetime.now(UTC).isoformat()}"
        await memory.add_user_fact(fact=test_fact, confidence=1.0)

        # Search for test facts
        results = await memory.search_memory(query="Integration test", limit=5)

        return {
            "status": "ok",
            "configured": True,
            "neo4j_uri": settings.neo4j_uri[:30] + "...",  # Truncated for security
            "added_fact": test_fact,
            "search_results_count": len(results),
            "facts_found": results[:3] if results else [],
        }

    except Exception as e:
        return {
            "status": "error",
            "configured": True,
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
    from nikita.db.repositories.user_repository import UserRepository
    from nikita.meta_prompts.service import MetaPromptService

    # Verify user exists (404 for non-existent)
    user_repo = UserRepository(session)
    user = await user_repo.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Generate preview prompt (skip_logging=True)
    service = MetaPromptService(session)
    result = await service.generate_system_prompt(user_id, skip_logging=True)

    return PromptDetailResponse(
        id=None,  # No ID - not logged
        prompt_content=result.content,
        token_count=result.token_count,
        generation_time_ms=result.generation_time_ms,
        meta_prompt_template=result.meta_prompt_type,
        context_snapshot=result.context_snapshot,
        conversation_id=None,
        created_at=None,  # No created_at - not logged
        is_preview=True,
    )
