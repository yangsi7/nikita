"""Tests for Telegram MessageHandler - WRITTEN FIRST (TDD Red phase).

These tests verify the Telegram-specific message handler that bridges
Telegram messages to the text agent.

AC Coverage: AC-FR002-001, AC-T015.1-5, B-2 (Scoring + Boss Integration)
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from nikita.platforms.telegram.message_handler import MessageHandler
from nikita.platforms.telegram.models import TelegramMessage, TelegramUser, TelegramChat
from nikita.platforms.telegram.rate_limiter import RateLimiter, RateLimitResult
from nikita.agents.text.handler import ResponseDecision
from nikita.config.enums import EngagementState
from nikita.db.models.user import User
from nikita.engine.scoring.calculator import ScoreResult
from nikita.engine.scoring.models import MetricDeltas, ScoreChangeEvent


@pytest.fixture(autouse=True)
def mock_text_patterns():
    """Mock text patterns processor to return input unchanged.

    This allows message handler tests to focus on their specific functionality
    without text patterns modifying responses (emoji, casing, etc.).
    Text patterns behavior is tested separately in tests/text_patterns/.
    """
    def passthrough(self, response: str, user=None) -> str:
        """Return response unchanged."""
        return response

    with patch.object(MessageHandler, "_apply_text_patterns", passthrough):
        yield


class TestMessageHandler:
    """Test suite for Telegram MessageHandler."""

    @pytest.fixture
    def mock_user_repository(self):
        """Mock UserRepository for testing."""
        repo = AsyncMock()
        # Alias _for_update to same mock so return_value settings apply to both
        repo.get_by_telegram_id_for_update = repo.get_by_telegram_id
        return repo

    @pytest.fixture
    def mock_conversation_repository(self):
        """Mock ConversationRepository for conversation tracking."""
        repo = AsyncMock()
        # Default: return a mock conversation
        mock_conversation = MagicMock()
        mock_conversation.id = uuid4()
        mock_conversation.status = "active"
        repo.get_active_conversation.return_value = mock_conversation
        repo.create_conversation.return_value = mock_conversation
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
        mock_conversation_repository,
        mock_text_agent_handler,
        mock_response_delivery,
        mock_bot,
    ):
        """Create MessageHandler instance with mocked dependencies."""
        return MessageHandler(
            user_repository=mock_user_repository,
            conversation_repository=mock_conversation_repository,
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
        # Spec 030: handle() now receives conversation context kwargs
        mock_text_agent_handler.handle.assert_called_once()
        call_args = mock_text_agent_handler.handle.call_args
        assert call_args[0][0] == user_id  # First positional arg is user_id
        assert call_args[0][1] == "Hello Nikita"  # Second positional arg is text
        assert "conversation_messages" in call_args[1]  # Now passes conversation context
        assert "conversation_id" in call_args[1]

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
        mock_user_repository.get_by_telegram_id_for_update.return_value = None

        # Act
        await handler.handle(sample_message)

        # Assert
        mock_user_repository.get_by_telegram_id_for_update.assert_called_once_with(123456789)
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
        self, mock_user_repository, mock_conversation_repository, mock_text_agent_handler,
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
            conversation_repository=mock_conversation_repository,
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
        self, mock_user_repository, mock_conversation_repository, mock_text_agent_handler,
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
            conversation_repository=mock_conversation_repository,
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
        self, mock_user_repository, mock_conversation_repository, mock_text_agent_handler,
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
            conversation_repository=mock_conversation_repository,
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
        self, mock_user_repository, mock_conversation_repository, mock_text_agent_handler,
        mock_response_delivery, mock_bot, sample_message
    ):
        """
        AC-T025.3: Rate limit messages stay in-character (no harsh technical errors).
        """
        # Arrange
        mock_rate_limiter = AsyncMock(spec=RateLimiter)
        handler = MessageHandler(
            user_repository=mock_user_repository,
            conversation_repository=mock_conversation_repository,
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
        self, mock_user_repository, mock_conversation_repository, mock_text_agent_handler,
        mock_response_delivery, mock_bot, sample_message
    ):
        """
        Verify that rate limiting is disabled when rate_limiter=None.
        """
        # Arrange - handler WITHOUT rate limiter
        handler = MessageHandler(
            user_repository=mock_user_repository,
            conversation_repository=mock_conversation_repository,
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


class TestScoringIntegration:
    """Test suite for B-2: Scoring and Boss Integration."""

    @pytest.fixture
    def mock_user_repository(self):
        """Mock UserRepository for testing."""
        repo = AsyncMock()
        repo.update_score = AsyncMock()
        repo.set_boss_fight_status = AsyncMock()
        # Alias _for_update to same mock so return_value settings apply to both
        repo.get_by_telegram_id_for_update = repo.get_by_telegram_id
        return repo

    @pytest.fixture
    def mock_conversation_repository(self):
        """Mock ConversationRepository for conversation tracking."""
        repo = AsyncMock()
        mock_conversation = MagicMock()
        mock_conversation.id = uuid4()
        mock_conversation.status = "active"
        repo.get_active_conversation.return_value = mock_conversation
        repo.create_conversation.return_value = mock_conversation
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
    def mock_scoring_service(self):
        """Mock ScoringService for testing."""
        service = AsyncMock()
        return service

    @pytest.fixture
    def sample_message(self):
        """Create sample Telegram message for testing."""
        return TelegramMessage(
            message_id=1,
            from_=TelegramUser(id=123456789, first_name="Alex"),
            chat=TelegramChat(id=123456789, type="private"),
            text="Hello Nikita",
        )

    @pytest.fixture
    def mock_user_with_metrics(self):
        """Create mock user with metrics for scoring tests."""
        user_id = uuid4()
        mock_user = MagicMock(spec=User)
        mock_user.id = user_id
        mock_user.chapter = 1
        mock_user.relationship_score = Decimal("50.0")
        mock_user.engagement_state = None  # Default to CALIBRATING

        # Mock metrics
        mock_metrics = MagicMock()
        mock_metrics.intimacy = Decimal("50")
        mock_metrics.passion = Decimal("50")
        mock_metrics.trust = Decimal("50")
        mock_metrics.secureness = Decimal("50")
        mock_user.metrics = mock_metrics

        return mock_user

    @pytest.mark.asyncio
    async def test_b2_scoring_called_after_response(
        self, mock_user_repository, mock_conversation_repository, mock_text_agent_handler,
        mock_response_delivery, mock_bot, mock_scoring_service, sample_message, mock_user_with_metrics
    ):
        """
        B-2: Given agent generates response, When response delivered,
        Then scoring service is called to score the interaction.
        """
        # Arrange
        handler = MessageHandler(
            user_repository=mock_user_repository,
            conversation_repository=mock_conversation_repository,
            text_agent_handler=mock_text_agent_handler,
            response_delivery=mock_response_delivery,
            bot=mock_bot,
            scoring_service=mock_scoring_service,
        )

        mock_user_repository.get_by_telegram_id.return_value = mock_user_with_metrics

        mock_decision = ResponseDecision(
            response="Hey there!",
            delay_seconds=60,
            scheduled_at=datetime.now(timezone.utc),
            should_respond=True,
        )
        mock_text_agent_handler.handle.return_value = mock_decision

        # Mock scoring result (no boss threshold)
        mock_result = ScoreResult(
            score_before=Decimal("50.0"),
            score_after=Decimal("52.0"),
            metrics_before={"intimacy": Decimal("50"), "passion": Decimal("50"), "trust": Decimal("50"), "secureness": Decimal("50")},
            metrics_after={"intimacy": Decimal("51"), "passion": Decimal("51"), "trust": Decimal("51"), "secureness": Decimal("50")},
            deltas_applied=MetricDeltas(
                intimacy=Decimal("1"), passion=Decimal("1"),
                trust=Decimal("1"), secureness=Decimal("0"),
            ),
            multiplier_applied=Decimal("1.0"),
            engagement_state=EngagementState.CALIBRATING,
            events=[],
        )
        mock_scoring_service.score_interaction.return_value = mock_result

        # Act
        await handler.handle(sample_message)

        # Assert - scoring service was called
        mock_scoring_service.score_interaction.assert_called_once()
        call_kwargs = mock_scoring_service.score_interaction.call_args.kwargs
        assert call_kwargs["user_id"] == mock_user_with_metrics.id
        assert call_kwargs["user_message"] == "Hello Nikita"
        assert call_kwargs["nikita_response"] == "Hey there!"

    @pytest.mark.asyncio
    async def test_b2_user_score_updated_when_delta_nonzero(
        self, mock_user_repository, mock_conversation_repository, mock_text_agent_handler,
        mock_response_delivery, mock_bot, mock_scoring_service, sample_message, mock_user_with_metrics
    ):
        """
        B-2: Given scoring returns positive delta, When interaction scored,
        Then user score is updated in database.
        """
        # Arrange
        handler = MessageHandler(
            user_repository=mock_user_repository,
            conversation_repository=mock_conversation_repository,
            text_agent_handler=mock_text_agent_handler,
            response_delivery=mock_response_delivery,
            bot=mock_bot,
            scoring_service=mock_scoring_service,
        )

        mock_user_repository.get_by_telegram_id.return_value = mock_user_with_metrics

        mock_decision = ResponseDecision(
            response="Great to hear from you!",
            delay_seconds=30,
            scheduled_at=datetime.now(timezone.utc),
            should_respond=True,
        )
        mock_text_agent_handler.handle.return_value = mock_decision

        # Mock scoring result with positive delta
        mock_result = ScoreResult(
            score_before=Decimal("50.0"),
            score_after=Decimal("53.5"),
            metrics_before={"intimacy": Decimal("50"), "passion": Decimal("50"), "trust": Decimal("50"), "secureness": Decimal("50")},
            metrics_after={"intimacy": Decimal("52"), "passion": Decimal("52"), "trust": Decimal("51"), "secureness": Decimal("51")},
            deltas_applied=MetricDeltas(
                intimacy=Decimal("2"), passion=Decimal("2"),
                trust=Decimal("1"), secureness=Decimal("1"),
            ),
            multiplier_applied=Decimal("1.0"),
            engagement_state=EngagementState.CALIBRATING,
            events=[],
        )
        mock_scoring_service.score_interaction.return_value = mock_result

        # Act
        await handler.handle(sample_message)

        # Assert - user score updated
        mock_user_repository.update_score.assert_called_once()
        call_kwargs = mock_user_repository.update_score.call_args.kwargs
        assert call_kwargs["user_id"] == mock_user_with_metrics.id
        assert call_kwargs["delta"] == Decimal("3.5")
        assert call_kwargs["event_type"] == "conversation"

    @pytest.mark.asyncio
    async def test_b2_boss_threshold_triggers_boss_fight_status(
        self, mock_user_repository, mock_conversation_repository, mock_text_agent_handler,
        mock_response_delivery, mock_bot, mock_scoring_service, sample_message, mock_user_with_metrics
    ):
        """
        B-2: Given score crosses boss threshold (55% for Ch1), When interaction scored,
        Then user set to boss_fight status.
        """
        # Arrange
        handler = MessageHandler(
            user_repository=mock_user_repository,
            conversation_repository=mock_conversation_repository,
            text_agent_handler=mock_text_agent_handler,
            response_delivery=mock_response_delivery,
            bot=mock_bot,
            scoring_service=mock_scoring_service,
        )

        mock_user_repository.get_by_telegram_id.return_value = mock_user_with_metrics

        mock_decision = ResponseDecision(
            response="You're really getting me!",
            delay_seconds=60,
            scheduled_at=datetime.now(timezone.utc),
            should_respond=True,
        )
        mock_text_agent_handler.handle.return_value = mock_decision

        # Mock scoring result with boss_threshold_reached event
        boss_event = ScoreChangeEvent(
            event_type="boss_threshold_reached",
            chapter=1,
            score_before=Decimal("53.0"),
            score_after=Decimal("56.0"),
            threshold=Decimal("55"),
        )
        mock_result = ScoreResult(
            score_before=Decimal("53.0"),
            score_after=Decimal("56.0"),
            metrics_before={"intimacy": Decimal("53"), "passion": Decimal("53"), "trust": Decimal("53"), "secureness": Decimal("53")},
            metrics_after={"intimacy": Decimal("55"), "passion": Decimal("55"), "trust": Decimal("54"), "secureness": Decimal("54")},
            deltas_applied=MetricDeltas(
                intimacy=Decimal("2"), passion=Decimal("2"),
                trust=Decimal("1"), secureness=Decimal("1"),
            ),
            multiplier_applied=Decimal("1.0"),
            engagement_state=EngagementState.CALIBRATING,
            events=[boss_event],
        )
        mock_scoring_service.score_interaction.return_value = mock_result

        # Act
        with patch("nikita.engine.chapters.prompts.get_boss_prompt") as mock_boss_prompt:
            mock_boss_prompt.return_value = {"in_character_opening": "So... we need to talk."}
            with patch("asyncio.sleep", new_callable=AsyncMock):  # Skip sleep in tests
                await handler.handle(sample_message)

        # Assert - boss fight status set
        mock_user_repository.set_boss_fight_status.assert_called_once_with(mock_user_with_metrics.id)

    @pytest.mark.asyncio
    async def test_b2_boss_opening_message_sent(
        self, mock_user_repository, mock_conversation_repository, mock_text_agent_handler,
        mock_response_delivery, mock_bot, mock_scoring_service, sample_message, mock_user_with_metrics
    ):
        """
        B-2: Given boss threshold reached, When boss triggered,
        Then boss opening message sent to chat.
        """
        # Arrange
        handler = MessageHandler(
            user_repository=mock_user_repository,
            conversation_repository=mock_conversation_repository,
            text_agent_handler=mock_text_agent_handler,
            response_delivery=mock_response_delivery,
            bot=mock_bot,
            scoring_service=mock_scoring_service,
        )

        mock_user_repository.get_by_telegram_id.return_value = mock_user_with_metrics

        mock_decision = ResponseDecision(
            response="You're really getting me!",
            delay_seconds=60,
            scheduled_at=datetime.now(timezone.utc),
            should_respond=True,
        )
        mock_text_agent_handler.handle.return_value = mock_decision

        # Mock scoring result with boss_threshold_reached event
        boss_event = ScoreChangeEvent(
            event_type="boss_threshold_reached",
            chapter=1,
            score_before=Decimal("53.0"),
            score_after=Decimal("56.0"),
            threshold=Decimal("55"),
        )
        mock_result = ScoreResult(
            score_before=Decimal("53.0"),
            score_after=Decimal("56.0"),
            metrics_before={"intimacy": Decimal("53"), "passion": Decimal("53"), "trust": Decimal("53"), "secureness": Decimal("53")},
            metrics_after={"intimacy": Decimal("55"), "passion": Decimal("55"), "trust": Decimal("54"), "secureness": Decimal("54")},
            deltas_applied=MetricDeltas(
                intimacy=Decimal("2"), passion=Decimal("2"),
                trust=Decimal("1"), secureness=Decimal("1"),
            ),
            multiplier_applied=Decimal("1.0"),
            engagement_state=EngagementState.CALIBRATING,
            events=[boss_event],
        )
        mock_scoring_service.score_interaction.return_value = mock_result

        # Act
        with patch("nikita.engine.chapters.prompts.get_boss_prompt") as mock_boss_prompt:
            mock_boss_prompt.return_value = {"in_character_opening": "So... I need to ask you something."}
            with patch("asyncio.sleep", new_callable=AsyncMock):  # Skip sleep in tests
                await handler.handle(sample_message)

        # Assert - boss opening sent (multiple sends: typing, response delivery calls bot internally)
        # Find the send_message call with boss opening
        boss_message_sent = False
        for call in mock_bot.send_message.call_args_list:
            if call.kwargs.get("text") == "So... I need to ask you something.":
                boss_message_sent = True
                break
        assert boss_message_sent, "Boss opening message should be sent"

    @pytest.mark.asyncio
    async def test_b2_scoring_failure_does_not_break_message_flow(
        self, mock_user_repository, mock_conversation_repository, mock_text_agent_handler,
        mock_response_delivery, mock_bot, mock_scoring_service, sample_message, mock_user_with_metrics
    ):
        """
        B-2: Given scoring service throws exception, When interaction processed,
        Then message flow continues (error logged but not propagated).
        """
        # Arrange
        handler = MessageHandler(
            user_repository=mock_user_repository,
            conversation_repository=mock_conversation_repository,
            text_agent_handler=mock_text_agent_handler,
            response_delivery=mock_response_delivery,
            bot=mock_bot,
            scoring_service=mock_scoring_service,
        )

        mock_user_repository.get_by_telegram_id.return_value = mock_user_with_metrics

        mock_decision = ResponseDecision(
            response="Hey!",
            delay_seconds=30,
            scheduled_at=datetime.now(timezone.utc),
            should_respond=True,
        )
        mock_text_agent_handler.handle.return_value = mock_decision

        # Mock scoring service to throw exception
        mock_scoring_service.score_interaction.side_effect = Exception("LLM API error")

        # Act - should NOT raise exception
        await handler.handle(sample_message)

        # Assert - response still queued despite scoring failure
        mock_response_delivery.queue.assert_called_once()
        queued_response = mock_response_delivery.queue.call_args.kwargs["response"]
        assert "Hey!" in queued_response

    @pytest.mark.asyncio
    async def test_b2_no_scoring_when_should_respond_false(
        self, mock_user_repository, mock_conversation_repository, mock_text_agent_handler,
        mock_response_delivery, mock_bot, mock_scoring_service, sample_message, mock_user_with_metrics
    ):
        """
        B-2: Given agent decides to skip response, When should_respond=False,
        Then scoring is NOT called (no interaction to score).
        """
        # Arrange
        handler = MessageHandler(
            user_repository=mock_user_repository,
            conversation_repository=mock_conversation_repository,
            text_agent_handler=mock_text_agent_handler,
            response_delivery=mock_response_delivery,
            bot=mock_bot,
            scoring_service=mock_scoring_service,
        )

        mock_user_repository.get_by_telegram_id.return_value = mock_user_with_metrics

        # Mock: Agent decides to skip (ghost)
        mock_decision = ResponseDecision(
            response="",
            delay_seconds=0,
            scheduled_at=datetime.now(timezone.utc),
            should_respond=False,
            skip_reason="Chapter 1 skip probability",
        )
        mock_text_agent_handler.handle.return_value = mock_decision

        # Act
        await handler.handle(sample_message)

        # Assert - scoring NOT called for skipped responses
        mock_scoring_service.score_interaction.assert_not_called()
        mock_response_delivery.queue.assert_not_called()


class TestProfileGate:
    """Test suite for Profile Gate - FR-012 (mandatory onboarding)."""

    @pytest.fixture
    def mock_user_repository(self):
        """Mock UserRepository for testing."""
        repo = AsyncMock()
        # Alias _for_update to same mock so return_value settings apply to both
        repo.get_by_telegram_id_for_update = repo.get_by_telegram_id
        return repo

    @pytest.fixture
    def mock_conversation_repository(self):
        """Mock ConversationRepository for conversation tracking."""
        repo = AsyncMock()
        mock_conversation = MagicMock()
        mock_conversation.id = uuid4()
        mock_conversation.status = "active"
        repo.get_active_conversation.return_value = mock_conversation
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
    def mock_profile_repository(self):
        """Mock ProfileRepository for testing."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_backstory_repository(self):
        """Mock BackstoryRepository for testing."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_onboarding_handler(self):
        """Mock OnboardingHandler for testing."""
        handler = AsyncMock()
        return handler

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
    async def test_fr012_profile_gate_passes_when_profile_and_backstory_exist(
        self,
        mock_user_repository,
        mock_conversation_repository,
        mock_text_agent_handler,
        mock_response_delivery,
        mock_bot,
        mock_profile_repository,
        mock_backstory_repository,
        sample_message,
    ):
        """
        FR-012: Given user has profile AND backstory, When they send message,
        Then message is routed to text agent (profile gate passes).
        """
        # Arrange
        handler = MessageHandler(
            user_repository=mock_user_repository,
            conversation_repository=mock_conversation_repository,
            text_agent_handler=mock_text_agent_handler,
            response_delivery=mock_response_delivery,
            bot=mock_bot,
            profile_repository=mock_profile_repository,
            backstory_repository=mock_backstory_repository,
        )

        user_id = uuid4()
        mock_user = MagicMock(spec=User)
        mock_user.id = user_id
        mock_user_repository.get_by_telegram_id.return_value = mock_user

        # User has profile and backstory
        mock_profile_repository.get_by_user_id.return_value = MagicMock()  # Profile exists
        mock_backstory_repository.get_by_user_id.return_value = MagicMock()  # Backstory exists

        mock_decision = ResponseDecision(
            response="Hey Alex!",
            delay_seconds=60,
            scheduled_at=datetime.now(timezone.utc),
            should_respond=True,
        )
        mock_text_agent_handler.handle.return_value = mock_decision

        # Act
        await handler.handle(sample_message)

        # Assert - text agent called (profile gate passed)
        mock_text_agent_handler.handle.assert_called_once()

    @pytest.mark.asyncio
    async def test_fr012_profile_gate_redirects_when_profile_missing(
        self,
        mock_user_repository,
        mock_conversation_repository,
        mock_text_agent_handler,
        mock_response_delivery,
        mock_bot,
        mock_profile_repository,
        mock_backstory_repository,
        sample_message,
    ):
        """
        FR-012: Given user missing profile, When they send message,
        Then redirected to onboarding (profile gate blocks).
        """
        # Arrange
        handler = MessageHandler(
            user_repository=mock_user_repository,
            conversation_repository=mock_conversation_repository,
            text_agent_handler=mock_text_agent_handler,
            response_delivery=mock_response_delivery,
            bot=mock_bot,
            profile_repository=mock_profile_repository,
            backstory_repository=mock_backstory_repository,
        )

        user_id = uuid4()
        mock_user = MagicMock(spec=User)
        mock_user.id = user_id
        mock_user_repository.get_by_telegram_id.return_value = mock_user

        # User has NO profile
        mock_profile_repository.get_by_user_id.return_value = None
        mock_backstory_repository.get_by_user_id.return_value = MagicMock()  # Backstory exists

        # Act
        await handler.handle(sample_message)

        # Assert - text agent NOT called (profile gate blocked)
        mock_text_agent_handler.handle.assert_not_called()
        # Redirect message sent
        mock_bot.send_message.assert_called()
        sent_text = mock_bot.send_message.call_args[1]["text"]
        assert "learn" in sent_text.lower() or "know" in sent_text.lower()

    @pytest.mark.asyncio
    async def test_fr012_profile_gate_redirects_when_backstory_missing(
        self,
        mock_user_repository,
        mock_conversation_repository,
        mock_text_agent_handler,
        mock_response_delivery,
        mock_bot,
        mock_profile_repository,
        mock_backstory_repository,
        sample_message,
    ):
        """
        FR-012: Given user missing backstory, When they send message,
        Then redirected to onboarding (profile gate blocks).
        """
        # Arrange
        handler = MessageHandler(
            user_repository=mock_user_repository,
            conversation_repository=mock_conversation_repository,
            text_agent_handler=mock_text_agent_handler,
            response_delivery=mock_response_delivery,
            bot=mock_bot,
            profile_repository=mock_profile_repository,
            backstory_repository=mock_backstory_repository,
        )

        user_id = uuid4()
        mock_user = MagicMock(spec=User)
        mock_user.id = user_id
        mock_user_repository.get_by_telegram_id.return_value = mock_user

        # User has profile but NO backstory
        mock_profile_repository.get_by_user_id.return_value = MagicMock()  # Profile exists
        mock_backstory_repository.get_by_user_id.return_value = None

        # Act
        await handler.handle(sample_message)

        # Assert - text agent NOT called (profile gate blocked)
        mock_text_agent_handler.handle.assert_not_called()
        # Redirect message sent
        mock_bot.send_message.assert_called()

    @pytest.mark.asyncio
    async def test_fr012_profile_gate_skipped_when_repos_not_configured(
        self,
        mock_user_repository,
        mock_conversation_repository,
        mock_text_agent_handler,
        mock_response_delivery,
        mock_bot,
        sample_message,
    ):
        """
        FR-012: Given profile/backstory repos not configured, When message sent,
        Then profile gate is skipped (graceful degradation).
        """
        # Arrange - handler WITHOUT profile/backstory repos
        handler = MessageHandler(
            user_repository=mock_user_repository,
            conversation_repository=mock_conversation_repository,
            text_agent_handler=mock_text_agent_handler,
            response_delivery=mock_response_delivery,
            bot=mock_bot,
            profile_repository=None,  # Not configured
            backstory_repository=None,  # Not configured
        )

        user_id = uuid4()
        mock_user = MagicMock(spec=User)
        mock_user.id = user_id
        mock_user_repository.get_by_telegram_id.return_value = mock_user

        mock_decision = ResponseDecision(
            response="Hey!",
            delay_seconds=0,
            scheduled_at=datetime.now(timezone.utc),
            should_respond=True,
        )
        mock_text_agent_handler.handle.return_value = mock_decision

        # Act
        await handler.handle(sample_message)

        # Assert - text agent called (graceful degradation)
        mock_text_agent_handler.handle.assert_called_once()
