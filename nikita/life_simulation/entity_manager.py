"""Entity Manager for Life Simulation Engine (Spec 022, T007-T008).

Manages recurring entities (colleagues, friends, places, projects) for Nikita's life.

AC-T007.1: EntityManager class manages recurring entities
AC-T007.2: get_entities_by_type() method
AC-T007.3: seed_entities() method for new users
AC-T007.4: Unit tests for manager
AC-T008.1: Seed data for colleagues (config)
AC-T008.2: Seed data for friends (config)
AC-T008.3: Seed data for places (config)
AC-T008.4: Config file entities.yaml
"""

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any
from uuid import UUID

import yaml

from nikita.life_simulation.models import (
    NikitaEntity,
    EntityType,
)
from nikita.life_simulation.store import EventStore, get_event_store

logger = logging.getLogger(__name__)


# Path to entity config
CONFIG_PATH = Path(__file__).parent.parent / "config_data" / "life_simulation" / "entities.yaml"


@lru_cache(maxsize=1)
def load_entity_config() -> dict[str, list[dict[str, str]]]:
    """Load entity configuration from YAML file.

    Returns:
        Dict with keys: colleagues, friends, places, projects
    """
    if not CONFIG_PATH.exists():
        logger.warning(f"Entity config not found at {CONFIG_PATH}, using defaults")
        return _get_default_entities_config()

    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)

    return config


def _get_default_entities_config() -> dict[str, list[dict[str, str]]]:
    """Get default entity config if YAML not available."""
    return {
        "colleagues": [
            {"name": "Lisa", "description": "Senior designer", "relationship": "Admires her work"},
            {"name": "Max", "description": "Junior developer", "relationship": "Mentors him"},
        ],
        "friends": [
            {"name": "Ana", "description": "Best friend since college", "relationship": "Very close"},
        ],
        "places": [
            {"name": "the office", "description": "Design studio", "relationship": "Work location"},
        ],
        "projects": [
            {"name": "the redesign", "description": "Client rebrand", "relationship": "High-stakes"},
        ],
    }


def get_default_entities() -> list[dict[str, Any]]:
    """Get default entities from YAML config.

    Returns:
        List of entity dicts with entity_type populated.
    """
    config = load_entity_config()
    entities: list[dict[str, Any]] = []

    # Map config sections to entity types
    type_mapping = {
        "colleagues": EntityType.COLLEAGUE,
        "friends": EntityType.FRIEND,
        "places": EntityType.PLACE,
        "projects": EntityType.PROJECT,
    }

    for section, entity_type in type_mapping.items():
        for item in config.get(section, []):
            entities.append({
                "entity_type": entity_type,
                "name": item["name"],
                "description": item.get("description", ""),
                "relationship": item.get("relationship", ""),
            })

    return entities


# Module-level accessor for default entities
DEFAULT_ENTITIES = get_default_entities()


class EntityManager:
    """Manages recurring entities in Nikita's life.

    Provides methods to:
    - Seed initial entities for new users
    - Retrieve entities by type
    - Add/update entities as narrative evolves

    Example:
        manager = EntityManager()
        await manager.seed_entities(user_id)

        colleagues = await manager.get_entities_by_type(user_id, EntityType.COLLEAGUE)
        # Returns: [NikitaEntity(name="Lisa", ...), ...]
    """

    def __init__(self, store: EventStore | None = None) -> None:
        """Initialize EntityManager.

        Args:
            store: Optional EventStore instance. Defaults to singleton.
        """
        self._store = store or get_event_store()

    async def seed_entities(self, user_id: UUID) -> list[NikitaEntity]:
        """Seed default entities for a new user.

        Creates the standard set of colleagues, friends, places, and projects
        that form Nikita's initial social world.

        Args:
            user_id: User ID to seed entities for.

        Returns:
            List of created entities.
        """
        # Check if user already has entities
        existing = await self._store.get_entities(user_id)
        if existing:
            logger.info(f"User {user_id} already has {len(existing)} entities, skipping seed")
            return existing

        # Create entities from defaults
        entities = [
            NikitaEntity(
                user_id=user_id,
                entity_type=seed["entity_type"],
                name=seed["name"],
                description=seed["description"],
                relationship=seed["relationship"],
            )
            for seed in DEFAULT_ENTITIES
        ]

        # Save all entities
        await self._store.save_entities(entities)
        logger.info(f"Seeded {len(entities)} entities for user {user_id}")

        return entities

    async def get_entities_by_type(
        self, user_id: UUID, entity_type: EntityType
    ) -> list[NikitaEntity]:
        """Get all entities of a specific type for a user.

        Args:
            user_id: User ID.
            entity_type: Type of entity (colleague, friend, place, project).

        Returns:
            List of matching entities.
        """
        return await self._store.get_entities_by_type(user_id, entity_type)

    async def get_all_entities(self, user_id: UUID) -> list[NikitaEntity]:
        """Get all entities for a user.

        Args:
            user_id: User ID.

        Returns:
            List of all entities.
        """
        return await self._store.get_entities(user_id)

    async def get_colleagues(self, user_id: UUID) -> list[NikitaEntity]:
        """Get all colleague entities for a user.

        Convenience method for common access pattern.
        """
        return await self.get_entities_by_type(user_id, EntityType.COLLEAGUE)

    async def get_friends(self, user_id: UUID) -> list[NikitaEntity]:
        """Get all friend entities for a user.

        Convenience method for common access pattern.
        """
        return await self.get_entities_by_type(user_id, EntityType.FRIEND)

    async def get_places(self, user_id: UUID) -> list[NikitaEntity]:
        """Get all place entities for a user.

        Convenience method for common access pattern.
        """
        return await self.get_entities_by_type(user_id, EntityType.PLACE)

    async def get_projects(self, user_id: UUID) -> list[NikitaEntity]:
        """Get all project entities for a user.

        Convenience method for common access pattern.
        """
        return await self.get_entities_by_type(user_id, EntityType.PROJECT)

    async def add_entity(self, entity: NikitaEntity) -> NikitaEntity:
        """Add a new entity to a user's world.

        Args:
            entity: Entity to add.

        Returns:
            Saved entity.
        """
        return await self._store.save_entity(entity)

    async def entity_exists(self, user_id: UUID, name: str) -> bool:
        """Check if an entity with the given name exists for a user.

        Args:
            user_id: User ID.
            name: Entity name to check.

        Returns:
            True if entity exists.
        """
        return await self._store.entity_exists(user_id, name)

    async def get_entity_names(self, user_id: UUID) -> dict[EntityType, list[str]]:
        """Get all entity names grouped by type.

        Useful for event generation to reference known entities.

        Args:
            user_id: User ID.

        Returns:
            Dict mapping entity type to list of names.
        """
        entities = await self._store.get_entities(user_id)
        result: dict[EntityType, list[str]] = {
            EntityType.COLLEAGUE: [],
            EntityType.FRIEND: [],
            EntityType.PLACE: [],
            EntityType.PROJECT: [],
        }
        for entity in entities:
            result[entity.entity_type].append(entity.name)
        return result

    async def get_entity_context(self, user_id: UUID) -> str:
        """Get entity context formatted for prompt injection.

        Returns a natural language summary of Nikita's social world.

        Args:
            user_id: User ID.

        Returns:
            Formatted context string.
        """
        entities = await self._store.get_entities(user_id)
        if not entities:
            return "Nikita hasn't established her social world yet."

        # Group by type
        by_type: dict[EntityType, list[NikitaEntity]] = {
            EntityType.COLLEAGUE: [],
            EntityType.FRIEND: [],
            EntityType.PLACE: [],
            EntityType.PROJECT: [],
        }
        for entity in entities:
            by_type[entity.entity_type].append(entity)

        lines = []

        # Colleagues
        if by_type[EntityType.COLLEAGUE]:
            names = [e.name for e in by_type[EntityType.COLLEAGUE]]
            lines.append(f"At work, Nikita works with {', '.join(names)}.")

        # Friends
        if by_type[EntityType.FRIEND]:
            names = [e.name for e in by_type[EntityType.FRIEND]]
            lines.append(f"Her close friends include {', '.join(names)}.")

        # Places
        if by_type[EntityType.PLACE]:
            names = [e.name for e in by_type[EntityType.PLACE]]
            lines.append(f"She frequents {', '.join(names)}.")

        # Projects
        if by_type[EntityType.PROJECT]:
            names = [e.name for e in by_type[EntityType.PROJECT]]
            lines.append(f"Current projects: {', '.join(names)}.")

        return " ".join(lines)


# Module-level singleton
_default_manager: EntityManager | None = None


def get_entity_manager() -> EntityManager:
    """Get the singleton EntityManager instance.

    Returns:
        Cached EntityManager instance.
    """
    global _default_manager
    if _default_manager is None:
        _default_manager = EntityManager()
    return _default_manager
