"""Migration utility for Spec 057: Conflict Temperature.

Migrates existing users from discrete conflict_state enum to
continuous temperature gauge in conflict_details JSONB.

Usage:
    from nikita.conflicts.migration import migrate_user_conflict_state

    details = migrate_user_conflict_state(
        conflict_state="passive_aggressive",
        score_history_entries=[{"delta": "2.5"}, {"delta": "-1.0"}],
    )
"""

from datetime import UTC, datetime
from typing import Any

from nikita.conflicts.gottman import GottmanTracker
from nikita.conflicts.models import ConflictDetails
from nikita.conflicts.temperature import TemperatureEngine
from nikita.emotional_state.models import ConflictState


def migrate_user_conflict_state(
    conflict_state: str | ConflictState = "none",
    score_history_entries: list[dict[str, Any]] | None = None,
    conflict_started_at: datetime | None = None,
) -> ConflictDetails:
    """Migrate a user's conflict state to temperature model.

    Reads current enum value, maps to temperature, initializes Gottman
    counters from score history.

    Args:
        conflict_state: Current conflict_state enum value.
        score_history_entries: Recent score_history entries with 'delta' key.
        conflict_started_at: When the last conflict started (for last_conflict_at).

    Returns:
        Initialized ConflictDetails for writing to JSONB.
    """
    # Parse enum
    if isinstance(conflict_state, str):
        try:
            state_enum = ConflictState(conflict_state)
        except ValueError:
            state_enum = ConflictState.NONE
    else:
        state_enum = conflict_state

    # Map enum to temperature
    temperature = ConflictState.temperature_from_enum(state_enum)
    zone = TemperatureEngine.get_zone(temperature)

    # Initialize Gottman counters from score history
    entries = score_history_entries or []
    counters = GottmanTracker.initialize_from_history(entries)

    # Determine if in conflict for Gottman target
    is_in_conflict = temperature >= 25.0  # WARM or above
    gottman_ratio = GottmanTracker.get_ratio(counters)
    gottman_target = GottmanTracker.get_target(is_in_conflict)

    now = datetime.now(UTC)

    return ConflictDetails(
        temperature=temperature,
        zone=zone.value,
        positive_count=counters.positive_count,
        negative_count=counters.negative_count,
        gottman_ratio=gottman_ratio if gottman_ratio != float("inf") else 999.0,
        gottman_target=gottman_target,
        horsemen_detected=[],
        repair_attempts=[],
        last_temp_update=now.isoformat(),
        session_positive=0,
        session_negative=0,
    )
