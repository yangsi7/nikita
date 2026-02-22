"""PsycheState repository for psyche agent data access (Spec 056 T4).

Provides get_current (single JSONB read <50ms) and upsert
(INSERT ON CONFLICT UPDATE) for the psyche_states table.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.psyche_state import PsycheStateRecord
from nikita.db.repositories.base import BaseRepository


class PsycheStateRepository(BaseRepository[PsycheStateRecord]):
    """Repository for PsycheStateRecord entity.

    Manages psyche state persistence with upsert semantics
    (one row per user, updated on each generation).
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PsycheStateRecord)

    async def get_current(self, user_id: UUID) -> PsycheStateRecord | None:
        """Get the current psyche state for a user.

        Single JSONB read, expected <50ms latency.

        Args:
            user_id: User UUID.

        Returns:
            PsycheStateRecord or None if no state exists.
        """
        stmt = select(PsycheStateRecord).where(
            PsycheStateRecord.user_id == user_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert(
        self,
        user_id: UUID,
        state: dict,
        model: str,
        token_count: int,
    ) -> PsycheStateRecord:
        """Insert or update psyche state for a user.

        Uses PostgreSQL INSERT ON CONFLICT(user_id) DO UPDATE
        for atomic upsert semantics.

        Args:
            user_id: User UUID.
            state: PsycheState dict (JSONB).
            model: Model name used for generation.
            token_count: Token count for cost tracking.

        Returns:
            The upserted PsycheStateRecord.
        """
        now = datetime.now(timezone.utc)

        stmt = pg_insert(PsycheStateRecord).values(
            user_id=user_id,
            state=state,
            model=model,
            token_count=token_count,
            generated_at=now,
        )

        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id"],
            set_={
                "state": stmt.excluded.state,
                "model": stmt.excluded.model,
                "token_count": stmt.excluded.token_count,
                "generated_at": stmt.excluded.generated_at,
            },
        )

        await self.session.execute(stmt)
        await self.session.flush()

        # Re-fetch the record to return it
        return await self.get_current(user_id)

    async def get_tier3_count_today(self, user_id: UUID) -> int:
        """Count Tier 3 (deep analysis) calls for a user today.

        Used by circuit breaker to enforce max 5/user/day limit.

        Args:
            user_id: User UUID.

        Returns:
            Number of Tier 3 generations today.
        """
        from sqlalchemy import func as sa_func, cast, Date

        today = datetime.now(timezone.utc).date()

        stmt = (
            select(sa_func.count())
            .select_from(PsycheStateRecord)
            .where(
                PsycheStateRecord.user_id == user_id,
                cast(PsycheStateRecord.generated_at, Date) == today,
                PsycheStateRecord.model.like("%opus%"),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0
