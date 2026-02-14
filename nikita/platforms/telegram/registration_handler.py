"""Registration handler for email capture during Telegram onboarding.

Handles the OTP registration flow when an unregistered user sends their email
after receiving the /start prompt. Sends OTP code (6-8 digits) to email.
"""

import logging
import re

from nikita.platforms.telegram.auth import TelegramAuth
from nikita.platforms.telegram.bot import TelegramBot

logger = logging.getLogger(__name__)


class RegistrationHandler:
    """Handle email capture during OTP registration flow.

    Routes email input from unregistered users to the TelegramAuth
    OTP flow, which sends an OTP code (6-8 digits) for verification in chat.
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

        AC-T2.9.1: Calls send_otp_code() instead of register_user()
        AC-T2.9.2: Bot message updated to prompt for OTP code
        AC-T2.9.3: Error handling for OTP send failures

        1. Validate email format
        2. Call TelegramAuth.send_otp_code()
        3. Send confirmation message prompting for code entry

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

        # AC-T2.9.1: Send OTP code via Supabase
        try:
            result = await self.telegram_auth.send_otp_code(
                telegram_id=telegram_id,
                chat_id=chat_id,
                email=email,
            )
        except ValueError as e:
            # Invalid email format from TelegramAuth validation
            await self.bot.send_message(
                chat_id=chat_id,
                text=f"That email doesn't seem right: {e}. Try again?",
            )
            return
        except Exception as e:
            # AC-T2.9.3: Error handling for OTP send failures
            logger.error(
                "OTP send failed for telegram_id=%s email=%s: %s",
                telegram_id,
                email,
                e,
                exc_info=True,
            )
            await self.bot.send_message(
                chat_id=chat_id,
                text="Something went wrong sending the code. Try /start again?",
            )
            return

        # Handle result
        # CRITICAL: Wrap send_message in try/except to prevent Telegram failures
        # from rolling back the database transaction (pending_registration creation)
        if result["status"] == "code_sent":
            # AC-T2.9.2: Updated message for OTP flow
            try:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "I sent a code to your email. 📧\n\n"
                        "Enter it here to get started!"
                    ),
                )
            except Exception as e:
                # Log but don't re-raise - pending registration was saved
                logger.error(
                    f"Failed to send OTP confirmation message: "
                    f"telegram_id={telegram_id}, error={e}"
                )
        elif result["status"] == "already_registered":
            try:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text="Looks like you're already registered. Just send me a message!",
                )
            except Exception as e:
                logger.error(
                    f"Failed to send already registered message: "
                    f"telegram_id={telegram_id}, error={e}"
                )
        else:
            # Unknown status or error
            error_msg = result.get("error", "Unknown error")
            try:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=f"Something went wrong: {error_msg}. Try /start again?",
                )
            except Exception as e:
                logger.error(
                    f"Failed to send error message: "
                    f"telegram_id={telegram_id}, error={e}"
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
