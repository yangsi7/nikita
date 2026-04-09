"""Tests for timing context in voice fallback prompt (Spec 209 PR 209-4).

AC-FR004-001: Correct time-of-day segment for user timezone
AC-FR004-002: Invalid timezone -> ZoneInfo fallback to UTC
AC-FR004-003: Pipeline-generated prompt already has timing (regression guard)
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from nikita.agents.voice.config import VoiceAgentConfig


def _make_config():
    """Create VoiceAgentConfig with mock settings."""
    mock_settings = MagicMock()
    return VoiceAgentConfig(settings=mock_settings)


@pytest.mark.asyncio
class TestTimingContext:
    """Spec 209 FR-004: Time-aware voice greeting."""

    def test_timezone_converts_time_of_day(self):
        """AC-FR004-001: Correct time-of-day for user timezone.

        At 02:00 UTC with timezone America/New_York (UTC-4):
        Local time = 22:00 -> "night"
        """
        config = _make_config()

        # Fix datetime.now to return 02:00 UTC
        mock_now = datetime(2026, 4, 9, 2, 0, 0, tzinfo=timezone.utc)

        with patch("nikita.agents.voice.config.datetime") as mock_dt:
            mock_dt.now.return_value = mock_now
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

            prompt = config.generate_system_prompt(
                user_id=uuid4(),
                chapter=3,
                vices=[],
                timezone="America/New_York",
            )

        assert "CURRENT MOMENT:" in prompt
        assert "night" in prompt.lower()

    def test_invalid_timezone_falls_back_to_utc(self):
        """AC-FR004-002: Invalid timezone -> no exception, UTC used."""
        config = _make_config()

        # Should not raise even with invalid timezone
        prompt = config.generate_system_prompt(
            user_id=uuid4(),
            chapter=3,
            vices=[],
            timezone="Invalid/Zone",
        )

        assert "CURRENT MOMENT:" in prompt
        # Should contain SOME time-of-day (from UTC)
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
        assert call_kwargs.kwargs.get("timezone") == "America/Chicago" or \
            (len(call_kwargs.args) > 5 and call_kwargs.args[5] == "America/Chicago")
