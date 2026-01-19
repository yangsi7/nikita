"""State Store for Emotional State Engine (Spec 023, T003).

Provides CRUD operations for emotional states.

AC-T003.1: StateStore class with CRUD operations
AC-T003.2: get_current_state() method
AC-T003.3: update_state() method
AC-T003.4: Supabase table: nikita_emotional_states
AC-T003.5: Unit tests for store
"""

import json
import logging
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from nikita.db.database import get_async_session
from nikita.emotional_state.models import (
    ConflictState,
    EmotionalStateModel,
)

logger = logging.getLogger(__name__)


class StateStore:
    """Store for emotional state data in Supabase.

    Provides CRUD operations for:
    - Emotional states (4D mood + conflict)
    - State history (for trend analysis)
    """

    def __init__(self, session_factory: Callable | None = None) -> None:
        """Initialize StateStore.

        Args:
            session_factory: Optional factory to create sessions.
        """
        self._session_factory = session_factory or get_async_session

    # ==================== CURRENT STATE ====================

    async def get_current_state(self, user_id: UUID) -> EmotionalStateModel | None:
        """Get the current emotional state for a user.

        Args:
            user_id: User ID.

        Returns:
            EmotionalStateModel or None if not found.
        """
        async with self._session_factory() as session:
            result = await session.execute(
                """
                SELECT * FROM nikita_emotional_states
                WHERE user_id = :user_id
                ORDER BY last_updated DESC
                LIMIT 1
                """,
                {"user_id": str(user_id)},
            )
            row = result.mappings().first()
            if not row:
                return None
            return self._row_to_state(dict(row))

    async def get_state(self, state_id: UUID) -> EmotionalStateModel | None:
        """Get a specific state by ID.

        Args:
            state_id: State ID.

        Returns:
            EmotionalStateModel or None if not found.
        """
        async with self._session_factory() as session:
            result = await session.execute(
                """
                SELECT * FROM nikita_emotional_states
                WHERE state_id = :state_id
                """,
                {"state_id": str(state_id)},
            )
            row = result.mappings().first()
            if not row:
                return None
            return self._row_to_state(dict(row))

    # ==================== CREATE / UPDATE ====================

    async def save_state(self, state: EmotionalStateModel) -> EmotionalStateModel:
        """Save an emotional state to the database.

        Args:
            state: EmotionalStateModel to save.

        Returns:
            Saved EmotionalStateModel with ID.
        """
        async with self._session_factory() as session:
            db_dict = state.model_dump_for_db()
            await session.execute(
                """
                INSERT INTO nikita_emotional_states
                (state_id, user_id, arousal, valence, dominance, intimacy,
                 conflict_state, conflict_started_at, conflict_trigger,
                 ignored_message_count, last_updated, created_at, metadata)
                VALUES (:state_id::uuid, :user_id::uuid, :arousal, :valence, :dominance, :intimacy,
                        :conflict_state, :conflict_started_at, :conflict_trigger,
                        :ignored_message_count, :last_updated, :created_at, :metadata::jsonb)
                """,
                {
                    **db_dict,
                    "metadata": json.dumps(db_dict.get("metadata", {})),
                },
            )
            await session.commit()
        logger.debug(f"Saved emotional state {state.state_id} for user {state.user_id}")
        return state

    async def update_state(
        self,
        user_id: UUID,
        arousal: float | None = None,
        valence: float | None = None,
        dominance: float | None = None,
        intimacy: float | None = None,
        conflict_state: ConflictState | None = None,
        conflict_trigger: str | None = None,
        ignored_message_count: int | None = None,
    ) -> EmotionalStateModel | None:
        """Update the current state for a user.

        Creates a new state record if none exists.
        Only updates fields that are provided.

        Args:
            user_id: User ID.
            arousal: New arousal value (optional).
            valence: New valence value (optional).
            dominance: New dominance value (optional).
            intimacy: New intimacy value (optional).
            conflict_state: New conflict state (optional).
            conflict_trigger: What triggered the conflict (optional).
            ignored_message_count: Count of ignored messages (optional).

        Returns:
            Updated EmotionalStateModel or None if no state exists.
        """
        current = await self.get_current_state(user_id)

        if current is None:
            # Create new state with provided values or defaults
            new_state = EmotionalStateModel(
                user_id=user_id,
                arousal=arousal if arousal is not None else 0.5,
                valence=valence if valence is not None else 0.5,
                dominance=dominance if dominance is not None else 0.5,
                intimacy=intimacy if intimacy is not None else 0.5,
                conflict_state=conflict_state or ConflictState.NONE,
                conflict_trigger=conflict_trigger,
                ignored_message_count=ignored_message_count or 0,
            )
            return await self.save_state(new_state)

        # Create updated state
        new_state = EmotionalStateModel(
            state_id=current.state_id,  # Keep same ID for update
            user_id=user_id,
            arousal=arousal if arousal is not None else current.arousal,
            valence=valence if valence is not None else current.valence,
            dominance=dominance if dominance is not None else current.dominance,
            intimacy=intimacy if intimacy is not None else current.intimacy,
            conflict_state=conflict_state if conflict_state is not None else current.conflict_state,
            conflict_trigger=conflict_trigger if conflict_trigger is not None else current.conflict_trigger,
            ignored_message_count=ignored_message_count if ignored_message_count is not None else current.ignored_message_count,
            created_at=current.created_at,  # Preserve original creation time
            metadata=current.metadata,
        )

        # Update in database
        async with self._session_factory() as session:
            db_dict = new_state.model_dump_for_db()
            await session.execute(
                """
                UPDATE nikita_emotional_states
                SET arousal = :arousal,
                    valence = :valence,
                    dominance = :dominance,
                    intimacy = :intimacy,
                    conflict_state = :conflict_state,
                    conflict_started_at = :conflict_started_at,
                    conflict_trigger = :conflict_trigger,
                    ignored_message_count = :ignored_message_count,
                    last_updated = :last_updated,
                    metadata = :metadata::jsonb
                WHERE state_id = :state_id::uuid
                """,
                {
                    **db_dict,
                    "metadata": json.dumps(db_dict.get("metadata", {})),
                },
            )
            await session.commit()

        logger.debug(f"Updated emotional state for user {user_id}")
        return new_state

    # ==================== HISTORY ====================

    async def get_state_history(
        self,
        user_id: UUID,
        days: int = 7,
        limit: int = 100,
    ) -> list[EmotionalStateModel]:
        """Get historical states for a user.

        Args:
            user_id: User ID.
            days: Number of days to look back.
            limit: Maximum number of states to return.

        Returns:
            List of EmotionalStateModel ordered by last_updated DESC.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        async with self._session_factory() as session:
            result = await session.execute(
                """
                SELECT * FROM nikita_emotional_states
                WHERE user_id = :user_id
                  AND last_updated >= :cutoff
                ORDER BY last_updated DESC
                LIMIT :limit
                """,
                {
                    "user_id": str(user_id),
                    "cutoff": cutoff.isoformat(),
                    "limit": limit,
                },
            )
            rows = result.mappings().all()
            return [self._row_to_state(dict(row)) for row in rows]

    async def get_conflict_history(
        self,
        user_id: UUID,
        days: int = 30,
    ) -> list[EmotionalStateModel]:
        """Get states where user was in conflict.

        Args:
            user_id: User ID.
            days: Number of days to look back.

        Returns:
            List of states with non-NONE conflict_state.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        async with self._session_factory() as session:
            result = await session.execute(
                """
                SELECT * FROM nikita_emotional_states
                WHERE user_id = :user_id
                  AND conflict_state != 'none'
                  AND last_updated >= :cutoff
                ORDER BY last_updated DESC
                """,
                {
                    "user_id": str(user_id),
                    "cutoff": cutoff.isoformat(),
                },
            )
            rows = result.mappings().all()
            return [self._row_to_state(dict(row)) for row in rows]

    # ==================== DELETE ====================

    async def delete_state(self, state_id: UUID) -> bool:
        """Delete a state by ID.

        Args:
            state_id: State ID to delete.

        Returns:
            True if deleted, False if not found.
        """
        async with self._session_factory() as session:
            result = await session.execute(
                """
                DELETE FROM nikita_emotional_states
                WHERE state_id = :state_id
                """,
                {"state_id": str(state_id)},
            )
            await session.commit()
            return result.rowcount > 0

    async def delete_user_states(self, user_id: UUID) -> int:
        """Delete all states for a user.

        Args:
            user_id: User ID.

        Returns:
            Number of deleted states.
        """
        async with self._session_factory() as session:
            result = await session.execute(
                """
                DELETE FROM nikita_emotional_states
                WHERE user_id = :user_id
                """,
                {"user_id": str(user_id)},
            )
            await session.commit()
            return result.rowcount

    # ==================== HELPERS ====================

    def _row_to_state(self, row: dict[str, Any]) -> EmotionalStateModel:
        """Convert database row to EmotionalStateModel.

        Args:
            row: Database row as dict.

        Returns:
            EmotionalStateModel instance.
        """
        # Handle metadata (could be dict or JSON string)
        metadata = row.get("metadata", {})
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = {}

        return EmotionalStateModel.from_db_row({
            **row,
            "metadata": metadata,
        })


# Singleton pattern
_store_instance: StateStore | None = None


def get_state_store() -> StateStore:
    """Get the singleton StateStore instance.

    Returns:
        StateStore instance.
    """
    global _store_instance
    if _store_instance is None:
        _store_instance = StateStore()
    return _store_instance
