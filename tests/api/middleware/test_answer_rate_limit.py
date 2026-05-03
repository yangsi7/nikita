"""T-B3-7 (Spec 216-B3): answer_rate_limit dependency — 30 rpm per-user.

Per AC B1.22 + brief: per-user rate limit (NOT per-conversation_id, to prevent
clients minting UUID4s to bypass quota). Bucket key prefix 'answer:' isolates
counters from voice/preview/choice/poll buckets.

Mirrors the _PipelineReadyRateLimiter pattern at
nikita/api/middleware/rate_limit.py:252-302.

Multi-tab tradeoff: per-user keying means multiple browser tabs on the same
account share quota. This is intentional — per-conversation_id keying lets a
malicious client bypass quota by rotating UUID4s. Documented in code.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession


USER_ID = UUID("550e8400-e29b-41d4-a716-446655440000")


class TestAnswerRateLimiter:
    """Limiter class shape + bucket-key isolation."""

    def test_limiter_class_uses_answer_prefix_for_minute_window(self) -> None:
        """Bucket key isolation: minute window prefixed 'answer:' so it
        does not collide with voice/preview/choice/poll counters in the
        rate_limits table (per F-03 precedent in _PreviewRateLimiter)."""
        from nikita.api.middleware.rate_limit import _AnswerRateLimiter

        limiter = _AnswerRateLimiter(AsyncMock(spec=AsyncSession))
        window = limiter._get_minute_window()
        assert window.startswith("answer:"), (
            f"Expected 'answer:' prefix on minute window, got: {window!r}"
        )

    def test_limiter_class_uses_answer_prefix_for_day_window(self) -> None:
        """Daily quota counter must also be 'answer:'-prefixed."""
        from nikita.api.middleware.rate_limit import _AnswerRateLimiter

        limiter = _AnswerRateLimiter(AsyncMock(spec=AsyncSession))
        window = limiter._get_day_window()
        assert window.startswith("answer:"), (
            f"Expected 'answer:' prefix on day window, got: {window!r}"
        )

    def test_limiter_max_per_minute_is_30(self) -> None:
        """B1.22 spec: 30 requests per minute per user."""
        from nikita.api.middleware.rate_limit import _AnswerRateLimiter

        assert _AnswerRateLimiter.MAX_PER_MINUTE == 30, (
            "B1.22 mandates 30 rpm. If this changes, update the spec AND the "
            "tuning constant docstring."
        )


class TestAnswerRateLimitDependency:
    """answer_rate_limit FastAPI dependency function."""

    @pytest.mark.asyncio
    async def test_passes_when_under_limit(self) -> None:
        """When the limiter says allowed=True, the dep returns None silently."""
        from nikita.api.middleware import rate_limit as rl_module
        from nikita.api.middleware.rate_limit import answer_rate_limit

        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.allowed = True
        mock_result.reason = None

        # Patch the limiter class so we don't hit DB
        original = rl_module._AnswerRateLimiter
        try:
            mock_limiter_instance = AsyncMock()
            mock_limiter_instance.check = AsyncMock(return_value=mock_result)
            rl_module._AnswerRateLimiter = MagicMock(
                return_value=mock_limiter_instance
            )

            result = await answer_rate_limit(USER_ID, mock_session)
            assert result is None
            mock_limiter_instance.check.assert_awaited_once_with(USER_ID)
        finally:
            rl_module._AnswerRateLimiter = original

    @pytest.mark.asyncio
    async def test_raises_429_with_retry_after_when_over_limit(self) -> None:
        """B1.22: 429 with Retry-After: 60 header (RFC 6585)."""
        from nikita.api.middleware import rate_limit as rl_module
        from nikita.api.middleware.rate_limit import answer_rate_limit

        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.allowed = False
        mock_result.reason = "minute_limit_exceeded"

        original = rl_module._AnswerRateLimiter
        try:
            mock_limiter_instance = AsyncMock()
            mock_limiter_instance.check = AsyncMock(return_value=mock_result)
            rl_module._AnswerRateLimiter = MagicMock(
                return_value=mock_limiter_instance
            )

            with pytest.raises(HTTPException) as exc_info:
                await answer_rate_limit(USER_ID, mock_session)
        finally:
            rl_module._AnswerRateLimiter = original

        assert exc_info.value.status_code == 429
        assert exc_info.value.headers is not None
        assert exc_info.value.headers.get("Retry-After") == "60", (
            "B1.22 expects RFC 6585 Retry-After: 60 header for 429 responses."
        )


class TestTuningConstant:
    """Regression guard for the named ANSWER_RATE_LIMIT_PER_MIN tuning constant
    per .claude/rules/tuning-constants.md (named + documented + tested)."""

    def test_answer_rate_limit_constant_value_is_30(self) -> None:
        """B1.22 mandates 30 rpm. This test fails RED if a future contributor
        changes the constant without updating spec + this regression guard."""
        from nikita.onboarding.tuning import ANSWER_RATE_LIMIT_PER_MIN

        assert ANSWER_RATE_LIMIT_PER_MIN == 30, (
            "ANSWER_RATE_LIMIT_PER_MIN drifted from 30. Update spec 216-B3 "
            "AC B1.22, the limiter class, AND the constant docstring before "
            "merging."
        )
