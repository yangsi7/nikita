"""Tests for VoiceAgentConfig (US-2: Natural Conversation).

Tests for T010, T011 acceptance criteria:
- AC-T011.1: generate_system_prompt includes Nikita persona
- AC-T011.2: get_agent_config returns ElevenLabs-compatible config
- AC-T011.3: Includes chapter behavior modifications
- AC-T011.4: Includes vice preference injection
"""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest


class TestVoiceAgentConfig:
    """Test VoiceAgentConfig - T010, T011."""

    @pytest.fixture
    def mock_user(self):
        """Create a mock user for testing."""
        user = MagicMock()
        user.id = uuid4()
        user.name = "TestUser"
        user.chapter = 3
        user.game_status = "active"
        user.engagement_state = "IN_ZONE"
        user.metrics = MagicMock()
        user.metrics.relationship_score = 65.0
        user.vice_preferences = []
        return user

    @pytest.fixture
    def mock_vice(self):
        """Create a mock vice preference."""
        vice = MagicMock()
        vice.vice_category = "dark_humor"
        vice.is_primary = True
        vice.severity = 3
        return vice

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.elevenlabs_api_key = "test_api_key"
        settings.elevenlabs_default_agent_id = "test_agent_id"
        settings.elevenlabs_default_voice_id = "nikita_voice_id"
        return settings

    def test_generate_system_prompt_includes_persona(self, mock_user, mock_settings):
        """AC-T011.1: generate_system_prompt includes Nikita persona."""
        from nikita.agents.voice.config import VoiceAgentConfig

        config = VoiceAgentConfig(settings=mock_settings)
        prompt = config.generate_system_prompt(
            user_id=mock_user.id,
            chapter=mock_user.chapter,
            vices=[],
        )

        assert prompt is not None
        assert len(prompt) > 100  # Should have substantial content
        assert "Nikita" in prompt  # Should mention Nikita
        # Should include voice-specific guidance
        assert any(
            keyword in prompt.lower()
            for keyword in ["voice", "speak", "conversation", "call"]
        )

    def test_generate_system_prompt_chapter_behavior(self, mock_user, mock_settings):
        """AC-T011.3: Includes chapter behavior modifications."""
        from nikita.agents.voice.config import VoiceAgentConfig

        config = VoiceAgentConfig(settings=mock_settings)

        # Chapter 1 - distant/guarded
        prompt_ch1 = config.generate_system_prompt(
            user_id=mock_user.id,
            chapter=1,
            vices=[],
        )

        # Chapter 5 - intimate/trusting
        prompt_ch5 = config.generate_system_prompt(
            user_id=mock_user.id,
            chapter=5,
            vices=[],
        )

        # Prompts should be different based on chapter
        assert prompt_ch1 != prompt_ch5

    def test_generate_system_prompt_vice_injection(
        self, mock_user, mock_vice, mock_settings
    ):
        """AC-T011.4: Includes vice preference injection."""
        from nikita.agents.voice.config import VoiceAgentConfig

        config = VoiceAgentConfig(settings=mock_settings)

        # With vice
        prompt_with_vice = config.generate_system_prompt(
            user_id=mock_user.id,
            chapter=3,
            vices=[mock_vice],
        )

        # Without vice
        prompt_no_vice = config.generate_system_prompt(
            user_id=mock_user.id,
            chapter=3,
            vices=[],
        )

        # Vice injection should modify the prompt
        assert prompt_with_vice != prompt_no_vice
        # Should mention the vice category
        assert "dark_humor" in prompt_with_vice.lower() or "humor" in prompt_with_vice.lower()

    def test_get_agent_config_returns_elevenlabs_format(
        self, mock_user, mock_settings
    ):
        """AC-T011.2: get_agent_config returns ElevenLabs-compatible config."""
        from nikita.agents.voice.config import VoiceAgentConfig

        config = VoiceAgentConfig(settings=mock_settings)
        agent_config = config.get_agent_config(user=mock_user)

        # Should have required ElevenLabs fields
        assert "agent_id" in agent_config
        assert "conversation_config_override" in agent_config

        # Conversation override should have required fields
        override = agent_config["conversation_config_override"]
        assert "agent" in override or "tts" in override or "asr" in override

    def test_get_agent_config_includes_dynamic_variables(
        self, mock_user, mock_settings
    ):
        """Agent config should include dynamic variables for prompt interpolation."""
        from nikita.agents.voice.config import VoiceAgentConfig

        config = VoiceAgentConfig(settings=mock_settings)
        agent_config = config.get_agent_config(user=mock_user)

        # Should have dynamic variables section
        override = agent_config["conversation_config_override"]
        if "agent" in override:
            agent_override = override["agent"]
            # Check for prompt override or dynamic variables
            assert (
                "prompt" in agent_override
                or "dynamic_variables" in agent_config
            )

    def test_get_agent_config_tts_settings_by_chapter(
        self, mock_user, mock_settings
    ):
        """TTS settings should vary by chapter (FR-016)."""
        from nikita.agents.voice.config import VoiceAgentConfig

        config = VoiceAgentConfig(settings=mock_settings)

        # Chapter 1 (distant)
        mock_user.chapter = 1
        config_ch1 = config.get_agent_config(user=mock_user)

        # Chapter 5 (intimate)
        mock_user.chapter = 5
        config_ch5 = config.get_agent_config(user=mock_user)

        # TTS settings should differ by chapter
        override1 = config_ch1["conversation_config_override"]
        override5 = config_ch5["conversation_config_override"]

        if "tts" in override1 and "tts" in override5:
            assert override1["tts"] != override5["tts"]
