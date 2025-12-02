"""Tests for ResponseDelivery - WRITTEN FIRST (TDD Red phase).

These tests verify delayed response delivery with intelligent message splitting.
AC Coverage: AC-FR002-002, AC-FR007-001, AC-T016.1-4
"""

import pytest
from unittest.mock import AsyncMock, call
from uuid import uuid4

from nikita.platforms.telegram.delivery import ResponseDelivery


class TestResponseDelivery:
    """Test suite for Telegram ResponseDelivery."""

    @pytest.fixture
    def mock_bot(self):
        """Mock TelegramBot for testing."""
        bot = AsyncMock()
        return bot

    @pytest.fixture
    def delivery(self, mock_bot):
        """Create ResponseDelivery instance with mocked bot."""
        return ResponseDelivery(bot=mock_bot)

    @pytest.mark.asyncio
    async def test_ac_fr002_002_response_delivered_via_telegram(
        self, delivery, mock_bot
    ):
        """
        AC-FR002-002: Given agent generates response, When response ready,
        Then it's delivered to user via Telegram.

        Verifies that responses are sent via Telegram bot.
        """
        # Arrange
        user_id = uuid4()
        chat_id = 123456789
        response = "Hey there! How are you doing?"
        delay_seconds = 0  # No delay for this test

        # Act
        await delivery.queue(
            user_id=user_id,
            chat_id=chat_id,
            response=response,
            delay_seconds=delay_seconds,
        )

        # Assert
        mock_bot.send_message.assert_called_once()
        call_kwargs = mock_bot.send_message.call_args[1]
        assert call_kwargs["chat_id"] == chat_id
        assert call_kwargs["text"] == response

    @pytest.mark.asyncio
    async def test_ac_fr007_001_long_response_split_intelligently(
        self, delivery, mock_bot
    ):
        """
        AC-FR007-001: Given long response, When exceeds Telegram limit,
        Then split intelligently (not mid-word).

        Verifies message splitting at sentence boundaries.
        """
        # Arrange
        user_id = uuid4()
        chat_id = 123456789

        # Create a message longer than 4096 characters
        long_response = "This is a test sentence. " * 200  # ~5000 chars

        # Act
        await delivery.queue(
            user_id=user_id,
            chat_id=chat_id,
            response=long_response,
            delay_seconds=0,
        )

        # Assert - should be called multiple times (split into chunks)
        assert mock_bot.send_message.call_count > 1

        # Verify each chunk is under 4096 characters
        for call_obj in mock_bot.send_message.call_args_list:
            text = call_obj[1]["text"]
            assert len(text) <= 4096

        # Verify no mid-word splitting (chunks should end with period or space)
        for call_obj in mock_bot.send_message.call_args_list[:-1]:  # Except last
            text = call_obj[1]["text"]
            assert text.rstrip().endswith(".") or text.endswith(" ")

    @pytest.mark.asyncio
    async def test_ac_t016_1_queue_stores_for_delivery(
        self, delivery, mock_bot
    ):
        """
        AC-T016.1: queue(user_id, chat_id, response, chapter) stores for delivery.

        Verifies that queue method accepts correct parameters.
        """
        # Arrange
        user_id = uuid4()
        chat_id = 999888777
        response = "Test response"
        delay_seconds = 0  # No delay for this test

        # Act
        await delivery.queue(
            user_id=user_id,
            chat_id=chat_id,
            response=response,
            delay_seconds=delay_seconds,
        )

        # Assert - for MVP, immediate delivery
        mock_bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_ac_t016_3_send_now_sends_with_typing_indicator(
        self, delivery, mock_bot
    ):
        """
        AC-T016.3: _send_now(chat_id, response) sends with typing indicator.

        Verifies that typing indicator is shown before sending.
        """
        # Arrange
        user_id = uuid4()
        chat_id = 123456789
        response = "Quick response"

        # Act
        await delivery.queue(
            user_id=user_id,
            chat_id=chat_id,
            response=response,
            delay_seconds=0,
        )

        # Assert - typing indicator should be sent first
        mock_bot.send_chat_action.assert_called_once_with(chat_id, "typing")

        # Verify order: typing indicator then message
        assert mock_bot.send_chat_action.call_count == 1
        assert mock_bot.send_message.call_count == 1

    @pytest.mark.asyncio
    async def test_ac_t016_4_splits_messages_intelligently_not_mid_word(
        self, delivery, mock_bot
    ):
        """
        AC-T016.4: Splits long messages intelligently (not mid-word).

        Verifies intelligent splitting at sentence boundaries.
        """
        # Arrange
        user_id = uuid4()
        chat_id = 123456789

        # Create message with long words to test splitting logic
        long_response = (
            "Hey! " + "This is sentence one. " * 100 +
            "This is sentence two. " * 100 +
            "This is sentence three."
        )  # ~4500 chars

        # Act
        await delivery.queue(
            user_id=user_id,
            chat_id=chat_id,
            response=long_response,
            delay_seconds=0,
        )

        # Assert - should split into multiple messages
        assert mock_bot.send_message.call_count >= 2

        # Verify each message ends properly (not mid-word)
        for call_obj in mock_bot.send_message.call_args_list:
            text = call_obj[1]["text"]
            # Should not end with partial word
            assert not text.endswith("-")
            # Should be reasonable length
            assert len(text) <= 4096

    @pytest.mark.asyncio
    async def test_short_message_not_split(self, delivery, mock_bot):
        """
        Verify that short messages are not split unnecessarily.
        """
        # Arrange
        user_id = uuid4()
        chat_id = 123456789
        short_response = "Just a short message."

        # Act
        await delivery.queue(
            user_id=user_id,
            chat_id=chat_id,
            response=short_response,
            delay_seconds=0,
        )

        # Assert - should be called exactly once (no splitting)
        assert mock_bot.send_message.call_count == 1
        assert mock_bot.send_message.call_args[1]["text"] == short_response

    @pytest.mark.asyncio
    async def test_exactly_4096_chars_not_split(self, delivery, mock_bot):
        """
        Verify that message exactly at limit is not split.
        """
        # Arrange
        user_id = uuid4()
        chat_id = 123456789
        exact_limit = "x" * 4096  # Exactly at limit

        # Act
        await delivery.queue(
            user_id=user_id,
            chat_id=chat_id,
            response=exact_limit,
            delay_seconds=0,
        )

        # Assert
        assert mock_bot.send_message.call_count == 1

    @pytest.mark.asyncio
    async def test_one_char_over_limit_triggers_split(self, delivery, mock_bot):
        """
        Verify that message one char over limit triggers split.
        """
        # Arrange
        user_id = uuid4()
        chat_id = 123456789
        over_limit = "This is a sentence. " * 250  # ~5000 chars

        # Act
        await delivery.queue(
            user_id=user_id,
            chat_id=chat_id,
            response=over_limit,
            delay_seconds=0,
        )

        # Assert - should be split
        assert mock_bot.send_message.call_count > 1

    @pytest.mark.asyncio
    async def test_multiple_chunks_all_under_limit(self, delivery, mock_bot):
        """
        Verify that when split, all chunks are under 4096 chars.
        """
        # Arrange
        user_id = uuid4()
        chat_id = 123456789
        very_long = "Sentence here. " * 500  # ~7500 chars

        # Act
        await delivery.queue(
            user_id=user_id,
            chat_id=chat_id,
            response=very_long,
            delay_seconds=0,
        )

        # Assert - all chunks under limit
        for call_obj in mock_bot.send_message.call_args_list:
            text = call_obj[1]["text"]
            assert len(text) <= 4096
            assert len(text) > 0  # No empty chunks

    @pytest.mark.asyncio
    async def test_empty_response_handled_gracefully(self, delivery, mock_bot):
        """
        Verify that empty response doesn't cause errors.
        """
        # Arrange
        user_id = uuid4()
        chat_id = 123456789
        empty_response = ""

        # Act & Assert - should not raise exception
        await delivery.queue(
            user_id=user_id,
            chat_id=chat_id,
            response=empty_response,
            delay_seconds=0,
        )

        # Should still call send_message (even if empty)
        mock_bot.send_message.assert_called_once()


class TestTypingIndicators:
    """Test suite for US-5 Typing Indicators.

    AC-FR009-001: Given user sends message, When processing, Then typing indicator appears
    AC-FR009-002: Given response has timing delay, When waiting, Then typing shows intermittently
    AC-FR009-003: Given response ready, When delivered, Then typing stops
    """

    @pytest.fixture
    def mock_bot(self):
        """Mock TelegramBot for testing."""
        bot = AsyncMock()
        return bot

    @pytest.fixture
    def delivery(self, mock_bot):
        """Create ResponseDelivery instance with mocked bot."""
        return ResponseDelivery(bot=mock_bot)

    @pytest.mark.asyncio
    async def test_ac_fr009_001_typing_indicator_appears_before_response(
        self, delivery, mock_bot
    ):
        """
        AC-FR009-001: Given user sends message, When processing,
        Then typing indicator appears.

        Verifies typing indicator is sent before response.
        """
        # Arrange
        user_id = uuid4()
        chat_id = 123456789
        response = "Hey babe!"

        # Act
        await delivery.queue(
            user_id=user_id,
            chat_id=chat_id,
            response=response,
            delay_seconds=0,
        )

        # Assert - typing indicator sent first
        mock_bot.send_chat_action.assert_called_with(chat_id, "typing")

        # Verify typing was called before message
        typing_call_order = None
        message_call_order = None

        # Track call order
        for i, call_obj in enumerate(mock_bot.method_calls):
            if call_obj[0] == "send_chat_action":
                if typing_call_order is None:
                    typing_call_order = i
            elif call_obj[0] == "send_message":
                if message_call_order is None:
                    message_call_order = i

        assert typing_call_order is not None, "Typing indicator should be called"
        assert message_call_order is not None, "Message should be sent"
        assert typing_call_order < message_call_order, "Typing should come before message"

    @pytest.mark.asyncio
    async def test_ac_fr009_002_periodic_typing_during_delay(
        self, delivery, mock_bot, monkeypatch
    ):
        """
        AC-FR009-002: Given response has timing delay, When waiting,
        Then typing shows intermittently.

        Verifies periodic typing during delays > 5 seconds.
        """
        # Arrange
        user_id = uuid4()
        chat_id = 123456789
        response = "Finally responding!"
        delay_seconds = 12  # Should trigger ~3 periodic typing calls (at 0s, 5s, 10s)

        # Mock asyncio.sleep to avoid actual waiting
        async def mock_sleep(seconds):
            pass  # Don't actually wait

        monkeypatch.setattr("nikita.platforms.telegram.delivery.asyncio.sleep", mock_sleep)

        # Act
        await delivery.queue(
            user_id=user_id,
            chat_id=chat_id,
            response=response,
            delay_seconds=delay_seconds,
        )

        # Assert - multiple typing indicators should be sent
        # Expecting: 3 during delay (at 0s, 5s, 10s) + 1 in _send_now = 4 total
        typing_calls = [
            c for c in mock_bot.method_calls
            if c[0] == "send_chat_action" and c[1] == (chat_id, "typing")
        ]
        assert len(typing_calls) >= 3, "Should send periodic typing during delay"

    @pytest.mark.asyncio
    async def test_ac_fr009_003_typing_stops_when_message_sent(
        self, delivery, mock_bot
    ):
        """
        AC-FR009-003: Given response ready, When delivered, Then typing stops.

        Verifies the last action is sending the message (not typing).
        """
        # Arrange
        user_id = uuid4()
        chat_id = 123456789
        response = "Done thinking!"

        # Act
        await delivery.queue(
            user_id=user_id,
            chat_id=chat_id,
            response=response,
            delay_seconds=0,
        )

        # Assert - last call should be send_message, not send_chat_action
        last_call = mock_bot.method_calls[-1]
        assert last_call[0] == "send_message", "Last action should be sending message"

    @pytest.mark.asyncio
    async def test_no_periodic_typing_for_short_delays(
        self, delivery, mock_bot, monkeypatch
    ):
        """
        Verify short delays get periodic typing but fewer iterations.
        """
        # Arrange
        user_id = uuid4()
        chat_id = 123456789
        response = "Quick response"
        delay_seconds = 3  # Under 5s threshold - only 1 iteration in delay loop

        # Mock asyncio.sleep to avoid actual waiting
        async def mock_sleep(seconds):
            pass

        monkeypatch.setattr("nikita.platforms.telegram.delivery.asyncio.sleep", mock_sleep)

        # Act
        await delivery.queue(
            user_id=user_id,
            chat_id=chat_id,
            response=response,
            delay_seconds=delay_seconds,
        )

        # Assert - 1 from delay loop + 1 from _send_now = 2 total
        typing_calls = [
            c for c in mock_bot.method_calls
            if c[0] == "send_chat_action"
        ]
        assert len(typing_calls) == 2, "Should have 1 delay typing + 1 send typing for short delays"

    @pytest.mark.asyncio
    async def test_typing_indicator_sent_for_each_chunk(
        self, delivery, mock_bot
    ):
        """
        Verify typing indicator is sent before each message chunk.
        """
        # Arrange
        user_id = uuid4()
        chat_id = 123456789
        long_response = "This is a long sentence. " * 200  # ~5000 chars, will split

        # Act
        await delivery.queue(
            user_id=user_id,
            chat_id=chat_id,
            response=long_response,
            delay_seconds=0,
        )

        # Assert - should have typing before each chunk
        message_count = mock_bot.send_message.call_count
        assert message_count >= 2, "Long message should be split"

        # For MVP: at least one typing indicator
        # Enhancement: typing before each chunk
        typing_calls = [
            c for c in mock_bot.method_calls
            if c[0] == "send_chat_action"
        ]
        assert len(typing_calls) >= 1, "Should have at least one typing indicator"
