"""EngagementState repository for engagement tracking operations.

Handles engagement state queries and transition history.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from nikita.db.models.engagement import EngagementHistory, EngagementState
from nikita.db.repositories.base import BaseRepository


class EngagementStateRepository(BaseRepository[EngagementState]):
    """Repository for EngagementState entity.

    Handles engagement state queries and history tracking.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize EngagementStateRepository."""
        super().__init__(session, EngagementState)

    async def get_by_user_id(self, user_id: UUID) -> EngagementState | None:
        """Get engagement state by user ID.

        Args:
            user_id: The user's UUID.

        Returns:
            EngagementState or None if not found.
        """
        stmt = select(EngagementState).where(EngagementState.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_recent_transitions(
        self, user_id: UUID, limit: int = 10
    ) -> list[EngagementHistory]:
        """Get recent engagement state transitions for user.

        Args:
            user_id: The user's UUID.
            limit: Maximum number of transitions to return (default: 10).

        Returns:
            List of EngagementHistory records ordered by created_at DESC.
        """
        stmt = (
            select(EngagementHistory)
            .where(EngagementHistory.user_id == user_id)
            .order_by(EngagementHistory.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
