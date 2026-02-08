"""Admin API request/response schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class AdminUserListItem(BaseModel):
    """User list item for admin dashboard."""

    id: UUID
    telegram_id: int | None = None
    email: str | None = None
    relationship_score: Decimal = Field(ge=0, le=100)
    chapter: int = Field(ge=1, le=5)
    engagement_state: str
    game_status: str
    last_interaction_at: datetime | None = None
    created_at: datetime


class AdminUserDetailResponse(BaseModel):
    """Full user detail for admin view."""

    id: UUID
    telegram_id: int | None
    phone: str | None
    relationship_score: Decimal
    chapter: int
    boss_attempts: int
    days_played: int
    game_status: str
    last_interaction_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AdminSetScoreRequest(BaseModel):
    """Request to set user score (admin only)."""

    score: Decimal = Field(ge=0, le=100, description="New relationship score")
    reason: str = Field(min_length=1, description="Reason for adjustment")


class AdminSetChapterRequest(BaseModel):
    """Request to set user chapter (admin only)."""

    chapter: int = Field(ge=1, le=5, description="New chapter (1-5)")
    reason: str = Field(min_length=1, description="Reason for adjustment")


class AdminSetGameStatusRequest(BaseModel):
    """Request to set game status (admin only)."""

    game_status: str = Field(
        description="Game status: active | boss_fight | game_over | won"
    )
    reason: str = Field(min_length=1, description="Reason for adjustment")


class AdminSetEngagementStateRequest(BaseModel):
    """Request to set engagement state (admin only)."""

    state: str = Field(
        description="Engagement state: calibrating | in_zone | drifting | clingy | distant | out_of_zone"
    )
    reason: str = Field(min_length=1, description="Reason for adjustment")


class AdminResetResponse(BaseModel):
    """Response for reset operations."""

    success: bool
    message: str


class GeneratedPromptResponse(BaseModel):
    """Generated prompt response for admin viewer."""

    id: UUID
    user_id: UUID
    conversation_id: UUID | None = None
    prompt_content: str
    token_count: int
    generation_time_ms: float
    meta_prompt_template: str
    created_at: datetime


class GeneratedPromptsResponse(BaseModel):
    """Paginated generated prompts list."""

    prompts: list[GeneratedPromptResponse]
    total_count: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)


class AdminHealthResponse(BaseModel):
    """System health status for admin."""

    api_status: str  # "healthy" | "degraded" | "down"
    database_status: str  # "healthy" | "slow" | "down"
    memory_status: str  # "healthy" | "slow" | "down"
    error_count_24h: int = Field(ge=0)
    active_users_24h: int = Field(ge=0)


class AdminStatsResponse(BaseModel):
    """Admin overview statistics."""

    total_users: int = Field(ge=0)
    active_users: int = Field(ge=0)
    new_users_7d: int = Field(ge=0)
    total_conversations: int = Field(ge=0)
    avg_relationship_score: Decimal = Field(ge=0, le=100)


class ProcessingStatsResponse(BaseModel):
    """Post-processing job statistics (Spec 031 T3.3)."""

    # 24h metrics
    success_rate: float = Field(ge=0, le=100, description="Success rate as percentage")
    avg_duration_ms: int = Field(ge=0, description="Average duration in milliseconds")
    total_processed: int = Field(ge=0, description="Total jobs processed in 24h")
    success_count: int = Field(ge=0, description="Successful jobs in 24h")
    failed_count: int = Field(ge=0, description="Failed jobs in 24h")

    # Current state
    pending_count: int = Field(ge=0, description="Conversations pending processing")
    stuck_count: int = Field(ge=0, description="Conversations stuck >30 min in processing")


# ============================================================================
# CONVERSATION MONITORING SCHEMAS (Spec 034 US-3)
# ============================================================================


class ConversationListItem(BaseModel):
    """Conversation list item for admin dashboard."""

    id: UUID
    user_id: UUID
    user_identifier: str | None = None  # telegram_id or phone for display
    platform: str  # "telegram" | "voice"
    started_at: datetime
    ended_at: datetime | None = None
    status: str  # "pending" | "processing" | "processed" | "failed"
    score_delta: Decimal | None = None
    emotional_tone: str | None = None
    message_count: int = 0


class AdminConversationsResponse(BaseModel):
    """Paginated conversations list for admin."""

    conversations: list[ConversationListItem]
    total_count: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    days: int = Field(ge=1, default=7)


class ConversationPromptItem(BaseModel):
    """Prompt item for conversation prompts view."""

    id: UUID
    prompt_content: str
    token_count: int
    generation_time_ms: float
    meta_prompt_template: str
    context_snapshot: dict | None = None
    created_at: datetime


class ConversationPromptsResponse(BaseModel):
    """Response for conversation prompts endpoint."""

    conversation_id: UUID
    prompts: list[ConversationPromptItem]
    count: int = Field(ge=0)


class PipelineStageItem(BaseModel):
    """Pipeline stage status item."""

    stage_name: str
    stage_number: int
    status: str  # "pending" | "running" | "completed" | "failed" | "skipped"
    result_summary: str | None = None
    error_message: str | None = None
    duration_ms: int | None = None


class PipelineStatusResponse(BaseModel):
    """Response for pipeline status endpoint."""

    conversation_id: UUID
    status: str  # "pending" | "processing" | "processed" | "failed"
    processing_attempts: int
    processed_at: datetime | None = None
    stages: list[PipelineStageItem]


# ============================================================================
# SYSTEM OVERVIEW & SUPPORTING SCHEMAS (Spec 034 US-4)
# ============================================================================


class SystemOverviewResponse(BaseModel):
    """System overview metrics for admin dashboard (T4.1)."""

    active_users: int = Field(ge=0, description="Users active in last 24h")
    conversations_today: int = Field(ge=0, description="Conversations started today")
    processing_success_rate: float = Field(
        ge=0, le=100, description="Post-processing success rate %"
    )
    average_response_time_ms: int = Field(
        ge=0, description="Average API response time in ms"
    )


class ErrorLogItem(BaseModel):
    """Error log entry for admin view (T4.2)."""

    id: UUID
    level: str  # "error" | "warning" | "critical"
    message: str
    source: str  # module/function that raised error
    user_id: UUID | None = None
    conversation_id: UUID | None = None
    occurred_at: datetime
    resolved: bool = False


class ErrorLogResponse(BaseModel):
    """Paginated error log response (T4.2)."""

    errors: list[ErrorLogItem]
    total_count: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    filters_applied: dict = Field(default_factory=dict)


class BossEncounterItem(BaseModel):
    """Boss encounter record for user (T4.3)."""

    id: UUID
    chapter: int = Field(ge=1, le=5)
    outcome: str  # "passed" | "failed" | "pending"
    score_before: Decimal
    score_after: Decimal | None = None
    reasoning: str | None = None
    attempted_at: datetime
    resolved_at: datetime | None = None


class BossEncountersResponse(BaseModel):
    """User boss encounters response (T4.3)."""

    user_id: UUID
    encounters: list[BossEncounterItem]
    total_count: int = Field(ge=0)


class AuditLogItem(BaseModel):
    """Audit log entry for admin actions (T4.4)."""

    id: UUID
    admin_email: str
    action: str  # e.g., "view_user", "reset_boss", "clear_engagement"
    resource_type: str  # e.g., "user", "conversation"
    resource_id: UUID | None = None
    details: dict = Field(default_factory=dict)
    timestamp: datetime


class AuditLogsResponse(BaseModel):
    """Paginated audit logs response (T4.4)."""

    logs: list[AuditLogItem]
    total_count: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)


# ============================================================================
# PIPELINE HEALTH SCHEMAS (Spec 037 T3.2)
# ============================================================================


class CircuitBreakerStatus(BaseModel):
    """Circuit breaker status for a dependency."""

    name: str
    state: str  # "closed" | "open" | "half_open"
    failure_count: int = Field(ge=0)
    last_failure_time: datetime | None = None
    recovery_timeout_seconds: float = Field(ge=0)


class StageStats(BaseModel):
    """Statistics for a pipeline stage."""

    name: str
    avg_duration_ms: float = Field(ge=0)
    success_rate: float = Field(ge=0, le=100)
    runs_24h: int = Field(ge=0)
    failures_24h: int = Field(ge=0)


class StageFailure(BaseModel):
    """Recent stage failure record."""

    stage_name: str
    conversation_id: UUID
    error_message: str
    occurred_at: datetime


class PipelineHealthResponse(BaseModel):
    """Pipeline health status for admin (Spec 037 T3.2).

    Exposes circuit breaker states and stage statistics for
    observability and debugging.
    """

    # Overall health
    status: str = Field(description="healthy | degraded | down")

    # Circuit breaker states
    circuit_breakers: list[CircuitBreakerStatus] = Field(
        description="Status of all circuit breakers"
    )

    # Per-stage statistics
    stage_stats: list[StageStats] = Field(
        description="Performance stats per pipeline stage"
    )

    # Recent failures
    recent_failures: list[StageFailure] = Field(
        default_factory=list,
        description="Most recent stage failures (last 10)"
    )

    # Summary metrics
    total_runs_24h: int = Field(ge=0, description="Total pipeline runs in 24h")
    overall_success_rate: float = Field(ge=0, le=100, description="Overall success rate %")
    avg_pipeline_duration_ms: float = Field(ge=0, description="Average full pipeline duration")


class UnifiedPipelineStageHealth(BaseModel):
    """Health data for a single unified pipeline stage."""

    name: str
    is_critical: bool = False
    avg_duration_ms: float = Field(ge=0, default=0.0)
    success_rate: float = Field(ge=0, le=100, default=100.0)
    runs_24h: int = Field(ge=0, default=0)
    failures_24h: int = Field(ge=0, default=0)
    timeout_seconds: float = Field(ge=0, default=30.0)


class UnifiedPipelineHealthResponse(BaseModel):
    """Unified pipeline health for admin (Spec 042 T2.12).

    Reports per-stage success rates, timing, and error counts
    for the 9-stage unified pipeline.
    """

    status: str = Field(description="healthy | degraded | down")
    pipeline_version: str = Field(default="0.1.0")
    stages: list[UnifiedPipelineStageHealth] = Field(
        description="Health data for each pipeline stage"
    )
    total_runs_24h: int = Field(ge=0, default=0)
    overall_success_rate: float = Field(ge=0, le=100, default=100.0)
    avg_pipeline_duration_ms: float = Field(ge=0, default=0.0)
    last_run_at: datetime | None = Field(default=None)


# ============================================================================
# NEW ADMIN MUTATION SCHEMAS (FR-029)
# ============================================================================


class TriggerPipelineRequest(BaseModel):
    """Request to trigger pipeline for a user (admin only)."""

    conversation_id: UUID | None = Field(
        None,
        description="Specific conversation ID to process (optional, uses most recent if None)",
    )


class TriggerPipelineResponse(BaseModel):
    """Response from pipeline trigger."""

    job_id: UUID | None = Field(None, description="Job execution ID if created")
    status: str = Field(description="ok | error")
    message: str = Field(description="Human-readable message")


class PipelineHistoryItem(BaseModel):
    """Pipeline execution history item."""

    id: UUID
    job_name: str
    status: str  # "running" | "completed" | "failed"
    duration_ms: int | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None


class PipelineHistoryResponse(BaseModel):
    """Paginated pipeline execution history."""

    items: list[PipelineHistoryItem]
    total_count: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)


class AdminSetMetricsRequest(BaseModel):
    """Request to set user metrics (admin only)."""

    intimacy: Decimal | None = Field(None, ge=0, le=100, description="Intimacy score 0-100")
    passion: Decimal | None = Field(None, ge=0, le=100, description="Passion score 0-100")
    trust: Decimal | None = Field(None, ge=0, le=100, description="Trust score 0-100")
    secureness: Decimal | None = Field(None, ge=0, le=100, description="Secureness score 0-100")
    reason: str = Field(min_length=1, description="Reason for adjustment")


class PromptDetailResponse(BaseModel):
    """Detailed prompt response for admin debug viewer."""

    id: UUID | None = None
    user_id: UUID
    conversation_id: UUID | None = None
    prompt_content: str
    token_count: int
    generation_time_ms: float
    meta_prompt_template: str
    context_snapshot: dict | None = None
    created_at: datetime | None = None
    is_preview: bool = False
