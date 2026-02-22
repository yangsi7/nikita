"""Tests for Call Availability (US-7: Voice Call Progression).

Tests for FR-011 acceptance criteria:
- AC-FR011-001: Chapter-based availability rates
- AC-FR011-002: Always available during boss fights
- AC-FR011-003: Blocked when game over/won
"""

from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

import pytest


class TestCallAvailability:
    """Test CallAvailability class (T033)."""

    @pytest.fixture
    def mock_user_ch1(self):
        """Create mock user in chapter 1."""
        user = MagicMock()
        user.id = uuid4()
        user.chapter = 1
        user.game_status = "active"
        user.metrics = MagicMock()
        user.metrics.relationship_score = Decimal("30.0")
        return user

    @pytest.fixture
    def mock_user_ch3(self):
        """Create mock user in chapter 3."""
        user = MagicMock()
        user.id = uuid4()
        user.chapter = 3
        user.game_status = "active"
        user.metrics = MagicMock()
        user.metrics.relationship_score = Decimal("65.0")
        return user

    @pytest.fixture
    def mock_user_ch5(self):
        """Create mock user in chapter 5."""
        user = MagicMock()
        user.id = uuid4()
        user.chapter = 5
        user.game_status = "active"
        user.metrics = MagicMock()
        user.metrics.relationship_score = Decimal("85.0")
        return user

    def test_chapter_1_low_availability(self, mock_user_ch1):
        """AC-FR011-001: Chapter 1 has 10% availability."""
        from nikita.agents.voice.availability import CallAvailability

        availability = CallAvailability()
        rate = availability.get_availability_rate(mock_user_ch1)

        # Chapter 1 should have 10% (0.1) base rate
        assert rate == 0.1

    def test_chapter_3_moderate_availability(self, mock_user_ch3):
        """AC-FR011-001: Chapter 3 has 80% availability."""
        from nikita.agents.voice.availability import CallAvailability

        availability = CallAvailability()
        rate = availability.get_availability_rate(mock_user_ch3)

        # Chapter 3 should have 80% (0.8) rate
        assert rate == 0.8

    def test_chapter_5_high_availability(self, mock_user_ch5):
        """AC-FR011-001: Chapter 5 has 95% availability."""
        from nikita.agents.voice.availability import CallAvailability

        availability = CallAvailability()
        rate = availability.get_availability_rate(mock_user_ch5)

        # Chapter 5 should have 95% (0.95) rate
        assert rate == 0.95

    def test_is_available_returns_tuple(self, mock_user_ch3):
        """AC-T033.1: is_available returns (available, reason) tuple."""
        from nikita.agents.voice.availability import CallAvailability

        availability = CallAvailability()
        result = availability.is_available(mock_user_ch3)

        assert isinstance(result, tuple)
        assert len(result) == 2
        is_available, reason = result
        assert isinstance(is_available, bool)
        assert isinstance(reason, str)

    def test_boss_fight_always_available(self):
        """AC-FR011-002: Boss fight always allows calls."""
        from nikita.agents.voice.availability import CallAvailability

        user = MagicMock()
        user.id = uuid4()
        user.chapter = 1  # Even chapter 1
        user.game_status = "boss_fight"
        user.metrics = MagicMock()
        user.metrics.relationship_score = Decimal("55.0")

        availability = CallAvailability()
        is_available, reason = availability.is_available(user)

        # Boss fight overrides chapter rate
        assert is_available is True
        assert "boss" in reason.lower()

    def test_game_over_blocks_calls(self):
        """AC-FR011-003: Game over blocks all calls."""
        from nikita.agents.voice.availability import CallAvailability

        user = MagicMock()
        user.id = uuid4()
        user.chapter = 5
        user.game_status = "game_over"
        user.metrics = MagicMock()
        user.metrics.relationship_score = Decimal("10.0")

        availability = CallAvailability()
        is_available, reason = availability.is_available(user)

        assert is_available is False
        assert "game" in reason.lower() and "over" in reason.lower()

    def test_game_won_blocks_calls(self):
        """AC-FR011-003: Game won blocks all calls."""
        from nikita.agents.voice.availability import CallAvailability

        user = MagicMock()
        user.id = uuid4()
        user.chapter = 5
        user.game_status = "won"
        user.metrics = MagicMock()
        user.metrics.relationship_score = Decimal("95.0")

        availability = CallAvailability()
        is_available, reason = availability.is_available(user)

        assert is_available is False
        assert "won" in reason.lower() or "complete" in reason.lower()

    def test_availability_rate_progression(self):
        """AC-T033.2: Rates progress by chapter (10, 40, 80, 90, 95)."""
        from nikita.agents.voice.availability import AVAILABILITY_RATES

        expected = {
            1: 0.1,
            2: 0.4,
            3: 0.8,
            4: 0.9,
            5: 0.95,
        }

        for chapter, expected_rate in expected.items():
            assert AVAILABILITY_RATES.get(chapter) == expected_rate


class TestAvailabilityWithRandomness:
    """Test availability with probabilistic checks."""

    def test_availability_uses_random_check(self):
        """Availability should use random check against rate."""
        from nikita.agents.voice.availability import CallAvailability
        from unittest.mock import patch

        user = MagicMock()
        user.id = uuid4()
        user.chapter = 3  # 80% rate
        user.game_status = "active"
        user.metrics = MagicMock()
        user.metrics.relationship_score = Decimal("60.0")

        availability = CallAvailability()

        # Mock random to always succeed
        with patch("nikita.agents.voice.availability.random") as mock_random:
            mock_random.random.return_value = 0.5  # < 0.8, should succeed
            is_available, _ = availability.is_available(user)
            assert is_available is True

        # Mock random to always fail
        with patch("nikita.agents.voice.availability.random") as mock_random:
            mock_random.random.return_value = 0.9  # > 0.8, should fail
            is_available, _ = availability.is_available(user)
            assert is_available is False

    def test_unavailable_provides_contextual_reason(self):
        """When unavailable, reason should be contextual."""
        from nikita.agents.voice.availability import CallAvailability
        from unittest.mock import patch

        user = MagicMock()
        user.id = uuid4()
        user.chapter = 1  # Only 10% rate
        user.game_status = "active"
        user.metrics = MagicMock()
        user.metrics.relationship_score = Decimal("25.0")

        availability = CallAvailability()

        # Force unavailable
        with patch("nikita.agents.voice.availability.random") as mock_random:
            mock_random.random.return_value = 0.99  # > 0.1, should fail
            mock_random.choice.return_value = "Nikita is busy with a work project right now."
            is_available, reason = availability.is_available(user)

            assert is_available is False
            # Should have a contextual reason about Nikita being busy
            assert len(reason) > 10


class TestCooldownCheck:
    """Tests for check_cooldown — 5-minute minimum gap between voice calls."""

    @pytest.fixture
    def mock_user(self):
        """Create a mock user."""
        user = MagicMock()
        user.id = uuid4()
        user.chapter = 3
        user.game_status = "active"
        return user

    @pytest.mark.asyncio
    async def test_no_prior_calls_allows_call(self, mock_user):
        """No prior voice conversations → no cooldown."""
        from nikita.agents.voice.availability import CallAvailability
        from unittest.mock import AsyncMock, MagicMock

        availability = CallAvailability()
        session = AsyncMock()
        # Simulate query returning None (no prior calls)
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        can_call, seconds_remaining = await availability.check_cooldown(mock_user, session)

        assert can_call is True
        assert seconds_remaining is None

    @pytest.mark.asyncio
    async def test_recent_call_blocks_with_remaining_seconds(self, mock_user):
        """Call ended 2 minutes ago → blocked with ~180 seconds remaining."""
        from nikita.agents.voice.availability import CallAvailability
        from unittest.mock import AsyncMock, MagicMock
        from datetime import datetime, timezone, timedelta

        # Simulate a call that ended 2 minutes ago
        two_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=2)

        availability = CallAvailability()
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = two_minutes_ago
        session.execute = AsyncMock(return_value=mock_result)

        can_call, seconds_remaining = await availability.check_cooldown(mock_user, session)

        assert can_call is False
        assert seconds_remaining is not None
        # 5 min cooldown - 2 min elapsed = ~3 min = ~180 seconds
        cooldown = availability.COOLDOWN_SECONDS
        assert (cooldown - 130) <= seconds_remaining <= cooldown

    @pytest.mark.asyncio
    async def test_old_call_allows_new_call(self, mock_user):
        """Call ended 10 minutes ago → cooldown expired, allow call."""
        from nikita.agents.voice.availability import CallAvailability
        from unittest.mock import AsyncMock, MagicMock
        from datetime import datetime, timezone, timedelta

        # Simulate a call that ended 10 minutes ago
        ten_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=10)

        availability = CallAvailability()
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = ten_minutes_ago
        session.execute = AsyncMock(return_value=mock_result)

        can_call, seconds_remaining = await availability.check_cooldown(mock_user, session)

        assert can_call is True
        assert seconds_remaining is None

    @pytest.mark.asyncio
    async def test_naive_datetime_handled_gracefully(self, mock_user):
        """check_cooldown handles naive datetimes from DB by treating them as UTC."""
        from nikita.agents.voice.availability import CallAvailability
        from unittest.mock import AsyncMock, MagicMock
        from datetime import datetime, timedelta

        # Naive datetime (no tzinfo) — 10 minutes ago
        ten_minutes_ago_naive = datetime.utcnow() - timedelta(minutes=10)

        availability = CallAvailability()
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = ten_minutes_ago_naive
        session.execute = AsyncMock(return_value=mock_result)

        # Should not raise; should treat naive datetime as UTC
        can_call, seconds_remaining = await availability.check_cooldown(mock_user, session)

        assert can_call is True
        assert seconds_remaining is None
