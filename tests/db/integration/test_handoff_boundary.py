"""Tests for Spec 214 T4.2 (FR-11e) — handoff-greeting one-shot
claim-intent column + repo methods.

Validates:

- AC-T4.2.1 (migration shape): the migration file exists and documents
  the column + partial index. Schema enforcement is via Supabase MCP
  (live DB), so this test asserts the migration STUB documents the
  expected DDL — same pattern as other "applied via MCP" stubs.
- AC-T4.2.2 (atomic claim): ``UserRepository.claim_handoff_intent``
  emits the expected predicate-filter ``UPDATE … RETURNING`` shape
  and returns True only on rowcount==1; second concurrent call
  (rowcount==0) returns False without re-firing.
- AC-T4.2.3 (clear pending_handoff): ``clear_pending_handoff`` issues
  ``UPDATE … SET pending_handoff = false WHERE id = :uid``.
- AC-T4.2.4 (reset dispatch): ``reset_handoff_dispatch`` issues
  ``UPDATE … SET handoff_greeting_dispatched_at = NULL WHERE id = :uid``.

Per .claude/rules/testing.md: ORM-mock unit tests for repo shape, not
live Postgres. Live-DB schema is exercised by the deployment + the
T4.5 stranded-user migration script + dogfood pass.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession


MIGRATION_FILE = (
    Path(__file__).resolve().parents[3]
    / "supabase"
    / "migrations"
    / "20260419150000_users_handoff_greeting_dispatched_at.sql"
)


def test_migration_adds_column_and_partial_index() -> None:
    """AC-T4.2.1: the migration stub MUST document both the new column
    and the partial index used by the pg_cron backstop predicate.

    Stubs are comment-only (DDL applied via Supabase MCP) per
    nikita/db/CLAUDE.md "Migrations" section. The stub is the single
    auditable record of the schema delta in version control, so a
    snapshot test of its keywords is the strongest local guard against
    silent column-name / index-shape drift.
    """
    assert MIGRATION_FILE.exists(), (
        f"migration stub missing at {MIGRATION_FILE}; T4.2.1 requires "
        "the column + partial index DDL be tracked in version control"
    )
    body = MIGRATION_FILE.read_text()
    # Column DDL surface
    assert "handoff_greeting_dispatched_at" in body
    assert "TIMESTAMPTZ" in body
    # Partial index surface (used by pg_cron backstop / FR-11e B1)
    assert "idx_users_handoff_backstop" in body
    assert "pending_handoff = TRUE" in body
    assert "telegram_id IS NOT NULL" in body


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    return session


class TestClaimHandoffIntent:
    """AC-T4.2.2: atomic UPDATE..RETURNING gates the one-shot dispatch."""

    @pytest.mark.asyncio
    async def test_first_call_returns_true_with_predicate_filter_update(
        self, mock_session: AsyncMock
    ) -> None:
        """Happy path: rowcount==1, returned id non-None → True.

        Compiled SQL MUST be UPDATE...RETURNING with the predicate
        filter (id = :uid AND dispatched_at IS NULL AND
        pending_handoff IS TRUE). The atomic-claim semantic is the
        ENTIRE point of the method; a non-atomic load+modify here would
        defeat the second-concurrent-/start race guard (FR-11e §2.5).
        """
        from nikita.db.repositories.user_repository import UserRepository

        captured: list = []

        async def capture(stmt, *args, **kwargs):
            captured.append(stmt)
            result = MagicMock()
            # First claim succeeds: row matched the predicate.
            result.scalar_one_or_none = MagicMock(return_value=uuid4())
            return result

        mock_session.execute = capture

        repo = UserRepository(mock_session)
        first = await repo.claim_handoff_intent(uuid4())
        assert first is True

        # Compiled SQL surface check — the predicate is the load-bearing
        # detail. Compile against the postgres dialect to avoid the
        # generic-dialect placeholders shifting the comparison shape.
        compiled = str(
            captured[0].compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": False},
            )
        )
        assert "UPDATE users" in compiled
        assert "handoff_greeting_dispatched_at IS NULL" in compiled
        assert "pending_handoff IS true" in compiled
        assert "RETURNING" in compiled

    @pytest.mark.asyncio
    async def test_second_concurrent_call_returns_false(
        self, mock_session: AsyncMock
    ) -> None:
        """Race guard: rowcount==0 (predicate already failed) → False.

        Models the second concurrent /start <code> for the same user:
        the first claim flipped dispatched_at to NOW(), so the second
        UPDATE's WHERE clause matches zero rows and RETURNING is empty.
        Caller MUST receive False so it skips the greeting dispatch.
        """
        from nikita.db.repositories.user_repository import UserRepository

        async def capture(stmt, *args, **kwargs):
            result = MagicMock()
            # Second claim: zero rows matched.
            result.scalar_one_or_none = MagicMock(return_value=None)
            return result

        mock_session.execute = capture

        repo = UserRepository(mock_session)
        second = await repo.claim_handoff_intent(uuid4())
        assert second is False


class TestClearPendingHandoff:
    """AC-T4.2.3: clear_pending_handoff issues the expected UPDATE."""

    @pytest.mark.asyncio
    async def test_clear_pending_handoff_emits_predicate_update(
        self, mock_session: AsyncMock
    ) -> None:
        from nikita.db.repositories.user_repository import UserRepository

        captured: list = []

        async def capture(stmt, *args, **kwargs):
            captured.append(stmt)
            return MagicMock()

        mock_session.execute = capture

        repo = UserRepository(mock_session)
        await repo.clear_pending_handoff(uuid4())

        compiled = str(
            captured[0].compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": False},
            )
        )
        assert "UPDATE users" in compiled
        assert "pending_handoff" in compiled
        # Tightly scoped: only the by-id predicate. Bulk update would
        # be a defect (would clear every user's pending_handoff).
        assert "users.id = " in compiled


class TestResetHandoffDispatch:
    """AC-T4.2.4: reset_handoff_dispatch nulls dispatched_at."""

    @pytest.mark.asyncio
    async def test_reset_handoff_dispatch_sets_dispatched_at_null(
        self, mock_session: AsyncMock
    ) -> None:
        from nikita.db.repositories.user_repository import UserRepository

        captured: list = []

        async def capture(stmt, *args, **kwargs):
            captured.append(stmt)
            return MagicMock()

        mock_session.execute = capture

        repo = UserRepository(mock_session)
        await repo.reset_handoff_dispatch(uuid4())

        compiled = str(
            captured[0].compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": False},
            )
        )
        assert "UPDATE users" in compiled
        assert "handoff_greeting_dispatched_at" in compiled
        assert "users.id = " in compiled
