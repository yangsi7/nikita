"""Tests for Spec 051: Voice Pipeline Polish.

Covers:
1. Voice availability checks - boss_fight allows, game_over blocks, won blocks
2. Chapter-based availability rates
3. Cooldown check
"""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from nikita.agents.voice.availability import (
    AVAILABILITY_RATES,
    CallAvailability,
    get_availability_service,
)


def _mock_user(*, chapter=1, game_status="active"):
    """Create a mock user for availability tests."""
    user = MagicMock()
    user.id = uuid4()
    user.chapter = chapter
    user.game_status = game_status
    return user


class TestCallAvailabilityGameStatus:
    """Test voice availability based on game status."""

    def test_boss_fight_always_available(self):
        """AC-T033.4: Boss fight always allows calls."""
        availability = CallAvailability()
        user = _mock_user(game_status="boss_fight", chapter=1)

        is_avail, reason = availability.is_available(user)

        assert is_avail is True
        assert "boss" in reason.lower() or "Boss" in reason

    def test_game_over_blocks_calls(self):
        """AC-T033.3: Game over blocks all calls."""
        availability = CallAvailability()
        user = _mock_user(game_status="game_over", chapter=3)

        is_avail, reason = availability.is_available(user)

        assert is_avail is False

    def test_won_blocks_calls(self):
        """AC-T033.3: Won status blocks all calls."""
        availability = CallAvailability()
        user = _mock_user(game_status="won", chapter=5)

        is_avail, reason = availability.is_available(user)

        assert is_avail is False


class TestCallAvailabilityRates:
    """Test chapter-based availability rates."""

    def test_chapter_1_rate(self):
        """Chapter 1: 10% availability."""
        availability = CallAvailability()
        user = _mock_user(chapter=1)
        assert availability.get_availability_rate(user) == 0.1

    def test_chapter_3_rate(self):
        """Chapter 3: 80% availability."""
        availability = CallAvailability()
        user = _mock_user(chapter=3)
        assert availability.get_availability_rate(user) == 0.8

    def test_chapter_5_rate(self):
        """Chapter 5: 95% availability."""
        availability = CallAvailability()
        user = _mock_user(chapter=5)
        assert availability.get_availability_rate(user) == 0.95

    def test_unknown_chapter_defaults(self):
        """Unknown chapter defaults to 10%."""
        availability = CallAvailability()
        user = _mock_user(chapter=99)
        assert availability.get_availability_rate(user) == 0.1

    def test_all_chapters_have_rates(self):
        """All 5 chapters have defined rates."""
        for chapter in range(1, 6):
            assert chapter in AVAILABILITY_RATES


class TestCallAvailabilityCooldown:
    """Test cooldown check."""

    @pytest.mark.asyncio
    async def test_no_prior_calls_allows_call(self):
        """With no prior voice calls, cooldown returns can_call=True."""
        from unittest.mock import AsyncMock, MagicMock

        availability = CallAvailability()
        user = _mock_user()

        # Simulate no prior voice conversations (DB returns None)
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        can_call, remaining = await availability.check_cooldown(user, mock_session)

        assert can_call is True
        assert remaining is None


class TestAvailabilitySingleton:
    """Test singleton pattern for availability service."""

    def test_returns_instance(self):
        """get_availability_service returns a CallAvailability instance."""
        import nikita.agents.voice.availability as avail_module
        avail_module._availability = None
        service = get_availability_service()
        assert isinstance(service, CallAvailability)

    def test_returns_same_instance(self):
        """Singleton returns the same instance on subsequent calls."""
        import nikita.agents.voice.availability as avail_module
        avail_module._availability = None
        service1 = get_availability_service()
        service2 = get_availability_service()
        assert service1 is service2
