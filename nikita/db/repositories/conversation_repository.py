"""Conversation repository for conversation-related database operations.

T4: ConversationRepository
"""

from datetime import UTC, datetime
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
        # This searches within the messages JSONB array
        stmt = (
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .where(Conversation.messages.cast(str).contains(query))
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
