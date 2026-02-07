"""Tests for Spec 043 T1.3: Outbound voice prompt loading.

Verifies the 3-tier prompt loading chain:
ready_prompt → cached_voice_prompt → static fallback.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


class TestOutboundPromptLoading:
    """T3.3: Outbound voice prompt loading tests."""

    @pytest.fixture
    def mock_settings(self):
        settings = MagicMock()
        settings.elevenlabs_api_key = "test-key"
        settings.elevenlabs_agent_id = "agent-123"
        settings.telegram_webhook_secret = "test-secret"
        settings.is_unified_pipeline_enabled_for_user = MagicMock(return_value=True)
        settings.unified_pipeline_enabled = True
        return settings

    @pytest.fixture
    def service(self, mock_settings):
        from nikita.agents.voice.service import VoiceService

        return VoiceService(settings=mock_settings)

    @pytest.fixture
    def mock_user(self):
        user = MagicMock()
        user.id = uuid4()
        user.game_status = "active"
        user.chapter = 2
        user.relationship_score = 55.0
        user.telegram_id = 12345
        user.cached_voice_prompt = None
        user.cached_voice_prompt_at = None
        return user

    @pytest.mark.asyncio
    async def test_outbound_uses_ready_prompt_when_available(self, service, mock_user):
        """AC-3.3.1: Outbound call uses ready_prompt when available."""
        ready_prompt_text = "You are Nikita, personalized prompt from pipeline"

        mock_record = MagicMock()
        mock_record.prompt_text = ready_prompt_text

        with patch.object(
            service, "_try_load_ready_prompt", return_value=ready_prompt_text
        ), patch.object(
            service, "_load_user", return_value=mock_user
        ), patch.object(
            service, "_load_context", return_value=MagicMock()
        ), patch.object(
            service, "_generate_session_id", return_value="test-session"
        ), patch.object(
            service, "_generate_signed_token", return_value="test-token"
        ), patch.object(
            service, "_log_call_started", return_value=None
        ), patch.object(
            service, "_build_dynamic_variables", return_value=MagicMock()
        ), patch.object(
            service, "_get_tts_settings", return_value=MagicMock(model_dump=lambda: {})
        ), patch.object(
            service, "_get_first_message", return_value="Hey there"
        ):
            result = await service.initiate_call(mock_user.id)

        # Verify the prompt content comes from ready_prompt
        config = result["conversation_config_override"]
        assert config["agent"]["prompt"]["prompt"] == ready_prompt_text
        assert config["_prompt_source"] == "ready_prompt"

    @pytest.mark.asyncio
    async def test_outbound_uses_cached_when_no_ready_prompt(self, service, mock_user):
        """AC-3.3.2: Outbound call uses cached_voice_prompt when no ready_prompt."""
        mock_user.cached_voice_prompt = "Cached voice prompt for user"

        with patch.object(
            service, "_try_load_ready_prompt", return_value=None
        ), patch.object(
            service, "_load_user", return_value=mock_user
        ), patch.object(
            service, "_load_context", return_value=MagicMock()
        ), patch.object(
            service, "_generate_session_id", return_value="test-session"
        ), patch.object(
            service, "_generate_signed_token", return_value="test-token"
        ), patch.object(
            service, "_log_call_started", return_value=None
        ), patch.object(
            service, "_build_dynamic_variables", return_value=MagicMock()
        ), patch.object(
            service, "_get_tts_settings", return_value=MagicMock(model_dump=lambda: {})
        ), patch.object(
            service, "_get_first_message", return_value="Hey there"
        ):
            result = await service.initiate_call(mock_user.id)

        config = result["conversation_config_override"]
        assert config["agent"]["prompt"]["prompt"] == "Cached voice prompt for user"
        assert config["_prompt_source"] == "cached"

    @pytest.mark.asyncio
    async def test_outbound_uses_fallback_when_nothing_cached(self, service, mock_user):
        """AC-3.3.3: Outbound call uses static fallback when nothing cached."""
        mock_user.cached_voice_prompt = None

        fallback_prompt = "Static fallback prompt"

        with patch.object(
            service, "_try_load_ready_prompt", return_value=None
        ), patch.object(
            service, "_load_user", return_value=mock_user
        ), patch.object(
            service, "_load_context", return_value=MagicMock()
        ), patch.object(
            service, "_generate_session_id", return_value="test-session"
        ), patch.object(
            service, "_generate_signed_token", return_value="test-token"
        ), patch.object(
            service, "_log_call_started", return_value=None
        ), patch.object(
            service, "_build_dynamic_variables", return_value=MagicMock()
        ), patch.object(
            service, "_get_tts_settings", return_value=MagicMock(model_dump=lambda: {})
        ), patch.object(
            service, "_get_first_message", return_value="Hey there"
        ), patch.object(
            service, "_generate_fallback_prompt", return_value=fallback_prompt
        ):
            result = await service.initiate_call(mock_user.id)

        config = result["conversation_config_override"]
        assert config["agent"]["prompt"]["prompt"] == fallback_prompt
        assert config["_prompt_source"] == "fallback"
