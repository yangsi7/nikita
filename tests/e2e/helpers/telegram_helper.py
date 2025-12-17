"""
Telegram Webhook Simulator for E2E Tests

Simulates Telegram webhook payloads to test the backend without a real bot.
Used for testing OTP flow and message handling.

For Claude Code execution, this sends HTTP requests to Cloud Run.
For CI/CD, same approach with environment-configured BACKEND_URL.
"""

import os
import time
from dataclasses import dataclass
from typing import Optional

import httpx


# Default backend URL (Cloud Run)
BACKEND_URL = os.getenv(
    "NIKITA_BACKEND_URL",
    "https://nikita-api-1040094048579.us-central1.run.app"
)
WEBHOOK_URL = f"{BACKEND_URL}/api/v1/telegram/webhook"


@dataclass
class TelegramUser:
    """Represents a Telegram user in webhook payloads."""
    id: int
    is_bot: bool = False
    first_name: str = "E2E Test"
    last_name: Optional[str] = "User"
    username: Optional[str] = None
    language_code: str = "en"


@dataclass
class TelegramChat:
    """Represents a Telegram chat in webhook payloads."""
    id: int
    type: str = "private"
    first_name: str = "E2E Test"
    last_name: Optional[str] = "User"
    username: Optional[str] = None


class TelegramWebhookSimulator:
    """Simulate Telegram webhook calls to the backend.

    Usage:
        simulator = TelegramWebhookSimulator()
        response = await simulator.send_command("/start", telegram_id=999888777)
        response = await simulator.send_message("Hello!", telegram_id=999888777)

    For authenticated testing, provide the webhook secret token.
    """

    def __init__(
        self,
        webhook_url: str = WEBHOOK_URL,
        secret_token: Optional[str] = None,
    ):
        """Initialize the webhook simulator.

        Args:
            webhook_url: URL of the webhook endpoint.
            secret_token: Optional X-Telegram-Bot-Api-Secret-Token for auth.
        """
        self.webhook_url = webhook_url
        self.secret_token = secret_token or os.getenv("TELEGRAM_WEBHOOK_SECRET")
        self._update_id_counter = int(time.time() * 1000) % 1_000_000
        self._message_id_counter = 1

    def _next_update_id(self) -> int:
        """Generate next unique update ID."""
        self._update_id_counter += 1
        return self._update_id_counter

    def _next_message_id(self) -> int:
        """Generate next unique message ID."""
        self._message_id_counter += 1
        return self._message_id_counter

    def _build_user(self, telegram_id: int) -> dict:
        """Build Telegram user object."""
        return {
            "id": telegram_id,
            "is_bot": False,
            "first_name": "E2E Test",
            "last_name": "User",
            "username": f"e2e_test_{telegram_id}",
            "language_code": "en",
        }

    def _build_chat(self, telegram_id: int) -> dict:
        """Build Telegram chat object (private chat = same ID as user)."""
        return {
            "id": telegram_id,
            "type": "private",
            "first_name": "E2E Test",
            "last_name": "User",
            "username": f"e2e_test_{telegram_id}",
        }

    def _build_message(self, telegram_id: int, text: str) -> dict:
        """Build Telegram message object."""
        return {
            "message_id": self._next_message_id(),
            "from": self._build_user(telegram_id),
            "chat": self._build_chat(telegram_id),
            "date": int(time.time()),
            "text": text,
        }

    def _build_update(self, telegram_id: int, text: str) -> dict:
        """Build complete Telegram Update payload.

        See: https://core.telegram.org/bots/api#update
        """
        return {
            "update_id": self._next_update_id(),
            "message": self._build_message(telegram_id, text),
        }

    def _build_command_update(
        self,
        telegram_id: int,
        command: str,
        args: Optional[str] = None,
    ) -> dict:
        """Build Telegram Update with command entity.

        Commands like /start are marked with 'entities' in the message.
        """
        text = command if not args else f"{command} {args}"
        update = self._build_update(telegram_id, text)

        # Add bot_command entity
        update["message"]["entities"] = [
            {
                "type": "bot_command",
                "offset": 0,
                "length": len(command),
            }
        ]

        return update

    async def send_message(
        self,
        text: str,
        telegram_id: int,
        timeout: float = 30.0,
    ) -> httpx.Response:
        """Send a text message via webhook.

        Args:
            text: Message text to send.
            telegram_id: Telegram user ID.
            timeout: Request timeout in seconds.

        Returns:
            HTTP response from the webhook endpoint.
        """
        payload = self._build_update(telegram_id, text)
        headers = self._build_headers()

        async with httpx.AsyncClient() as client:
            return await client.post(
                self.webhook_url,
                json=payload,
                headers=headers,
                timeout=timeout,
            )

    async def send_command(
        self,
        command: str,
        telegram_id: int,
        args: Optional[str] = None,
        timeout: float = 30.0,
    ) -> httpx.Response:
        """Send a command message (e.g., /start) via webhook.

        Args:
            command: Command to send (e.g., "/start").
            telegram_id: Telegram user ID.
            args: Optional command arguments.
            timeout: Request timeout in seconds.

        Returns:
            HTTP response from the webhook endpoint.
        """
        payload = self._build_command_update(telegram_id, command, args)
        headers = self._build_headers()

        async with httpx.AsyncClient() as client:
            return await client.post(
                self.webhook_url,
                json=payload,
                headers=headers,
                timeout=timeout,
            )

    def _build_headers(self) -> dict:
        """Build request headers including optional secret token."""
        headers = {
            "Content-Type": "application/json",
        }
        if self.secret_token:
            headers["X-Telegram-Bot-Api-Secret-Token"] = self.secret_token
        return headers


# ==================== Utility Functions ====================

def generate_test_telegram_id() -> int:
    """Generate a unique test Telegram ID in the 900M-999M range.

    This range avoids collision with real Telegram IDs.
    """
    import random
    return random.randint(900_000_000, 999_999_999)


def generate_test_email(telegram_id: int) -> str:
    """Generate a test email address for a given Telegram ID."""
    return f"nikita.e2e.{telegram_id}@test.example.com"


# ==================== Test Data Classes ====================

@dataclass
class WebhookTestData:
    """Container for webhook test data."""
    telegram_id: int
    email: str
    chat_id: int  # Same as telegram_id for private chats

    @classmethod
    def create(cls) -> "WebhookTestData":
        """Create new test data with unique IDs."""
        telegram_id = generate_test_telegram_id()
        return cls(
            telegram_id=telegram_id,
            email=generate_test_email(telegram_id),
            chat_id=telegram_id,
        )
