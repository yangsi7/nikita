"""Game state API schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ScoreHistoryResponse(BaseModel):
    """Schema for score history entry."""

    id: UUID
    score: Decimal
    chapter: int
    event_type: str | None
    event_details: dict[str, Any] | None
    recorded_at: datetime

    model_config = {"from_attributes": True}


class DailySummaryResponse(BaseModel):
    """Schema for daily summary."""

    id: UUID
    date: date
    score_start: Decimal | None
    score_end: Decimal | None
    score_change: Decimal | None
    decay_applied: Decimal | None
    conversations_count: int
    nikita_summary_text: str | None
    key_events: list[dict[str, Any]] | None

    model_config = {"from_attributes": True}


class GameStateResponse(BaseModel):
    """Schema for complete game state."""

    user_id: UUID
    relationship_score: Decimal
    chapter: int
    chapter_name: str
    days_played: int
    boss_attempts: int
    game_status: str
    last_interaction_at: datetime | None

    # Progress toward next chapter
    next_boss_threshold: Decimal | None
    score_to_boss: Decimal | None
    can_trigger_boss: bool

    # Current chapter info
    decay_rate: Decimal
    grace_period_hours: int


class BossEncounterResponse(BaseModel):
    """Schema for boss encounter info."""

    chapter: int
    name: str
    trigger: str
    challenge: str
    attempts_remaining: int
    is_available: bool


class VicePreferenceResponse(BaseModel):
    """Schema for vice preference."""

    category: str
    intensity_level: int
    engagement_score: Decimal
    discovered_at: datetime

    model_config = {"from_attributes": True}
