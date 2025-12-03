"""Tests for ConversationThreadRepository class.

TDD Tests for context engineering (spec 012) - Thread tracking

Acceptance Criteria:
- AC-1: create_thread() creates valid thread types
- AC-2: create_thread() raises ValueError for invalid types
- AC-3: get_open_threads() returns only open threads
- AC-4: get_threads_for_prompt() groups by type
- AC-5: resolve_thread() sets status and timestamp
- AC-6: bulk operations work correctly
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.context import ConversationThread, THREAD_TYPES


class TestConversationThreadRepository:
    """Test suite for ConversationThreadRepository."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock AsyncSession."""
        session = AsyncMock(spec=AsyncSession)
        session.get = AsyncMock()
        session.add = MagicMock()
        session.delete = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.execute = AsyncMock()
        return session

    # ========================================
    # AC-1: create_thread() creates valid thread types
    # ========================================
    @pytest.mark.asyncio
    @pytest.mark.parametrize("thread_type", THREAD_TYPES)
    async def test_create_thread_valid_types(self, mock_session: AsyncMock, thread_type: str):
        """AC-1: create_thread() creates all valid thread types."""
        from nikita.db.repositories.thread_repository import ConversationThreadRepository

        user_id = uuid4()
        content = f"Test {thread_type} content"

        # Mock the create method from base class
        async def mock_create(entity):
            return entity

        repo = ConversationThreadRepository(mock_session)
        with patch.object(repo, "create", side_effect=mock_create):
            result = await repo.create_thread(
                user_id=user_id,
                thread_type=thread_type,
                content=content,
            )

        assert result.user_id == user_id
        assert result.thread_type == thread_type
        assert result.content == content
        assert result.status == "open"

    # ========================================
    # AC-2: create_thread() raises ValueError for invalid types
    # ========================================
    @pytest.mark.asyncio
    async def test_create_thread_invalid_type_raises(self, mock_session: AsyncMock):
        """AC-2: create_thread() raises ValueError for invalid thread types."""
        from nikita.db.repositories.thread_repository import ConversationThreadRepository

        repo = ConversationThreadRepository(mock_session)

        with pytest.raises(ValueError, match="Invalid thread_type"):
            await repo.create_thread(
                user_id=uuid4(),
                thread_type="invalid_type",
                content="Test content",
            )

    # ========================================
    # AC-3: get_open_threads() returns only open threads
    # ========================================
    @pytest.mark.asyncio
    async def test_get_open_threads_returns_only_open(self, mock_session: AsyncMock):
        """AC-3: get_open_threads() returns only threads with status='open'."""
        from nikita.db.repositories.thread_repository import ConversationThreadRepository

        user_id = uuid4()
        open_thread = ConversationThread(
            id=uuid4(),
            user_id=user_id,
            thread_type="follow_up",
            content="Open thread",
            status="open",
            created_at=datetime.now(UTC),
        )

        # Mock scalars chain
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [open_thread]
        mock_session.execute.return_value = mock_result

        repo = ConversationThreadRepository(mock_session)
        result = await repo.get_open_threads(user_id=user_id)

        assert len(result) == 1
        assert result[0].status == "open"
        assert result[0].content == "Open thread"

    @pytest.mark.asyncio
    async def test_get_open_threads_filters_by_type(self, mock_session: AsyncMock):
        """AC-3b: get_open_threads() can filter by thread_type."""
        from nikita.db.repositories.thread_repository import ConversationThreadRepository

        user_id = uuid4()
        question_thread = ConversationThread(
            id=uuid4(),
            user_id=user_id,
            thread_type="question",
            content="Unanswered question",
            status="open",
            created_at=datetime.now(UTC),
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [question_thread]
        mock_session.execute.return_value = mock_result

        repo = ConversationThreadRepository(mock_session)
        result = await repo.get_open_threads(user_id=user_id, thread_type="question")

        assert len(result) == 1
        assert result[0].thread_type == "question"

    # ========================================
    # AC-4: get_threads_for_prompt() groups by type
    # ========================================
    @pytest.mark.asyncio
    async def test_get_threads_for_prompt_groups_by_type(self, mock_session: AsyncMock):
        """AC-4: get_threads_for_prompt() returns dict grouped by thread type."""
        from nikita.db.repositories.thread_repository import ConversationThreadRepository

        user_id = uuid4()

        # Create threads for different types
        follow_up = ConversationThread(
            id=uuid4(),
            user_id=user_id,
            thread_type="follow_up",
            content="Follow up content",
            status="open",
            created_at=datetime.now(UTC),
        )
        question = ConversationThread(
            id=uuid4(),
            user_id=user_id,
            thread_type="question",
            content="Question content",
            status="open",
            created_at=datetime.now(UTC),
        )

        repo = ConversationThreadRepository(mock_session)

        # Mock get_open_threads to return different results per call
        call_count = 0

        async def mock_get_open_threads(user_id, thread_type=None, limit=5):
            nonlocal call_count
            call_count += 1
            if thread_type == "follow_up":
                return [follow_up]
            elif thread_type == "question":
                return [question]
            return []

        with patch.object(repo, "get_open_threads", side_effect=mock_get_open_threads):
            result = await repo.get_threads_for_prompt(user_id=user_id, max_per_type=5)

        assert "follow_up" in result
        assert "question" in result
        assert len(result["follow_up"]) == 1
        assert len(result["question"]) == 1
        assert result["follow_up"][0].content == "Follow up content"
        assert result["question"][0].content == "Question content"

    # ========================================
    # AC-5: resolve_thread() sets status and timestamp
    # ========================================
    @pytest.mark.asyncio
    async def test_resolve_thread_sets_status_and_timestamp(self, mock_session: AsyncMock):
        """AC-5: resolve_thread() sets status='resolved' and resolved_at timestamp."""
        from nikita.db.repositories.thread_repository import ConversationThreadRepository

        thread_id = uuid4()
        thread = ConversationThread(
            id=thread_id,
            user_id=uuid4(),
            thread_type="follow_up",
            content="Thread to resolve",
            status="open",
            created_at=datetime.now(UTC),
        )

        repo = ConversationThreadRepository(mock_session)

        # Mock get method
        with patch.object(repo, "get", return_value=thread):
            result = await repo.resolve_thread(thread_id)

        assert result.status == "resolved"
        assert result.resolved_at is not None
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once_with(thread)

    @pytest.mark.asyncio
    async def test_resolve_thread_not_found_raises(self, mock_session: AsyncMock):
        """AC-5b: resolve_thread() raises ValueError if thread not found."""
        from nikita.db.repositories.thread_repository import ConversationThreadRepository

        repo = ConversationThreadRepository(mock_session)

        with patch.object(repo, "get", return_value=None):
            with pytest.raises(ValueError, match="not found"):
                await repo.resolve_thread(uuid4())

    @pytest.mark.asyncio
    async def test_expire_thread_sets_expired_status(self, mock_session: AsyncMock):
        """AC-5c: expire_thread() sets status='expired' and resolved_at."""
        from nikita.db.repositories.thread_repository import ConversationThreadRepository

        thread_id = uuid4()
        thread = ConversationThread(
            id=thread_id,
            user_id=uuid4(),
            thread_type="topic",
            content="Thread to expire",
            status="open",
            created_at=datetime.now(UTC),
        )

        repo = ConversationThreadRepository(mock_session)

        with patch.object(repo, "get", return_value=thread):
            result = await repo.expire_thread(thread_id)

        assert result.status == "expired"
        assert result.resolved_at is not None

    # ========================================
    # AC-6: Bulk operations work correctly
    # ========================================
    @pytest.mark.asyncio
    async def test_bulk_create_threads_creates_all(self, mock_session: AsyncMock):
        """AC-6: bulk_create_threads() creates all threads."""
        from nikita.db.repositories.thread_repository import ConversationThreadRepository

        user_id = uuid4()
        threads_data = [
            {"thread_type": "follow_up", "content": "Follow up 1"},
            {"thread_type": "question", "content": "Question 1"},
            {"thread_type": "promise", "content": "Promise 1"},
        ]

        created_threads = []

        async def mock_create_thread(user_id, thread_type, content, source_conversation_id=None):
            thread = ConversationThread(
                id=uuid4(),
                user_id=user_id,
                thread_type=thread_type,
                content=content,
                status="open",
                created_at=datetime.now(UTC),
            )
            created_threads.append(thread)
            return thread

        repo = ConversationThreadRepository(mock_session)

        with patch.object(repo, "create_thread", side_effect=mock_create_thread):
            result = await repo.bulk_create_threads(
                user_id=user_id,
                threads_data=threads_data,
            )

        assert len(result) == 3
        assert result[0].thread_type == "follow_up"
        assert result[1].thread_type == "question"
        assert result[2].thread_type == "promise"

    @pytest.mark.asyncio
    async def test_bulk_resolve_threads_resolves_found(self, mock_session: AsyncMock):
        """AC-6b: bulk_resolve_threads() resolves found threads and skips missing."""
        from nikita.db.repositories.thread_repository import ConversationThreadRepository

        thread_id_1 = uuid4()
        thread_id_2 = uuid4()
        thread_id_missing = uuid4()

        resolved_count = 0

        async def mock_resolve_thread(thread_id):
            nonlocal resolved_count
            if thread_id in [thread_id_1, thread_id_2]:
                resolved_count += 1
                return ConversationThread(
                    id=thread_id,
                    user_id=uuid4(),
                    thread_type="follow_up",
                    content="Resolved",
                    status="resolved",
                    created_at=datetime.now(UTC),
                )
            else:
                raise ValueError(f"Thread {thread_id} not found")

        repo = ConversationThreadRepository(mock_session)

        with patch.object(repo, "resolve_thread", side_effect=mock_resolve_thread):
            result = await repo.bulk_resolve_threads(
                thread_ids=[thread_id_1, thread_id_2, thread_id_missing]
            )

        # Should return 2 (the found ones), not raise for missing
        assert result == 2
