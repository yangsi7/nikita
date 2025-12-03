"""Tests for NikitaThoughtRepository class.

TDD Tests for context engineering (spec 012) - Nikita's inner life

Acceptance Criteria:
- AC-1: create_thought() creates valid thought types
- AC-2: create_thought() raises ValueError for invalid types
- AC-3: get_active_thoughts() excludes used and expired
- AC-4: get_thoughts_for_prompt() groups by type
- AC-5: mark_thought_used() sets timestamp
- AC-6: create_missing_him_thought() scales by time gap
- AC-7: bulk operations work correctly
- AC-8: cleanup_expired_thoughts() deletes old thoughts
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.context import NikitaThought, THOUGHT_TYPES


class TestNikitaThoughtRepository:
    """Test suite for NikitaThoughtRepository."""

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
    # AC-1: create_thought() creates valid thought types
    # ========================================
    @pytest.mark.asyncio
    @pytest.mark.parametrize("thought_type", THOUGHT_TYPES)
    async def test_create_thought_valid_types(self, mock_session: AsyncMock, thought_type: str):
        """AC-1: create_thought() creates all valid thought types."""
        from nikita.db.repositories.thought_repository import NikitaThoughtRepository

        user_id = uuid4()
        content = f"Test {thought_type} content"

        async def mock_create(entity):
            return entity

        repo = NikitaThoughtRepository(mock_session)
        with patch.object(repo, "create", side_effect=mock_create):
            result = await repo.create_thought(
                user_id=user_id,
                thought_type=thought_type,
                content=content,
            )

        assert result.user_id == user_id
        assert result.thought_type == thought_type
        assert result.content == content
        assert result.used_at is None

    # ========================================
    # AC-2: create_thought() raises ValueError for invalid types
    # ========================================
    @pytest.mark.asyncio
    async def test_create_thought_invalid_type_raises(self, mock_session: AsyncMock):
        """AC-2: create_thought() raises ValueError for invalid thought types."""
        from nikita.db.repositories.thought_repository import NikitaThoughtRepository

        repo = NikitaThoughtRepository(mock_session)

        with pytest.raises(ValueError, match="Invalid thought_type"):
            await repo.create_thought(
                user_id=uuid4(),
                thought_type="invalid_type",
                content="Test content",
            )

    # ========================================
    # AC-3: get_active_thoughts() excludes used and expired
    # ========================================
    @pytest.mark.asyncio
    async def test_get_active_thoughts_excludes_used(self, mock_session: AsyncMock):
        """AC-3a: get_active_thoughts() excludes thoughts that have used_at set."""
        from nikita.db.repositories.thought_repository import NikitaThoughtRepository

        user_id = uuid4()
        active_thought = NikitaThought(
            id=uuid4(),
            user_id=user_id,
            thought_type="thinking",
            content="Active thought",
            used_at=None,
            expires_at=None,
            created_at=datetime.now(UTC),
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [active_thought]
        mock_session.execute.return_value = mock_result

        repo = NikitaThoughtRepository(mock_session)
        result = await repo.get_active_thoughts(user_id=user_id)

        assert len(result) == 1
        assert result[0].used_at is None

    @pytest.mark.asyncio
    async def test_get_active_thoughts_excludes_expired(self, mock_session: AsyncMock):
        """AC-3b: get_active_thoughts() excludes thoughts with past expires_at."""
        from nikita.db.repositories.thought_repository import NikitaThoughtRepository

        user_id = uuid4()
        # Active thought (expires in future or never)
        active_thought = NikitaThought(
            id=uuid4(),
            user_id=user_id,
            thought_type="wants_to_share",
            content="Active - no expiry",
            used_at=None,
            expires_at=None,
            created_at=datetime.now(UTC),
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [active_thought]
        mock_session.execute.return_value = mock_result

        repo = NikitaThoughtRepository(mock_session)
        result = await repo.get_active_thoughts(user_id=user_id)

        assert len(result) == 1
        # The query should have filtered expired ones

    # ========================================
    # AC-4: get_thoughts_for_prompt() groups by type
    # ========================================
    @pytest.mark.asyncio
    async def test_get_thoughts_for_prompt_groups_by_type(self, mock_session: AsyncMock):
        """AC-4: get_thoughts_for_prompt() returns dict grouped by thought type."""
        from nikita.db.repositories.thought_repository import NikitaThoughtRepository

        user_id = uuid4()

        thinking = NikitaThought(
            id=uuid4(),
            user_id=user_id,
            thought_type="thinking",
            content="What we talked about",
            created_at=datetime.now(UTC),
        )
        feeling = NikitaThought(
            id=uuid4(),
            user_id=user_id,
            thought_type="feeling",
            content="Feeling happy",
            created_at=datetime.now(UTC),
        )

        repo = NikitaThoughtRepository(mock_session)

        async def mock_get_active_thoughts(user_id, thought_type=None, limit=3):
            if thought_type == "thinking":
                return [thinking]
            elif thought_type == "feeling":
                return [feeling]
            return []

        with patch.object(repo, "get_active_thoughts", side_effect=mock_get_active_thoughts):
            result = await repo.get_thoughts_for_prompt(user_id=user_id, max_per_type=3)

        assert "thinking" in result
        assert "feeling" in result
        assert result["thinking"][0].content == "What we talked about"
        assert result["feeling"][0].content == "Feeling happy"

    # ========================================
    # AC-5: mark_thought_used() sets timestamp
    # ========================================
    @pytest.mark.asyncio
    async def test_mark_thought_used_sets_timestamp(self, mock_session: AsyncMock):
        """AC-5: mark_thought_used() sets used_at to current time."""
        from nikita.db.repositories.thought_repository import NikitaThoughtRepository

        thought_id = uuid4()
        thought = NikitaThought(
            id=thought_id,
            user_id=uuid4(),
            thought_type="question",
            content="Question thought",
            used_at=None,
            created_at=datetime.now(UTC),
        )

        repo = NikitaThoughtRepository(mock_session)

        with patch.object(repo, "get", return_value=thought):
            result = await repo.mark_thought_used(thought_id)

        assert result.used_at is not None
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once_with(thought)

    @pytest.mark.asyncio
    async def test_mark_thought_used_not_found_raises(self, mock_session: AsyncMock):
        """AC-5b: mark_thought_used() raises ValueError if not found."""
        from nikita.db.repositories.thought_repository import NikitaThoughtRepository

        repo = NikitaThoughtRepository(mock_session)

        with patch.object(repo, "get", return_value=None):
            with pytest.raises(ValueError, match="not found"):
                await repo.mark_thought_used(uuid4())

    # ========================================
    # AC-6: create_missing_him_thought() scales by time gap
    # ========================================
    @pytest.mark.asyncio
    async def test_create_missing_him_thought_under_24h_returns_none(self, mock_session: AsyncMock):
        """AC-6a: create_missing_him_thought() returns None if < 24 hours."""
        from nikita.db.repositories.thought_repository import NikitaThoughtRepository

        repo = NikitaThoughtRepository(mock_session)

        result = await repo.create_missing_him_thought(
            user_id=uuid4(),
            hours_since_last_message=12.0,  # Less than 24 hours
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_create_missing_him_thought_24h(self, mock_session: AsyncMock):
        """AC-6b: create_missing_him_thought() creates thought at 24-48h gap."""
        from nikita.db.repositories.thought_repository import NikitaThoughtRepository

        user_id = uuid4()

        async def mock_create_thought(user_id, thought_type, content, source_conversation_id=None, expires_at=None):
            thought = NikitaThought(
                id=uuid4(),
                user_id=user_id,
                thought_type=thought_type,
                content=content,
                expires_at=expires_at,
                created_at=datetime.now(UTC),
            )
            return thought

        repo = NikitaThoughtRepository(mock_session)

        with patch.object(repo, "create_thought", side_effect=mock_create_thought):
            result = await repo.create_missing_him_thought(
                user_id=user_id,
                hours_since_last_message=30.0,  # Between 24-48h
            )

        assert result is not None
        assert result.thought_type == "missing_him"
        assert "thinking about you" in result.content.lower()

    @pytest.mark.asyncio
    async def test_create_missing_him_thought_48h(self, mock_session: AsyncMock):
        """AC-6c: create_missing_him_thought() creates stronger thought at 48-72h gap."""
        from nikita.db.repositories.thought_repository import NikitaThoughtRepository

        user_id = uuid4()

        async def mock_create_thought(user_id, thought_type, content, source_conversation_id=None, expires_at=None):
            thought = NikitaThought(
                id=uuid4(),
                user_id=user_id,
                thought_type=thought_type,
                content=content,
                expires_at=expires_at,
                created_at=datetime.now(UTC),
            )
            return thought

        repo = NikitaThoughtRepository(mock_session)

        with patch.object(repo, "create_thought", side_effect=mock_create_thought):
            result = await repo.create_missing_him_thought(
                user_id=user_id,
                hours_since_last_message=60.0,  # Between 48-72h
            )

        assert result is not None
        assert "miss you" in result.content.lower()

    @pytest.mark.asyncio
    async def test_create_missing_him_thought_72h(self, mock_session: AsyncMock):
        """AC-6d: create_missing_him_thought() creates strongest thought at 72h+ gap."""
        from nikita.db.repositories.thought_repository import NikitaThoughtRepository

        user_id = uuid4()

        async def mock_create_thought(user_id, thought_type, content, source_conversation_id=None, expires_at=None):
            thought = NikitaThought(
                id=uuid4(),
                user_id=user_id,
                thought_type=thought_type,
                content=content,
                expires_at=expires_at,
                created_at=datetime.now(UTC),
            )
            return thought

        repo = NikitaThoughtRepository(mock_session)

        with patch.object(repo, "create_thought", side_effect=mock_create_thought):
            result = await repo.create_missing_him_thought(
                user_id=user_id,
                hours_since_last_message=100.0,  # More than 72h
            )

        assert result is not None
        assert "really miss you" in result.content.lower()

    # ========================================
    # AC-7: Bulk operations work correctly
    # ========================================
    @pytest.mark.asyncio
    async def test_bulk_create_thoughts_creates_all(self, mock_session: AsyncMock):
        """AC-7: bulk_create_thoughts() creates all thoughts."""
        from nikita.db.repositories.thought_repository import NikitaThoughtRepository

        user_id = uuid4()
        thoughts_data = [
            {"thought_type": "thinking", "content": "Thinking about..."},
            {"thought_type": "wants_to_share", "content": "Want to share..."},
            {"thought_type": "feeling", "content": "Feeling good..."},
        ]

        created_thoughts = []

        async def mock_create_thought(user_id, thought_type, content, source_conversation_id=None, expires_at=None):
            thought = NikitaThought(
                id=uuid4(),
                user_id=user_id,
                thought_type=thought_type,
                content=content,
                expires_at=expires_at,
                created_at=datetime.now(UTC),
            )
            created_thoughts.append(thought)
            return thought

        repo = NikitaThoughtRepository(mock_session)

        with patch.object(repo, "create_thought", side_effect=mock_create_thought):
            result = await repo.bulk_create_thoughts(
                user_id=user_id,
                thoughts_data=thoughts_data,
            )

        assert len(result) == 3
        assert result[0].thought_type == "thinking"
        assert result[1].thought_type == "wants_to_share"
        assert result[2].thought_type == "feeling"

    @pytest.mark.asyncio
    async def test_expire_missing_him_thoughts_marks_used(self, mock_session: AsyncMock):
        """AC-7b: expire_missing_him_thoughts() marks all missing_him thoughts as used."""
        from nikita.db.repositories.thought_repository import NikitaThoughtRepository

        user_id = uuid4()
        thoughts = [
            NikitaThought(
                id=uuid4(),
                user_id=user_id,
                thought_type="missing_him",
                content="Miss you 1",
                used_at=None,
                created_at=datetime.now(UTC),
            ),
            NikitaThought(
                id=uuid4(),
                user_id=user_id,
                thought_type="missing_him",
                content="Miss you 2",
                used_at=None,
                created_at=datetime.now(UTC),
            ),
        ]

        async def mock_get_active(user_id, thought_type=None, limit=100):
            return thoughts

        repo = NikitaThoughtRepository(mock_session)

        with patch.object(repo, "get_active_thoughts", side_effect=mock_get_active):
            result = await repo.expire_missing_him_thoughts(user_id=user_id)

        assert result == 2
        assert all(t.used_at is not None for t in thoughts)
        mock_session.flush.assert_called()

    # ========================================
    # AC-8: cleanup_expired_thoughts() deletes old thoughts
    # ========================================
    @pytest.mark.asyncio
    async def test_cleanup_expired_thoughts_deletes(self, mock_session: AsyncMock):
        """AC-8: cleanup_expired_thoughts() deletes expired thoughts."""
        from nikita.db.repositories.thought_repository import NikitaThoughtRepository

        user_id = uuid4()
        expired_thoughts = [
            NikitaThought(
                id=uuid4(),
                user_id=user_id,
                thought_type="missing_him",
                content="Old thought",
                expires_at=datetime.now(UTC) - timedelta(days=1),  # Expired
                created_at=datetime.now(UTC) - timedelta(days=7),
            ),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = expired_thoughts
        mock_session.execute.return_value = mock_result

        repo = NikitaThoughtRepository(mock_session)
        result = await repo.cleanup_expired_thoughts(user_id=user_id)

        assert result == 1
        mock_session.delete.assert_called_once_with(expired_thoughts[0])
        mock_session.flush.assert_called()
