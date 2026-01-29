"""Event Store for Life Simulation Engine (Spec 022, T004).

Provides CRUD operations for life events, narrative arcs, and entities.

AC-T004.1: EventStore class with CRUD operations
AC-T004.2: get_events_for_date() method
AC-T004.3: get_recent_events() method (7-day lookback)
AC-T004.4: Unit tests for store
"""

import logging
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select, and_, delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.database import get_session_maker
from nikita.life_simulation.models import (
    LifeEvent,
    NarrativeArc,
    NikitaEntity,
    EventDomain,
    EventType,
    ArcStatus,
    TimeOfDay,
    EmotionalImpact,
    EntityType,
)

logger = logging.getLogger(__name__)


class EventStore:
    """Store for life simulation data in Supabase.

    Provides CRUD operations for:
    - Life events (daily happenings)
    - Narrative arcs (multi-day stories)
    - Entities (recurring people, places, projects)
    """

    def __init__(self, session_factory: Callable | None = None) -> None:
        """Initialize EventStore.

        Args:
            session_factory: Optional factory to create sessions.
        """
        self._session_factory = session_factory or get_session_maker()

    # ==================== LIFE EVENTS ====================

    async def save_event(self, event: LifeEvent) -> LifeEvent:
        """Save a life event to the database.

        Args:
            event: LifeEvent to save.

        Returns:
            Saved LifeEvent with ID.
        """
        async with self._session_factory() as session:
            db_dict = event.model_dump_for_db()
            await session.execute(
                text("""
                INSERT INTO nikita_life_events
                (event_id, user_id, event_date, time_of_day, domain, event_type,
                 description, entities, emotional_impact, importance, narrative_arc_id, created_at)
                VALUES (:event_id, :user_id::uuid, :event_date, :time_of_day, :domain, :event_type,
                        :description, :entities::jsonb, :emotional_impact::jsonb, :importance,
                        :narrative_arc_id::uuid, :created_at)
                """),
                {
                    **db_dict,
                    "entities": str(db_dict["entities"]).replace("'", '"'),
                    "emotional_impact": str(db_dict["emotional_impact"]).replace("'", '"'),
                },
            )
            await session.commit()
        return event

    async def save_events(self, events: list[LifeEvent]) -> list[LifeEvent]:
        """Save multiple life events.

        Args:
            events: List of LifeEvent objects to save.

        Returns:
            List of saved events.
        """
        for event in events:
            await self.save_event(event)
        return events

    async def get_event(self, event_id: UUID) -> LifeEvent | None:
        """Get a single event by ID.

        Args:
            event_id: Event ID.

        Returns:
            LifeEvent or None if not found.
        """
        async with self._session_factory() as session:
            result = await session.execute(
                text("""
                SELECT * FROM nikita_life_events WHERE event_id = :event_id
                """),
                {"event_id": str(event_id)},
            )
            row = result.mappings().first()
            if not row:
                return None
            return self._row_to_event(dict(row))

    async def get_events_for_date(
        self, user_id: UUID, event_date: date
    ) -> list[LifeEvent]:
        """Get all events for a specific date (AC-T004.2).

        Args:
            user_id: User ID.
            event_date: Date to get events for.

        Returns:
            List of events for that date.
        """
        async with self._session_factory() as session:
            result = await session.execute(
                text("""
                SELECT * FROM nikita_life_events
                WHERE user_id = :user_id AND event_date = :event_date
                ORDER BY
                    CASE time_of_day
                        WHEN 'morning' THEN 1
                        WHEN 'afternoon' THEN 2
                        WHEN 'evening' THEN 3
                        WHEN 'night' THEN 4
                    END
                """),
                {"user_id": str(user_id), "event_date": event_date.isoformat()},
            )
            rows = result.mappings().all()
            return [self._row_to_event(dict(row)) for row in rows]

    async def get_recent_events(
        self, user_id: UUID, days: int = 7
    ) -> list[LifeEvent]:
        """Get events from the last N days (AC-T004.3).

        Args:
            user_id: User ID.
            days: Number of days to look back (default 7).

        Returns:
            List of recent events.
        """
        cutoff_date = date.today() - timedelta(days=days)
        async with self._session_factory() as session:
            result = await session.execute(
                text("""
                SELECT * FROM nikita_life_events
                WHERE user_id = :user_id AND event_date >= :cutoff_date
                ORDER BY event_date DESC,
                    CASE time_of_day
                        WHEN 'morning' THEN 1
                        WHEN 'afternoon' THEN 2
                        WHEN 'evening' THEN 3
                        WHEN 'night' THEN 4
                    END
                """),
                {"user_id": str(user_id), "cutoff_date": cutoff_date.isoformat()},
            )
            rows = result.mappings().all()
            return [self._row_to_event(dict(row)) for row in rows]

    async def get_events_by_domain(
        self, user_id: UUID, domain: EventDomain, days: int = 7
    ) -> list[LifeEvent]:
        """Get recent events for a specific domain.

        Args:
            user_id: User ID.
            domain: Event domain.
            days: Days to look back.

        Returns:
            List of events in that domain.
        """
        cutoff_date = date.today() - timedelta(days=days)
        async with self._session_factory() as session:
            result = await session.execute(
                text("""
                SELECT * FROM nikita_life_events
                WHERE user_id = :user_id
                  AND domain = :domain
                  AND event_date >= :cutoff_date
                ORDER BY event_date DESC
                """),
                {
                    "user_id": str(user_id),
                    "domain": domain.value,
                    "cutoff_date": cutoff_date.isoformat(),
                },
            )
            rows = result.mappings().all()
            return [self._row_to_event(dict(row)) for row in rows]

    async def delete_old_events(self, user_id: UUID, days_to_keep: int = 7) -> int:
        """Delete events older than specified days.

        Args:
            user_id: User ID.
            days_to_keep: Number of days of events to retain.

        Returns:
            Number of deleted events.
        """
        cutoff_date = date.today() - timedelta(days=days_to_keep)
        async with self._session_factory() as session:
            result = await session.execute(
                text("""
                DELETE FROM nikita_life_events
                WHERE user_id = :user_id AND event_date < :cutoff_date
                """),
                {"user_id": str(user_id), "cutoff_date": cutoff_date.isoformat()},
            )
            await session.commit()
            return result.rowcount

    # ==================== NARRATIVE ARCS ====================

    async def save_arc(self, arc: NarrativeArc) -> NarrativeArc:
        """Save a narrative arc.

        Args:
            arc: NarrativeArc to save.

        Returns:
            Saved arc.
        """
        async with self._session_factory() as session:
            db_dict = arc.model_dump_for_db()
            await session.execute(
                text("""
                INSERT INTO nikita_narrative_arcs
                (arc_id, user_id, domain, arc_type, status, start_date, entities,
                 current_state, possible_outcomes, created_at, resolved_at)
                VALUES (:arc_id, :user_id::uuid, :domain, :arc_type, :status, :start_date,
                        :entities::jsonb, :current_state, :possible_outcomes::jsonb,
                        :created_at, :resolved_at)
                """),
                {
                    **db_dict,
                    "entities": str(db_dict["entities"]).replace("'", '"'),
                    "possible_outcomes": str(db_dict["possible_outcomes"]).replace("'", '"'),
                },
            )
            await session.commit()
        return arc

    async def get_active_arcs(self, user_id: UUID) -> list[NarrativeArc]:
        """Get all active narrative arcs for a user.

        Args:
            user_id: User ID.

        Returns:
            List of active arcs.
        """
        async with self._session_factory() as session:
            result = await session.execute(
                text("""
                SELECT * FROM nikita_narrative_arcs
                WHERE user_id = :user_id AND status = 'active'
                ORDER BY created_at DESC
                """),
                {"user_id": str(user_id)},
            )
            rows = result.mappings().all()
            return [self._row_to_arc(dict(row)) for row in rows]

    async def update_arc_status(
        self,
        arc_id: UUID,
        status: ArcStatus,
        resolved_at: datetime | None = None,
    ) -> bool:
        """Update arc status.

        Args:
            arc_id: Arc ID.
            status: New status.
            resolved_at: Resolution timestamp.

        Returns:
            True if updated.
        """
        async with self._session_factory() as session:
            result = await session.execute(
                text("""
                UPDATE nikita_narrative_arcs
                SET status = :status, resolved_at = :resolved_at
                WHERE arc_id = :arc_id
                """),
                {
                    "arc_id": str(arc_id),
                    "status": status.value,
                    "resolved_at": resolved_at.isoformat() if resolved_at else None,
                },
            )
            await session.commit()
            return result.rowcount > 0

    async def update_arc_state(self, arc_id: UUID, current_state: str) -> bool:
        """Update arc's current state.

        Args:
            arc_id: Arc ID.
            current_state: New state description.

        Returns:
            True if updated.
        """
        async with self._session_factory() as session:
            result = await session.execute(
                text("""
                UPDATE nikita_narrative_arcs
                SET current_state = :current_state
                WHERE arc_id = :arc_id
                """),
                {"arc_id": str(arc_id), "current_state": current_state},
            )
            await session.commit()
            return result.rowcount > 0

    # ==================== ENTITIES ====================

    async def save_entity(self, entity: NikitaEntity) -> NikitaEntity:
        """Save an entity.

        Args:
            entity: NikitaEntity to save.

        Returns:
            Saved entity.
        """
        async with self._session_factory() as session:
            db_dict = entity.model_dump_for_db()
            await session.execute(
                text("""
                INSERT INTO nikita_entities
                (entity_id, user_id, entity_type, name, description, relationship, created_at)
                VALUES (:entity_id, :user_id::uuid, :entity_type, :name, :description,
                        :relationship, :created_at)
                """),
                db_dict,
            )
            await session.commit()
        return entity

    async def save_entities(self, entities: list[NikitaEntity]) -> list[NikitaEntity]:
        """Save multiple entities.

        Args:
            entities: List of entities to save.

        Returns:
            List of saved entities.
        """
        for entity in entities:
            await self.save_entity(entity)
        return entities

    async def get_entities(self, user_id: UUID) -> list[NikitaEntity]:
        """Get all entities for a user.

        Args:
            user_id: User ID.

        Returns:
            List of entities.
        """
        async with self._session_factory() as session:
            result = await session.execute(
                text("""
                SELECT * FROM nikita_entities WHERE user_id = :user_id
                ORDER BY entity_type, name
                """),
                {"user_id": str(user_id)},
            )
            rows = result.mappings().all()
            return [self._row_to_entity(dict(row)) for row in rows]

    async def get_entities_by_type(
        self, user_id: UUID, entity_type: EntityType
    ) -> list[NikitaEntity]:
        """Get entities of a specific type.

        Args:
            user_id: User ID.
            entity_type: Entity type filter.

        Returns:
            List of matching entities.
        """
        async with self._session_factory() as session:
            result = await session.execute(
                text("""
                SELECT * FROM nikita_entities
                WHERE user_id = :user_id AND entity_type = :entity_type
                ORDER BY name
                """),
                {"user_id": str(user_id), "entity_type": entity_type.value},
            )
            rows = result.mappings().all()
            return [self._row_to_entity(dict(row)) for row in rows]

    async def entity_exists(self, user_id: UUID, name: str) -> bool:
        """Check if an entity with this name exists.

        Args:
            user_id: User ID.
            name: Entity name.

        Returns:
            True if entity exists.
        """
        async with self._session_factory() as session:
            result = await session.execute(
                text("""
                SELECT 1 FROM nikita_entities
                WHERE user_id = :user_id AND name = :name
                LIMIT 1
                """),
                {"user_id": str(user_id), "name": name},
            )
            return result.scalar() is not None

    # ==================== HELPERS ====================

    def _row_to_event(self, row: dict[str, Any]) -> LifeEvent:
        """Convert database row to LifeEvent."""
        emotional_impact = row.get("emotional_impact", {})
        if isinstance(emotional_impact, str):
            import json
            emotional_impact = json.loads(emotional_impact)

        entities = row.get("entities", [])
        if isinstance(entities, str):
            import json
            entities = json.loads(entities)

        return LifeEvent(
            event_id=UUID(str(row["event_id"])),
            user_id=UUID(str(row["user_id"])),
            event_date=row["event_date"] if isinstance(row["event_date"], date) else date.fromisoformat(row["event_date"]),
            time_of_day=TimeOfDay(row["time_of_day"]),
            domain=EventDomain(row["domain"]),
            event_type=EventType(row["event_type"]),
            description=row["description"],
            entities=entities,
            emotional_impact=EmotionalImpact(**emotional_impact),
            importance=float(row["importance"]),
            narrative_arc_id=UUID(str(row["narrative_arc_id"])) if row.get("narrative_arc_id") else None,
            created_at=row["created_at"] if isinstance(row["created_at"], datetime) else datetime.fromisoformat(row["created_at"]),
        )

    def _row_to_arc(self, row: dict[str, Any]) -> NarrativeArc:
        """Convert database row to NarrativeArc."""
        entities = row.get("entities", [])
        if isinstance(entities, str):
            import json
            entities = json.loads(entities)

        possible_outcomes = row.get("possible_outcomes", [])
        if isinstance(possible_outcomes, str):
            import json
            possible_outcomes = json.loads(possible_outcomes)

        resolved_at = row.get("resolved_at")
        if isinstance(resolved_at, str):
            resolved_at = datetime.fromisoformat(resolved_at)

        return NarrativeArc(
            arc_id=UUID(str(row["arc_id"])),
            user_id=UUID(str(row["user_id"])),
            domain=EventDomain(row["domain"]),
            arc_type=row["arc_type"],
            status=ArcStatus(row["status"]),
            start_date=row["start_date"] if isinstance(row["start_date"], date) else date.fromisoformat(row["start_date"]),
            entities=entities,
            current_state=row.get("current_state", ""),
            possible_outcomes=possible_outcomes,
            created_at=row["created_at"] if isinstance(row["created_at"], datetime) else datetime.fromisoformat(row["created_at"]),
            resolved_at=resolved_at,
        )

    def _row_to_entity(self, row: dict[str, Any]) -> NikitaEntity:
        """Convert database row to NikitaEntity."""
        return NikitaEntity(
            entity_id=UUID(str(row["entity_id"])),
            user_id=UUID(str(row["user_id"])),
            entity_type=EntityType(row["entity_type"]),
            name=row["name"],
            description=row.get("description"),
            relationship=row.get("relationship"),
            created_at=row["created_at"] if isinstance(row["created_at"], datetime) else datetime.fromisoformat(row["created_at"]),
        )


# Module-level singleton
_default_store: EventStore | None = None


def get_event_store() -> EventStore:
    """Get the singleton EventStore instance.

    Returns:
        Cached EventStore instance.
    """
    global _default_store
    if _default_store is None:
        _default_store = EventStore()
    return _default_store
