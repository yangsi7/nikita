"""Tests for TelegramSignupSessionRepository.

Verifies atomic compare-and-swap (CAS) FSM transitions per Spec 215 §7.2.1.

Each transition is a CAS update that asserts the prior signup_state and fails
loud if 0 rows are returned (concurrent worker race or expired window).

AC Coverage:
- AC-3.2 (CODE_SENT → MAGIC_LINK_SENT atomic)
- AC-5.5 (MAGIC_LINK_SENT → COMPLETED idempotent)
- §7.2.1 hard-rule: every FSM transition is CAS, never read-modify-write.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from nikita.db.repositories.telegram_signup_session_repository import (
    ConcurrentTransitionError,
    ExpiredOrConcurrentError,
    TelegramSignupSessionRepository,
)


class TestTelegramSignupSessionRepositoryCAS:
    """CAS transition contract per spec §7.2.1."""

    @pytest.fixture
    def mock_session(self):
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        return TelegramSignupSessionRepository(mock_session)

    # AC-1: AWAITING_EMAIL → CODE_SENT CAS

    @pytest.mark.asyncio
    async def test_transition_to_code_sent_returns_id_on_success(
        self, repo, mock_session
    ):
        """Successful CAS update returns the row id."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "row-uuid-123"
        mock_session.execute.return_value = mock_result

        row_id = await repo.transition_to_code_sent(
            telegram_id=42,
            email="user@example.com",
        )

        assert row_id == "row-uuid-123"
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_transition_to_code_sent_raises_on_zero_rows(
        self, repo, mock_session
    ):
        """0 rows returned (state mismatch) raises ConcurrentTransitionError."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with pytest.raises(ConcurrentTransitionError):
            await repo.transition_to_code_sent(
                telegram_id=42,
                email="user@example.com",
            )

    # AC-2: CODE_SENT → MAGIC_LINK_SENT CAS (with TTL guard)

    @pytest.mark.asyncio
    async def test_transition_to_magic_link_sent_returns_id_on_success(
        self, repo, mock_session
    ):
        """Successful CAS update returns the row id."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "row-uuid-456"
        mock_session.execute.return_value = mock_result

        row_id = await repo.transition_to_magic_link_sent(
            telegram_id=42,
            hashed_token="hash-abc",
            verification_type="magiclink",
        )

        assert row_id == "row-uuid-456"
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_transition_to_magic_link_sent_raises_when_expired(
        self, repo, mock_session
    ):
        """0 rows (expired or already advanced) raises ExpiredOrConcurrentError."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with pytest.raises(ExpiredOrConcurrentError):
            await repo.transition_to_magic_link_sent(
                telegram_id=42,
                hashed_token="hash-xyz",
                verification_type="signup",
            )

    # AC-3: MAGIC_LINK_SENT → COMPLETED is idempotent

    @pytest.mark.asyncio
    async def test_delete_on_completion_returns_one_when_row_existed(
        self, repo, mock_session
    ):
        """Deleting an existing magic_link_sent row returns rowcount."""
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        count = await repo.delete_on_completion(telegram_id=42)
        assert count == 1

    @pytest.mark.asyncio
    async def test_delete_on_completion_is_idempotent_on_zero_rows(
        self, repo, mock_session
    ):
        """Re-tap (no row) returns 0 — must NOT raise."""
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        # Idempotent: returns 0, no exception
        count = await repo.delete_on_completion(telegram_id=42)
        assert count == 0

    # AC-4: increment_attempts is atomic

    @pytest.mark.asyncio
    async def test_increment_attempts_returns_new_count(
        self, repo, mock_session
    ):
        """Atomic increment returns the new attempts value."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 2
        mock_session.execute.return_value = mock_result

        new_count = await repo.increment_attempts(telegram_id=42)
        assert new_count == 2
        mock_session.execute.assert_awaited_once()


class TestGetByEmailCaseInsensitive:
    """Spec 216 EM-2: get_by_email must be case-insensitive.

    Supabase normalizes `auth.users.email` to lowercase, but the FSM
    row's email column comes from the bot's free-text capture
    (`signup_handler.handle_email`) and preserves the user's typed
    casing. Without case-insensitive matching, `/auth/confirm`
    autobind silently no-ops with `no_session=True` even when the
    session row exists.

    Approach: compile the `select` to a SQL string and assert
    `LOWER(...)` appears on both sides of the equality. This is
    falsifiable — reverting `get_by_email` to plain `==` would drop
    `lower(` from the SQL and the test would fail.
    """

    @pytest.fixture
    def mock_session(self):
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        return TelegramSignupSessionRepository(mock_session)

    @pytest.mark.asyncio
    async def test_compiled_sql_uses_lower_on_both_sides(
        self, repo, mock_session
    ):
        """The WHERE clause must wrap BOTH stored email and bound param
        in LOWER() so case-mismatched rows still match."""
        from sqlalchemy.dialects import postgresql

        captured = {}

        async def _capture_execute(stmt):
            captured["stmt"] = stmt
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            return mock_result

        mock_session.execute.side_effect = _capture_execute

        await repo.get_by_email("Test@Example.COM")

        assert "stmt" in captured, "execute() was not called"
        compiled = str(
            captured["stmt"].compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        )
        # Postgres compiler emits `lower(...)` lowercase. Both sides
        # must be wrapped — single-sided lowering still misses rows.
        assert compiled.lower().count("lower(") >= 2, (
            f"Expected LOWER() on both sides of email comparison; "
            f"compiled SQL: {compiled}"
        )
        # And the lowercase form of the bound literal is what the
        # query compares against; the SQL contains the lower-cased
        # email so a mixed-case stored row can match.
        assert "test@example.com" in compiled.lower(), (
            f"Lower-cased email literal missing from compiled SQL: "
            f"{compiled}"
        )

    @pytest.mark.asyncio
    async def test_caller_with_lowercase_email_finds_uppercase_row(
        self, repo, mock_session
    ):
        """End-to-end shape: a caller passing `test@example.com`
        retrieves the row even when stored as `Test@Example.com`.

        Mock-DB shape: the comparator emitted by SQLAlchemy is what
        the real DB would evaluate. We assert that the comparator is
        symmetric-lower on the compiled SQL (both sides), and that
        the API returns the row as the caller expects.
        """
        from sqlalchemy.dialects import postgresql

        fake_row = MagicMock()
        fake_row.telegram_id = 999
        fake_row.email = "Test@Example.com"  # stored mixed-case
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = fake_row
        mock_session.execute.return_value = mock_result

        # Caller passes lowercase (e.g. JWT.email from Supabase auth)
        result = await repo.get_by_email("test@example.com")
        assert result is fake_row

        # Sanity: confirm the SQL was lower-symmetric, so against a
        # real DB this would ALSO match `Test@Example.com` storage.
        stmt = mock_session.execute.call_args[0][0]
        compiled = str(
            stmt.compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        )
        assert compiled.lower().count("lower(") >= 2
