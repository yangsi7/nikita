"""Tests for UserService — Spec 216 EM-3b consolidation.

Covers the four branches of ``UserService.create_or_get``:
  1. Lookup hit (existing user) → no create call, returns existing row.
  2. Lookup miss → create_with_metrics called, returns new row.
  3. Race conflict (IntegrityError on create) → session.rollback() then
     re-fetches, returns the winning row.
  4. Non-race IntegrityError (refetch returns None) → re-raises.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from nikita.services.user_service import UserService


def _make_session_mock() -> Mock:
    """Return an AsyncSession mock with rollback as AsyncMock."""
    session = Mock()
    session.rollback = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_create_or_get_returns_existing_user_without_creating() -> None:
    """If get() returns a row, create_with_metrics MUST NOT be called."""
    existing_user = Mock(name="existing_user")
    user_repo = Mock()
    user_repo.get = AsyncMock(return_value=existing_user)
    user_repo.create_with_metrics = AsyncMock()
    session = _make_session_mock()

    service = UserService(user_repo=user_repo, session=session)
    user_id = uuid4()

    result = await service.create_or_get(supabase_id=user_id)

    assert result is existing_user
    user_repo.get.assert_awaited_once_with(user_id)
    user_repo.create_with_metrics.assert_not_called()
    session.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_create_or_get_creates_new_user_when_missing() -> None:
    """If get() returns None, create_with_metrics is called with the supabase_id."""
    new_user = Mock(name="new_user")
    user_repo = Mock()
    user_repo.get = AsyncMock(return_value=None)
    user_repo.create_with_metrics = AsyncMock(return_value=new_user)
    session = _make_session_mock()

    service = UserService(user_repo=user_repo, session=session)
    user_id = uuid4()

    result = await service.create_or_get(
        supabase_id=user_id,
        telegram_id=12345,
        phone="+15555550100",
    )

    assert result is new_user
    user_repo.get.assert_awaited_once_with(user_id)
    user_repo.create_with_metrics.assert_awaited_once_with(
        user_id=user_id,
        telegram_id=12345,
        phone="+15555550100",
    )
    session.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_create_or_get_handles_race_conflict_via_rollback_and_refetch() -> None:
    """If create_with_metrics raises IntegrityError (concurrent insert),
    UserService rolls back the failed transaction THEN re-fetches and returns
    the winning row.

    Without the rollback, the next operation on the failed session raises
    PendingRollbackError. The test asserts both that rollback is awaited AND
    that it precedes the second get() call.
    """
    winning_user = Mock(name="winning_user")
    user_repo = Mock()
    # First get() returns None (so we try to create), second get() returns the
    # row inserted by the racing transaction.
    user_repo.get = AsyncMock(side_effect=[None, winning_user])
    user_repo.create_with_metrics = AsyncMock(
        side_effect=IntegrityError("duplicate key", None, Exception("23505"))
    )
    session = _make_session_mock()

    service = UserService(user_repo=user_repo, session=session)
    user_id = uuid4()

    result = await service.create_or_get(supabase_id=user_id)

    assert result is winning_user
    assert user_repo.get.await_count == 2
    user_repo.create_with_metrics.assert_awaited_once()
    session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_or_get_rolls_back_then_reraises_when_no_winner() -> None:
    """If the IntegrityError was NOT a race (refetch returns None), the
    session is still rolled back (so the caller's session is in a usable
    state) and the original IntegrityError re-raises."""
    user_repo = Mock()
    user_repo.get = AsyncMock(side_effect=[None, None])
    user_repo.create_with_metrics = AsyncMock(
        side_effect=IntegrityError("constraint", None, Exception("23503"))
    )
    session = _make_session_mock()

    service = UserService(user_repo=user_repo, session=session)

    with pytest.raises(IntegrityError):
        await service.create_or_get(supabase_id=uuid4())

    session.rollback.assert_awaited_once()
