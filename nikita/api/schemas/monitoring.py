"""Response schemas for admin monitoring endpoints.

Part of Spec 034 - Admin User Monitoring Dashboard.

These schemas define the structure of API responses for monitoring endpoints.
All schemas are Pydantic models with validation.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


# =============================================================================
# System Overview Schemas
# =============================================================================


class SystemMetrics(BaseModel):
    """System-wide metrics for dashboard overview.

    FR-010: System overview dashboard with aggregate metrics.
    """

    total_users: int = Field(ge=0, description="Total registered users")
    active_users_24h: int = Field(ge=0, description="Users active in last 24h")
    total_conversations: int = Field(ge=0, description="Total conversations")
    conversations_today: int = Field(ge=0, description="Conversations started today")
    total_voice_sessions: int = Field(ge=0, description="Total voice sessions")
    voice_sessions_today: int = Field(ge=0, description="Voice sessions today")
    avg_score: float = Field(description="Average relationship score")
    users_in_boss_fight: int = Field(ge=0, description="Users currently in boss fight")
    users_game_over: int = Field(ge=0, description="Users with game_over status")


# =============================================================================
# Memory Graph Schemas
# =============================================================================


class MemorySnapshot(BaseModel):
    """Snapshot of user's memory graph status.

    FR-007: Memory graph monitoring (3 graphs).
    """

    user_facts_count: int = Field(ge=0, description="Facts in user_graph")
    relationship_episodes_count: int = Field(ge=0, description="Episodes in relationship_graph")
    nikita_events_count: int = Field(ge=0, description="Events in nikita_graph")
    total_threads: int = Field(ge=0, description="Total conversation threads")
    open_threads: int = Field(ge=0, description="Open/unresolved threads")
    last_sync: datetime | None = Field(description="Last graph sync timestamp")
    graph_status: Literal["healthy", "syncing", "error", "unavailable"] = Field(
        description="Current graph connection status"
    )


# =============================================================================
# Pipeline Status Schemas
# =============================================================================


class PipelineStage(BaseModel):
    """Status of a single pipeline processing stage.

    FR-004: Post-processing pipeline (9 stages).
    """

    name: str = Field(description="Stage name (e.g., extraction, graph_update)")
    status: Literal["pending", "in_progress", "completed", "failed", "skipped"] = Field(
        description="Stage execution status"
    )
    started_at: datetime | None = Field(description="Stage start time")
    completed_at: datetime | None = Field(description="Stage completion time")
    error: str | None = Field(description="Error message if failed")


class PipelineStatus(BaseModel):
    """Full pipeline status for a conversation.

    FR-004: Post-processing pipeline status tracking.
    """

    conversation_id: UUID = Field(description="Conversation being processed")
    stages: list[PipelineStage] = Field(description="All 9 pipeline stages")
    overall_status: Literal["pending", "in_progress", "completed", "failed"] = Field(
        description="Overall pipeline status"
    )


# =============================================================================
# Error Tracking Schemas
# =============================================================================


class ErrorEntry(BaseModel):
    """Single error log entry.

    FR-009: Error monitoring across all components.
    """

    timestamp: datetime = Field(description="When error occurred")
    error_type: str = Field(description="Error category")
    message: str = Field(description="Error message")
    conversation_id: UUID | None = Field(description="Related conversation if applicable")
    user_id: UUID | None = Field(description="Related user if applicable")


class ErrorSummary(BaseModel):
    """Summary of errors over a time period.

    FR-009: Error monitoring with aggregations.
    """

    total_errors_24h: int = Field(ge=0, description="Total errors in last 24h")
    error_rate_percent: float = Field(description="Error rate as percentage")
    errors: list[ErrorEntry] = Field(description="Recent error entries")


# =============================================================================
# Scoring Schemas
# =============================================================================


class ScorePoint(BaseModel):
    """Single point in score timeline.

    FR-005: Scoring history tracking.
    """

    timestamp: datetime = Field(description="When score was recorded")
    score: float = Field(description="Score value at this point")
    event_type: str = Field(description="What triggered this score change")
    delta: float = Field(description="Change from previous score")


class ScoreTimeline(BaseModel):
    """User's complete score timeline.

    FR-005: Scoring history with chart data.
    """

    user_id: UUID = Field(description="User being tracked")
    points: list[ScorePoint] = Field(description="Score history points")
    current_score: float = Field(description="Current relationship score")
    boss_threshold: float = Field(description="Score that triggers boss fight")
    chapter: int = Field(ge=1, le=5, description="Current chapter")


# =============================================================================
# Boss Encounter Schemas
# =============================================================================


class BossEncounter(BaseModel):
    """Single boss encounter record.

    FR-005: Boss encounter tracking (part of scoring).
    """

    timestamp: datetime = Field(description="When encounter occurred")
    chapter: int = Field(ge=1, le=5, description="Chapter of encounter")
    attempt: int = Field(ge=1, description="Attempt number (1-3)")
    result: Literal["passed", "failed"] = Field(description="Encounter outcome")
    score_before: float = Field(description="Score before encounter")
    score_after: float = Field(description="Score after encounter")
    trigger_reason: str = Field(description="What triggered the boss fight")


class BossEncounters(BaseModel):
    """All boss encounters for a user.

    FR-005: Boss encounter history.
    """

    user_id: UUID = Field(description="User being tracked")
    total_attempts: int = Field(ge=0, description="Total boss attempts")
    successful: int = Field(ge=0, description="Successful encounters")
    failed: int = Field(ge=0, description="Failed encounters")
    encounters: list[BossEncounter] = Field(description="Encounter history")


# =============================================================================
# User Monitoring Schemas
# =============================================================================


class UserListItem(BaseModel):
    """User summary for list view.

    FR-001: User monitoring list.
    """

    id: UUID = Field(description="User ID")
    email: str | None = Field(description="User email (if available)")
    telegram_id: int | None = Field(description="Telegram user ID")
    relationship_score: float = Field(description="Current score")
    chapter: int = Field(ge=1, le=5, description="Current chapter")
    game_status: str = Field(description="active, boss_fight, game_over, won")
    last_activity: datetime | None = Field(description="Last interaction time")
    conversations_count: int = Field(ge=0, description="Total conversations")
    voice_sessions_count: int = Field(ge=0, description="Total voice sessions")


class UserDetail(BaseModel):
    """Full user detail view.

    FR-001: User monitoring detail.
    """

    id: UUID
    email: str | None
    telegram_id: int | None
    relationship_score: float
    chapter: int
    boss_attempts: int
    game_status: str
    created_at: datetime
    last_activity: datetime | None

    # Metrics
    intimacy: float
    passion: float
    trust: float
    secureness: float

    # Counts
    conversations_count: int
    voice_sessions_count: int
    generated_prompts_count: int

    # Memory
    memory_snapshot: MemorySnapshot | None


# =============================================================================
# Conversation Monitoring Schemas
# =============================================================================


class ConversationListItem(BaseModel):
    """Conversation summary for list view.

    FR-002: Conversation monitoring list.
    """

    id: UUID
    user_id: UUID
    platform: str
    started_at: datetime
    ended_at: datetime | None
    message_count: int
    status: str
    pipeline_status: str | None


class ConversationDetail(BaseModel):
    """Full conversation detail.

    FR-002: Conversation monitoring detail.
    """

    id: UUID
    user_id: UUID
    platform: str
    started_at: datetime
    ended_at: datetime | None
    messages: list[dict]  # Full message history
    status: str
    pipeline_status: PipelineStatus | None
    generated_prompt_id: UUID | None


# =============================================================================
# Generated Prompt Schemas
# =============================================================================


class GeneratedPromptListItem(BaseModel):
    """Generated prompt summary for list view.

    FR-003: Generated prompt inspection.
    """

    id: UUID
    user_id: UUID
    conversation_id: UUID | None
    created_at: datetime
    token_count: int | None
    template_version: str | None


class GeneratedPromptDetail(BaseModel):
    """Full generated prompt detail.

    FR-003: Generated prompt layers inspection.
    """

    id: UUID
    user_id: UUID
    conversation_id: UUID | None
    created_at: datetime
    token_count: int | None
    template_version: str | None

    # Prompt layers
    system_prompt: str | None
    user_context: str | None
    humanization_layer: str | None
    full_prompt: str | None


# =============================================================================
# Job Execution Schemas
# =============================================================================


class JobExecutionListItem(BaseModel):
    """Job execution summary for list view.

    FR-008: Job execution monitoring.
    """

    id: UUID
    job_name: str
    status: str
    started_at: datetime
    completed_at: datetime | None
    conversation_id: UUID | None
    error_message: str | None


class JobExecutionDetail(BaseModel):
    """Full job execution detail.

    FR-008: Job execution monitoring detail.
    """

    id: UUID
    job_name: str
    status: str
    started_at: datetime
    completed_at: datetime | None
    conversation_id: UUID | None
    error_message: str | None
    stage_results: dict | None  # Per-stage execution details
