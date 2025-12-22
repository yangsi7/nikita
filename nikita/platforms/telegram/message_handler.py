"""Telegram-specific message handler.

Bridges Telegram messages to the text agent, handling:
- Authentication checks
- Profile gate check (redirects to onboarding if incomplete)
- Rate limiting (20 msg/min, 500 msg/day)
- Message routing to text agent
- Response queuing for delivery
- Typing indicators
- Conversation tracking for post-processing pipeline
- Scoring after each interaction (B-2 integration)
- Boss encounter triggering when threshold reached
"""

import logging
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from uuid import UUID

logger = logging.getLogger(__name__)

from nikita.agents.text.handler import MessageHandler as TextAgentMessageHandler
from nikita.config.enums import EngagementState
from nikita.db.models.conversation import Conversation
from nikita.db.repositories.conversation_repository import ConversationRepository
from nikita.db.repositories.profile_repository import BackstoryRepository, ProfileRepository
from nikita.db.repositories.user_repository import UserRepository
from nikita.engine.scoring.models import ConversationContext
from nikita.engine.scoring.service import ScoringService
from nikita.platforms.telegram.bot import TelegramBot
from nikita.platforms.telegram.delivery import ResponseDelivery
from nikita.platforms.telegram.models import TelegramMessage
from nikita.platforms.telegram.rate_limiter import RateLimiter

if TYPE_CHECKING:
    from nikita.platforms.telegram.onboarding.handler import OnboardingHandler


class MessageHandler:
    """Handle text messages from Telegram users.

    Routes authenticated user messages to the text agent and queues
    responses for delivery.
    """

    def __init__(
        self,
        user_repository: UserRepository,
        conversation_repository: ConversationRepository,
        text_agent_handler: TextAgentMessageHandler,
        response_delivery: ResponseDelivery,
        bot: TelegramBot,
        rate_limiter: Optional[RateLimiter] = None,
        scoring_service: Optional[ScoringService] = None,
        profile_repository: Optional[ProfileRepository] = None,
        backstory_repository: Optional[BackstoryRepository] = None,
        onboarding_handler: Optional["OnboardingHandler"] = None,
    ):
        """Initialize MessageHandler.

        Args:
            user_repository: Repository for user lookups.
            conversation_repository: Repository for conversation tracking.
            text_agent_handler: Text agent message handler.
            response_delivery: Response delivery service.
            bot: Telegram bot client for sending messages.
            rate_limiter: Optional rate limiter (if None, rate limiting disabled).
            scoring_service: Optional scoring service (if None, default created).
            profile_repository: Optional profile repository for profile gate check.
            backstory_repository: Optional backstory repository for profile gate check.
            onboarding_handler: Optional onboarding handler for redirect.
        """
        self.user_repository = user_repository
        self.conversation_repo = conversation_repository
        self.text_agent_handler = text_agent_handler
        self.response_delivery = response_delivery
        self.bot = bot
        self.rate_limiter = rate_limiter
        self.scoring_service = scoring_service or ScoringService()
        self.profile_repo = profile_repository
        self.backstory_repo = backstory_repository
        self.onboarding_handler = onboarding_handler

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

        logger.info(
            f"[LLM-DEBUG] MessageHandler.handle called: "
            f"telegram_id={telegram_id}, text_len={len(text)}"
        )

        # AC-T015.2: Check authentication
        user = await self.user_repository.get_by_telegram_id(telegram_id)
        logger.info(
            f"[LLM-DEBUG] User lookup: found={user is not None}, "
            f"user_id={user.id if user else 'None'}"
        )
        if user is None:
            # Prompt registration
            await self.bot.send_message(
                chat_id=chat_id,
                text="You need to register first. Send /start to begin.",
            )
            return

        # PROFILE GATE: Check if user completed onboarding (has profile + backstory)
        # This ensures personalization is complete before allowing conversation
        if await self._needs_onboarding(user.id, telegram_id, chat_id):
            logger.info(
                f"[PROFILE-GATE] User {user.id} missing profile/backstory - "
                "redirecting to onboarding"
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

        # CONVERSATION TRACKING: Get or create active conversation for post-processing
        conversation = await self._get_or_create_conversation(user.id, user.chapter)
        logger.info(
            f"[LLM-DEBUG] Conversation tracking: id={conversation.id}, "
            f"status={conversation.status}"
        )

        # Append user message to conversation
        await self.conversation_repo.append_message(
            conversation_id=conversation.id,
            role="user",
            content=text,
        )

        # Send typing indicator for better UX
        await self.bot.send_chat_action(chat_id, "typing")

        # AC-T035.1: Try/catch around agent invocation with fallback
        # AC-FR008-001: If agent unavailable, notify user
        try:
            # AC-T015.4: Route to text agent with user context
            # AC-FR002-001: Message routed to text agent
            logger.info(
                f"[LLM-DEBUG] Calling text_agent_handler.handle for user_id={user.id}"
            )
            decision = await self.text_agent_handler.handle(user.id, text)
            logger.info(
                f"[LLM-DEBUG] Agent returned: should_respond={decision.should_respond}, "
                f"response_len={len(decision.response) if decision.response else 0}"
            )
        except Exception as e:
            # AC-FR008-001: Notify user in-character
            # AC-T035.3: In-character delay notification
            logger.error(
                f"[LLM-DEBUG] Agent exception: {type(e).__name__}: {e}",
                exc_info=True,
            )
            await self._send_error_response(chat_id)
            return

        # AC-T015.5: Queue response for delivery (only if should respond)
        if decision.should_respond:
            # Append agent response to conversation for post-processing
            await self.conversation_repo.append_message(
                conversation_id=conversation.id,
                role="nikita",
                content=decision.response,
            )

            # B-2: Score the interaction and check for boss threshold
            await self._score_and_check_boss(
                user=user,
                user_message=text,
                nikita_response=decision.response,
                chat_id=chat_id,
            )

            # AC-FR006-002: Add warning if approaching daily limit
            response_text = decision.response
            if self.rate_limiter:
                limit_result = await self.rate_limiter.check(user.id)
                if limit_result.warning_threshold_reached:
                    # AC-T025.2: Subtle warning when approaching daily limit
                    response_text += "\n\n(btw I might need some alone time soon... been chatting a lot today 💭)"

            logger.info(
                f"[LLM-DEBUG] Queuing response for delivery: "
                f"delay_seconds={decision.delay_seconds}, response_len={len(response_text)}"
            )

            # AC-T035.1: Wrap delivery in try/catch for graceful handling
            # AC-FR008-002: Handle delivery failures gracefully
            try:
                await self.response_delivery.queue(
                    user_id=user.id,
                    chat_id=chat_id,
                    response=response_text,
                    delay_seconds=decision.delay_seconds,
                )
                logger.info(f"[LLM-DEBUG] Response delivered successfully")
            except Exception as e:
                # AC-FR008-002: Delivery failure - notify user
                logger.error(f"[LLM-DEBUG] Delivery failed: {e}")
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

    async def _get_or_create_conversation(
        self,
        user_id: UUID,
        chapter: int,
    ) -> Conversation:
        """Get active conversation or create a new one.

        Ensures conversation tracking for post-processing pipeline.
        The post-processor will detect stale conversations (15min timeout)
        and process them for memory extraction, thread creation, etc.

        Args:
            user_id: User's UUID.
            chapter: Current chapter for context.

        Returns:
            Active or newly created Conversation.
        """
        conversation = await self.conversation_repo.get_active_conversation(user_id)
        if conversation is None:
            conversation = await self.conversation_repo.create_conversation(
                user_id=user_id,
                platform="telegram",
                chapter_at_time=chapter,
            )
            logger.info(
                f"[LLM-DEBUG] Created new conversation: id={conversation.id} "
                f"for user_id={user_id}"
            )
        return conversation

    async def _score_and_check_boss(
        self,
        user,
        user_message: str,
        nikita_response: str,
        chat_id: int,
    ) -> None:
        """Score interaction and check for boss threshold (B-2 integration).

        This integrates the scoring engine with the message flow:
        1. Analyzes the interaction with LLM
        2. Calculates score deltas
        3. Checks for boss_threshold_reached event
        4. If triggered, sets user to boss_fight mode and notifies

        Args:
            user: User model with metrics and engagement_state.
            user_message: The user's message text.
            nikita_response: Nikita's response text.
            chat_id: Telegram chat ID for boss notification.
        """
        try:
            # Build conversation context for scoring
            # Get current metrics from user
            current_metrics = {
                "intimacy": user.metrics.intimacy if user.metrics else Decimal("50"),
                "passion": user.metrics.passion if user.metrics else Decimal("50"),
                "trust": user.metrics.trust if user.metrics else Decimal("50"),
                "secureness": user.metrics.secureness if user.metrics else Decimal("50"),
            }

            # Get engagement state (default to CALIBRATING if not set)
            engagement_state = EngagementState.CALIBRATING
            if user.engagement_state:
                try:
                    engagement_state = EngagementState(user.engagement_state.state)
                except (ValueError, AttributeError):
                    pass

            # Build context
            context = ConversationContext(
                chapter=user.chapter,
                relationship_score=user.relationship_score,
                recent_messages=[("user", user_message), ("nikita", nikita_response)],
                engagement_state=engagement_state.value,
            )

            # Score the interaction
            logger.info(
                f"[SCORING] Scoring interaction for user {user.id}: "
                f"chapter={user.chapter}, score={user.relationship_score}"
            )
            result = await self.scoring_service.score_interaction(
                user_id=user.id,
                user_message=user_message,
                nikita_response=nikita_response,
                context=context,
                current_metrics=current_metrics,
                engagement_state=engagement_state,
            )

            logger.info(
                f"[SCORING] Result: score {result.score_before} -> {result.score_after} "
                f"(delta: {result.delta})"
            )

            # Update user's score in database
            if result.delta != Decimal("0"):
                await self.user_repository.update_score(
                    user_id=user.id,
                    delta=result.delta,
                    event_type="conversation",
                    event_details={
                        "deltas": {
                            "intimacy": str(result.deltas_applied.intimacy),
                            "passion": str(result.deltas_applied.passion),
                            "trust": str(result.deltas_applied.trust),
                            "secureness": str(result.deltas_applied.secureness),
                        },
                        "multiplier": str(result.multiplier_applied),
                    },
                )
                logger.info(f"[SCORING] Updated user score by {result.delta}")

            # Check for boss threshold event
            for event in result.events:
                if event.event_type == "boss_threshold_reached":
                    logger.info(
                        f"[BOSS] Boss threshold reached for user {user.id} "
                        f"at chapter {user.chapter}!"
                    )
                    # Set user to boss_fight status
                    await self.user_repository.set_boss_fight_status(user.id)

                    # Send boss encounter opening message
                    await self._send_boss_opening(chat_id, user.chapter)
                    break

        except Exception as e:
            # Don't fail the message flow if scoring fails
            # Just log the error and continue
            logger.error(
                f"[SCORING] Failed to score interaction for user {user.id}: {e}",
                exc_info=True,
            )

    async def _send_boss_opening(self, chat_id: int, chapter: int) -> None:
        """Send boss encounter opening message.

        Args:
            chat_id: Telegram chat ID.
            chapter: Current chapter for boss context.
        """
        from nikita.engine.chapters.prompts import get_boss_prompt

        try:
            boss_prompt = get_boss_prompt(chapter)
            opening = boss_prompt.get("in_character_opening", "")

            if opening:
                # Small delay before boss opening to create dramatic effect
                import asyncio
                await asyncio.sleep(2)
                await self.bot.send_message(chat_id=chat_id, text=opening)
                logger.info(f"[BOSS] Sent boss opening for chapter {chapter}")
        except Exception as e:
            logger.error(f"[BOSS] Failed to send boss opening: {e}")

    async def _needs_onboarding(
        self,
        user_id: UUID,
        telegram_id: int,
        chat_id: int,
    ) -> bool:
        """Check if user needs onboarding (missing profile or backstory).

        PROFILE GATE: Ensures personalization is complete before allowing
        conversation. Users without profile/backstory are redirected to
        onboarding to collect personalization data.

        Args:
            user_id: User's UUID.
            telegram_id: Telegram user ID.
            chat_id: Telegram chat ID.

        Returns:
            True if user was redirected to onboarding, False if profile complete.
        """
        # Skip check if repositories not configured
        if self.profile_repo is None or self.backstory_repo is None:
            logger.debug(
                "[PROFILE-GATE] Profile/backstory repos not configured - skipping check"
            )
            return False

        # Check for profile
        profile = await self.profile_repo.get_by_user_id(user_id)
        if profile is None:
            logger.info(f"[PROFILE-GATE] User {user_id} missing profile")
            await self._redirect_to_onboarding(telegram_id, chat_id)
            return True

        # Check for backstory
        backstory = await self.backstory_repo.get_by_user_id(user_id)
        if backstory is None:
            logger.info(f"[PROFILE-GATE] User {user_id} missing backstory")
            await self._redirect_to_onboarding(telegram_id, chat_id)
            return True

        # Profile and backstory exist - personalization complete
        logger.debug(f"[PROFILE-GATE] User {user_id} has complete profile")
        return False

    async def _redirect_to_onboarding(
        self,
        telegram_id: int,
        chat_id: int,
    ) -> None:
        """Redirect user to onboarding flow.

        Sends an encouraging message and resumes onboarding from where
        they left off (or starts fresh if no state exists).

        Args:
            telegram_id: Telegram user ID.
            chat_id: Telegram chat ID.
        """
        # Try to resume onboarding if handler available
        if self.onboarding_handler:
            # Check if there's existing onboarding state to resume
            has_state = await self.onboarding_handler.has_incomplete_onboarding(
                telegram_id
            )
            if has_state:
                # Resume from where they left off
                await self.onboarding_handler.resume(telegram_id, chat_id)
            else:
                # Start fresh onboarding
                await self.onboarding_handler.start(telegram_id, chat_id)
        else:
            # Fallback: just send a message asking them to complete onboarding
            await self.bot.send_message(
                chat_id=chat_id,
                text="Hey! Before we can really talk, I need to get to know you first. 💕\n\n"
                     "Send /start to begin - I promise it'll be worth it!",
            )
