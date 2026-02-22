"""Voice event scheduling for cross-platform message delivery.

This module implements VoiceEventScheduler which enables:
- Scheduling voice call reminders
- Cross-platform follow-ups (text → voice, voice → text)
- Chapter-based delay calculation

Implements US-8 (Unified Event Scheduling) acceptance criteria:
- AC-FR013-001: Voice follow-up scheduled with platform='voice'
- AC-FR013-002: Cross-platform events work
- AC-FR013-003: Correct platform handler invoked
- AC-FR013-004: Chapter-based delay calculation
"""

import logging
import random
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    from nikita.db.models.scheduled_event import ScheduledEvent
    from nikita.db.models.user import User

logger = logging.getLogger(__name__)

# Chapter-based delay ranges (in seconds)
# Chapter 1: Nikita is distant, responds slower
# Chapter 5: Nikita is intimate, responds quickly
CHAPTER_DELAY_RANGES: dict[int, tuple[int, int]] = {
    1: (120, 300),   # 2-5 minutes
    2: (60, 180),    # 1-3 minutes
    3: (30, 120),    # 30s-2 minutes
    4: (10, 60),     # 10s-1 minute
    5: (5, 30),      # 5-30 seconds
}


class VoiceEventScheduler:
    """Scheduler for voice-related events with cross-platform support.

    Enables:
    - Scheduling voice call reminders
    - Cross-platform follow-ups (text → voice, voice → text)
    - Chapter-based delay calculation
    """

    def get_chapter_delay(self, user: "User") -> int:
        """
        Calculate delay based on user's chapter.

        AC-FR013-004: Uses chapter-based delay logic.

        Args:
            user: User model with chapter attribute

        Returns:
            Delay in seconds
        """
        chapter = getattr(user, "chapter", 3)
        min_delay, max_delay = CHAPTER_DELAY_RANGES.get(chapter, (30, 120))
        return random.randint(min_delay, max_delay)

    async def schedule_follow_up(
        self,
        user_id: UUID,
        event_type: str,
        content: dict[str, Any],
        delay_seconds: int,
        source_conversation_id: UUID | None = None,
        platform: str = "voice",
    ) -> "ScheduledEvent":
        """
        Schedule a follow-up event.

        AC-T043.1: Creates event with specified parameters
        AC-T043.4: Links source_conversation_id for traceability

        Args:
            user_id: User UUID
            event_type: Type of event (call_reminder, follow_up, etc.)
            content: Platform-specific payload
            delay_seconds: Seconds to wait before delivery
            source_conversation_id: Optional originating conversation
            platform: Target platform ('voice' or 'telegram')

        Returns:
            Created ScheduledEvent
        """
        scheduled_at = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)

        return await self._create_event(
            user_id=user_id,
            event_type=event_type,
            content=content,
            scheduled_at=scheduled_at,
            source_conversation_id=source_conversation_id,
            platform=platform,
        )

    async def schedule_voice_call(
        self,
        user_id: UUID,
        delay_hours: float,
        prompt: str,
        source_platform: str | None = None,
        source_conversation_id: UUID | None = None,
    ) -> "ScheduledEvent":
        """
        Schedule a voice call reminder.

        AC-FR013-001: Follow-up scheduled with platform='voice'
        AC-FR013-002: Cross-platform events work

        Args:
            user_id: User UUID
            delay_hours: Hours to wait before call
            prompt: Voice prompt for Nikita
            source_platform: Optional source platform (for cross-platform tracking)
            source_conversation_id: Optional originating conversation

        Returns:
            Created ScheduledEvent
        """
        from nikita.config.settings import get_settings

        settings = get_settings()
        delay_seconds = int(delay_hours * 3600)

        content = {
            "voice_prompt": prompt,
            "agent_id": settings.elevenlabs_default_agent_id,
            "source_platform": source_platform,
        }

        logger.info(
            f"[SCHEDULER] Scheduling voice call for user {user_id} "
            f"in {delay_hours} hours"
        )

        return await self._create_event(
            user_id=user_id,
            event_type="call_reminder",
            content=content,
            scheduled_at=datetime.now(timezone.utc) + timedelta(seconds=delay_seconds),
            source_conversation_id=source_conversation_id,
            platform="voice",
        )

    async def schedule_telegram_message(
        self,
        user_id: UUID,
        telegram_id: int,
        text: str,
        delay_seconds: int,
        source_conversation_id: UUID | None = None,
    ) -> "ScheduledEvent":
        """
        Schedule a Telegram message from voice context.

        Enables voice → text cross-platform events.

        Args:
            user_id: User UUID
            telegram_id: User's Telegram chat ID
            text: Message text
            delay_seconds: Seconds to wait before delivery
            source_conversation_id: Optional originating conversation

        Returns:
            Created ScheduledEvent
        """
        content = {
            "chat_id": telegram_id,
            "text": text,
        }

        logger.info(
            f"[SCHEDULER] Scheduling Telegram message for user {user_id} "
            f"in {delay_seconds} seconds"
        )

        return await self._create_event(
            user_id=user_id,
            event_type="message_delivery",
            content=content,
            scheduled_at=datetime.now(timezone.utc) + timedelta(seconds=delay_seconds),
            source_conversation_id=source_conversation_id,
            platform="telegram",
        )

    async def _create_event(
        self,
        user_id: UUID,
        event_type: str,
        content: dict[str, Any],
        scheduled_at: datetime,
        source_conversation_id: UUID | None,
        platform: str,
    ) -> "ScheduledEvent":
        """
        Create event in database.

        Args:
            user_id: User UUID
            event_type: Type of event
            content: Payload dictionary
            scheduled_at: When to deliver
            source_conversation_id: Optional source conversation
            platform: Target platform

        Returns:
            Created ScheduledEvent
        """
        from nikita.db.database import get_session_maker
        from nikita.db.repositories.scheduled_event_repository import (
            ScheduledEventRepository,
        )

        session_maker = get_session_maker()
        async with session_maker() as session:
            repo = ScheduledEventRepository(session)
            event = await repo.create(
                user_id=user_id,
                platform=platform,
                event_type=event_type,
                content=content,
                scheduled_at=scheduled_at,
                source_conversation_id=source_conversation_id,
            )
            await session.commit()

            logger.info(
                f"[SCHEDULER] Created event {event.id}: "
                f"type={event_type}, platform={platform}, "
                f"scheduled_at={scheduled_at}"
            )

            return event


class EventDeliveryHandler:
    """Handles delivery of scheduled events to various platforms.

    AC-T044.1: Handles 'telegram' platform events
    AC-T044.2: Handles 'voice' platform events
    AC-T044.3: Marks events as delivered after success
    """

    async def deliver(self, event: "ScheduledEvent") -> bool:
        """
        Deliver a scheduled event.

        Routes to appropriate platform handler.

        Args:
            event: ScheduledEvent to deliver

        Returns:
            True if delivery succeeded
        """
        platform = event.platform

        if platform == "voice":
            success = await self._deliver_voice_event(event)
        elif platform == "telegram":
            success = await self._deliver_telegram_event(event)
        else:
            logger.warning(f"[DELIVERY] Unknown platform: {platform}")
            return False

        if success:
            await self._mark_delivered(event)

        return success

    async def _deliver_voice_event(self, event: "ScheduledEvent") -> bool:
        """
        Deliver voice event (initiate outbound call).

        AC-T044.2: Voice platform events trigger voice handler.

        Args:
            event: Voice event to deliver

        Returns:
            True if call initiated successfully
        """
        try:
            from nikita.agents.voice.service import get_voice_service
            from nikita.db.database import get_session_maker
            from nikita.db.repositories.user_repository import UserRepository

            content = event.content
            voice_prompt = content.get("voice_prompt")

            # Load user for phone number
            session_maker = get_session_maker()
            async with session_maker() as session:
                user_repo = UserRepository(session)
                user = await user_repo.get(event.user_id)

            if not user or not user.phone:
                logger.warning(
                    f"[DELIVERY] No phone for user {event.user_id}, "
                    "cannot initiate voice call"
                )
                return False

            # Build config override with voice_prompt
            config_override = None
            if voice_prompt:
                config_override = {"agent": {"prompt": {"prompt": voice_prompt}}}

            voice_service = get_voice_service()
            result = await voice_service.make_outbound_call(
                to_number=user.phone,
                user_id=event.user_id,
                conversation_config_override=config_override,
            )

            success = result.get("success", False)
            if success:
                logger.info(
                    f"[DELIVERY] Voice call initiated for user {event.user_id}: "
                    f"conversation_id={result.get('conversation_id')}"
                )
            else:
                logger.warning(
                    f"[DELIVERY] Voice call failed for user {event.user_id}: "
                    f"{result.get('error', 'Unknown error')}"
                )

            return success

        except Exception as e:
            logger.error(f"[DELIVERY] Voice event failed: {e}", exc_info=True)
            return False

    async def _deliver_telegram_event(self, event: "ScheduledEvent") -> bool:
        """
        Deliver Telegram message event.

        AC-T044.1: Telegram platform events send messages.

        Args:
            event: Telegram event to deliver

        Returns:
            True if message sent successfully
        """
        try:
            from nikita.platforms.telegram.bot import TelegramBot

            bot = TelegramBot()
            content = event.content

            chat_id = content.get("chat_id")
            text = content.get("text", "")

            if not chat_id or not text:
                logger.error("[DELIVERY] Missing chat_id or text in Telegram event")
                return False

            await bot.send_message(chat_id=chat_id, text=text)

            logger.info(f"[DELIVERY] Sent Telegram message to chat {chat_id}")
            return True

        except Exception as e:
            logger.error(f"[DELIVERY] Telegram event failed: {e}", exc_info=True)
            return False

    async def _mark_delivered(self, event: "ScheduledEvent") -> None:
        """
        Mark event as delivered.

        AC-T044.3: Marks events as delivered after successful send.

        Args:
            event: Event to mark as delivered
        """
        from nikita.db.database import get_session_maker
        from nikita.db.repositories.scheduled_event_repository import (
            ScheduledEventRepository,
        )

        session_maker = get_session_maker()
        async with session_maker() as session:
            repo = ScheduledEventRepository(session)
            await repo.mark_delivered(event.id)
            await session.commit()

            logger.info(f"[DELIVERY] Marked event {event.id} as delivered")


# Singleton instances
_scheduler: VoiceEventScheduler | None = None
_delivery_handler: EventDeliveryHandler | None = None


def get_voice_scheduler() -> VoiceEventScheduler:
    """Get voice scheduler singleton."""
    global _scheduler
    if _scheduler is None:
        _scheduler = VoiceEventScheduler()
    return _scheduler


def get_delivery_handler() -> EventDeliveryHandler:
    """Get delivery handler singleton."""
    global _delivery_handler
    if _delivery_handler is None:
        _delivery_handler = EventDeliveryHandler()
    return _delivery_handler
