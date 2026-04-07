"""Rate limiting dependency for voice API endpoints (SEC-010).

FastAPI dependency that checks DatabaseRateLimiter before allowing
voice calls through. Fails open on DB errors to avoid blocking
legitimate callers.
"""

import hashlib
import logging
from uuid import UUID

from fastapi import HTTPException, Request

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
