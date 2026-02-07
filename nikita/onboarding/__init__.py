"""Voice Onboarding System (Spec 028).

This module implements voice onboarding where Meta-Nikita conducts
a voice call to introduce game mechanics, collect user profile,
and configure experience preferences.

Key Components:
- UserOnboardingProfile: Profile data collected during onboarding
- OnboardingStatus: State machine for onboarding flow
- MetaNikitaConfig: ElevenLabs agent configuration for Meta-Nikita
- ProfileCollector: Extracts and validates profile fields (Phase E)
- PreferenceConfigurator: Maps darkness/pacing preferences (Phase F)
- HandoffManager: Transitions from Meta-Nikita to Nikita (Phase G)

Usage:
    from nikita.onboarding import (
        UserOnboardingProfile,
        OnboardingStatus,
        MetaNikitaConfig,
    )

    # Check onboarding status
    if user.onboarding_status == OnboardingStatus.PENDING:
        await initiate_onboarding_call(user)

    # Get Meta-Nikita agent config for ElevenLabs
    config = MetaNikitaConfig()
    agent_config = config.get_agent_config(user_id=user.id, user_name=user.name)

    # Collect profile during call (via server tools)
    profile = await collector.collect("timezone", "America/New_York")

    # Complete onboarding and handoff
    await handoff.transition(user)
"""

from nikita.onboarding.meta_nikita import (
    META_NIKITA_FIRST_MESSAGE,
    META_NIKITA_PERSONA,
    META_NIKITA_TTS_SETTINGS,
    MetaNikitaConfig,
    build_meta_nikita_config_override,
)
from nikita.onboarding.models import (
    ConversationStyle,
    DarknessLevel,
    OnboardingStatus,
    PacingWeeks,
    PersonalityType,
    UserOnboardingProfile,
)
from nikita.onboarding.server_tools import (
    OnboardingServerToolHandler,
    OnboardingToolRequest,
    OnboardingToolResponse,
)
from nikita.onboarding.voice_flow import (
    OnboardingState,
    VoiceOnboardingFlow,
)
from nikita.onboarding.profile_collector import (
    CollectionResult,
    ProfileCollector,
    ProfileField,
    TimezoneValidator,
    extract_hobbies,
    extract_timezone_from_location,
    infer_personality_type,
)
from nikita.onboarding.preference_config import (
    BehavioralConfig,
    ConfigurationResult,
    ConversationStyleConfig,
    DarknessLevelConfig,
    PacingConfig,
    PreferenceConfigurator,
    get_conversation_style_config,
    get_darkness_config,
    get_pacing_config,
)
from nikita.onboarding.handoff import (
    FirstMessageGenerator,
    HandoffManager,
    HandoffResult,
    generate_first_nikita_message,
)

__all__ = [
    # Enums
    "ConversationStyle",
    "DarknessLevel",
    "OnboardingStatus",
    "PacingWeeks",
    "PersonalityType",
    # Models
    "UserOnboardingProfile",
    # Meta-Nikita (Phase B)
    "MetaNikitaConfig",
    "META_NIKITA_PERSONA",
    "META_NIKITA_FIRST_MESSAGE",
    "META_NIKITA_TTS_SETTINGS",
    "build_meta_nikita_config_override",  # Spec 033: Unified phone number
    # Server Tools (Phase C)
    "OnboardingServerToolHandler",
    "OnboardingToolRequest",
    "OnboardingToolResponse",
    # Voice Flow (Phase D)
    "OnboardingState",
    "VoiceOnboardingFlow",
    # Profile Collection (Phase E)
    "CollectionResult",
    "ProfileCollector",
    "ProfileField",
    "TimezoneValidator",
    "extract_hobbies",
    "extract_timezone_from_location",
    "infer_personality_type",
    # Preference Configuration (Phase F)
    "BehavioralConfig",
    "ConfigurationResult",
    "ConversationStyleConfig",
    "DarknessLevelConfig",
    "PacingConfig",
    "PreferenceConfigurator",
    "get_conversation_style_config",
    "get_darkness_config",
    "get_pacing_config",
    # Handoff (Phase G)
    "FirstMessageGenerator",
    "HandoffManager",
    "HandoffResult",
    "generate_first_nikita_message",
]
