"""Dependency container for NikitaTextAgent.

This module defines the NikitaDeps dataclass used by Pydantic AI
for dependency injection into the agent and its tools.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from nikita.config.settings import Settings
    from nikita.db.models.user import User
    from nikita.memory.supabase_memory import SupabaseMemory


@dataclass
class NikitaDeps:
    """
    Dependency container for Nikita text agent.

    Contains all dependencies needed by the agent and its tools:
    - memory: SupabaseMemory instance for knowledge graph access (optional)
    - user: User model with game state
    - settings: Application settings
    - generated_prompt: Personalized system prompt (injected before agent run)
    - conversation_messages: Raw messages from conversation.messages JSONB (Spec 030)
    - conversation_id: UUID for logging/debugging (Spec 030)

    Attributes:
        memory: Supabase-based memory system for the user (None if unavailable)
        user: Database user model with current game state
        settings: Application configuration settings
        generated_prompt: Dynamic personalized prompt (None = use static)
        conversation_messages: Raw messages for message_history injection (None = new session)
        conversation_id: The current conversation's UUID for logging
        session: Database session for session propagation (None = create new, Spec 038)
    """

    memory: "SupabaseMemory | None"
    user: "User"
    settings: "Settings"
    generated_prompt: str | None = None  # Personalized prompt from MetaPromptService
    conversation_messages: list[dict[str, Any]] | None = None  # Spec 030: Message history
    conversation_id: UUID | None = None  # Spec 030: For logging
    session: "AsyncSession | None" = None  # Spec 038: Session propagation
    psyche_state: dict | None = None  # Spec 056: Psyche agent state for L3 injection

    @property
    def chapter(self) -> int:
        """
        Get the user's current chapter.

        Returns:
            Current chapter number (1-5)
        """
        return self.user.chapter
