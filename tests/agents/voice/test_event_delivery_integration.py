"""Integration tests for event delivery pipeline.

Tests EventDeliveryHandler routing: scheduled_event -> platform-specific delivery.
Verifies voice/telegram routing, failure handling, and batch delivery.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_event(platform="voice", voice_prompt="Hey there!", chat_id=None, text=None):
    """Build a minimal ScheduledEvent mock."""
    event = MagicMock()
    event.id = uuid4()
    event.platform = platform
    event.event_type = "call_reminder" if platform == "voice" else "message_delivery"
    event.status = "pending"
    event.user_id = uuid4()
    event.scheduled_at = datetime.now(timezone.utc) - timedelta(minutes=1)

    if platform == "voice":
        event.content = {
            "voice_prompt": voice_prompt,
            "agent_id": "test_agent_id",
        }
    elif platform == "telegram":
        event.content = {
            "chat_id": chat_id or 12345,
            "text": text or "Hello from Nikita!",
        }
    return event


def _make_user(phone="+41787950009"):
    """Build a minimal User mock."""
    user = MagicMock()
    user.id = uuid4()
    user.phone = phone
    user.chapter = 3
    user.game_status = "active"
    return user


def _patch_delivery_deps(user, call_result=None):
    """Create context managers for patching EventDeliveryHandler dependencies.

    Note: scheduling.py uses lazy imports (from nikita.db.database import get_session_maker)
    inside method bodies, so we must patch at the source module.
    """
    mock_voice_service = MagicMock()
    mock_voice_service.make_outbound_call = AsyncMock(
        return_value=call_result or {"success": True, "conversation_id": "conv_123"}
    )

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.commit = AsyncMock()
    mock_session_maker = MagicMock(return_value=mock_session)

    mock_user_repo = MagicMock()
    mock_user_repo.get = AsyncMock(return_value=user)

    mock_event_repo = MagicMock()
    mock_event_repo.mark_delivered = AsyncMock()

    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock()

    patches = {
        "voice_service": patch(
            "nikita.agents.voice.service.get_voice_service",
            return_value=mock_voice_service,
        ),
        "session_maker": patch(
            "nikita.db.database.get_session_maker",
            return_value=mock_session_maker,
        ),
        "user_repo": patch(
            "nikita.db.repositories.user_repository.UserRepository",
            return_value=mock_user_repo,
        ),
        "event_repo": patch(
            "nikita.db.repositories.scheduled_event_repository.ScheduledEventRepository",
            return_value=mock_event_repo,
        ),
        "bot": patch(
            "nikita.platforms.telegram.bot.TelegramBot",
            return_value=mock_bot,
        ),
    }

    return patches, {
        "voice_service": mock_voice_service,
        "user_repo": mock_user_repo,
        "event_repo": mock_event_repo,
        "bot": mock_bot,
        "session_maker": mock_session_maker,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestEventDeliveryIntegration:
    """Integration tests for EventDeliveryHandler routing and delivery."""

    async def test_voice_event_routes_to_make_outbound_call(self):
        """Platform='voice' event -> EventDeliveryHandler -> VoiceService.make_outbound_call."""
        from nikita.agents.voice.scheduling import EventDeliveryHandler

        event = _make_event(platform="voice", voice_prompt="Missing you!")
        user = _make_user(phone="+41787950009")
        patches, mocks = _patch_delivery_deps(user)

        with patches["voice_service"], patches["session_maker"], patches["user_repo"], \
             patches["event_repo"]:
            handler = EventDeliveryHandler()
            result = await handler.deliver(event)

        assert result is True
        mocks["voice_service"].make_outbound_call.assert_called_once()
        call_kwargs = mocks["voice_service"].make_outbound_call.call_args.kwargs
        assert call_kwargs["to_number"] == "+41787950009"
        assert call_kwargs["user_id"] == event.user_id

    async def test_telegram_event_routes_to_send_message(self):
        """Platform='telegram' event -> EventDeliveryHandler -> bot.send_message."""
        from nikita.agents.voice.scheduling import EventDeliveryHandler

        event = _make_event(platform="telegram", chat_id=99999, text="Hi from Nikita!")
        patches, mocks = _patch_delivery_deps(None)

        with patches["bot"], patches["session_maker"], patches["event_repo"]:
            handler = EventDeliveryHandler()
            result = await handler.deliver(event)

        assert result is True
        mocks["bot"].send_message.assert_called_once()
        call_kwargs = mocks["bot"].send_message.call_args.kwargs
        assert call_kwargs["chat_id"] == 99999
        assert call_kwargs["text"] == "Hi from Nikita!"

    async def test_mixed_platform_batch_delivery(self):
        """Batch with voice+telegram events -> each routed to correct handler."""
        from nikita.agents.voice.scheduling import EventDeliveryHandler

        voice_event = _make_event(platform="voice")
        telegram_event = _make_event(platform="telegram", chat_id=111, text="Hey!")
        user = _make_user(phone="+41787950009")
        patches, mocks = _patch_delivery_deps(user)

        with patches["voice_service"], patches["session_maker"], patches["user_repo"], \
             patches["event_repo"], patches["bot"]:
            handler = EventDeliveryHandler()
            voice_result = await handler.deliver(voice_event)
            telegram_result = await handler.deliver(telegram_event)

        assert voice_result is True
        assert telegram_result is True
        mocks["voice_service"].make_outbound_call.assert_called_once()
        mocks["bot"].send_message.assert_called_once()

    async def test_failed_delivery_returns_false(self):
        """Voice call fails -> deliver() returns False."""
        from nikita.agents.voice.scheduling import EventDeliveryHandler

        event = _make_event(platform="voice")
        user = _make_user(phone="+41787950009")
        patches, mocks = _patch_delivery_deps(
            user, call_result={"success": False, "error": "ElevenLabs API error: 500"}
        )

        with patches["voice_service"], patches["session_maker"], patches["user_repo"]:
            handler = EventDeliveryHandler()
            result = await handler.deliver(event)

        assert result is False

    async def test_missing_phone_skips_voice_delivery(self):
        """User has no phone -> deliver returns False."""
        from nikita.agents.voice.scheduling import EventDeliveryHandler

        event = _make_event(platform="voice")
        user = _make_user(phone=None)
        patches, mocks = _patch_delivery_deps(user)

        with patches["voice_service"], patches["session_maker"], patches["user_repo"]:
            handler = EventDeliveryHandler()
            result = await handler.deliver(event)

        assert result is False
        mocks["voice_service"].make_outbound_call.assert_not_called()

    async def test_delivery_creates_job_execution_record(self):
        """deliver_pending_messages() -> job_execution started -> events processed -> job completed with counts."""
        from nikita.db.models.scheduled_event import EventPlatform

        voice_event = MagicMock()
        voice_event.id = uuid4()
        voice_event.platform = EventPlatform.VOICE.value
        voice_event.user_id = uuid4()
        voice_event.content = {"voice_prompt": "Hey!", "agent_id": "test"}

        user = _make_user(phone="+41787950009")

        mock_event_repo = MagicMock()
        mock_event_repo.get_due_events = AsyncMock(return_value=[voice_event])
        mock_event_repo.mark_delivered = AsyncMock()
        mock_event_repo.mark_failed = AsyncMock()

        mock_user_repo = MagicMock()
        mock_user_repo.get = AsyncMock(return_value=user)

        mock_execution = MagicMock()
        mock_execution.id = uuid4()
        mock_job_repo = MagicMock()
        mock_job_repo.start_execution = AsyncMock(return_value=mock_execution)
        mock_job_repo.complete_execution = AsyncMock()

        mock_voice_service = MagicMock()
        mock_voice_service.make_outbound_call = AsyncMock(
            return_value={"success": True, "conversation_id": "conv_xyz"}
        )

        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock()
        mock_bot.close = AsyncMock()

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_maker = MagicMock(return_value=mock_session)

        with patch(
            "nikita.api.routes.tasks.get_session_maker",
            return_value=mock_session_maker,
        ), patch(
            "nikita.db.repositories.scheduled_event_repository.ScheduledEventRepository",
            return_value=mock_event_repo,
        ), patch(
            "nikita.db.repositories.user_repository.UserRepository",
            return_value=mock_user_repo,
        ), patch(
            "nikita.api.routes.tasks.JobExecutionRepository",
            return_value=mock_job_repo,
        ), patch(
            "nikita.agents.voice.service.get_voice_service",
            return_value=mock_voice_service,
        ), patch(
            "nikita.platforms.telegram.bot.TelegramBot",
            return_value=mock_bot,
        ):
            from nikita.api.routes.tasks import deliver_pending_messages
            result = await deliver_pending_messages()

        # Job execution started and completed
        mock_job_repo.start_execution.assert_called_once()
        mock_job_repo.complete_execution.assert_called_once()
        complete_args = mock_job_repo.complete_execution.call_args
        assert complete_args[0][0] == mock_execution.id  # positional arg

        # Event delivered
        assert result["delivered"] == 1
        assert result["failed"] == 0
