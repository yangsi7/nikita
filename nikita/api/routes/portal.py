"""Portal API routes for user dashboard."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from math import ceil
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.api.dependencies.auth import get_current_user_id
from nikita.api.schemas.portal import (
    ConversationDetailResponse,
    ConversationListItem,
    ConversationMessage,
    ConversationsResponse,
    DailySummaryResponse,
    DecayStatusResponse,
    DetailedScoreHistoryResponse,
    DetailedScorePoint,
    EmotionalImpactSchema,
    EmotionalStateHistoryResponse,
    EmotionalStatePointSchema,
    EmotionalStateResponse,
    EngagementResponse,
    EngagementTransition,
    LifeEventItemSchema,
    LifeEventsResponse,
    LinkCodeResponse,
    NarrativeArcItemSchema,
    NarrativeArcsResponse,
    PsycheTipsResponse,
    ScoreHistoryPoint,
    ScoreHistoryResponse,
    SocialCircleMemberSchema,
    SocialCircleResponse,
    SuccessResponse,
    ThreadListResponse,
    ThreadResponse,
    ThoughtItemSchema,
    ThoughtsResponse,
    UpdateSettingsRequest,
    UserMetricsResponse,
    UserSettingsResponse,
    UserStatsResponse,
    VicePreferenceResponse,
)
from nikita.db.database import get_async_session
from nikita.db.repositories.conversation_repository import ConversationRepository
from nikita.db.repositories.engagement_repository import EngagementStateRepository
from nikita.db.repositories.metrics_repository import UserMetricsRepository
from nikita.db.repositories.narrative_arc_repository import NarrativeArcRepository
from nikita.db.repositories.score_history_repository import ScoreHistoryRepository
from nikita.db.repositories.social_circle_repository import SocialCircleRepository
from nikita.db.repositories.summary_repository import DailySummaryRepository
from nikita.db.repositories.telegram_link_repository import TelegramLinkRepository
from nikita.db.repositories.thought_repository import NikitaThoughtRepository
from nikita.db.repositories.thread_repository import ConversationThreadRepository
from nikita.db.repositories.user_repository import UserRepository
from nikita.db.repositories.vice_repository import VicePreferenceRepository
from nikita.emotional_state.models import EmotionalStateModel
from nikita.emotional_state.store import get_state_store
from nikita.engine.constants import BOSS_THRESHOLDS, CHAPTER_NAMES, DECAY_RATES
from nikita.life_simulation.store import get_event_store

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
    boss_threshold = BOSS_THRESHOLDS.get(user.chapter, Decimal("60"))
    progress_to_boss = min(Decimal(str(user.relationship_score)) / boss_threshold * 100, Decimal("100"))

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

    # Return default state for new users without engagement record
    if not engagement:
        return EngagementResponse(
            state="calibrating",
            multiplier=1.0,
            calibration_score=0.5,
            consecutive_in_zone=0,
            consecutive_clingy_days=0,
            consecutive_distant_days=0,
            recent_transitions=[],
        )

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
    days: int = Query(default=30, ge=1, le=365),
):
    """Get score history for charts."""
    score_repo = ScoreHistoryRepository(session)

    # Get history for the last N days
    since = datetime.now(UTC) - timedelta(days=days)
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
    limit: int = Query(default=30, ge=1, le=100),
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
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
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
        hours_since = (datetime.now(UTC) - user.last_interaction_at).total_seconds() / 3600
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


# Valid IANA timezones (subset of common ones)
VALID_TIMEZONES = {
    "UTC",
    "America/New_York",
    "America/Chicago",
    "America/Denver",
    "America/Los_Angeles",
    "America/Anchorage",
    "America/Honolulu",
    "America/Toronto",
    "America/Vancouver",
    "America/Mexico_City",
    "America/Sao_Paulo",
    "America/Buenos_Aires",
    "Europe/London",
    "Europe/Paris",
    "Europe/Berlin",
    "Europe/Rome",
    "Europe/Madrid",
    "Europe/Amsterdam",
    "Europe/Brussels",
    "Europe/Vienna",
    "Europe/Zurich",
    "Europe/Stockholm",
    "Europe/Oslo",
    "Europe/Copenhagen",
    "Europe/Helsinki",
    "Europe/Warsaw",
    "Europe/Prague",
    "Europe/Budapest",
    "Europe/Athens",
    "Europe/Moscow",
    "Asia/Tokyo",
    "Asia/Seoul",
    "Asia/Shanghai",
    "Asia/Hong_Kong",
    "Asia/Singapore",
    "Asia/Bangkok",
    "Asia/Jakarta",
    "Asia/Mumbai",
    "Asia/Dubai",
    "Asia/Jerusalem",
    "Australia/Sydney",
    "Australia/Melbourne",
    "Australia/Brisbane",
    "Australia/Perth",
    "Pacific/Auckland",
    "Pacific/Fiji",
    "Africa/Cairo",
    "Africa/Johannesburg",
    "Africa/Lagos",
}


@router.get("/settings", response_model=UserSettingsResponse)
async def get_user_settings(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Get current user settings.

    Returns timezone, notification preferences, and email.
    For portal-first users, creates default settings.
    """
    user_repo = UserRepository(session)
    user = await user_repo.get(user_id)

    # Portal-first flow: create user with defaults if doesn't exist
    if not user:
        user = await user_repo.create_with_metrics(user_id=user_id)
        await session.commit()
        await session.refresh(user)

    return UserSettingsResponse(
        timezone=user.timezone,
        notifications_enabled=user.notifications_enabled,
        email=None,  # Email comes from JWT, not stored in users table
    )


@router.put("/settings", response_model=UserSettingsResponse)
async def update_user_settings(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    request: UpdateSettingsRequest,
):
    """Update user settings.

    Allows updating timezone and notification preferences.
    """
    user_repo = UserRepository(session)

    # Validate timezone if provided
    if request.timezone is not None and request.timezone not in VALID_TIMEZONES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid timezone: {request.timezone}. Must be a valid IANA timezone.",
        )

    user = await user_repo.get(user_id)

    # Portal-first flow: create user with defaults if doesn't exist
    if not user:
        user = await user_repo.create_with_metrics(user_id=user_id)
        await session.commit()

    # Update settings
    user = await user_repo.update_settings(
        user_id=user_id,
        timezone=request.timezone,
        notifications_enabled=request.notifications_enabled,
    )
    await session.commit()

    return UserSettingsResponse(
        timezone=user.timezone,
        notifications_enabled=user.notifications_enabled,
        email=None,
    )


@router.delete("/account", response_model=SuccessResponse)
async def delete_account(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    confirm: bool = False,
):
    """Delete user account and all associated data.

    Requires confirm=true query parameter to prevent accidental deletion.
    This permanently deletes:
    - User profile and metrics
    - All conversations and messages
    - Score history and daily summaries
    - Vice preferences
    - Engagement state and history
    - Generated prompts
    - All other user data

    This action cannot be undone.
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Account deletion requires confirm=true",
        )

    user_repo = UserRepository(session)
    deleted = await user_repo.delete_user_cascade(user_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")

    await session.commit()

    return SuccessResponse(
        success=True,
        message="Account and all associated data deleted successfully",
    )


@router.post("/link-telegram", response_model=LinkCodeResponse)
async def generate_link_code(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Generate a code to link Telegram account.

    Creates a 6-character code that the user can send to the Telegram
    bot via /link CODE command. The code expires after 10 minutes.

    Returns the code, expiry timestamp, and instructions for linking.
    """
    link_repo = TelegramLinkRepository(session)
    link_code = await link_repo.create_link_code(user_id)
    await session.commit()

    return LinkCodeResponse(
        code=link_code.code,
        expires_at=link_code.expires_at,
        instructions=(
            f"Send this command to @Nikita_my_bot on Telegram:\n"
            f"/link {link_code.code}\n\n"
            f"This code expires in 10 minutes."
        ),
    )


# Note: get_state_store() and get_event_store() are singletons that manage
# their own sessions internally (session_factory pattern). Unlike repository
# classes that accept AsyncSession via DI, these stores create sessions
# on-demand. This is by design — see nikita/emotional_state/store.py and
# nikita/life_simulation/store.py.
@router.get("/emotional-state", response_model=EmotionalStateResponse)
async def get_emotional_state(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
):
    """Get Nikita's current 4D emotional state."""
    store = get_state_store()
    state = await store.get_current_state(user_id)

    if not state:
        # Return defaults for new users (all 0.5, no conflict)
        state = EmotionalStateModel(user_id=user_id)

    return EmotionalStateResponse(
        state_id=str(state.state_id),
        arousal=state.arousal,
        valence=state.valence,
        dominance=state.dominance,
        intimacy=state.intimacy,
        conflict_state=state.conflict_state.value,
        conflict_started_at=state.conflict_started_at,
        conflict_trigger=state.conflict_trigger,
        description=state.to_description(),
        last_updated=state.last_updated,
    )


@router.get("/emotional-state/history", response_model=EmotionalStateHistoryResponse)
async def get_emotional_state_history(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    hours: int = Query(default=24, ge=1, le=720),
):
    """Get emotional state history over time."""
    store = get_state_store()
    days = ceil(hours / 24)
    states = await store.get_state_history(user_id, days=days, limit=100)

    # Post-filter to requested hours window
    cutoff = datetime.now(UTC) - timedelta(hours=hours)
    filtered = [s for s in states if s.last_updated >= cutoff]

    points = [
        EmotionalStatePointSchema(
            arousal=s.arousal,
            valence=s.valence,
            dominance=s.dominance,
            intimacy=s.intimacy,
            conflict_state=s.conflict_state.value,
            recorded_at=s.last_updated,
        )
        for s in filtered
    ]

    return EmotionalStateHistoryResponse(
        points=points,
        total_count=len(points),
    )


@router.get("/life-events", response_model=LifeEventsResponse)
async def get_life_events(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    date_str: str | None = None,
):
    """Get Nikita's life events for a specific date."""
    from datetime import date as date_type

    if date_str:
        try:
            target_date = date_type.fromisoformat(date_str)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid date format. Use YYYY-MM-DD.")
    else:
        target_date = date_type.today()

    store = get_event_store()
    events = await store.get_events_for_date(user_id, target_date)

    items = [
        LifeEventItemSchema(
            event_id=str(event.event_id),
            time_of_day=event.time_of_day.value if hasattr(event.time_of_day, 'value') else str(event.time_of_day),
            domain=event.domain.value if hasattr(event.domain, 'value') else str(event.domain),
            event_type=event.event_type.value if hasattr(event.event_type, 'value') else str(event.event_type),
            description=event.description,
            entities=event.entities,
            importance=event.importance,
            emotional_impact=EmotionalImpactSchema(
                arousal_delta=event.emotional_impact.arousal_delta,
                valence_delta=event.emotional_impact.valence_delta,
                dominance_delta=event.emotional_impact.dominance_delta,
                intimacy_delta=event.emotional_impact.intimacy_delta,
            ) if event.emotional_impact else None,
            narrative_arc_id=str(event.narrative_arc_id) if event.narrative_arc_id else None,
        )
        for event in events
    ]

    return LifeEventsResponse(
        events=items,
        date=str(target_date),
        total_count=len(items),
    )


@router.get("/thoughts", response_model=ThoughtsResponse)
async def get_thoughts(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    type: str = "all",
):
    """Get Nikita's inner thoughts with pagination."""
    thought_repo = NikitaThoughtRepository(session)
    thought_type = type if type != "all" else None
    thoughts, total_count = await thought_repo.get_paginated(
        user_id, limit=limit, offset=offset, thought_type=thought_type,
    )

    now = datetime.now(UTC)
    items = [
        ThoughtItemSchema(
            id=t.id,
            thought_type=t.thought_type,
            content=t.content,
            source_conversation_id=t.source_conversation_id,
            expires_at=t.expires_at,
            used_at=t.used_at,
            is_expired=t.expires_at is not None and t.expires_at < now,
            psychological_context=t.psychological_context,
            created_at=t.created_at,
        )
        for t in thoughts
    ]

    return ThoughtsResponse(
        thoughts=items,
        total_count=total_count,
        has_more=total_count > offset + limit,
    )


@router.get("/narrative-arcs", response_model=NarrativeArcsResponse)
async def get_narrative_arcs(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    active_only: bool = True,
):
    """Get Nikita's narrative arcs (storylines)."""
    arc_repo = NarrativeArcRepository(session)

    if active_only:
        active_arcs = await arc_repo.get_active_arcs(user_id)
        resolved_arcs = []
    else:
        all_arcs = await arc_repo.get_all_arcs(user_id)
        active_arcs = [a for a in all_arcs if a.is_active]
        resolved_arcs = [a for a in all_arcs if not a.is_active]

    def arc_to_schema(arc):
        return NarrativeArcItemSchema.model_validate(arc)

    return NarrativeArcsResponse(
        active_arcs=[arc_to_schema(a) for a in active_arcs],
        resolved_arcs=[arc_to_schema(a) for a in resolved_arcs],
        total_count=len(active_arcs) + len(resolved_arcs),
    )


@router.get("/social-circle", response_model=SocialCircleResponse)
async def get_social_circle(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Get Nikita's social circle (friends)."""
    circle_repo = SocialCircleRepository(session)
    friends = await circle_repo.get_circle(user_id)

    return SocialCircleResponse(
        friends=[SocialCircleMemberSchema.model_validate(f) for f in friends],
        total_count=len(friends),
    )


@router.get("/score-history/detailed", response_model=DetailedScoreHistoryResponse)
async def get_detailed_score_history(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    days: int = Query(default=30, ge=1, le=365),
):
    """Get detailed score history with per-metric deltas."""
    score_repo = ScoreHistoryRepository(session)
    since = datetime.now(UTC) - timedelta(days=days)
    history = await score_repo.get_history_since(user_id, since)

    points = []
    for entry in history:
        details = entry.event_details or {}
        points.append(DetailedScorePoint(
            id=entry.id,
            score=float(entry.score),
            chapter=entry.chapter,
            event_type=entry.event_type,
            recorded_at=entry.recorded_at,
            intimacy_delta=details.get("intimacy_delta"),
            passion_delta=details.get("passion_delta"),
            trust_delta=details.get("trust_delta"),
            secureness_delta=details.get("secureness_delta"),
            score_delta=details.get("composite_delta"),
            conversation_id=details.get("conversation_id"),
        ))

    return DetailedScoreHistoryResponse(
        points=points,
        total_count=len(points),
    )


@router.get("/threads", response_model=ThreadListResponse)
async def get_threads(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    status: str = "open",
    type: str = "all",
    limit: int = Query(default=50, ge=1, le=200),
):
    """Get conversation threads with filtering."""
    thread_repo = ConversationThreadRepository(session)

    thread_status = status if status != "all" else None
    thread_type = type if type != "all" else None

    threads, total_count = await thread_repo.get_threads_filtered(
        user_id, status=thread_status, thread_type=thread_type, limit=limit,
    )

    # Always compute open_count regardless of current filter
    open_threads = await thread_repo.get_open_threads(user_id, limit=1000)
    open_count = len(open_threads)

    return ThreadListResponse(
        threads=[ThreadResponse.model_validate(t) for t in threads],
        total_count=total_count,
        open_count=open_count,
    )


@router.get("/psyche-tips", response_model=PsycheTipsResponse)
async def get_psyche_tips(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Get Nikita's psyche insights for player tips (Spec 059).

    Returns actionable tips derived from the psyche agent's analysis.
    Falls back to safe defaults if no psyche state exists yet.
    """
    from nikita.agents.psyche.models import PsycheState
    from nikita.db.repositories.psyche_state_repository import PsycheStateRepository

    repo = PsycheStateRepository(session)
    record = await repo.get_current(user_id)

    if record and record.state:
        try:
            state = PsycheState.model_validate(record.state)
            generated_at = record.generated_at
        except Exception:
            state = PsycheState.default()
            generated_at = None
    else:
        state = PsycheState.default()
        generated_at = None

    # Split behavioral_guidance into bullet tips (sentence-split)
    tips = [
        tip.strip()
        for tip in state.behavioral_guidance.replace(". ", ".\n").split("\n")
        if tip.strip()
    ]

    return PsycheTipsResponse(
        attachment_style=state.attachment_activation,
        defense_mode=state.defense_mode,
        emotional_tone=state.emotional_tone,
        vulnerability_level=state.vulnerability_level,
        behavioral_tips=tips,
        topics_to_encourage=state.topics_to_encourage,
        topics_to_avoid=state.topics_to_avoid,
        internal_monologue=state.internal_monologue,
        generated_at=generated_at,
    )


@router.get("/export/{export_type}")
async def export_data(
    export_type: str,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    format: str = Query(default="csv", pattern="^(csv|json)$"),
    days: int = Query(default=90, ge=1, le=365),
):
    """Export user data as CSV or JSON.

    Supported export types: score-history, conversations, metrics, vices.
    """
    import csv
    import io
    import json

    from fastapi.responses import StreamingResponse

    if export_type == "score-history":
        score_repo = ScoreHistoryRepository(session)
        since = datetime.now(UTC) - timedelta(days=days)
        history = await score_repo.get_history_since(user_id, since)
        rows = [
            {
                "recorded_at": entry.recorded_at.isoformat(),
                "score": float(entry.score),
                "chapter": entry.chapter,
                "event_type": entry.event_type or "",
            }
            for entry in history
        ]
        filename = f"nikita-score-history-{days}d"

    elif export_type == "conversations":
        conv_repo = ConversationRepository(session)
        conversations, _ = await conv_repo.get_paginated(user_id, offset=0, limit=500)
        rows = [
            {
                "id": str(conv.id),
                "platform": conv.platform,
                "started_at": conv.started_at.isoformat() if conv.started_at else "",
                "ended_at": conv.ended_at.isoformat() if conv.ended_at else "",
                "score_delta": conv.score_delta,
                "emotional_tone": conv.emotional_tone or "",
                "message_count": len(conv.messages) if conv.messages else 0,
            }
            for conv in conversations
        ]
        filename = f"nikita-conversations-{days}d"

    elif export_type == "vices":
        vice_repo = VicePreferenceRepository(session)
        vices = await vice_repo.get_active(user_id)
        rows = [
            {
                "category": vice.category,
                "intensity_level": vice.intensity_level,
                "engagement_score": float(vice.engagement_score),
                "discovered_at": vice.discovered_at.isoformat(),
            }
            for vice in vices
        ]
        filename = "nikita-vices"

    else:
        raise HTTPException(status_code=400, detail=f"Unknown export type: {export_type}")

    if format == "json":
        content = json.dumps(rows, indent=2)
        return StreamingResponse(
            io.BytesIO(content.encode()),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}.json"'},
        )

    # CSV format
    if not rows:
        return StreamingResponse(
            io.BytesIO(b""),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}.csv"'},
        )

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}.csv"'},
    )
