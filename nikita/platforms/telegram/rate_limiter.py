"""
Rate limiter for Telegram messages - prevents abuse while maintaining good UX.

Limits:
- Per-minute: 20 messages maximum
- Per-day: 500 messages maximum

Implementations:
- InMemoryCache: For development/testing (doesn't persist across restarts)
- DatabaseRateLimiter: For production (persists in PostgreSQL)
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, TYPE_CHECKING
from uuid import UUID
import asyncio
import time

from sqlalchemy import select, update, and_
from sqlalchemy.dialects.postgresql import insert

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from nikita.db.models.rate_limit import RateLimit


class InMemoryCache:
    """
    Simple in-memory cache with TTL support.

    Provides Redis-like interface for rate limiting.
    Note: Does not persist across restarts, suitable for MVP/alpha.
    """

    def __init__(self):
        self._store: dict[str, int] = {}
        self._expiry: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def incr(self, key: str) -> int:
        """Increment counter and return new value."""
        async with self._lock:
            self._cleanup_expired()
            self._store[key] = self._store.get(key, 0) + 1
            return self._store[key]

    async def expire(self, key: str, seconds: int) -> None:
        """Set expiration time for a key."""
        async with self._lock:
            self._expiry[key] = time.time() + seconds

    async def get(self, key: str) -> int:
        """Get current value (returns 0 if not exists or expired)."""
        async with self._lock:
            self._cleanup_expired()
            return self._store.get(key, 0)

    def _cleanup_expired(self) -> None:
        """Remove expired keys (called within lock)."""
        now = time.time()
        expired_keys = [
            key for key, exp_time in self._expiry.items() if exp_time <= now
        ]
        for key in expired_keys:
            self._store.pop(key, None)
            self._expiry.pop(key, None)


# Singleton cache instance for rate limiting
_shared_cache: InMemoryCache | None = None


def get_shared_cache() -> InMemoryCache:
    """Get shared InMemoryCache instance (singleton)."""
    global _shared_cache
    if _shared_cache is None:
        _shared_cache = InMemoryCache()
    return _shared_cache


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
        now = datetime.now(timezone.utc)
        midnight = datetime.combine(
            now.date(),
            datetime.min.time(),
            tzinfo=timezone.utc,
        )
        midnight = midnight + timedelta(days=1)  # Next midnight (handles month boundaries)
        seconds = int((midnight - now).total_seconds())
        return seconds


class DatabaseRateLimiter:
    """
    Database-backed rate limiter for production use.

    Stores rate limit counters in PostgreSQL, enabling:
    - Persistence across service restarts
    - Rate limiting across multiple Cloud Run instances
    - Automatic cleanup of expired records

    Uses the same interface as RateLimiter for drop-in replacement.
    """

    # Configuration (same as RateLimiter)
    MAX_PER_MINUTE = 20
    MAX_PER_DAY = 500
    WARNING_THRESHOLD = 450

    def __init__(self, session: "AsyncSession"):
        """
        Initialize DatabaseRateLimiter.

        Args:
            session: SQLAlchemy async session for database access.
        """
        self.session = session

    async def check(self, user_id: UUID) -> RateLimitResult:
        """
        Check if user is within rate limits using database.

        Uses PostgreSQL UPSERT (INSERT ... ON CONFLICT) for atomic increment.

        Args:
            user_id: User to check.

        Returns:
            RateLimitResult with allowed status and remaining quota.
        """
        from nikita.db.models.rate_limit import RateLimit

        now = datetime.now(timezone.utc)

        # Generate window identifiers
        minute_window = self._get_minute_window()
        day_window = self._get_day_window()

        # Calculate expiration times
        minute_expires = now + timedelta(seconds=60)
        day_expires = now + timedelta(days=1)

        # Atomic increment for minute window
        minute_stmt = (
            insert(RateLimit)
            .values(
                user_id=user_id,
                window=minute_window,
                count=1,
                expires_at=minute_expires,
            )
            .on_conflict_do_update(
                constraint="uq_rate_limit_user_window",
                set_={"count": RateLimit.count + 1},
            )
            .returning(RateLimit.count)
        )
        minute_result = await self.session.execute(minute_stmt)
        minute_count = minute_result.scalar_one()

        # Atomic increment for day window
        day_stmt = (
            insert(RateLimit)
            .values(
                user_id=user_id,
                window=day_window,
                count=1,
                expires_at=day_expires,
            )
            .on_conflict_do_update(
                constraint="uq_rate_limit_user_window",
                set_={"count": RateLimit.count + 1},
            )
            .returning(RateLimit.count)
        )
        day_result = await self.session.execute(day_stmt)
        day_count = day_result.scalar_one()

        # Commit the increments
        await self.session.commit()

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
                retry_after_seconds=60,
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
        Get remaining quota for user without incrementing counters.

        Args:
            user_id: User to check.

        Returns:
            Dictionary with quota information.
        """
        from nikita.db.models.rate_limit import RateLimit

        minute_window = self._get_minute_window()
        day_window = self._get_day_window()
        now = datetime.now(timezone.utc)

        # Query current counts
        minute_stmt = select(RateLimit.count).where(
            and_(
                RateLimit.user_id == user_id,
                RateLimit.window == minute_window,
                RateLimit.expires_at > now,
            )
        )
        minute_result = await self.session.execute(minute_stmt)
        minute_count = minute_result.scalar_one_or_none() or 0

        day_stmt = select(RateLimit.count).where(
            and_(
                RateLimit.user_id == user_id,
                RateLimit.window == day_window,
                RateLimit.expires_at > now,
            )
        )
        day_result = await self.session.execute(day_stmt)
        day_count = day_result.scalar_one_or_none() or 0

        return {
            "minute_remaining": max(0, self.MAX_PER_MINUTE - minute_count),
            "day_remaining": max(0, self.MAX_PER_DAY - day_count),
            "minute_used": minute_count,
            "day_used": day_count,
        }

    def _get_minute_window(self) -> str:
        """
        Generate window identifier for current minute.

        Format: "minute:<YYYY-MM-DD-HH-MM>"
        """
        now = datetime.now(timezone.utc)
        return f"minute:{now.strftime('%Y-%m-%d-%H-%M')}"

    def _get_day_window(self) -> str:
        """
        Generate window identifier for current day.

        Format: "day:<YYYY-MM-DD>"
        """
        today = datetime.now(timezone.utc).date()
        return f"day:{today}"

    def _seconds_until_midnight(self) -> int:
        """Calculate seconds until midnight UTC (when daily limit resets)."""
        now = datetime.now(timezone.utc)
        midnight = datetime.combine(
            now.date(),
            datetime.min.time(),
            tzinfo=timezone.utc,
        )
        midnight = midnight + timedelta(days=1)
        seconds = int((midnight - now).total_seconds())
        return seconds
