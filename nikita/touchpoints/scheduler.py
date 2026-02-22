"""TouchpointScheduler for scheduling proactive initiations (Spec 025, Phase B: T006-T011).

Evaluates users for touchpoint eligibility and schedules touchpoints based on:
- Time triggers (morning/evening slots)
- Event triggers (life events from 022)
- Gap triggers (>24h without contact)

Spec 071 (Wave F): _evaluate_event_trigger() processes LifeEvent lists from
LifeSimStage, filtering by importance >= 0.7 and emotional impact, and
deduplicating against recent EVENT touchpoints for the same event_id.
"""

import logging
import random
from datetime import datetime, time, timedelta, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID

from nikita.touchpoints.models import (
    CHAPTER_CONFIGS,
    ScheduledTouchpoint,
    TouchpointConfig,
    TriggerContext,
    TriggerType,
    get_config_for_chapter,
)

if TYPE_CHECKING:
    from nikita.life_simulation.models import LifeEvent

logger = logging.getLogger(__name__)


class TouchpointScheduler:
    """Schedules proactive touchpoints for users.

    Evaluates eligibility based on:
    - Time of day (morning/evening slots)
    - Gap since last interaction
    - Life events
    - Chapter-specific rates (FR-002)

    Attributes:
        default_config: Default TouchpointConfig if chapter not specified.
    """

    def __init__(self, default_config: TouchpointConfig | None = None):
        """Initialize scheduler.

        Args:
            default_config: Default config if chapter not found.
        """
        self.default_config = default_config or TouchpointConfig()

    def get_config(self, chapter: int) -> TouchpointConfig:
        """Get configuration for a chapter.

        Args:
            chapter: User's current chapter (1-5).

        Returns:
            TouchpointConfig for the chapter.
        """
        return get_config_for_chapter(chapter)

    def evaluate_user(
        self,
        user_id: UUID,
        chapter: int,
        user_timezone: str = "UTC",
        last_interaction_at: datetime | None = None,
        current_time: datetime | None = None,
        recent_touchpoints: list[ScheduledTouchpoint] | None = None,
        life_events: list["LifeEvent"] | None = None,
    ) -> list[TriggerContext]:
        """Evaluate if user is eligible for touchpoints.

        Checks time-based, gap-based, and event-based triggers.
        Returns list of applicable trigger contexts (may be empty).

        Args:
            user_id: User's UUID.
            chapter: User's current chapter.
            user_timezone: User's timezone string.
            last_interaction_at: Time of last user interaction.
            current_time: Current time (for testing, defaults to now).
            recent_touchpoints: Recent touchpoints for deduplication.
            life_events: LifeEvent objects from LifeSimStage (Spec 071).

        Returns:
            List of TriggerContext objects for applicable triggers.
        """
        current_time = current_time or datetime.now(timezone.utc)
        config = self.get_config(chapter)
        triggers: list[TriggerContext] = []

        # Check deduplication - don't trigger if recent touchpoint exists
        if recent_touchpoints:
            if not self._can_trigger_after_recent(config, recent_touchpoints, current_time):
                return []

        # 1. Check time-based triggers
        time_trigger = self._evaluate_time_trigger(
            chapter=chapter,
            user_timezone=user_timezone,
            current_time=current_time,
            config=config,
        )
        if time_trigger:
            triggers.append(time_trigger)

        # 2. Check gap-based triggers
        if last_interaction_at:
            gap_trigger = self._evaluate_gap_trigger(
                chapter=chapter,
                last_interaction_at=last_interaction_at,
                current_time=current_time,
                config=config,
            )
            if gap_trigger:
                triggers.append(gap_trigger)

        # 3. Check event-based triggers (Spec 071: Wave F)
        if life_events:
            # Extract recent EVENT touchpoints for per-event dedup
            recent_event_touchpoints = [
                tp for tp in (recent_touchpoints or [])
                if tp.trigger_type == TriggerType.EVENT
            ]
            event_triggers = self._evaluate_event_trigger(
                user_id=user_id,
                life_events=life_events,
                chapter=chapter,
                recent_event_touchpoints=recent_event_touchpoints or None,
            )
            triggers.extend(event_triggers)

        return triggers

    def _can_trigger_after_recent(
        self,
        config: TouchpointConfig,
        recent_touchpoints: list[ScheduledTouchpoint],
        current_time: datetime,
    ) -> bool:
        """Check if we can trigger after recent touchpoints.

        Args:
            config: Touchpoint configuration.
            recent_touchpoints: Recent touchpoints.
            current_time: Current time.

        Returns:
            True if we can trigger, False if too soon.
        """
        if not recent_touchpoints:
            return True

        min_gap = timedelta(hours=config.min_gap_hours)

        for tp in recent_touchpoints:
            # Check if any recent touchpoint is too close
            if tp.delivered and tp.delivered_at:
                if current_time - tp.delivered_at < min_gap:
                    return False
            elif not tp.delivered and not tp.skipped:
                # Pending touchpoint exists - don't double-schedule
                return False

        return True

    def _evaluate_time_trigger(
        self,
        chapter: int,
        user_timezone: str,
        current_time: datetime,
        config: TouchpointConfig,
    ) -> TriggerContext | None:
        """Evaluate time-based trigger eligibility.

        Args:
            chapter: User's current chapter.
            user_timezone: User's timezone.
            current_time: Current time.
            config: Touchpoint configuration.

        Returns:
            TriggerContext if time trigger applies, None otherwise.
        """
        # Get user's local time
        user_local_time = self._get_user_local_time(current_time, user_timezone)
        user_hour = user_local_time.hour

        # Check if in time slot
        time_slot = self._get_current_time_slot(user_hour, config)
        if not time_slot:
            return None

        # Apply probability check
        rate = self._get_initiation_rate(config)
        if not self._should_trigger(rate):
            return None

        return TriggerContext(
            trigger_type=TriggerType.TIME,
            time_slot=time_slot,
            chapter=chapter,
        )

    def _evaluate_gap_trigger(
        self,
        chapter: int,
        last_interaction_at: datetime,
        current_time: datetime,
        config: TouchpointConfig,
    ) -> TriggerContext | None:
        """Evaluate gap-based trigger eligibility.

        Args:
            chapter: User's current chapter.
            last_interaction_at: Time of last interaction.
            current_time: Current time.
            config: Touchpoint configuration.

        Returns:
            TriggerContext if gap trigger applies, None otherwise.
        """
        hours_since = (current_time - last_interaction_at).total_seconds() / 3600

        if hours_since < config.gap_trigger_hours:
            return None

        # Gap triggers are more certain - higher probability than time triggers
        gap_rate = min(0.5, self._get_initiation_rate(config) * 1.5)
        if not self._should_trigger(gap_rate):
            return None

        return TriggerContext(
            trigger_type=TriggerType.GAP,
            hours_since_contact=hours_since,
            chapter=chapter,
        )

    def _evaluate_event_trigger(
        self,
        user_id: UUID,
        life_events: list["LifeEvent"] | None,
        chapter: int,
        recent_event_touchpoints: list[ScheduledTouchpoint] | None = None,
    ) -> list[TriggerContext]:
        """Evaluate life events and return EVENT trigger contexts (Spec 071 Wave F).

        Processes a list of LifeEvent objects from LifeSimStage:
        1. Filters to events with importance >= 0.7
        2. Filters to events with meaningful emotional impact (abs sum > 0)
        3. Deduplicates against recent EVENT touchpoints for the same event_id
        4. Applies chapter-specific initiation rates via evaluate_event_trigger()

        Args:
            user_id: User's UUID.
            life_events: LifeEvent objects from LifeSimStage. None or empty → no triggers.
            chapter: User's current chapter (affects initiation rate).
            recent_event_touchpoints: Recent EVENT touchpoints for per-event dedup.

        Returns:
            List of TriggerContext objects for qualifying life events (may be empty).
        """
        if not life_events:
            return []

        # Build set of already-triggered event IDs for dedup
        triggered_event_ids: set[str] = set()
        if recent_event_touchpoints:
            for tp in recent_event_touchpoints:
                if tp.trigger_context.event_id:
                    triggered_event_ids.add(tp.trigger_context.event_id)

        triggers: list[TriggerContext] = []

        for event in life_events:
            # Filter 1: importance threshold
            if event.importance < 0.7:
                logger.debug(
                    "event_trigger_skipped_low_importance",
                    event_id=str(event.event_id),
                    importance=event.importance,
                )
                continue

            # Filter 2: must have meaningful emotional impact (at least one non-zero dimension)
            impact = event.emotional_impact
            emotional_magnitude = abs(impact.arousal_delta) + abs(impact.valence_delta)
            if emotional_magnitude == 0.0:
                logger.debug(
                    "event_trigger_skipped_no_emotional_impact",
                    event_id=str(event.event_id),
                )
                continue

            # Filter 3: deduplication — skip if already triggered for this event
            event_id_str = str(event.event_id)
            if event_id_str in triggered_event_ids:
                logger.debug(
                    "event_trigger_deduplicated",
                    event_id=event_id_str,
                )
                continue

            # Calculate emotional intensity from impact magnitude (normalised to 0–1)
            emotional_intensity = min(1.0, emotional_magnitude / 0.6)

            # Delegate to existing evaluate_event_trigger() which applies chapter rates
            trigger_ctx = self.evaluate_event_trigger(
                chapter=chapter,
                event_id=event_id_str,
                event_type=event.event_type.value,
                event_description=event.description,
                importance=event.importance,
                emotional_intensity=emotional_intensity,
            )

            if trigger_ctx:
                triggers.append(trigger_ctx)
                logger.debug(
                    "event_trigger_created",
                    event_id=event_id_str,
                    event_type=event.event_type.value,
                    chapter=chapter,
                )

        return triggers

    def evaluate_event_trigger(
        self,
        chapter: int,
        event_id: str,
        event_type: str,
        event_description: str,
        importance: float = 0.5,
        emotional_intensity: float = 0.5,
        emotional_state: dict[str, Any] | None = None,
    ) -> TriggerContext | None:
        """Evaluate event-based trigger eligibility.

        Higher importance and emotional intensity increase trigger probability.

        Args:
            chapter: User's current chapter.
            event_id: Life event ID.
            event_type: Type of event.
            event_description: Description of event.
            importance: Event importance (0.0-1.0).
            emotional_intensity: Emotional intensity (0.0-1.0).
            emotional_state: Current emotional state snapshot.

        Returns:
            TriggerContext if event trigger applies, None otherwise.
        """
        config = self.get_config(chapter)
        base_rate = self._get_initiation_rate(config)

        # Modify rate by importance and emotional intensity
        # High importance events get 2x rate, high emotional events get 1.5x
        modified_rate = base_rate * (1 + importance) * (1 + emotional_intensity * 0.5)
        modified_rate = min(0.8, modified_rate)  # Cap at 80%

        if not self._should_trigger(modified_rate):
            return None

        return TriggerContext(
            trigger_type=TriggerType.EVENT,
            event_id=event_id,
            event_type=event_type,
            event_description=event_description,
            chapter=chapter,
            emotional_state=emotional_state or {},
        )

    def schedule(
        self,
        user_id: UUID,
        trigger_context: TriggerContext,
        delivery_delay_minutes: int = 0,
        message_content: str = "",
    ) -> ScheduledTouchpoint:
        """Create a scheduled touchpoint.

        Args:
            user_id: User's UUID.
            trigger_context: Trigger context.
            delivery_delay_minutes: Minutes to delay delivery.
            message_content: Pre-generated message (can be empty, generated later).

        Returns:
            Scheduled touchpoint ready for persistence.
        """
        delivery_at = datetime.now(timezone.utc) + timedelta(minutes=delivery_delay_minutes)

        return ScheduledTouchpoint(
            user_id=user_id,
            trigger_type=trigger_context.trigger_type,
            trigger_context=trigger_context,
            message_content=message_content,
            delivery_at=delivery_at,
        )

    def _get_user_local_time(self, utc_time: datetime, user_timezone: str) -> datetime:
        """Convert UTC time to user's local time.

        Args:
            utc_time: Time in UTC.
            user_timezone: User's timezone string.

        Returns:
            Time in user's timezone.
        """
        try:
            import zoneinfo

            tz = zoneinfo.ZoneInfo(user_timezone)
            return utc_time.astimezone(tz)
        except Exception:
            # Fallback to UTC if timezone is invalid
            return utc_time

    def _get_current_time_slot(self, hour: int, config: TouchpointConfig) -> str | None:
        """Get current time slot name if in a slot.

        Args:
            hour: Current hour (0-23).
            config: Touchpoint configuration.

        Returns:
            "morning", "evening", or None.
        """
        if config.morning_slot_start <= hour < config.morning_slot_end:
            return "morning"
        if config.evening_slot_start <= hour < config.evening_slot_end:
            return "evening"
        return None

    def _get_initiation_rate(self, config: TouchpointConfig) -> float:
        """Get random initiation rate within config bounds.

        Args:
            config: Touchpoint configuration.

        Returns:
            Initiation rate (0.0-1.0).
        """
        return random.uniform(config.initiation_rate_min, config.initiation_rate_max)

    def _should_trigger(self, probability: float) -> bool:
        """Probabilistic trigger decision.

        Args:
            probability: Probability of triggering (0.0-1.0).

        Returns:
            True if should trigger.
        """
        return random.random() < probability


def get_hours_since_interaction(
    last_interaction_at: datetime | None,
    current_time: datetime | None = None,
) -> float:
    """Calculate hours since last interaction.

    Args:
        last_interaction_at: Time of last interaction.
        current_time: Current time (defaults to now).

    Returns:
        Hours since interaction, or float('inf') if no interaction.
    """
    if last_interaction_at is None:
        return float("inf")

    current_time = current_time or datetime.now(timezone.utc)

    # Ensure both are timezone-aware
    if last_interaction_at.tzinfo is None:
        last_interaction_at = last_interaction_at.replace(tzinfo=timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)

    return (current_time - last_interaction_at).total_seconds() / 3600
