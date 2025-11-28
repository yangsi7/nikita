"""Tests for Agent Factory - TDD for T1.4.

Acceptance Criteria:
- AC-1.4.1: `get_nikita_agent(user_id: UUID)` async function exists
- AC-1.4.2: Function loads user from database
- AC-1.4.3: Function initializes NikitaMemory for user
- AC-1.4.4: Function returns tuple (Agent, NikitaDeps)
- AC-1.4.5: Function handles user not found with appropriate error
"""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch


class TestGetNikitaAgentForUser:
    """Tests for get_nikita_agent_for_user factory function."""

    def test_function_exists(self):
        """Factory function should exist and be importable."""
        from nikita.agents.text import get_nikita_agent_for_user

        assert callable(get_nikita_agent_for_user)

    @pytest.mark.asyncio
    async def test_ac_1_4_1_accepts_user_id(self):
        """AC-1.4.1: Function accepts user_id: UUID parameter."""
        from nikita.agents.text import get_nikita_agent_for_user
        import inspect

        sig = inspect.signature(get_nikita_agent_for_user)
        assert "user_id" in sig.parameters

    @pytest.mark.asyncio
    async def test_function_is_async(self):
        """Factory function should be async."""
        from nikita.agents.text import get_nikita_agent_for_user
        import inspect

        assert inspect.iscoroutinefunction(get_nikita_agent_for_user)

    @pytest.mark.asyncio
    async def test_ac_1_4_4_returns_tuple_with_deps(self):
        """AC-1.4.4: Function returns tuple (Agent, NikitaDeps)."""
        from nikita.agents.text import get_nikita_agent_for_user
        from nikita.agents.text.deps import NikitaDeps

        user_id = uuid4()

        # Mock the dependencies - use AsyncMock for async functions
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.chapter = 2

        mock_memory = MagicMock()
        mock_settings = MagicMock()
        mock_agent = MagicMock()

        with patch("nikita.agents.text.get_user_by_id", new=AsyncMock(return_value=mock_user)), \
             patch("nikita.agents.text.get_memory_client", new=AsyncMock(return_value=mock_memory)), \
             patch("nikita.agents.text.get_settings", return_value=mock_settings), \
             patch("nikita.agents.text.get_nikita_agent", return_value=mock_agent):

            result = await get_nikita_agent_for_user(user_id)

            assert isinstance(result, tuple)
            assert len(result) == 2

            agent, deps = result
            assert isinstance(deps, NikitaDeps)
            assert deps.user is mock_user
            assert deps.memory is mock_memory
            assert deps.settings is mock_settings
            assert agent is mock_agent

    @pytest.mark.asyncio
    async def test_ac_1_4_2_loads_user(self):
        """AC-1.4.2: Function loads user from database."""
        from nikita.agents.text import get_nikita_agent_for_user

        user_id = uuid4()

        mock_user = MagicMock()
        mock_user.id = user_id

        mock_get_user = AsyncMock(return_value=mock_user)

        with patch("nikita.agents.text.get_user_by_id", new=mock_get_user), \
             patch("nikita.agents.text.get_memory_client", new=AsyncMock(return_value=MagicMock())), \
             patch("nikita.agents.text.get_settings"), \
             patch("nikita.agents.text.get_nikita_agent", return_value=MagicMock()):

            await get_nikita_agent_for_user(user_id)

            mock_get_user.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_ac_1_4_3_initializes_memory(self):
        """AC-1.4.3: Function initializes NikitaMemory for user."""
        from nikita.agents.text import get_nikita_agent_for_user

        user_id = uuid4()

        mock_user = MagicMock()
        mock_user.id = user_id

        mock_get_memory = AsyncMock(return_value=MagicMock())

        with patch("nikita.agents.text.get_user_by_id", new=AsyncMock(return_value=mock_user)), \
             patch("nikita.agents.text.get_memory_client", new=mock_get_memory), \
             patch("nikita.agents.text.get_settings"), \
             patch("nikita.agents.text.get_nikita_agent", return_value=MagicMock()):

            await get_nikita_agent_for_user(user_id)

            mock_get_memory.assert_called_once_with(str(user_id))

    @pytest.mark.asyncio
    async def test_ac_1_4_5_handles_user_not_found(self):
        """AC-1.4.5: Function handles user not found with appropriate error."""
        from nikita.agents.text import get_nikita_agent_for_user, UserNotFoundError

        user_id = uuid4()

        with patch("nikita.agents.text.get_user_by_id", new=AsyncMock(return_value=None)):
            with pytest.raises(UserNotFoundError) as exc_info:
                await get_nikita_agent_for_user(user_id)

            assert str(user_id) in str(exc_info.value)
