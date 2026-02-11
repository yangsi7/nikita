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
from datetime import datetime, timezone
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
from nikita.utils.nikita_state import (
    compute_day_of_week,
    compute_emotional_context,
    compute_nikita_activity,
    compute_nikita_energy,
    compute_time_of_day,
)

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

        # Spec 032: Extract new context fields with safe defaults
        today_summary = getattr(context, "today_summary", "") or ""
        last_conversation_summary = context.last_conversation_summary or ""
        nikita_daily_events = getattr(context, "nikita_daily_events", "") or ""
        user_backstory = getattr(context, "user_backstory", "") or ""

        # Spec 032: 4D mood extraction (default to neutral 0.5)
        nikita_mood_4d = getattr(context, "nikita_mood_4d", None) or {}
        nikita_mood_arousal = nikita_mood_4d.get("arousal", 0.5) if isinstance(nikita_mood_4d, dict) else 0.5
        nikita_mood_valence = nikita_mood_4d.get("valence", 0.5) if isinstance(nikita_mood_4d, dict) else 0.5
        nikita_mood_dominance = nikita_mood_4d.get("dominance", 0.5) if isinstance(nikita_mood_4d, dict) else 0.5
        nikita_mood_intimacy = nikita_mood_4d.get("intimacy", 0.5) if isinstance(nikita_mood_4d, dict) else 0.5

        # Spec 032: Conflict extraction
        active_conflict = getattr(context, "active_conflict", None) or {}
        active_conflict_type = active_conflict.get("type", "") if isinstance(active_conflict, dict) else ""
        active_conflict_severity = active_conflict.get("severity", 0.0) if isinstance(active_conflict, dict) else 0.0

        # Spec 032: Build context_block
        context_block = self._build_context_block(
            user_name=context.user_name,
            chapter=context.chapter,
            relationship_score=context.relationship_score,
            today_summary=today_summary,
            last_conversation_summary=last_conversation_summary,
            nikita_daily_events=nikita_daily_events,
            nikita_mood_4d={
                "arousal": nikita_mood_arousal,
                "valence": nikita_mood_valence,
                "dominance": nikita_mood_dominance,
                "intimacy": nikita_mood_intimacy,
            },
            active_conflict_type=active_conflict_type,
            active_conflict_severity=active_conflict_severity,
        )

        # Spec 032: Compute emotional context summary
        emotional_context = self._compute_emotional_context(
            nikita_mood_arousal, nikita_mood_valence, nikita_mood_dominance, nikita_mood_intimacy
        )

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
            # Spec 032: New context fields
            today_summary=today_summary,
            last_conversation_summary=last_conversation_summary,
            nikita_mood_arousal=nikita_mood_arousal,
            nikita_mood_valence=nikita_mood_valence,
            nikita_mood_dominance=nikita_mood_dominance,
            nikita_mood_intimacy=nikita_mood_intimacy,
            nikita_daily_events=nikita_daily_events,
            active_conflict_type=active_conflict_type,
            active_conflict_severity=active_conflict_severity,
            emotional_context=emotional_context,
            user_backstory=user_backstory,
            context_block=context_block,
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
            delta = datetime.now(timezone.utc) - user.last_interaction_at
            hours_since_last = round(delta.total_seconds() / 3600, 1)

        day_of_week = self._get_day_of_week()
        nikita_activity = self._compute_nikita_activity(time_of_day, day_of_week)
        nikita_energy = self._compute_nikita_energy(time_of_day)

        # Spec 032: Extract backstory from onboarding profile
        user_name = getattr(user, "name", "friend") or "friend"
        onboarding_profile = getattr(user, "onboarding_profile", None) or {}
        user_backstory = onboarding_profile.get("backstory", "") if isinstance(onboarding_profile, dict) else ""

        # Spec 032: Build context_block with available data
        context_block = self._build_context_block(
            user_name=user_name,
            chapter=chapter,
            relationship_score=relationship_score,
        )

        return DynamicVariables(
            user_name=user_name,
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
            # Spec 032: New fields with defaults (populated from full context in build_from_context)
            today_summary="",
            last_conversation_summary="",
            nikita_mood_arousal=0.5,
            nikita_mood_valence=0.5,
            nikita_mood_dominance=0.5,
            nikita_mood_intimacy=0.5,
            nikita_daily_events="",
            active_conflict_type="",
            active_conflict_severity=0.0,
            emotional_context="",
            user_backstory=user_backstory,
            context_block=context_block,
            secret__user_id=str(user.id),
            secret__signed_token=session_token or "",
        )

    def _get_time_of_day(self, hour: int) -> str:
        """Get time of day category from hour. Delegates to shared utility."""
        return compute_time_of_day(hour)

    def _get_day_of_week(self) -> str:
        """Get current day of week name. Delegates to shared utility."""
        return compute_day_of_week()

    def _compute_nikita_activity(self, time_of_day: str, day_of_week: str) -> str:
        """Compute what Nikita is doing. Delegates to shared utility."""
        return compute_nikita_activity(time_of_day, day_of_week)

    def _compute_nikita_energy(self, time_of_day: str) -> str:
        """Compute energy level. Delegates to shared utility."""
        return compute_nikita_energy(time_of_day)

    def _build_context_block(
        self,
        user_name: str = "",
        chapter: int = 1,
        relationship_score: float = 50.0,
        today_summary: str = "",
        last_conversation_summary: str = "",
        nikita_daily_events: str = "",
        nikita_mood_4d: dict | None = None,
        active_conflict_type: str = "",
        active_conflict_severity: float = 0.0,
        user_backstory: str = "",
    ) -> str:
        """Build aggregated context block for prompt injection.

        Spec 032 T1.4: Generate context_block string ≤500 tokens.

        Args:
            user_name: User's name
            chapter: Current chapter (1-5)
            relationship_score: Current relationship score
            today_summary: Summary of today's interactions
            last_conversation_summary: Summary of last conversation
            nikita_daily_events: What Nikita has been doing
            nikita_mood_4d: 4D emotional state dict
            active_conflict_type: Type of active conflict
            active_conflict_severity: Severity of conflict (0-1)
            user_backstory: How user and Nikita met

        Returns:
            Aggregated context string (≤2000 chars ≈ 500 tokens)
        """
        parts: list[str] = []

        # Relationship state (always include)
        chapter_names = {
            1: "just met",
            2: "getting acquainted",
            3: "building trust",
            4: "growing close",
            5: "deeply connected",
        }
        relationship_state = chapter_names.get(chapter, "developing")
        parts.append(f"With {user_name or 'them'}: {relationship_state} (score: {relationship_score:.0f})")

        # User backstory (if available)
        if user_backstory:
            backstory = user_backstory[:150]  # Truncate
            parts.append(f"How we met: {backstory}")

        # Recent context (if available)
        if last_conversation_summary:
            summary = last_conversation_summary[:200]  # Truncate
            parts.append(f"Last talk: {summary}")

        if today_summary:
            summary = today_summary[:150]  # Truncate
            parts.append(f"Today: {summary}")

        # Nikita's state (if available)
        if nikita_daily_events:
            events = nikita_daily_events[:150]  # Truncate
            parts.append(f"Nikita's day: {events}")

        # Emotional context from 4D mood
        if nikita_mood_4d:
            emotional_summary = self._compute_emotional_context(
                nikita_mood_4d.get("arousal", 0.5),
                nikita_mood_4d.get("valence", 0.5),
                nikita_mood_4d.get("dominance", 0.5),
                nikita_mood_4d.get("intimacy", 0.5),
            )
            if emotional_summary:
                parts.append(f"Mood: {emotional_summary}")

        # Active conflict (if any)
        if active_conflict_type and active_conflict_severity > 0.1:
            severity_word = "minor" if active_conflict_severity < 0.3 else (
                "moderate" if active_conflict_severity < 0.6 else "serious"
            )
            parts.append(f"Tension: {severity_word} {active_conflict_type}")

        # Join and enforce token budget (≤2000 chars ≈ 500 tokens)
        context_block = " | ".join(parts)
        if len(context_block) > 2000:
            context_block = context_block[:1997] + "..."

        return context_block

    def _compute_emotional_context(
        self,
        arousal: float = 0.5,
        valence: float = 0.5,
        dominance: float = 0.5,
        intimacy: float = 0.5,
    ) -> str:
        """Compute emotional context summary. Delegates to shared utility."""
        return compute_emotional_context(arousal, valence, dominance, intimacy)


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
        """Generate personalized system prompt using context_engine router.

        Spec 042: Voice prompts generated via unified pipeline.
        Falls back to static prompt if pipeline unavailable.

        Args:
            user: User model

        Returns:
            Complete system prompt (pipeline or fallback)
        """
        # Voice uses static fallback (pipeline prompt generation happens separately)
        # TODO: Integrate voice with unified pipeline prompt builder
        logger.info(f"[VOICE] Generating fallback prompt for user {user.id}")
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
