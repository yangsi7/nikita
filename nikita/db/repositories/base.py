"""Base repository class for database access layer.

Provides generic CRUD operations for SQLAlchemy models with async session support.
All entity-specific repositories should inherit from BaseRepository.
"""

from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.base import Base

# Generic type for SQLAlchemy models
ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Base repository providing generic CRUD operations.

    All entity repositories inherit from this class to get standard database
    operations with consistent patterns and proper session management.

    Type Parameters:
        ModelT: The SQLAlchemy model type this repository manages.

    Example:
        class UserRepository(BaseRepository[User]):
            def __init__(self, session: AsyncSession):
                super().__init__(session, User)

            async def get_by_telegram_id(self, telegram_id: int) -> User | None:
                # Custom query using self.session
                ...
    """

    def __init__(self, session: AsyncSession, model_class: type[ModelT]) -> None:
        """Initialize repository with database session.

        Args:
            session: Async SQLAlchemy session for database operations.
            model_class: The SQLAlchemy model class this repository manages.
        """
        self._session = session
        self._model_class = model_class

    @property
    def session(self) -> AsyncSession:
        """Access the database session (read-only).

        Subclasses can use this property to build custom queries.

        Returns:
            The AsyncSession instance for database operations.
        """
        return self._session

    async def get(self, id: UUID) -> ModelT | None:
        """Get entity by primary key.

        Args:
            id: The UUID primary key of the entity.

        Returns:
            The entity if found, None otherwise.
        """
        return await self._session.get(self._model_class, id)

    async def create(self, entity: ModelT) -> ModelT:
        """Create and persist a new entity.

        Args:
            entity: The entity instance to persist.

        Returns:
            The persisted entity with any database-generated values populated.
        """
        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def update(self, entity: ModelT) -> ModelT:
        """Flush changes to an existing entity.

        Note: The entity should already be in the session (either retrieved
        via get() or created via create()).

        Args:
            entity: The entity with modifications to persist.

        Returns:
            The updated entity with any database-generated values refreshed.
        """
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def delete(self, entity: ModelT) -> None:
        """Delete an entity from the database.

        Args:
            entity: The entity instance to delete.
        """
        await self._session.delete(entity)
        await self._session.flush()

    async def delete_by_id(self, id: UUID) -> bool:
        """Delete entity by primary key.

        Args:
            id: The UUID primary key of the entity to delete.

        Returns:
            True if entity was found and deleted, False if not found.
        """
        entity = await self.get(id)
        if entity is None:
            return False
        await self.delete(entity)
        return True
