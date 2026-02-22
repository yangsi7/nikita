"""BUG-BOSS-2 regression tests: Boss 4 pass vs Boss 5 pass distinction.

Verifies that process_pass() correctly distinguishes:
- Boss 4 pass: old_chapter=4 → advance to Ch5 → game_status='active' (NOT won)
- Boss 5 pass: old_chapter=5 → chapter stays 5 (capped) → game_status='won'
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from nikita.engine.chapters.boss import BossStateMachine


def _make_user_repo(old_chapter: int, new_chapter_after_advance: int) -> AsyncMock:
    """Build a mock UserRepository for boss pass tests.

    Args:
        old_chapter: Chapter BEFORE boss pass (returned by get()).
        new_chapter_after_advance: Chapter AFTER advance_chapter() (capped at 5).

    Returns:
        AsyncMock UserRepository with pre-configured return values.
    """
    repo = AsyncMock()

    # get() returns pre-advance user (used to capture old_chapter)
    pre_user = MagicMock()
    pre_user.chapter = old_chapter
    repo.get.return_value = pre_user

    # advance_chapter() returns post-advance user
    post_user = MagicMock()
    post_user.chapter = new_chapter_after_advance
    post_user.boss_attempts = 0
    repo.advance_chapter.return_value = post_user

    # update_game_status returns the updated user
    updated_user = MagicMock()
    updated_user.chapter = new_chapter_after_advance
    updated_user.boss_attempts = 0
    repo.update_game_status.return_value = updated_user

    return repo


class TestBugBoss2Regression:
    """BUG-BOSS-2: Boss 4 pass must NOT trigger 'won'; only Boss 5 pass wins."""

    @pytest.mark.asyncio
    async def test_boss_4_pass_advances_to_chapter_5_active(self):
        """Boss 4 pass: old_chapter=4 → advance to Ch5 → status='active' (NOT won).

        Regression for BUG-BOSS-2 where Boss 4 pass was setting game_status='won'
        because the code checked `user.chapter >= 5` AFTER advance (both ch4→5 and
        ch5→5 would satisfy this). Fixed by capturing old_chapter BEFORE advance.
        """
        sm = BossStateMachine()
        user_id = uuid4()

        # Boss 4: player was in chapter 4, advance moves them to chapter 5
        repo = _make_user_repo(old_chapter=4, new_chapter_after_advance=5)

        result = await sm.process_pass(user_id, user_repository=repo)

        assert result["new_chapter"] == 5
        assert result["game_status"] == "active", (
            "Boss 4 pass should set status='active' (player enters Ch5), NOT 'won'"
        )
        assert result["boss_attempts"] == 0

        # Verify advance_chapter was called
        repo.advance_chapter.assert_called_once_with(user_id)
        # Verify game status was updated to 'active'
        repo.update_game_status.assert_called_once_with(user_id, "active")

    @pytest.mark.asyncio
    async def test_boss_5_pass_sets_won(self):
        """Boss 5 pass: old_chapter=5 → chapter stays 5 (capped) → status='won'.

        advance_chapter() caps at chapter 5, so chapter stays 5. The distinction
        is captured by reading old_chapter BEFORE the advance call.
        """
        sm = BossStateMachine()
        user_id = uuid4()

        # Boss 5: player was ALREADY in chapter 5, advance is a no-op (capped)
        repo = _make_user_repo(old_chapter=5, new_chapter_after_advance=5)

        result = await sm.process_pass(user_id, user_repository=repo)

        assert result["new_chapter"] == 5
        assert result["game_status"] == "won", (
            "Boss 5 pass should set status='won' (game complete)"
        )
        assert result["boss_attempts"] == 0

        # Verify advance_chapter was called (even though chapter stays 5)
        repo.advance_chapter.assert_called_once_with(user_id)
        # Verify game status was updated to 'won'
        repo.update_game_status.assert_called_once_with(user_id, "won")

    @pytest.mark.asyncio
    async def test_boss_1_pass_advances_to_chapter_2_active(self):
        """Boss 1 pass: old_chapter=1 → advance to Ch2 → status='active'.

        Verifies basic pass flow works for early chapters.
        """
        sm = BossStateMachine()
        user_id = uuid4()

        repo = _make_user_repo(old_chapter=1, new_chapter_after_advance=2)

        result = await sm.process_pass(user_id, user_repository=repo)

        assert result["new_chapter"] == 2
        assert result["game_status"] == "active"

    @pytest.mark.asyncio
    async def test_boss_3_pass_advances_to_chapter_4_active(self):
        """Boss 3 pass: old_chapter=3 → advance to Ch4 → status='active'."""
        sm = BossStateMachine()
        user_id = uuid4()

        repo = _make_user_repo(old_chapter=3, new_chapter_after_advance=4)

        result = await sm.process_pass(user_id, user_repository=repo)

        assert result["new_chapter"] == 4
        assert result["game_status"] == "active"

    @pytest.mark.asyncio
    async def test_process_pass_requires_user_repository(self):
        """process_pass raises ValueError when user_repository is None."""
        sm = BossStateMachine()
        user_id = uuid4()

        with pytest.raises(ValueError, match="user_repository is required"):
            await sm.process_pass(user_id, user_repository=None)

    @pytest.mark.asyncio
    async def test_process_outcome_boss_4_pass_active(self):
        """process_outcome with PASS outcome for Boss 4 returns 'active' status.

        Tests the full 3-way dispatch path (outcome="PASS").
        """
        sm = BossStateMachine()
        user_id = uuid4()

        repo = _make_user_repo(old_chapter=4, new_chapter_after_advance=5)

        result = await sm.process_outcome(
            user_id,
            user_repository=repo,
            outcome="PASS",
        )

        assert result["passed"] is True
        assert result["outcome"] == "PASS"
        assert result["new_chapter"] == 5

    @pytest.mark.asyncio
    async def test_process_outcome_boss_5_pass_won(self):
        """process_outcome with PASS outcome for Boss 5 triggers 'won' state.

        Tests the full 3-way dispatch path (outcome="PASS") for final chapter.
        """
        sm = BossStateMachine()
        user_id = uuid4()

        repo = _make_user_repo(old_chapter=5, new_chapter_after_advance=5)

        result = await sm.process_outcome(
            user_id,
            user_repository=repo,
            outcome="PASS",
        )

        assert result["passed"] is True
        assert result["outcome"] == "PASS"
        assert result["new_chapter"] == 5
        # update_game_status should have been called with 'won'
        repo.update_game_status.assert_called_once_with(user_id, "won")
