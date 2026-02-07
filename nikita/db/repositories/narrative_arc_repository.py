"""Narrative Arc Repository (Spec 035).

Manages CRUD operations for user narrative arcs.
"""

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.narrative_arc import UserNarrativeArc

if TYPE_CHECKING:
    from nikita.life_simulation.arcs import ArcTemplate

logger = logging.getLogger(__name__)


class NarrativeArcRepository:
    """Repository for managing user narrative arcs.

    Narrative arcs are multi-conversation storylines that develop over time.
    Users can have at most 2 active arcs at any time.
    """

    MAX_ACTIVE_ARCS = 2

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def create_arc(
        self,
        user_id: UUID,
        template: "ArcTemplate",
    ) -> UserNarrativeArc:
        """Create a new narrative arc from a template.

        Args:
            user_id: User ID to create arc for
            template: ArcTemplate to instantiate

        Returns:
            Created UserNarrativeArc record

        Raises:
            ValueError: If user already has MAX_ACTIVE_ARCS active arcs
        """
        # Check current active arc count
        active_count = await self._count_active_arcs(user_id)
        if active_count >= self.MAX_ACTIVE_ARCS:
            raise ValueError(
                f"User {user_id} already has {active_count} active arcs (max {self.MAX_ACTIVE_ARCS})"
            )

        # Determine max conversations from template range
        import random
        min_conv, max_conv = template.duration_conversations
        max_conversations = random.randint(min_conv, max_conv)

        # Get initial stage description
        initial_description = template.stages.get("setup", "Arc beginning...")

        arc = UserNarrativeArc(
            user_id=user_id,
            template_name=template.name,
            category=template.category.value,
            current_stage="setup",
            stage_progress=0,
            conversations_in_arc=0,
            max_conversations=max_conversations,
            current_description=initial_description,
            involved_characters=template.involved_characters,
            emotional_impact=template.emotional_impact,
            is_active=True,
            started_at=datetime.now(UTC),
        )

        self.session.add(arc)
        await self.session.flush()

        logger.info(
            f"Created arc '{template.name}' ({template.category.value}) for user {user_id}, "
            f"max {max_conversations} conversations"
        )
        return arc

    async def get_active_arcs(self, user_id: UUID) -> list[UserNarrativeArc]:
        """Get all active narrative arcs for a user.

        Args:
            user_id: User ID

        Returns:
            List of active UserNarrativeArc records (max 2)
        """
        stmt = (
            select(UserNarrativeArc)
            .where(
                UserNarrativeArc.user_id == user_id,
                UserNarrativeArc.is_active == True,  # noqa: E712
            )
            .order_by(UserNarrativeArc.started_at)
            .limit(self.MAX_ACTIVE_ARCS)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_arc_by_id(self, arc_id: UUID) -> UserNarrativeArc | None:
        """Get a specific arc by ID.

        Args:
            arc_id: Arc ID

        Returns:
            UserNarrativeArc or None
        """
        stmt = select(UserNarrativeArc).where(UserNarrativeArc.id == arc_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def advance_arc(
        self, arc_id: UUID, new_stage: str, description: str | None = None
    ) -> UserNarrativeArc | None:
        """Advance an arc to a new stage.

        Args:
            arc_id: Arc ID
            new_stage: New stage (setup, rising, climax, falling, resolved)
            description: Optional new description for the stage

        Returns:
            Updated UserNarrativeArc or None if not found
        """
        arc = await self.get_arc_by_id(arc_id)
        if not arc:
            return None

        old_stage = arc.current_stage
        arc.current_stage = new_stage

        if description:
            arc.current_description = description

        if new_stage == "resolved":
            arc.is_active = False
            arc.resolved_at = datetime.now(UTC)

        await self.session.flush()

        logger.info(f"Advanced arc {arc_id} from {old_stage} to {new_stage}")
        return arc

    async def resolve_arc(self, arc_id: UUID) -> UserNarrativeArc | None:
        """Mark an arc as resolved.

        Args:
            arc_id: Arc ID

        Returns:
            Updated UserNarrativeArc or None if not found
        """
        return await self.advance_arc(arc_id, "resolved", "Story concluded.")

    async def increment_conversation_count(
        self, arc_id: UUID
    ) -> UserNarrativeArc | None:
        """Increment the conversation count for an arc.

        Args:
            arc_id: Arc ID

        Returns:
            Updated UserNarrativeArc or None if not found
        """
        arc = await self.get_arc_by_id(arc_id)
        if not arc:
            return None

        arc.conversations_in_arc += 1
        await self.session.flush()

        logger.debug(
            f"Arc {arc_id} now at {arc.conversations_in_arc}/{arc.max_conversations} conversations"
        )
        return arc

    async def get_all_arcs(self, user_id: UUID) -> list[UserNarrativeArc]:
        """Get all arcs (active and resolved) for a user.

        Args:
            user_id: User ID

        Returns:
            List of all UserNarrativeArc records
        """
        stmt = (
            select(UserNarrativeArc)
            .where(UserNarrativeArc.user_id == user_id)
            .order_by(UserNarrativeArc.started_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_arcs_by_category(
        self, user_id: UUID, category: str
    ) -> list[UserNarrativeArc]:
        """Get all arcs of a specific category for a user.

        Args:
            user_id: User ID
            category: Arc category (career, social, personal, relationship, family)

        Returns:
            List of UserNarrativeArc records in that category
        """
        stmt = (
            select(UserNarrativeArc)
            .where(
                UserNarrativeArc.user_id == user_id,
                UserNarrativeArc.category == category,
            )
            .order_by(UserNarrativeArc.started_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def _count_active_arcs(self, user_id: UUID) -> int:
        """Count active arcs for a user.

        Args:
            user_id: User ID

        Returns:
            Number of active arcs
        """
        arcs = await self.get_active_arcs(user_id)
        return len(arcs)
