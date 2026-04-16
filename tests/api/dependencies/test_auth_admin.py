"""Tests for admin authentication dependency.

Admin access is gated on the JWT `app_metadata.role === "admin"` claim,
which is server-role-only (not client-writable). This replaces the older
email-domain / ADMIN_EMAILS allowlist mechanism and closes the
user_metadata.role self-elevation vector.

Acceptance Criteria:
- app_metadata.role == "admin" grants admin access.
- user_metadata.role == "admin" DOES NOT grant admin access
  (privilege escalation regression guard).
- Missing role / non-admin role denies access.
"""

import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

import jwt
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from nikita.api.dependencies.auth import get_current_admin_user, _is_admin_claim


@pytest.fixture
def mock_settings():
    """Mock settings with JWT secret."""
    settings = MagicMock()
    settings.supabase_jwt_secret = "test-jwt-secret"
    return settings


@pytest.fixture
def make_token(mock_settings):
    """Factory to build a JWT token with arbitrary claims.

    Callers pass the extra top-level claims to embed (e.g. app_metadata dict).
    'sub' + 'aud' are always populated.
    """

    def _make(extra_claims: dict | None = None, user_id: str | None = None) -> str:
        if user_id is None:
            user_id = str(uuid4())
        payload = {"sub": user_id, "aud": "authenticated"}
        if extra_claims:
            payload.update(extra_claims)
        return jwt.encode(
            payload, mock_settings.supabase_jwt_secret, algorithm="HS256"
        )

    return _make


class TestIsAdminClaim:
    """Unit tests for _is_admin_claim helper."""

    def test_app_metadata_role_admin_returns_true(self):
        assert _is_admin_claim({"app_metadata": {"role": "admin"}}) is True

    def test_app_metadata_role_player_returns_false(self):
        assert _is_admin_claim({"app_metadata": {"role": "player"}}) is False

    def test_user_metadata_role_admin_returns_false(self):
        """Privesc guard: user_metadata is client-writable, must never grant."""
        assert _is_admin_claim({"user_metadata": {"role": "admin"}}) is False

    def test_missing_app_metadata_returns_false(self):
        assert _is_admin_claim({}) is False

    def test_empty_app_metadata_returns_false(self):
        assert _is_admin_claim({"app_metadata": {}}) is False

    def test_app_metadata_no_role_returns_false(self):
        assert _is_admin_claim({"app_metadata": {"other": "value"}}) is False


class TestGetCurrentAdminUser:
    """Integration tests for get_current_admin_user FastAPI dependency."""

    @pytest.mark.asyncio
    async def test_app_metadata_role_admin_grants_admin(
        self, mock_settings, make_token
    ):
        """app_metadata.role == 'admin' grants admin access."""
        user_id = str(uuid4())
        token = make_token({"app_metadata": {"role": "admin"}}, user_id=user_id)
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with patch(
            "nikita.api.dependencies.auth.get_settings", return_value=mock_settings
        ):
            result = await get_current_admin_user(credentials)

        assert str(result) == user_id

    @pytest.mark.asyncio
    async def test_user_metadata_role_admin_does_not_grant_admin(
        self, mock_settings, make_token
    ):
        """Privesc regression guard — user_metadata.role is client-writable,
        MUST NOT grant admin access even when it says 'admin'.
        """
        token = make_token({"user_metadata": {"role": "admin"}})
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with patch(
            "nikita.api.dependencies.auth.get_settings", return_value=mock_settings
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_admin_user(credentials)

        assert exc_info.value.status_code == 403
        assert "admin" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_missing_role_denies_admin(self, mock_settings, make_token):
        """JWT with no role claim at all → 403."""
        token = make_token(None)
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with patch(
            "nikita.api.dependencies.auth.get_settings", return_value=mock_settings
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_admin_user(credentials)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_app_metadata_role_player_denies_admin(
        self, mock_settings, make_token
    ):
        """app_metadata.role == 'player' (non-admin role) → 403."""
        token = make_token({"app_metadata": {"role": "player"}})
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with patch(
            "nikita.api.dependencies.auth.get_settings", return_value=mock_settings
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_admin_user(credentials)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self, mock_settings):
        """Invalid token → 401 Unauthorized."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="invalid-token"
        )

        with patch(
            "nikita.api.dependencies.auth.get_settings", return_value=mock_settings
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_admin_user(credentials)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_expired_token_raises_401(self, mock_settings):
        """Expired token → 401."""
        import time

        user_id = str(uuid4())
        payload = {
            "sub": user_id,
            "aud": "authenticated",
            "app_metadata": {"role": "admin"},
            "exp": int(time.time()) - 3600,
        }
        token = jwt.encode(
            payload, mock_settings.supabase_jwt_secret, algorithm="HS256"
        )
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with patch(
            "nikita.api.dependencies.auth.get_settings", return_value=mock_settings
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_admin_user(credentials)

        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_missing_sub_claim_raises_403(self, mock_settings):
        """Token with no 'sub' claim → 403."""
        payload = {
            "aud": "authenticated",
            "app_metadata": {"role": "admin"},
        }
        token = jwt.encode(
            payload, mock_settings.supabase_jwt_secret, algorithm="HS256"
        )
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with patch(
            "nikita.api.dependencies.auth.get_settings", return_value=mock_settings
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_admin_user(credentials)

        assert exc_info.value.status_code == 403
