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
    neo4j_status: str  # "healthy" | "slow" | "down"
    error_count_24h: int = Field(ge=0)
    active_users_24h: int = Field(ge=0)


class AdminStatsResponse(BaseModel):
    """Admin overview statistics."""

    total_users: int = Field(ge=0)
    active_users: int = Field(ge=0)
    new_users_7d: int = Field(ge=0)
    total_conversations: int = Field(ge=0)
    avg_relationship_score: Decimal = Field(ge=0, le=100)
