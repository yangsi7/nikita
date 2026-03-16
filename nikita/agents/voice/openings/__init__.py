"""Voice call opening templates for post-onboarding first interaction.

Chess-like "openings" that define how Nikita approaches the first voice call,
personalized based on the user's onboarding profile (darkness level, scene,
interests, etc.).
"""

from nikita.agents.voice.openings.models import Opening
from nikita.agents.voice.openings.override import build_override_from_opening
from nikita.agents.voice.openings.registry import OpeningRegistry
from nikita.agents.voice.openings.selector import OpeningSelector

__all__ = [
    "Opening",
    "OpeningRegistry",
    "OpeningSelector",
    "build_override_from_opening",
]
