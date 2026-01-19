"""Admin Debug Portal API response schemas.

Schemas for admin debug portal endpoints that provide:
- System overview stats
- Job execution status
- User debugging info
- State machine details
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# System Overview Schemas (T2.1)
# ============================================================================


class GameStatusDistribution(BaseModel):
    """User count by game status."""

    active: int = Field(ge=0)
    boss_fight: int = Field(ge=0)
    game_over: int = Field(ge=0)
    won: int = Field(ge=0)


class ChapterDistribution(BaseModel):
    """User count by chapter (1-5)."""

    chapter_1: int = Field(ge=0)
    chapter_2: int = Field(ge=0)
    chapter_3: int = Field(ge=0)
    chapter_4: int = Field(ge=0)
    chapter_5: int = Field(ge=0)


class EngagementDistribution(BaseModel):
    """User count by engagement state."""

    calibrating: int = Field(ge=0)
    in_zone: int = Field(ge=0)
    drifting: int = Field(ge=0)
    clingy: int = Field(ge=0)
    distant: int = Field(ge=0)
    out_of_zone: int = Field(ge=0)


class ActiveUserCounts(BaseModel):
    """Active user counts by time period."""

    last_24h: int = Field(ge=0)
    last_7d: int = Field(ge=0)
    last_30d: int = Field(ge=0)


class SystemOverviewResponse(BaseModel):
    """System overview stats response (AC-FR002-001 to AC-FR010-001)."""

    total_users: int = Field(ge=0)
    game_status: GameStatusDistribution
    chapters: ChapterDistribution
    engagement_states: EngagementDistribution
    active_users: ActiveUserCounts


# ============================================================================
# Job Monitoring Schemas (T2.2)
# ============================================================================


class JobExecutionStatus(BaseModel):
    """Single job execution status."""

    job_name: str
    last_run_at: datetime | None
    last_status: str | None  # running, completed, failed
    last_duration_ms: int | None = Field(None, ge=0)
    last_result: dict | None = None
    runs_24h: int = Field(ge=0)
    failures_24h: int = Field(ge=0)


class JobStatusResponse(BaseModel):
    """Job monitoring response with all 5 job types."""

    jobs: list[JobExecutionStatus]
    recent_failures: list[JobExecutionStatus] = Field(default_factory=list)


# ============================================================================
# User List Schemas (T2.3)
# ============================================================================


class UserListItem(BaseModel):
    """User list item for admin debug portal."""

    id: UUID
    telegram_id: int | None
    email: str | None
    relationship_score: float = Field(ge=0, le=100)
    chapter: int = Field(ge=1, le=5)
    engagement_state: str | None
    game_status: str
    last_interaction_at: datetime | None
    created_at: datetime


class UserListResponse(BaseModel):
    """Paginated user list response."""

    users: list[UserListItem]
    total_count: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)


# ============================================================================
# User Detail Schemas (T2.4)
# ============================================================================


class UserTimingInfo(BaseModel):
    """User timing and countdown info."""

    grace_period_remaining_hours: float = Field(ge=0)
    is_in_grace_period: bool
    decay_rate_per_hour: float = Field(ge=0, le=10)
    hours_since_last_interaction: float = Field(ge=0)
    next_decay_at: datetime | None
    boss_ready: bool
    boss_attempts_remaining: int = Field(ge=0, le=3)


class UserNextActions(BaseModel):
    """Suggested next actions for debugging."""

    should_decay: bool
    decay_due_at: datetime | None
    can_trigger_boss: bool
    boss_threshold: float = Field(ge=0, le=100)
    score_to_boss: float


class UserDetailResponse(BaseModel):
    """Comprehensive user detail for debugging."""

    id: UUID
    telegram_id: int | None
    email: str | None
    phone: str | None

    # Game state
    relationship_score: float = Field(ge=0, le=100)
    chapter: int = Field(ge=1, le=5)
    chapter_name: str
    boss_attempts: int = Field(ge=0, le=3)
    days_played: int = Field(ge=0)
    game_status: str

    # Timing
    timing: UserTimingInfo
    next_actions: UserNextActions

    # Metadata
    created_at: datetime
    updated_at: datetime
    last_interaction_at: datetime | None


# ============================================================================
# State Machine Schemas (T2.5)
# ============================================================================


class EngagementStateInfo(BaseModel):
    """Engagement state machine details."""

    current_state: str
    multiplier: float = Field(ge=0, le=1)
    calibration_score: float = Field(ge=0, le=1)
    consecutive_in_zone: int = Field(ge=0)
    consecutive_clingy_days: int = Field(ge=0)
    consecutive_distant_days: int = Field(ge=0)
    recent_transitions: list[dict] = Field(default_factory=list)


class ChapterStateInfo(BaseModel):
    """Chapter state machine details."""

    current_chapter: int = Field(ge=1, le=5)
    chapter_name: str
    boss_threshold: float = Field(ge=0, le=100)
    current_score: float = Field(ge=0, le=100)
    progress_to_boss: float = Field(ge=0, le=100)
    boss_attempts: int = Field(ge=0, le=3)
    can_trigger_boss: bool


class ViceInfo(BaseModel):
    """Vice profile info."""

    category: str
    intensity_level: int = Field(ge=1, le=5)
    engagement_score: float = Field(ge=0, le=100)
    discovered_at: datetime


class ViceProfileInfo(BaseModel):
    """Vice personalization profile."""

    top_vices: list[ViceInfo]
    total_vices_discovered: int = Field(ge=0)
    expression_level: str | None  # subtle, moderate, explicit


class StateMachinesResponse(BaseModel):
    """All state machines for a user."""

    user_id: UUID
    engagement: EngagementStateInfo
    chapter: ChapterStateInfo
    vice_profile: ViceProfileInfo


# ============================================================================
# Prompt Viewing Schemas (Spec 018)
# ============================================================================


class PromptListItem(BaseModel):
    """Prompt list item for admin debug portal (without full content).

    AC-018-001: Returns id, token_count, generation_time_ms, meta_prompt_template, created_at
    """

    id: UUID
    token_count: int = Field(ge=0)
    generation_time_ms: float = Field(ge=0)
    meta_prompt_template: str
    created_at: datetime
    conversation_id: UUID | None = None


class PromptListResponse(BaseModel):
    """Paginated prompt list response.

    AC-018-002: Supports limit parameter
    AC-018-004: Returns empty list for non-existent user (not 404)
    """

    items: list[PromptListItem]
    count: int = Field(ge=0)
    user_id: UUID


class PromptDetailResponse(BaseModel):
    """Full prompt detail with content for debugging.

    AC-018-005: Returns full prompt_content, token_count, generation_time_ms,
    meta_prompt_template, context_snapshot, created_at
    AC-018-007: Includes conversation_id if present
    AC-018-010: Includes context_snapshot
    AC-018-011: Includes is_preview flag for preview mode
    """

    id: UUID | None = None  # None for preview (not logged)
    prompt_content: str
    token_count: int = Field(ge=0)
    generation_time_ms: float = Field(ge=0)
    meta_prompt_template: str
    context_snapshot: dict | None = None
    conversation_id: UUID | None = None
    created_at: datetime | None = None  # None for preview
    is_preview: bool = False  # True for preview, False for logged prompts
    message: str | None = None  # Optional message (e.g., "No prompts found")


# ============================================================================
# Voice Monitoring Schemas (Phase 3.1)
# ============================================================================


class VoiceConversationListItem(BaseModel):
    """Voice conversation summary for list display."""

    id: UUID
    user_id: UUID
    user_name: str | None = None
    started_at: datetime
    ended_at: datetime | None = None
    message_count: int = Field(ge=0)
    score_delta: float | None = None
    chapter_at_time: int | None = None
    elevenlabs_session_id: str | None = None
    status: str = "active"  # 'active' | 'processing' | 'processed' | 'failed'
    conversation_summary: str | None = None


class VoiceConversationListResponse(BaseModel):
    """Paginated voice conversation list."""

    items: list[VoiceConversationListItem]
    count: int = Field(ge=0)
    has_more: bool = False


class TranscriptEntryResponse(BaseModel):
    """Single transcript entry."""

    role: str  # 'user' | 'nikita' | 'agent'
    content: str
    timestamp: str | None = None


class VoiceConversationDetailResponse(BaseModel):
    """Full voice conversation detail with transcript."""

    id: UUID
    user_id: UUID
    user_name: str | None = None
    started_at: datetime
    ended_at: datetime | None = None
    message_count: int = Field(ge=0)
    score_delta: float | None = None
    chapter_at_time: int | None = None
    elevenlabs_session_id: str | None = None
    status: str
    conversation_summary: str | None = None
    emotional_tone: str | None = None
    transcript_raw: str | None = None
    messages: list[TranscriptEntryResponse] = []
    extracted_entities: dict | None = None
    processed_at: datetime | None = None


class ElevenLabsCallListItem(BaseModel):
    """Call summary from ElevenLabs API."""

    conversation_id: str
    agent_id: str
    start_time_unix: int
    call_duration_secs: int
    message_count: int
    status: str
    call_successful: str | None = None
    transcript_summary: str | None = None
    direction: str | None = None


class ElevenLabsCallListResponse(BaseModel):
    """ElevenLabs API call list response."""

    items: list[ElevenLabsCallListItem]
    has_more: bool = False
    next_cursor: str | None = None


class ElevenLabsTranscriptTurn(BaseModel):
    """Single turn in ElevenLabs transcript."""

    role: str  # 'user' | 'agent'
    message: str
    time_in_call_secs: float
    tool_calls: list[dict] | None = None
    tool_results: list[dict] | None = None


class ElevenLabsCallDetailResponse(BaseModel):
    """Full call detail from ElevenLabs API."""

    conversation_id: str
    agent_id: str
    status: str
    transcript: list[ElevenLabsTranscriptTurn]
    start_time_unix: int | None = None
    call_duration_secs: int | None = None
    cost: float | None = None
    transcript_summary: str | None = None
    call_successful: str | None = None
    has_audio: bool = False


class VoiceStatsResponse(BaseModel):
    """Voice call statistics."""

    total_calls_24h: int = 0
    total_calls_7d: int = 0
    total_calls_30d: int = 0
    avg_call_duration_secs: float | None = None
    calls_by_chapter: dict[int, int] = {}
    calls_by_status: dict[str, int] = {}
    processing_stats: dict[str, int] = {}  # active, processing, processed, failed


# ============================================================================
# Text Monitoring Schemas (Phase 4.1)
# ============================================================================


class TextConversationListItem(BaseModel):
    """Text conversation summary for list display."""

    id: UUID
    user_id: UUID
    user_name: str | None = None
    started_at: datetime
    ended_at: datetime | None = None
    message_count: int = Field(ge=0)
    score_delta: float | None = None
    chapter_at_time: int | None = None
    is_boss_fight: bool = False
    status: str = "active"  # 'active' | 'processing' | 'processed' | 'failed'
    conversation_summary: str | None = None
    emotional_tone: str | None = None


class TextConversationListResponse(BaseModel):
    """Paginated text conversation list."""

    items: list[TextConversationListItem]
    count: int = Field(ge=0)
    has_more: bool = False


class MessageResponse(BaseModel):
    """Single message in a conversation."""

    role: str  # 'user' | 'nikita'
    content: str
    timestamp: str | None = None
    analysis: dict | None = None


class TextConversationDetailResponse(BaseModel):
    """Full text conversation detail with messages."""

    id: UUID
    user_id: UUID
    user_name: str | None = None
    started_at: datetime
    ended_at: datetime | None = None
    message_count: int = Field(ge=0)
    score_delta: float | None = None
    chapter_at_time: int | None = None
    is_boss_fight: bool = False
    status: str
    conversation_summary: str | None = None
    emotional_tone: str | None = None
    messages: list[MessageResponse] = []
    extracted_entities: dict | None = None
    processed_at: datetime | None = None
    processing_attempts: int = 0
    last_message_at: datetime | None = None


class PipelineStageStatus(BaseModel):
    """Status of a post-processing pipeline stage."""

    stage_name: str
    stage_number: int
    completed: bool = False
    result_summary: str | None = None


class PipelineStatusResponse(BaseModel):
    """Post-processing pipeline status for a conversation."""

    conversation_id: UUID
    status: str  # 'active' | 'processing' | 'processed' | 'failed'
    processing_attempts: int = 0
    processed_at: datetime | None = None
    stages: list[PipelineStageStatus] = []
    threads_created: int = 0
    thoughts_created: int = 0
    entities_extracted: int = 0
    summary: str | None = None


class TextStatsResponse(BaseModel):
    """Text conversation statistics."""

    total_conversations_24h: int = 0
    total_conversations_7d: int = 0
    total_conversations_30d: int = 0
    total_messages_24h: int = 0
    avg_messages_per_conversation: float | None = None
    conversations_by_chapter: dict[int, int] = {}
    conversations_by_status: dict[str, int] = {}
    boss_fights_24h: int = 0
    processing_stats: dict[str, int] = {}


class ThreadListItem(BaseModel):
    """Conversation thread summary."""

    id: UUID
    user_id: UUID
    thread_type: str
    topic: str | None = None
    is_active: bool = True
    message_count: int = 0
    created_at: datetime
    last_mentioned_at: datetime | None = None


class ThreadListResponse(BaseModel):
    """Paginated thread list."""

    items: list[ThreadListItem]
    count: int = Field(ge=0)


class ThoughtListItem(BaseModel):
    """Nikita thought summary."""

    id: UUID
    user_id: UUID
    content: str
    thought_type: str | None = None
    created_at: datetime


class ThoughtListResponse(BaseModel):
    """Paginated thought list."""

    items: list[ThoughtListItem]
    count: int = Field(ge=0)
