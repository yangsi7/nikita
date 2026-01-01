"""User repository for user-related database operations.

Handles User entity with eager-loaded metrics, score updates,
decay application, and chapter advancement.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from nikita.db.models.engagement import EngagementState
from nikita.db.models.game import ScoreHistory
from nikita.db.models.user import User, UserMetrics
from nikita.db.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User entity with game-specific operations.

    Provides standard CRUD plus game mechanics:
    - Score updates with history logging
    - Daily decay application
    - Chapter advancement
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize UserRepository.

        Args:
            session: Async SQLAlchemy session.
        """
        super().__init__(session, User)

    async def get(self, user_id: UUID) -> User | None:
        """Get user by ID with eager-loaded metrics and engagement_state.

        Args:
            user_id: The user's UUID.

        Returns:
            User with metrics and engagement_state loaded, or None if not found.
        """
        stmt = (
            select(User)
            .options(joinedload(User.metrics), joinedload(User.engagement_state))
            .where(User.id == user_id)
        )
        result = await self.session.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Get user by Telegram ID with eager-loaded metrics and engagement_state.

        Args:
            telegram_id: The user's Telegram ID.

        Returns:
            User with metrics and engagement_state loaded, or None if not found.
        """
        stmt = (
            select(User)
            .options(joinedload(User.metrics), joinedload(User.engagement_state))
            .where(User.telegram_id == telegram_id)
        )
        result = await self.session.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def get_by_phone_number(self, phone_number: str) -> User | None:
        """Get user by phone number with eager-loaded metrics and engagement_state.

        Used for inbound voice calls to look up user by caller ID.

        Args:
            phone_number: Phone number in E.164 format (e.g., +41787950009).

        Returns:
            User with metrics and engagement_state loaded, or None if not found.
        """
        stmt = (
            select(User)
            .options(joinedload(User.metrics), joinedload(User.engagement_state))
            .where(User.phone == phone_number)
        )
        result = await self.session.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def create_with_metrics(
        self,
        user_id: UUID,
        telegram_id: int | None = None,
        phone: str | None = None,
    ) -> User:
        """Create a new user with default metrics atomically.

        Args:
            user_id: UUID to assign (usually from Supabase Auth).
            telegram_id: Optional Telegram ID.
            phone: Optional phone number.

        Returns:
            Created User with UserMetrics attached.
        """
        # Create user
        user = User(
            id=user_id,
            telegram_id=telegram_id,
            phone=phone,
            relationship_score=Decimal("50.00"),
            chapter=1,
            boss_attempts=0,
            days_played=0,
            game_status="active",
        )

        # Create metrics with defaults
        metrics = UserMetrics(
            id=uuid4(),
            user_id=user_id,
            intimacy=Decimal("50.00"),
            passion=Decimal("50.00"),
            trust=Decimal("50.00"),
            secureness=Decimal("50.00"),
        )

        # Create engagement state with defaults (spec 014)
        engagement_state = EngagementState(
            id=uuid4(),
            user_id=user_id,
            state="calibrating",
            calibration_score=Decimal("0.50"),
            multiplier=Decimal("0.90"),
            consecutive_in_zone=0,
            consecutive_clingy_days=0,
            consecutive_distant_days=0,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        # Attach metrics and engagement state to user
        user.metrics = metrics
        user.engagement_state = engagement_state

        # Add and flush
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)

        return user

    async def update_score(
        self,
        user_id: UUID,
        delta: Decimal,
        event_type: str | None = None,
        event_details: dict[str, Any] | None = None,
    ) -> User:
        """Update user's relationship score and log to history.

        Args:
            user_id: The user's UUID.
            delta: Score change (positive or negative).
            event_type: Type of event causing change (conversation, decay, etc.).
            event_details: Additional details about the event.

        Returns:
            Updated User entity.

        Raises:
            ValueError: If user not found.
        """
        user = await self.get(user_id)
        if user is None:
            raise ValueError(f"User {user_id} not found")

        # Calculate new score with clamping
        new_score = user.relationship_score + delta
        new_score = max(Decimal("0.00"), min(Decimal("100.00"), new_score))
        user.relationship_score = new_score

        # Log to score history
        history = ScoreHistory(
            id=uuid4(),
            user_id=user_id,
            score=new_score,
            chapter=user.chapter,
            event_type=event_type,
            event_details=event_details,
            recorded_at=datetime.now(UTC),
        )
        self.session.add(history)

        await self.session.flush()
        await self.session.refresh(user)

        return user

    async def apply_decay(
        self,
        user_id: UUID,
        decay_amount: Decimal,
    ) -> User:
        """Apply daily decay to user's score.

        Args:
            user_id: The user's UUID.
            decay_amount: Amount to subtract (positive value).

        Returns:
            Updated User entity.
        """
        return await self.update_score(
            user_id,
            delta=-decay_amount,
            event_type="decay",
            event_details={"decay_amount": str(decay_amount)},
        )

    async def advance_chapter(self, user_id: UUID) -> User:
        """Advance user to the next chapter.

        Increments chapter (max 5), resets boss attempts, and logs event.

        Args:
            user_id: The user's UUID.

        Returns:
            Updated User entity.
        """
        user = await self.get(user_id)
        if user is None:
            raise ValueError(f"User {user_id} not found")

        old_chapter = user.chapter

        # Increment chapter (cap at 5)
        if user.chapter < 5:
            user.chapter += 1

        # Reset boss attempts
        user.boss_attempts = 0

        # Log chapter advancement
        if user.chapter != old_chapter:
            history = ScoreHistory(
                id=uuid4(),
                user_id=user_id,
                score=user.relationship_score,
                chapter=user.chapter,
                event_type="chapter_advance",
                event_details={
                    "from_chapter": old_chapter,
                    "to_chapter": user.chapter,
                },
                recorded_at=datetime.now(UTC),
            )
            self.session.add(history)

        await self.session.flush()
        await self.session.refresh(user)

        return user

    async def update_last_interaction(
        self,
        user_id: UUID,
        timestamp: datetime | None = None,
    ) -> User:
        """Update user's last_interaction_at to reset decay grace period.

        Called by text agent and voice agent after qualifying interactions.
        This resets the grace period timer for the decay system.

        Args:
            user_id: The user's UUID.
            timestamp: Timestamp to set (defaults to now if not specified).

        Returns:
            Updated User entity.

        Raises:
            ValueError: If user not found.
        """
        user = await self.get(user_id)
        if user is None:
            raise ValueError(f"User {user_id} not found")

        # Use provided timestamp or current time
        user.last_interaction_at = timestamp or datetime.now(UTC)

        await self.session.flush()
        await self.session.refresh(user)

        return user

    async def get_active_users_for_decay(self) -> list[User]:
        """Get all users eligible for decay check.

        Returns users with game_status='active' only.
        Users in boss_fight, game_over, or won status are excluded.

        Returns:
            List of active users to check for decay.
        """
        stmt = (
            select(User)
            .options(joinedload(User.metrics), joinedload(User.engagement_state))
            .where(User.game_status == "active")
        )
        result = await self.session.execute(stmt)
        return list(result.unique().scalars().all())

    async def update_game_status(
        self,
        user_id: UUID,
        status: str,
    ) -> User:
        """Update user's game status.

        Args:
            user_id: The user's UUID.
            status: New game status (active, boss_fight, game_over, won).

        Returns:
            Updated User entity.

        Raises:
            ValueError: If user not found.
        """
        user = await self.get(user_id)
        if user is None:
            raise ValueError(f"User {user_id} not found")

        user.game_status = status

        await self.session.flush()
        await self.session.refresh(user)

        return user

    async def set_boss_fight_status(self, user_id: UUID) -> User:
        """Set user's game status to boss_fight and log event.

        Used when a boss encounter is initiated (T5-001).

        Args:
            user_id: The user's UUID.

        Returns:
            Updated User entity.

        Raises:
            ValueError: If user not found.
        """
        user = await self.get(user_id)
        if user is None:
            raise ValueError(f"User {user_id} not found")

        old_status = user.game_status
        user.game_status = "boss_fight"

        # Log to score_history
        history = ScoreHistory(
            id=uuid4(),
            user_id=user_id,
            score=user.relationship_score,
            chapter=user.chapter,
            event_type="boss_initiated",
            event_details={
                "from_status": old_status,
                "to_status": "boss_fight",
                "chapter": user.chapter,
            },
            recorded_at=datetime.now(UTC),
        )
        self.session.add(history)

        await self.session.flush()
        await self.session.refresh(user)

        return user

    async def increment_boss_attempts(self, user_id: UUID) -> User:
        """Increment user's boss_attempts counter and log event.

        Used when a boss encounter fails (T5-003).
        Max 3 attempts before game_over.

        Args:
            user_id: The user's UUID.

        Returns:
            Updated User entity with incremented boss_attempts.

        Raises:
            ValueError: If user not found.
        """
        user = await self.get(user_id)
        if user is None:
            raise ValueError(f"User {user_id} not found")

        old_attempts = user.boss_attempts
        user.boss_attempts += 1

        # Log to score_history
        history = ScoreHistory(
            id=uuid4(),
            user_id=user_id,
            score=user.relationship_score,
            chapter=user.chapter,
            event_type="boss_failed",
            event_details={
                "attempts": user.boss_attempts,
                "max_attempts": 3,
            },
            recorded_at=datetime.now(UTC),
        )
        self.session.add(history)

        await self.session.flush()
        await self.session.refresh(user)

        return user
