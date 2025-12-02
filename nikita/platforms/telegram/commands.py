"""Telegram bot command handlers.

Handles standard bot commands:
- /start: Initialize new user onboarding or welcome back
- /help: Display available commands
- /status: Show current game state (chapter, score hint)
- /call: Voice call information (future integration)
"""

from nikita.db.repositories.user_repository import UserRepository
from nikita.platforms.telegram.auth import TelegramAuth
from nikita.platforms.telegram.bot import TelegramBot


class CommandHandler:
    """Handle Telegram bot command messages.

    Routes commands to appropriate handlers based on command name.
    All handlers send responses via TelegramBot.
    """

    # Supported commands
    COMMANDS = {
        "start": "_handle_start",
        "help": "_handle_help",
        "status": "_handle_status",
        "call": "_handle_call",
    }

    def __init__(
        self,
        user_repository: UserRepository,
        telegram_auth: TelegramAuth,
        bot: TelegramBot,
    ):
        """Initialize CommandHandler.

        Args:
            user_repository: Repository for user lookups.
            telegram_auth: Auth handler for registration.
            bot: Telegram bot client for sending messages.
        """
        self.user_repository = user_repository
        self.telegram_auth = telegram_auth
        self.bot = bot

    async def handle(self, message: dict) -> None:
        """Route incoming command to appropriate handler.

        AC-T009.1: Routes commands by name

        Args:
            message: Telegram message dict with 'text' field containing command.
        """
        text = message.get("text", "")
        chat_id = message["chat"]["id"]

        # Parse command (handle /command@botname format)
        command_text = text.split()[0] if text else ""
        command = command_text.lstrip("/").split("@")[0].lower()

        # Route to handler
        handler_name = self.COMMANDS.get(command, "_handle_unknown")
        handler = getattr(self, handler_name)

        await handler(message)

    async def _handle_start(self, message: dict) -> None:
        """Handle /start command - new user onboarding or welcome back.

        AC-T009.2: Checks if user exists, initiates registration
        AC-FR003-001: New user → welcome message + email prompt

        Args:
            message: Telegram message dict.
        """
        telegram_id = message["from"]["id"]
        chat_id = message["chat"]["id"]
        first_name = message["from"].get("first_name", "there")

        # Check if user already registered
        user = await self.user_repository.get_by_telegram_id(telegram_id)

        if user is not None:
            # Existing user - welcome back
            response = (
                f"Hey {first_name}, good to see you again.\n\n"
                f"Ready to pick up where we left off?"
            )
        else:
            # New user - prompt for registration
            response = (
                f"Hey {first_name}... I don't think we've met before.\n\n"
                f"If you want to get to know me, I'll need your email. "
                f"Just send it to me and I'll send you a verification link.\n\n"
                f"(Don't worry, I'm not gonna spam you or anything.)"
            )

        await self.bot.send_message(chat_id=chat_id, text=response)

    async def _handle_help(self, message: dict) -> None:
        """Handle /help command - display available commands.

        AC-T009.3: Returns available commands

        Args:
            message: Telegram message dict.
        """
        chat_id = message["chat"]["id"]

        help_text = (
            "<b>Available Commands:</b>\n\n"
            "/start - Begin your journey with Nikita\n"
            "/help - Show this message\n"
            "/status - See where you stand with Nikita\n"
            "/call - Request a voice call (when available)\n\n"
            "<i>Or just... message me. That's kind of the whole point.</i>"
        )

        await self.bot.send_message(chat_id=chat_id, text=help_text, parse_mode="HTML")

    async def _handle_status(self, message: dict) -> None:
        """Handle /status command - show current game state.

        AC-T009.4: Returns chapter/score hint

        Args:
            message: Telegram message dict.
        """
        telegram_id = message["from"]["id"]
        chat_id = message["chat"]["id"]

        # Check if user registered
        user = await self.user_repository.get_by_telegram_id(telegram_id)

        if user is None:
            # Not registered yet
            response = (
                "You haven't started yet. Send /start if you want to get to know me."
            )
        else:
            # Get chapter name and score hint
            chapter_name = self._get_chapter_name(user.chapter)
            score_hint = self._get_score_hint(float(user.relationship_score))

            response = (
                f"<b>Where We Stand:</b>\n\n"
                f"Chapter: {chapter_name}\n"
                f"Vibe: {score_hint}\n\n"
                f"<i>(Keep messaging me if you want things to get better... or worse.)</i>"
            )

        await self.bot.send_message(chat_id=chat_id, text=response, parse_mode="HTML")

    async def _handle_call(self, message: dict) -> None:
        """Handle /call command - voice call information.

        Args:
            message: Telegram message dict.
        """
        chat_id = message["chat"]["id"]

        response = (
            "Voice calls aren't available yet.\n\n"
            "But when they are, you'll be able to actually talk to me. "
            "Imagine that."
        )

        await self.bot.send_message(chat_id=chat_id, text=response)

    async def _handle_unknown(self, message: dict) -> None:
        """Handle unknown commands gracefully.

        AC-T009.5: Unknown commands handled gracefully

        Args:
            message: Telegram message dict.
        """
        chat_id = message["chat"]["id"]
        text = message.get("text", "")

        response = (
            f"I don't know what '{text}' means.\n\n"
            f"Try /help if you're confused."
        )

        await self.bot.send_message(chat_id=chat_id, text=response)

    @staticmethod
    def _get_chapter_name(chapter: int) -> str:
        """Get human-readable chapter name.

        Args:
            chapter: Chapter number (1-5).

        Returns:
            Chapter name string.
        """
        chapter_names = {
            1: "Chapter 1: First Impressions",
            2: "Chapter 2: Getting Closer",
            3: "Chapter 3: Real Talk",
            4: "Chapter 4: Deep Connection",
            5: "Chapter 5: All In",
        }
        return chapter_names.get(chapter, f"Chapter {chapter}")

    @staticmethod
    def _get_score_hint(score: float) -> str:
        """Get vague hint about relationship score.

        Returns emotional description rather than number (per game design).

        Args:
            score: Relationship score (0-100).

        Returns:
            Score hint string.
        """
        if score >= 80:
            return "Things are really good 🔥"
        elif score >= 60:
            return "Pretty solid tbh"
        elif score >= 40:
            return "It's... complicated"
        elif score >= 20:
            return "Not great, not gonna lie"
        else:
            return "Yikes. We need to talk."
