"""Tests for Touchpoint Intelligence enrichment (Spec 103).

FR-001: Life events wired to message generator
FR-002: PsycheState loaded into StrategicSilence
FR-003: Content deduplication (SequenceMatcher on last 5 delivered)
FR-004: Open conversation threads injected into generation prompt
FR-005: Top vice categories injected into generation prompt
"""

from difflib import SequenceMatcher
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.touchpoints.silence import StrategicSilence


def _make_engine():
    """Create TouchpointEngine with mocked generator (no API key needed)."""
    from nikita.touchpoints.engine import TouchpointEngine

    with patch("nikita.touchpoints.engine.MessageGenerator"):
        engine = TouchpointEngine(AsyncMock())

    # Replace generator with a controllable mock
    engine.generator = AsyncMock()
    engine.generator.generate = AsyncMock(return_value="Hey!")
    return engine


# ===== FR-001: Life Events =====

class TestLifeEventsWiring:
    """Test that life events are passed to message generation."""

    @pytest.mark.asyncio
    async def test_generate_message_passes_life_events(self):
        """FR-001: _generate_message passes life_event_description from trigger_context."""
        engine = _make_engine()
        engine.generator.generate = AsyncMock(return_value="Hey babe!")

        touchpoint = MagicMock()
        touchpoint.user_id = uuid4()
        touchpoint.trigger_context = MagicMock()
        touchpoint.trigger_context.life_event_description = "Got a promotion at work"

        engine._load_open_threads = AsyncMock(return_value=[])
        engine._load_top_vices = AsyncMock(return_value=[])

        result = await engine._generate_message(touchpoint)

        engine.generator.generate.assert_called_once()
        call_kwargs = engine.generator.generate.call_args[1]
        assert call_kwargs.get("life_event_description") == "Got a promotion at work"

    @pytest.mark.asyncio
    async def test_generate_message_handles_no_life_event(self):
        """FR-001: Graceful when no life_event_description in trigger_context."""
        engine = _make_engine()

        touchpoint = MagicMock()
        touchpoint.user_id = uuid4()
        touchpoint.trigger_context = MagicMock()
        touchpoint.trigger_context.life_event_description = None

        engine._load_open_threads = AsyncMock(return_value=[])
        engine._load_top_vices = AsyncMock(return_value=[])

        result = await engine._generate_message(touchpoint)

        engine.generator.generate.assert_called_once()
        call_kwargs = engine.generator.generate.call_args[1]
        assert call_kwargs.get("life_event_description") is None


# ===== FR-002: PsycheState in Silence =====

class TestPsycheStateSilence:
    """Test PsycheState integration into StrategicSilence."""

    def test_defense_mode_guarded_increases_silence(self):
        """FR-002: defense_mode='guarded' increases silence modifier."""
        silence = StrategicSilence()

        emotional_state = {"valence": 0.5, "arousal": 0.5, "dominance": 0.5}
        psyche_state = {"defense_mode": "guarded", "attachment_activation": "secure"}

        modifier = silence._compute_emotional_modifier(
            emotional_state, psyche_state=psyche_state,
        )

        # Guarded should increase modifier above baseline 1.0
        assert modifier > 1.0

    def test_defense_mode_withdrawing_increases_silence_more(self):
        """FR-002: defense_mode='withdrawing' increases silence more than 'guarded'."""
        silence = StrategicSilence()

        emotional_state = {"valence": 0.5, "arousal": 0.5, "dominance": 0.5}

        mod_guarded = silence._compute_emotional_modifier(
            emotional_state,
            psyche_state={"defense_mode": "guarded", "attachment_activation": "secure"},
        )
        mod_withdrawing = silence._compute_emotional_modifier(
            emotional_state,
            psyche_state={"defense_mode": "withdrawing", "attachment_activation": "secure"},
        )

        assert mod_withdrawing > mod_guarded

    def test_attachment_anxious_increases_silence(self):
        """FR-002: attachment_activation='anxious' increases silence modifier."""
        silence = StrategicSilence()

        emotional_state = {"valence": 0.5, "arousal": 0.5, "dominance": 0.5}

        mod_secure = silence._compute_emotional_modifier(
            emotional_state,
            psyche_state={"defense_mode": "open", "attachment_activation": "secure"},
        )
        mod_anxious = silence._compute_emotional_modifier(
            emotional_state,
            psyche_state={"defense_mode": "open", "attachment_activation": "anxious"},
        )

        assert mod_anxious > mod_secure

    def test_no_psyche_state_uses_default(self):
        """FR-002: None psyche_state doesn't crash, uses default modifier."""
        silence = StrategicSilence()

        emotional_state = {"valence": 0.5, "arousal": 0.5, "dominance": 0.5}

        modifier = silence._compute_emotional_modifier(
            emotional_state, psyche_state=None,
        )

        assert modifier == 1.0


# ===== FR-003: Content Deduplication =====

class TestContentDedup:
    """Test content deduplication for touchpoint messages."""

    @pytest.mark.asyncio
    async def test_duplicate_message_detected(self):
        """FR-003: Identical message detected as duplicate."""
        engine = _make_engine()
        recent = ["Hey, thinking about you!", "What are you up to?"]
        assert engine.is_content_duplicate("Hey, thinking about you!", recent) is True

    @pytest.mark.asyncio
    async def test_similar_message_detected(self):
        """FR-003: Similar message (>0.7) detected as duplicate."""
        engine = _make_engine()
        recent = ["Hey, I was thinking about you today!"]
        assert engine.is_content_duplicate(
            "Hey, I was thinking about you!", recent,
        ) is True

    @pytest.mark.asyncio
    async def test_different_message_not_duplicate(self):
        """FR-003: Different message passes dedup."""
        engine = _make_engine()
        recent = ["Hey, thinking about you!"]
        assert engine.is_content_duplicate(
            "Just got back from the gym, feeling great", recent,
        ) is False

    @pytest.mark.asyncio
    async def test_empty_recent_not_duplicate(self):
        """FR-003: Empty recent list = no duplicate."""
        engine = _make_engine()
        assert engine.is_content_duplicate("Hello", []) is False


# ===== FR-004: Thread Injection =====

class TestThreadInjection:
    """Test open conversation threads injected into generation."""

    @pytest.mark.asyncio
    async def test_generate_message_includes_threads(self):
        """FR-004: Open threads passed to generator as context."""
        engine = _make_engine()
        engine.generator.generate = AsyncMock(return_value="Hey about that trip...")

        touchpoint = MagicMock()
        touchpoint.user_id = uuid4()
        touchpoint.trigger_context = MagicMock()
        touchpoint.trigger_context.life_event_description = None

        engine._load_open_threads = AsyncMock(
            return_value=["planning weekend trip", "discussing favorite movies"],
        )
        engine._load_top_vices = AsyncMock(return_value=[])

        result = await engine._generate_message(touchpoint)

        call_kwargs = engine.generator.generate.call_args[1]
        assert "open_threads" in call_kwargs
        assert len(call_kwargs["open_threads"]) == 2

    @pytest.mark.asyncio
    async def test_generate_message_handles_no_threads(self):
        """FR-004: No threads = empty list passed to generator."""
        engine = _make_engine()

        touchpoint = MagicMock()
        touchpoint.user_id = uuid4()
        touchpoint.trigger_context = MagicMock()
        touchpoint.trigger_context.life_event_description = None

        engine._load_open_threads = AsyncMock(return_value=[])
        engine._load_top_vices = AsyncMock(return_value=[])

        result = await engine._generate_message(touchpoint)

        call_kwargs = engine.generator.generate.call_args[1]
        assert call_kwargs.get("open_threads") == []


# ===== FR-005: Vice Hints =====

class TestViceHints:
    """Test top vice categories injected into generation."""

    @pytest.mark.asyncio
    async def test_generate_message_includes_vice_hints(self):
        """FR-005: Top 2 vice categories passed to generator."""
        engine = _make_engine()
        engine.generator.generate = AsyncMock(return_value="Something edgy...")

        touchpoint = MagicMock()
        touchpoint.user_id = uuid4()
        touchpoint.trigger_context = MagicMock()
        touchpoint.trigger_context.life_event_description = None

        engine._load_open_threads = AsyncMock(return_value=[])
        engine._load_top_vices = AsyncMock(
            return_value=["dark_humor", "intellectual_dominance"],
        )

        result = await engine._generate_message(touchpoint)

        call_kwargs = engine.generator.generate.call_args[1]
        assert "vice_hints" in call_kwargs
        assert call_kwargs["vice_hints"] == ["dark_humor", "intellectual_dominance"]

    @pytest.mark.asyncio
    async def test_generate_message_handles_no_vices(self):
        """FR-005: No vices = empty list."""
        engine = _make_engine()

        touchpoint = MagicMock()
        touchpoint.user_id = uuid4()
        touchpoint.trigger_context = MagicMock()
        touchpoint.trigger_context.life_event_description = None

        engine._load_open_threads = AsyncMock(return_value=[])
        engine._load_top_vices = AsyncMock(return_value=[])

        result = await engine._generate_message(touchpoint)

        call_kwargs = engine.generator.generate.call_args[1]
        assert call_kwargs.get("vice_hints") == []
