"""Scoring service for integrated scoring operations (spec 003).

This module provides a high-level service that integrates:
- ScoreAnalyzer: LLM-based conversation analysis
- ScoreCalculator: Score calculation with engagement multipliers
- Score history logging: Audit trail of all score changes

Usage:
    service = ScoringService()
    result = await service.score_interaction(
        user_id=user_id,
        user_message="Hello!",
        nikita_response="Hi there!",
        context=context,
        current_metrics=metrics,
        engagement_state=EngagementState.IN_ZONE,
        session=db_session,  # Optional - for history logging
    )
"""

import logging
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from nikita.config.enums import EngagementState
from nikita.engine.scoring.analyzer import ScoreAnalyzer
from nikita.engine.scoring.calculator import ScoreCalculator, ScoreResult
from nikita.engine.scoring.models import ConversationContext, ResponseAnalysis

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ScoringService:
    """High-level scoring service integrating analysis and calculation.

    Provides a simple interface for:
    - Scoring individual interactions
    - Batch scoring voice transcripts
    - Analysis-only mode (no score update)
    - History logging integration
    """

    def __init__(self):
        """Initialize the scoring service with analyzer and calculator."""
        self.analyzer = ScoreAnalyzer()
        self.calculator = ScoreCalculator()

    async def score_interaction(
        self,
        user_id: UUID,
        user_message: str,
        nikita_response: str,
        context: ConversationContext,
        current_metrics: dict[str, Decimal],
        engagement_state: EngagementState,
        session: "AsyncSession | None" = None,
    ) -> ScoreResult:
        """Score a single user-Nikita interaction.

        Full scoring flow:
        1. Analyze with LLM to get deltas
        2. Apply engagement multiplier
        3. Calculate new scores
        4. Detect threshold events
        5. Log to history (if session provided)

        Args:
            user_id: The user's UUID
            user_message: The user's message
            nikita_response: Nikita's response
            context: Conversation context
            current_metrics: Current metric values
            engagement_state: Current engagement state
            session: Optional DB session for history logging

        Returns:
            ScoreResult with full before/after state and events
        """
        # Step 1: Analyze with LLM
        analysis = await self.analyzer.analyze(
            user_message=user_message,
            nikita_response=nikita_response,
            context=context,
        )

        # Step 2-4: Calculate scores
        result = self.calculator.calculate(
            current_metrics=current_metrics,
            analysis=analysis,
            engagement_state=engagement_state,
            chapter=context.chapter,
        )

        # Step 5: Log to history if session provided
        if session is not None:
            await self._log_history(
                user_id=user_id,
                result=result,
                context=context,
                session=session,
            )

        return result

    async def score_batch(
        self,
        user_id: UUID,
        exchanges: list[tuple[str, str]],
        context: ConversationContext,
        current_metrics: dict[str, Decimal],
        engagement_state: EngagementState,
        session: "AsyncSession | None" = None,
    ) -> ScoreResult:
        """Score multiple exchanges at once (for voice transcripts).

        Args:
            user_id: The user's UUID
            exchanges: List of (user_message, nikita_response) tuples
            context: Conversation context
            current_metrics: Current metric values
            engagement_state: Current engagement state
            session: Optional DB session for history logging

        Returns:
            ScoreResult for the combined exchanges
        """
        # Analyze batch with LLM
        analysis = await self.analyzer.analyze_batch(
            exchanges=exchanges,
            context=context,
        )

        # Calculate scores
        result = self.calculator.calculate(
            current_metrics=current_metrics,
            analysis=analysis,
            engagement_state=engagement_state,
            chapter=context.chapter,
        )

        # Log to history if session provided
        if session is not None:
            await self._log_history(
                user_id=user_id,
                result=result,
                context=context,
                session=session,
                event_type="voice_call",
            )

        return result

    async def analyze_only(
        self,
        user_message: str,
        nikita_response: str,
        context: ConversationContext,
    ) -> ResponseAnalysis:
        """Analyze an interaction without calculating scores.

        Useful for:
        - Preview what score change would be
        - Testing/debugging
        - Analysis without side effects

        Args:
            user_message: The user's message
            nikita_response: Nikita's response
            context: Conversation context

        Returns:
            ResponseAnalysis with deltas and explanation
        """
        return await self.analyzer.analyze(
            user_message=user_message,
            nikita_response=nikita_response,
            context=context,
        )

    async def _log_history(
        self,
        user_id: UUID,
        result: ScoreResult,
        context: ConversationContext,
        session: "AsyncSession",
        event_type: str = "conversation",
    ) -> None:
        """Log score change to history.

        Args:
            user_id: The user's UUID
            result: The ScoreResult to log
            context: Conversation context
            session: DB session
            event_type: Type of event (conversation, voice_call, decay)
        """
        from nikita.db.repositories.score_history_repository import (
            ScoreHistoryRepository,
        )

        repo = ScoreHistoryRepository(session)

        # Build event details
        details = {
            "score_before": str(result.score_before),
            "score_after": str(result.score_after),
            "delta": str(result.delta),
            "multiplier": str(result.multiplier_applied),
            "engagement_state": result.engagement_state.value,
            "deltas": {
                "intimacy": str(result.deltas_applied.intimacy),
                "passion": str(result.deltas_applied.passion),
                "trust": str(result.deltas_applied.trust),
                "secureness": str(result.deltas_applied.secureness),
            },
        }

        # Log events if any
        if result.events:
            details["events"] = [
                {"type": e.event_type, "threshold": str(e.threshold) if e.threshold else None}
                for e in result.events
            ]

        await repo.log_event(
            user_id=user_id,
            score=result.score_after,
            chapter=context.chapter,
            event_type=event_type,
            event_details=details,
        )

        logger.info(
            f"Logged score change for user {user_id}: "
            f"{result.score_before} -> {result.score_after} ({event_type})"
        )
