"""PackageStore for context package persistence (Spec 021, T003).

Provides storage and retrieval of pre-computed context packages
using Supabase JSONB for simplicity and sufficient performance.

Target latency: <50ms for get() operations.
"""

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.context.package import ContextPackage
from nikita.db.models.context_package import ContextPackageModel

logger = logging.getLogger(__name__)


class PackageStore:
    """Storage layer for context packages.

    Uses Supabase JSONB for storage with 24h TTL default.
    Designed for fast retrieval (<50ms target).
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize PackageStore.

        Args:
            session: Async SQLAlchemy session.
        """
        self._session = session

    async def get(self, user_id: UUID) -> ContextPackage | None:
        """Load the latest non-expired context package for a user.

        Target latency: <50ms.

        Args:
            user_id: The user's UUID.

        Returns:
            ContextPackage if found and not expired, None otherwise.
        """
        stmt = (
            select(ContextPackageModel)
            .where(ContextPackageModel.user_id == user_id)
            .where(ContextPackageModel.expires_at > datetime.now(UTC))
            .order_by(ContextPackageModel.created_at.desc())
            .limit(1)
        )

        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            logger.debug(f"No context package found for user {user_id}")
            return None

        # Deserialize JSONB to ContextPackage
        try:
            package = ContextPackage.model_validate(model.package)
            logger.debug(
                f"Loaded context package for user {user_id}, "
                f"version={package.version}"
            )
            return package
        except Exception as e:
            logger.error(f"Failed to deserialize context package: {e}")
            return None

    async def set(
        self,
        user_id: UUID,
        package: ContextPackage,
        ttl_hours: int = 24,
    ) -> None:
        """Store a context package with TTL.

        Uses upsert to replace existing package for the user.

        Args:
            user_id: The user's UUID.
            package: The context package to store.
            ttl_hours: Time-to-live in hours (default 24).
        """
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=ttl_hours)

        # Serialize package to dict for JSONB storage
        package_data = package.model_dump(mode="json")

        # Use PostgreSQL upsert (INSERT ... ON CONFLICT DO UPDATE)
        stmt = insert(ContextPackageModel).values(
            user_id=user_id,
            package=package_data,
            created_at=now,
            expires_at=expires_at,
        )

        # On conflict (user_id), update the package
        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id"],
            set_={
                "package": package_data,
                "created_at": now,
                "expires_at": expires_at,
            },
        )

        await self._session.execute(stmt)
        await self._session.commit()

        logger.info(
            f"Stored context package for user {user_id}, "
            f"expires_at={expires_at.isoformat()}"
        )

    async def delete(self, user_id: UUID) -> bool:
        """Delete context package for a user.

        Useful for cache invalidation on chapter change, game-over, etc.

        Args:
            user_id: The user's UUID.

        Returns:
            True if a package was deleted, False if none existed.
        """
        stmt = delete(ContextPackageModel).where(
            ContextPackageModel.user_id == user_id
        )
        result = await self._session.execute(stmt)
        await self._session.commit()

        deleted = result.rowcount > 0
        if deleted:
            logger.info(f"Deleted context package for user {user_id}")
        return deleted

    async def cleanup_expired(self) -> int:
        """Delete all expired context packages.

        Should be run periodically via pg_cron.

        Returns:
            Number of packages deleted.
        """
        stmt = delete(ContextPackageModel).where(
            ContextPackageModel.expires_at < datetime.now(UTC)
        )
        result = await self._session.execute(stmt)
        await self._session.commit()

        count = result.rowcount
        if count > 0:
            logger.info(f"Cleaned up {count} expired context packages")
        return count

    async def exists(self, user_id: UUID) -> bool:
        """Check if a non-expired package exists for a user.

        Faster than get() when you only need to check existence.

        Args:
            user_id: The user's UUID.

        Returns:
            True if a valid package exists.
        """
        stmt = (
            select(ContextPackageModel.id)
            .where(ContextPackageModel.user_id == user_id)
            .where(ContextPackageModel.expires_at > datetime.now(UTC))
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None


# Singleton factory for dependency injection
_default_store: PackageStore | None = None


def get_package_store(session: AsyncSession | None = None) -> PackageStore:
    """Get or create a PackageStore singleton.

    Args:
        session: Optional SQLAlchemy session. If provided, creates a new store.
                 If None, returns the cached default store.

    Returns:
        PackageStore instance.

    Raises:
        RuntimeError: If no session provided and no default store exists.
    """
    global _default_store

    if session is not None:
        # Create new store with provided session
        return PackageStore(session)

    if _default_store is None:
        raise RuntimeError(
            "No default PackageStore. Call get_package_store(session) first "
            "to initialize, or provide a session."
        )

    return _default_store


def set_default_package_store(store: PackageStore) -> None:
    """Set the default PackageStore singleton.

    Useful for application startup or testing.

    Args:
        store: The PackageStore to use as default.
    """
    global _default_store
    _default_store = store
