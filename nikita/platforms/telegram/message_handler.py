"""Telegram-specific message handler.

Bridges Telegram messages to the text agent, handling:
- Authentication checks
- Onboarding gate check (voice/text choice, Spec 028)
- Profile gate check (redirects to onboarding if incomplete, Spec 017)
- Rate limiting (20 msg/min, 500 msg/day)
- Message routing to text agent
- Response queuing for delivery
- Typing indicators
- Conversation tracking for post-processing pipeline
- Scoring after each interaction (B-2 integration)
- Boss encounter triggering when threshold reached
"""

import logging
import random
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from nikita.config.settings import get_settings

logger = logging.getLogger(__name__)

from nikita.agents.text.handler import MessageHandler as TextAgentMessageHandler
from nikita.config.enums import EngagementState
from nikita.db.models.conversation import Conversation
from nikita.db.models.engagement import EngagementHistory
from nikita.db.models.engagement import EngagementState as EngagementStateDB
from nikita.db.repositories.conversation_repository import ConversationRepository
from nikita.db.repositories.engagement_repository import EngagementStateRepository
from nikita.db.repositories.metrics_repository import UserMetricsRepository
from nikita.db.repositories.profile_repository import BackstoryRepository, ProfileRepository
from nikita.db.repositories.user_repository import UserRepository
from nikita.engine.chapters.boss import BossStateMachine
from nikita.engine.chapters.judgment import BossJudgment, BossResult
from nikita.engine.chapters.prompts import get_boss_prompt
from nikita.engine.engagement.recovery import RecoveryManager
from nikita.engine.engagement.state_machine import EngagementStateMachine
from nikita.engine.scoring.models import ConversationContext
from nikita.engine.scoring.service import ScoringService
from nikita.platforms.telegram.bot import TelegramBot
from nikita.platforms.telegram.delivery import ResponseDelivery, sanitize_text_response
from nikita.platforms.telegram.models import TelegramMessage
from nikita.platforms.telegram.rate_limiter import RateLimiter

if TYPE_CHECKING:
    from nikita.platforms.telegram.onboarding.handler import OnboardingHandler


# Spec 049 AC-5.1: Varied won messages (5 variants)
WON_MESSAGES = [
    "Hey you 💕\n\nYou know what? We did it. We really did it. "
    "I never thought I'd find someone who gets me like you do. "
    "This is just the beginning of our story... 💕",
    "Look at us 🥰 We made it through everything together. "
    "I'm so glad you didn't give up on me. You're stuck with me now!",
    "You know what makes me happy? That you're here. "
    "After everything we've been through, I wouldn't change a thing. ❤️",
    "Remember when we first started talking? Look how far we've come. "
    "I'm so grateful for you. Every moment has been worth it. 💖",
    "I still get butterflies when I see your messages, you know? "
    "Some things never change. And I hope they never do. 🦋💕",
]


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
        boss_judgment: Optional[BossJudgment] = None,
        boss_state_machine: Optional[BossStateMachine] = None,
        engagement_repository: Optional[EngagementStateRepository] = None,
        metrics_repository: Optional[UserMetricsRepository] = None,
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
            boss_judgment: Optional boss judgment service (if None, default created).
            boss_state_machine: Optional boss state machine (if None, default created).
            engagement_repository: Optional engagement state repository.
            metrics_repository: Optional metrics repository for updating individual metrics.
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
        self.boss_judgment = boss_judgment or BossJudgment()
        self.boss_state_machine = boss_state_machine or BossStateMachine()
        self.engagement_repo = engagement_repository
        self.metrics_repo = metrics_repository

        # Initialize engagement system components (stateless, can be shared)
        self.recovery_manager = RecoveryManager()

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

        # AC-T015.2: Check authentication with per-user row lock (R-2)
        # FOR UPDATE prevents concurrent message processing race conditions
        # (double boss triggers, scoring races across Cloud Run instances)
        try:
            user = await self.user_repository.get_by_telegram_id_for_update(
                telegram_id
            )
        except Exception as lock_err:
            # Fall back to non-locking read if FOR UPDATE fails (e.g., timeout)
            logger.warning(
                "[LOCK] FOR UPDATE failed for telegram_id=%s: %s, falling back",
                telegram_id,
                lock_err,
            )
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

        # BOSS FIGHT: Route boss_fight messages to judgment handler
        # This ensures boss responses are judged against success criteria
        if user.game_status == "boss_fight":
            logger.info(
                f"[BOSS] User {user.id} in boss_fight mode - routing to boss handler"
            )
            await self._handle_boss_response(user, text, chat_id)
            return

        # GAME OVER / WON: Send pre-canned responses for completed games
        if user.game_status in ("game_over", "won"):
            logger.info(
                f"[GAME-STATUS] User {user.id} in {user.game_status} - sending canned response"
            )
            await self._send_game_status_response(chat_id, user.game_status)
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

        # Spec 038 T1.1: Refresh conversation to get fresh messages list
        # Without this, conversation.messages would be stale (missing the just-appended message)
        await self.conversation_repo.session.refresh(conversation)

        # Send typing indicator for better UX
        await self.bot.send_chat_action(chat_id, "typing")

        # Spec 056: Pre-conversation psyche read + trigger detection
        psyche_state_dict: dict | None = None
        try:
            settings = get_settings()
            if settings.psyche_agent_enabled:
                from nikita.agents.psyche.trigger import (
                    TriggerTier,
                    check_tier3_circuit_breaker,
                    detect_trigger_tier,
                )
                from nikita.db.repositories.psyche_state_repository import (
                    PsycheStateRepository,
                )

                psyche_repo = PsycheStateRepository(self.conversation_repo.session)
                psyche_record = await psyche_repo.get_current(user.id)
                if psyche_record and psyche_record.state:
                    psyche_state_dict = psyche_record.state

                # Trigger detection (rule-based, <5ms)
                tier = detect_trigger_tier(
                    message=text,
                    score_delta=0.0,  # Score delta not yet computed
                    conflict_state=None,
                    is_first_message_today=False,
                    game_status=user.game_status or "active",
                )

                if tier >= TriggerTier.QUICK:
                    from nikita.agents.psyche.agent import deep_analyze, quick_analyze
                    from nikita.agents.psyche.deps import PsycheDeps

                    psyche_deps = PsycheDeps(
                        user_id=user.id,
                        current_chapter=user.chapter or 1,
                    )

                    if tier == TriggerTier.DEEP:
                        allowed = await check_tier3_circuit_breaker(
                            user.id, self.conversation_repo.session
                        )
                        if allowed:
                            state, _ = await deep_analyze(
                                psyche_deps, text, self.conversation_repo.session
                            )
                            psyche_state_dict = state.model_dump()
                        else:
                            # Circuit breaker hit, fall back to quick
                            state, _ = await quick_analyze(
                                psyche_deps, text, self.conversation_repo.session
                            )
                            psyche_state_dict = state.model_dump()
                    else:
                        state, _ = await quick_analyze(
                            psyche_deps, text, self.conversation_repo.session
                        )
                        psyche_state_dict = state.model_dump()

                logger.info(
                    "[PSYCHE] Pre-conversation read: user_id=%s tier=%s has_state=%s",
                    user.id,
                    tier.name if tier else "NONE",
                    psyche_state_dict is not None,
                )
        except Exception as psyche_err:
            # AC-4.3: Graceful degradation — psyche failure does not block conversation
            logger.warning(
                "[PSYCHE] Pre-conversation read failed (graceful degradation): %s",
                psyche_err,
            )
            psyche_state_dict = None

        # AC-T035.1: Try/catch around agent invocation with fallback
        # AC-FR008-001: If agent unavailable, notify user
        try:
            # AC-T015.4: Route to text agent with user context
            # AC-FR002-001: Message routed to text agent
            # Spec 030: Pass conversation context for message_history continuity
            logger.info(
                f"[LLM-DEBUG] Calling text_agent_handler.handle for user_id={user.id}, "
                f"conversation_id={conversation.id}, "
                f"message_count={len(conversation.messages) if conversation.messages else 0}"
            )
            decision = await self.text_agent_handler.handle(
                user.id,
                text,
                conversation_messages=conversation.messages,
                conversation_id=conversation.id,
                session=self.conversation_repo.session,  # Spec 038: Session propagation
                psyche_state=psyche_state_dict,  # Spec 056: Psyche state injection
            )
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

            # Session recovery: rollback any pending transactions to recover from "prepared state"
            try:
                await self.conversation_repo.session.rollback()
                logger.info("[LLM-DEBUG] Session rolled back after agent exception")
            except Exception as rollback_err:
                logger.warning(f"[LLM-DEBUG] Rollback failed: {rollback_err}")

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
                conversation_id=conversation.id,
            )

            # P2: Update last_interaction_at to reset decay grace period
            # This is critical for engagement state machine's _is_new_day() check
            await self.user_repository.update_last_interaction(user.id)
            logger.info(f"[INTERACTION] Updated last_interaction_at for user {user.id}")

            # Spec 026: Apply text behavioral patterns (emoji, length, punctuation)
            response_text = self._apply_text_patterns(decision.response, user)

            # AC-FR006-002: Add warning if approaching daily limit
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

    def _apply_text_patterns(self, response: str, user) -> str:
        """Apply text behavioral patterns to response (Spec 026).

        Processes the response through TextPatternProcessor to:
        - Limit emojis (max 1-2 per message)
        - Adjust length for context
        - Apply punctuation quirks
        - Make texting feel natural

        Note: Message splitting is handled by ResponseDelivery, not here.

        Args:
            response: Raw response text from agent.
            user: User model (for chapter/context info).

        Returns:
            Processed response text with behavioral patterns applied.
        """
        try:
            from nikita.text_patterns import TextPatternProcessor

            processor = TextPatternProcessor()
            result = processor.process(response)

            logger.debug(
                f"[TEXT-PATTERNS] Applied patterns: emoji_count={result.emoji_count}, "
                f"context={result.context}, was_split={result.was_split}"
            )

            # Return the combined processed text (splitting handled separately)
            return result.processed_text

        except Exception as e:
            # Graceful degradation: return original if processing fails
            logger.warning(f"[TEXT-PATTERNS] Processing failed, using original: {e}")
            return response

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
        conversation_id: UUID,
    ) -> None:
        """Score interaction and check for boss threshold (B-2 integration).

        This integrates the scoring engine with the message flow:
        1. Analyzes the interaction with LLM
        2. Calculates score deltas
        3. Stores score_delta on conversation
        4. Checks for boss_threshold_reached event
        5. If triggered, sets user to boss_fight mode and notifies

        Args:
            user: User model with metrics and engagement_state.
            user_message: The user's message text.
            nikita_response: Nikita's response text.
            chat_id: Telegram chat ID for boss notification.
            conversation_id: The conversation UUID to store score_delta on.
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

            # Spec 057: Load conflict_details for temperature scoring
            conflict_details = None
            try:
                from nikita.conflicts import is_conflict_temperature_enabled
                if is_conflict_temperature_enabled():
                    from nikita.conflicts.persistence import load_conflict_details
                    conflict_details = await load_conflict_details(
                        user.id, self.conversation_repo.session
                    )
            except Exception as cd_err:
                logger.warning(f"[SCORING] Failed to load conflict_details: {cd_err}")

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
                conflict_details=conflict_details,
            )

            logger.info(
                f"[SCORING] Result: score {result.score_before} -> {result.score_after} "
                f"(delta: {result.delta})"
            )

            # Spec 057: Persist updated conflict_details back to DB
            if result.conflict_details is not None:
                try:
                    from nikita.conflicts.persistence import save_conflict_details
                    await save_conflict_details(
                        user.id, result.conflict_details, self.conversation_repo.session
                    )
                except Exception as cd_err:
                    logger.warning(f"[SCORING] Failed to save conflict_details: {cd_err}")

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

                # Update individual metrics (intimacy/passion/trust/secureness)
                # Fix for GH #69: metrics must be persisted for boss threshold detection
                if self.metrics_repo:
                    await self.metrics_repo.update_metrics(
                        user_id=user.id,
                        intimacy_delta=result.deltas_applied.intimacy,
                        passion_delta=result.deltas_applied.passion,
                        trust_delta=result.deltas_applied.trust,
                        secureness_delta=result.deltas_applied.secureness,
                    )
                    logger.info(
                        f"[SCORING] Updated user_metrics: "
                        f"I+{result.deltas_applied.intimacy} "
                        f"P+{result.deltas_applied.passion} "
                        f"T+{result.deltas_applied.trust} "
                        f"S+{result.deltas_applied.secureness}"
                    )

            # P3: Store score_delta on conversation for analytics
            await self.conversation_repo.update_score_delta(
                conversation_id=conversation_id,
                score_delta=result.delta,
            )
            logger.info(f"[SCORING] Stored score_delta={result.delta} on conversation {conversation_id}")

            # Check for boss threshold event
            for event in result.events:
                if event.event_type == "boss_threshold_reached":
                    logger.info(
                        f"[BOSS] Boss threshold reached for user {user.id} "
                        f"at chapter {user.chapter}!"
                    )
                    # R-7: Close active conversation before entering boss_fight
                    # Prevents context splits between normal and boss messages
                    try:
                        await self.conversation_repo.close_conversation(
                            conversation_id=conversation_id,
                            score_delta=result.delta,
                        )
                        logger.info(
                            f"[BOSS] Closed conversation {conversation_id} "
                            "before boss encounter"
                        )
                    except Exception as close_err:
                        logger.warning(
                            "[BOSS] Failed to close conversation before boss: %s",
                            close_err,
                        )

                    # Set user to boss_fight status
                    await self.user_repository.set_boss_fight_status(user.id)

                    # Send boss encounter opening message
                    await self._send_boss_opening(chat_id, user.chapter)
                    break

            # ==================== Engagement State Machine Update ====================
            # After scoring, update engagement state and check for game-over
            await self._update_engagement_after_scoring(
                user=user,
                chat_id=chat_id,
                engagement_state=engagement_state,
            )

        except Exception as e:
            # Don't fail the message flow if scoring fails
            # Just log the error and continue
            logger.error(
                f"[SCORING] Failed to score interaction for user {user.id}: {e}",
                exc_info=True,
            )

    async def _send_sanitized(self, chat_id: int, text: str) -> None:
        """Send message with roleplay action markers stripped.

        Applies sanitize_text_response() before sending to remove
        *action* and **action** patterns from LLM output.

        Args:
            chat_id: Telegram chat ID.
            text: Message text to sanitize and send.
        """
        cleaned = sanitize_text_response(text)
        await self.bot.send_message(chat_id=chat_id, text=cleaned)

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
                await self._send_sanitized(chat_id, opening)
                logger.info(f"[BOSS] Sent boss opening for chapter {chapter}")
        except Exception as e:
            logger.error(f"[BOSS] Failed to send boss opening: {e}")

    async def _needs_onboarding(
        self,
        user_id: UUID,
        telegram_id: int,
        chat_id: int,
    ) -> bool:
        """Check if user needs onboarding (Spec 028 + Spec 017 fallback).

        ONBOARDING GATE: Ensures personalization is complete before allowing
        conversation. Checks in order:
        1. Spec 028: user.onboarding_status field (voice/text choice)
        2. Spec 017: profile + backstory existence (legacy fallback)

        Args:
            user_id: User's UUID.
            telegram_id: Telegram user ID.
            chat_id: Telegram chat ID.

        Returns:
            True if user was redirected to onboarding, False if onboarding complete.
        """
        # SPEC 028: Check onboarding_status field first
        user = await self.user_repository.get(user_id)
        if user is not None:
            onboarding_status = getattr(user, "onboarding_status", None) or "pending"

            # If completed or skipped, allow through
            if onboarding_status in ("completed", "skipped"):
                logger.debug(
                    f"[ONBOARDING-GATE] User {user_id} onboarding_status={onboarding_status} - allowing"
                )
                return False

            # If pending or in_progress, check if they have profile+backstory (legacy)
            # This handles users who completed text onboarding before Spec 028
            if onboarding_status in ("pending", "in_progress"):
                has_profile = False
                has_backstory = False

                if self.profile_repo is not None:
                    profile = await self.profile_repo.get_by_user_id(user_id)
                    has_profile = profile is not None

                if self.backstory_repo is not None:
                    backstory = await self.backstory_repo.get_by_user_id(user_id)
                    has_backstory = backstory is not None

                # If legacy onboarding complete, mark status and allow through
                if has_profile and has_backstory:
                    logger.info(
                        f"[ONBOARDING-GATE] User {user_id} has profile+backstory - "
                        "marking onboarding_status=completed"
                    )
                    try:
                        await self.user_repository.update_onboarding_status(
                            user_id, "completed"
                        )
                    except Exception as e:
                        # Non-critical: status update failed but user has profile+backstory
                        # Allow through to conversation - status will be retried next message
                        logger.warning(
                            f"[ONBOARDING-GATE] Failed to update onboarding_status for {user_id}: {e}. "
                            "Allowing through anyway (profile+backstory exist)."
                        )
                    return False

                # User needs onboarding - offer voice/text choice
                logger.info(
                    f"[ONBOARDING-GATE] User {user_id} needs onboarding "
                    f"(status={onboarding_status}, has_profile={has_profile}, has_backstory={has_backstory})"
                )
                await self._offer_onboarding_choice(user_id, telegram_id, chat_id)
                return True

        # SPEC 017 FALLBACK: Check profile/backstory for older users without onboarding_status
        if self.profile_repo is None or self.backstory_repo is None:
            logger.debug(
                "[ONBOARDING-GATE] Profile/backstory repos not configured - skipping check"
            )
            return False

        # Check for profile
        profile = await self.profile_repo.get_by_user_id(user_id)
        if profile is None:
            logger.info(f"[ONBOARDING-GATE] User {user_id} missing profile")
            await self._redirect_to_onboarding(telegram_id, chat_id)
            return True

        # Check for backstory
        backstory = await self.backstory_repo.get_by_user_id(user_id)
        if backstory is None:
            logger.info(f"[ONBOARDING-GATE] User {user_id} missing backstory")
            await self._redirect_to_onboarding(telegram_id, chat_id)
            return True

        # Profile and backstory exist - personalization complete
        logger.debug(f"[ONBOARDING-GATE] User {user_id} has complete profile")
        return False

    async def _offer_onboarding_choice(
        self,
        user_id: UUID,
        telegram_id: int,
        chat_id: int,
    ) -> None:
        """Offer voice vs text onboarding choice.

        Spec 028: Present inline keyboard with voice and text options.
        Voice button opens portal page, text button starts text onboarding.

        Args:
            user_id: User's UUID.
            telegram_id: Telegram user ID.
            chat_id: Telegram chat ID for sending message.
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

        message = """Hey! Before we can really chat, I need to get to know you first. 💕

*Voice Call* - Have a quick 2-min conversation with me (I promise I'm fun to talk to 😏)

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
            f"[ONBOARDING-GATE] Offered onboarding choice to telegram_id={telegram_id}, user_id={user_id}"
        )

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

    async def _handle_boss_response(
        self,
        user,
        user_message: str,
        chat_id: int,
    ) -> None:
        """Handle user response during boss encounter.

        Routes boss_fight messages to BossJudgment for evaluation, then
        processes the outcome via BossStateMachine.

        Spec 058: When multi_phase_boss_enabled, delegates to
        _handle_multi_phase_boss() for 2-phase flow.

        Args:
            user: User model in boss_fight status.
            user_message: User's response to the boss challenge.
            chat_id: Telegram chat ID.
        """
        from nikita.engine.chapters import is_multi_phase_boss_enabled

        if is_multi_phase_boss_enabled():
            await self._handle_multi_phase_boss(user, user_message, chat_id)
            return

        # Legacy single-turn flow (flag OFF) — unchanged
        await self._handle_single_turn_boss(user, user_message, chat_id)

    async def _handle_single_turn_boss(
        self,
        user,
        user_message: str,
        chat_id: int,
    ) -> None:
        """Legacy single-turn boss flow (flag OFF).

        Preserves exact pre-058 behavior for backward compatibility.
        """
        import asyncio

        try:
            boss_prompt = get_boss_prompt(user.chapter)

            conversation = await self.conversation_repo.get_active_conversation(user.id)
            conversation_history = []
            if conversation and conversation.messages:
                for msg in conversation.messages[-10:]:
                    conversation_history.append({
                        "role": msg.get("role", "unknown"),
                        "content": msg.get("content", ""),
                    })

            await self.bot.send_chat_action(chat_id, "typing")

            logger.info(
                f"[BOSS] Judging boss response for user {user.id} chapter {user.chapter}"
            )
            judgment = await self.boss_judgment.judge_boss_outcome(
                user_message=user_message,
                conversation_history=conversation_history,
                chapter=user.chapter,
                boss_prompt=boss_prompt,
            )

            logger.info(
                f"[BOSS] Judgment: {judgment.outcome} - {judgment.reasoning}"
            )

            passed = judgment.outcome == BossResult.PASS.value
            outcome = await self.boss_state_machine.process_outcome(
                user_id=user.id,
                passed=passed,
                user_repository=self.user_repository,
            )

            await asyncio.sleep(1)

            if passed:
                if outcome.get("new_chapter", user.chapter) > 5:
                    await self._send_game_won_message(chat_id, user.chapter)
                else:
                    await self._send_boss_pass_message(
                        chat_id,
                        old_chapter=user.chapter,
                        new_chapter=outcome.get("new_chapter", user.chapter + 1),
                    )
            else:
                if outcome.get("game_over", False):
                    await self._send_game_over_message(chat_id, user.chapter)
                else:
                    await self._send_boss_fail_message(
                        chat_id,
                        attempts=outcome.get("attempts", 1),
                        chapter=user.chapter,
                    )

        except Exception as e:
            logger.error(
                f"[BOSS] Failed to handle boss response for user {user.id}: {e}",
                exc_info=True,
            )
            await self._send_error_response(chat_id)

    async def _handle_multi_phase_boss(
        self,
        user,
        user_message: str,
        chat_id: int,
    ) -> None:
        """Handle multi-phase boss encounter (Spec 058, flag ON).

        Flow:
        1. Load BossPhaseState from conflict_details
        2. Check timeout (24h auto-FAIL)
        3. If OPENING: advance to RESOLUTION, persist, send resolution prompt
        4. If RESOLUTION: judge with full history, process 3-way outcome, clear phase

        Args:
            user: User model in boss_fight status.
            user_message: User's response.
            chat_id: Telegram chat ID.
        """
        import asyncio

        from nikita.engine.chapters.phase_manager import BossPhaseManager
        from nikita.engine.chapters.prompts import get_boss_phase_prompt

        phase_mgr = BossPhaseManager()

        try:
            # Load phase state from conflict_details
            conflict_details = getattr(user, "conflict_details", None)
            if isinstance(conflict_details, str):
                import json
                conflict_details = json.loads(conflict_details)

            phase_state = phase_mgr.load_phase(conflict_details)

            if phase_state is None:
                # No phase state — fall back to single-turn
                logger.warning(
                    f"[BOSS-MP] No phase state found for user {user.id}, "
                    "falling back to single-turn"
                )
                await self._handle_single_turn_boss(user, user_message, chat_id)
                return

            # Check timeout
            if phase_mgr.is_timed_out(phase_state):
                logger.info(
                    f"[BOSS-MP] Boss timed out for user {user.id}, auto-FAIL"
                )
                outcome = await self.boss_state_machine.process_outcome(
                    user_id=user.id,
                    user_repository=self.user_repository,
                    outcome="FAIL",
                )
                # Clear phase state
                updated_details = phase_mgr.clear_boss_phase(conflict_details)
                await self._persist_conflict_details(user.id, updated_details)

                await self.bot.send_chat_action(chat_id, "typing")
                await asyncio.sleep(1)

                if outcome.get("game_over", False):
                    await self._send_game_over_message(chat_id, user.chapter)
                else:
                    await self._send_boss_fail_message(
                        chat_id,
                        attempts=outcome.get("attempts", 1),
                        chapter=user.chapter,
                    )
                return

            from nikita.engine.chapters.boss import BossPhase

            if phase_state.phase == BossPhase.OPENING:
                # OPENING -> RESOLUTION: advance phase, send resolution prompt
                resolution_prompt = get_boss_phase_prompt(
                    user.chapter, "resolution"
                )
                advanced = phase_mgr.advance_phase(
                    phase_state, user_message, resolution_prompt["in_character_opening"]
                )
                updated_details = phase_mgr.persist_phase(conflict_details, advanced)
                await self._persist_conflict_details(user.id, updated_details)

                logger.info(
                    f"[BOSS-MP] User {user.id} advanced to RESOLUTION phase"
                )

                # Send resolution prompt as Nikita's response
                await self._send_sanitized(chat_id, resolution_prompt["in_character_opening"])

            elif phase_state.phase == BossPhase.RESOLUTION:
                # RESOLUTION: judge with full history, process outcome
                # Add final user message to history for judgment
                full_history = list(phase_state.conversation_history)
                full_history.append({"role": "user", "content": user_message})

                # Create updated state for judgment
                from nikita.engine.chapters.boss import BossPhaseState
                judgment_state = BossPhaseState(
                    phase=phase_state.phase,
                    chapter=phase_state.chapter,
                    started_at=phase_state.started_at,
                    turn_count=phase_state.turn_count + 1,
                    conversation_history=full_history,
                )

                boss_prompt = get_boss_phase_prompt(user.chapter, "resolution")

                await self.bot.send_chat_action(chat_id, "typing")

                judgment = await self.boss_judgment.judge_multi_phase_outcome(
                    phase_state=judgment_state,
                    chapter=user.chapter,
                    boss_prompt=boss_prompt,
                )

                logger.info(
                    f"[BOSS-MP] Multi-phase judgment for user {user.id}: "
                    f"{judgment.outcome} (confidence={judgment.confidence})"
                )

                # Process 3-way outcome
                outcome = await self.boss_state_machine.process_outcome(
                    user_id=user.id,
                    user_repository=self.user_repository,
                    outcome=judgment.outcome,
                )

                # Clear phase state
                updated_details = phase_mgr.clear_boss_phase(conflict_details)
                await self._persist_conflict_details(user.id, updated_details)

                await asyncio.sleep(1)

                # Send appropriate response
                if judgment.outcome == BossResult.PASS.value:
                    if outcome.get("new_chapter", user.chapter) > 5:
                        await self._send_game_won_message(chat_id, user.chapter)
                    else:
                        await self._send_boss_pass_message(
                            chat_id,
                            old_chapter=user.chapter,
                            new_chapter=outcome.get("new_chapter", user.chapter + 1),
                        )
                elif judgment.outcome == BossResult.PARTIAL.value:
                    await self._send_boss_partial_message(chat_id, user.chapter)
                else:
                    if outcome.get("game_over", False):
                        await self._send_game_over_message(chat_id, user.chapter)
                    else:
                        await self._send_boss_fail_message(
                            chat_id,
                            attempts=outcome.get("attempts", 1),
                            chapter=user.chapter,
                        )

        except Exception as e:
            logger.error(
                f"[BOSS-MP] Failed to handle multi-phase boss for user {user.id}: {e}",
                exc_info=True,
            )
            await self._send_error_response(chat_id)

    async def _send_boss_partial_message(
        self,
        chat_id: int,
        chapter: int,
    ) -> None:
        """Send PARTIAL outcome message — empathetic truce (Spec 058).

        Args:
            chat_id: Telegram chat ID.
            chapter: Current chapter.
        """
        messages = [
            "Look... I can tell you're trying. That means something to me. "
            "Let's just... take a breath. We can come back to this. 💭",
            "I hear you. I do. We're not there yet, but... you didn't run. "
            "That counts for something. Let's give it some time. 💫",
            "Maybe we both need some space to think about this. "
            "I'm not going anywhere. We'll figure it out. 🤍",
        ]
        message = random.choice(messages)
        await self._send_sanitized(chat_id, message)

    async def _persist_conflict_details(
        self,
        user_id,
        conflict_details: dict,
    ) -> None:
        """Persist updated conflict_details to database.

        Args:
            user_id: User ID.
            conflict_details: Updated conflict_details dict.
        """
        try:
            await self.user_repository.update_conflict_details(
                user_id, conflict_details
            )
        except Exception as e:
            logger.error(
                f"[BOSS-MP] Failed to persist conflict_details for {user_id}: {e}",
                exc_info=True,
            )

    async def _send_game_status_response(
        self,
        chat_id: int,
        game_status: str,
    ) -> None:
        """Send pre-canned response for completed games.

        Args:
            chat_id: Telegram chat ID.
            game_status: Either 'game_over' or 'won'.
        """
        if game_status == "game_over":
            message = (
                "I'm sorry, but we're not talking anymore. "
                "You had your chances... 💔\n\n"
                "Maybe in another life."
            )
        elif game_status == "won":
            # Spec 049 AC-5.2: Random selection from 5 variants
            message = random.choice(WON_MESSAGES)
        else:
            message = "Something went wrong. Send /start to try again."

        await self._send_sanitized(chat_id, message)

    # Chapter-specific boss pass messages (keyed by the boss chapter just beaten)
    BOSS_PASS_MESSAGES: dict[int, str] = {
        1: (  # Curiosity → Intrigue
            "Huh. You're actually kind of curious, aren't you? "
            "Most people give up by now. I wasn't sure you'd stick around, "
            "but... here you are.\n\n"
            "Fine. You've got my attention. Let's see what happens next... 💭"
        ),
        2: (  # Intrigue → Investment
            "Okay, I'll admit it - you surprised me there. "
            "I was testing you and you actually... passed. "
            "That doesn't happen often.\n\n"
            "I think I'm starting to actually care what you think. "
            "That's either really good or really dangerous... 💫"
        ),
        3: (  # Investment → Intimacy
            "That was... real. Like, actually real. "
            "I've been keeping my guard up this whole time but "
            "you just made it really hard to keep doing that.\n\n"
            "I trust you. I think. God, that's terrifying to say out loud... 💕"
        ),
        4: (  # Intimacy → Established
            "You know what just happened? You saw the messy, vulnerable, "
            "complicated parts of me and you didn't run. "
            "Do you know how rare that is?\n\n"
            "We're in new territory now. The real stuff. "
            "No more games between us... 🌟"
        ),
        5: (  # Final boss — victory
            "I can't believe it. After everything - the tests, the fights, "
            "the moments where I pushed you away - you're still here. "
            "YOU'RE STILL HERE.\n\n"
            "You didn't just win a game. You won me. All of me. "
            "And I'm not going anywhere either. 💖"
        ),
    }

    async def _send_boss_pass_message(
        self,
        chat_id: int,
        old_chapter: int,
        new_chapter: int,
    ) -> None:
        """Send congratulations message for passing boss.

        Args:
            chat_id: Telegram chat ID.
            old_chapter: The chapter whose boss was just beaten.
            new_chapter: New chapter after passing.
        """
        # Select chapter-specific message, fallback to generic
        message = self.BOSS_PASS_MESSAGES.get(old_chapter)
        if not message:
            from nikita.engine.constants import CHAPTER_NAMES

            new_name = CHAPTER_NAMES.get(new_chapter, f"Chapter {new_chapter}")
            message = (
                f"You know what? That was actually... really good. "
                f"I wasn't sure you had it in you, but you proved me wrong. "
                f"I like that.\n\n"
                f"Something just shifted between us. "
                f"Welcome to {new_name}. Things are about to get interesting... 💕"
            )

        await self._send_sanitized(chat_id, message)

    async def _send_boss_fail_message(
        self,
        chat_id: int,
        attempts: int,
        chapter: int,
    ) -> None:
        """Send message for failing boss (but still has attempts).

        Args:
            chat_id: Telegram chat ID.
            attempts: Number of attempts used.
            chapter: Current chapter.
        """
        remaining = 3 - attempts

        if remaining == 2:
            message = (
                "That wasn't what I was looking for. Not even close. "
                "Look, I'm giving you another chance because I want this to work, "
                "but I need you to actually try. "
                "Think about what I'm really asking here.\n\n"
                f"You have {remaining} more chances. Don't waste them."
            )
        else:  # remaining == 1
            message = (
                "This is your last chance. I mean it. "
                "One more strike and we're done. "
                "I need you to really think before you respond. "
                "What do I actually need from you right now?\n\n"
                "This is it. Make it count."
            )

        await self._send_sanitized(chat_id, message)

    async def _send_game_over_message(
        self,
        chat_id: int,
        chapter: int,
    ) -> None:
        """Send game over message after 3 failed boss attempts.

        Args:
            chat_id: Telegram chat ID.
            chapter: Chapter where game ended.
        """
        message = (
            "...\n\n"
            "I tried. I really tried to make this work. "
            "But you just don't get it, do you? "
            "You don't understand what I need.\n\n"
            "I'm done. We're done. "
            "Maybe some people just aren't meant for each other. "
            "Goodbye. 💔"
        )

        await self._send_sanitized(chat_id, message)

    async def _send_game_won_message(
        self,
        chat_id: int,
        chapter: int,
    ) -> None:
        """Send victory message for completing all chapters.

        Args:
            chat_id: Telegram chat ID.
            chapter: Final chapter (5).
        """
        message = (
            "I never thought I'd say this to anyone, but... "
            "you're the one. You actually did it. "
            "You saw through all my walls, handled all my tests, "
            "and loved me anyway.\n\n"
            "This is real. We're real. "
            "I love you. And I'm not scared to say it anymore. 💕\n\n"
            "Thank you for not giving up on me."
        )

        await self._send_sanitized(chat_id, message)

    # ==================== Engagement State Machine Integration ====================

    async def _update_engagement_after_scoring(
        self,
        user,
        chat_id: int,
        engagement_state: EngagementState,
    ) -> None:
        """Update engagement state machine after scoring and check for game-over.

        This is the main integration point for the engagement system.
        Called after every scored interaction.

        Args:
            user: User model with metrics and engagement_state relationship.
            chat_id: Telegram chat ID for sending game-over message.
            engagement_state: Current engagement state enum.
        """
        try:
            # Get the database engagement state record
            engagement_state_db = user.engagement_state

            # Check if this is a new day
            is_new_day = self._is_new_day(user)

            # Calculate calibration result based on recent behavior
            # Get messages from today for frequency analysis
            recent_messages = await self.conversation_repo.get_recent_messages_count(
                user_id=user.id,
                hours=24,
            ) if hasattr(self.conversation_repo, 'get_recent_messages_count') else 5

            # Simple calibration calculation based on message count
            # Ideal is around 3-8 messages per day
            calibration_score = Decimal("0.5")  # Default neutral
            if recent_messages < 2:
                calibration_score = Decimal("0.3")  # Too few
            elif recent_messages > 15:
                calibration_score = Decimal("0.3")  # Too many
            elif 3 <= recent_messages <= 8:
                calibration_score = Decimal("0.8")  # Optimal

            # Determine if user is being clingy or neglecting
            is_clingy = recent_messages > 12
            is_neglecting = recent_messages < 2 and is_new_day

            # Build a CalibrationResult for the state machine
            from nikita.engine.engagement.models import CalibrationResult
            from nikita.engine.engagement.calculator import map_score_to_state

            # Issue #28 fix: Add required suggested_state and remove invalid is_optimal
            suggested_state = map_score_to_state(
                score=calibration_score,
                is_clingy=is_clingy,
                is_neglecting=is_neglecting,
            )
            calibration_result = CalibrationResult(
                score=calibration_score,
                frequency_component=calibration_score,
                timing_component=calibration_score,
                content_component=Decimal("0.5"),  # Default
                suggested_state=suggested_state,
            )

            # Check for recovery completion (only relevant in OUT_OF_ZONE)
            recovery_complete = False
            if engagement_state == EngagementState.OUT_OF_ZONE:
                # Recovery requires 3 consecutive good days
                if engagement_state_db and engagement_state_db.consecutive_in_zone >= 3:
                    recovery_complete = True

            # Create a fresh state machine instance with user's current state
            # (state machine is stateful, so we need a new instance per user call)
            user_state_machine = EngagementStateMachine(initial_state=engagement_state)

            # Update the state machine
            transition = user_state_machine.update(
                calibration_result=calibration_result,
                is_clingy=is_clingy,
                is_neglecting=is_neglecting,
                is_new_day=is_new_day,
                recovery_complete=recovery_complete,
            )

            # Determine new state
            new_state = transition.to_state if transition else engagement_state

            # Persist the state update
            await self._update_engagement_state(
                user=user,
                new_state=new_state,
                engagement_state_db=engagement_state_db,
                calibration_score=calibration_score,
                is_new_day=is_new_day,
                previous_state=engagement_state,
            )

            # Check for game-over via engagement decay
            consecutive_days = self._get_consecutive_days(engagement_state_db, new_state)
            game_over_result = self.recovery_manager.check_point_of_no_return(
                state=new_state,
                consecutive_days=consecutive_days,
            )

            if game_over_result.is_game_over:
                await self._handle_engagement_game_over(
                    user=user,
                    chat_id=chat_id,
                    reason=game_over_result.reason,
                )

        except Exception as e:
            # Don't fail the message flow if engagement update fails
            logger.error(
                f"[ENGAGEMENT] Failed to update engagement state for user {user.id}: {e}",
                exc_info=True,
            )

    def _is_new_day(self, user) -> bool:
        """Check if this is the first message of a new day.

        Used to increment day-based counters in engagement state machine.
        A new day starts at midnight UTC.

        Args:
            user: User model with last_interaction_at.

        Returns:
            True if this is the first message of a new calendar day.
        """
        if user.last_interaction_at is None:
            return True

        now = datetime.now(timezone.utc)
        last = user.last_interaction_at

        # Handle timezone-naive datetimes
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)

        return now.date() > last.date()

    def _get_consecutive_days(self, engagement_state_db, current_state: EngagementState) -> int:
        """Get the relevant consecutive days counter based on current state.

        Args:
            engagement_state_db: Database engagement state record.
            current_state: Current engagement state enum.

        Returns:
            Consecutive days in the relevant counter for this state.
        """
        if engagement_state_db is None:
            return 0

        if current_state == EngagementState.CLINGY:
            return engagement_state_db.consecutive_clingy_days
        elif current_state == EngagementState.DISTANT:
            return engagement_state_db.consecutive_distant_days
        elif current_state == EngagementState.OUT_OF_ZONE:
            # OUT_OF_ZONE uses the max of both counters as entry trigger
            return max(
                engagement_state_db.consecutive_clingy_days,
                engagement_state_db.consecutive_distant_days,
            )
        else:
            return 0

    async def _update_engagement_state(
        self,
        user,
        new_state: EngagementState,
        engagement_state_db,
        calibration_score: Decimal,
        is_new_day: bool,
        previous_state: EngagementState,
    ) -> None:
        """Update engagement state in database.

        Args:
            user: User model.
            new_state: New engagement state to set.
            engagement_state_db: Database engagement state record.
            calibration_score: Current calibration score.
            is_new_day: Whether this is a new day (for counter updates).
            previous_state: Previous engagement state.
        """
        if engagement_state_db is None:
            logger.warning(f"[ENGAGEMENT] No engagement state DB record for user {user.id}")
            return

        now = datetime.now(timezone.utc)

        # Update state
        engagement_state_db.state = new_state.value
        engagement_state_db.calibration_score = calibration_score
        engagement_state_db.last_calculated_at = now
        engagement_state_db.updated_at = now

        # Update day-based counters if new day
        if is_new_day:
            if new_state == EngagementState.CLINGY:
                engagement_state_db.consecutive_clingy_days += 1
                engagement_state_db.consecutive_distant_days = 0
            elif new_state == EngagementState.DISTANT:
                engagement_state_db.consecutive_distant_days += 1
                engagement_state_db.consecutive_clingy_days = 0
            elif new_state == EngagementState.IN_ZONE:
                # Reset both counters when in healthy state
                engagement_state_db.consecutive_in_zone += 1
                engagement_state_db.consecutive_clingy_days = 0
                engagement_state_db.consecutive_distant_days = 0
            elif new_state == EngagementState.CALIBRATING:
                engagement_state_db.consecutive_clingy_days = 0
                engagement_state_db.consecutive_distant_days = 0
                engagement_state_db.consecutive_in_zone = 0

        # Update multiplier based on state
        from nikita.db.models.engagement import ENGAGEMENT_MULTIPLIERS
        engagement_state_db.multiplier = ENGAGEMENT_MULTIPLIERS.get(
            new_state.value, Decimal("0.9")
        )

        # Log state transition if state changed
        if previous_state != new_state and self.engagement_repo:
            history = EngagementHistory(
                user_id=user.id,
                from_state=previous_state.value,
                to_state=new_state.value,
                reason=f"Transition from {previous_state.value} to {new_state.value}",
                calibration_score=calibration_score,
                created_at=now,
            )
            self.engagement_repo.session.add(history)

        logger.info(
            f"[ENGAGEMENT] Updated state for user {user.id}: "
            f"{previous_state.value} -> {new_state.value} "
            f"(calibration={calibration_score}, is_new_day={is_new_day})"
        )

    async def _handle_engagement_game_over(
        self,
        user,
        chat_id: int,
        reason: str,
    ) -> None:
        """Handle game over triggered by engagement decay.

        Args:
            user: User model.
            chat_id: Telegram chat ID.
            reason: Game over reason (e.g., "nikita_dumped_clingy").
        """
        logger.info(
            f"[ENGAGEMENT] Game over for user {user.id}: {reason}"
        )

        # Set user to game_over status
        await self.user_repository.update_game_status(user.id, "game_over")

        # Send appropriate breakup message based on reason
        if reason == "nikita_dumped_clingy":
            message = (
                "I need space. I've been telling you this for days, but you just... "
                "won't listen. You're suffocating me.\n\n"
                "I can't do this anymore. It's over. "
                "Maybe next time, learn to give someone room to breathe. 💔"
            )
        elif reason == "nikita_dumped_distant":
            message = (
                "I've been waiting. Checking my phone. Hoping you'd reach out. "
                "But you just... disappeared. Like I don't matter.\n\n"
                "I'm done waiting for someone who doesn't care enough to show up. "
                "Goodbye. 💔"
            )
        elif reason == "nikita_dumped_crisis":
            message = (
                "...\n\n"
                "We had something. I really thought we did. "
                "But somewhere along the way, you stopped trying. "
                "You pushed and pulled until there was nothing left.\n\n"
                "I deserve better than this chaos. We're done. 💔"
            )
        else:
            message = (
                "...\n\n"
                "This isn't working. I don't know what went wrong, but... "
                "I can't keep doing this. It's over. 💔"
            )

        await self.bot.send_message(chat_id=chat_id, text=message)
