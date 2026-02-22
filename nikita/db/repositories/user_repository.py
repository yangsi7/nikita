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
        """Get user by ID with eager-loaded metrics, engagement_state, and vice_preferences.

        Args:
            user_id: The user's UUID.

        Returns:
            User with metrics, engagement_state, and vice_preferences loaded, or None if not found.
        """
        stmt = (
            select(User)
            .options(
                joinedload(User.metrics),
                joinedload(User.engagement_state),
                joinedload(User.vice_preferences),
            )
            .where(User.id == user_id)
        )
        result = await self.session.execute(stmt)
        return result.unique().scalar_one_or_none()

    # Alias for backwards compatibility (Spec 045 WP-5c)
    async def get_by_id(self, user_id: UUID) -> User | None:
        """Alias for get() — used by touchpoints module."""
        return await self.get(user_id)

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

    async def get_by_telegram_id_for_update(
        self, telegram_id: int, *, timeout_ms: int = 10_000
    ) -> User | None:
        """Get user by Telegram ID with row-level lock (R-2).

        Uses SELECT ... FOR UPDATE to prevent concurrent message
        processing race conditions (double boss triggers, scoring races).
        Lock is held until the enclosing transaction commits/rolls back.

        Args:
            telegram_id: The user's Telegram ID.
            timeout_ms: Statement timeout in ms to prevent deadlocks (default 10s).

        Returns:
            User with metrics and engagement_state loaded, or None if not found.
        """
        from sqlalchemy import text

        # Set statement timeout to prevent deadlock hangs
        await self.session.execute(
            text(f"SET LOCAL statement_timeout = '{timeout_ms}'")
        )
        stmt = (
            select(User)
            .options(joinedload(User.metrics), joinedload(User.engagement_state))
            .where(User.telegram_id == telegram_id)
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def get_by_phone_number(self, phone_number: str) -> User | None:
        """Get user by phone number with eager-loaded relationships.

        Used for inbound voice calls to look up user by caller ID.
        Eager-loads metrics, engagement_state, and vice_preferences to avoid
        DetachedInstanceError when accessed after session closes.

        Args:
            phone_number: Phone number in E.164 format (e.g., +41787950009).

        Returns:
            User with metrics, engagement_state, and vice_preferences loaded,
            or None if not found.
        """
        stmt = (
            select(User)
            .options(
                joinedload(User.metrics),
                joinedload(User.engagement_state),
                joinedload(User.vice_preferences),
            )
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
        # Spec 049 P8: Clear boss fight timestamp when leaving boss_fight
        if status != "boss_fight":
            user.boss_fight_started_at = None

        await self.session.flush()
        await self.session.refresh(user)

        return user

    async def reset_game_state(self, user_id: UUID) -> User:
        """Reset ALL game state fields to defaults for a fresh start.

        Used when a player restarts after game_over or won. Resets user,
        metrics, and engagement state to match create_with_metrics() defaults.

        Args:
            user_id: The user's UUID.

        Returns:
            Updated User entity with reset state.

        Raises:
            ValueError: If user not found.
        """
        user = await self.get(user_id)
        if user is None:
            raise ValueError(f"User {user_id} not found")

        # Reset user game fields
        user.relationship_score = Decimal("50.00")
        user.chapter = 1
        user.boss_attempts = 0
        user.days_played = 0
        user.game_status = "active"
        user.boss_fight_started_at = None  # Spec 049 P8
        user.onboarding_status = "pending"
        user.last_interaction_at = None
        user.cached_voice_prompt = None
        user.cached_voice_context = None
        user.cached_voice_prompt_at = None

        # Reset metrics to defaults
        if user.metrics is not None:
            user.metrics.intimacy = Decimal("50.00")
            user.metrics.passion = Decimal("50.00")
            user.metrics.trust = Decimal("50.00")
            user.metrics.secureness = Decimal("50.00")

        # Reset engagement state to defaults
        if user.engagement_state is not None:
            user.engagement_state.state = "calibrating"
            user.engagement_state.calibration_score = Decimal("0.50")
            user.engagement_state.multiplier = Decimal("0.90")
            user.engagement_state.consecutive_in_zone = 0
            user.engagement_state.consecutive_clingy_days = 0
            user.engagement_state.consecutive_distant_days = 0
            user.engagement_state.updated_at = datetime.now(UTC)

        # Log score history entry for the reset
        reset_entry = ScoreHistory(
            id=uuid4(),
            user_id=user_id,
            score_before=user.relationship_score,
            score_after=Decimal("50.00"),
            delta=Decimal("0.00"),
            event_type="game_reset",
        )
        self.session.add(reset_entry)

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
        # Spec 049 P8: Set dedicated boss fight timestamp for timeout detection
        user.boss_fight_started_at = datetime.now(UTC)

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

    # --- Onboarding Methods (Spec 028) ---

    async def update_onboarding_status(
        self,
        user_id: UUID,
        status: str,
        call_id: str | None = None,
    ) -> User:
        """Update user's onboarding status.

        Args:
            user_id: The user's UUID.
            status: New onboarding status (pending, in_progress, completed, skipped).
            call_id: Optional ElevenLabs call ID.

        Returns:
            Updated User entity.

        Raises:
            ValueError: If user not found or invalid status.
        """
        valid_statuses = {"pending", "in_progress", "completed", "skipped"}
        if status not in valid_statuses:
            raise ValueError(f"Invalid onboarding status: {status}")

        user = await self.get(user_id)
        if user is None:
            raise ValueError(f"User {user_id} not found")

        user.onboarding_status = status
        if call_id:
            user.onboarding_call_id = call_id

        if status == "completed":
            user.onboarded_at = datetime.now(UTC)

        await self.session.flush()
        await self.session.refresh(user)

        return user

    async def update_onboarding_profile(
        self,
        user_id: UUID,
        profile_updates: dict[str, Any],
    ) -> User:
        """Update user's onboarding profile data.

        Merges profile_updates with existing onboarding_profile JSONB.

        Args:
            user_id: The user's UUID.
            profile_updates: Profile fields to update.

        Returns:
            Updated User entity.

        Raises:
            ValueError: If user not found.
        """
        user = await self.get(user_id)
        if user is None:
            raise ValueError(f"User {user_id} not found")

        # Merge with existing profile
        existing_profile = user.onboarding_profile or {}
        updated_profile = {**existing_profile, **profile_updates}
        user.onboarding_profile = updated_profile

        await self.session.flush()
        await self.session.refresh(user)

        return user

    async def complete_onboarding(
        self,
        user_id: UUID,
        call_id: str,
        profile: dict[str, Any],
    ) -> User:
        """Mark user as onboarded and store final profile.

        Args:
            user_id: The user's UUID.
            call_id: ElevenLabs call ID for the onboarding call.
            profile: Complete onboarding profile data.

        Returns:
            Updated User entity.

        Raises:
            ValueError: If user not found.
        """
        user = await self.get(user_id)
        if user is None:
            raise ValueError(f"User {user_id} not found")

        user.onboarding_status = "completed"
        user.onboarding_call_id = call_id
        user.onboarding_profile = profile
        user.onboarded_at = datetime.now(UTC)

        # Log to score_history
        history = ScoreHistory(
            id=uuid4(),
            user_id=user_id,
            score=user.relationship_score,
            chapter=user.chapter,
            event_type="onboarding_complete",
            event_details={
                "call_id": call_id,
                "darkness_level": profile.get("darkness_level"),
                "pacing_weeks": profile.get("pacing_weeks"),
            },
            recorded_at=datetime.now(UTC),
        )
        self.session.add(history)

        await self.session.flush()
        await self.session.refresh(user)

        return user

    async def get_users_pending_onboarding(self) -> list[User]:
        """Get users who haven't completed onboarding.

        Returns:
            List of users with onboarding_status = 'pending'.
        """
        stmt = (
            select(User)
            .options(joinedload(User.metrics), joinedload(User.engagement_state))
            .where(User.onboarding_status == "pending")
        )
        result = await self.session.execute(stmt)
        return list(result.unique().scalars().all())

    async def is_onboarded(self, user_id: UUID) -> bool:
        """Check if user has completed onboarding.

        Args:
            user_id: The user's UUID.

        Returns:
            True if onboarding is completed or skipped.
        """
        user = await self.get(user_id)
        if user is None:
            return False
        return user.onboarding_status in {"completed", "skipped"}

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

    async def increment_days_played(self, user_id: UUID) -> User:
        """Increment user's days_played counter by 1 (Spec 101 FR-002).

        Called once per decay cycle for each active user, regardless of whether
        decay was applied, to track total days the player has been engaged.

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

        user.days_played += 1

        await self.session.flush()
        await self.session.refresh(user)

        return user

    async def set_cool_down(self, user_id: UUID, cool_down_until: datetime) -> User:
        """Set boss PARTIAL cooldown expiry (Spec 101 FR-001).

        Called after a PARTIAL boss outcome to prevent the boss from
        re-triggering until the cooldown expires.

        Args:
            user_id: The user's UUID.
            cool_down_until: Timestamp when cooldown expires (typically now+24h).

        Returns:
            Updated User entity.

        Raises:
            ValueError: If user not found.
        """
        user = await self.get(user_id)
        if user is None:
            raise ValueError(f"User {user_id} not found")

        user.cool_down_until = cool_down_until

        await self.session.flush()
        await self.session.refresh(user)

        return user

    # --- Voice Cache Methods (Spec 031) ---

    async def invalidate_voice_cache(self, user_id: UUID) -> None:
        """Invalidate user's cached voice prompt.

        Called after text post-processing to ensure voice-text consistency.
        Sets cached_voice_prompt and cached_voice_prompt_at to NULL.

        Args:
            user_id: The user's UUID.

        Raises:
            ValueError: If user not found.
        """
        user = await self.get(user_id)
        if user is None:
            raise ValueError(f"User {user_id} not found")

        user.cached_voice_prompt = None
        user.cached_voice_prompt_at = None

        await self.session.flush()

    # --- Settings Methods (Spec 008, T44) ---

    async def update_settings(
        self,
        user_id: UUID,
        timezone: str | None = None,
        notifications_enabled: bool | None = None,
    ) -> User:
        """Update user settings (timezone, notifications).

        Args:
            user_id: The user's UUID.
            timezone: Optional new timezone (e.g., "Europe/Zurich").
            notifications_enabled: Optional notifications preference.

        Returns:
            Updated User entity.

        Raises:
            ValueError: If user not found.
        """
        user = await self.get(user_id)
        if user is None:
            raise ValueError(f"User {user_id} not found")

        if timezone is not None:
            user.timezone = timezone
        if notifications_enabled is not None:
            user.notifications_enabled = notifications_enabled

        await self.session.flush()
        await self.session.refresh(user)

        return user

    async def reconcile_score(self, user_id: UUID) -> dict | None:
        """Reconcile relationship_score with composite score from metrics.

        Spec 102 FR-003: Detects and corrects drift between relationship_score
        and the composite score computed from UserMetrics dimensions.

        Args:
            user_id: The user's UUID.

        Returns:
            Dict with old_score, new_score, drift if corrected; None otherwise.
        """
        user = await self.get(user_id)
        if user is None:
            return None

        if user.metrics is None:
            return None

        composite = user.metrics.calculate_composite_score()
        old_score = user.relationship_score
        drift = abs(composite - old_score)

        # Threshold: correct if drift > 0.01
        if drift <= Decimal("0.01"):
            return None

        user.relationship_score = composite
        await self.session.flush()

        return {
            "old_score": old_score,
            "new_score": composite,
            "drift": drift,
        }

    async def delete_user_cascade(self, user_id: UUID) -> bool:
        """Delete user and all related data (cascade delete).

        Due to ON DELETE CASCADE constraints in the database, deleting
        the user will automatically cascade to:
        - user_metrics
        - user_vice_preferences
        - conversations
        - score_history
        - daily_summaries
        - conversation_threads
        - nikita_thoughts
        - engagement_state, engagement_history
        - generated_prompts
        - profile, backstory
        - scheduled_events, scheduled_touchpoints

        Args:
            user_id: The user's UUID.

        Returns:
            True if user was deleted, False if not found.
        """
        user = await self.get(user_id)
        if user is None:
            return False

        await self.session.delete(user)
        await self.session.flush()

        return True
