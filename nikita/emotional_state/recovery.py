"""Recovery Manager for Emotional State Engine (Spec 023, T015-T017).

Handles recovery from conflict states through:
- Positive interaction effects
- Recovery rate calculation based on approach
- Time-based decay recovery

AC-T015: RecoveryManager class
AC-T016: Recovery rate calculation
AC-T017: Decay-based recovery
"""

import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from nikita.emotional_state.models import (
    ConflictState,
    EmotionalStateModel,
)

logger = logging.getLogger(__name__)


class RecoveryApproach(str, Enum):
    """User's approach to recovery affects rate."""

    APOLOGETIC = "apologetic"  # Full apology - fastest recovery
    VALIDATING = "validating"  # Acknowledges feelings - fast recovery
    NEUTRAL = "neutral"  # No action - slow recovery
    DEFENSIVE = "defensive"  # Justifying behavior - minimal recovery
    DISMISSIVE = "dismissive"  # Ignoring issue - no recovery


class RecoveryResult(BaseModel):
    """Result of a recovery attempt."""

    recovered: bool = False
    new_state: ConflictState = ConflictState.NONE
    recovery_amount: float = 0.0
    reason: str = ""


class RecoveryManager:
    """Manages recovery from conflict states.

    Recovery can occur through:
    1. Positive interactions (active recovery)
    2. Time-based decay (passive recovery)

    Recovery rates depend on:
    - Current conflict state
    - User's approach (apologetic, validating, dismissive, etc.)
    - Time since conflict started
    """

    # Recovery rates by approach (multiplier on base rate)
    # AC-T016: Recovery rate depends on user's approach
    APPROACH_RATES: dict[RecoveryApproach, float] = {
        RecoveryApproach.APOLOGETIC: 2.0,  # Fastest
        RecoveryApproach.VALIDATING: 1.5,
        RecoveryApproach.NEUTRAL: 0.5,
        RecoveryApproach.DEFENSIVE: 0.1,
        RecoveryApproach.DISMISSIVE: 0.0,  # No recovery
    }

    # Base recovery amount per positive interaction
    BASE_RECOVERY_AMOUNT = 0.2

    # Thresholds for state transitions during recovery
    RECOVERY_THRESHOLDS: dict[ConflictState, float] = {
        ConflictState.EXPLOSIVE: 0.3,  # Need 30% recovery to de-escalate
        ConflictState.COLD: 0.4,
        ConflictState.VULNERABLE: 0.5,
        ConflictState.PASSIVE_AGGRESSIVE: 0.3,
        ConflictState.NONE: 0.0,  # Already recovered
    }

    # Decay rates per day for passive recovery
    # AC-T017: Decay rate configurable per conflict state
    DECAY_RATES_PER_DAY: dict[ConflictState, float] = {
        ConflictState.EXPLOSIVE: 0.05,  # Slowest (needs 6+ days to fully decay)
        ConflictState.COLD: 0.15,  # 3-4 days
        ConflictState.VULNERABLE: 0.2,  # 3 days
        ConflictState.PASSIVE_AGGRESSIVE: 0.25,  # 2-3 days
        ConflictState.NONE: 0.0,
    }

    # Minimum time before passive decay starts (hours)
    DECAY_COOLDOWN_HOURS = 24

    def __init__(self) -> None:
        """Initialize RecoveryManager."""
        pass

    def can_recover(
        self,
        state: EmotionalStateModel,
        approach: RecoveryApproach = RecoveryApproach.NEUTRAL,
    ) -> bool:
        """Check if recovery is possible from current conflict state.

        AC-T015.2: can_recover() checks if recovery possible

        Args:
            state: Current emotional state.
            approach: User's recovery approach.

        Returns:
            True if recovery is possible.
        """
        # Already recovered
        if state.conflict_state == ConflictState.NONE:
            return False

        # Dismissive approach blocks recovery
        if approach == RecoveryApproach.DISMISSIVE:
            return False

        # Defensive approach has very low chance
        if approach == RecoveryApproach.DEFENSIVE:
            # Still possible but unlikely - allow attempt
            return True

        return True

    def apply_recovery(
        self,
        state: EmotionalStateModel,
        approach: RecoveryApproach = RecoveryApproach.NEUTRAL,
        intensity: float = 1.0,
    ) -> tuple[EmotionalStateModel, RecoveryResult]:
        """Apply recovery from positive interaction.

        AC-T015.3: apply_recovery() applies positive interaction effect

        Args:
            state: Current emotional state.
            approach: How the user approached recovery.
            intensity: How intense the recovery interaction was (0.0-1.0).

        Returns:
            Tuple of (updated state, recovery result).
        """
        result = RecoveryResult()

        if not self.can_recover(state, approach):
            result.reason = "Cannot recover with this approach"
            return state, result

        # Calculate recovery amount
        rate = self.APPROACH_RATES.get(approach, 0.5)
        recovery_amount = self.BASE_RECOVERY_AMOUNT * rate * intensity
        result.recovery_amount = recovery_amount

        # Get current recovery progress (from state metadata or start fresh)
        current_progress = state.metadata.get("recovery_progress", 0.0)
        new_progress = min(1.0, current_progress + recovery_amount)

        # Check if we've crossed the threshold for de-escalation
        threshold = self.RECOVERY_THRESHOLDS.get(state.conflict_state, 0.5)

        if new_progress >= threshold:
            # De-escalate to next lower state
            new_conflict_state = self._get_de_escalated_state(state.conflict_state)
            result.recovered = True
            result.new_state = new_conflict_state
            result.reason = f"Recovery progress {new_progress:.2f} crossed threshold {threshold:.2f}"

            # Update state
            new_state = state.set_conflict(
                new_conflict_state,
                trigger=f"Recovered via {approach.value}" if new_conflict_state != ConflictState.NONE else None,
            )
            # Reset progress for next level
            new_metadata = dict(state.metadata)
            new_metadata["recovery_progress"] = 0.0 if new_conflict_state != ConflictState.NONE else new_progress
            new_metadata["last_recovery_at"] = datetime.now(timezone.utc).isoformat()
            new_state = EmotionalStateModel(
                **{k: v for k, v in new_state.model_dump().items() if k != "metadata"},
                metadata=new_metadata,
            )

            logger.info(
                f"Recovery: {state.conflict_state.value} → {new_conflict_state.value} "
                f"(approach={approach.value}, progress={new_progress:.2f})"
            )
        else:
            result.recovered = False
            result.new_state = state.conflict_state
            result.reason = f"Progress {new_progress:.2f} below threshold {threshold:.2f}"

            # Update progress in state
            new_metadata = dict(state.metadata)
            new_metadata["recovery_progress"] = new_progress
            new_metadata["last_recovery_at"] = datetime.now(timezone.utc).isoformat()
            new_state = EmotionalStateModel(
                **{k: v for k, v in state.model_dump().items() if k != "metadata"},
                metadata=new_metadata,
            )

            logger.debug(
                f"Recovery progress: {current_progress:.2f} → {new_progress:.2f} "
                f"(threshold: {threshold:.2f})"
            )

        return new_state, result

    def calculate_recovery_rate(
        self,
        approach: RecoveryApproach,
        conflict_state: ConflictState,
    ) -> float:
        """Calculate recovery rate for given approach and state.

        AC-T016.1: Recovery rate depends on user's approach
        AC-T016.2: Apology + validation = faster recovery
        AC-T016.3: Dismissive = no recovery

        Args:
            approach: User's recovery approach.
            conflict_state: Current conflict state.

        Returns:
            Recovery rate (0.0-1.0 per interaction).
        """
        base_rate = self.BASE_RECOVERY_AMOUNT
        approach_multiplier = self.APPROACH_RATES.get(approach, 0.5)

        # Explosive state is harder to recover from
        if conflict_state == ConflictState.EXPLOSIVE:
            state_modifier = 0.5
        elif conflict_state == ConflictState.COLD:
            state_modifier = 0.7
        else:
            state_modifier = 1.0

        return base_rate * approach_multiplier * state_modifier

    def apply_decay_recovery(
        self,
        state: EmotionalStateModel,
        current_time: datetime | None = None,
    ) -> tuple[EmotionalStateModel, RecoveryResult]:
        """Apply passive decay-based recovery over time.

        AC-T017.1: Unresolved states decay slowly (3-5 days)
        AC-T017.2: Decay rate configurable per conflict state

        Args:
            state: Current emotional state.
            current_time: Current time (defaults to now).

        Returns:
            Tuple of (updated state, recovery result).
        """
        result = RecoveryResult()
        current_time = current_time or datetime.now(timezone.utc)

        # Can't decay from NONE
        if state.conflict_state == ConflictState.NONE:
            result.reason = "No conflict to recover from"
            return state, result

        # Check cooldown period
        conflict_started = state.conflict_started_at
        if conflict_started is None:
            conflict_started = current_time - timedelta(hours=self.DECAY_COOLDOWN_HOURS)

        hours_since_conflict = (current_time - conflict_started).total_seconds() / 3600
        if hours_since_conflict < self.DECAY_COOLDOWN_HOURS:
            result.reason = f"Cooldown period: {hours_since_conflict:.1f}h < {self.DECAY_COOLDOWN_HOURS}h"
            return state, result

        # Calculate decay amount based on time since last decay check
        last_decay_check = state.metadata.get("last_decay_check")
        if last_decay_check:
            last_decay_time = datetime.fromisoformat(last_decay_check)
        else:
            last_decay_time = conflict_started + timedelta(hours=self.DECAY_COOLDOWN_HOURS)

        days_since_check = (current_time - last_decay_time).total_seconds() / (24 * 3600)
        if days_since_check <= 0:
            result.reason = "No time elapsed since last decay check"
            return state, result

        # Get decay rate for this conflict state
        decay_rate = self.DECAY_RATES_PER_DAY.get(state.conflict_state, 0.1)
        decay_amount = decay_rate * days_since_check
        result.recovery_amount = decay_amount

        # Get current recovery progress
        current_progress = state.metadata.get("recovery_progress", 0.0)
        new_progress = min(1.0, current_progress + decay_amount)

        # Check threshold
        threshold = self.RECOVERY_THRESHOLDS.get(state.conflict_state, 0.5)

        # Update metadata
        new_metadata = dict(state.metadata)
        new_metadata["last_decay_check"] = current_time.isoformat()
        new_metadata["decay_amount"] = decay_amount

        if new_progress >= threshold:
            new_conflict_state = self._get_de_escalated_state(state.conflict_state)
            result.recovered = True
            result.new_state = new_conflict_state
            result.reason = f"Decay recovery: {days_since_check:.1f} days at {decay_rate:.2f}/day"

            new_metadata["recovery_progress"] = 0.0 if new_conflict_state != ConflictState.NONE else new_progress

            new_state = state.set_conflict(
                new_conflict_state,
                trigger="Decay recovery" if new_conflict_state != ConflictState.NONE else None,
            )
            new_state = EmotionalStateModel(
                **{k: v for k, v in new_state.model_dump().items() if k != "metadata"},
                metadata=new_metadata,
            )

            logger.info(
                f"Decay recovery: {state.conflict_state.value} → {new_conflict_state.value} "
                f"after {days_since_check:.1f} days"
            )
        else:
            result.recovered = False
            result.new_state = state.conflict_state
            result.reason = f"Decay progress: {new_progress:.2f}/{threshold:.2f}"

            new_metadata["recovery_progress"] = new_progress
            new_state = EmotionalStateModel(
                **{k: v for k, v in state.model_dump().items() if k != "metadata"},
                metadata=new_metadata,
            )

        return new_state, result

    def _get_de_escalated_state(self, current: ConflictState) -> ConflictState:
        """Get the next lower conflict state (de-escalation path).

        De-escalation paths:
        - EXPLOSIVE → COLD
        - COLD → NONE
        - VULNERABLE → NONE
        - PASSIVE_AGGRESSIVE → NONE
        """
        de_escalation_map = {
            ConflictState.EXPLOSIVE: ConflictState.COLD,
            ConflictState.COLD: ConflictState.NONE,
            ConflictState.VULNERABLE: ConflictState.NONE,
            ConflictState.PASSIVE_AGGRESSIVE: ConflictState.NONE,
            ConflictState.NONE: ConflictState.NONE,
        }
        return de_escalation_map.get(current, ConflictState.NONE)

    def get_estimated_recovery_time(
        self,
        state: EmotionalStateModel,
        approach: RecoveryApproach = RecoveryApproach.NEUTRAL,
    ) -> timedelta:
        """Estimate time to full recovery with given approach.

        Args:
            state: Current emotional state.
            approach: Expected recovery approach.

        Returns:
            Estimated time to full recovery.
        """
        if state.conflict_state == ConflictState.NONE:
            return timedelta(0)

        # For active recovery with neutral approach
        rate = self.calculate_recovery_rate(approach, state.conflict_state)
        if rate <= 0:
            # Fall back to decay-based estimate
            decay_rate = self.DECAY_RATES_PER_DAY.get(state.conflict_state, 0.1)
            threshold = self.RECOVERY_THRESHOLDS.get(state.conflict_state, 0.5)
            current_progress = state.metadata.get("recovery_progress", 0.0)
            remaining = threshold - current_progress
            if decay_rate > 0:
                days = remaining / decay_rate
                return timedelta(days=days)
            return timedelta(days=7)  # Default worst case

        # Estimate based on interactions
        threshold = self.RECOVERY_THRESHOLDS.get(state.conflict_state, 0.5)
        current_progress = state.metadata.get("recovery_progress", 0.0)
        remaining = threshold - current_progress
        interactions_needed = remaining / rate

        # Assume roughly 1 interaction per hour during active conversation
        return timedelta(hours=interactions_needed)


# Singleton
_recovery_instance: RecoveryManager | None = None


def get_recovery_manager() -> RecoveryManager:
    """Get singleton RecoveryManager instance."""
    global _recovery_instance
    if _recovery_instance is None:
        _recovery_instance = RecoveryManager()
    return _recovery_instance
