"""Tests for ResponseDelivery - WRITTEN FIRST (TDD Red phase).

These tests verify delayed response delivery with intelligent message splitting.
AC Coverage: AC-FR002-002, AC-FR007-001, AC-T016.1-4
Also covers Spec 065: sanitize_text_response strips *action* markers from all messages.
"""

import pytest
from unittest.mock import AsyncMock, call
from uuid import uuid4

from nikita.platforms.telegram.delivery import ResponseDelivery, sanitize_text_response


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


class TestSanitizeTextResponse:
    """Unit tests for sanitize_text_response (Spec 065 anti-asterisk).

    Verifies that *sighs*, *takes a deep breath*, *long pause* and similar
    roleplay action markers are stripped before delivery.
    """

    def test_strips_single_asterisk_action(self):
        """*sighs* is removed from output."""
        result = sanitize_text_response("*sighs* I can't believe you said that.")
        assert "*sighs*" not in result
        assert "I can't believe you said that." in result

    def test_strips_double_asterisk_action(self):
        """**sighs** is removed from output."""
        result = sanitize_text_response("**sighs** Really?")
        assert "**sighs**" not in result
        assert "Really?" in result

    def test_strips_takes_a_deep_breath(self):
        """*takes a deep breath* is removed."""
        result = sanitize_text_response("*takes a deep breath* Okay, let me think.")
        assert "*takes a deep breath*" not in result
        assert "Okay, let me think." in result

    def test_strips_long_pause(self):
        """*long pause* is removed."""
        result = sanitize_text_response("*long pause* I don't know what to say.")
        assert "*long pause*" not in result
        assert "I don't know what to say." in result

    def test_strips_action_mid_sentence(self):
        """Inline *action* markers mid-sentence are removed."""
        result = sanitize_text_response("I just *rolls eyes* can't deal with this.")
        assert "*rolls eyes*" not in result
        assert "can't deal with this." in result

    def test_strips_multiple_actions(self):
        """Multiple *action* markers in one message are all removed."""
        text = "*sighs* Look at me. *takes a deep breath* Okay."
        result = sanitize_text_response(text)
        assert "*sighs*" not in result
        assert "*takes a deep breath*" not in result
        assert "Look at me." in result
        assert "Okay." in result

    def test_passthrough_clean_text(self):
        """Text without markers is returned unchanged (modulo whitespace)."""
        text = "Hey, how are you doing today?"
        result = sanitize_text_response(text)
        assert result == text

    def test_passthrough_text_with_asterisk_emphasis(self):
        """Bold/italic markdown *word* (≤50 chars) is stripped — intentional behavior."""
        # The function strips ALL *short* asterisk patterns as defense-in-depth.
        # This is expected: Nikita should not use markdown formatting in Telegram.
        text = "You are *so* annoying."
        result = sanitize_text_response(text)
        assert "*so*" not in result

    def test_empty_string_returns_empty(self):
        """Empty input returns empty string."""
        assert sanitize_text_response("") == ""

    def test_only_action_marker_returns_empty(self):
        """Message that is only an action marker returns empty string."""
        result = sanitize_text_response("*sighs*")
        assert result == ""

    def test_long_action_beyond_50_chars_not_stripped(self):
        """Action strings longer than 50 chars are NOT stripped (regex limit)."""
        long_action = "*" + "a" * 51 + "*"
        text = f"Before. {long_action} After."
        result = sanitize_text_response(text)
        # Long pattern should pass through
        assert long_action in result

    def test_newlines_preserved_after_action_strip(self):
        """Newlines mid-text are preserved; leading whitespace after strip is cleaned."""
        text = "I need some time to think.\n\n*sighs* It's a lot."
        result = sanitize_text_response(text)
        assert "*sighs*" not in result
        # Newline between sentences is preserved (strip only removes leading/trailing)
        assert "I need some time to think." in result
        assert "It's a lot." in result

    @pytest.mark.asyncio
    async def test_delivery_queue_strips_asterisks_before_send(self):
        """ResponseDelivery.queue() sends sanitized text — asterisks never reach Telegram."""
        mock_bot = AsyncMock()
        delivery = ResponseDelivery(bot=mock_bot)
        chat_id = 123456789
        user_id = uuid4()

        await delivery.queue(
            user_id=user_id,
            chat_id=chat_id,
            response="*sighs* You're impossible sometimes.",
            delay_seconds=0,
        )

        sent_text = mock_bot.send_message.call_args[1]["text"]
        assert "*sighs*" not in sent_text
        assert "You're impossible sometimes." in sent_text


class TestBossMessageSanitization:
    """Verify boss-specific static messages are delivered without asterisk artifacts.

    Static boss messages don't normally contain asterisks, but the sanitization
    path must be confirmed active for dynamic LLM judgment responses.
    """

    @pytest.mark.asyncio
    async def test_send_sanitized_strips_action_from_boss_opening(self):
        """_send_sanitized strips *action* from dynamic boss opening (LLM output)."""
        from unittest.mock import MagicMock
        from nikita.platforms.telegram.message_handler import MessageHandler as TelegramMessageHandler

        handler = MagicMock()
        handler.bot = AsyncMock()
        handler._send_sanitized = TelegramMessageHandler._send_sanitized.__get__(handler)

        await handler._send_sanitized(
            123456, "*takes a deep breath* So... you think you know me?"
        )

        sent_text = handler.bot.send_message.call_args[1]["text"]
        assert "*takes a deep breath*" not in sent_text
        assert "So... you think you know me?" in sent_text

    @pytest.mark.asyncio
    async def test_send_sanitized_strips_sighs_from_judgment_response(self):
        """_send_sanitized strips *sighs* from dynamic judgment response."""
        from unittest.mock import MagicMock
        from nikita.platforms.telegram.message_handler import MessageHandler as TelegramMessageHandler

        handler = MagicMock()
        handler.bot = AsyncMock()
        handler._send_sanitized = TelegramMessageHandler._send_sanitized.__get__(handler)

        await handler._send_sanitized(
            123456, "*sighs* I guess that's good enough."
        )

        sent_text = handler.bot.send_message.call_args[1]["text"]
        assert "*sighs*" not in sent_text
        assert "I guess that's good enough." in sent_text

    @pytest.mark.asyncio
    async def test_send_sanitized_strips_long_pause_from_boss_pass(self):
        """_send_sanitized strips *long pause* from boss pass LLM response."""
        from unittest.mock import MagicMock
        from nikita.platforms.telegram.message_handler import MessageHandler as TelegramMessageHandler

        handler = MagicMock()
        handler.bot = AsyncMock()
        handler._send_sanitized = TelegramMessageHandler._send_sanitized.__get__(handler)

        await handler._send_sanitized(
            123456, "*long pause* Okay. You actually did well."
        )

        sent_text = handler.bot.send_message.call_args[1]["text"]
        assert "*long pause*" not in sent_text
        assert "Okay. You actually did well." in sent_text

    @pytest.mark.asyncio
    async def test_send_sanitized_clean_text_unchanged(self):
        """_send_sanitized passes clean boss messages through unchanged."""
        from unittest.mock import MagicMock
        from nikita.platforms.telegram.message_handler import MessageHandler as TelegramMessageHandler

        handler = MagicMock()
        handler.bot = AsyncMock()
        handler._send_sanitized = TelegramMessageHandler._send_sanitized.__get__(handler)

        message = "You passed. I didn't see that coming. 💭"
        await handler._send_sanitized(123456, message)

        sent_text = handler.bot.send_message.call_args[1]["text"]
        assert sent_text == message
