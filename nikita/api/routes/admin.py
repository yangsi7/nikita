"""Admin API routes for system management and debugging."""

from datetime import datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.api.schemas.admin import (
    AdminHealthResponse,
    AdminResetResponse,
    AdminSetChapterRequest,
    AdminSetEngagementStateRequest,
    AdminSetGameStatusRequest,
    AdminSetScoreRequest,
    AdminStatsResponse,
    AdminUserDetailResponse,
    AdminUserListItem,
    GeneratedPromptResponse,
    GeneratedPromptsResponse,
)
from nikita.api.schemas.portal import (
    ConversationsResponse,
    EngagementResponse,
    UserMetricsResponse,
    VicePreferenceResponse,
)
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


# Dependency for admin check
async def get_current_admin_user_id(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> UUID:
    """Check if current user is admin.

    TODO: Implement actual Supabase JWT validation + is_admin() check.
    For now, this is a placeholder.
    """
    raise HTTPException(status_code=403, detail="Admin access required")


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

    return [
        AdminUserListItem(
            id=user.id,
            telegram_id=user.telegram_id,
            email=None,  # TODO: Fetch from auth.users
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
        created_at=datetime.utcnow(),
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
    # TODO: Implement once generated_prompts model is created
    # For now, return empty list
    return GeneratedPromptsResponse(
        prompts=[],
        total_count=0,
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
    # TODO: Implement once generated_prompts model is created
    raise HTTPException(status_code=501, detail="Prompt viewer not implemented yet")


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

    # TODO: Check Neo4j connectivity
    neo4j_status = "unknown"

    # TODO: Count errors in last 24 hours (requires error logging table)
    error_count = 0

    # Count active users in last 24 hours
    since = datetime.utcnow() - timedelta(hours=24)
    stmt = select(func.count(User.id)).where(User.last_interaction_at >= since)
    result = await session.execute(stmt)
    active_users = result.scalar() or 0

    return AdminHealthResponse(
        api_status="healthy",
        database_status=db_status,
        neo4j_status=neo4j_status,
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
    since_7d = datetime.utcnow() - timedelta(days=7)
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
