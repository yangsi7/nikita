"""Conversation thread repository for tracking unresolved topics.

Supports the context engineering redesign (spec 012) by tracking:
- Follow-up topics
- Unanswered questions
- Promises made by either party
- Topics worth revisiting
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.context import ConversationThread, THREAD_STATUSES, THREAD_TYPES
from nikita.db.repositories.base import BaseRepository


class ConversationThreadRepository(BaseRepository[ConversationThread]):
    """Repository for ConversationThread entity.

    Handles creation, resolution, and retrieval of conversation threads
    for the post-processing pipeline and system prompt generation.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize ConversationThreadRepository."""
        super().__init__(session, ConversationThread)

    async def create_thread(
        self,
        user_id: UUID,
        thread_type: str,
        content: str,
        source_conversation_id: UUID | None = None,
    ) -> ConversationThread:
        """Create a new conversation thread.

        Args:
            user_id: The user's UUID.
            thread_type: One of THREAD_TYPES ('follow_up', 'question', 'promise', 'topic').
            content: The thread content/description.
            source_conversation_id: Optional source conversation UUID.

        Returns:
            Created ConversationThread entity.

        Raises:
            ValueError: If thread_type is invalid.
        """
        if thread_type not in THREAD_TYPES:
            raise ValueError(f"Invalid thread_type: {thread_type}. Must be one of {THREAD_TYPES}")

        thread = ConversationThread(
            user_id=user_id,
            thread_type=thread_type,
            content=content,
            source_conversation_id=source_conversation_id,
            status="open",
            created_at=datetime.now(UTC),
        )
        return await self.create(thread)

    async def get_open_threads(
        self,
        user_id: UUID,
        thread_type: str | None = None,
        limit: int = 20,
    ) -> list[ConversationThread]:
        """Get open (unresolved) threads for a user.

        Args:
            user_id: The user's UUID.
            thread_type: Optional filter by thread type.
            limit: Maximum number of threads to return.

        Returns:
            List of open threads, newest first.
        """
        stmt = (
            select(ConversationThread)
            .where(ConversationThread.user_id == user_id)
            .where(ConversationThread.status == "open")
        )

        if thread_type is not None:
            stmt = stmt.where(ConversationThread.thread_type == thread_type)

        stmt = stmt.order_by(ConversationThread.created_at.desc()).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_threads_for_prompt(
        self,
        user_id: UUID,
        max_per_type: int = 5,
    ) -> dict[str, list[ConversationThread]]:
        """Get threads organized by type for system prompt generation.

        Args:
            user_id: The user's UUID.
            max_per_type: Maximum threads per type.

        Returns:
            Dict mapping thread_type to list of threads.
        """
        result: dict[str, list[ConversationThread]] = {}

        for thread_type in THREAD_TYPES:
            threads = await self.get_open_threads(
                user_id=user_id,
                thread_type=thread_type,
                limit=max_per_type,
            )
            if threads:
                result[thread_type] = threads

        return result

    async def resolve_thread(
        self,
        thread_id: UUID,
    ) -> ConversationThread:
        """Mark a thread as resolved.

        Args:
            thread_id: The thread's UUID.

        Returns:
            Updated ConversationThread entity.

        Raises:
            ValueError: If thread not found.
        """
        thread = await self.get(thread_id)
        if thread is None:
            raise ValueError(f"Thread {thread_id} not found")

        thread.status = "resolved"
        thread.resolved_at = datetime.now(UTC)

        await self.session.flush()
        await self.session.refresh(thread)

        return thread

    async def expire_thread(
        self,
        thread_id: UUID,
    ) -> ConversationThread:
        """Mark a thread as expired (no longer relevant).

        Args:
            thread_id: The thread's UUID.

        Returns:
            Updated ConversationThread entity.

        Raises:
            ValueError: If thread not found.
        """
        thread = await self.get(thread_id)
        if thread is None:
            raise ValueError(f"Thread {thread_id} not found")

        thread.status = "expired"
        thread.resolved_at = datetime.now(UTC)

        await self.session.flush()
        await self.session.refresh(thread)

        return thread

    async def bulk_create_threads(
        self,
        user_id: UUID,
        threads_data: list[dict],
        source_conversation_id: UUID | None = None,
    ) -> list[ConversationThread]:
        """Create multiple threads at once (for post-processing pipeline).

        Args:
            user_id: The user's UUID.
            threads_data: List of dicts with 'thread_type' and 'content' keys.
            source_conversation_id: Optional source conversation UUID.

        Returns:
            List of created ConversationThread entities.
        """
        created_threads = []

        for data in threads_data:
            thread = await self.create_thread(
                user_id=user_id,
                thread_type=data["thread_type"],
                content=data["content"],
                source_conversation_id=source_conversation_id,
            )
            created_threads.append(thread)

        return created_threads

    async def bulk_resolve_threads(
        self,
        thread_ids: list[UUID],
    ) -> int:
        """Resolve multiple threads at once.

        Args:
            thread_ids: List of thread UUIDs to resolve.

        Returns:
            Number of threads resolved.
        """
        resolved_count = 0

        for thread_id in thread_ids:
            try:
                await self.resolve_thread(thread_id)
                resolved_count += 1
            except ValueError:
                # Thread not found, skip
                pass

        return resolved_count

    async def get_threads_filtered(
        self,
        user_id: UUID,
        status: str | None = None,
        thread_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ConversationThread], int]:
        """Get threads with filtering and pagination.

        Args:
            user_id: The user's UUID.
            status: Filter by status ('open', 'resolved', 'expired', 'all', or None for all).
            thread_type: Filter by type ('follow_up', 'question', 'promise', 'topic', 'all', or None for all).
            limit: Maximum number of threads to return.
            offset: Number of threads to skip (for pagination).

        Returns:
            Tuple of (list of threads, total count before pagination).
        """
        # Build base query for threads
        stmt = select(ConversationThread).where(ConversationThread.user_id == user_id)

        # Apply status filter
        if status is not None and status != "all":
            stmt = stmt.where(ConversationThread.status == status)

        # Apply thread_type filter
        if thread_type is not None and thread_type != "all":
            stmt = stmt.where(ConversationThread.thread_type == thread_type)

        # Get total count (before limit/offset)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.session.execute(count_stmt)
        total_count = count_result.scalar_one()

        # Apply ordering and pagination
        stmt = stmt.order_by(ConversationThread.created_at.desc()).limit(limit).offset(offset)

        # Execute query
        result = await self.session.execute(stmt)
        threads = list(result.scalars().all())

        return (threads, total_count)
