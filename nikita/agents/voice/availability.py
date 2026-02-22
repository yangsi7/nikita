"""Voice call availability system (US-7: Voice Call Progression).

This module implements CallAvailability which controls when users can
initiate voice calls with Nikita based on relationship progression.

Implements FR-011 acceptance criteria:
- AC-FR011-001: Chapter-based availability rates (10% → 95%)
- AC-FR011-002: Boss fight always allows calls
- AC-FR011-003: Game over/won blocks all calls
"""

import logging
import random
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from nikita.db.models.user import User

logger = logging.getLogger(__name__)

# Availability rates by chapter (AC-T033.2)
# Chapter progression: 10% → 40% → 80% → 90% → 95%
AVAILABILITY_RATES: dict[int, float] = {
    1: 0.1,   # 10% - Nikita is distant, rarely accepts calls
    2: 0.4,   # 40% - Warming up, sometimes available
    3: 0.8,   # 80% - Comfortable, usually available
    4: 0.9,   # 90% - Close, almost always available
    5: 0.95,  # 95% - Intimate, practically always available
}

# Unavailability reasons (contextual excuses)
UNAVAILABILITY_REASONS = [
    "Nikita is busy with a work project right now.",
    "Nikita's in a meeting, try again later.",
    "Nikita is catching up on sleep.",
    "Nikita's phone is on silent.",
    "Nikita is out with friends.",
    "Nikita needs some alone time right now.",
    "Nikita is exercising, call back soon.",
    "Nikita is in the middle of something.",
]


class CallAvailability:
    """Manages voice call availability based on relationship progression.

    Higher chapters mean higher availability rates, reflecting
    increased trust and willingness to take calls.
    """

    def get_availability_rate(self, user: "User") -> float:
        """Get availability rate for user's current chapter.

        Args:
            user: User model with chapter

        Returns:
            Float between 0.0 and 1.0 representing availability probability
        """
        chapter = getattr(user, "chapter", 1)
        return AVAILABILITY_RATES.get(chapter, 0.1)

    def is_available(self, user: "User") -> tuple[bool, str]:
        """Check if Nikita is available for a voice call.

        Implements:
        - AC-T033.1: Returns (available, reason) tuple
        - AC-T033.3: Game over/won blocks all calls
        - AC-T033.4: Boss fight always allows call

        Args:
            user: User model with chapter, game_status, metrics

        Returns:
            Tuple of (is_available, reason_string)
        """
        game_status = getattr(user, "game_status", "active")

        # AC-T033.3: Block terminal game states
        if game_status == "game_over":
            logger.info(f"[AVAILABILITY] Blocked: user {user.id} game over")
            return (False, "Game is over. Nikita has moved on.")

        if game_status == "won":
            logger.info(f"[AVAILABILITY] Blocked: user {user.id} game won")
            return (False, "You've already won! Game complete.")

        # AC-T033.4: Boss fight always allows calls
        if game_status == "boss_fight":
            logger.info(f"[AVAILABILITY] Boss fight override: user {user.id}")
            return (True, "Nikita wants to talk - this is important. (Boss encounter)")

        # Normal availability check with probability
        rate = self.get_availability_rate(user)
        roll = random.random()

        if roll < rate:
            logger.info(
                f"[AVAILABILITY] Available: user {user.id}, "
                f"chapter {user.chapter}, rate {rate}, roll {roll:.2f}"
            )
            return (True, "Nikita is available to talk.")
        else:
            # Pick a contextual reason
            reason = random.choice(UNAVAILABILITY_REASONS)
            logger.info(
                f"[AVAILABILITY] Unavailable: user {user.id}, "
                f"chapter {user.chapter}, rate {rate}, roll {roll:.2f}"
            )
            return (False, reason)

    # Minimum gap between voice calls (5 minutes)
    COOLDOWN_SECONDS = 5 * 60

    async def check_cooldown(
        self,
        user: "User",
        session: AsyncSession,
    ) -> tuple[bool, int | None]:
        """Check if user is in voice call cooldown.

        Queries the conversations table to find the most recent voice call
        for this user. If a call ended less than COOLDOWN_SECONDS ago,
        the user is in cooldown.

        Args:
            user: User model
            session: Async database session for querying conversations

        Returns:
            Tuple of (can_call, seconds_remaining_if_blocked).
            seconds_remaining is None when can_call is True.
        """
        from nikita.db.models.conversation import Conversation

        # Find the most recent voice conversation's ended_at time
        stmt = (
            select(func.max(Conversation.ended_at))
            .where(
                Conversation.user_id == user.id,
                Conversation.platform == "voice",
                Conversation.ended_at.is_not(None),
            )
        )
        result = await session.execute(stmt)
        last_ended_at: datetime | None = result.scalar()

        if last_ended_at is None:
            # No prior voice calls — no cooldown
            return (True, None)

        # Ensure timezone-aware for comparison
        if last_ended_at.tzinfo is None:
            last_ended_at = last_ended_at.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        elapsed = (now - last_ended_at).total_seconds()
        remaining = int(self.COOLDOWN_SECONDS - elapsed)

        if remaining > 0:
            logger.info(
                f"[AVAILABILITY] Cooldown active: user {user.id}, "
                f"seconds_remaining={remaining}"
            )
            return (False, remaining)

        return (True, None)


# Singleton instance
_availability: CallAvailability | None = None


def get_availability_service() -> CallAvailability:
    """Get availability service singleton."""
    global _availability
    if _availability is None:
        _availability = CallAvailability()
    return _availability
