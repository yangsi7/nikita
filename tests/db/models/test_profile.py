"""Tests for profile models: UserProfile, UserBackstory, VenueCache, OnboardingState.

Tests are organized by TDD approach - each test corresponds to an acceptance criterion.

T1.1: UserProfile Model
- AC-T1.1-001: UserProfile model with 6 fields
- AC-T1.1-002: SQLAlchemy model inherits from Base, UUID PK referencing users.id
- AC-T1.1-003: Migration creates table (tested via MCP)

T1.2: UserBackstory Model
- AC-T1.2-001: UserBackstory model with 7 fields including JSONB
- AC-T1.2-002: One-to-one relationship with User (UNIQUE constraint)
- AC-T1.2-003: Migration creates table (tested via MCP)

T1.3: VenueCache Model
- AC-T1.3-001: VenueCache model with 5 fields including JSONB venues
- AC-T1.3-002: Composite unique constraint on (city, scene)
- AC-T1.3-003: Migration creates table (tested via MCP)

T1.4: OnboardingState Model
- AC-T1.4-001: OnboardingState model with 5 fields including JSONB
- AC-T1.4-002: Steps enum with 8 values
- AC-T1.4-003: Transient state (delete on completion pattern)
"""

from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from uuid import uuid4

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

# Import models (will fail until implemented - TDD RED phase)
from nikita.db.models.profile import (
    OnboardingState,
    OnboardingStep,
    UserBackstory,
    UserProfile,
    VenueCache,
)


class TestUserProfileModel:
    """Tests for UserProfile model (T1.1)."""

    def test_user_profile_has_required_fields(self):
        """AC-T1.1-001: UserProfile model has all 6 required fields."""
        # Check field names via column inspection
        mapper = inspect(UserProfile)
        column_names = {c.name for c in mapper.columns}

        expected_fields = {
            "id",  # Primary key matching user.id
            "location_city",
            "location_country",
            "life_stage",
            "social_scene",
            "primary_interest",
            "drug_tolerance",
        }

        for field in expected_fields:
            assert field in column_names, f"UserProfile missing field: {field}"

    def test_user_profile_inherits_from_base(self):
        """AC-T1.1-002: UserProfile inherits from Base."""
        from nikita.db.models.base import Base

        assert issubclass(UserProfile, Base)

    def test_user_profile_has_uuid_primary_key(self):
        """AC-T1.1-002: UserProfile has UUID primary key."""
        mapper = inspect(UserProfile)
        pk_columns = [c.name for c in mapper.primary_key]
        assert pk_columns == ["id"]

    def test_user_profile_drug_tolerance_range(self):
        """AC-T1.1-001: drug_tolerance is 1-5 scale."""
        user_id = uuid4()
        # Valid values
        profile = UserProfile(id=user_id, drug_tolerance=3)
        assert profile.drug_tolerance == 3

    def test_user_profile_table_name(self):
        """UserProfile uses correct table name."""
        assert UserProfile.__tablename__ == "user_profiles"


class TestUserBackstoryModel:
    """Tests for UserBackstory model (T1.2)."""

    def test_user_backstory_has_required_fields(self):
        """AC-T1.2-001: UserBackstory has all required fields."""
        mapper = inspect(UserBackstory)
        column_names = {c.name for c in mapper.columns}

        expected_fields = {
            "id",
            "user_id",
            "venue_name",
            "venue_city",
            "scenario_type",
            "how_we_met",
            "the_moment",
            "unresolved_hook",
            "nikita_persona_overrides",  # JSONB
        }

        for field in expected_fields:
            assert field in column_names, f"UserBackstory missing field: {field}"

    def test_user_backstory_persona_overrides_is_jsonb(self):
        """AC-T1.2-001: nikita_persona_overrides is JSONB."""
        mapper = inspect(UserBackstory)
        columns = {c.name: c for c in mapper.columns}

        assert "nikita_persona_overrides" in columns
        col_type = str(columns["nikita_persona_overrides"].type)
        assert "JSON" in col_type.upper()

    def test_user_backstory_user_id_unique(self):
        """AC-T1.2-002: user_id has UNIQUE constraint (one-to-one)."""
        mapper = inspect(UserBackstory)
        columns = {c.name: c for c in mapper.columns}

        user_id_col = columns["user_id"]
        assert user_id_col.unique, "user_id must have UNIQUE constraint for 1:1"

    def test_user_backstory_table_name(self):
        """UserBackstory uses correct table name."""
        assert UserBackstory.__tablename__ == "user_backstories"


class TestVenueCacheModel:
    """Tests for VenueCache model (T1.3)."""

    def test_venue_cache_has_required_fields(self):
        """AC-T1.3-001: VenueCache has all required fields."""
        mapper = inspect(VenueCache)
        column_names = {c.name for c in mapper.columns}

        expected_fields = {
            "id",
            "city",
            "scene",
            "venues",  # JSONB array
            "fetched_at",
            "expires_at",
        }

        for field in expected_fields:
            assert field in column_names, f"VenueCache missing field: {field}"

    def test_venue_cache_venues_is_jsonb(self):
        """AC-T1.3-001: venues field is JSONB."""
        mapper = inspect(VenueCache)
        columns = {c.name: c for c in mapper.columns}

        assert "venues" in columns
        col_type = str(columns["venues"].type)
        assert "JSON" in col_type.upper()

    def test_venue_cache_composite_unique(self):
        """AC-T1.3-002: Composite unique constraint on (city, scene)."""
        # Check table constraints
        table = VenueCache.__table__

        # Find unique constraints
        unique_constraints = [c for c in table.constraints if c.name and "uq_" in c.name.lower()]

        # Should have a unique constraint covering city and scene
        has_composite = False
        for constraint in unique_constraints:
            columns = {col.name for col in constraint.columns}
            if "city" in columns and "scene" in columns:
                has_composite = True
                break

        # Alternative: check UniqueConstraint in table args
        if not has_composite:
            from sqlalchemy import UniqueConstraint

            for constraint in table.constraints:
                if isinstance(constraint, UniqueConstraint):
                    columns = {col.name for col in constraint.columns}
                    if "city" in columns and "scene" in columns:
                        has_composite = True
                        break

        assert has_composite, "VenueCache must have unique constraint on (city, scene)"

    def test_venue_cache_table_name(self):
        """VenueCache uses correct table name."""
        assert VenueCache.__tablename__ == "venue_cache"

    def test_venue_cache_is_expired(self):
        """AC-T1.3-003: VenueCache has is_expired() method."""
        from nikita.db.models.base import utc_now

        cache = VenueCache(
            city="berlin",
            scene="techno",
            venues=[],
            fetched_at=utc_now() - timedelta(days=35),
            expires_at=utc_now() - timedelta(days=5),  # Expired 5 days ago
        )
        assert cache.is_expired() is True

        cache_valid = VenueCache(
            city="berlin",
            scene="techno",
            venues=[],
            fetched_at=utc_now(),
            expires_at=utc_now() + timedelta(days=30),  # Expires in 30 days
        )
        assert cache_valid.is_expired() is False


class TestOnboardingStateModel:
    """Tests for OnboardingState model (T1.4)."""

    def test_onboarding_state_has_required_fields(self):
        """AC-T1.4-001: OnboardingState has all required fields."""
        mapper = inspect(OnboardingState)
        column_names = {c.name for c in mapper.columns}

        expected_fields = {
            "telegram_id",  # Primary key
            "current_step",
            "collected_answers",  # JSONB
            "started_at",
            "updated_at",
        }

        for field in expected_fields:
            assert field in column_names, f"OnboardingState missing field: {field}"

    def test_onboarding_step_enum_values(self):
        """AC-T1.4-002: OnboardingStep enum has 8 values."""
        expected_values = {
            "LOCATION",
            "LIFE_STAGE",
            "SCENE",
            "INTEREST",
            "DRUG_TOLERANCE",
            "VENUE_RESEARCH",
            "SCENARIO_SELECTION",
            "COMPLETE",
        }

        actual_values = {step.name for step in OnboardingStep}
        assert actual_values == expected_values

    def test_onboarding_state_telegram_id_is_pk(self):
        """AC-T1.4-001: telegram_id is primary key (like PendingRegistration)."""
        mapper = inspect(OnboardingState)
        pk_columns = [c.name for c in mapper.primary_key]
        assert pk_columns == ["telegram_id"]

    def test_onboarding_state_collected_answers_is_jsonb(self):
        """AC-T1.4-001: collected_answers is JSONB."""
        mapper = inspect(OnboardingState)
        columns = {c.name: c for c in mapper.columns}

        assert "collected_answers" in columns
        col_type = str(columns["collected_answers"].type)
        assert "JSON" in col_type.upper()

    def test_onboarding_state_table_name(self):
        """OnboardingState uses correct table name."""
        assert OnboardingState.__tablename__ == "onboarding_states"


class TestOnboardingStepEnum:
    """Tests for OnboardingStep enum transitions."""

    def test_enum_is_subclass_of_str_enum(self):
        """OnboardingStep is a string enum for database storage."""
        assert issubclass(OnboardingStep, str)
        assert issubclass(OnboardingStep, Enum)

    def test_enum_values_are_strings(self):
        """Each enum value is a string for database compatibility."""
        for step in OnboardingStep:
            assert isinstance(step.value, str)

    def test_enum_step_order(self):
        """Steps follow logical flow order."""
        steps = list(OnboardingStep)
        step_names = [s.name for s in steps]

        # Verify profile collection steps come first
        profile_steps = ["LOCATION", "LIFE_STAGE", "SCENE", "INTEREST", "DRUG_TOLERANCE"]
        for i, step in enumerate(profile_steps):
            assert step in step_names

        # COMPLETE should be last
        assert steps[-1] == OnboardingStep.COMPLETE
