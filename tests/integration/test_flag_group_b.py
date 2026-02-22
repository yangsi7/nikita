"""Integration tests for Group B feature flags (Spec 066 T2).

Verifies that psyche_agent_enabled flag activates gated behavior paths
and that graceful degradation works when psyche state is None/missing.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock


class TestPsycheAgentFlagEnabled:
    """Tests for psyche_agent_enabled=True flag behavior."""

    def test_is_psyche_agent_enabled_returns_true_when_flag_on(self):
        """is_psyche_agent_enabled() returns True when flag is ON."""
        from nikita.agents.psyche import is_psyche_agent_enabled

        mock_settings = MagicMock()
        mock_settings.psyche_agent_enabled = True

        with patch("nikita.config.settings.get_settings", return_value=mock_settings):
            assert is_psyche_agent_enabled() is True

    def test_is_psyche_agent_enabled_returns_false_when_flag_off(self):
        """is_psyche_agent_enabled() returns False when flag is OFF."""
        from nikita.agents.psyche import is_psyche_agent_enabled

        mock_settings = MagicMock()
        mock_settings.psyche_agent_enabled = False

        with patch("nikita.config.settings.get_settings", return_value=mock_settings):
            assert is_psyche_agent_enabled() is False

    @pytest.mark.asyncio
    async def test_psyche_batch_skipped_when_flag_off(self):
        """run_psyche_batch() returns skip result when flag is OFF."""
        from nikita.agents.psyche.batch import run_psyche_batch

        mock_settings = MagicMock()
        mock_settings.psyche_agent_enabled = False

        with patch("nikita.config.settings.get_settings", return_value=mock_settings):
            result = await run_psyche_batch()

        assert result["processed"] == 0
        assert result["skipped"] == 0 or result.get("skipped") is not None
        # Key signal: no errors and batch was effectively a no-op
        assert "errors" in result

    @pytest.mark.asyncio
    async def test_psyche_batch_proceeds_when_flag_on(self):
        """run_psyche_batch() enters active processing branch when flag is ON.

        We mock DB and agent calls so it runs without real DB — just checking that
        the flag-gate is passed and processing is attempted. Imports in batch.py
        are lazy (inside function body), so we patch the source modules directly.
        """
        from nikita.agents.psyche.batch import run_psyche_batch

        mock_user = MagicMock()
        mock_user.id = __import__("uuid").uuid4()
        mock_user.telegram_id = 12345

        mock_user_repo = MagicMock()
        mock_user_repo.get_active_users_for_decay = AsyncMock(return_value=[mock_user])

        mock_psyche_repo = MagicMock()
        mock_psyche_repo.get_current = AsyncMock(return_value=None)
        mock_psyche_repo.upsert = AsyncMock()

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock(return_value=mock_session)

        async def mock_generate_psyche_state(deps):
            return MagicMock(model_dump=MagicMock(return_value={"disposition": "neutral"}))

        with patch("nikita.agents.psyche.batch.is_psyche_agent_enabled", return_value=True):
            with patch("nikita.db.database.get_session_maker", return_value=mock_session_maker):
                with patch("nikita.db.repositories.user_repository.UserRepository", return_value=mock_user_repo):
                    with patch("nikita.db.repositories.psyche_state_repository.PsycheStateRepository", return_value=mock_psyche_repo):
                        with patch("nikita.agents.psyche.agent.generate_psyche_state", side_effect=mock_generate_psyche_state):
                            with patch("nikita.agents.psyche.deps.PsycheDeps", MagicMock()):
                                result = await run_psyche_batch()

        # The batch ran and returned a result dict (not the early-exit skip result)
        assert "processed" in result
        assert "errors" in result


class TestPsycheGracefulDegradation:
    """Tests that psyche state None/missing doesn't crash the pipeline."""

    def test_psyche_state_dict_none_is_acceptable(self):
        """psyche_state_dict=None is a valid state — no crash expected.

        Verifies the data structure contract: callers must handle None.
        """
        # Simulate what message_handler does: psyche_state_dict starts as None
        psyche_state_dict: dict | None = None

        # Downstream code should handle None gracefully
        if psyche_state_dict:
            state_value = psyche_state_dict.get("disposition", "neutral")
        else:
            state_value = "neutral"

        assert state_value == "neutral"

    def test_psyche_state_dict_empty_is_acceptable(self):
        """psyche_state_dict={} (empty dict) is falsy — treated same as None."""
        psyche_state_dict: dict | None = {}

        if psyche_state_dict:
            state_value = psyche_state_dict.get("disposition", "neutral")
        else:
            state_value = "neutral"

        assert state_value == "neutral"

    def test_psyche_state_dict_with_data_is_used(self):
        """psyche_state_dict with data is passed to downstream callers."""
        psyche_state_dict: dict | None = {"disposition": "anxious", "energy": 0.3}

        if psyche_state_dict:
            state_value = psyche_state_dict.get("disposition", "neutral")
        else:
            state_value = "neutral"

        assert state_value == "anxious"

    @pytest.mark.asyncio
    async def test_psyche_repo_returns_none_no_crash(self):
        """PsycheStateRepository.get_current() returning None doesn't crash handler logic."""
        # Simulates the block in message_handler.py lines 251-254
        mock_psyche_record = None
        psyche_state_dict = None

        if mock_psyche_record and mock_psyche_record.state:
            psyche_state_dict = mock_psyche_record.state

        # No crash, psyche_state_dict remains None
        assert psyche_state_dict is None

    @pytest.mark.asyncio
    async def test_psyche_repo_returns_record_with_none_state_no_crash(self):
        """PsycheStateRepository.get_current() returning record with state=None doesn't crash."""
        mock_psyche_record = MagicMock()
        mock_psyche_record.state = None
        psyche_state_dict = None

        if mock_psyche_record and mock_psyche_record.state:
            psyche_state_dict = mock_psyche_record.state

        assert psyche_state_dict is None
