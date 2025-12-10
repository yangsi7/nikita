"""Portal API routes for user dashboard."""

from datetime import datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.api.dependencies.auth import get_current_user_id
from nikita.api.schemas.portal import (
    ConversationDetailResponse,
    ConversationListItem,
    ConversationMessage,
    ConversationsResponse,
    DailySummaryResponse,
    DecayStatusResponse,
    EngagementResponse,
    EngagementTransition,
    ScoreHistoryPoint,
    ScoreHistoryResponse,
    UserMetricsResponse,
    UserStatsResponse,
    VicePreferenceResponse,
)
from nikita.db.database import get_async_session
from nikita.db.repositories.conversation_repository import ConversationRepository
from nikita.db.repositories.engagement_repository import EngagementStateRepository
from nikita.db.repositories.metrics_repository import UserMetricsRepository
from nikita.db.repositories.score_history_repository import ScoreHistoryRepository
from nikita.db.repositories.summary_repository import DailySummaryRepository
from nikita.db.repositories.user_repository import UserRepository
from nikita.db.repositories.vice_repository import VicePreferenceRepository
from nikita.engine.constants import BOSS_THRESHOLDS, CHAPTER_NAMES, DECAY_RATES

router = APIRouter()


@router.get("/stats", response_model=UserStatsResponse)
async def get_user_stats(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Get full dashboard statistics for current user.

    For portal-first users (who registered via magic link but never used Telegram),
    creates a new user with default game state (score=50, chapter=1, all metrics=50).
    """
    user_repo = UserRepository(session)
    user = await user_repo.get(user_id)

    # Portal-first flow: create user with defaults if doesn't exist
    if not user:
        user = await user_repo.create_with_metrics(user_id=user_id)
        await session.commit()
        await session.refresh(user)

    # Get metrics (should exist after create_with_metrics)
    metrics_repo = UserMetricsRepository(session)
    metrics = await metrics_repo.get_by_user_id(user_id)

    # Calculate boss progress
    boss_threshold = BOSS_THRESHOLDS.get(user.chapter, 60.0)
    progress_to_boss = min(float(user.relationship_score) / boss_threshold * 100, 100)

    return UserStatsResponse(
        id=user.id,
        relationship_score=user.relationship_score,
        chapter=user.chapter,
        chapter_name=CHAPTER_NAMES.get(user.chapter, f"Chapter {user.chapter}"),
        boss_threshold=boss_threshold,
        progress_to_boss=progress_to_boss,
        days_played=user.days_played,
        game_status=user.game_status,
        last_interaction_at=user.last_interaction_at,
        boss_attempts=user.boss_attempts,
        metrics=UserMetricsResponse(
            intimacy=metrics.intimacy,
            passion=metrics.passion,
            trust=metrics.trust,
            secureness=metrics.secureness,
        ) if metrics else None,
    )


@router.get("/metrics", response_model=UserMetricsResponse)
async def get_user_metrics(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Get 4 hidden metrics with weights."""
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


@router.get("/engagement", response_model=EngagementResponse)
async def get_engagement_state(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Get engagement state and recent transitions."""
    engagement_repo = EngagementStateRepository(session)
    engagement = await engagement_repo.get_by_user_id(user_id)

    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement state not found")

    # Get recent transitions
    transitions = await engagement_repo.get_recent_transitions(user_id, limit=10)

    return EngagementResponse(
        state=engagement.state,
        multiplier=engagement.multiplier,
        calibration_score=engagement.calibration_score,
        consecutive_in_zone=engagement.consecutive_in_zone,
        consecutive_clingy_days=engagement.consecutive_clingy_days,
        consecutive_distant_days=engagement.consecutive_distant_days,
        recent_transitions=[
            EngagementTransition(
                from_state=t.from_state,
                to_state=t.to_state,
                reason=t.reason,
                created_at=t.created_at,
            )
            for t in transitions
        ],
    )


@router.get("/vices", response_model=list[VicePreferenceResponse])
async def get_vice_preferences(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Get discovered vice preferences."""
    vice_repo = VicePreferenceRepository(session)
    vices = await vice_repo.get_active(user_id)

    return [
        VicePreferenceResponse(
            category=vice.category,
            intensity_level=vice.intensity_level,
            engagement_score=vice.engagement_score,
            discovered_at=vice.discovered_at,
        )
        for vice in vices
    ]


@router.get("/score-history", response_model=ScoreHistoryResponse)
async def get_score_history(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    days: int = 30,
):
    """Get score history for charts."""
    score_repo = ScoreHistoryRepository(session)

    # Get history for the last N days
    since = datetime.utcnow() - timedelta(days=days)
    history = await score_repo.get_history_since(user_id, since)

    points = [
        ScoreHistoryPoint(
            score=entry.score,
            chapter=entry.chapter,
            event_type=entry.event_type,
            recorded_at=entry.recorded_at,
        )
        for entry in history
    ]

    return ScoreHistoryResponse(
        points=points,
        total_count=len(points),
    )


@router.get("/daily-summaries", response_model=list[DailySummaryResponse])
async def get_daily_summaries(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    limit: int = 30,
):
    """Get daily summaries list."""
    summary_repo = DailySummaryRepository(session)
    summaries = await summary_repo.get_recent(user_id, limit=limit)

    return [
        DailySummaryResponse(
            id=summary.id,
            date=summary.date,
            score_start=summary.score_start,
            score_end=summary.score_end,
            decay_applied=summary.decay_applied,
            conversations_count=summary.conversations_count,
            summary_text=summary.summary_text,
            emotional_tone=summary.emotional_tone,
        )
        for summary in summaries
    ]


@router.get("/conversations", response_model=ConversationsResponse)
async def get_conversations(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    page: int = 1,
    page_size: int = 20,
):
    """Get paginated conversation list."""
    conv_repo = ConversationRepository(session)

    offset = (page - 1) * page_size
    conversations, total = await conv_repo.get_paginated(user_id, offset=offset, limit=page_size)

    items = [
        ConversationListItem(
            id=conv.id,
            platform=conv.platform,
            started_at=conv.started_at,
            ended_at=conv.ended_at,
            score_delta=conv.score_delta,
            emotional_tone=conv.emotional_tone,
            message_count=len(conv.messages) if conv.messages else 0,
        )
        for conv in conversations
    ]

    return ConversationsResponse(
        conversations=items,
        total_count=total,
        page=page,
        page_size=page_size,
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation_detail(
    conversation_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Get full conversation detail (read-only)."""
    conv_repo = ConversationRepository(session)
    conversation = await conv_repo.get(conversation_id)

    if not conversation or conversation.user_id != user_id:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = [
        ConversationMessage(
            role=msg.get("role", "unknown"),
            content=msg.get("content", ""),
            timestamp=msg.get("timestamp"),
        )
        for msg in (conversation.messages or [])
    ]

    return ConversationDetailResponse(
        id=conversation.id,
        platform=conversation.platform,
        messages=messages,
        started_at=conversation.started_at,
        ended_at=conversation.ended_at,
        score_delta=conversation.score_delta,
        is_boss_fight=conversation.is_boss_fight,
        emotional_tone=conversation.emotional_tone,
        extracted_entities=conversation.extracted_entities,
        conversation_summary=conversation.conversation_summary,
    )


@router.get("/decay", response_model=DecayStatusResponse)
async def get_decay_status(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Get decay warning and projection."""
    user_repo = UserRepository(session)
    user = await user_repo.get(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Calculate decay status
    grace_period_hours = 24  # From spec: 24 hour grace period

    if user.last_interaction_at:
        hours_since = (datetime.utcnow() - user.last_interaction_at).total_seconds() / 3600
        hours_remaining = max(grace_period_hours - hours_since, 0)
    else:
        hours_remaining = grace_period_hours

    decay_rate = DECAY_RATES.get(user.chapter, 0.5)
    is_decaying = hours_remaining == 0

    # Project score if no interaction
    hours_until_next_decay = max(hours_remaining, 0)
    projected_score = float(user.relationship_score)
    if is_decaying:
        projected_score = max(projected_score - float(decay_rate), 0)

    return DecayStatusResponse(
        grace_period_hours=grace_period_hours,
        hours_remaining=hours_remaining,
        decay_rate=decay_rate,
        current_score=user.relationship_score,
        projected_score=projected_score,
        is_decaying=is_decaying,
    )
