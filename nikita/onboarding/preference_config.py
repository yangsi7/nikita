"""Preference Configuration (Spec 028 Phase F).

Implements PreferenceConfigurator for darkness level, pacing,
and conversation style configuration during voice onboarding.

Implements:
- AC-T022.1-4: PreferenceConfigurator class
- AC-T023.1-4: Darkness level mapping
- AC-T024.1-4: Pacing configuration
"""

import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from nikita.onboarding.models import ConversationStyle, UserOnboardingProfile

logger = logging.getLogger(__name__)


@dataclass
class DarknessLevelConfig:
    """Configuration for a darkness level.

    Maps the 1-5 darkness scale to behavioral parameters.
    """

    level: int
    name: str
    description: str
    allows_manipulation: bool = False
    manipulation_intensity: str = "none"  # none, subtle, moderate, overt
    allows_substance_mentions: bool = False
    allows_possessiveness: bool = False
    emotional_intensity: str = "moderate"  # low, moderate, high, extreme
    behavioral_traits: dict[str, Any] = field(default_factory=dict)


@dataclass
class PacingConfig:
    """Configuration for pacing (game duration).

    Defines how the 4 or 8 week durations affect gameplay.
    """

    weeks: int
    name: str
    description: str
    chapters_per_week: float
    decay_multiplier: float = 1.0
    touchpoints_per_day: float = 2.0
    grace_period_hours: int = 24


@dataclass
class ConversationStyleConfig:
    """Configuration for conversation style.

    Defines the balance between listening and sharing.
    """

    style: ConversationStyle
    question_ratio: float  # 0-1, how much Nikita asks questions
    sharing_ratio: float  # 0-1, how much Nikita shares about herself
    listening_ratio: float  # 0-1, how much she reflects back


@dataclass
class BehavioralConfig:
    """Combined behavioral configuration."""

    darkness_config: DarknessLevelConfig
    pacing_config: PacingConfig
    conversation_style_config: ConversationStyleConfig
    decay_rate: float
    allows_manipulation: bool


@dataclass
class ConfigurationResult:
    """Result of a preference configuration."""

    success: bool
    applied: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


# Darkness level configurations
DARKNESS_CONFIGS = {
    1: DarknessLevelConfig(
        level=1,
        name="vanilla",
        description="Wholesome and supportive. No edge, pure affection.",
        allows_manipulation=False,
        manipulation_intensity="none",
        allows_substance_mentions=False,
        allows_possessiveness=False,
        emotional_intensity="low",
        behavioral_traits={
            "jealousy": "none",
            "passive_aggressive": False,
            "boundary_testing": False,
            "emotional_volatility": "stable",
        },
    ),
    2: DarknessLevelConfig(
        level=2,
        name="mild",
        description="Mostly sweet with occasional mild insecurity.",
        allows_manipulation=False,
        manipulation_intensity="none",
        allows_substance_mentions=False,
        allows_possessiveness=False,
        emotional_intensity="moderate",
        behavioral_traits={
            "jealousy": "mild",
            "passive_aggressive": False,
            "boundary_testing": False,
            "emotional_volatility": "mostly_stable",
        },
    ),
    3: DarknessLevelConfig(
        level=3,
        name="balanced",
        description="Realistic with subtle manipulation and occasional drama.",
        allows_manipulation=True,
        manipulation_intensity="subtle",
        allows_substance_mentions=True,
        allows_possessiveness=False,
        emotional_intensity="moderate",
        behavioral_traits={
            "jealousy": "moderate",
            "passive_aggressive": True,
            "boundary_testing": True,
            "emotional_volatility": "variable",
        },
    ),
    4: DarknessLevelConfig(
        level=4,
        name="edgy",
        description="Complex with notable manipulation and emotional depth.",
        allows_manipulation=True,
        manipulation_intensity="moderate",
        allows_substance_mentions=True,
        allows_possessiveness=True,
        emotional_intensity="high",
        behavioral_traits={
            "jealousy": "notable",
            "passive_aggressive": True,
            "boundary_testing": True,
            "emotional_volatility": "volatile",
        },
    ),
    5: DarknessLevelConfig(
        level=5,
        name="noir",
        description="Full noir: overt manipulation, possessiveness, high stakes.",
        allows_manipulation=True,
        manipulation_intensity="overt",
        allows_substance_mentions=True,
        allows_possessiveness=True,
        emotional_intensity="extreme",
        behavioral_traits={
            "jealousy": "intense",
            "passive_aggressive": True,
            "boundary_testing": True,
            "emotional_volatility": "unpredictable",
        },
    ),
}

# Pacing configurations
PACING_CONFIGS = {
    4: PacingConfig(
        weeks=4,
        name="intense",
        description="Fast-paced journey. 1 chapter per week approximately.",
        chapters_per_week=1.25,  # 5 chapters / 4 weeks
        decay_multiplier=1.5,  # Higher decay = more pressure
        touchpoints_per_day=3.0,  # More frequent
        grace_period_hours=18,  # Shorter grace period
    ),
    8: PacingConfig(
        weeks=8,
        name="relaxed",
        description="Gradual journey. More time to build relationship.",
        chapters_per_week=0.625,  # 5 chapters / 8 weeks
        decay_multiplier=0.75,  # Lower decay = less pressure
        touchpoints_per_day=1.5,  # Less frequent
        grace_period_hours=36,  # Longer grace period
    ),
}

# Conversation style configurations
CONVERSATION_STYLE_CONFIGS = {
    ConversationStyle.LISTENER: ConversationStyleConfig(
        style=ConversationStyle.LISTENER,
        question_ratio=0.45,
        sharing_ratio=0.25,
        listening_ratio=0.30,
    ),
    ConversationStyle.BALANCED: ConversationStyleConfig(
        style=ConversationStyle.BALANCED,
        question_ratio=0.33,
        sharing_ratio=0.33,
        listening_ratio=0.34,
    ),
    ConversationStyle.SHARER: ConversationStyleConfig(
        style=ConversationStyle.SHARER,
        question_ratio=0.25,
        sharing_ratio=0.45,
        listening_ratio=0.30,
    ),
}


def get_darkness_config(level: int) -> DarknessLevelConfig:
    """
    Get darkness level configuration.

    AC-T023.1: Map 1-5 to behavioral parameters

    Args:
        level: Darkness level (1-5)

    Returns:
        DarknessLevelConfig for the level

    Raises:
        ValueError: If level is not 1-5
    """
    if level not in DARKNESS_CONFIGS:
        raise ValueError(f"Invalid darkness level {level}. Must be 1-5.")
    return DARKNESS_CONFIGS[level]


def get_pacing_config(weeks: int) -> PacingConfig:
    """
    Get pacing configuration.

    AC-T024.1-2: 4 weeks = intense, 8 weeks = relaxed

    Args:
        weeks: Pacing in weeks (4 or 8)

    Returns:
        PacingConfig for the duration

    Raises:
        ValueError: If weeks is not 4 or 8
    """
    if weeks not in PACING_CONFIGS:
        raise ValueError(f"Invalid pacing {weeks} weeks. Must be 4 or 8.")
    return PACING_CONFIGS[weeks]


def get_conversation_style_config(style: ConversationStyle) -> ConversationStyleConfig:
    """Get conversation style configuration."""
    return CONVERSATION_STYLE_CONFIGS.get(
        style, CONVERSATION_STYLE_CONFIGS[ConversationStyle.BALANCED]
    )


class PreferenceConfigurator:
    """Configures user preferences during onboarding.

    Manages darkness level, pacing, and conversation style
    preferences with validation and behavioral mapping.
    """

    def __init__(self) -> None:
        """Initialize the configurator."""
        self._profiles: dict[str, UserOnboardingProfile] = {}

    def configure(
        self,
        user_id: UUID,
        darkness_level: int | None = None,
        pacing_weeks: int | None = None,
        conversation_style: ConversationStyle | None = None,
    ) -> ConfigurationResult:
        """
        Configure user preferences.

        AC-T022.2: configure() method
        AC-T022.3: Stores preferences in user profile

        Args:
            user_id: User's UUID
            darkness_level: Darkness level 1-5
            pacing_weeks: Pacing 4 or 8 weeks
            conversation_style: Conversation style

        Returns:
            ConfigurationResult with status
        """
        user_key = str(user_id)

        # Get or create profile
        if user_key not in self._profiles:
            self._profiles[user_key] = UserOnboardingProfile()

        profile = self._profiles[user_key]
        applied: dict[str, Any] = {}

        try:
            # Validate and apply darkness level
            if darkness_level is not None:
                if not 1 <= darkness_level <= 5:
                    return ConfigurationResult(
                        success=False,
                        error=f"Invalid darkness level {darkness_level}. Must be 1-5.",
                    )
                profile.darkness_level = darkness_level
                applied["darkness_level"] = darkness_level

            # Validate and apply pacing
            if pacing_weeks is not None:
                if pacing_weeks not in (4, 8):
                    return ConfigurationResult(
                        success=False,
                        error=f"Invalid pacing {pacing_weeks}. Must be 4 or 8 weeks.",
                    )
                profile.pacing_weeks = pacing_weeks
                applied["pacing_weeks"] = pacing_weeks

            # Apply conversation style
            if conversation_style is not None:
                profile.conversation_style = conversation_style
                applied["conversation_style"] = conversation_style.value

            logger.debug(f"Configured preferences for user {user_id}: {applied}")

            return ConfigurationResult(success=True, applied=applied)

        except Exception as e:
            logger.error(f"Error configuring preferences: {e}")
            return ConfigurationResult(success=False, error=str(e))

    def get_preferences(self, user_id: UUID) -> UserOnboardingProfile:
        """Get user's preference profile."""
        user_key = str(user_id)
        if user_key not in self._profiles:
            return UserOnboardingProfile()
        return self._profiles[user_key]

    def get_conversation_style_config(self, user_id: UUID) -> ConversationStyleConfig:
        """Get conversation style configuration for user."""
        profile = self.get_preferences(user_id)
        style = profile.conversation_style or ConversationStyle.BALANCED
        return get_conversation_style_config(style)

    def get_behavioral_config(self, user_id: UUID) -> BehavioralConfig:
        """Get combined behavioral configuration for user."""
        profile = self.get_preferences(user_id)

        darkness = get_darkness_config(profile.darkness_level or 3)
        pacing = get_pacing_config(profile.pacing_weeks or 4)
        style = self.get_conversation_style_config(user_id)

        # Calculate effective decay rate
        base_decay = 0.8  # Base hourly decay
        effective_decay = base_decay * pacing.decay_multiplier

        return BehavioralConfig(
            darkness_config=darkness,
            pacing_config=pacing,
            conversation_style_config=style,
            decay_rate=effective_decay,
            allows_manipulation=darkness.allows_manipulation,
        )

    def to_dict(self, user_id: UUID) -> dict[str, Any]:
        """Convert preferences to dictionary."""
        profile = self.get_preferences(user_id)
        return {
            "darkness_level": profile.darkness_level,
            "pacing_weeks": profile.pacing_weeks,
            "conversation_style": profile.conversation_style.value
            if profile.conversation_style
            else "balanced",
        }
