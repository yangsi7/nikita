"""Escalation management for conflict system (Spec 027, Phase D).

Handles conflict escalation timeline and natural resolution.
"""

import random
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field

from nikita.conflicts.models import (
    ActiveConflict,
    ConflictConfig,
    EscalationLevel,
    ResolutionType,
    get_conflict_config,
)
from nikita.conflicts.store import ConflictStore, get_conflict_store


class EscalationResult(BaseModel):
    """Result of escalation check.

    Attributes:
        escalated: Whether escalation occurred.
        new_level: New escalation level (if escalated).
        naturally_resolved: Whether conflict resolved naturally.
        time_until_escalation: Time until next escalation (if applicable).
    """

    escalated: bool = False
    new_level: EscalationLevel | None = None
    naturally_resolved: bool = False
    time_until_escalation: timedelta | None = None
    reason: str = ""


class EscalationManager:
    """Manages conflict escalation and natural resolution.

    Handles:
    - Time-based escalation (Level 1→2: 2-6h, Level 2→3: 12-24h)
    - Natural resolution probability (30% L1, 10% L2, 0% L3)
    - Acknowledgment-based reset
    """

    def __init__(
        self,
        store: ConflictStore | None = None,
        config: ConflictConfig | None = None,
    ):
        """Initialize escalation manager.

        Args:
            store: ConflictStore for persistence.
            config: Conflict configuration.
        """
        self._store = store or get_conflict_store()
        self._config = config or get_conflict_config()

    def check_escalation(
        self,
        conflict: ActiveConflict,
        conflict_details: dict[str, Any] | None = None,
    ) -> EscalationResult:
        """Check if a conflict should escalate or resolve.

        Spec 057: When temperature flag is ON, uses temperature zones
        for escalation decisions. HOT=DIRECT, CRITICAL=CRISIS.

        Args:
            conflict: The conflict to check.
            conflict_details: Optional conflict_details JSONB (Spec 057).

        Returns:
            EscalationResult with outcomes.
        """
        if conflict.resolved:
            return EscalationResult(reason="Conflict already resolved")

        # Spec 057: Temperature-based escalation
        from nikita.conflicts import is_conflict_temperature_enabled

        if is_conflict_temperature_enabled() and conflict_details is not None:
            return self._check_escalation_with_temperature(conflict, conflict_details)

        # Check for natural resolution first
        if self._check_natural_resolution(conflict):
            self._store.resolve_conflict(
                conflict.conflict_id,
                ResolutionType.NATURAL,
            )
            return EscalationResult(
                naturally_resolved=True,
                reason="Conflict resolved naturally",
            )

        # Check escalation timeline
        time_in_level = self._get_time_in_level(conflict)
        escalation_threshold = self._get_escalation_threshold(conflict.escalation_level)

        if escalation_threshold is None:
            # At max level (CRISIS), no further escalation
            return EscalationResult(reason="At maximum escalation level")

        if time_in_level >= escalation_threshold:
            # Escalate
            new_level = self._get_next_level(conflict.escalation_level)
            if new_level:
                self._store.escalate_conflict(conflict.conflict_id, new_level)
                return EscalationResult(
                    escalated=True,
                    new_level=new_level,
                    reason=f"Escalated to {new_level.name}",
                )

        # Not yet time to escalate
        time_remaining = escalation_threshold - time_in_level
        return EscalationResult(
            time_until_escalation=time_remaining,
            reason=f"Escalation in {time_remaining.total_seconds() / 3600:.1f} hours",
        )

    def _check_escalation_with_temperature(
        self,
        conflict: ActiveConflict,
        conflict_details: dict[str, Any],
    ) -> EscalationResult:
        """Temperature-based escalation check (Spec 057).

        Zone mapping:
        - CALM/WARM: Natural resolution possible
        - HOT: Equivalent to DIRECT escalation level
        - CRITICAL: Equivalent to CRISIS escalation level

        Args:
            conflict: The conflict.
            conflict_details: Conflict details JSONB.

        Returns:
            EscalationResult.
        """
        from nikita.conflicts.models import ConflictDetails, TemperatureZone
        from nikita.conflicts.temperature import TemperatureEngine

        details = ConflictDetails.from_jsonb(conflict_details)
        zone = TemperatureEngine.get_zone(details.temperature)

        # CALM/WARM zones: try natural resolution
        if zone in (TemperatureZone.CALM, TemperatureZone.WARM):
            if self._check_natural_resolution(conflict):
                self._store.resolve_conflict(conflict.conflict_id, ResolutionType.NATURAL)
                return EscalationResult(
                    naturally_resolved=True,
                    reason=f"Temperature {details.temperature:.1f} ({zone.value}) — resolved naturally",
                )
            return EscalationResult(
                reason=f"Temperature {details.temperature:.1f} ({zone.value}) — no escalation",
            )

        # HOT zone: equivalent to DIRECT
        if zone == TemperatureZone.HOT:
            target_level = EscalationLevel.DIRECT
            if conflict.escalation_level.value < target_level.value:
                self._store.escalate_conflict(conflict.conflict_id, target_level)
                return EscalationResult(
                    escalated=True,
                    new_level=target_level,
                    reason=f"Temperature {details.temperature:.1f} (HOT) — escalated to DIRECT",
                )
            return EscalationResult(
                reason=f"Temperature {details.temperature:.1f} (HOT) — already at {conflict.escalation_level.name}",
            )

        # CRITICAL zone: equivalent to CRISIS
        target_level = EscalationLevel.CRISIS
        if conflict.escalation_level.value < target_level.value:
            self._store.escalate_conflict(conflict.conflict_id, target_level)
            return EscalationResult(
                escalated=True,
                new_level=target_level,
                reason=f"Temperature {details.temperature:.1f} (CRITICAL) — escalated to CRISIS",
            )
        return EscalationResult(
            reason=f"Temperature {details.temperature:.1f} (CRITICAL) — already at CRISIS",
        )

    def escalate(self, conflict: ActiveConflict) -> EscalationResult:
        """Force escalation of a conflict.

        Args:
            conflict: The conflict to escalate.

        Returns:
            EscalationResult with new level.
        """
        if conflict.resolved:
            return EscalationResult(reason="Cannot escalate resolved conflict")

        new_level = self._get_next_level(conflict.escalation_level)
        if not new_level:
            return EscalationResult(reason="Already at maximum level")

        self._store.escalate_conflict(conflict.conflict_id, new_level)
        return EscalationResult(
            escalated=True,
            new_level=new_level,
            reason=f"Force escalated to {new_level.name}",
        )

    def acknowledge(
        self,
        conflict: ActiveConflict,
        conflict_details: dict[str, Any] | None = None,
    ) -> bool | dict[str, Any]:
        """Handle user acknowledgment of conflict.

        Resets the escalation timer but doesn't resolve.
        Spec 057: Also reduces temperature by 5-10 points when flag ON.

        Args:
            conflict: The conflict being acknowledged.
            conflict_details: Optional conflict_details JSONB (Spec 057).

        Returns:
            True if acknowledged (flag OFF), or updated conflict_details dict (flag ON).
            False if already resolved.
        """
        if conflict.resolved:
            return False

        # Reset escalation timer by updating last_escalated
        self._store.update_conflict(
            conflict.conflict_id,
            last_escalated=datetime.now(UTC),
        )

        # Increment resolution attempts
        self._store.increment_resolution_attempts(conflict.conflict_id)

        # Spec 057: Reduce temperature on acknowledgment
        from nikita.conflicts import is_conflict_temperature_enabled

        if is_conflict_temperature_enabled() and conflict_details is not None:
            from nikita.conflicts.models import ConflictDetails
            from nikita.conflicts.temperature import TemperatureEngine

            details = ConflictDetails.from_jsonb(conflict_details)
            # Reduce temperature by 5-10 based on escalation level
            reduction = {
                EscalationLevel.SUBTLE: 10.0,
                EscalationLevel.DIRECT: 7.0,
                EscalationLevel.CRISIS: 5.0,
            }.get(conflict.escalation_level, 7.0)

            details = TemperatureEngine.update_conflict_details(
                details=details,
                temp_delta=-reduction,
            )
            return details.to_jsonb()

        return True

    def _check_natural_resolution(self, conflict: ActiveConflict) -> bool:
        """Check if conflict resolves naturally.

        Args:
            conflict: The conflict to check.

        Returns:
            True if should resolve naturally.
        """
        level = conflict.escalation_level
        probability = self._get_natural_resolution_probability(level)

        if probability <= 0:
            return False

        # Only check once per escalation check (using time-based seed)
        # This prevents repeated random checks from eventually succeeding
        time_in_level = self._get_time_in_level(conflict)
        hours_in_level = time_in_level.total_seconds() / 3600

        # Check once per hour spent in level
        check_count = int(hours_in_level)
        if check_count < 1:
            return False

        # Use deterministic seed based on conflict and hour
        seed = hash(f"{conflict.conflict_id}:{check_count}")
        rng = random.Random(seed)

        return rng.random() < probability

    def _get_natural_resolution_probability(self, level: EscalationLevel) -> float:
        """Get natural resolution probability for a level.

        Args:
            level: Escalation level.

        Returns:
            Probability (0.0-1.0).
        """
        if level == EscalationLevel.SUBTLE:
            return self._config.natural_resolution_probability_level_1
        elif level == EscalationLevel.DIRECT:
            return self._config.natural_resolution_probability_level_2
        else:  # CRISIS
            return self._config.natural_resolution_probability_level_3

    def _get_time_in_level(self, conflict: ActiveConflict) -> timedelta:
        """Get time spent in current escalation level.

        Args:
            conflict: The conflict.

        Returns:
            Time in current level.
        """
        reference_time = conflict.last_escalated or conflict.triggered_at
        return datetime.now(UTC) - reference_time

    def _get_escalation_threshold(self, level: EscalationLevel) -> timedelta | None:
        """Get escalation threshold for a level.

        Args:
            level: Current escalation level.

        Returns:
            Time threshold for escalation, None if at max.
        """
        if level == EscalationLevel.SUBTLE:
            min_hours, max_hours = self._config.escalation_time_subtle_to_direct_hours
            # Use middle of range for deterministic behavior
            hours = (min_hours + max_hours) / 2
            return timedelta(hours=hours)
        elif level == EscalationLevel.DIRECT:
            min_hours, max_hours = self._config.escalation_time_direct_to_crisis_hours
            hours = (min_hours + max_hours) / 2
            return timedelta(hours=hours)
        else:  # CRISIS
            return None  # No further escalation

    def _get_next_level(self, current: EscalationLevel) -> EscalationLevel | None:
        """Get the next escalation level.

        Args:
            current: Current level.

        Returns:
            Next level or None if at max.
        """
        if current == EscalationLevel.SUBTLE:
            return EscalationLevel.DIRECT
        elif current == EscalationLevel.DIRECT:
            return EscalationLevel.CRISIS
        else:
            return None

    def get_escalation_timeline(self, conflict: ActiveConflict) -> dict[str, Any]:
        """Get the full escalation timeline for a conflict.

        Args:
            conflict: The conflict.

        Returns:
            Dictionary with timeline information.
        """
        if conflict.resolved:
            return {
                "status": "resolved",
                "resolution_type": conflict.resolution_type.value if conflict.resolution_type else None,
            }

        time_in_level = self._get_time_in_level(conflict)
        threshold = self._get_escalation_threshold(conflict.escalation_level)

        return {
            "status": "active",
            "current_level": conflict.escalation_level.name,
            "current_level_value": conflict.escalation_level.value,
            "time_in_level_hours": time_in_level.total_seconds() / 3600,
            "escalation_threshold_hours": threshold.total_seconds() / 3600 if threshold else None,
            "time_until_escalation_hours": (
                (threshold - time_in_level).total_seconds() / 3600
                if threshold and time_in_level < threshold
                else 0
            ),
            "natural_resolution_probability": self._get_natural_resolution_probability(
                conflict.escalation_level
            ),
        }


# Global escalation manager instance
_escalation_manager: EscalationManager | None = None


def get_escalation_manager() -> EscalationManager:
    """Get the global escalation manager instance.

    Returns:
        EscalationManager instance.
    """
    global _escalation_manager
    if _escalation_manager is None:
        _escalation_manager = EscalationManager()
    return _escalation_manager
