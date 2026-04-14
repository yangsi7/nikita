"""Rate limiting dependencies for voice and preview API endpoints.

voice_rate_limit (SEC-010): checks DatabaseRateLimiter before allowing
voice calls through. Fails open on DB errors to avoid blocking legitimate callers.

_PreviewRateLimiter + preview_rate_limit (Spec 213 FR-4a.1): separate
per-user limiter for POST /onboarding/preview-backstory — limit=5/min,
separate counter key prefix 'preview:' avoids sharing quota with voice.
"""

import hashlib
import logging
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.api.dependencies.auth import get_current_user_id
from nikita.db.database import get_async_session
from nikita.onboarding.tuning import PREVIEW_RATE_LIMIT_PER_MIN
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
