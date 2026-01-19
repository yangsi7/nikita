"""OTP verification handler for Telegram registration flow.

Handles OTP code entry (6-8 digits) in Telegram chat during the registration flow.
Part of v2.0 OTP authentication (replaces magic link redirects).

Enhanced in 017-enhanced-onboarding to route new users to profile collection.
Enhanced in 028-voice-onboarding to offer voice vs text onboarding choice.
Fixed in Dec 2025: Added retry limit to prevent infinite verification loop.
Fixed in Dec 2025: Accept 6-8 digit codes (Supabase sends 8-digit codes).
"""

import logging
from typing import TYPE_CHECKING

from nikita.config.settings import get_settings
from nikita.platforms.telegram.auth import TelegramAuth
from nikita.platforms.telegram.bot import TelegramBot

if TYPE_CHECKING:
    from nikita.db.repositories.pending_registration_repository import (
        PendingRegistrationRepository,
    )
    from nikita.db.repositories.profile_repository import (
        OnboardingStateRepository,
        ProfileRepository,
    )
    from nikita.db.repositories.user_repository import UserRepository
    from nikita.platforms.telegram.onboarding.handler import OnboardingHandler


logger = logging.getLogger(__name__)

# Maximum failed OTP attempts before user must restart with /start
MAX_OTP_ATTEMPTS = 3


class OTPVerificationHandler:
    """Handle OTP code verification in Telegram chat.

    AC-T2.4.1: OTPVerificationHandler class exists
    AC-T2.4.2: handle(telegram_id, chat_id, code) method verifies OTP
    AC-T2.4.3: On success: sends welcome message (or routes to onboarding)
    AC-T2.4.4: On invalid code: sends error message
    AC-T2.4.5: On expired code: sends error message
    AC-T2.4.6: Logs all verification attempts

    017-enhanced-onboarding additions:
    AC-T2.2-001: After OTP verification success, check if user has profile
    AC-T2.2-002: If no profile, route to OnboardingHandler instead of welcome message
    AC-T2.2-003: If profile exists, send normal welcome message
    """

    def __init__(
        self,
        telegram_auth: TelegramAuth,
        bot: TelegramBot,
        pending_repo: "PendingRegistrationRepository | None" = None,
        onboarding_handler: "OnboardingHandler | None" = None,
        profile_repository: "ProfileRepository | None" = None,
        user_repository: "UserRepository | None" = None,
    ):
        """Initialize OTPVerificationHandler.

        Args:
            telegram_auth: Auth handler for OTP verification.
            bot: Telegram bot client for sending messages.
            pending_repo: Repository for pending registrations (for retry tracking).
            onboarding_handler: Optional handler for new user onboarding (017 feature).
            profile_repository: Optional repo to check for existing profile.
            user_repository: Optional repo to check onboarding_status (028 feature).
        """
        self.telegram_auth = telegram_auth
        self.bot = bot
        self.pending_repo = pending_repo
        self.onboarding_handler = onboarding_handler
        self.profile_repo = profile_repository
        self.user_repo = user_repository

    async def handle(
        self,
        telegram_id: int,
        chat_id: int,
        code: str,
    ) -> bool:
        """Verify OTP code and send appropriate response.

        AC-T2.4.2: Main handler method for OTP verification.

        Args:
            telegram_id: User's Telegram ID.
            chat_id: Chat ID for response delivery.
            code: OTP code (6-8 digits) from user.

        Returns:
            True if verification succeeded, False otherwise.
        """
        # AC-T2.4.6: Log verification attempt
        logger.info(
            f"OTP verification attempt: telegram_id={telegram_id}, "
            f"code_length={len(code)}"
        )

        try:
            # Verify OTP code via TelegramAuth
            user = await self.telegram_auth.verify_otp_code(telegram_id, code)

            # AC-T2.4.6: Log success
            logger.info(
                f"OTP verification successful: telegram_id={telegram_id}, "
                f"user_id={user.id}"
            )

            # Spec 028: Check onboarding_status first (voice onboarding)
            # Falls back to profile check (017 text onboarding) for backwards compatibility
            needs_onboarding = False
            onboarding_status = "pending"  # Default

            if self.user_repo is not None:
                try:
                    user_record = await self.user_repo.get(user.id)
                    if user_record:
                        onboarding_status = user_record.onboarding_status or "pending"
                        # User needs onboarding if status is pending or in_progress
                        needs_onboarding = onboarding_status in ("pending", "in_progress")
                        logger.info(
                            f"Onboarding status check: user_id={user.id}, "
                            f"status={onboarding_status}, needs_onboarding={needs_onboarding}"
                        )
                except Exception as e:
                    logger.warning(f"Failed to check onboarding status: {e}")
                    # Fall back to profile check
                    needs_onboarding = True

            # AC-T2.2-001: Fallback to profile check (017 feature)
            if not needs_onboarding:
                has_profile = False
                if self.profile_repo is not None:
                    try:
                        profile = await self.profile_repo.get_by_user_id(user.id)
                        has_profile = profile is not None
                        if not has_profile:
                            needs_onboarding = True
                        logger.info(
                            f"Profile check: user_id={user.id}, has_profile={has_profile}"
                        )
                    except Exception as e:
                        logger.warning(f"Failed to check profile: {e}")

            # Spec 028: Offer voice vs text onboarding choice
            if needs_onboarding:
                logger.info(f"Routing to onboarding choice: telegram_id={telegram_id}")
                try:
                    await self._offer_onboarding_choice(
                        chat_id=chat_id,
                        user_id=str(user.id),
                        telegram_id=telegram_id,
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to offer onboarding choice: "
                        f"telegram_id={telegram_id}, error={e}"
                    )
                    # Fall back to text onboarding
                    if self.onboarding_handler is not None:
                        await self.onboarding_handler.start(
                            telegram_id=telegram_id,
                            chat_id=chat_id,
                        )
                return True

            # AC-T2.2-003 / AC-T2.4.3: Send welcome message (has profile or no onboarding)
            # CRITICAL: Wrap in try/except to prevent Telegram failures from
            # rolling back the database transaction. User creation MUST persist
            # even if we can't send the confirmation message.
            try:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "Perfect! You're all set up now. 💕\n\n"
                        "So... what's on your mind?"
                    ),
                )
            except Exception as e:
                # Log but don't re-raise - user is already created in database
                logger.error(
                    f"Failed to send welcome message after OTP verification: "
                    f"telegram_id={telegram_id}, error={e}"
                )
                # Still return True - registration succeeded even if message failed

            return True

        except ValueError as e:
            error_msg = str(e).lower()

            # AC-T2.4.6: Log failure
            logger.warning(
                f"OTP verification failed: telegram_id={telegram_id}, "
                f"error={e}"
            )

            # Increment attempt counter and check for max attempts
            # SECURITY: Fail closed - if we can't track attempts, force restart
            if self.pending_repo is None:
                logger.error(
                    f"[OTP-DEBUG] FAIL CLOSED: pending_repo is None, forcing restart: "
                    f"telegram_id={telegram_id}"
                )
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "Something went wrong. 😔\n\n"
                        "Type /start to try again!"
                    ),
                )
                return False

            try:
                new_attempts = await self.pending_repo.increment_attempts(telegram_id)

                # -1 means record was deleted/expired during verification
                if new_attempts == -1:
                    logger.warning(
                        f"[OTP-DEBUG] Record not found during increment: telegram_id={telegram_id}"
                    )
                    await self.bot.send_message(
                        chat_id=chat_id,
                        text=(
                            "Your session expired. 😔\n\n"
                            "Type /start to try again!"
                        ),
                    )
                    return False

                attempts_remaining = MAX_OTP_ATTEMPTS - new_attempts
                logger.info(
                    f"[OTP-DEBUG] Attempt #{new_attempts}/{MAX_OTP_ATTEMPTS} for telegram_id={telegram_id}"
                )

                # If max attempts reached, delete pending and force restart
                if attempts_remaining <= 0:
                    await self.pending_repo.delete(telegram_id)
                    logger.warning(
                        f"Max OTP attempts reached, deleted pending registration: "
                        f"telegram_id={telegram_id}"
                    )
                    await self.bot.send_message(
                        chat_id=chat_id,
                        text=(
                            "Too many failed attempts. 😔\n\n"
                            "Type /start to try again!"
                        ),
                    )
                    return False

            except Exception as repo_error:
                # SECURITY: Fail closed - if we can't track attempts, force restart
                logger.error(
                    f"[OTP-DEBUG] FAIL CLOSED: Repository error, forcing restart: "
                    f"telegram_id={telegram_id}, error={repo_error}"
                )
                try:
                    await self.pending_repo.delete(telegram_id)
                except Exception:
                    pass  # Best effort cleanup
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "Something went wrong. 😔\n\n"
                        "Type /start to try again!"
                    ),
                )
                return False

            # AC-T2.4.4 & AC-T2.4.5: Send appropriate error message with attempts remaining
            if "expired" in error_msg:
                # AC-T2.4.5: Expired code - tell user to restart
                await self.pending_repo.delete(telegram_id) if self.pending_repo else None
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "That code has expired. 😔\n\n"
                        "Type /start to get a fresh code!"
                    ),
                )
            elif "invalid" in error_msg:
                # AC-T2.4.4: Invalid code message with attempts remaining
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        f"Hmm, that code doesn't look right. 🤔\n\n"
                        f"You have {attempts_remaining} attempt(s) left. "
                        f"Check your email and try again!"
                    ),
                )
            else:
                # Generic error
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "Something went wrong verifying that code.\n\n"
                        "Type /start to try again!"
                    ),
                )

            return False

        except Exception as e:
            # AC-T2.4.6: Log unexpected error
            logger.error(
                f"OTP verification error: telegram_id={telegram_id}, "
                f"error={e}",
                exc_info=True,
            )

            await self.bot.send_message(
                chat_id=chat_id,
                text=(
                    "Something went wrong on my end. 😅\n\n"
                    "Try /start again?"
                ),
            )

            return False

    async def _offer_onboarding_choice(
        self,
        chat_id: int,
        user_id: str,
        telegram_id: int,
    ) -> None:
        """Offer voice vs text onboarding choice.

        Spec 028: Present inline keyboard with voice and text options.

        Args:
            chat_id: Telegram chat ID for sending message.
            user_id: User's UUID for building portal URL.
            telegram_id: Telegram user ID for fallback.
        """
        settings = get_settings()
        portal_url = settings.portal_url or "https://nikita.app"

        # Build voice onboarding URL (portal page that initiates voice call)
        voice_url = f"{portal_url}/onboarding/voice?user_id={user_id}"

        # Inline keyboard with voice and text options
        keyboard = [
            [
                {"text": "📞 Voice Call (Recommended)", "url": voice_url},
            ],
            [
                {"text": "💬 Text Chat Instead", "callback_data": "onboarding_text"},
            ],
        ]

        message = """You're all set! 🎉

Before we really get to know each other, I'd love to have a quick chat to learn about you.

*Voice Call* - Have a 2-min conversation with me (I promise I'm fun to talk to 😏)

*Text Chat* - Answer a few questions right here

What do you prefer?"""

        await self.bot.send_message_with_keyboard(
            chat_id=chat_id,
            text=message,
            keyboard=keyboard,
            parse_mode="Markdown",
            escape=False,  # Message is trusted
        )

        logger.info(
            f"Offered onboarding choice to telegram_id={telegram_id}, user_id={user_id}"
        )

    async def handle_callback(
        self,
        callback_query_id: str,
        telegram_id: int,
        chat_id: int,
        data: str,
    ) -> bool:
        """Handle callback query from inline keyboard.

        Spec 028: Route text onboarding callback.

        Args:
            callback_query_id: ID of the callback query to answer.
            telegram_id: Telegram user ID.
            chat_id: Chat ID for messages.
            data: Callback data from button.

        Returns:
            True if handled, False otherwise.
        """
        if data == "onboarding_text":
            # Answer callback first
            await self.bot.answer_callback_query(
                callback_query_id=callback_query_id,
                text="Starting text onboarding...",
            )

            # Start text-based onboarding (017 flow)
            if self.onboarding_handler is not None:
                await self.onboarding_handler.start(
                    telegram_id=telegram_id,
                    chat_id=chat_id,
                )
                logger.info(
                    f"Started text onboarding via callback: telegram_id={telegram_id}"
                )
                return True
            else:
                # No onboarding handler configured, send welcome
                await self.bot.send_message(
                    chat_id=chat_id,
                    text="Perfect! You're all set up now. 💕\n\nSo... what's on your mind?",
                )
                return True

        return False

    @staticmethod
    def is_otp_code(text: str) -> bool:
        """Check if text looks like an OTP code (6-8 digits).

        Supabase may send 6 or 8 digit codes depending on configuration.
        Accept both to be resilient to config changes.

        Args:
            text: Text to check.

        Returns:
            True if text is 6-8 digits.
        """
        text = text.strip()
        return text.isdigit() and 6 <= len(text) <= 8
