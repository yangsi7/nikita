"""Tests for UserService — Spec 216 EM-3b consolidation.

Covers the three branches of ``UserService.create_or_get``:
  1. Lookup hit (existing user) → no create call, returns existing row.
  2. Lookup miss → create_with_metrics called, returns new row.
  3. Race conflict (IntegrityError on create) → re-fetches, returns row.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from nikita.services.user_service import UserService


@pytest.mark.asyncio
async def test_create_or_get_returns_existing_user_without_creating() -> None:
    """If get() returns a row, create_with_metrics MUST NOT be called."""
    existing_user = Mock(name="existing_user")
    user_repo = Mock()
    user_repo.get = AsyncMock(return_value=existing_user)
    user_repo.create_with_metrics = AsyncMock()

    service = UserService(user_repo=user_repo)
    user_id = uuid4()

    result = await service.create_or_get(supabase_id=user_id)

    assert result is existing_user
    user_repo.get.assert_awaited_once_with(user_id)
    user_repo.create_with_metrics.assert_not_called()


@pytest.mark.asyncio
async def test_create_or_get_creates_new_user_when_missing() -> None:
    """If get() returns None, create_with_metrics is called with the supabase_id."""
    new_user = Mock(name="new_user")
    user_repo = Mock()
    user_repo.get = AsyncMock(return_value=None)
    user_repo.create_with_metrics = AsyncMock(return_value=new_user)

    service = UserService(user_repo=user_repo)
    user_id = uuid4()

    result = await service.create_or_get(
        supabase_id=user_id,
        email="player@example.com",
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


@pytest.mark.asyncio
async def test_create_or_get_handles_race_conflict_via_refetch() -> None:
    """If create_with_metrics raises IntegrityError (concurrent insert),
    UserService re-fetches and returns the winning row instead of bubbling up."""
    winning_user = Mock(name="winning_user")
    user_repo = Mock()
    # First get() returns None (so we try to create), second get() returns the
    # row inserted by the racing transaction.
    user_repo.get = AsyncMock(side_effect=[None, winning_user])
    user_repo.create_with_metrics = AsyncMock(
        side_effect=IntegrityError("duplicate key", None, Exception("23505"))
    )

    service = UserService(user_repo=user_repo)
    user_id = uuid4()

    result = await service.create_or_get(supabase_id=user_id)

    assert result is winning_user
    assert user_repo.get.await_count == 2
    user_repo.create_with_metrics.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_or_get_reraises_when_integrity_error_has_no_winner() -> None:
    """If the IntegrityError was NOT a race (refetch returns None), re-raise."""
    user_repo = Mock()
    user_repo.get = AsyncMock(side_effect=[None, None])
    user_repo.create_with_metrics = AsyncMock(
        side_effect=IntegrityError("constraint", None, Exception("23503"))
    )

    service = UserService(user_repo=user_repo)

    with pytest.raises(IntegrityError):
        await service.create_or_get(supabase_id=uuid4())
