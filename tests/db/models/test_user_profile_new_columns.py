"""Tests for UserProfile new columns added in Spec 213 PR 213-2.

T1.6.R — TDD RED phase tests for name, occupation, age columns on UserProfile.

Acceptance criteria:
- UserProfile accepts name (str|None), occupation (str|None), age (int|None)
- Fields are readable after instantiation
- Uses AsyncMock session pattern — NO live DB
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from unittest.mock import MagicMock, AsyncMock


class TestUserProfileNewColumns:
    """Tests for Spec 213 new columns on UserProfile (T1.6)."""

    def test_user_profile_has_name_column(self):
        """UserProfile has a name column mapped as String(100), nullable."""
        from sqlalchemy import inspect

        from nikita.db.models.profile import UserProfile

        mapper = inspect(UserProfile)
        column_names = {c.name for c in mapper.columns}
        assert "name" in column_names, "UserProfile must have 'name' column"

    def test_user_profile_has_occupation_column(self):
        """UserProfile has an occupation column mapped as String(100), nullable."""
        from sqlalchemy import inspect

        from nikita.db.models.profile import UserProfile

        mapper = inspect(UserProfile)
        column_names = {c.name for c in mapper.columns}
        assert "occupation" in column_names, "UserProfile must have 'occupation' column"

    def test_user_profile_has_age_column(self):
        """UserProfile has an age column mapped as SmallInteger, nullable."""
        from sqlalchemy import inspect

        from nikita.db.models.profile import UserProfile

        mapper = inspect(UserProfile)
        column_names = {c.name for c in mapper.columns}
        assert "age" in column_names, "UserProfile must have 'age' column"

    def test_user_profile_new_fields_readable(self):
        """Instantiate UserProfile with name, occupation, age — assert fields readable."""
        from nikita.db.models.profile import UserProfile

        user_id = uuid4()
        profile = UserProfile(
            id=user_id,
            location_city="Berlin",
            drug_tolerance=3,
            name="Anna",
            occupation="designer",
            age=29,
        )

        assert profile.name == "Anna"
        assert profile.occupation == "designer"
        assert profile.age == 29

    def test_user_profile_new_fields_default_to_none(self):
        """UserProfile name, occupation, age default to None when not provided."""
        from nikita.db.models.profile import UserProfile

        profile = UserProfile(
            id=uuid4(),
            drug_tolerance=3,
        )

        assert profile.name is None
        assert profile.occupation is None
        assert profile.age is None

    def test_user_profile_name_column_type_is_string(self):
        """name column is of type String (not Text or Integer)."""
        from sqlalchemy import inspect, String

        from nikita.db.models.profile import UserProfile

        mapper = inspect(UserProfile)
        name_col = next(c for c in mapper.columns if c.name == "name")
        assert isinstance(name_col.type, String), (
            f"Expected String type, got {type(name_col.type)}"
        )

    def test_user_profile_age_column_type_is_smallinteger(self):
        """age column is of type SmallInteger (not Integer) per FR-1b spec."""
        from sqlalchemy import inspect
        from sqlalchemy import SmallInteger

        from nikita.db.models.profile import UserProfile

        mapper = inspect(UserProfile)
        age_col = next(c for c in mapper.columns if c.name == "age")
        assert isinstance(age_col.type, SmallInteger), (
            f"Expected SmallInteger type, got {type(age_col.type)}"
        )

    def test_user_profile_new_columns_are_nullable(self):
        """name, occupation, age columns are nullable (optional fields)."""
        from sqlalchemy import inspect

        from nikita.db.models.profile import UserProfile

        mapper = inspect(UserProfile)
        columns = {c.name: c for c in mapper.columns}

        assert columns["name"].nullable is True, "name must be nullable"
        assert columns["occupation"].nullable is True, "occupation must be nullable"
        assert columns["age"].nullable is True, "age must be nullable"
