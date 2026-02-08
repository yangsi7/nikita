"""Tests for ReadyPrompt integration in text agent (Spec 042 T4.1).

Acceptance Criteria:
- AC-4.1.1: build_system_prompt() reads from ready_prompts when unified_pipeline_enabled=true
- AC-4.1.2: Falls back to on-the-fly generation if no prompt exists
- AC-4.1.3: Logs warning on fallback with user_id
"""

import logging
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


@pytest.mark.asyncio
class TestReadyPromptIntegration:
    """Tests for ready_prompt integration in build_system_prompt."""

    async def test_ac_4_1_1_loads_from_ready_prompts_when_enabled(self, caplog):
        """AC-4.1.1: build_system_prompt() reads from ready_prompts when enabled."""
        from nikita.agents.text.agent import _try_load_ready_prompt

        user_id = uuid4()

        # Mock ready_prompt object
        mock_ready_prompt = MagicMock()
        mock_ready_prompt.prompt_text = "Pre-built prompt from ready_prompts"
        mock_ready_prompt.token_count = 2500

        # Mock session maker (avoids asyncpg import) + ReadyPromptRepository
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session_maker = MagicMock(return_value=mock_session)

        with (
            patch(
                "nikita.db.database.get_session_maker",
                return_value=mock_session_maker,
            ),
            patch(
                "nikita.db.repositories.ready_prompt_repository.ReadyPromptRepository"
            ) as MockRepo,
            caplog.at_level(logging.INFO),
        ):
            mock_repo_instance = MockRepo.return_value
            mock_repo_instance.get_current = AsyncMock(return_value=mock_ready_prompt)

            result = await _try_load_ready_prompt(user_id, None)

        # Verify we got the pre-built prompt
        assert result == "Pre-built prompt from ready_prompts"

        # Verify repository was called correctly
        mock_repo_instance.get_current.assert_called_once_with(user_id, "text")

        # Verify info log about loading ready_prompt
        assert any("loaded_ready_prompt" in record.message for record in caplog.records)
        assert any(str(user_id) in record.message for record in caplog.records)

    async def test_ac_4_1_2_returns_none_if_no_prompt(self, caplog):
        """AC-4.1.2: Returns None if no prompt exists."""
        from nikita.agents.text.agent import _try_load_ready_prompt

        user_id = uuid4()

        # Mock session maker (avoids asyncpg import) + ReadyPromptRepository
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session_maker = MagicMock(return_value=mock_session)

        with (
            patch(
                "nikita.db.database.get_session_maker",
                return_value=mock_session_maker,
            ),
            patch(
                "nikita.db.repositories.ready_prompt_repository.ReadyPromptRepository"
            ) as MockRepo,
        ):
            mock_repo_instance = MockRepo.return_value
            mock_repo_instance.get_current = AsyncMock(return_value=None)

            result = await _try_load_ready_prompt(user_id, None)

        # Verify None is returned
        assert result is None

        # Verify repository was called
        mock_repo_instance.get_current.assert_called_once_with(user_id, "text")

    async def test_ac_4_1_3_logs_warning_on_error(self, caplog):
        """AC-4.1.3: Logs warning on error with user_id."""
        from nikita.agents.text.agent import _try_load_ready_prompt

        user_id = uuid4()

        # Mock session maker (avoids asyncpg import) + ReadyPromptRepository
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)  # Don't suppress exceptions
        mock_session_maker = MagicMock(return_value=mock_session)

        with (
            patch(
                "nikita.db.database.get_session_maker",
                return_value=mock_session_maker,
            ),
            patch(
                "nikita.db.repositories.ready_prompt_repository.ReadyPromptRepository"
            ) as MockRepo,
            caplog.at_level(logging.WARNING, logger="nikita.agents.text.agent"),
        ):
            mock_repo_instance = MockRepo.return_value
            mock_repo_instance.get_current = AsyncMock(
                side_effect=Exception("Database connection failed")
            )

            result = await _try_load_ready_prompt(user_id, None)

            # Verify None is returned (graceful degradation)
            assert result is None

            # AC-4.1.3: Verify warning log with user_id
            warning_logs = [r for r in caplog.records if r.levelname == "WARNING"]
            assert len(warning_logs) > 0
            assert any("ready_prompt_load_failed" in r.message for r in warning_logs)
            assert any(str(user_id) in r.message for r in warning_logs)
            assert any("Database connection failed" in r.message for r in warning_logs)

    async def test_uses_provided_session_if_available(self):
        """Should use provided session instead of creating new one."""
        from nikita.agents.text.agent import _try_load_ready_prompt

        user_id = uuid4()
        mock_session = MagicMock()

        # Mock ready_prompt
        mock_ready_prompt = MagicMock()
        mock_ready_prompt.prompt_text = "Pre-built prompt"
        mock_ready_prompt.token_count = 2500

        with patch(
            "nikita.db.repositories.ready_prompt_repository.ReadyPromptRepository"
        ) as MockRepo:
            mock_repo_instance = MockRepo.return_value
            mock_repo_instance.get_current = AsyncMock(return_value=mock_ready_prompt)

            result = await _try_load_ready_prompt(user_id, mock_session)

        # Verify we got the pre-built prompt
        assert result == "Pre-built prompt"

        # Verify repository was initialized with the provided session
        MockRepo.assert_called_once_with(mock_session)

    async def test_integration_with_build_system_prompt(self, caplog):
        """Test full integration: build_system_prompt loads from ready_prompts when enabled."""
        from nikita.agents.text.agent import build_system_prompt

        user_id = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.chapter = 1

        # Mock settings to enable unified pipeline
        mock_settings = MagicMock()
        mock_settings.is_unified_pipeline_enabled_for_user.return_value = True

        # Mock ready_prompt
        mock_ready_prompt = MagicMock()
        mock_ready_prompt.prompt_text = "Pre-built prompt from ready_prompts table"
        mock_ready_prompt.token_count = 3000

        with (
            patch("nikita.config.settings.get_settings", return_value=mock_settings),
            patch(
                "nikita.db.repositories.ready_prompt_repository.ReadyPromptRepository"
            ) as MockRepo,
            patch("nikita.db.database.get_session_maker"),  # Mock session maker
            caplog.at_level(logging.INFO),
        ):
            mock_repo_instance = MockRepo.return_value
            mock_repo_instance.get_current = AsyncMock(return_value=mock_ready_prompt)

            result = await build_system_prompt(None, mock_user, "test message")

        # Verify we got the pre-built prompt
        assert result == "Pre-built prompt from ready_prompts table"

        # Verify feature flag was checked
        mock_settings.is_unified_pipeline_enabled_for_user.assert_called_once_with(
            user_id
        )

        # Verify ready_prompt was loaded
        assert any("loaded_ready_prompt" in r.message for r in caplog.records)

    async def test_integration_fallback_when_no_prompt(self, caplog):
        """Test fallback: build_system_prompt falls back to legacy when no ready_prompt exists."""
        from nikita.agents.text.agent import build_system_prompt

        user_id = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.chapter = 1

        # Mock settings to enable unified pipeline
        mock_settings = MagicMock()
        mock_settings.is_unified_pipeline_enabled_for_user.return_value = True

        # Mock get_session_maker to return a mock session
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.commit = AsyncMock()

        mock_session_maker = MagicMock()
        mock_session_maker.return_value = mock_session

        with (
            patch("nikita.config.settings.get_settings", return_value=mock_settings),
            patch(
                "nikita.db.repositories.ready_prompt_repository.ReadyPromptRepository"
            ) as MockRepo,
            patch(
                "nikita.db.database.get_session_maker",
                return_value=mock_session_maker,
            ),
            patch(
                "nikita.agents.text.agent._build_system_prompt_legacy",
                new_callable=AsyncMock,
                return_value="Legacy fallback prompt",
            ) as mock_legacy,
            caplog.at_level(logging.WARNING),
        ):
            # Mock repository returning None (no prompt)
            mock_repo_instance = MockRepo.return_value
            mock_repo_instance.get_current = AsyncMock(return_value=None)

            result = await build_system_prompt(None, mock_user, "test message")

        # Verify we got the legacy fallback prompt
        assert result == "Legacy fallback prompt"

        # Verify warning log about fallback
        warning_logs = [r for r in caplog.records if r.levelname == "WARNING"]
        assert any("no_ready_prompt" in r.message for r in warning_logs)

        # Verify legacy builder was called
        mock_legacy.assert_called_once()
