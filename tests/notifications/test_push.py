"""Tests for push notification helper (Spec 070, T6).

AC-4.5: Push failures are logged but don't block game flow
AC-3.3: Missing subscriptions return sent=0 (no error)
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest

from nikita.notifications.push import send_push


@pytest.mark.asyncio
class TestSendPush:
    """Tests for send_push helper."""

    @pytest.fixture
    def user_id(self):
        return uuid4()

    @pytest.fixture
    def mock_settings(self):
        settings = MagicMock()
        settings.supabase_url = "https://test.supabase.co"
        settings.supabase_service_key = "test-service-key"
        return settings

    async def test_successful_push(self, user_id, mock_settings):
        """Successful push returns sent/failed counts."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"sent": 2, "failed": 0}

        with (
            patch("nikita.notifications.push.get_settings", return_value=mock_settings),
            patch("nikita.notifications.push.httpx.AsyncClient") as mock_client_cls,
        ):
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await send_push(user_id, "Test Title", "Test Body")

            assert result["sent"] == 2
            assert result["failed"] == 0
            mock_client.post.assert_called_once()

    async def test_no_subscriptions_returns_zero(self, user_id, mock_settings):
        """No subscriptions returns sent=0 without error."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "sent": 0,
            "failed": 0,
            "message": "No subscriptions found",
        }

        with (
            patch("nikita.notifications.push.get_settings", return_value=mock_settings),
            patch("nikita.notifications.push.httpx.AsyncClient") as mock_client_cls,
        ):
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await send_push(user_id, "Title", "Body")

            assert result["sent"] == 0

    async def test_http_error_returns_error(self, user_id, mock_settings):
        """HTTP error returns error dict, doesn't raise."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with (
            patch("nikita.notifications.push.get_settings", return_value=mock_settings),
            patch("nikita.notifications.push.httpx.AsyncClient") as mock_client_cls,
        ):
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await send_push(user_id, "Title", "Body")

            assert result["sent"] == 0
            assert "error" in result
            assert "500" in result["error"]

    async def test_network_error_returns_error(self, user_id, mock_settings):
        """Network error returns error dict, doesn't raise."""
        with (
            patch("nikita.notifications.push.get_settings", return_value=mock_settings),
            patch("nikita.notifications.push.httpx.AsyncClient") as mock_client_cls,
        ):
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.ConnectError("Connection refused")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await send_push(user_id, "Title", "Body")

            assert result["sent"] == 0
            assert "error" in result

    async def test_no_supabase_url_skips(self, user_id):
        """Missing SUPABASE_URL skips push gracefully."""
        mock_settings = MagicMock()
        mock_settings.supabase_url = None

        with patch("nikita.notifications.push.get_settings", return_value=mock_settings):
            result = await send_push(user_id, "Title", "Body")

            assert result["sent"] == 0
            assert "not configured" in result.get("error", "")

    async def test_custom_url_and_tag(self, user_id, mock_settings):
        """Custom url and tag are passed to edge function."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"sent": 1, "failed": 0}

        with (
            patch("nikita.notifications.push.get_settings", return_value=mock_settings),
            patch("nikita.notifications.push.httpx.AsyncClient") as mock_client_cls,
        ):
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            await send_push(
                user_id,
                "Chapter Unlocked",
                "Welcome to Intrigue",
                url="/engagement",
                tag="chapter-advance",
            )

            call_args = mock_client.post.call_args
            payload = call_args.kwargs.get("json") or call_args[1].get("json")
            assert payload["url"] == "/engagement"
            assert payload["tag"] == "chapter-advance"
