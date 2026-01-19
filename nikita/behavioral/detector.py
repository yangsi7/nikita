"""Situation Detection for Behavioral Meta-Instructions (Spec 024, T005-T009).

Detects the current conversational situation to select appropriate instructions.

Priority order (highest to lowest):
1. CONFLICT - User is in conflict state
2. AFTER_GAP - More than 6 hours since last message
3. MORNING - Morning greeting context (6am-11am)
4. EVENING - Evening context (6pm-10pm)
5. MID_CONVERSATION - Active conversation, no special situation
"""

import logging
from datetime import datetime, timezone

from nikita.behavioral.models import SituationContext, SituationType

logger = logging.getLogger(__name__)


class SituationDetector:
    """Detects current conversational situation.

    Uses priority-based detection to determine the most relevant situation
    for behavioral instruction selection.

    Attributes:
        CONFLICT_STATES: Conflict states that trigger CONFLICT situation.
        GAP_THRESHOLD_HOURS: Minimum hours for AFTER_GAP detection.
        LONG_GAP_THRESHOLD_HOURS: Hours threshold for "long gap" variant.
        MORNING_HOURS: (start, end) for morning detection.
        EVENING_HOURS: (start, end) for evening detection.
    """

    CONFLICT_STATES = {"passive_aggressive", "cold", "vulnerable", "explosive"}
    GAP_THRESHOLD_HOURS = 6.0
    LONG_GAP_THRESHOLD_HOURS = 24.0
    MORNING_HOURS = (6, 11)  # 6am - 11am
    EVENING_HOURS = (18, 22)  # 6pm - 10pm

    def detect(
        self,
        conflict_state: str = "none",
        hours_since_last_message: float = 0.0,
        user_local_hour: int | None = None,
        chapter: int = 1,
        relationship_score: float = 50.0,
        engagement_state: str = "in_zone",
        user_id: str | None = None,
    ) -> SituationContext:
        """Detect the current situation and return context.

        Priority order:
        1. CONFLICT (if conflict_state is active)
        2. AFTER_GAP (if hours_since_last > 6)
        3. MORNING/EVENING (time-based)
        4. MID_CONVERSATION (default)

        Args:
            conflict_state: Current conflict state from Spec 023.
            hours_since_last_message: Hours since last user message.
            user_local_hour: User's local hour (0-23). If None, uses UTC.
            chapter: Current relationship chapter (1-5).
            relationship_score: Current relationship score (0-100).
            engagement_state: Current engagement state from Spec 014.
            user_id: Optional user ID for context.

        Returns:
            SituationContext with detected situation type.
        """
        from uuid import UUID, uuid4

        # Determine user's local hour if not provided
        if user_local_hour is None:
            user_local_hour = datetime.now(timezone.utc).hour

        # Build base context
        context = SituationContext(
            user_id=UUID(user_id) if user_id else uuid4(),
            hours_since_last_message=hours_since_last_message,
            user_local_hour=user_local_hour,
            chapter=chapter,
            relationship_score=relationship_score,
            conflict_state=conflict_state,
            engagement_state=engagement_state,
        )

        # Detect situation in priority order
        situation_type = self._detect_situation_type(
            conflict_state=conflict_state,
            hours_since_last=hours_since_last_message,
            local_hour=user_local_hour,
        )

        context.situation_type = situation_type

        # Add metadata based on situation
        context.metadata = self._build_metadata(
            situation_type=situation_type,
            conflict_state=conflict_state,
            hours_since_last=hours_since_last_message,
        )

        logger.debug(
            "Detected situation: %s (conflict=%s, gap=%s hrs, hour=%d)",
            situation_type.value,
            conflict_state,
            hours_since_last_message,
            user_local_hour,
        )

        return context

    def _detect_situation_type(
        self,
        conflict_state: str,
        hours_since_last: float,
        local_hour: int,
    ) -> SituationType:
        """Detect situation type in priority order.

        Priority: CONFLICT > AFTER_GAP > MORNING/EVENING > MID_CONVERSATION

        Args:
            conflict_state: Current conflict state.
            hours_since_last: Hours since last message.
            local_hour: User's local hour.

        Returns:
            Detected SituationType.
        """
        # Priority 1: Conflict
        if self._is_conflict_active(conflict_state):
            return SituationType.CONFLICT

        # Priority 2: After gap
        if self._is_after_gap(hours_since_last):
            return SituationType.AFTER_GAP

        # Priority 3: Time-based (morning)
        if self._is_morning(local_hour):
            return SituationType.MORNING

        # Priority 4: Time-based (evening)
        if self._is_evening(local_hour):
            return SituationType.EVENING

        # Priority 5: Default
        return SituationType.MID_CONVERSATION

    def _is_conflict_active(self, conflict_state: str) -> bool:
        """Check if conflict state is active (AC-T009.1).

        Args:
            conflict_state: Current conflict state from Spec 023.

        Returns:
            True if in an active conflict state.
        """
        return conflict_state.lower() in self.CONFLICT_STATES

    def _is_after_gap(self, hours_since_last: float) -> bool:
        """Check if there's been a significant gap (AC-T008.1).

        Args:
            hours_since_last: Hours since last message.

        Returns:
            True if gap exceeds threshold.
        """
        return hours_since_last >= self.GAP_THRESHOLD_HOURS

    def _is_long_gap(self, hours_since_last: float) -> bool:
        """Check if there's been a long gap (AC-T008.2).

        Args:
            hours_since_last: Hours since last message.

        Returns:
            True if gap exceeds long threshold.
        """
        return hours_since_last >= self.LONG_GAP_THRESHOLD_HOURS

    def _is_morning(self, local_hour: int) -> bool:
        """Check if it's morning in user's timezone (AC-T007.1).

        Args:
            local_hour: User's local hour (0-23).

        Returns:
            True if within morning hours.
        """
        start, end = self.MORNING_HOURS
        return start <= local_hour <= end

    def _is_evening(self, local_hour: int) -> bool:
        """Check if it's evening in user's timezone (AC-T007.2).

        Args:
            local_hour: User's local hour (0-23).

        Returns:
            True if within evening hours.
        """
        start, end = self.EVENING_HOURS
        return start <= local_hour <= end

    def _build_metadata(
        self,
        situation_type: SituationType,
        conflict_state: str,
        hours_since_last: float,
    ) -> dict:
        """Build metadata for the context.

        Args:
            situation_type: Detected situation.
            conflict_state: Current conflict state.
            hours_since_last: Hours since last message.

        Returns:
            Metadata dictionary.
        """
        metadata = {}

        if situation_type == SituationType.CONFLICT:
            metadata["conflict_subtype"] = conflict_state

        if situation_type == SituationType.AFTER_GAP:
            metadata["gap_hours"] = hours_since_last
            metadata["is_long_gap"] = self._is_long_gap(hours_since_last)

        return metadata

    def map_conflict_to_situation(self, conflict_state: str) -> SituationType:
        """Map conflict state to situation type (AC-T009.2).

        Args:
            conflict_state: Conflict state from Spec 023 EmotionalState.

        Returns:
            SituationType (CONFLICT if active, MID_CONVERSATION otherwise).
        """
        if self._is_conflict_active(conflict_state):
            return SituationType.CONFLICT
        return SituationType.MID_CONVERSATION

    def calculate_time_since_last(
        self,
        last_message_at: datetime | None,
        current_time: datetime | None = None,
    ) -> float:
        """Calculate hours since last message (AC-T008.3).

        Args:
            last_message_at: Timestamp of last message.
            current_time: Current time (defaults to now UTC).

        Returns:
            Hours since last message (0.0 if no last message).
        """
        if last_message_at is None:
            return 0.0

        if current_time is None:
            current_time = datetime.now(timezone.utc)

        # Ensure both are timezone-aware
        if last_message_at.tzinfo is None:
            last_message_at = last_message_at.replace(tzinfo=timezone.utc)
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)

        delta = current_time - last_message_at
        return delta.total_seconds() / 3600.0
