"""Repository for scheduled event operations.

Handles storage, retrieval, and management of scheduled events for
delayed message delivery across both Telegram and voice platforms.

Spec: 011-background-tasks, T2.2
Spec: 007-voice-agent, FR-013 (Unified Event Scheduling)
"""

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.base import utc_now
from nikita.db.models.scheduled_event import (
    EventPlatform,
    EventStatus,
    EventType,
    ScheduledEvent,
)


class ScheduledEventRepository:
    """Repository for scheduled event operations.

    Supports unified event scheduling for both text (Telegram) and
    voice (ElevenLabs) platforms with:
    - Due event retrieval for delivery
    - Status management (pending -> delivered/failed)
    - Retry tracking
    - Platform-specific filtering
    """

    # Maximum retry attempts before marking as failed
    MAX_RETRIES = 3

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: Async SQLAlchemy session for database operations.
        """
        self._session = session

    @property
    def session(self) -> AsyncSession:
        """Access the database session."""
        return self._session

    async def create_event(
        self,
        user_id: UUID,
        platform: EventPlatform | str,
        event_type: EventType | str,
        content: dict[str, Any],
        scheduled_at: datetime,
        source_conversation_id: UUID | None = None,
    ) -> ScheduledEvent:
        """Create a new scheduled event.

        Args:
            user_id: User this event is for.
            platform: Target platform ('telegram' or 'voice').
            event_type: Type of event ('message_delivery', 'call_reminder', etc).
            content: Platform-specific payload (JSONB).
            scheduled_at: When to deliver the event.
            source_conversation_id: Optional reference to originating conversation.

        Returns:
            The created ScheduledEvent.

        Example content for Telegram:
            {"chat_id": 123456789, "text": "Hey, I was thinking..."}

        Example content for Voice:
            {"voice_prompt": "Call reminder", "agent_id": "nikita_ch3"}
        """
        # Handle enum values
        platform_value = platform.value if isinstance(platform, EventPlatform) else platform
        event_type_value = event_type.value if isinstance(event_type, EventType) else event_type

        event = ScheduledEvent(
            user_id=user_id,
            platform=platform_value,
            event_type=event_type_value,
            content=content,
            scheduled_at=scheduled_at,
            source_conversation_id=source_conversation_id,
            status=EventStatus.PENDING.value,
            retry_count=0,
        )

        self._session.add(event)
        await self._session.flush()
        await self._session.refresh(event)

        return event

    async def get_due_events(
        self,
        limit: int = 50,
        platform: EventPlatform | str | None = None,
    ) -> list[ScheduledEvent]:
        """Get events that are due for delivery.

        Args:
            limit: Maximum number of events to return.
            platform: Optional platform filter.

        Returns:
            List of pending events past their scheduled_at time.
        """
        now = utc_now()

        stmt = (
            select(ScheduledEvent)
            .where(
                ScheduledEvent.status == EventStatus.PENDING.value,
                ScheduledEvent.scheduled_at <= now,
            )
            .order_by(ScheduledEvent.scheduled_at)
            .limit(limit)
        )

        # Optional platform filter
        if platform:
            platform_value = platform.value if isinstance(platform, EventPlatform) else platform
            stmt = stmt.where(ScheduledEvent.platform == platform_value)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def mark_delivered(self, event_id: UUID) -> bool:
        """Mark an event as successfully delivered.

        Args:
            event_id: Event ID to mark as delivered.

        Returns:
            True if event was found and updated, False otherwise.
        """
        stmt = (
            update(ScheduledEvent)
            .where(ScheduledEvent.id == event_id)
            .values(
                status=EventStatus.DELIVERED.value,
                delivered_at=utc_now(),
            )
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def mark_failed(
        self,
        event_id: UUID,
        error_message: str | None = None,
        increment_retry: bool = True,
    ) -> bool:
        """Mark an event as failed (with optional retry).

        If increment_retry is True and retry count is under MAX_RETRIES,
        the event remains pending for retry. Otherwise, it's marked failed.

        Args:
            event_id: Event ID to mark.
            error_message: Optional error details.
            increment_retry: Whether to increment retry counter.

        Returns:
            True if event was found and updated, False otherwise.
        """
        # First get current retry count
        stmt = select(ScheduledEvent).where(ScheduledEvent.id == event_id)
        result = await self._session.execute(stmt)
        event = result.scalar_one_or_none()

        if not event:
            return False

        new_retry_count = event.retry_count + 1 if increment_retry else event.retry_count

        # Determine new status
        if new_retry_count >= self.MAX_RETRIES:
            new_status = EventStatus.FAILED.value
        else:
            new_status = EventStatus.PENDING.value  # Keep pending for retry

        # Calculate next retry time with exponential backoff
        if new_status == EventStatus.PENDING.value and increment_retry:
            # Backoff: 1 min, 2 min, 4 min...
            backoff_minutes = 2 ** (new_retry_count - 1)
            new_scheduled_at = utc_now() + timedelta(minutes=backoff_minutes)
        else:
            new_scheduled_at = event.scheduled_at  # Keep original if not retrying

        update_stmt = (
            update(ScheduledEvent)
            .where(ScheduledEvent.id == event_id)
            .values(
                status=new_status,
                retry_count=new_retry_count,
                error_message=error_message,
                scheduled_at=new_scheduled_at,
            )
        )
        await self._session.execute(update_stmt)
        return True

    async def cancel_event(self, event_id: UUID) -> bool:
        """Cancel a pending event.

        Args:
            event_id: Event ID to cancel.

        Returns:
            True if event was found and cancelled, False otherwise.
        """
        stmt = (
            update(ScheduledEvent)
            .where(
                ScheduledEvent.id == event_id,
                ScheduledEvent.status == EventStatus.PENDING.value,
            )
            .values(status=EventStatus.CANCELLED.value)
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def get_user_pending_events(
        self,
        user_id: UUID,
        platform: EventPlatform | str | None = None,
    ) -> list[ScheduledEvent]:
        """Get all pending events for a user.

        Args:
            user_id: User ID to get events for.
            platform: Optional platform filter.

        Returns:
            List of pending events for the user.
        """
        stmt = (
            select(ScheduledEvent)
            .where(
                ScheduledEvent.user_id == user_id,
                ScheduledEvent.status == EventStatus.PENDING.value,
            )
            .order_by(ScheduledEvent.scheduled_at)
        )

        if platform:
            platform_value = platform.value if isinstance(platform, EventPlatform) else platform
            stmt = stmt.where(ScheduledEvent.platform == platform_value)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def cancel_user_pending_events(
        self,
        user_id: UUID,
        platform: EventPlatform | str | None = None,
    ) -> int:
        """Cancel all pending events for a user.

        Useful when user has game_over or other status changes
        that should clear their scheduled events.

        Args:
            user_id: User ID to cancel events for.
            platform: Optional platform filter.

        Returns:
            Number of events cancelled.
        """
        stmt = (
            update(ScheduledEvent)
            .where(
                ScheduledEvent.user_id == user_id,
                ScheduledEvent.status == EventStatus.PENDING.value,
            )
            .values(status=EventStatus.CANCELLED.value)
        )

        if platform:
            platform_value = platform.value if isinstance(platform, EventPlatform) else platform
            stmt = stmt.where(ScheduledEvent.platform == platform_value)

        result = await self._session.execute(stmt)
        return result.rowcount

    async def cleanup_stale_events(self, max_age_hours: int = 48) -> int:
        """Mark very old pending events as failed.

        Events older than max_age_hours that are still pending
        are likely stuck and should be marked failed.

        Args:
            max_age_hours: Maximum age in hours for pending events.

        Returns:
            Number of stale events marked as failed.
        """
        cutoff = utc_now() - timedelta(hours=max_age_hours)

        stmt = (
            update(ScheduledEvent)
            .where(
                ScheduledEvent.status == EventStatus.PENDING.value,
                ScheduledEvent.scheduled_at < cutoff,
            )
            .values(
                status=EventStatus.FAILED.value,
                error_message=f"Stale event (older than {max_age_hours} hours)",
            )
        )

        result = await self._session.execute(stmt)
        return result.rowcount
