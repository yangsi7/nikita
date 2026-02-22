"""Tests for Spec 056 PsycheStateRepository (Phase 1: T4, T5).

TDD: Write failing tests FIRST. These test the repository methods:
get_current (single JSONB read) and upsert (INSERT ON CONFLICT UPDATE).

AC refs: AC-4.4, AC-6.1
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from nikita.db.models.psyche_state import PsycheStateRecord
from nikita.db.repositories.psyche_state_repository import PsycheStateRepository


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def mock_session():
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def repo(mock_session):
    return PsycheStateRepository(mock_session)


# ============================================================================
# Repository class structure
# ============================================================================


class TestPsycheStateRepositoryStructure:
    """PsycheStateRepository extends BaseRepository."""

    def test_module_importable(self):
        from nikita.db.repositories.psyche_state_repository import PsycheStateRepository

        assert PsycheStateRepository is not None

    def test_is_base_repository_subclass(self):
        from nikita.db.repositories.base import BaseRepository

        assert issubclass(PsycheStateRepository, BaseRepository)

    def test_has_get_current_method(self, repo):
        assert hasattr(repo, "get_current")
        assert callable(repo.get_current)

    def test_has_upsert_method(self, repo):
        assert hasattr(repo, "upsert")
        assert callable(repo.upsert)

    def test_get_current_is_async(self, repo):
        import asyncio

        assert asyncio.iscoroutinefunction(repo.get_current)

    def test_upsert_is_async(self, repo):
        import asyncio

        assert asyncio.iscoroutinefunction(repo.upsert)


# ============================================================================
# get_current - AC-4.4: single JSONB read <50ms
# ============================================================================


class TestGetCurrent:
    """get_current reads single JSONB row for user."""

    @pytest.mark.asyncio
    async def test_returns_record_when_exists(self, repo, mock_session, user_id):
        """get_current returns PsycheStateRecord for existing user."""
        record = PsycheStateRecord(
            id=uuid4(),
            user_id=user_id,
            state={"attachment_activation": "secure", "defense_mode": "open"},
            model="sonnet",
            token_count=500,
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = record
        mock_session.execute.return_value = mock_result

        result = await repo.get_current(user_id)

        mock_session.execute.assert_called_once()
        assert result is record
        assert result.user_id == user_id

    @pytest.mark.asyncio
    async def test_returns_none_when_missing(self, repo, mock_session, user_id):
        """get_current returns None when no psyche state exists for user."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repo.get_current(user_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_queries_by_user_id(self, repo, mock_session, user_id):
        """get_current queries by user_id."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        await repo.get_current(user_id)

        # Verify execute was called (SQL query built)
        mock_session.execute.assert_called_once()


# ============================================================================
# upsert - AC-6.1: INSERT ON CONFLICT UPDATE
# ============================================================================


class TestUpsert:
    """upsert creates or updates psyche state for user."""

    @pytest.mark.asyncio
    async def test_upsert_calls_execute(self, repo, mock_session, user_id):
        """upsert executes SQL statement (upsert + re-fetch via get_current)."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        state_dict = {
            "attachment_activation": "secure",
            "defense_mode": "open",
            "behavioral_guidance": "Be warm.",
            "internal_monologue": "Feeling safe.",
            "vulnerability_level": 0.6,
            "emotional_tone": "warm",
            "topics_to_encourage": ["family"],
            "topics_to_avoid": [],
        }

        await repo.upsert(
            user_id=user_id,
            state=state_dict,
            model="sonnet",
            token_count=450,
        )

        # Called twice: once for pg_insert, once for re-fetch via get_current
        assert mock_session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_upsert_returns_record(self, repo, mock_session, user_id):
        """upsert returns the created/updated PsycheStateRecord."""
        state_dict = {"attachment_activation": "secure", "defense_mode": "open"}

        # Mock the returned result after upsert
        mock_result = MagicMock()
        mock_record = PsycheStateRecord(
            id=uuid4(),
            user_id=user_id,
            state=state_dict,
            model="sonnet",
            token_count=400,
        )
        mock_result.scalar_one_or_none.return_value = mock_record
        mock_session.execute.return_value = mock_result

        result = await repo.upsert(
            user_id=user_id,
            state=state_dict,
            model="sonnet",
            token_count=400,
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_upsert_accepts_required_params(self, repo, mock_session, user_id):
        """upsert accepts user_id, state, model, token_count."""
        import inspect

        sig = inspect.signature(repo.upsert)
        params = set(sig.parameters.keys())
        assert "user_id" in params
        assert "state" in params
        assert "model" in params
        assert "token_count" in params


# ============================================================================
# PsycheStateRecord model structure
# ============================================================================


class TestPsycheStateRecordModel:
    """PsycheStateRecord SQLAlchemy model has required columns."""

    def test_model_importable(self):
        from nikita.db.models.psyche_state import PsycheStateRecord

        assert PsycheStateRecord is not None

    def test_tablename(self):
        assert PsycheStateRecord.__tablename__ == "psyche_states"

    def test_has_user_id_column(self):
        assert hasattr(PsycheStateRecord, "user_id")

    def test_has_state_column(self):
        assert hasattr(PsycheStateRecord, "state")

    def test_has_generated_at_column(self):
        assert hasattr(PsycheStateRecord, "generated_at")

    def test_has_model_column(self):
        assert hasattr(PsycheStateRecord, "model")

    def test_has_token_count_column(self):
        assert hasattr(PsycheStateRecord, "token_count")

    def test_inherits_uuid_mixin(self):
        assert hasattr(PsycheStateRecord, "id")

    def test_inherits_timestamp_mixin(self):
        assert hasattr(PsycheStateRecord, "created_at")
        assert hasattr(PsycheStateRecord, "updated_at")

    def test_registered_in_models_init(self):
        """PsycheStateRecord is importable from db.models."""
        from nikita.db.models import PsycheStateRecord as imported

        assert imported is PsycheStateRecord
