"""ScoringOrchestrator — extracted scoring + boss-threshold logic (Strangler Fig, Phase 2).

Handles:
- Building ConversationContext from user state
- Calling ScoringService.score_interaction
- Persisting score delta to user and conversation
- Detecting boss_threshold_reached event and triggering the callback
- Persisting conflict_details (Spec 057)

This class is standalone and unit-testable independently of MessageHandler.
"""

import logging
from decimal import Decimal
from typing import Callable, Awaitable, Optional
from uuid import UUID

from nikita.config.enums import EngagementState
from nikita.engine.scoring.models import ConversationContext
from nikita.engine.scoring.service import ScoringService
from nikita.db.repositories.user_repository import UserRepository
from nikita.db.repositories.conversation_repository import ConversationRepository
from nikita.db.repositories.metrics_repository import UserMetricsRepository

logger = logging.getLogger(__name__)


class ScoringOrchestrator:
    """Standalone orchestrator for scoring interactions and detecting boss thresholds.

    Extracted from MessageHandler._score_and_check_boss via Strangler Fig.
    Accepts async callbacks so callers can hook boss-trigger logic without
    coupling to this class's implementation.
    """

    def __init__(
        self,
        user_repository: UserRepository,
        conversation_repository: ConversationRepository,
        scoring_service: Optional[ScoringService] = None,
        metrics_repository: Optional[UserMetricsRepository] = None,
    ) -> None:
        """Initialise ScoringOrchestrator.

        Args:
            user_repository: Repository for user score updates.
            conversation_repository: Repository for conversation delta persistence.
            scoring_service: Scoring service (default created if None).
            metrics_repository: Optional metrics repository for individual metric updates.
        """
        self.user_repository = user_repository
        self.conversation_repo = conversation_repository
        self.scoring_service = scoring_service or ScoringService()
        self.metrics_repo = metrics_repository

    async def score_and_check_boss(
        self,
        user,
        user_message: str,
        nikita_response: str,
        chat_id: int,
        conversation_id: UUID,
        on_boss_threshold: Optional[Callable[[int, int], Awaitable[None]]] = None,
        on_engagement_update: Optional[Callable[[object, int, EngagementState], Awaitable[None]]] = None,
    ) -> None:
        """Score interaction and detect boss-threshold event.

        Mirrors MessageHandler._score_and_check_boss behaviour.

        Args:
            user: User model with metrics and engagement_state.
            user_message: The user's message text.
            nikita_response: Nikita's response text.
            chat_id: Telegram chat ID (for boss notification callback).
            conversation_id: Active conversation UUID.
            on_boss_threshold: Async callback(chat_id, chapter) called when boss threshold
                reached. Called after set_boss_fight_status, before returning.
            on_engagement_update: Async callback(user, chat_id, engagement_state) called
                after scoring to run engagement state machine update.
        """
        try:
            current_metrics = {
                "intimacy": user.metrics.intimacy if user.metrics else Decimal("50"),
                "passion": user.metrics.passion if user.metrics else Decimal("50"),
                "trust": user.metrics.trust if user.metrics else Decimal("50"),
                "secureness": user.metrics.secureness if user.metrics else Decimal("50"),
            }

            engagement_state = EngagementState.CALIBRATING
            if user.engagement_state:
                try:
                    engagement_state = EngagementState(user.engagement_state.state)
                except (ValueError, AttributeError):
                    pass

            context = ConversationContext(
                chapter=user.chapter,
                relationship_score=user.relationship_score,
                recent_messages=[("user", user_message), ("nikita", nikita_response)],
                engagement_state=engagement_state.value,
            )

            # Spec 057: Load conflict_details for temperature scoring
            conflict_details = None
            try:
                from nikita.conflicts import is_conflict_temperature_enabled
                if is_conflict_temperature_enabled():
                    from nikita.conflicts.persistence import load_conflict_details
                    conflict_details = await load_conflict_details(
                        user.id, self.conversation_repo.session
                    )
            except Exception as cd_err:
                logger.warning("[SCORING] Failed to load conflict_details: %s", cd_err)

            logger.info(
                "[SCORING] Scoring interaction for user %s: chapter=%s, score=%s",
                user.id,
                user.chapter,
                user.relationship_score,
            )
            result = await self.scoring_service.score_interaction(
                user_id=user.id,
                user_message=user_message,
                nikita_response=nikita_response,
                context=context,
                current_metrics=current_metrics,
                engagement_state=engagement_state,
                conflict_details=conflict_details,
            )

            logger.info(
                "[SCORING] Result: score %s -> %s (delta: %s)",
                result.score_before,
                result.score_after,
                result.delta,
            )

            # Spec 057: Persist updated conflict_details
            if result.conflict_details is not None:
                try:
                    from nikita.conflicts.persistence import save_conflict_details
                    await save_conflict_details(
                        user.id, result.conflict_details, self.conversation_repo.session
                    )
                except Exception as cd_err:
                    logger.warning("[SCORING] Failed to save conflict_details: %s", cd_err)

            # Persist score delta
            if result.delta != Decimal("0"):
                await self.user_repository.update_score(
                    user_id=user.id,
                    delta=result.delta,
                    event_type="conversation",
                    event_details={
                        "deltas": {
                            "intimacy": str(result.deltas_applied.intimacy),
                            "passion": str(result.deltas_applied.passion),
                            "trust": str(result.deltas_applied.trust),
                            "secureness": str(result.deltas_applied.secureness),
                        },
                        "multiplier": str(result.multiplier_applied),
                    },
                )
                logger.info("[SCORING] Updated user score by %s", result.delta)

                if self.metrics_repo:
                    await self.metrics_repo.update_metrics(
                        user_id=user.id,
                        intimacy_delta=result.deltas_applied.intimacy,
                        passion_delta=result.deltas_applied.passion,
                        trust_delta=result.deltas_applied.trust,
                        secureness_delta=result.deltas_applied.secureness,
                    )
                    logger.info(
                        "[SCORING] Updated user_metrics: I+%s P+%s T+%s S+%s",
                        result.deltas_applied.intimacy,
                        result.deltas_applied.passion,
                        result.deltas_applied.trust,
                        result.deltas_applied.secureness,
                    )

            await self.conversation_repo.update_score_delta(
                conversation_id=conversation_id,
                score_delta=result.delta,
            )
            logger.info(
                "[SCORING] Stored score_delta=%s on conversation %s",
                result.delta,
                conversation_id,
            )

            # Check for boss threshold event
            for event in result.events:
                if event.event_type == "boss_threshold_reached":
                    logger.info(
                        "[BOSS] Boss threshold reached for user %s at chapter %s!",
                        user.id,
                        user.chapter,
                    )
                    # R-7: Close active conversation before entering boss_fight
                    try:
                        await self.conversation_repo.close_conversation(
                            conversation_id=conversation_id,
                            score_delta=result.delta,
                        )
                        logger.info(
                            "[BOSS] Closed conversation %s before boss encounter",
                            conversation_id,
                        )
                    except Exception as close_err:
                        logger.warning(
                            "[BOSS] Failed to close conversation before boss: %s", close_err
                        )

                    await self.user_repository.set_boss_fight_status(user.id)

                    if on_boss_threshold is not None:
                        await on_boss_threshold(chat_id, user.chapter)
                    break

            # Engagement state machine update callback
            if on_engagement_update is not None:
                await on_engagement_update(user, chat_id, engagement_state)

        except Exception as exc:
            logger.error(
                "[SCORING] Failed to score interaction for user %s: %s",
                user.id,
                exc,
                exc_info=True,
            )
