"""Tests for voice prompt staleness logging in inbound handler (Spec 209 PR 209-1).

AC-FR001-004: Staleness log in _get_conversation_config_override() when prompt >4h old.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.agents.voice.inbound import InboundCallHandler


def _make_user(**overrides):
    """Create a mock User with defaults for inbound handler."""
    defaults = dict(
        id=uuid4(),
        chapter=2,
        game_status="active",
        phone_number="+41787950009",
        telegram_id=12345678,
        onboarding_status="completed",
        cached_voice_prompt="You are Nikita...",
        cached_voice_prompt_at=datetime.now(timezone.utc),
        name="TestUser",
        relationship_score=Decimal("65.0"),
        metrics=MagicMock(relationship_score=Decimal("65.0")),
        vice_preferences=[],
        onboarding_profile={"name": "TestUser"},
        timezone="UTC",
    )
    defaults.update(overrides)
    return MagicMock(**defaults)


@pytest.fixture(autouse=True)
def _patch_settings():
    """Patch settings for all tests."""
    mock_settings = MagicMock()
    mock_settings.elevenlabs_webhook_secret = "test_secret"
    with patch("nikita.config.settings.get_settings", return_value=mock_settings):
        yield


@pytest.mark.asyncio
class TestVoicePromptStaleness:
    """Spec 209 FR-001 AC-FR001-004: Staleness logging."""

    async def test_stale_prompt_logs_warning(self, caplog):
        """cached_voice_prompt_at >4h old -> 'voice_prompt_stale' in log."""
        stale_time = datetime.now(timezone.utc) - timedelta(hours=5)
        user = _make_user(cached_voice_prompt_at=stale_time)

        handler = InboundCallHandler()

        # Mock the ready_prompt lookup to return None (use cached_voice_prompt)
        with patch.object(
            handler, "_try_load_ready_prompt", new_callable=AsyncMock, return_value=None
        ), caplog.at_level(logging.INFO, logger="nikita.agents.voice.inbound"):
            config = await handler._get_conversation_config_override(user)

        assert "voice_prompt_stale" in caplog.text

    async def test_fresh_prompt_no_staleness_log(self, caplog):
        """cached_voice_prompt_at <4h old -> no staleness log."""
        fresh_time = datetime.now(timezone.utc) - timedelta(hours=1)
        user = _make_user(cached_voice_prompt_at=fresh_time)

        handler = InboundCallHandler()

        with patch.object(
            handler, "_try_load_ready_prompt", new_callable=AsyncMock, return_value=None
        ), caplog.at_level(logging.INFO, logger="nikita.agents.voice.inbound"):
            config = await handler._get_conversation_config_override(user)

        assert "voice_prompt_stale" not in caplog.text

    async def test_null_prompt_at_no_error(self, caplog):
        """cached_voice_prompt_at = None -> no log, no error."""
        user = _make_user(cached_voice_prompt_at=None)

        handler = InboundCallHandler()

        with patch.object(
            handler, "_try_load_ready_prompt", new_callable=AsyncMock, return_value=None
        ), caplog.at_level(logging.INFO, logger="nikita.agents.voice.inbound"):
            config = await handler._get_conversation_config_override(user)

        assert "voice_prompt_stale" not in caplog.text
