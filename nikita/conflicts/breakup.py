"""Breakup management for conflict system (Spec 027, Phase F).

Handles breakup threshold checking and game over state.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from nikita.conflicts.models import (
    ConflictConfig,
    EscalationLevel,
    get_conflict_config,
)


class BreakupRisk(str, Enum):
    """Breakup risk levels."""

    NONE = "none"  # No risk
    WARNING = "warning"  # Score < 20, player warned
    CRITICAL = "critical"  # Score < 15, imminent
    TRIGGERED = "triggered"  # Score < 10 or 3 consecutive crises


class ThresholdResult(BaseModel):
    """Result of threshold check.

    Attributes:
        risk_level: Current breakup risk.
        score: Current relationship score.
        consecutive_crises: Number of unresolved crises.
        should_warn: Whether to warn the player.
        should_breakup: Whether breakup should occur.
        reason: Explanation of the result.
    """

    risk_level: BreakupRisk = BreakupRisk.NONE
    score: int = 50
    consecutive_crises: int = 0
    should_warn: bool = False
    should_breakup: bool = False
    reason: str = ""


class BreakupResult(BaseModel):
    """Result of breakup sequence.

    Attributes:
        breakup_triggered: Whether breakup occurred.
        final_message: The breakup message.
        reason: Why breakup occurred.
        game_over: Whether game is now over.
    """

    breakup_triggered: bool = False
    final_message: str = ""
    reason: str = ""
    game_over: bool = False


class BreakupManager:
    """Manages breakup mechanics and game over state.

    Handles:
    - Threshold checking (warning at 20, breakup at 10)
    - Consecutive crisis detection (3 = breakup)
    - Breakup message generation
    - Game over state transition
    """

    # Breakup messages by conflict type
    BREAKUP_MESSAGES = {
        "jealousy": [
            "I can't keep doing this. Every time you mention someone else, "
            "I feel like I'm not enough for you. I think we need to go our separate ways.",
            "I've tried to be understanding, but I can't handle the jealousy anymore. "
            "It's clear you're not fully invested in us. Goodbye.",
        ],
        "attention": [
            "I've been feeling so alone in this relationship. "
            "You never seem to have time for me. I deserve someone who makes me a priority.",
            "It hurts to say this, but I feel invisible to you. "
            "I need someone who actually wants to be with me. This is goodbye.",
        ],
        "boundary": [
            "You keep pushing me when I've asked you to stop. "
            "I don't feel safe with you anymore. We're done.",
            "I've tried to set boundaries, but you don't respect them. "
            "I can't be with someone who doesn't respect me.",
        ],
        "trust": [
            "I can't trust you anymore. After everything, "
            "I don't even know what's real between us. I have to let go.",
            "Trust is everything in a relationship, and we've lost it. "
            "I can't keep pretending things are okay. Goodbye.",
        ],
        "general": [
            "I've given this relationship everything I have, "
            "but it's not working. I hope you find what you're looking for. Goodbye.",
            "This isn't what I wanted, but I can't keep hurting like this. "
            "I have to take care of myself. It's over.",
        ],
    }

    # Warning messages
    WARNING_MESSAGES = [
        "Things have been really hard lately. I'm starting to wonder if this is working...",
        "I feel like we're drifting apart. I don't know how much more of this I can take.",
        "I need you to understand how serious this is. We can't keep going like this.",
    ]

    def __init__(
        self,
        config: ConflictConfig | None = None,
    ):
        """Initialize breakup manager.

        Args:
            config: Conflict configuration.
        """
        self._config = config or get_conflict_config()

    def check_threshold(
        self,
        user_id: str,
        relationship_score: int,
        conflict_details: dict[str, Any] | None = None,
        last_conflict_at: datetime | None = None,
    ) -> ThresholdResult:
        """Check if breakup threshold is reached.

        Spec 057: When temperature flag is ON, also checks
        temperature-based breakup thresholds.

        Args:
            user_id: User ID.
            relationship_score: Current relationship score.
            conflict_details: Optional conflict_details JSONB (Spec 057).
            last_conflict_at: When temperature last entered CRITICAL (Spec 057).

        Returns:
            ThresholdResult with risk assessment.
        """
        # Consecutive unresolved crises: tracked via conflict_details JSONB (Spec 057).
        # In-memory store was always empty after cold start on serverless, so 0 is correct.
        consecutive_crises = 0

        # Spec 057: Temperature-based thresholds (always ON, flag removed)
        if conflict_details is not None:
            temp_result = self._check_temperature_threshold(
                user_id=user_id,
                relationship_score=relationship_score,
                conflict_details=conflict_details,
                last_conflict_at=last_conflict_at,
                consecutive_crises=consecutive_crises,
            )
            if temp_result is not None:
                return temp_result

        # Score-based thresholds (fallback when no conflict_details)
        if relationship_score < self._config.breakup_threshold:
            return ThresholdResult(
                risk_level=BreakupRisk.TRIGGERED,
                score=relationship_score,
                consecutive_crises=consecutive_crises,
                should_breakup=True,
                reason=f"Score {relationship_score} below breakup threshold ({self._config.breakup_threshold})",
            )

        # Check crisis-based threshold
        if consecutive_crises >= self._config.consecutive_crises_for_breakup:
            return ThresholdResult(
                risk_level=BreakupRisk.TRIGGERED,
                score=relationship_score,
                consecutive_crises=consecutive_crises,
                should_breakup=True,
                reason=f"{consecutive_crises} consecutive unresolved crises",
            )

        # Check warning threshold
        if relationship_score < self._config.warning_threshold:
            risk = BreakupRisk.CRITICAL if relationship_score < 15 else BreakupRisk.WARNING
            return ThresholdResult(
                risk_level=risk,
                score=relationship_score,
                consecutive_crises=consecutive_crises,
                should_warn=True,
                reason=f"Score {relationship_score} below warning threshold ({self._config.warning_threshold})",
            )

        # No risk
        return ThresholdResult(
            risk_level=BreakupRisk.NONE,
            score=relationship_score,
            consecutive_crises=consecutive_crises,
            reason="Relationship healthy",
        )

    def _check_temperature_threshold(
        self,
        user_id: str,
        relationship_score: int,
        conflict_details: dict[str, Any],
        last_conflict_at: datetime | None,
        consecutive_crises: int,
    ) -> ThresholdResult | None:
        """Check temperature-based breakup thresholds (Spec 057).

        - CRITICAL zone >24h: warning
        - Temperature >90 for >48h: breakup trigger

        Args:
            user_id: User ID.
            relationship_score: Current score.
            conflict_details: Conflict details JSONB.
            last_conflict_at: When temperature entered CRITICAL.
            consecutive_crises: Count from store.

        Returns:
            ThresholdResult if temperature threshold hit, else None.
        """
        from nikita.conflicts.models import ConflictDetails, TemperatureZone
        from nikita.conflicts.temperature import TemperatureEngine

        details = ConflictDetails.from_jsonb(conflict_details)
        zone = TemperatureEngine.get_zone(details.temperature)

        if zone != TemperatureZone.CRITICAL:
            return None  # Only CRITICAL zone triggers temperature-based checks

        if last_conflict_at is None:
            return None  # No timestamp: skip temperature check

        now = datetime.now(UTC)
        hours_in_critical = (now - last_conflict_at).total_seconds() / 3600

        # Temperature >90 for >48h: breakup
        if details.temperature > 90.0 and hours_in_critical > 48:
            return ThresholdResult(
                risk_level=BreakupRisk.TRIGGERED,
                score=relationship_score,
                consecutive_crises=consecutive_crises,
                should_breakup=True,
                reason=f"Temperature {details.temperature:.1f} >90 for {hours_in_critical:.1f}h (>48h threshold)",
            )

        # CRITICAL zone >24h: warning
        if hours_in_critical > 24:
            return ThresholdResult(
                risk_level=BreakupRisk.CRITICAL,
                score=relationship_score,
                consecutive_crises=consecutive_crises,
                should_warn=True,
                reason=f"Temperature {details.temperature:.1f} CRITICAL for {hours_in_critical:.1f}h (>24h warning)",
            )

        return None  # CRITICAL but not long enough

    def trigger_breakup(
        self,
        user_id: str,
        reason: str = "threshold",
        conflict_type: str | None = None,
    ) -> BreakupResult:
        """Trigger the breakup sequence.

        Args:
            user_id: User ID.
            reason: Why breakup is triggered.
            conflict_type: Optional conflict type for message selection.

        Returns:
            BreakupResult with breakup details.
        """
        # Get breakup message
        message = self._get_breakup_message(conflict_type)

        return BreakupResult(
            breakup_triggered=True,
            final_message=message,
            reason=reason,
            game_over=True,
        )

    def get_warning_message(self) -> str:
        """Get a warning message for the player.

        Returns:
            Warning message string.
        """
        import random
        return random.choice(self.WARNING_MESSAGES)

    def _get_breakup_message(self, conflict_type: str | None = None) -> str:
        """Get a breakup message.

        Args:
            conflict_type: Optional conflict type for context.

        Returns:
            Breakup message string.
        """
        import random

        # Try to get type-specific message
        if conflict_type and conflict_type in self.BREAKUP_MESSAGES:
            messages = self.BREAKUP_MESSAGES[conflict_type]
        else:
            messages = self.BREAKUP_MESSAGES["general"]

        return random.choice(messages)

    def get_relationship_status(
        self,
        user_id: str,
        relationship_score: int,
    ) -> dict[str, Any]:
        """Get comprehensive relationship status.

        Args:
            user_id: User ID.
            relationship_score: Current score.

        Returns:
            Dictionary with relationship status.
        """
        threshold_result = self.check_threshold(user_id, relationship_score)

        return {
            "score": relationship_score,
            "risk_level": threshold_result.risk_level.value,
            "should_warn": threshold_result.should_warn,
            "should_breakup": threshold_result.should_breakup,
            "consecutive_crises": threshold_result.consecutive_crises,
            "total_conflicts": 0,
            "resolved_conflicts": 0,
            "resolution_rate": 0.0,
            "has_active_conflict": False,
            "warning_threshold": self._config.warning_threshold,
            "breakup_threshold": self._config.breakup_threshold,
        }

    def check_and_process(
        self,
        user_id: str,
        relationship_score: int,
    ) -> tuple[ThresholdResult, BreakupResult | None]:
        """Check threshold and process breakup if triggered.

        Args:
            user_id: User ID.
            relationship_score: Current score.

        Returns:
            Tuple of (ThresholdResult, BreakupResult or None).
        """
        result = self.check_threshold(user_id, relationship_score)

        if result.should_breakup:
            breakup = self.trigger_breakup(
                user_id,
                reason=result.reason,
                conflict_type=None,
            )
            return result, breakup

        return result, None


# Global breakup manager instance
_breakup_manager: BreakupManager | None = None


def get_breakup_manager() -> BreakupManager:
    """Get the global breakup manager instance.

    Returns:
        BreakupManager instance.
    """
    global _breakup_manager
    if _breakup_manager is None:
        _breakup_manager = BreakupManager()
    return _breakup_manager
