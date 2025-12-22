"""ScoreHistory repository for score timeline operations.

T5: ScoreHistoryRepository
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.game import ScoreHistory
from nikita.db.repositories.base import BaseRepository


class ScoreHistoryRepository(BaseRepository[ScoreHistory]):
    """Repository for ScoreHistory entity.

    Handles score event logging and timeline retrieval.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize ScoreHistoryRepository."""
        super().__init__(session, ScoreHistory)

    async def log_event(
        self,
        user_id: UUID,
        score: Decimal,
        chapter: int,
        event_type: str | None = None,
        event_details: dict[str, Any] | None = None,
    ) -> ScoreHistory:
        """Log a score event to history.

        Args:
            user_id: The user's UUID.
            score: Current score at time of event.
            chapter: Current chapter at time of event.
            event_type: Type of event (conversation, decay, boss_pass, etc.).
            event_details: Additional details about the event.

        Returns:
            Created ScoreHistory entity.
        """
        history = ScoreHistory(
            id=uuid4(),
            user_id=user_id,
            score=score,
            chapter=chapter,
            event_type=event_type,
            event_details=event_details,
            recorded_at=datetime.now(UTC),
        )
        return await self.create(history)

    async def get_history(
        self,
        user_id: UUID,
        limit: int = 50,
    ) -> list[ScoreHistory]:
        """Get score timeline for a user.

        Args:
            user_id: The user's UUID.
            limit: Maximum number of records to return.

        Returns:
            List of score history records, newest first.
        """
        stmt = (
            select(ScoreHistory)
            .where(ScoreHistory.user_id == user_id)
            .order_by(ScoreHistory.recorded_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_daily_stats(
        self,
        user_id: UUID,
        target_date: date,
    ) -> dict[str, Any]:
        """Get aggregated stats for a specific date.

        Args:
            user_id: The user's UUID.
            target_date: Date to get stats for.

        Returns:
            Dict with daily stats (events_count, score_change, etc.).
        """
        # Get all events for the date
        stmt = (
            select(ScoreHistory)
            .where(ScoreHistory.user_id == user_id)
            .where(func.date(ScoreHistory.recorded_at) == target_date)
            .order_by(ScoreHistory.recorded_at.asc())
        )
        result = await self.session.execute(stmt)
        events = list(result.scalars().all())

        if not events:
            return {
                "date": target_date,
                "events_count": 0,
                "score_start": None,
                "score_end": None,
                "score_change": None,
                "events_by_type": {},
            }

        # Calculate stats
        score_start = events[0].score
        score_end = events[-1].score

        # Count events by type
        events_by_type: dict[str, int] = {}
        for event in events:
            event_type = event.event_type or "unknown"
            events_by_type[event_type] = events_by_type.get(event_type, 0) + 1

        return {
            "date": target_date,
            "events_count": len(events),
            "score_start": score_start,
            "score_end": score_end,
            "score_change": score_end - score_start,
            "events_by_type": events_by_type,
        }

    async def get_events_by_type(
        self,
        user_id: UUID,
        event_type: str,
        limit: int = 50,
    ) -> list[ScoreHistory]:
        """Get score events of a specific type.

        Args:
            user_id: The user's UUID.
            event_type: Event type to filter by.
            limit: Maximum number of records.

        Returns:
            List of matching score history records.
        """
        stmt = (
            select(ScoreHistory)
            .where(ScoreHistory.user_id == user_id)
            .where(ScoreHistory.event_type == event_type)
            .order_by(ScoreHistory.recorded_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_history_since(
        self,
        user_id: UUID,
        since: datetime,
        limit: int = 1000,
    ) -> list[ScoreHistory]:
        """Get score history since a specific datetime.

        Args:
            user_id: The user's UUID.
            since: Get records after this datetime.
            limit: Maximum number of records.

        Returns:
            List of score history records, oldest first.
        """
        stmt = (
            select(ScoreHistory)
            .where(ScoreHistory.user_id == user_id)
            .where(ScoreHistory.recorded_at >= since)
            .order_by(ScoreHistory.recorded_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
