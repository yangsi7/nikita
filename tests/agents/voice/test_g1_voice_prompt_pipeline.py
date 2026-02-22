"""Tests for G1: Voice Prompt Pipeline Integration (Spec 072).

Verifies ConversationConfigBuilder._generate_system_prompt() loads
pre-built prompts from ready_prompts table first, falling back to
static VoiceAgentConfig when no ready prompt is available.

TDD: Tests written before implementation.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def mock_user(user_id):
    user = MagicMock()
    user.id = user_id
    user.name = "TestUser"
    user.chapter = 3
    user.game_status = "active"
    user.relationship_score = 65.0
    user.metrics = MagicMock()
    user.metrics.relationship_score = 65.0
    user.vice_preferences = []
    return user


@pytest.fixture
def mock_settings_enabled():
    s = MagicMock()
    s.elevenlabs_api_key = "test-key"
    s.elevenlabs_default_agent_id = "test-agent"
    s.elevenlabs_webhook_secret = "test-secret"
    s.unified_pipeline_enabled = True
    s.unified_pipeline_rollout_pct = 100
    s.is_unified_pipeline_enabled_for_user = MagicMock(return_value=True)
    return s


@pytest.fixture
def mock_settings_disabled():
    s = MagicMock()
    s.elevenlabs_api_key = "test-key"
    s.elevenlabs_default_agent_id = "test-agent"
    s.elevenlabs_webhook_secret = "test-secret"
    s.unified_pipeline_enabled = False
    s.is_unified_pipeline_enabled_for_user = MagicMock(return_value=False)
    return s


@pytest.fixture
def mock_ready_prompt():
    return SimpleNamespace(
        prompt_text="You are Nikita. This is the pipeline prompt.",
        token_count=1200,
        pipeline_version="072-v1",
        is_current=True,
        platform="voice",
    )


def _make_config_builder(settings):
    """Create ConversationConfigBuilder with given settings."""
    from nikita.agents.voice.context import ConversationConfigBuilder
    return ConversationConfigBuilder(settings=settings)


def _make_session_context_manager():
    """Create mock async session context manager."""
    mock_session = AsyncMock()
    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_sm = MagicMock(return_value=mock_session_ctx)
    return mock_sm, mock_session


class TestVoicePromptPipelineIntegration:
    """Test _generate_system_prompt uses pipeline prompt when available."""

    @pytest.mark.asyncio
    async def test_uses_ready_prompt_when_flag_enabled(
        self, mock_user, mock_settings_enabled, mock_ready_prompt
    ):
        """When pipeline enabled and ready_prompt exists, use it."""
        mock_repo = AsyncMock()
        mock_repo.get_current = AsyncMock(return_value=mock_ready_prompt)
        mock_sm, _ = _make_session_context_manager()

        builder = _make_config_builder(mock_settings_enabled)

        with (
            patch("nikita.config.settings.get_settings", return_value=mock_settings_enabled),
            patch("nikita.db.repositories.ready_prompt_repository.ReadyPromptRepository", return_value=mock_repo),
            patch("nikita.db.database.get_session_maker", return_value=mock_sm),
        ):
            prompt = await builder._generate_system_prompt(mock_user)

        assert prompt == "You are Nikita. This is the pipeline prompt."

    @pytest.mark.asyncio
    async def test_falls_back_when_no_ready_prompt(
        self, mock_user, mock_settings_enabled
    ):
        """When pipeline enabled but no ready_prompt, fall back to static."""
        mock_repo = AsyncMock()
        mock_repo.get_current = AsyncMock(return_value=None)
        mock_sm, _ = _make_session_context_manager()

        builder = _make_config_builder(mock_settings_enabled)
        fallback_prompt = "STATIC_FALLBACK_PROMPT"

        with (
            patch("nikita.config.settings.get_settings", return_value=mock_settings_enabled),
            patch("nikita.db.repositories.ready_prompt_repository.ReadyPromptRepository", return_value=mock_repo),
            patch("nikita.db.database.get_session_maker", return_value=mock_sm),
            patch.object(builder, "_generate_fallback_prompt", return_value=fallback_prompt),
        ):
            prompt = await builder._generate_system_prompt(mock_user)

        assert prompt == fallback_prompt

    @pytest.mark.asyncio
    async def test_falls_back_when_flag_disabled(
        self, mock_user, mock_settings_disabled
    ):
        """When pipeline disabled, always use fallback (no DB call)."""
        builder = _make_config_builder(mock_settings_disabled)
        fallback_prompt = "STATIC_FALLBACK_PROMPT"

        with (
            patch("nikita.config.settings.get_settings", return_value=mock_settings_disabled),
            patch.object(builder, "_generate_fallback_prompt", return_value=fallback_prompt),
        ):
            prompt = await builder._generate_system_prompt(mock_user)

        assert prompt == fallback_prompt

    @pytest.mark.asyncio
    async def test_exception_falls_back_gracefully(
        self, mock_user, mock_settings_enabled
    ):
        """When DB call raises exception, fall back gracefully to static."""
        mock_repo = AsyncMock()
        mock_repo.get_current = AsyncMock(side_effect=RuntimeError("DB unavailable"))
        mock_sm, _ = _make_session_context_manager()

        builder = _make_config_builder(mock_settings_enabled)
        fallback_prompt = "STATIC_FALLBACK_PROMPT"

        with (
            patch("nikita.config.settings.get_settings", return_value=mock_settings_enabled),
            patch("nikita.db.repositories.ready_prompt_repository.ReadyPromptRepository", return_value=mock_repo),
            patch("nikita.db.database.get_session_maker", return_value=mock_sm),
            patch.object(builder, "_generate_fallback_prompt", return_value=fallback_prompt),
        ):
            prompt = await builder._generate_system_prompt(mock_user)

        assert prompt == fallback_prompt

    @pytest.mark.asyncio
    async def test_uses_voice_platform_key(
        self, mock_user, mock_settings_enabled, mock_ready_prompt
    ):
        """Verifies get_current is called with platform='voice'."""
        mock_repo = AsyncMock()
        mock_repo.get_current = AsyncMock(return_value=mock_ready_prompt)
        mock_sm, _ = _make_session_context_manager()

        builder = _make_config_builder(mock_settings_enabled)

        with (
            patch("nikita.config.settings.get_settings", return_value=mock_settings_enabled),
            patch("nikita.db.repositories.ready_prompt_repository.ReadyPromptRepository", return_value=mock_repo),
            patch("nikita.db.database.get_session_maker", return_value=mock_sm),
        ):
            await builder._generate_system_prompt(mock_user)

        call_args = mock_repo.get_current.call_args[0]
        assert call_args[1] == "voice"

    @pytest.mark.asyncio
    async def test_prompt_source_logged(
        self, mock_user, mock_settings_enabled, mock_ready_prompt, caplog
    ):
        """Verify ready_prompt source is logged."""
        import logging
        mock_repo = AsyncMock()
        mock_repo.get_current = AsyncMock(return_value=mock_ready_prompt)
        mock_sm, _ = _make_session_context_manager()

        builder = _make_config_builder(mock_settings_enabled)

        with (
            patch("nikita.config.settings.get_settings", return_value=mock_settings_enabled),
            patch("nikita.db.repositories.ready_prompt_repository.ReadyPromptRepository", return_value=mock_repo),
            patch("nikita.db.database.get_session_maker", return_value=mock_sm),
            caplog.at_level(logging.INFO),
        ):
            await builder._generate_system_prompt(mock_user)

        assert any("ready_prompt" in record.message.lower() for record in caplog.records)
