"""Voice agent context builders (FR-018, FR-025).

This module provides builders for:
- DynamicVariables: Variables injected into ElevenLabs prompts
- ConversationConfig: Complete conversation configuration for ElevenLabs API

Implements US-13 acceptance criteria:
- AC-FR018-001: user_name, chapter, mood available in prompts
- AC-FR018-002: Secret variables hidden from LLM
- AC-FR025-001: Custom system prompt override
- AC-FR025-002: First message override
"""

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from nikita.agents.voice.models import (
    ConversationConfig,
    DynamicVariables,
    NikitaMood,
    TTSSettings,
    VoiceContext,
)
from nikita.agents.voice.tts_config import TTSConfigService, get_tts_config_service

if TYPE_CHECKING:
    from nikita.config.settings import Settings
    from nikita.db.models.user import User

logger = logging.getLogger(__name__)


class DynamicVariablesBuilder:
    """Builder for ElevenLabs dynamic variables (FR-018).

    Dynamic variables are injected into the system prompt using
    {{variable_name}} syntax. This allows personalization without
    regenerating the entire prompt.
    """

    def build_from_context(
        self,
        context: VoiceContext,
        session_token: str | None = None,
    ) -> DynamicVariables:
        """Build dynamic variables from voice context.

        Args:
            context: Loaded voice context
            session_token: Optional session token for auth

        Returns:
            DynamicVariables with all fields populated
        """
        return DynamicVariables(
            # User context
            user_name=context.user_name,
            chapter=context.chapter,
            relationship_score=context.relationship_score,
            engagement_state=context.engagement_state,
            # Nikita state
            nikita_mood=context.nikita_mood.value
            if isinstance(context.nikita_mood, NikitaMood)
            else str(context.nikita_mood),
            nikita_energy=context.nikita_energy,
            time_of_day=context.time_of_day,
            # Conversation context (comma-separated for prompt)
            recent_topics=", ".join(context.recent_topics)
            if context.recent_topics
            else "",
            open_threads=", ".join(context.open_threads)
            if context.open_threads
            else "",
            # Secrets (server-side only)
            secret__user_id=str(context.user_id),
            secret__session_token=session_token or "",
        )

    def build_from_user(
        self,
        user: "User",
        session_token: str | None = None,
    ) -> DynamicVariables:
        """Build dynamic variables directly from user model.

        Args:
            user: User database model
            session_token: Optional session token

        Returns:
            DynamicVariables with user info populated
        """
        # Get relationship score
        relationship_score = 50.0
        if user.metrics:
            relationship_score = float(
                getattr(user.metrics, "relationship_score", 50.0)
            )

        # Get engagement state
        engagement_state = getattr(user, "engagement_state", "IN_ZONE") or "IN_ZONE"

        # Calculate time of day
        current_hour = datetime.now().hour
        time_of_day = self._get_time_of_day(current_hour)

        return DynamicVariables(
            user_name=getattr(user, "name", "friend") or "friend",
            chapter=user.chapter,
            relationship_score=relationship_score,
            engagement_state=engagement_state,
            nikita_mood="neutral",
            nikita_energy="medium",
            time_of_day=time_of_day,
            recent_topics="",
            open_threads="",
            secret__user_id=str(user.id),
            secret__session_token=session_token or "",
        )

    def _get_time_of_day(self, hour: int) -> str:
        """Get time of day category from hour.

        Args:
            hour: Hour of day (0-23)

        Returns:
            One of: morning, afternoon, evening, night
        """
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 18:
            return "afternoon"
        elif 18 <= hour < 22:
            return "evening"
        else:
            return "night"


class ConversationConfigBuilder:
    """Builder for ElevenLabs conversation configuration (FR-025).

    Creates complete conversation config including:
    - System prompt with Nikita persona
    - First message based on chapter
    - TTS settings for emotional expression
    - Dynamic variables for personalization
    """

    def __init__(self, settings: "Settings"):
        """Initialize config builder.

        Args:
            settings: Application settings with ElevenLabs config
        """
        self.settings = settings
        self.tts_service = get_tts_config_service()
        self._vars_builder = DynamicVariablesBuilder()

    def build_config(
        self,
        user: "User",
        mood: NikitaMood | None = None,
        session_token: str | None = None,
    ) -> ConversationConfig:
        """Build complete conversation configuration.

        Args:
            user: User model with chapter, vices, metrics
            mood: Optional mood override for TTS
            session_token: Optional session token

        Returns:
            ConversationConfig ready for ElevenLabs API
        """
        # Build dynamic variables
        dynamic_variables = self._vars_builder.build_from_user(
            user, session_token=session_token
        )

        # Get TTS settings (chapter + mood)
        tts_settings = self.tts_service.get_final_settings(
            chapter=user.chapter, mood=mood
        )

        # Generate system prompt
        system_prompt = self._generate_system_prompt(user)

        # Get first message
        first_message = self._get_first_message(
            chapter=user.chapter,
            user_name=getattr(user, "name", None),
        )

        return ConversationConfig(
            system_prompt=system_prompt,
            first_message=first_message,
            tts=tts_settings,
            dynamic_variables=dynamic_variables,
        )

    def _generate_system_prompt(self, user: "User") -> str:
        """Generate personalized system prompt.

        Reuses VoiceAgentConfig logic for consistency.

        Args:
            user: User model

        Returns:
            Complete system prompt
        """
        from nikita.agents.voice.config import VoiceAgentConfig

        config = VoiceAgentConfig(settings=self.settings)

        # Get vices
        vices = getattr(user, "vice_preferences", []) or []
        primary_vices = [v for v in vices if getattr(v, "is_primary", False)]

        return config.generate_system_prompt(
            user_id=user.id,
            chapter=user.chapter,
            vices=primary_vices,
            user_name=getattr(user, "name", "friend") or "friend",
            relationship_score=self._get_relationship_score(user),
        )

    def _get_relationship_score(self, user: "User") -> float:
        """Get relationship score from user metrics."""
        if user.metrics:
            return float(getattr(user.metrics, "relationship_score", 50.0))
        return 50.0

    def _get_first_message(
        self,
        chapter: int,
        user_name: str | None,
    ) -> str:
        """Get chapter-appropriate first message.

        Args:
            chapter: Current chapter (1-5)
            user_name: User's name

        Returns:
            Personalized first message
        """
        name = user_name or "you"

        first_messages = {
            1: f"Oh, hey... {name}, right? What's going on?",
            2: f"Hey {name}! Good timing, I was just thinking about you.",
            3: f"There you are, {name}. I was hoping you'd call.",
            4: f"Mmm, hey {name}... I've been wanting to hear your voice.",
            5: f"Hi baby... I missed you. What's on your mind?",
        }
        return first_messages.get(chapter, f"Hey {name}, what's up?")

    def to_elevenlabs_format(self, config: ConversationConfig) -> dict[str, Any]:
        """Convert ConversationConfig to ElevenLabs API format.

        Args:
            config: Built conversation configuration

        Returns:
            Dict compatible with ElevenLabs API
        """
        result: dict[str, Any] = {
            "agent_id": self.settings.elevenlabs_default_agent_id,
            "conversation_config_override": {},
        }

        override = result["conversation_config_override"]

        # Agent section (prompt and first message)
        if config.system_prompt or config.first_message:
            override["agent"] = {}
            if config.system_prompt:
                override["agent"]["prompt"] = {"prompt": config.system_prompt}
            if config.first_message:
                override["agent"]["first_message"] = config.first_message

        # TTS section
        if config.tts:
            override["tts"] = {
                "stability": config.tts.stability,
                "similarity_boost": config.tts.similarity_boost,
                "speed": config.tts.speed,
            }

        # Dynamic variables (top-level, not in override)
        if config.dynamic_variables:
            result["dynamic_variables"] = config.dynamic_variables.to_dict()

        return result


# Singleton instance
_vars_builder: DynamicVariablesBuilder | None = None
_config_builder: ConversationConfigBuilder | None = None


def get_dynamic_variables_builder() -> DynamicVariablesBuilder:
    """Get singleton dynamic variables builder."""
    global _vars_builder
    if _vars_builder is None:
        _vars_builder = DynamicVariablesBuilder()
    return _vars_builder


def get_conversation_config_builder(
    settings: "Settings",
) -> ConversationConfigBuilder:
    """Get conversation config builder with settings."""
    # Not singleton - needs settings injection
    return ConversationConfigBuilder(settings=settings)


async def build_dynamic_variables(user: "User") -> dict[str, Any]:
    """Convenience function to build dynamic variables for a user.

    Used by InboundCallHandler to build context for voice calls.

    Args:
        user: User model with metrics and engagement_state loaded.

    Returns:
        Dictionary of dynamic variables for ElevenLabs agent.
    """
    from typing import Any

    builder = get_dynamic_variables_builder()

    # Build variables from user model
    variables = builder.build_from_user(user)

    return variables.to_dict()
