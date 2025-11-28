"""Conversation-related API schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class MessageRequest(BaseModel):
    """Schema for incoming message from user."""

    content: str = Field(..., min_length=1, max_length=10000)
    platform: str = Field(default="telegram")  # 'telegram' | 'voice'


class MessageResponse(BaseModel):
    """Schema for Nikita's response."""

    message: str
    emotional_state: str | None = None
    score_delta: Decimal | None = None
    is_boss_trigger: bool = False


class ConversationMessage(BaseModel):
    """Schema for a single message in a conversation."""

    role: str  # 'user' | 'nikita'
    content: str
    timestamp: datetime
    analysis: dict[str, Any] | None = None


class ConversationResponse(BaseModel):
    """Schema for conversation history response."""

    id: UUID
    user_id: UUID
    platform: str
    messages: list[ConversationMessage]
    score_delta: Decimal | None
    started_at: datetime
    ended_at: datetime | None
    is_boss_fight: bool
    chapter_at_time: int | None

    model_config = {"from_attributes": True}


class ConversationSummary(BaseModel):
    """Schema for conversation summary in lists."""

    id: UUID
    platform: str
    message_count: int
    score_delta: Decimal | None
    started_at: datetime
    ended_at: datetime | None
    is_boss_fight: bool
