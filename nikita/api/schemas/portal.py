"""Portal API response schemas for user dashboard."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class UserMetricsResponse(BaseModel):
    """Hidden metrics response with weights."""

    intimacy: float = Field(ge=0, le=100)
    passion: float = Field(ge=0, le=100)
    trust: float = Field(ge=0, le=100)
    secureness: float = Field(ge=0, le=100)
    weights: dict[str, float] = Field(
        default={
            "intimacy": 0.30,
            "passion": 0.25,
            "trust": 0.25,
            "secureness": 0.20,
        }
    )


class UserStatsResponse(BaseModel):
    """Full dashboard statistics response."""

    id: UUID
    relationship_score: float = Field(ge=0, le=100)
    chapter: int = Field(ge=1, le=5)
    chapter_name: str
    boss_threshold: float
    progress_to_boss: float = Field(ge=0, le=100)
    days_played: int = Field(ge=0)
    game_status: str
    last_interaction_at: datetime | None = None
    boss_attempts: int = Field(ge=0, le=3, default=0)
    metrics: UserMetricsResponse | None = None


class EngagementTransition(BaseModel):
    """Engagement state transition record."""

    from_state: str | None
    to_state: str
    reason: str | None
    created_at: datetime


class EngagementResponse(BaseModel):
    """Engagement state and history response."""

    state: str
    multiplier: float = Field(ge=0, le=1)
    calibration_score: float = Field(ge=0, le=1)
    consecutive_in_zone: int = Field(ge=0)
    consecutive_clingy_days: int = Field(ge=0)
    consecutive_distant_days: int = Field(ge=0)
    recent_transitions: list[EngagementTransition] = Field(default_factory=list)


class VicePreferenceResponse(BaseModel):
    """Vice preference display response."""

    category: str
    intensity_level: int = Field(ge=1, le=5)
    engagement_score: float = Field(ge=0, le=100)
    discovered_at: datetime


class DecayStatusResponse(BaseModel):
    """Decay warning and projection response."""

    grace_period_hours: int = Field(ge=0)
    hours_remaining: float = Field(ge=0)
    decay_rate: float = Field(ge=0, le=10)
    current_score: float = Field(ge=0, le=100)
    projected_score: float = Field(ge=0, le=100)
    is_decaying: bool


class ScoreHistoryPoint(BaseModel):
    """Single score history point for charts."""

    score: float = Field(ge=0, le=100)
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
    score_start: float | None = Field(None, ge=0, le=100)
    score_end: float | None = Field(None, ge=0, le=100)
    decay_applied: float | None = None
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
    score_delta: float | None
    emotional_tone: str | None
    message_count: int = Field(ge=0)


class ConversationDetailResponse(BaseModel):
    """Full conversation detail (read-only)."""

    id: UUID
    platform: str
    messages: list[ConversationMessage]
    started_at: datetime
    ended_at: datetime | None
    score_delta: float | None
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


class UpdateSettingsRequest(BaseModel):
    """Update user settings request."""

    timezone: str | None = None
    notifications_enabled: bool | None = None


class LinkCodeResponse(BaseModel):
    """Telegram linking code response."""

    code: str
    expires_at: datetime
    instructions: str


class SuccessResponse(BaseModel):
    """Generic success response."""

    success: bool
    message: str


# Spec 046 — Emotional Intelligence Schemas


class EmotionalStateResponse(BaseModel):
    """Current emotional state response."""

    state_id: str
    arousal: float = Field(ge=0.0, le=1.0)
    valence: float = Field(ge=0.0, le=1.0)
    dominance: float = Field(ge=0.0, le=1.0)
    intimacy: float = Field(ge=0.0, le=1.0)
    conflict_state: Literal["none", "passive_aggressive", "cold", "vulnerable", "explosive"]
    conflict_started_at: datetime | None = None
    conflict_trigger: str | None = None
    description: str
    last_updated: datetime


class EmotionalStatePointSchema(BaseModel):
    """Single point in emotional state history."""

    arousal: float = Field(ge=0.0, le=1.0)
    valence: float = Field(ge=0.0, le=1.0)
    dominance: float = Field(ge=0.0, le=1.0)
    intimacy: float = Field(ge=0.0, le=1.0)
    conflict_state: str
    recorded_at: datetime


class EmotionalStateHistoryResponse(BaseModel):
    """Emotional state history over time."""

    points: list[EmotionalStatePointSchema]
    total_count: int = Field(ge=0)


class EmotionalImpactSchema(BaseModel):
    """Emotional impact of a life event."""

    arousal_delta: float = 0.0
    valence_delta: float = 0.0
    dominance_delta: float = 0.0
    intimacy_delta: float = 0.0


class LifeEventItemSchema(BaseModel):
    """Single life event item."""

    event_id: str
    time_of_day: str
    domain: str
    event_type: str
    description: str
    entities: list[str] = Field(default_factory=list)
    importance: float = Field(ge=0.0, le=1.0)
    emotional_impact: EmotionalImpactSchema | None = None
    narrative_arc_id: str | None = None


class LifeEventsResponse(BaseModel):
    """Life events for a specific date."""

    events: list[LifeEventItemSchema]
    date: str
    total_count: int = Field(ge=0)


class ThoughtItemSchema(BaseModel):
    """Single thought item."""

    id: UUID
    thought_type: str
    content: str
    source_conversation_id: UUID | None = None
    expires_at: datetime | None = None
    used_at: datetime | None = None
    is_expired: bool
    psychological_context: dict | None = None
    created_at: datetime


class ThoughtsResponse(BaseModel):
    """Nikita's thoughts collection."""

    thoughts: list[ThoughtItemSchema]
    total_count: int = Field(ge=0)
    has_more: bool


class NarrativeArcItemSchema(BaseModel):
    """Single narrative arc item."""

    id: UUID
    template_name: str
    category: str
    current_stage: Literal["setup", "rising", "climax", "falling", "resolved"]
    stage_progress: int = Field(ge=0)
    conversations_in_arc: int = Field(ge=0)
    max_conversations: int = Field(ge=1)
    current_description: str | None = None
    involved_characters: list[str] = Field(default_factory=list)
    emotional_impact: dict = Field(default_factory=dict)
    is_active: bool
    started_at: datetime
    resolved_at: datetime | None = None

    model_config = {"from_attributes": True}


class NarrativeArcsResponse(BaseModel):
    """Narrative arcs collection."""

    active_arcs: list[NarrativeArcItemSchema]
    resolved_arcs: list[NarrativeArcItemSchema] = Field(default_factory=list)
    total_count: int = Field(ge=0)


class SocialCircleMemberSchema(BaseModel):
    """Single social circle member."""

    id: UUID
    friend_name: str
    friend_role: str
    age: int | None = None
    occupation: str | None = None
    personality: str | None = None
    relationship_to_nikita: str | None = None
    storyline_potential: list[str] = Field(default_factory=list)
    is_active: bool

    model_config = {"from_attributes": True}


class SocialCircleResponse(BaseModel):
    """Social circle collection."""

    friends: list[SocialCircleMemberSchema]
    total_count: int = Field(ge=0)


# Spec 047 — Deep Insights Schemas


class DetailedScorePoint(BaseModel):
    """Detailed score history point with metric deltas."""

    id: UUID
    score: float = Field(ge=0, le=100)
    chapter: int = Field(ge=1, le=5)
    event_type: str | None = None
    recorded_at: datetime
    intimacy_delta: float | None = None
    passion_delta: float | None = None
    trust_delta: float | None = None
    secureness_delta: float | None = None
    score_delta: float | None = None
    conversation_id: UUID | None = None

    model_config = {"from_attributes": True}


class DetailedScoreHistoryResponse(BaseModel):
    """Detailed score history with metric breakdown."""

    points: list[DetailedScorePoint]
    total_count: int = Field(ge=0)


class ThreadResponse(BaseModel):
    """Single conversation thread."""

    id: UUID
    thread_type: str
    content: str
    status: str
    source_conversation_id: UUID | None = None
    created_at: datetime
    resolved_at: datetime | None = None

    model_config = {"from_attributes": True}


class ThreadListResponse(BaseModel):
    """Thread list with counts."""

    threads: list[ThreadResponse]
    total_count: int = Field(ge=0)
    open_count: int = Field(ge=0)


# Spec 059 — Nikita's Day (Psyche Tips)


class PsycheTipsResponse(BaseModel):
    """Psyche tips for portal Nikita's Day page."""

    attachment_style: str
    defense_mode: str
    emotional_tone: str
    vulnerability_level: float = Field(ge=0.0, le=1.0)
    behavioral_tips: list[str] = Field(default_factory=list)
    topics_to_encourage: list[str] = Field(default_factory=list)
    topics_to_avoid: list[str] = Field(default_factory=list)
    internal_monologue: str
    generated_at: datetime | None = None


# Spec 063 — Data Export

class ExportResponse(BaseModel):
    """Data export response metadata."""

    export_type: str
    format: str
    row_count: int
    generated_at: datetime
