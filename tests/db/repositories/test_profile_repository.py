"""Unit tests for profile-related repositories.

Tests for:
- ProfileRepository (T1.5 AC-T1.5-001)
- BackstoryRepository (T1.5 AC-T1.5-002)
- OnboardingStateRepository (T1.5 AC-T1.5-003)
- VenueCacheRepository (implicit, for VenueCache operations)

All repositories follow TDD approach with acceptance criteria tests.

Note: Integration tests that require real database connectivity have been
moved to tests/db/integration/test_profile_integration.py
"""

import pytest

from nikita.db.repositories.profile_repository import (
    BackstoryRepository,
    OnboardingStateRepository,
    ProfileRepository,
    VenueCacheRepository,
)


class TestProfileRepository:
    """Tests for ProfileRepository (AC-T1.5-001)."""

    def test_profile_repository_has_required_methods(self):
        """AC-T1.5-001: ProfileRepository has create_profile(), get_by_user_id(), update()."""
        # Check method existence
        assert hasattr(ProfileRepository, "create_profile")
        assert hasattr(ProfileRepository, "get_by_user_id")
        assert hasattr(ProfileRepository, "update")

        # Methods should be callable
        assert callable(getattr(ProfileRepository, "create_profile"))
        assert callable(getattr(ProfileRepository, "get_by_user_id"))
        assert callable(getattr(ProfileRepository, "update"))

    def test_profile_repository_inherits_from_base(self):
        """AC-T1.5-004: ProfileRepository inherits from BaseRepository."""
        from nikita.db.repositories.base import BaseRepository

        assert issubclass(ProfileRepository, BaseRepository)


class TestBackstoryRepository:
    """Tests for BackstoryRepository (AC-T1.5-002)."""

    def test_backstory_repository_has_required_methods(self):
        """AC-T1.5-002: BackstoryRepository has create(), get_by_user_id(), update()."""
        # Check method existence
        assert hasattr(BackstoryRepository, "create")
        assert hasattr(BackstoryRepository, "get_by_user_id")
        assert hasattr(BackstoryRepository, "update")

        # Methods should be callable
        assert callable(getattr(BackstoryRepository, "create"))
        assert callable(getattr(BackstoryRepository, "get_by_user_id"))
        assert callable(getattr(BackstoryRepository, "update"))

    def test_backstory_repository_inherits_from_base(self):
        """AC-T1.5-004: BackstoryRepository inherits from BaseRepository."""
        from nikita.db.repositories.base import BaseRepository

        assert issubclass(BackstoryRepository, BaseRepository)


class TestOnboardingStateRepository:
    """Tests for OnboardingStateRepository (AC-T1.5-003)."""

    def test_onboarding_state_repository_has_required_methods(self):
        """AC-T1.5-003: OnboardingStateRepository has get_or_create(), update_step(), delete()."""
        # Check method existence
        assert hasattr(OnboardingStateRepository, "get_or_create")
        assert hasattr(OnboardingStateRepository, "update_step")
        assert hasattr(OnboardingStateRepository, "delete")

        # Methods should be callable
        assert callable(getattr(OnboardingStateRepository, "get_or_create"))
        assert callable(getattr(OnboardingStateRepository, "update_step"))
        assert callable(getattr(OnboardingStateRepository, "delete"))

    def test_onboarding_state_repository_does_not_inherit_base(self):
        """OnboardingStateRepository uses telegram_id (int) not UUID, so no BaseRepository."""
        from nikita.db.repositories.base import BaseRepository

        # Similar to PendingRegistrationRepository, this doesn't inherit from BaseRepository
        # because the primary key is telegram_id (int) not UUID
        # This is an implementation choice for consistency with the pattern
        assert not issubclass(OnboardingStateRepository, BaseRepository)


class TestVenueCacheRepository:
    """Tests for VenueCacheRepository."""

    def test_venue_cache_repository_has_required_methods(self):
        """VenueCacheRepository has get_or_none(), store(), and is_expired logic."""
        # Check method existence
        assert hasattr(VenueCacheRepository, "get_or_none")
        assert hasattr(VenueCacheRepository, "store")
        assert hasattr(VenueCacheRepository, "cleanup_expired")

        # Methods should be callable
        assert callable(getattr(VenueCacheRepository, "get_or_none"))
        assert callable(getattr(VenueCacheRepository, "store"))
        assert callable(getattr(VenueCacheRepository, "cleanup_expired"))

    def test_venue_cache_repository_does_not_inherit_base(self):
        """VenueCacheRepository uses composite key (city, scene), so no BaseRepository."""
        from nikita.db.repositories.base import BaseRepository

        # VenueCache lookup is by (city, scene) not UUID
        assert not issubclass(VenueCacheRepository, BaseRepository)
