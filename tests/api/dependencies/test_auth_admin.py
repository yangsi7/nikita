"""Tests for admin authentication dependency.

TDD tests for T1.1: Create Admin Auth Dependency

Acceptance Criteria:
- AC-FR001-001: Users with @silent-agents.com email can access admin endpoints
- AC-FR001-002: Users with other emails receive 403 Forbidden
"""

import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

import jwt
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from nikita.api.dependencies.auth import get_current_admin_user


@pytest.fixture
def mock_settings():
    """Mock settings with JWT secret and empty admin list."""
    settings = MagicMock()
    settings.supabase_jwt_secret = "test-jwt-secret"
    settings.admin_emails = []  # Default: no explicit admins
    return settings


@pytest.fixture
def mock_settings_with_allowlist():
    """Mock settings with JWT secret and explicit admin allowlist."""
    settings = MagicMock()
    settings.supabase_jwt_secret = "test-jwt-secret"
    settings.admin_emails = ["allowed.admin@gmail.com", "another.admin@example.com"]
    return settings


@pytest.fixture
def make_token(mock_settings):
    """Factory to create JWT tokens for testing."""
    def _make(email: str, user_id: str | None = None):
        if user_id is None:
            user_id = str(uuid4())
        payload = {
            "sub": user_id,
            "email": email,
            "aud": "authenticated",
        }
        return jwt.encode(payload, mock_settings.supabase_jwt_secret, algorithm="HS256")
    return _make


class TestGetCurrentAdminUser:
    """Test suite for get_current_admin_user dependency."""

    @pytest.mark.asyncio
    async def test_admin_email_returns_user_id(self, mock_settings, make_token):
        """AC-FR001-001: @silent-agents.com email grants admin access."""
        user_id = str(uuid4())
        token = make_token("admin@silent-agents.com", user_id)
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with patch("nikita.api.dependencies.auth.get_settings", return_value=mock_settings):
            result = await get_current_admin_user(credentials)

        assert str(result) == user_id

    @pytest.mark.asyncio
    async def test_admin_email_subdomain_access(self, mock_settings, make_token):
        """AC-FR001-001: Any @silent-agents.com email works (e.g., dev@silent-agents.com)."""
        user_id = str(uuid4())
        token = make_token("dev@silent-agents.com", user_id)
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with patch("nikita.api.dependencies.auth.get_settings", return_value=mock_settings):
            result = await get_current_admin_user(credentials)

        assert str(result) == user_id

    @pytest.mark.asyncio
    async def test_non_admin_email_raises_403(self, mock_settings, make_token):
        """AC-FR001-002: Other emails receive 403 Forbidden."""
        token = make_token("user@gmail.com")
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with patch("nikita.api.dependencies.auth.get_settings", return_value=mock_settings):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_admin_user(credentials)

        assert exc_info.value.status_code == 403
        assert "Admin access required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_similar_domain_raises_403(self, mock_settings, make_token):
        """AC-FR001-002: Similar domains like silent-agents.com.fake are rejected."""
        token = make_token("user@silent-agents.com.fake")
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with patch("nikita.api.dependencies.auth.get_settings", return_value=mock_settings):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_admin_user(credentials)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_no_email_in_token_raises_403(self, mock_settings):
        """Token without email claim should raise 403."""
        user_id = str(uuid4())
        payload = {
            "sub": user_id,
            "aud": "authenticated",
            # No email claim
        }
        token = jwt.encode(payload, mock_settings.supabase_jwt_secret, algorithm="HS256")
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with patch("nikita.api.dependencies.auth.get_settings", return_value=mock_settings):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_admin_user(credentials)

        assert exc_info.value.status_code == 403
        assert "email" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self, mock_settings):
        """Invalid token should raise 401 Unauthorized."""
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid-token")

        with patch("nikita.api.dependencies.auth.get_settings", return_value=mock_settings):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_admin_user(credentials)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_expired_token_raises_401(self, mock_settings):
        """Expired token should raise 401."""
        import time
        user_id = str(uuid4())
        payload = {
            "sub": user_id,
            "email": "admin@silent-agents.com",
            "aud": "authenticated",
            "exp": int(time.time()) - 3600,  # Expired 1 hour ago
        }
        token = jwt.encode(payload, mock_settings.supabase_jwt_secret, algorithm="HS256")
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with patch("nikita.api.dependencies.auth.get_settings", return_value=mock_settings):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_admin_user(credentials)

        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()


class TestAdminAllowlist:
    """Test suite for explicit admin email allowlist functionality."""

    @pytest.mark.asyncio
    async def test_explicit_admin_email_grants_access(self, mock_settings_with_allowlist):
        """Email in admin_emails allowlist grants admin access."""
        user_id = str(uuid4())
        payload = {
            "sub": user_id,
            "email": "allowed.admin@gmail.com",  # In allowlist
            "aud": "authenticated",
        }
        token = jwt.encode(payload, mock_settings_with_allowlist.supabase_jwt_secret, algorithm="HS256")
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with patch("nikita.api.dependencies.auth.get_settings", return_value=mock_settings_with_allowlist):
            result = await get_current_admin_user(credentials)

        assert str(result) == user_id

    @pytest.mark.asyncio
    async def test_explicit_admin_email_case_insensitive(self, mock_settings_with_allowlist):
        """Admin email matching is case-insensitive."""
        user_id = str(uuid4())
        payload = {
            "sub": user_id,
            "email": "ALLOWED.ADMIN@GMAIL.COM",  # Uppercase, but should match
            "aud": "authenticated",
        }
        token = jwt.encode(payload, mock_settings_with_allowlist.supabase_jwt_secret, algorithm="HS256")
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with patch("nikita.api.dependencies.auth.get_settings", return_value=mock_settings_with_allowlist):
            result = await get_current_admin_user(credentials)

        assert str(result) == user_id

    @pytest.mark.asyncio
    async def test_non_allowlisted_email_raises_403(self, mock_settings_with_allowlist):
        """Email not in allowlist and not @silent-agents.com raises 403."""
        payload = {
            "sub": str(uuid4()),
            "email": "random@gmail.com",  # Not in allowlist
            "aud": "authenticated",
        }
        token = jwt.encode(payload, mock_settings_with_allowlist.supabase_jwt_secret, algorithm="HS256")
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with patch("nikita.api.dependencies.auth.get_settings", return_value=mock_settings_with_allowlist):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_admin_user(credentials)

        assert exc_info.value.status_code == 403
        assert "Admin access required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_domain_still_works_with_allowlist(self, mock_settings_with_allowlist):
        """@silent-agents.com still works even when allowlist is configured."""
        user_id = str(uuid4())
        payload = {
            "sub": user_id,
            "email": "admin@silent-agents.com",
            "aud": "authenticated",
        }
        token = jwt.encode(payload, mock_settings_with_allowlist.supabase_jwt_secret, algorithm="HS256")
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with patch("nikita.api.dependencies.auth.get_settings", return_value=mock_settings_with_allowlist):
            result = await get_current_admin_user(credentials)

        assert str(result) == user_id
