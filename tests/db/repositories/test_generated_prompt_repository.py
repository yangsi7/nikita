"""Tests for GeneratedPromptRepository - Issue 1: Prompt Logging.

These tests verify that prompts are properly committed to the database.
TDD: Tests written BEFORE fixes - should FAIL initially.
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from nikita.db.models.generated_prompt import GeneratedPrompt
from nikita.db.repositories.generated_prompt_repository import GeneratedPromptRepository


@pytest.fixture
def user_id():
    """Create a test user ID."""
    return uuid4()


@pytest.fixture
def conversation_id():
    """Create a test conversation ID."""
    return uuid4()


@pytest.fixture
def mock_session():
    """Create a mock async database session."""
    session = MagicMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    session.refresh = AsyncMock()
    return session


class TestGeneratedPromptRepository:
    """Tests for GeneratedPromptRepository persistence."""

    @pytest.mark.asyncio
    async def test_create_log_calls_commit_not_flush(
        self,
        mock_session,
        user_id,
        conversation_id,
    ):
        """Verify create_log() calls commit() instead of just flush() (T1.1).

        This is the CRITICAL test - prompts must be persisted immediately
        after create_log() is called, not just flushed.
        """
        repo = GeneratedPromptRepository(mock_session)

        # Create a prompt log
        prompt = await repo.create_log(
            user_id=user_id,
            prompt_content="Test system prompt for Nikita",
            token_count=100,
            generation_time_ms=150.5,
            meta_prompt_template="system_prompt",
            conversation_id=conversation_id,
            context_snapshot={"chapter": 1, "score": 50.0},
        )

        # CRITICAL: Verify commit was called, not just flush
        mock_session.commit.assert_called_once()

        # Verify add was called with a GeneratedPrompt object
        mock_session.add.assert_called_once()
        added_obj = mock_session.add.call_args[0][0]
        assert isinstance(added_obj, GeneratedPrompt)
        assert added_obj.user_id == user_id
        assert added_obj.conversation_id == conversation_id
        assert added_obj.prompt_content == "Test system prompt for Nikita"

    @pytest.mark.asyncio
    async def test_create_log_includes_conversation_id(
        self,
        mock_session,
        user_id,
        conversation_id,
    ):
        """Verify conversation_id is stored with prompt (T1.3)."""
        repo = GeneratedPromptRepository(mock_session)

        await repo.create_log(
            user_id=user_id,
            prompt_content="Test prompt",
            token_count=50,
            generation_time_ms=100.0,
            meta_prompt_template="system_prompt",
            conversation_id=conversation_id,
        )

        # Verify the prompt was created with conversation_id
        added_obj = mock_session.add.call_args[0][0]
        assert added_obj.conversation_id == conversation_id

    @pytest.mark.asyncio
    async def test_create_log_without_conversation_id(
        self,
        mock_session,
        user_id,
    ):
        """Verify prompts can be created without conversation_id."""
        repo = GeneratedPromptRepository(mock_session)

        await repo.create_log(
            user_id=user_id,
            prompt_content="Test prompt without conversation",
            token_count=75,
            generation_time_ms=120.0,
            meta_prompt_template="system_prompt",
            conversation_id=None,
        )

        added_obj = mock_session.add.call_args[0][0]
        assert added_obj.conversation_id is None
        assert added_obj.user_id == user_id

    @pytest.mark.asyncio
    async def test_create_log_stores_context_snapshot(
        self,
        mock_session,
        user_id,
    ):
        """Verify context_snapshot is stored correctly."""
        repo = GeneratedPromptRepository(mock_session)

        complex_snapshot = {
            "chapter": 3,
            "relationship_score": 75.5,
            "engagement_state": "in_zone",
            "top_vices": ["intellectual_dominance", "risk_taking"],
            "thread_count": 5,
            "has_backstory": True,
        }

        await repo.create_log(
            user_id=user_id,
            prompt_content="Test prompt",
            token_count=100,
            generation_time_ms=150.0,
            meta_prompt_template="system_prompt",
            context_snapshot=complex_snapshot,
        )

        added_obj = mock_session.add.call_args[0][0]
        assert added_obj.context_snapshot == complex_snapshot
        assert added_obj.context_snapshot["chapter"] == 3
        assert added_obj.context_snapshot["top_vices"] == ["intellectual_dominance", "risk_taking"]

    @pytest.mark.asyncio
    async def test_get_by_user_id_queries_correct_filter(
        self,
        mock_session,
        user_id,
    ):
        """Verify get_by_user_id queries with correct user_id filter."""
        # Setup mock to return empty result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        repo = GeneratedPromptRepository(mock_session)
        result = await repo.get_by_user_id(user_id)

        # Verify execute was called (query was made)
        mock_session.execute.assert_called_once()

        # Result should be empty list
        assert result == []

    @pytest.mark.asyncio
    async def test_get_latest_by_user_id_queries_with_limit(
        self,
        mock_session,
        user_id,
    ):
        """Verify get_latest_by_user_id queries with limit 1."""
        # Setup mock to return None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = GeneratedPromptRepository(mock_session)
        result = await repo.get_latest_by_user_id(user_id)

        # Verify execute was called
        mock_session.execute.assert_called_once()

        # Result should be None (no prompts)
        assert result is None


class TestGeneratedPromptRepositoryCommitBehavior:
    """Tests specifically for commit vs flush behavior."""

    @pytest.mark.asyncio
    async def test_flush_not_called_on_create_log(
        self,
        mock_session,
        user_id,
    ):
        """Verify flush is NOT called (we use commit now)."""
        repo = GeneratedPromptRepository(mock_session)

        await repo.create_log(
            user_id=user_id,
            prompt_content="Test",
            token_count=10,
            generation_time_ms=50.0,
            meta_prompt_template="system_prompt",
        )

        # Flush should NOT be called anymore
        mock_session.flush.assert_not_called()

        # Commit SHOULD be called
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_log_returns_prompt_after_commit(
        self,
        mock_session,
        user_id,
        conversation_id,
    ):
        """Verify create_log returns the prompt object after commit."""
        repo = GeneratedPromptRepository(mock_session)

        result = await repo.create_log(
            user_id=user_id,
            prompt_content="Returned prompt",
            token_count=100,
            generation_time_ms=150.0,
            meta_prompt_template="system_prompt",
            conversation_id=conversation_id,
        )

        # Result should be a GeneratedPrompt object
        assert isinstance(result, GeneratedPrompt)
        assert result.prompt_content == "Returned prompt"
        assert result.user_id == user_id
        assert result.conversation_id == conversation_id
