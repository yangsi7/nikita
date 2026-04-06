"""Shared webhook authentication utilities for ElevenLabs endpoints.

Extracted from voice.py to be reused by both voice and onboarding routes.
Provides signed token validation and ElevenLabs webhook HMAC verification.

Closes #220, #225 (Batch A: auth surface fix).
"""

import hashlib
import hmac
import time

from nikita.config.settings import get_settings

# Token validity: 30 minutes (voice calls can last this long)
TOKEN_VALIDITY_SECONDS = 1800

# Webhook timestamp tolerance: 5 minutes
WEBHOOK_TIMESTAMP_TOLERANCE = 300


def validate_signed_token(token: str) -> tuple[str, str]:
    """Validate HMAC signed token and extract user_id and session_id.

    Token format: {user_id}:{session_id}:{timestamp}:{signature}
    Signature = HMAC-SHA256(secret, "{user_id}:{session_id}:{timestamp}")

    Args:
        token: The 4-part colon-separated signed token.

    Returns:
        Tuple of (user_id, session_id) as strings.

    Raises:
        ValueError: If token format is invalid, expired, or signature mismatch.
    """
    parts = token.split(":")
    if len(parts) != 4:
        raise ValueError("Invalid token format")

    user_id, session_id, timestamp_str, signature = parts

    # Validate timestamp
    try:
        timestamp = int(timestamp_str)
    except ValueError:
        raise ValueError("Invalid timestamp")

    # Check expiry (30-minute window for longer conversations)
    current_time = int(time.time())
    if current_time - timestamp > TOKEN_VALIDITY_SECONDS:
        raise ValueError("Token expired")

    # Verify HMAC signature
    settings = get_settings()
    if not settings.elevenlabs_webhook_secret:
        raise ValueError("ELEVENLABS_WEBHOOK_SECRET must be configured")
    secret = settings.elevenlabs_webhook_secret
    payload = f"{user_id}:{session_id}:{timestamp_str}"
    expected_signature = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(signature, expected_signature):
        raise ValueError("Invalid signature")

    return user_id, session_id


def verify_elevenlabs_signature(
    payload: str, signature_header: str, secret: str
) -> bool:
    """Verify ElevenLabs webhook HMAC signature.

    Signature header format: t={timestamp},v0={signature}
    Signed message: "{timestamp}.{raw_body}"

    Args:
        payload: Raw request body as string.
        signature_header: Value of the elevenlabs-signature header.
        secret: ELEVENLABS_WEBHOOK_SECRET.

    Returns:
        True if signature is valid.

    Raises:
        ValueError: If timestamp is expired (>5 minutes old).
    """
    if not signature_header:
        return False

    # Parse signature header: t={timestamp},v0={signature}
    parts = {}
    for part in signature_header.split(","):
        if "=" in part:
            key, value = part.split("=", 1)
            parts[key] = value

    timestamp_str = parts.get("t")
    signature = parts.get("v0")  # ElevenLabs uses v0 format

    if not timestamp_str or not signature:
        return False

    # Validate timestamp
    try:
        timestamp = int(timestamp_str)
    except ValueError:
        return False

    current_time = int(time.time())
    if current_time - timestamp > WEBHOOK_TIMESTAMP_TOLERANCE:
        raise ValueError("Webhook timestamp expired")

    # Verify signature using constant-time comparison
    message = f"{timestamp}.{payload}"
    expected_signature = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(signature, expected_signature)
