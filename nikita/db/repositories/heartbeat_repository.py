"""NikitaDailyPlanRepository — Spec 215 PR 215-A foundation.

Repository for the ``nikita_daily_plan`` table. Two operations:
    - get_plan_for_date()  → return plan or None
    - upsert_plan()        → ON CONFLICT (user_id, plan_date) DO UPDATE

Caller manages the transaction — this repository NEVER calls session.commit().
Follows the BackstoryCacheRepository pattern (cache-style upsert) and the
broader UserRepository conventions (constructor takes session, methods async).

asyncpg JSONB strategy: the repository passes ``arc_json`` as a Python dict
directly to SQLAlchemy. Do NOT call json.dumps() on it. See
nikita.db.models.heartbeat module docstring for the PR #319 burn precedent.
"""

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.heartbeat import NikitaDailyPlan


class NikitaDailyPlanRepository:
    """Repository for the nikita_daily_plan table (Spec 215 PR 215-A).

    Idempotency contract: ``upsert_plan`` uses ON CONFLICT (user_id, plan_date)
    DO UPDATE so calling it twice in the same day for the same user replaces
    the row in place — exactly one row per (user_id, plan_date). The unique
    index ``idx_nikita_daily_plan_user_date`` (in the migration) backs this
    constraint.

    RLS: rows are user-scoped read; writes require the service-role key (the
    pg_cron handler at /tasks/generate-daily-arcs is the only writer). See the
    migration for the exact policies.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize NikitaDailyPlanRepository.

        Args:
            session: Async SQLAlchemy session. Caller manages the transaction.
        """
        self._session = session

    @property
    def session(self) -> AsyncSession:
        """Access the database session."""
        return self._session

    async def get_plan_for_date(
        self,
        user_id: UUID,
        plan_date: date,
    ) -> NikitaDailyPlan | None:
        """Return the plan for a single (user, date), or None if none exists.

        Used by the /tasks/heartbeat handler to load today's plan; also used
        by the midnight-UTC fallback (T4.2 AC-T4.2-009) to read D-1 when D
        hasn't been generated yet.

        Args:
            user_id: Owning user.
            plan_date: Calendar date (UTC) the plan applies to.

        Returns:
            NikitaDailyPlan instance, or None on miss.
        """
        stmt = select(NikitaDailyPlan).where(
            NikitaDailyPlan.user_id == user_id,
            NikitaDailyPlan.plan_date == plan_date,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_plan(
        self,
        *,
        user_id: UUID,
        plan_date: date,
        arc_json: dict[str, Any],
        narrative_text: str,
        model_used: str | None = None,
    ) -> NikitaDailyPlan:
        """Upsert (insert or update-in-place) a plan for (user_id, plan_date).

        Per FR-002 AC-FR2-002, calling twice in the same day for the same user
        produces exactly one row, with ``generated_at`` refreshed on the
        second call. The unique index on (user_id, plan_date) is the
        idempotency anchor; ON CONFLICT triggers the UPDATE branch.

        ``arc_json`` is passed as a Python dict — the SQLAlchemy JSONB type
        adapter handles serialization. Do NOT call json.dumps() on it (see
        module docstring + nikita.db.models.heartbeat module docstring).

        Returns the persisted row (via RETURNING) so callers can correlate
        ``id`` and the server-stamped ``generated_at`` for cost-ledger
        attribution and observability without a follow-up SELECT.

        Caller manages the transaction; this method does NOT commit.

        Keyword-only arguments enforce positional-arg safety: callers cannot
        accidentally swap ``user_id`` and ``plan_date`` (different types
        already, but the convention helps the next reviewer).

        Args:
            user_id: Owning user.
            plan_date: Calendar date (UTC) the plan applies to.
            arc_json: Structured plan-step list + conditional actions.
            narrative_text: Human-readable narrative for prompt injection.
            model_used: LLM model identifier (e.g. "claude-haiku-4-5-20251001").
                Optional; nullable in DB so synthetic tests don't have to fake
                an LLM call.

        Returns:
            The persisted NikitaDailyPlan row, freshly loaded from RETURNING.
        """
        # ``id`` and ``generated_at`` intentionally omitted from the values
        # clause — both have server defaults (gen_random_uuid + now()) and
        # re-supplying them from Python would risk clock skew and key
        # collisions. ON CONFLICT DO UPDATE refreshes ``generated_at`` via
        # ``func.now()`` server-side rather than passing a Python-computed
        # timestamp.
        stmt = (
            insert(NikitaDailyPlan)
            .values(
                user_id=user_id,
                plan_date=plan_date,
                arc_json=arc_json,
                narrative_text=narrative_text,
                model_used=model_used,
            )
            .on_conflict_do_update(
                index_elements=["user_id", "plan_date"],
                set_={
                    "arc_json": arc_json,
                    "narrative_text": narrative_text,
                    "model_used": model_used,
                    "generated_at": func.now(),
                },
            )
            .returning(NikitaDailyPlan)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()
