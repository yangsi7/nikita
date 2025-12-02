"""
Rate limiter for Telegram messages - prevents abuse while maintaining good UX.

Limits:
- Per-minute: 20 messages maximum
- Per-day: 500 messages maximum

Implementation uses Redis or in-memory cache with automatic key expiration.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID


@dataclass
class RateLimitResult:
    """
    Result of rate limit check.

    Attributes:
        allowed: Whether the message is allowed (within limits)
        reason: Reason for blocking, if applicable ("minute_limit_exceeded" or "day_limit_exceeded")
        minute_remaining: How many messages remaining this minute
        day_remaining: How many messages remaining today
        retry_after_seconds: How long to wait before retrying (if blocked)
        warning_threshold_reached: True if user is approaching daily limit (450+)
    """

    allowed: bool
    reason: Optional[str] = None
    minute_remaining: Optional[int] = None
    day_remaining: Optional[int] = None
    retry_after_seconds: Optional[int] = None
    warning_threshold_reached: bool = False


class RateLimiter:
    """
    Rate limiting for Telegram messages.

    Prevents abuse while maintaining good UX through:
    1. Per-minute limit (20 max) - prevents spam bursts
    2. Per-day limit (500 max) - prevents sustained abuse
    3. Graceful warnings (at 450/500) - gives user heads-up
    4. Automatic key expiration - Redis/cache handles cleanup
    """

    # Configuration
    MAX_PER_MINUTE = 20
    MAX_PER_DAY = 500
    WARNING_THRESHOLD = 450  # Warn when user reaches 90% of daily limit

    def __init__(self, cache: Any):
        """
        Initialize RateLimiter.

        Args:
            cache: Cache client (Redis or in-memory) with incr(), expire(), get() methods
        """
        self.cache = cache

    async def check(self, user_id: UUID) -> RateLimitResult:
        """
        Check if user is within rate limits.

        Args:
            user_id: User to check

        Returns:
            RateLimitResult with allowed status and remaining quota
        """
        # Generate cache keys
        minute_key = self._get_minute_key(user_id)
        day_key = self._get_day_key(user_id)

        # Increment counters
        minute_count = await self.cache.incr(minute_key)
        day_count = await self.cache.incr(day_key)

        # Set expiration on first message (counter == 1)
        if minute_count == 1:
            await self.cache.expire(minute_key, 60)  # 60 seconds

        if day_count == 1:
            await self.cache.expire(day_key, 86400)  # 24 hours

        # Calculate remaining quota
        minute_remaining = max(0, self.MAX_PER_MINUTE - minute_count)
        day_remaining = max(0, self.MAX_PER_DAY - day_count)

        # Check minute limit
        if minute_count > self.MAX_PER_MINUTE:
            return RateLimitResult(
                allowed=False,
                reason="minute_limit_exceeded",
                minute_remaining=0,
                day_remaining=day_remaining,
                retry_after_seconds=60,  # Wait until minute resets
                warning_threshold_reached=False,
            )

        # Check daily limit
        if day_count > self.MAX_PER_DAY:
            return RateLimitResult(
                allowed=False,
                reason="day_limit_exceeded",
                minute_remaining=minute_remaining,
                day_remaining=0,
                retry_after_seconds=self._seconds_until_midnight(),
                warning_threshold_reached=False,
            )

        # Check if approaching daily limit
        warning_threshold_reached = day_count >= self.WARNING_THRESHOLD

        # Allowed
        return RateLimitResult(
            allowed=True,
            reason=None,
            minute_remaining=minute_remaining,
            day_remaining=day_remaining,
            retry_after_seconds=None,
            warning_threshold_reached=warning_threshold_reached,
        )

    async def get_remaining(self, user_id: UUID) -> dict:
        """
        Get remaining quota for user (without incrementing counters).

        Args:
            user_id: User to check

        Returns:
            Dictionary with quota information:
            - minute_remaining: Messages remaining this minute
            - day_remaining: Messages remaining today
            - minute_used: Messages used this minute
            - day_used: Messages used today
        """
        minute_key = self._get_minute_key(user_id)
        day_key = self._get_day_key(user_id)

        # Get current counts (without incrementing)
        minute_count = await self.cache.get(minute_key) or 0
        day_count = await self.cache.get(day_key) or 0

        return {
            "minute_remaining": max(0, self.MAX_PER_MINUTE - minute_count),
            "day_remaining": max(0, self.MAX_PER_DAY - day_count),
            "minute_used": minute_count,
            "day_used": day_count,
        }

    def _get_minute_key(self, user_id: UUID) -> str:
        """Generate cache key for per-minute limit."""
        return f"rate:{user_id}:minute"

    def _get_day_key(self, user_id: UUID) -> str:
        """Generate cache key for per-day limit."""
        today = datetime.now(timezone.utc).date()
        return f"rate:{user_id}:day:{today}"

    def _seconds_until_midnight(self) -> int:
        """Calculate seconds until midnight UTC (when daily limit resets)."""
        from datetime import timedelta

        now = datetime.now(timezone.utc)
        midnight = datetime.combine(
            now.date(),
            datetime.min.time(),
            tzinfo=timezone.utc,
        )
        midnight = midnight + timedelta(days=1)  # Next midnight (handles month boundaries)
        seconds = int((midnight - now).total_seconds())
        return seconds
