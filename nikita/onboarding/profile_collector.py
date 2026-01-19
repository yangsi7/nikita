"""Profile Collection (Spec 028 Phase E).

Implements ProfileCollector for structured extraction and validation
of user profile data during voice onboarding.

Implements:
- AC-T018.1-4: ProfileCollector class
- AC-T019.1-4: Structured extraction
- AC-T020.1-4: Validation
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import UUID

from nikita.onboarding.models import PersonalityType, UserOnboardingProfile

logger = logging.getLogger(__name__)

# Location to timezone mapping
LOCATION_TIMEZONE_MAP = {
    # Major US cities
    "new york": "America/New_York",
    "los angeles": "America/Los_Angeles",
    "chicago": "America/Chicago",
    "houston": "America/Chicago",
    "phoenix": "America/Phoenix",
    "san francisco": "America/Los_Angeles",
    "seattle": "America/Los_Angeles",
    "miami": "America/New_York",
    "boston": "America/New_York",
    "denver": "America/Denver",
    # European cities
    "london": "Europe/London",
    "paris": "Europe/Paris",
    "berlin": "Europe/Berlin",
    "zurich": "Europe/Zurich",
    "geneva": "Europe/Zurich",
    "amsterdam": "Europe/Amsterdam",
    "madrid": "Europe/Madrid",
    "rome": "Europe/Rome",
    "vienna": "Europe/Vienna",
    "munich": "Europe/Berlin",
    # Asian cities
    "tokyo": "Asia/Tokyo",
    "singapore": "Asia/Singapore",
    "hong kong": "Asia/Hong_Kong",
    "seoul": "Asia/Seoul",
    "shanghai": "Asia/Shanghai",
    "beijing": "Asia/Shanghai",
    "sydney": "Australia/Sydney",
    "mumbai": "Asia/Kolkata",
    "dubai": "Asia/Dubai",
    # Countries
    "usa": "America/New_York",
    "united states": "America/New_York",
    "uk": "Europe/London",
    "united kingdom": "Europe/London",
    "france": "Europe/Paris",
    "germany": "Europe/Berlin",
    "switzerland": "Europe/Zurich",
    "japan": "Asia/Tokyo",
    "china": "Asia/Shanghai",
    "india": "Asia/Kolkata",
    "australia": "Australia/Sydney",
}

# Known timezones (subset for validation)
KNOWN_TIMEZONES = {
    "UTC",
    "America/New_York",
    "America/Chicago",
    "America/Denver",
    "America/Phoenix",
    "America/Los_Angeles",
    "America/Anchorage",
    "Pacific/Honolulu",
    "Europe/London",
    "Europe/Paris",
    "Europe/Berlin",
    "Europe/Zurich",
    "Europe/Amsterdam",
    "Europe/Madrid",
    "Europe/Rome",
    "Europe/Vienna",
    "Europe/Moscow",
    "Asia/Tokyo",
    "Asia/Seoul",
    "Asia/Shanghai",
    "Asia/Hong_Kong",
    "Asia/Singapore",
    "Asia/Kolkata",
    "Asia/Dubai",
    "Australia/Sydney",
    "Australia/Melbourne",
    "Pacific/Auckland",
}

# Hobby keywords for extraction
HOBBY_KEYWORDS = {
    "hiking", "reading", "cooking", "gaming", "music", "travel", "photography",
    "writing", "painting", "drawing", "yoga", "meditation", "running", "cycling",
    "swimming", "fishing", "camping", "gardening", "dancing", "singing",
    "movies", "tv", "anime", "sports", "basketball", "soccer", "tennis",
    "golf", "skiing", "snowboarding", "surfing", "climbing", "baking",
    "crafts", "knitting", "woodworking", "coding", "programming", "chess",
    "podcasts", "volunteering", "fitness", "gym", "working out",
}

# Introvert/extrovert indicators
INTROVERT_INDICATORS = {
    "alone", "quiet", "home", "book", "solitude", "peaceful", "small group",
    "introverted", "introvert", "shy", "reserved", "private", "prefer my own",
    "recharge alone", "need time alone", "don't like crowds",
}

EXTROVERT_INDICATORS = {
    "party", "parties", "social", "people", "meeting", "crowd", "events",
    "extroverted", "extrovert", "outgoing", "love people", "energized by",
    "group activities", "networking", "making friends", "hanging out",
}


class ProfileField(str, Enum):
    """Fields that can be collected for a user profile."""

    TIMEZONE = "timezone"
    OCCUPATION = "occupation"
    HOBBIES = "hobbies"
    PERSONALITY_TYPE = "personality_type"
    HANGOUT_SPOTS = "hangout_spots"
    DARKNESS_LEVEL = "darkness_level"
    PACING_WEEKS = "pacing_weeks"
    CONVERSATION_STYLE = "conversation_style"


# Required fields for a complete profile
REQUIRED_FIELDS = {
    ProfileField.TIMEZONE,
    ProfileField.DARKNESS_LEVEL,
    ProfileField.PACING_WEEKS,
}


@dataclass
class CollectionResult:
    """Result of a profile field collection attempt."""

    success: bool
    field: ProfileField
    value: Any
    error: str | None = None


class TimezoneValidator:
    """Validates timezone strings."""

    def is_valid(self, timezone: str) -> bool:
        """Check if timezone is in known list."""
        if not timezone:
            return False
        return timezone in KNOWN_TIMEZONES

    def get_known_timezones(self) -> set[str]:
        """Return set of known timezone strings."""
        return KNOWN_TIMEZONES.copy()


class ProfileCollector:
    """Collects and validates user profile data during onboarding.

    Manages the collection of profile fields during voice onboarding,
    with validation and structured extraction capabilities.
    """

    def __init__(self) -> None:
        """Initialize the collector."""
        self._profiles: dict[str, UserOnboardingProfile] = {}
        self._timezone_validator = TimezoneValidator()

    def collect(
        self, user_id: UUID, field: ProfileField, value: Any
    ) -> CollectionResult:
        """
        Collect and store a profile field value.

        AC-T018.2: collect() method for each field

        Args:
            user_id: User's UUID
            field: Field to collect
            value: Value to store

        Returns:
            CollectionResult with success status
        """
        user_key = str(user_id)

        # Get or create profile
        if user_key not in self._profiles:
            self._profiles[user_key] = UserOnboardingProfile()

        profile = self._profiles[user_key]

        # Validate and process based on field type
        try:
            processed_value = self._validate_and_process(field, value)
            self._set_field(profile, field, processed_value)

            logger.debug(f"Collected {field.value} for user {user_id}: {processed_value}")

            return CollectionResult(
                success=True,
                field=field,
                value=processed_value,
            )
        except ValueError as e:
            return CollectionResult(
                success=False,
                field=field,
                value=value,
                error=str(e),
            )

    def _validate_and_process(self, field: ProfileField, value: Any) -> Any:
        """Validate and process a field value."""
        # Handle None and empty string
        if value is None:
            return None

        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None

        # Field-specific validation
        if field == ProfileField.DARKNESS_LEVEL:
            if not isinstance(value, int) or not 1 <= value <= 5:
                raise ValueError("darkness_level must be between 1-5")
            return value

        if field == ProfileField.PACING_WEEKS:
            if value not in (4, 8):
                raise ValueError("pacing_weeks must be 4 or 8")
            return value

        if field == ProfileField.HOBBIES:
            if isinstance(value, list):
                # Filter empty entries and strip whitespace
                return [h.strip() for h in value if h and h.strip()]
            return value

        if field == ProfileField.HANGOUT_SPOTS:
            if isinstance(value, list):
                return [s.strip() for s in value if s and s.strip()]
            return value

        return value

    def _set_field(self, profile: UserOnboardingProfile, field: ProfileField, value: Any) -> None:
        """Set a field value on the profile."""
        if field == ProfileField.TIMEZONE:
            profile.timezone = value
        elif field == ProfileField.OCCUPATION:
            profile.occupation = value
        elif field == ProfileField.HOBBIES:
            profile.hobbies = value if value else []
        elif field == ProfileField.PERSONALITY_TYPE:
            profile.personality_type = value
        elif field == ProfileField.HANGOUT_SPOTS:
            profile.hangout_spots = value if value else []
        elif field == ProfileField.DARKNESS_LEVEL:
            profile.darkness_level = value if value else 3
        elif field == ProfileField.PACING_WEEKS:
            profile.pacing_weeks = value if value else 4
        elif field == ProfileField.CONVERSATION_STYLE:
            profile.conversation_style = value

    def get_profile(self, user_id: UUID) -> UserOnboardingProfile:
        """
        Get the complete profile for a user.

        AC-T018.3: get_profile() returns complete profile

        Args:
            user_id: User's UUID

        Returns:
            UserOnboardingProfile with all collected data
        """
        user_key = str(user_id)
        if user_key not in self._profiles:
            return UserOnboardingProfile()
        return self._profiles[user_key]

    def is_complete(self, user_id: UUID) -> bool:
        """Check if profile has all required fields."""
        profile = self.get_profile(user_id)

        # Check required fields
        if profile.timezone is None:
            return False
        if profile.darkness_level is None or profile.darkness_level == 0:
            return False
        if profile.pacing_weeks is None or profile.pacing_weeks == 0:
            return False

        return True

    def get_missing_fields(self, user_id: UUID) -> set[ProfileField]:
        """Get set of missing required fields."""
        profile = self.get_profile(user_id)
        missing = set()

        if profile.timezone is None:
            missing.add(ProfileField.TIMEZONE)
        if profile.darkness_level is None or profile.darkness_level == 0:
            missing.add(ProfileField.DARKNESS_LEVEL)
        if profile.pacing_weeks is None or profile.pacing_weeks == 0:
            missing.add(ProfileField.PACING_WEEKS)

        return missing

    def get_completeness_percentage(self, user_id: UUID) -> float:
        """Calculate profile completeness as percentage."""
        profile = self.get_profile(user_id)
        total_fields = 7  # All optional and required fields
        filled = 0

        if profile.timezone:
            filled += 1
        if profile.occupation:
            filled += 1
        if profile.hobbies:
            filled += 1
        if profile.personality_type:
            filled += 1
        if profile.hangout_spots:
            filled += 1
        if profile.darkness_level and profile.darkness_level > 0:
            filled += 1
        if profile.pacing_weeks and profile.pacing_weeks > 0:
            filled += 1

        return (filled / total_fields) * 100


def extract_timezone_from_location(location: str) -> str | None:
    """
    Extract timezone from location string.

    AC-T019.1: Extract timezone from location

    Args:
        location: City or country name

    Returns:
        Timezone string or None if not found
    """
    if not location:
        return None

    location_lower = location.lower().strip()

    # Direct lookup
    if location_lower in LOCATION_TIMEZONE_MAP:
        return LOCATION_TIMEZONE_MAP[location_lower]

    # Partial match
    for loc, tz in LOCATION_TIMEZONE_MAP.items():
        if loc in location_lower or location_lower in loc:
            return tz

    return None


def extract_hobbies(text: str) -> list[str]:
    """
    Extract hobbies from natural language text.

    AC-T019.2: Extract hobbies as list

    Args:
        text: Free-form text mentioning hobbies

    Returns:
        List of extracted hobbies
    """
    if not text or not text.strip():
        return []

    text_lower = text.lower()
    found_hobbies = []

    # Split by common separators
    parts = re.split(r"[,;]|\band\b", text_lower)

    for part in parts:
        part = part.strip()
        # Check if part matches any hobby keyword
        for hobby in HOBBY_KEYWORDS:
            if hobby in part:
                found_hobbies.append(hobby)

    # Also check full text for multi-word hobbies
    if "working out" in text_lower and "working out" not in found_hobbies:
        found_hobbies.append("working out")

    return list(set(found_hobbies))  # Remove duplicates


def infer_personality_type(text: str) -> PersonalityType:
    """
    Infer personality type from conversation text.

    AC-T019.3: Infer personality type from conversation

    Args:
        text: Conversation or response text

    Returns:
        Inferred PersonalityType
    """
    if not text:
        return PersonalityType.AMBIVERT

    text_lower = text.lower()

    introvert_score = sum(1 for ind in INTROVERT_INDICATORS if ind in text_lower)
    extrovert_score = sum(1 for ind in EXTROVERT_INDICATORS if ind in text_lower)

    if introvert_score > extrovert_score and introvert_score >= 2:
        return PersonalityType.INTROVERT
    elif extrovert_score > introvert_score and extrovert_score >= 2:
        return PersonalityType.EXTROVERT
    else:
        return PersonalityType.AMBIVERT
