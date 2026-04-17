"""User repository for user-related database operations.

Handles User entity with eager-loaded metrics, score updates,
decay application, and chapter advancement.
"""

import enum
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import cast, func, or_, select, update
from sqlalchemy.dialects.postgresql import JSONB, array
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from nikita.db.models.engagement import EngagementState
from nikita.db.models.game import ScoreHistory
from nikita.db.models.user import User, UserMetrics
from nikita.db.repositories.base import BaseRepository


class BindResult(enum.Enum):
    """Outcome of UserRepository.update_telegram_id.

    - BOUND: fresh binding, users.telegram_id was NULL before.
    - ALREADY_BOUND_SAME_USER: user_id already had this telegram_id;
      idempotent no-op. No error raised.

    Cross-user conflict (telegram_id held by a different user) raises
    TelegramIdAlreadyBoundByOtherUserError instead of returning a BindResult.
    """

    BOUND = "bound"
    ALREADY_BOUND_SAME_USER = "already_bound_same_user"


class TelegramIdAlreadyBoundByOtherUserError(Exception):
    """Raised when a portal user attempts to bind a telegram_id already
    held by another user row.

    Carries the conflicting telegram_id on the instance so callers can
    produce a useful error message without re-querying.
    """

    def __init__(self, telegram_id: int) -> None:
        self.telegram_id = telegram_id
        super().__init__(
            f"telegram_id {telegram_id} is already bound to another user"
        )


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
            phone_number: Phone number in E.164 format (e.g., +41445056044).

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

    async def update_phone(self, user_id: UUID, phone: str) -> None:
        """Update the user's phone number.

        Fetches the user by ID and sets the phone column. Calls
        ``session.flush()`` so the write is visible within the current
        transaction before the session auto-commits.

        Callers must handle ``sqlalchemy.exc.IntegrityError`` if a unique
        constraint on ``users.phone`` is violated (i.e. the number is already
        registered to another account).

        Args:
            user_id: The user's UUID.
            phone: Normalized E.164 phone string (e.g. "+41791234567").

        Raises:
            IntegrityError: If the phone number already exists in ``users.phone``
                (unique partial index ``uq_users_phone`` added in Spec 212 PR B).
        """
        user = await self.get(user_id)
        if user:
            user.phone = phone
            await self.session.flush()

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
            score=Decimal("50.00"),
            chapter=1,
            event_type="game_reset",
            event_details={"reset_from_score": str(user.relationship_score)},
            recorded_at=datetime.now(UTC),
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

    async def activate_game(self, user_id: UUID) -> User:
        """Activate game state for a newly onboarded user (GH #183).

        Sets game_status='active', relationship_score=50.00, days_played=0.
        Called after portal or voice onboarding completes to start the game.

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

        user.game_status = "active"
        user.relationship_score = Decimal("50.00")
        user.days_played = 0

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

    async def set_pending_handoff(self, user_id: UUID, value: bool) -> None:
        """Set the user's ``pending_handoff`` flag.

        Used by the portal onboarding → Telegram handoff retry mechanism
        (PR-2, GH #198-linked). When portal onboarding completes without a
        linked ``telegram_id``, we set this flag to True and fire the
        HandoffManager work on the user's first subsequent message.

        Args:
            user_id: The user's UUID.
            value: True to defer handoff, False to mark it completed.

        Raises:
            ValueError: If the user is not found.
        """
        user = await self.get(user_id)
        if user is None:
            raise ValueError(f"User {user_id} not found")

        user.pending_handoff = value

        await self.session.flush()
        await self.session.refresh(user)

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

    async def update_onboarding_profile_key(
        self,
        user_id: UUID,
        key: str,
        value: Any,
    ) -> None:
        """Set a single key inside users.onboarding_profile JSONB via jsonb_set.

        Uses ``jsonb_set(onboarding_profile, ARRAY[<key>]::TEXT[], cast(value, JSONB))``
        to update exactly one key without loading the full profile into Python.
        Callers must pass ``key`` as a plain string; it is wrapped as a
        single-element ``text[]`` for the jsonb_set path automatically.

        CRITICAL implementation notes (two gotchas):

        1. The JSONB value MUST bind as the RAW Python object
           (``cast(value, JSONB)``), NOT pre-encoded via ``json.dumps()``.
           asyncpg's JSONB codec serializes Python objects to JSON exactly
           once at the wire-protocol layer. Passing ``json.dumps(value)``
           (a Python string) causes asyncpg to encode AGAIN, producing
           double-encoded JSONB: e.g. ``json.dumps(28) -> "28"`` then
           codec -> stored as JSON string ``"28"`` instead of JSON number
           28. Downstream ``_age_bucket`` then TypeErrors comparing str to
           int. This was the GH #318 bug, surfaced by Agent H-3 dogfood
           on 2026-04-17. Earlier PR #279/#282 docstring advised the
           opposite; that guidance was incorrect for our asyncpg stack
           and was never exercised against a live DB until PR #315 wired
           the wizard's first real PATCH call.

        2. The path MUST be a Postgres ``text[]``, constructed via
           ``sqlalchemy.dialects.postgresql.array([key])``. Passing a plain
           Python string like ``f"{{{key}}}"`` makes asyncpg infer the bind
           as ``character varying`` at runtime, and Postgres rejects because
           ``jsonb_set``'s real signature is
           ``jsonb_set(jsonb, text[], jsonb)``. This was the GH #316 bug,
           latent since PR #283 and surfaced by PR #315 when the wizard
           first exercised this code path in prod.

        Silently no-ops if the user does not exist (UPDATE affects 0 rows).

        Args:
            user_id: The user's UUID.
            key: Top-level JSONB key to set (e.g. ``"pipeline_state"``).
            value: Python value to store. Any JSON-serializable type
                (str, int, float, bool, None, list, dict). asyncpg's
                JSONB codec handles serialization at execute time.
        """
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(
                onboarding_profile=func.jsonb_set(
                    User.onboarding_profile,
                    # Emits `ARRAY[$N]::TEXT[]`. See docstring note #2 for
                    # the asyncpg VARCHAR inference bug this guards against.
                    array([key]),
                    # Bind raw value, NOT json.dumps. asyncpg's JSONB codec
                    # serializes once. See docstring note #1 for GH #318.
                    cast(value, JSONB),
                )
            )
        )
        await self.session.execute(stmt)

    async def update_telegram_id(
        self,
        user_id: UUID,
        telegram_id: int,
    ) -> BindResult:
        """Atomically bind users.telegram_id for a portal user (GH #321 REQ-4).

        Used by the Telegram bot's `_handle_start <code>` flow after a
        successful `TelegramLinkRepository.verify_code`. The WHERE predicate
        `(telegram_id IS NULL OR telegram_id = :tid)` is the atomic gate:
        the UPDATE affects the row only when it is safe to do so. A small
        probe SELECT on the primary key precedes the UPDATE to distinguish
        `BOUND` (fresh bind) from `ALREADY_BOUND_SAME_USER` (idempotent re-bind)
        without needing RETURNING-old-value gymnastics.

        Respects the ``users.telegram_id`` UNIQUE constraint without ever
        hitting a raw IntegrityError path — the WHERE predicate filters out
        the cross-user conflict case pre-update, and a disambiguation SELECT
        confirms whether the telegram_id is held by another row.

        Args:
            user_id: The portal user's UUID (from `verify_code`).
            telegram_id: The Telegram account's numeric ID (from the bot update).

        Returns:
            BindResult.BOUND if a fresh binding was created.
            BindResult.ALREADY_BOUND_SAME_USER if user_id already had this
              telegram_id (idempotent no-op).

        Raises:
            TelegramIdAlreadyBoundByOtherUserError: if ``telegram_id`` is
              already bound to a different ``user_id``. Carries the conflicting
              telegram_id on the exception.
            ValueError: if ``user_id`` does not exist in ``users``.
        """
        # Step 1: Probe existing telegram_id on this user. PK lookup,
        # microseconds. `scalar_one_or_none()` returns None in two cases
        # that matter here:
        #   (a) user_id exists but telegram_id column IS NULL (fresh bind path)
        #   (b) user_id does not exist at all
        # We cannot distinguish (a) from (b) from the probe alone; if the
        # UPDATE in Step 2 affects 0 rows, Step 3's disambiguation resolves
        # which case it was.
        probe_stmt = select(User.telegram_id).where(User.id == user_id)
        probe_result = await self.session.execute(probe_stmt)
        existing_tid = probe_result.scalar_one_or_none()

        if existing_tid is not None and existing_tid == telegram_id:
            # Idempotent no-op: user is already bound to this telegram_id.
            # Guard on `is not None` so a non-existent user_id (probe
            # returns None) doesn't accidentally short-circuit as
            # ALREADY_BOUND_SAME_USER when `telegram_id` is also None.
            return BindResult.ALREADY_BOUND_SAME_USER

        # Step 2: Atomic UPDATE with predicate-filter. The predicate
        # `(telegram_id IS NULL OR telegram_id = :tid)` filters out the
        # cross-user conflict case pre-constraint. RETURNING tells us
        # whether the row was actually updated.
        update_stmt = (
            update(User)
            .where(User.id == user_id)
            .where(
                or_(
                    User.telegram_id.is_(None),
                    User.telegram_id == telegram_id,
                )
            )
            .values(telegram_id=telegram_id)
            .returning(User.telegram_id)
        )
        update_result = await self.session.execute(update_stmt)
        row = update_result.first()

        if row is not None:
            # Successful bind — existing_tid was None (probe confirmed),
            # so this was a fresh binding.
            return BindResult.BOUND

        # Step 3: rowcount == 0. Three sub-cases to disambiguate:
        #   (a) user_id doesn't exist at all → ValueError
        #   (b) telegram_id is held by a DIFFERENT user → typed conflict exception
        #   (c) user_id exists but got its telegram_id concurrently set to a
        #       third value (probe saw NULL, a racing call bound before our
        #       UPDATE) → typed concurrent-modification error so the caller
        #       can decide whether to retry. The probe returned None per
        #       Step 1, so this is a genuine race window, not a bad probe.
        # First: does the telegram_id we attempted to bind belong to someone?
        conflict_stmt = select(User.id).where(User.telegram_id == telegram_id)
        conflict_result = await self.session.execute(conflict_stmt)
        conflict_holder = conflict_result.scalar_one_or_none()

        if conflict_holder is not None and conflict_holder != user_id:
            raise TelegramIdAlreadyBoundByOtherUserError(telegram_id)

        # Not-a-conflict: check whether user_id still exists. If it does,
        # something between the probe and the UPDATE mutated telegram_id to
        # a value other than NULL and other than our target. That's a
        # concurrent-modification race — raise a distinct error instead of
        # misreporting "user not found".
        existence_stmt = select(User.id).where(User.id == user_id)
        existence_result = await self.session.execute(existence_stmt)
        if existence_result.scalar_one_or_none() is not None:
            raise TelegramIdAlreadyBoundByOtherUserError(telegram_id)

        raise ValueError(f"User {user_id} not found")

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

        # Idempotency guard: skip if already completed (Closes #220)
        if user.onboarding_status == "completed":
            return user

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

        .. deprecated::
            Use :meth:`bulk_increment_days_played` instead.  This per-user
            method causes N+1 queries in batch contexts.  Retained for
            single-user admin/test scenarios only.

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

    async def bulk_increment_days_played(self, user_ids: list[UUID]) -> int:
        """Bulk increment days_played for multiple users in a single UPDATE.

        Eliminates N+1 query pattern from process_all() (Spec 101 FR-002).

        Args:
            user_ids: List of user UUIDs to increment.

        Returns:
            Number of rows updated.
        """
        if not user_ids:
            return 0
        from sqlalchemy import update
        stmt = (
            update(User)
            .where(User.id.in_(user_ids))
            .values(days_played=User.days_played + 1)
        )
        # Bulk UPDATE bypasses SQLAlchemy identity map — callers must not
        # read days_played from in-session User objects after this call.
        result = await self.session.execute(stmt)
        return result.rowcount

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
        await self.session.refresh(user)

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

    async def get_users_with_stale_voice_prompts(
        self,
        stale_hours: int = 6,
        limit: int = 50,
    ) -> list[User]:
        """Get active users with stale or missing voice prompts (Spec 209 FR-005).

        Returns users where cached_voice_prompt_at is NULL or older than
        stale_hours. Eager-loads user_metrics and vice_preferences for
        pipeline processing.

        Args:
            stale_hours: Hours after which a prompt is considered stale.
            limit: Maximum users to return (batch cap).

        Returns:
            List of User objects with relationships eager-loaded.
        """
        from sqlalchemy import or_

        stale_cutoff = datetime.now(UTC) - timedelta(hours=stale_hours)
        stmt = (
            select(User)
            .options(
                joinedload(User.metrics),
                joinedload(User.vice_preferences),
                joinedload(User.engagement_state),
            )
            .where(
                User.game_status == "active",
                or_(
                    User.cached_voice_prompt_at.is_(None),
                    User.cached_voice_prompt_at < stale_cutoff,
                ),
            )
            .order_by(User.cached_voice_prompt_at.asc().nulls_first())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.unique().scalars().all())

    async def count_users_with_stale_voice_prompts(
        self,
        stale_hours: int = 6,
    ) -> int:
        """Count active users with stale or missing voice prompts (Spec 209 FR-005).

        Used by refresh cron to compute accurate deferred count.

        Args:
            stale_hours: Hours after which a prompt is considered stale.

        Returns:
            Total count of stale users (unbounded).
        """
        from sqlalchemy import func, or_

        stale_cutoff = datetime.now(UTC) - timedelta(hours=stale_hours)
        stmt = (
            select(func.count())
            .select_from(User)
            .where(
                User.game_status == "active",
                or_(
                    User.cached_voice_prompt_at.is_(None),
                    User.cached_voice_prompt_at < stale_cutoff,
                ),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()
