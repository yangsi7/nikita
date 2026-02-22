"""Tests for outbound voice call delivery wiring (Wave G-Tier2).

Tests:
- EventDeliveryHandler._deliver_voice_event() with valid phone -> calls make_outbound_call
- _deliver_voice_event() with no phone -> returns False
- _deliver_voice_event() with no user -> returns False
- _deliver_voice_event() with call failure -> returns False
- _deliver_voice_event() passes config_override with voice_prompt
- tasks.py voice delivery: success path -> mark_delivered
- tasks.py voice delivery: no phone -> mark_failed
- tasks.py voice delivery: call failure -> mark_failed
- tasks.py voice delivery: no user -> mark_failed
- Config override passes voice_prompt correctly
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_voice_event(voice_prompt: str = "Hey, I was thinking about you!") -> MagicMock:
    """Build a minimal voice ScheduledEvent mock."""
    event = MagicMock()
    event.id = uuid4()
    event.platform = "voice"
    event.event_type = "call_reminder"
    event.status = "pending"
    event.user_id = uuid4()
    event.content = {
        "voice_prompt": voice_prompt,
        "agent_id": "test_agent_id",
    }
    event.scheduled_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    return event


def _make_user(phone: str | None = "+41787950009") -> MagicMock:
    """Build a minimal User mock."""
    user = MagicMock()
    user.id = uuid4()
    user.phone = phone
    user.chapter = 3
    user.game_status = "active"
    return user


# ---------------------------------------------------------------------------
# EventDeliveryHandler._deliver_voice_event() tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestDeliverVoiceEventHandler:
    """Tests for EventDeliveryHandler._deliver_voice_event() in scheduling.py."""

    def _patch_scheduling_imports(self, user, call_result=None):
        """Return a context manager tuple patching the three lazy imports in
        EventDeliveryHandler._deliver_voice_event().

        Because the imports happen inside the method body, we must patch the
        symbols at their source modules, not at the scheduling module itself.
        """
        mock_voice_service = MagicMock()
        mock_voice_service.make_outbound_call = AsyncMock(
            return_value=call_result or {"success": True, "conversation_id": "conv_123"}
        )

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_maker = MagicMock(return_value=mock_session)

        mock_user_repo = MagicMock()
        mock_user_repo.get = AsyncMock(return_value=user)

        patches = [
            patch(
                "nikita.agents.voice.service.get_voice_service",
                return_value=mock_voice_service,
            ),
            patch(
                "nikita.db.database.get_session_maker",
                return_value=mock_session_maker,
            ),
            patch(
                "nikita.db.repositories.user_repository.UserRepository",
                return_value=mock_user_repo,
            ),
        ]
        return patches, mock_voice_service, mock_user_repo

    async def test_valid_phone_calls_make_outbound_call(self):
        """With valid phone, make_outbound_call is called with user phone number."""
        from nikita.agents.voice.scheduling import EventDeliveryHandler

        event = _make_voice_event()
        user = _make_user(phone="+41787950009")

        patches, mock_voice_service, _ = self._patch_scheduling_imports(user)

        with patches[0], patches[1], patches[2]:
            handler = EventDeliveryHandler()
            result = await handler._deliver_voice_event(event)

        assert result is True
        mock_voice_service.make_outbound_call.assert_called_once()
        call_kwargs = mock_voice_service.make_outbound_call.call_args.kwargs
        assert call_kwargs["to_number"] == "+41787950009"
        assert call_kwargs["user_id"] == event.user_id

    async def test_no_phone_returns_false(self):
        """User without phone number: returns False without calling make_outbound_call."""
        from nikita.agents.voice.scheduling import EventDeliveryHandler

        event = _make_voice_event()
        user = _make_user(phone=None)

        patches, mock_voice_service, _ = self._patch_scheduling_imports(user)

        with patches[0], patches[1], patches[2]:
            handler = EventDeliveryHandler()
            result = await handler._deliver_voice_event(event)

        assert result is False
        mock_voice_service.make_outbound_call.assert_not_called()

    async def test_no_user_returns_false(self):
        """User not found in DB: returns False without calling make_outbound_call."""
        from nikita.agents.voice.scheduling import EventDeliveryHandler

        event = _make_voice_event()

        patches, mock_voice_service, _ = self._patch_scheduling_imports(user=None)

        with patches[0], patches[1], patches[2]:
            handler = EventDeliveryHandler()
            result = await handler._deliver_voice_event(event)

        assert result is False
        mock_voice_service.make_outbound_call.assert_not_called()

    async def test_call_failure_returns_false(self):
        """make_outbound_call returning success=False causes handler to return False."""
        from nikita.agents.voice.scheduling import EventDeliveryHandler

        event = _make_voice_event()
        user = _make_user(phone="+41787950009")

        patches, mock_voice_service, _ = self._patch_scheduling_imports(
            user, call_result={"success": False, "error": "ElevenLabs API error: 500"}
        )

        with patches[0], patches[1], patches[2]:
            handler = EventDeliveryHandler()
            result = await handler._deliver_voice_event(event)

        assert result is False

    async def test_voice_prompt_passed_as_config_override(self):
        """voice_prompt from event content is passed as conversation_config_override."""
        from nikita.agents.voice.scheduling import EventDeliveryHandler

        voice_prompt = "I've been thinking about you all day..."
        event = _make_voice_event(voice_prompt=voice_prompt)
        user = _make_user(phone="+41787950009")

        patches, mock_voice_service, _ = self._patch_scheduling_imports(user)

        with patches[0], patches[1], patches[2]:
            handler = EventDeliveryHandler()
            await handler._deliver_voice_event(event)

        call_kwargs = mock_voice_service.make_outbound_call.call_args.kwargs
        expected_override = {"agent": {"prompt": {"prompt": voice_prompt}}}
        assert call_kwargs["conversation_config_override"] == expected_override

    async def test_exception_during_db_lookup_returns_false(self):
        """Exception raised inside handler body is caught and returns False."""
        from nikita.agents.voice.scheduling import EventDeliveryHandler

        event = _make_voice_event()

        # Simulate the session maker itself raising on call (before context manager entry)
        with patch(
            "nikita.db.database.get_session_maker",
            side_effect=RuntimeError("DB connection failed"),
        ):
            handler = EventDeliveryHandler()
            result = await handler._deliver_voice_event(event)

        assert result is False


# ---------------------------------------------------------------------------
# tasks.py deliver_pending_messages voice delivery path tests
# ---------------------------------------------------------------------------

def _make_due_voice_event(voice_prompt: str = "Hey there!", user_id=None) -> MagicMock:
    """Build a voice ScheduledEvent mock for tasks.py tests."""
    from nikita.db.models.scheduled_event import EventPlatform

    event = MagicMock()
    event.id = uuid4()
    event.platform = EventPlatform.VOICE.value
    event.user_id = user_id or uuid4()
    event.content = {"voice_prompt": voice_prompt, "agent_id": "test_agent"}
    return event


def _make_tasks_test_mocks(
    due_events: list,
    user: MagicMock | None = None,
    call_result: dict | None = None,
):
    """Create all the mocks needed to test deliver_pending_messages."""
    from nikita.db.models.job_execution import JobName

    mock_event_repo = MagicMock()
    mock_event_repo.get_due_events = AsyncMock(return_value=due_events)
    mock_event_repo.mark_delivered = AsyncMock()
    mock_event_repo.mark_failed = AsyncMock()

    mock_user_repo = MagicMock()
    mock_user_repo.get = AsyncMock(return_value=user)

    mock_execution = MagicMock()
    mock_execution.id = uuid4()
    mock_job_repo = MagicMock()
    mock_job_repo.start_execution = AsyncMock(return_value=mock_execution)
    mock_job_repo.complete_execution = AsyncMock()
    mock_job_repo.fail_execution = AsyncMock()

    mock_voice_service = MagicMock()
    mock_voice_service.make_outbound_call = AsyncMock(
        return_value=call_result or {"success": True, "conversation_id": "conv_xyz"}
    )

    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock()
    mock_bot.close = AsyncMock()

    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session_maker = MagicMock(return_value=mock_session)

    return {
        "event_repo": mock_event_repo,
        "user_repo": mock_user_repo,
        "job_repo": mock_job_repo,
        "voice_service": mock_voice_service,
        "bot": mock_bot,
        "session": mock_session,
        "session_maker": mock_session_maker,
        "execution": mock_execution,
    }


@pytest.mark.asyncio
class TestTasksVoiceDelivery:
    """Tests for the voice delivery path inside deliver_pending_messages."""

    async def test_success_path_marks_delivered(self):
        """Voice event with valid phone and successful call is marked delivered."""
        user = _make_user(phone="+41787950009")
        event = _make_due_voice_event(user_id=user.id)
        mocks = _make_tasks_test_mocks(
            due_events=[event],
            user=user,
            call_result={"success": True, "conversation_id": "conv_abc"},
        )

        with patch(
            "nikita.db.database.get_session_maker",
            return_value=mocks["session_maker"],
        ), patch(
            "nikita.db.repositories.scheduled_event_repository.ScheduledEventRepository",
            return_value=mocks["event_repo"],
        ), patch(
            "nikita.db.repositories.user_repository.UserRepository",
            return_value=mocks["user_repo"],
        ), patch(
            "nikita.db.repositories.job_execution_repository.JobExecutionRepository",
            return_value=mocks["job_repo"],
        ), patch(
            "nikita.agents.voice.service.get_voice_service",
            return_value=mocks["voice_service"],
        ), patch(
            "nikita.platforms.telegram.bot.TelegramBot",
            return_value=mocks["bot"],
        ):
            from nikita.api.routes.tasks import deliver_pending_messages
            result = await deliver_pending_messages()

        mocks["event_repo"].mark_delivered.assert_called_once_with(event.id)
        assert result["delivered"] == 1
        assert result["failed"] == 0

    async def test_no_phone_marks_failed_no_retry(self):
        """Voice event for user without phone is marked failed without retry."""
        user = _make_user(phone=None)
        event = _make_due_voice_event(user_id=user.id)
        mocks = _make_tasks_test_mocks(due_events=[event], user=user)

        with patch(
            "nikita.db.database.get_session_maker",
            return_value=mocks["session_maker"],
        ), patch(
            "nikita.db.repositories.scheduled_event_repository.ScheduledEventRepository",
            return_value=mocks["event_repo"],
        ), patch(
            "nikita.db.repositories.user_repository.UserRepository",
            return_value=mocks["user_repo"],
        ), patch(
            "nikita.db.repositories.job_execution_repository.JobExecutionRepository",
            return_value=mocks["job_repo"],
        ), patch(
            "nikita.agents.voice.service.get_voice_service",
            return_value=mocks["voice_service"],
        ), patch(
            "nikita.platforms.telegram.bot.TelegramBot",
            return_value=mocks["bot"],
        ):
            from nikita.api.routes.tasks import deliver_pending_messages
            result = await deliver_pending_messages()

        mocks["event_repo"].mark_failed.assert_called_once()
        call_kwargs = mocks["event_repo"].mark_failed.call_args.kwargs
        assert call_kwargs.get("increment_retry") is False
        mocks["voice_service"].make_outbound_call.assert_not_called()
        assert result["failed"] == 1
        assert result["delivered"] == 0

    async def test_call_failure_marks_failed_with_retry(self):
        """When make_outbound_call returns success=False, event is marked failed with retry."""
        user = _make_user(phone="+41787950009")
        event = _make_due_voice_event(user_id=user.id)
        mocks = _make_tasks_test_mocks(
            due_events=[event],
            user=user,
            call_result={"success": False, "error": "Twilio timeout"},
        )

        with patch(
            "nikita.db.database.get_session_maker",
            return_value=mocks["session_maker"],
        ), patch(
            "nikita.db.repositories.scheduled_event_repository.ScheduledEventRepository",
            return_value=mocks["event_repo"],
        ), patch(
            "nikita.db.repositories.user_repository.UserRepository",
            return_value=mocks["user_repo"],
        ), patch(
            "nikita.db.repositories.job_execution_repository.JobExecutionRepository",
            return_value=mocks["job_repo"],
        ), patch(
            "nikita.agents.voice.service.get_voice_service",
            return_value=mocks["voice_service"],
        ), patch(
            "nikita.platforms.telegram.bot.TelegramBot",
            return_value=mocks["bot"],
        ):
            from nikita.api.routes.tasks import deliver_pending_messages
            result = await deliver_pending_messages()

        mocks["event_repo"].mark_failed.assert_called_once()
        call_kwargs = mocks["event_repo"].mark_failed.call_args.kwargs
        assert call_kwargs.get("increment_retry") is True
        assert "Twilio timeout" in call_kwargs.get("error_message", "")
        assert result["failed"] == 1
        assert result["delivered"] == 0

    async def test_no_user_marks_failed_no_retry(self):
        """Voice event where user lookup returns None is marked failed without retry."""
        event = _make_due_voice_event()
        mocks = _make_tasks_test_mocks(due_events=[event], user=None)

        with patch(
            "nikita.db.database.get_session_maker",
            return_value=mocks["session_maker"],
        ), patch(
            "nikita.db.repositories.scheduled_event_repository.ScheduledEventRepository",
            return_value=mocks["event_repo"],
        ), patch(
            "nikita.db.repositories.user_repository.UserRepository",
            return_value=mocks["user_repo"],
        ), patch(
            "nikita.db.repositories.job_execution_repository.JobExecutionRepository",
            return_value=mocks["job_repo"],
        ), patch(
            "nikita.agents.voice.service.get_voice_service",
            return_value=mocks["voice_service"],
        ), patch(
            "nikita.platforms.telegram.bot.TelegramBot",
            return_value=mocks["bot"],
        ):
            from nikita.api.routes.tasks import deliver_pending_messages
            result = await deliver_pending_messages()

        mocks["event_repo"].mark_failed.assert_called_once()
        call_kwargs = mocks["event_repo"].mark_failed.call_args.kwargs
        assert call_kwargs.get("increment_retry") is False
        mocks["voice_service"].make_outbound_call.assert_not_called()
        assert result["failed"] == 1

    async def test_config_override_contains_voice_prompt(self):
        """The voice_prompt from event content is embedded in conversation_config_override."""
        voice_prompt = "Missing you, come talk to me."
        user = _make_user(phone="+41787950009")
        event = _make_due_voice_event(voice_prompt=voice_prompt, user_id=user.id)
        mocks = _make_tasks_test_mocks(
            due_events=[event],
            user=user,
            call_result={"success": True, "conversation_id": "conv_999"},
        )

        with patch(
            "nikita.db.database.get_session_maker",
            return_value=mocks["session_maker"],
        ), patch(
            "nikita.db.repositories.scheduled_event_repository.ScheduledEventRepository",
            return_value=mocks["event_repo"],
        ), patch(
            "nikita.db.repositories.user_repository.UserRepository",
            return_value=mocks["user_repo"],
        ), patch(
            "nikita.db.repositories.job_execution_repository.JobExecutionRepository",
            return_value=mocks["job_repo"],
        ), patch(
            "nikita.agents.voice.service.get_voice_service",
            return_value=mocks["voice_service"],
        ), patch(
            "nikita.platforms.telegram.bot.TelegramBot",
            return_value=mocks["bot"],
        ):
            from nikita.api.routes.tasks import deliver_pending_messages
            await deliver_pending_messages()

        call_kwargs = mocks["voice_service"].make_outbound_call.call_args.kwargs
        override = call_kwargs.get("conversation_config_override")
        assert override is not None
        assert override["agent"]["prompt"]["prompt"] == voice_prompt
