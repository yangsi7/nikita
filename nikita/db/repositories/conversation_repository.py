"""Conversation repository for conversation-related database operations.

T4: ConversationRepository
"""

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.conversation import Conversation
from nikita.db.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


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

    async def create_voice_conversation(
        self,
        user_id: UUID,
        session_id: str,
        transcript_raw: str = "",
        messages: list[dict[str, Any]] | None = None,
        chapter_at_time: int | None = None,
    ) -> Conversation:
        """Create a voice conversation from ElevenLabs webhook data (Spec 032 T3.1).

        Creates a conversation record specifically for voice calls with:
        - Platform set to 'voice'
        - ElevenLabs session ID linked
        - Raw transcript stored
        - Messages JSONB populated

        Args:
            user_id: The user's UUID.
            session_id: ElevenLabs conversation/session ID.
            transcript_raw: Raw transcript string (User: ...\nNikita: ...).
            messages: Parsed messages list [{role, content}].
            chapter_at_time: Current chapter at conversation start.

        Returns:
            Created Conversation entity.

        Acceptance Criteria:
            - AC-T3.1.1: Creates conversation with platform='voice'
            - AC-T3.1.2: Stores transcript in messages JSONB and transcript_raw
            - AC-T3.1.3: Sets initial status='active'
            - AC-T3.1.4: Links to ElevenLabs session via elevenlabs_session_id
        """
        now = datetime.now(UTC)
        conversation = Conversation(
            user_id=user_id,
            platform="voice",  # AC-T3.1.1
            messages=messages or [],  # AC-T3.1.2
            transcript_raw=transcript_raw,  # AC-T3.1.2
            elevenlabs_session_id=session_id,  # AC-T3.1.4
            started_at=now,
            last_message_at=now,
            status="active",  # AC-T3.1.3
            chapter_at_time=chapter_at_time,
        )
        self.session.add(conversation)
        await self.session.flush()
        await self.session.refresh(conversation)
        return conversation

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

        # Handle session in 'prepared' or committed state (background task scenario)
        # by creating a new session for this operation
        from nikita.db.database import get_session_maker

        try:
            await self.session.flush()
            await self.session.refresh(conversation)
            return conversation
        except Exception as e:
            # Session is in bad state (prepared/committed), use a new session
            if "prepared" in str(e) or "committed" in str(e):
                logger.warning(f"Session in bad state, creating new session: {e}")
                session_maker = get_session_maker()
                async with session_maker() as new_session:
                    # Re-fetch and update with new session
                    from sqlalchemy import select

                    stmt = select(Conversation).where(Conversation.id == conversation_id)
                    result = await new_session.execute(stmt)
                    fresh_conversation = result.scalar_one_or_none()
                    if fresh_conversation is None:
                        # Race condition: conversation not yet committed, create new one
                        logger.warning(
                            f"Conversation {conversation_id} not found in fallback, "
                            "creating new conversation entry"
                        )
                        fresh_conversation = Conversation(
                            id=conversation_id,
                            user_id=conversation.user_id,
                            platform=conversation.platform,
                            started_at=conversation.started_at,
                            last_message_at=datetime.now(UTC),
                            status="active",
                            messages=[],  # Explicitly initialize to avoid None
                            # Copy game state fields from original conversation
                            # Default chapter_at_time to 1 if None (defensive)
                            chapter_at_time=conversation.chapter_at_time or 1,
                            is_boss_fight=conversation.is_boss_fight or False,
                            score_delta=conversation.score_delta,
                        )
                        new_session.add(fresh_conversation)
                    fresh_conversation.add_message(role, content, analysis)
                    fresh_conversation.last_message_at = datetime.now(UTC)
                    await new_session.commit()
                    return fresh_conversation
            raise

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

    async def get_paginated(
        self,
        user_id: UUID,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Conversation], int]:
        """Get paginated conversations for a user with total count.

        Args:
            user_id: The user's UUID.
            offset: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            Tuple of (conversations list, total count).
        """
        # Get total count
        count_stmt = (
            select(func.count())
            .select_from(Conversation)
            .where(Conversation.user_id == user_id)
        )
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar_one()

        # Get paginated results
        stmt = (
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.started_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        conversations = list(result.scalars().all())

        return conversations, total

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
        conversation.processing_started_at = datetime.now(UTC)  # Spec 031 T4.1

        await self.session.flush()
        await self.session.refresh(conversation)

        return conversation

    async def detect_stuck(
        self,
        timeout_minutes: int = 30,
        limit: int = 50,
    ) -> list[UUID]:
        """Detect conversations stuck in processing state (Spec 031 T4.2).

        Args:
            timeout_minutes: Minutes before considering processing stuck.
            limit: Maximum conversations to return.

        Returns:
            List of conversation IDs stuck in processing state.
        """
        cutoff_time = datetime.now(UTC) - timedelta(minutes=timeout_minutes)

        stmt = (
            select(Conversation.id)
            .where(Conversation.status == "processing")
            .where(Conversation.processing_started_at.isnot(None))
            .where(Conversation.processing_started_at < cutoff_time)
            .order_by(Conversation.processing_started_at.asc())
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

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

    async def get_conversation_summaries_for_prompt(
        self,
        user_id: UUID,
        exclude_conversation_id: UUID | None = None,
    ) -> dict[str, str | None]:
        """Get conversation summaries for prompt generation (Spec 045 WP-3).

        Returns last conversation summary, today's summaries, and this week's
        summaries as formatted strings, suitable for template injection.

        Token budget: ~1000 tokens total (200 last + 300 today + 500 week).

        Args:
            user_id: The user's UUID.
            exclude_conversation_id: Current conversation ID to exclude.

        Returns:
            Dict with keys: last_summary, today_summaries, week_summaries.
        """
        now = datetime.now(UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=7)

        # Last conversation summary (most recent processed, not current)
        last_summary = await self.get_last_conversation_summary(
            user_id, exclude_conversation_id
        )

        # Today's conversation summaries
        today_stmt = (
            select(Conversation.conversation_summary, Conversation.started_at)
            .where(Conversation.user_id == user_id)
            .where(Conversation.conversation_summary.isnot(None))
            .where(Conversation.started_at >= today_start)
            .order_by(Conversation.started_at.desc())
            .limit(5)
        )
        if exclude_conversation_id:
            today_stmt = today_stmt.where(Conversation.id != exclude_conversation_id)
        today_result = await self.session.execute(today_stmt)
        today_rows = today_result.all()

        today_text = None
        if today_rows:
            parts = []
            for summary, started_at in today_rows:
                time_str = started_at.strftime("%H:%M") if started_at else ""
                parts.append(f"- [{time_str}] {summary}")
            today_text = "\n".join(parts)
            # Truncate to ~300 tokens (~1200 chars)
            if len(today_text) > 1200:
                today_text = today_text[:1197] + "..."

        # Week's conversation summaries (excluding today)
        week_stmt = (
            select(Conversation.conversation_summary, Conversation.started_at)
            .where(Conversation.user_id == user_id)
            .where(Conversation.conversation_summary.isnot(None))
            .where(Conversation.started_at >= week_start)
            .where(Conversation.started_at < today_start)
            .order_by(Conversation.started_at.desc())
            .limit(10)
        )
        if exclude_conversation_id:
            week_stmt = week_stmt.where(Conversation.id != exclude_conversation_id)
        week_result = await self.session.execute(week_stmt)
        week_rows = week_result.all()

        week_text = None
        if week_rows:
            parts = []
            for summary, started_at in week_rows:
                day_str = started_at.strftime("%a %H:%M") if started_at else ""
                parts.append(f"- [{day_str}] {summary}")
            week_text = "\n".join(parts)
            # Truncate to ~500 tokens (~2000 chars)
            if len(week_text) > 2000:
                week_text = week_text[:1997] + "..."

        return {
            "last_summary": last_summary,
            "today_summaries": today_text,
            "week_summaries": week_text,
        }

    async def get_last_conversation_summary(
        self,
        user_id: UUID,
        current_conversation_id: UUID | None = None,
    ) -> str | None:
        """Get summary from user's last conversation (Spec 030 US-4 T4.1).

        Returns the conversation_summary from the most recent non-current
        conversation that is older than 24 hours.

        Args:
            user_id: The user's UUID.
            current_conversation_id: Optional ID of current conversation to exclude.

        Returns:
            Conversation summary string, or None if no prior conversations.

        Acceptance Criteria:
            - AC-T4.1.1: Returns conversation_summary from most recent non-current conversation
            - AC-T4.1.2: Excludes current session (by conversation_id)
            - AC-T4.1.3: Returns None if no prior conversations
            - AC-T4.1.4: Only returns summaries >24h old
        """
        # Only return summaries from conversations older than 24 hours
        cutoff_time = datetime.now(UTC) - timedelta(hours=24)

        stmt = (
            select(Conversation.conversation_summary)
            .where(Conversation.user_id == user_id)
            .where(Conversation.conversation_summary.isnot(None))
            .where(Conversation.started_at < cutoff_time)  # AC-T4.1.4: >24h old
            .order_by(Conversation.started_at.desc())
            .limit(1)
        )

        # AC-T4.1.2: Exclude current session if provided
        if current_conversation_id is not None:
            stmt = stmt.where(Conversation.id != current_conversation_id)

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def recover_stuck(
        self,
        timeout_minutes: int = 30,
        max_attempts: int = 3,
        limit: int = 50,
    ) -> list[UUID]:
        """Recover conversations stuck in processing state (Remediation Plan T1.2).

        Finds conversations stuck in 'processing' for longer than timeout_minutes
        and either resets them to 'active' (if under max_attempts) or marks them
        as 'failed' (if max_attempts exceeded).

        Args:
            timeout_minutes: Minutes before considering processing stuck.
            max_attempts: Maximum processing attempts before marking failed.
            limit: Maximum conversations to process.

        Returns:
            List of conversation IDs that were recovered.
        """
        stuck_ids = await self.detect_stuck(
            timeout_minutes=timeout_minutes,
            limit=limit,
        )

        recovered_ids: list[UUID] = []

        for conversation_id in stuck_ids:
            try:
                conversation = await self.get(conversation_id)
                if conversation is None:
                    continue

                if conversation.processing_attempts >= max_attempts:
                    # Too many attempts - mark as failed
                    conversation.status = "failed"
                    logger.warning(
                        f"Conversation {conversation_id} marked failed after "
                        f"{conversation.processing_attempts} attempts"
                    )
                else:
                    # Reset to active for retry
                    conversation.status = "active"
                    conversation.processing_started_at = None
                    logger.info(
                        f"Conversation {conversation_id} reset to active "
                        f"(attempt {conversation.processing_attempts})"
                    )

                await self.session.flush()
                recovered_ids.append(conversation_id)
            except Exception as e:
                logger.error(f"Failed to recover conversation {conversation_id}: {e}")

        return recovered_ids

    async def force_status_update(
        self,
        conversation_id: UUID,
        status: str,
    ) -> bool:
        """Force update conversation status via raw SQL (Remediation Plan T1.3).

        Last resort fallback when ORM operations fail. Uses raw SQL to ensure
        conversations never get stuck in 'processing' state indefinitely.

        Args:
            conversation_id: The conversation's UUID.
            status: New status ('processed', 'failed', 'active').

        Returns:
            True if update succeeded, False otherwise.
        """
        from sqlalchemy import text

        try:
            stmt = text(
                "UPDATE conversations SET status = :status, updated_at = :now "
                "WHERE id = :id"
            )
            await self.session.execute(
                stmt,
                {
                    "status": status,
                    "now": datetime.now(UTC),
                    "id": str(conversation_id),
                },
            )
            await self.session.commit()
            logger.info(f"Force updated conversation {conversation_id} to {status}")
            return True
        except Exception as e:
            logger.error(f"Force status update failed for {conversation_id}: {e}")
            return False

    async def get_recent_voice_summaries(
        self, user_id: UUID, limit: int = 3
    ) -> list[str]:
        """Get summaries from recent voice conversations (Spec 106 I14).

        Returns summary text from the most recent voice conversations
        to inject into text agent context for cross-platform continuity.

        Args:
            user_id: User's UUID.
            limit: Max number of summaries to return.

        Returns:
            List of summary strings from voice conversations.
        """
        stmt = (
            select(Conversation.conversation_summary)
            .where(
                Conversation.user_id == user_id,
                Conversation.platform == "voice",
                Conversation.conversation_summary.isnot(None),
                Conversation.conversation_summary != "",
            )
            .order_by(Conversation.started_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [row[0] for row in result.all()]
