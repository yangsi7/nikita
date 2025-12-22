"""Repositories for profile and onboarding operations.

Provides repository pattern implementation for:
- UserProfile: User preferences for personalization
- UserBackstory: How Nikita and user "met"
- OnboardingState: Transient onboarding flow state
- VenueCache: Cached venue research results

Part of 017-enhanced-onboarding feature (T1.5).
"""

from datetime import timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.base import utc_now
from nikita.db.models.profile import (
    OnboardingState,
    OnboardingStep,
    UserBackstory,
    UserProfile,
    VenueCache,
)
from nikita.db.repositories.base import BaseRepository


class ProfileRepository(BaseRepository[UserProfile]):
    """Repository for UserProfile operations.

    Handles user profile CRUD with defaults and validation.
    Uses UUID primary key matching users.id for 1:1 relationship.

    AC-T1.5-001: ProfileRepository with create_profile(), get_by_user_id(), update()
    AC-T1.5-004: Inherits from BaseRepository[UserProfile]
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize ProfileRepository.

        Args:
            session: Async SQLAlchemy session.
        """
        super().__init__(session, UserProfile)

    async def get_by_user_id(self, user_id: UUID) -> UserProfile | None:
        """Get profile by user ID.

        Args:
            user_id: The user's UUID (same as profile.id).

        Returns:
            UserProfile if found, None otherwise.
        """
        # Profile.id == User.id (1:1 relationship)
        return await self.get(user_id)

    async def create_profile(
        self,
        user_id: UUID,
        location_city: str | None = None,
        location_country: str | None = None,
        life_stage: str | None = None,
        social_scene: str | None = None,
        primary_interest: str | None = None,
        drug_tolerance: int = 3,
    ) -> UserProfile:
        """Create a new user profile.

        Args:
            user_id: UUID matching user.id (FK relationship).
            location_city: User's city (e.g., "Berlin").
            location_country: User's country (e.g., "Germany").
            life_stage: Career phase (e.g., "tech", "artist", "student").
            social_scene: Social scene preference (e.g., "techno", "art").
            primary_interest: Main hobby/interest.
            drug_tolerance: Content intensity 1-5 (default 3).

        Returns:
            Created UserProfile entity.
        """
        profile = UserProfile(
            id=user_id,
            location_city=location_city,
            location_country=location_country,
            life_stage=life_stage,
            social_scene=social_scene,
            primary_interest=primary_interest,
            drug_tolerance=drug_tolerance,
        )
        return await self.create(profile)

    async def update_from_onboarding(
        self,
        user_id: UUID,
        collected_answers: dict[str, Any],
    ) -> UserProfile:
        """Update profile from onboarding collected answers.

        Convenience method to bulk-update profile from OnboardingState.collected_answers.

        Args:
            user_id: The user's UUID.
            collected_answers: Dict from OnboardingState.collected_answers.

        Returns:
            Updated UserProfile entity.
        """
        profile = await self.get_by_user_id(user_id)
        if profile is None:
            # Create new profile if doesn't exist
            return await self.create_profile(
                user_id=user_id,
                location_city=collected_answers.get("location_city"),
                location_country=collected_answers.get("location_country"),
                life_stage=collected_answers.get("life_stage"),
                social_scene=collected_answers.get("social_scene"),
                primary_interest=collected_answers.get("primary_interest"),
                drug_tolerance=collected_answers.get("drug_tolerance", 3),
            )

        # Update existing profile
        if "location_city" in collected_answers:
            profile.location_city = collected_answers["location_city"]
        if "location_country" in collected_answers:
            profile.location_country = collected_answers["location_country"]
        if "life_stage" in collected_answers:
            profile.life_stage = collected_answers["life_stage"]
        if "social_scene" in collected_answers:
            profile.social_scene = collected_answers["social_scene"]
        if "primary_interest" in collected_answers:
            profile.primary_interest = collected_answers["primary_interest"]
        if "drug_tolerance" in collected_answers:
            profile.drug_tolerance = collected_answers["drug_tolerance"]

        return await self.update(profile)


class BackstoryRepository(BaseRepository[UserBackstory]):
    """Repository for UserBackstory operations.

    Handles backstory CRUD with JSONB persona overrides.
    Uses auto-generated UUID primary key, UNIQUE constraint on user_id.

    AC-T1.5-002: BackstoryRepository with create(), get_by_user_id(), update()
    AC-T1.5-004: Inherits from BaseRepository[UserBackstory]
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize BackstoryRepository.

        Args:
            session: Async SQLAlchemy session.
        """
        super().__init__(session, UserBackstory)

    async def get_by_user_id(self, user_id: UUID) -> UserBackstory | None:
        """Get backstory by user ID.

        Args:
            user_id: The user's UUID.

        Returns:
            UserBackstory if found, None otherwise.
        """
        stmt = select(UserBackstory).where(UserBackstory.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        user_id: UUID,
        venue_name: str | None = None,
        venue_city: str | None = None,
        scenario_type: str | None = None,
        how_we_met: str | None = None,
        the_moment: str | None = None,
        unresolved_hook: str | None = None,
        nikita_persona_overrides: dict[str, Any] | None = None,
    ) -> UserBackstory:
        """Create a new backstory for user.

        Args:
            user_id: The user's UUID.
            venue_name: Where they met (e.g., "Berghain").
            venue_city: City of venue (e.g., "Berlin").
            scenario_type: Type of meeting (romantic, intellectual, chaotic, custom).
            how_we_met: Narrative of the first encounter.
            the_moment: The pivotal emotional moment.
            unresolved_hook: What keeps the tension going.
            nikita_persona_overrides: JSONB dict of persona customizations.

        Returns:
            Created UserBackstory entity.
        """
        backstory = UserBackstory(
            user_id=user_id,
            venue_name=venue_name,
            venue_city=venue_city,
            scenario_type=scenario_type,
            how_we_met=how_we_met,
            the_moment=the_moment,
            unresolved_hook=unresolved_hook,
            nikita_persona_overrides=nikita_persona_overrides,
        )
        self.session.add(backstory)
        await self.session.flush()
        await self.session.refresh(backstory)
        return backstory

    async def create_from_scenario(
        self,
        user_id: UUID,
        scenario: dict[str, Any],
    ) -> UserBackstory:
        """Create backstory from generated scenario dict.

        Convenience method used by BackstoryGeneratorService.

        Args:
            user_id: The user's UUID.
            scenario: Generated scenario dict with keys matching backstory fields.

        Returns:
            Created UserBackstory entity.
        """
        return await self.create(
            user_id=user_id,
            venue_name=scenario.get("venue_name"),
            venue_city=scenario.get("venue_city"),
            scenario_type=scenario.get("scenario_type"),
            how_we_met=scenario.get("how_we_met"),
            the_moment=scenario.get("the_moment"),
            unresolved_hook=scenario.get("unresolved_hook"),
            nikita_persona_overrides=scenario.get("nikita_persona_overrides"),
        )


class OnboardingStateRepository:
    """Repository for OnboardingState operations.

    Handles transient onboarding state with step transitions.
    Uses telegram_id (int) as primary key, similar to PendingRegistrationRepository.

    Note: Does NOT inherit from BaseRepository because:
    - Primary key is telegram_id (bigint), not UUID
    - Transient state (deleted on completion)
    - Simple CRUD operations only

    AC-T1.5-003: OnboardingStateRepository with get_or_create(), update_step(), delete()
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize OnboardingStateRepository.

        Args:
            session: Async SQLAlchemy session.
        """
        self._session = session

    @property
    def session(self) -> AsyncSession:
        """Access the database session."""
        return self._session

    async def get(self, telegram_id: int) -> OnboardingState | None:
        """Get onboarding state by Telegram ID.

        Args:
            telegram_id: Telegram user ID.

        Returns:
            OnboardingState if found, None otherwise.
        """
        stmt = select(OnboardingState).where(
            OnboardingState.telegram_id == telegram_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(self, telegram_id: int) -> OnboardingState:
        """Get existing state or create new one at LOCATION step.

        Uses upsert pattern to handle race conditions.

        Args:
            telegram_id: Telegram user ID.

        Returns:
            Existing or newly created OnboardingState.
        """
        # Try to get existing
        existing = await self.get(telegram_id)
        if existing is not None:
            return existing

        # Create new at first step
        stmt = insert(OnboardingState).values(
            telegram_id=telegram_id,
            current_step=OnboardingStep.LOCATION.value,
            collected_answers={},
        ).on_conflict_do_nothing(
            index_elements=["telegram_id"]
        ).returning(OnboardingState)

        result = await self._session.execute(stmt)
        state = result.scalar_one_or_none()

        # If on_conflict_do_nothing matched, we need to fetch
        if state is None:
            state = await self.get(telegram_id)

        return state

    async def update_step(
        self,
        telegram_id: int,
        step: OnboardingStep,
        collected_answers: dict[str, Any] | None = None,
    ) -> OnboardingState:
        """Update onboarding step and collected answers.

        Args:
            telegram_id: Telegram user ID.
            step: New step to transition to.
            collected_answers: Updated answers dict (replaces existing).

        Returns:
            Updated OnboardingState.

        Raises:
            ValueError: If state not found.
        """
        state = await self.get(telegram_id)
        if state is None:
            raise ValueError(f"OnboardingState not found for telegram_id {telegram_id}")

        state.current_step = step.value

        if collected_answers is not None:
            state.collected_answers = collected_answers

        await self._session.flush()
        await self._session.refresh(state)

        return state

    async def add_answer(
        self,
        telegram_id: int,
        key: str,
        value: Any,
    ) -> OnboardingState:
        """Add single answer to collected_answers.

        Convenience method for step-by-step answer collection.

        Args:
            telegram_id: Telegram user ID.
            key: Answer key (e.g., "location_city").
            value: Answer value.

        Returns:
            Updated OnboardingState.
        """
        state = await self.get(telegram_id)
        if state is None:
            raise ValueError(f"OnboardingState not found for telegram_id {telegram_id}")

        # Update JSONB - SQLAlchemy tracks changes automatically
        state.collected_answers = {**state.collected_answers, key: value}

        await self._session.flush()
        await self._session.refresh(state)

        return state

    async def delete(self, telegram_id: int) -> bool:
        """Delete onboarding state (called on completion).

        Args:
            telegram_id: Telegram user ID.

        Returns:
            True if deleted, False if not found.
        """
        stmt = delete(OnboardingState).where(
            OnboardingState.telegram_id == telegram_id
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0


class VenueCacheRepository:
    """Repository for VenueCache operations.

    Handles venue cache with composite key (city, scene) and expiration.
    Uses upsert for cache updates and automatic expiration.

    Note: Does NOT inherit from BaseRepository because:
    - Lookup by composite key (city, scene), not UUID
    - Cache semantics with expiration
    """

    # Default cache TTL: 30 days
    DEFAULT_TTL_DAYS = 30

    def __init__(self, session: AsyncSession) -> None:
        """Initialize VenueCacheRepository.

        Args:
            session: Async SQLAlchemy session.
        """
        self._session = session

    @property
    def session(self) -> AsyncSession:
        """Access the database session."""
        return self._session

    async def get_or_none(
        self,
        city: str,
        scene: str,
    ) -> VenueCache | None:
        """Get cached venues for city+scene, None if not found or expired.

        Args:
            city: Normalized city name (lowercase).
            scene: Social scene type (lowercase).

        Returns:
            VenueCache if found and not expired, None otherwise.
        """
        stmt = select(VenueCache).where(
            VenueCache.city == city.lower(),
            VenueCache.scene == scene.lower(),
            VenueCache.expires_at > utc_now(),  # Not expired
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def store(
        self,
        city: str,
        scene: str,
        venues: list[dict[str, Any]],
        ttl_days: int | None = None,
    ) -> VenueCache:
        """Store or update venue cache.

        Uses upsert to handle existing entries for same (city, scene).

        Args:
            city: Normalized city name.
            scene: Social scene type.
            venues: List of venue dicts from Firecrawl.
            ttl_days: Optional custom TTL in days (default 30).

        Returns:
            Created/updated VenueCache entry.
        """
        now = utc_now()
        ttl = ttl_days if ttl_days is not None else self.DEFAULT_TTL_DAYS
        expires = now + timedelta(days=ttl)

        stmt = insert(VenueCache).values(
            city=city.lower(),
            scene=scene.lower(),
            venues=venues,
            fetched_at=now,
            expires_at=expires,
        ).on_conflict_do_update(
            constraint="uq_venue_cache_city_scene",
            set_={
                "venues": venues,
                "fetched_at": now,
                "expires_at": expires,
            },
        ).returning(VenueCache)

        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def cleanup_expired(self) -> int:
        """Delete all expired cache entries.

        Called by maintenance job to clean up stale cache.

        Returns:
            Number of expired entries deleted.
        """
        stmt = delete(VenueCache).where(
            VenueCache.expires_at <= utc_now()
        )
        result = await self._session.execute(stmt)
        return result.rowcount
