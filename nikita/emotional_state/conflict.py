"""Conflict Detection for Emotional State Engine (Spec 023, T011-T013).

Detects conflict states based on emotional dimensions and behavioral patterns.

AC-T011: ConflictDetector class with threshold maps
AC-T012: Trigger threshold detection (passive-aggressive, cold, vulnerable, explosive)
AC-T013: Conflict state transitions (escalation/de-escalation paths)
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from nikita.emotional_state.models import (
    ConflictState,
    EmotionalStateModel,
)

logger = logging.getLogger(__name__)

# Spec 101 FR-004: EXPLOSIVE conflict auto de-escalation timeout (hours)
EXPLOSIVE_TIMEOUT_HOURS: int = 6


class ConflictDetector:
    """Detects and manages conflict state transitions.

    Conflict states:
    - NONE: Normal state
    - PASSIVE_AGGRESSIVE: Subtle upset (ignored messages)
    - COLD: Emotionally distant (low valence)
    - VULNERABLE: Hurt and sensitive (intimacy drop)
    - EXPLOSIVE: Very upset (high arousal + low valence)

    Transitions follow escalation/de-escalation paths:
    - Cannot jump directly to explosive (must escalate)
    - Recovery requires positive interactions
    """

    # Threshold triggers for conflict states
    # AC-T012: Trigger threshold detection
    THRESHOLDS = {
        # AC-T012.1: Passive-aggressive: 2+ ignored messages
        "passive_aggressive": {
            "ignored_messages": 2,
        },
        # AC-T012.2: Cold: valence < 0.3
        "cold": {
            "valence_max": 0.3,
        },
        # AC-T012.3: Vulnerable: intimacy drop > 0.2
        "vulnerable": {
            "intimacy_drop": 0.2,
        },
        # AC-T012.4: Explosive: arousal > 0.8 + valence < 0.3
        "explosive": {
            "arousal_min": 0.8,
            "valence_max": 0.3,
        },
    }

    # Valid state transitions (escalation and de-escalation)
    # AC-T013: State transitions
    VALID_TRANSITIONS: dict[ConflictState, list[ConflictState]] = {
        # From NONE
        ConflictState.NONE: [
            ConflictState.PASSIVE_AGGRESSIVE,
            ConflictState.COLD,
            ConflictState.VULNERABLE,
        ],
        # From PASSIVE_AGGRESSIVE
        ConflictState.PASSIVE_AGGRESSIVE: [
            ConflictState.NONE,  # De-escalation
            ConflictState.COLD,  # Escalation
            ConflictState.VULNERABLE,  # Different path
        ],
        # From COLD
        ConflictState.COLD: [
            ConflictState.NONE,  # De-escalation
            ConflictState.PASSIVE_AGGRESSIVE,  # Different path
            ConflictState.EXPLOSIVE,  # Escalation (only from cold)
        ],
        # From VULNERABLE
        ConflictState.VULNERABLE: [
            ConflictState.NONE,  # De-escalation
            ConflictState.COLD,  # Escalation
            ConflictState.EXPLOSIVE,  # Escalation (only if also cold)
        ],
        # From EXPLOSIVE
        ConflictState.EXPLOSIVE: [
            ConflictState.COLD,  # De-escalation (must go through cold)
            ConflictState.VULNERABLE,  # De-escalation path
        ],
    }

    # Severity order for escalation checks
    SEVERITY_ORDER = [
        ConflictState.NONE,
        ConflictState.PASSIVE_AGGRESSIVE,
        ConflictState.COLD,
        ConflictState.VULNERABLE,
        ConflictState.EXPLOSIVE,
    ]

    # Spec 104 Story 6: Attachment-style threshold modifiers
    ATTACHMENT_EXPLOSIVE_MODIFIER: dict[str, float] = {
        "anxious": -0.1,       # Lower arousal threshold -> easier to go explosive
        "avoidant": 0.0,
        "secure": 0.0,
        "disorganized": 0.0,
    }
    ATTACHMENT_COLD_MODIFIER: dict[str, float] = {
        "anxious": 0.0,
        "avoidant": -0.1,      # Lower valence threshold -> harder to exit cold
        "secure": 0.0,
        "disorganized": 0.0,
    }

    def __init__(self) -> None:
        """Initialize ConflictDetector."""
        pass

    def detect_conflict_state(
        self,
        state: EmotionalStateModel,
        previous_state: EmotionalStateModel | None = None,
        attachment_style: str | None = None,
    ) -> ConflictState:
        """Detect if a conflict state should be triggered.

        AC-T011.2: detect_conflict_state() method
        AC-T011.3: Supports 4 conflict states

        Args:
            state: Current emotional state.
            previous_state: Previous state for delta calculations.
            attachment_style: Optional attachment style ('anxious', 'avoidant', 'secure', 'disorganized').

        Returns:
            Detected ConflictState.
        """
        # Check triggers in severity order (lowest to highest)
        detected = ConflictState.NONE

        # Check passive-aggressive (ignored messages)
        if state.ignored_message_count >= self.THRESHOLDS["passive_aggressive"]["ignored_messages"]:
            detected = ConflictState.PASSIVE_AGGRESSIVE
            logger.debug(f"Passive-aggressive detected: {state.ignored_message_count} ignored messages")

        # Check cold (low valence)
        if state.valence < self.THRESHOLDS["cold"]["valence_max"]:
            # Cold is more severe than passive-aggressive
            if self._get_severity(ConflictState.COLD) > self._get_severity(detected):
                detected = ConflictState.COLD
                logger.debug(f"Cold detected: valence={state.valence:.2f}")

        # Check vulnerable (intimacy drop)
        if previous_state:
            intimacy_drop = previous_state.intimacy - state.intimacy
            if intimacy_drop >= self.THRESHOLDS["vulnerable"]["intimacy_drop"]:
                # Vulnerable has same severity as cold
                if self._get_severity(ConflictState.VULNERABLE) >= self._get_severity(detected):
                    detected = ConflictState.VULNERABLE
                    logger.debug(f"Vulnerable detected: intimacy drop={intimacy_drop:.2f}")

        # Check explosive (high arousal + low valence)
        explosive_thresh = self.THRESHOLDS["explosive"]
        explosive_arousal_min = explosive_thresh["arousal_min"]
        if attachment_style:
            explosive_arousal_min += self.ATTACHMENT_EXPLOSIVE_MODIFIER.get(
                attachment_style, 0.0
            )
        if (
            state.arousal >= explosive_arousal_min
            and state.valence < explosive_thresh["valence_max"]
        ):
            # Explosive is highest severity, but must validate transition
            current_conflict = state.conflict_state
            if self._can_transition(current_conflict, ConflictState.EXPLOSIVE):
                detected = ConflictState.EXPLOSIVE
                logger.debug(
                    f"Explosive detected: arousal={state.arousal:.2f}, "
                    f"valence={state.valence:.2f}"
                )

        return detected

    def can_transition_to(
        self,
        current_state: ConflictState,
        target_state: ConflictState,
    ) -> bool:
        """Check if transition to target state is valid.

        AC-T013.2: Cannot jump from None to explosive (must escalate)
        AC-T013.3: De-escalation paths defined

        Args:
            current_state: Current conflict state.
            target_state: Desired target state.

        Returns:
            True if transition is valid.
        """
        return self._can_transition(current_state, target_state)

    def _can_transition(
        self,
        current: ConflictState,
        target: ConflictState,
    ) -> bool:
        """Internal transition validation."""
        if current == target:
            return True  # No change

        valid_targets = self.VALID_TRANSITIONS.get(current, [])
        return target in valid_targets

    def _get_severity(self, state: ConflictState) -> int:
        """Get severity level for a conflict state."""
        try:
            return self.SEVERITY_ORDER.index(state)
        except ValueError:
            return 0

    def apply_transition(
        self,
        state: EmotionalStateModel,
        target: ConflictState,
        trigger: str | None = None,
    ) -> EmotionalStateModel:
        """Apply a conflict state transition if valid.

        Args:
            state: Current emotional state.
            target: Target conflict state.
            trigger: What triggered the transition.

        Returns:
            Updated EmotionalStateModel with new conflict state.

        Raises:
            ValueError: If transition is invalid.
        """
        if not self._can_transition(state.conflict_state, target):
            raise ValueError(
                f"Invalid transition from {state.conflict_state.value} "
                f"to {target.value}"
            )

        return state.set_conflict(target, trigger)

    def check_escalation(
        self,
        state: EmotionalStateModel,
        previous_state: EmotionalStateModel | None = None,
    ) -> tuple[bool, ConflictState | None, str | None]:
        """Check if conflict should escalate based on state.

        Args:
            state: Current emotional state.
            previous_state: Previous state for comparison.

        Returns:
            Tuple of (should_escalate, target_state, trigger_reason).
        """
        detected = self.detect_conflict_state(state, previous_state)

        # No escalation needed
        if detected == ConflictState.NONE:
            return False, None, None

        # Check if we need to escalate
        current = state.conflict_state
        if detected == current:
            return False, None, None

        # Validate transition
        if not self._can_transition(current, detected):
            # Find intermediate state
            intermediate = self._find_intermediate_state(current, detected)
            if intermediate:
                trigger = self._get_trigger_reason(state, intermediate)
                return True, intermediate, trigger
            return False, None, None

        trigger = self._get_trigger_reason(state, detected)
        return True, detected, trigger

    def check_de_escalation(
        self,
        state: EmotionalStateModel,
        positive_interaction: bool = False,
    ) -> tuple[bool, ConflictState | None, str | None]:
        """Check if conflict should de-escalate.

        Args:
            state: Current emotional state.
            positive_interaction: Whether a positive interaction occurred.

        Returns:
            Tuple of (should_de_escalate, target_state, reason).
        """
        current = state.conflict_state

        if current == ConflictState.NONE:
            return False, None, None

        # Check de-escalation conditions
        should_de_escalate = False
        target = None
        reason = None

        if current == ConflictState.EXPLOSIVE:
            # Spec 101 FR-004: Auto de-escalation after timeout
            if (
                state.conflict_started_at is not None
                and (datetime.now(timezone.utc) - state.conflict_started_at)
                >= timedelta(hours=EXPLOSIVE_TIMEOUT_HOURS)
            ):
                target = ConflictState.COLD
                reason = "Explosive timeout — auto de-escalation after 6h"
                should_de_escalate = True
            # Explosive can only go to cold or vulnerable
            elif state.valence >= 0.4 or positive_interaction:
                target = ConflictState.COLD
                reason = "Calming down from explosive"
                should_de_escalate = True

        elif current == ConflictState.COLD:
            if state.valence >= 0.4 and positive_interaction:
                target = ConflictState.NONE
                reason = "Warmed up from positive interaction"
                should_de_escalate = True

        elif current == ConflictState.VULNERABLE:
            if state.intimacy >= 0.5 and positive_interaction:
                target = ConflictState.NONE
                reason = "Feeling supported"
                should_de_escalate = True

        elif current == ConflictState.PASSIVE_AGGRESSIVE:
            if state.ignored_message_count == 0 and positive_interaction:
                target = ConflictState.NONE
                reason = "Engagement restored"
                should_de_escalate = True

        return should_de_escalate, target, reason

    def _find_intermediate_state(
        self,
        current: ConflictState,
        target: ConflictState,
    ) -> ConflictState | None:
        """Find intermediate state for invalid direct transition."""
        current_sev = self._get_severity(current)
        target_sev = self._get_severity(target)

        if target_sev > current_sev:
            # Escalation - find next step
            valid = self.VALID_TRANSITIONS.get(current, [])
            for state in self.SEVERITY_ORDER[current_sev + 1:]:
                if state in valid:
                    return state
        else:
            # De-escalation - find previous step
            valid = self.VALID_TRANSITIONS.get(current, [])
            for state in reversed(self.SEVERITY_ORDER[:current_sev]):
                if state in valid:
                    return state

        return None

    def _get_trigger_reason(
        self,
        state: EmotionalStateModel,
        target: ConflictState,
    ) -> str:
        """Get human-readable trigger reason for transition."""
        if target == ConflictState.PASSIVE_AGGRESSIVE:
            return f"Ignored messages ({state.ignored_message_count})"
        elif target == ConflictState.COLD:
            return f"Low mood (valence: {state.valence:.2f})"
        elif target == ConflictState.VULNERABLE:
            return "Intimacy drop detected"
        elif target == ConflictState.EXPLOSIVE:
            return f"High tension (arousal: {state.arousal:.2f}, valence: {state.valence:.2f})"
        return "Unknown trigger"


# Singleton
_detector_instance: ConflictDetector | None = None


def get_conflict_detector() -> ConflictDetector:
    """Get singleton ConflictDetector instance."""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = ConflictDetector()
    return _detector_instance
