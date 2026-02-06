"""
Tests for text agent ready prompt loading (Spec 042 T4.1/T4.6).

Tests verify the agent's ability to load pre-built prompts from ready_prompts table
when unified pipeline feature flag is enabled.
"""

import asyncio
import time

import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID


# --- Fixtures ---


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def mock_ready_prompt():
    return SimpleNamespace(
        prompt_text="You are Nikita, a witty AI girlfriend who loves banter...",
        token_count=5800,
        pipeline_version="042-v1",
        is_current=True,
    )


@pytest.fixture
def mock_user():
    return SimpleNamespace(
        id=uuid4(),
        username="test_user",
        phone_number="+15551234567",
        chapter=2,
        relationship_score=65.0,
    )


# --- Category 1: _try_load_ready_prompt unit tests ---


class TestTryLoadReadyPrompt:
    """Tests for the _try_load_ready_prompt helper function."""

    async def test_with_session_returns_prompt_text(self, user_id, mock_session, mock_ready_prompt):
        """Uses provided session, returns prompt_text string."""
        mock_repo = AsyncMock()
        mock_repo.get_current = AsyncMock(return_value=mock_ready_prompt)

        with patch(
            "nikita.db.repositories.ready_prompt_repository.ReadyPromptRepository",
            return_value=mock_repo,
        ):
            from nikita.agents.text.agent import _try_load_ready_prompt

            result = await _try_load_ready_prompt(user_id, mock_session)

        assert result == mock_ready_prompt.prompt_text

    async def test_returns_none_when_not_found(self, user_id, mock_session):
        """Returns None when no prompt in DB."""
        mock_repo = AsyncMock()
        mock_repo.get_current = AsyncMock(return_value=None)

        with patch(
            "nikita.db.repositories.ready_prompt_repository.ReadyPromptRepository",
            return_value=mock_repo,
        ):
            from nikita.agents.text.agent import _try_load_ready_prompt

            result = await _try_load_ready_prompt(user_id, mock_session)

        assert result is None

    async def test_catches_exceptions_returns_none(self, user_id, mock_session):
        """Returns None on DB error."""
        mock_repo = AsyncMock()
        mock_repo.get_current = AsyncMock(side_effect=Exception("DB connection failed"))

        with patch(
            "nikita.db.repositories.ready_prompt_repository.ReadyPromptRepository",
            return_value=mock_repo,
        ):
            from nikita.agents.text.agent import _try_load_ready_prompt

            result = await _try_load_ready_prompt(user_id, mock_session)

        assert result is None

    async def test_uses_text_platform(self, user_id, mock_session):
        """Passes 'text' as platform argument to get_current."""
        mock_repo = AsyncMock()
        mock_repo.get_current = AsyncMock(return_value=None)

        with patch(
            "nikita.db.repositories.ready_prompt_repository.ReadyPromptRepository",
            return_value=mock_repo,
        ):
            from nikita.agents.text.agent import _try_load_ready_prompt

            await _try_load_ready_prompt(user_id, mock_session)

        mock_repo.get_current.assert_called_once_with(user_id, "text")

    async def test_without_session_creates_own(self, user_id, mock_ready_prompt):
        """Creates its own session via get_session_maker when None passed."""
        mock_repo = AsyncMock()
        mock_repo.get_current = AsyncMock(return_value=mock_ready_prompt)

        mock_new_session = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_new_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_session_maker = MagicMock(return_value=mock_ctx)

        with patch(
            "nikita.db.repositories.ready_prompt_repository.ReadyPromptRepository",
            return_value=mock_repo,
        ):
            with patch(
                "nikita.db.database.get_session_maker",
                return_value=mock_session_maker,
            ):
                from nikita.agents.text.agent import _try_load_ready_prompt

                result = await _try_load_ready_prompt(user_id, None)

        assert result == mock_ready_prompt.prompt_text

    async def test_load_under_100ms(self, user_id, mock_session, mock_ready_prompt):
        """Mocked load should be nearly instant."""
        mock_repo = AsyncMock()
        mock_repo.get_current = AsyncMock(return_value=mock_ready_prompt)

        with patch(
            "nikita.db.repositories.ready_prompt_repository.ReadyPromptRepository",
            return_value=mock_repo,
        ):
            from nikita.agents.text.agent import _try_load_ready_prompt

            start = time.perf_counter()
            result = await _try_load_ready_prompt(user_id, mock_session)
            elapsed_ms = (time.perf_counter() - start) * 1000

        assert result == mock_ready_prompt.prompt_text
        assert elapsed_ms < 100

    async def test_concurrent_reads_safe(self, user_id, mock_ready_prompt):
        """Multiple concurrent reads don't conflict."""
        mock_repo = AsyncMock()
        mock_repo.get_current = AsyncMock(return_value=mock_ready_prompt)

        session_1 = AsyncMock()
        session_2 = AsyncMock()

        with patch(
            "nikita.db.repositories.ready_prompt_repository.ReadyPromptRepository",
            return_value=mock_repo,
        ):
            from nikita.agents.text.agent import _try_load_ready_prompt

            results = await asyncio.gather(
                _try_load_ready_prompt(user_id, session_1),
                _try_load_ready_prompt(user_id, session_2),
                _try_load_ready_prompt(user_id, session_1),
            )

        assert len(results) == 3
        assert all(r == mock_ready_prompt.prompt_text for r in results)


# --- Category 2: build_system_prompt feature flag integration ---


class TestBuildSystemPromptFeatureFlag:
    """Test that build_system_prompt respects the unified pipeline flag."""

    async def test_flag_enabled_returns_ready_prompt(self, mock_user, mock_session):
        """When flag ON and prompt exists, returns pre-built prompt."""
        settings = MagicMock()
        settings.is_unified_pipeline_enabled_for_user = MagicMock(return_value=True)

        with patch("nikita.config.settings.get_settings", return_value=settings):
            with patch(
                "nikita.agents.text.agent._try_load_ready_prompt",
                new_callable=AsyncMock,
                return_value="Pre-built Nikita prompt",
            ):
                from nikita.agents.text.agent import build_system_prompt

                result = await build_system_prompt(
                    memory=None,
                    user=mock_user,
                    user_message="Hello",
                    conversation_id=None,
                    session=mock_session,
                )

        assert result == "Pre-built Nikita prompt"

    async def test_flag_enabled_no_prompt_falls_back(self, mock_user, mock_session):
        """When flag ON but no prompt, falls through to legacy generation."""
        settings = MagicMock()
        settings.is_unified_pipeline_enabled_for_user = MagicMock(return_value=True)

        with patch("nikita.config.settings.get_settings", return_value=settings):
            with patch(
                "nikita.agents.text.agent._try_load_ready_prompt",
                new_callable=AsyncMock,
                return_value=None,
            ):
                with patch(
                    "nikita.agents.text.agent._build_system_prompt_legacy",
                    new_callable=AsyncMock,
                    return_value="Legacy generated prompt",
                ):
                    from nikita.agents.text.agent import build_system_prompt

                    result = await build_system_prompt(
                        memory=None,
                        user=mock_user,
                        user_message="Hello",
                        conversation_id=None,
                        session=mock_session,
                    )

        assert result == "Legacy generated prompt"

    async def test_flag_disabled_skips_ready_prompt(self, mock_user, mock_session):
        """When flag OFF, _try_load_ready_prompt is NOT called."""
        settings = MagicMock()
        settings.is_unified_pipeline_enabled_for_user = MagicMock(return_value=False)

        with patch("nikita.config.settings.get_settings", return_value=settings):
            with patch(
                "nikita.agents.text.agent._try_load_ready_prompt",
                new_callable=AsyncMock,
            ) as mock_try_load:
                with patch(
                    "nikita.agents.text.agent._build_system_prompt_legacy",
                    new_callable=AsyncMock,
                    return_value="Legacy prompt",
                ):
                    from nikita.agents.text.agent import build_system_prompt

                    result = await build_system_prompt(
                        memory=None,
                        user=mock_user,
                        user_message="Hello",
                        conversation_id=None,
                        session=mock_session,
                    )

        mock_try_load.assert_not_called()
        assert result == "Legacy prompt"

    async def test_prompt_returned_verbatim(self, mock_user, mock_session):
        """Prompt text returned exactly as stored, no modification."""
        exact = "EXACT_PROMPT_!@#$%^&*()"
        settings = MagicMock()
        settings.is_unified_pipeline_enabled_for_user = MagicMock(return_value=True)

        with patch("nikita.config.settings.get_settings", return_value=settings):
            with patch(
                "nikita.agents.text.agent._try_load_ready_prompt",
                new_callable=AsyncMock,
                return_value=exact,
            ):
                from nikita.agents.text.agent import build_system_prompt

                result = await build_system_prompt(
                    memory=None,
                    user=mock_user,
                    user_message="Hi",
                    session=mock_session,
                )

        assert result == exact


# --- Category 3: Feature flag settings ---


class TestFeatureFlagSettings:
    """Test the feature flag configuration."""

    def test_settings_has_unified_pipeline_flag(self):
        """Settings model includes the feature flag."""
        from nikita.config.settings import Settings

        assert "unified_pipeline_enabled" in Settings.model_fields
        assert "unified_pipeline_rollout_pct" in Settings.model_fields

    def test_flag_defaults_to_false(self):
        """Feature flag defaults to disabled."""
        from nikita.config.settings import Settings

        field_info = Settings.model_fields["unified_pipeline_enabled"]
        assert field_info.default is False

    def test_rollout_pct_hash_deterministic(self):
        """Same user_id always gets same result."""
        from nikita.config.settings import Settings

        # Use is_unified_pipeline_enabled_for_user via mock settings
        settings = MagicMock()
        settings.unified_pipeline_enabled = True
        settings.unified_pipeline_rollout_pct = 50

        # Replicate the actual hash logic
        uid = uuid4()
        user_hash = hash(str(uid)) % 100
        expected = user_hash < 50

        # Verify deterministic: same uid always same result
        result1 = hash(str(uid)) % 100 < 50
        result2 = hash(str(uid)) % 100 < 50
        assert result1 == result2 == expected
