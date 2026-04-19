"""Scheduled-outbound override builder (Spec 108 fix).

Bridges the scheduled outbound voice path (pg_cron-driven proactive calls)
into a complete ElevenLabs override payload. Without this helper the
scheduled outbound path was sending prompt-only overrides — every other
Code-owned setting (TTS, first_message, secret tokens) was dropped.

All scheduled outbound callers MUST go through `build_scheduled_outbound_override`.
This is the single seam keeping the configuration ownership matrix
(`docs/reference/elevenlabs-configuration.md`) honest on the wire.

Resolved settings:
- TTS values come from `nikita.agents.voice.tts_config.get_final_settings()`
  with mood resolved via the same `VoiceService._compute_nikita_mood()` path
  used by the interactive `initiate_call`. Defaults to `NEUTRAL` if mood
  computation fails.
- first_message comes from `nikita.agents.voice.audio_tags.get_first_message()`.
- voice_id comes from `settings.elevenlabs_voice_id` and is OMITTED (not None)
  when unset — ElevenLabs rejects null voice_id.
- secret__user_id and secret__signed_token are required for mid-call
  server-tool auth (score_turn / update_memory / get_context / get_memory).
  The signed token is produced via the canonical
  `VoiceService._generate_signed_token()` helper — never reimplemented.

Out of scope: Meta-Nikita / onboarding flows. Those use a separate path
in `nikita/onboarding/` and intentionally do NOT go through this helper.
"""

from __future__ import annotations

import logging
import secrets
import time
from typing import Any
from uuid import UUID

from nikita.agents.voice.audio_tags import get_first_message
from nikita.agents.voice.models import NikitaMood
from nikita.agents.voice.tts_config import get_tts_config_service
from nikita.config.settings import get_settings

logger = logging.getLogger(__name__)


async def _load_user_for_override(user_id: UUID):
    """Load user with relationships needed for chapter+mood resolution.

    Mirrors `VoiceService._load_user`. Kept module-private so tests can
    patch this single seam instead of mocking the SQLAlchemy session.
    """
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload

    from nikita.db.database import get_session_maker
    from nikita.db.models.user import User

    session_maker = get_session_maker()
    async with session_maker() as session:
        stmt = (
            select(User)
            .options(
                joinedload(User.metrics),
                joinedload(User.engagement_state),
                joinedload(User.vice_preferences),
            )
            .where(User.id == user_id)
        )
        result = await session.execute(stmt)
        return result.unique().scalar_one_or_none()


def _resolve_user_name(user: Any) -> str:
    """Best-effort name extraction matching VoiceService._get_user_name."""
    profile = getattr(user, "onboarding_profile", None)
    if isinstance(profile, dict) and profile.get("name"):
        return str(profile["name"])
    name = getattr(user, "name", None)
    if name:
        return str(name)
    return "friend"


def _resolve_nikita_mood(user: Any) -> NikitaMood:
    """Resolve Nikita's mood for TTS modulation.

    Defers to `VoiceService._compute_nikita_mood` via a lightweight
    instance — the method is pure (chapter + relationship_score in,
    NikitaMood out) so the singleton settings dependency is fine.

    Defaults to NEUTRAL on any failure (per brief constraint).
    """
    try:
        from nikita.agents.voice.service import VoiceService

        service = VoiceService(settings=get_settings())
        return service._compute_nikita_mood(user)
    except Exception as exc:  # noqa: BLE001 — fail open with safe default
        logger.warning(
            "[SCHEDULING_OVERRIDE] mood computation failed for user=%s, "
            "defaulting to NEUTRAL: %s",
            getattr(user, "id", "?"),
            exc,
        )
        return NikitaMood.NEUTRAL


def _generate_session_id() -> str:
    """Generate a session ID matching VoiceService._generate_session_id."""
    return f"voice_{secrets.token_hex(8)}_{int(time.time())}"


async def build_scheduled_outbound_override(
    user_id: UUID,
    voice_prompt: str | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build full ElevenLabs override payload for a scheduled outbound call.

    Args:
        user_id: UUID of the user receiving the call.
        voice_prompt: Caller-supplied prompt text. Lands at
            `conversation_config_override.agent.prompt.prompt`.
            None or empty string is allowed (helper still produces a
            valid override; ElevenLabs uses agent default prompt).

    Returns:
        (conversation_config_override, dynamic_variables) tuple suitable
        for direct passthrough to `VoiceService.make_outbound_call`.

    Raises:
        ValueError: If user_id does not resolve to a known user.

    Behaviour notes:
        - voice_id key is OMITTED (not None) when settings.elevenlabs_voice_id
          is unset; ElevenLabs API rejects null voice_id.
        - expressive_mode is always True for scheduled outbound calls (Spec 108).
        - secret__signed_token is generated via VoiceService._generate_signed_token
          for mid-call server-tool auth.
    """
    settings = get_settings()
    user = await _load_user_for_override(user_id)
    if user is None:
        raise ValueError(f"User {user_id} not found for scheduled outbound override")

    chapter = getattr(user, "chapter", 1) or 1
    mood = _resolve_nikita_mood(user)
    user_name = _resolve_user_name(user)

    # TTS — single source of truth (no inline numeric literals)
    tts_settings = get_tts_config_service().get_final_settings(chapter=chapter, mood=mood)
    tts_override: dict[str, Any] = tts_settings.model_dump()
    tts_override["expressive_mode"] = True
    if settings.elevenlabs_voice_id:
        tts_override["voice_id"] = settings.elevenlabs_voice_id

    # first_message — chapter-tagged greeting from single source of truth
    first_message = get_first_message(chapter, user_name)

    # Agent block — caller-supplied prompt wins; first_message attaches
    agent_override: dict[str, Any] = {"first_message": first_message}
    if voice_prompt:
        agent_override["prompt"] = {"prompt": voice_prompt}

    config_override: dict[str, Any] = {
        "agent": agent_override,
        "tts": tts_override,
    }

    # Dynamic variables — server-tool auth requires secret__signed_token
    # Reuse the canonical signed-token generator. Do NOT reimplement HMAC.
    from nikita.agents.voice.service import VoiceService

    session_id = _generate_session_id()
    voice_service = VoiceService(settings=settings)
    signed_token = voice_service._generate_signed_token(str(user_id), session_id)

    dynamic_variables: dict[str, Any] = {
        "secret__user_id": str(user_id),
        "secret__signed_token": signed_token,
    }

    logger.info(
        "[SCHEDULING_OVERRIDE] built override for user=%s chapter=%s mood=%s "
        "voice_id_set=%s prompt_chars=%d",
        user_id,
        chapter,
        mood.value,
        bool(settings.elevenlabs_voice_id),
        len(voice_prompt) if voice_prompt else 0,
    )

    return config_override, dynamic_variables
