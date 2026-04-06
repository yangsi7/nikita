"""Tests for shared webhook authentication utilities."""

import hashlib
import hmac
import time
from unittest.mock import patch, MagicMock

import pytest

from nikita.api.utils.webhook_auth import (
    validate_signed_token,
    verify_elevenlabs_signature,
    TOKEN_VALIDITY_SECONDS,
    WEBHOOK_TIMESTAMP_TOLERANCE,
)


def _make_signed_token(user_id: str, session_id: str, secret: str, timestamp: int | None = None) -> str:
    """Helper to generate a valid signed token."""
    ts = timestamp or int(time.time())
    payload = f"{user_id}:{session_id}:{ts}"
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{sig}"


def _make_elevenlabs_signature(body: str, secret: str, timestamp: int | None = None) -> str:
    """Helper to generate a valid ElevenLabs signature header."""
    ts = timestamp or int(time.time())
    message = f"{ts}.{body}"
    sig = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    return f"t={ts},v0={sig}"


TEST_SECRET = "test-webhook-secret-123"


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.elevenlabs_webhook_secret = TEST_SECRET
    with patch("nikita.api.utils.webhook_auth.get_settings", return_value=settings):
        yield settings


class TestValidateSignedToken:
    def test_valid_token(self, mock_settings):
        token = _make_signed_token("user-1", "session-1", TEST_SECRET)
        user_id, session_id = validate_signed_token(token)
        assert user_id == "user-1"
        assert session_id == "session-1"

    def test_expired_token(self, mock_settings):
        old_ts = int(time.time()) - TOKEN_VALIDITY_SECONDS - 10
        token = _make_signed_token("user-1", "session-1", TEST_SECRET, timestamp=old_ts)
        with pytest.raises(ValueError, match="Token expired"):
            validate_signed_token(token)

    def test_bad_signature(self, mock_settings):
        token = _make_signed_token("user-1", "session-1", "wrong-secret")
        with pytest.raises(ValueError, match="Invalid signature"):
            validate_signed_token(token)

    def test_wrong_format_3_parts(self, mock_settings):
        with pytest.raises(ValueError, match="Invalid token format"):
            validate_signed_token("a:b:c")

    def test_invalid_timestamp(self, mock_settings):
        with pytest.raises(ValueError, match="Invalid timestamp"):
            validate_signed_token("user:session:notanumber:sig")

    def test_missing_secret(self):
        settings = MagicMock()
        settings.elevenlabs_webhook_secret = None
        with patch("nikita.api.utils.webhook_auth.get_settings", return_value=settings):
            # Use a fresh timestamp so the token is not expired before reaching secret check
            fresh_ts = int(time.time())
            token = f"user:session:{fresh_ts}:sig"
            with pytest.raises(ValueError, match="ELEVENLABS_WEBHOOK_SECRET"):
                validate_signed_token(token)


class TestVerifyElevenLabsSignature:
    def test_valid_signature(self):
        body = '{"type": "call_ended"}'
        header = _make_elevenlabs_signature(body, TEST_SECRET)
        assert verify_elevenlabs_signature(body, header, TEST_SECRET) is True

    def test_invalid_signature(self):
        body = '{"type": "call_ended"}'
        header = _make_elevenlabs_signature(body, "wrong-secret")
        assert verify_elevenlabs_signature(body, header, TEST_SECRET) is False

    def test_expired_timestamp(self):
        body = '{"type": "call_ended"}'
        old_ts = int(time.time()) - WEBHOOK_TIMESTAMP_TOLERANCE - 10
        header = _make_elevenlabs_signature(body, TEST_SECRET, timestamp=old_ts)
        with pytest.raises(ValueError, match="expired"):
            verify_elevenlabs_signature(body, header, TEST_SECRET)

    def test_empty_header(self):
        assert verify_elevenlabs_signature("body", "", TEST_SECRET) is False

    def test_missing_v0(self):
        header = f"t={int(time.time())}"
        assert verify_elevenlabs_signature("body", header, TEST_SECRET) is False
