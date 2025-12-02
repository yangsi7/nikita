"""Telegram-specific message handler.

Bridges Telegram messages to the text agent, handling:
- Authentication checks
- Rate limiting (20 msg/min, 500 msg/day)
- Message routing to text agent
- Response queuing for delivery
- Typing indicators
"""

from typing import Optional

from nikita.agents.text.handler import MessageHandler as TextAgentMessageHandler
from nikita.db.repositories.user_repository import UserRepository
from nikita.platforms.telegram.bot import TelegramBot
from nikita.platforms.telegram.delivery import ResponseDelivery
from nikita.platforms.telegram.models import TelegramMessage
from nikita.platforms.telegram.rate_limiter import RateLimiter


class MessageHandler:
    """Handle text messages from Telegram users.

    Routes authenticated user messages to the text agent and queues
    responses for delivery.
    """

    def __init__(
        self,
        user_repository: UserRepository,
        text_agent_handler: TextAgentMessageHandler,
        response_delivery: ResponseDelivery,
        bot: TelegramBot,
        rate_limiter: Optional[RateLimiter] = None,
    ):
        """Initialize MessageHandler.

        Args:
            user_repository: Repository for user lookups.
            text_agent_handler: Text agent message handler.
            response_delivery: Response delivery service.
            bot: Telegram bot client for sending messages.
            rate_limiter: Optional rate limiter (if None, rate limiting disabled).
        """
        self.user_repository = user_repository
        self.text_agent_handler = text_agent_handler
        self.response_delivery = response_delivery
        self.bot = bot
        self.rate_limiter = rate_limiter

    async def handle(self, message: TelegramMessage) -> None:
        """Process incoming text message from Telegram.

        AC-T015.1: Processes text messages
        AC-T015.2: Checks authentication
        AC-T015.3: Checks rate limits (20 msg/min, 500 msg/day)
        AC-T015.4: Routes to text agent with user context
        AC-T015.5: Queues response for delivery
        AC-FR002-001: Message routed to text agent
        AC-FR006-001: Rate limit enforced gracefully
        AC-FR006-002: Warning when approaching daily limit

        Args:
            message: Telegram message object.
        """
        # Extract message details
        telegram_id = message.from_.id
        text = message.text or ""
        chat_id = message.chat.id

        # AC-T015.2: Check authentication
        user = await self.user_repository.get_by_telegram_id(telegram_id)
        if user is None:
            # Prompt registration
            await self.bot.send_message(
                chat_id=chat_id,
                text="You need to register first. Send /start to begin.",
            )
            return

        # AC-T015.3: Check rate limits (if rate limiter configured)
        # AC-FR006-001: Rate limit enforced gracefully
        if self.rate_limiter:
            limit_result = await self.rate_limiter.check(user.id)
            if not limit_result.allowed:
                # AC-T025.1: Send in-character rate limit response
                await self._send_rate_limit_response(chat_id, limit_result)
                return

        # Send typing indicator for better UX
        await self.bot.send_chat_action(chat_id, "typing")

        # AC-T035.1: Try/catch around agent invocation with fallback
        # AC-FR008-001: If agent unavailable, notify user
        try:
            # AC-T015.4: Route to text agent with user context
            # AC-FR002-001: Message routed to text agent
            decision = await self.text_agent_handler.handle(user.id, text)
        except Exception:
            # AC-FR008-001: Notify user in-character
            # AC-T035.3: In-character delay notification
            await self._send_error_response(chat_id)
            return

        # AC-T015.5: Queue response for delivery (only if should respond)
        if decision.should_respond:
            # AC-FR006-002: Add warning if approaching daily limit
            response_text = decision.response
            if self.rate_limiter:
                limit_result = await self.rate_limiter.check(user.id)
                if limit_result.warning_threshold_reached:
                    # AC-T025.2: Subtle warning when approaching daily limit
                    response_text += "\n\n(btw I might need some alone time soon... been chatting a lot today 💭)"

            # AC-T035.1: Wrap delivery in try/catch for graceful handling
            # AC-FR008-002: Handle delivery failures gracefully
            try:
                await self.response_delivery.queue(
                    user_id=user.id,
                    chat_id=chat_id,
                    response=response_text,
                    delay_seconds=decision.delay_seconds,
                )
            except Exception:
                # AC-FR008-002: Delivery failure - notify user
                await self._send_error_response(chat_id)
                return
        # If skipped (should_respond=False), do nothing - Nikita is ghosting

    async def _send_rate_limit_response(self, chat_id: int, result) -> None:
        """Send in-character rate limit message.

        AC-T025.1: Graceful in-character rate limit message
        AC-T025.3: No harsh technical error messages

        Args:
            chat_id: Telegram chat ID.
            result: RateLimitResult with reason and retry_after_seconds.
        """
        if result.reason == "minute_limit_exceeded":
            # Minute limit: playful "slow down"
            message = "Whoa slow down babe, give me a sec to breathe 😅"
        elif result.reason == "day_limit_exceeded":
            # Daily limit: needs space
            message = "I need some space tonight. Talk tomorrow? 💤"
        else:
            # Fallback (shouldn't happen)
            message = "Hey, can we chat later? Need a break 💕"

        await self.bot.send_message(chat_id=chat_id, text=message)

    async def _send_error_response(self, chat_id: int) -> None:
        """Send in-character error message.

        AC-FR008-001: Notify user gracefully when agent unavailable
        AC-T035.3: In-character notification (no technical terms)

        Args:
            chat_id: Telegram chat ID.
        """
        # In-character responses that don't mention technical issues
        message = "Sorry babe, having a moment... can you give me a minute? 💭"
        await self.bot.send_message(chat_id=chat_id, text=message)
