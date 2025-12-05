"""Registration handler for email capture during Telegram onboarding.

Handles the registration flow when an unregistered user sends their email
after receiving the /start prompt.
"""

import re

from nikita.platforms.telegram.auth import TelegramAuth
from nikita.platforms.telegram.bot import TelegramBot


class RegistrationHandler:
    """Handle email capture during registration flow.

    Routes email input from unregistered users to the TelegramAuth
    registration flow, which sends a magic link for verification.
    """

    # Email validation regex (basic validation)
    EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    def __init__(
        self,
        telegram_auth: TelegramAuth,
        bot: TelegramBot,
    ):
        """Initialize RegistrationHandler.

        Args:
            telegram_auth: Auth handler for registration flow.
            bot: Telegram bot client for sending messages.
        """
        self.telegram_auth = telegram_auth
        self.bot = bot

    async def handle_email_input(
        self,
        telegram_id: int,
        chat_id: int,
        email: str,
    ) -> None:
        """Process email input from unregistered user.

        AC-FR004-001: Valid email triggers magic link
        AC-T008.1: Creates pending registration
        AC-T008.2: Sends confirmation message

        1. Validate email format
        2. Call TelegramAuth.register_user()
        3. Send confirmation message

        Args:
            telegram_id: User's Telegram ID.
            chat_id: Chat ID for response delivery.
            email: Email address provided by user.
        """
        # Strip whitespace
        email = email.strip()

        # Validate email format
        if not self.is_valid_email(email):
            await self.bot.send_message(
                chat_id=chat_id,
                text="Hmm, that doesn't look like a valid email. Try again?",
            )
            return

        # Initiate registration
        try:
            result = await self.telegram_auth.register_user(telegram_id, email)
        except ValueError as e:
            # Invalid email format from TelegramAuth validation
            await self.bot.send_message(
                chat_id=chat_id,
                text=f"That email doesn't seem right: {e}. Try again?",
            )
            return
        except Exception:
            # Unexpected error
            await self.bot.send_message(
                chat_id=chat_id,
                text="Something went wrong on my end. Try /start again?",
            )
            return

        # Handle result
        if result["status"] == "magic_link_sent":
            await self.bot.send_message(
                chat_id=chat_id,
                text=(
                    "Check your email - I sent you a verification link.\n\n"
                    "Once you verify, we can start chatting for real."
                ),
            )
        elif result["status"] == "already_registered":
            await self.bot.send_message(
                chat_id=chat_id,
                text="Looks like you're already registered. Just send me a message!",
            )
        else:
            # Unknown status or error
            error_msg = result.get("error", "Unknown error")
            await self.bot.send_message(
                chat_id=chat_id,
                text=f"Something went wrong: {error_msg}. Try /start again?",
            )

    def is_valid_email(self, text: str) -> bool:
        """Check if text looks like a valid email address.

        Basic validation - checks format only, not deliverability.

        Args:
            text: Text to validate.

        Returns:
            True if text matches email pattern.
        """
        return bool(self.EMAIL_REGEX.match(text.strip()))
