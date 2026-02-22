"""Tests for psyche batch safeguards (Spec 069)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from nikita.agents.psyche.batch import run_psyche_batch, MAX_BATCH_USERS


class TestPsycheBatchSafeguards:
    """Test safeguards added in Spec 069."""

    @pytest.mark.asyncio
    async def test_skips_when_flag_off(self):
        """Batch should skip when psyche_agent_enabled=False."""
        with patch("nikita.agents.psyche.batch.is_psyche_agent_enabled", return_value=False):
            result = await run_psyche_batch()
            assert result["processed"] == 0
            assert result["skipped"] == 0

    @pytest.mark.asyncio
    async def test_aborts_without_api_key(self):
        """Batch should abort if ANTHROPIC_API_KEY is not set."""
        mock_settings = MagicMock()
        mock_settings.anthropic_api_key = None

        # get_settings is imported inside the function body, so patch at source module
        with patch("nikita.agents.psyche.batch.is_psyche_agent_enabled", return_value=True), \
             patch("nikita.config.settings.get_settings", return_value=mock_settings):
            result = await run_psyche_batch()
            assert result["processed"] == 0
            assert "ANTHROPIC_API_KEY not configured" in result["errors"]

    @pytest.mark.asyncio
    async def test_caps_batch_at_max_users(self):
        """Batch should cap at MAX_BATCH_USERS."""
        mock_settings = MagicMock()
        mock_settings.anthropic_api_key = "sk-test-key"

        # Create more users than MAX_BATCH_USERS
        mock_users = [MagicMock(id=f"user-{i}") for i in range(MAX_BATCH_USERS + 50)]

        mock_session = AsyncMock()
        mock_user_repo = AsyncMock()
        mock_user_repo.get_active_users_for_decay.return_value = mock_users

        # Mock psyche generation to succeed
        mock_state = MagicMock()
        mock_state.model_dump.return_value = {}
        mock_gen = AsyncMock(return_value=(mock_state, 1500))

        psyche_repo = AsyncMock()
        mock_psyche_repo_cls = MagicMock(return_value=psyche_repo)

        # Set up session context manager
        session_cm = AsyncMock()
        session_cm.__aenter__.return_value = mock_session
        session_cm.__aexit__.return_value = False
        mock_session_factory = MagicMock(return_value=session_cm)
        mock_get_session_maker = MagicMock(return_value=mock_session_factory)

        # All heavy imports happen lazily inside the function body;
        # patch them at their canonical source modules.
        with patch("nikita.agents.psyche.batch.is_psyche_agent_enabled", return_value=True), \
             patch("nikita.config.settings.get_settings", return_value=mock_settings), \
             patch.dict("sys.modules", {
                 "nikita.db.database": MagicMock(get_session_maker=mock_get_session_maker),
                 "nikita.db.repositories.user_repository": MagicMock(UserRepository=MagicMock(return_value=mock_user_repo)),
                 "nikita.db.repositories.psyche_state_repository": MagicMock(PsycheStateRepository=mock_psyche_repo_cls),
                 "nikita.agents.psyche.agent": MagicMock(generate_psyche_state=mock_gen),
                 "nikita.agents.psyche.deps": MagicMock(),
             }):
            result = await run_psyche_batch()

            # Should only process MAX_BATCH_USERS, not MAX_BATCH_USERS + 50
            assert result["processed"] <= MAX_BATCH_USERS

    def test_max_batch_users_constant(self):
        """Verify MAX_BATCH_USERS is a reasonable value."""
        assert MAX_BATCH_USERS == 100
        assert isinstance(MAX_BATCH_USERS, int)
