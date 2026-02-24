"""MemoryFact repository for semantic memory operations (Spec 042)."""

from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.memory_fact import MemoryFact
from nikita.db.repositories.base import BaseRepository


class MemoryFactRepository(BaseRepository[MemoryFact]):
    """Repository for MemoryFact entity.

    Provides semantic search via pgVector cosine distance,
    fact management, and deactivation with supersession tracking.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, MemoryFact)

    async def add_fact(
        self,
        user_id: UUID,
        fact: str,
        graph_type: str,
        embedding: list[float],
        source: str,
        confidence: float,
        metadata: dict[str, Any] | None = None,
        conversation_id: UUID | None = None,
    ) -> MemoryFact:
        """Insert a new memory fact.

        Args:
            user_id: Owner user UUID.
            fact: The fact text.
            graph_type: One of 'user', 'relationship', 'nikita'.
            embedding: 1536-dim float vector.
            source: Where this fact came from (e.g. 'conversation', 'onboarding').
            confidence: 0.0 to 1.0 confidence score.
            metadata: Optional JSONB metadata.
            conversation_id: Optional conversation UUID.

        Returns:
            The created MemoryFact.
        """
        memory_fact = MemoryFact(
            user_id=user_id,
            graph_type=graph_type,
            fact=fact,
            source=source,
            confidence=confidence,
            embedding=embedding,
            fact_metadata=metadata or {},
            is_active=True,
            conversation_id=conversation_id,
        )
        self.session.add(memory_fact)
        await self.session.flush()
        await self.session.refresh(memory_fact)
        return memory_fact

    async def semantic_search(
        self,
        user_id: UUID,
        query_embedding: list[float],
        graph_type: str | None = None,
        limit: int = 10,
        min_confidence: float = 0.0,
    ) -> list[tuple[MemoryFact, float]]:
        """Search for semantically similar facts using pgVector cosine distance.

        Args:
            user_id: Owner user UUID.
            query_embedding: 1536-dim query vector.
            graph_type: Optional filter by graph type.
            limit: Max results.
            min_confidence: Minimum confidence threshold.

        Returns:
            List of (MemoryFact, distance) tuples ordered by distance ASC.
        """
        distance = MemoryFact.embedding.cosine_distance(query_embedding)

        stmt = (
            select(MemoryFact, distance.label("distance"))
            .where(
                MemoryFact.user_id == user_id,
                MemoryFact.is_active.is_(True),
                MemoryFact.confidence >= min_confidence,
            )
            .order_by(distance)
            .limit(limit)
        )

        if graph_type is not None:
            stmt = stmt.where(MemoryFact.graph_type == graph_type)

        result = await self.session.execute(stmt)
        return list(result.all())

    async def semantic_search_batch(
        self,
        user_id: UUID,
        query_embedding: list[float],
        graph_types: list[str],
        limit: int = 10,
        min_confidence: float = 0.0,
    ) -> list[tuple["MemoryFact", float]]:
        """Search across multiple graph types in a single DB query.

        Spec 102 FR-002: Single query with WHERE graph_type IN (...)
        instead of N sequential queries.

        Args:
            user_id: Owner user UUID.
            query_embedding: 1536-dim query vector.
            graph_types: List of graph types to search within.
            limit: Max results.
            min_confidence: Minimum confidence threshold.

        Returns:
            List of (MemoryFact, distance) tuples ordered by distance ASC.
        """
        distance = MemoryFact.embedding.cosine_distance(query_embedding)

        stmt = (
            select(MemoryFact, distance.label("distance"))
            .where(
                MemoryFact.user_id == user_id,
                MemoryFact.is_active.is_(True),
                MemoryFact.confidence >= min_confidence,
                MemoryFact.graph_type.in_(graph_types),
            )
            .order_by(distance)
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.all())

    async def get_recent(
        self,
        user_id: UUID,
        graph_type: str | None = None,
        limit: int = 20,
    ) -> list[MemoryFact]:
        """Get recent facts ordered by created_at DESC.

        Args:
            user_id: Owner user UUID.
            graph_type: Optional filter.
            limit: Max results.

        Returns:
            List of MemoryFact records.
        """
        stmt = (
            select(MemoryFact)
            .where(
                MemoryFact.user_id == user_id,
                MemoryFact.is_active.is_(True),
            )
            .order_by(MemoryFact.created_at.desc())
            .limit(limit)
        )

        if graph_type is not None:
            stmt = stmt.where(MemoryFact.graph_type == graph_type)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def deactivate(
        self,
        fact_id: UUID,
        superseded_by_id: UUID | None = None,
    ) -> bool:
        """Deactivate a fact (soft delete).

        Args:
            fact_id: The fact to deactivate.
            superseded_by_id: Optional ID of the replacing fact.

        Returns:
            True if found and deactivated, False if not found.
        """
        fact = await self.session.get(MemoryFact, fact_id)
        if fact is None:
            return False

        fact.is_active = False
        if superseded_by_id is not None:
            fact.superseded_by = superseded_by_id
        await self.session.flush()
        return True

    async def get_by_user(
        self,
        user_id: UUID,
        graph_type: str | None = None,
        active_only: bool = True,
    ) -> list[MemoryFact]:
        """Get all facts for a user.

        Args:
            user_id: Owner user UUID.
            graph_type: Optional filter.
            active_only: If True, only return active facts.

        Returns:
            List of MemoryFact records.
        """
        conditions = [MemoryFact.user_id == user_id]

        if active_only:
            conditions.append(MemoryFact.is_active.is_(True))
        if graph_type is not None:
            conditions.append(MemoryFact.graph_type == graph_type)

        stmt = (
            select(MemoryFact)
            .where(*conditions)
            .order_by(MemoryFact.created_at.desc())
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())
