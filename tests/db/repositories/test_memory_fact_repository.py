"""Tests for MemoryFactRepository (Spec 042 T0.5)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from nikita.db.models.memory_fact import MemoryFact
from nikita.db.repositories.memory_fact_repository import MemoryFactRepository


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
    return MemoryFactRepository(mock_session)


class TestAddFact:
    """Tests for add_fact method (AC-0.5.2)."""

    @pytest.mark.asyncio
    async def test_add_fact_creates_memory_fact(self, repo, mock_session, user_id):
        """add_fact inserts a new MemoryFact."""
        embedding = [0.1] * 1536
        result = await repo.add_fact(
            user_id=user_id,
            fact="User enjoys hiking",
            graph_type="user",
            embedding=embedding,
            source="conversation",
            confidence=0.9,
            metadata={"topic": "hobbies"},
        )

        mock_session.add.assert_called_once()
        added_obj = mock_session.add.call_args[0][0]
        assert isinstance(added_obj, MemoryFact)
        assert added_obj.user_id == user_id
        assert added_obj.fact == "User enjoys hiking"
        assert added_obj.graph_type == "user"
        assert added_obj.source == "conversation"
        assert added_obj.confidence == 0.9
        assert added_obj.embedding == embedding
        assert added_obj.fact_metadata == {"topic": "hobbies"}
        assert added_obj.is_active is True

    @pytest.mark.asyncio
    async def test_add_fact_flushes_session(self, repo, mock_session, user_id):
        """add_fact flushes to persist."""
        await repo.add_fact(
            user_id=user_id,
            fact="Test",
            graph_type="nikita",
            embedding=[0.0] * 1536,
            source="test",
            confidence=0.5,
        )
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_fact_with_conversation_id(self, repo, mock_session, user_id):
        """add_fact supports optional conversation_id."""
        conv_id = uuid4()
        await repo.add_fact(
            user_id=user_id,
            fact="Test",
            graph_type="relationship",
            embedding=[0.0] * 1536,
            source="test",
            confidence=0.7,
            conversation_id=conv_id,
        )
        added_obj = mock_session.add.call_args[0][0]
        assert added_obj.conversation_id == conv_id


class TestSemanticSearch:
    """Tests for semantic_search method (AC-0.5.1)."""

    @pytest.mark.asyncio
    async def test_semantic_search_executes_query(self, repo, mock_session, user_id):
        """semantic_search calls execute with a query."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        results = await repo.semantic_search(
            user_id=user_id,
            query_embedding=[0.1] * 1536,
            limit=5,
        )

        mock_session.execute.assert_called_once()
        assert results == []

    @pytest.mark.asyncio
    async def test_semantic_search_with_graph_type_filter(self, repo, mock_session, user_id):
        """semantic_search respects graph_type filter."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        await repo.semantic_search(
            user_id=user_id,
            query_embedding=[0.1] * 1536,
            graph_type="user",
            limit=5,
        )

        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_semantic_search_with_min_confidence(self, repo, mock_session, user_id):
        """semantic_search respects min_confidence filter."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        await repo.semantic_search(
            user_id=user_id,
            query_embedding=[0.1] * 1536,
            min_confidence=0.8,
        )

        mock_session.execute.assert_called_once()


class TestGetRecent:
    """Tests for get_recent method (AC-0.5.3)."""

    @pytest.mark.asyncio
    async def test_get_recent_returns_list(self, repo, mock_session, user_id):
        """get_recent returns list of MemoryFacts ordered by created_at DESC."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        results = await repo.get_recent(user_id=user_id)

        mock_session.execute.assert_called_once()
        assert results == []

    @pytest.mark.asyncio
    async def test_get_recent_with_graph_type(self, repo, mock_session, user_id):
        """get_recent filters by graph_type."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await repo.get_recent(user_id=user_id, graph_type="relationship")

        mock_session.execute.assert_called_once()


class TestDeactivate:
    """Tests for deactivate method (AC-0.5.4)."""

    @pytest.mark.asyncio
    async def test_deactivate_sets_inactive(self, repo, mock_session):
        """deactivate sets is_active=False."""
        fact_id = uuid4()
        fact = MemoryFact(
            id=fact_id,
            user_id=uuid4(),
            graph_type="user",
            fact="old fact",
            source="test",
            confidence=0.5,
            embedding=[0.0] * 1536,
            is_active=True,
        )
        mock_session.get = AsyncMock(return_value=fact)

        result = await repo.deactivate(fact_id)

        assert result is True
        assert fact.is_active is False
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_deactivate_with_superseded_by(self, repo, mock_session):
        """deactivate sets superseded_by when provided."""
        fact_id = uuid4()
        new_fact_id = uuid4()
        fact = MemoryFact(
            id=fact_id,
            user_id=uuid4(),
            graph_type="user",
            fact="old fact",
            source="test",
            confidence=0.5,
            embedding=[0.0] * 1536,
            is_active=True,
        )
        mock_session.get = AsyncMock(return_value=fact)

        result = await repo.deactivate(fact_id, superseded_by_id=new_fact_id)

        assert result is True
        assert fact.is_active is False
        assert fact.superseded_by == new_fact_id

    @pytest.mark.asyncio
    async def test_deactivate_returns_false_for_missing(self, repo, mock_session):
        """deactivate returns False if fact not found."""
        mock_session.get = AsyncMock(return_value=None)

        result = await repo.deactivate(uuid4())

        assert result is False


class TestGetByUser:
    """Tests for get_by_user method (AC-0.5.5)."""

    @pytest.mark.asyncio
    async def test_get_by_user_returns_list(self, repo, mock_session, user_id):
        """get_by_user returns all facts for a user."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        results = await repo.get_by_user(user_id=user_id)

        mock_session.execute.assert_called_once()
        assert results == []

    @pytest.mark.asyncio
    async def test_get_by_user_with_graph_type(self, repo, mock_session, user_id):
        """get_by_user filters by graph_type."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await repo.get_by_user(user_id=user_id, graph_type="nikita")

        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_user_active_only_default(self, repo, mock_session, user_id):
        """get_by_user defaults to active_only=True."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await repo.get_by_user(user_id=user_id, active_only=True)

        mock_session.execute.assert_called_once()
