"""Telegram Bot API client wrapper.

Provides async interface to Telegram Bot API for sending messages,
managing typing indicators, and configuring webhooks.

SEC-03: HTML escaping for all user-provided content to prevent injection attacks.
"""

import html
from httpx import AsyncClient
from nikita.config.settings import get_settings


def escape_html(text: str) -> str:
    """
    Escape HTML special characters to prevent injection attacks.

    Converts:
    - & → &amp;
    - < → &lt;
    - > → &gt;
    - " → &quot;
    - ' → &#x27;

    Args:
        text: Raw text that may contain HTML special characters.

    Returns:
        HTML-escaped text safe for Telegram HTML parse mode.
    """
    return html.escape(text, quote=True)


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
        escape: bool = True,
    ) -> dict:
        """Send text message to user.

        SEC-03: Automatically escapes HTML by default to prevent injection attacks.

        Args:
            chat_id: Telegram chat ID.
            text: Message text (supports HTML formatting by default).
            parse_mode: Formatting mode ("HTML" or "Markdown").
            escape: If True, escapes HTML special characters in text.
                   Set to False ONLY if text is already trusted/escaped.

        Returns:
            Telegram API response.

        Raises:
            Exception: If Telegram API returns an error or bot not configured.
        """
        if not self.base_url:
            raise Exception("Telegram bot not configured (missing TELEGRAM_BOT_TOKEN)")

        # SEC-03: Escape HTML by default to prevent injection
        if escape and parse_mode == "HTML":
            text = escape_html(text)

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

    async def send_message_with_keyboard(
        self,
        chat_id: int,
        text: str,
        keyboard: list[list[dict]],
        parse_mode: str = "HTML",
        escape: bool = True,
    ) -> dict:
        """Send message with inline keyboard buttons.

        Spec 028: Voice onboarding choice presentation.

        Args:
            chat_id: Telegram chat ID.
            text: Message text.
            keyboard: Inline keyboard as list of rows, each row is list of buttons.
                Each button is a dict with 'text' and either 'callback_data' or 'url'.
                Example: [[{"text": "Voice 📞", "url": "https://..."}, {"text": "Text 💬", "callback_data": "text_onboard"}]]
            parse_mode: Formatting mode ("HTML" or "Markdown").
            escape: If True, escapes HTML special characters in text.

        Returns:
            Telegram API response.
        """
        if not self.base_url:
            raise Exception("Telegram bot not configured (missing TELEGRAM_BOT_TOKEN)")

        if escape and parse_mode == "HTML":
            text = escape_html(text)

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "reply_markup": {
                "inline_keyboard": keyboard,
            },
        }

        response = await self.client.post(url, json=payload)
        data = response.json()

        if not data.get("ok"):
            error_code = data.get("error_code", response.status_code)
            description = data.get("description", "Unknown error")
            raise Exception(f"Telegram API error {error_code}: {description}")

        return data

    async def answer_callback_query(
        self,
        callback_query_id: str,
        text: str | None = None,
        show_alert: bool = False,
    ) -> dict:
        """Answer a callback query from inline keyboard.

        Args:
            callback_query_id: ID of the callback query.
            text: Optional notification text to show.
            show_alert: If True, show as alert popup.

        Returns:
            Telegram API response.
        """
        if not self.base_url:
            raise Exception("Telegram bot not configured (missing TELEGRAM_BOT_TOKEN)")

        url = f"{self.base_url}/answerCallbackQuery"
        payload = {
            "callback_query_id": callback_query_id,
        }
        if text:
            payload["text"] = text
        if show_alert:
            payload["show_alert"] = show_alert

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

    async def set_webhook(self, url: str, secret_token: str | None = None) -> dict:
        """Configure webhook URL for receiving updates.

        Args:
            url: Webhook URL (must be HTTPS)
            secret_token: Secret token for webhook validation.
                         If provided, Telegram will send this in the
                         X-Telegram-Bot-Api-Secret-Token header.

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

        # SEC-01: Include secret_token for webhook signature validation
        if secret_token:
            payload["secret_token"] = secret_token

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


# Singleton instance
_bot_instance: TelegramBot | None = None


def get_bot() -> TelegramBot:
    """Get or create singleton TelegramBot instance.

    Returns:
        TelegramBot instance.
    """
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = TelegramBot()
    return _bot_instance
