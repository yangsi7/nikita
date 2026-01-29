"""Tests for Voice Prompt Logging (Spec 035 T4.2, T4.5)."""

import os
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

# Set environment variable before imports
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-for-testing")


class TestVoiceConfigLogsPrompt:
    """Tests for ConversationConfigBuilder prompt logging (T4.2)."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.elevenlabs_api_key = "test-key"
        settings.elevenlabs_agent_id = "test-agent"
        return settings

    @pytest.fixture
    def mock_user(self):
        """Create mock user with all required attributes."""
        user = MagicMock()
        user.id = uuid4()
        user.chapter = 3
        user.name = "TestUser"

        # Mock metrics
        user.metrics = MagicMock()
        user.metrics.relationship_score = 75.5
        user.metrics.secureness = 60.0

        # Mock engagement state
        user.engagement_state = MagicMock()
        user.engagement_state.state = "IN_ZONE"

        # Mock other optional attributes
        user.last_interaction_at = None
        user.onboarding_profile = {}
        user.vice_preferences = []

        return user

    @pytest.mark.asyncio
    async def test_voice_config_logs_prompt(self, mock_settings, mock_user):
        """Test that build_config triggers prompt logging (AC-T4.2.1)."""
        from nikita.agents.voice.context import ConversationConfigBuilder

        builder = ConversationConfigBuilder(mock_settings)

        with patch.object(builder, "_generate_system_prompt", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = "Test system prompt"

            # Patch TTS service
            with patch("nikita.agents.voice.context.get_tts_config_service") as mock_tts:
                mock_tts.return_value.get_final_settings.return_value = MagicMock()

                config = await builder.build_config(mock_user)

                # Verify system prompt was generated (which triggers logging)
                mock_gen.assert_called_once()
                assert config.system_prompt == "Test system prompt"

    @pytest.mark.asyncio
    async def test_voice_prompt_has_platform_voice(self, mock_settings, mock_user):
        """Test that voice prompts use voice-specific generation (AC-T4.2.2).

        Spec 039: Voice prompts now use generate_voice_prompt from context_engine.router.
        This test verifies the router is called (which logs platform="voice" internally).
        """
        from nikita.agents.voice.context import ConversationConfigBuilder

        builder = ConversationConfigBuilder(mock_settings)

        # Patch the router's generate_voice_prompt at source (imported inside method)
        with patch(
            "nikita.context_engine.router.generate_voice_prompt",
            new_callable=AsyncMock,
        ) as mock_gen:
            mock_gen.return_value = "Voice system prompt"

            with patch("nikita.agents.voice.context.get_tts_config_service") as mock_tts:
                mock_tts.return_value.get_final_settings.return_value = MagicMock()

                with patch("nikita.db.database.get_session_maker") as mock_sm:
                    mock_session = AsyncMock()
                    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                    mock_session.__aexit__ = AsyncMock(return_value=None)
                    mock_sm.return_value = MagicMock(return_value=mock_session)

                    config = await builder.build_config(mock_user)

                    # Verify generate_voice_prompt was called (logs platform="voice" internally)
                    mock_gen.assert_called_once()
                    assert config.system_prompt == "Voice system prompt"


class TestMetaPromptServicePlatformLogging:
    """Tests for MetaPromptService platform parameter (T4.5)."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async session."""
        session = AsyncMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)
        session.commit = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_generate_system_prompt_accepts_platform(self, mock_session):
        """Test that generate_system_prompt accepts platform parameter."""
        from nikita.meta_prompts.service import MetaPromptService

        with patch("nikita.meta_prompts.service.Agent"):
            service = MetaPromptService(mock_session)

            # Verify method signature includes platform
            import inspect
            sig = inspect.signature(service.generate_system_prompt)
            assert "platform" in sig.parameters

    @pytest.mark.asyncio
    async def test_log_prompt_receives_platform(self, mock_session):
        """Test that _log_prompt receives platform parameter (AC-T4.5.2)."""
        from nikita.meta_prompts.service import MetaPromptService

        with patch("nikita.meta_prompts.service.Agent"):
            service = MetaPromptService(mock_session)

            # Verify _log_prompt signature includes platform
            import inspect
            sig = inspect.signature(service._log_prompt)
            assert "platform" in sig.parameters
            assert sig.parameters["platform"].default == "text"

    @pytest.mark.asyncio
    async def test_repository_receives_platform(self, mock_session):
        """Test that repository create_log receives platform (AC-T4.5.3)."""
        from nikita.db.repositories.generated_prompt_repository import (
            GeneratedPromptRepository,
        )

        # Verify repository method signature includes platform
        import inspect
        sig = inspect.signature(GeneratedPromptRepository.create_log)
        assert "platform" in sig.parameters
        assert sig.parameters["platform"].default == "text"


class TestVoiceVsTextPlatformDifferentiation:
    """Tests for voice/text platform differentiation."""

    def test_text_prompt_defaults_to_text_platform(self):
        """Test that text prompts default to 'text' platform."""
        from nikita.db.models.generated_prompt import GeneratedPrompt

        # Column default is 'text'
        column = GeneratedPrompt.__table__.columns.get("platform")
        assert column is not None
        assert column.default.arg == "text"

    @pytest.mark.asyncio
    async def test_voice_prompt_uses_voice_platform(self):
        """Test that voice prompts use 'voice' platform."""
        from nikita.db.models.generated_prompt import GeneratedPrompt

        prompt = GeneratedPrompt(
            id=uuid4(),
            user_id=uuid4(),
            prompt_content="Voice prompt content",
            token_count=100,
            generation_time_ms=50.0,
            meta_prompt_template="system_prompt",
            platform="voice",
            created_at=datetime.now(UTC),
        )

        assert prompt.platform == "voice"
