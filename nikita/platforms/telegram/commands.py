"""Telegram bot command handlers.

Handles standard bot commands:
- /start: Route users to the portal (FR-11c, Spec 214). Payload-less
  `/start` branches on user state: E1 unknown → bare URL; E2 onboarded
  + active → welcome-back text; E3/E4 game_over/won → reset + re-onboard
  bridge (1h); E5/E6 pending/in_progress/limbo → resume bridge (24h).
  `/start <code>` (E7) preserves FR-11b atomic-bind behavior unchanged.
- /help: Display available commands
- /status: Show current game state (chapter, score hint)
- /call: Voice call information (future integration)
- /onboard: Re-send portal onboarding link for stuck users (GH #160)
"""

import logging
import re

from nikita.db.repositories.profile_repository import ProfileRepository
from nikita.db.repositories.telegram_link_repository import TelegramLinkRepository
from nikita.db.repositories.user_repository import (
    BindResult,
    TelegramIdAlreadyBoundByOtherUserError,
    UserRepository,
)
from nikita.onboarding.bridge_tokens import generate_portal_bridge_url
from nikita.platforms.telegram.auth import TelegramAuth
from nikita.platforms.telegram.bot import TelegramBot

logger = logging.getLogger(__name__)

# GH #321 REQ-3: portal deep-link payload format.
# TelegramLinkCode stores 6-char uppercase alphanumeric PKs. Regex is the
# pre-DB validation gate: injection/typo guard. Any mismatch short-circuits
# before verify_code is called.
_LINK_CODE_PATTERN = re.compile(r"^[A-Z0-9]{6}$")


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
        "onboard": "_handle_onboard",
    }

    def __init__(
        self,
        user_repository: UserRepository,
        telegram_auth: TelegramAuth,
        bot: TelegramBot,
        profile_repository: ProfileRepository | None = None,
        telegram_link_repository: TelegramLinkRepository | None = None,
    ):
        """Initialize CommandHandler.

        Args:
            user_repository: Repository for user lookups.
            telegram_auth: Auth handler for registration (legacy; FR-11c
                removes the vanilla `/start` email-OTP branch but the
                param stays for callers that still wire it).
            bot: Telegram bot client for sending messages.
            profile_repository: Repository for profile lookups. Required
                by `_handle_start` (FR-11c limbo-state detection). Left
                optional in the signature so legacy test fixtures compile,
                but `_handle_start` raises RuntimeError at call time if it
                is None AND a known user is present (AC-11c.9).
            telegram_link_repository: Repository for deep-link code
                verification (GH #321). When None, `/start <payload>`
                raises loudly rather than silently falling through.
        """
        self.user_repository = user_repository
        self.telegram_auth = telegram_auth
        self.bot = bot
        self.profile_repository = profile_repository
        self.telegram_link_repository = telegram_link_repository

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
        """Handle /start command (FR-11c, Spec 214).

        Payload-less routing by user state:
          - E1 unknown telegram_id → single URL button to bare
            {portal}/onboarding/auth. Zero DB writes. AC-11c.1.
          - E2/E8 onboarded + profile + active → welcome-back text only.
            No button, no state mutation. AC-11c.2.
          - E3/E4 game_over / won → reset_game_state + bridge token
            with reason='re-onboard' (1h TTL). AC-11c.3.
          - E5/E6 pending / in_progress / limbo (user row without
            profile) → bridge token with reason='resume' (24h TTL).
            AC-11c.4, AC-11c.5.

        Payload path `/start <code>` preserves FR-11b atomic-bind
        behavior unchanged (AC-11c.6 / E7).

        Raises:
            RuntimeError: if `profile_repository` is missing and the
                user is known (AC-11c.9). `assert` is stripped under
                `python -O`, so a loud runtime failure is required.
        """
        telegram_id = message["from"]["id"]
        chat_id = message["chat"]["id"]
        first_name = message["from"].get("first_name", "there")
        text = message.get("text", "")

        # GH #321 REQ-3: if the command arrived as `/start <payload>`, route
        # to the payload branch. Payload is the second whitespace-separated
        # token. Command has already been parsed upstream as `/start`; only
        # the arg needs extraction. `.strip()` is required because
        # `split(maxsplit=1)` preserves leading whitespace (e.g. `/start  X`
        # → `["/start", " X"]`).
        parts = text.split(maxsplit=1)
        payload = parts[1].strip() if len(parts) >= 2 else ""

        if payload:
            # A payload was supplied. If DI never wired the link repo, we
            # MUST NOT silently fall through to vanilla /start; that would
            # reproduce the exact orphan-row bug GH #321 fixes. Treat
            # misconfig as a loud runtime failure instead.
            if self.telegram_link_repository is None:
                logger.error(
                    "_handle_start: payload supplied (telegram_id=%s) but "
                    "telegram_link_repository is None. Dependency injection "
                    "is misconfigured; refusing to fall through.",
                    telegram_id,
                )
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "Something's broken on my end. Try again in a minute."
                    ),
                )
                return
            await self._handle_start_with_payload(
                telegram_id=telegram_id,
                chat_id=chat_id,
                first_name=first_name,
                payload=payload,
            )
            return

        # Vanilla `/start` (no payload): FR-11c state-routing.
        user = await self.user_repository.get_by_telegram_id(telegram_id)

        if user is None:
            # E1: unknown user. Bare portal URL, zero DB writes.
            await self._send_bare_portal_auth_link(
                chat_id=chat_id, first_name=first_name
            )
            return

        # AC-11c.9: known-user branches require profile_repository to
        # disambiguate limbo from fully-onboarded. Raise RuntimeError
        # (not assert) so misconfig fails loudly under `python -O`.
        if self.profile_repository is None:
            raise RuntimeError(
                "_handle_start requires profile_repository dependency for "
                "known-user routing (AC-11c.9). DI is misconfigured."
            )

        profile = await self.profile_repository.get(user.id)
        has_profile = profile is not None

        # E3/E4: game ended → reset + re-onboard bridge (1h TTL).
        if user.game_status in ("game_over", "won"):
            logger.info(
                "_handle_start: game ended (status=%s) for user_id=%s; "
                "resetting and sending re-onboard bridge",
                user.game_status,
                user.id,
            )
            await self.user_repository.reset_game_state(user.id)
            await self._send_bridge(
                chat_id=chat_id,
                first_name=first_name,
                user_id=str(user.id),
                reason="re-onboard",
            )
            return

        # E5/E6: pending / in_progress onboarding OR limbo (user row
        # without profile) → resume bridge (24h TTL).
        needs_resume = (
            user.onboarding_status in ("pending", "in_progress")
            or not has_profile
        )
        if needs_resume:
            logger.info(
                "_handle_start: resume path for user_id=%s "
                "(onboarding_status=%s, has_profile=%s)",
                user.id,
                user.onboarding_status,
                has_profile,
            )
            await self._send_bridge(
                chat_id=chat_id,
                first_name=first_name,
                user_id=str(user.id),
                reason="resume",
            )
            return

        # E2/E8: onboarded + active + profile present → welcome back.
        response = (
            f"Hey {first_name}, good to see you again.\n\n"
            f"Ready to pick up where we left off?"
        )
        await self.bot.send_message(chat_id=chat_id, text=response)

    async def _send_bare_portal_auth_link(
        self, *, chat_id: int, first_name: str
    ) -> None:
        """E1: send the bare `/onboarding/auth` URL to an unknown user.

        No bridge token (AC-11c.12 forbids query params on E1). No DB
        row created for this telegram_id.
        """
        url = await generate_portal_bridge_url(user_id=None, reason=None)
        text = (
            f"Hey {first_name}. I don't think we've met.\n\n"
            f"Tap below to open the door."
        )
        keyboard = [[{"text": "Meet her here", "url": url}]]
        await self.bot.send_message_with_keyboard(
            chat_id=chat_id,
            text=text,
            keyboard=keyboard,
        )
        logger.info(
            "_handle_start E1: sent bare portal URL to chat_id=%s", chat_id
        )

    async def _send_bridge(
        self,
        *,
        chat_id: int,
        first_name: str,
        user_id: str,
        reason: str,
    ) -> None:
        """Mint a PortalBridgeToken and send an inline-button reply.

        `reason` MUST be 'resume' or 're-onboard' (validated downstream
        in generate_portal_bridge_url / repo.mint).
        """
        url = await generate_portal_bridge_url(
            user_id=user_id, reason=reason
        )
        if reason == "re-onboard":
            text = (
                f"Hey {first_name}. New chapter. Let's start fresh.\n\n"
                f"Tap below to get back in."
            )
            button = "Back in"
        else:
            text = (
                f"Hey {first_name}. Let's pick this up where you left off.\n\n"
                f"Tap below to continue."
            )
            button = "Pick it up"
        keyboard = [[{"text": button, "url": url}]]
        await self.bot.send_message_with_keyboard(
            chat_id=chat_id,
            text=text,
            keyboard=keyboard,
        )
        logger.info(
            "_handle_start: bridge reason=%s sent to chat_id=%s",
            reason,
            chat_id,
        )

    async def _handle_start_with_payload(
        self,
        *,
        telegram_id: int,
        chat_id: int,
        first_name: str,
        payload: str,
    ) -> None:
        """Handle `/start <payload>` for portal deep-link binding (GH #321 REQ-3).

        Steps:
        1. Validate the payload format (`^[A-Z0-9]{6}$`): injection/typo gate.
        2. Call `TelegramLinkRepository.verify_code` (atomic DELETE..RETURNING).
        3. On success, call `UserRepository.update_telegram_id` (atomic predicate
           UPDATE..RETURNING).
        4. Send Nikita-voiced confirmation or error. ANY reject short-circuits
           here; we never fall through to the email-OTP flow (vanilla /start
           branch-3), because that would orphan the portal row and reproduce
           the exact bug GH #321 fixes.
        """
        # Step 1: regex gate. Before any DB call.
        if not _LINK_CODE_PATTERN.match(payload):
            logger.info(
                "_handle_start: invalid payload format from telegram_id=%s",
                telegram_id,
            )
            await self.bot.send_message(
                chat_id=chat_id,
                text=(
                    "That link doesn't look right. Open the portal and tap "
                    "the button again to get a fresh one."
                ),
            )
            return

        # Step 2: atomic verify + delete. The caller in `_handle_start` has
        # already guarded against None, but raise an explicit RuntimeError
        # here rather than `assert` because assertions are stripped under
        # `python -O` and this invariant needs to hold in every environment.
        if self.telegram_link_repository is None:
            raise RuntimeError(
                "telegram_link_repository required to process /start payload"
            )
        portal_user_id = await self.telegram_link_repository.verify_code(payload)

        if portal_user_id is None:
            logger.info(
                "_handle_start: expired/unknown payload from telegram_id=%s",
                telegram_id,
            )
            await self.bot.send_message(
                chat_id=chat_id,
                text=(
                    "That link expired. Open the portal and tap the button "
                    "again to get a fresh one."
                ),
            )
            return

        # Step 3: atomic bind.
        try:
            result = await self.user_repository.update_telegram_id(
                portal_user_id, telegram_id
            )
        except TelegramIdAlreadyBoundByOtherUserError:
            logger.warning(
                "_handle_start: telegram_id=%s already linked to another "
                "portal account; refused to overwrite",
                telegram_id,
            )
            await self.bot.send_message(
                chat_id=chat_id,
                text=(
                    "This Telegram account is already linked to another "
                    "profile. Contact support if you think that's a mistake."
                ),
            )
            return

        # Step 4: success.
        logger.info(
            "_handle_start: bound portal user_id=%s to telegram_id=%s (result=%s)",
            portal_user_id,
            telegram_id,
            result.value,
        )
        await self.bot.send_message(
            chat_id=chat_id,
            text=(
                f"Hey {first_name}, you're linked. "
                f"Let's get into it. Just message me whenever you're ready."
            ),
        )

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
            "/call - Request a voice call (when available)\n"
            "/onboard - Get the portal setup link again\n\n"
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

    async def _handle_onboard(self, message: dict) -> None:
        """Handle /onboard command - re-send portal onboarding link.

        GH #160: Users who completed OTP but never clicked the portal magic
        link stay stuck at onboarding_status=pending. This command lets them
        request a fresh link without restarting the whole flow.

        Args:
            message: Telegram message dict.
        """
        telegram_id = message["from"]["id"]
        chat_id = message["chat"]["id"]

        # Look up user by telegram_id
        user = await self.user_repository.get_by_telegram_id(telegram_id)

        if user is None:
            await self.bot.send_message(
                chat_id=chat_id,
                text="You need to register first! Type /start",
            )
            return

        # Already completed onboarding
        if user.onboarding_status == "completed":
            await self.bot.send_message(
                chat_id=chat_id,
                text="You're already set up! Just start chatting.",
            )
            return

        # Pending or in_progress — generate a fresh portal magic link
        if user.onboarding_status in ("pending", "in_progress"):
            from nikita.config.settings import get_settings
            from nikita.platforms.telegram.utils import generate_portal_bridge_url

            settings = get_settings()
            portal_url = settings.portal_url or "https://portal-phi-orcin.vercel.app"

            # Zero-click portal auth via bridge token (GH #187 / GH #233)
            magic_link = await generate_portal_bridge_url(
                user_id=str(user.id),
                redirect_path="/onboarding",
            )

            # Fallback to regular login URL if magic link generation fails
            if magic_link:
                button_url = magic_link
            else:
                button_url = f"{portal_url}/login?next=/onboarding"
                logger.warning(
                    f"Magic link failed for /onboard, telegram_id={telegram_id}, "
                    f"falling back to login URL"
                )

            keyboard = [
                [
                    {"text": "Open Onboarding →", "url": button_url},
                ],
            ]

            text = (
                "No worries, here's your portal link again.\n\n"
                "Tap below to finish setting up your profile."
            )

            await self.bot.send_message_with_keyboard(
                chat_id=chat_id,
                text=text,
                keyboard=keyboard,
            )

            logger.info(
                f"/onboard: Sent portal link to telegram_id={telegram_id}, "
                f"user_id={user.id}, magic_link={'yes' if magic_link else 'fallback'}"
            )
            return

        # Any other status (e.g. "skipped") — treat as completed
        await self.bot.send_message(
            chat_id=chat_id,
            text="You're already set up! Just start chatting.",
        )

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
