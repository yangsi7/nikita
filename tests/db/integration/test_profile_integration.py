"""Integration tests for profile-related repositories.

Moved from tests/db/repositories/test_profile_repository.py to consolidate
integration tests that require real database connectivity.

Tests for:
- ProfileRepository integration
- BackstoryRepository integration
- OnboardingStateRepository integration
- VenueCacheRepository integration
"""

from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.base import utc_now
from nikita.db.models.profile import (
    OnboardingStep,
    VenueCache,
)
from nikita.db.repositories.profile_repository import (
    BackstoryRepository,
    OnboardingStateRepository,
    ProfileRepository,
    VenueCacheRepository,
)


@pytest.mark.asyncio
class TestProfileRepositoryIntegration:
    """Integration tests for ProfileRepository with database."""

    async def test_create_and_get_profile(self, session: AsyncSession):
        """Test create_profile() and get_by_user_id() work together."""
        from nikita.db.repositories.user_repository import UserRepository

        # First create a user (required for FK relationship)
        user_repo = UserRepository(session)
        user_id = uuid4()
        user = await user_repo.create_with_metrics(user_id=user_id, telegram_id=123456789)

        # Now create profile
        profile_repo = ProfileRepository(session)
        profile = await profile_repo.create_profile(
            user_id=user_id,
            location_city="Berlin",
            location_country="Germany",
            life_stage="tech",
            social_scene="techno",
            primary_interest="electronic music",
            drug_tolerance=4,
        )

        # Verify creation
        assert profile is not None
        assert profile.id == user_id
        assert profile.location_city == "Berlin"
        assert profile.drug_tolerance == 4

        # Verify retrieval
        retrieved = await profile_repo.get_by_user_id(user_id)
        assert retrieved is not None
        assert retrieved.location_city == "Berlin"

    async def test_update_profile(self, session: AsyncSession):
        """Test profile update works correctly."""
        from nikita.db.repositories.user_repository import UserRepository

        # Setup user and profile
        user_repo = UserRepository(session)
        user_id = uuid4()
        await user_repo.create_with_metrics(user_id=user_id, telegram_id=123456790)

        profile_repo = ProfileRepository(session)
        profile = await profile_repo.create_profile(
            user_id=user_id,
            location_city="New York",
        )

        # Update profile
        profile.location_city = "Los Angeles"
        profile.life_stage = "artist"
        updated = await profile_repo.update(profile)

        # Verify update
        assert updated.location_city == "Los Angeles"
        assert updated.life_stage == "artist"


@pytest.mark.asyncio
class TestBackstoryRepositoryIntegration:
    """Integration tests for BackstoryRepository with database."""

    async def test_create_and_get_backstory(self, session: AsyncSession):
        """Test create() and get_by_user_id() work together."""
        from nikita.db.repositories.user_repository import UserRepository

        # Setup user
        user_repo = UserRepository(session)
        user_id = uuid4()
        await user_repo.create_with_metrics(user_id=user_id, telegram_id=123456791)

        # Create backstory
        backstory_repo = BackstoryRepository(session)
        backstory = await backstory_repo.create(
            user_id=user_id,
            venue_name="Berghain",
            venue_city="Berlin",
            scenario_type="romantic",
            how_we_met="Met at the bar during sunrise set",
            the_moment="Locked eyes during the drop",
            unresolved_hook="Never got your number",
            nikita_persona_overrides={"occupation": "DJ", "vice_intensity": 5},
        )

        # Verify creation
        assert backstory is not None
        assert backstory.user_id == user_id
        assert backstory.venue_name == "Berghain"
        assert backstory.nikita_persona_overrides == {"occupation": "DJ", "vice_intensity": 5}

        # Verify retrieval
        retrieved = await backstory_repo.get_by_user_id(user_id)
        assert retrieved is not None
        assert retrieved.scenario_type == "romantic"


@pytest.mark.asyncio
class TestOnboardingStateRepositoryIntegration:
    """Integration tests for OnboardingStateRepository with database."""

    async def test_get_or_create_new(self, session: AsyncSession):
        """Test get_or_create() creates new state when none exists."""
        repo = OnboardingStateRepository(session)
        telegram_id = 987654321

        state = await repo.get_or_create(telegram_id)

        assert state is not None
        assert state.telegram_id == telegram_id
        assert state.current_step == OnboardingStep.LOCATION.value
        assert state.collected_answers == {}

    async def test_get_or_create_existing(self, session: AsyncSession):
        """Test get_or_create() returns existing state."""
        repo = OnboardingStateRepository(session)
        telegram_id = 987654322

        # Create initial state
        state1 = await repo.get_or_create(telegram_id)
        state1.collected_answers = {"location_city": "Tokyo"}
        await repo.update_step(telegram_id, OnboardingStep.LIFE_STAGE, state1.collected_answers)

        # Get again - should return existing
        state2 = await repo.get_or_create(telegram_id)

        assert state2.current_step == OnboardingStep.LIFE_STAGE.value
        assert state2.collected_answers == {"location_city": "Tokyo"}

    async def test_update_step(self, session: AsyncSession):
        """Test update_step() advances step and updates answers."""
        repo = OnboardingStateRepository(session)
        telegram_id = 987654323

        # Create initial state
        await repo.get_or_create(telegram_id)

        # Update to next step
        updated = await repo.update_step(
            telegram_id,
            OnboardingStep.SCENE,
            {"location_city": "Paris", "life_stage": "finance"},
        )

        assert updated.current_step == OnboardingStep.SCENE.value
        assert updated.collected_answers["life_stage"] == "finance"

    async def test_delete_state(self, session: AsyncSession):
        """Test delete() removes onboarding state."""
        repo = OnboardingStateRepository(session)
        telegram_id = 987654324

        # Create and verify
        await repo.get_or_create(telegram_id)

        # Delete
        deleted = await repo.delete(telegram_id)
        assert deleted is True

        # Verify gone - get_or_create should create new
        state = await repo.get_or_create(telegram_id)
        assert state.current_step == OnboardingStep.LOCATION.value

    async def test_delete_nonexistent(self, session: AsyncSession):
        """Test delete() returns False for non-existent state."""
        repo = OnboardingStateRepository(session)

        deleted = await repo.delete(999999999)
        assert deleted is False


@pytest.mark.asyncio
class TestVenueCacheRepositoryIntegration:
    """Integration tests for VenueCacheRepository with database."""

    async def test_store_and_get(self, session: AsyncSession):
        """Test store() and get_or_none() work together."""
        repo = VenueCacheRepository(session)

        venues = [
            {"name": "Berghain", "description": "Legendary techno club", "vibe": "dark techno"},
            {"name": "Watergate", "description": "Riverside views", "vibe": "house"},
        ]

        # Store venues
        cache = await repo.store(city="berlin", scene="techno", venues=venues)

        assert cache is not None
        assert cache.city == "berlin"
        assert cache.scene == "techno"
        assert len(cache.venues) == 2

        # Retrieve
        retrieved = await repo.get_or_none(city="berlin", scene="techno")
        assert retrieved is not None
        assert retrieved.venues[0]["name"] == "Berghain"

    async def test_get_nonexistent_returns_none(self, session: AsyncSession):
        """Test get_or_none() returns None for missing cache."""
        repo = VenueCacheRepository(session)

        result = await repo.get_or_none(city="nonexistent", scene="unknown")
        assert result is None

    async def test_store_upserts_existing(self, session: AsyncSession):
        """Test store() updates existing cache entry."""
        repo = VenueCacheRepository(session)

        # Store initial
        await repo.store(city="london", scene="dnb", venues=[{"name": "Fabric"}])

        # Store updated
        updated = await repo.store(
            city="london",
            scene="dnb",
            venues=[{"name": "Fabric"}, {"name": "Printworks"}],
        )

        assert len(updated.venues) == 2

        # Verify only one entry exists
        result = await repo.get_or_none(city="london", scene="dnb")
        assert len(result.venues) == 2

    async def test_cleanup_expired(self, session: AsyncSession):
        """Test cleanup_expired() removes old cache entries."""
        repo = VenueCacheRepository(session)

        # Create expired entry manually
        expired_cache = VenueCache(
            city="expired_city",
            scene="expired_scene",
            venues=[],
            fetched_at=utc_now() - timedelta(days=35),
            expires_at=utc_now() - timedelta(days=5),
        )
        session.add(expired_cache)
        await session.flush()

        # Cleanup
        deleted_count = await repo.cleanup_expired()

        assert deleted_count >= 1

        # Verify deleted
        result = await repo.get_or_none(city="expired_city", scene="expired_scene")
        assert result is None
