"""Unit tests for BackstoryCacheRepository — Spec 213 PR 213-2.

T1.9.R — TDD RED phase tests for BackstoryCacheRepository.

Tests use AsyncMock session following tests/conftest.py patterns.
NO live database required — all DB calls are mocked.

6 required tests per task spec:
1. test_get_miss_returns_none
2. test_get_hit_returns_list_of_dict
3. test_get_expired_treated_as_miss
4. test_set_inserts_row
5. test_set_ttl_days_computes_expires_at
6. test_set_conflict_updates_row

Each test has at least one assertion (non-zero-assertion rule per testing.md).
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestBackstoryCacheRepositoryGet:
    """Tests for BackstoryCacheRepository.get() method."""

    @pytest.mark.asyncio
    async def test_get_miss_returns_none(self):
        """get() returns None when no matching row exists (cache miss).

        Mock: session.execute returns result with scalar_one_or_none() = None.
        """
        from nikita.db.repositories.backstory_cache_repository import (
            BackstoryCacheRepository,
        )

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = BackstoryCacheRepository(mock_session)
        result = await repo.get("berlin|techno|tech")

        assert result is None
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_hit_returns_list_of_dict(self):
        """get() returns list[dict] envelope when a valid (non-expired) row exists.

        Return type MUST be list[dict], NOT list[BackstoryOption].
        The facade layer (BackstoryGeneratorService) deserializes into BackstoryOption.
        """
        from nikita.db.models.backstory_cache import BackstoryCache
        from nikita.db.repositories.backstory_cache_repository import (
            BackstoryCacheRepository,
        )

        future = datetime.now(timezone.utc) + timedelta(days=30)
        scenarios_data = [
            {"id": "a", "venue": "Berghain", "context": "dark techno basement"},
            {"id": "b", "venue": "Tresor", "context": "underground rave"},
        ]

        mock_row = MagicMock(spec=BackstoryCache)
        mock_row.scenarios = scenarios_data
        mock_row.ttl_expires_at = future

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_row
        mock_session.execute.return_value = mock_result

        repo = BackstoryCacheRepository(mock_session)
        result = await repo.get("berlin|techno|tech")

        # Result MUST be list[dict], not list[BackstoryOption]
        assert result is not None
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["venue"] == "Berghain"
        assert result[1]["venue"] == "Tresor"
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_expired_treated_as_miss(self):
        """get() applies TTL filter at query-time so expired rows are never returned.

        This test verifies TWO things (QA iter-1 F2 fix: was structurally
        identical to the miss test — now inspects the actual WHERE clause):
          1. The compiled SELECT contains a ``ttl_expires_at > :now`` predicate
             so the filter is applied at the DB level (not Python-side).
          2. When the DB returns no row (simulating the filter excluding an
             expired entry), the repository returns None.
        """
        from sqlalchemy.dialects import postgresql

        from nikita.db.repositories.backstory_cache_repository import (
            BackstoryCacheRepository,
        )

        # Simulate DB returning None because the WHERE ttl_expires_at > now() filter excluded it
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = BackstoryCacheRepository(mock_session)
        result = await repo.get("stale|key|here")

        assert result is None, "Expired entries filtered at DB level must return None"
        mock_session.execute.assert_awaited_once()

        # Verify the query actually contains the TTL WHERE clause.
        # Without this check the test is indistinguishable from test_get_miss_returns_none.
        stmt = mock_session.execute.call_args[0][0]
        compiled_sql = str(stmt.compile(dialect=postgresql.dialect()))
        # Collapse whitespace so "ttl_expires_at\n>" and "ttl_expires_at >"
        # both match. Requiring column+operator together (rather than a bare
        # ``>`` anywhere in the compiled SQL) makes the check falsifiable
        # against regressions like ``>=`` or ``<``.
        normalized = " ".join(compiled_sql.split())
        assert "ttl_expires_at >" in normalized, (
            f"SELECT must filter on ``ttl_expires_at > :param``; "
            f"compiled SQL:\n{compiled_sql}"
        )


class TestBackstoryCacheRepositorySet:
    """Tests for BackstoryCacheRepository.set() method."""

    @pytest.mark.asyncio
    async def test_set_inserts_row(self):
        """set() calls session.execute with an INSERT ... ON CONFLICT statement.

        Verifies that set() uses session.execute (not session.add) and that
        the statement is issued exactly once.
        """
        from nikita.db.repositories.backstory_cache_repository import (
            BackstoryCacheRepository,
        )

        mock_session = AsyncMock()
        mock_session.execute.return_value = MagicMock()

        repo = BackstoryCacheRepository(mock_session)
        await repo.set(
            cache_key="berlin|techno|tech",
            scenarios=[{"id": "a", "venue": "Berghain"}],
            venues_used=["Berghain"],
            ttl_days=30,
        )

        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_set_ttl_days_computes_expires_at(self):
        """set() computes ttl_expires_at = now() + timedelta(days=ttl_days).

        Patches utc_now to a fixed time, then verifies ttl_expires_at in the
        compiled INSERT bind parameters is exactly ``fixed_now + ttl_days``.

        QA iter-1 F1 fix: the prior version of this test contained no real
        assertion on the TTL value — ``assert call_args is not None`` was
        always true once ``assert_awaited_once`` had passed. The test is now
        falsifiable: a drift in ``utc_now() + timedelta(days=ttl_days)`` (e.g.
        hours vs days, or unit swap) will fail the bind-param comparison below.
        """
        from sqlalchemy.dialects import postgresql

        from nikita.db.repositories.backstory_cache_repository import (
            BackstoryCacheRepository,
        )

        fixed_now = datetime(2026, 4, 14, 12, 0, 0, tzinfo=timezone.utc)
        expected_expires = fixed_now + timedelta(days=7)

        mock_session = AsyncMock()
        mock_session.execute.return_value = MagicMock()

        with patch(
            "nikita.db.repositories.backstory_cache_repository.utc_now",
            return_value=fixed_now,
        ):
            repo = BackstoryCacheRepository(mock_session)
            await repo.set(
                cache_key="test|key",
                scenarios=[],
                venues_used=[],
                ttl_days=7,
            )

        mock_session.execute.assert_awaited_once()
        # Extract the compiled INSERT statement to check bind parameters.
        call_args = mock_session.execute.call_args
        stmt = call_args[0][0]
        compiled = stmt.compile(dialect=postgresql.dialect())

        # The Insert().values() + on_conflict_do_update() statement binds
        # expires_at in BOTH the INSERT values dict AND the ON CONFLICT set_ dict.
        # Both bindings must equal fixed_now + timedelta(days=7) — any mismatch
        # means the TTL computation drifted or the ON CONFLICT path uses a
        # different value than the INSERT path.
        bound_expires_values = [
            v for v in compiled.params.values() if isinstance(v, datetime)
        ]
        assert expected_expires in bound_expires_values, (
            f"Expected ttl_expires_at={expected_expires} in compiled bind params, "
            f"got {bound_expires_values}"
        )

    @pytest.mark.asyncio
    async def test_set_conflict_updates_row(self):
        """set() uses ON CONFLICT to upsert — calling twice with same key overwrites.

        Simulates two consecutive set() calls with the same cache_key.
        Both should invoke session.execute (upsert, not insert-then-fail).

        QA iter-3 F2: also asserts the compiled SQL contains ``ON CONFLICT``.
        Without this, ``await_count == 2`` would pass even for plain INSERT
        statements that would fail on duplicate key at the DB — making the
        test a no-op for the upsert contract it claims to verify.
        """
        from sqlalchemy.dialects import postgresql

        from nikita.db.repositories.backstory_cache_repository import (
            BackstoryCacheRepository,
        )

        mock_session = AsyncMock()
        mock_session.execute.return_value = MagicMock()

        repo = BackstoryCacheRepository(mock_session)

        await repo.set(
            cache_key="paris|food|finance",
            scenarios=[{"id": "a", "venue": "Le Comptoir"}],
            venues_used=["Le Comptoir"],
            ttl_days=30,
        )
        await repo.set(
            cache_key="paris|food|finance",
            scenarios=[{"id": "b", "venue": "Septime"}],
            venues_used=["Le Comptoir", "Septime"],
            ttl_days=30,
        )

        # Both calls should succeed — upsert pattern, no IntegrityError
        assert mock_session.execute.await_count == 2

        # Verify BOTH statements compile to an ON CONFLICT DO UPDATE upsert.
        # A plain INSERT would also satisfy await_count == 2 but would fail at
        # the DB layer on the second call with a duplicate-key IntegrityError.
        for call in mock_session.execute.call_args_list:
            stmt = call[0][0]
            compiled_sql = " ".join(
                str(stmt.compile(dialect=postgresql.dialect())).split()
            )
            assert "ON CONFLICT" in compiled_sql.upper(), (
                "set() must emit an ON CONFLICT upsert (not a plain INSERT); "
                f"compiled SQL:\n{compiled_sql}"
            )
            assert "DO UPDATE" in compiled_sql.upper(), (
                "ON CONFLICT clause must use DO UPDATE (not DO NOTHING); "
                f"compiled SQL:\n{compiled_sql}"
            )

    @pytest.mark.asyncio
    async def test_set_does_not_auto_commit(self):
        """set() does NOT call session.commit() — caller manages the transaction.

        Per repository pattern: auto-commit is the caller's responsibility.
        """
        from nikita.db.repositories.backstory_cache_repository import (
            BackstoryCacheRepository,
        )

        mock_session = AsyncMock()
        mock_session.execute.return_value = MagicMock()

        repo = BackstoryCacheRepository(mock_session)
        await repo.set(
            cache_key="berlin|techno|tech",
            scenarios=[],
            venues_used=[],
            ttl_days=30,
        )

        mock_session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_set_with_empty_scenarios_list(self):
        """set() accepts empty scenarios list without error (degraded-path support).

        The degraded path may store an empty scenario list as a placeholder.
        """
        from nikita.db.repositories.backstory_cache_repository import (
            BackstoryCacheRepository,
        )

        mock_session = AsyncMock()
        mock_session.execute.return_value = MagicMock()

        repo = BackstoryCacheRepository(mock_session)
        await repo.set(
            cache_key="empty|key",
            scenarios=[],
            venues_used=[],
            ttl_days=1,
        )

        mock_session.execute.assert_awaited_once()
