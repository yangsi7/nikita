"""Tests for PersistenceStage (Spec 067)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from nikita.pipeline.stages.persistence import PersistenceStage
from nikita.pipeline.models import PipelineContext

# Lazy imports inside persistence.py are patched at their actual module paths
_THOUGHT_REPO = "nikita.db.repositories.thought_repository.NikitaThoughtRepository"
_THREAD_REPO = "nikita.db.repositories.thread_repository.ConversationThreadRepository"


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.begin_nested = MagicMock(return_value=AsyncMock().__aenter__())
    return session


@pytest.fixture
def pipeline_context():
    return PipelineContext(
        conversation_id=uuid4(),
        user_id=uuid4(),
        started_at=datetime.now(timezone.utc),
        platform="text",
    )


class TestPersistenceStage:
    """Tests for PersistenceStage."""

    def test_stage_attributes(self):
        stage = PersistenceStage()
        assert stage.name == "persistence"
        assert stage.is_critical is False
        assert stage.timeout_seconds == 15.0

    @pytest.mark.asyncio
    async def test_no_session_skips(self, pipeline_context):
        stage = PersistenceStage(session=None)
        result = await stage._run(pipeline_context)
        assert result["thoughts_persisted"] == 0
        assert result["threads_persisted"] == 0
        assert result["skipped"] is True

    @pytest.mark.asyncio
    async def test_empty_extractions_skips(self, mock_session, pipeline_context):
        stage = PersistenceStage(session=mock_session)
        result = await stage._run(pipeline_context)
        assert result["thoughts_persisted"] == 0
        assert result["threads_persisted"] == 0

    @pytest.mark.asyncio
    async def test_persist_string_thoughts(self, mock_session, pipeline_context):
        """ExtractionStage produces list[str] — verify mapping to dicts."""
        pipeline_context.extracted_thoughts = [
            "She seems stressed about work",
            "I should ask about her weekend plans",
        ]

        mock_thoughts = [MagicMock(), MagicMock()]

        with patch(_THOUGHT_REPO) as MockRepo:
            repo_instance = AsyncMock()
            repo_instance.bulk_create_thoughts.return_value = mock_thoughts
            MockRepo.return_value = repo_instance

            stage = PersistenceStage(session=mock_session)
            result = await stage._run(pipeline_context)

            assert result["thoughts_persisted"] == 2
            assert pipeline_context.thoughts_persisted == 2

            # Verify mapping: str → dict with thought_type="reflection"
            call_args = repo_instance.bulk_create_thoughts.call_args
            thoughts_data = call_args.kwargs["thoughts_data"]
            assert len(thoughts_data) == 2
            assert thoughts_data[0] == {
                "thought_type": "reflection",
                "content": "She seems stressed about work",
            }
            assert thoughts_data[1] == {
                "thought_type": "reflection",
                "content": "I should ask about her weekend plans",
            }

    @pytest.mark.asyncio
    async def test_persist_dict_thoughts(self, mock_session, pipeline_context):
        """If thoughts come as dicts, use their types."""
        pipeline_context.extracted_thoughts = [
            {"thought_type": "worry", "content": "He hasn't texted back"},
            {"thought_type": "curiosity", "content": "What is he doing tonight"},
        ]

        mock_thoughts = [MagicMock(), MagicMock()]

        with patch(_THOUGHT_REPO) as MockRepo:
            repo_instance = AsyncMock()
            repo_instance.bulk_create_thoughts.return_value = mock_thoughts
            MockRepo.return_value = repo_instance

            stage = PersistenceStage(session=mock_session)
            result = await stage._run(pipeline_context)

            assert result["thoughts_persisted"] == 2
            call_args = repo_instance.bulk_create_thoughts.call_args
            thoughts_data = call_args.kwargs["thoughts_data"]
            assert thoughts_data[0]["thought_type"] == "worry"
            assert thoughts_data[1]["thought_type"] == "curiosity"

    @pytest.mark.asyncio
    async def test_persist_string_threads(self, mock_session, pipeline_context):
        """ExtractionStage produces list[str] for threads too."""
        pipeline_context.extracted_threads = [
            "Weekend trip planning",
            "That book she mentioned",
        ]

        mock_threads = [MagicMock(), MagicMock()]

        with patch(_THREAD_REPO) as MockRepo:
            repo_instance = AsyncMock()
            repo_instance.bulk_create_threads.return_value = mock_threads
            MockRepo.return_value = repo_instance

            stage = PersistenceStage(session=mock_session)
            result = await stage._run(pipeline_context)

            assert result["threads_persisted"] == 2
            assert pipeline_context.threads_persisted == 2

            call_args = repo_instance.bulk_create_threads.call_args
            threads_data = call_args.kwargs["threads_data"]
            assert threads_data[0] == {
                "thread_type": "unresolved",
                "content": "Weekend trip planning",
            }

    @pytest.mark.asyncio
    async def test_persist_dict_threads(self, mock_session, pipeline_context):
        pipeline_context.extracted_threads = [
            {"thread_type": "promise", "content": "Promised to call tomorrow"},
        ]

        mock_threads = [MagicMock()]

        with patch(_THREAD_REPO) as MockRepo:
            repo_instance = AsyncMock()
            repo_instance.bulk_create_threads.return_value = mock_threads
            MockRepo.return_value = repo_instance

            stage = PersistenceStage(session=mock_session)
            result = await stage._run(pipeline_context)

            assert result["threads_persisted"] == 1
            call_args = repo_instance.bulk_create_threads.call_args
            assert call_args.kwargs["threads_data"][0]["thread_type"] == "promise"

    @pytest.mark.asyncio
    async def test_thought_persist_failure_non_critical(self, mock_session, pipeline_context):
        """DB failure should not crash — returns 0 and continues."""
        pipeline_context.extracted_thoughts = ["A thought"]

        with patch(_THOUGHT_REPO) as MockRepo:
            repo_instance = AsyncMock()
            repo_instance.bulk_create_thoughts.side_effect = Exception("DB error")
            MockRepo.return_value = repo_instance

            stage = PersistenceStage(session=mock_session)
            result = await stage._run(pipeline_context)

            assert result["thoughts_persisted"] == 0
            assert result["threads_persisted"] == 0

    @pytest.mark.asyncio
    async def test_thread_persist_failure_non_critical(self, mock_session, pipeline_context):
        pipeline_context.extracted_threads = ["A thread"]

        with patch(_THREAD_REPO) as MockRepo:
            repo_instance = AsyncMock()
            repo_instance.bulk_create_threads.side_effect = Exception("DB error")
            MockRepo.return_value = repo_instance

            stage = PersistenceStage(session=mock_session)
            result = await stage._run(pipeline_context)

            assert result["thoughts_persisted"] == 0
            assert result["threads_persisted"] == 0

    @pytest.mark.asyncio
    async def test_both_thoughts_and_threads(self, mock_session, pipeline_context):
        """Both can be persisted in same run."""
        pipeline_context.extracted_thoughts = ["Thought 1"]
        pipeline_context.extracted_threads = ["Thread 1", "Thread 2"]

        with patch(_THOUGHT_REPO) as MockThoughtRepo, \
             patch(_THREAD_REPO) as MockThreadRepo:
            thought_repo = AsyncMock()
            thought_repo.bulk_create_thoughts.return_value = [MagicMock()]
            MockThoughtRepo.return_value = thought_repo

            thread_repo = AsyncMock()
            thread_repo.bulk_create_threads.return_value = [MagicMock(), MagicMock()]
            MockThreadRepo.return_value = thread_repo

            stage = PersistenceStage(session=mock_session)
            result = await stage._run(pipeline_context)

            assert result["thoughts_persisted"] == 1
            assert result["threads_persisted"] == 2

    @pytest.mark.asyncio
    async def test_source_conversation_id_passed(self, mock_session, pipeline_context):
        """Verify source_conversation_id is passed to bulk_create."""
        pipeline_context.extracted_thoughts = ["A thought"]

        with patch(_THOUGHT_REPO) as MockRepo:
            repo_instance = AsyncMock()
            repo_instance.bulk_create_thoughts.return_value = [MagicMock()]
            MockRepo.return_value = repo_instance

            stage = PersistenceStage(session=mock_session)
            await stage._run(pipeline_context)

            call_args = repo_instance.bulk_create_thoughts.call_args
            assert call_args.kwargs["source_conversation_id"] == pipeline_context.conversation_id
            assert call_args.kwargs["user_id"] == pipeline_context.user_id
