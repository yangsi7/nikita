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


class TestCheckByTelegramId:
    """Spec 115 FR-002/FR-006: check_by_telegram_id uses telegram_id (int) as key."""

    @pytest.mark.asyncio
    async def test_check_by_telegram_id_allowed(self, rate_limiter, mock_cache):
        """First call for a telegram_id returns allowed=True."""
        mock_cache.incr.return_value = 1
        result = await rate_limiter.check_by_telegram_id(telegram_id=123456789)
        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_check_by_telegram_id_minute_exceeded(self, rate_limiter, mock_cache):
        """21st call in a minute returns allowed=False, reason=minute_limit_exceeded."""
        mock_cache.incr.return_value = 21
        result = await rate_limiter.check_by_telegram_id(telegram_id=123456789)
        assert result.allowed is False
        assert result.reason == "minute_limit_exceeded"
        assert result.retry_after_seconds == 60

    @pytest.mark.asyncio
    async def test_check_by_telegram_id_day_exceeded(self, rate_limiter, mock_cache):
        """501st call in a day returns allowed=False, reason=day_limit_exceeded."""
        # minute count stays low, day count exceeds
        mock_cache.incr.side_effect = [1, 501]
        result = await rate_limiter.check_by_telegram_id(telegram_id=123456789)
        assert result.allowed is False
        assert result.reason == "day_limit_exceeded"

    @pytest.mark.asyncio
    async def test_check_by_telegram_id_different_ids_independent(
        self, rate_limiter, mock_cache
    ):
        """Different telegram_ids track independently (separate cache keys)."""
        mock_cache.incr.return_value = 1
        r1 = await rate_limiter.check_by_telegram_id(telegram_id=111)
        r2 = await rate_limiter.check_by_telegram_id(telegram_id=222)
        assert r1.allowed is True
        assert r2.allowed is True
        # Two separate calls → two separate cache interactions per call
        assert mock_cache.incr.call_count == 4  # 2 keys × 2 telegram_ids


# =====================================================================
# GAP-002: DatabaseRateLimiter tests (mock AsyncSession)
# =====================================================================


from nikita.platforms.telegram.rate_limiter import DatabaseRateLimiter


class _FakeScalarResult:
    """Minimal stand-in for SQLAlchemy scalar results."""

    def __init__(self, value):
        self._value = value

    def scalar_one(self):
        return self._value

    def scalar_one_or_none(self):
        return self._value


@pytest.fixture
def mock_session():
    """Mock AsyncSession for DatabaseRateLimiter."""
    session = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def db_rate_limiter(mock_session):
    return DatabaseRateLimiter(session=mock_session)


class TestDatabaseRateLimiterCheck:
    """DatabaseRateLimiter.check() with mocked DB session."""

    @pytest.mark.asyncio
    async def test_db_rate_limiter_check_allows_under_limit(
        self, db_rate_limiter, mock_session
    ):
        """Counts well under limits → allowed=True."""
        mock_session.execute = AsyncMock(
            side_effect=[_FakeScalarResult(1), _FakeScalarResult(1)]
        )
        result = await db_rate_limiter.check(uuid4())
        assert result.allowed is True
        assert result.minute_remaining == 19
        assert result.day_remaining == 499

    @pytest.mark.asyncio
    async def test_db_rate_limiter_check_rejects_at_minute_limit(
        self, db_rate_limiter, mock_session
    ):
        """minute count > 20 → blocked with reason=minute_limit_exceeded."""
        mock_session.execute = AsyncMock(
            side_effect=[_FakeScalarResult(21), _FakeScalarResult(5)]
        )
        result = await db_rate_limiter.check(uuid4())
        assert result.allowed is False
        assert result.reason == "minute_limit_exceeded"
        assert result.retry_after_seconds == 60

    @pytest.mark.asyncio
    async def test_db_rate_limiter_check_rejects_at_day_limit(
        self, db_rate_limiter, mock_session
    ):
        """day count > 500 → blocked with reason=day_limit_exceeded."""
        mock_session.execute = AsyncMock(
            side_effect=[_FakeScalarResult(5), _FakeScalarResult(501)]
        )
        result = await db_rate_limiter.check(uuid4())
        assert result.allowed is False
        assert result.reason == "day_limit_exceeded"
        assert result.day_remaining == 0

    @pytest.mark.asyncio
    async def test_db_rate_limiter_check_by_telegram_id(
        self, db_rate_limiter, mock_session
    ):
        """check_by_telegram_id derives UUID and delegates to check()."""
        mock_session.execute = AsyncMock(
            side_effect=[_FakeScalarResult(1), _FakeScalarResult(1)]
        )
        result = await db_rate_limiter.check_by_telegram_id(telegram_id=12345)
        assert result.allowed is True


class TestDatabaseRateLimiterGetRemaining:
    """DatabaseRateLimiter.get_remaining() — read-only quota check."""

    @pytest.mark.asyncio
    async def test_db_rate_limiter_get_remaining(
        self, db_rate_limiter, mock_session
    ):
        """Returns remaining counts without incrementing."""
        mock_session.execute = AsyncMock(
            side_effect=[_FakeScalarResult(10), _FakeScalarResult(100)]
        )
        remaining = await db_rate_limiter.get_remaining(uuid4())
        assert remaining["minute_remaining"] == 10
        assert remaining["day_remaining"] == 400
        assert remaining["minute_used"] == 10
        assert remaining["day_used"] == 100


class TestDatabaseRateLimiterWindows:
    """Window format strings."""

    def test_db_rate_limiter_minute_window_format(self, db_rate_limiter):
        """minute window → 'minute:YYYY-MM-DD-HH-MM'."""
        window = db_rate_limiter._get_minute_window()
        assert window.startswith("minute:")
        parts = window.split(":")[1].split("-")
        assert len(parts) == 5  # YYYY-MM-DD-HH-MM

    def test_db_rate_limiter_day_window_format(self, db_rate_limiter):
        """day window → 'day:YYYY-MM-DD'."""
        window = db_rate_limiter._get_day_window()
        assert window.startswith("day:")
        parts = window.split(":")[1].split("-")
        assert len(parts) == 3  # YYYY-MM-DD


class TestDatabaseRateLimiterSessionError:
    """Verify session errors propagate (caller handles them)."""

    @pytest.mark.asyncio
    async def test_db_rate_limiter_handles_session_error(
        self, db_rate_limiter, mock_session
    ):
        """DB error during check → exception propagates."""
        mock_session.execute = AsyncMock(side_effect=RuntimeError("connection lost"))
        with pytest.raises(RuntimeError, match="connection lost"):
            await db_rate_limiter.check(uuid4())
