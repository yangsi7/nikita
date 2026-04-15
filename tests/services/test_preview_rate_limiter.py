"""Unit tests for _PreviewRateLimiter — Spec 213 PR 213-3.

TDD RED phase: tests written BEFORE implementation.
_PreviewRateLimiter is a DatabaseRateLimiter subclass with:
  - MAX_PER_MINUTE = PREVIEW_RATE_LIMIT_PER_MIN (5)
  - _get_minute_window() prefixed with 'preview:'

Per .claude/rules/testing.md:
  - Non-empty mocks for all counter paths
  - Every test_* has at least one assert
  - Patch source module, NOT importer
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest


USER_ID = UUID("550e8400-e29b-41d4-a716-446655440000")


class TestPreviewRateLimiterConfig:
    """_PreviewRateLimiter class-level configuration tests."""

    def test_max_per_minute_equals_tuning_constant(self):
        """MAX_PER_MINUTE must equal PREVIEW_RATE_LIMIT_PER_MIN from tuning.py."""
        from nikita.api.middleware.rate_limit import _PreviewRateLimiter
        from nikita.onboarding.tuning import PREVIEW_RATE_LIMIT_PER_MIN

        assert _PreviewRateLimiter.MAX_PER_MINUTE == PREVIEW_RATE_LIMIT_PER_MIN

    def test_is_subclass_of_database_rate_limiter(self):
        """_PreviewRateLimiter must subclass DatabaseRateLimiter."""
        from nikita.api.middleware.rate_limit import _PreviewRateLimiter
        from nikita.platforms.telegram.rate_limiter import DatabaseRateLimiter

        assert issubclass(_PreviewRateLimiter, DatabaseRateLimiter)

    def test_max_per_minute_is_five(self):
        """Regression guard: MAX_PER_MINUTE == 5 (PREVIEW_RATE_LIMIT_PER_MIN)."""
        from nikita.api.middleware.rate_limit import _PreviewRateLimiter

        assert _PreviewRateLimiter.MAX_PER_MINUTE == 5


class TestPreviewRateLimiterWindowKey:
    """_get_minute_window() returns 'preview:' prefixed key."""

    def test_window_has_preview_prefix(self):
        """_get_minute_window() must return string starting with 'preview:'."""
        from nikita.api.middleware.rate_limit import _PreviewRateLimiter

        mock_session = AsyncMock()
        limiter = _PreviewRateLimiter(mock_session)
        window = limiter._get_minute_window()
        assert window.startswith("preview:")

    def test_window_differs_from_base_window(self):
        """Preview window key differs from base DatabaseRateLimiter window."""
        from nikita.api.middleware.rate_limit import _PreviewRateLimiter
        from nikita.platforms.telegram.rate_limiter import DatabaseRateLimiter

        mock_session = AsyncMock()
        preview_limiter = _PreviewRateLimiter(mock_session)
        base_limiter = DatabaseRateLimiter(mock_session)

        assert preview_limiter._get_minute_window() != base_limiter._get_minute_window()

    def test_window_format_includes_timestamp(self):
        """Window key includes the minute-level timestamp after 'preview:'."""
        from nikita.api.middleware.rate_limit import _PreviewRateLimiter

        mock_session = AsyncMock()
        limiter = _PreviewRateLimiter(mock_session)
        window = limiter._get_minute_window()
        # Format: "preview:minute:YYYY-MM-DD-HH-MM"
        # Strip prefix, rest should not be empty
        suffix = window[len("preview:"):]
        assert len(suffix) > 0
        assert "minute:" in suffix


class TestPreviewRateLimiterDayWindow:
    """_get_day_window() returns 'preview:' prefixed key (F-03)."""

    def test_day_window_is_preview_prefixed(self):
        """_get_day_window() must return string starting with 'preview:day:'.

        Without this override the daily counter was shared with voice (F-03).
        """
        from nikita.api.middleware.rate_limit import _PreviewRateLimiter

        mock_session = AsyncMock()
        limiter = _PreviewRateLimiter(mock_session)
        assert limiter._get_day_window().startswith("preview:day:")

    def test_day_window_differs_from_base_day_window(self):
        """Preview day window differs from base DatabaseRateLimiter day window."""
        from nikita.api.middleware.rate_limit import _PreviewRateLimiter
        from nikita.platforms.telegram.rate_limiter import DatabaseRateLimiter

        mock_session = AsyncMock()
        preview_limiter = _PreviewRateLimiter(mock_session)
        base_limiter = DatabaseRateLimiter(mock_session)

        assert preview_limiter._get_day_window() != base_limiter._get_day_window()

    def test_minute_window_is_preview_prefixed(self):
        """_get_minute_window() must return string starting with 'preview:'."""
        from nikita.api.middleware.rate_limit import _PreviewRateLimiter

        mock_session = AsyncMock()
        limiter = _PreviewRateLimiter(mock_session)
        assert limiter._get_minute_window().startswith("preview:")


class TestPreviewRateLimiterCheck:
    """_PreviewRateLimiter.check() allows up to 5/min, blocks at 6."""

    @pytest.mark.asyncio
    async def test_allows_within_limit(self):
        """count <= 5 → allowed=True."""
        from nikita.api.middleware.rate_limit import _PreviewRateLimiter
        from nikita.db.models.rate_limit import RateLimit

        mock_session = AsyncMock()
        # Simulate count=3 returned from UPSERT
        mock_minute_result = MagicMock()
        mock_minute_result.scalar_one.return_value = 3
        mock_day_result = MagicMock()
        mock_day_result.scalar_one.return_value = 3

        mock_session.execute.side_effect = [mock_minute_result, mock_day_result]

        limiter = _PreviewRateLimiter(mock_session)
        result = await limiter.check(USER_ID)

        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_blocks_at_limit_exceeded(self):
        """count > 5 → allowed=False, reason='minute_limit_exceeded'."""
        from nikita.api.middleware.rate_limit import _PreviewRateLimiter

        mock_session = AsyncMock()
        # Simulate count=6 (exceeds limit of 5)
        mock_minute_result = MagicMock()
        mock_minute_result.scalar_one.return_value = 6
        mock_day_result = MagicMock()
        mock_day_result.scalar_one.return_value = 6

        mock_session.execute.side_effect = [mock_minute_result, mock_day_result]

        limiter = _PreviewRateLimiter(mock_session)
        result = await limiter.check(USER_ID)

        assert result.allowed is False
        assert result.reason == "minute_limit_exceeded"

    @pytest.mark.asyncio
    async def test_retry_after_60_on_exceeded(self):
        """retry_after_seconds == 60 when rate limit exceeded."""
        from nikita.api.middleware.rate_limit import _PreviewRateLimiter

        mock_session = AsyncMock()
        mock_minute_result = MagicMock()
        mock_minute_result.scalar_one.return_value = 6
        mock_day_result = MagicMock()
        mock_day_result.scalar_one.return_value = 6

        mock_session.execute.side_effect = [mock_minute_result, mock_day_result]

        limiter = _PreviewRateLimiter(mock_session)
        result = await limiter.check(USER_ID)

        assert result.retry_after_seconds == 60


class TestPreviewRateLimitDependency:
    """preview_rate_limit FastAPI dependency tests."""

    @pytest.mark.asyncio
    async def test_passes_when_allowed(self):
        """Dependency returns None (no exception) when within limit."""
        from nikita.api.middleware.rate_limit import preview_rate_limit

        with patch(
            "nikita.api.middleware.rate_limit._PreviewRateLimiter"
        ) as MockLimiter:
            mock_inst = AsyncMock()
            mock_result = MagicMock()
            mock_result.allowed = True
            mock_inst.check.return_value = mock_result
            MockLimiter.return_value = mock_inst

            mock_session = AsyncMock()
            # Should complete without raising
            await preview_rate_limit(
                current_user_id=USER_ID,
                session=mock_session,
            )
            mock_inst.check.assert_awaited_once_with(USER_ID)

    @pytest.mark.asyncio
    async def test_raises_429_when_exceeded(self):
        """Dependency raises HTTPException(429) when rate limit exceeded."""
        from fastapi import HTTPException
        from nikita.api.middleware.rate_limit import preview_rate_limit

        with patch(
            "nikita.api.middleware.rate_limit._PreviewRateLimiter"
        ) as MockLimiter:
            mock_inst = AsyncMock()
            mock_result = MagicMock()
            mock_result.allowed = False
            mock_result.retry_after_seconds = 60
            mock_inst.check.return_value = mock_result
            MockLimiter.return_value = mock_inst

            mock_session = AsyncMock()
            with pytest.raises(HTTPException) as exc_info:
                await preview_rate_limit(
                    current_user_id=USER_ID,
                    session=mock_session,
                )

            assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_429_has_retry_after_header(self):
        """HTTPException on rate limit includes Retry-After: 60 header."""
        from fastapi import HTTPException
        from nikita.api.middleware.rate_limit import preview_rate_limit

        with patch(
            "nikita.api.middleware.rate_limit._PreviewRateLimiter"
        ) as MockLimiter:
            mock_inst = AsyncMock()
            mock_result = MagicMock()
            mock_result.allowed = False
            mock_result.retry_after_seconds = 60
            mock_inst.check.return_value = mock_result
            MockLimiter.return_value = mock_inst

            mock_session = AsyncMock()
            with pytest.raises(HTTPException) as exc_info:
                await preview_rate_limit(
                    current_user_id=USER_ID,
                    session=mock_session,
                )

            assert exc_info.value.headers is not None
            assert exc_info.value.headers.get("Retry-After") == "60"
