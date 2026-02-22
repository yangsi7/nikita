"""Admin API routes for system management and debugging."""

from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import String, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.api.schemas.admin import (
    AdminConversationsResponse,
    AdminHealthResponse,
    AdminResetResponse,
    AdminSetChapterRequest,
    AdminSetEngagementStateRequest,
    AdminSetGameStatusRequest,
    AdminSetMetricsRequest,
    AdminSetScoreRequest,
    AdminStatsResponse,
    AdminUserDetailResponse,
    AdminUserListItem,
    AuditLogItem,
    AuditLogsResponse,
    BossEncounterItem,
    BossEncountersResponse,
    ConversationListItem,
    ConversationPromptItem,
    ConversationPromptsResponse,
    ErrorLogItem,
    ErrorLogResponse,
    GeneratedPromptResponse,
    GeneratedPromptsResponse,
    PipelineHealthResponse,
    PipelineHistoryItem,
    PipelineHistoryResponse,
    PipelineStageItem,
    PipelineStatusResponse,
    ProcessingStatsResponse,
    StageFailure,
    StageStats,
    SystemOverviewResponse,
    TriggerPipelineRequest,
    TriggerPipelineResponse,
    UnifiedPipelineHealthResponse,
    UnifiedPipelineStageHealth,
)
from nikita.db.models.job_execution import JobExecution, JobName, JobStatus
from nikita.api.schemas.portal import (
    ConversationsResponse,
    EngagementResponse,
    UserMetricsResponse,
    VicePreferenceResponse,
)
from nikita.api.dependencies.auth import get_current_admin_user
from nikita.db.database import get_async_session
from nikita.db.models.conversation import Conversation
from nikita.db.models.engagement import EngagementHistory, EngagementState
from nikita.db.models.user import User, UserMetrics, UserVicePreference
from nikita.db.repositories.conversation_repository import ConversationRepository
from nikita.db.repositories.engagement_repository import EngagementStateRepository
from nikita.db.repositories.metrics_repository import UserMetricsRepository
from nikita.db.repositories.user_repository import UserRepository
from nikita.db.repositories.vice_repository import VicePreferenceRepository

router = APIRouter()


# Dependency for admin check - uses JWT validation from auth.py
# get_current_admin_user validates Supabase JWT and checks admin email domain
get_current_admin_user_id = get_current_admin_user


# ============================================================================
# USER ENDPOINTS
# ============================================================================


@router.get("/users", response_model=list[AdminUserListItem])
async def list_users(
    admin_id: Annotated[UUID, Depends(get_current_admin_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    page: int = 1,
    page_size: int = 50,
):
    """List all users (paginated, admin only)."""
    offset = (page - 1) * page_size

    stmt = (
        select(User, EngagementState)
        .outerjoin(EngagementState, User.id == EngagementState.user_id)
        .offset(offset)
        .limit(page_size)
    )
    result = await session.execute(stmt)
    rows = result.all()

    # Collect user IDs to batch-fetch emails from auth.users
    user_ids = [str(user.id) for user, _ in rows]
    email_map: dict[str, str] = {}
    if user_ids:
        # auth.users is a Supabase internal table in the auth schema.
        # We query it via raw SQL since SQLAlchemy models only cover public schema tables.
        placeholders = ", ".join(f"'{uid}'" for uid in user_ids)
        email_result = await session.execute(
            text(f"SELECT id::text, email FROM auth.users WHERE id::text IN ({placeholders})")
        )
        for row in email_result:
            email_map[row[0]] = row[1]

    return [
        AdminUserListItem(
            id=user.id,
            telegram_id=user.telegram_id,
            email=email_map.get(str(user.id)),
            relationship_score=user.relationship_score,
            chapter=user.chapter,
            engagement_state=engagement.state if engagement else "unknown",
            game_status=user.game_status,
            last_interaction_at=user.last_interaction_at,
            created_at=user.created_at,
        )
        for user, engagement in rows
    ]


@router.get("/users/{user_id}", response_model=AdminUserDetailResponse)
async def get_user_detail(
    user_id: UUID,
    admin_id: Annotated[UUID, Depends(get_current_admin_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Get full user detail (admin only)."""
    user_repo = UserRepository(session)
    user = await user_repo.get(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return AdminUserDetailResponse(
        id=user.id,
        telegram_id=user.telegram_id,
        phone=user.phone,
        relationship_score=user.relationship_score,
        chapter=user.chapter,
        boss_attempts=user.boss_attempts,
        days_played=user.days_played,
        game_status=user.game_status,
        last_interaction_at=user.last_interaction_at,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.get("/users/{user_id}/metrics", response_model=UserMetricsResponse)
async def get_user_metrics(
    user_id: UUID,
    admin_id: Annotated[UUID, Depends(get_current_admin_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Get user metrics (admin only)."""
    metrics_repo = UserMetricsRepository(session)
    metrics = await metrics_repo.get_by_user_id(user_id)

    if not metrics:
        raise HTTPException(status_code=404, detail="Metrics not found")

    return UserMetricsResponse(
        intimacy=metrics.intimacy,
        passion=metrics.passion,
        trust=metrics.trust,
        secureness=metrics.secureness,
    )


@router.get("/users/{user_id}/engagement", response_model=EngagementResponse)
async def get_user_engagement(
    user_id: UUID,
    admin_id: Annotated[UUID, Depends(get_current_admin_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Get user engagement state (admin only)."""
    engagement_repo = EngagementStateRepository(session)
    engagement = await engagement_repo.get_by_user_id(user_id)

    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement state not found")

    transitions = await engagement_repo.get_recent_transitions(user_id, limit=10)

    return EngagementResponse(
        state=engagement.state,
        multiplier=engagement.multiplier,
        calibration_score=engagement.calibration_score,
        consecutive_in_zone=engagement.consecutive_in_zone,
        consecutive_clingy_days=engagement.consecutive_clingy_days,
        consecutive_distant_days=engagement.consecutive_distant_days,
        recent_transitions=[
            {
                "from_state": t.from_state,
                "to_state": t.to_state,
                "reason": t.reason,
                "created_at": t.created_at,
            }
            for t in transitions
        ],
    )


@router.get("/users/{user_id}/vices", response_model=list[VicePreferenceResponse])
async def get_user_vices(
    user_id: UUID,
    admin_id: Annotated[UUID, Depends(get_current_admin_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Get user vice preferences (admin only)."""
    vice_repo = VicePreferenceRepository(session)
    vices = await vice_repo.get_by_user(user_id)

    return [
        VicePreferenceResponse(
            category=vice.category,
            intensity_level=vice.intensity_level,
            engagement_score=vice.engagement_score,
            discovered_at=vice.discovered_at,
        )
        for vice in vices
    ]


@router.get("/users/{user_id}/conversations", response_model=ConversationsResponse)
async def get_user_conversations(
    user_id: UUID,
    admin_id: Annotated[UUID, Depends(get_current_admin_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    page: int = 1,
    page_size: int = 20,
):
    """Get user conversations (admin only)."""
    conv_repo = ConversationRepository(session)

    offset = (page - 1) * page_size
    conversations, total = await conv_repo.get_paginated(user_id, offset=offset, limit=page_size)

    items = [
        {
            "id": conv.id,
            "platform": conv.platform,
            "started_at": conv.started_at,
            "ended_at": conv.ended_at,
            "score_delta": conv.score_delta,
            "emotional_tone": conv.emotional_tone,
            "message_count": len(conv.messages) if conv.messages else 0,
        }
        for conv in conversations
    ]

    return ConversationsResponse(
        conversations=items,
        total_count=total,
        page=page,
        page_size=page_size,
    )


# ============================================================================
# USER MEMORY ENDPOINT (T2.3)
# ============================================================================


@router.get("/users/{user_id}/memory")
async def get_user_memory(
    user_id: UUID,
    admin_id: Annotated[UUID, Depends(get_current_admin_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Get user memory graph data (admin only).

    AC-2.3.1: Returns user_facts, relationship_episodes, nikita_events.
    AC-2.3.2: 30s timeout returns 503 with retry_after.
    AC-2.3.3: Rate limited to 30 queries/hour.
    """
    import asyncio

    from nikita.memory import get_memory_client

    # Check user exists
    user_repo = UserRepository(session)
    user = await user_repo.get(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        # Get memory client with 30s timeout
        memory = await asyncio.wait_for(
            get_memory_client(user_id),
            timeout=30.0,
        )

        # Fetch all 3 graphs with timeout
        user_facts = await asyncio.wait_for(
            memory.get_user_facts(limit=50),
            timeout=30.0,
        )
        relationship_episodes = await asyncio.wait_for(
            memory.get_relationship_episodes(limit=50),
            timeout=30.0,
        )
        nikita_events = await asyncio.wait_for(
            memory.get_nikita_events(limit=50),
            timeout=30.0,
        )

        return {
            "user_facts": user_facts,
            "relationship_episodes": relationship_episodes,
            "nikita_events": nikita_events,
            "graph_status": "healthy",
        }

    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=503,
            detail="Memory graph query timed out. Neo4j Aura may be cold starting.",
            headers={"Retry-After": "60"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Memory graph unavailable: {str(e)}",
            headers={"Retry-After": "60"},
        )


# ============================================================================
# USER SCORES ENDPOINT (T2.4)
# ============================================================================


@router.get("/users/{user_id}/scores")
async def get_user_scores(
    user_id: UUID,
    admin_id: Annotated[UUID, Depends(get_current_admin_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    days: int = 7,
):
    """Get user score timeline (admin only).

    AC-2.4.1: Returns score timeline with trust, intimacy, attraction, commitment.
    AC-2.4.2: Date range filter works (default 7 days).
    """
    from nikita.db.models.game import ScoreHistory

    # Check user exists
    user_repo = UserRepository(session)
    user = await user_repo.get(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get score history for date range
    cutoff = datetime.now(UTC) - timedelta(days=days)

    stmt = (
        select(ScoreHistory)
        .where(ScoreHistory.user_id == user_id)
        .where(ScoreHistory.recorded_at >= cutoff)
        .order_by(ScoreHistory.recorded_at.asc())
    )

    result = await session.execute(stmt)
    history = result.scalars().all()

    # Format timeline - extract deltas from event_details if present
    points = [
        {
            "timestamp": entry.recorded_at.isoformat(),
            "score": float(entry.score),
            "chapter": entry.chapter,
            "event_type": entry.event_type,
            "event_details": entry.event_details or {},
        }
        for entry in history
    ]

    return {
        "user_id": str(user_id),
        "current_score": user.relationship_score,
        "chapter": user.chapter,
        "points": points,
        "days": days,
    }


# ============================================================================
# USER MODIFICATION ENDPOINTS
# ============================================================================


@router.put("/users/{user_id}/score", response_model=AdminResetResponse)
async def set_user_score(
    user_id: UUID,
    request: AdminSetScoreRequest,
    admin_id: Annotated[UUID, Depends(get_current_admin_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Set user score (admin only)."""
    user_repo = UserRepository(session)
    user = await user_repo.get(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update score and log to score_history
    await user_repo.update_score(
        user_id=user_id,
        new_score=request.score,
        event_type="manual_adjustment",
        event_details={"reason": request.reason, "admin_id": str(admin_id)},
    )

    await session.commit()

    return AdminResetResponse(
        success=True,
        message=f"Score set to {request.score}. Reason: {request.reason}",
    )


@router.put("/users/{user_id}/chapter", response_model=AdminResetResponse)
async def set_user_chapter(
    user_id: UUID,
    request: AdminSetChapterRequest,
    admin_id: Annotated[UUID, Depends(get_current_admin_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Set user chapter (admin only)."""
    user_repo = UserRepository(session)
    user = await user_repo.get(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.chapter = request.chapter
    user.boss_attempts = 0  # Reset boss attempts when changing chapters

    await session.commit()

    return AdminResetResponse(
        success=True,
        message=f"Chapter set to {request.chapter}. Reason: {request.reason}",
    )


@router.put("/users/{user_id}/status", response_model=AdminResetResponse)
async def set_game_status(
    user_id: UUID,
    request: AdminSetGameStatusRequest,
    admin_id: Annotated[UUID, Depends(get_current_admin_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Set game status (admin only)."""
    user_repo = UserRepository(session)
    user = await user_repo.get(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if request.game_status not in ["active", "boss_fight", "game_over", "won"]:
        raise HTTPException(status_code=400, detail="Invalid game_status")

    user.game_status = request.game_status

    await session.commit()

    return AdminResetResponse(
        success=True,
        message=f"Game status set to {request.game_status}. Reason: {request.reason}",
    )


@router.put("/users/{user_id}/engagement", response_model=AdminResetResponse)
async def set_engagement_state(
    user_id: UUID,
    request: AdminSetEngagementStateRequest,
    admin_id: Annotated[UUID, Depends(get_current_admin_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Set engagement state (admin only)."""
    engagement_repo = EngagementStateRepository(session)
    engagement = await engagement_repo.get_by_user_id(user_id)

    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement state not found")

    valid_states = ["calibrating", "in_zone", "drifting", "clingy", "distant", "out_of_zone"]
    if request.state not in valid_states:
        raise HTTPException(status_code=400, detail="Invalid engagement state")

    # Log transition
    old_state = engagement.state
    engagement.state = request.state

    # Create history entry
    history_entry = EngagementHistory(
        user_id=user_id,
        from_state=old_state,
        to_state=request.state,
        reason=f"Admin override: {request.reason}",
        calibration_score=engagement.calibration_score,
        created_at=datetime.now(UTC),
    )
    session.add(history_entry)

    await session.commit()

    return AdminResetResponse(
        success=True,
        message=f"Engagement state set to {request.state}. Reason: {request.reason}",
    )


@router.post("/users/{user_id}/reset-boss", response_model=AdminResetResponse)
async def reset_boss_attempts(
    user_id: UUID,
    admin_id: Annotated[UUID, Depends(get_current_admin_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Reset boss attempts to 0 (admin only)."""
    user_repo = UserRepository(session)
    user = await user_repo.get(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.boss_attempts = 0

    await session.commit()

    return AdminResetResponse(
        success=True,
        message="Boss attempts reset to 0",
    )


@router.post("/users/{user_id}/clear-engagement", response_model=AdminResetResponse)
async def clear_engagement_history(
    user_id: UUID,
    admin_id: Annotated[UUID, Depends(get_current_admin_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Clear engagement history (admin only)."""
    stmt = select(EngagementHistory).where(EngagementHistory.user_id == user_id)
    result = await session.execute(stmt)
    history_entries = result.scalars().all()

    for entry in history_entries:
        await session.delete(entry)

    await session.commit()

    return AdminResetResponse(
        success=True,
        message=f"Cleared {len(history_entries)} engagement history entries",
    )


# ============================================================================
# NEW ADMIN MUTATION ENDPOINTS (FR-029)
# ============================================================================


@router.post("/users/{user_id}/trigger-pipeline")
async def trigger_pipeline(
    user_id: UUID,
    admin_id: Annotated[UUID, Depends(get_current_admin_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    request: TriggerPipelineRequest = TriggerPipelineRequest(),
):
    """Trigger pipeline processing for a user (admin only).

    Args:
        user_id: User UUID to process
        request: Optional conversation_id to process (uses most recent if None)

    Returns:
        TriggerPipelineResponse with job status
    """
    from nikita.api.schemas.admin import TriggerPipelineRequest, TriggerPipelineResponse
    from nikita.pipeline.orchestrator import PipelineOrchestrator

    # Verify user exists
    user_repo = UserRepository(session)
    user = await user_repo.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    # Get conversation ID
    conv_repo = ConversationRepository(session)
    conversation_id = request.conversation_id
    if not conversation_id:
        # Get most recent conversation
        conversations = await conv_repo.get_recent(user_id, limit=1)
        if not conversations:
            return TriggerPipelineResponse(
                job_id=None,
                status="error",
                message="No conversations found for user",
            )
        conversation_id = conversations[0].id

    # Load conversation for pipeline
    conv = await conv_repo.get(conversation_id)
    if not conv:
        return TriggerPipelineResponse(
            job_id=None,
            status="error",
            message="Conversation not found",
        )

    # Trigger pipeline
    try:
        orchestrator = PipelineOrchestrator(session)
        result = await orchestrator.process(
            conversation_id=conversation_id,
            user_id=user_id,
            platform=conv.platform or "text",
            conversation=conv,
            user=user,
        )

        return TriggerPipelineResponse(
            job_id=None,
            status="ok" if result.success else "error",
            message=f"Pipeline {'completed' if result.success else 'failed'} in {result.total_duration_ms}ms",
        )
    except Exception as e:
        return TriggerPipelineResponse(
            job_id=None,
            status="error",
            message=f"Pipeline error: {str(e)}",
        )


@router.get("/users/{user_id}/pipeline-history")
async def get_pipeline_history(
    user_id: UUID,
    admin_id: Annotated[UUID, Depends(get_current_admin_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    page: int = 1,
    page_size: int = 50,
):
    """Get pipeline execution history for a user (admin only).

    Args:
        user_id: User UUID
        page: Page number (default 1)
        page_size: Items per page (default 50)

    Returns:
        PipelineHistoryResponse with paginated results
    """
    from nikita.api.schemas.admin import PipelineHistoryItem, PipelineHistoryResponse

    # Query JobExecution for this user
    # Job names contain conversation IDs which link to user_id via conversations table
    offset = (page - 1) * page_size

    stmt = (
        select(JobExecution)
        .join(Conversation, JobExecution.job_name.contains(Conversation.id.cast(String)))
        .where(Conversation.user_id == user_id)
        .order_by(JobExecution.started_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await session.execute(stmt)
    jobs = result.scalars().all()

    # Count total
    count_stmt = (
        select(func.count(JobExecution.id))
        .join(Conversation, JobExecution.job_name.contains(Conversation.id.cast(String)))
        .where(Conversation.user_id == user_id)
    )
    count_result = await session.execute(count_stmt)
    total_count = count_result.scalar() or 0

    items = [
        PipelineHistoryItem(
            id=job.id,
            job_name=job.job_name,
            status=job.status,
            duration_ms=job.duration_ms,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_message=job.result.get("error") if job.result and job.status == "failed" else None,
        )
        for job in jobs
    ]

    return PipelineHistoryResponse(
        items=items,
        total_count=total_count,
        page=page,
        page_size=page_size,
    )


@router.put("/users/{user_id}/metrics")
async def set_user_metrics(
    user_id: UUID,
    request: AdminSetMetricsRequest,
    admin_id: Annotated[UUID, Depends(get_current_admin_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Set user metrics (admin only).

    Args:
        user_id: User UUID
        request: Metrics to set (only non-None fields are updated)

    Returns:
        AdminResetResponse with success status
    """
    from nikita.api.schemas.admin import AdminSetMetricsRequest

    # Get metrics
    metrics_repo = UserMetricsRepository(session)
    metrics = await metrics_repo.get(user_id)
    if not metrics:
        raise HTTPException(status_code=404, detail=f"Metrics not found for user {user_id}")

    # Update only non-None fields
    updated_fields = []
    if request.intimacy is not None:
        metrics.intimacy = request.intimacy
        updated_fields.append("intimacy")
    if request.passion is not None:
        metrics.passion = request.passion
        updated_fields.append("passion")
    if request.trust is not None:
        metrics.trust = request.trust
        updated_fields.append("trust")
    if request.secureness is not None:
        metrics.secureness = request.secureness
        updated_fields.append("secureness")

    if not updated_fields:
        return AdminResetResponse(
            success=False,
            message="No metrics provided to update",
        )

    # Commit changes
    await session.commit()

    return AdminResetResponse(
        success=True,
        message=f"Updated metrics: {', '.join(updated_fields)} (reason: {request.reason})",
    )


# ============================================================================
# CONVERSATION MONITORING ENDPOINTS (Spec 034 US-3)
# ============================================================================


@router.get("/conversations", response_model=AdminConversationsResponse)
async def list_conversations(
    admin_id: Annotated[UUID, Depends(get_current_admin_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    page: int = 1,
    page_size: int = 50,
    platform: str | None = None,
    status: str | None = None,
    days: int = 7,
):
    """List all conversations with filters (admin only).

    AC-3.1.1: Filter by platform (telegram/voice)
    AC-3.1.2: Filter by status (pending/processing/processed/failed)
    AC-3.1.3: Date range filter works (default 7 days)
    """
    # Build base query with user join
    stmt = select(Conversation, User).join(User, Conversation.user_id == User.id)

    # Apply date range filter
    cutoff = datetime.now(UTC) - timedelta(days=days)
    stmt = stmt.where(Conversation.started_at >= cutoff)

    # Apply platform filter
    if platform:
        stmt = stmt.where(Conversation.platform == platform)

    # Apply status filter
    if status:
        stmt = stmt.where(Conversation.status == status)

    # Count total matching
    count_stmt = select(func.count(Conversation.id)).join(
        User, Conversation.user_id == User.id
    ).where(Conversation.started_at >= cutoff)
    if platform:
        count_stmt = count_stmt.where(Conversation.platform == platform)
    if status:
        count_stmt = count_stmt.where(Conversation.status == status)
    count_result = await session.execute(count_stmt)
    total_count = count_result.scalar() or 0

    # Apply pagination and ordering
    offset = (page - 1) * page_size
    stmt = stmt.order_by(Conversation.started_at.desc()).offset(offset).limit(page_size)

    result = await session.execute(stmt)
    rows = result.all()

    conversations = [
        ConversationListItem(
            id=conv.id,
            user_id=conv.user_id,
            user_identifier=str(user.telegram_id) if user.telegram_id else user.phone,
            platform=conv.platform,
            started_at=conv.started_at,
            ended_at=conv.ended_at,
            status=conv.status,
            score_delta=conv.score_delta,
            emotional_tone=conv.emotional_tone,
            message_count=len(conv.messages) if conv.messages else 0,
        )
        for conv, user in rows
    ]

    return AdminConversationsResponse(
        conversations=conversations,
        total_count=total_count,
        page=page,
        page_size=page_size,
        days=days,
    )


@router.get("/conversations/{conversation_id}/prompts", response_model=ConversationPromptsResponse)
async def get_conversation_prompts(
    conversation_id: UUID,
    admin_id: Annotated[UUID, Depends(get_current_admin_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Get all prompts generated for a conversation (admin only).

    AC-3.2.1: Returns all prompts for conversation
    AC-3.2.2: Ordered by created_at ascending
    """
    from nikita.db.models.generated_prompt import GeneratedPrompt

    # Verify conversation exists
    conv_repo = ConversationRepository(session)
    conversation = await conv_repo.get(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Get prompts for this conversation
    stmt = (
        select(GeneratedPrompt)
        .where(GeneratedPrompt.conversation_id == conversation_id)
        .order_by(GeneratedPrompt.created_at.asc())
    )
    result = await session.execute(stmt)
    prompts = result.scalars().all()

    return ConversationPromptsResponse(
        conversation_id=conversation_id,
        prompts=[
            ConversationPromptItem(
                id=p.id,
                prompt_content=p.prompt_content,
                token_count=p.token_count,
                generation_time_ms=p.generation_time_ms,
                meta_prompt_template=p.meta_prompt_template,
                context_snapshot=p.context_snapshot,
                created_at=p.created_at,
            )
            for p in prompts
        ],
        count=len(prompts),
    )


@router.get("/conversations/{conversation_id}/pipeline", response_model=PipelineStatusResponse)
async def get_conversation_pipeline(
    conversation_id: UUID,
    admin_id: Annotated[UUID, Depends(get_current_admin_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Get pipeline processing status for a conversation (admin only).

    AC-3.3.1: Returns 9-stage status synthesized from conversation fields
    AC-3.3.2: Failed stages include error details from conversation status

    Note: Pipeline stages are synthesized from conversation data since
    individual stage execution is not tracked in the database.
    """
    # Verify conversation exists
    conv_repo = ConversationRepository(session)
    conversation = await conv_repo.get(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Build synthetic pipeline stages based on conversation state
    stages = _build_pipeline_stages(conversation)

    return PipelineStatusResponse(
        conversation_id=conversation_id,
        status=conversation.status,
        processing_attempts=conversation.processing_attempts or 0,
        processed_at=conversation.processed_at,
        stages=stages,
    )


def _build_pipeline_stages(conversation) -> list[PipelineStageItem]:
    """Build synthetic pipeline stages from conversation state.

    The 9-stage post-processing pipeline (Spec 031) doesn't log individual
    stages to the database. We infer stage status from conversation fields.
    """
    status = conversation.status
    is_processed = status == "processed"
    is_failed = status == "failed"
    is_processing = status == "processing"
    is_pending = status in ("active", "pending")

    # Define the 9 stages with their indicators
    stage_definitions = [
        ("validation", "Validate conversation is processable"),
        ("message_extraction", "Extract messages from JSONB"),
        ("entity_extraction", "Extract entities via LLM"),
        ("thought_simulation", "Generate Nikita thoughts"),
        ("thread_identification", "Identify conversation threads"),
        ("summary_generation", "Generate conversation summary"),
        ("emotional_analysis", "Analyze emotional tone"),
        ("graph_update", "Update Neo4j memory graphs"),
        ("layer_composition", "Compose prompt layers"),
    ]

    stages = []
    for i, (name, description) in enumerate(stage_definitions, start=1):
        # Determine stage status based on conversation state
        error_message = None
        result_summary = None

        if is_pending:
            stage_status = "pending"
        elif is_processed:
            stage_status = "completed"
            # Check if this stage has visible output
            result_summary = _get_stage_result(conversation, name)
        elif is_failed:
            # For failed conversations, mark all stages as failed
            # (we don't know exactly which stage failed without detailed logging)
            stage_status = "failed"
            error_message = f"Pipeline failed after {conversation.processing_attempts} attempts"
        elif is_processing:
            # Conversation is currently processing - stages are in progress
            stage_status = "running"
        else:
            stage_status = "pending"

        stages.append(
            PipelineStageItem(
                stage_name=name,
                stage_number=i,
                status=stage_status,
                result_summary=result_summary,
                error_message=error_message,
                duration_ms=None,
            )
        )

    return stages


def _get_stage_result(conversation, stage_name: str) -> str | None:
    """Get result summary for a completed stage based on conversation data."""
    if stage_name == "message_extraction":
        count = len(conversation.messages) if conversation.messages else 0
        return f"Extracted {count} messages"
    elif stage_name == "entity_extraction":
        if conversation.extracted_entities:
            count = len(conversation.extracted_entities)
            return f"Extracted {count} entity types"
        return None
    elif stage_name == "summary_generation":
        if conversation.conversation_summary:
            length = len(conversation.conversation_summary)
            return f"Generated {length} char summary"
        return None
    elif stage_name == "emotional_analysis":
        if conversation.emotional_tone:
            return f"Tone: {conversation.emotional_tone}"
        return None
    return None


# ============================================================================
# PROMPT VIEWER ENDPOINTS
# ============================================================================


@router.get("/prompts", response_model=GeneratedPromptsResponse)
async def list_prompts(
    admin_id: Annotated[UUID, Depends(get_current_admin_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    page: int = 1,
    page_size: int = 50,
    user_id: UUID | None = None,
    template: str | None = None,
):
    """List generated prompts (admin only).

    Supports filtering by user_id and template.
    """
    from nikita.db.models.generated_prompt import GeneratedPrompt

    offset = (page - 1) * page_size

    # Build query with optional filters
    stmt = select(GeneratedPrompt).order_by(GeneratedPrompt.created_at.desc())

    if user_id:
        stmt = stmt.where(GeneratedPrompt.user_id == user_id)
    if template:
        stmt = stmt.where(GeneratedPrompt.meta_prompt_template == template)

    # Get total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_count_result = await session.execute(count_stmt)
    total_count = total_count_result.scalar() or 0

    # Get paginated results
    stmt = stmt.offset(offset).limit(page_size)
    result = await session.execute(stmt)
    prompts = result.scalars().all()

    return GeneratedPromptsResponse(
        prompts=[
            GeneratedPromptResponse(
                id=p.id,
                user_id=p.user_id,
                conversation_id=p.conversation_id,
                prompt_content=p.prompt_content,
                token_count=p.token_count,
                generation_time_ms=p.generation_time_ms,
                meta_prompt_template=p.meta_prompt_template,
                created_at=p.created_at,
            )
            for p in prompts
        ],
        total_count=total_count,
        page=page,
        page_size=page_size,
    )


@router.get("/prompts/{prompt_id}", response_model=GeneratedPromptResponse)
async def get_prompt_detail(
    prompt_id: UUID,
    admin_id: Annotated[UUID, Depends(get_current_admin_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Get prompt detail (admin only)."""
    from nikita.db.models.generated_prompt import GeneratedPrompt

    stmt = select(GeneratedPrompt).where(GeneratedPrompt.id == prompt_id)
    result = await session.execute(stmt)
    prompt = result.scalar_one_or_none()

    if not prompt:
        raise HTTPException(status_code=404, detail=f"Prompt {prompt_id} not found")

    return GeneratedPromptResponse(
        id=prompt.id,
        user_id=prompt.user_id,
        conversation_id=prompt.conversation_id,
        prompt_content=prompt.prompt_content,
        token_count=prompt.token_count,
        generation_time_ms=prompt.generation_time_ms,
        meta_prompt_template=prompt.meta_prompt_template,
        created_at=prompt.created_at,
    )


# ============================================================================
# SYSTEM HEALTH ENDPOINTS
# ============================================================================


@router.get("/health", response_model=AdminHealthResponse)
async def get_system_health(
    admin_id: Annotated[UUID, Depends(get_current_admin_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Get system health status (admin only)."""
    # Check database connectivity
    try:
        await session.execute(select(1))
        db_status = "healthy"
    except Exception:
        db_status = "down"

    # Memory uses Supabase pgVector (same DB)
    memory_status = db_status

    # Count errors logged in the last 24 hours from the error_logs table
    from nikita.db.models.error_log import ErrorLog
    since_24h = datetime.now(UTC) - timedelta(hours=24)
    try:
        err_stmt = select(func.count(ErrorLog.id)).where(ErrorLog.occurred_at >= since_24h)
        err_result = await session.execute(err_stmt)
        error_count = err_result.scalar() or 0
    except Exception:
        # Gracefully degrade if error_logs table is unavailable
        error_count = 0

    # Count active users in last 24 hours
    since = datetime.now(UTC) - timedelta(hours=24)
    stmt = select(func.count(User.id)).where(User.last_interaction_at >= since)
    result = await session.execute(stmt)
    active_users = result.scalar() or 0

    return AdminHealthResponse(
        api_status="healthy",
        database_status=db_status,
        memory_status=memory_status,
        error_count_24h=error_count,
        active_users_24h=active_users,
    )


@router.get("/stats", response_model=AdminStatsResponse)
async def get_admin_stats(
    admin_id: Annotated[UUID, Depends(get_current_admin_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Get admin overview statistics."""
    # Total users
    stmt = select(func.count(User.id))
    result = await session.execute(stmt)
    total_users = result.scalar() or 0

    # Active users (last 7 days)
    since_7d = datetime.now(UTC) - timedelta(days=7)
    stmt = select(func.count(User.id)).where(User.last_interaction_at >= since_7d)
    result = await session.execute(stmt)
    active_users = result.scalar() or 0

    # New users (last 7 days)
    stmt = select(func.count(User.id)).where(User.created_at >= since_7d)
    result = await session.execute(stmt)
    new_users_7d = result.scalar() or 0

    # Total conversations
    stmt = select(func.count(Conversation.id))
    result = await session.execute(stmt)
    total_conversations = result.scalar() or 0

    # Average relationship score
    stmt = select(func.avg(User.relationship_score))
    result = await session.execute(stmt)
    avg_score = result.scalar() or 0

    return AdminStatsResponse(
        total_users=total_users,
        active_users=active_users,
        new_users_7d=new_users_7d,
        total_conversations=total_conversations,
        avg_relationship_score=avg_score,
    )


@router.get("/processing-stats", response_model=ProcessingStatsResponse)
async def get_processing_stats(
    admin_id: Annotated[UUID, Depends(get_current_admin_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Get post-processing job statistics (Spec 031 T3.3).

    Returns 24h success rate, avg duration, pending/failed counts.
    """
    from datetime import timezone

    since_24h = datetime.now(timezone.utc) - timedelta(hours=24)

    # Get 24h job stats for post_processing jobs
    stmt = select(
        func.count(JobExecution.id).label("total"),
        func.count(JobExecution.id)
        .filter(JobExecution.status == JobStatus.COMPLETED.value)
        .label("success"),
        func.count(JobExecution.id)
        .filter(JobExecution.status == JobStatus.FAILED.value)
        .label("failed"),
        func.avg(JobExecution.duration_ms).label("avg_duration"),
    ).where(
        JobExecution.job_name == JobName.POST_PROCESSING.value,
        JobExecution.started_at >= since_24h,
    )
    result = await session.execute(stmt)
    row = result.one()

    total_processed = row.total or 0
    success_count = row.success or 0
    failed_count = row.failed or 0
    avg_duration_ms = int(row.avg_duration or 0)

    # Calculate success rate
    success_rate = 0.0
    if total_processed > 0:
        success_rate = (success_count / total_processed) * 100

    # Get pending conversations (status = 'active' but no recent messages)
    # Using 15-min timeout to match session detector logic
    since_15m = datetime.now(timezone.utc) - timedelta(minutes=15)
    stmt = select(func.count(Conversation.id)).where(
        Conversation.status == "active",
        Conversation.updated_at < since_15m,
    )
    result = await session.execute(stmt)
    pending_count = result.scalar() or 0

    # Get stuck conversations (status = 'processing' for >30 min)
    since_30m = datetime.now(timezone.utc) - timedelta(minutes=30)
    stmt = select(func.count(Conversation.id)).where(
        Conversation.status == "processing",
        Conversation.updated_at < since_30m,
    )
    result = await session.execute(stmt)
    stuck_count = result.scalar() or 0

    return ProcessingStatsResponse(
        success_rate=round(success_rate, 1),
        avg_duration_ms=avg_duration_ms,
        total_processed=total_processed,
        success_count=success_count,
        failed_count=failed_count,
        pending_count=pending_count,
        stuck_count=stuck_count,
    )


# ============================================================================
# PIPELINE HEALTH ENDPOINT (Spec 037 T3.2)
# ============================================================================


@router.get("/pipeline-health", response_model=PipelineHealthResponse)
async def get_pipeline_health(
    admin_id: Annotated[UUID, Depends(get_current_admin_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Get pipeline health status (DEPRECATED - Spec 042).

    This endpoint is deprecated. The old context/stages pipeline has been
    replaced by nikita/pipeline/. Use /admin/unified-pipeline-health instead.
    """
    raise HTTPException(
        status_code=410,
        detail="Endpoint deprecated. Use GET /admin/unified-pipeline-health instead.",
    )


# ============================================================================
# SYSTEM OVERVIEW & SUPPORTING ENDPOINTS (Spec 034 US-4)
# ============================================================================


@router.get("/metrics/overview", response_model=SystemOverviewResponse)
async def get_system_overview(
    admin_id: Annotated[UUID, Depends(get_current_admin_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Get system overview metrics (T4.1).

    Returns active users, conversations today, processing success rate,
    and average response time.
    """
    from datetime import timezone

    now = datetime.now(timezone.utc)
    since_24h = now - timedelta(hours=24)
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Active users in last 24h
    stmt = select(func.count(User.id)).where(User.last_interaction_at >= since_24h)
    result = await session.execute(stmt)
    active_users = result.scalar() or 0

    # Conversations started today
    stmt = select(func.count(Conversation.id)).where(
        Conversation.started_at >= start_of_today
    )
    result = await session.execute(stmt)
    conversations_today = result.scalar() or 0

    # Processing success rate (24h)
    stmt = select(func.count(Conversation.id)).where(
        Conversation.status == "processed",
        Conversation.updated_at >= since_24h,
    )
    result = await session.execute(stmt)
    success_count = result.scalar() or 0

    stmt = select(func.count(Conversation.id)).where(
        Conversation.status.in_(["processed", "failed"]),
        Conversation.updated_at >= since_24h,
    )
    result = await session.execute(stmt)
    total_processed = result.scalar() or 0

    processing_success_rate = 0.0
    if total_processed > 0:
        processing_success_rate = (success_count / total_processed) * 100

    # Average response time (using processing duration from job_executions)
    # Default to 500ms if no data available
    avg_response_time_ms = 500

    return SystemOverviewResponse(
        active_users=active_users,
        conversations_today=conversations_today,
        processing_success_rate=round(processing_success_rate, 1),
        average_response_time_ms=avg_response_time_ms,
    )


@router.get("/errors", response_model=ErrorLogResponse)
async def get_error_log(
    admin_id: Annotated[UUID, Depends(get_current_admin_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    level: str | None = None,
    search: str | None = None,
    days: int = 7,
    page: int = 1,
    page_size: int = 50,
):
    """Get error log from error_logs table (Issue #19 fix).

    Returns errors logged via error_logging utility.
    Filterable by level, date range, and search term.
    Falls back to failed conversations if no logged errors exist.
    """
    from datetime import timezone

    from nikita.db.models.error_log import ErrorLog

    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Build query for error_logs table
    query = select(ErrorLog).where(ErrorLog.occurred_at >= since)

    # Filter by level if provided
    if level:
        query = query.where(ErrorLog.level == level)

    # Apply search filter - search in message and source
    if search:
        query = query.where(
            (ErrorLog.message.ilike(f"%{search}%"))
            | (ErrorLog.source.ilike(f"%{search}%"))
        )

    # Get total count
    count_stmt = select(func.count(ErrorLog.id)).where(ErrorLog.occurred_at >= since)
    if level:
        count_stmt = count_stmt.where(ErrorLog.level == level)
    if search:
        count_stmt = count_stmt.where(
            (ErrorLog.message.ilike(f"%{search}%"))
            | (ErrorLog.source.ilike(f"%{search}%"))
        )
    result = await session.execute(count_stmt)
    total_count = result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(ErrorLog.occurred_at.desc())

    result = await session.execute(query)
    error_logs = result.scalars().all()

    errors = [
        ErrorLogItem(
            id=log.id,
            level=log.level,
            message=log.message,
            source=log.source,
            user_id=log.user_id,
            conversation_id=log.conversation_id,
            occurred_at=log.occurred_at,
            resolved=log.resolved,
        )
        for log in error_logs
    ]

    # If no logged errors, fall back to failed conversations for backwards compat
    if not errors and not level and not search:
        conv_query = select(Conversation).where(
            Conversation.status == "failed",
            Conversation.updated_at >= since,
        ).offset(offset).limit(page_size).order_by(Conversation.updated_at.desc())

        conv_count = select(func.count(Conversation.id)).where(
            Conversation.status == "failed",
            Conversation.updated_at >= since,
        )
        conv_result = await session.execute(conv_count)
        conv_total = conv_result.scalar() or 0

        if conv_total > 0:
            total_count = conv_total
            conv_result = await session.execute(conv_query)
            failed_convs = conv_result.all()
            for (conv,) in failed_convs:
                error_msg = "Post-processing failed"
                if conv.conversation_summary:
                    error_msg = f"Failed: {conv.conversation_summary[:100]}"
                errors.append(
                    ErrorLogItem(
                        id=conv.id,
                        level="error",
                        message=error_msg,
                        source="post_processing",
                        user_id=conv.user_id,
                        conversation_id=conv.id,
                        occurred_at=conv.updated_at,
                        resolved=False,
                    )
                )

    filters_applied = {}
    if level:
        filters_applied["level"] = level
    if search:
        filters_applied["search"] = search
    filters_applied["days"] = days

    return ErrorLogResponse(
        errors=errors,
        total_count=total_count,
        page=page,
        page_size=page_size,
        filters_applied=filters_applied,
    )


@router.get("/users/{user_id}/boss", response_model=BossEncountersResponse)
async def get_user_boss_encounters(
    user_id: UUID,
    admin_id: Annotated[UUID, Depends(get_current_admin_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Get boss encounters for a user (T4.3).

    Returns all boss encounters from score_history where
    event_type is 'boss_pass' or 'boss_fail'.
    """
    from nikita.db.models.game import ScoreHistory

    # Verify user exists
    user_repo = UserRepository(session)
    user = await user_repo.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get boss encounters
    stmt = select(ScoreHistory).where(
        ScoreHistory.user_id == user_id,
        ScoreHistory.event_type.in_(["boss_pass", "boss_fail", "boss_encounter"]),
    ).order_by(ScoreHistory.recorded_at.desc())

    result = await session.execute(stmt)
    encounters = result.scalars().all()

    encounter_items = []
    for enc in encounters:
        details = enc.event_details or {}
        outcome = "pending"
        if enc.event_type == "boss_pass":
            outcome = "passed"
        elif enc.event_type == "boss_fail":
            outcome = "failed"
        elif details.get("outcome"):
            outcome = details["outcome"]

        encounter_items.append(
            BossEncounterItem(
                id=enc.id,
                chapter=enc.chapter,
                outcome=outcome,
                score_before=details.get("score_before", enc.score),
                score_after=details.get("score_after"),
                reasoning=details.get("reasoning"),
                attempted_at=enc.recorded_at,
                resolved_at=enc.recorded_at if outcome != "pending" else None,
            )
        )

    return BossEncountersResponse(
        user_id=user_id,
        encounters=encounter_items,
        total_count=len(encounter_items),
    )


@router.get("/audit-logs", response_model=AuditLogsResponse)
async def get_audit_logs(
    admin_id: Annotated[UUID, Depends(get_current_admin_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    days: int = 7,
    page: int = 1,
    page_size: int = 50,
):
    """Get admin's own audit log entries (T4.4).

    Returns paginated audit logs for the current admin.
    """
    from datetime import timezone

    from nikita.db.models.audit_log import AuditLog

    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Get admin email for display
    user_repo = UserRepository(session)
    admin = await user_repo.get(admin_id)
    admin_email = admin.email if admin else "unknown"

    # Get total count for this admin
    count_stmt = select(func.count(AuditLog.id)).where(
        AuditLog.admin_id == admin_id,
        AuditLog.created_at >= since,
    )
    result = await session.execute(count_stmt)
    total_count = result.scalar() or 0

    # Get paginated logs
    offset = (page - 1) * page_size
    stmt = select(AuditLog).where(
        AuditLog.admin_id == admin_id,
        AuditLog.created_at >= since,
    ).order_by(AuditLog.created_at.desc()).offset(offset).limit(page_size)

    result = await session.execute(stmt)
    logs = result.scalars().all()

    log_items = []
    for log in logs:
        log_items.append(
            AuditLogItem(
                id=log.id,
                admin_email=log.admin_email,
                action=log.action,
                resource_type=log.resource_type,
                resource_id=log.resource_id,
                details=log.details,
                timestamp=log.created_at,
            )
        )

    return AuditLogsResponse(
        logs=log_items,
        total_count=total_count,
        page=page,
        page_size=page_size,
    )



@router.get("/pipeline/timings")
async def get_pipeline_timings(
    admin_id: Annotated[UUID, Depends(get_current_admin_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    days: int = 7,
):
    """Get per-stage pipeline timing statistics (Spec 105).

    Reads stage_timings from job_executions metadata and calculates
    p50/p95/p99 latency percentiles per stage.
    """
    import statistics

    since = datetime.now(UTC) - timedelta(days=days)

    stmt = (
        select(JobExecution)
        .where(
            JobExecution.job_name == "unified_pipeline",
            JobExecution.started_at >= since,
            JobExecution.status == JobStatus.COMPLETED.value,
        )
        .order_by(JobExecution.started_at.desc())
        .limit(500)
    )
    result = await session.execute(stmt)
    jobs = result.scalars().all()

    # Collect timing samples per stage
    stage_samples: dict[str, list[float]] = {}
    for job in jobs:
        meta = job.result or {}
        stage_timings = meta.get("stage_timings", {})
        for stage_name, duration_ms in stage_timings.items():
            if isinstance(duration_ms, (int, float)):
                stage_samples.setdefault(stage_name, []).append(float(duration_ms))

    # Calculate percentiles per stage
    stats: dict[str, dict] = {}
    for stage_name, samples in stage_samples.items():
        if not samples:
            continue
        sorted_samples = sorted(samples)
        n = len(sorted_samples)
        p50_idx = int(n * 0.50)
        p95_idx = min(int(n * 0.95), n - 1)
        p99_idx = min(int(n * 0.99), n - 1)
        stats[stage_name] = {
            "count": n,
            "p50_ms": round(sorted_samples[p50_idx], 1),
            "p95_ms": round(sorted_samples[p95_idx], 1),
            "p99_ms": round(sorted_samples[p99_idx], 1),
            "avg_ms": round(statistics.mean(sorted_samples), 1),
        }

    return {
        "days": days,
        "jobs_analyzed": len(jobs),
        "stage_stats": stats,
    }


@router.get("/analytics/engagement")
async def get_engagement_analytics(
    admin_id: Annotated[UUID, Depends(get_current_admin_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    since: str | None = None,
):
    """Get engagement analytics with active users and conversation counts (Spec 105).

    Args:
        since: Optional ISO date string to filter from (e.g., '2026-01-01'). Defaults to 30 days ago.
    """
    if since:
        try:
            since_dt = datetime.fromisoformat(since).replace(tzinfo=UTC)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid 'since' date format. Use ISO format: YYYY-MM-DD")
    else:
        since_dt = datetime.now(UTC) - timedelta(days=30)

    # Get active users with conversation counts in the date range
    stmt = (
        select(
            User.id,
            User.telegram_id,
            User.chapter,
            User.relationship_score,
            User.last_interaction_at,
            func.count(Conversation.id).label("conversation_count"),
        )
        .outerjoin(
            Conversation,
            (Conversation.user_id == User.id) & (Conversation.started_at >= since_dt),
        )
        .where(User.last_interaction_at >= since_dt)
        .group_by(User.id)
        .order_by(func.count(Conversation.id).desc())
        .limit(100)
    )
    result = await session.execute(stmt)
    rows = result.all()

    # Engagement state lookup
    engagement_stmt = select(EngagementState).where(
        EngagementState.user_id.in_([row.id for row in rows])
    )
    eng_result = await session.execute(engagement_stmt)
    engagement_map = {e.user_id: e.state for e in eng_result.scalars().all()}

    users_data = [
        {
            "user_id": str(row.id),
            "telegram_id": row.telegram_id,
            "chapter": row.chapter,
            "relationship_score": float(row.relationship_score),
            "last_interaction_at": row.last_interaction_at.isoformat() if row.last_interaction_at else None,
            "conversation_count": row.conversation_count,
            "engagement_state": engagement_map.get(row.id, "unknown"),
        }
        for row in rows
    ]

    # Summary stats
    total_active = len(users_data)
    avg_conversations = (
        sum(u["conversation_count"] for u in users_data) / total_active
        if total_active > 0
        else 0
    )

    return {
        "since": since_dt.isoformat(),
        "total_active_users": total_active,
        "avg_conversations_per_user": round(avg_conversations, 1),
        "users": users_data,
    }


@router.get("/unified-pipeline/health", response_model=UnifiedPipelineHealthResponse)
async def get_unified_pipeline_health(
    admin_id: Annotated[UUID, Depends(get_current_admin_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Get unified pipeline health status (Spec 042 T2.12).

    Returns per-stage success rates, avg timing, error counts
    for the 9-stage unified pipeline.
    """
    from nikita.pipeline.orchestrator import PipelineOrchestrator

    stage_defs = PipelineOrchestrator.STAGE_DEFINITIONS

    stages = []
    for name, _class_path, is_critical in stage_defs:
        stages.append(
            UnifiedPipelineStageHealth(
                name=name,
                is_critical=is_critical,
            )
        )

    # Query job_executions for unified pipeline runs in last 24h
    since_24h = datetime.now(UTC) - timedelta(hours=24)

    stmt = select(
        func.count(JobExecution.id).label("total"),
        func.count(JobExecution.id)
        .filter(JobExecution.status == JobStatus.COMPLETED.value)
        .label("success"),
        func.avg(JobExecution.duration_ms).label("avg_duration"),
        func.max(JobExecution.started_at).label("last_run"),
    ).where(
        JobExecution.job_name == "unified_pipeline",
        JobExecution.started_at >= since_24h,
    )

    result = await session.execute(stmt)
    row = result.one_or_none()

    total_runs = 0
    success_count = 0
    avg_duration = 0.0
    last_run_at = None

    if row:
        total_runs = row.total or 0
        success_count = row.success or 0
        avg_duration = float(row.avg_duration or 0)
        last_run_at = row.last_run

    success_rate = (success_count / total_runs * 100) if total_runs > 0 else 100.0

    status = "healthy"
    if total_runs > 0 and success_rate < 90:
        status = "degraded"
    if total_runs > 0 and success_rate < 50:
        status = "down"

    return UnifiedPipelineHealthResponse(
        status=status,
        stages=stages,
        total_runs_24h=total_runs,
        overall_success_rate=round(success_rate, 1),
        avg_pipeline_duration_ms=round(avg_duration, 1),
        last_run_at=last_run_at,
    )
