"""Tests for asyncpg session-poison prevention in MessageHandler (GH #624).

Root cause: when get_by_telegram_id_for_update raises (e.g., lock timeout, statement
timeout, or DB error), the asyncpg connection's transaction enters FAILED state.
The except-Exception at message_handler.py:203 catches the error but does NOT
rollback. The fallback get_by_telegram_id call at :210 then hits
InFailedSQLTransactionError.

Fix: rollback the session inside the except block BEFORE executing the fallback
query, so the transaction is clean for subsequent operations.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, call
from sqlalchemy.exc import OperationalError


class TestMessageHandlerLockFallbackRollback:
    """MessageHandler.handle() must rollback before the lock-fallback read (GH #624)."""

    @pytest.fixture
    def mock_session(self):
        """A mock AsyncSession with rollback tracking."""
        session = AsyncMock()
        session.rollback = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.fixture
    def mock_user_repo(self, mock_session):
        """UserRepository mock that fails FOR UPDATE but succeeds on plain get."""
        repo = AsyncMock()
        repo.session = mock_session
        # Simulate lock/timeout failure on FOR UPDATE
        repo.get_by_telegram_id_for_update = AsyncMock(
            side_effect=OperationalError("lock timeout", {}, None)
        )
        # Plain get returns None (user not found for new signup)
        repo.get_by_telegram_id = AsyncMock(return_value=None)
        return repo

    @pytest.mark.asyncio
    async def test_rollback_called_before_fallback_on_lock_failure(
        self, mock_session, mock_user_repo
    ):
        """When FOR UPDATE fails, session.rollback() must be called BEFORE
        the fallback get_by_telegram_id(), otherwise the session is poisoned.

        This is the GH #624 root cause: fallback query runs on a FAILED
        transaction → InFailedSQLTransactionError on every subsequent query.

        Assertion tests ORDER, not merely presence: rollback index must be
        strictly less than fallback index in the parent mock call list.
        """
        from nikita.platforms.telegram.message_handler import MessageHandler

        mock_bot = AsyncMock()
        mock_bot.send_message = AsyncMock()

        # Build a minimal MessageHandler with DI
        handler = MessageHandler.__new__(MessageHandler)
        handler.bot = mock_bot
        handler.user_repository = mock_user_repo
        handler._pre_onboard_gate_fires = AsyncMock(return_value=True)

        from types import SimpleNamespace
        message = SimpleNamespace(
            message_id=1,
            chat=SimpleNamespace(id=999),
            from_=SimpleNamespace(id=12345),
            text="hello",
        )

        # Attach both to a parent mock so we can check call ORDER.
        parent = MagicMock()
        parent.attach_mock(mock_session.rollback, "rollback")
        parent.attach_mock(mock_user_repo.get_by_telegram_id, "fallback")

        await handler.handle(message)

        # Both must have been called exactly once.
        mock_session.rollback.assert_awaited_once()
        mock_user_repo.get_by_telegram_id.assert_awaited_once_with(12345)

        # ORDER check: rollback MUST appear before the fallback read (GH #624).
        # If production called fallback first then rolled back, this fails.
        rollback_idx = parent.mock_calls.index(call.rollback())
        fallback_idx = parent.mock_calls.index(call.fallback(12345))
        assert rollback_idx < fallback_idx, (
            f"rollback() must be called BEFORE fallback get_by_telegram_id(): "
            f"rollback at index {rollback_idx}, fallback at index {fallback_idx}. "
            "GH #624: running fallback on a FAILED transaction poisons the pool."
        )

    @pytest.mark.asyncio
    async def test_rollback_raises_fallback_still_reached(
        self, mock_session, mock_user_repo
    ):
        """When rollback itself raises (dead connection), fallback STILL executes.

        Without a try/except around the rollback call, a secondary exception in
        rollback causes the except-block to re-raise, abandoning the fallback read
        silently — user sees 'Something went wrong' for a transient lock timeout
        (GH #624 yellow finding).
        """
        from nikita.platforms.telegram.message_handler import MessageHandler

        mock_bot = AsyncMock()
        mock_bot.send_message = AsyncMock()

        # Rollback itself explodes (dead connection scenario)
        mock_session.rollback = AsyncMock(
            side_effect=OperationalError("connection lost", {}, None)
        )

        handler = MessageHandler.__new__(MessageHandler)
        handler.bot = mock_bot
        handler.user_repository = mock_user_repo
        handler._pre_onboard_gate_fires = AsyncMock(return_value=True)

        from types import SimpleNamespace
        message = SimpleNamespace(
            message_id=1,
            chat=SimpleNamespace(id=999),
            from_=SimpleNamespace(id=12345),
            text="hello",
        )

        # Should NOT raise — fallback must be reached even if rollback fails
        await handler.handle(message)

        # Fallback read must still be called despite rollback failure
        mock_user_repo.get_by_telegram_id.assert_awaited_once_with(12345)

    @pytest.mark.asyncio
    async def test_no_rollback_on_clean_lock_path(self, mock_session):
        """When FOR UPDATE succeeds, no spurious rollback should be called."""
        from nikita.platforms.telegram.message_handler import MessageHandler

        mock_user = MagicMock()
        mock_user.id = "some-uuid"
        mock_user.telegram_id = 12345

        mock_user_repo = AsyncMock()
        mock_user_repo.session = mock_session
        mock_user_repo.get_by_telegram_id_for_update = AsyncMock(return_value=mock_user)
        mock_user_repo.get_by_telegram_id = AsyncMock(return_value=mock_user)

        mock_bot = AsyncMock()
        mock_bot.send_message = AsyncMock()

        handler = MessageHandler.__new__(MessageHandler)
        handler.bot = mock_bot
        handler.user_repository = mock_user_repo
        handler._pre_onboard_gate_fires = AsyncMock(return_value=True)

        from types import SimpleNamespace
        message = SimpleNamespace(
            message_id=1,
            chat=SimpleNamespace(id=999),
            from_=SimpleNamespace(id=12345),
            text="hello",
        )

        await handler.handle(message)

        # No rollback on happy path
        mock_session.rollback.assert_not_awaited()
        # Fallback NOT called (FOR UPDATE succeeded)
        mock_user_repo.get_by_telegram_id.assert_not_awaited()
