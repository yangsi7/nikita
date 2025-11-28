"""VicePreference repository for vice tracking operations.

T6: VicePreferenceRepository
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.user import UserVicePreference
from nikita.db.repositories.base import BaseRepository


class VicePreferenceRepository(BaseRepository[UserVicePreference]):
    """Repository for UserVicePreference entity.

    Handles vice preference tracking and intensity updates.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize VicePreferenceRepository."""
        super().__init__(session, UserVicePreference)

    async def get_active(self, user_id: UUID) -> list[UserVicePreference]:
        """Get all active vice preferences for a user.

        Args:
            user_id: The user's UUID.

        Returns:
            List of active vice preferences.
        """
        stmt = (
            select(UserVicePreference)
            .where(UserVicePreference.user_id == user_id)
            .order_by(UserVicePreference.engagement_score.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_category(
        self,
        user_id: UUID,
        category: str,
    ) -> UserVicePreference | None:
        """Get vice preference by category.

        Args:
            user_id: The user's UUID.
            category: Vice category name.

        Returns:
            VicePreference or None if not found.
        """
        stmt = (
            select(UserVicePreference)
            .where(UserVicePreference.user_id == user_id)
            .where(UserVicePreference.category == category)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_intensity(
        self,
        preference_id: UUID,
        delta: int,
    ) -> UserVicePreference:
        """Update intensity level of a vice preference.

        Args:
            preference_id: The preference's UUID.
            delta: Change to intensity level (positive or negative).

        Returns:
            Updated VicePreference entity.

        Raises:
            ValueError: If preference not found.
        """
        preference = await self.get(preference_id)
        if preference is None:
            raise ValueError(f"VicePreference {preference_id} not found")

        # Update with clamping (1-5)
        new_intensity = preference.intensity_level + delta
        preference.intensity_level = max(1, min(5, new_intensity))

        await self.session.flush()
        await self.session.refresh(preference)

        return preference

    async def discover(
        self,
        user_id: UUID,
        category: str,
        initial_intensity: int = 1,
    ) -> UserVicePreference:
        """Discover/create a new vice preference.

        Args:
            user_id: The user's UUID.
            category: Vice category name.
            initial_intensity: Starting intensity level.

        Returns:
            Created VicePreference entity.
        """
        # Check if already exists
        existing = await self.get_by_category(user_id, category)
        if existing:
            return existing

        preference = UserVicePreference(
            id=uuid4(),
            user_id=user_id,
            category=category,
            intensity_level=initial_intensity,
            engagement_score=Decimal("0.00"),
            discovered_at=datetime.now(UTC),
        )
        return await self.create(preference)

    async def update_engagement(
        self,
        preference_id: UUID,
        delta: Decimal,
    ) -> UserVicePreference:
        """Update engagement score for a vice preference.

        Args:
            preference_id: The preference's UUID.
            delta: Change to engagement score.

        Returns:
            Updated VicePreference entity.

        Raises:
            ValueError: If preference not found.
        """
        preference = await self.get(preference_id)
        if preference is None:
            raise ValueError(f"VicePreference {preference_id} not found")

        new_score = preference.engagement_score + delta
        preference.engagement_score = max(Decimal("0.00"), new_score)

        await self.session.flush()
        await self.session.refresh(preference)

        return preference
