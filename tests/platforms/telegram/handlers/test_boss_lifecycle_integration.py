"""Integration tests for multi-phase boss encounter lifecycle.

Tests BossEncounterHandler + BossPhaseManager + BossStateMachine together
with mocked repos/bot to verify the full boss round-trip.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from nikita.engine.chapters.boss import BossPhase, BossPhaseState, BossStateMachine
from nikita.engine.chapters.judgment import BossResult
from nikita.engine.chapters.phase_manager import BossPhaseManager
from nikita.platforms.telegram.handlers.boss_encounter import BossEncounterHandler


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
    repo.advance_chapter = AsyncMock()
    repo.increment_boss_attempts = AsyncMock()
    repo.update_game_status = AsyncMock()
    repo.get = AsyncMock()
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
def real_boss_state_machine():
    """Use the real BossStateMachine (not mocked) for integration testing."""
    return BossStateMachine()


@pytest.fixture
def handler(mock_bot, mock_user_repo, mock_conversation_repo, mock_boss_judgment):
    """Handler with real BossStateMachine for lifecycle tests."""
    return BossEncounterHandler(
        bot=mock_bot,
        user_repository=mock_user_repo,
        conversation_repository=mock_conversation_repo,
        boss_judgment=mock_boss_judgment,
        boss_state_machine=BossStateMachine(),
    )


@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = uuid4()
    user.chapter = 2
    user.conflict_details = None
    user.boss_attempts = 0
    return user


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestBossLifecycleIntegration:
    """Tests for the full boss encounter lifecycle."""

    @pytest.mark.asyncio
    async def test_boss_opening_to_judgment_round_trip(
        self, handler, mock_bot, mock_boss_judgment, mock_user_repo, mock_user
    ):
        """Opening sent -> user responds -> judgment rendered -> outcome delivered -> conversation closed."""
        # 1. Send opening
        mock_prompt = {
            "in_character_opening": "Prove your commitment.",
            "challenge_context": "test context",
            "success_criteria": "show empathy",
        }
        with patch(
            "nikita.engine.chapters.prompts.get_boss_prompt",
            return_value=mock_prompt,
        ), patch("asyncio.sleep", new_callable=AsyncMock):
            await handler.send_boss_opening(chat_id=100, chapter=2)

        # Opening message sent
        assert mock_bot.send_message.call_count == 1
        opening_text = mock_bot.send_message.call_args.kwargs["text"]
        assert "Prove your commitment" in opening_text

        mock_bot.send_message.reset_mock()

        # 2. User responds -> judgment
        mock_boss_judgment.judge_boss_outcome.return_value = MagicMock(
            outcome=BossResult.PASS, reasoning="great answer"
        )

        # Mock user_repo methods for process_pass flow
        advanced_user = MagicMock(chapter=3, boss_attempts=0)
        mock_user_repo.get.return_value = mock_user
        mock_user_repo.advance_chapter.return_value = advanced_user

        with patch(
            "nikita.engine.chapters.prompts.get_boss_prompt",
            return_value=mock_prompt,
        ), patch("asyncio.sleep", new_callable=AsyncMock):
            await handler.handle_single_turn_boss(mock_user, "I understand your feelings", chat_id=100)

        # Pass message sent
        assert mock_bot.send_message.called
        # game_status updated
        mock_user_repo.update_game_status.assert_called_once_with(mock_user.id, "active")

    @pytest.mark.asyncio
    async def test_multi_phase_boss_state_persistence(self):
        """Phase 1 saved to conflict_details -> next message loads it -> phase advances correctly."""
        phase_mgr = BossPhaseManager()

        # Start boss in OPENING phase
        state = phase_mgr.start_boss(chapter=2)
        assert state.phase == BossPhase.OPENING
        assert state.turn_count == 0

        # Persist to conflict_details
        conflict_details = phase_mgr.persist_phase(None, state)
        assert "boss_phase" in conflict_details

        # Load it back
        loaded = phase_mgr.load_phase(conflict_details)
        assert loaded is not None
        assert loaded.phase == BossPhase.OPENING
        assert loaded.chapter == 2

        # Advance to RESOLUTION
        advanced = phase_mgr.advance_phase(
            loaded, "I hear you", "Good. Now tell me what you'd do differently."
        )
        assert advanced.phase == BossPhase.RESOLUTION
        assert advanced.turn_count == 1
        assert len(advanced.conversation_history) == 2

        # Persist again
        conflict_details = phase_mgr.persist_phase(conflict_details, advanced)
        reloaded = phase_mgr.load_phase(conflict_details)
        assert reloaded.phase == BossPhase.RESOLUTION
        assert reloaded.turn_count == 1
        assert len(reloaded.conversation_history) == 2

    @pytest.mark.asyncio
    async def test_boss_pass_advances_chapter(
        self, mock_user_repo, mock_user
    ):
        """Boss pass -> user.chapter incremented -> user.game_status reset to 'active'."""
        sm = BossStateMachine()

        # Mock: user was in chapter 2, advance_chapter returns chapter 3
        mock_user.chapter = 2
        mock_user_repo.get.return_value = mock_user
        advanced_user = MagicMock(chapter=3, boss_attempts=0)
        mock_user_repo.advance_chapter.return_value = advanced_user

        result = await sm.process_pass(
            user_id=mock_user.id,
            user_repository=mock_user_repo,
        )

        assert result["new_chapter"] == 3
        assert result["game_status"] == "active"
        mock_user_repo.advance_chapter.assert_called_once_with(mock_user.id)
        mock_user_repo.update_game_status.assert_called_once_with(mock_user.id, "active")

    @pytest.mark.asyncio
    async def test_boss_fail_increments_attempts_game_over_on_third(
        self, mock_user_repo, mock_user
    ):
        """Boss fail -> boss_attempts incremented -> if 3rd fail -> game_over."""
        sm = BossStateMachine()

        # First fail: attempts=1
        fail_user_1 = MagicMock(boss_attempts=1)
        mock_user_repo.increment_boss_attempts.return_value = fail_user_1
        result1 = await sm.process_fail(user_id=mock_user.id, user_repository=mock_user_repo)
        assert result1["attempts"] == 1
        assert result1["game_over"] is False

        # Second fail: attempts=2
        fail_user_2 = MagicMock(boss_attempts=2)
        mock_user_repo.increment_boss_attempts.return_value = fail_user_2
        result2 = await sm.process_fail(user_id=mock_user.id, user_repository=mock_user_repo)
        assert result2["attempts"] == 2
        assert result2["game_over"] is False

        # Third fail: attempts=3 -> game_over
        fail_user_3 = MagicMock(boss_attempts=3)
        mock_user_repo.increment_boss_attempts.return_value = fail_user_3
        result3 = await sm.process_fail(user_id=mock_user.id, user_repository=mock_user_repo)
        assert result3["attempts"] == 3
        assert result3["game_over"] is True
        mock_user_repo.update_game_status.assert_called_with(mock_user.id, "game_over")

    @pytest.mark.asyncio
    async def test_conflict_details_cleared_after_outcome(self):
        """After outcome -> conflict_details reset -> next boss starts fresh."""
        phase_mgr = BossPhaseManager()

        # Start and advance a boss
        state = phase_mgr.start_boss(chapter=3)
        advanced = phase_mgr.advance_phase(state, "user msg", "nikita msg")
        conflict_details = phase_mgr.persist_phase(None, advanced)

        # Verify boss_phase exists
        loaded = phase_mgr.load_phase(conflict_details)
        assert loaded is not None
        assert loaded.phase == BossPhase.RESOLUTION

        # Clear after outcome
        cleared = phase_mgr.clear_boss_phase(conflict_details)
        assert cleared["boss_phase"] is None

        # Verify next load returns None (fresh start)
        reloaded = phase_mgr.load_phase(cleared)
        assert reloaded is None

        # Starting a new boss from cleared state works
        new_state = phase_mgr.start_boss(chapter=3)
        new_details = phase_mgr.persist_phase(cleared, new_state)
        fresh = phase_mgr.load_phase(new_details)
        assert fresh is not None
        assert fresh.phase == BossPhase.OPENING
        assert fresh.turn_count == 0
