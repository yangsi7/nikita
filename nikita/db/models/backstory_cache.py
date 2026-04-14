"""BackstoryCache ORM model for Spec 213 PR 213-2.

Admin-only cache table: maps a composite cache_key (city|scene|life_stage) to
a list of generated backstory scenarios. Service_role bypass required — all
authenticated reads/writes are blocked by RLS (USING (false)).

Table: backstory_cache
Primary Key: cache_key (TEXT) — no UUID, cache semantics
TTL: ttl_expires_at column; is_expired() checked at read time.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from nikita.db.models.base import Base, utc_now


class BackstoryCache(Base):
    """Cached backstory scenarios keyed by (city|scene|life_stage).

    Reduces Firecrawl + LLM costs by caching generated scenarios per
    demographic segment. Cache is keyed by a canonical string that encodes
    the relevant profile dimensions. Service-role-only access via RLS.

    Table: backstory_cache
    Primary Key: cache_key (TEXT) — composite segment string

    Spec 213 FR-12:
    - AC: BackstoryCacheRepository.get() returns list[dict] | None
    - AC: BackstoryCacheRepository.set() upserts with ON CONFLICT
    - AC: TTL filter applied at query-time (WHERE ttl_expires_at > now())
    """

    __tablename__ = "backstory_cache"

    # PRIMARY KEY: opaque segment key, e.g. "berlin|techno|tech".
    # ``String`` without a length argument maps to PostgreSQL TEXT (unbounded)
    # — intentional: the key is produced by ``compute_backstory_cache_key``
    # which joins 7 bucketed fields with ``|``; its length is not user-bounded
    # and a cap here would silently truncate future additions to the key.
    cache_key: Mapped[str] = mapped_column(String, primary_key=True)

    # Generated scenarios — list of BackstoryOption-shaped dicts
    # e.g. [{"id": "...", "venue": "Berghain", "context": "...", ...}]
    scenarios: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    # Venues already consumed for this cache_key (de-duplication across TTL resets)
    venues_used: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    # Expiry timestamp — entry is stale after this point
    ttl_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Insertion timestamp for audit / debugging
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def is_expired(self) -> bool:
        """Return True if the cache entry has passed its TTL.

        Uses utc_now() helper (timezone-aware) for comparison. Matches
        VenueCache.is_expired() pattern from profile.py.

        Returns:
            True if current UTC time is past ttl_expires_at.
        """
        return utc_now() > self.ttl_expires_at

    def __repr__(self) -> str:
        return (
            f"BackstoryCache("
            f"cache_key={self.cache_key!r}, "
            f"scenarios_count={len(self.scenarios)}, "
            f"ttl_expires_at={self.ttl_expires_at!r})"
        )
