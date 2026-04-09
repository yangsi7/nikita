"""Tests for timing context in voice fallback prompt (Spec 209 PR 209-4).

AC-FR004-001: Correct time-of-day segment for user timezone
AC-FR004-002: Invalid timezone -> ZoneInfo fallback to UTC
AC-FR004-003: Pipeline-generated prompt timing is handled by prompt_builder stage (not tested here)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from nikita.agents.voice.config import VoiceAgentConfig


def _make_config():
    """Create VoiceAgentConfig with mock settings."""
    mock_settings = MagicMock()
    return VoiceAgentConfig(settings=mock_settings)


class TestTimingContext:
    """Spec 209 FR-004: Time-aware voice greeting."""

    def test_timezone_converts_time_of_day(self):
        """AC-FR004-001: generate_system_prompt passes tz-converted hour to compute_time_of_day."""
        config = _make_config()

        captured_hours = []

        def _capture_hour(hour: int) -> str:
            captured_hours.append(hour)
            return "night"

        with patch("nikita.agents.voice.config.compute_time_of_day", side_effect=_capture_hour):
            with patch("nikita.agents.voice.config.ZoneInfo") as mock_zi:
                mock_tz = MagicMock()
                mock_zi.return_value = mock_tz

                mock_local = MagicMock()
                mock_local.hour = 22
                mock_local.weekday.return_value = 3
                mock_local.strftime.return_value = "Thursday"

                with patch("nikita.agents.voice.config.datetime") as mock_dt:
                    mock_dt.now.return_value = mock_local

                    prompt = config.generate_system_prompt(
                        user_id=uuid4(),
                        chapter=3,
                        vices=[],
                        timezone="America/New_York",
                    )

        assert captured_hours == [22]
        mock_zi.assert_called_once_with("America/New_York")
        assert "CURRENT MOMENT:" in prompt
        assert "night" in prompt.lower()

    def test_invalid_timezone_falls_back_to_utc(self):
        """AC-FR004-002: Invalid timezone -> no exception, UTC used."""
        config = _make_config()

        prompt = config.generate_system_prompt(
            user_id=uuid4(),
            chapter=3,
            vices=[],
            timezone="Invalid/Zone",
        )

        assert "CURRENT MOMENT:" in prompt
        time_words = ["morning", "afternoon", "evening", "night", "late_night"]
        assert any(w in prompt.lower() for w in time_words)

    def test_default_utc_when_no_timezone(self):
        """Default (no timezone arg) -> UTC-based time."""
        config = _make_config()

        prompt = config.generate_system_prompt(
            user_id=uuid4(),
            chapter=3,
            vices=[],
        )

        assert "CURRENT MOMENT:" in prompt

    def test_current_moment_section_in_prompt(self):
        """CURRENT MOMENT section appears in generated prompt."""
        config = _make_config()

        prompt = config.generate_system_prompt(
            user_id=uuid4(),
            chapter=2,
            vices=[],
            timezone="Europe/Zurich",
        )

        assert "CURRENT MOMENT:" in prompt

    def test_caller_passes_user_timezone(self):
        """Caller (inbound.py) passes timezone=user.timezone."""
        from nikita.agents.voice.inbound import InboundCallHandler

        handler = InboundCallHandler()

        user = MagicMock()
        user.id = uuid4()
        user.chapter = 2
        user.game_status = "active"
        user.vice_preferences = []
        user.name = "TestUser"
        user.metrics = MagicMock(relationship_score=50.0)
        user.timezone = "America/Chicago"
        user.cached_voice_prompt = None

        mock_config = MagicMock()
        mock_config.generate_system_prompt.return_value = "test prompt"

        with patch(
            "nikita.agents.voice.config.VoiceAgentConfig",
            return_value=mock_config,
        ), patch(
            "nikita.config.settings.get_settings",
            return_value=MagicMock(),
        ):
            handler._generate_fallback_prompt(user)

        mock_config.generate_system_prompt.assert_called_once()
        call_kwargs = mock_config.generate_system_prompt.call_args
        assert call_kwargs.kwargs.get("timezone") == "America/Chicago"

    def test_service_passes_user_timezone(self):
        """VoiceService._generate_fallback_prompt passes timezone=user.timezone."""
        from nikita.agents.voice.service import VoiceService

        mock_settings = MagicMock()
        service = VoiceService(settings=mock_settings)

        user = MagicMock()
        user.id = uuid4()
        user.chapter = 2
        user.vice_preferences = []
        user.name = "TestUser"
        user.metrics = MagicMock(relationship_score=50.0)
        user.timezone = "Europe/Zurich"

        mock_config = MagicMock()
        mock_config.generate_system_prompt.return_value = "test prompt"

        with patch(
            "nikita.agents.voice.config.VoiceAgentConfig",
            return_value=mock_config,
        ):
            service._generate_fallback_prompt(user)

        mock_config.generate_system_prompt.assert_called_once()
        call_kwargs = mock_config.generate_system_prompt.call_args
        assert call_kwargs.kwargs.get("timezone") == "Europe/Zurich"

    def test_context_builder_passes_user_timezone(self):
        """ConversationConfigBuilder._generate_fallback_prompt passes timezone=user.timezone."""
        from nikita.agents.voice.context import ConversationConfigBuilder

        mock_settings = MagicMock()
        builder = ConversationConfigBuilder(settings=mock_settings)

        user = MagicMock()
        user.id = uuid4()
        user.chapter = 3
        user.vice_preferences = []
        user.name = "TestUser"
        user.metrics = MagicMock(relationship_score=60.0)
        user.timezone = "Asia/Tokyo"

        mock_config = MagicMock()
        mock_config.generate_system_prompt.return_value = "test prompt"

        with patch(
            "nikita.agents.voice.config.VoiceAgentConfig",
            return_value=mock_config,
        ):
            builder._generate_fallback_prompt(user)

        mock_config.generate_system_prompt.assert_called_once()
        call_kwargs = mock_config.generate_system_prompt.call_args
        assert call_kwargs.kwargs.get("timezone") == "Asia/Tokyo"
