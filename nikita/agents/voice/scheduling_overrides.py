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

Caller contract: pass a fully-loaded `User` instance (with `metrics`,
`engagement_state`, `vice_preferences` eager-loaded). Both production
call sites already obtain the user via `UserRepository.get()` which
joinedloads those relationships, so this is a no-op for them. Passing
the user directly removes a redundant SELECT and prevents snapshot
divergence between the two reads.

Out of scope: Meta-Nikita / onboarding flows. Those use a separate path
in `nikita/onboarding/` and intentionally do NOT go through this helper.
"""

from __future__ import annotations

import logging
import secrets
import time
from typing import TYPE_CHECKING, Any

from nikita.agents.voice.audio_tags import get_first_message
from nikita.agents.voice.models import NikitaMood
from nikita.agents.voice.service import VoiceService
from nikita.agents.voice.tts_config import get_tts_config_service
from nikita.config.settings import get_settings

if TYPE_CHECKING:
    from nikita.db.models.user import User

logger = logging.getLogger(__name__)


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

    VoiceService instantiation is cheap (just settings injection);
    `_compute_nikita_mood` is the canonical mood-resolution path —
    extracting to a module-level pure function would require service.py
    changes outside this PR's scope. Tracked as followup.

    Defaults to NEUTRAL on any failure (per brief constraint).
    """
    try:
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
    user: User,
    voice_prompt: str | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build full ElevenLabs override payload for a scheduled outbound call.

    Args:
        user: Fully-loaded User instance. MUST have `metrics`,
            `engagement_state`, and `vice_preferences` relationships
            eager-loaded (e.g. via `UserRepository.get()` which uses
            joinedload). Passing a partially-loaded user will raise
            DetachedInstanceError on attribute access during mood
            computation.
        voice_prompt: Caller-supplied prompt text. Lands at
            `conversation_config_override.agent.prompt.prompt`.
            None or empty string is allowed (helper still produces a
            valid override; ElevenLabs uses agent default prompt).

    Returns:
        (conversation_config_override, dynamic_variables) tuple suitable
        for direct passthrough to `VoiceService.make_outbound_call`.

    Raises:
        ValueError: If `user` is None.

    Behaviour notes:
        - voice_id key is OMITTED (not None) when settings.elevenlabs_voice_id
          is unset; ElevenLabs API rejects null voice_id.
        - expressive_mode is always True for scheduled outbound calls (Spec 108).
        - secret__signed_token is generated via VoiceService._generate_signed_token
          for mid-call server-tool auth.
    """
    if user is None:
        raise ValueError("User must not be None for scheduled outbound override")

    settings = get_settings()
    user_id = user.id
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

    # Dynamic variables — server-tool auth requires secret__signed_token.
    # Reuse the canonical signed-token generator. Do NOT reimplement HMAC.
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
