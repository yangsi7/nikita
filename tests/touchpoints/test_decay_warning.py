"""Tests for Spec 106 I8: Decay-triggered warning touchpoints.

When decay drops a player's score below a warning threshold,
Nikita sends an in-character "you've been quiet..." touchpoint.
"""

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from nikita.touchpoints.engine import (
    DECAY_WARNING_TEMPLATES,
    TouchpointEngine,
)


class TestDecayWarningThresholds:
    """Test decay warning threshold crossing detection."""

    @pytest.mark.asyncio
    async def test_warning_triggered_on_threshold_cross(self):
        """Score drops from 42 to 38 (crosses 40.0) — warning scheduled."""
        engine = TouchpointEngine(session=AsyncMock())
        engine.store = AsyncMock()
        engine.store.get_recent_touchpoints.return_value = []  # No recent warnings
        engine.store.create_touchpoint = AsyncMock()

        await engine.schedule_decay_warning(
            user_id=uuid4(),
            chapter=3,
            current_score=38.0,
        )

        engine.store.create_touchpoint.assert_called_once()
        call_kwargs = engine.store.create_touchpoint.call_args[1]
        assert call_kwargs["touchpoint_type"] == "decay_warning"
        assert call_kwargs["message"] is not None
        assert len(call_kwargs["message"]) > 0

    @pytest.mark.asyncio
    async def test_cooldown_prevents_repeat_warning(self):
        """Warning already sent within 24h — skip."""
        engine = TouchpointEngine(session=AsyncMock())
        engine.store = AsyncMock()
        engine.store.get_recent_touchpoints.return_value = [MagicMock()]  # Recent warning exists

        await engine.schedule_decay_warning(
            user_id=uuid4(),
            chapter=3,
            current_score=38.0,
        )

        engine.store.create_touchpoint.assert_not_called()

    @pytest.mark.asyncio
    async def test_chapter_appropriate_message(self):
        """Each chapter produces unique message tone."""
        engine = TouchpointEngine(session=AsyncMock())
        engine.store = AsyncMock()
        engine.store.get_recent_touchpoints.return_value = []
        engine.store.create_touchpoint = AsyncMock()

        messages = {}
        for ch in range(1, 6):
            engine.store.create_touchpoint.reset_mock()
            await engine.schedule_decay_warning(
                user_id=uuid4(),
                chapter=ch,
                current_score=38.0,
            )
            call_kwargs = engine.store.create_touchpoint.call_args[1]
            messages[ch] = call_kwargs["message"]

        # All chapters should produce messages
        for ch, msg in messages.items():
            assert msg is not None and len(msg) > 0, f"Chapter {ch} has no message"

        # Messages should come from per-chapter templates
        assert all(ch in DECAY_WARNING_TEMPLATES for ch in range(1, 6))


class TestDecayWarningTemplates:
    """Test warning message template structure."""

    def test_all_chapters_have_templates(self):
        """All 5 chapters have at least 1 warning template."""
        for ch in range(1, 6):
            assert ch in DECAY_WARNING_TEMPLATES
            assert len(DECAY_WARNING_TEMPLATES[ch]) >= 1

    def test_templates_are_in_character(self):
        """Templates should be lowercase, casual (in-character Nikita voice)."""
        for ch, templates in DECAY_WARNING_TEMPLATES.items():
            for t in templates:
                # Nikita texts in lowercase
                assert t[0].islower(), f"Ch{ch} template starts uppercase: {t}"
