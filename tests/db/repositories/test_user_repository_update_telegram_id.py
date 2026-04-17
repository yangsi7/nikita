"""Tests for UserRepository.update_telegram_id (GH #321 REQ-4).

The post-#321 `_handle_start <code>` flow needs to bind a portal user_id
to a Telegram user_id atomically, without a SELECT-then-UPDATE race and
without ever silently overwriting an existing binding on someone else's row.

Semantics (per planning brief REQ-4):

  UPDATE users SET telegram_id = :tid
  WHERE id = :uid
    AND (telegram_id IS NULL OR telegram_id = :tid)
  RETURNING telegram_id

- rowcount == 1, returned value == :tid: binding succeeded OR was already
  set to the same :tid (idempotent no-op). We distinguish via a check on
  the pre-update state or the returned-vs-input comparison.
- rowcount == 0: either user_id not found OR `telegram_id` IS already held
  by a different user_id (UNIQUE constraint would fire, but the predicate
  filters out before the UPDATE fires). Disambiguate via one SELECT on
  telegram_id, then raise `TelegramIdAlreadyBoundByOtherUserError` for
  the latter case.

BindResult enum:
- BOUND: fresh binding, `users.telegram_id` was NULL before.
- ALREADY_BOUND_SAME_USER: user_id already had this telegram_id; no-op.
- (conflict case raises, does not return a BindResult)

Test shape rationale:
- Unit level: patch `session.execute` and assert the compiled SQL statement
  shape (UPDATE + WHERE predicate + RETURNING). This is the ONLY reliable
  unit-level guard against the #316/#318 class of SQLAlchemy bind-processor
  regressions. Real-DB three-case integration test lives in
  tests/db/integration/test_repositories_integration.py (REQ-5).

Per .claude/rules/testing.md:
- Non-empty fixtures for all paths.
- Every async def test_* has at least one assert.
- Patch source module, not importer.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


class TestUpdateTelegramIdStatementShape:
    """Assert the compiled SQL statement shape for update_telegram_id."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_update_telegram_id_is_single_update_returning_statement(
        self, mock_session: AsyncMock
    ) -> None:
        """The compiled SQL MUST be UPDATE ... WHERE (telegram_id IS NULL OR
        telegram_id = :tid) ... RETURNING telegram_id. This is the atomic
        shape that prevents silent-overwrite and race without a pre-check
        round-trip.

        Guard class: post-fix impl MUST NOT fall back to SELECT-then-UPDATE.
        Pre-fix would have emitted a SELECT first, which this assertion
        catches by inspecting captured_stmts[0].
        """
        from nikita.db.repositories.user_repository import UserRepository
        from sqlalchemy.dialects import postgresql

        captured_stmts: list = []

        async def capture_execute(stmt, *args, **kwargs):
            captured_stmts.append(stmt)
            result = MagicMock()
            # rowcount == 1 keeps control flow in the happy path; we care only
            # about the statement shape here.
            result.rowcount = 1
            result.first = MagicMock(return_value=(12345,))
            result.scalar_one_or_none = MagicMock(return_value=12345)
            return result

        mock_session.execute = capture_execute

        repo = UserRepository(mock_session)
        await repo.update_telegram_id(uuid4(), 12345)

        assert captured_stmts, "update_telegram_id must execute at least one statement"
        first_stmt = captured_stmts[0]
        compiled = first_stmt.compile(dialect=postgresql.dialect())
        sql = str(compiled).upper()

        assert sql.startswith("UPDATE"), (
            f"update_telegram_id's first statement must be UPDATE, not SELECT "
            f"(GH #321 REQ-4 atomicity). Got: {sql[:120]}"
        )
        assert "RETURNING" in sql, (
            f"update_telegram_id must RETURN telegram_id for conflict disambiguation. "
            f"Got: {sql[:200]}"
        )
        # Predicate must filter the conflict case in SQL, not in Python
        assert "TELEGRAM_ID" in sql and ("IS NULL" in sql or "IS NOT DISTINCT FROM" in sql), (
            f"WHERE clause must include (telegram_id IS NULL OR telegram_id = :tid) "
            f"predicate. Got: {sql[:400]}"
        )


class TestUpdateTelegramIdThreeCases:
    """Unit-level tests for the three outcome branches.

    Real-DB coverage of these branches lives in
    tests/db/integration/test_repositories_integration.py::TestUserRepositoryIntegration::
      test_update_telegram_id_three_cases (REQ-5).
    """

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_fresh_bind_returns_bound(self, mock_session: AsyncMock) -> None:
        """telegram_id was NULL; UPDATE sets it; returns BindResult.BOUND."""
        from nikita.db.repositories.user_repository import (
            BindResult,
            UserRepository,
        )

        # Two calls happen in the impl: an initial SELECT-for-current-telegram_id
        # probe (to distinguish fresh-bind vs same-user re-bind), then the
        # atomic UPDATE. The probe returns None (no existing binding).
        execute_call_idx = {"i": 0}

        async def capture_execute(stmt, *args, **kwargs):
            idx = execute_call_idx["i"]
            execute_call_idx["i"] += 1
            result = MagicMock()
            if idx == 0:
                # Probe: SELECT telegram_id FROM users WHERE id = :uid
                result.scalar_one_or_none = MagicMock(return_value=None)
                result.first = MagicMock(return_value=(None,))
                result.rowcount = 1
            else:
                # UPDATE ... RETURNING
                result.scalar_one_or_none = MagicMock(return_value=12345)
                result.first = MagicMock(return_value=(12345,))
                result.rowcount = 1
            return result

        mock_session.execute = capture_execute

        repo = UserRepository(mock_session)
        outcome = await repo.update_telegram_id(uuid4(), 12345)

        assert outcome == BindResult.BOUND, (
            f"fresh bind (telegram_id was NULL) must return BindResult.BOUND. "
            f"Got: {outcome}"
        )

    @pytest.mark.asyncio
    async def test_idempotent_same_user_rebind_returns_already_bound_same_user(
        self, mock_session: AsyncMock
    ) -> None:
        """user_id already has this telegram_id; idempotent no-op; returns
        BindResult.ALREADY_BOUND_SAME_USER. No error raised."""
        from nikita.db.repositories.user_repository import (
            BindResult,
            UserRepository,
        )

        execute_call_idx = {"i": 0}

        async def capture_execute(stmt, *args, **kwargs):
            idx = execute_call_idx["i"]
            execute_call_idx["i"] += 1
            result = MagicMock()
            if idx == 0:
                # Probe finds the same telegram_id already set on this user.
                result.scalar_one_or_none = MagicMock(return_value=12345)
                result.first = MagicMock(return_value=(12345,))
                result.rowcount = 1
            else:
                # UPDATE is a no-op but the WHERE predicate still matches
                # (telegram_id = :tid branch); rowcount == 1.
                result.scalar_one_or_none = MagicMock(return_value=12345)
                result.first = MagicMock(return_value=(12345,))
                result.rowcount = 1
            return result

        mock_session.execute = capture_execute

        repo = UserRepository(mock_session)
        outcome = await repo.update_telegram_id(uuid4(), 12345)

        assert outcome == BindResult.ALREADY_BOUND_SAME_USER, (
            f"same-user re-bind must return BindResult.ALREADY_BOUND_SAME_USER "
            f"(idempotent, no error). Got: {outcome}"
        )

    @pytest.mark.asyncio
    async def test_conflict_different_user_raises(
        self, mock_session: AsyncMock
    ) -> None:
        """telegram_id is bound to a different user_id; UPDATE WHERE predicate
        filters this user out (rowcount == 0); after disambiguation via a
        SELECT, raise TelegramIdAlreadyBoundByOtherUserError."""
        from nikita.db.repositories.user_repository import (
            TelegramIdAlreadyBoundByOtherUserError,
            UserRepository,
        )

        execute_call_idx = {"i": 0}

        async def capture_execute(stmt, *args, **kwargs):
            idx = execute_call_idx["i"]
            execute_call_idx["i"] += 1
            result = MagicMock()
            if idx == 0:
                # Probe: this user has no existing telegram_id.
                result.scalar_one_or_none = MagicMock(return_value=None)
                result.first = MagicMock(return_value=(None,))
                result.rowcount = 1
            elif idx == 1:
                # UPDATE: predicate filters out because telegram_id belongs
                # to another row. rowcount == 0 triggers conflict path.
                result.scalar_one_or_none = MagicMock(return_value=None)
                result.first = MagicMock(return_value=None)
                result.rowcount = 0
            else:
                # Disambiguation SELECT: telegram_id IS held by someone.
                result.scalar_one_or_none = MagicMock(return_value=uuid4())
                result.first = MagicMock(return_value=(uuid4(),))
                result.rowcount = 1
            return result

        mock_session.execute = capture_execute

        repo = UserRepository(mock_session)

        with pytest.raises(TelegramIdAlreadyBoundByOtherUserError) as exc_info:
            await repo.update_telegram_id(uuid4(), 12345)

        # The exception must carry the conflicting telegram_id so the caller
        # can produce a useful error message to the end user.
        assert hasattr(exc_info.value, "telegram_id") or "12345" in str(exc_info.value), (
            "TelegramIdAlreadyBoundByOtherUserError must surface the conflicting telegram_id"
        )
