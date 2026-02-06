"""Tests for ReadyPromptRepository (Spec 042 T0.6)."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from nikita.db.models.ready_prompt import ReadyPrompt
from nikita.db.repositories.ready_prompt_repository import ReadyPromptRepository


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def mock_session():
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def repo(mock_session):
    return ReadyPromptRepository(mock_session)


class TestGetCurrent:
    """Tests for get_current method (AC-0.6.1)."""

    @pytest.mark.asyncio
    async def test_get_current_returns_prompt(self, repo, mock_session, user_id):
        """get_current returns active prompt for user/platform."""
        prompt = ReadyPrompt(
            id=uuid4(),
            user_id=user_id,
            platform="text",
            prompt_text="You are Nikita...",
            token_count=500,
            pipeline_version="042-v1",
            generation_time_ms=8000.0,
            is_current=True,
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = prompt
        mock_session.execute.return_value = mock_result

        result = await repo.get_current(user_id=user_id, platform="text")

        mock_session.execute.assert_called_once()
        assert result is prompt
        assert result.is_current is True

    @pytest.mark.asyncio
    async def test_get_current_returns_none_when_empty(self, repo, mock_session, user_id):
        """get_current returns None when no prompt exists."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repo.get_current(user_id=user_id, platform="text")

        assert result is None


class TestSetCurrent:
    """Tests for set_current method (AC-0.6.2)."""

    @pytest.mark.asyncio
    async def test_set_current_deactivates_old_and_inserts_new(self, repo, mock_session, user_id):
        """set_current deactivates old prompt and inserts new."""
        result = await repo.set_current(
            user_id=user_id,
            platform="text",
            prompt_text="New prompt...",
            token_count=600,
            context_snapshot={"chapter": 3},
            pipeline_version="042-v1",
            generation_time_ms=9000.0,
        )

        # Should execute UPDATE (deactivate) then ADD new
        assert mock_session.execute.call_count >= 1  # Deactivate query
        mock_session.add.assert_called_once()

        added_obj = mock_session.add.call_args[0][0]
        assert isinstance(added_obj, ReadyPrompt)
        assert added_obj.user_id == user_id
        assert added_obj.platform == "text"
        assert added_obj.prompt_text == "New prompt..."
        assert added_obj.token_count == 600
        assert added_obj.is_current is True

    @pytest.mark.asyncio
    async def test_set_current_with_conversation_id(self, repo, mock_session, user_id):
        """set_current stores conversation_id."""
        conv_id = uuid4()
        await repo.set_current(
            user_id=user_id,
            platform="voice",
            prompt_text="Voice prompt...",
            token_count=200,
            pipeline_version="042-v1",
            generation_time_ms=5000.0,
            conversation_id=conv_id,
        )

        added_obj = mock_session.add.call_args[0][0]
        assert added_obj.conversation_id == conv_id

    @pytest.mark.asyncio
    async def test_set_current_flushes(self, repo, mock_session, user_id):
        """set_current flushes to persist."""
        await repo.set_current(
            user_id=user_id,
            platform="text",
            prompt_text="Test",
            token_count=100,
            pipeline_version="042-v1",
            generation_time_ms=1000.0,
        )
        mock_session.flush.assert_called()


class TestGetHistory:
    """Tests for get_history method (AC-0.6.3)."""

    @pytest.mark.asyncio
    async def test_get_history_returns_list(self, repo, mock_session, user_id):
        """get_history returns past prompts."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        results = await repo.get_history(user_id=user_id)

        mock_session.execute.assert_called_once()
        assert results == []

    @pytest.mark.asyncio
    async def test_get_history_with_platform_filter(self, repo, mock_session, user_id):
        """get_history filters by platform."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await repo.get_history(user_id=user_id, platform="voice")

        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_history_with_limit(self, repo, mock_session, user_id):
        """get_history respects limit parameter."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await repo.get_history(user_id=user_id, limit=5)

        mock_session.execute.assert_called_once()
