"""Boss State Machine for chapter progression.

Implements boss encounter detection, triggering, and outcome processing.
Part of spec 004-chapter-boss-system.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

from nikita.config.enums import GameStatus
from nikita.engine.constants import BOSS_ENCOUNTERS, BOSS_THRESHOLDS

if TYPE_CHECKING:
    from nikita.db.repositories.user_repository import UserRepository


class BossStateMachine:
    """Manages boss encounter state transitions.

    The boss system controls chapter advancement:
    - should_trigger_boss: Pure function to check if boss should trigger
    - check_threshold: Async wrapper that fetches user data
    - trigger_boss: Initiates boss encounter, changes game_status
    - process_outcome: Handles pass/fail, advances chapter or resets

    Flow:
        Normal play → check_threshold() → True → trigger_boss()
        → boss_fight state → process_outcome(passed=True/False)
        → advance chapter OR retry
    """

    # Valid game statuses that can trigger a boss
    _ACTIVE_STATUS = "active"
    _BLOCKING_STATUSES = frozenset({"boss_fight", "game_over", "won"})

    def should_trigger_boss(
        self,
        relationship_score: Decimal,
        chapter: int,
        game_status: str,
    ) -> bool:
        """Check if boss should trigger based on user state.

        Pure function for testability - does not access database.

        Args:
            relationship_score: User's current score (0-100)
            chapter: Current chapter (1-5)
            game_status: Current game status (active, boss_fight, game_over, won)

        Returns:
            True if score >= threshold AND status is "active"
        """
        # Block if not in active state
        if game_status != self._ACTIVE_STATUS:
            return False

        # Check if score meets or exceeds threshold for current chapter
        threshold = BOSS_THRESHOLDS.get(chapter)
        if threshold is None:
            return False

        return relationship_score >= threshold

    async def check_threshold(self, user_id: UUID) -> bool:
        """Check if user's score has reached boss threshold for current chapter.

        Async method that fetches user data and delegates to should_trigger_boss.

        Args:
            user_id: The user's UUID

        Returns:
            True if score >= threshold and not already in boss_fight
        """
        # TODO: In integration (T4), inject UserRepository and fetch user
        # For now, returns False as stub
        return False

    async def initiate_boss(
        self,
        user_id: UUID,
        chapter: int,
    ) -> dict[str, Any]:
        """Initiate boss encounter and return challenge prompt.

        This is the main boss initiation method (T4).
        Returns the full prompt with challenge context, success criteria,
        and in-character opening for the specified chapter.

        Args:
            user_id: The user's UUID
            chapter: Current chapter (1-5) for boss prompt selection

        Returns:
            dict with full boss prompt:
                - chapter: int (1-5)
                - challenge_context: str (situation description)
                - success_criteria: str (what player must demonstrate)
                - in_character_opening: str (Nikita's opening line)
        """
        from nikita.engine.chapters.prompts import get_boss_prompt

        prompt = get_boss_prompt(chapter)
        return {
            "chapter": chapter,
            "challenge_context": prompt["challenge_context"],
            "success_criteria": prompt["success_criteria"],
            "in_character_opening": prompt["in_character_opening"],
        }

    async def trigger_boss(self, user_id: UUID) -> dict[str, Any]:
        """Legacy method - initiate boss encounter for the user.

        DEPRECATED: Use initiate_boss() instead for full prompt.
        Kept for backwards compatibility.

        Args:
            user_id: The user's UUID

        Returns:
            dict with encounter details:
                - chapter: int (1-5)
                - name: str (boss name)
                - trigger: str (opening line)
                - challenge: str (what user must demonstrate)
        """
        # TODO: In integration, fetch user chapter from DB
        chapter = 1  # Default for now
        return {
            "chapter": chapter,
            "name": BOSS_ENCOUNTERS[chapter]["name"],
            "trigger": BOSS_ENCOUNTERS[chapter]["trigger"],
            "challenge": BOSS_ENCOUNTERS[chapter]["challenge"],
        }

    async def process_pass(
        self,
        user_id: UUID,
        user_repository: UserRepository | None = None,
    ) -> dict[str, Any]:
        """Process a successful boss encounter (T7).

        Called when the user passes the boss challenge.
        Advances the chapter, resets boss_attempts, sets status to 'active' or 'won'.

        Args:
            user_id: The user's UUID
            user_repository: UserRepository with active session (required)

        Returns:
            dict with:
                - new_chapter: int (the new chapter after advancement)
                - game_status: str ('active' or 'won' for chapter 5)
                - boss_attempts: int (reset to 0)
        """
        if user_repository is None:
            raise ValueError(
                "user_repository is required - pass it from the caller"
            )
        user = await user_repository.advance_chapter(user_id)

        # Set game_status: 'won' if reached chapter 5, else 'active'
        new_status = "won" if user.chapter >= 5 else "active"
        await user_repository.update_game_status(user_id, new_status)

        return {
            "new_chapter": user.chapter,
            "game_status": new_status,
            "boss_attempts": user.boss_attempts,
        }

    async def process_fail(
        self,
        user_id: UUID,
        user_repository: UserRepository | None = None,
    ) -> dict[str, Any]:
        """Process a failed boss encounter (T8).

        Called when the user fails the boss challenge.
        Increments boss_attempts, checks for game over (3 strikes).

        Args:
            user_id: The user's UUID
            user_repository: UserRepository with active session (required)

        Returns:
            dict with:
                - attempts: int (current boss_attempts)
                - game_over: bool (True if 3 attempts reached)
                - game_status: str ('boss_fight' or 'game_over')
        """
        if user_repository is None:
            raise ValueError(
                "user_repository is required - pass it from the caller"
            )
        user = await user_repository.increment_boss_attempts(user_id)

        game_over = user.boss_attempts >= 3

        # Update game_status in DB if game over
        if game_over:
            await user_repository.update_game_status(user_id, "game_over")

        return {
            "attempts": user.boss_attempts,
            "game_over": game_over,
            "game_status": "game_over" if game_over else "boss_fight",
        }

    async def process_outcome(
        self,
        user_id: UUID,
        passed: bool,
        user_repository: UserRepository | None = None,
    ) -> dict[str, Any]:
        """Process the outcome of a boss encounter.

        Delegates to process_pass or process_fail based on outcome.

        Args:
            user_id: The user's UUID
            passed: Whether user passed the boss challenge
            user_repository: UserRepository with active session (required)

        Returns:
            dict with outcome details from process_pass or process_fail
        """
        if passed:
            result = await self.process_pass(
                user_id, user_repository=user_repository
            )
            return {
                "passed": True,
                "new_chapter": result["new_chapter"],
                "message": "Chapter advanced!",
            }
        else:
            result = await self.process_fail(
                user_id, user_repository=user_repository
            )
            return {
                "passed": False,
                "attempts": result["attempts"],
                "game_over": result["game_over"],
                "message": "Game over!" if result["game_over"] else "Try again!",
            }
