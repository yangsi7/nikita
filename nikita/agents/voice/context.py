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
        # Spec 029: Voice-text parity - compute additional context
        day_of_week = context.day_of_week if hasattr(context, "day_of_week") else self._get_day_of_week()
        nikita_activity = self._compute_nikita_activity(context.time_of_day, day_of_week)

        return DynamicVariables(
            # User context
            user_name=context.user_name,
            chapter=context.chapter,
            relationship_score=context.relationship_score,
            engagement_state=context.engagement_state,
            # Spec 029: Voice-text parity - additional user context
            secureness=context.secureness if hasattr(context, "secureness") else 50.0,
            hours_since_last=context.hours_since_last if hasattr(context, "hours_since_last") else 0.0,
            # Nikita state
            nikita_mood=context.nikita_mood.value
            if isinstance(context.nikita_mood, NikitaMood)
            else str(context.nikita_mood),
            nikita_energy=context.nikita_energy,
            time_of_day=context.time_of_day,
            day_of_week=day_of_week,
            nikita_activity=nikita_activity,
            # Conversation context (comma-separated for prompt)
            recent_topics=", ".join(context.recent_topics)
            if context.recent_topics
            else "",
            open_threads=", ".join(context.open_threads)
            if context.open_threads
            else "",
            # Secrets (server-side only)
            secret__user_id=str(context.user_id),
            secret__signed_token=session_token or "",
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
        # Get relationship score (handle None)
        relationship_score = 50.0
        if user.metrics:
            rs = getattr(user.metrics, "relationship_score", 50.0)
            relationship_score = float(rs) if rs is not None else 50.0

        # Get engagement state (user.engagement_state is a RELATIONSHIP object, need .state attribute)
        es_obj = getattr(user, "engagement_state", None)
        if es_obj is not None and hasattr(es_obj, "state") and es_obj.state:
            engagement_state = es_obj.state.upper()
        else:
            engagement_state = "IN_ZONE"

        # Get chapter (handle None - default to 1)
        chapter = user.chapter if user.chapter is not None else 1

        # Calculate time of day
        current_hour = datetime.now().hour
        time_of_day = self._get_time_of_day(current_hour)

        # Spec 029: Voice-text parity - compute additional context
        secureness = 50.0
        if user.metrics:
            sec = getattr(user.metrics, "secureness", 50.0)
            secureness = float(sec) if sec is not None else 50.0

        hours_since_last = 0.0
        if hasattr(user, "last_interaction_at") and user.last_interaction_at:
            delta = datetime.utcnow() - user.last_interaction_at
            hours_since_last = round(delta.total_seconds() / 3600, 1)

        day_of_week = self._get_day_of_week()
        nikita_activity = self._compute_nikita_activity(time_of_day, day_of_week)
        nikita_energy = self._compute_nikita_energy(time_of_day)

        return DynamicVariables(
            user_name=getattr(user, "name", "friend") or "friend",
            chapter=chapter,
            relationship_score=relationship_score,
            engagement_state=engagement_state,
            # Spec 029: Voice-text parity
            secureness=secureness,
            hours_since_last=hours_since_last,
            nikita_mood="neutral",
            nikita_energy=nikita_energy,
            time_of_day=time_of_day,
            day_of_week=day_of_week,
            nikita_activity=nikita_activity,
            recent_topics="",
            open_threads="",
            secret__user_id=str(user.id),
            secret__signed_token=session_token or "",
        )

    def _get_time_of_day(self, hour: int) -> str:
        """Get time of day category from hour.

        Args:
            hour: Hour of day (0-23)

        Returns:
            One of: morning, afternoon, evening, night, late_night
        """
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 21:
            return "evening"
        elif 21 <= hour < 24:
            return "night"
        else:
            return "late_night"

    def _get_day_of_week(self) -> str:
        """Get current day of week name.

        Returns:
            Day name (Monday, Tuesday, etc.)
        """
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        return day_names[datetime.now().weekday()]

    def _compute_nikita_activity(self, time_of_day: str, day_of_week: str) -> str:
        """Compute what Nikita is likely doing based on time.

        Spec 029: Voice-text parity - matches meta_prompts/service.py implementation.

        Args:
            time_of_day: Time of day (morning, afternoon, evening, night, late_night)
            day_of_week: Day name (Monday, Tuesday, etc.)

        Returns:
            Activity description string
        """
        weekend = day_of_week in ("Saturday", "Sunday")

        activities = {
            ("morning", False): "just finished her morning coffee, checking emails",
            ("morning", True): "sleeping in after a late night",
            ("afternoon", False): "deep in a security audit, headphones on",
            ("afternoon", True): "at the gym, checking her phone between sets",
            ("evening", False): "wrapping up work, cat on her lap",
            ("evening", True): "getting ready to go out with friends",
            ("night", False): "on the couch with wine, watching trash TV",
            ("night", True): "at a bar with friends, slightly buzzed",
            ("late_night", False): "in bed scrolling, can't sleep",
            ("late_night", True): "stumbling home from a night out",
        }

        return activities.get((time_of_day, weekend), "doing her thing")

    def _compute_nikita_energy(self, time_of_day: str) -> str:
        """Compute energy level based on time of day.

        Spec 029: Voice-text parity - matches meta_prompts/service.py implementation.

        Args:
            time_of_day: Time of day (morning, afternoon, evening, night, late_night)

        Returns:
            Energy level (low, moderate, high)
        """
        energy_map = {
            "morning": "moderate",
            "afternoon": "high",
            "evening": "moderate",
            "night": "low",
            "late_night": "low",
        }
        return energy_map.get(time_of_day, "moderate")


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

    async def build_config(
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

        # Generate system prompt using MetaPromptService
        system_prompt = await self._generate_system_prompt(user)

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

    async def _generate_system_prompt(self, user: "User") -> str:
        """Generate personalized system prompt using MetaPromptService.

        Uses LLM-powered meta-prompt generation for context-aware personalization,
        matching the text agent's approach to prompt generation.

        Args:
            user: User model

        Returns:
            Complete system prompt generated by MetaPromptService
        """
        from nikita.db.database import get_session_maker
        from nikita.meta_prompts.service import MetaPromptService

        try:
            session_maker = get_session_maker()
            async with session_maker() as session:
                service = MetaPromptService(session)
                result = await service.generate_system_prompt(
                    user_id=user.id,
                    skip_logging=False,  # Phase 2: Enable voice prompt logging
                )
                return result.content
        except Exception as e:
            # Fallback to static prompt if MetaPromptService fails
            logger.warning(f"[VOICE] MetaPromptService failed, using fallback: {e}")
            return self._generate_fallback_prompt(user)

    def _generate_fallback_prompt(self, user: "User") -> str:
        """Generate fallback prompt using static VoiceAgentConfig.

        Used when MetaPromptService is unavailable.

        Args:
            user: User model

        Returns:
            Static system prompt
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


async def build_dynamic_variables(
    user: "User",
    signed_token: str | None = None,
) -> dict[str, Any]:
    """Convenience function to build dynamic variables for a user.

    Used by InboundCallHandler to build context for voice calls.

    IMPORTANT: Returns dict WITH secrets for ElevenLabs webhook response.
    Secret variables (secret__*) are hidden from LLM but available for
    server tool parameter substitution via {{variable_name}}.

    Args:
        user: User model with metrics and engagement_state loaded.
        signed_token: HMAC-signed token for server tool authentication.

    Returns:
        Dictionary of dynamic variables INCLUDING secrets for ElevenLabs.
    """
    from typing import Any

    builder = get_dynamic_variables_builder()

    # Build variables from user model with signed token
    variables = builder.build_from_user(user, session_token=signed_token)

    # CRITICAL: Use to_dict_with_secrets() for webhook response
    # ElevenLabs needs secrets for server tool parameter substitution
    return variables.to_dict_with_secrets()
