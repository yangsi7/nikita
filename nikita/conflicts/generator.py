"""Conflict generation for relationship dynamics (Spec 027, Phase C).

Generates conflicts from detected triggers, calculating severity
and selecting appropriate conflict types.

Spec 057: Temperature zone injection (flag removed, always ON).
"""

import random
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field

from nikita.conflicts.models import (
    ActiveConflict,
    ConflictConfig,
    ConflictTrigger,
    ConflictType,
    EscalationLevel,
    TriggerType,
    get_conflict_config,
    trigger_to_conflict_type,
)
from nikita.conflicts.store import ConflictStore, get_conflict_store


class GenerationContext(BaseModel):
    """Context for conflict generation.

    Attributes:
        user_id: User ID.
        chapter: Current game chapter.
        relationship_score: Current relationship score.
        recent_conflicts: Recent conflict history.
        days_since_last_conflict: Days since last conflict (None if no conflicts).
    """

    user_id: str
    chapter: int = Field(default=1, ge=1, le=5)
    relationship_score: int = Field(default=50, ge=0, le=100)
    recent_conflicts: list[ActiveConflict] = Field(default_factory=list)
    days_since_last_conflict: float | None = None


class GenerationResult(BaseModel):
    """Result of conflict generation.

    Attributes:
        conflict: Generated conflict (None if no conflict generated).
        generated: Whether a conflict was generated.
        reason: Reason for generation or skipping.
        contributing_triggers: Triggers that contributed to the conflict.
    """

    conflict: ActiveConflict | None = None
    generated: bool = False
    reason: str = ""
    contributing_triggers: list[ConflictTrigger] = Field(default_factory=list)


class ConflictGenerator:
    """Generates conflicts from detected triggers.

    Handles:
    - Trigger prioritization
    - Severity calculation
    - Conflict type selection
    - Prevention of duplicate conflicts

    .. deprecated::
        Uses in-memory ConflictStore which is ineffective on serverless.
        Spec 057 temperature system handles conflict generation via ConflictStage.
        Will be removed in Spec 109.
    """

    # Severity base values per trigger type
    TRIGGER_SEVERITY_BASE = {
        TriggerType.DISMISSIVE: 0.3,
        TriggerType.NEGLECT: 0.4,
        TriggerType.JEALOUSY: 0.5,
        TriggerType.BOUNDARY: 0.6,
        TriggerType.TRUST: 0.7,
    }

    # Conflict type priority (higher = more important)
    CONFLICT_PRIORITY = {
        ConflictType.TRUST: 4,
        ConflictType.BOUNDARY: 3,
        ConflictType.JEALOUSY: 2,
        ConflictType.ATTENTION: 1,
    }

    # Minimum severity to generate a conflict
    MIN_SEVERITY_THRESHOLD = 0.25

    # Cooldown between conflicts (hours)
    CONFLICT_COOLDOWN_HOURS = 4

    def __init__(
        self,
        store: ConflictStore | None = None,
        config: ConflictConfig | None = None,
    ):
        """Initialize conflict generator.

        Args:
            store: ConflictStore for persistence.
            config: Conflict configuration.
        """
        self._store = store or get_conflict_store()
        self._config = config or get_conflict_config()

    def generate(
        self,
        triggers: list[ConflictTrigger],
        context: GenerationContext,
        conflict_details: dict[str, Any] | None = None,
    ) -> GenerationResult:
        """Generate a conflict from triggers.

        Spec 057: When temperature flag is ON, uses temperature zone
        to determine injection probability. Falls through to existing
        logic when flag is OFF.

        Args:
            triggers: List of detected triggers.
            context: Generation context.
            conflict_details: Optional conflict_details JSONB (Spec 057).

        Returns:
            GenerationResult with conflict if generated.
        """
        # Spec 057: Temperature-based injection (always ON, flag removed)
        if conflict_details is not None:
            return self._generate_with_temperature(triggers, context, conflict_details)

        # Legacy fallback when no conflict_details provided
        skip_reason = self._check_should_skip(triggers, context)
        if skip_reason:
            return GenerationResult(
                generated=False,
                reason=skip_reason,
            )

        # Check for existing active conflict
        existing = self._store.get_active_conflict(context.user_id)
        if existing:
            return GenerationResult(
                generated=False,
                reason="Active conflict already exists",
                conflict=existing,
            )

        # Prioritize and select triggers
        selected_triggers = self._prioritize_triggers(triggers)
        if not selected_triggers:
            return GenerationResult(
                generated=False,
                reason="No triggers met threshold after filtering",
            )

        # Determine conflict type
        conflict_type = self._select_conflict_type(selected_triggers, context)

        # Calculate severity
        severity = self._calculate_severity(selected_triggers, context)

        # Create the conflict
        conflict = self._store.create_conflict(
            user_id=context.user_id,
            conflict_type=conflict_type,
            severity=severity,
            trigger_ids=[t.trigger_id for t in selected_triggers],
        )

        return GenerationResult(
            conflict=conflict,
            generated=True,
            reason=f"Conflict generated: {conflict_type.value}",
            contributing_triggers=selected_triggers,
        )

    def _generate_with_temperature(
        self,
        triggers: list[ConflictTrigger],
        context: GenerationContext,
        conflict_details: dict[str, Any],
    ) -> GenerationResult:
        """Generate conflict using temperature zone probability (Spec 057).

        Replaces cooldown-based generation with temperature-driven injection.
        CALM zone: never injects. Other zones: stochastic injection.

        Args:
            triggers: List of detected triggers.
            context: Generation context.
            conflict_details: Conflict details JSONB from DB.

        Returns:
            GenerationResult with conflict if generated.
        """
        from nikita.conflicts.models import ConflictDetails, TemperatureZone
        from nikita.conflicts.temperature import TemperatureEngine

        details = ConflictDetails.from_jsonb(conflict_details)
        zone = TemperatureEngine.get_zone(details.temperature)

        # CALM zone: no conflicts generated
        if zone == TemperatureZone.CALM:
            return GenerationResult(
                generated=False,
                reason=f"Temperature {details.temperature:.1f} in CALM zone — no conflict",
            )

        # Check for existing active conflict
        existing = self._store.get_active_conflict(context.user_id)
        if existing:
            return GenerationResult(
                generated=False,
                reason="Active conflict already exists",
                conflict=existing,
            )

        # No triggers at all: still skip
        if not triggers:
            return GenerationResult(
                generated=False,
                reason="No triggers detected (temperature injection requires triggers)",
            )

        # Stochastic injection based on temperature
        injection_probability = TemperatureEngine.interpolate_probability(details.temperature)
        if random.random() >= injection_probability:
            return GenerationResult(
                generated=False,
                reason=f"Temperature {details.temperature:.1f} ({zone.value}): "
                       f"injection roll failed (prob={injection_probability:.2f})",
            )

        # Prioritize triggers
        selected_triggers = self._prioritize_triggers(triggers)
        if not selected_triggers:
            return GenerationResult(
                generated=False,
                reason="No triggers met threshold after filtering",
            )

        # Select conflict type
        conflict_type = self._select_conflict_type(selected_triggers, context)

        # Calculate severity — cap by zone
        severity = self._calculate_severity(selected_triggers, context)
        max_severity = TemperatureEngine.get_max_severity(zone)
        severity = min(severity, max_severity)

        # Create the conflict
        conflict = self._store.create_conflict(
            user_id=context.user_id,
            conflict_type=conflict_type,
            severity=severity,
            trigger_ids=[t.trigger_id for t in selected_triggers],
        )

        return GenerationResult(
            conflict=conflict,
            generated=True,
            reason=f"Temperature-based conflict: {conflict_type.value} "
                   f"(temp={details.temperature:.1f}, zone={zone.value}, "
                   f"severity={severity:.2f})",
            contributing_triggers=selected_triggers,
        )

    def _check_should_skip(
        self,
        triggers: list[ConflictTrigger],
        context: GenerationContext,
    ) -> str | None:
        """Check if we should skip conflict generation.

        Returns:
            Skip reason if should skip, None otherwise.
        """
        # No triggers
        if not triggers:
            return "No triggers detected"

        # Check cooldown
        if context.days_since_last_conflict is not None:
            cooldown_days = self.CONFLICT_COOLDOWN_HOURS / 24
            if context.days_since_last_conflict < cooldown_days:
                return f"In cooldown period ({context.days_since_last_conflict:.1f} days < {cooldown_days:.1f})"

        # Very high relationship score reduces conflict probability
        if context.relationship_score >= 90:
            max_severity = max(t.severity for t in triggers)
            if max_severity < 0.6:
                return "High relationship score prevents minor conflict"

        return None

    def _prioritize_triggers(
        self,
        triggers: list[ConflictTrigger],
    ) -> list[ConflictTrigger]:
        """Prioritize and filter triggers.

        Args:
            triggers: All detected triggers.

        Returns:
            Filtered and sorted triggers.
        """
        # Filter by minimum severity
        valid = [t for t in triggers if t.severity >= self.MIN_SEVERITY_THRESHOLD]

        # Sort by severity (highest first)
        valid.sort(key=lambda t: t.severity, reverse=True)

        # Return top 3 triggers max
        return valid[:3]

    def _select_conflict_type(
        self,
        triggers: list[ConflictTrigger],
        context: GenerationContext,
    ) -> ConflictType:
        """Select the conflict type based on triggers.

        Args:
            triggers: Prioritized triggers.
            context: Generation context.

        Returns:
            Selected conflict type.
        """
        # Map triggers to conflict types with priorities
        type_scores: dict[ConflictType, float] = {}

        for trigger in triggers:
            conflict_type = trigger_to_conflict_type(trigger.trigger_type)
            priority = self.CONFLICT_PRIORITY.get(conflict_type, 1)
            score = trigger.severity * priority

            if conflict_type in type_scores:
                type_scores[conflict_type] = max(type_scores[conflict_type], score)
            else:
                type_scores[conflict_type] = score

        # Check for same conflict type in recent history
        recent_types = {c.conflict_type for c in context.recent_conflicts[:3]}

        # If best type was recent, penalize it
        best_type = max(type_scores, key=type_scores.get)
        if best_type in recent_types and len(type_scores) > 1:
            # Try to select a different type
            for conflict_type in sorted(type_scores, key=type_scores.get, reverse=True):
                if conflict_type not in recent_types:
                    return conflict_type

        return best_type

    def _calculate_severity(
        self,
        triggers: list[ConflictTrigger],
        context: GenerationContext,
    ) -> float:
        """Calculate final conflict severity.

        Args:
            triggers: Contributing triggers.
            context: Generation context.

        Returns:
            Calculated severity (0.0-1.0).
        """
        if not triggers:
            return 0.0

        # Base severity from triggers (weighted average)
        total_weight = 0.0
        weighted_sum = 0.0

        for trigger in triggers:
            base = self.TRIGGER_SEVERITY_BASE.get(trigger.trigger_type, 0.4)
            weight = trigger.severity
            weighted_sum += (base + trigger.severity) / 2 * weight
            total_weight += weight

        base_severity = weighted_sum / total_weight if total_weight > 0 else 0.5

        # Relationship score modifier (lower score = higher severity)
        relationship_modifier = 1.0 + (50 - context.relationship_score) / 100
        relationship_modifier = max(0.7, min(1.3, relationship_modifier))

        # Recent conflict modifier (more conflicts = higher severity)
        conflict_count = len(context.recent_conflicts)
        conflict_modifier = 1.0 + (conflict_count * 0.1)
        conflict_modifier = min(1.5, conflict_modifier)

        # Chapter modifier (later chapters = slightly less severe)
        chapter_modifier = 1.0 - (context.chapter - 1) * 0.05
        chapter_modifier = max(0.8, chapter_modifier)

        # Calculate final severity
        final_severity = (
            base_severity
            * relationship_modifier
            * conflict_modifier
            * chapter_modifier
        )

        # Clamp to 0.0-1.0
        return max(0.0, min(1.0, final_severity))

    def should_generate_conflict(
        self,
        triggers: list[ConflictTrigger],
        context: GenerationContext,
    ) -> tuple[bool, str]:
        """Check if a conflict should be generated without creating one.

        Args:
            triggers: Detected triggers.
            context: Generation context.

        Returns:
            Tuple of (should_generate, reason).
        """
        skip_reason = self._check_should_skip(triggers, context)
        if skip_reason:
            return False, skip_reason

        existing = self._store.get_active_conflict(context.user_id)
        if existing:
            return False, "Active conflict already exists"

        selected = self._prioritize_triggers(triggers)
        if not selected:
            return False, "No triggers met threshold"

        return True, "Conflict conditions met"


# Global generator instance
_generator: ConflictGenerator | None = None


def get_conflict_generator() -> ConflictGenerator:
    """Get the global conflict generator instance.

    Returns:
        ConflictGenerator instance.
    """
    global _generator
    if _generator is None:
        _generator = ConflictGenerator()
    return _generator
