"""Tests for Error Recovery (US-7) - WRITTEN FIRST (TDD Red phase).

These tests verify graceful error handling for the Telegram message flow.
AC Coverage: AC-FR008-001, AC-FR008-002, AC-FR008-003, AC-T035.1-4
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from nikita.platforms.telegram.message_handler import MessageHandler
from nikita.platforms.telegram.models import (
    TelegramMessage,
    TelegramUser,
    TelegramChat,
)


class TestErrorRecovery:
    """Test suite for US-7 Error Recovery.

    AC-FR008-001: Given agent unavailable, When message sent, Then queued and user notified
    AC-FR008-002: Given network timeout, When delivery fails, Then retry with backoff
    AC-FR008-003: Given auth token expired, When messaging, Then clear re-auth path
    """

    @pytest.fixture
    def mock_user_repository(self):
        """Mock UserRepository."""
        repo = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.telegram_id = 123456789
        mock_user.chapter = 1
        repo.get_by_telegram_id.return_value = mock_user
        return repo

    @pytest.fixture
    def mock_text_agent_handler(self):
        """Mock TextAgentMessageHandler."""
        handler = AsyncMock()
        mock_decision = MagicMock()
        mock_decision.should_respond = True
        mock_decision.response = "Hey babe!"
        mock_decision.delay_seconds = 0
        handler.handle.return_value = mock_decision
        return handler

    @pytest.fixture
    def mock_response_delivery(self):
        """Mock ResponseDelivery."""
        return AsyncMock()

    @pytest.fixture
    def mock_bot(self):
        """Mock TelegramBot."""
        return AsyncMock()

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
    def sample_message(self):
        """Create a sample TelegramMessage."""
        return TelegramMessage(
            message_id=1,
            date=1234567890,
            from_=TelegramUser(id=123456789, first_name="Test"),
            chat=TelegramChat(id=123456789, type="private"),
            text="Hello Nikita!",
        )

    @pytest.fixture
    def handler(
        self,
        mock_user_repository,
        mock_conversation_repository,
        mock_text_agent_handler,
        mock_response_delivery,
        mock_bot,
    ):
        """Create MessageHandler with mocked dependencies."""
        return MessageHandler(
            user_repository=mock_user_repository,
            conversation_repository=mock_conversation_repository,
            text_agent_handler=mock_text_agent_handler,
            response_delivery=mock_response_delivery,
            bot=mock_bot,
        )

    @pytest.mark.asyncio
    async def test_ac_fr008_001_agent_unavailable_user_notified(
        self,
        handler,
        mock_text_agent_handler,
        mock_bot,
        sample_message,
    ):
        """
        AC-FR008-001: Given agent unavailable, When message sent,
        Then user is notified gracefully.

        Verifies in-character notification when agent fails.
        """
        # Arrange - agent throws exception
        mock_text_agent_handler.handle.side_effect = Exception("Agent unavailable")

        # Act
        await handler.handle(sample_message)

        # Assert - user should receive in-character error message
        mock_bot.send_message.assert_called()
        sent_message = mock_bot.send_message.call_args[1]["text"]

        # Should be in-character, not technical
        assert "error" not in sent_message.lower()
        assert "exception" not in sent_message.lower()
        # Should have some apologetic/in-character tone
        assert any(word in sent_message.lower() for word in [
            "sorry", "moment", "busy", "later", "having", "minute"
        ])

    @pytest.mark.asyncio
    async def test_ac_fr008_001_agent_unavailable_no_crash(
        self,
        handler,
        mock_text_agent_handler,
        sample_message,
    ):
        """
        AC-FR008-001: Agent exception should not crash the handler.

        Verifies graceful degradation without raising exception.
        """
        # Arrange - agent throws exception
        mock_text_agent_handler.handle.side_effect = RuntimeError("LLM API timeout")

        # Act & Assert - should not raise exception
        try:
            await handler.handle(sample_message)
        except Exception as e:
            pytest.fail(f"Handler should not raise exception, but raised: {e}")

    @pytest.mark.asyncio
    async def test_ac_fr008_002_delivery_failure_handled_gracefully(
        self,
        handler,
        mock_response_delivery,
        mock_bot,
        sample_message,
    ):
        """
        AC-FR008-002: Given network timeout, When delivery fails,
        Then error handled gracefully.

        Verifies delivery failures don't crash the handler.
        """
        # Arrange - delivery throws exception
        mock_response_delivery.queue.side_effect = Exception("Network timeout")

        # Act & Assert - should not raise
        try:
            await handler.handle(sample_message)
        except Exception as e:
            pytest.fail(f"Handler should not raise exception, but raised: {e}")

    @pytest.mark.asyncio
    async def test_ac_fr008_003_auth_failure_prompts_reauth(
        self,
        mock_user_repository,
        mock_conversation_repository,
        mock_text_agent_handler,
        mock_response_delivery,
        mock_bot,
        sample_message,
    ):
        """
        AC-FR008-003: Given auth token expired, When messaging,
        Then clear re-auth path provided.

        Verifies that unknown users get registration prompt.
        """
        # Arrange - user not found (simulates expired/invalid auth)
        mock_user_repository.get_by_telegram_id.return_value = None

        handler = MessageHandler(
            user_repository=mock_user_repository,
            conversation_repository=mock_conversation_repository,
            text_agent_handler=mock_text_agent_handler,
            response_delivery=mock_response_delivery,
            bot=mock_bot,
        )

        # Act
        await handler.handle(sample_message)

        # Assert - should send registration prompt
        mock_bot.send_message.assert_called()
        sent_message = mock_bot.send_message.call_args[1]["text"]
        assert "/start" in sent_message.lower() or "register" in sent_message.lower()

    @pytest.mark.asyncio
    async def test_ac_t035_1_try_catch_around_agent_invocation(
        self,
        handler,
        mock_text_agent_handler,
        mock_bot,
        sample_message,
    ):
        """
        AC-T035.1: Try/catch around agent invocation with fallback.

        Verifies agent invocation is wrapped in error handling.
        """
        # Arrange - agent throws various exceptions
        exceptions = [
            TimeoutError("API timeout"),
            ConnectionError("Network error"),
            RuntimeError("Internal error"),
            ValueError("Bad response"),
        ]

        for exc in exceptions:
            mock_text_agent_handler.handle.side_effect = exc
            mock_bot.reset_mock()

            # Act & Assert - should handle each exception type
            try:
                await handler.handle(sample_message)
            except Exception as e:
                pytest.fail(f"Handler should catch {type(exc).__name__}, but raised: {e}")

            # Verify user got feedback
            mock_bot.send_message.assert_called()

    @pytest.mark.asyncio
    async def test_ac_t035_3_notify_user_in_character(
        self,
        handler,
        mock_text_agent_handler,
        mock_bot,
        sample_message,
    ):
        """
        AC-T035.3: Notify user of delay in-character.

        Verifies error messages maintain Nikita's persona.
        """
        # Arrange
        mock_text_agent_handler.handle.side_effect = Exception("Agent error")

        # Act
        await handler.handle(sample_message)

        # Assert - message should be in Nikita's voice
        sent_message = mock_bot.send_message.call_args[1]["text"]

        # Technical terms should NOT be present
        technical_terms = [
            "error", "exception", "failed", "unavailable",
            "timeout", "connection", "api", "server"
        ]
        for term in technical_terms:
            assert term not in sent_message.lower(), f"Message contains technical term: {term}"

    @pytest.mark.asyncio
    async def test_normal_flow_still_works(
        self,
        handler,
        mock_text_agent_handler,
        mock_response_delivery,
        mock_bot,
        sample_message,
    ):
        """
        Verify normal message flow still works after adding error handling.
        """
        # Arrange - normal operation
        mock_decision = MagicMock()
        mock_decision.should_respond = True
        mock_decision.response = "Hey babe!"
        mock_decision.delay_seconds = 0
        mock_text_agent_handler.handle.return_value = mock_decision

        # Act
        await handler.handle(sample_message)

        # Assert - normal flow executed
        mock_text_agent_handler.handle.assert_called_once()
        mock_response_delivery.queue.assert_called_once()
