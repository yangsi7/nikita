"""Tests for nikita.onboarding.spend_ledger.LLMSpendLedger (Spec 214 FR-11d).

The ``add_spend`` concurrency invariant (AC-T2.6.3) is proven by the
DDL's ``ON CONFLICT DO UPDATE`` lock. Without a live DB we assert:

- Migration text includes the D2 UPSERT pattern + RLS + rollover cron.
- Repo emits the correct SQL.
- ``get_today`` returns ``Decimal("0")`` for new users and parses the
  numeric type correctly.

Live per-user lock-serialization verification is deferred to a post-
merge Supabase MCP test.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from nikita.onboarding.spend_ledger import LLMSpendLedger


_MIGRATION_PATH = (
    Path(__file__).parents[2]
    / "supabase"
    / "migrations"
    / "20260419120500_llm_spend_ledger.sql"
)


def _mock_session_with_row(row_data):
    session = AsyncMock()
    result = MagicMock()
    result.first = MagicMock(return_value=row_data)
    session.execute = AsyncMock(return_value=result)
    return session


class TestMigrationShape:
    def test_migration_applies_with_rls_and_cron(self):
        """AC-T2.6.1: llm_spend_ledger migration has RLS + rollover cron
        + D2 UPSERT-friendly schema.
        """
        assert _MIGRATION_PATH.exists()
        sql = _MIGRATION_PATH.read_text()
        assert "CREATE TABLE IF NOT EXISTS llm_spend_ledger" in sql
        assert "PRIMARY KEY (user_id, day)" in sql
        assert "spend_usd NUMERIC(10, 4)" in sql
        assert "ENABLE ROW LEVEL SECURITY" in sql
        assert "CREATE POLICY" in sql
        assert 'is_admin() OR auth.role() = \'service_role\'' in sql
        assert "llm_spend_ledger_rollover" in sql
        assert "interval '30 days'" in sql


class TestGetToday:
    @pytest.mark.asyncio
    async def test_get_today_returns_current_sum(self):
        """AC-T2.6.2: returns 0 for new user; numeric sum thereafter."""
        # New user (no row)
        session = _mock_session_with_row(None)
        ledger = LLMSpendLedger(session)
        total = await ledger.get_today(uuid4())
        assert total == Decimal("0")

        # Existing row
        session_existing = _mock_session_with_row((Decimal("1.2500"),))
        ledger_existing = LLMSpendLedger(session_existing)
        total_existing = await ledger_existing.get_today(uuid4())
        assert total_existing == Decimal("1.2500")


class TestAddSpend:
    @pytest.mark.asyncio
    async def test_add_spend_emits_atomic_upsert(self):
        """AC-T2.6.3 (repo side): emit D2 UPSERT pattern.

        Concurrency invariant is enforced by the ON CONFLICT DO UPDATE
        clause + Postgres row-level lock. Proving it live requires a
        real DB; proving the SQL shape here closes the implementation
        contract.
        """
        session = AsyncMock()
        session.execute = AsyncMock()
        ledger = LLMSpendLedger(session)

        await ledger.add_spend(uuid4(), Decimal("0.005"))

        session.execute.assert_awaited_once()
        sql = str(session.execute.call_args.args[0])
        assert "INSERT INTO llm_spend_ledger" in sql
        assert "ON CONFLICT (user_id, day) DO UPDATE" in sql
        assert "spend_usd + EXCLUDED.spend_usd" in sql

    @pytest.mark.asyncio
    async def test_add_spend_accepts_float(self):
        session = AsyncMock()
        session.execute = AsyncMock()
        ledger = LLMSpendLedger(session)
        # Accepting float is useful for the endpoint — delta_usd is
        # computed from model.usage() which returns float.
        await ledger.add_spend(uuid4(), 0.01)
        session.execute.assert_awaited_once()
