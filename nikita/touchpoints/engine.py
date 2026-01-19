"""TouchpointEngine for Proactive Touchpoint System (Spec 025, Phase E: T021-T025).

Orchestrates the full touchpoint delivery pipeline:
1. Evaluates eligible users
2. Schedules touchpoints
3. Generates messages
4. Applies strategic silence
5. Delivers via Telegram

Architecture:
- pg_cron triggers /api/v1/tasks/touchpoints every 5 minutes
- Engine processes due touchpoints
- Telegram delivery with retry logic
- Deduplication prevents double messaging
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID

from nikita.touchpoints.generator import MessageGenerator
from nikita.touchpoints.models import (
    ScheduledTouchpoint,
    TouchpointConfig,
    TriggerContext,
    TriggerType,
)
from nikita.touchpoints.scheduler import TouchpointScheduler
from nikita.touchpoints.silence import StrategicSilence, SilenceDecision
from nikita.touchpoints.store import TouchpointStore

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class DeliveryResult:
    """Result of touchpoint delivery attempt."""

    def __init__(
        self,
        touchpoint_id: UUID,
        success: bool,
        delivered_at: datetime | None = None,
        error: str | None = None,
        skipped_reason: str | None = None,
    ):
        self.touchpoint_id = touchpoint_id
        self.success = success
        self.delivered_at = delivered_at
        self.error = error
        self.skipped_reason = skipped_reason

    def __repr__(self) -> str:
        if self.success:
            return f"DeliveryResult(id={self.touchpoint_id}, success=True)"
        elif self.skipped_reason:
            return f"DeliveryResult(id={self.touchpoint_id}, skipped={self.skipped_reason})"
        else:
            return f"DeliveryResult(id={self.touchpoint_id}, error={self.error})"


class TouchpointEngine:
    """Orchestrates touchpoint evaluation, scheduling, and delivery.

    This is the main entry point for the proactive touchpoint system.
    It coordinates all components to enable Nikita to initiate conversations.

    Attributes:
        session: Database session.
        config: Touchpoint configuration.
        min_gap_minutes: Minimum gap between touchpoints to prevent spam.
    """

    # Default minimum gap between touchpoints (2 hours)
    DEFAULT_MIN_GAP_MINUTES = 120

    def __init__(
        self,
        session: "AsyncSession",
        config: TouchpointConfig | None = None,
        min_gap_minutes: int | None = None,
    ):
        """Initialize the touchpoint engine.

        Args:
            session: Async database session.
            config: Optional touchpoint configuration.
            min_gap_minutes: Minimum gap between touchpoints.
        """
        self.session = session
        self.config = config or TouchpointConfig()
        self.min_gap_minutes = min_gap_minutes or self.DEFAULT_MIN_GAP_MINUTES

        # Initialize components
        self.store = TouchpointStore(session)
        self.scheduler = TouchpointScheduler(default_config=self.config)
        self.generator = MessageGenerator(session)
        self.silence = StrategicSilence()

    async def deliver_due_touchpoints(self) -> list[DeliveryResult]:
        """Process and deliver all due touchpoints.

        This is called by pg_cron every 5 minutes.

        Returns:
            List of delivery results.
        """
        results = []

        # Get due touchpoints
        due_touchpoints = await self.store.get_due_touchpoints()
        logger.info(f"Found {len(due_touchpoints)} due touchpoints")

        for touchpoint in due_touchpoints:
            try:
                result = await self._deliver_single(touchpoint)
                results.append(result)
            except Exception as e:
                logger.error(f"Error delivering touchpoint {touchpoint.id}: {e}")
                results.append(
                    DeliveryResult(
                        touchpoint_id=touchpoint.id,
                        success=False,
                        error=str(e),
                    )
                )

        return results

    async def _deliver_single(
        self, touchpoint: ScheduledTouchpoint
    ) -> DeliveryResult:
        """Deliver a single touchpoint.

        Args:
            touchpoint: The touchpoint to deliver.

        Returns:
            Delivery result.
        """
        # Check for deduplication
        if await self._should_skip_for_dedup(touchpoint):
            await self.store.mark_skipped(touchpoint.id, "dedup")
            return DeliveryResult(
                touchpoint_id=touchpoint.id,
                success=False,
                skipped_reason="dedup",
            )

        # Apply strategic silence
        silence_decision = await self._evaluate_silence(touchpoint)
        if silence_decision.should_skip:
            reason = silence_decision.reason.value if silence_decision.reason else "silence"
            await self.store.mark_skipped(touchpoint.id, reason)
            return DeliveryResult(
                touchpoint_id=touchpoint.id,
                success=False,
                skipped_reason=reason,
            )

        # Generate message if not pre-generated
        if not touchpoint.message_content:
            touchpoint.message_content = await self._generate_message(touchpoint)

        # Deliver via Telegram
        success = await self._send_telegram_message(touchpoint)

        if success:
            await self.store.mark_delivered(touchpoint.id)
            return DeliveryResult(
                touchpoint_id=touchpoint.id,
                success=True,
                delivered_at=datetime.now(timezone.utc),
            )
        else:
            # Mark for retry (increment attempt counter)
            await self.store.mark_failed(touchpoint.id)
            return DeliveryResult(
                touchpoint_id=touchpoint.id,
                success=False,
                error="telegram_send_failed",
            )

    async def _should_skip_for_dedup(
        self, touchpoint: ScheduledTouchpoint
    ) -> bool:
        """Check if touchpoint should be skipped due to recent contact.

        Prevents sending multiple touchpoints too close together.

        Args:
            touchpoint: The touchpoint to check.

        Returns:
            True if should skip.
        """
        # Check for recent touchpoints to this user
        recent_cutoff = datetime.now(timezone.utc) - timedelta(minutes=self.min_gap_minutes)
        recent = await self.store.get_recent_touchpoints(
            user_id=touchpoint.user_id,
            since=recent_cutoff,
            exclude_id=touchpoint.id,
        )

        if recent:
            logger.info(
                f"Skipping touchpoint {touchpoint.id} due to recent contact "
                f"({len(recent)} touchpoints in last {self.min_gap_minutes} minutes)"
            )
            return True

        return False

    async def _evaluate_silence(
        self, touchpoint: ScheduledTouchpoint
    ) -> SilenceDecision:
        """Evaluate strategic silence for a touchpoint.

        Args:
            touchpoint: The touchpoint to evaluate.

        Returns:
            Silence decision.
        """
        # Load emotional state for user
        emotional_state = await self._load_emotional_state(touchpoint.user_id)

        # Check for active conflict
        conflict_active = await self._check_conflict_active(touchpoint.user_id)

        return self.silence.apply_strategic_silence(
            chapter=touchpoint.chapter or 1,
            emotional_state=emotional_state,
            conflict_active=conflict_active,
        )

    async def _load_emotional_state(
        self, user_id: UUID
    ) -> dict[str, Any] | None:
        """Load current emotional state for user.

        Args:
            user_id: User's UUID.

        Returns:
            Emotional state dict or None.
        """
        # TODO: Integrate with Spec 023 Emotional State Engine
        # For now, return neutral state
        # In full implementation, would query emotional_states table
        return {
            "valence": 0.5,  # Default neutral
            "arousal": 0.5,
            "dominance": 0.5,
        }

    async def _check_conflict_active(self, user_id: UUID) -> bool:
        """Check if there's an active conflict with user.

        Args:
            user_id: User's UUID.

        Returns:
            True if conflict is active.
        """
        # TODO: Integrate with conflict system (Spec 027)
        return False

    async def _generate_message(
        self, touchpoint: ScheduledTouchpoint
    ) -> str:
        """Generate message content for touchpoint.

        Args:
            touchpoint: The touchpoint.

        Returns:
            Generated message content.
        """
        # Use the existing trigger_context (it's already a TriggerContext model)
        return await self.generator.generate(
            user_id=touchpoint.user_id,
            trigger_context=touchpoint.trigger_context,
        )

    async def _send_telegram_message(
        self, touchpoint: ScheduledTouchpoint
    ) -> bool:
        """Send message via Telegram.

        Args:
            touchpoint: The touchpoint with message content.

        Returns:
            True if successful.
        """
        # Import here to avoid circular imports
        try:
            from nikita.platforms.telegram.bot import get_bot

            bot = get_bot()
            chat_id = await self._get_chat_id(touchpoint.user_id)

            if not chat_id:
                logger.error(f"No chat_id found for user {touchpoint.user_id}")
                return False

            await bot.send_message(chat_id, touchpoint.message_content)
            return True

        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
            return False

    async def _get_chat_id(self, user_id: UUID) -> int | None:
        """Get Telegram chat ID for user.

        Args:
            user_id: User's UUID.

        Returns:
            Chat ID or None.
        """
        from nikita.db.repositories.user_repository import UserRepository

        user_repo = UserRepository(self.session)
        user = await user_repo.get_by_id(user_id)

        if user and user.telegram_chat_id:
            return user.telegram_chat_id

        return None

    async def evaluate_and_schedule_for_user(
        self,
        user_id: UUID,
        current_time: datetime | None = None,
    ) -> ScheduledTouchpoint | None:
        """Evaluate if a user is eligible for a touchpoint and schedule it.

        Args:
            user_id: User's UUID.
            current_time: Current time (for testing).

        Returns:
            Scheduled touchpoint or None if not eligible.
        """
        current_time = current_time or datetime.now(timezone.utc)

        # Check deduplication first
        recent_cutoff = current_time - timedelta(minutes=self.min_gap_minutes)
        recent = await self.store.get_recent_touchpoints(
            user_id=user_id,
            since=recent_cutoff,
        )

        if recent:
            logger.debug(f"User {user_id} has recent touchpoints, skipping")
            return None

        # Load user context
        from nikita.db.repositories.user_repository import UserRepository

        user_repo = UserRepository(self.session)
        user = await user_repo.get_by_id(user_id)

        if not user:
            return None

        # Evaluate eligibility
        trigger_context = self.scheduler.evaluate_user(
            user_id=user_id,
            chapter=user.chapter or 1,
            hours_since_contact=self._compute_hours_since_contact(user),
            current_hour=current_time.hour,
        )

        if not trigger_context:
            return None

        # Schedule the touchpoint
        delivery_time = self._compute_delivery_time(trigger_context, current_time)

        touchpoint = await self.store.create(
            user_id=user_id,
            trigger_type=trigger_context.trigger_type,
            trigger_context=trigger_context.to_dict(),
            delivery_at=delivery_time,
            chapter=trigger_context.chapter,
        )

        logger.info(
            f"Scheduled touchpoint {touchpoint.id} for user {user_id} "
            f"at {delivery_time} (trigger: {trigger_context.trigger_type.value})"
        )

        return touchpoint

    def _compute_hours_since_contact(self, user) -> float:
        """Compute hours since last contact with user.

        Args:
            user: User model.

        Returns:
            Hours since last contact.
        """
        if not user.last_interaction_at:
            return 48.0  # Default to 2 days if no interaction

        delta = datetime.now(timezone.utc) - user.last_interaction_at
        return delta.total_seconds() / 3600

    def _compute_delivery_time(
        self,
        trigger_context: TriggerContext,
        current_time: datetime,
    ) -> datetime:
        """Compute optimal delivery time for touchpoint.

        Args:
            trigger_context: Trigger context.
            current_time: Current time.

        Returns:
            Delivery time.
        """
        # For time-based triggers, deliver immediately within the slot
        if trigger_context.trigger_type == TriggerType.TIME:
            return current_time

        # For event triggers, add small delay for naturalness
        if trigger_context.trigger_type == TriggerType.EVENT:
            return current_time + timedelta(minutes=5)

        # For gap triggers, deliver soon
        if trigger_context.trigger_type == TriggerType.GAP:
            return current_time + timedelta(minutes=2)

        return current_time


async def deliver_due_touchpoints(session: "AsyncSession") -> list[DeliveryResult]:
    """Convenience function to deliver due touchpoints.

    Called by /api/v1/tasks/touchpoints endpoint.

    Args:
        session: Database session.

    Returns:
        List of delivery results.
    """
    engine = TouchpointEngine(session)
    return await engine.deliver_due_touchpoints()
