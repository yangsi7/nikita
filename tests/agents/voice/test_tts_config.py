"""Tests for TTS configuration (US-11: Emotional Voice Expression).

Tests for T058-T061 acceptance criteria (V3 Conversational):
- AC-FR016-001: Ch1 user calls → stability=0.55, speed=0.92 (distant but responsive)
- AC-FR016-002: Ch5 user calls → stability=0.35 (fully expressive for audio tags)
- AC-FR017-001: Nikita annoyed → speed=1.1, stability=0.30
- AC-FR017-002: Nikita vulnerable → speed=0.9, stability=0.52
"""

import pytest

from nikita.agents.voice.models import NikitaMood, TTSSettings


class TestTTSConfigChapterBased:
    """Test chapter-based TTS settings (FR-016)."""

    def test_chapter_1_distant_voice(self):
        """AC-FR016-001: Ch1 → stability=0.55, speed=0.92 (distant but V3-responsive)."""
        from nikita.agents.voice.tts_config import TTSConfigService

        service = TTSConfigService()
        settings = service.get_chapter_settings(chapter=1)

        assert settings.stability == 0.55
        assert settings.speed == 0.92
        assert settings.similarity_boost == 0.70

    def test_chapter_2_warming_voice(self):
        """Ch2 → slightly more expressive, warming up."""
        from nikita.agents.voice.tts_config import TTSConfigService

        service = TTSConfigService()
        settings = service.get_chapter_settings(chapter=2)

        assert settings.stability == 0.48
        assert settings.speed == 0.95
        assert settings.similarity_boost == 0.75

    def test_chapter_3_comfortable_voice(self):
        """Ch3 → natural range, comfortable expression."""
        from nikita.agents.voice.tts_config import TTSConfigService

        service = TTSConfigService()
        settings = service.get_chapter_settings(chapter=3)

        assert settings.stability == 0.42
        assert settings.speed == 0.98
        assert settings.similarity_boost == 0.80

    def test_chapter_4_intimate_voice(self):
        """Ch4 → more emotional variation, intimate."""
        from nikita.agents.voice.tts_config import TTSConfigService

        service = TTSConfigService()
        settings = service.get_chapter_settings(chapter=4)

        assert settings.stability == 0.38
        assert settings.speed == 0.98
        assert settings.similarity_boost == 0.82

    def test_chapter_5_expressive_voice(self):
        """AC-FR016-002: Ch5 → stability=0.35 (fully expressive for audio tags)."""
        from nikita.agents.voice.tts_config import TTSConfigService

        service = TTSConfigService()
        settings = service.get_chapter_settings(chapter=5)

        assert settings.stability == 0.35
        assert settings.speed == 1.00
        assert settings.similarity_boost == 0.85

    def test_invalid_chapter_defaults_to_3(self):
        """Invalid chapter falls back to chapter 3 defaults."""
        from nikita.agents.voice.tts_config import TTSConfigService

        service = TTSConfigService()
        settings = service.get_chapter_settings(chapter=99)

        assert settings.stability == 0.42  # Ch3 default
        assert settings.speed == 0.98


class TestTTSConfigMoodBased:
    """Test mood-based TTS modulation (FR-017)."""

    def test_annoyed_mood_fast_unstable(self):
        """AC-FR017-001: Annoyed → speed=1.1, stability=0.30."""
        from nikita.agents.voice.tts_config import TTSConfigService

        service = TTSConfigService()
        settings = service.get_mood_modulation(mood=NikitaMood.ANNOYED)

        assert settings.speed == 1.1
        assert settings.stability == 0.30
        assert settings.similarity_boost == 0.7

    def test_vulnerable_mood_slow_stable(self):
        """AC-FR017-002: Vulnerable → speed=0.9, stability=0.52."""
        from nikita.agents.voice.tts_config import TTSConfigService

        service = TTSConfigService()
        settings = service.get_mood_modulation(mood=NikitaMood.VULNERABLE)

        assert settings.speed == 0.9
        assert settings.stability == 0.52
        assert settings.similarity_boost == 0.9

    def test_flirty_mood_medium_expressive(self):
        """Flirty → moderate speed, lower stability for V3 expressiveness."""
        from nikita.agents.voice.tts_config import TTSConfigService

        service = TTSConfigService()
        settings = service.get_mood_modulation(mood=NikitaMood.FLIRTY)

        assert settings.speed == 1.0
        assert settings.stability == 0.40
        assert settings.similarity_boost == 0.8

    def test_playful_mood_upbeat(self):
        """Playful → slightly faster, lower stability for V3."""
        from nikita.agents.voice.tts_config import TTSConfigService

        service = TTSConfigService()
        settings = service.get_mood_modulation(mood=NikitaMood.PLAYFUL)

        assert settings.speed == 1.1
        assert settings.stability == 0.32
        assert settings.similarity_boost == 0.8

    def test_distant_mood_controlled(self):
        """Distant → slower, higher stability (but V3-lowered)."""
        from nikita.agents.voice.tts_config import TTSConfigService

        service = TTSConfigService()
        settings = service.get_mood_modulation(mood=NikitaMood.DISTANT)

        assert settings.speed == 0.95
        assert settings.stability == 0.58
        assert settings.similarity_boost == 0.9

    def test_neutral_mood_balanced(self):
        """Neutral → balanced V3 settings."""
        from nikita.agents.voice.tts_config import TTSConfigService

        service = TTSConfigService()
        settings = service.get_mood_modulation(mood=NikitaMood.NEUTRAL)

        assert settings.speed == 1.0
        assert settings.stability == 0.45
        assert settings.similarity_boost == 0.8


class TestTTSConfigCombined:
    """Test combined chapter + mood settings."""

    def test_get_final_settings_mood_overrides_chapter(self):
        """Mood should override chapter settings when specified."""
        from nikita.agents.voice.tts_config import TTSConfigService

        service = TTSConfigService()

        # Ch1 normally has stability=0.55, but annoyed mood overrides
        settings = service.get_final_settings(
            chapter=1, mood=NikitaMood.ANNOYED
        )

        # Mood takes priority
        assert settings.stability == 0.30  # Annoyed, not chapter 1
        assert settings.speed == 1.1  # Annoyed speed

    def test_get_final_settings_no_mood_uses_chapter(self):
        """Without mood, use chapter settings."""
        from nikita.agents.voice.tts_config import TTSConfigService

        service = TTSConfigService()
        settings = service.get_final_settings(chapter=5, mood=None)

        assert settings.stability == 0.35  # Ch5 settings
        assert settings.speed == 1.00

    def test_get_final_settings_neutral_mood_uses_chapter(self):
        """Neutral mood uses chapter settings as base."""
        from nikita.agents.voice.tts_config import TTSConfigService

        service = TTSConfigService()

        # With neutral mood, should blend with chapter
        settings = service.get_final_settings(
            chapter=5, mood=NikitaMood.NEUTRAL
        )

        # Neutral mood should blend, not completely override
        # Expecting some combination of ch5 expressive + neutral balanced
        assert 0.35 <= settings.stability <= 0.45
        assert 1.0 <= settings.speed <= 1.00

    def test_tts_settings_within_bounds(self):
        """All TTS settings should be within ElevenLabs bounds."""
        from nikita.agents.voice.tts_config import TTSConfigService

        service = TTSConfigService()

        for chapter in range(1, 6):
            for mood in NikitaMood:
                settings = service.get_final_settings(chapter=chapter, mood=mood)

                assert 0.0 <= settings.stability <= 1.0
                assert 0.0 <= settings.similarity_boost <= 1.0
                assert 0.7 <= settings.speed <= 1.2
