"""Tests for Spec 068 context enrichment — historical thoughts/threads in PromptBuilder."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from nikita.pipeline.stages.prompt_builder import PromptBuilderStage
from nikita.pipeline.models import PipelineContext

# Patch paths for lazy imports inside _enrich_context try blocks
_THOUGHT_REPO = "nikita.db.repositories.thought_repository.NikitaThoughtRepository"
_THREAD_REPO = "nikita.db.repositories.thread_repository.ConversationThreadRepository"
_CONV_REPO = "nikita.db.repositories.conversation_repository.ConversationRepository"
_USER_REPO = "nikita.db.repositories.user_repository.UserRepository"
_GET_SETTINGS = "nikita.config.settings.get_settings"
_SUPABASE_MEMORY = "nikita.memory.supabase_memory.SupabaseMemory"


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def pipeline_context():
    return PipelineContext(
        conversation_id=uuid4(),
        user_id=uuid4(),
        started_at=datetime.now(timezone.utc),
        platform="text",
        chapter=2,
        relationship_score=65,
    )


def _make_conv_repo_mock():
    """Return an AsyncMock ConversationRepository that returns empty summaries."""
    conv_repo = AsyncMock()
    conv_repo.get_conversation_summaries_for_prompt.return_value = {}
    return conv_repo


def _make_user_repo_mock():
    """Return an AsyncMock UserRepository that returns None."""
    user_repo = AsyncMock()
    user_repo.get.return_value = None
    return user_repo


def _make_settings_mock(openai_key=None):
    """Return a settings mock with optional openai key."""
    settings = MagicMock()
    settings.openai_api_key = openai_key
    return settings


class TestEnrichContextThoughts:
    """Tests for historical thought loading in _enrich_context (Spec 068)."""

    @pytest.mark.asyncio
    async def test_loads_active_thoughts_from_db(self, mock_session, pipeline_context):
        """Verify thoughts loaded from NikitaThoughtRepository."""
        mock_thought_1 = MagicMock()
        mock_thought_1.content = "I wonder if he's thinking about me"
        mock_thought_2 = MagicMock()
        mock_thought_2.content = "Should I bring up that restaurant?"

        with patch(_THOUGHT_REPO) as MockThoughtRepo, \
             patch(_THREAD_REPO) as MockThreadRepo, \
             patch(_CONV_REPO) as MockConvRepo, \
             patch(_USER_REPO) as MockUserRepo, \
             patch(_GET_SETTINGS, return_value=_make_settings_mock()):

            thought_repo = AsyncMock()
            thought_repo.get_active_thoughts.return_value = [mock_thought_1, mock_thought_2]
            MockThoughtRepo.return_value = thought_repo

            thread_repo = AsyncMock()
            thread_repo.get_open_threads.return_value = []
            MockThreadRepo.return_value = thread_repo

            MockConvRepo.return_value = _make_conv_repo_mock()
            MockUserRepo.return_value = _make_user_repo_mock()

            stage = PromptBuilderStage(session=mock_session)
            await stage._enrich_context(pipeline_context)

            assert len(pipeline_context.active_thoughts) == 2
            assert pipeline_context.active_thoughts[0] == "I wonder if he's thinking about me"
            assert pipeline_context.active_thoughts[1] == "Should I bring up that restaurant?"

            # Verify correct arguments passed
            thought_repo.get_active_thoughts.assert_called_once_with(
                user_id=pipeline_context.user_id, limit=10,
            )

    @pytest.mark.asyncio
    async def test_thought_db_failure_non_critical(self, mock_session, pipeline_context):
        """DB error on thoughts should not crash enrichment."""
        with patch(_THOUGHT_REPO) as MockThoughtRepo, \
             patch(_THREAD_REPO) as MockThreadRepo, \
             patch(_CONV_REPO) as MockConvRepo, \
             patch(_USER_REPO) as MockUserRepo, \
             patch(_GET_SETTINGS, return_value=_make_settings_mock()):

            thought_repo = AsyncMock()
            thought_repo.get_active_thoughts.side_effect = Exception("DB connection lost")
            MockThoughtRepo.return_value = thought_repo

            thread_repo = AsyncMock()
            thread_repo.get_open_threads.return_value = []
            MockThreadRepo.return_value = thread_repo

            MockConvRepo.return_value = _make_conv_repo_mock()
            MockUserRepo.return_value = _make_user_repo_mock()

            stage = PromptBuilderStage(session=mock_session)
            # Should not raise
            await stage._enrich_context(pipeline_context)

            # active_thoughts should remain empty (default)
            assert pipeline_context.active_thoughts == []


class TestEnrichContextThreads:
    """Tests for historical thread loading in _enrich_context (Spec 068)."""

    @pytest.mark.asyncio
    async def test_merges_extracted_and_historical_threads(self, mock_session, pipeline_context):
        """Verify DB threads merged with extraction threads."""
        pipeline_context.extracted_threads = ["Current topic: weekend plans"]

        other_conv_id = uuid4()
        mock_thread = MagicMock()
        mock_thread.content = "He promised to call"
        mock_thread.thread_type = "promise"
        mock_thread.created_at = datetime(2026, 2, 20, tzinfo=timezone.utc)
        mock_thread.source_conversation_id = other_conv_id

        with patch(_THOUGHT_REPO) as MockThoughtRepo, \
             patch(_THREAD_REPO) as MockThreadRepo, \
             patch(_CONV_REPO) as MockConvRepo, \
             patch(_USER_REPO) as MockUserRepo, \
             patch(_GET_SETTINGS, return_value=_make_settings_mock()):

            thought_repo = AsyncMock()
            thought_repo.get_active_thoughts.return_value = []
            MockThoughtRepo.return_value = thought_repo

            thread_repo = AsyncMock()
            thread_repo.get_open_threads.return_value = [mock_thread]
            MockThreadRepo.return_value = thread_repo

            MockConvRepo.return_value = _make_conv_repo_mock()
            MockUserRepo.return_value = _make_user_repo_mock()

            stage = PromptBuilderStage(session=mock_session)
            await stage._enrich_context(pipeline_context)

            # Should have 1 extracted + 1 historical
            assert len(pipeline_context.open_threads) == 2
            assert pipeline_context.open_threads[0] == "Current topic: weekend plans"
            assert pipeline_context.open_threads[1]["topic"] == "He promised to call"
            assert pipeline_context.open_threads[1]["type"] == "promise"

    @pytest.mark.asyncio
    async def test_excludes_current_conversation_threads(self, mock_session, pipeline_context):
        """Threads from same conversation_id should be excluded."""
        mock_thread_same = MagicMock()
        mock_thread_same.content = "From current conversation"
        mock_thread_same.thread_type = "unresolved"
        mock_thread_same.created_at = datetime(2026, 2, 22, tzinfo=timezone.utc)
        mock_thread_same.source_conversation_id = pipeline_context.conversation_id  # Same!

        mock_thread_other = MagicMock()
        mock_thread_other.content = "From previous conversation"
        mock_thread_other.thread_type = "follow_up"
        mock_thread_other.created_at = datetime(2026, 2, 21, tzinfo=timezone.utc)
        mock_thread_other.source_conversation_id = uuid4()

        with patch(_THOUGHT_REPO) as MockThoughtRepo, \
             patch(_THREAD_REPO) as MockThreadRepo, \
             patch(_CONV_REPO) as MockConvRepo, \
             patch(_USER_REPO) as MockUserRepo, \
             patch(_GET_SETTINGS, return_value=_make_settings_mock()):

            thought_repo = AsyncMock()
            thought_repo.get_active_thoughts.return_value = []
            MockThoughtRepo.return_value = thought_repo

            thread_repo = AsyncMock()
            thread_repo.get_open_threads.return_value = [mock_thread_same, mock_thread_other]
            MockThreadRepo.return_value = thread_repo

            MockConvRepo.return_value = _make_conv_repo_mock()
            MockUserRepo.return_value = _make_user_repo_mock()

            stage = PromptBuilderStage(session=mock_session)
            await stage._enrich_context(pipeline_context)

            # Only the other-conversation thread should be in open_threads (as historical dict)
            historical = [t for t in pipeline_context.open_threads if isinstance(t, dict)]
            assert len(historical) == 1
            assert historical[0]["topic"] == "From previous conversation"

    @pytest.mark.asyncio
    async def test_thread_db_failure_falls_back_to_extraction(self, mock_session, pipeline_context):
        """DB failure should fall back to extracted_threads."""
        pipeline_context.extracted_threads = ["Fallback thread"]

        with patch(_THOUGHT_REPO) as MockThoughtRepo, \
             patch(_THREAD_REPO) as MockThreadRepo, \
             patch(_CONV_REPO) as MockConvRepo, \
             patch(_USER_REPO) as MockUserRepo, \
             patch(_GET_SETTINGS, return_value=_make_settings_mock()):

            thought_repo = AsyncMock()
            thought_repo.get_active_thoughts.return_value = []
            MockThoughtRepo.return_value = thought_repo

            thread_repo = AsyncMock()
            thread_repo.get_open_threads.side_effect = Exception("DB gone")
            MockThreadRepo.return_value = thread_repo

            MockConvRepo.return_value = _make_conv_repo_mock()
            MockUserRepo.return_value = _make_user_repo_mock()

            stage = PromptBuilderStage(session=mock_session)
            await stage._enrich_context(pipeline_context)

            # Should fall back to extracted threads
            assert pipeline_context.open_threads == ["Fallback thread"]

    @pytest.mark.asyncio
    async def test_no_session_falls_back_to_extraction(self, pipeline_context):
        """With no session, should fall back to extracted_threads (no DB call)."""
        pipeline_context.extracted_threads = ["Extracted only thread"]

        stage = PromptBuilderStage(session=None)
        await stage._enrich_context(pipeline_context)

        # No session — should use extracted_threads directly
        assert pipeline_context.open_threads == ["Extracted only thread"]
        # active_thoughts stays empty
        assert pipeline_context.active_thoughts == []

    @pytest.mark.asyncio
    async def test_empty_extraction_no_session_leaves_open_threads_empty(self, pipeline_context):
        """With no session and no extracted_threads, open_threads stays empty."""
        pipeline_context.extracted_threads = []

        stage = PromptBuilderStage(session=None)
        await stage._enrich_context(pipeline_context)

        assert pipeline_context.open_threads == []
