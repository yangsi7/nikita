"""Tests for scheduled-outbound override builder (Spec 108 fix).

Verifies the helper that bridges scheduled outbound calls (pg_cron path)
into full ElevenLabs override payloads, including:
- Per-chapter TTS settings from `tts_config.get_final_settings()`
- Audio-tagged first_message from `audio_tags.get_first_message()`
- Caller-supplied voice_prompt at `agent.prompt.prompt`
- secret__user_id + secret__signed_token in dynamic_variables
- voice_id presence/absence based on settings.elevenlabs_voice_id

Regression guard for the original bug where scheduled outbound calls
sent prompt-only overrides, dropping every other Code-owned setting.
"""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from nikita.agents.voice.service import VoiceService
from nikita.agents.voice.tts_config import get_tts_config_service
from nikita.config.settings import get_settings


def _make_user(user_id, chapter, name="TestUser", score=50.0):
    """Build a mock user with the minimum attributes the helper consumes."""
    user = MagicMock()
    user.id = user_id
    user.name = name
    user.chapter = chapter
    user.relationship_score = score
    user.game_status = "active"
    user.phone = "+14155552671"
    user.onboarding_profile = None
    user.vice_preferences = []
    user.engagement_state = None
    return user


def _expected_mood_for(user):
    """Resolve expected mood via the canonical VoiceService path.

    Drives the per-chapter test parametrisation off the same code that
    `build_scheduled_outbound_override` calls in production. Hardcoding
    a chapter -> mood map would silently rot if `_compute_nikita_mood`
    thresholds shift.
    """
    return VoiceService(settings=get_settings())._compute_nikita_mood(user)


@pytest.mark.asyncio
class TestBuildScheduledOutboundOverride:
    """Unit tests for build_scheduled_outbound_override helper."""

    @pytest.fixture
    def mock_settings(self):
        s = MagicMock()
        s.elevenlabs_api_key = "test-api-key"
        s.elevenlabs_default_agent_id = "agent_test"
        s.elevenlabs_phone_number_id = "phn_test"
        s.elevenlabs_webhook_secret = "test-webhook-secret"
        s.elevenlabs_voice_id = None
        return s

    @pytest.mark.parametrize("chapter", [1, 2, 3, 4, 5])
    async def test_per_chapter_tts_matches_get_final_settings(
        self, chapter, mock_settings
    ):
        """R1: TTS values exactly match tts_config.get_final_settings(chapter, mood).

        Per-key AND-conjoined assertions (no OR). Covers stability,
        similarity_boost, speed; expressive_mode is True; voice_id absent
        when settings.elevenlabs_voice_id is None.
        """
        from nikita.agents.voice.scheduling_overrides import (
            build_scheduled_outbound_override,
        )

        user_id = uuid4()
        user = _make_user(user_id, chapter)
        mood = _expected_mood_for(user)
        expected = get_tts_config_service().get_final_settings(chapter, mood).model_dump()

        with patch(
            "nikita.agents.voice.scheduling_overrides.get_settings",
            return_value=mock_settings,
        ):
            override, _dv = await build_scheduled_outbound_override(
                user=user, voice_prompt="test prompt"
            )

        assert override["tts"]["stability"] == expected["stability"]
        assert override["tts"]["similarity_boost"] == expected["similarity_boost"]
        assert override["tts"]["speed"] == expected["speed"]
        assert override["tts"]["expressive_mode"] is True
        assert "voice_id" not in override["tts"]

    @pytest.mark.parametrize(
        "chapter,expected_tag",
        [
            (1, "[dismissive]"),
            (2, "[curious]"),
            (3, "[happy]"),
            (4, "[cheeky]"),
            (5, "[whispers]"),
        ],
    )
    async def test_first_message_has_chapter_audio_tag(
        self, chapter, expected_tag, mock_settings
    ):
        """R2: first_message starts with the chapter-appropriate audio tag."""
        from nikita.agents.voice.scheduling_overrides import (
            build_scheduled_outbound_override,
        )

        user_id = uuid4()
        user = _make_user(user_id, chapter, name="Simon")

        with patch(
            "nikita.agents.voice.scheduling_overrides.get_settings",
            return_value=mock_settings,
        ):
            override, _dv = await build_scheduled_outbound_override(
                user=user, voice_prompt="test prompt"
            )

        first_message = override["agent"]["first_message"]
        assert first_message.startswith(expected_tag), (
            f"Expected first_message to start with {expected_tag}, got: {first_message!r}"
        )
        assert "Simon" in first_message

    async def test_voice_id_included_when_setting_present(self, mock_settings):
        """R3 (positive): voice_id appears in tts override when env var is set."""
        from nikita.agents.voice.scheduling_overrides import (
            build_scheduled_outbound_override,
        )

        mock_settings.elevenlabs_voice_id = "voice_abc123"
        user_id = uuid4()
        user = _make_user(user_id, 3)

        with patch(
            "nikita.agents.voice.scheduling_overrides.get_settings",
            return_value=mock_settings,
        ):
            override, _dv = await build_scheduled_outbound_override(
                user=user, voice_prompt="test prompt"
            )

        assert override["tts"].get("voice_id") == "voice_abc123"

    async def test_voice_id_omitted_when_setting_unset(self, mock_settings):
        """R3 (negative): voice_id key is OMITTED (not None) when unset."""
        from nikita.agents.voice.scheduling_overrides import (
            build_scheduled_outbound_override,
        )

        mock_settings.elevenlabs_voice_id = None
        user_id = uuid4()
        user = _make_user(user_id, 3)

        with patch(
            "nikita.agents.voice.scheduling_overrides.get_settings",
            return_value=mock_settings,
        ):
            override, _dv = await build_scheduled_outbound_override(
                user=user, voice_prompt="test prompt"
            )

        assert "voice_id" not in override["tts"]

    async def test_dynamic_variables_contain_secret_user_id(self, mock_settings):
        """R4: dynamic_variables contain secret__user_id == str(user.id)."""
        from nikita.agents.voice.scheduling_overrides import (
            build_scheduled_outbound_override,
        )

        user_id = uuid4()
        user = _make_user(user_id, 3)

        with patch(
            "nikita.agents.voice.scheduling_overrides.get_settings",
            return_value=mock_settings,
        ):
            _override, dv = await build_scheduled_outbound_override(
                user=user, voice_prompt="test prompt"
            )

        assert dv.get("secret__user_id") == str(user_id)

    async def test_dynamic_variables_contain_signed_token(self, mock_settings):
        """R4a: dynamic_variables contain secret__signed_token (non-empty)."""
        from nikita.agents.voice.scheduling_overrides import (
            build_scheduled_outbound_override,
        )

        user_id = uuid4()
        user = _make_user(user_id, 3)

        with patch(
            "nikita.agents.voice.scheduling_overrides.get_settings",
            return_value=mock_settings,
        ):
            _override, dv = await build_scheduled_outbound_override(
                user=user, voice_prompt="test prompt"
            )

        token = dv.get("secret__signed_token")
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
        # Format: "{user_id}:{session_id}:{ts}:{hex-signature}"
        assert token.count(":") >= 3

    async def test_voice_prompt_lands_at_agent_prompt_prompt(self, mock_settings):
        """R5: caller-supplied voice_prompt is placed at agent.prompt.prompt."""
        from nikita.agents.voice.scheduling_overrides import (
            build_scheduled_outbound_override,
        )

        user_id = uuid4()
        user = _make_user(user_id, 3)
        prompt_text = "You are Nikita, special scheduled prompt content."

        with patch(
            "nikita.agents.voice.scheduling_overrides.get_settings",
            return_value=mock_settings,
        ):
            override, _dv = await build_scheduled_outbound_override(
                user=user, voice_prompt=prompt_text
            )

        assert override["agent"]["prompt"]["prompt"] == prompt_text


@pytest.mark.asyncio
class TestOutboundPayloadOnTheWire:
    """R8: Integration test capturing the actual httpx POST body.

    Mocks httpx.AsyncClient.post, captures payload, asserts EXACT EQUALITY
    against tts_config.get_final_settings().model_dump() per chapter+mood.
    AND-conjoined per-key (no OR). This is the regression guard for the
    original bug where override.tts was empty in production.
    """

    @pytest.fixture
    def mock_settings(self):
        s = MagicMock()
        s.elevenlabs_api_key = "test-api-key"
        s.elevenlabs_default_agent_id = "agent_test"
        s.elevenlabs_phone_number_id = "phn_test"
        s.elevenlabs_webhook_secret = "test-webhook-secret"
        s.elevenlabs_voice_id = None
        return s

    @pytest.mark.parametrize("chapter", [1, 2, 3, 4, 5])
    async def test_outbound_payload_per_chapter(self, chapter, mock_settings):
        """R1 + R8: Wire-level payload contains chapter-specific TTS values."""
        from nikita.agents.voice.scheduling_overrides import (
            build_scheduled_outbound_override,
        )

        user_id = uuid4()
        user = _make_user(user_id, chapter)
        mood = _expected_mood_for(user)
        expected_tts = (
            get_tts_config_service().get_final_settings(chapter, mood).model_dump()
        )

        # Capture the JSON body sent to ElevenLabs
        captured = {}

        async def fake_post(self_unused, url, json, headers, timeout):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            resp = MagicMock()
            resp.status_code = 200
            resp.json = MagicMock(
                return_value={"success": True, "conversation_id": "conv_x", "callSid": "CA1"}
            )
            return resp

        with patch(
            "nikita.agents.voice.scheduling_overrides.get_settings",
            return_value=mock_settings,
        ), patch("httpx.AsyncClient.post", new=fake_post):
            override, dvars = await build_scheduled_outbound_override(
                user=user, voice_prompt="prompt"
            )
            service = VoiceService(settings=mock_settings)
            await service.make_outbound_call(
                to_number="+14155552671",
                user_id=user_id,
                conversation_config_override=override,
                dynamic_variables=dvars,
            )

        # Assert payload structure
        assert "conversation_initiation_client_data" in captured["json"]
        client_data = captured["json"]["conversation_initiation_client_data"]
        assert "conversation_config_override" in client_data
        sent_override = client_data["conversation_config_override"]

        # R1 — TTS exact-equality, AND-conjoined per key
        assert sent_override["tts"]["stability"] == expected_tts["stability"]
        assert sent_override["tts"]["similarity_boost"] == expected_tts["similarity_boost"]
        assert sent_override["tts"]["speed"] == expected_tts["speed"]
        assert sent_override["tts"]["expressive_mode"] is True

        # R2 — first_message has audio tag
        first_msg = sent_override["agent"]["first_message"]
        assert first_msg.startswith("["), (
            f"first_message missing audio tag: {first_msg!r}"
        )

        # R5 — caller voice_prompt preserved
        assert sent_override["agent"]["prompt"]["prompt"] == "prompt"

        # R4 + R4a — dynamic variables include secret__user_id and secret__signed_token
        sent_dvars = client_data["dynamic_variables"]
        assert sent_dvars["secret__user_id"] == str(user_id)
        assert sent_dvars.get("secret__signed_token")
        assert len(sent_dvars["secret__signed_token"]) > 0
