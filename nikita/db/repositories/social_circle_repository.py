"""Social Circle Repository (Spec 035).

Manages CRUD operations for user social circles.
"""

import logging
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.social_circle import UserSocialCircle

if TYPE_CHECKING:
    from nikita.life_simulation.social_generator import FriendCharacter

logger = logging.getLogger(__name__)


class SocialCircleRepository:
    """Repository for managing user social circles.

    Social circles are generated once during onboarding and remain
    immutable throughout the game.
    """

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def create_circle_for_user(
        self,
        user_id: UUID,
        friends: list["FriendCharacter"],
    ) -> list[UserSocialCircle]:
        """Store a complete social circle for a user.

        Args:
            user_id: User ID to create circle for
            friends: List of FriendCharacter objects from generator

        Returns:
            List of created UserSocialCircle records
        """
        if not friends:
            logger.warning(f"No friends to create for user {user_id}")
            return []

        # Check if user already has a social circle
        existing = await self.get_circle(user_id)
        if existing:
            logger.warning(
                f"User {user_id} already has social circle with {len(existing)} friends"
            )
            return existing

        records = []
        for friend in friends:
            record = UserSocialCircle(
                user_id=user_id,
                friend_name=friend.name,
                friend_role=friend.role,
                age=friend.age,
                occupation=friend.occupation,
                personality=friend.personality,
                relationship_to_nikita=friend.relationship_to_nikita,
                storyline_potential=friend.storyline_potential,
                trigger_conditions=friend.trigger_conditions,
                adapted_traits=friend.adapted_traits,
            )
            self.session.add(record)
            records.append(record)

        await self.session.flush()
        logger.info(f"Created social circle with {len(records)} friends for user {user_id}")
        return records

    async def get_circle(self, user_id: UUID) -> list[UserSocialCircle]:
        """Get all friends in a user's social circle.

        Args:
            user_id: User ID to get circle for

        Returns:
            List of UserSocialCircle records (may be empty)
        """
        stmt = (
            select(UserSocialCircle)
            .where(UserSocialCircle.user_id == user_id)
            .order_by(UserSocialCircle.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_friends(self, user_id: UUID) -> list[UserSocialCircle]:
        """Get only active friends in a user's social circle.

        Args:
            user_id: User ID to get active friends for

        Returns:
            List of active UserSocialCircle records
        """
        stmt = (
            select(UserSocialCircle)
            .where(
                UserSocialCircle.user_id == user_id,
                UserSocialCircle.is_active == True,  # noqa: E712
            )
            .order_by(UserSocialCircle.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_friend_by_name(
        self, user_id: UUID, friend_name: str
    ) -> UserSocialCircle | None:
        """Get a specific friend by name.

        Args:
            user_id: User ID
            friend_name: Name of the friend

        Returns:
            UserSocialCircle or None if not found
        """
        stmt = select(UserSocialCircle).where(
            UserSocialCircle.user_id == user_id,
            UserSocialCircle.friend_name == friend_name,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_friend_by_role(
        self, user_id: UUID, role: str
    ) -> UserSocialCircle | None:
        """Get a friend by their role.

        Args:
            user_id: User ID
            role: Role (best_friend, ex, work_colleague, etc.)

        Returns:
            First UserSocialCircle with that role or None
        """
        stmt = (
            select(UserSocialCircle)
            .where(
                UserSocialCircle.user_id == user_id,
                UserSocialCircle.friend_role == role,
                UserSocialCircle.is_active == True,  # noqa: E712
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def deactivate_friend(
        self, user_id: UUID, friend_name: str
    ) -> bool:
        """Deactivate a friend (soft delete).

        Args:
            user_id: User ID
            friend_name: Name of friend to deactivate

        Returns:
            True if deactivated, False if not found
        """
        friend = await self.get_friend_by_name(user_id, friend_name)
        if not friend:
            return False

        friend.is_active = False
        await self.session.flush()
        logger.info(f"Deactivated friend {friend_name} for user {user_id}")
        return True
