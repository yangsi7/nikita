"""DailySummary repository for daily summary operations.

T6: DailySummaryRepository
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.game import DailySummary
from nikita.db.repositories.base import BaseRepository


class DailySummaryRepository(BaseRepository[DailySummary]):
    """Repository for DailySummary entity.

    Handles daily summary creation and retrieval.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize DailySummaryRepository."""
        super().__init__(session, DailySummary)

    async def create_summary(
        self,
        user_id: UUID,
        summary_date: date,
        score_start: Decimal | None = None,
        score_end: Decimal | None = None,
        decay_applied: Decimal | None = None,
        conversations_count: int = 0,
        nikita_summary_text: str | None = None,
        key_events: list[dict[str, Any]] | None = None,
    ) -> DailySummary:
        """Create a daily summary.

        Args:
            user_id: The user's UUID.
            summary_date: Date for this summary.
            score_start: Score at start of day.
            score_end: Score at end of day.
            decay_applied: Decay amount applied.
            conversations_count: Number of conversations.
            nikita_summary_text: Nikita's in-character summary.
            key_events: List of key events.

        Returns:
            Created DailySummary entity.
        """
        summary = DailySummary(
            id=uuid4(),
            user_id=user_id,
            date=summary_date,
            score_start=score_start,
            score_end=score_end,
            decay_applied=decay_applied,
            conversations_count=conversations_count,
            nikita_summary_text=nikita_summary_text,
            key_events=key_events,
            created_at=datetime.now(UTC),
        )
        return await self.create(summary)

    async def get_by_date(
        self,
        user_id: UUID,
        summary_date: date,
    ) -> DailySummary | None:
        """Get summary for a specific date.

        Args:
            user_id: The user's UUID.
            summary_date: Date to get summary for.

        Returns:
            DailySummary or None if not found.
        """
        stmt = (
            select(DailySummary)
            .where(DailySummary.user_id == user_id)
            .where(DailySummary.date == summary_date)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_range(
        self,
        user_id: UUID,
        start_date: date,
        end_date: date,
    ) -> list[DailySummary]:
        """Get summaries within a date range.

        Args:
            user_id: The user's UUID.
            start_date: Start of date range (inclusive).
            end_date: End of date range (inclusive).

        Returns:
            List of DailySummary entities in date order.
        """
        stmt = (
            select(DailySummary)
            .where(DailySummary.user_id == user_id)
            .where(DailySummary.date >= start_date)
            .where(DailySummary.date <= end_date)
            .order_by(DailySummary.date.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_summary(
        self,
        summary_id: UUID,
        score_end: Decimal | None = None,
        nikita_summary_text: str | None = None,
        key_events: list[dict[str, Any]] | None = None,
    ) -> DailySummary:
        """Update an existing daily summary.

        Args:
            summary_id: The summary's UUID.
            score_end: Updated end score.
            nikita_summary_text: Updated summary text.
            key_events: Updated key events.

        Returns:
            Updated DailySummary entity.

        Raises:
            ValueError: If summary not found.
        """
        summary = await self.get(summary_id)
        if summary is None:
            raise ValueError(f"DailySummary {summary_id} not found")

        if score_end is not None:
            summary.score_end = score_end
        if nikita_summary_text is not None:
            summary.nikita_summary_text = nikita_summary_text
        if key_events is not None:
            summary.key_events = key_events

        await self.session.flush()
        await self.session.refresh(summary)

        return summary

    async def get_recent(
        self,
        user_id: UUID,
        limit: int = 7,
    ) -> list[DailySummary]:
        """Get recent daily summaries.

        Args:
            user_id: The user's UUID.
            limit: Maximum number to return.

        Returns:
            List of recent summaries, newest first.
        """
        stmt = (
            select(DailySummary)
            .where(DailySummary.user_id == user_id)
            .order_by(DailySummary.date.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
