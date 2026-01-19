"""Tests for EntityManager (Spec 022, T007).

AC-T007.1: EntityManager class manages recurring entities
AC-T007.2: get_entities_by_type() method
AC-T007.3: seed_entities() method for new users
AC-T007.4: Unit tests for manager
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from nikita.life_simulation.entity_manager import (
    DEFAULT_ENTITIES,
    EntityManager,
    get_entity_manager,
)
from nikita.life_simulation.models import EntityType, NikitaEntity


class TestEntityManager:
    """Tests for EntityManager class (AC-T007.1)."""

    @pytest.fixture
    def mock_store(self):
        """Create mock EventStore."""
        store = MagicMock()
        store.get_entities = AsyncMock(return_value=[])
        store.get_entities_by_type = AsyncMock(return_value=[])
        store.save_entity = AsyncMock()
        store.save_entities = AsyncMock()
        store.entity_exists = AsyncMock(return_value=False)
        return store

    @pytest.fixture
    def manager(self, mock_store):
        """Create manager with mock store."""
        return EntityManager(store=mock_store)

    @pytest.fixture
    def user_id(self):
        """Test user ID."""
        return uuid4()

    # ==================== SEED ENTITIES TESTS (AC-T007.3) ====================

    @pytest.mark.asyncio
    async def test_seed_entities_creates_defaults(self, manager, mock_store, user_id):
        """Seed entities creates default set for new user."""
        # Simulate new user with no entities
        mock_store.get_entities.return_value = []
        mock_store.save_entities = AsyncMock(side_effect=lambda x: x)

        result = await manager.seed_entities(user_id)

        assert len(result) == len(DEFAULT_ENTITIES)
        mock_store.save_entities.assert_called_once()

    @pytest.mark.asyncio
    async def test_seed_entities_skips_existing(self, manager, mock_store, user_id):
        """Seed entities skips if user already has entities."""
        existing = [
            NikitaEntity(
                user_id=user_id,
                entity_type=EntityType.COLLEAGUE,
                name="Existing",
            )
        ]
        mock_store.get_entities.return_value = existing

        result = await manager.seed_entities(user_id)

        assert result == existing
        mock_store.save_entities.assert_not_called()

    @pytest.mark.asyncio
    async def test_seed_entities_includes_colleagues(self, manager, mock_store, user_id):
        """Seed data includes multiple colleagues."""
        mock_store.get_entities.return_value = []
        mock_store.save_entities = AsyncMock(side_effect=lambda x: x)

        result = await manager.seed_entities(user_id)

        colleagues = [e for e in result if e.entity_type == EntityType.COLLEAGUE]
        assert len(colleagues) >= 3  # At least 3 colleagues

    @pytest.mark.asyncio
    async def test_seed_entities_includes_friends(self, manager, mock_store, user_id):
        """Seed data includes friends."""
        mock_store.get_entities.return_value = []
        mock_store.save_entities = AsyncMock(side_effect=lambda x: x)

        result = await manager.seed_entities(user_id)

        friends = [e for e in result if e.entity_type == EntityType.FRIEND]
        assert len(friends) >= 2  # At least 2 friends

    @pytest.mark.asyncio
    async def test_seed_entities_includes_places(self, manager, mock_store, user_id):
        """Seed data includes recurring places."""
        mock_store.get_entities.return_value = []
        mock_store.save_entities = AsyncMock(side_effect=lambda x: x)

        result = await manager.seed_entities(user_id)

        places = [e for e in result if e.entity_type == EntityType.PLACE]
        assert len(places) >= 2  # At least 2 places

    @pytest.mark.asyncio
    async def test_seed_entities_includes_projects(self, manager, mock_store, user_id):
        """Seed data includes projects."""
        mock_store.get_entities.return_value = []
        mock_store.save_entities = AsyncMock(side_effect=lambda x: x)

        result = await manager.seed_entities(user_id)

        projects = [e for e in result if e.entity_type == EntityType.PROJECT]
        assert len(projects) >= 1  # At least 1 project

    # ==================== GET BY TYPE TESTS (AC-T007.2) ====================

    @pytest.mark.asyncio
    async def test_get_entities_by_type_colleagues(self, manager, mock_store, user_id):
        """Get entities by type returns matching entities."""
        mock_store.get_entities_by_type.return_value = [
            NikitaEntity(
                user_id=user_id,
                entity_type=EntityType.COLLEAGUE,
                name="Lisa",
            )
        ]

        result = await manager.get_entities_by_type(user_id, EntityType.COLLEAGUE)

        assert len(result) == 1
        assert result[0].name == "Lisa"
        mock_store.get_entities_by_type.assert_called_once_with(
            user_id, EntityType.COLLEAGUE
        )

    @pytest.mark.asyncio
    async def test_get_colleagues_convenience_method(self, manager, mock_store, user_id):
        """get_colleagues() is a convenience wrapper."""
        mock_store.get_entities_by_type.return_value = []

        await manager.get_colleagues(user_id)

        mock_store.get_entities_by_type.assert_called_once_with(
            user_id, EntityType.COLLEAGUE
        )

    @pytest.mark.asyncio
    async def test_get_friends_convenience_method(self, manager, mock_store, user_id):
        """get_friends() is a convenience wrapper."""
        mock_store.get_entities_by_type.return_value = []

        await manager.get_friends(user_id)

        mock_store.get_entities_by_type.assert_called_once_with(
            user_id, EntityType.FRIEND
        )

    @pytest.mark.asyncio
    async def test_get_places_convenience_method(self, manager, mock_store, user_id):
        """get_places() is a convenience wrapper."""
        mock_store.get_entities_by_type.return_value = []

        await manager.get_places(user_id)

        mock_store.get_entities_by_type.assert_called_once_with(
            user_id, EntityType.PLACE
        )

    @pytest.mark.asyncio
    async def test_get_projects_convenience_method(self, manager, mock_store, user_id):
        """get_projects() is a convenience wrapper."""
        mock_store.get_entities_by_type.return_value = []

        await manager.get_projects(user_id)

        mock_store.get_entities_by_type.assert_called_once_with(
            user_id, EntityType.PROJECT
        )

    # ==================== OTHER METHODS ====================

    @pytest.mark.asyncio
    async def test_get_all_entities(self, manager, mock_store, user_id):
        """Get all entities returns full list."""
        expected = [
            NikitaEntity(user_id=user_id, entity_type=EntityType.COLLEAGUE, name="A"),
            NikitaEntity(user_id=user_id, entity_type=EntityType.FRIEND, name="B"),
        ]
        mock_store.get_entities.return_value = expected

        result = await manager.get_all_entities(user_id)

        assert result == expected

    @pytest.mark.asyncio
    async def test_add_entity(self, manager, mock_store, user_id):
        """Add entity saves to store."""
        entity = NikitaEntity(
            user_id=user_id,
            entity_type=EntityType.COLLEAGUE,
            name="New Person",
        )
        mock_store.save_entity.return_value = entity

        result = await manager.add_entity(entity)

        assert result == entity
        mock_store.save_entity.assert_called_once_with(entity)

    @pytest.mark.asyncio
    async def test_entity_exists(self, manager, mock_store, user_id):
        """Check if entity exists delegates to store."""
        mock_store.entity_exists.return_value = True

        result = await manager.entity_exists(user_id, "Lisa")

        assert result is True
        mock_store.entity_exists.assert_called_once_with(user_id, "Lisa")

    @pytest.mark.asyncio
    async def test_entity_not_exists(self, manager, mock_store, user_id):
        """Check non-existent entity returns False."""
        mock_store.entity_exists.return_value = False

        result = await manager.entity_exists(user_id, "Unknown")

        assert result is False

    @pytest.mark.asyncio
    async def test_get_entity_names(self, manager, mock_store, user_id):
        """Get entity names grouped by type."""
        mock_store.get_entities.return_value = [
            NikitaEntity(user_id=user_id, entity_type=EntityType.COLLEAGUE, name="Lisa"),
            NikitaEntity(user_id=user_id, entity_type=EntityType.COLLEAGUE, name="Max"),
            NikitaEntity(user_id=user_id, entity_type=EntityType.FRIEND, name="Ana"),
        ]

        result = await manager.get_entity_names(user_id)

        assert result[EntityType.COLLEAGUE] == ["Lisa", "Max"]
        assert result[EntityType.FRIEND] == ["Ana"]
        assert result[EntityType.PLACE] == []
        assert result[EntityType.PROJECT] == []

    @pytest.mark.asyncio
    async def test_get_entity_context_empty(self, manager, mock_store, user_id):
        """Get entity context for user with no entities."""
        mock_store.get_entities.return_value = []

        result = await manager.get_entity_context(user_id)

        assert "hasn't established" in result

    @pytest.mark.asyncio
    async def test_get_entity_context_with_entities(self, manager, mock_store, user_id):
        """Get entity context formats as natural language."""
        mock_store.get_entities.return_value = [
            NikitaEntity(user_id=user_id, entity_type=EntityType.COLLEAGUE, name="Lisa"),
            NikitaEntity(user_id=user_id, entity_type=EntityType.FRIEND, name="Ana"),
            NikitaEntity(
                user_id=user_id, entity_type=EntityType.PLACE, name="Bluestone Café"
            ),
        ]

        result = await manager.get_entity_context(user_id)

        assert "Lisa" in result
        assert "Ana" in result
        assert "Bluestone Café" in result
        assert "At work" in result
        assert "friends" in result
        assert "frequents" in result


class TestDefaultEntities:
    """Tests for default entity seed data."""

    def test_default_entities_not_empty(self):
        """Default entities list has content."""
        assert len(DEFAULT_ENTITIES) > 0

    def test_default_entities_have_all_types(self):
        """Default entities cover all entity types."""
        types_present = {e["entity_type"] for e in DEFAULT_ENTITIES}
        assert EntityType.COLLEAGUE in types_present
        assert EntityType.FRIEND in types_present
        assert EntityType.PLACE in types_present
        assert EntityType.PROJECT in types_present

    def test_default_entities_have_descriptions(self):
        """All default entities have descriptions."""
        for entity in DEFAULT_ENTITIES:
            assert "description" in entity
            assert len(entity["description"]) > 10

    def test_default_entities_have_relationships(self):
        """All default entities have relationship context."""
        for entity in DEFAULT_ENTITIES:
            assert "relationship" in entity
            assert len(entity["relationship"]) > 10


class TestGetEntityManager:
    """Tests for singleton factory."""

    def test_singleton_pattern(self):
        """get_entity_manager returns same instance."""
        import nikita.life_simulation.entity_manager as em_module

        em_module._default_manager = None

        manager1 = get_entity_manager()
        manager2 = get_entity_manager()

        assert manager1 is manager2
