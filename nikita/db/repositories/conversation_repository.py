"""Conversation repository for conversation-related database operations.

T4: ConversationRepository
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.conversation import Conversation
from nikita.db.repositories.base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    """Repository for Conversation entity.

    Handles conversation lifecycle, message appending,
    and retrieval operations.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize ConversationRepository."""
        super().__init__(session, Conversation)

    async def create_conversation(
        self,
        user_id: UUID,
        platform: str,
        started_at: datetime | None = None,
        is_boss_fight: bool = False,
        chapter_at_time: int | None = None,
    ) -> Conversation:
        """Create a new conversation.

        Args:
            user_id: The user's UUID.
            platform: Platform type ('telegram' or 'voice').
            started_at: When conversation started (defaults to now).
            is_boss_fight: Whether this is a boss fight conversation.
            chapter_at_time: Current chapter at conversation start.

        Returns:
            Created Conversation entity.
        """
        conversation = Conversation(
            user_id=user_id,
            platform=platform,
            messages=[],
            started_at=started_at or datetime.now(UTC),
            is_boss_fight=is_boss_fight,
            chapter_at_time=chapter_at_time,
        )
        return await self.create(conversation)

    async def append_message(
        self,
        conversation_id: UUID,
        role: str,
        content: str,
        analysis: dict[str, Any] | None = None,
    ) -> Conversation:
        """Append a message to the conversation's JSONB messages.

        Args:
            conversation_id: The conversation's UUID.
            role: Message role ('user' or 'nikita').
            content: Message content.
            analysis: Optional analysis dict.

        Returns:
            Updated Conversation entity.

        Raises:
            ValueError: If conversation not found.
        """
        conversation = await self.get(conversation_id)
        if conversation is None:
            raise ValueError(f"Conversation {conversation_id} not found")

        conversation.add_message(role, content, analysis)
        conversation.last_message_at = datetime.now(UTC)

        await self.session.flush()
        await self.session.refresh(conversation)

        return conversation

    async def get_recent(
        self,
        user_id: UUID,
        limit: int = 10,
    ) -> list[Conversation]:
        """Get recent conversations for a user.

        Args:
            user_id: The user's UUID.
            limit: Maximum number to return.

        Returns:
            List of recent conversations, newest first.
        """
        stmt = (
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.started_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def search(
        self,
        user_id: UUID,
        query: str,
    ) -> list[Conversation]:
        """Search conversations by text content.

        Note: Full-text search on search_vector requires the tsvector
        column and index to be set up in the migration. This is a
        placeholder that searches in JSONB messages.

        Args:
            user_id: The user's UUID.
            query: Search query string.

        Returns:
            List of matching conversations.
        """
        # Basic JSONB text search (can be enhanced with full-text search)
        # This searches within the messages JSONB array using PostgreSQL casting
        from sqlalchemy import cast, String
        from sqlalchemy.dialects.postgresql import JSONB

        stmt = (
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .where(cast(Conversation.messages, String).contains(query))
            .order_by(Conversation.started_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def close_conversation(
        self,
        conversation_id: UUID,
        score_delta: Decimal | None = None,
    ) -> Conversation:
        """Close a conversation by setting ended_at.

        Args:
            conversation_id: The conversation's UUID.
            score_delta: Optional score change from this conversation.

        Returns:
            Updated Conversation entity.

        Raises:
            ValueError: If conversation not found.
        """
        conversation = await self.get(conversation_id)
        if conversation is None:
            raise ValueError(f"Conversation {conversation_id} not found")

        conversation.ended_at = datetime.now(UTC)
        if score_delta is not None:
            conversation.score_delta = score_delta

        await self.session.flush()
        await self.session.refresh(conversation)

        return conversation

    # Post-processing pipeline support (spec 012)

    async def get_stale_active_conversations(
        self,
        timeout_minutes: int = 15,
        max_attempts: int = 3,
        limit: int = 50,
    ) -> list[Conversation]:
        """Get active conversations that have timed out for post-processing.

        Args:
            timeout_minutes: Minutes since last message to consider stale.
            max_attempts: Maximum processing attempts before skipping.
            limit: Maximum conversations to return.

        Returns:
            List of stale active conversations ready for processing.
        """
        cutoff_time = datetime.now(UTC) - timedelta(minutes=timeout_minutes)

        stmt = (
            select(Conversation)
            .where(Conversation.status == "active")
            .where(Conversation.last_message_at.isnot(None))
            .where(Conversation.last_message_at < cutoff_time)
            .where(Conversation.processing_attempts < max_attempts)
            .order_by(Conversation.last_message_at.asc())
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def mark_processing(
        self,
        conversation_id: UUID,
    ) -> Conversation:
        """Mark conversation as being processed.

        Args:
            conversation_id: The conversation's UUID.

        Returns:
            Updated Conversation entity.

        Raises:
            ValueError: If conversation not found.
        """
        conversation = await self.get(conversation_id)
        if conversation is None:
            raise ValueError(f"Conversation {conversation_id} not found")

        conversation.status = "processing"
        conversation.processing_attempts += 1

        await self.session.flush()
        await self.session.refresh(conversation)

        return conversation

    async def mark_processed(
        self,
        conversation_id: UUID,
        summary: str | None = None,
        emotional_tone: str | None = None,
        extracted_entities: dict[str, Any] | None = None,
    ) -> Conversation:
        """Mark conversation as processed and store results.

        Args:
            conversation_id: The conversation's UUID.
            summary: Optional conversation summary.
            emotional_tone: Optional emotional tone ('positive'/'neutral'/'negative').
            extracted_entities: Optional extracted entities dict.

        Returns:
            Updated Conversation entity.

        Raises:
            ValueError: If conversation not found.
        """
        conversation = await self.get(conversation_id)
        if conversation is None:
            raise ValueError(f"Conversation {conversation_id} not found")

        conversation.status = "processed"
        conversation.processed_at = datetime.now(UTC)

        if summary is not None:
            conversation.conversation_summary = summary
        if emotional_tone is not None:
            conversation.emotional_tone = emotional_tone
        if extracted_entities is not None:
            conversation.extracted_entities = extracted_entities

        await self.session.flush()
        await self.session.refresh(conversation)

        return conversation

    async def mark_failed(
        self,
        conversation_id: UUID,
    ) -> Conversation:
        """Mark conversation processing as failed.

        Args:
            conversation_id: The conversation's UUID.

        Returns:
            Updated Conversation entity.

        Raises:
            ValueError: If conversation not found.
        """
        conversation = await self.get(conversation_id)
        if conversation is None:
            raise ValueError(f"Conversation {conversation_id} not found")

        conversation.status = "failed"

        await self.session.flush()
        await self.session.refresh(conversation)

        return conversation

    async def update_last_message_at(
        self,
        conversation_id: UUID,
    ) -> Conversation:
        """Update the last_message_at timestamp.

        Called when a new message is added to track session activity.

        Args:
            conversation_id: The conversation's UUID.

        Returns:
            Updated Conversation entity.

        Raises:
            ValueError: If conversation not found.
        """
        conversation = await self.get(conversation_id)
        if conversation is None:
            raise ValueError(f"Conversation {conversation_id} not found")

        conversation.last_message_at = datetime.now(UTC)

        await self.session.flush()
        await self.session.refresh(conversation)

        return conversation

    async def update_score_delta(
        self,
        conversation_id: UUID,
        score_delta: Decimal,
    ) -> Conversation:
        """Update the score_delta for a conversation.

        This accumulates (adds to) the existing score_delta if present.

        Args:
            conversation_id: The conversation's UUID.
            score_delta: The score change to add.

        Returns:
            Updated Conversation entity.

        Raises:
            ValueError: If conversation not found.
        """
        conversation = await self.get(conversation_id)
        if conversation is None:
            raise ValueError(f"Conversation {conversation_id} not found")

        # Accumulate score deltas (multiple turns in one conversation)
        if conversation.score_delta is None:
            conversation.score_delta = score_delta
        else:
            conversation.score_delta += score_delta

        await self.session.flush()
        await self.session.refresh(conversation)

        return conversation

    async def get_active_conversation(
        self,
        user_id: UUID,
    ) -> Conversation | None:
        """Get the current active conversation for a user.

        Args:
            user_id: The user's UUID.

        Returns:
            Active conversation if exists, None otherwise.
        """
        stmt = (
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .where(Conversation.status == "active")
            .order_by(Conversation.started_at.desc())
            .limit(1)
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_processed_conversations(
        self,
        user_id: UUID,
        days: int = 7,
        limit: int = 50,
    ) -> list[Conversation]:
        """Get processed conversations for summary generation.

        Args:
            user_id: The user's UUID.
            days: Number of days to look back.
            limit: Maximum conversations to return.

        Returns:
            List of processed conversations, newest first.
        """
        cutoff_date = datetime.now(UTC) - timedelta(days=days)

        stmt = (
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .where(Conversation.status == "processed")
            .where(Conversation.started_at > cutoff_date)
            .order_by(Conversation.started_at.desc())
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())
