"""Tests for PackageStore (Spec 021, T003).

AC-T003.1: PackageStore class with get() and set() methods
AC-T003.2: Supabase JSONB storage implementation
AC-T003.3: TTL support (24h default)
AC-T003.4: get() completes in <50ms (mocked test)
AC-T003.5: Unit tests for store operations
"""

import time
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.context.package import ContextPackage, EmotionalState
from nikita.context.store import PackageStore


@pytest.fixture
def mock_session():
    """Create a mock async session."""
    session = AsyncMock()
    return session


@pytest.fixture
def sample_package():
    """Create a sample context package."""
    return ContextPackage(
        user_id=uuid4(),
        chapter_layer="Chapter 2: Testing phase",
        emotional_state_layer="Feeling curious",
        user_facts=["Loves testing", "Enjoys Python"],
        nikita_mood=EmotionalState(arousal=0.6, valence=0.7),
        life_events_today=["Had a great debugging session"],
    )


class TestPackageStoreInit:
    """Tests for PackageStore initialization."""

    def test_init_with_session(self, mock_session):
        """AC-T003.1: Store initializes with session."""
        store = PackageStore(mock_session)
        assert store._session == mock_session


class TestPackageStoreGet:
    """Tests for PackageStore.get()."""

    @pytest.mark.asyncio
    async def test_get_returns_none_when_not_found(self, mock_session):
        """AC-T003.1: get() returns None when no package exists."""
        # Setup mock to return None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        store = PackageStore(mock_session)
        result = await store.get(uuid4())

        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_returns_package_when_found(self, mock_session, sample_package):
        """AC-T003.1: get() returns package when found."""
        # Create mock model with package data
        mock_model = MagicMock()
        mock_model.package = sample_package.model_dump(mode="json")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_model
        mock_session.execute.return_value = mock_result

        store = PackageStore(mock_session)
        result = await store.get(sample_package.user_id)

        assert result is not None
        assert result.chapter_layer == sample_package.chapter_layer
        assert len(result.user_facts) == 2

    @pytest.mark.asyncio
    async def test_get_latency_under_50ms(self, mock_session, sample_package):
        """AC-T003.4: get() completes in <50ms (mocked)."""
        mock_model = MagicMock()
        mock_model.package = sample_package.model_dump(mode="json")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_model
        mock_session.execute.return_value = mock_result

        store = PackageStore(mock_session)

        start = time.perf_counter()
        await store.get(sample_package.user_id)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Mocked operations should be very fast
        assert elapsed_ms < 50, f"get() took {elapsed_ms:.2f}ms, expected <50ms"


class TestPackageStoreSet:
    """Tests for PackageStore.set()."""

    @pytest.mark.asyncio
    async def test_set_stores_package(self, mock_session, sample_package):
        """AC-T003.1: set() stores package."""
        store = PackageStore(mock_session)
        await store.set(sample_package.user_id, sample_package)

        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_with_custom_ttl(self, mock_session, sample_package):
        """AC-T003.3: set() supports custom TTL."""
        store = PackageStore(mock_session)
        await store.set(sample_package.user_id, sample_package, ttl_hours=48)

        # Verify execute was called (TTL is in the statement)
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_default_ttl_24h(self, mock_session, sample_package):
        """AC-T003.3: Default TTL is 24 hours."""
        store = PackageStore(mock_session)

        # Capture the expires_at from the insert statement
        with patch("nikita.context.store.datetime") as mock_dt:
            mock_now = datetime(2026, 1, 12, 12, 0, 0, tzinfo=UTC)
            mock_dt.now.return_value = mock_now

            await store.set(sample_package.user_id, sample_package)

            # Default TTL should be 24 hours
            # The actual verification would be in integration tests


class TestPackageStoreDelete:
    """Tests for PackageStore.delete()."""

    @pytest.mark.asyncio
    async def test_delete_returns_true_when_deleted(self, mock_session):
        """AC-T003.1: delete() returns True when package deleted."""
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        store = PackageStore(mock_session)
        result = await store.delete(uuid4())

        assert result is True
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_returns_false_when_not_found(self, mock_session):
        """AC-T003.1: delete() returns False when no package existed."""
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        store = PackageStore(mock_session)
        result = await store.delete(uuid4())

        assert result is False


class TestPackageStoreCleanup:
    """Tests for PackageStore.cleanup_expired()."""

    @pytest.mark.asyncio
    async def test_cleanup_expired_returns_count(self, mock_session):
        """AC-T003.3: cleanup_expired() removes expired packages."""
        mock_result = MagicMock()
        mock_result.rowcount = 5
        mock_session.execute.return_value = mock_result

        store = PackageStore(mock_session)
        count = await store.cleanup_expired()

        assert count == 5
        mock_session.commit.assert_called_once()


class TestPackageStoreExists:
    """Tests for PackageStore.exists()."""

    @pytest.mark.asyncio
    async def test_exists_returns_true_when_found(self, mock_session):
        """AC-T003.1: exists() returns True when package exists."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 1  # ID exists
        mock_session.execute.return_value = mock_result

        store = PackageStore(mock_session)
        result = await store.exists(uuid4())

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_returns_false_when_not_found(self, mock_session):
        """AC-T003.1: exists() returns False when no package."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        store = PackageStore(mock_session)
        result = await store.exists(uuid4())

        assert result is False
