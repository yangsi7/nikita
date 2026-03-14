"""Tests for Spec 052: Infrastructure Cleanup.

Covers:
1. Task auth secret verification - dedicated task_auth_secret
2. Secret fallback behavior - telegram_webhook_secret fallback (DEPRECATED — BKD-003)
3. Development mode - no secret configured
4. BKD-003: telegram_webhook_secret must NOT be used as fallback for task auth
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


class TestBKD003SecurityIsolation:
    """BKD-003: task_auth_secret must not fall back to telegram_webhook_secret.

    These tests document the CORRECT post-fix behavior.  They FAIL against the
    current code (which returns telegram_webhook_secret as a fallback) and PASS
    once the fallback branch is removed from _get_task_secret().
    """

    def test_get_task_secret_returns_none_when_only_telegram_secret_set(self):
        """BKD-003: _get_task_secret() must return None, not the telegram secret.

        Current code returns telegram_webhook_secret as a fallback — this test
        fails until that fallback is removed.
        """
        with patch("nikita.api.routes.tasks.get_settings") as mock_get_settings:
            settings = MagicMock()
            settings.task_auth_secret = None
            settings.telegram_webhook_secret = "tg-secret-123"
            mock_get_settings.return_value = settings

            result = _get_task_secret()

            # After the fix: task_auth_secret absent → no fallback → None (dev mode)
            # Before the fix: returns "tg-secret-123" — this assertion fails
            assert result is None, (
                "BKD-003: _get_task_secret() must not fall back to "
                "telegram_webhook_secret.  Got %r instead of None." % result
            )

    @pytest.mark.asyncio
    async def test_verify_task_secret_rejects_telegram_secret_as_bearer_token(self):
        """BKD-003: verify_task_secret must raise 401 when bearer token is the telegram secret.

        With task_auth_secret="real-task-secret" and telegram_webhook_secret="tg-secret-123",
        a request bearing 'Authorization: Bearer tg-secret-123' must receive 401.
        The telegram secret must not be accepted as a valid task auth token.
        """
        with patch("nikita.api.routes.tasks.get_settings") as mock_get_settings:
            settings = MagicMock()
            settings.task_auth_secret = "real-task-secret"
            settings.telegram_webhook_secret = "tg-secret-123"
            mock_get_settings.return_value = settings

            # Presenting the telegram secret as a Bearer token must be rejected.
            # verify_task_secret checks authorization == "Bearer <task_auth_secret>"
            # which is "Bearer real-task-secret", so "Bearer tg-secret-123" must 401.
            with pytest.raises(HTTPException) as exc_info:
                await verify_task_secret(authorization="Bearer tg-secret-123")
            assert exc_info.value.status_code == 401, (
                "BKD-003: Task endpoint accepted telegram_webhook_secret as Bearer token. "
                "Task and Telegram auth must be independent secrets."
            )
