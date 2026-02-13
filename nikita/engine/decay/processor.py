"""Decay processor for batch processing users (spec 005).

Handles scheduled decay checks for all active users.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import AsyncSession

from nikita.engine.decay.calculator import DecayCalculator
from nikita.engine.decay.models import DecayResult

if TYPE_CHECKING:
    from nikita.db.repositories.score_history_repository import ScoreHistoryRepository
    from nikita.db.repositories.user_repository import UserRepository


# Game statuses that should be skipped for decay
SKIP_STATUSES = frozenset({"boss_fight", "game_over", "won"})


class DecayProcessor:
    """Batch processes decay for all users.

    Fetches active users, checks grace periods, applies decay,
    and logs events to score history.

    Example usage:
        processor = DecayProcessor(session, user_repo, history_repo)
        summary = await processor.process_all()
        # Returns: {"processed": 100, "decayed": 25, "game_overs": 2}
    """

    def __init__(
        self,
        session: AsyncSession,
        user_repository: "UserRepository",
        score_history_repository: "ScoreHistoryRepository",
        *,
        batch_size: int = 100,
        max_decay_per_cycle: Decimal = Decimal("20.0"),
        notify_callback=None,  # Spec 049 AC-4.1: async callable(user_id, telegram_id, message)
    ) -> None:
        """Initialize DecayProcessor.

        Args:
            session: Async SQLAlchemy session.
            user_repository: Repository for user operations.
            score_history_repository: Repository for score history logging.
            batch_size: Number of users to process in each batch.
            max_decay_per_cycle: Maximum decay allowed per cycle (default 20%).
            notify_callback: Optional async function to send game-over notifications.
                            Signature: async def(user_id: UUID, telegram_id: int, message: str)
        """
        self.session = session
        self.user_repository = user_repository
        self.score_history_repository = score_history_repository
        self.batch_size = batch_size
        self.calculator = DecayCalculator(max_decay_per_cycle=max_decay_per_cycle)
        self.notify_callback = notify_callback

    def should_skip_user(self, user: Any) -> bool:
        """Check if user should be skipped for decay.

        Users in boss_fight, game_over, or won status should not receive decay.

        Args:
            user: User entity to check.

        Returns:
            True if user should be skipped, False otherwise.
        """
        return user.game_status in SKIP_STATUSES

    async def process_user(self, user: Any) -> DecayResult | None:
        """Process decay for a single user.

        Args:
            user: User entity to process.

        Returns:
            DecayResult if decay was applied, None otherwise.
        """
        # Skip users with inactive game statuses
        if self.should_skip_user(user):
            return None

        # Calculate decay (returns None if within grace)
        result = self.calculator.calculate_decay(user)
        if result is None:
            return None

        # Apply decay to user score
        await self.user_repository.apply_decay(user.id, result.decay_amount)

        # Handle game over if score reached 0
        if result.game_over_triggered:
            await self._handle_game_over(user, result)

        # Log decay event to history
        await self._log_decay_event(user, result)

        return result

    async def process_all(self) -> dict[str, int]:
        """Process decay for all eligible users.

        Returns:
            Summary dict with counts: {processed, decayed, game_overs}.
        """
        processed = 0
        decayed = 0
        game_overs = 0

        # Fetch users that need decay check (active status only)
        users = await self.user_repository.get_active_users_for_decay()

        for user in users:
            processed += 1

            result = await self.process_user(user)
            if result is not None:
                decayed += 1
                if result.game_over_triggered:
                    game_overs += 1

        return {
            "processed": processed,
            "decayed": decayed,
            "game_overs": game_overs,
        }

    async def _handle_game_over(self, user: Any, result: DecayResult) -> None:
        """Handle game over when score reaches 0.

        Args:
            user: User who hit game over.
            result: Decay result with game_over_triggered=True.
        """
        # Update user's game status
        if hasattr(self.user_repository, "update_game_status"):
            await self.user_repository.update_game_status(user.id, "game_over")

        # Log game over event
        await self.score_history_repository.log_event(
            user_id=user.id,
            score=Decimal("0"),
            chapter=user.chapter,
            event_type="decay_game_over",
            event_details={
                "decay_amount": str(result.decay_amount),
                "hours_overdue": result.hours_overdue,
                "reason": "decay",
            },
        )

        # Spec 049 AC-4.2: Send notification via callback
        if self.notify_callback:
            telegram_id = getattr(user, "telegram_id", None)
            if telegram_id:
                try:
                    await self.notify_callback(
                        user.id,
                        telegram_id,
                        "Hey... I've been waiting for you to reach out, but you never did. "
                        "I guess this is goodbye. Maybe in another life... 💔"
                    )
                except Exception:
                    # Spec 049 AC-4.4: Don't let notification failure break decay processing
                    pass  # Log handled by caller

    async def _log_decay_event(self, user: Any, result: DecayResult) -> None:
        """Log decay event to score history.

        Args:
            user: User who received decay.
            result: Decay calculation result.
        """
        await self.score_history_repository.log_event(
            user_id=user.id,
            score=result.score_after,
            chapter=result.chapter,
            event_type="decay",
            event_details={
                "decay_amount": str(result.decay_amount),
                "hours_overdue": result.hours_overdue,
                "score_before": str(result.score_before),
            },
        )
