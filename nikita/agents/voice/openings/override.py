"""Build ElevenLabs conversation_config_override from an Opening template."""

from __future__ import annotations

import logging
from typing import Any

from nikita.agents.voice.config import BASE_VOICE_PERSONA, CHAPTER_PERSONAS
from nikita.agents.voice.models import NikitaMood
from nikita.agents.voice.openings.models import Opening
from nikita.agents.voice.tts_config import MOOD_TTS_SETTINGS

logger = logging.getLogger(__name__)


def build_override_from_opening(
    opening: Opening,
    *,
    user_name: str = "there",
    city: str = "your city",
    interest: str = "life",
) -> dict[str, Any]:
    """Build a conversation_config_override dict from an Opening.

    Composes:
    - BASE_VOICE_PERSONA (always)
    - Chapter 1 persona (post-onboarding = always Ch1)
    - Opening's system_prompt_addendum
    - Opening's goals/forbidden as meta-instructions

    Args:
        opening: The selected Opening template.
        user_name: Player's name from onboarding.
        city: Player's city from onboarding.
        interest: Player's primary interest from onboarding.

    Returns:
        Dict compatible with ElevenLabs conversation_config_override.
    """
    # Build system prompt
    goals_text = ""
    if opening.goals:
        goals_text = "\n\nGOALS FOR THIS CALL:\n" + "\n".join(
            f"- {g}" for g in opening.goals
        )

    forbidden_text = ""
    if opening.forbidden:
        forbidden_text = "\n\nRULES FOR THIS CALL:\n" + "\n".join(
            f"- {f}" for f in opening.forbidden
        )

    duration_text = f"\n\nCALL DURATION: Keep this call around {opening.max_duration_hint}. End naturally, don't rush."

    system_prompt = (
        BASE_VOICE_PERSONA
        + "\n"
        + CHAPTER_PERSONAS.get(1, "")
        + "\n\n"
        + opening.system_prompt_addendum.format(
            name=user_name, city=city, interest=interest
        )
        + goals_text
        + forbidden_text
        + duration_text
    )

    # Format first message
    first_message = opening.format_first_message(
        name=user_name,
        city=city,
        interest=interest,
    )

    # Build TTS override from mood
    tts: dict[str, Any] = {}
    try:
        mood_enum = NikitaMood(opening.mood.lower()) if opening.mood else NikitaMood.NEUTRAL
    except ValueError:
        mood_enum = NikitaMood.NEUTRAL
    mood_settings = MOOD_TTS_SETTINGS.get(mood_enum)
    if mood_settings:
        tts = {
            "stability": mood_settings.stability,
            "similarity_boost": mood_settings.similarity_boost,
            "speed": mood_settings.speed,
        }

    # Apply explicit TTS overrides if any
    if opening.tts_override:
        tts.update(opening.tts_override)

    override: dict[str, Any] = {
        "agent": {
            "prompt": {"prompt": system_prompt},
            "first_message": first_message,
        },
    }

    if tts:
        override["tts"] = tts

    logger.info(
        f"Built override from opening '{opening.id}': "
        f"prompt={len(system_prompt)} chars, mood={opening.mood}"
    )

    return override
