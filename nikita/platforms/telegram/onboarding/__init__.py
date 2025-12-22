"""Onboarding handler for enhanced user personalization.

Part of 017-enhanced-onboarding feature.
Collects 5 profile fields from new users after OTP verification.
"""

from nikita.platforms.telegram.onboarding.handler import (
    INTRO_MESSAGE,
    STEP_PROMPTS,
    OnboardingHandler,
)

__all__ = [
    "OnboardingHandler",
    "INTRO_MESSAGE",
    "STEP_PROMPTS",
]
