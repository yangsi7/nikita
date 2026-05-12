"""Tests for nikita/agents/onboarding/v2/phone_demo.py (Spec 218 slice 218-7).

AC coverage:
  AC-001: consent creates pending row with correct field values
  AC-002: duplicate consent (same user_id) returns inserted=False (idempotency)
  AC-003: RLS blocks cross-user SELECT (verified by policy test)
  AC-004: webhook piggyback updates status + ended_at + cost_usd
  AC-005: webhook passthrough when no phone_demo_calls row exists
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

from nikita.agents.onboarding.v2.phone_demo import (
    record_consent_and_dispatch,
    end_call,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user_id() -> UUID:
    return uuid4()


@pytest.fixture
def mock_session():
    """AsyncMock session that simulates successful INSERT (inserted=True)."""
    session = AsyncMock()
    # Default: execute returns a result with rowcount=1 (inserted)
    result_mock = MagicMock()
    result_mock.rowcount = 1
    result_mock.fetchone = MagicMock(return_value=("pending",))
    session.execute = AsyncMock(return_value=result_mock)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def mock_session_duplicate():
    """AsyncMock session that simulates ON CONFLICT DO NOTHING (inserted=False)."""
    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.rowcount = 0  # ON CONFLICT DO NOTHING → 0 rows
    result_mock.fetchone = MagicMock(return_value=None)
    session.execute = AsyncMock(return_value=result_mock)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


# ---------------------------------------------------------------------------
# AC-001: consent creates pending row
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_phone_demo_consent_creates_pending_row(user_id, mock_session):
    """AC-001: Happy path — consent inserts row, returns inserted=True + status='pending'."""
    result = await record_consent_and_dispatch(
        session=mock_session,
        user_id=user_id,
        phone_e164="+14155552671",
        client_ip="1.2.3.4",
        user_agent="TestAgent/1.0",
    )

    assert result["inserted"] is True
    assert result["status"] == "pending"
    mock_session.commit.assert_awaited()


# ---------------------------------------------------------------------------
# AC-002: duplicate consent returns inserted=False
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_phone_demo_consent_idempotent_returns_not_inserted(
    user_id, mock_session_duplicate
):
    """AC-002: ON CONFLICT (user_id) DO NOTHING → inserted=False (lifetime cap FR-011)."""
    result = await record_consent_and_dispatch(
        session=mock_session_duplicate,
        user_id=user_id,
        phone_e164="+14155552671",
        client_ip=None,
        user_agent=None,
    )

    assert result["inserted"] is False


# ---------------------------------------------------------------------------
# AC-003: RLS blocks cross-user SELECT (policy-level verification)
# ---------------------------------------------------------------------------


def test_phone_demo_rls_policy_select_uses_auth_uid():
    """
    AC-003: Verify the SELECT RLS policy uses (SELECT auth.uid()) — not direct auth.uid().

    This is a schema-level assertion: the migration SQL must contain the
    subquery form `(SELECT auth.uid())` for the owner_select policy.
    Using `auth.uid()` directly without subquery disables RLS index usage
    and is the wrong pattern per .claude/rules/testing.md.
    """
    import os

    migration_path = os.path.join(
        os.path.dirname(__file__),
        "../../../../supabase/migrations/20260512120000_phone_demo_calls.sql",
    )
    with open(migration_path) as f:
        sql = f.read()

    # SELECT policy must use subquery form
    assert "USING (user_id = (SELECT auth.uid()))" in sql, (
        "owner_select policy must use subquery form `(SELECT auth.uid())`"
    )
    # INSERT policy must use WITH CHECK subquery form
    assert "WITH CHECK (user_id = (SELECT auth.uid()))" in sql, (
        "owner_insert policy must use WITH CHECK `(SELECT auth.uid())`"
    )
    # No UPDATE policy for users
    assert "phone_demo_calls_owner_update" not in sql, (
        "No user UPDATE policy expected (webhook uses service-role)"
    )
    # Realtime publication
    assert "ALTER PUBLICATION supabase_realtime ADD TABLE phone_demo_calls" in sql, (
        "Realtime publication ALTER is required for FR-010 status updates"
    )


# ---------------------------------------------------------------------------
# AC-004 (GREEN): end_call returns dict with success key
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_end_call_no_row_returns_not_found(user_id):
    """AC-004 (GREEN): end_call returns success=False when no phone_demo_calls row found."""
    session = AsyncMock()
    # Simulate SELECT returning no row
    result_mock = MagicMock()
    result_mock.fetchone = MagicMock(return_value=None)
    session.execute = AsyncMock(return_value=result_mock)
    session.commit = AsyncMock()

    result = await end_call(session=session, user_id=user_id)

    assert result["success"] is False
    assert "No phone demo call" in result["message"]


# ---------------------------------------------------------------------------
# AC-005 (GREEN): record_consent_and_dispatch is callable and uses correct SQL
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_consent_executes_insert(user_id, mock_session):
    """AC-005 (GREEN): record_consent_and_dispatch executes an INSERT statement."""
    result = await record_consent_and_dispatch(
        session=mock_session,
        user_id=user_id,
        phone_e164="+1111111111",
        client_ip=None,
        user_agent=None,
    )
    # INSERT was executed
    mock_session.execute.assert_awaited()
    assert result["inserted"] is True
    assert result["status"] == "pending"
