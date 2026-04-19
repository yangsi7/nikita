"""Per-user daily LLM spend ledger for /converse (Spec 214 FR-11d, GH #353).

Backing table: ``llm_spend_ledger`` (see
``supabase/migrations/20260419120500_llm_spend_ledger.sql``).

Enforces ``CONVERSE_DAILY_LLM_CAP_USD`` (default $2.00). The endpoint
calls ``get_today(user_id)`` pre-call to decide whether to 429; on
success it calls ``add_spend(user_id, delta_usd)`` to accumulate.

Accumulation pattern (decision D2): atomic per-user upsert

    INSERT ... ON CONFLICT (user_id, day)
    DO UPDATE SET spend_usd = llm_spend_ledger.spend_usd + EXCLUDED.spend_usd

Two concurrent ``add_spend(user_id, 0.5)`` calls finalize at ``1.0``
under Postgres row-level lock — verified by the concurrency test.
"""

from __future__ import annotations

from datetime import date, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class LLMSpendLedger:
    """Async wrapper around ``llm_spend_ledger`` using raw SQL.

    Raw SQL (not ORM) keeps this module's import graph free of
    SQLAlchemy ORM model churn — the table is a pure running-total
    ledger with no relationships to user/profile.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_today(self, user_id: UUID) -> Decimal:
        """Return the user's spend total for today (UTC). 0 if no row."""
        today = _today_utc()
        row = await self._session.execute(
            text(
                """
                SELECT spend_usd FROM llm_spend_ledger
                 WHERE user_id = :uid AND day = :day
                """
            ),
            {"uid": user_id, "day": today},
        )
        record = row.first()
        if record is None:
            return Decimal("0")
        return Decimal(record[0])

    async def add_spend(self, user_id: UUID, delta_usd: Decimal | float) -> None:
        """Atomically accumulate today's spend using D2's UPSERT pattern.

        Idempotency: the endpoint MUST NOT call ``add_spend`` on an
        idempotency-cache HIT (per M5 — the LLM call did not happen).
        """
        today = _today_utc()
        await self._session.execute(
            text(
                """
                INSERT INTO llm_spend_ledger (user_id, day, spend_usd, last_updated)
                VALUES (:uid, :day, :delta, now())
                ON CONFLICT (user_id, day) DO UPDATE
                  SET spend_usd = llm_spend_ledger.spend_usd + EXCLUDED.spend_usd,
                      last_updated = now()
                """
            ),
            {
                "uid": user_id,
                "day": today,
                "delta": str(Decimal(str(delta_usd))),
            },
        )


def _today_utc() -> date:
    """Return today's UTC date (pg_cron rollover runs at 00:05 UTC)."""
    from datetime import datetime

    return datetime.now(timezone.utc).date()


__all__ = [
    "LLMSpendLedger",
]
