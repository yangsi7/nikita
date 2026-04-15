"""Rate limiting dependencies for voice, preview, choice, and poll API endpoints.

voice_rate_limit (SEC-010): checks DatabaseRateLimiter before allowing
voice calls through. Fails open on DB errors to avoid blocking legitimate callers.

_PreviewRateLimiter + preview_rate_limit (Spec 213 FR-4a.1): separate
per-user limiter for POST /onboarding/preview-backstory — limit=5/min,
'preview:' key prefix isolates BOTH minute AND day counters from voice.

Spec 214 PR 214-D additions:
_ChoiceRateLimiter + choice_rate_limit (FR-10.1): per-user limiter for
PUT /onboarding/profile/chosen-option — limit=10/min, 'choice:' prefix.
429 responses include Retry-After: 60 header (RFC 6585).

_PipelineReadyRateLimiter + pipeline_ready_rate_limit (AC-5.6): per-user
limiter for GET /onboarding/pipeline-ready/{user_id} — limit=30/min,
'poll:' prefix. 429 responses include Retry-After: 60 header.
"""

import hashlib
import logging
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.api.dependencies.auth import get_current_user_id
from nikita.db.database import get_async_session
from nikita.onboarding.tuning import (
    CHOICE_RATE_LIMIT_PER_MIN,
    PIPELINE_POLL_RATE_LIMIT_PER_MIN,
    PREVIEW_RATE_LIMIT_PER_MIN,
)
from nikita.platforms.telegram.rate_limiter import DatabaseRateLimiter

logger = logging.getLogger(__name__)


async def voice_rate_limit(request: Request) -> None:
    """Enforce per-user rate limiting on voice endpoints.

    Identity extraction order:
    1. Path param ``user_id``  (GET /signed-url/{user_id})
    2. Body field ``user_id``  (POST /initiate)
    3. Body field ``caller_id`` (POST /pre-call) -- SHA-256 → deterministic UUID

    Raises:
        HTTPException: 429 with Retry-After header when limit exceeded.
    """
    user_uuid: UUID | None = None

    # 1. Path param
    raw = request.path_params.get("user_id")
    if raw:
        try:
            user_uuid = UUID(str(raw))
        except ValueError:
            return  # Let endpoint handle bad UUID

    # 2. Body fields (POST)
    if user_uuid is None and request.method == "POST":
        try:
            body = await request.json()
            if "user_id" in body:
                user_uuid = UUID(str(body["user_id"]))
            elif "caller_id" in body:
                digest = hashlib.sha256(body["caller_id"].encode()).hexdigest()[:32]
                user_uuid = UUID(int=int(digest, 16))
        except Exception:
            pass

    if user_uuid is None:
        return  # Can't identify user -- allow through

    # Check rate limit
    from nikita.db.database import get_session_maker

    try:
        session_maker = get_session_maker()
        async with session_maker() as session:
            limiter = DatabaseRateLimiter(session)
            result = await limiter.check(user_uuid)

            if not result.allowed:
                logger.warning(
                    "[VOICE RATE LIMIT] Rejected user=%s reason=%s",
                    user_uuid,
                    result.reason,
                )
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded: {result.reason}",
                    headers={"Retry-After": str(result.retry_after_seconds or 60)},
                )
    except HTTPException:
        raise
    except Exception as exc:
        # Fail open -- rate-limit outage must not block calls
        logger.warning("[VOICE RATE LIMIT] Check failed (allowing): %s", exc)


# ---------------------------------------------------------------------------
# Preview backstory rate limiter (Spec 213 FR-4a.1)
# ---------------------------------------------------------------------------


class _PreviewRateLimiter(DatabaseRateLimiter):
    """DatabaseRateLimiter subclass for POST /onboarding/preview-backstory.

    Overrides:
    - MAX_PER_MINUTE: 5 (from PREVIEW_RATE_LIMIT_PER_MIN tuning constant)
    - _get_minute_window(): adds 'preview:' prefix so preview calls are
      counted separately from voice calls in the rate_limits table.
    - _get_day_window(): adds 'preview:' prefix so daily preview quota is
      also isolated from voice (F-03: previously shared the voice daily row).

    Approach per spec FR-4a.1: subclass avoids modifying the shared
    DatabaseRateLimiter.check() signature. Using PREVIEW_RATE_LIMIT_PER_MIN
    directly (not a bare literal) per .claude/rules/tuning-constants.md.
    """

    # PREVIEW_RATE_LIMIT_PER_MIN = 5 (new in Spec 213, GH #213).
    # Prior values: none. Rationale: each call triggers Claude + Firecrawl;
    # 5/min covers wizard navigation + legitimate retries without enabling abuse.
    MAX_PER_MINUTE: int = PREVIEW_RATE_LIMIT_PER_MIN

    def _get_minute_window(self) -> str:
        """Return prefixed window key to isolate preview counters from voice.

        Format: 'preview:minute:<YYYY-MM-DD-HH-MM>'
        Prefix ensures the UPSERT key for preview calls never collides with
        the voice rate limiter's 'minute:<...>' key in the rate_limits table.
        """
        return f"preview:{super()._get_minute_window()}"

    def _get_day_window(self) -> str:
        """Return prefixed day window key to isolate preview daily quota from voice.

        Format: 'preview:day:<YYYY-MM-DD>'
        Without this override the daily counter row was shared with voice (F-03);
        the docstring claiming 'preview: avoids sharing quota with voice' was
        partially false — only the minute window was isolated.
        """
        return f"preview:{super()._get_day_window()}"


async def preview_rate_limit(
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    """FastAPI dependency: enforce 5 req/min per user on preview-backstory.

    Uses _PreviewRateLimiter (DatabaseRateLimiter subclass) so counters
    persist across Cloud Run instances and survive restarts.

    Raises:
        HTTPException: 429 with Retry-After: 60 header when limit exceeded.
    """
    limiter = _PreviewRateLimiter(session)
    result = await limiter.check(current_user_id)
    if not result.allowed:
        logger.warning(
            "[PREVIEW RATE LIMIT] Rejected user=%s reason=%s",
            current_user_id,
            result.reason,
        )
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": "60"},
        )


# ---------------------------------------------------------------------------
# Choice backstory rate limiter (Spec 214 FR-10.1)
# ---------------------------------------------------------------------------


class _ChoiceRateLimiter(DatabaseRateLimiter):
    """DatabaseRateLimiter subclass for PUT /onboarding/profile/chosen-option.

    Overrides:
    - MAX_PER_MINUTE: 10 (from CHOICE_RATE_LIMIT_PER_MIN tuning constant)
    - _get_minute_window(): adds 'choice:' prefix so choice calls are
      counted separately from voice/preview calls in the rate_limits table.
    - _get_day_window(): adds 'choice:' prefix so daily choice quota is
      also isolated (mirrors _PreviewRateLimiter pattern at rate_limit.py).

    CHOICE_RATE_LIMIT_PER_MIN = 10 (new in Spec 214 PR 214-D).
    Prior values: none. Rationale: one-shot user action (no external service
    call), idempotent endpoint; 10/min allows legitimate retries without abuse.
    """

    # CHOICE_RATE_LIMIT_PER_MIN = 10 (Spec 214 PR 214-D).
    MAX_PER_MINUTE: int = CHOICE_RATE_LIMIT_PER_MIN

    def _get_minute_window(self) -> str:
        """Return prefixed window key to isolate choice counters from voice/preview.

        Format: 'choice:minute:<YYYY-MM-DD-HH-MM>'
        Prefix ensures the UPSERT key never collides with 'minute:<...>' (voice)
        or 'preview:minute:<...>' in the rate_limits table.
        """
        return f"choice:{super()._get_minute_window()}"

    def _get_day_window(self) -> str:
        """Return prefixed day window key to isolate choice daily quota.

        Format: 'choice:day:<YYYY-MM-DD>'
        Without this override the daily counter row is shared with voice (F-03
        precedent from _PreviewRateLimiter); must prefix both windows.
        """
        return f"choice:{super()._get_day_window()}"


async def choice_rate_limit(
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    """FastAPI dependency: enforce 10 req/min per user on chosen-option PUT.

    Uses _ChoiceRateLimiter (DatabaseRateLimiter subclass) so counters
    persist across Cloud Run instances and survive restarts.

    Raises:
        HTTPException: 429 with Retry-After: 60 header when limit exceeded
            (RFC 6585 — same pattern as preview_rate_limit).
    """
    limiter = _ChoiceRateLimiter(session)
    result = await limiter.check(current_user_id)
    if not result.allowed:
        logger.warning(
            "[CHOICE RATE LIMIT] Rejected user=%s reason=%s",
            current_user_id,
            result.reason,
        )
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": "60"},
        )


# ---------------------------------------------------------------------------
# Pipeline-ready poll rate limiter (Spec 214 AC-5.6)
# ---------------------------------------------------------------------------


class _PipelineReadyRateLimiter(DatabaseRateLimiter):
    """DatabaseRateLimiter subclass for GET /pipeline-ready/{user_id}.

    Overrides:
    - MAX_PER_MINUTE: 30 (from PIPELINE_POLL_RATE_LIMIT_PER_MIN tuning constant)
    - _get_minute_window(): adds 'poll:' prefix for counter isolation.
    - _get_day_window(): adds 'poll:' prefix for daily quota isolation.

    PIPELINE_POLL_RATE_LIMIT_PER_MIN = 30 (new in Spec 214 PR 214-D, AC-5.6).
    Prior values: none (endpoint was previously unlimited).
    Rationale: portal polls every 2s over 20s window → 10 calls nominal. 30/min
    allows 3× overrun (mobile reconnects, tab backgrounding) without 429.
    """

    # PIPELINE_POLL_RATE_LIMIT_PER_MIN = 30 (Spec 214 PR 214-D).
    MAX_PER_MINUTE: int = PIPELINE_POLL_RATE_LIMIT_PER_MIN

    def _get_minute_window(self) -> str:
        """Return prefixed window key to isolate poll counters from voice/preview/choice.

        Format: 'poll:minute:<YYYY-MM-DD-HH-MM>'
        """
        return f"poll:{super()._get_minute_window()}"

    def _get_day_window(self) -> str:
        """Return prefixed day window key to isolate poll daily quota.

        Format: 'poll:day:<YYYY-MM-DD>'
        """
        return f"poll:{super()._get_day_window()}"


async def pipeline_ready_rate_limit(
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    """FastAPI dependency: enforce 30 req/min per user on pipeline-ready GET.

    Uses _PipelineReadyRateLimiter (DatabaseRateLimiter subclass) so counters
    persist across Cloud Run instances and survive restarts.

    Raises:
        HTTPException: 429 with Retry-After: 60 header when limit exceeded
            (RFC 6585 — same pattern as preview_rate_limit and choice_rate_limit).
    """
    limiter = _PipelineReadyRateLimiter(session)
    result = await limiter.check(current_user_id)
    if not result.allowed:
        logger.warning(
            "[PIPELINE READY RATE LIMIT] Rejected user=%s reason=%s",
            current_user_id,
            result.reason,
        )
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": "60"},
        )
