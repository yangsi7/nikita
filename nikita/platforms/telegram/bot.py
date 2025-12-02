"""Telegram Bot API client wrapper.

Provides async interface to Telegram Bot API for sending messages,
managing typing indicators, and configuring webhooks.
"""

from httpx import AsyncClient
from nikita.config.settings import get_settings


class TelegramBot:
    """Telegram Bot API client wrapper."""

    def __init__(self):
        """Initialize bot with settings and HTTP client."""
        self.settings = get_settings()
        token = self.settings.telegram_bot_token
        if token:
            self.base_url = f"https://api.telegram.org/bot{token}"
        else:
            self.base_url = None  # Bot not configured
        self.client = AsyncClient()

    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: str = "HTML",
    ) -> dict:
        """Send text message to user.

        Args:
            chat_id: Telegram chat ID
            text: Message text (supports HTML formatting by default)
            parse_mode: Formatting mode ("HTML" or "Markdown")

        Returns:
            Telegram API response

        Raises:
            Exception: If Telegram API returns an error or bot not configured
        """
        if not self.base_url:
            raise Exception("Telegram bot not configured (missing TELEGRAM_BOT_TOKEN)")
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }

        response = await self.client.post(url, json=payload)
        data = response.json()

        if not data.get("ok"):
            error_code = data.get("error_code", response.status_code)
            description = data.get("description", "Unknown error")
            raise Exception(f"Telegram API error {error_code}: {description}")

        return data

    async def send_chat_action(
        self,
        chat_id: int,
        action: str = "typing",
    ) -> dict:
        """Send typing indicator or other chat action.

        Args:
            chat_id: Telegram chat ID
            action: Action type (typing, upload_photo, etc.)

        Returns:
            Telegram API response

        Raises:
            Exception: If Telegram API returns an error or bot not configured
        """
        if not self.base_url:
            raise Exception("Telegram bot not configured (missing TELEGRAM_BOT_TOKEN)")
        url = f"{self.base_url}/sendChatAction"
        payload = {
            "chat_id": chat_id,
            "action": action,
        }

        response = await self.client.post(url, json=payload)
        data = response.json()

        if not data.get("ok"):
            error_code = data.get("error_code", response.status_code)
            description = data.get("description", "Unknown error")
            raise Exception(f"Telegram API error {error_code}: {description}")

        return data

    async def set_webhook(self, url: str) -> dict:
        """Configure webhook URL for receiving updates.

        Args:
            url: Webhook URL (must be HTTPS)

        Returns:
            Telegram API response

        Raises:
            Exception: If Telegram API returns an error or bot not configured
        """
        if not self.base_url:
            raise Exception("Telegram bot not configured (missing TELEGRAM_BOT_TOKEN)")
        api_url = f"{self.base_url}/setWebhook"
        payload = {
            "url": url,
        }

        response = await self.client.post(api_url, json=payload)
        data = response.json()

        if not data.get("ok"):
            error_code = data.get("error_code", response.status_code)
            description = data.get("description", "Unknown error")
            raise Exception(f"Telegram API error {error_code}: {description}")

        return data

    async def close(self):
        """Close the HTTP client connection."""
        await self.client.aclose()
