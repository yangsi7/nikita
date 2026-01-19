"""Phase A: Infrastructure tests (Spec 028).

Tests for onboarding models and module structure.

Implements:
- AC-T001.1: Module exists at nikita/onboarding/__init__.py
- AC-T001.2: Module structure matches spec
- AC-T002.1: UserOnboardingProfile Pydantic model
- AC-T002.2: Validation for darkness_level (1-5)
- AC-T002.3: Validation for pacing_weeks (4 or 8)
- AC-T002.4: Unit tests for models
- AC-T004.1: Test file exists
- AC-T004.2: Coverage > 85%
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from nikita.onboarding import (
    ConversationStyle,
    DarknessLevel,
    OnboardingStatus,
    PacingWeeks,
    PersonalityType,
    UserOnboardingProfile,
)
from nikita.onboarding.models import (
    OnboardingCallRequest,
    OnboardingCallResponse,
    ProfileFieldUpdate,
)


class TestModuleStructure:
    """Tests for module structure (T001)."""

    def test_module_exists(self) -> None:
        """AC-T001.1: Module exists at nikita/onboarding/__init__.py."""
        import nikita.onboarding

        assert nikita.onboarding is not None

    def test_module_exports_enums(self) -> None:
        """AC-T001.2: Module exports required enums."""
        from nikita.onboarding import (
            ConversationStyle,
            DarknessLevel,
            OnboardingStatus,
            PacingWeeks,
            PersonalityType,
        )

        assert OnboardingStatus.PENDING.value == "pending"
        assert PersonalityType.INTROVERT.value == "introvert"
        assert ConversationStyle.BALANCED.value == "balanced"
        assert DarknessLevel.DEFAULT == 3
        assert PacingWeeks.INTENSE == 4

    def test_module_exports_models(self) -> None:
        """AC-T001.2: Module exports required models."""
        from nikita.onboarding import UserOnboardingProfile

        profile = UserOnboardingProfile()
        assert profile.darkness_level == 3


class TestOnboardingStatus:
    """Tests for OnboardingStatus enum."""

    def test_all_statuses_defined(self) -> None:
        """Verify all expected statuses exist."""
        assert OnboardingStatus.PENDING.value == "pending"
        assert OnboardingStatus.CALL_SCHEDULED.value == "call_scheduled"
        assert OnboardingStatus.IN_CALL.value == "in_call"
        assert OnboardingStatus.COMPLETED.value == "completed"
        assert OnboardingStatus.SKIPPED.value == "skipped"
        assert OnboardingStatus.FAILED.value == "failed"

    def test_status_is_string_enum(self) -> None:
        """Verify status values are strings."""
        assert isinstance(OnboardingStatus.PENDING.value, str)


class TestPersonalityType:
    """Tests for PersonalityType enum."""

    def test_all_types_defined(self) -> None:
        """Verify all personality types exist."""
        assert PersonalityType.INTROVERT.value == "introvert"
        assert PersonalityType.EXTROVERT.value == "extrovert"
        assert PersonalityType.AMBIVERT.value == "ambivert"


class TestConversationStyle:
    """Tests for ConversationStyle enum."""

    def test_all_styles_defined(self) -> None:
        """Verify all conversation styles exist."""
        assert ConversationStyle.LISTENER.value == "listener"
        assert ConversationStyle.BALANCED.value == "balanced"
        assert ConversationStyle.SHARER.value == "sharer"


class TestDarknessLevel:
    """Tests for DarknessLevel enum."""

    def test_all_levels_defined(self) -> None:
        """Verify all darkness levels exist (1-5)."""
        assert DarknessLevel.VANILLA == 1
        assert DarknessLevel.LIGHT_EDGE == 2
        assert DarknessLevel.DEFAULT == 3
        assert DarknessLevel.DARK == 4
        assert DarknessLevel.FULL_NOIR == 5

    def test_levels_are_int(self) -> None:
        """Verify levels are integers."""
        assert isinstance(DarknessLevel.DEFAULT.value, int)


class TestPacingWeeks:
    """Tests for PacingWeeks enum."""

    def test_all_options_defined(self) -> None:
        """Verify pacing options exist (4 and 8)."""
        assert PacingWeeks.INTENSE == 4
        assert PacingWeeks.RELAXED == 8


class TestUserOnboardingProfile:
    """Tests for UserOnboardingProfile model (T002)."""

    def test_default_values(self) -> None:
        """AC-T002.1: Model has correct defaults."""
        profile = UserOnboardingProfile()

        assert profile.timezone is None
        assert profile.occupation is None
        assert profile.hobbies == []
        assert profile.personality_type is None
        assert profile.hangout_spots == []
        assert profile.darkness_level == 3
        assert profile.pacing_weeks == 4
        assert profile.conversation_style == ConversationStyle.BALANCED
        assert profile.onboarded_at is None
        assert profile.onboarding_call_id is None

    def test_full_profile_creation(self) -> None:
        """AC-T002.1: Model accepts all fields."""
        now = datetime.now()
        profile = UserOnboardingProfile(
            timezone="America/New_York",
            occupation="Software Engineer",
            hobbies=["gaming", "reading"],
            personality_type=PersonalityType.INTROVERT,
            hangout_spots=["coffee shops", "bookstores"],
            darkness_level=4,
            pacing_weeks=8,
            conversation_style=ConversationStyle.LISTENER,
            onboarded_at=now,
            onboarding_call_id="call_123",
        )

        assert profile.timezone == "America/New_York"
        assert profile.occupation == "Software Engineer"
        assert profile.hobbies == ["gaming", "reading"]
        assert profile.personality_type == PersonalityType.INTROVERT
        assert profile.hangout_spots == ["coffee shops", "bookstores"]
        assert profile.darkness_level == 4
        assert profile.pacing_weeks == 8
        assert profile.conversation_style == ConversationStyle.LISTENER
        assert profile.onboarded_at == now
        assert profile.onboarding_call_id == "call_123"

    def test_darkness_level_validation_valid_range(self) -> None:
        """AC-T002.2: Accepts darkness_level 1-5."""
        for level in range(1, 6):
            profile = UserOnboardingProfile(darkness_level=level)
            assert profile.darkness_level == level

    def test_darkness_level_validation_too_low(self) -> None:
        """AC-T002.2: Rejects darkness_level < 1."""
        with pytest.raises(ValidationError) as exc_info:
            UserOnboardingProfile(darkness_level=0)
        assert "darkness_level" in str(exc_info.value)

    def test_darkness_level_validation_too_high(self) -> None:
        """AC-T002.2: Rejects darkness_level > 5."""
        with pytest.raises(ValidationError) as exc_info:
            UserOnboardingProfile(darkness_level=6)
        assert "darkness_level" in str(exc_info.value)

    def test_pacing_weeks_validation_4(self) -> None:
        """AC-T002.3: Accepts pacing_weeks=4."""
        profile = UserOnboardingProfile(pacing_weeks=4)
        assert profile.pacing_weeks == 4

    def test_pacing_weeks_validation_8(self) -> None:
        """AC-T002.3: Accepts pacing_weeks=8."""
        profile = UserOnboardingProfile(pacing_weeks=8)
        assert profile.pacing_weeks == 8

    def test_pacing_weeks_validation_invalid(self) -> None:
        """AC-T002.3: Rejects pacing_weeks not in {4, 8}."""
        for invalid_weeks in [1, 2, 3, 5, 6, 7, 10, 12]:
            with pytest.raises(ValidationError) as exc_info:
                UserOnboardingProfile(pacing_weeks=invalid_weeks)
            assert "pacing_weeks must be 4 or 8" in str(exc_info.value)

    def test_is_complete_empty_profile(self) -> None:
        """is_complete returns False for empty profile."""
        profile = UserOnboardingProfile()
        assert profile.is_complete() is False

    def test_is_complete_partial_profile(self) -> None:
        """is_complete returns False when missing required fields."""
        profile = UserOnboardingProfile(timezone="America/New_York")
        assert profile.is_complete() is False

        profile = UserOnboardingProfile(personality_type=PersonalityType.INTROVERT)
        assert profile.is_complete() is False

    def test_is_complete_full_profile(self) -> None:
        """is_complete returns True when required fields are set."""
        profile = UserOnboardingProfile(
            timezone="America/New_York",
            personality_type=PersonalityType.INTROVERT,
        )
        assert profile.is_complete() is True

    def test_to_context_dict(self) -> None:
        """to_context_dict returns proper format for prompts."""
        profile = UserOnboardingProfile(
            timezone="America/New_York",
            occupation="Engineer",
            hobbies=["coding"],
            personality_type=PersonalityType.EXTROVERT,
            hangout_spots=["bars"],
            darkness_level=4,
            pacing_weeks=8,
            conversation_style=ConversationStyle.SHARER,
        )

        ctx = profile.to_context_dict()

        assert ctx["timezone"] == "America/New_York"
        assert ctx["occupation"] == "Engineer"
        assert ctx["hobbies"] == ["coding"]
        assert ctx["personality_type"] == "extrovert"
        assert ctx["hangout_spots"] == ["bars"]
        assert ctx["darkness_level"] == 4
        assert ctx["pacing_weeks"] == 8
        assert ctx["conversation_style"] == "sharer"

    def test_to_context_dict_empty_profile(self) -> None:
        """to_context_dict handles None values."""
        profile = UserOnboardingProfile()
        ctx = profile.to_context_dict()

        assert ctx["timezone"] is None
        assert ctx["occupation"] is None
        assert ctx["personality_type"] is None

    def test_get_darkness_description(self) -> None:
        """get_darkness_description returns readable text."""
        profile = UserOnboardingProfile(darkness_level=1)
        assert "Vanilla" in profile.get_darkness_description()

        profile = UserOnboardingProfile(darkness_level=3)
        assert "Default" in profile.get_darkness_description()

        profile = UserOnboardingProfile(darkness_level=5)
        assert "Full Noir" in profile.get_darkness_description()

    def test_get_pacing_description(self) -> None:
        """get_pacing_description returns readable text."""
        profile = UserOnboardingProfile(pacing_weeks=4)
        assert "Intense" in profile.get_pacing_description()

        profile = UserOnboardingProfile(pacing_weeks=8)
        assert "Relaxed" in profile.get_pacing_description()


class TestProfileFieldUpdate:
    """Tests for ProfileFieldUpdate model."""

    def test_valid_field_names(self) -> None:
        """Valid field names are accepted."""
        valid_fields = [
            "timezone",
            "occupation",
            "hobbies",
            "personality_type",
            "hangout_spots",
            "darkness_level",
            "pacing_weeks",
            "conversation_style",
        ]
        for field in valid_fields:
            update = ProfileFieldUpdate(field_name=field, value="test")
            assert update.field_name == field

    def test_invalid_field_name(self) -> None:
        """Invalid field names are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ProfileFieldUpdate(field_name="invalid_field", value="test")
        assert "Invalid field_name" in str(exc_info.value)

    def test_value_can_be_any_type(self) -> None:
        """Value field accepts any type."""
        update = ProfileFieldUpdate(field_name="timezone", value="America/New_York")
        assert update.value == "America/New_York"

        update = ProfileFieldUpdate(field_name="hobbies", value=["gaming", "reading"])
        assert update.value == ["gaming", "reading"]

        update = ProfileFieldUpdate(field_name="darkness_level", value=4)
        assert update.value == 4


class TestOnboardingCallModels:
    """Tests for call request/response models."""

    def test_call_request(self) -> None:
        """OnboardingCallRequest accepts required fields."""
        request = OnboardingCallRequest(
            user_id="user_123",
            phone_number="+41787950009",
            language="en",
        )
        assert request.user_id == "user_123"
        assert request.phone_number == "+41787950009"
        assert request.language == "en"

    def test_call_request_default_language(self) -> None:
        """OnboardingCallRequest defaults to English."""
        request = OnboardingCallRequest(
            user_id="user_123",
            phone_number="+41787950009",
        )
        assert request.language == "en"

    def test_call_response_success(self) -> None:
        """OnboardingCallResponse for successful call."""
        response = OnboardingCallResponse(
            success=True,
            call_id="call_abc123",
        )
        assert response.success is True
        assert response.call_id == "call_abc123"
        assert response.error is None

    def test_call_response_failure(self) -> None:
        """OnboardingCallResponse for failed call."""
        response = OnboardingCallResponse(
            success=False,
            error="Phone number invalid",
        )
        assert response.success is False
        assert response.call_id is None
        assert response.error == "Phone number invalid"


class TestModelSerialization:
    """Tests for model serialization/deserialization."""

    def test_profile_to_json(self) -> None:
        """UserOnboardingProfile serializes to JSON."""
        profile = UserOnboardingProfile(
            timezone="America/New_York",
            occupation="Engineer",
            darkness_level=3,
            pacing_weeks=4,
        )
        json_str = profile.model_dump_json()
        assert "America/New_York" in json_str
        assert "Engineer" in json_str

    def test_profile_from_json(self) -> None:
        """UserOnboardingProfile deserializes from dict."""
        data = {
            "timezone": "Europe/London",
            "occupation": "Designer",
            "hobbies": ["art", "music"],
            "darkness_level": 2,
            "pacing_weeks": 8,
        }
        profile = UserOnboardingProfile(**data)
        assert profile.timezone == "Europe/London"
        assert profile.occupation == "Designer"
        assert profile.hobbies == ["art", "music"]
        assert profile.darkness_level == 2
        assert profile.pacing_weeks == 8

    def test_profile_with_enum_string(self) -> None:
        """Profile accepts enum values as strings."""
        profile = UserOnboardingProfile(
            personality_type="introvert",  # type: ignore
            conversation_style="listener",  # type: ignore
        )
        assert profile.personality_type == PersonalityType.INTROVERT
        assert profile.conversation_style == ConversationStyle.LISTENER
