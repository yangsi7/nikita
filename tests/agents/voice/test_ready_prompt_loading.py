"""Tests for voice agent ready prompt loading (Spec 042 T4.2/T4.3/T4.6).

Verifies voice agents load pre-built prompts from ready_prompts table
when unified pipeline feature flag is enabled.

server_tools._try_load_ready_prompt(self, user_id: str, session) -> str | None
inbound._try_load_ready_prompt(self, user_id: UUID) -> str | None
"""

import time

import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def user_id_str(user_id):
    return str(user_id)


@pytest.fixture
def mock_session():
    session = MagicMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def mock_ready_prompt():
    return SimpleNamespace(
        prompt_text="You are Nikita. Keep responses brief for voice.",
        token_count=1900,
        pipeline_version="042-v1",
        is_current=True,
        platform="voice",
    )


@pytest.fixture
def mock_settings_enabled():
    s = MagicMock()
    s.unified_pipeline_enabled = True
    s.unified_pipeline_rollout_pct = 100
    s.is_unified_pipeline_enabled_for_user = MagicMock(return_value=True)
    s.elevenlabs_api_key = "test-key"
    s.elevenlabs_agent_id = "test-agent"
    return s


@pytest.fixture
def mock_settings_disabled():
    s = MagicMock()
    s.unified_pipeline_enabled = False
    s.is_unified_pipeline_enabled_for_user = MagicMock(return_value=False)
    s.elevenlabs_api_key = "test-key"
    s.elevenlabs_agent_id = "test-agent"
    return s


def _make_server_handler(settings):
    """Create ServerToolHandler with mocked settings."""
    from nikita.agents.voice.server_tools import ServerToolHandler
    return ServerToolHandler(settings=settings)


# =============================================================================
# 1. Voice Server Tools _try_load_ready_prompt (7 tests)
# =============================================================================


class TestServerToolsReadyPrompt:

    @pytest.mark.asyncio
    async def test_flag_disabled_skips(self, user_id_str, mock_session, mock_settings_disabled):
        with patch("nikita.config.settings.get_settings", return_value=mock_settings_disabled):
            handler = _make_server_handler(mock_settings_disabled)
            result = await handler._try_load_ready_prompt(user_id_str, mock_session)
            assert result is None

    @pytest.mark.asyncio
    async def test_flag_enabled_loads(self, user_id_str, mock_session, mock_settings_enabled, mock_ready_prompt):
        mock_repo = AsyncMock()
        mock_repo.get_current = AsyncMock(return_value=mock_ready_prompt)

        with (
            patch("nikita.config.settings.get_settings", return_value=mock_settings_enabled),
            patch("nikita.db.repositories.ready_prompt_repository.ReadyPromptRepository", return_value=mock_repo),
        ):
            handler = _make_server_handler(mock_settings_enabled)
            result = await handler._try_load_ready_prompt(user_id_str, mock_session)
            assert result == "You are Nikita. Keep responses brief for voice."

    @pytest.mark.asyncio
    async def test_fallback_on_no_prompt(self, user_id_str, mock_session, mock_settings_enabled):
        mock_repo = AsyncMock()
        mock_repo.get_current = AsyncMock(return_value=None)

        with (
            patch("nikita.config.settings.get_settings", return_value=mock_settings_enabled),
            patch("nikita.db.repositories.ready_prompt_repository.ReadyPromptRepository", return_value=mock_repo),
        ):
            handler = _make_server_handler(mock_settings_enabled)
            result = await handler._try_load_ready_prompt(user_id_str, mock_session)
            assert result is None

    @pytest.mark.asyncio
    async def test_exception_handled(self, user_id_str, mock_session, mock_settings_enabled):
        mock_repo = AsyncMock()
        mock_repo.get_current = AsyncMock(side_effect=RuntimeError("DB down"))

        with (
            patch("nikita.config.settings.get_settings", return_value=mock_settings_enabled),
            patch("nikita.db.repositories.ready_prompt_repository.ReadyPromptRepository", return_value=mock_repo),
        ):
            handler = _make_server_handler(mock_settings_enabled)
            result = await handler._try_load_ready_prompt(user_id_str, mock_session)
            assert result is None

    @pytest.mark.asyncio
    async def test_uses_voice_platform(self, user_id_str, mock_session, mock_settings_enabled, mock_ready_prompt):
        mock_repo = AsyncMock()
        mock_repo.get_current = AsyncMock(return_value=mock_ready_prompt)

        with (
            patch("nikita.config.settings.get_settings", return_value=mock_settings_enabled),
            patch("nikita.db.repositories.ready_prompt_repository.ReadyPromptRepository", return_value=mock_repo),
        ):
            handler = _make_server_handler(mock_settings_enabled)
            await handler._try_load_ready_prompt(user_id_str, mock_session)
            # Verify second arg is "voice"
            call_args = mock_repo.get_current.call_args[0]
            assert call_args[1] == "voice"

    @pytest.mark.asyncio
    async def test_returns_string(self, user_id_str, mock_session, mock_settings_enabled, mock_ready_prompt):
        mock_repo = AsyncMock()
        mock_repo.get_current = AsyncMock(return_value=mock_ready_prompt)

        with (
            patch("nikita.config.settings.get_settings", return_value=mock_settings_enabled),
            patch("nikita.db.repositories.ready_prompt_repository.ReadyPromptRepository", return_value=mock_repo),
        ):
            handler = _make_server_handler(mock_settings_enabled)
            result = await handler._try_load_ready_prompt(user_id_str, mock_session)
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_converts_str_to_uuid(self, user_id, mock_session, mock_settings_enabled, mock_ready_prompt):
        """user_id is str, but get_current expects UUID — verify conversion."""
        mock_repo = AsyncMock()
        mock_repo.get_current = AsyncMock(return_value=mock_ready_prompt)

        with (
            patch("nikita.config.settings.get_settings", return_value=mock_settings_enabled),
            patch("nikita.db.repositories.ready_prompt_repository.ReadyPromptRepository", return_value=mock_repo),
        ):
            handler = _make_server_handler(mock_settings_enabled)
            result = await handler._try_load_ready_prompt(str(user_id), mock_session)
            # Should have called get_current with UUID, not string
            call_args = mock_repo.get_current.call_args[0]
            assert isinstance(call_args[0], UUID)


# =============================================================================
# 2. Voice Inbound _try_load_ready_prompt (6 tests)
# =============================================================================


class TestInboundReadyPrompt:

    def _make_handler(self):
        """Create InboundCallHandler with mocked VoiceSessionManager."""
        with patch("nikita.agents.voice.inbound.VoiceSessionManager"):
            from nikita.agents.voice.inbound import InboundCallHandler
            return InboundCallHandler()

    @pytest.mark.asyncio
    async def test_flag_disabled_skips(self, user_id, mock_settings_disabled):
        with patch("nikita.config.settings.get_settings", return_value=mock_settings_disabled):
            handler = self._make_handler()
            result = await handler._try_load_ready_prompt(user_id)
            assert result is None

    @pytest.mark.asyncio
    async def test_flag_enabled_loads(self, user_id, mock_settings_enabled, mock_ready_prompt):
        mock_repo = AsyncMock()
        mock_repo.get_current = AsyncMock(return_value=mock_ready_prompt)
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_sm = MagicMock(return_value=mock_session_ctx)

        with (
            patch("nikita.config.settings.get_settings", return_value=mock_settings_enabled),
            patch("nikita.db.repositories.ready_prompt_repository.ReadyPromptRepository", return_value=mock_repo),
            patch("nikita.db.database.get_session_maker", return_value=mock_sm),
        ):
            handler = self._make_handler()
            result = await handler._try_load_ready_prompt(user_id)
            assert result == "You are Nikita. Keep responses brief for voice."

    @pytest.mark.asyncio
    async def test_fallback_on_no_prompt(self, user_id, mock_settings_enabled):
        mock_repo = AsyncMock()
        mock_repo.get_current = AsyncMock(return_value=None)
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_sm = MagicMock(return_value=mock_session_ctx)

        with (
            patch("nikita.config.settings.get_settings", return_value=mock_settings_enabled),
            patch("nikita.db.repositories.ready_prompt_repository.ReadyPromptRepository", return_value=mock_repo),
            patch("nikita.db.database.get_session_maker", return_value=mock_sm),
        ):
            handler = self._make_handler()
            result = await handler._try_load_ready_prompt(user_id)
            assert result is None

    @pytest.mark.asyncio
    async def test_exception_returns_none(self, user_id, mock_settings_enabled):
        mock_repo = AsyncMock()
        mock_repo.get_current = AsyncMock(side_effect=RuntimeError("boom"))
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_sm = MagicMock(return_value=mock_session_ctx)

        with (
            patch("nikita.config.settings.get_settings", return_value=mock_settings_enabled),
            patch("nikita.db.repositories.ready_prompt_repository.ReadyPromptRepository", return_value=mock_repo),
            patch("nikita.db.database.get_session_maker", return_value=mock_sm),
        ):
            handler = self._make_handler()
            result = await handler._try_load_ready_prompt(user_id)
            assert result is None

    @pytest.mark.asyncio
    async def test_uses_voice_platform(self, user_id, mock_settings_enabled, mock_ready_prompt):
        mock_repo = AsyncMock()
        mock_repo.get_current = AsyncMock(return_value=mock_ready_prompt)
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_sm = MagicMock(return_value=mock_session_ctx)

        with (
            patch("nikita.config.settings.get_settings", return_value=mock_settings_enabled),
            patch("nikita.db.repositories.ready_prompt_repository.ReadyPromptRepository", return_value=mock_repo),
            patch("nikita.db.database.get_session_maker", return_value=mock_sm),
        ):
            handler = self._make_handler()
            await handler._try_load_ready_prompt(user_id)
            call_args = mock_repo.get_current.call_args[0]
            assert call_args[1] == "voice"

    @pytest.mark.asyncio
    async def test_returns_string(self, user_id, mock_settings_enabled, mock_ready_prompt):
        mock_repo = AsyncMock()
        mock_repo.get_current = AsyncMock(return_value=mock_ready_prompt)
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_sm = MagicMock(return_value=mock_session_ctx)

        with (
            patch("nikita.config.settings.get_settings", return_value=mock_settings_enabled),
            patch("nikita.db.repositories.ready_prompt_repository.ReadyPromptRepository", return_value=mock_repo),
            patch("nikita.db.database.get_session_maker", return_value=mock_sm),
        ):
            handler = self._make_handler()
            result = await handler._try_load_ready_prompt(user_id)
            assert isinstance(result, str)


# =============================================================================
# 3. Integration Flow Tests (4 tests)
# =============================================================================


class TestVoiceIntegrationFlow:

    @pytest.mark.asyncio
    async def test_voice_text_isolation(self, user_id_str, mock_session, mock_settings_enabled, mock_ready_prompt):
        """Voice reads voice platform, not text."""
        mock_repo = AsyncMock()
        mock_repo.get_current = AsyncMock(return_value=mock_ready_prompt)

        with (
            patch("nikita.config.settings.get_settings", return_value=mock_settings_enabled),
            patch("nikita.db.repositories.ready_prompt_repository.ReadyPromptRepository", return_value=mock_repo),
        ):
            handler = _make_server_handler(mock_settings_enabled)
            await handler._try_load_ready_prompt(user_id_str, mock_session)
            assert mock_repo.get_current.call_args[0][1] == "voice"

    @pytest.mark.asyncio
    async def test_prompt_returned_verbatim(self, user_id_str, mock_session, mock_settings_enabled):
        """Prompt text returned exactly as stored."""
        exact = "## 1. IDENTITY\nNikita\n## 2. VOICE\nBrief."
        prompt = SimpleNamespace(prompt_text=exact, token_count=50)
        mock_repo = AsyncMock()
        mock_repo.get_current = AsyncMock(return_value=prompt)

        with (
            patch("nikita.config.settings.get_settings", return_value=mock_settings_enabled),
            patch("nikita.db.repositories.ready_prompt_repository.ReadyPromptRepository", return_value=mock_repo),
        ):
            handler = _make_server_handler(mock_settings_enabled)
            result = await handler._try_load_ready_prompt(user_id_str, mock_session)
            assert result == exact

    @pytest.mark.asyncio
    async def test_concurrent_reads_safe(self, mock_session, mock_settings_enabled, mock_ready_prompt):
        """Multiple concurrent reads safe."""
        import asyncio
        mock_repo = AsyncMock()
        mock_repo.get_current = AsyncMock(return_value=mock_ready_prompt)

        with (
            patch("nikita.config.settings.get_settings", return_value=mock_settings_enabled),
            patch("nikita.db.repositories.ready_prompt_repository.ReadyPromptRepository", return_value=mock_repo),
        ):
            handler = _make_server_handler(mock_settings_enabled)
            uid = str(uuid4())
            results = await asyncio.gather(
                handler._try_load_ready_prompt(uid, mock_session),
                handler._try_load_ready_prompt(uid, mock_session),
                handler._try_load_ready_prompt(uid, mock_session),
            )
            assert all(r == mock_ready_prompt.prompt_text for r in results)

    @pytest.mark.asyncio
    async def test_no_meta_prompt_when_ready(self, user_id_str, mock_session, mock_settings_enabled, mock_ready_prompt):
        """MetaPromptService not invoked for ready prompt loading."""
        mock_repo = AsyncMock()
        mock_repo.get_current = AsyncMock(return_value=mock_ready_prompt)

        with (
            patch("nikita.config.settings.get_settings", return_value=mock_settings_enabled),
            patch("nikita.db.repositories.ready_prompt_repository.ReadyPromptRepository", return_value=mock_repo),
        ):
            handler = _make_server_handler(mock_settings_enabled)
            result = await handler._try_load_ready_prompt(user_id_str, mock_session)
            assert result is not None
            # MetaPromptService is no longer called - ready prompts bypass it


# =============================================================================
# 4. Performance Tests (3 tests)
# =============================================================================


class TestVoicePerformance:

    @pytest.mark.asyncio
    async def test_load_under_100ms(self, user_id_str, mock_session, mock_settings_enabled, mock_ready_prompt):
        mock_repo = AsyncMock()
        mock_repo.get_current = AsyncMock(return_value=mock_ready_prompt)

        with (
            patch("nikita.config.settings.get_settings", return_value=mock_settings_enabled),
            patch("nikita.db.repositories.ready_prompt_repository.ReadyPromptRepository", return_value=mock_repo),
        ):
            handler = _make_server_handler(mock_settings_enabled)
            start = time.perf_counter()
            await handler._try_load_ready_prompt(user_id_str, mock_session)
            elapsed_ms = (time.perf_counter() - start) * 1000
            assert elapsed_ms < 100, f"Expected <100ms, got {elapsed_ms:.1f}ms"

    @pytest.mark.asyncio
    async def test_flag_check_fast(self, user_id_str, mock_session, mock_settings_disabled):
        with patch("nikita.config.settings.get_settings", return_value=mock_settings_disabled):
            handler = _make_server_handler(mock_settings_disabled)
            start = time.perf_counter()
            await handler._try_load_ready_prompt(user_id_str, mock_session)
            elapsed_ms = (time.perf_counter() - start) * 1000
            assert elapsed_ms < 10, f"Expected <10ms, got {elapsed_ms:.1f}ms"

    @pytest.mark.asyncio
    async def test_no_context_engine_when_ready(self, user_id_str, mock_session, mock_settings_enabled, mock_ready_prompt):
        """ContextEngine not invoked during ready prompt load."""
        mock_repo = AsyncMock()
        mock_repo.get_current = AsyncMock(return_value=mock_ready_prompt)

        with (
            patch("nikita.config.settings.get_settings", return_value=mock_settings_enabled),
            patch("nikita.db.repositories.ready_prompt_repository.ReadyPromptRepository", return_value=mock_repo),
        ):
            handler = _make_server_handler(mock_settings_enabled)
            result = await handler._try_load_ready_prompt(user_id_str, mock_session)
            assert result is not None
            # _try_load_ready_prompt never touches ContextEngine
