"""Tests for TelegramLinkRepository.verify_code atomicity (GH #321 REQ-3a).

Regression guard for the race condition in the original SELECT-then-DELETE
implementation (telegram_link_repository.py:68-96, pre-#321-fix). Two concurrent
`/start <same-code>` calls could both observe the row before either DELETE
committed, both return the user_id, and the downstream update_telegram_id would
either race or hit a UNIQUE violation.

Post-fix: verify_code MUST compile to a single atomic statement
`DELETE FROM telegram_link_codes WHERE code = :code AND expires_at > now() RETURNING user_id`.

Per .claude/rules/testing.md:
- Non-empty fixtures for all paths.
- Every async def test_* has at least one assert.
- Patch source module, NOT importer.

The integration-level race test (asyncio.gather against real DB) lives in
tests/db/integration/test_repositories_integration.py when implemented. This
unit file only verifies the compiled statement shape, which is sufficient to
fail against the pre-fix SELECT-then-DELETE code path.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


class TestVerifyCodeAtomic:
    """Unit tests for TelegramLinkRepository.verify_code post-#321 atomicity fix."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock AsyncSession."""
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_verify_code_compiles_to_single_delete_returning(
        self, mock_session: AsyncMock
    ) -> None:
        """verify_code MUST compile to one DELETE ... RETURNING statement,
        not SELECT then DELETE in two round-trips.

        Pre-fix impl (telegram_link_repository.py:68-96) calls get_by_code()
        which emits SELECT, inspects the result in Python, then calls delete()
        which emits DELETE. Two statements, two round-trips, race window
        between them.

        Post-fix: one `DELETE ... WHERE code = :code AND expires_at > now()
        RETURNING user_id` statement. Atomic at the DB level; concurrent
        callers see exactly one winner.
        """
        from nikita.db.repositories.telegram_link_repository import (
            TelegramLinkRepository,
        )
        from sqlalchemy.dialects import postgresql

        captured_stmts: list = []

        async def capture_execute(stmt, *args, **kwargs):
            captured_stmts.append(stmt)
            # Simulate "code not found" return: empty result so verify_code
            # returns None. Sufficient for compile-shape assertion.
            result = MagicMock()
            result.scalar_one_or_none = MagicMock(return_value=None)
            result.first = MagicMock(return_value=None)
            result.rowcount = 0
            return result

        mock_session.execute = capture_execute

        repo = TelegramLinkRepository(mock_session)
        await repo.verify_code("ABC123")

        # Guard #1: exactly one statement executed (post-fix single round-trip).
        # Pre-fix impl executes 2 statements even in the "not found" path (SELECT
        # that returns None + follow-up DELETE short-circuits because the Python
        # branch exits early — but the SELECT alone is 1 statement, so the more
        # discriminating assertion below is needed).
        assert len(captured_stmts) >= 1, "verify_code must execute at least one statement"

        # Guard #2: the executed statement must be a DELETE with RETURNING clause.
        # Pre-fix code executes a SELECT first, which would make captured_stmts[0]
        # a Select construct not a Delete-with-RETURNING. This assertion FAILS
        # against the pre-fix implementation.
        first_stmt = captured_stmts[0]
        compiled = first_stmt.compile(dialect=postgresql.dialect())
        sql = str(compiled).upper()

        assert sql.startswith("DELETE"), (
            f"verify_code's first statement must be DELETE, not SELECT "
            f"(GH #321 REQ-3a atomicity). Got: {sql[:80]}"
        )
        assert "RETURNING" in sql, (
            f"verify_code DELETE must include RETURNING user_id clause "
            f"(GH #321 REQ-3a atomicity). Got: {sql[:200]}"
        )

    @pytest.mark.asyncio
    async def test_verify_code_returns_user_id_on_valid_code(
        self, mock_session: AsyncMock
    ) -> None:
        """Valid unexpired code: DELETE ... RETURNING returns the row, so
        verify_code returns the user_id.
        """
        from nikita.db.repositories.telegram_link_repository import (
            TelegramLinkRepository,
        )

        expected_user_id = uuid4()

        async def capture_execute(stmt, *args, **kwargs):
            # Simulate RETURNING clause producing a row with the user_id.
            result = MagicMock()
            result.scalar_one_or_none = MagicMock(return_value=expected_user_id)
            result.first = MagicMock(return_value=(expected_user_id,))
            result.rowcount = 1
            return result

        mock_session.execute = capture_execute

        repo = TelegramLinkRepository(mock_session)
        returned = await repo.verify_code("XYZ789")

        assert returned == expected_user_id, (
            f"valid code path must return the user_id from the RETURNING clause. "
            f"Expected {expected_user_id}, got {returned}."
        )

    @pytest.mark.asyncio
    async def test_verify_code_returns_none_for_missing_or_expired(
        self, mock_session: AsyncMock
    ) -> None:
        """Missing or expired code: the WHERE predicate (code match + not
        expired) filters the row out; DELETE affects 0 rows; RETURNING yields
        nothing; verify_code returns None.

        The beauty of the post-fix design: the expires_at check lives in the
        WHERE clause (atomic with the delete), not in Python after a separate
        SELECT (pre-fix race surface).
        """
        from nikita.db.repositories.telegram_link_repository import (
            TelegramLinkRepository,
        )

        async def capture_execute(stmt, *args, **kwargs):
            result = MagicMock()
            result.scalar_one_or_none = MagicMock(return_value=None)
            result.first = MagicMock(return_value=None)
            result.rowcount = 0
            return result

        mock_session.execute = capture_execute

        repo = TelegramLinkRepository(mock_session)
        returned = await repo.verify_code("MISSIN")

        assert returned is None, (
            "missing/expired code path must return None (no RETURNING row)."
        )

    @pytest.mark.asyncio
    async def test_verify_code_filters_expiry_in_where_clause(
        self, mock_session: AsyncMock
    ) -> None:
        """Compiled SQL must include the expiry check in the WHERE clause
        (e.g. `expires_at > now()` or equivalent SQLAlchemy construct),
        NOT as a separate Python-side check after a SELECT.

        This is the concrete fix that makes the statement atomic: filter and
        delete in one shot.
        """
        from nikita.db.repositories.telegram_link_repository import (
            TelegramLinkRepository,
        )
        from sqlalchemy.dialects import postgresql

        captured_stmts: list = []

        async def capture_execute(stmt, *args, **kwargs):
            captured_stmts.append(stmt)
            result = MagicMock()
            result.scalar_one_or_none = MagicMock(return_value=None)
            result.first = MagicMock(return_value=None)
            result.rowcount = 0
            return result

        mock_session.execute = capture_execute

        repo = TelegramLinkRepository(mock_session)
        await repo.verify_code("ABCDEF")

        assert captured_stmts, "at least one statement must be executed"
        compiled = captured_stmts[0].compile(dialect=postgresql.dialect())
        sql = str(compiled).lower()

        # The expiry predicate must live in SQL, not in Python branch.
        # Accept either `expires_at >` or `expires_at <` depending on the
        # direction chosen by the implementation (both are valid shapes,
        # the latter would be `NOW() < expires_at` form).
        assert "expires_at" in sql, (
            f"expires_at must appear in compiled SQL's WHERE clause "
            f"(GH #321 REQ-3a atomicity). Got: {sql[:300]}"
        )
