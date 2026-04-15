"""BackstoryCacheRepository — Spec 213 PR 213-2.

Admin-only repository for the backstory_cache table. Cache is keyed by a
canonical segment string (e.g. "berlin|techno|tech") and stores a JSONB array
of BackstoryOption-shaped dicts. TTL is enforced at query-time via
WHERE ttl_expires_at > now().

Return contract:
- get() → list[dict] | None   (raw JSONB envelope; caller deserializes)
- set() → None                (upsert, no return value)

Caller manages the transaction — this repository NEVER calls session.commit().
Follows VenueCacheRepository pattern from profile_repository.py.
"""

from datetime import timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.backstory_cache import BackstoryCache
from nikita.db.models.base import utc_now


class BackstoryCacheRepository:
    """Repository for BackstoryCache table (admin-only, RLS: service_role bypass).

    Cache semantics:
    - get()  returns raw list[dict] or None (miss / expired filtered at DB level)
    - set()  upserts via ON CONFLICT (cache_key) DO UPDATE SET ...

    Spec 213 FR-12 + AR2-L2 resolution:
    - Return type is list[dict] NOT list[BackstoryOption]
    - Facade (BackstoryGeneratorService) deserializes into BackstoryOption
    - TTL filter applied at query-time so expired rows are never served
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize BackstoryCacheRepository.

        Args:
            session: Async SQLAlchemy session. Caller manages the transaction.
        """
        self._session = session

    @property
    def session(self) -> AsyncSession:
        """Access the database session."""
        return self._session

    async def get(self, cache_key: str) -> list[dict[str, Any]] | None:
        """Return raw scenarios list[dict] envelope, or None if miss/expired.

        TTL filter applied at query-time (WHERE ttl_expires_at > now()).
        Return type is list[dict] NOT list[BackstoryOption] — the facade layer
        (BackstoryGeneratorService) deserializes into BackstoryOption.

        Args:
            cache_key: Canonical segment key, e.g. "berlin|techno|tech".

        Returns:
            List of scenario dicts, or None on cache miss / expiry.
        """
        now = utc_now()
        stmt = select(BackstoryCache).where(
            BackstoryCache.cache_key == cache_key,
            BackstoryCache.ttl_expires_at > now,  # TTL filter at query-time
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return row.scenarios  # list[dict] envelope, not deserialized

    async def get_envelope(self, cache_key: str) -> dict[str, object] | None:
        """Return full cache envelope dict, or None if miss/expired.

        Unlike get(), returns both ``scenarios`` and ``venues_used`` so callers
        that need venue de-dup data (e.g. generate_preview) can access it.

        Return shape on hit:
            {"scenarios": list[dict], "venues_used": list[str]}

        TTL filter applied at query-time (WHERE ttl_expires_at > now()).
        Returns None on cache miss or expiry — callers MUST handle None.

        Args:
            cache_key: Canonical segment key, e.g. "berlin|techno|tech".

        Returns:
            Dict envelope with "scenarios" and "venues_used", or None on miss.
        """
        now = utc_now()
        stmt = select(BackstoryCache).where(
            BackstoryCache.cache_key == cache_key,
            BackstoryCache.ttl_expires_at > now,  # TTL filter at query-time
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return {"scenarios": row.scenarios, "venues_used": row.venues_used}

    async def set(
        self,
        cache_key: str,
        scenarios: list[dict[str, Any]],
        venues_used: list[str],
        ttl_days: int,
    ) -> None:
        """Upsert cache entry with TTL = now() + ttl_days.

        Uses ON CONFLICT (cache_key) DO UPDATE SET ... — idempotent on re-entry.
        Caller manages the transaction; this method does NOT commit.

        Args:
            cache_key: Canonical segment key, e.g. "berlin|techno|tech".
            scenarios: List of BackstoryOption-shaped dicts to cache.
            venues_used: Venue names already consumed (for cross-TTL de-dup).
            ttl_days: Number of days until cache entry expires.
        """
        now = utc_now()
        expires_at = now + timedelta(days=ttl_days)

        # ``created_at`` intentionally omitted — the column has
        # ``server_default=func.now()`` in the ORM, so PostgreSQL fills it on
        # INSERT. Passing it from Python would risk clock skew between the app
        # and DB and is inconsistent with other cache models (VenueCache).
        # On CONFLICT DO UPDATE we also omit it to preserve the original
        # creation timestamp across upserts.
        stmt = (
            insert(BackstoryCache)
            .values(
                cache_key=cache_key,
                scenarios=scenarios,
                venues_used=venues_used,
                ttl_expires_at=expires_at,
            )
            .on_conflict_do_update(
                index_elements=["cache_key"],
                set_={
                    "scenarios": scenarios,
                    "venues_used": venues_used,
                    "ttl_expires_at": expires_at,
                },
            )
        )
        await self._session.execute(stmt)
