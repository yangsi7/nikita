"""Response delivery with intelligent message splitting.

Handles delayed delivery of responses to Telegram users, including:
- Typing indicators (AC-FR009-001, AC-FR009-002, AC-FR009-003)
- Intelligent message splitting (4096 char limit)
- Chapter-based timing delays (future: Phase 11)
"""

import asyncio
import re
from uuid import UUID

from nikita.platforms.telegram.bot import TelegramBot


def sanitize_text_response(text: str) -> str:
    """Strip roleplay action markers from text responses (Spec 045 WP-4).

    Removes *action* and **action** patterns that leak from prompt
    cross-contamination. Defense in depth — the prompt also instructs
    against this, but LLMs sometimes ignore instructions.

    Args:
        text: Raw response text from LLM.

    Returns:
        Cleaned text with action markers removed.
    """
    # Remove *action* and **action** patterns (1-50 chars between asterisks)
    cleaned = re.sub(r'\*{1,2}[^*\n]{1,50}\*{1,2}', '', text)
    # Collapse multiple spaces from removal
    cleaned = re.sub(r' {2,}', ' ', cleaned)
    # Clean up leading/trailing whitespace
    return cleaned.strip()


class ResponseDelivery:
    """Deliver responses to Telegram with intelligent splitting.

    Handles Telegram's 4096 character message limit by splitting
    long messages at sentence boundaries.
    """

    # Telegram Bot API message length limit
    MAX_MESSAGE_LENGTH = 4096

    # Typing indicator interval (seconds) - AC-FR009-002
    TYPING_INTERVAL = 5

    def __init__(self, bot: TelegramBot):
        """Initialize ResponseDelivery.

        Args:
            bot: Telegram bot client for sending messages.
        """
        self.bot = bot

    async def queue(
        self,
        user_id: UUID,
        chat_id: int,
        response: str,
        delay_seconds: int,
    ) -> None:
        """Queue response for delivery.

        AC-T016.1: Queues response for delivery
        AC-FR002-002: Response delivered via Telegram
        AC-FR009-002: Periodic typing during delays

        For MVP: Handles delay with periodic typing indicators.
        For Production (Phase 11): Store in database + pg_cron.

        Args:
            user_id: User UUID (for tracking).
            chat_id: Telegram chat ID.
            response: Response text to send.
            delay_seconds: Delay before sending (with periodic typing).
        """
        # AC-FR009-002: Send periodic typing during delay
        if delay_seconds > 0:
            await self._wait_with_typing(chat_id, delay_seconds)

        # Sanitize text response (Spec 045 WP-4: remove *action* markers)
        response = sanitize_text_response(response)

        # Send the actual message
        await self._send_now(chat_id, response)

    async def _wait_with_typing(self, chat_id: int, delay_seconds: int) -> None:
        """Wait for delay while sending periodic typing indicators.

        AC-FR009-002: Typing shows intermittently during delays.

        Args:
            chat_id: Telegram chat ID.
            delay_seconds: Total delay in seconds.
        """
        elapsed = 0
        while elapsed < delay_seconds:
            # Send typing indicator
            await self.bot.send_chat_action(chat_id, "typing")

            # Wait for interval or remaining time (whichever is shorter)
            wait_time = min(self.TYPING_INTERVAL, delay_seconds - elapsed)
            await asyncio.sleep(wait_time)
            elapsed += wait_time

    async def _send_now(self, chat_id: int, response: str) -> None:
        """Send response immediately with typing indicator.

        AC-T016.3: Sends with typing indicator
        AC-T016.4: Splits messages intelligently
        AC-FR007-001: Long messages split intelligently

        Args:
            chat_id: Telegram chat ID.
            response: Response text to send.
        """
        # AC-T016.3: Send typing indicator
        await self.bot.send_chat_action(chat_id, "typing")

        # Brief pause for realism
        await asyncio.sleep(0.5)

        # AC-T016.4 & AC-FR007-001: Split if necessary
        chunks = self._split_message(response)

        # Send all chunks
        for chunk in chunks:
            await self.bot.send_message(chat_id=chat_id, text=chunk)

    def _split_message(self, text: str) -> list[str]:
        """Split long message into chunks at sentence boundaries.

        AC-FR007-001: Split intelligently (not mid-word)

        Splits at sentence boundaries (". ") to preserve readability.
        Falls back to word boundaries if sentences too long.

        Args:
            text: Message text to split.

        Returns:
            List of message chunks, each ≤ MAX_MESSAGE_LENGTH.
        """
        # If short enough, return as-is
        if len(text) <= self.MAX_MESSAGE_LENGTH:
            return [text]

        chunks = []
        current = ""

        # Try splitting at sentence boundaries first
        sentences = text.split(". ")

        for i, sentence in enumerate(sentences):
            # Add back the period (except for last sentence)
            sentence_with_period = sentence + (". " if i < len(sentences) - 1 else "")

            # Check if adding this sentence would exceed limit
            if len(current) + len(sentence_with_period) > self.MAX_MESSAGE_LENGTH:
                # Current chunk is full
                if current:
                    chunks.append(current.rstrip())
                    current = sentence_with_period
                else:
                    # Single sentence too long - split at word boundary
                    words = sentence_with_period.split()
                    word_chunk = ""
                    for word in words:
                        if len(word_chunk) + len(word) + 1 > self.MAX_MESSAGE_LENGTH:
                            chunks.append(word_chunk.rstrip())
                            word_chunk = word + " "
                        else:
                            word_chunk += word + " "
                    current = word_chunk
            else:
                current += sentence_with_period

        # Add final chunk
        if current:
            chunks.append(current.rstrip())

        return chunks
