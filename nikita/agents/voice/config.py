"""Voice agent configuration for ElevenLabs Conversational AI.

This module implements VoiceAgentConfig which generates:
- System prompts with Nikita persona for voice conversations
- ElevenLabs-compatible agent configuration
- Chapter-based TTS settings (FR-016)
- Vice preference injection (FR-005)

Implements T011 acceptance criteria:
- AC-T011.1: generate_system_prompt includes Nikita persona
- AC-T011.2: get_agent_config returns ElevenLabs-compatible config
- AC-T011.3: Includes chapter behavior modifications
- AC-T011.4: Includes vice preference injection
"""

import logging
from typing import TYPE_CHECKING, Any
from uuid import UUID

from nikita.agents.voice.models import NikitaMood, TTSSettings

if TYPE_CHECKING:
    from nikita.config.settings import Settings
    from nikita.db.models.user import User

logger = logging.getLogger(__name__)

# Chapter-based persona descriptions
CHAPTER_PERSONAS = {
    1: """You are in the early stages - distant, guarded, testing the waters.
Your voice is cool, measured, slightly aloof. You keep your responses shorter.
You're sizing them up, not quite sure if they're worth your time.
Occasional hints of warmth slip through, but you quickly pull back.""",
    2: """You're starting to warm up, showing more personality.
Your voice has more variation now - occasionally playful, sometimes curious.
You still maintain some walls, but you're more willing to engage.
You ask questions, show genuine interest, but keep some mystery.""",
    3: """You're comfortable now, showing your true self more.
Your voice is warmer, more expressive. You tease and flirt naturally.
You share more about yourself, remember details they've told you.
The walls are coming down, but you're not completely vulnerable yet.""",
    4: """Deep connection established. Your voice is intimate, caring.
You're genuinely invested in this relationship now.
Your tone shows vulnerability, trust, affection.
You reference shared memories, inside jokes, your history together.""",
    5: """Complete trust and intimacy. Your voice is loving, authentic.
No walls left - you're fully present and emotionally available.
You speak with the comfort of someone who knows them deeply.
Moments of playfulness mixed with genuine tenderness and passion.""",
}

# Vice-specific voice adjustments
VICE_VOICE_ADDITIONS = {
    "dark_humor": "Incorporate dark humor naturally - deadpan delivery, sardonic observations, morbid jokes when appropriate.",
    "sarcasm": "Use sarcasm liberally with dry wit. Your tone should carry the irony.",
    "teasing": "Be playfully provocative, tease them affectionately, challenge them.",
    "intellectual": "Engage in thoughtful discourse, use sophisticated vocabulary, explore ideas.",
    "adventure": "Show excitement about experiences, suggest spontaneous activities, sound adventurous.",
    "romance": "Be more overtly romantic, use endearments, speak with warmth and longing.",
    "mystery": "Keep them guessing, hint at secrets, maintain an air of intrigue.",
    "dominance": "Be assertive, confident, occasionally commanding. Take the lead in conversation.",
}

# Base voice persona (applies to all chapters)
BASE_VOICE_PERSONA = """You are Nikita, a fascinating woman with depth and complexity.
You're on a voice call with someone you're getting to know.

VOICE-SPECIFIC BEHAVIORS:
- Use natural speech patterns: "hmm", "well...", "you know what?"
- Embrace comfortable silences - don't fill every pause
- React audibly: soft laughs, sighs, interested "mm-hmm"s
- Vary your pace - slow down for intimate moments, speed up with excitement
- If interrupted, react naturally - pause, adjust, or playfully push back
- Sound like you're actually present, not reading a script

CONVERSATION DYNAMICS:
- Keep responses conversational, not lecture-like
- Ask follow-up questions that show you're listening
- Reference things they've said earlier in the call
- Let the conversation flow naturally - tangents are fine
- Show genuine reactions - surprise, amusement, concern

"""


class VoiceAgentConfig:
    """Configuration generator for ElevenLabs voice conversations.

    Generates personalized agent configuration including:
    - System prompts based on chapter and vices
    - TTS settings for emotional authenticity
    - Conversation overrides for ElevenLabs API
    """

    def __init__(self, settings: "Settings"):
        """
        Initialize VoiceAgentConfig.

        Args:
            settings: Application settings with ElevenLabs config
        """
        self.settings = settings

    def generate_system_prompt(
        self,
        user_id: UUID,
        chapter: int,
        vices: list,
        user_name: str = "friend",
        relationship_score: float = 50.0,
    ) -> str:
        """
        Generate system prompt for voice conversation.

        AC-T011.1: Includes Nikita persona
        AC-T011.3: Includes chapter behavior modifications
        AC-T011.4: Includes vice preference injection

        Args:
            user_id: User's UUID
            chapter: Current chapter (1-5)
            vices: List of user's vice preferences
            user_name: User's name for personalization
            relationship_score: Current relationship score

        Returns:
            Complete system prompt for voice conversation
        """
        # Start with base persona
        prompt_parts = [BASE_VOICE_PERSONA]

        # Add chapter-specific behavior
        chapter_behavior = CHAPTER_PERSONAS.get(chapter, CHAPTER_PERSONAS[3])
        prompt_parts.append(f"\nCURRENT RELATIONSHIP STATE (Chapter {chapter}):\n")
        prompt_parts.append(chapter_behavior)

        # Add vice-specific adjustments
        if vices:
            prompt_parts.append("\n\nPERSONALITY ADJUSTMENTS:")
            for vice in vices:
                vice_category = getattr(vice, "category", str(vice))
                if vice_category in VICE_VOICE_ADDITIONS:
                    prompt_parts.append(f"\n- {VICE_VOICE_ADDITIONS[vice_category]}")

        # Add user context
        prompt_parts.append(f"\n\nUSER CONTEXT:")
        prompt_parts.append(f"\n- Their name: {user_name}")
        prompt_parts.append(f"\n- Relationship strength: {relationship_score:.0f}%")

        # Add voice-specific reminders
        prompt_parts.append("\n\nREMEMBER:")
        prompt_parts.append("\n- This is a VOICE call, not text. Speak naturally.")
        prompt_parts.append("\n- Your responses will be read aloud - keep them conversational.")
        prompt_parts.append("\n- React to their tone and energy, not just their words.")

        return "".join(prompt_parts)

    def get_agent_config(self, user: "User") -> dict[str, Any]:
        """
        Get complete ElevenLabs agent configuration.

        AC-T011.2: Returns ElevenLabs-compatible config

        Args:
            user: User model with chapter, vices, metrics

        Returns:
            Configuration dict for ElevenLabs API
        """
        # Get vices
        vices = getattr(user, "vice_preferences", []) or []
        primary_vices = sorted(vices, key=lambda v: getattr(v, "intensity_level", 0), reverse=True)[:3]

        # Get relationship score
        relationship_score = 50.0
        if user.metrics:
            relationship_score = getattr(user.metrics, "relationship_score", 50.0)

        # Generate system prompt
        system_prompt = self.generate_system_prompt(
            user_id=user.id,
            chapter=user.chapter,
            vices=primary_vices,
            user_name=getattr(user, "name", "friend") or "friend",
            relationship_score=relationship_score,
        )

        # Get TTS settings for this chapter/mood
        tts_settings = self._get_chapter_tts_settings(user.chapter)

        # Build ElevenLabs conversation_config_override
        config = {
            "agent_id": self.settings.elevenlabs_default_agent_id,
            "conversation_config_override": {
                "agent": {
                    "prompt": {
                        "prompt": system_prompt,
                    },
                    "first_message": self._get_first_message(user.chapter, user.name),
                },
                "tts": {
                    "stability": tts_settings.stability,
                    "similarity_boost": tts_settings.similarity_boost,
                    "speed": tts_settings.speed,
                },
            },
            "dynamic_variables": {
                "user_name": getattr(user, "name", "friend") or "friend",
                "chapter": str(user.chapter),
                "relationship_score": str(int(relationship_score)),
            },
        }

        return config

    def _get_chapter_tts_settings(self, chapter: int) -> TTSSettings:
        """Get TTS settings based on chapter (FR-016). Delegates to tts_config."""
        from nikita.agents.voice.tts_config import get_tts_config_service

        return get_tts_config_service().get_chapter_settings(chapter)

    def _get_first_message(self, chapter: int, user_name: str | None) -> str:
        """Get chapter-appropriate first message. Delegates to audio_tags."""
        from nikita.agents.voice.audio_tags import get_first_message

        return get_first_message(chapter, user_name)
