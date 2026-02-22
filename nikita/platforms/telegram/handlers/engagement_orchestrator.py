"""EngagementOrchestrator — extracted engagement state machine logic (Strangler Fig, Phase 2).

Handles:
- Updating the engagement state machine after each scored interaction
- Persisting state transitions to the database
- Detecting game-over via engagement decay (RecoveryManager)
- Sending appropriate breakup messages

This class is standalone and unit-testable independently of MessageHandler.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from nikita.config.enums import EngagementState
from nikita.db.models.engagement import EngagementHistory, ENGAGEMENT_MULTIPLIERS
from nikita.db.repositories.user_repository import UserRepository
from nikita.db.repositories.conversation_repository import ConversationRepository
from nikita.db.repositories.engagement_repository import EngagementStateRepository
from nikita.engine.engagement.recovery import RecoveryManager
from nikita.engine.engagement.state_machine import EngagementStateMachine
from nikita.platforms.telegram.bot import TelegramBot

logger = logging.getLogger(__name__)


class EngagementOrchestrator:
    """Standalone orchestrator for engagement state machine updates.

    Extracted from MessageHandler._update_engagement_after_scoring via Strangler Fig.
    Manages the full engagement lifecycle: calibration, state update, game-over detection.
    """

    def __init__(
        self,
        bot: TelegramBot,
        user_repository: UserRepository,
        conversation_repository: ConversationRepository,
        engagement_repository: Optional[EngagementStateRepository] = None,
    ) -> None:
        """Initialise EngagementOrchestrator.

        Args:
            bot: Telegram bot client for sending breakup messages.
            user_repository: Repository for user status updates.
            conversation_repository: Repository for recent-messages lookups.
            engagement_repository: Optional engagement history repository.
        """
        self.bot = bot
        self.user_repository = user_repository
        self.conversation_repo = conversation_repository
        self.engagement_repo = engagement_repository
        self.recovery_manager = RecoveryManager()

    async def update_engagement_after_scoring(
        self,
        user,
        chat_id: int,
        engagement_state: EngagementState,
    ) -> None:
        """Update engagement state machine after scoring and check for game-over.

        Mirrors MessageHandler._update_engagement_after_scoring behaviour.

        Args:
            user: User model with metrics and engagement_state relationship.
            chat_id: Telegram chat ID for sending game-over message.
            engagement_state: Current engagement state enum.
        """
        try:
            engagement_state_db = user.engagement_state
            is_new_day = self._is_new_day(user)

            recent_messages = (
                await self.conversation_repo.get_recent_messages_count(
                    user_id=user.id,
                    hours=24,
                )
                if hasattr(self.conversation_repo, "get_recent_messages_count")
                else 5
            )

            calibration_score = Decimal("0.5")
            if recent_messages < 2:
                calibration_score = Decimal("0.3")
            elif recent_messages > 15:
                calibration_score = Decimal("0.3")
            elif 3 <= recent_messages <= 8:
                calibration_score = Decimal("0.8")

            is_clingy = recent_messages > 12
            is_neglecting = recent_messages < 2 and is_new_day

            from nikita.engine.engagement.calculator import map_score_to_state
            from nikita.engine.engagement.models import CalibrationResult

            suggested_state = map_score_to_state(
                score=calibration_score,
                is_clingy=is_clingy,
                is_neglecting=is_neglecting,
            )
            calibration_result = CalibrationResult(
                score=calibration_score,
                frequency_component=calibration_score,
                timing_component=calibration_score,
                content_component=Decimal("0.5"),
                suggested_state=suggested_state,
            )

            recovery_complete = False
            if engagement_state == EngagementState.OUT_OF_ZONE:
                if engagement_state_db and engagement_state_db.consecutive_in_zone >= 3:
                    recovery_complete = True

            user_state_machine = EngagementStateMachine(initial_state=engagement_state)
            transition = user_state_machine.update(
                calibration_result=calibration_result,
                is_clingy=is_clingy,
                is_neglecting=is_neglecting,
                is_new_day=is_new_day,
                recovery_complete=recovery_complete,
            )

            new_state = transition.to_state if transition else engagement_state

            await self._update_engagement_state(
                user=user,
                new_state=new_state,
                engagement_state_db=engagement_state_db,
                calibration_score=calibration_score,
                is_new_day=is_new_day,
                previous_state=engagement_state,
            )

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

        except Exception as exc:
            logger.error(
                "[ENGAGEMENT] Failed to update engagement state for user %s: %s",
                user.id,
                exc,
                exc_info=True,
            )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _is_new_day(self, user) -> bool:
        """Return True if this is the first message of a new calendar day (UTC)."""
        if user.last_interaction_at is None:
            return True

        now = datetime.now(timezone.utc)
        last = user.last_interaction_at

        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)

        return now.date() > last.date()

    def _get_consecutive_days(self, engagement_state_db, current_state: EngagementState) -> int:
        """Return the relevant consecutive-days counter for the given state."""
        if engagement_state_db is None:
            return 0

        if current_state == EngagementState.CLINGY:
            return engagement_state_db.consecutive_clingy_days
        elif current_state == EngagementState.DISTANT:
            return engagement_state_db.consecutive_distant_days
        elif current_state == EngagementState.OUT_OF_ZONE:
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
        """Persist engagement state update to the database record."""
        if engagement_state_db is None:
            logger.warning("[ENGAGEMENT] No engagement state DB record for user %s", user.id)
            return

        now = datetime.now(timezone.utc)

        engagement_state_db.state = new_state.value
        engagement_state_db.calibration_score = calibration_score
        engagement_state_db.last_calculated_at = now
        engagement_state_db.updated_at = now

        if is_new_day:
            if new_state == EngagementState.CLINGY:
                engagement_state_db.consecutive_clingy_days += 1
                engagement_state_db.consecutive_distant_days = 0
            elif new_state == EngagementState.DISTANT:
                engagement_state_db.consecutive_distant_days += 1
                engagement_state_db.consecutive_clingy_days = 0
            elif new_state == EngagementState.IN_ZONE:
                engagement_state_db.consecutive_in_zone += 1
                engagement_state_db.consecutive_clingy_days = 0
                engagement_state_db.consecutive_distant_days = 0
            elif new_state == EngagementState.CALIBRATING:
                engagement_state_db.consecutive_clingy_days = 0
                engagement_state_db.consecutive_distant_days = 0
                engagement_state_db.consecutive_in_zone = 0

        engagement_state_db.multiplier = ENGAGEMENT_MULTIPLIERS.get(
            new_state.value, Decimal("0.9")
        )

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
            "[ENGAGEMENT] Updated state for user %s: %s -> %s "
            "(calibration=%s, is_new_day=%s)",
            user.id,
            previous_state.value,
            new_state.value,
            calibration_score,
            is_new_day,
        )

    async def _handle_engagement_game_over(
        self,
        user,
        chat_id: int,
        reason: str,
    ) -> None:
        """Handle game-over triggered by engagement decay."""
        logger.info("[ENGAGEMENT] Game over for user %s: %s", user.id, reason)

        await self.user_repository.update_game_status(user.id, "game_over")

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
