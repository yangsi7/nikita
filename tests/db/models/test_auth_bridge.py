"""Tests for AuthBridgeToken model."""

import pytest
from datetime import timedelta
from uuid import uuid4

from nikita.db.models.auth_bridge import AuthBridgeToken, generate_bridge_token


class TestGenerateBridgeToken:
    """Tests for generate_bridge_token()."""

    def test_length(self):
        """Token should be at least 32 chars (token_urlsafe(32) ~43 chars)."""
        token = generate_bridge_token()
        assert len(token) >= 32

    def test_uniqueness(self):
        """100 generated tokens should all be unique."""
        tokens = {generate_bridge_token() for _ in range(100)}
        assert len(tokens) == 100

    def test_url_safe(self):
        """Token should only contain URL-safe characters."""
        token = generate_bridge_token()
        # token_urlsafe uses A-Z, a-z, 0-9, -, _
        import re

        assert re.match(r"^[A-Za-z0-9_-]+$", token)


class TestAuthBridgeToken:
    """Tests for AuthBridgeToken model."""

    def test_create_with_redirect_path(self):
        """Create sets user_id, redirect_path, token, and non-expired expiry."""
        user_id = uuid4()
        bridge = AuthBridgeToken.create(user_id, "/onboarding")
        assert bridge.user_id == user_id
        assert bridge.redirect_path == "/onboarding"
        assert bridge.token  # Not empty
        assert not bridge.is_expired()

    def test_create_default_redirect_path(self):
        """Default redirect_path is /onboarding."""
        bridge = AuthBridgeToken.create(uuid4())
        assert bridge.redirect_path == "/onboarding"

    def test_is_expired_false_when_fresh(self):
        """Freshly created token should not be expired."""
        bridge = AuthBridgeToken.create(uuid4(), "/onboarding")
        assert not bridge.is_expired()

    def test_is_expired_true_when_past(self):
        """Token with past expires_at should be expired."""
        from nikita.db.models.base import utc_now

        bridge = AuthBridgeToken.create(uuid4(), "/onboarding")
        bridge.expires_at = utc_now() - timedelta(minutes=1)
        assert bridge.is_expired()

    def test_expiry_is_5_minutes(self):
        """Token expiry should be approximately 5 minutes from creation."""
        from nikita.db.models.base import utc_now

        before = utc_now()
        bridge = AuthBridgeToken.create(uuid4(), "/onboarding")
        after = utc_now()

        # expires_at should be ~5 min from now
        expected_min = before + timedelta(minutes=4, seconds=59)
        expected_max = after + timedelta(minutes=5, seconds=1)
        assert expected_min <= bridge.expires_at <= expected_max

    def test_repr(self):
        """repr should show truncated token and user_id."""
        bridge = AuthBridgeToken.create(uuid4(), "/onboarding")
        r = repr(bridge)
        assert "AuthBridgeToken" in r
        assert "..." in r  # Token is truncated

    def test_each_create_generates_unique_token(self):
        """Each create() call should produce a different token."""
        user_id = uuid4()
        b1 = AuthBridgeToken.create(user_id, "/a")
        b2 = AuthBridgeToken.create(user_id, "/b")
        assert b1.token != b2.token
