"""Engagement state machine (spec 014).

This module implements the 6-state engagement model that tracks how players
interact with Nikita. State transitions are based on calibration scores
and consecutive behavior patterns.

State Machine:
- CALIBRATING: Initial state, learning player's style
- IN_ZONE: Sweet spot engagement
- DRIFTING: Off but recoverable
- CLINGY: Player messaging too much
- DISTANT: Player not engaging enough
- OUT_OF_ZONE: Crisis mode, needs recovery

Transition Rules:
- CALIBRATING → IN_ZONE: score >= 0.8 for 3+ consecutive
- CALIBRATING → DRIFTING: score < 0.5 for 2+ consecutive
- IN_ZONE → DRIFTING: score < 0.6 for 1+ exchange
- DRIFTING → IN_ZONE: score >= 0.7 for 2+ exchanges
- DRIFTING → CLINGY: clinginess > 0.7 for 2+ days
- DRIFTING → DISTANT: neglect > 0.6 for 2+ days
- CLINGY → DRIFTING: clinginess < 0.5 for 2+ days
- CLINGY → OUT_OF_ZONE: clingy 3+ consecutive days
- DISTANT → DRIFTING: neglect < 0.4 for 1+ day
- DISTANT → OUT_OF_ZONE: distant 5+ consecutive days
- OUT_OF_ZONE → CALIBRATING: recovery + grace period
"""

from decimal import Decimal

from nikita.config.enums import EngagementState
from nikita.engine.engagement.models import CalibrationResult, StateTransition

# Transition thresholds
THRESHOLDS = {
    # Score thresholds
    "in_zone_score": Decimal("0.8"),      # Score to be IN_ZONE
    "drifting_score": Decimal("0.6"),     # Below this = drift from IN_ZONE
    "low_score": Decimal("0.5"),          # Below this = drift from CALIBRATING
    "recovery_score": Decimal("0.7"),     # Score to recover from DRIFTING

    # Consecutive requirements
    "calibrating_to_in_zone": 3,    # Consecutive high scores
    "calibrating_to_drifting": 2,   # Consecutive low scores
    "drifting_to_in_zone": 2,       # Consecutive recovery scores
    "drifting_to_clingy": 2,        # Consecutive clingy days
    "drifting_to_distant": 2,       # Consecutive distant days
    "clingy_to_drifting": 2,        # Consecutive good days
    "clingy_to_out_of_zone": 3,     # Consecutive clingy days
    "distant_to_out_of_zone": 5,    # Consecutive distant days
}


class EngagementStateMachine:
    """State machine for engagement model.

    Tracks current state, consecutive counters, and transition history.
    Does NOT persist to database - caller is responsible for persistence.
    """

    def __init__(
        self,
        initial_state: EngagementState = EngagementState.CALIBRATING,
    ) -> None:
        """Initialize state machine.

        Args:
            initial_state: Starting state (default: CALIBRATING)
        """
        self._state = initial_state
        self._history: list[StateTransition] = []

        # Consecutive counters
        self._consecutive_high_scores = 0
        self._consecutive_low_scores = 0
        self._consecutive_in_zone = 0
        self._consecutive_clingy_days = 0
        self._consecutive_distant_days = 0
        self._consecutive_recovery_scores = 0
        self._consecutive_good_days = 0  # For recovering from CLINGY/DISTANT

    @property
    def current_state(self) -> EngagementState:
        """Get current engagement state."""
        return self._state

    @property
    def current_multiplier(self) -> Decimal:
        """Get scoring multiplier for current state."""
        return self._state.get_multiplier()

    def update(
        self,
        calibration_result: CalibrationResult,
        is_clingy: bool = False,
        is_neglecting: bool = False,
        is_new_day: bool = False,
        recovery_complete: bool = False,
    ) -> StateTransition | None:
        """Evaluate and apply state transitions.

        Args:
            calibration_result: Current calibration result
            is_clingy: True if clinginess detected (score > 0.7)
            is_neglecting: True if neglect detected (score > 0.6)
            is_new_day: True if this is first update of new day
            recovery_complete: True if recovery action completed

        Returns:
            StateTransition if state changed, None otherwise
        """
        old_state = self._state
        score = calibration_result.score

        # Update consecutive counters based on score
        self._update_counters(score, is_clingy, is_neglecting, is_new_day)

        # Evaluate transitions based on current state
        new_state = self._evaluate_transition(
            score, is_clingy, is_neglecting, recovery_complete
        )

        if new_state != old_state:
            return self._apply_transition(old_state, new_state, score)

        return None

    def _update_counters(
        self,
        score: Decimal,
        is_clingy: bool,
        is_neglecting: bool,
        is_new_day: bool,
    ) -> None:
        """Update consecutive counters based on current metrics."""
        # High score counter
        if score >= THRESHOLDS["in_zone_score"]:
            self._consecutive_high_scores += 1
            self._consecutive_low_scores = 0
        else:
            self._consecutive_high_scores = 0

        # Low score counter
        if score < THRESHOLDS["low_score"]:
            self._consecutive_low_scores += 1
        else:
            self._consecutive_low_scores = 0

        # Recovery score counter (for DRIFTING → IN_ZONE)
        if score >= THRESHOLDS["recovery_score"]:
            self._consecutive_recovery_scores += 1
        else:
            self._consecutive_recovery_scores = 0

        # Day-based counters (only update on new days)
        if is_new_day:
            if is_clingy:
                self._consecutive_clingy_days += 1
                self._consecutive_distant_days = 0
                self._consecutive_good_days = 0
            elif is_neglecting:
                self._consecutive_distant_days += 1
                self._consecutive_clingy_days = 0
                self._consecutive_good_days = 0
            else:
                # Good day - track for recovery from CLINGY/DISTANT
                self._consecutive_good_days += 1
                self._consecutive_clingy_days = 0
                self._consecutive_distant_days = 0

    def _evaluate_transition(
        self,
        score: Decimal,
        is_clingy: bool,
        is_neglecting: bool,
        recovery_complete: bool,
    ) -> EngagementState:
        """Evaluate which state to transition to based on rules."""
        state = self._state

        if state == EngagementState.CALIBRATING:
            # CALIBRATING → IN_ZONE: 3+ consecutive high scores
            if self._consecutive_high_scores >= THRESHOLDS["calibrating_to_in_zone"]:
                return EngagementState.IN_ZONE
            # CALIBRATING → DRIFTING: 2+ consecutive low scores
            if self._consecutive_low_scores >= THRESHOLDS["calibrating_to_drifting"]:
                return EngagementState.DRIFTING

        elif state == EngagementState.IN_ZONE:
            # IN_ZONE → DRIFTING: 1+ exchange below threshold
            if score < THRESHOLDS["drifting_score"]:
                return EngagementState.DRIFTING

        elif state == EngagementState.DRIFTING:
            # DRIFTING → IN_ZONE: 2+ consecutive recovery scores
            if self._consecutive_recovery_scores >= THRESHOLDS["drifting_to_in_zone"]:
                return EngagementState.IN_ZONE
            # DRIFTING → CLINGY: 2+ clingy days
            if self._consecutive_clingy_days >= THRESHOLDS["drifting_to_clingy"]:
                return EngagementState.CLINGY
            # DRIFTING → DISTANT: 2+ distant days
            if self._consecutive_distant_days >= THRESHOLDS["drifting_to_distant"]:
                return EngagementState.DISTANT

        elif state == EngagementState.CLINGY:
            # CLINGY → OUT_OF_ZONE: 3+ consecutive clingy days
            if self._consecutive_clingy_days >= THRESHOLDS["clingy_to_out_of_zone"]:
                return EngagementState.OUT_OF_ZONE
            # CLINGY → DRIFTING: 2+ good days (not clingy)
            if self._consecutive_good_days >= THRESHOLDS["clingy_to_drifting"]:
                return EngagementState.DRIFTING

        elif state == EngagementState.DISTANT:
            # DISTANT → OUT_OF_ZONE: 5+ consecutive distant days
            if self._consecutive_distant_days >= THRESHOLDS["distant_to_out_of_zone"]:
                return EngagementState.OUT_OF_ZONE
            # DISTANT → DRIFTING: 1+ good day (not neglecting)
            if not is_neglecting:
                return EngagementState.DRIFTING

        elif state == EngagementState.OUT_OF_ZONE:
            # OUT_OF_ZONE → CALIBRATING: recovery complete
            if recovery_complete:
                return EngagementState.CALIBRATING

        return state

    def _apply_transition(
        self,
        from_state: EngagementState,
        to_state: EngagementState,
        score: Decimal,
    ) -> StateTransition:
        """Apply state transition and record in history."""
        reason = self._get_transition_reason(from_state, to_state)

        transition = StateTransition(
            from_state=from_state,
            to_state=to_state,
            reason=reason,
            calibration_score=score,
        )

        self._state = to_state
        self._history.append(transition)

        # Reset counters on transition
        if to_state == EngagementState.CALIBRATING:
            self._reset_counters()

        return transition

    def _get_transition_reason(
        self,
        from_state: EngagementState,
        to_state: EngagementState,
    ) -> str:
        """Get human-readable reason for transition."""
        reasons = {
            (EngagementState.CALIBRATING, EngagementState.IN_ZONE):
                "Achieved 3+ consecutive high calibration scores",
            (EngagementState.CALIBRATING, EngagementState.DRIFTING):
                "2+ consecutive low calibration scores",
            (EngagementState.IN_ZONE, EngagementState.DRIFTING):
                "Calibration score dropped below threshold",
            (EngagementState.DRIFTING, EngagementState.IN_ZONE):
                "2+ consecutive recovery scores",
            (EngagementState.DRIFTING, EngagementState.CLINGY):
                "2+ consecutive clingy days detected",
            (EngagementState.DRIFTING, EngagementState.DISTANT):
                "2+ consecutive distant days detected",
            (EngagementState.CLINGY, EngagementState.DRIFTING):
                "2+ consecutive non-clingy days",
            (EngagementState.CLINGY, EngagementState.OUT_OF_ZONE):
                "3+ consecutive clingy days - crisis mode",
            (EngagementState.DISTANT, EngagementState.DRIFTING):
                "Engagement improved - no longer neglecting",
            (EngagementState.DISTANT, EngagementState.OUT_OF_ZONE):
                "5+ consecutive distant days - crisis mode",
            (EngagementState.OUT_OF_ZONE, EngagementState.CALIBRATING):
                "Recovery completed - starting fresh calibration",
        }
        return reasons.get(
            (from_state, to_state),
            f"Transition from {from_state.value} to {to_state.value}"
        )

    def _reset_counters(self) -> None:
        """Reset all consecutive counters."""
        self._consecutive_high_scores = 0
        self._consecutive_low_scores = 0
        self._consecutive_in_zone = 0
        self._consecutive_clingy_days = 0
        self._consecutive_distant_days = 0
        self._consecutive_recovery_scores = 0
        self._consecutive_good_days = 0

    def on_chapter_change(self, new_chapter: int) -> StateTransition:
        """Handle chapter transition - reset to CALIBRATING.

        Args:
            new_chapter: New chapter number

        Returns:
            StateTransition recording the reset
        """
        old_state = self._state
        score = Decimal("0.5")  # Neutral score for chapter change

        transition = StateTransition(
            from_state=old_state,
            to_state=EngagementState.CALIBRATING,
            reason=f"Chapter change to chapter {new_chapter} - resetting calibration",
            calibration_score=score,
        )

        self._state = EngagementState.CALIBRATING
        self._reset_counters()
        self._history.append(transition)

        return transition

    def get_history(self) -> list[StateTransition]:
        """Get list of state transitions.

        Returns:
            List of StateTransition objects
        """
        return list(self._history)
