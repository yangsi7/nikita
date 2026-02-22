"""Boss State Machine for chapter progression.

Implements boss encounter detection, triggering, and outcome processing.
Part of spec 004-chapter-boss-system.
Spec 058: Multi-phase boss encounters with PARTIAL outcome.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pydantic import BaseModel, Field

from nikita.config.enums import GameStatus
from nikita.engine.constants import BOSS_ENCOUNTERS, BOSS_THRESHOLDS

if TYPE_CHECKING:
    from nikita.db.repositories.user_repository import UserRepository


# ============================================================================
# Spec 058: Multi-Phase Boss Models
# ============================================================================


class BossPhase(str, Enum):
    """Phase of a multi-phase boss encounter (Spec 058).

    OPENING: Nikita presents the challenge.
    RESOLUTION: Player works toward resolution after initial response.
    """

    OPENING = "opening"
    RESOLUTION = "resolution"


class BossPhaseState(BaseModel):
    """State of an in-progress multi-phase boss encounter (Spec 058).

    Persisted in conflict_details.boss_phase JSONB.

    Attributes:
        phase: Current boss phase (OPENING or RESOLUTION).
        chapter: Chapter the boss encounter is for (1-5).
        started_at: When the boss encounter started.
        turn_count: Number of player responses so far.
        conversation_history: Messages exchanged during the boss encounter.
    """

    phase: BossPhase
    chapter: int
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    turn_count: int = 0
    conversation_history: list[dict[str, str]] = Field(default_factory=list)


class BossStateMachine:
    """Manages boss encounter state transitions.

    The boss system controls chapter advancement:
    - should_trigger_boss: Pure function to check if boss should trigger
    - initiate_boss: Initiates boss encounter, returns full prompt
    - process_outcome: Handles pass/fail/partial, advances chapter or resets
    - process_pass: Called when player passes the boss challenge
    - process_fail: Called when player fails the boss challenge
    - process_partial: Called on PARTIAL (truce) outcome (Spec 058)
    """

    # Valid game statuses that can trigger a boss
    _ACTIVE_STATUS = "active"
    _BLOCKING_STATUSES = frozenset({"boss_fight", "game_over", "won"})

    def should_trigger_boss(
        self,
        relationship_score: Decimal,
        chapter: int,
        game_status: str,
        cool_down_until: datetime | None = None,
    ) -> bool:
        """Check if boss should trigger based on user state.

        Pure function for testability - does not access database.

        Args:
            relationship_score: User's current score (0-100)
            chapter: Current chapter (1-5)
            game_status: Current game status (active, boss_fight, game_over, won)
            cool_down_until: Optional cooldown expiry (Spec 101). If set and in
                the future, boss trigger is suppressed.

        Returns:
            True if score >= threshold AND status is "active" AND not in cooldown
        """
        # Block if not in active state
        if game_status != self._ACTIVE_STATUS:
            return False

        # Block if cooldown is still active (Spec 101 FR-001)
        if cool_down_until is not None and cool_down_until > datetime.now(UTC):
            return False

        # Check if score meets or exceeds threshold for current chapter
        threshold = BOSS_THRESHOLDS.get(chapter)
        if threshold is None:
            return False

        return relationship_score >= threshold

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
        # Capture chapter BEFORE advancement to distinguish Boss 4 pass (ch4→5)
        # from Boss 5 pass (ch5→5, capped). Only the latter means victory.
        pre_advance_user = await user_repository.get(user_id)
        old_chapter = pre_advance_user.chapter if pre_advance_user else 0

        user = await user_repository.advance_chapter(user_id)

        # Won = was already in chapter 5 (final boss completed).
        # advance_chapter() caps at 5, so ch5 boss pass keeps chapter at 5.
        # Boss 4 pass: old_chapter=4, user.chapter=5 → "active" (enter Ch5)
        # Boss 5 pass: old_chapter=5, user.chapter=5 → "won" (game complete)
        new_status = "won" if old_chapter >= 5 else "active"
        await user_repository.update_game_status(user_id, new_status)

        # Spec 070: Push notification for chapter advance
        try:
            from nikita.notifications.push import send_push
            from nikita.engine.constants import CHAPTER_NAMES

            chapter_name = CHAPTER_NAMES.get(user.chapter, f"Chapter {user.chapter}")
            if new_status == "won":
                await send_push(
                    user_id=user_id,
                    title="You won!",
                    body="You've completed all chapters with Nikita",
                    url="/dashboard",
                    tag="game-won",
                )
            else:
                await send_push(
                    user_id=user_id,
                    title="New chapter unlocked",
                    body=f"Welcome to {chapter_name}",
                    url="/engagement",
                    tag="chapter-advance",
                )
        except Exception:
            pass  # Push failures never block game flow

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

    async def process_partial(
        self,
        user_id: UUID,
        user_repository: UserRepository | None = None,
    ) -> dict[str, Any]:
        """Process a PARTIAL boss outcome — truce (Spec 058).

        PARTIAL: does NOT increment boss_attempts, does NOT advance chapter.
        Sets status back to "active" and records cool-down timestamp.

        Args:
            user_id: The user's UUID
            user_repository: UserRepository with active session (required)

        Returns:
            dict with:
                - attempts: int (unchanged boss_attempts)
                - game_status: str ("active")
                - cool_down_until: str (ISO datetime, 24h from now)
        """
        if user_repository is None:
            raise ValueError(
                "user_repository is required - pass it from the caller"
            )

        # Set status back to active (not boss_fight)
        await user_repository.update_game_status(user_id, "active")

        # Get current user for attempts count
        user = await user_repository.get(user_id)
        attempts = user.boss_attempts if user else 0

        # 24h cool-down (Spec 101 FR-001)
        cool_down_until = datetime.now(UTC) + timedelta(hours=24)

        # Persist cooldown timestamp so should_trigger_boss() can suppress re-trigger
        await user_repository.set_cool_down(user_id, cool_down_until)

        return {
            "attempts": attempts,
            "game_status": "active",
            "cool_down_until": cool_down_until.isoformat(),
        }

    async def process_outcome(
        self,
        user_id: UUID,
        passed: bool | None = None,
        user_repository: UserRepository | None = None,
        *,
        outcome: str | None = None,
    ) -> dict[str, Any]:
        """Process the outcome of a boss encounter.

        Supports both legacy (passed: bool) and new (outcome: str) signatures.
        When outcome is provided, dispatches to process_pass/fail/partial.
        When only passed is provided, uses legacy bool dispatch.

        Args:
            user_id: The user's UUID
            passed: Whether user passed (legacy, bool). Used when flag OFF.
            user_repository: UserRepository with active session (required)
            outcome: PASS/FAIL/PARTIAL string (Spec 058). Takes priority over passed.

        Returns:
            dict with outcome details from the dispatched handler.
        """
        from nikita.engine.chapters.judgment import BossResult

        # Spec 058: three-way dispatch when outcome string provided
        if outcome is not None:
            if outcome == BossResult.PASS.value:
                result = await self.process_pass(
                    user_id, user_repository=user_repository
                )
                return {
                    "passed": True,
                    "outcome": "PASS",
                    "new_chapter": result["new_chapter"],
                    "message": "Chapter advanced!",
                }
            elif outcome == BossResult.PARTIAL.value:
                result = await self.process_partial(
                    user_id, user_repository=user_repository
                )
                return {
                    "passed": False,
                    "outcome": "PARTIAL",
                    "attempts": result["attempts"],
                    "game_status": result["game_status"],
                    "cool_down_until": result["cool_down_until"],
                    "message": "A tense truce...",
                }
            else:
                result = await self.process_fail(
                    user_id, user_repository=user_repository
                )
                return {
                    "passed": False,
                    "outcome": "FAIL",
                    "attempts": result["attempts"],
                    "game_over": result["game_over"],
                    "message": "Game over!" if result["game_over"] else "Try again!",
                }

        # Legacy bool dispatch (backward compat, flag OFF)
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
