"""Tests for shared _decode_jwt helper.

Extracted from PR #113 review: DRY refactor of JWT decode logic
shared across get_current_user_id, get_authenticated_user, and
get_current_admin_user.
"""

import time
from unittest.mock import MagicMock, patch
from uuid import uuid4

import jwt as pyjwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from nikita.api.dependencies.auth import _decode_jwt


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.supabase_jwt_secret = "test-jwt-secret"
    return settings


@pytest.fixture
def make_credentials(mock_settings):
    def _make(payload: dict) -> HTTPAuthorizationCredentials:
        token = pyjwt.encode(payload, mock_settings.supabase_jwt_secret, algorithm="HS256")
        return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    return _make


class TestDecodeJwt:
    """Test suite for _decode_jwt shared helper."""

    @pytest.mark.asyncio
    async def test_returns_payload_for_valid_token(self, mock_settings, make_credentials):
        """Valid token returns decoded payload with sub and email."""
        payload = {"sub": str(uuid4()), "email": "test@example.com", "aud": "authenticated"}
        creds = make_credentials(payload)
        with patch("nikita.api.dependencies.auth.get_settings", return_value=mock_settings):
            result = await _decode_jwt(creds)
        assert result["sub"] == payload["sub"]
        assert result["email"] == payload["email"]

    @pytest.mark.asyncio
    async def test_raises_401_for_expired_token(self, mock_settings, make_credentials):
        """Expired token raises 401."""
        payload = {"sub": str(uuid4()), "aud": "authenticated", "exp": int(time.time()) - 3600}
        creds = make_credentials(payload)
        with patch("nikita.api.dependencies.auth.get_settings", return_value=mock_settings):
            with pytest.raises(HTTPException) as exc_info:
                await _decode_jwt(creds)
        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_raises_401_for_invalid_token(self, mock_settings):
        """Garbage token raises 401."""
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="garbage")
        with patch("nikita.api.dependencies.auth.get_settings", return_value=mock_settings):
            with pytest.raises(HTTPException) as exc_info:
                await _decode_jwt(creds)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_raises_401_for_wrong_audience(self, mock_settings):
        """Token with wrong audience raises 401."""
        payload = {"sub": str(uuid4()), "aud": "wrong-audience"}
        token = pyjwt.encode(payload, mock_settings.supabase_jwt_secret, algorithm="HS256")
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        with patch("nikita.api.dependencies.auth.get_settings", return_value=mock_settings):
            with pytest.raises(HTTPException) as exc_info:
                await _decode_jwt(creds)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_raises_500_when_no_jwt_secret(self):
        """Missing JWT secret raises 500."""
        settings = MagicMock()
        settings.supabase_jwt_secret = None
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="any")
        with patch("nikita.api.dependencies.auth.get_settings", return_value=settings):
            with pytest.raises(HTTPException) as exc_info:
                await _decode_jwt(creds)
        assert exc_info.value.status_code == 500
