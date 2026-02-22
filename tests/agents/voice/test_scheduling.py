"""Tests for Voice Event Scheduling (US-8: Unified Event Scheduling).

Tests for T042-T046 acceptance criteria:
- AC-FR013-001: Voice follow-up scheduled with platform='voice'
- AC-FR013-002: Cross-platform events work (text schedules voice)
- AC-FR013-003: /tasks/deliver invokes correct platform handler
- AC-FR013-004: Chapter-based delay calculation
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

# Skip tests that require pydantic_settings if not installed
try:
    from nikita.config import settings as _settings_module
    HAS_SETTINGS = True
except ImportError:
    HAS_SETTINGS = False

needs_settings = pytest.mark.skipif(
    not HAS_SETTINGS,
    reason="Requires pydantic_settings module"
)


@pytest.mark.asyncio
class TestVoiceEventScheduler:
    """Test VoiceEventScheduler class (T042, T043)."""

    @pytest.fixture
    def mock_user(self):
        """Create mock user with metrics."""
        user = MagicMock()
        user.id = uuid4()
        user.chapter = 3
        user.game_status = "active"
        user.telegram_id = 12345678
        user.metrics = MagicMock()
        user.metrics.relationship_score = Decimal("65.0")
        return user

    @pytest.fixture
    def mock_conversation(self):
        """Create mock conversation."""
        conv = MagicMock()
        conv.id = uuid4()
        conv.platform = "voice"
        return conv

    def test_scheduler_calculates_chapter_delay(self, mock_user):
        """AC-FR013-004: Uses chapter-based delay calculation."""
        from nikita.agents.voice.scheduling import VoiceEventScheduler

        scheduler = VoiceEventScheduler()

        # Chapter 1 = longer delays (2-5 min)
        mock_user.chapter = 1
        delay_ch1 = scheduler.get_chapter_delay(mock_user)
        assert delay_ch1 >= 2 * 60  # At least 2 minutes
        assert delay_ch1 <= 5 * 60  # At most 5 minutes

        # Chapter 5 = shorter delays (near-instant)
        mock_user.chapter = 5
        delay_ch5 = scheduler.get_chapter_delay(mock_user)
        assert delay_ch5 <= 30  # At most 30 seconds

    async def test_schedule_follow_up_sets_platform_voice(self, mock_user, mock_conversation):
        """AC-FR013-001: Follow-up scheduled with platform='voice'."""
        from nikita.agents.voice.scheduling import VoiceEventScheduler

        scheduler = VoiceEventScheduler()

        with patch.object(
            scheduler, "_create_event", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = MagicMock(id=uuid4())

            event = await scheduler.schedule_follow_up(
                user_id=mock_user.id,
                event_type="call_reminder",
                content={"voice_prompt": "Hey, wanted to check in with you!"},
                delay_seconds=300,
                source_conversation_id=mock_conversation.id,
            )

        # Verify platform is set to 'voice'
        call_args = mock_create.call_args
        assert call_args is not None
        assert call_args[1].get("platform") == "voice"

    async def test_schedule_follow_up_links_source_conversation(self, mock_user, mock_conversation):
        """AC-T043.4: Links source_conversation_id for traceability."""
        from nikita.agents.voice.scheduling import VoiceEventScheduler

        scheduler = VoiceEventScheduler()

        with patch.object(
            scheduler, "_create_event", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = MagicMock(id=uuid4())

            await scheduler.schedule_follow_up(
                user_id=mock_user.id,
                event_type="follow_up",
                content={"voice_prompt": "Hey!"},
                delay_seconds=60,
                source_conversation_id=mock_conversation.id,
            )

        call_args = mock_create.call_args
        assert call_args[1].get("source_conversation_id") == mock_conversation.id

    @needs_settings
    async def test_schedule_voice_call_reminder(self, mock_user):
        """AC-T043.1: Creates voice call reminder event."""
        from nikita.agents.voice.scheduling import VoiceEventScheduler

        scheduler = VoiceEventScheduler()

        with patch.object(
            scheduler, "_create_event", new_callable=AsyncMock
        ) as mock_create, patch(
            "nikita.config.settings.get_settings"
        ) as mock_settings:
            mock_create.return_value = MagicMock(id=uuid4())
            mock_settings.return_value = MagicMock(
                elevenlabs_default_agent_id="test_agent"
            )

            await scheduler.schedule_voice_call(
                user_id=mock_user.id,
                delay_hours=1.0,
                prompt="I was thinking about you...",
            )

        mock_create.assert_called_once()
        call_args = mock_create.call_args
        assert call_args[1].get("event_type") == "call_reminder"
        assert call_args[1].get("platform") == "voice"


@pytest.mark.asyncio
class TestCrossPlatformScheduling:
    """Test cross-platform event scheduling (T044)."""

    @pytest.fixture
    def mock_user(self):
        """Create mock user."""
        user = MagicMock()
        user.id = uuid4()
        user.telegram_id = 12345678
        user.chapter = 3
        return user

    @needs_settings
    async def test_text_can_schedule_voice_follow_up(self, mock_user):
        """AC-FR013-002: Text schedules voice reminder works."""
        from nikita.agents.voice.scheduling import VoiceEventScheduler

        scheduler = VoiceEventScheduler()

        with patch.object(
            scheduler, "_create_event", new_callable=AsyncMock
        ) as mock_create, patch(
            "nikita.config.settings.get_settings"
        ) as mock_settings:
            mock_create.return_value = MagicMock(id=uuid4())
            mock_settings.return_value = MagicMock(
                elevenlabs_default_agent_id="test_agent"
            )

            # Schedule voice follow-up from text context
            await scheduler.schedule_voice_call(
                user_id=mock_user.id,
                delay_hours=0.5,  # 30 minutes
                prompt="Hey, I noticed you've been quiet. Want to talk?",
                source_platform="telegram",  # Coming from text
            )

        mock_create.assert_called_once()
        call_args = mock_create.call_args
        assert call_args[1].get("platform") == "voice"  # Target is voice

    async def test_voice_can_schedule_telegram_message(self, mock_user):
        """Cross-platform: Voice schedules Telegram follow-up."""
        from nikita.agents.voice.scheduling import VoiceEventScheduler

        scheduler = VoiceEventScheduler()

        with patch.object(
            scheduler, "_create_event", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = MagicMock(id=uuid4())

            await scheduler.schedule_telegram_message(
                user_id=mock_user.id,
                telegram_id=mock_user.telegram_id,
                text="Great talking to you! \U0001f495",
                delay_seconds=60,
            )

        mock_create.assert_called_once()
        call_args = mock_create.call_args
        assert call_args[1].get("platform") == "telegram"


class TestChapterDelayCalculation:
    """Test chapter-based delay calculation (T043)."""

    def test_chapter_1_longest_delays(self):
        """Chapter 1: Longest delays (2-5 minutes)."""
        from nikita.agents.voice.scheduling import VoiceEventScheduler

        scheduler = VoiceEventScheduler()
        user = MagicMock()
        user.chapter = 1

        delay = scheduler.get_chapter_delay(user)

        # Chapter 1 should have 2-5 minute delays
        assert 120 <= delay <= 300

    def test_chapter_3_medium_delays(self):
        """Chapter 3: Medium delays (30s-2min)."""
        from nikita.agents.voice.scheduling import VoiceEventScheduler

        scheduler = VoiceEventScheduler()
        user = MagicMock()
        user.chapter = 3

        delay = scheduler.get_chapter_delay(user)

        # Chapter 3 should have 30s-2min delays
        assert 30 <= delay <= 120

    def test_chapter_5_shortest_delays(self):
        """Chapter 5: Shortest delays (near-instant)."""
        from nikita.agents.voice.scheduling import VoiceEventScheduler

        scheduler = VoiceEventScheduler()
        user = MagicMock()
        user.chapter = 5

        delay = scheduler.get_chapter_delay(user)

        # Chapter 5 should have very short delays
        assert delay <= 30


@pytest.mark.asyncio
class TestEventDelivery:
    """Test event delivery handler (T044)."""

    @pytest.fixture
    def pending_voice_event(self):
        """Create pending voice event."""
        event = MagicMock()
        event.id = uuid4()
        event.platform = "voice"
        event.event_type = "call_reminder"
        event.status = "pending"
        event.content = {
            "voice_prompt": "Hey, I was thinking about you!",
            "agent_id": "test_agent",
        }
        event.user_id = uuid4()
        event.scheduled_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        return event

    @pytest.fixture
    def pending_telegram_event(self):
        """Create pending telegram event."""
        event = MagicMock()
        event.id = uuid4()
        event.platform = "telegram"
        event.event_type = "message_delivery"
        event.status = "pending"
        event.content = {
            "chat_id": 12345678,
            "text": "Hey there! \U0001f495",
        }
        event.user_id = uuid4()
        event.scheduled_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        return event

    async def test_deliver_voice_event_calls_elevenlabs(self, pending_voice_event):
        """AC-T044.2: Voice platform events trigger voice handler."""
        from nikita.agents.voice.scheduling import EventDeliveryHandler

        handler = EventDeliveryHandler()

        with patch.object(
            handler, "_deliver_voice_event", new_callable=AsyncMock
        ) as mock_deliver, patch.object(
            handler, "_mark_delivered", new_callable=AsyncMock
        ):
            mock_deliver.return_value = True

            result = await handler.deliver(pending_voice_event)

        mock_deliver.assert_called_once_with(pending_voice_event)

    async def test_deliver_telegram_event_sends_message(self, pending_telegram_event):
        """AC-T044.1: Telegram platform events send messages."""
        from nikita.agents.voice.scheduling import EventDeliveryHandler

        handler = EventDeliveryHandler()

        with patch.object(
            handler, "_deliver_telegram_event", new_callable=AsyncMock
        ) as mock_deliver, patch.object(
            handler, "_mark_delivered", new_callable=AsyncMock
        ):
            mock_deliver.return_value = True

            result = await handler.deliver(pending_telegram_event)

        mock_deliver.assert_called_once_with(pending_telegram_event)

    async def test_marks_event_delivered_on_success(self, pending_voice_event):
        """AC-T044.3: Marks events as delivered after success."""
        from nikita.agents.voice.scheduling import EventDeliveryHandler

        handler = EventDeliveryHandler()

        with patch.object(
            handler, "_deliver_voice_event", new_callable=AsyncMock
        ) as mock_deliver, patch.object(
            handler, "_mark_delivered", new_callable=AsyncMock
        ) as mock_mark:
            mock_deliver.return_value = True

            await handler.deliver(pending_voice_event)

        mock_mark.assert_called_once_with(pending_voice_event)
