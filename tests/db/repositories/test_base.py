"""Tests for BaseRepository class.

TDD Tests for T1: Create Base Repository Class

Acceptance Criteria:
- AC-T1.1: BaseRepository class accepts AsyncSession in __init__
- AC-T1.2: BaseRepository exposes session property for subclasses
- AC-T1.3: BaseRepository has generic CRUD methods (get, create, update, delete)
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.base import Base


# Test model for repository tests
class MockModel(Base):
    """Mock model for testing."""

    __tablename__ = "mock_models"

    from sqlalchemy import Column, String
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(100))


class TestBaseRepository:
    """Test suite for BaseRepository - T1 ACs."""

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
    # AC-T1.1: BaseRepository accepts AsyncSession in __init__
    # ========================================
    def test_base_repository_accepts_async_session(self, mock_session: AsyncMock):
        """AC-T1.1: BaseRepository class accepts AsyncSession in __init__."""
        from nikita.db.repositories.base import BaseRepository

        # Should not raise
        repo = BaseRepository(mock_session, MockModel)

        # Verify session was stored
        assert repo._session is mock_session

    def test_base_repository_requires_session(self):
        """AC-T1.1: BaseRepository requires session parameter."""
        from nikita.db.repositories.base import BaseRepository

        with pytest.raises(TypeError):
            BaseRepository()  # type: ignore

    # ========================================
    # AC-T1.2: BaseRepository exposes session property for subclasses
    # ========================================
    def test_base_repository_session_property(self, mock_session: AsyncMock):
        """AC-T1.2: BaseRepository exposes session property for subclasses."""
        from nikita.db.repositories.base import BaseRepository

        repo = BaseRepository(mock_session, MockModel)

        # Session should be accessible via property
        assert repo.session is mock_session

    def test_session_property_readonly(self, mock_session: AsyncMock):
        """AC-T1.2: Session property should be read-only."""
        from nikita.db.repositories.base import BaseRepository

        repo = BaseRepository(mock_session, MockModel)

        # Attempting to set should raise AttributeError
        with pytest.raises(AttributeError):
            repo.session = AsyncMock()  # type: ignore

    # ========================================
    # AC-T1.3: BaseRepository has generic CRUD methods
    # ========================================
    @pytest.mark.asyncio
    async def test_get_method_returns_entity(self, mock_session: AsyncMock):
        """AC-T1.3: get(id) returns entity by primary key."""
        from nikita.db.repositories.base import BaseRepository

        test_id = uuid4()
        expected_entity = MockModel(id=test_id, name="test")
        mock_session.get.return_value = expected_entity

        repo = BaseRepository(mock_session, MockModel)
        result = await repo.get(test_id)

        mock_session.get.assert_called_once_with(MockModel, test_id)
        assert result is expected_entity

    @pytest.mark.asyncio
    async def test_get_method_returns_none_for_missing(self, mock_session: AsyncMock):
        """AC-T1.3: get(id) returns None if entity not found."""
        from nikita.db.repositories.base import BaseRepository

        mock_session.get.return_value = None

        repo = BaseRepository(mock_session, MockModel)
        result = await repo.get(uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_create_method_adds_entity(self, mock_session: AsyncMock):
        """AC-T1.3: create(entity) adds and returns entity."""
        from nikita.db.repositories.base import BaseRepository

        entity = MockModel(name="new entity")

        repo = BaseRepository(mock_session, MockModel)
        result = await repo.create(entity)

        mock_session.add.assert_called_once_with(entity)
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once_with(entity)
        assert result is entity

    @pytest.mark.asyncio
    async def test_update_method_flushes_changes(self, mock_session: AsyncMock):
        """AC-T1.3: update(entity) flushes entity changes."""
        from nikita.db.repositories.base import BaseRepository

        entity = MockModel(id=uuid4(), name="updated")

        repo = BaseRepository(mock_session, MockModel)
        result = await repo.update(entity)

        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once_with(entity)
        assert result is entity

    @pytest.mark.asyncio
    async def test_delete_method_removes_entity(self, mock_session: AsyncMock):
        """AC-T1.3: delete(entity) removes entity from session."""
        from nikita.db.repositories.base import BaseRepository

        entity = MockModel(id=uuid4(), name="to delete")

        repo = BaseRepository(mock_session, MockModel)
        await repo.delete(entity)

        mock_session.delete.assert_called_once_with(entity)
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_by_id_method(self, mock_session: AsyncMock):
        """AC-T1.3: delete_by_id(id) gets and deletes entity."""
        from nikita.db.repositories.base import BaseRepository

        test_id = uuid4()
        entity = MockModel(id=test_id, name="to delete")
        mock_session.get.return_value = entity

        repo = BaseRepository(mock_session, MockModel)
        result = await repo.delete_by_id(test_id)

        mock_session.get.assert_called_once_with(MockModel, test_id)
        mock_session.delete.assert_called_once_with(entity)
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_by_id_returns_false_for_missing(
        self, mock_session: AsyncMock
    ):
        """AC-T1.3: delete_by_id(id) returns False if entity not found."""
        from nikita.db.repositories.base import BaseRepository

        mock_session.get.return_value = None

        repo = BaseRepository(mock_session, MockModel)
        result = await repo.delete_by_id(uuid4())

        assert result is False
        mock_session.delete.assert_not_called()


class TestBaseRepositorySubclassing:
    """Test that BaseRepository can be properly subclassed."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock AsyncSession."""
        return AsyncMock(spec=AsyncSession)

    def test_subclass_can_access_session(self, mock_session: AsyncMock):
        """Verify subclasses can access session via property."""
        from nikita.db.repositories.base import BaseRepository

        class UserRepo(BaseRepository[MockModel]):
            def custom_method(self):
                # Should be able to access session
                return self.session

        repo = UserRepo(mock_session, MockModel)
        assert repo.custom_method() is mock_session

    def test_subclass_inherits_crud(self, mock_session: AsyncMock):
        """Verify subclasses inherit CRUD methods."""
        from nikita.db.repositories.base import BaseRepository

        class UserRepo(BaseRepository[MockModel]):
            pass

        repo = UserRepo(mock_session, MockModel)

        # Should have all CRUD methods
        assert hasattr(repo, "get")
        assert hasattr(repo, "create")
        assert hasattr(repo, "update")
        assert hasattr(repo, "delete")
        assert hasattr(repo, "delete_by_id")
