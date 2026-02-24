"""Push notification delivery via Supabase Edge Function.

Sends web push notifications to a user's subscribed browsers.
All errors are caught and logged — push failures never block game flow.
"""

import logging
from uuid import UUID

import httpx

from nikita.config.settings import get_settings

logger = logging.getLogger(__name__)


async def send_push(
    user_id: UUID,
    title: str,
    body: str,
    *,
    url: str = "/dashboard",
    tag: str = "nikita-default",
) -> dict:
    """Send a push notification to all of a user's subscribed browsers.

    Args:
        user_id: Target user UUID
        title: Notification title
        body: Notification body text
        url: URL to open on click (default: /dashboard)
        tag: Notification tag for deduplication

    Returns:
        dict with {sent, failed} counts, or {error} on failure
    """
    settings = get_settings()

    if not settings.supabase_url:
        logger.warning("[Push] SUPABASE_URL not configured, skipping push")
        return {"sent": 0, "failed": 0, "error": "supabase_url not configured"}

    if not settings.supabase_service_key:
        logger.warning("[Push] SUPABASE_SERVICE_KEY not configured, skipping push")
        return {"sent": 0, "failed": 0, "error": "service_key not configured"}

    function_url = f"{settings.supabase_url}/functions/v1/push-notify"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                function_url,
                json={
                    "user_id": str(user_id),
                    "title": title,
                    "body": body,
                    "url": url,
                    "tag": tag,
                },
                headers={
                    "Authorization": f"Bearer {settings.supabase_service_key or ''}",
                    "Content-Type": "application/json",
                },
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("sent", 0) == 0 and result.get("message", "").startswith("Push delivery stub"):
                    logger.info("[Push] STUB: push-notify edge function not yet implemented, user=%s", user_id)
                else:
                    logger.info(
                        "[Push] Sent to user %s: %d sent, %d failed",
                        user_id,
                        result.get("sent", 0),
                        result.get("failed", 0),
                    )
                return result
            else:
                logger.warning(
                    "[Push] Edge function returned %d: %s",
                    response.status_code,
                    response.text[:200],
                )
                return {"sent": 0, "failed": 0, "error": f"HTTP {response.status_code}"}

    except Exception as exc:
        logger.error("[Push] Failed to send push to user %s: %s", user_id, exc)
        return {"sent": 0, "failed": 0, "error": str(exc)}
