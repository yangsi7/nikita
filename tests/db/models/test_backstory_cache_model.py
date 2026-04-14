"""Tests for BackstoryCache ORM model added in Spec 213 PR 213-2.

T1.8.R — TDD RED phase tests for BackstoryCache model.

Acceptance criteria:
- BackstoryCache instantiates with cache_key, scenarios, venues_used, ttl_expires_at
- is_expired() returns True when ttl_expires_at is in the past
- is_expired() returns False when ttl_expires_at is in the future
- Uses AsyncMock session pattern — NO live DB
"""

from datetime import datetime, timedelta, timezone

import pytest


class TestBackstoryCacheModel:
    """Tests for BackstoryCache ORM model (T1.8)."""

    def test_backstory_cache_instantiates_with_required_fields(self):
        """BackstoryCache accepts cache_key, scenarios, venues_used, ttl_expires_at."""
        from nikita.db.models.backstory_cache import BackstoryCache

        future = datetime.now(timezone.utc) + timedelta(days=30)
        cache = BackstoryCache(
            cache_key="berlin|techno|tech",
            scenarios=[{"id": "x", "venue": "Berghain", "context": "dark techno"}],
            venues_used=["Berghain"],
            ttl_expires_at=future,
        )

        assert cache.cache_key == "berlin|techno|tech"
        assert cache.scenarios == [{"id": "x", "venue": "Berghain", "context": "dark techno"}]
        assert cache.venues_used == ["Berghain"]
        assert cache.ttl_expires_at == future

    def test_backstory_cache_is_expired_returns_true_for_past_ttl(self):
        """is_expired() returns True when ttl_expires_at is in the past."""
        from nikita.db.models.backstory_cache import BackstoryCache

        past = datetime.now(timezone.utc) - timedelta(seconds=1)
        cache = BackstoryCache(
            cache_key="berlin|techno|tech",
            scenarios=[],
            venues_used=[],
            ttl_expires_at=past,
        )

        assert cache.is_expired() is True

    def test_backstory_cache_is_expired_returns_false_for_future_ttl(self):
        """is_expired() returns False when ttl_expires_at is in the future."""
        from nikita.db.models.backstory_cache import BackstoryCache

        future = datetime.now(timezone.utc) + timedelta(days=30)
        cache = BackstoryCache(
            cache_key="berlin|art|creative",
            scenarios=[{"id": "y", "venue": "Café Kafka"}],
            venues_used=["Café Kafka"],
            ttl_expires_at=future,
        )

        assert cache.is_expired() is False

    def test_backstory_cache_has_cache_key_as_primary_key(self):
        """cache_key column is the primary key (not a UUID)."""
        from sqlalchemy import inspect

        from nikita.db.models.backstory_cache import BackstoryCache

        mapper = inspect(BackstoryCache)
        pk_cols = [c.name for c in mapper.primary_key]
        assert pk_cols == ["cache_key"], f"Expected ['cache_key'], got {pk_cols}"

    def test_backstory_cache_scenarios_is_jsonb(self):
        """scenarios column uses JSONB type for PostgreSQL storage."""
        from sqlalchemy import inspect
        from sqlalchemy.dialects.postgresql import JSONB

        from nikita.db.models.backstory_cache import BackstoryCache

        mapper = inspect(BackstoryCache)
        col = next(c for c in mapper.columns if c.name == "scenarios")
        assert isinstance(col.type, JSONB), f"Expected JSONB, got {type(col.type)}"

    def test_backstory_cache_venues_used_is_jsonb(self):
        """venues_used column uses JSONB type."""
        from sqlalchemy import inspect
        from sqlalchemy.dialects.postgresql import JSONB

        from nikita.db.models.backstory_cache import BackstoryCache

        mapper = inspect(BackstoryCache)
        col = next(c for c in mapper.columns if c.name == "venues_used")
        assert isinstance(col.type, JSONB), f"Expected JSONB, got {type(col.type)}"

    def test_backstory_cache_tablename(self):
        """BackstoryCache maps to 'backstory_cache' table."""
        from nikita.db.models.backstory_cache import BackstoryCache

        assert BackstoryCache.__tablename__ == "backstory_cache"

    def test_backstory_cache_has_no_uuid_primary_key(self):
        """BackstoryCache does NOT have an id/UUID PK — cache_key is the PK."""
        from sqlalchemy import inspect

        from nikita.db.models.backstory_cache import BackstoryCache

        mapper = inspect(BackstoryCache)
        column_names = {c.name for c in mapper.columns}
        assert "id" not in column_names, "BackstoryCache must NOT have an 'id' column"

    def test_backstory_cache_multiple_scenarios_readable(self):
        """BackstoryCache scenarios list with multiple items is accessible."""
        from nikita.db.models.backstory_cache import BackstoryCache

        future = datetime.now(timezone.utc) + timedelta(days=7)
        scenarios = [
            {"id": "a", "venue": "Berghain", "tone": "chaotic"},
            {"id": "b", "venue": "Tresor", "tone": "romantic"},
            {"id": "c", "venue": "Watergate", "tone": "intellectual"},
        ]
        cache = BackstoryCache(
            cache_key="berlin|techno|tech",
            scenarios=scenarios,
            venues_used=["Berghain", "Tresor", "Watergate"],
            ttl_expires_at=future,
        )

        assert len(cache.scenarios) == 3
        assert cache.scenarios[0]["venue"] == "Berghain"
        assert len(cache.venues_used) == 3
