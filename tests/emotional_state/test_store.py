"""Unit Tests: Emotional State Store (Spec 023, T003).

Tests StateStore CRUD operations:
- get_current_state() retrieves latest state
- save_state() creates new records
- update_state() modifies existing state
- get_state_history() retrieves historical states
- get_conflict_history() retrieves conflict states

AC-T003.1: StateStore class with CRUD operations
AC-T003.2: get_current_state() method
AC-T003.3: update_state() method
AC-T003.5: Unit tests for store
"""

import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from nikita.emotional_state.models import ConflictState, EmotionalStateModel
from nikita.emotional_state.store import StateStore, get_state_store


class MockMappings:
    """Mock for SQLAlchemy result.mappings()."""

    def __init__(self, rows: list[dict[str, Any]] | None = None):
        self.rows = rows or []

    def first(self) -> dict[str, Any] | None:
        return self.rows[0] if self.rows else None

    def all(self) -> list[dict[str, Any]]:
        return self.rows


class MockResult:
    """Mock for SQLAlchemy result."""

    def __init__(self, rows: list[dict[str, Any]] | None = None, rowcount: int = 0):
        self._rows = rows or []
        self.rowcount = rowcount

    def mappings(self) -> MockMappings:
        return MockMappings(self._rows)


@pytest.fixture
def user_id():
    """Generate test user ID."""
    return uuid4()


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def mock_session_factory(mock_session):
    """Create a mock session factory."""
    @asynccontextmanager
    async def factory():
        yield mock_session
    return factory


@pytest.fixture
def store(mock_session_factory):
    """Create StateStore with mock session."""
    return StateStore(session_factory=mock_session_factory)


class TestStateStoreGetCurrentState:
    """AC-T003.2: get_current_state() method."""

    @pytest.mark.asyncio
    async def test_get_current_state_returns_latest(self, store, mock_session, user_id):
        """Should return the most recent state for a user."""
        state_id = uuid4()
        now = datetime.now(timezone.utc)

        mock_session.execute.return_value = MockResult(rows=[{
            "state_id": str(state_id),
            "user_id": str(user_id),
            "arousal": 0.7,
            "valence": 0.6,
            "dominance": 0.5,
            "intimacy": 0.4,
            "conflict_state": "none",
            "conflict_started_at": None,
            "conflict_trigger": None,
            "ignored_message_count": 0,
            "last_updated": now.isoformat(),
            "created_at": now.isoformat(),
            "metadata": {},
        }])

        result = await store.get_current_state(user_id)

        assert result is not None
        assert result.state_id == state_id
        assert result.arousal == 0.7
        assert result.valence == 0.6

    @pytest.mark.asyncio
    async def test_get_current_state_returns_none_if_not_found(self, store, mock_session, user_id):
        """Should return None if no state exists for user."""
        mock_session.execute.return_value = MockResult(rows=[])

        result = await store.get_current_state(user_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_current_state_handles_conflict_state(self, store, mock_session, user_id):
        """Should properly deserialize conflict states."""
        state_id = uuid4()
        now = datetime.now(timezone.utc)
        conflict_started = now - timedelta(hours=2)

        mock_session.execute.return_value = MockResult(rows=[{
            "state_id": str(state_id),
            "user_id": str(user_id),
            "arousal": 0.8,
            "valence": 0.2,
            "dominance": 0.6,
            "intimacy": 0.3,
            "conflict_state": "cold",
            "conflict_started_at": conflict_started.isoformat(),
            "conflict_trigger": "User was distant",
            "ignored_message_count": 3,
            "last_updated": now.isoformat(),
            "created_at": (now - timedelta(days=1)).isoformat(),
            "metadata": {"source": "test"},
        }])

        result = await store.get_current_state(user_id)

        assert result is not None
        assert result.conflict_state == ConflictState.COLD
        assert result.conflict_trigger == "User was distant"
        assert result.ignored_message_count == 3


class TestStateStoreSaveState:
    """Tests for save_state() method."""

    @pytest.mark.asyncio
    async def test_save_state_inserts_new_record(self, store, mock_session, user_id):
        """Should insert a new state record."""
        state = EmotionalStateModel(
            user_id=user_id,
            arousal=0.7,
            valence=0.6,
            dominance=0.5,
            intimacy=0.4,
        )

        result = await store.save_state(state)

        assert result == state
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_state_with_conflict(self, store, mock_session, user_id):
        """Should save state with conflict information."""
        state = EmotionalStateModel(
            user_id=user_id,
            arousal=0.9,
            valence=0.2,
            conflict_state=ConflictState.EXPLOSIVE,
            conflict_trigger="Big argument",
        )

        result = await store.save_state(state)

        assert result.conflict_state == ConflictState.EXPLOSIVE
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_state_with_metadata(self, store, mock_session, user_id):
        """Should save state with metadata."""
        state = EmotionalStateModel(
            user_id=user_id,
            metadata={"source": "conversation", "message_id": "123"},
        )

        await store.save_state(state)

        # Verify execute was called with metadata
        call_args = mock_session.execute.call_args
        assert call_args is not None


class TestStateStoreUpdateState:
    """AC-T003.3: update_state() method."""

    @pytest.mark.asyncio
    async def test_update_state_creates_if_not_exists(self, store, mock_session, user_id):
        """Should create new state if none exists."""
        # First call returns no existing state
        mock_session.execute.side_effect = [
            MockResult(rows=[]),  # get_current_state returns nothing
            MockResult(),  # save_state INSERT
        ]

        result = await store.update_state(
            user_id=user_id,
            arousal=0.8,
            valence=0.7,
        )

        assert result is not None
        assert result.arousal == 0.8
        assert result.valence == 0.7
        # Defaults for unspecified
        assert result.dominance == 0.5
        assert result.intimacy == 0.5

    @pytest.mark.asyncio
    async def test_update_state_modifies_existing(self, store, mock_session, user_id):
        """Should update existing state."""
        state_id = uuid4()
        now = datetime.now(timezone.utc)

        # First call returns existing state
        mock_session.execute.side_effect = [
            MockResult(rows=[{
                "state_id": str(state_id),
                "user_id": str(user_id),
                "arousal": 0.5,
                "valence": 0.5,
                "dominance": 0.5,
                "intimacy": 0.5,
                "conflict_state": "none",
                "conflict_started_at": None,
                "conflict_trigger": None,
                "ignored_message_count": 0,
                "last_updated": now.isoformat(),
                "created_at": now.isoformat(),
                "metadata": {},
            }]),
            MockResult(),  # UPDATE
        ]

        result = await store.update_state(
            user_id=user_id,
            arousal=0.9,
            # Only update arousal, keep others
        )

        assert result is not None
        assert result.arousal == 0.9
        assert result.valence == 0.5  # Unchanged
        assert result.state_id == state_id  # Same ID

    @pytest.mark.asyncio
    async def test_update_state_partial_update(self, store, mock_session, user_id):
        """Should only update specified fields."""
        state_id = uuid4()
        now = datetime.now(timezone.utc)

        mock_session.execute.side_effect = [
            MockResult(rows=[{
                "state_id": str(state_id),
                "user_id": str(user_id),
                "arousal": 0.3,
                "valence": 0.4,
                "dominance": 0.5,
                "intimacy": 0.6,
                "conflict_state": "none",
                "conflict_started_at": None,
                "conflict_trigger": None,
                "ignored_message_count": 0,
                "last_updated": now.isoformat(),
                "created_at": now.isoformat(),
                "metadata": {},
            }]),
            MockResult(),
        ]

        result = await store.update_state(
            user_id=user_id,
            conflict_state=ConflictState.VULNERABLE,
            conflict_trigger="Feeling hurt",
        )

        assert result is not None
        assert result.arousal == 0.3  # Unchanged
        assert result.valence == 0.4  # Unchanged
        assert result.conflict_state == ConflictState.VULNERABLE
        assert result.conflict_trigger == "Feeling hurt"


class TestStateStoreHistory:
    """Tests for history methods."""

    @pytest.mark.asyncio
    async def test_get_state_history(self, store, mock_session, user_id):
        """Should return historical states."""
        now = datetime.now(timezone.utc)

        mock_session.execute.return_value = MockResult(rows=[
            {
                "state_id": str(uuid4()),
                "user_id": str(user_id),
                "arousal": 0.7,
                "valence": 0.6,
                "dominance": 0.5,
                "intimacy": 0.4,
                "conflict_state": "none",
                "conflict_started_at": None,
                "conflict_trigger": None,
                "ignored_message_count": 0,
                "last_updated": now.isoformat(),
                "created_at": now.isoformat(),
                "metadata": {},
            },
            {
                "state_id": str(uuid4()),
                "user_id": str(user_id),
                "arousal": 0.5,
                "valence": 0.5,
                "dominance": 0.5,
                "intimacy": 0.5,
                "conflict_state": "none",
                "conflict_started_at": None,
                "conflict_trigger": None,
                "ignored_message_count": 0,
                "last_updated": (now - timedelta(hours=1)).isoformat(),
                "created_at": (now - timedelta(hours=1)).isoformat(),
                "metadata": {},
            },
        ])

        result = await store.get_state_history(user_id, days=7)

        assert len(result) == 2
        assert result[0].arousal == 0.7  # Most recent first

    @pytest.mark.asyncio
    async def test_get_conflict_history(self, store, mock_session, user_id):
        """Should return only states with conflict."""
        now = datetime.now(timezone.utc)

        mock_session.execute.return_value = MockResult(rows=[
            {
                "state_id": str(uuid4()),
                "user_id": str(user_id),
                "arousal": 0.8,
                "valence": 0.2,
                "dominance": 0.6,
                "intimacy": 0.3,
                "conflict_state": "cold",
                "conflict_started_at": (now - timedelta(hours=5)).isoformat(),
                "conflict_trigger": "Distance",
                "ignored_message_count": 0,
                "last_updated": now.isoformat(),
                "created_at": now.isoformat(),
                "metadata": {},
            },
        ])

        result = await store.get_conflict_history(user_id, days=30)

        assert len(result) == 1
        assert result[0].conflict_state == ConflictState.COLD


class TestStateStoreDelete:
    """Tests for delete methods."""

    @pytest.mark.asyncio
    async def test_delete_state(self, store, mock_session):
        """Should delete a specific state."""
        state_id = uuid4()
        mock_session.execute.return_value = MockResult(rowcount=1)

        result = await store.delete_state(state_id)

        assert result is True
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_state_not_found(self, store, mock_session):
        """Should return False if state not found."""
        state_id = uuid4()
        mock_session.execute.return_value = MockResult(rowcount=0)

        result = await store.delete_state(state_id)

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_user_states(self, store, mock_session, user_id):
        """Should delete all states for a user."""
        mock_session.execute.return_value = MockResult(rowcount=5)

        result = await store.delete_user_states(user_id)

        assert result == 5


class TestStateStoreGetState:
    """Tests for get_state() method."""

    @pytest.mark.asyncio
    async def test_get_state_by_id(self, store, mock_session):
        """Should retrieve state by ID."""
        state_id = uuid4()
        user_id = uuid4()
        now = datetime.now(timezone.utc)

        mock_session.execute.return_value = MockResult(rows=[{
            "state_id": str(state_id),
            "user_id": str(user_id),
            "arousal": 0.6,
            "valence": 0.7,
            "dominance": 0.5,
            "intimacy": 0.8,
            "conflict_state": "none",
            "conflict_started_at": None,
            "conflict_trigger": None,
            "ignored_message_count": 0,
            "last_updated": now.isoformat(),
            "created_at": now.isoformat(),
            "metadata": {},
        }])

        result = await store.get_state(state_id)

        assert result is not None
        assert result.state_id == state_id
        assert result.intimacy == 0.8

    @pytest.mark.asyncio
    async def test_get_state_not_found(self, store, mock_session):
        """Should return None if state not found."""
        mock_session.execute.return_value = MockResult(rows=[])

        result = await store.get_state(uuid4())

        assert result is None


class TestGetStateStore:
    """Tests for singleton get_state_store()."""

    def setup_method(self):
        """Reset singleton between tests."""
        import nikita.emotional_state.store as store_mod
        store_mod._store_instance = None

    def teardown_method(self):
        """Reset singleton after tests."""
        import nikita.emotional_state.store as store_mod
        store_mod._store_instance = None

    def test_get_state_store_returns_instance(self):
        """Should return StateStore instance."""
        from unittest.mock import patch
        with patch("nikita.emotional_state.store.get_session_maker"):
            store = get_state_store()
            assert isinstance(store, StateStore)

    def test_get_state_store_singleton(self):
        """Should return same instance on multiple calls."""
        from unittest.mock import patch
        with patch("nikita.emotional_state.store.get_session_maker"):
            store1 = get_state_store()
            store2 = get_state_store()
            assert store1 is store2
