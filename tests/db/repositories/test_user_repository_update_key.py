"""Tests for UserRepository.update_onboarding_profile_key (Spec 213, F-01).

Verifies:
- jsonb_set SQL function is used (not a Python-level merge)
- cast(json.dumps(value), JSONB) is used — NOT cast(value, JSONB) (PR #279/#282 gotcha)
- Method executes without error when user doesn't exist (silent no-op)

Per .claude/rules/testing.md:
- Non-empty fixtures for all paths
- Every async def test_* has at least one assert
- Patch source module, NOT importer
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch, call
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


TEST_USER_ID = uuid4()


class TestUpdateOnboardingProfileKey:
    """Unit tests for UserRepository.update_onboarding_profile_key."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock AsyncSession."""
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock(return_value=MagicMock(rowcount=1))
        session.flush = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_executes_update_statement(self, mock_session: AsyncMock):
        """update_onboarding_profile_key calls session.execute exactly once."""
        from nikita.db.repositories.user_repository import UserRepository

        repo = UserRepository(mock_session)
        await repo.update_onboarding_profile_key(TEST_USER_ID, "pipeline_state", "pending")

        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_compiled_sql_contains_jsonb_set(self, mock_session: AsyncMock):
        """Compiled SQL string contains jsonb_set — not a Python-level merge."""
        from nikita.db.repositories.user_repository import UserRepository
        from sqlalchemy.dialects import postgresql

        captured_stmt = None

        async def capture_execute(stmt, *args, **kwargs):
            nonlocal captured_stmt
            captured_stmt = stmt
            return MagicMock(rowcount=1)

        mock_session.execute = capture_execute

        repo = UserRepository(mock_session)
        await repo.update_onboarding_profile_key(TEST_USER_ID, "pipeline_state", "pending")

        assert captured_stmt is not None
        # Compile to PostgreSQL dialect so we can inspect the rendered SQL
        compiled = captured_stmt.compile(dialect=postgresql.dialect())
        sql_str = str(compiled)
        assert "jsonb_set" in sql_str.lower(), (
            f"Expected 'jsonb_set' in compiled SQL, got:\n{sql_str}"
        )

    @pytest.mark.asyncio
    async def test_uses_json_dumps_not_raw_value(self, mock_session: AsyncMock):
        """The JSONB cast wraps json.dumps(value) — NOT the raw Python value.

        This is a regression guard for PR #279/#282 gotcha: cast(value, JSONB)
        is INVALID for strings; cast(json.dumps(value), JSONB) is correct.

        We verify via compiled.params: the bind value should be '"pending"'
        (JSON-encoded string with surrounding quotes), not 'pending' (bare string).
        json.dumps("pending") == '"pending"'.
        """
        from nikita.db.repositories.user_repository import UserRepository
        from sqlalchemy.dialects import postgresql

        captured_stmt = None

        async def capture_execute(stmt, *args, **kwargs):
            nonlocal captured_stmt
            captured_stmt = stmt
            return MagicMock(rowcount=1)

        mock_session.execute = capture_execute

        repo = UserRepository(mock_session)
        await repo.update_onboarding_profile_key(TEST_USER_ID, "pipeline_state", "pending")

        assert captured_stmt is not None
        compiled = captured_stmt.compile(dialect=postgresql.dialect())
        params = compiled.params
        # json.dumps("pending") == '"pending"' — the value in params must be JSON-encoded
        expected_json = json.dumps("pending")  # '"pending"'
        # Look for the param value that matches the JSON-encoded string
        assert expected_json in params.values(), (
            f"Expected JSON-encoded value '{expected_json}' in compiled params, "
            f"got: {dict(params)}"
        )

    @pytest.mark.asyncio
    async def test_key_appears_in_jsonb_path(self, mock_session: AsyncMock):
        """The key is embedded in the jsonb_set path param as '{<key>}'."""
        from nikita.db.repositories.user_repository import UserRepository
        from sqlalchemy.dialects import postgresql

        captured_stmt = None

        async def capture_execute(stmt, *args, **kwargs):
            nonlocal captured_stmt
            captured_stmt = stmt
            return MagicMock(rowcount=1)

        mock_session.execute = capture_execute

        repo = UserRepository(mock_session)
        await repo.update_onboarding_profile_key(TEST_USER_ID, "pipeline_state", "ready")

        assert captured_stmt is not None
        compiled = captured_stmt.compile(dialect=postgresql.dialect())
        params = compiled.params
        # The jsonb_set path argument should be '{pipeline_state}'
        assert "{pipeline_state}" in params.values(), (
            f"Expected '{{pipeline_state}}' path in compiled params, got: {dict(params)}"
        )

    @pytest.mark.asyncio
    async def test_noop_when_user_missing(self, mock_session: AsyncMock):
        """When user doesn't exist, UPDATE affects 0 rows — no exception raised."""
        from nikita.db.repositories.user_repository import UserRepository

        mock_session.execute = AsyncMock(return_value=MagicMock(rowcount=0))

        repo = UserRepository(mock_session)
        # Must not raise
        await repo.update_onboarding_profile_key(TEST_USER_ID, "pipeline_state", "pending")

        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_non_string_value_json_serialized(self, mock_session: AsyncMock):
        """Non-string values (dict, int, list) are also JSON-serialized correctly.

        json.dumps({"venues": [...], "count": 3}) should appear in compiled params,
        not the raw Python dict.
        """
        from nikita.db.repositories.user_repository import UserRepository
        from sqlalchemy.dialects import postgresql

        captured_stmt = None

        async def capture_execute(stmt, *args, **kwargs):
            nonlocal captured_stmt
            captured_stmt = stmt
            return MagicMock(rowcount=1)

        mock_session.execute = capture_execute

        repo = UserRepository(mock_session)
        value = {"venues": ["Berghain"], "count": 3}
        await repo.update_onboarding_profile_key(TEST_USER_ID, "meta", value)

        assert captured_stmt is not None
        compiled = captured_stmt.compile(dialect=postgresql.dialect())
        params = compiled.params
        expected_json = json.dumps(value)
        assert expected_json in params.values(), (
            f"Expected JSON-encoded dict '{expected_json}' in compiled params, "
            f"got: {dict(params)}"
        )
