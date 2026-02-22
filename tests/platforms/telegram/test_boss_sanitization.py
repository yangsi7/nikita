"""Tests for boss message sanitization (Spec 065).

Verifies that *action* markers are stripped from all boss messages
before delivery to the player.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from nikita.platforms.telegram.delivery import sanitize_text_response


class TestSanitizeTextResponse:
    """Unit tests for sanitize_text_response."""

    def test_strips_single_asterisk_actions(self):
        assert sanitize_text_response("Hello *sighs* world") == "Hello world"

    def test_strips_double_asterisk_actions(self):
        assert sanitize_text_response("Hello **takes a deep breath** world") == "Hello world"

    def test_strips_long_pause(self):
        assert sanitize_text_response("I see *long pause* okay") == "I see okay"

    def test_preserves_normal_text(self):
        assert sanitize_text_response("Hello world") == "Hello world"

    def test_strips_multiple_actions(self):
        text = "*sighs* Look, *takes a deep breath* I need to tell you *long pause* something."
        result = sanitize_text_response(text)
        assert "*" not in result
        assert "Look," in result
        assert "something." in result

    def test_preserves_emojis(self):
        assert "💕" in sanitize_text_response("I love you 💕")

    def test_strips_action_at_start(self):
        result = sanitize_text_response("*rolls eyes* Fine.")
        assert "rolls eyes" not in result
        assert "Fine." in result

    def test_strips_action_at_end(self):
        result = sanitize_text_response("Okay *smiles*")
        assert "smiles" not in result
        assert "Okay" in result

    def test_collapses_extra_spaces(self):
        result = sanitize_text_response("Hello *sighs* *pauses* world")
        # Should not have triple spaces
        assert "   " not in result

    def test_empty_string(self):
        assert sanitize_text_response("") == ""

    def test_only_action_marker(self):
        result = sanitize_text_response("*sighs*")
        assert result == ""

    def test_action_with_punctuation_preserved(self):
        result = sanitize_text_response("I... *long pause* ...don't know.")
        assert "I..." in result
        assert "...don't know." in result


class TestSendSanitizedIntegration:
    """Integration tests: _send_sanitized uses sanitize_text_response."""

    @pytest.mark.asyncio
    async def test_send_sanitized_strips_action_before_delivery(self):
        """_send_sanitized must strip *action* markers before calling bot.send_message."""
        from nikita.platforms.telegram.message_handler import MessageHandler

        # Set up mock handler with real _send_sanitized bound
        handler = MagicMock()
        handler.bot = AsyncMock()
        handler.bot.send_message = AsyncMock()
        handler._send_sanitized = MessageHandler._send_sanitized.__get__(handler)

        text_with_action = "*sighs deeply* I can't believe you did that."
        await handler._send_sanitized(12345, text_with_action)

        # Verify send_message was called once
        handler.bot.send_message.assert_called_once()
        call_kwargs = handler.bot.send_message.call_args.kwargs
        assert call_kwargs["chat_id"] == 12345
        # Verify action marker was stripped
        assert "*" not in call_kwargs["text"]
        assert "I can't believe you did that." in call_kwargs["text"]

    @pytest.mark.asyncio
    async def test_send_sanitized_preserves_clean_text(self):
        """_send_sanitized passes clean text through unchanged (aside from strip)."""
        from nikita.platforms.telegram.message_handler import MessageHandler

        handler = MagicMock()
        handler.bot = AsyncMock()
        handler.bot.send_message = AsyncMock()
        handler._send_sanitized = MessageHandler._send_sanitized.__get__(handler)

        clean_text = "You know what? That was actually really good. 💕"
        await handler._send_sanitized(99999, clean_text)

        call_kwargs = handler.bot.send_message.call_args.kwargs
        assert call_kwargs["chat_id"] == 99999
        assert "You know what? That was actually really good." in call_kwargs["text"]
        assert "💕" in call_kwargs["text"]

    @pytest.mark.asyncio
    async def test_send_boss_opening_sanitizes_output(self):
        """_send_boss_opening sends sanitized opening via _send_sanitized."""
        from nikita.platforms.telegram.message_handler import MessageHandler

        handler = MagicMock()
        handler.bot = AsyncMock()
        handler.bot.send_message = AsyncMock()
        handler.bot.send_chat_action = AsyncMock()
        handler._send_sanitized = MessageHandler._send_sanitized.__get__(handler)
        handler._send_boss_opening = MessageHandler._send_boss_opening.__get__(handler)

        # Patch get_boss_prompt to return a prompt with action markers
        mock_prompt = {
            "in_character_opening": "*narrows eyes* You think you know me? Prove it.",
            "challenge_context": "test",
            "success_criteria": "test",
        }

        with patch(
            "nikita.engine.chapters.prompts.get_boss_prompt",
            return_value=mock_prompt,
        ), patch("asyncio.sleep", new_callable=AsyncMock):
            await handler._send_boss_opening(chat_id=12345, chapter=1)

        # send_message should have been called with sanitized text
        handler.bot.send_message.assert_called_once()
        call_text = handler.bot.send_message.call_args.kwargs["text"]
        assert "*" not in call_text
        assert "You think you know me? Prove it." in call_text
