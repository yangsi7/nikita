"""Summary Generator for Post-Processing Pipeline (Spec 021, T022).

Wraps existing summary logic to generate/update daily and weekly summaries.

AC-T022.1: SummaryGenerator class wraps existing summary logic
AC-T022.2: Generates/updates daily summary
AC-T022.3: Generates/updates weekly summary (if applicable)
AC-T022.4: Unit tests for generator
"""

import logging
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from nikita.db.database import get_async_session
from nikita.db.repositories.summary_repository import DailySummaryRepository
from nikita.db.repositories.conversation_repository import ConversationRepository

logger = logging.getLogger(__name__)


class SummaryGenerator:
    """Generates and updates daily/weekly summaries.

    Wraps DailySummaryRepository to:
    - Generate daily summaries from conversation data
    - Update weekly summaries (aggregate of daily)

    Attributes:
        session_factory: Factory function to create database sessions.
    """

    def __init__(
        self,
        session_factory: Callable | None = None,
    ) -> None:
        """Initialize SummaryGenerator.

        Args:
            session_factory: Optional factory to create sessions.
                             Defaults to get_async_session.
        """
        self._session_factory = session_factory or get_async_session

    async def generate(
        self,
        user_id: UUID,
        conversation_id: UUID,
    ) -> tuple[bool, bool]:
        """Generate or update summaries for a conversation.

        Args:
            user_id: User ID to generate summaries for.
            conversation_id: Conversation that triggered generation.

        Returns:
            Tuple of (daily_updated, weekly_updated).
        """
        daily_updated = False
        weekly_updated = False

        async with self._session_factory() as session:
            summary_repo = DailySummaryRepository(session)
            conversation_repo = ConversationRepository(session)

            # Get conversation data
            conversation = await conversation_repo.get(conversation_id)
            if not conversation:
                logger.warning(f"Conversation {conversation_id} not found")
                return daily_updated, weekly_updated

            today = datetime.now(timezone.utc).date()

            # Update daily summary
            daily_updated = await self._update_daily_summary(
                summary_repo=summary_repo,
                conversation_repo=conversation_repo,
                user_id=user_id,
                summary_date=today,
                conversation=conversation,
            )

            # Update weekly summary if it's end of week (Sunday)
            if today.weekday() == 6:  # Sunday
                weekly_updated = await self._update_weekly_summary(
                    summary_repo=summary_repo,
                    user_id=user_id,
                    week_end=today,
                )

            await session.commit()

        return daily_updated, weekly_updated

    async def _update_daily_summary(
        self,
        summary_repo: DailySummaryRepository,
        conversation_repo: ConversationRepository,
        user_id: UUID,
        summary_date: date,
        conversation: Any,
    ) -> bool:
        """Update or create daily summary.

        Args:
            summary_repo: DailySummaryRepository instance.
            conversation_repo: ConversationRepository instance.
            user_id: User ID.
            summary_date: Date for summary.
            conversation: Conversation entity.

        Returns:
            True if summary was updated/created.
        """
        try:
            # Get existing summary or create new
            existing = await summary_repo.get_by_date(user_id, summary_date)

            # Count conversations for today
            conversations_today = await self._count_conversations_today(
                conversation_repo, user_id, summary_date
            )

            # Extract summary text from conversation (simplified)
            summary_text = self._generate_summary_text(conversation)

            if existing:
                # Update existing summary
                await summary_repo.update_summary(
                    summary_id=existing.id,
                    summary_text=summary_text,
                    emotional_tone=self._detect_emotional_tone(conversation),
                )
            else:
                # Create new summary
                await summary_repo.create_summary(
                    user_id=user_id,
                    summary_date=summary_date,
                    conversations_count=conversations_today,
                    summary_text=summary_text,
                    emotional_tone=self._detect_emotional_tone(conversation),
                )

            logger.info(f"Daily summary updated for user {user_id} on {summary_date}")
            return True

        except Exception as e:
            logger.exception(f"Failed to update daily summary: {e}")
            return False

    async def _update_weekly_summary(
        self,
        summary_repo: DailySummaryRepository,
        user_id: UUID,
        week_end: date,
    ) -> bool:
        """Update or create weekly summary aggregate.

        Args:
            summary_repo: DailySummaryRepository instance.
            user_id: User ID.
            week_end: End date of the week (Sunday).

        Returns:
            True if weekly summary was updated.
        """
        try:
            week_start = week_end - timedelta(days=6)

            # Get all daily summaries for the week
            daily_summaries = await summary_repo.get_range(
                user_id=user_id,
                start_date=week_start,
                end_date=week_end,
            )

            if not daily_summaries:
                return False

            # Aggregate weekly data
            total_conversations = sum(
                s.conversations_count or 0 for s in daily_summaries
            )

            # Combine summary texts
            week_summary_parts = [
                s.summary_text for s in daily_summaries if s.summary_text
            ]
            week_summary = " | ".join(week_summary_parts) if week_summary_parts else None

            # For now, weekly summaries are stored as a special daily summary
            # on the week's Sunday with aggregated data
            existing = await summary_repo.get_by_date(user_id, week_end)
            if existing:
                await summary_repo.update_summary(
                    summary_id=existing.id,
                    summary_text=week_summary,
                    key_moments=[
                        {"type": "weekly_aggregate", "count": total_conversations}
                    ],
                )

            logger.info(
                f"Weekly summary updated for user {user_id}: "
                f"{total_conversations} conversations"
            )
            return True

        except Exception as e:
            logger.exception(f"Failed to update weekly summary: {e}")
            return False

    async def _count_conversations_today(
        self,
        conversation_repo: ConversationRepository,
        user_id: UUID,
        summary_date: date,
    ) -> int:
        """Count conversations for a specific date.

        Args:
            conversation_repo: ConversationRepository instance.
            user_id: User ID.
            summary_date: Date to count for.

        Returns:
            Number of conversations.
        """
        try:
            conversations = await conversation_repo.list_recent(user_id, limit=100)
            return sum(
                1
                for c in conversations
                if c.created_at.date() == summary_date
            )
        except Exception:
            return 0

    def _generate_summary_text(self, conversation: Any) -> str:
        """Generate summary text from conversation.

        Args:
            conversation: Conversation entity.

        Returns:
            Summary text.
        """
        # Simplified summary generation
        # In production, this would use LLM to summarize
        if hasattr(conversation, "transcript") and conversation.transcript:
            message_count = len(conversation.transcript)
            return f"Conversation with {message_count} messages"
        return "Brief conversation"

    def _detect_emotional_tone(self, conversation: Any) -> str:
        """Detect emotional tone from conversation.

        Args:
            conversation: Conversation entity.

        Returns:
            Emotional tone (positive/neutral/negative).
        """
        # Simplified tone detection
        # In production, this would use LLM or sentiment analysis
        return "neutral"

    async def generate_daily(
        self,
        user_id: UUID,
        summary_date: date | None = None,
    ) -> bool:
        """Generate daily summary for a specific date.

        Args:
            user_id: User ID.
            summary_date: Date for summary (defaults to today).

        Returns:
            True if summary was generated.
        """
        if summary_date is None:
            summary_date = datetime.now(timezone.utc).date()

        async with self._session_factory() as session:
            summary_repo = DailySummaryRepository(session)
            conversation_repo = ConversationRepository(session)

            # Get conversations for the date
            conversations = await conversation_repo.list_recent(user_id, limit=50)
            date_conversations = [
                c for c in conversations if c.created_at.date() == summary_date
            ]

            if not date_conversations:
                return False

            # Create summary from aggregated conversations
            total_messages = sum(
                len(c.transcript) if hasattr(c, "transcript") and c.transcript else 0
                for c in date_conversations
            )

            existing = await summary_repo.get_by_date(user_id, summary_date)

            if existing:
                await summary_repo.update_summary(
                    summary_id=existing.id,
                    summary_text=f"Day with {len(date_conversations)} conversations, {total_messages} messages",
                )
            else:
                await summary_repo.create_summary(
                    user_id=user_id,
                    summary_date=summary_date,
                    conversations_count=len(date_conversations),
                    summary_text=f"Day with {len(date_conversations)} conversations, {total_messages} messages",
                )

            await session.commit()

        return True


# Module-level singleton
_default_generator: SummaryGenerator | None = None


def get_summary_generator() -> SummaryGenerator:
    """Get the singleton SummaryGenerator instance.

    Returns:
        Cached SummaryGenerator instance.
    """
    global _default_generator
    if _default_generator is None:
        _default_generator = SummaryGenerator()
    return _default_generator
