"""UserMetrics repository for metrics-related database operations.

T3: UserMetricsRepository
"""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.user import UserMetrics
from nikita.db.repositories.base import BaseRepository


class UserMetricsRepository(BaseRepository[UserMetrics]):
    """Repository for UserMetrics entity.

    Handles individual metric updates and composite score calculation.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize UserMetricsRepository."""
        super().__init__(session, UserMetrics)

    async def get_by_user_id(self, user_id: UUID) -> UserMetrics | None:
        """Get metrics by user ID.

        Args:
            user_id: The user's UUID.

        Returns:
            UserMetrics or None if not found.
        """
        stmt = select(UserMetrics).where(UserMetrics.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_metrics(
        self,
        user_id: UUID,
        intimacy_delta: Decimal = Decimal("0"),
        passion_delta: Decimal = Decimal("0"),
        trust_delta: Decimal = Decimal("0"),
        secureness_delta: Decimal = Decimal("0"),
    ) -> UserMetrics:
        """Update metrics atomically with deltas.

        Args:
            user_id: The user's UUID.
            intimacy_delta: Change to intimacy metric.
            passion_delta: Change to passion metric.
            trust_delta: Change to trust metric.
            secureness_delta: Change to secureness metric.

        Returns:
            Updated UserMetrics entity.

        Raises:
            ValueError: If metrics not found for user.
        """
        metrics = await self.get_by_user_id(user_id)
        if metrics is None:
            raise ValueError(f"Metrics not found for user {user_id}")

        # Apply deltas with clamping (0-100)
        metrics.intimacy = self._clamp(metrics.intimacy + intimacy_delta)
        metrics.passion = self._clamp(metrics.passion + passion_delta)
        metrics.trust = self._clamp(metrics.trust + trust_delta)
        metrics.secureness = self._clamp(metrics.secureness + secureness_delta)

        await self.session.flush()
        await self.session.refresh(metrics)

        return metrics

    async def calculate_composite(self, user_id: UUID) -> Decimal:
        """Calculate composite score from metrics.

        Args:
            user_id: The user's UUID.

        Returns:
            Calculated composite score.

        Raises:
            ValueError: If metrics not found for user.
        """
        metrics = await self.get_by_user_id(user_id)
        if metrics is None:
            raise ValueError(f"Metrics not found for user {user_id}")

        return metrics.calculate_composite_score()

    @staticmethod
    def _clamp(value: Decimal) -> Decimal:
        """Clamp value between 0 and 100."""
        return max(Decimal("0.00"), min(Decimal("100.00"), value))
