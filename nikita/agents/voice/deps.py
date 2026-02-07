"""Dependency container for VoiceAgent.

This module defines the VoiceAgentDeps dataclass used for
dependency injection in voice agent services and handlers.
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from nikita.agents.voice.models import (
        VoiceContext,
        TTSSettings,
        DynamicVariables,
        ConversationConfig,
    )
    from nikita.config.settings import Settings
    from nikita.db.models.user import User
    from nikita.memory.supabase_memory import SupabaseMemory


@dataclass
class VoiceAgentDeps:
    """
    Dependency container for Nikita voice agent.

    Contains all dependencies needed by voice services and handlers:
    - user: User model with game state
    - settings: Application settings
    - memory: SupabaseMemory instance (optional, for context loading)
    - voice_context: Pre-loaded context for server tools
    - tts_settings: Voice synthesis parameters
    - conversation_config: ElevenLabs config overrides
    - session_id: ElevenLabs session identifier

    Attributes:
        user: Database user model with current game state
        settings: Application configuration settings
        memory: Graphiti-based memory system (None if Neo4j unavailable)
        voice_context: Loaded context for voice conversation
        tts_settings: TTS parameters based on chapter/mood
        conversation_config: ElevenLabs overrides (prompt, first message, etc.)
        session_id: ElevenLabs conversation session ID
        call_started_at: When the call was initiated
    """

    user: "User"
    settings: "Settings"
    memory: "SupabaseMemory | None" = None
    voice_context: "VoiceContext | None" = None
    tts_settings: "TTSSettings | None" = None
    conversation_config: "ConversationConfig | None" = None
    session_id: str | None = None
    call_started_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def user_id(self) -> UUID:
        """Get the user's ID."""
        return self.user.id

    @property
    def chapter(self) -> int:
        """Get the user's current chapter."""
        return self.user.chapter

    @property
    def relationship_score(self) -> float:
        """Get the user's current relationship score."""
        if self.user.metrics:
            return self.user.metrics.relationship_score
        return 50.0

    @property
    def is_voice_available(self) -> bool:
        """
        Check if voice calls are available for this user.

        Voice availability depends on:
        - Game status (must be 'active')
        - Chapter progression (chapter 1 = rare, chapter 5 = common)

        Returns:
            True if user can make voice calls
        """
        if self.user.game_status != "active":
            return False
        # Voice always available for chapters 2+
        # Chapter 1 has limited availability (handled by CallAvailability)
        return True
