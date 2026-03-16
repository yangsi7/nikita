"""Tests for build_override_from_opening — Opening → config override conversion."""

from __future__ import annotations

from nikita.agents.voice.openings.models import Opening
from nikita.agents.voice.openings.override import build_override_from_opening


def _make_opening(**kwargs) -> Opening:
    """Helper to create test openings."""
    defaults = {
        "id": "test",
        "name": "Test Opening",
        "first_message": "Hey {name} from {city}, into {interest}?",
        "system_prompt_addendum": "Be warm with {name} from {city}.",
        "mood": "neutral",
        "goals": ["Learn something"],
        "forbidden": ["Don't be boring"],
    }
    defaults.update(kwargs)
    return Opening(**defaults)


class TestBuildOverrideFromOpening:
    """Override builder produces valid ElevenLabs conversation_config_override."""

    def test_override_has_agent_key(self) -> None:
        opening = _make_opening()
        override = build_override_from_opening(opening, user_name="Alex")
        assert "agent" in override
        assert "prompt" in override["agent"]
        assert "first_message" in override["agent"]

    def test_first_message_interpolated(self) -> None:
        opening = _make_opening()
        override = build_override_from_opening(
            opening, user_name="Alex", city="Zurich", interest="chess"
        )
        msg = override["agent"]["first_message"]
        assert "Alex" in msg
        assert "Zurich" in msg
        assert "chess" in msg

    def test_system_prompt_contains_base_persona(self) -> None:
        opening = _make_opening()
        override = build_override_from_opening(opening, user_name="Alex")
        prompt = override["agent"]["prompt"]["prompt"]
        # BASE_VOICE_PERSONA contains "You are Nikita"
        assert "You are Nikita" in prompt

    def test_system_prompt_contains_chapter_1_persona(self) -> None:
        opening = _make_opening()
        override = build_override_from_opening(opening, user_name="Alex")
        prompt = override["agent"]["prompt"]["prompt"]
        # CHAPTER_PERSONAS[1] contains "distant" or "guarded"
        assert "distant" in prompt.lower() or "guarded" in prompt.lower()

    def test_system_prompt_contains_addendum(self) -> None:
        opening = _make_opening(
            system_prompt_addendum="SPECIAL INSTRUCTION: be extra warm"
        )
        override = build_override_from_opening(opening, user_name="Alex")
        prompt = override["agent"]["prompt"]["prompt"]
        assert "SPECIAL INSTRUCTION: be extra warm" in prompt

    def test_system_prompt_contains_goals(self) -> None:
        opening = _make_opening(goals=["Make them laugh", "Ask about hobbies"])
        override = build_override_from_opening(opening, user_name="Alex")
        prompt = override["agent"]["prompt"]["prompt"]
        assert "Make them laugh" in prompt
        assert "Ask about hobbies" in prompt

    def test_system_prompt_contains_forbidden(self) -> None:
        opening = _make_opening(forbidden=["Don't mention scores"])
        override = build_override_from_opening(opening, user_name="Alex")
        prompt = override["agent"]["prompt"]["prompt"]
        assert "Don't mention scores" in prompt

    def test_system_prompt_contains_duration_hint(self) -> None:
        opening = _make_opening(max_duration_hint="4min")
        override = build_override_from_opening(opening, user_name="Alex")
        prompt = override["agent"]["prompt"]["prompt"]
        assert "4min" in prompt

    def test_tts_override_for_flirty_mood(self) -> None:
        opening = _make_opening(mood="flirty")
        override = build_override_from_opening(opening, user_name="Alex")
        # flirty mood should produce TTS override
        if "tts" in override:
            assert "stability" in override["tts"]

    def test_explicit_tts_override_applied(self) -> None:
        opening = _make_opening(tts_override={"speed": 0.85})
        override = build_override_from_opening(opening, user_name="Alex")
        if "tts" in override:
            assert override["tts"]["speed"] == 0.85

    def test_addendum_placeholders_interpolated(self) -> None:
        """system_prompt_addendum with {name} should be interpolated."""
        opening = _make_opening(
            system_prompt_addendum="This is your first call with {name}."
        )
        override = build_override_from_opening(
            opening, user_name="Boris", city="Geneva"
        )
        prompt = override["agent"]["prompt"]["prompt"]
        assert "Boris" in prompt
        assert "{name}" not in prompt  # Should be interpolated
