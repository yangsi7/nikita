"""Tests for nikita.onboarding.idempotency.IdempotencyStore (Spec 214 FR-11d).

Live-DB integration is deferred to a post-merge verification step (the
Supabase MCP path is not reachable from the implementor worktree). These
tests exercise the repo logic against an ``AsyncMock`` session +
assert the SQL shape for the DDL contract in the migration file.

Migration file:
``supabase/migrations/20260419120000_llm_idempotency_cache.sql``
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from nikita.onboarding.idempotency import (
    IDEMPOTENCY_CACHE_TTL_SECONDS,
    IdempotencyStore,
)


_MIGRATION_PATH = (
    Path(__file__).parents[2]
    / "supabase"
    / "migrations"
    / "20260419120000_llm_idempotency_cache.sql"
)


def _mock_session_with_row(row_data):
    session = AsyncMock()
    result = MagicMock()
    result.first = MagicMock(return_value=row_data)
    session.execute = AsyncMock(return_value=result)
    return session


class TestMigrationShape:
    def test_migration_applies_with_rls_and_prune_cron(self):
        """AC-T2.7.1: migration enables RLS + schedules pg_cron prune.

        DDL inspection (not live application). Live application happens
        via Supabase MCP post-merge; the shape is covered here so a
        silent drift in the migration text fails the test.
        """
        assert _MIGRATION_PATH.exists(), (
            f"migration missing at {_MIGRATION_PATH}"
        )
        sql = _MIGRATION_PATH.read_text()
        assert "CREATE TABLE IF NOT EXISTS llm_idempotency_cache" in sql
        assert "PRIMARY KEY (user_id, turn_id)" in sql
        assert "ENABLE ROW LEVEL SECURITY" in sql
        assert "CREATE POLICY" in sql
        assert 'is_admin() OR auth.role() = \'service_role\'' in sql
        # Prune cron job hourly.
        assert "llm_idempotency_cache_prune" in sql
        assert "interval '5 minutes'" in sql


class TestIdempotencyStoreGetPut:
    @pytest.mark.asyncio
    async def test_get_put_respects_5min_ttl(self):
        """AC-T2.7.2: fresh row returned; stale (>5m) row suppressed."""
        user_id = uuid4()
        turn_id = uuid4()
        body = {"nikita_reply": "hey", "progress_pct": 10}

        # --- Fresh row (HIT) ---
        fresh_ts = datetime.now(timezone.utc) - timedelta(seconds=60)
        session = _mock_session_with_row((body, 200, fresh_ts))
        store = IdempotencyStore(session)
        result = await store.get(user_id, turn_id)
        assert result is not None
        returned_body, status = result
        assert status == 200
        assert returned_body == body

        # --- Stale row (miss per TTL) ---
        stale_ts = datetime.now(timezone.utc) - timedelta(
            seconds=IDEMPOTENCY_CACHE_TTL_SECONDS + 10
        )
        session_stale = _mock_session_with_row((body, 200, stale_ts))
        store_stale = IdempotencyStore(session_stale)
        assert await store_stale.get(user_id, turn_id) is None

        # --- Missing row ---
        session_missing = _mock_session_with_row(None)
        store_missing = IdempotencyStore(session_missing)
        assert await store_missing.get(user_id, turn_id) is None

    @pytest.mark.asyncio
    async def test_put_emits_insert_with_on_conflict_do_nothing(self):
        session = AsyncMock()
        session.execute = AsyncMock()
        store = IdempotencyStore(session)

        await store.put(
            user_id=uuid4(),
            turn_id=uuid4(),
            response_body={"k": "v"},
            status_code=200,
        )
        session.execute.assert_awaited_once()
        call_args = session.execute.call_args
        sql = str(call_args.args[0])
        assert "INSERT INTO llm_idempotency_cache" in sql
        assert "ON CONFLICT (user_id, turn_id) DO NOTHING" in sql
        assert "CAST(:body AS jsonb)" in sql

    def test_ttl_constant_matches_spec(self):
        assert IDEMPOTENCY_CACHE_TTL_SECONDS == 300
