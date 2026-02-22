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

Spec 041 T2.9/T2.10: Integrated with Emotional State Engine (Spec 023) and
Conflict System (Spec 027) for context-aware touchpoint delivery.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID

from nikita.emotional_state.models import ConflictState
from nikita.emotional_state.store import get_state_store
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

        Spec 041 T2.9: Integrated with Emotional State Engine (Spec 023).
        Queries nikita_emotional_states table via StateStore.

        Args:
            user_id: User's UUID.

        Returns:
            Emotional state dict with valence, arousal, dominance, intimacy,
            or default neutral state if no state exists.
        """
        try:
            store = get_state_store()
            state = await store.get_current_state(user_id)

            if state is None:
                # Return default neutral state if no state recorded
                logger.debug(f"No emotional state found for user {user_id}, using defaults")
                return {
                    "valence": 0.5,
                    "arousal": 0.5,
                    "dominance": 0.5,
                    "intimacy": 0.5,
                }

            # Convert EmotionalStateModel to dict format expected by StrategicSilence
            return {
                "valence": state.valence,
                "arousal": state.arousal,
                "dominance": state.dominance,
                "intimacy": state.intimacy,
            }

        except Exception as e:
            logger.warning(f"Failed to load emotional state for user {user_id}: {e}")
            # Graceful degradation: return neutral state on error
            return {
                "valence": 0.5,
                "arousal": 0.5,
                "dominance": 0.5,
                "intimacy": 0.5,
            }

    async def _check_conflict_active(self, user_id: UUID) -> bool:
        """Check if there's an active conflict with user.

        Spec 041 T2.10: Integrated with Conflict System (Spec 027).
        Checks conflict_state field from emotional state.

        Args:
            user_id: User's UUID.

        Returns:
            True if conflict is active (any state other than NONE).
        """
        try:
            store = get_state_store()
            state = await store.get_current_state(user_id)

            if state is None:
                return False

            # Conflict is active if state is anything other than NONE
            is_active = state.conflict_state != ConflictState.NONE

            if is_active:
                logger.debug(
                    f"Active conflict detected for user {user_id}: "
                    f"{state.conflict_state.value}"
                )

            return is_active

        except Exception as e:
            logger.warning(f"Failed to check conflict state for user {user_id}: {e}")
            # Graceful degradation: assume no conflict on error
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
        life_events: list | None = None,
    ) -> ScheduledTouchpoint | None:
        """Evaluate if a user is eligible for a touchpoint and schedule it.

        Args:
            user_id: User's UUID.
            current_time: Current time (for testing).
            life_events: LifeEvent objects from LifeSimStage for event-based
                triggers (Spec 071 Wave F). Pass None to skip event evaluation.

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

        # Evaluate eligibility (including event-based triggers from Spec 071)
        trigger_contexts = self.scheduler.evaluate_user(
            user_id=user_id,
            chapter=user.chapter or 1,
            user_timezone=getattr(user, "timezone", "UTC") or "UTC",
            last_interaction_at=getattr(user, "last_interaction_at", None),
            current_time=current_time,
            recent_touchpoints=recent,
            life_events=life_events,
        )

        if not trigger_contexts:
            return None

        # Use first (highest priority) trigger context
        trigger_context = trigger_contexts[0]

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
