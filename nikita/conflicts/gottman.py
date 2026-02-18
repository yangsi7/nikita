"""Gottman ratio tracker for conflict system (Spec 057).

Tracks positive/negative interaction ratios using the Gottman method:
- 5:1 ratio during active conflict periods
- 20:1 ratio during normal periods
- Rolling 7-day window + per-session tracking

Pure computation class — no database access.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from nikita.conflicts.models import ConflictDetails, GottmanCounters


class GottmanTracker:
    """Tracks Gottman positive/negative interaction ratios (Spec 057).

    Two-ratio system:
    - During active conflict: target 5:1 (positive:negative)
    - During normal play: target 20:1 (positive:negative)

    Tracks both rolling 7-day window and per-session counters.
    """

    # Target ratios
    CONFLICT_TARGET: float = 5.0
    NORMAL_TARGET: float = 20.0

    # Rolling window (days)
    WINDOW_DAYS: int = 7

    # Temperature deltas for ratio status
    BELOW_TARGET_DELTA_MIN: float = 2.0
    BELOW_TARGET_DELTA_MAX: float = 5.0
    ABOVE_TARGET_DELTA_MIN: float = -1.0
    ABOVE_TARGET_DELTA_MAX: float = -2.0

    @classmethod
    def record_interaction(
        cls,
        counters: GottmanCounters,
        is_positive: bool,
        timestamp: datetime | None = None,
    ) -> GottmanCounters:
        """Record a positive or negative interaction.

        Args:
            counters: Current counters.
            is_positive: Whether the interaction was positive.
            timestamp: When the interaction occurred.

        Returns:
            Updated GottmanCounters.
        """
        timestamp = timestamp or datetime.now(UTC)

        if is_positive:
            return GottmanCounters(
                positive_count=counters.positive_count + 1,
                negative_count=counters.negative_count,
                session_positive=counters.session_positive + 1,
                session_negative=counters.session_negative,
                window_start=counters.window_start,
            )
        else:
            return GottmanCounters(
                positive_count=counters.positive_count,
                negative_count=counters.negative_count + 1,
                session_positive=counters.session_positive,
                session_negative=counters.session_negative + 1,
                window_start=counters.window_start,
            )

    @classmethod
    def get_ratio(cls, counters: GottmanCounters) -> float:
        """Calculate positive/negative ratio.

        Handles division by zero:
        - 0 positive, 0 negative -> 0.0 (neutral)
        - N positive, 0 negative -> infinity (healthy)

        Args:
            counters: Current counters.

        Returns:
            Ratio value. Float('inf') if no negatives but has positives.
        """
        if counters.negative_count == 0:
            return float("inf") if counters.positive_count > 0 else 0.0
        return counters.positive_count / counters.negative_count

    @classmethod
    def get_target(cls, is_in_conflict: bool) -> float:
        """Get target ratio based on conflict status.

        Args:
            is_in_conflict: Whether user is currently in a conflict.

        Returns:
            Target ratio (5.0 for conflict, 20.0 for normal).
        """
        return cls.CONFLICT_TARGET if is_in_conflict else cls.NORMAL_TARGET

    @classmethod
    def is_below_target(
        cls,
        counters: GottmanCounters,
        is_in_conflict: bool,
    ) -> bool:
        """Check if current ratio is below the target.

        Args:
            counters: Current counters.
            is_in_conflict: Whether user is in a conflict.

        Returns:
            True if ratio is below target (unhealthy).
        """
        ratio = cls.get_ratio(counters)
        target = cls.get_target(is_in_conflict)

        # Infinity is always above target
        if ratio == float("inf"):
            return False
        # Zero ratio with no interactions: not below target (neutral)
        if ratio == 0.0 and counters.positive_count == 0 and counters.negative_count == 0:
            return False
        return ratio < target

    @classmethod
    def calculate_temperature_delta(
        cls,
        counters: GottmanCounters,
        is_in_conflict: bool,
    ) -> float:
        """Calculate temperature delta based on Gottman ratio status.

        Below target: +2 to +5 (proportional to how far below)
        Above target: -1 to -2 (proportional to how far above)

        Args:
            counters: Current counters.
            is_in_conflict: Whether user is in a conflict.

        Returns:
            Temperature delta (positive = increase temp, negative = decrease).
        """
        ratio = cls.get_ratio(counters)
        target = cls.get_target(is_in_conflict)

        # No interactions yet — no delta
        if counters.positive_count == 0 and counters.negative_count == 0:
            return 0.0

        # Infinity ratio is always good
        if ratio == float("inf"):
            return cls.ABOVE_TARGET_DELTA_MIN  # -1.0

        if ratio < target:
            # Below target: temperature increases
            # Scale from min to max based on how far below
            if target == 0:
                shortfall = 1.0
            else:
                shortfall = min(1.0, (target - ratio) / target)
            return cls.BELOW_TARGET_DELTA_MIN + (
                cls.BELOW_TARGET_DELTA_MAX - cls.BELOW_TARGET_DELTA_MIN
            ) * shortfall
        else:
            # Above target: temperature decreases
            if target == 0:
                surplus = 1.0
            else:
                surplus = min(1.0, (ratio - target) / target)
            return cls.ABOVE_TARGET_DELTA_MIN + (
                cls.ABOVE_TARGET_DELTA_MAX - cls.ABOVE_TARGET_DELTA_MIN
            ) * surplus

    @classmethod
    def prune_window(
        cls,
        counters: GottmanCounters,
        window_days: int | None = None,
        now: datetime | None = None,
    ) -> GottmanCounters:
        """Prune counters if outside the rolling window.

        If the window has fully expired, reset counters.
        Partial pruning not supported (would need timestamped events).

        Args:
            counters: Current counters.
            window_days: Window size in days (default 7).
            now: Current timestamp.

        Returns:
            Updated counters (reset if window expired).
        """
        window = window_days if window_days is not None else cls.WINDOW_DAYS
        now = now or datetime.now(UTC)
        window_cutoff = now - timedelta(days=window)

        if counters.window_start < window_cutoff:
            # Window expired — reset rolling counters
            return GottmanCounters(
                positive_count=0,
                negative_count=0,
                session_positive=counters.session_positive,
                session_negative=counters.session_negative,
                window_start=now,
            )

        return counters

    @classmethod
    def reset_session(cls, counters: GottmanCounters) -> GottmanCounters:
        """Reset session counters while preserving rolling counters.

        Args:
            counters: Current counters.

        Returns:
            Counters with session reset.
        """
        return GottmanCounters(
            positive_count=counters.positive_count,
            negative_count=counters.negative_count,
            session_positive=0,
            session_negative=0,
            window_start=counters.window_start,
        )

    @classmethod
    def initialize_from_history(
        cls,
        score_entries: list[dict[str, Any]],
    ) -> GottmanCounters:
        """Bootstrap Gottman counters from score_history entries.

        Reads score_history entries and counts positive (delta>0) and
        negative (delta<0) entries from the last 7 days.

        Args:
            score_entries: List of dicts with 'delta' and optionally 'created_at' keys.

        Returns:
            Initialized GottmanCounters.
        """
        positive = 0
        negative = 0

        for entry in score_entries:
            delta = entry.get("delta", 0)
            # Handle string/Decimal delta values
            try:
                delta_val = float(delta)
            except (ValueError, TypeError):
                continue

            if delta_val > 0:
                positive += 1
            elif delta_val < 0:
                negative += 1

        return GottmanCounters(
            positive_count=positive,
            negative_count=negative,
            session_positive=0,
            session_negative=0,
            window_start=datetime.now(UTC),
        )

    @classmethod
    def update_conflict_details(
        cls,
        details: ConflictDetails,
        is_positive: bool,
        is_in_conflict: bool,
    ) -> ConflictDetails:
        """Update conflict details with a new Gottman interaction.

        Args:
            details: Current conflict details.
            is_positive: Whether the interaction was positive.
            is_in_conflict: Whether currently in conflict.

        Returns:
            Updated ConflictDetails.
        """
        counters = GottmanCounters(
            positive_count=details.positive_count,
            negative_count=details.negative_count,
            session_positive=details.session_positive,
            session_negative=details.session_negative,
        )

        new_counters = cls.record_interaction(counters, is_positive)
        new_ratio = cls.get_ratio(new_counters)
        new_target = cls.get_target(is_in_conflict)

        return ConflictDetails(
            temperature=details.temperature,
            zone=details.zone,
            positive_count=new_counters.positive_count,
            negative_count=new_counters.negative_count,
            gottman_ratio=new_ratio if new_ratio != float("inf") else 999.0,
            gottman_target=new_target,
            horsemen_detected=details.horsemen_detected,
            repair_attempts=details.repair_attempts,
            last_temp_update=details.last_temp_update,
            session_positive=new_counters.session_positive,
            session_negative=new_counters.session_negative,
        )
