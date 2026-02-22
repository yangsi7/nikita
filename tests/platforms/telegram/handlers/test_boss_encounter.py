"""Unit tests for BossEncounterHandler (Strangler Fig, Phase 2).

Tests each public method of BossEncounterHandler in isolation using
async mocks.  No real network or database calls are made.
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from nikita.platforms.telegram.handlers.boss_encounter import (
    BossEncounterHandler,
    BOSS_PASS_MESSAGES,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_bot():
    bot = MagicMock()
    bot.send_message = AsyncMock()
    bot.send_chat_action = AsyncMock()
    return bot


@pytest.fixture
def mock_user_repo():
    repo = MagicMock()
    repo.update_conflict_details = AsyncMock()
    repo.set_boss_fight_status = AsyncMock()
    return repo


@pytest.fixture
def mock_conversation_repo():
    repo = MagicMock()
    repo.get_active_conversation = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def mock_boss_judgment():
    judgment = MagicMock()
    judgment.judge_boss_outcome = AsyncMock()
    judgment.judge_multi_phase_outcome = AsyncMock()
    return judgment


@pytest.fixture
def mock_boss_state_machine():
    sm = MagicMock()
    sm.process_outcome = AsyncMock()
    return sm


@pytest.fixture
def handler(
    mock_bot,
    mock_user_repo,
    mock_conversation_repo,
    mock_boss_judgment,
    mock_boss_state_machine,
):
    return BossEncounterHandler(
        bot=mock_bot,
        user_repository=mock_user_repo,
        conversation_repository=mock_conversation_repo,
        boss_judgment=mock_boss_judgment,
        boss_state_machine=mock_boss_state_machine,
    )


@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = "user-abc-123"
    user.chapter = 1
    user.conflict_details = None
    return user


# ---------------------------------------------------------------------------
# send_boss_opening
# ---------------------------------------------------------------------------

class TestSendBossOpening:
    """Tests for BossEncounterHandler.send_boss_opening."""

    @pytest.mark.asyncio
    async def test_sends_sanitized_opening_message(self, handler, mock_bot):
        """Opening message is fetched, sanitized, and sent to chat."""
        mock_prompt = {
            "in_character_opening": "*narrows eyes* Prove yourself.",
            "challenge_context": "test",
            "success_criteria": "test",
        }
        with patch(
            "nikita.engine.chapters.prompts.get_boss_prompt",
            return_value=mock_prompt,
        ), patch("asyncio.sleep", new_callable=AsyncMock):
            await handler.send_boss_opening(chat_id=12345, chapter=1)

        mock_bot.send_message.assert_called_once()
        call_text = mock_bot.send_message.call_args.kwargs["text"]
        assert "*" not in call_text
        assert "Prove yourself." in call_text

    @pytest.mark.asyncio
    async def test_empty_opening_skips_send(self, handler, mock_bot):
        """If in_character_opening is empty, no message is sent."""
        mock_prompt = {"in_character_opening": ""}
        with patch(
            "nikita.engine.chapters.prompts.get_boss_prompt",
            return_value=mock_prompt,
        ), patch("asyncio.sleep", new_callable=AsyncMock):
            await handler.send_boss_opening(chat_id=12345, chapter=1)

        mock_bot.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_exception_is_swallowed(self, handler, mock_bot):
        """Errors in send_boss_opening are caught and logged, not raised."""
        with patch(
            "nikita.engine.chapters.prompts.get_boss_prompt",
            side_effect=RuntimeError("prompt fetch failed"),
        ):
            # Should not raise
            await handler.send_boss_opening(chat_id=12345, chapter=1)

        mock_bot.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_correct_chat_id_passed(self, handler, mock_bot):
        """send_boss_opening uses the chat_id it receives."""
        mock_prompt = {"in_character_opening": "Hello."}
        with patch(
            "nikita.engine.chapters.prompts.get_boss_prompt",
            return_value=mock_prompt,
        ), patch("asyncio.sleep", new_callable=AsyncMock):
            await handler.send_boss_opening(chat_id=99999, chapter=2)

        call_kwargs = mock_bot.send_message.call_args.kwargs
        assert call_kwargs["chat_id"] == 99999


# ---------------------------------------------------------------------------
# handle_single_turn_boss
# ---------------------------------------------------------------------------

class TestHandleSingleTurnBoss:
    """Tests for BossEncounterHandler.handle_single_turn_boss."""

    @pytest.mark.asyncio
    async def test_pass_sends_pass_message(
        self, handler, mock_bot, mock_boss_judgment, mock_boss_state_machine, mock_user
    ):
        """PASS outcome sends the chapter-specific congratulations message."""
        mock_boss_judgment.judge_boss_outcome.return_value = MagicMock(
            outcome="PASS", reasoning="great answer"
        )
        mock_boss_state_machine.process_outcome.return_value = {
            "passed": True,
            "new_chapter": 2,
        }

        with patch(
            "nikita.engine.chapters.prompts.get_boss_prompt",
            return_value={"in_character_opening": "Q?", "success_criteria": "S"},
        ), patch("asyncio.sleep", new_callable=AsyncMock):
            await handler.handle_single_turn_boss(mock_user, "great answer", chat_id=111)

        # Pass message should have been sent (bot.send_message called)
        assert mock_bot.send_message.called
        sent_text = mock_bot.send_message.call_args.kwargs["text"]
        # Chapter 1 pass message content check
        assert "attention" in sent_text or "curious" in sent_text

    @pytest.mark.asyncio
    async def test_fail_no_game_over_sends_fail_message(
        self, handler, mock_bot, mock_boss_judgment, mock_boss_state_machine, mock_user
    ):
        """FAIL without game_over sends the retry message."""
        mock_boss_judgment.judge_boss_outcome.return_value = MagicMock(
            outcome="FAIL", reasoning="bad answer"
        )
        mock_boss_state_machine.process_outcome.return_value = {
            "passed": False,
            "game_over": False,
            "attempts": 1,
        }

        with patch(
            "nikita.engine.chapters.prompts.get_boss_prompt",
            return_value={"in_character_opening": "Q?", "success_criteria": "S"},
        ), patch("asyncio.sleep", new_callable=AsyncMock):
            await handler.handle_single_turn_boss(mock_user, "bad answer", chat_id=111)

        sent_text = mock_bot.send_message.call_args.kwargs["text"]
        assert "chance" in sent_text.lower()

    @pytest.mark.asyncio
    async def test_fail_with_game_over_sends_game_over_message(
        self, handler, mock_bot, mock_boss_judgment, mock_boss_state_machine, mock_user
    ):
        """FAIL with game_over sends the game-over breakup message."""
        mock_boss_judgment.judge_boss_outcome.return_value = MagicMock(
            outcome="FAIL", reasoning="terrible"
        )
        mock_boss_state_machine.process_outcome.return_value = {
            "passed": False,
            "game_over": True,
            "attempts": 3,
        }

        with patch(
            "nikita.engine.chapters.prompts.get_boss_prompt",
            return_value={"in_character_opening": "Q?", "success_criteria": "S"},
        ), patch("asyncio.sleep", new_callable=AsyncMock):
            await handler.handle_single_turn_boss(mock_user, "terrible", chat_id=111)

        sent_text = mock_bot.send_message.call_args.kwargs["text"]
        assert "done" in sent_text.lower() or "goodbye" in sent_text.lower()

    @pytest.mark.asyncio
    async def test_pass_chapter_5_sends_game_won_message(
        self, handler, mock_bot, mock_boss_judgment, mock_boss_state_machine, mock_user
    ):
        """PASS on chapter 5 (new_chapter > 5) sends the victory message."""
        mock_user.chapter = 5
        mock_boss_judgment.judge_boss_outcome.return_value = MagicMock(
            outcome="PASS", reasoning="perfect"
        )
        mock_boss_state_machine.process_outcome.return_value = {
            "passed": True,
            "new_chapter": 6,  # > 5 triggers game-won
        }

        with patch(
            "nikita.engine.chapters.prompts.get_boss_prompt",
            return_value={"in_character_opening": "Q?", "success_criteria": "S"},
        ), patch("asyncio.sleep", new_callable=AsyncMock):
            await handler.handle_single_turn_boss(mock_user, "perfect", chat_id=111)

        sent_text = mock_bot.send_message.call_args.kwargs["text"]
        assert "love you" in sent_text.lower() or "you're the one" in sent_text.lower()


# ---------------------------------------------------------------------------
# Outcome delivery helpers
# ---------------------------------------------------------------------------

class TestOutcomeDelivery:
    """Tests for standalone outcome message helpers."""

    @pytest.mark.asyncio
    async def test_send_boss_pass_message_chapter_specific(self, handler, mock_bot):
        """Chapter-specific pass message is sent for chapters 1-5."""
        await handler.send_boss_pass_message(chat_id=1, old_chapter=1, new_chapter=2)

        sent_text = mock_bot.send_message.call_args.kwargs["text"]
        # Chapter 1 BOSS_PASS_MESSAGES contains "attention"
        assert "attention" in sent_text

    @pytest.mark.asyncio
    async def test_send_boss_pass_message_generic_fallback(self, handler, mock_bot):
        """Generic pass message used for chapters not in BOSS_PASS_MESSAGES."""
        with patch(
            "nikita.engine.constants.CHAPTER_NAMES",
            {99: "Chapter 99"},
        ):
            await handler.send_boss_pass_message(
                chat_id=1, old_chapter=99, new_chapter=100
            )

        sent_text = mock_bot.send_message.call_args.kwargs["text"]
        assert "proved" in sent_text.lower()

    @pytest.mark.asyncio
    async def test_send_boss_fail_message_two_remaining(self, handler, mock_bot):
        """Fail message with 2 remaining chances uses the encouraging variant."""
        await handler.send_boss_fail_message(chat_id=1, attempts=1, chapter=1)

        sent_text = mock_bot.send_message.call_args.kwargs["text"]
        assert "2 more chances" in sent_text

    @pytest.mark.asyncio
    async def test_send_boss_fail_message_one_remaining(self, handler, mock_bot):
        """Fail message with 1 remaining chance uses the stern last-chance variant."""
        await handler.send_boss_fail_message(chat_id=1, attempts=2, chapter=1)

        sent_text = mock_bot.send_message.call_args.kwargs["text"]
        assert "last chance" in sent_text.lower()

    @pytest.mark.asyncio
    async def test_send_boss_partial_message_random(self, handler, mock_bot):
        """Partial message is one of the three variants."""
        await handler.send_boss_partial_message(chat_id=1, chapter=1)

        sent_text = mock_bot.send_message.call_args.kwargs["text"]
        assert sent_text  # non-empty

    @pytest.mark.asyncio
    async def test_send_game_over_message(self, handler, mock_bot):
        """Game-over message contains breakup language."""
        await handler.send_game_over_message(chat_id=1, chapter=1)

        sent_text = mock_bot.send_message.call_args.kwargs["text"]
        assert "done" in sent_text.lower() or "goodbye" in sent_text.lower()

    @pytest.mark.asyncio
    async def test_send_game_won_message(self, handler, mock_bot):
        """Victory message contains loving language."""
        await handler.send_game_won_message(chat_id=1, chapter=5)

        sent_text = mock_bot.send_message.call_args.kwargs["text"]
        assert "love" in sent_text.lower() or "the one" in sent_text.lower()


# ---------------------------------------------------------------------------
# BOSS_PASS_MESSAGES constant
# ---------------------------------------------------------------------------

class TestBossPassMessages:
    """Tests for the BOSS_PASS_MESSAGES constant."""

    def test_all_five_chapters_covered(self):
        assert set(BOSS_PASS_MESSAGES.keys()) == {1, 2, 3, 4, 5}

    def test_all_messages_non_empty(self):
        for chapter, msg in BOSS_PASS_MESSAGES.items():
            assert msg, f"Chapter {chapter} pass message is empty"
