"""Phase E: Profile Collection tests (Spec 028).

Tests for ProfileCollector class and structured extraction.

Implements:
- AC-T018.1-4: ProfileCollector class
- AC-T019.1-4: Structured extraction
- AC-T020.1-4: Validation
- AC-T021.1-2: Coverage tests
"""

from uuid import uuid4

import pytest

from nikita.onboarding.models import PersonalityType, UserOnboardingProfile
from nikita.onboarding.profile_collector import (
    ProfileCollector,
    ProfileField,
    TimezoneValidator,
    extract_hobbies,
    extract_timezone_from_location,
    infer_personality_type,
)


class TestProfileCollector:
    """Tests for ProfileCollector class (T018)."""

    @pytest.fixture
    def collector(self) -> ProfileCollector:
        """Create collector instance."""
        return ProfileCollector()

    def test_collect_single_field(self, collector: ProfileCollector) -> None:
        """AC-T018.2: collect() method stores single field."""
        user_id = uuid4()

        result = collector.collect(user_id, ProfileField.TIMEZONE, "America/New_York")

        assert result.success is True
        profile = collector.get_profile(user_id)
        assert profile.timezone == "America/New_York"

    def test_collect_multiple_fields(self, collector: ProfileCollector) -> None:
        """AC-T018.2: collect() works for multiple fields."""
        user_id = uuid4()

        collector.collect(user_id, ProfileField.TIMEZONE, "Europe/Zurich")
        collector.collect(user_id, ProfileField.OCCUPATION, "Software Engineer")
        collector.collect(user_id, ProfileField.HOBBIES, ["coding", "hiking"])

        profile = collector.get_profile(user_id)
        assert profile.timezone == "Europe/Zurich"
        assert profile.occupation == "Software Engineer"
        assert profile.hobbies == ["coding", "hiking"]

    def test_get_profile_new_user(self, collector: ProfileCollector) -> None:
        """AC-T018.3: get_profile() returns empty profile for new user."""
        user_id = uuid4()

        profile = collector.get_profile(user_id)

        assert isinstance(profile, UserOnboardingProfile)
        assert profile.timezone is None
        assert profile.hobbies == []

    def test_get_profile_returns_complete_profile(self, collector: ProfileCollector) -> None:
        """AC-T018.3: get_profile() returns all collected data."""
        user_id = uuid4()

        collector.collect(user_id, ProfileField.TIMEZONE, "Asia/Tokyo")
        collector.collect(user_id, ProfileField.OCCUPATION, "Teacher")
        collector.collect(user_id, ProfileField.HOBBIES, ["reading", "gardening"])
        collector.collect(user_id, ProfileField.PERSONALITY_TYPE, PersonalityType.INTROVERT)
        collector.collect(user_id, ProfileField.HANGOUT_SPOTS, ["library", "park"])
        collector.collect(user_id, ProfileField.DARKNESS_LEVEL, 3)
        collector.collect(user_id, ProfileField.PACING_WEEKS, 4)

        profile = collector.get_profile(user_id)

        assert profile.timezone == "Asia/Tokyo"
        assert profile.occupation == "Teacher"
        assert profile.hobbies == ["reading", "gardening"]
        assert profile.personality_type == PersonalityType.INTROVERT
        assert profile.hangout_spots == ["library", "park"]
        assert profile.darkness_level == 3
        assert profile.pacing_weeks == 4

    def test_collect_overwrites_existing(self, collector: ProfileCollector) -> None:
        """AC-T018.2: Subsequent collect() overwrites previous value."""
        user_id = uuid4()

        collector.collect(user_id, ProfileField.OCCUPATION, "Developer")
        collector.collect(user_id, ProfileField.OCCUPATION, "Manager")

        profile = collector.get_profile(user_id)
        assert profile.occupation == "Manager"

    def test_collect_returns_collection_result(self, collector: ProfileCollector) -> None:
        """AC-T018.2: collect() returns result with status."""
        user_id = uuid4()

        result = collector.collect(user_id, ProfileField.TIMEZONE, "America/Los_Angeles")

        assert result.success is True
        assert result.field == ProfileField.TIMEZONE
        assert result.value == "America/Los_Angeles"
        assert result.error is None

    def test_profiles_isolated_between_users(self, collector: ProfileCollector) -> None:
        """AC-T018.1: Each user has separate profile."""
        user1 = uuid4()
        user2 = uuid4()

        collector.collect(user1, ProfileField.OCCUPATION, "Doctor")
        collector.collect(user2, ProfileField.OCCUPATION, "Lawyer")

        assert collector.get_profile(user1).occupation == "Doctor"
        assert collector.get_profile(user2).occupation == "Lawyer"


class TestStructuredExtraction:
    """Tests for structured extraction (T019)."""

    def test_extract_timezone_from_city(self) -> None:
        """AC-T019.1: Extract timezone from city name."""
        assert extract_timezone_from_location("New York") == "America/New_York"
        assert extract_timezone_from_location("London") == "Europe/London"
        assert extract_timezone_from_location("Tokyo") == "Asia/Tokyo"

    def test_extract_timezone_from_country(self) -> None:
        """AC-T019.1: Extract timezone from country."""
        assert extract_timezone_from_location("Switzerland") == "Europe/Zurich"
        assert extract_timezone_from_location("Japan") == "Asia/Tokyo"
        assert extract_timezone_from_location("USA") == "America/New_York"

    def test_extract_timezone_case_insensitive(self) -> None:
        """AC-T019.1: Extraction is case-insensitive."""
        assert extract_timezone_from_location("NEW YORK") == "America/New_York"
        assert extract_timezone_from_location("london") == "Europe/London"

    def test_extract_timezone_unknown_location(self) -> None:
        """AC-T019.1: Unknown location returns None."""
        assert extract_timezone_from_location("Unknown City 12345") is None
        assert extract_timezone_from_location("") is None

    def test_extract_hobbies_from_text(self) -> None:
        """AC-T019.2: Extract hobbies as list from text."""
        hobbies = extract_hobbies("I like hiking, reading, and cooking")
        assert "hiking" in hobbies
        assert "reading" in hobbies
        assert "cooking" in hobbies

    def test_extract_hobbies_comma_separated(self) -> None:
        """AC-T019.2: Extract comma-separated hobbies."""
        hobbies = extract_hobbies("gaming, music, travel")
        assert len(hobbies) >= 3
        assert "gaming" in hobbies
        assert "music" in hobbies
        assert "travel" in hobbies

    def test_extract_hobbies_handles_and(self) -> None:
        """AC-T019.2: Handles 'and' separator."""
        hobbies = extract_hobbies("swimming and cycling")
        assert "swimming" in hobbies
        assert "cycling" in hobbies

    def test_extract_hobbies_empty_input(self) -> None:
        """AC-T019.2: Empty input returns empty list."""
        assert extract_hobbies("") == []
        assert extract_hobbies("   ") == []

    def test_infer_personality_introvert(self) -> None:
        """AC-T019.3: Infer introvert from conversation clues."""
        # Introvert indicators: prefer alone, quiet, small groups
        text = "I prefer spending time alone, reading books. I like quiet evenings at home."
        personality = infer_personality_type(text)
        assert personality == PersonalityType.INTROVERT

    def test_infer_personality_extrovert(self) -> None:
        """AC-T019.3: Infer extrovert from conversation clues."""
        # Extrovert indicators: parties, social, meeting people
        text = "I love going to parties and meeting new people. I'm always organizing social events."
        personality = infer_personality_type(text)
        assert personality == PersonalityType.EXTROVERT

    def test_infer_personality_ambivert_default(self) -> None:
        """AC-T019.3: Default to ambivert if unclear."""
        text = "I like both spending time with friends and having quiet time."
        personality = infer_personality_type(text)
        assert personality == PersonalityType.AMBIVERT

    def test_infer_personality_empty_text(self) -> None:
        """AC-T019.3: Empty text defaults to ambivert."""
        assert infer_personality_type("") == PersonalityType.AMBIVERT


class TestTimezoneValidator:
    """Tests for timezone validation (T020)."""

    @pytest.fixture
    def validator(self) -> TimezoneValidator:
        """Create validator instance."""
        return TimezoneValidator()

    def test_validate_known_timezone(self, validator: TimezoneValidator) -> None:
        """AC-T020.1: Known timezone passes validation."""
        assert validator.is_valid("America/New_York") is True
        assert validator.is_valid("Europe/London") is True
        assert validator.is_valid("Asia/Tokyo") is True
        assert validator.is_valid("UTC") is True

    def test_validate_unknown_timezone(self, validator: TimezoneValidator) -> None:
        """AC-T020.1: Unknown timezone fails validation."""
        assert validator.is_valid("Invalid/Timezone") is False
        assert validator.is_valid("Fake/City") is False
        assert validator.is_valid("") is False

    def test_get_known_timezones(self, validator: TimezoneValidator) -> None:
        """AC-T020.1: Can retrieve list of known timezones."""
        timezones = validator.get_known_timezones()
        assert "America/New_York" in timezones
        assert "Europe/London" in timezones
        assert len(timezones) >= 20  # Curated list of common timezones


class TestDarknessLevelValidation:
    """Tests for darkness level validation (T020)."""

    @pytest.fixture
    def collector(self) -> ProfileCollector:
        """Create collector instance."""
        return ProfileCollector()

    def test_valid_darkness_levels(self, collector: ProfileCollector) -> None:
        """AC-T020.2: Valid levels 1-5 accepted."""
        user_id = uuid4()
        for level in range(1, 6):
            result = collector.collect(user_id, ProfileField.DARKNESS_LEVEL, level)
            assert result.success is True, f"Level {level} should be valid"

    def test_invalid_darkness_level_too_low(self, collector: ProfileCollector) -> None:
        """AC-T020.2: Level 0 rejected."""
        user_id = uuid4()
        result = collector.collect(user_id, ProfileField.DARKNESS_LEVEL, 0)
        assert result.success is False
        assert "1-5" in result.error.lower() or "invalid" in result.error.lower()

    def test_invalid_darkness_level_too_high(self, collector: ProfileCollector) -> None:
        """AC-T020.2: Level 6+ rejected."""
        user_id = uuid4()
        result = collector.collect(user_id, ProfileField.DARKNESS_LEVEL, 6)
        assert result.success is False

    def test_invalid_darkness_level_negative(self, collector: ProfileCollector) -> None:
        """AC-T020.2: Negative level rejected."""
        user_id = uuid4()
        result = collector.collect(user_id, ProfileField.DARKNESS_LEVEL, -1)
        assert result.success is False


class TestPacingValidation:
    """Tests for pacing validation (T020)."""

    @pytest.fixture
    def collector(self) -> ProfileCollector:
        """Create collector instance."""
        return ProfileCollector()

    def test_valid_pacing_4_weeks(self, collector: ProfileCollector) -> None:
        """AC-T020.3: 4 weeks accepted."""
        user_id = uuid4()
        result = collector.collect(user_id, ProfileField.PACING_WEEKS, 4)
        assert result.success is True

    def test_valid_pacing_8_weeks(self, collector: ProfileCollector) -> None:
        """AC-T020.3: 8 weeks accepted."""
        user_id = uuid4()
        result = collector.collect(user_id, ProfileField.PACING_WEEKS, 8)
        assert result.success is True

    def test_invalid_pacing_other_values(self, collector: ProfileCollector) -> None:
        """AC-T020.3: Other values rejected."""
        user_id = uuid4()
        for invalid in [1, 2, 3, 5, 6, 7, 12]:
            result = collector.collect(user_id, ProfileField.PACING_WEEKS, invalid)
            assert result.success is False, f"Pacing {invalid} should be invalid"


class TestGracefulErrorHandling:
    """Tests for graceful error handling (T020)."""

    @pytest.fixture
    def collector(self) -> ProfileCollector:
        """Create collector instance."""
        return ProfileCollector()

    def test_collect_handles_none_value(self, collector: ProfileCollector) -> None:
        """AC-T020.3: None value handled gracefully."""
        user_id = uuid4()
        result = collector.collect(user_id, ProfileField.OCCUPATION, None)
        # None clears the field
        assert result.success is True

    def test_collect_handles_empty_string(self, collector: ProfileCollector) -> None:
        """AC-T020.3: Empty string handled gracefully."""
        user_id = uuid4()
        result = collector.collect(user_id, ProfileField.OCCUPATION, "")
        assert result.success is True

    def test_collect_trims_whitespace(self, collector: ProfileCollector) -> None:
        """AC-T020.3: Whitespace trimmed."""
        user_id = uuid4()
        collector.collect(user_id, ProfileField.OCCUPATION, "  Engineer  ")
        profile = collector.get_profile(user_id)
        assert profile.occupation == "Engineer"

    def test_collect_hobbies_filters_empty(self, collector: ProfileCollector) -> None:
        """AC-T020.3: Empty hobby entries filtered."""
        user_id = uuid4()
        collector.collect(user_id, ProfileField.HOBBIES, ["hiking", "", "  ", "reading"])
        profile = collector.get_profile(user_id)
        assert profile.hobbies == ["hiking", "reading"]


class TestProfileCompleteness:
    """Tests for profile completeness checking."""

    @pytest.fixture
    def collector(self) -> ProfileCollector:
        """Create collector instance."""
        return ProfileCollector()

    def test_is_complete_minimal(self, collector: ProfileCollector) -> None:
        """Profile with required fields is complete."""
        user_id = uuid4()
        collector.collect(user_id, ProfileField.TIMEZONE, "America/New_York")
        collector.collect(user_id, ProfileField.DARKNESS_LEVEL, 3)
        collector.collect(user_id, ProfileField.PACING_WEEKS, 4)

        assert collector.is_complete(user_id) is True

    def test_is_complete_missing_required(self, collector: ProfileCollector) -> None:
        """Profile missing required fields is incomplete."""
        user_id = uuid4()
        collector.collect(user_id, ProfileField.HOBBIES, ["hiking"])

        assert collector.is_complete(user_id) is False

    def test_get_missing_fields(self, collector: ProfileCollector) -> None:
        """Can retrieve list of missing required fields."""
        user_id = uuid4()
        # New user without any collections - only timezone is missing
        # (darkness_level and pacing_weeks have model defaults)
        missing = collector.get_missing_fields(user_id)
        assert ProfileField.TIMEZONE in missing

        # After setting timezone, no more required fields missing
        collector.collect(user_id, ProfileField.TIMEZONE, "America/New_York")
        missing = collector.get_missing_fields(user_id)
        assert ProfileField.TIMEZONE not in missing

    def test_completeness_percentage(self, collector: ProfileCollector) -> None:
        """Can calculate profile completeness percentage."""
        user_id = uuid4()
        collector.collect(user_id, ProfileField.TIMEZONE, "America/New_York")
        collector.collect(user_id, ProfileField.OCCUPATION, "Developer")
        collector.collect(user_id, ProfileField.HOBBIES, ["coding"])

        percentage = collector.get_completeness_percentage(user_id)
        assert 0 <= percentage <= 100
        assert percentage > 0  # At least some fields filled
