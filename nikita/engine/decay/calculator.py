"""Decay calculator for Nikita game engine (spec 005).

Calculates decay amounts based on time since last interaction,
chapter-specific rates, and grace periods.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Protocol

from nikita.engine.constants import DECAY_RATES, GRACE_PERIODS
from nikita.engine.decay.models import DecayResult

if TYPE_CHECKING:
    from uuid import UUID


class UserLike(Protocol):
    """Protocol for user objects accepted by DecayCalculator."""

    id: "UUID"
    chapter: int
    relationship_score: Decimal
    last_interaction_at: datetime | None
    game_status: str


class DecayCalculator:
    """Calculates decay for inactive users.

    Uses chapter-specific grace periods and decay rates from constants.py.

    Example usage:
        calculator = DecayCalculator()
        if calculator.is_overdue(user):
            result = calculator.calculate_decay(user)
            if result:
                # Apply result.decay_amount to user's score
    """

    def __init__(
        self,
        *,
        max_decay_per_cycle: Decimal = Decimal("20.0"),
    ) -> None:
        """Initialize decay calculator.

        Args:
            max_decay_per_cycle: Maximum decay allowed per calculation cycle.
                Defaults to 20% to prevent catastrophic decay from long absences.
        """
        self.max_decay_per_cycle = max_decay_per_cycle

    def is_overdue(self, user: UserLike) -> bool:
        """Check if user is past their grace period.

        Args:
            user: User object with chapter and last_interaction_at fields.

        Returns:
            True if user is overdue for decay, False if still within grace period.
        """
        if user.last_interaction_at is None:
            return True

        grace_period = GRACE_PERIODS[user.chapter]
        now = datetime.now(UTC)
        time_since_interaction = now - user.last_interaction_at

        # Overdue if STRICTLY past grace period (at grace boundary is still safe)
        # Use seconds comparison to avoid floating point issues
        return time_since_interaction.total_seconds() > grace_period.total_seconds()

    def calculate_decay(self, user: UserLike) -> DecayResult | None:
        """Calculate decay for a user.

        Args:
            user: User object with chapter, relationship_score, last_interaction_at.

        Returns:
            DecayResult with calculated decay amount, or None if user is within grace period.
        """
        if not self.is_overdue(user):
            return None

        now = datetime.now(UTC)
        grace_period = GRACE_PERIODS[user.chapter]
        decay_rate = DECAY_RATES[user.chapter]

        # Calculate hours overdue (time past grace period)
        if user.last_interaction_at is None:
            # If never interacted, use a reasonable default (24 hours overdue)
            hours_overdue = 24.0
        else:
            time_since = now - user.last_interaction_at
            time_overdue = time_since - grace_period
            hours_overdue = time_overdue.total_seconds() / 3600.0

        # Calculate raw decay: hours × rate
        raw_decay = Decimal(str(hours_overdue)) * decay_rate

        # Cap at max_decay_per_cycle
        capped_decay = min(raw_decay, self.max_decay_per_cycle)

        # Calculate score after (floor at 0)
        score_before = user.relationship_score
        score_after = max(Decimal("0"), score_before - capped_decay)

        # Actual decay applied (may be less than capped if score was low)
        actual_decay = score_before - score_after

        # Check if game over triggered
        game_over_triggered = score_after == Decimal("0")

        return DecayResult(
            user_id=user.id,
            decay_amount=actual_decay,
            score_before=score_before,
            score_after=score_after,
            hours_overdue=hours_overdue,
            chapter=user.chapter,
            timestamp=now,
            game_over_triggered=game_over_triggered,
            decay_reason="inactivity",
        )
