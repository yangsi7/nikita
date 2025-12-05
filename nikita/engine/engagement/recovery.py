"""Recovery system for engagement model (spec 014).

This module handles recovery mechanics for unhealthy engagement states
and game over triggers when players fail to recover.

Recovery Actions:
- CLINGY: Give space for 24 hours (reduce message frequency)
- DISTANT: Engage meaningfully within 12 hours (quality messages)
- OUT_OF_ZONE: Complete recovery mission (48 hours)
- DRIFTING: Natural recovery through good engagement

Game Over Triggers:
- CLINGY for 7+ consecutive days → "nikita_dumped_clingy"
- DISTANT for 10+ consecutive days → "nikita_dumped_distant"
- OUT_OF_ZONE for 14+ days → "nikita_dumped_crisis"
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from nikita.config.enums import EngagementState

# Recovery duration requirements (hours)
RECOVERY_DURATIONS = {
    EngagementState.CLINGY: 24,       # Give space for 24 hours
    EngagementState.DISTANT: 12,      # Engage within 12 hours
    EngagementState.OUT_OF_ZONE: 48,  # Complete recovery mission
    EngagementState.DRIFTING: 6,      # Quick recovery possible
}

# Game over thresholds (consecutive days)
GAME_OVER_THRESHOLDS = {
    EngagementState.CLINGY: 7,        # 7 consecutive clingy days
    EngagementState.DISTANT: 10,      # 10 consecutive distant days
    EngagementState.OUT_OF_ZONE: 14,  # 14 days in crisis
    EngagementState.DRIFTING: None,   # Drifting doesn't trigger game over
    EngagementState.CALIBRATING: None,
    EngagementState.IN_ZONE: None,
}

# Recovery requirements
CLINGY_MAX_MESSAGES_24H = 5  # Max messages in 24h to prove giving space
DISTANT_MIN_MESSAGES = 5    # Min messages to show engagement
DISTANT_MIN_LENGTH = 40     # Min avg message length for meaningful engagement


@dataclass
class RecoveryAction:
    """Action required to recover from unhealthy state."""

    description: str
    duration_hours: int


@dataclass
class RecoveryCheckResult:
    """Result of checking if recovery is complete."""

    is_complete: bool
    reason: str = ""


@dataclass
class GameOverResult:
    """Result of checking if game over is triggered."""

    is_game_over: bool
    reason: str = ""
    days_remaining: int | None = None


# Recovery action descriptions
RECOVERY_ACTIONS = {
    EngagementState.CLINGY: RecoveryAction(
        description="Give Nikita space for 24 hours. Send fewer messages and wait for her responses.",
        duration_hours=24,
    ),
    EngagementState.DISTANT: RecoveryAction(
        description="Engage meaningfully within 12 hours. Send thoughtful messages that show you care.",
        duration_hours=12,
    ),
    EngagementState.OUT_OF_ZONE: RecoveryAction(
        description="Complete a recovery mission. Show Nikita you're committed by engaging consistently for 48 hours.",
        duration_hours=48,
    ),
    EngagementState.DRIFTING: RecoveryAction(
        description="Get back on track. A few good exchanges will help.",
        duration_hours=6,
    ),
}


class RecoveryManager:
    """Manages recovery mechanics for unhealthy engagement states.

    Responsibilities:
    - Provide recovery actions for each unhealthy state
    - Check if recovery is complete
    - Check if game over threshold is reached
    """

    def get_recovery_action(self, state: EngagementState) -> RecoveryAction | None:
        """Get required recovery action for given state.

        Args:
            state: Current engagement state

        Returns:
            RecoveryAction if state needs recovery, None for healthy states
        """
        # Healthy states don't need recovery
        if state in (EngagementState.CALIBRATING, EngagementState.IN_ZONE):
            return None

        return RECOVERY_ACTIONS.get(state)

    def check_recovery_complete(
        self,
        state: EngagementState,
        recovery_started_at: datetime,
        messages_since_recovery: int,
        avg_message_length: int = 0,
    ) -> RecoveryCheckResult:
        """Check if recovery requirements are met.

        Args:
            state: Current engagement state
            recovery_started_at: When recovery period started
            messages_since_recovery: Number of messages sent since recovery started
            avg_message_length: Average length of messages sent

        Returns:
            RecoveryCheckResult indicating if recovery is complete
        """
        now = datetime.now(timezone.utc)
        hours_elapsed = (now - recovery_started_at).total_seconds() / 3600

        # State-specific checks
        # Note: CLINGY requires waiting (grace period), but DISTANT/DRIFTING allow early completion
        if state == EngagementState.CLINGY:
            # CLINGY requires waiting out the full grace period
            required_duration = RECOVERY_DURATIONS.get(state, 24)
            if hours_elapsed < required_duration:
                return RecoveryCheckResult(
                    is_complete=False,
                    reason="Grace period not elapsed",
                )
            return self._check_clingy_recovery(messages_since_recovery)

        elif state == EngagementState.DISTANT:
            # DISTANT can complete early if engaged meaningfully
            return self._check_distant_recovery(messages_since_recovery, avg_message_length)

        elif state == EngagementState.OUT_OF_ZONE:
            # OUT_OF_ZONE requires waiting + engagement
            required_duration = RECOVERY_DURATIONS.get(state, 48)
            if hours_elapsed < required_duration:
                return RecoveryCheckResult(
                    is_complete=False,
                    reason="Grace period not elapsed",
                )
            return self._check_out_of_zone_recovery(messages_since_recovery, avg_message_length)

        elif state == EngagementState.DRIFTING:
            # Drifting recovers naturally with any engagement
            return RecoveryCheckResult(
                is_complete=messages_since_recovery > 0,
                reason="Engagement resumed" if messages_since_recovery > 0 else "No engagement",
            )

        return RecoveryCheckResult(is_complete=False, reason="Unknown state")

    def _check_clingy_recovery(self, messages: int) -> RecoveryCheckResult:
        """Check if clingy recovery is complete (gave space)."""
        if messages <= CLINGY_MAX_MESSAGES_24H:
            return RecoveryCheckResult(
                is_complete=True,
                reason="Successfully gave Nikita space",
            )
        return RecoveryCheckResult(
            is_complete=False,
            reason=f"Too many messages ({messages}). Need to give more space.",
        )

    def _check_distant_recovery(self, messages: int, avg_length: int) -> RecoveryCheckResult:
        """Check if distant recovery is complete (engaged meaningfully)."""
        if messages < DISTANT_MIN_MESSAGES:
            return RecoveryCheckResult(
                is_complete=False,
                reason=f"Not enough messages ({messages}). Need {DISTANT_MIN_MESSAGES}+.",
            )
        if avg_length < DISTANT_MIN_LENGTH:
            return RecoveryCheckResult(
                is_complete=False,
                reason=f"Messages too short ({avg_length} avg). Need {DISTANT_MIN_LENGTH}+ chars.",
            )
        return RecoveryCheckResult(
            is_complete=True,
            reason="Successfully re-engaged with meaningful messages",
        )

    def _check_out_of_zone_recovery(self, messages: int, avg_length: int) -> RecoveryCheckResult:
        """Check if out of zone recovery is complete."""
        # Requires both decent volume and quality
        if messages < DISTANT_MIN_MESSAGES * 2:
            return RecoveryCheckResult(
                is_complete=False,
                reason=f"Need more engagement ({messages}/{DISTANT_MIN_MESSAGES * 2} messages)",
            )
        if avg_length < DISTANT_MIN_LENGTH:
            return RecoveryCheckResult(
                is_complete=False,
                reason=f"Messages too short ({avg_length}/{DISTANT_MIN_LENGTH} avg chars)",
            )
        return RecoveryCheckResult(
            is_complete=True,
            reason="Successfully completed recovery mission",
        )

    def check_point_of_no_return(
        self,
        state: EngagementState,
        consecutive_days: int,
    ) -> GameOverResult:
        """Check if game over threshold is reached.

        Args:
            state: Current engagement state
            consecutive_days: Days in this state

        Returns:
            GameOverResult indicating if game over is triggered
        """
        threshold = GAME_OVER_THRESHOLDS.get(state)

        # Healthy states never trigger game over
        if threshold is None:
            return GameOverResult(
                is_game_over=False,
                reason="",
                days_remaining=None,
            )

        days_remaining = threshold - consecutive_days

        if consecutive_days >= threshold:
            reason = self._get_game_over_reason(state)
            return GameOverResult(
                is_game_over=True,
                reason=reason,
                days_remaining=0,
            )

        return GameOverResult(
            is_game_over=False,
            reason="",
            days_remaining=max(0, days_remaining),
        )

    def _get_game_over_reason(self, state: EngagementState) -> str:
        """Get game over reason string for state."""
        reasons = {
            EngagementState.CLINGY: "nikita_dumped_clingy",
            EngagementState.DISTANT: "nikita_dumped_distant",
            EngagementState.OUT_OF_ZONE: "nikita_dumped_crisis",
        }
        return reasons.get(state, "nikita_dumped_unknown")
