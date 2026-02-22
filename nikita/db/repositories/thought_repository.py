"""Nikita thought repository for simulating inner life.

Supports the context engineering redesign (spec 012) by managing:
- What Nikita is thinking about from conversations
- Things she wants to share next time
- Questions she has for him
- Her emotional state/feelings
- "Missing him" thoughts (scaled by time gap)
"""

from datetime import UTC, datetime, timedelta
from difflib import SequenceMatcher
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.context import NikitaThought, THOUGHT_TYPES
from nikita.db.repositories.base import BaseRepository


class NikitaThoughtRepository(BaseRepository[NikitaThought]):
    """Repository for NikitaThought entity.

    Handles creation, usage tracking, and retrieval of Nikita's
    simulated thoughts for system prompt generation.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize NikitaThoughtRepository."""
        super().__init__(session, NikitaThought)

    async def create_thought(
        self,
        user_id: UUID,
        thought_type: str,
        content: str,
        source_conversation_id: UUID | None = None,
        expires_at: datetime | None = None,
    ) -> NikitaThought:
        """Create a new Nikita thought.

        Args:
            user_id: The user's UUID.
            thought_type: One of THOUGHT_TYPES.
            content: The thought content.
            source_conversation_id: Optional source conversation UUID.
            expires_at: Optional expiration time.

        Returns:
            Created NikitaThought entity.

        Raises:
            ValueError: If thought_type is invalid.
        """
        if thought_type not in THOUGHT_TYPES:
            raise ValueError(f"Invalid thought_type: {thought_type}. Must be one of {THOUGHT_TYPES}")

        thought = NikitaThought(
            user_id=user_id,
            thought_type=thought_type,
            content=content,
            source_conversation_id=source_conversation_id,
            expires_at=expires_at,
            created_at=datetime.now(UTC),
        )
        return await self.create(thought)

    async def get_active_thoughts(
        self,
        user_id: UUID,
        thought_type: str | None = None,
        limit: int = 10,
    ) -> list[NikitaThought]:
        """Get active (not used, not expired) thoughts for a user.

        Args:
            user_id: The user's UUID.
            thought_type: Optional filter by thought type.
            limit: Maximum number of thoughts to return.

        Returns:
            List of active thoughts, newest first.
        """
        now = datetime.now(UTC)

        stmt = (
            select(NikitaThought)
            .where(NikitaThought.user_id == user_id)
            .where(NikitaThought.used_at.is_(None))  # Not used
        )

        # Filter out expired thoughts
        stmt = stmt.where(
            (NikitaThought.expires_at.is_(None)) | (NikitaThought.expires_at > now)
        )

        if thought_type is not None:
            stmt = stmt.where(NikitaThought.thought_type == thought_type)

        stmt = stmt.order_by(NikitaThought.created_at.desc()).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_thoughts_for_prompt(
        self,
        user_id: UUID,
        max_per_type: int = 3,
    ) -> dict[str, list[NikitaThought]]:
        """Get thoughts organized by type for system prompt generation.

        Args:
            user_id: The user's UUID.
            max_per_type: Maximum thoughts per type.

        Returns:
            Dict mapping thought_type to list of thoughts.
        """
        result: dict[str, list[NikitaThought]] = {}

        for thought_type in THOUGHT_TYPES:
            thoughts = await self.get_active_thoughts(
                user_id=user_id,
                thought_type=thought_type,
                limit=max_per_type,
            )
            if thoughts:
                result[thought_type] = thoughts

        return result

    async def mark_thought_used(
        self,
        thought_id: UUID,
    ) -> NikitaThought:
        """Mark a thought as used (incorporated into conversation).

        Args:
            thought_id: The thought's UUID.

        Returns:
            Updated NikitaThought entity.

        Raises:
            ValueError: If thought not found.
        """
        thought = await self.get(thought_id)
        if thought is None:
            raise ValueError(f"Thought {thought_id} not found")

        thought.used_at = datetime.now(UTC)

        await self.session.flush()
        await self.session.refresh(thought)

        return thought

    async def create_missing_him_thought(
        self,
        user_id: UUID,
        hours_since_last_message: float,
        source_conversation_id: UUID | None = None,
    ) -> NikitaThought | None:
        """Create a "missing him" thought scaled by time gap.

        Different intensities based on time gap:
        - 24-48h: "I've been thinking about you"
        - 48-72h: "I miss you"
        - 72h+: "I really miss you"

        Args:
            user_id: The user's UUID.
            hours_since_last_message: Hours since last user message.
            source_conversation_id: Optional source conversation UUID.

        Returns:
            Created NikitaThought entity, or None if time gap too small.
        """
        if hours_since_last_message < 24:
            return None

        # Determine intensity based on time gap
        if hours_since_last_message < 48:
            content = "I've been thinking about you... wondering what you've been up to."
        elif hours_since_last_message < 72:
            content = "I miss you. It's been quiet without hearing from you."
        else:
            content = "I really miss you. It feels like forever since we talked."

        # Expire when he messages (will be marked used or deleted on session start)
        expires_at = datetime.now(UTC) + timedelta(days=7)

        return await self.create_thought(
            user_id=user_id,
            thought_type="missing_him",
            content=content,
            source_conversation_id=source_conversation_id,
            expires_at=expires_at,
        )

    async def bulk_create_thoughts(
        self,
        user_id: UUID,
        thoughts_data: list[dict],
        source_conversation_id: UUID | None = None,
    ) -> list[NikitaThought]:
        """Create multiple thoughts at once (for post-processing pipeline).

        Args:
            user_id: The user's UUID.
            thoughts_data: List of dicts with 'thought_type', 'content',
                          and optional 'expires_at' keys.
            source_conversation_id: Optional source conversation UUID.

        Returns:
            List of created NikitaThought entities.
        """
        created_thoughts = []

        for data in thoughts_data:
            thought = await self.create_thought(
                user_id=user_id,
                thought_type=data["thought_type"],
                content=data["content"],
                source_conversation_id=source_conversation_id,
                expires_at=data.get("expires_at"),
            )
            created_thoughts.append(thought)

        return created_thoughts

    async def expire_missing_him_thoughts(
        self,
        user_id: UUID,
    ) -> int:
        """Mark all "missing him" thoughts as used when user messages.

        Called at session start when user sends a message.

        Args:
            user_id: The user's UUID.

        Returns:
            Number of thoughts marked as used.
        """
        thoughts = await self.get_active_thoughts(
            user_id=user_id,
            thought_type="missing_him",
            limit=100,
        )

        for thought in thoughts:
            thought.used_at = datetime.now(UTC)

        await self.session.flush()

        return len(thoughts)

    async def cleanup_expired_thoughts(
        self,
        user_id: UUID,
    ) -> int:
        """Delete expired thoughts to keep database clean.

        Args:
            user_id: The user's UUID.

        Returns:
            Number of thoughts deleted.
        """
        now = datetime.now(UTC)

        stmt = (
            select(NikitaThought)
            .where(NikitaThought.user_id == user_id)
            .where(NikitaThought.expires_at.isnot(None))
            .where(NikitaThought.expires_at < now)
        )

        result = await self.session.execute(stmt)
        expired_thoughts = list(result.scalars().all())

        for thought in expired_thoughts:
            await self.session.delete(thought)

        await self.session.flush()

        return len(expired_thoughts)

    # Spec 104 Story 2: Narrative arc retrieval
    async def get_active_arcs(self, user_id: UUID) -> list[str]:
        """Get active narrative arc thought contents."""
        thoughts = await self.get_active_thoughts(
            user_id=user_id, thought_type="arc", limit=5
        )
        return [t.content for t in thoughts]

    # Spec 104 Story 3: Thought auto-resolution
    RESOLUTION_THRESHOLD = 0.6

    async def resolve_matching_thoughts(
        self, user_id: UUID, facts: list[str]
    ) -> int:
        """Cross-ref facts against active thoughts; mark resolved if similar."""
        if not facts:
            return 0
        active = await self.get_active_thoughts(user_id=user_id, limit=50)
        resolved = 0
        for thought in active:
            for fact in facts:
                ratio = SequenceMatcher(
                    None, thought.content.lower(), fact.lower()
                ).ratio()
                if ratio >= self.RESOLUTION_THRESHOLD:
                    await self.mark_thought_used(thought.id)
                    resolved += 1
                    break
        return resolved

    # Spec 104 Story 4: Thought-driven openers
    async def get_active_openers(
        self, user_id: UUID, limit: int = 3
    ) -> list[str]:
        """Get active 'wants_to_share' thoughts as conversation openers."""
        thoughts = await self.get_active_thoughts(
            user_id=user_id, thought_type="wants_to_share", limit=limit
        )
        return [t.content for t in thoughts]

    async def get_paginated(
        self,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0,
        thought_type: str | None = None,
    ) -> tuple[list[NikitaThought], int]:
        """Get paginated thoughts for a user (includes expired and used).

        Args:
            user_id: The user's UUID.
            limit: Maximum number of thoughts to return.
            offset: Number of thoughts to skip for pagination.
            thought_type: Optional filter by thought type ("all" or None returns all types).

        Returns:
            Tuple of (list of thoughts, total count before pagination).
        """
        # Build base query for thoughts
        stmt = (
            select(NikitaThought)
            .where(NikitaThought.user_id == user_id)
        )

        # Apply thought type filter if specified (and not "all")
        if thought_type is not None and thought_type != "all":
            stmt = stmt.where(NikitaThought.thought_type == thought_type)

        # Get total count before pagination
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.session.execute(count_stmt)
        total_count = count_result.scalar_one()

        # Apply ordering and pagination
        stmt = stmt.order_by(NikitaThought.created_at.desc()).limit(limit).offset(offset)

        # Execute query
        result = await self.session.execute(stmt)
        thoughts = list(result.scalars().all())

        return thoughts, total_count
