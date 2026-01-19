"""Onboarding models (Spec 028).

Pydantic models for voice onboarding system including:
- UserOnboardingProfile: All profile data collected during onboarding
- OnboardingStatus: State machine for onboarding flow
- Preference enums: DarknessLevel, PacingWeeks, ConversationStyle

Implements:
- AC-T002.1: UserOnboardingProfile Pydantic model
- AC-T002.2: Validation for darkness_level (1-5)
- AC-T002.3: Validation for pacing_weeks (4 or 8)
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class OnboardingStatus(str, Enum):
    """Onboarding state machine states."""

    PENDING = "pending"  # User registered but not onboarded
    CALL_SCHEDULED = "call_scheduled"  # Onboarding call scheduled
    IN_CALL = "in_call"  # Currently in onboarding call
    COMPLETED = "completed"  # Successfully onboarded
    SKIPPED = "skipped"  # User skipped voice onboarding
    FAILED = "failed"  # Onboarding call failed


class PersonalityType(str, Enum):
    """User personality type."""

    INTROVERT = "introvert"
    EXTROVERT = "extrovert"
    AMBIVERT = "ambivert"


class ConversationStyle(str, Enum):
    """Preferred conversation style."""

    LISTENER = "listener"  # Prefers listening (Nikita talks more)
    BALANCED = "balanced"  # 50/50 give and take
    SHARER = "sharer"  # Prefers sharing (Nikita asks more)


class DarknessLevel(int, Enum):
    """Experience darkness level (1-5 scale).

    Level 1: Vanilla - PG-13 flirtation, no edge
    Level 2: Light Edge - Mild teasing, light innuendo
    Level 3: Default - Discusses substances/sex freely, mild manipulation
    Level 4: Dark - Possessive, jealous, emotional manipulation
    Level 5: Full Noir - Intense, boundary-pushing, high drama
    """

    VANILLA = 1
    LIGHT_EDGE = 2
    DEFAULT = 3
    DARK = 4
    FULL_NOIR = 5


class PacingWeeks(int, Enum):
    """Game pacing in weeks.

    4 weeks: Intense (1 chapter per week)
    8 weeks: Relaxed (1 chapter per 2 weeks)
    """

    INTENSE = 4
    RELAXED = 8


class UserOnboardingProfile(BaseModel):
    """Complete user profile collected during voice onboarding.

    Implements AC-T002.1: UserOnboardingProfile Pydantic model
    """

    # Basic info
    timezone: str | None = Field(
        default=None,
        description="User's timezone (e.g., 'America/New_York')",
    )
    occupation: str | None = Field(
        default=None,
        description="User's job or occupation",
    )
    hobbies: list[str] = Field(
        default_factory=list,
        description="User's hobbies and interests",
    )
    personality_type: PersonalityType | None = Field(
        default=None,
        description="Introvert, extrovert, or ambivert",
    )
    hangout_spots: list[str] = Field(
        default_factory=list,
        description="Places user likes to hang out",
    )

    # Experience preferences
    darkness_level: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Experience darkness level (1-5)",
    )
    pacing_weeks: int = Field(
        default=4,
        description="Game duration in weeks (4 or 8)",
    )
    conversation_style: ConversationStyle = Field(
        default=ConversationStyle.BALANCED,
        description="Preferred conversation style",
    )

    # Onboarding metadata
    onboarded_at: datetime | None = Field(
        default=None,
        description="When onboarding was completed",
    )
    onboarding_call_id: str | None = Field(
        default=None,
        description="ElevenLabs conversation ID for onboarding call",
    )

    @field_validator("darkness_level")
    @classmethod
    def validate_darkness_level(cls, v: int) -> int:
        """Validate darkness_level is 1-5.

        Implements AC-T002.2: Validation for darkness_level (1-5)
        """
        if not 1 <= v <= 5:
            raise ValueError("darkness_level must be between 1 and 5")
        return v

    @field_validator("pacing_weeks")
    @classmethod
    def validate_pacing_weeks(cls, v: int) -> int:
        """Validate pacing_weeks is 4 or 8.

        Implements AC-T002.3: Validation for pacing_weeks (4 or 8)
        """
        if v not in (4, 8):
            raise ValueError("pacing_weeks must be 4 or 8")
        return v

    def is_complete(self) -> bool:
        """Check if profile has minimum required fields.

        Returns True if at least timezone and personality_type are set.
        """
        return self.timezone is not None and self.personality_type is not None

    def to_context_dict(self) -> dict[str, Any]:
        """Convert profile to context dictionary for prompts.

        Returns dict suitable for injection into Nikita's context.
        """
        return {
            "timezone": self.timezone,
            "occupation": self.occupation,
            "hobbies": self.hobbies,
            "personality_type": (
                self.personality_type.value if self.personality_type else None
            ),
            "hangout_spots": self.hangout_spots,
            "darkness_level": self.darkness_level,
            "pacing_weeks": self.pacing_weeks,
            "conversation_style": self.conversation_style.value,
        }

    def get_darkness_description(self) -> str:
        """Get human-readable description of darkness level."""
        descriptions = {
            1: "Vanilla - Light flirtation, no edge",
            2: "Light Edge - Mild teasing and innuendo",
            3: "Default - Freely discusses adult topics, mild manipulation",
            4: "Dark - Possessive, jealous, emotional manipulation",
            5: "Full Noir - Intense, boundary-pushing, high drama",
        }
        return descriptions.get(self.darkness_level, "Unknown")

    def get_pacing_description(self) -> str:
        """Get human-readable description of pacing."""
        return (
            "Intense (4 weeks)" if self.pacing_weeks == 4 else "Relaxed (8 weeks)"
        )


class ProfileFieldUpdate(BaseModel):
    """Single profile field update from server tool.

    Used by collect_profile server tool during onboarding call.
    """

    field_name: str = Field(description="Name of field to update")
    value: Any = Field(description="Value to set")

    @field_validator("field_name")
    @classmethod
    def validate_field_name(cls, v: str) -> str:
        """Validate field_name is a valid profile field."""
        valid_fields = {
            "timezone",
            "occupation",
            "hobbies",
            "personality_type",
            "hangout_spots",
            "darkness_level",
            "pacing_weeks",
            "conversation_style",
        }
        if v not in valid_fields:
            raise ValueError(f"Invalid field_name: {v}. Must be one of {valid_fields}")
        return v


class OnboardingCallRequest(BaseModel):
    """Request to initiate onboarding voice call."""

    user_id: str = Field(description="User UUID")
    phone_number: str = Field(description="Phone number to call")
    language: str = Field(default="en", description="Language code")


class OnboardingCallResponse(BaseModel):
    """Response from onboarding call initiation."""

    success: bool
    call_id: str | None = None
    error: str | None = None
