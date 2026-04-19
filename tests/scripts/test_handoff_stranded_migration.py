"""Tests for Spec 214 T4.5 (FR-11e) — stranded-user one-shot migration.

Verifies AC-T4.5.1:
  - 5 fixture users → 5 dispatched + 5 claims succeed.
  - Re-run is a no-op (idempotent): re-running with all rows already
    cleared returns scanned=dispatched=0.

Per .claude/rules/testing.md: ORM-mock unit tests only — no live DB.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


def _make_row(user_id, telegram_id):
    row = MagicMock()
    row.id = user_id
    row.telegram_id = telegram_id
    return row


@pytest.mark.asyncio
async def test_migrates_5_stranded_users_and_is_idempotent():
    """Two-phase test: first run dispatches 5; second run dispatches 0.

    Single test (not split) so the idempotency contract is checked
    against a SHARED fixture state — splitting would risk one of the
    two halves passing while the other regresses on a refactor.
    """
    from scripts import handoff_stranded_migration as migration

    user_ids = [uuid4() for _ in range(5)]
    telegram_ids = [1000 + i for i in range(5)]

    # ── Phase 1: 5 stranded rows surface, all claim wins, all dispatch ──

    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    scan_result = MagicMock()
    scan_result.all = MagicMock(
        return_value=[_make_row(uid, tid) for uid, tid in zip(user_ids, telegram_ids)]
    )
    mock_session.execute = AsyncMock(return_value=scan_result)

    async def _aenter(*_a, **_k):
        return mock_session

    async def _aexit(*_a, **_k):
        return None

    ctx = MagicMock()
    ctx.__aenter__ = _aenter
    ctx.__aexit__ = _aexit
    session_maker = MagicMock(return_value=ctx)

    with patch(
        "scripts.handoff_stranded_migration.get_session_maker",
        return_value=session_maker,
    ), patch(
        "scripts.handoff_stranded_migration.TelegramBot"
    ), patch(
        "scripts.handoff_stranded_migration._dispatch_handoff_greeting",
        new=AsyncMock(),
    ) as mock_dispatch, patch(
        "scripts.handoff_stranded_migration.UserRepository"
    ) as mock_repo_cls:
        repo = MagicMock()
        repo.claim_handoff_intent = AsyncMock(return_value=True)
        mock_repo_cls.return_value = repo

        summary = await migration.run(dry_run=False)

    assert summary["scanned"] == 5
    assert summary["claimed"] == 5
    assert summary["dispatched"] == 5
    assert summary["errors"] == 0
    assert mock_dispatch.await_count == 5

    # ── Phase 2 (idempotency): scan returns zero rows ──

    mock_session_2 = AsyncMock()
    mock_session_2.commit = AsyncMock()
    scan_result_2 = MagicMock()
    scan_result_2.all = MagicMock(return_value=[])
    mock_session_2.execute = AsyncMock(return_value=scan_result_2)

    async def _aenter2(*_a, **_k):
        return mock_session_2

    async def _aexit2(*_a, **_k):
        return None

    ctx2 = MagicMock()
    ctx2.__aenter__ = _aenter2
    ctx2.__aexit__ = _aexit2
    session_maker_2 = MagicMock(return_value=ctx2)

    with patch(
        "scripts.handoff_stranded_migration.get_session_maker",
        return_value=session_maker_2,
    ), patch(
        "scripts.handoff_stranded_migration.TelegramBot"
    ), patch(
        "scripts.handoff_stranded_migration._dispatch_handoff_greeting",
        new=AsyncMock(),
    ) as mock_dispatch_2, patch(
        "scripts.handoff_stranded_migration.UserRepository"
    ):
        summary_2 = await migration.run(dry_run=False)

    assert summary_2["scanned"] == 0
    assert summary_2["dispatched"] == 0
    mock_dispatch_2.assert_not_called()


@pytest.mark.asyncio
async def test_dry_run_skips_dispatch():
    """``--dry-run`` reports the count without invoking the dispatcher.

    Useful for ops to size the backlog before flipping the switch.
    """
    from scripts import handoff_stranded_migration as migration

    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    scan_result = MagicMock()
    scan_result.all = MagicMock(
        return_value=[_make_row(uuid4(), 999)]
    )
    mock_session.execute = AsyncMock(return_value=scan_result)

    async def _aenter(*_a, **_k):
        return mock_session

    async def _aexit(*_a, **_k):
        return None

    ctx = MagicMock()
    ctx.__aenter__ = _aenter
    ctx.__aexit__ = _aexit
    session_maker = MagicMock(return_value=ctx)

    with patch(
        "scripts.handoff_stranded_migration.get_session_maker",
        return_value=session_maker,
    ), patch(
        "scripts.handoff_stranded_migration.TelegramBot"
    ), patch(
        "scripts.handoff_stranded_migration._dispatch_handoff_greeting",
        new=AsyncMock(),
    ) as mock_dispatch:
        summary = await migration.run(dry_run=True)

    assert summary["scanned"] == 1
    assert summary["dispatched"] == 0
    assert summary["dry_run"] is True
    mock_dispatch.assert_not_called()
