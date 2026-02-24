"""Conflict store for database operations (Spec 027, T004).

Provides CRUD operations for conflict triggers and active conflicts.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.conflicts.models import (
    ActiveConflict,
    ConflictSummary,
    ConflictTrigger,
    ConflictType,
    EscalationLevel,
    ResolutionType,
    TriggerType,
)


class ConflictStore:
    """Store for conflict triggers and active conflicts.

    .. deprecated::
        In-memory store is ineffective on serverless (Cloud Run scales to zero).
        Spec 057 temperature system uses conflict_details JSONB on User model.
        This class is dead code for the main game loop — only tests use it.
        Will be removed in Spec 109.
    """

    def __init__(self):
        """Initialize conflict store with in-memory storage."""
        import warnings

        warnings.warn(
            "ConflictStore is deprecated. Use conflict_details JSONB (Spec 057).",
            DeprecationWarning,
            stacklevel=2,
        )
        self._triggers: dict[str, ConflictTrigger] = {}
        self._conflicts: dict[str, ActiveConflict] = {}
        self._user_triggers: dict[str, list[str]] = {}  # user_id -> trigger_ids
        self._user_conflicts: dict[str, list[str]] = {}  # user_id -> conflict_ids

    # Trigger operations

    def create_trigger(
        self,
        user_id: str,
        trigger_type: TriggerType,
        severity: float,
        context: dict[str, Any] | None = None,
        user_messages: list[str] | None = None,
    ) -> ConflictTrigger:
        """Create a new conflict trigger.

        Args:
            user_id: User ID.
            trigger_type: Type of trigger.
            severity: Severity score (0.0-1.0).
            context: Additional context.
            user_messages: Messages that triggered this.

        Returns:
            Created ConflictTrigger.
        """
        trigger_id = str(uuid.uuid4())
        trigger = ConflictTrigger(
            trigger_id=trigger_id,
            trigger_type=trigger_type,
            severity=severity,
            detected_at=datetime.now(UTC),
            context=context or {},
            user_messages=user_messages or [],
        )

        self._triggers[trigger_id] = trigger
        if user_id not in self._user_triggers:
            self._user_triggers[user_id] = []
        self._user_triggers[user_id].append(trigger_id)

        return trigger

    def get_trigger(self, trigger_id: str) -> ConflictTrigger | None:
        """Get a trigger by ID.

        Args:
            trigger_id: Trigger ID.

        Returns:
            ConflictTrigger if found, None otherwise.
        """
        return self._triggers.get(trigger_id)

    def get_user_triggers(
        self,
        user_id: str,
        since: datetime | None = None,
    ) -> list[ConflictTrigger]:
        """Get all triggers for a user.

        Args:
            user_id: User ID.
            since: Only return triggers after this time.

        Returns:
            List of ConflictTrigger.
        """
        trigger_ids = self._user_triggers.get(user_id, [])
        triggers = [
            self._triggers[tid]
            for tid in trigger_ids
            if tid in self._triggers
        ]

        if since:
            triggers = [t for t in triggers if t.detected_at >= since]

        return sorted(triggers, key=lambda t: t.detected_at, reverse=True)

    def delete_trigger(self, trigger_id: str) -> bool:
        """Delete a trigger.

        Args:
            trigger_id: Trigger ID.

        Returns:
            True if deleted, False if not found.
        """
        if trigger_id in self._triggers:
            del self._triggers[trigger_id]
            # Clean up user mapping
            for user_id, trigger_ids in self._user_triggers.items():
                if trigger_id in trigger_ids:
                    trigger_ids.remove(trigger_id)
            return True
        return False

    # Conflict operations

    def create_conflict(
        self,
        user_id: str,
        conflict_type: ConflictType,
        severity: float,
        trigger_ids: list[str] | None = None,
    ) -> ActiveConflict:
        """Create a new active conflict.

        Args:
            user_id: User ID.
            conflict_type: Type of conflict.
            severity: Initial severity.
            trigger_ids: IDs of triggers that caused this.

        Returns:
            Created ActiveConflict.
        """
        conflict_id = str(uuid.uuid4())
        conflict = ActiveConflict(
            conflict_id=conflict_id,
            user_id=user_id,
            conflict_type=conflict_type,
            severity=severity,
            escalation_level=EscalationLevel.SUBTLE,
            triggered_at=datetime.now(UTC),
            trigger_ids=trigger_ids or [],
        )

        self._conflicts[conflict_id] = conflict
        if user_id not in self._user_conflicts:
            self._user_conflicts[user_id] = []
        self._user_conflicts[user_id].append(conflict_id)

        return conflict

    def get_conflict(self, conflict_id: str) -> ActiveConflict | None:
        """Get a conflict by ID.

        Args:
            conflict_id: Conflict ID.

        Returns:
            ActiveConflict if found, None otherwise.
        """
        return self._conflicts.get(conflict_id)

    def get_active_conflict(self, user_id: str) -> ActiveConflict | None:
        """Get the active (unresolved) conflict for a user.

        Args:
            user_id: User ID.

        Returns:
            Active conflict if exists, None otherwise.
        """
        conflict_ids = self._user_conflicts.get(user_id, [])
        for conflict_id in reversed(conflict_ids):
            conflict = self._conflicts.get(conflict_id)
            if conflict and not conflict.resolved:
                return conflict
        return None

    def get_user_conflicts(
        self,
        user_id: str,
        resolved: bool | None = None,
    ) -> list[ActiveConflict]:
        """Get all conflicts for a user.

        Args:
            user_id: User ID.
            resolved: Filter by resolution status.

        Returns:
            List of ActiveConflict.
        """
        conflict_ids = self._user_conflicts.get(user_id, [])
        conflicts = [
            self._conflicts[cid]
            for cid in conflict_ids
            if cid in self._conflicts
        ]

        if resolved is not None:
            conflicts = [c for c in conflicts if c.resolved == resolved]

        return sorted(conflicts, key=lambda c: c.triggered_at, reverse=True)

    def update_conflict(
        self,
        conflict_id: str,
        **updates: Any,
    ) -> ActiveConflict | None:
        """Update a conflict.

        Args:
            conflict_id: Conflict ID.
            **updates: Fields to update.

        Returns:
            Updated conflict if found, None otherwise.
        """
        conflict = self._conflicts.get(conflict_id)
        if not conflict:
            return None

        # Create updated conflict with new values
        conflict_dict = conflict.model_dump()
        conflict_dict.update(updates)
        updated_conflict = ActiveConflict(**conflict_dict)
        self._conflicts[conflict_id] = updated_conflict

        return updated_conflict

    def escalate_conflict(
        self,
        conflict_id: str,
        new_level: EscalationLevel,
    ) -> ActiveConflict | None:
        """Escalate a conflict to a new level.

        Args:
            conflict_id: Conflict ID.
            new_level: New escalation level.

        Returns:
            Updated conflict if found, None otherwise.
        """
        return self.update_conflict(
            conflict_id,
            escalation_level=new_level,
            last_escalated=datetime.now(UTC),
        )

    def resolve_conflict(
        self,
        conflict_id: str,
        resolution_type: ResolutionType,
    ) -> ActiveConflict | None:
        """Resolve a conflict.

        Args:
            conflict_id: Conflict ID.
            resolution_type: How the conflict was resolved.

        Returns:
            Updated conflict if found, None otherwise.
        """
        return self.update_conflict(
            conflict_id,
            resolved=True,
            resolution_type=resolution_type,
        )

    def increment_resolution_attempts(
        self,
        conflict_id: str,
    ) -> ActiveConflict | None:
        """Increment the resolution attempts counter.

        Args:
            conflict_id: Conflict ID.

        Returns:
            Updated conflict if found, None otherwise.
        """
        conflict = self._conflicts.get(conflict_id)
        if not conflict:
            return None

        return self.update_conflict(
            conflict_id,
            resolution_attempts=conflict.resolution_attempts + 1,
        )

    def reduce_severity(
        self,
        conflict_id: str,
        reduction: float,
    ) -> ActiveConflict | None:
        """Reduce the severity of a conflict.

        Args:
            conflict_id: Conflict ID.
            reduction: Amount to reduce severity by.

        Returns:
            Updated conflict if found, None otherwise.
        """
        conflict = self._conflicts.get(conflict_id)
        if not conflict:
            return None

        new_severity = max(0.0, conflict.severity - reduction)
        return self.update_conflict(conflict_id, severity=new_severity)

    # Summary operations

    def get_conflict_summary(self, user_id: str) -> ConflictSummary:
        """Get a summary of a user's conflict history.

        Args:
            user_id: User ID.

        Returns:
            ConflictSummary with statistics.
        """
        conflicts = self.get_user_conflicts(user_id)

        total = len(conflicts)
        resolved = len([c for c in conflicts if c.resolved])
        unresolved_crises = len([
            c for c in conflicts
            if not c.resolved and c.escalation_level == EscalationLevel.CRISIS
        ])
        current = self.get_active_conflict(user_id)
        last_conflict_at = conflicts[0].triggered_at if conflicts else None

        return ConflictSummary(
            user_id=user_id,
            total_conflicts=total,
            resolved_conflicts=resolved,
            unresolved_crises=unresolved_crises,
            current_conflict=current,
            last_conflict_at=last_conflict_at,
        )

    def count_consecutive_unresolved_crises(self, user_id: str) -> int:
        """Count consecutive unresolved crisis-level conflicts.

        Args:
            user_id: User ID.

        Returns:
            Number of consecutive unresolved crises.
        """
        conflicts = self.get_user_conflicts(user_id)
        count = 0

        for conflict in conflicts:
            if (
                not conflict.resolved
                and conflict.escalation_level == EscalationLevel.CRISIS
            ):
                count += 1
            elif conflict.resolved:
                break  # Reset count on resolved conflict

        return count

    def clear_user_data(self, user_id: str) -> None:
        """Clear all conflict data for a user.

        Args:
            user_id: User ID.
        """
        # Clear triggers
        trigger_ids = self._user_triggers.pop(user_id, [])
        for trigger_id in trigger_ids:
            self._triggers.pop(trigger_id, None)

        # Clear conflicts
        conflict_ids = self._user_conflicts.pop(user_id, [])
        for conflict_id in conflict_ids:
            self._conflicts.pop(conflict_id, None)


# Global store instance
_store: ConflictStore | None = None


def get_conflict_store() -> ConflictStore:
    """Get the global conflict store instance.

    Returns:
        ConflictStore instance.
    """
    global _store
    if _store is None:
        _store = ConflictStore()
    return _store
