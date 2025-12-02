"""
Tests for RateLimiter class - prevents abuse while maintaining good UX.

Acceptance Criteria:
- AC-FR006-001: Given 21+ messages in 1 minute, When rate limit hit, Then user informed gracefully
- AC-FR006-002: Given user at 450/500 daily, When approaching limit, Then subtle warning
- AC-FR006-003: Given rate limit expires, When cooldown complete, Then normal messaging

TDD Approach: Tests written BEFORE implementation (expect FAIL initially).
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, Mock

from nikita.platforms.telegram.rate_limiter import RateLimiter, RateLimitResult


@pytest.fixture
def mock_cache():
    """Mock cache client for rate limit tracking."""
    cache = Mock()
    cache.incr = AsyncMock()
    cache.expire = AsyncMock()
    cache.get = AsyncMock()
    return cache


@pytest.fixture
def rate_limiter(mock_cache):
    """Create RateLimiter with mocked cache."""
    return RateLimiter(cache=mock_cache)


class TestRateLimiter:
    """Test suite for US-4: Rate Limiting Protection."""

    @pytest.mark.asyncio
    async def test_ac_fr006_001_rate_limit_hit_after_20_messages_per_minute(
        self,
        rate_limiter,
        mock_cache,
    ):
        """
        AC-FR006-001: Given user sends 21+ messages in 1 minute,
        When rate limit hit, Then user is informed gracefully.

        Implementation: Track per-minute limit (20 max) via cache.
        """
        user_id = uuid4()

        # Simulate 20 messages (should all pass)
        for i in range(1, 21):
            mock_cache.incr.return_value = i
            result = await rate_limiter.check(user_id)
            assert result.allowed is True, f"Message {i} should be allowed"

        # 21st message (should be rate limited)
        mock_cache.incr.return_value = 21
        result = await rate_limiter.check(user_id)

        assert result.allowed is False
        assert result.reason == "minute_limit_exceeded"
        assert result.retry_after_seconds > 0  # Time until minute resets

    @pytest.mark.asyncio
    async def test_ac_t024_1_check_returns_rate_limit_status(
        self,
        rate_limiter,
        mock_cache,
    ):
        """
        AC-T024.1: `check(user_id)` returns RateLimitResult with allowed status.
        """
        user_id = uuid4()

        # First message: allowed
        mock_cache.incr.return_value = 1
        result = await rate_limiter.check(user_id)

        assert isinstance(result, RateLimitResult)
        assert result.allowed is True
        assert result.reason is None
        assert result.minute_remaining is not None
        assert result.day_remaining is not None

    @pytest.mark.asyncio
    async def test_ac_t024_2_tracks_per_minute_and_per_day_limits(
        self,
        rate_limiter,
        mock_cache,
    ):
        """
        AC-T024.2: Tracks per-minute (20 max) and per-day (500 max) limits.
        """
        user_id = uuid4()

        # Mock: 19 messages this minute, 499 messages today
        async def mock_incr(key):
            if "minute" in key:
                return 19  # Below minute limit
            elif "day" in key:
                return 499  # Below daily limit
            return 0

        mock_cache.incr.side_effect = mock_incr

        result = await rate_limiter.check(user_id)

        # Both limits under threshold
        assert result.allowed is True
        assert result.minute_remaining == 1  # 20 - 19
        assert result.day_remaining == 1  # 500 - 499

        # Verify cache.incr called for both keys
        assert mock_cache.incr.call_count == 2
        call_keys = [call[0][0] for call in mock_cache.incr.call_args_list]
        assert any("minute" in key for key in call_keys)
        assert any("day" in key for key in call_keys)

    @pytest.mark.asyncio
    async def test_ac_fr006_002_warning_when_approaching_daily_limit(
        self,
        rate_limiter,
        mock_cache,
    ):
        """
        AC-FR006-002: Given user at 450/500 daily,
        When approaching limit, Then subtle warning is provided.
        """
        user_id = uuid4()

        # Mock: 450 messages today (90% of daily limit)
        async def mock_incr(key):
            if "minute" in key:
                return 5  # Fine on minute
            elif "day" in key:
                return 450  # Approaching daily limit
            return 0

        mock_cache.incr.side_effect = mock_incr

        result = await rate_limiter.check(user_id)

        # Still allowed but with warning
        assert result.allowed is True
        assert result.warning_threshold_reached is True
        assert result.day_remaining == 50  # 500 - 450

    @pytest.mark.asyncio
    async def test_daily_limit_exceeded_blocks_message(
        self,
        rate_limiter,
        mock_cache,
    ):
        """
        Test: Given user at 501/500 daily, When messaging, Then blocked.
        """
        user_id = uuid4()

        # Mock: Daily limit exceeded
        async def mock_incr(key):
            if "minute" in key:
                return 1
            elif "day" in key:
                return 501  # Over daily limit
            return 0

        mock_cache.incr.side_effect = mock_incr

        result = await rate_limiter.check(user_id)

        assert result.allowed is False
        assert result.reason == "day_limit_exceeded"
        assert result.retry_after_seconds > 0  # Time until day resets

    @pytest.mark.asyncio
    async def test_ac_t024_4_keys_expire_appropriately(
        self,
        rate_limiter,
        mock_cache,
    ):
        """
        AC-T024.4: Keys expire appropriately (60s for minute, 24h for day).
        """
        user_id = uuid4()

        # Mock: First message (both counters == 1)
        mock_cache.incr.return_value = 1

        await rate_limiter.check(user_id)

        # Verify cache.expire called with correct TTL
        assert mock_cache.expire.call_count == 2

        expire_calls = mock_cache.expire.call_args_list
        ttls = {call[0][1] for call in expire_calls}

        assert 60 in ttls  # Minute key expires in 60 seconds
        assert 86400 in ttls  # Day key expires in 86400 seconds (24 hours)

    @pytest.mark.asyncio
    async def test_ac_fr006_003_rate_limit_resets_after_cooldown(
        self,
        rate_limiter,
        mock_cache,
    ):
        """
        AC-FR006-003: Given rate limit expires,
        When cooldown complete, Then normal messaging resumes.

        Implementation: Minute key expires after 60s, counter resets to 1.
        """
        user_id = uuid4()

        # Scenario: User was rate limited (21 messages in minute)
        mock_cache.incr.return_value = 21
        result1 = await rate_limiter.check(user_id)
        assert result1.allowed is False

        # After cooldown (minute key expired, counter reset)
        mock_cache.incr.return_value = 1  # Fresh minute
        result2 = await rate_limiter.check(user_id)

        assert result2.allowed is True
        assert result2.reason is None

    @pytest.mark.asyncio
    async def test_ac_t024_3_get_remaining_returns_quota_info(
        self,
        rate_limiter,
        mock_cache,
    ):
        """
        AC-T024.3: `get_remaining(user_id)` returns quota information.
        """
        user_id = uuid4()

        # Mock: 15 messages this minute, 300 messages today
        async def mock_get(key):
            if "minute" in key:
                return 15
            elif "day" in key:
                return 300
            return 0

        mock_cache.get.side_effect = mock_get

        result = await rate_limiter.get_remaining(user_id)

        assert result["minute_remaining"] == 5  # 20 - 15
        assert result["day_remaining"] == 200  # 500 - 300
        assert result["minute_used"] == 15
        assert result["day_used"] == 300

    @pytest.mark.asyncio
    async def test_multiple_users_isolated(
        self,
        rate_limiter,
        mock_cache,
    ):
        """
        Test: Different users have independent rate limits.
        """
        user1_id = uuid4()
        user2_id = uuid4()

        # Mock: User 1 at limit, User 2 fresh
        call_count = {"user1": 0, "user2": 0}

        async def mock_incr(key):
            if str(user1_id) in key:
                call_count["user1"] += 1
                return 21 if call_count["user1"] > 1 else 1
            elif str(user2_id) in key:
                call_count["user2"] += 1
                return 1
            return 0

        mock_cache.incr.side_effect = mock_incr

        # User 1: rate limited
        result1 = await rate_limiter.check(user1_id)
        result1_again = await rate_limiter.check(user1_id)

        # User 2: allowed
        result2 = await rate_limiter.check(user2_id)

        # User 1 blocked, User 2 allowed
        assert result1_again.allowed is False  # User 1 at limit
        assert result2.allowed is True  # User 2 fresh

    @pytest.mark.asyncio
    async def test_edge_case_exactly_20_messages_allowed(
        self,
        rate_limiter,
        mock_cache,
    ):
        """
        Edge case: 20th message should be allowed, 21st should be blocked.
        """
        user_id = uuid4()

        # 20th message
        mock_cache.incr.return_value = 20
        result = await rate_limiter.check(user_id)
        assert result.allowed is True

        # 21st message
        mock_cache.incr.return_value = 21
        result = await rate_limiter.check(user_id)
        assert result.allowed is False
