"""Portal API response schemas for user dashboard."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class UserStatsResponse(BaseModel):
    """Full dashboard statistics response."""

    id: UUID
    relationship_score: Decimal = Field(ge=0, le=100)
    chapter: int = Field(ge=1, le=5)
    chapter_name: str
    boss_threshold: Decimal
    progress_to_boss: Decimal = Field(ge=0, le=100)
    days_played: int = Field(ge=0)
    game_status: str
    last_interaction_at: datetime | None = None


class UserMetricsResponse(BaseModel):
    """Hidden metrics response with weights."""

    intimacy: Decimal = Field(ge=0, le=100)
    passion: Decimal = Field(ge=0, le=100)
    trust: Decimal = Field(ge=0, le=100)
    secureness: Decimal = Field(ge=0, le=100)
    weights: dict[str, Decimal] = Field(
        default={
            "intimacy": Decimal("0.30"),
            "passion": Decimal("0.25"),
            "trust": Decimal("0.25"),
            "secureness": Decimal("0.20"),
        }
    )


class EngagementTransition(BaseModel):
    """Engagement state transition record."""

    from_state: str | None
    to_state: str
    reason: str | None
    created_at: datetime


class EngagementResponse(BaseModel):
    """Engagement state and history response."""

    state: str
    multiplier: Decimal = Field(ge=0, le=1)
    calibration_score: Decimal = Field(ge=0, le=1)
    consecutive_in_zone: int = Field(ge=0)
    consecutive_clingy_days: int = Field(ge=0)
    consecutive_distant_days: int = Field(ge=0)
    recent_transitions: list[EngagementTransition] = Field(default_factory=list)


class VicePreferenceResponse(BaseModel):
    """Vice preference display response."""

    category: str
    intensity_level: int = Field(ge=1, le=5)
    engagement_score: Decimal = Field(ge=0, le=100)
    discovered_at: datetime


class DecayStatusResponse(BaseModel):
    """Decay warning and projection response."""

    grace_period_hours: int = Field(ge=0)
    hours_remaining: float = Field(ge=0)
    decay_rate: Decimal = Field(ge=0, le=10)
    current_score: Decimal = Field(ge=0, le=100)
    projected_score: Decimal = Field(ge=0, le=100)
    is_decaying: bool


class ScoreHistoryPoint(BaseModel):
    """Single score history point for charts."""

    score: Decimal = Field(ge=0, le=100)
    chapter: int = Field(ge=1, le=5)
    event_type: str | None
    recorded_at: datetime


class ScoreHistoryResponse(BaseModel):
    """Score history for charts."""

    points: list[ScoreHistoryPoint]
    total_count: int = Field(ge=0)


class DailySummaryResponse(BaseModel):
    """Daily summary from Nikita's perspective."""

    id: UUID
    date: datetime
    score_start: Decimal | None = Field(None, ge=0, le=100)
    score_end: Decimal | None = Field(None, ge=0, le=100)
    decay_applied: Decimal | None = None
    conversations_count: int = Field(ge=0)
    summary_text: str | None = None
    emotional_tone: str | None = None


class ConversationMessage(BaseModel):
    """Single message in conversation."""

    role: str
    content: str
    timestamp: datetime | None = None


class ConversationListItem(BaseModel):
    """Conversation list item for pagination."""

    id: UUID
    platform: str
    started_at: datetime
    ended_at: datetime | None
    score_delta: Decimal | None
    emotional_tone: str | None
    message_count: int = Field(ge=0)


class ConversationDetailResponse(BaseModel):
    """Full conversation detail (read-only)."""

    id: UUID
    platform: str
    messages: list[ConversationMessage]
    started_at: datetime
    ended_at: datetime | None
    score_delta: Decimal | None
    is_boss_fight: bool
    emotional_tone: str | None
    extracted_entities: dict | None = None
    conversation_summary: str | None = None


class ConversationsResponse(BaseModel):
    """Paginated conversation list."""

    conversations: list[ConversationListItem]
    total_count: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)


class UserSettingsResponse(BaseModel):
    """User settings response."""

    notifications_enabled: bool
    timezone: str
    email: str | None


class LinkCodeResponse(BaseModel):
    """Telegram linking code response."""

    code: str
    expires_at: datetime
    instructions: str


class SuccessResponse(BaseModel):
    """Generic success response."""

    success: bool
    message: str
