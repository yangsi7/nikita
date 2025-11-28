"""User-related API schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    """Schema for creating a new user."""

    telegram_id: int | None = None
    phone: str | None = None
    timezone: str = Field(default="UTC", max_length=50)


class UserResponse(BaseModel):
    """Schema for user response."""

    id: UUID
    telegram_id: int | None
    relationship_score: Decimal
    chapter: int
    days_played: int
    game_status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class UserStatsResponse(BaseModel):
    """Schema for user stats (portal dashboard)."""

    current_score: Decimal
    chapter: int
    chapter_name: str
    days_played: int
    boss_attempts: int
    game_status: str
    score_history: list["ScorePointResponse"]


class ScorePointResponse(BaseModel):
    """Schema for a single score data point."""

    date: datetime
    score: Decimal


class UserMetricsResponse(BaseModel):
    """Schema for hidden metrics (admin/debug only)."""

    intimacy: Decimal
    passion: Decimal
    trust: Decimal
    secureness: Decimal
    composite_score: Decimal
    updated_at: datetime

    model_config = {"from_attributes": True}
