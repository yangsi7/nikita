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
