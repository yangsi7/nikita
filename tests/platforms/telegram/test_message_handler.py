"""Tests for Telegram MessageHandler - WRITTEN FIRST (TDD Red phase).

These tests verify the Telegram-specific message handler that bridges
Telegram messages to the text agent.

AC Coverage: AC-FR002-001, AC-T015.1-5
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime, timezone

from nikita.platforms.telegram.message_handler import MessageHandler
from nikita.platforms.telegram.models import TelegramMessage, TelegramUser, TelegramChat
from nikita.platforms.telegram.rate_limiter import RateLimiter, RateLimitResult
from nikita.agents.text.handler import ResponseDecision
from nikita.db.models.user import User


class TestMessageHandler:
    """Test suite for Telegram MessageHandler."""

    @pytest.fixture
    def mock_user_repository(self):
        """Mock UserRepository for testing."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_text_agent_handler(self):
        """Mock text agent MessageHandler."""
        handler = AsyncMock()
        return handler

    @pytest.fixture
    def mock_response_delivery(self):
        """Mock ResponseDelivery for testing."""
        delivery = AsyncMock()
        return delivery

    @pytest.fixture
    def mock_bot(self):
        """Mock TelegramBot for testing."""
        bot = AsyncMock()
        return bot

    @pytest.fixture
    def handler(
        self,
        mock_user_repository,
        mock_text_agent_handler,
        mock_response_delivery,
        mock_bot,
    ):
        """Create MessageHandler instance with mocked dependencies."""
        return MessageHandler(
            user_repository=mock_user_repository,
            text_agent_handler=mock_text_agent_handler,
            response_delivery=mock_response_delivery,
            bot=mock_bot,
        )

    @pytest.fixture
    def sample_message(self):
        """Create sample Telegram message for testing."""
        return TelegramMessage(
            message_id=1,
            from_=TelegramUser(id=123456789, first_name="Alex"),
            chat=TelegramChat(id=123456789, type="private"),
            text="Hello Nikita",
        )

    @pytest.mark.asyncio
    async def test_ac_fr002_001_authenticated_user_message_routed_to_text_agent(
        self, handler, mock_user_repository, mock_text_agent_handler, sample_message
    ):
        """
        AC-FR002-001: Given authenticated user, When they send text message,
        Then message is routed to text agent.

        Verifies core message routing functionality.
        """
        # Arrange
        user_id = uuid4()
        mock_user = MagicMock(spec=User)
        mock_user.id = user_id
        mock_user.chapter = 2
        mock_user_repository.get_by_telegram_id.return_value = mock_user

        mock_decision = ResponseDecision(
            response="Hey Alex",
            delay_seconds=60,
            scheduled_at=datetime.now(timezone.utc),
            should_respond=True,
        )
        mock_text_agent_handler.handle.return_value = mock_decision

        # Act
        await handler.handle(sample_message)

        # Assert
        mock_user_repository.get_by_telegram_id.assert_called_once_with(123456789)
        mock_text_agent_handler.handle.assert_called_once_with(user_id, "Hello Nikita")

    @pytest.mark.asyncio
    async def test_ac_t015_1_handle_processes_text_messages(
        self, handler, mock_user_repository, mock_text_agent_handler, sample_message
    ):
        """
        AC-T015.1: handle(message) processes text messages.

        Verifies that text messages are extracted and processed.
        """
        # Arrange
        user_id = uuid4()
        mock_user = MagicMock(spec=User)
        mock_user.id = user_id
        mock_user_repository.get_by_telegram_id.return_value = mock_user

        mock_decision = ResponseDecision(
            response="Hey",
            delay_seconds=0,
            scheduled_at=datetime.now(timezone.utc),
        )
        mock_text_agent_handler.handle.return_value = mock_decision

        # Act
        await handler.handle(sample_message)

        # Assert - verify text extracted correctly
        assert mock_text_agent_handler.handle.call_args[0][1] == "Hello Nikita"

    @pytest.mark.asyncio
    async def test_ac_t015_2_checks_authentication_prompts_registration(
        self, handler, mock_user_repository, mock_bot, sample_message
    ):
        """
        AC-T015.2: Checks authentication (prompts registration if needed).

        Verifies that unregistered users are prompted to register.
        """
        # Arrange
        mock_user_repository.get_by_telegram_id.return_value = None

        # Act
        await handler.handle(sample_message)

        # Assert
        mock_user_repository.get_by_telegram_id.assert_called_once_with(123456789)
        mock_bot.send_message.assert_called_once()

        # Verify registration prompt message
        sent_message = mock_bot.send_message.call_args[1]["text"]
        assert "/start" in sent_message or "register" in sent_message.lower()

    @pytest.mark.asyncio
    async def test_ac_t015_4_routes_to_text_agent_with_user_context(
        self, handler, mock_user_repository, mock_text_agent_handler, sample_message
    ):
        """
        AC-T015.4: Routes to text agent with user context.

        Verifies that user_id is passed to text agent handler.
        """
        # Arrange
        user_id = uuid4()
        mock_user = MagicMock(spec=User)
        mock_user.id = user_id
        mock_user_repository.get_by_telegram_id.return_value = mock_user

        mock_decision = ResponseDecision(
            response="Response",
            delay_seconds=0,
            scheduled_at=datetime.now(timezone.utc),
        )
        mock_text_agent_handler.handle.return_value = mock_decision

        # Act
        await handler.handle(sample_message)

        # Assert - verify user_id passed correctly
        call_args = mock_text_agent_handler.handle.call_args
        assert call_args[0][0] == user_id  # First arg is user_id

    @pytest.mark.asyncio
    async def test_ac_t015_5_queues_response_for_delivery(
        self, handler, mock_user_repository, mock_text_agent_handler,
        mock_response_delivery, sample_message
    ):
        """
        AC-T015.5: Queues response for delivery.

        Verifies that generated responses are queued for delivery.
        """
        # Arrange
        user_id = uuid4()
        mock_user = MagicMock(spec=User)
        mock_user.id = user_id
        mock_user_repository.get_by_telegram_id.return_value = mock_user

        mock_decision = ResponseDecision(
            response="Hey there",
            delay_seconds=120,
            scheduled_at=datetime.now(timezone.utc),
            should_respond=True,
        )
        mock_text_agent_handler.handle.return_value = mock_decision

        # Act
        await handler.handle(sample_message)

        # Assert
        mock_response_delivery.queue.assert_called_once()
        call_kwargs = mock_response_delivery.queue.call_args[1]
        assert call_kwargs["user_id"] == user_id
        assert call_kwargs["chat_id"] == 123456789
        assert call_kwargs["response"] == "Hey there"
        assert call_kwargs["delay_seconds"] == 120

    @pytest.mark.asyncio
    async def test_skip_response_not_queued(
        self, handler, mock_user_repository, mock_text_agent_handler,
        mock_response_delivery, sample_message
    ):
        """
        Verify that skipped responses (should_respond=False) are not queued.
        """
        # Arrange
        user_id = uuid4()
        mock_user = MagicMock(spec=User)
        mock_user.id = user_id
        mock_user_repository.get_by_telegram_id.return_value = mock_user

        # Mock: Text agent decides to skip response
        mock_decision = ResponseDecision(
            response="",
            delay_seconds=0,
            scheduled_at=datetime.now(timezone.utc),
            should_respond=False,
            skip_reason="Random skip based on chapter 2 probability",
        )
        mock_text_agent_handler.handle.return_value = mock_decision

        # Act
        await handler.handle(sample_message)

        # Assert - response delivery should NOT be called
        mock_response_delivery.queue.assert_not_called()

    @pytest.mark.asyncio
    async def test_typing_indicator_sent_before_processing(
        self, handler, mock_user_repository, mock_text_agent_handler,
        mock_bot, sample_message
    ):
        """
        Verify that typing indicator is sent before processing message.
        """
        # Arrange
        user_id = uuid4()
        mock_user = MagicMock(spec=User)
        mock_user.id = user_id
        mock_user_repository.get_by_telegram_id.return_value = mock_user

        mock_decision = ResponseDecision(
            response="Response",
            delay_seconds=0,
            scheduled_at=datetime.now(timezone.utc),
        )
        mock_text_agent_handler.handle.return_value = mock_decision

        # Act
        await handler.handle(sample_message)

        # Assert
        mock_bot.send_chat_action.assert_called_once_with(123456789, "typing")

    @pytest.mark.asyncio
    async def test_empty_message_handled_gracefully(
        self, handler, mock_user_repository, mock_bot
    ):
        """
        Verify that empty messages don't crash the handler.
        """
        # Arrange
        empty_message = TelegramMessage(
            message_id=1,
            from_=TelegramUser(id=123456789, first_name="Alex"),
            chat=TelegramChat(id=123456789, type="private"),
            text="",
        )

        user_id = uuid4()
        mock_user = MagicMock(spec=User)
        mock_user.id = user_id
        mock_user_repository.get_by_telegram_id.return_value = mock_user

        # Act & Assert - should not raise exception
        await handler.handle(empty_message)

        # Should still send typing indicator and look up user
        mock_bot.send_chat_action.assert_called_once()
        mock_user_repository.get_by_telegram_id.assert_called_once()

    # ===== Rate Limiting Integration Tests =====

    @pytest.mark.asyncio
    async def test_ac_t025_1_minute_limit_sends_in_character_response(
        self, mock_user_repository, mock_text_agent_handler,
        mock_response_delivery, mock_bot, sample_message
    ):
        """
        AC-T025.1: Given user hits minute rate limit (21st message),
        When rate limit check fails, Then in-character response sent.
        """
        # Arrange
        mock_rate_limiter = AsyncMock(spec=RateLimiter)
        handler = MessageHandler(
            user_repository=mock_user_repository,
            text_agent_handler=mock_text_agent_handler,
            response_delivery=mock_response_delivery,
            bot=mock_bot,
            rate_limiter=mock_rate_limiter,
        )

        user_id = uuid4()
        mock_user = MagicMock(spec=User)
        mock_user.id = user_id
        mock_user_repository.get_by_telegram_id.return_value = mock_user

        # Mock: Minute limit exceeded
        mock_rate_limiter.check.return_value = RateLimitResult(
            allowed=False,
            reason="minute_limit_exceeded",
            retry_after_seconds=45,
        )

        # Act
        await handler.handle(sample_message)

        # Assert - in-character response sent
        mock_bot.send_message.assert_called_once()
        sent_message = mock_bot.send_message.call_args[1]["text"]
        assert "slow down" in sent_message.lower()
        assert "breathe" in sent_message.lower()

        # Text agent should NOT be called
        mock_text_agent_handler.handle.assert_not_called()

    @pytest.mark.asyncio
    async def test_ac_t025_1_daily_limit_sends_in_character_response(
        self, mock_user_repository, mock_text_agent_handler,
        mock_response_delivery, mock_bot, sample_message
    ):
        """
        AC-T025.1: Given user hits daily rate limit (501st message),
        When rate limit check fails, Then in-character response sent.
        """
        # Arrange
        mock_rate_limiter = AsyncMock(spec=RateLimiter)
        handler = MessageHandler(
            user_repository=mock_user_repository,
            text_agent_handler=mock_text_agent_handler,
            response_delivery=mock_response_delivery,
            bot=mock_bot,
            rate_limiter=mock_rate_limiter,
        )

        user_id = uuid4()
        mock_user = MagicMock(spec=User)
        mock_user.id = user_id
        mock_user_repository.get_by_telegram_id.return_value = mock_user

        # Mock: Daily limit exceeded
        mock_rate_limiter.check.return_value = RateLimitResult(
            allowed=False,
            reason="day_limit_exceeded",
            retry_after_seconds=18000,
        )

        # Act
        await handler.handle(sample_message)

        # Assert - in-character response sent
        mock_bot.send_message.assert_called_once()
        sent_message = mock_bot.send_message.call_args[1]["text"]
        assert "space" in sent_message.lower()
        assert "tomorrow" in sent_message.lower()

        # Text agent should NOT be called
        mock_text_agent_handler.handle.assert_not_called()

    @pytest.mark.asyncio
    async def test_ac_t025_2_warning_when_approaching_daily_limit(
        self, mock_user_repository, mock_text_agent_handler,
        mock_response_delivery, mock_bot, sample_message
    ):
        """
        AC-T025.2: Given user at 450+/500 daily,
        When processing message, Then subtle warning appended to response.
        """
        # Arrange
        mock_rate_limiter = AsyncMock(spec=RateLimiter)
        handler = MessageHandler(
            user_repository=mock_user_repository,
            text_agent_handler=mock_text_agent_handler,
            response_delivery=mock_response_delivery,
            bot=mock_bot,
            rate_limiter=mock_rate_limiter,
        )

        user_id = uuid4()
        mock_user = MagicMock(spec=User)
        mock_user.id = user_id
        mock_user_repository.get_by_telegram_id.return_value = mock_user

        # Mock: Allowed but approaching daily limit
        mock_rate_limiter.check.return_value = RateLimitResult(
            allowed=True,
            warning_threshold_reached=True,
            day_remaining=45,
        )

        mock_decision = ResponseDecision(
            response="Hey what's up?",
            delay_seconds=60,
            scheduled_at=datetime.now(timezone.utc),
            should_respond=True,
        )
        mock_text_agent_handler.handle.return_value = mock_decision

        # Act
        await handler.handle(sample_message)

        # Assert - response queued with warning appended
        mock_response_delivery.queue.assert_called_once()
        queued_response = mock_response_delivery.queue.call_args[1]["response"]
        assert "Hey what's up?" in queued_response  # Original response
        assert "alone time" in queued_response  # Warning
        assert "chatting a lot" in queued_response

    @pytest.mark.asyncio
    async def test_ac_t025_3_no_harsh_technical_error_messages(
        self, mock_user_repository, mock_text_agent_handler,
        mock_response_delivery, mock_bot, sample_message
    ):
        """
        AC-T025.3: Rate limit messages stay in-character (no harsh technical errors).
        """
        # Arrange
        mock_rate_limiter = AsyncMock(spec=RateLimiter)
        handler = MessageHandler(
            user_repository=mock_user_repository,
            text_agent_handler=mock_text_agent_handler,
            response_delivery=mock_response_delivery,
            bot=mock_bot,
            rate_limiter=mock_rate_limiter,
        )

        user_id = uuid4()
        mock_user = MagicMock(spec=User)
        mock_user.id = user_id
        mock_user_repository.get_by_telegram_id.return_value = mock_user

        # Mock: Minute limit exceeded
        mock_rate_limiter.check.return_value = RateLimitResult(
            allowed=False,
            reason="minute_limit_exceeded",
        )

        # Act
        await handler.handle(sample_message)

        # Assert - no technical jargon in message
        sent_message = mock_bot.send_message.call_args[1]["text"]
        forbidden_terms = ["rate limit", "quota", "api", "error", "429", "throttle"]
        for term in forbidden_terms:
            assert term not in sent_message.lower()

    @pytest.mark.asyncio
    async def test_rate_limiting_disabled_when_no_limiter_configured(
        self, mock_user_repository, mock_text_agent_handler,
        mock_response_delivery, mock_bot, sample_message
    ):
        """
        Verify that rate limiting is disabled when rate_limiter=None.
        """
        # Arrange - handler WITHOUT rate limiter
        handler = MessageHandler(
            user_repository=mock_user_repository,
            text_agent_handler=mock_text_agent_handler,
            response_delivery=mock_response_delivery,
            bot=mock_bot,
            rate_limiter=None,  # No rate limiting
        )

        user_id = uuid4()
        mock_user = MagicMock(spec=User)
        mock_user.id = user_id
        mock_user_repository.get_by_telegram_id.return_value = mock_user

        mock_decision = ResponseDecision(
            response="No limits here",
            delay_seconds=0,
            scheduled_at=datetime.now(timezone.utc),
            should_respond=True,
        )
        mock_text_agent_handler.handle.return_value = mock_decision

        # Act
        await handler.handle(sample_message)

        # Assert - message processed normally (no rate limit check)
        mock_text_agent_handler.handle.assert_called_once()
        mock_response_delivery.queue.assert_called_once()
