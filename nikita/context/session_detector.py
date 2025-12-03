"""Session detection for context engineering pipeline.

Detects when conversations have ended based on timeout:
- Text (Telegram): 15 minutes of no messages
- Voice (ElevenLabs): When call ends (explicit signal)

Called by pg_cron every minute to find stale conversations
that need post-processing.
"""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.repositories.conversation_repository import ConversationRepository

logger = logging.getLogger(__name__)

# Default timeout for text sessions (minutes)
TEXT_SESSION_TIMEOUT_MINUTES = 15


class SessionDetector:
    """Detects ended sessions for post-processing.

    Uses the conversation repository to find:
    - Active text conversations with no messages for 15+ minutes
    - These are marked for post-processing

    Voice sessions are handled differently (explicit call end signal).
    """

    def __init__(
        self,
        session: AsyncSession,
        timeout_minutes: int = TEXT_SESSION_TIMEOUT_MINUTES,
    ) -> None:
        """Initialize session detector.

        Args:
            session: Database session.
            timeout_minutes: Timeout for text sessions (default 15).
        """
        self._session = session
        self._timeout_minutes = timeout_minutes
        self._conversation_repo = ConversationRepository(session)

    async def get_stale_sessions(
        self,
        limit: int = 50,
    ) -> list[UUID]:
        """Get conversation IDs that have timed out.

        Finds active conversations where:
        - last_message_at is more than timeout_minutes ago
        - processing_attempts < 3 (avoid infinite retries)

        Args:
            limit: Maximum conversations to return.

        Returns:
            List of conversation UUIDs ready for post-processing.
        """
        conversations = await self._conversation_repo.get_stale_active_conversations(
            timeout_minutes=self._timeout_minutes,
            max_attempts=3,
            limit=limit,
        )

        conversation_ids = [conv.id for conv in conversations]

        if conversation_ids:
            logger.info(
                f"Found {len(conversation_ids)} stale sessions for processing "
                f"(timeout: {self._timeout_minutes} min)"
            )

        return conversation_ids

    async def mark_for_processing(
        self,
        conversation_id: UUID,
    ) -> bool:
        """Mark a conversation as being processed.

        Args:
            conversation_id: The conversation UUID.

        Returns:
            True if marked successfully, False if not found.
        """
        try:
            await self._conversation_repo.mark_processing(conversation_id)
            logger.info(f"Marked conversation {conversation_id} for processing")
            return True
        except ValueError:
            logger.warning(f"Conversation {conversation_id} not found")
            return False

    async def detect_and_queue(
        self,
        limit: int = 50,
    ) -> list[UUID]:
        """Detect stale sessions and mark them for processing.

        This is the main entry point called by the pg_cron task.

        Args:
            limit: Maximum sessions to process.

        Returns:
            List of conversation UUIDs queued for processing.
        """
        stale_ids = await self.get_stale_sessions(limit=limit)

        queued_ids = []
        for conv_id in stale_ids:
            if await self.mark_for_processing(conv_id):
                queued_ids.append(conv_id)

        if queued_ids:
            logger.info(f"Queued {len(queued_ids)} conversations for post-processing")

        return queued_ids


async def detect_stale_sessions(
    session: AsyncSession,
    timeout_minutes: int = TEXT_SESSION_TIMEOUT_MINUTES,
    limit: int = 50,
) -> list[UUID]:
    """Convenience function to detect stale sessions.

    Args:
        session: Database session.
        timeout_minutes: Timeout for text sessions.
        limit: Maximum sessions to return.

    Returns:
        List of conversation UUIDs ready for post-processing.
    """
    detector = SessionDetector(session, timeout_minutes)
    return await detector.detect_and_queue(limit=limit)
