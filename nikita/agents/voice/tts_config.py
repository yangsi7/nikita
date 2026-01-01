"""TTS configuration service for voice agent (FR-016, FR-017).

This module provides chapter-based and mood-based TTS settings for
ElevenLabs voice synthesis, implementing emotional voice expression.

Implements US-11 acceptance criteria:
- AC-FR016-001: Ch1 → stability=0.8, speed=0.95 (distant)
- AC-FR016-002: Ch5 → stability=0.4-0.5 (expressive)
- AC-FR017-001: Annoyed → speed=1.1, stability=0.4
- AC-FR017-002: Vulnerable → speed=0.9, stability=0.7
"""

import logging
from typing import TYPE_CHECKING

from nikita.agents.voice.models import NikitaMood, TTSSettings

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# =============================================================================
# CHAPTER-BASED TTS SETTINGS (FR-016)
# =============================================================================

CHAPTER_TTS_SETTINGS: dict[int, TTSSettings] = {
    # Chapter 1: Distant, guarded - high stability, slower pace
    1: TTSSettings(stability=0.8, similarity_boost=0.7, speed=0.95),
    # Chapter 2: Warming up - slightly more expressive
    2: TTSSettings(stability=0.7, similarity_boost=0.75, speed=0.98),
    # Chapter 3: Comfortable - balanced, natural
    3: TTSSettings(stability=0.6, similarity_boost=0.8, speed=1.0),
    # Chapter 4: Intimate - more emotional variation
    4: TTSSettings(stability=0.5, similarity_boost=0.82, speed=1.0),
    # Chapter 5: Full expression - low stability for emotional range
    5: TTSSettings(stability=0.4, similarity_boost=0.85, speed=1.02),
}

# Default settings (chapter 3)
DEFAULT_TTS_SETTINGS = CHAPTER_TTS_SETTINGS[3]


# =============================================================================
# MOOD-BASED TTS MODULATION (FR-017)
# =============================================================================

MOOD_TTS_SETTINGS: dict[NikitaMood, TTSSettings] = {
    # Flirty: Moderate speed, expressive
    NikitaMood.FLIRTY: TTSSettings(stability=0.5, similarity_boost=0.8, speed=1.0),
    # Vulnerable: Slower, more stable (careful, emotional)
    NikitaMood.VULNERABLE: TTSSettings(stability=0.7, similarity_boost=0.9, speed=0.9),
    # Annoyed: Faster, less stable (snappy, irritated)
    NikitaMood.ANNOYED: TTSSettings(stability=0.4, similarity_boost=0.7, speed=1.1),
    # Playful: Faster, expressive (upbeat, fun)
    NikitaMood.PLAYFUL: TTSSettings(stability=0.4, similarity_boost=0.8, speed=1.1),
    # Distant: Slower, very stable (controlled, aloof)
    NikitaMood.DISTANT: TTSSettings(stability=0.8, similarity_boost=0.9, speed=0.95),
    # Neutral: Balanced (default conversational)
    NikitaMood.NEUTRAL: TTSSettings(stability=0.6, similarity_boost=0.8, speed=1.0),
}


class TTSConfigService:
    """Service for generating TTS settings based on context.

    Provides chapter-based defaults with mood-based overrides for
    emotionally authentic voice synthesis.
    """

    def __init__(self):
        """Initialize TTS config service."""
        self._chapter_settings = CHAPTER_TTS_SETTINGS
        self._mood_settings = MOOD_TTS_SETTINGS

    def get_chapter_settings(self, chapter: int) -> TTSSettings:
        """Get TTS settings for a chapter (FR-016).

        Args:
            chapter: Chapter number (1-5)

        Returns:
            TTSSettings for the chapter, defaults to chapter 3 if invalid
        """
        return self._chapter_settings.get(chapter, DEFAULT_TTS_SETTINGS)

    def get_mood_modulation(self, mood: NikitaMood) -> TTSSettings:
        """Get TTS settings for a mood (FR-017).

        Args:
            mood: Nikita's current mood

        Returns:
            TTSSettings for the mood
        """
        return self._mood_settings.get(mood, MOOD_TTS_SETTINGS[NikitaMood.NEUTRAL])

    def get_final_settings(
        self,
        chapter: int,
        mood: NikitaMood | None = None,
    ) -> TTSSettings:
        """Get final TTS settings combining chapter and mood.

        Mood overrides chapter settings when specified and non-neutral.
        For neutral mood, blends chapter and mood settings.

        Args:
            chapter: Chapter number (1-5)
            mood: Optional mood override

        Returns:
            Final TTSSettings for voice synthesis
        """
        chapter_settings = self.get_chapter_settings(chapter)

        # If no mood specified, use chapter settings
        if mood is None:
            return chapter_settings

        mood_settings = self.get_mood_modulation(mood)

        # For neutral mood, blend with chapter settings
        if mood == NikitaMood.NEUTRAL:
            return self._blend_settings(chapter_settings, mood_settings)

        # Mood overrides chapter for non-neutral moods
        return mood_settings

    def _blend_settings(
        self,
        primary: TTSSettings,
        secondary: TTSSettings,
        weight: float = 0.5,
    ) -> TTSSettings:
        """Blend two TTS settings with weighted average.

        Args:
            primary: Primary settings (higher weight)
            secondary: Secondary settings (lower weight)
            weight: Weight for primary (0-1), secondary gets 1-weight

        Returns:
            Blended TTSSettings
        """
        return TTSSettings(
            stability=round(
                primary.stability * weight + secondary.stability * (1 - weight), 2
            ),
            similarity_boost=round(
                primary.similarity_boost * weight
                + secondary.similarity_boost * (1 - weight),
                2,
            ),
            speed=round(
                primary.speed * weight + secondary.speed * (1 - weight), 2
            ),
        )


# Singleton instance
_tts_config_service: TTSConfigService | None = None


def get_tts_config_service() -> TTSConfigService:
    """Get singleton TTS config service instance."""
    global _tts_config_service
    if _tts_config_service is None:
        _tts_config_service = TTSConfigService()
    return _tts_config_service
