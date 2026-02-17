"""Tests for Spec 052: Infrastructure Cleanup.

Covers:
1. Task auth secret verification - dedicated task_auth_secret
2. Secret fallback behavior - telegram_webhook_secret fallback
3. Development mode - no secret configured
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from nikita.api.routes.tasks import _get_task_secret, verify_task_secret


class TestGetTaskSecret:
    """Test _get_task_secret() helper (Spec 052 BACK-06)."""

    def test_prefers_task_auth_secret(self):
        """BACK-06: Use dedicated task_auth_secret when available."""
        with patch("nikita.api.routes.tasks.get_settings") as mock_settings:
            settings = MagicMock()
            settings.task_auth_secret = "my-task-secret"
            settings.telegram_webhook_secret = "my-telegram-secret"
            mock_settings.return_value = settings

            assert _get_task_secret() == "my-task-secret"

    def test_falls_back_to_telegram_secret(self):
        """BACK-06: Falls back to telegram_webhook_secret."""
        with patch("nikita.api.routes.tasks.get_settings") as mock_settings:
            settings = MagicMock()
            settings.task_auth_secret = None
            settings.telegram_webhook_secret = "telegram-secret"
            mock_settings.return_value = settings

            assert _get_task_secret() == "telegram-secret"

    def test_returns_none_in_dev_mode(self):
        """Returns None when no secrets configured (dev mode)."""
        with patch("nikita.api.routes.tasks.get_settings") as mock_settings:
            settings = MagicMock()
            settings.task_auth_secret = None
            settings.telegram_webhook_secret = None
            mock_settings.return_value = settings

            assert _get_task_secret() is None


class TestVerifyTaskSecret:
    """Test verify_task_secret dependency."""

    @pytest.mark.asyncio
    async def test_accepts_valid_bearer_token(self):
        """Valid Bearer token passes verification."""
        with patch(
            "nikita.api.routes.tasks._get_task_secret",
            return_value="correct-secret",
        ):
            await verify_task_secret(authorization="Bearer correct-secret")

    @pytest.mark.asyncio
    async def test_rejects_invalid_token(self):
        """Invalid token raises 401."""
        with patch(
            "nikita.api.routes.tasks._get_task_secret",
            return_value="correct-secret",
        ):
            with pytest.raises(HTTPException) as exc_info:
                await verify_task_secret(authorization="Bearer wrong-secret")
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_rejects_missing_authorization(self):
        """Missing Authorization header raises 401."""
        with patch(
            "nikita.api.routes.tasks._get_task_secret",
            return_value="correct-secret",
        ):
            with pytest.raises(HTTPException) as exc_info:
                await verify_task_secret(authorization=None)
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_allows_dev_mode_without_secret(self):
        """Dev mode (no secret) allows access with warning."""
        with patch(
            "nikita.api.routes.tasks._get_task_secret",
            return_value=None,
        ):
            await verify_task_secret(authorization=None)

    @pytest.mark.asyncio
    async def test_rejects_non_bearer_format(self):
        """Non-Bearer format is rejected."""
        with patch(
            "nikita.api.routes.tasks._get_task_secret",
            return_value="correct-secret",
        ):
            with pytest.raises(HTTPException) as exc_info:
                await verify_task_secret(authorization="Basic correct-secret")
            assert exc_info.value.status_code == 401
