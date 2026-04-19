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

Cost computation (I6 QA iter-1): ``compute_turn_cost`` accepts the
optional Pydantic AI ``RunUsage`` object and converts token counts to
USD via ``CLAUDE_SONNET_PRICING_USD``. Falls back to a flat per-turn
estimate if usage is missing.
"""

from __future__ import annotations

from datetime import date, timezone
from decimal import Decimal
from typing import Final
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


# I6 QA iter-1: per-1M-token pricing for Claude Sonnet (input / output).
# Source: anthropic.com/pricing. Stored as Decimal-safe strings so the
# pricing math preserves exact rates without binary-float drift.
CLAUDE_SONNET_PRICING_USD: Final[dict[str, str]] = {
    "input_per_million": "3.00",
    "output_per_million": "15.00",
}

# Per-call estimated LLM cost (USD). Used for daily-cap accounting when
# the agent does not return usage. Conservative overestimate so the cap
# never undershoots. Real Claude Sonnet turns run $0.003-$0.01.
ESTIMATED_TURN_COST_USD: Final[Decimal] = Decimal("0.01")


def compute_turn_cost(usage: object | None) -> Decimal:
    """Convert a Pydantic AI ``RunUsage`` (or None) into a USD ``Decimal``.

    Reads ``input_tokens`` + ``output_tokens`` off the usage record and
    applies ``CLAUDE_SONNET_PRICING_USD``. Missing usage → flat
    ``ESTIMATED_TURN_COST_USD`` fallback so the daily cap never
    undershoots when the model wrapper omits telemetry.
    """
    if usage is None:
        return ESTIMATED_TURN_COST_USD
    input_tokens = getattr(usage, "input_tokens", None) or 0
    output_tokens = getattr(usage, "output_tokens", None) or 0
    if input_tokens == 0 and output_tokens == 0:
        return ESTIMATED_TURN_COST_USD
    million = Decimal("1000000")
    input_cost = (
        Decimal(input_tokens)
        * Decimal(CLAUDE_SONNET_PRICING_USD["input_per_million"])
        / million
    )
    output_cost = (
        Decimal(output_tokens)
        * Decimal(CLAUDE_SONNET_PRICING_USD["output_per_million"])
        / million
    )
    return input_cost + output_cost


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
        # N5 QA iter-1: route through `str()` so a float/int driver
        # return value stays exact (no binary-float rounding artefact).
        return Decimal(str(record[0]))

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
    "CLAUDE_SONNET_PRICING_USD",
    "ESTIMATED_TURN_COST_USD",
    "LLMSpendLedger",
    "compute_turn_cost",
]
