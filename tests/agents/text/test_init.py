"""Tests for nikita.agents.text module initialization.

Tests the get_user_by_id() function and get_nikita_agent_for_user() factory.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from nikita.agents.text import get_user_by_id, UserNotFoundError


class TestGetUserById:
    """Tests for get_user_by_id() function."""

    @pytest.mark.asyncio
    async def test_returns_user_when_exists(self):
        """
        AC-T1.3, AC-T1.4: Uses UserRepository.get() and returns User if found.
        """
        user_id = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id

        # Mock the repository and session
        mock_repo = AsyncMock()
        mock_repo.get.return_value = mock_user

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_maker = MagicMock(return_value=mock_session)

        with patch("nikita.db.database.get_session_maker", return_value=mock_maker):
            with patch(
                "nikita.db.repositories.user_repository.UserRepository", return_value=mock_repo
            ):
                result = await get_user_by_id(user_id)

        assert result == mock_user
        mock_repo.get.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        """
        AC-T1.4: Returns None if user not found.
        """
        user_id = uuid4()

        # Mock the repository returning None
        mock_repo = AsyncMock()
        mock_repo.get.return_value = None

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_maker = MagicMock(return_value=mock_session)

        with patch("nikita.db.database.get_session_maker", return_value=mock_maker):
            with patch(
                "nikita.db.repositories.user_repository.UserRepository", return_value=mock_repo
            ):
                result = await get_user_by_id(user_id)

        assert result is None
        mock_repo.get.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_creates_session_and_repository(self):
        """
        AC-T1.2, AC-T1.5: Creates session using get_session_maker() and closes properly.
        """
        user_id = uuid4()

        mock_repo = AsyncMock()
        mock_repo.get.return_value = None

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_maker = MagicMock(return_value=mock_session)

        with patch(
            "nikita.db.database.get_session_maker", return_value=mock_maker
        ) as mock_get_maker:
            with patch(
                "nikita.db.repositories.user_repository.UserRepository", return_value=mock_repo
            ) as mock_repo_class:
                await get_user_by_id(user_id)

        # Verify session maker was called
        mock_get_maker.assert_called_once()
        # Verify session context was entered and exited
        mock_session.__aenter__.assert_called_once()
        mock_session.__aexit__.assert_called_once()
        # Verify repository was created with session
        mock_repo_class.assert_called_once_with(mock_session)


class TestGetNikitaAgentForUser:
    """Tests for get_nikita_agent_for_user() factory."""

    @pytest.mark.asyncio
    async def test_raises_user_not_found_when_user_missing(self):
        """
        Verify UserNotFoundError is raised when user doesn't exist.
        """
        from nikita.agents.text import get_nikita_agent_for_user

        user_id = uuid4()

        with patch(
            "nikita.agents.text.get_user_by_id",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with pytest.raises(UserNotFoundError) as exc_info:
                await get_nikita_agent_for_user(user_id)

            assert exc_info.value.user_id == user_id

    @pytest.mark.asyncio
    async def test_loads_user_memory_and_settings(self):
        """
        Verify factory loads user, initializes memory, and gets settings.
        """
        from nikita.agents.text import get_nikita_agent_for_user

        user_id = uuid4()

        mock_user = MagicMock()
        mock_user.id = user_id

        mock_memory = AsyncMock()
        mock_settings = MagicMock()
        mock_agent = MagicMock()

        with patch(
            "nikita.agents.text.get_user_by_id",
            new_callable=AsyncMock,
            return_value=mock_user,
        ):
            with patch(
                "nikita.agents.text.get_memory_client",
                new_callable=AsyncMock,
                return_value=mock_memory,
            ):
                with patch(
                    "nikita.agents.text.get_settings", return_value=mock_settings
                ):
                    with patch(
                        "nikita.agents.text.get_nikita_agent", return_value=mock_agent
                    ):
                        agent, deps = await get_nikita_agent_for_user(user_id)

        assert agent == mock_agent
        assert deps.user == mock_user
        assert deps.memory == mock_memory
        assert deps.settings == mock_settings
