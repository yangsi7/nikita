"""Scoring service for integrated scoring operations (spec 003).

This module provides a high-level service that integrates:
- ScoreAnalyzer: LLM-based conversation analysis
- ScoreCalculator: Score calculation with engagement multipliers
- Score history logging: Audit trail of all score changes
- Spec 057: Temperature + Gottman updates (behind feature flag)

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
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
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
        conflict_details: dict[str, Any] | None = None,
        v_exchange_count: int = 0,
    ) -> ScoreResult:
        """Score a single user-Nikita interaction.

        Full scoring flow:
        1. Analyze with LLM to get deltas
        2. Apply engagement multiplier
        3. Calculate new scores
        4. Detect threshold events
        5. Log to history (if session provided)
        6. Update temperature + Gottman (Spec 057, behind feature flag)

        Args:
            user_id: The user's UUID
            user_message: The user's message
            nikita_response: Nikita's response
            context: Conversation context
            current_metrics: Current metric values
            engagement_state: Current engagement state
            session: Optional DB session for history logging
            conflict_details: Optional conflict_details JSONB (Spec 057)

        Returns:
            ScoreResult with full before/after state and events
        """
        # Step 1: Analyze with LLM
        analysis = await self.analyzer.analyze(
            user_message=user_message,
            nikita_response=nikita_response,
            context=context,
        )

        # Step 2a (Spec 058): Apply warmth bonus if vulnerability exchange detected
        if (
            "vulnerability_exchange" in analysis.behaviors_identified
            and self._is_multi_phase_boss_enabled()
        ):
            analysis = ResponseAnalysis(
                deltas=self.calculator.apply_warmth_bonus(
                    analysis.deltas, v_exchange_count
                ),
                explanation=analysis.explanation,
                behaviors_identified=analysis.behaviors_identified,
                confidence=analysis.confidence,
                repair_attempt_detected=analysis.repair_attempt_detected,
                repair_quality=analysis.repair_quality,
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

        # Step 6 (Spec 057): Update temperature + Gottman (behind feature flag)
        updated_details = self._update_temperature_and_gottman(
            analysis=analysis,
            result=result,
            conflict_details=conflict_details,
        )
        if updated_details is not None:
            result.conflict_details = updated_details

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

    @staticmethod
    def _is_multi_phase_boss_enabled() -> bool:
        """Check if multi-phase boss feature flag is ON (Spec 058)."""
        try:
            from nikita.engine.chapters import is_multi_phase_boss_enabled
            return is_multi_phase_boss_enabled()
        except Exception:
            return False

    def _update_temperature_and_gottman(
        self,
        analysis: ResponseAnalysis,
        result: ScoreResult,
        conflict_details: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Update temperature and Gottman counters (Spec 057).

        Always runs (feature flag removed — temperature is the sole path).

        Args:
            analysis: LLM analysis result.
            result: Score calculation result.
            conflict_details: Current conflict_details JSONB from DB.

        Returns:
            Updated conflict_details dict, or None on error.
        """
        from nikita.conflicts.gottman import GottmanTracker
        from nikita.conflicts.models import ConflictDetails, HorsemanType, RepairRecord
        from nikita.conflicts.temperature import TemperatureEngine
        from nikita.engine.scoring.models import (
            REPAIR_QUALITY_DELTAS,
            get_horsemen_from_behaviors,
        )

        # Parse current conflict details (or initialize empty)
        details = ConflictDetails.from_jsonb(conflict_details)
        is_in_conflict = details.zone in ("hot", "critical")

        # ── Repair bypass (doom spiral fix) ──────────────────────────
        # When user sends a genuine repair attempt, bypass score-based
        # temperature increase. The LLM scores the *pair* (user apology +
        # Nikita cold response) as negative, creating a positive feedback
        # loop. Repair detection evaluates user intent independently.
        if analysis.repair_attempt_detected and analysis.repair_quality:
            repair_delta = REPAIR_QUALITY_DELTAS.get(analysis.repair_quality, -5.0)

            # Record repair in conflict_details
            repair_record = RepairRecord(
                quality=analysis.repair_quality,
                temp_delta=repair_delta,
            )
            details.repair_attempts.append(repair_record.model_dump(mode="json"))

            # Force positive Gottman counter (repair = positive interaction)
            details = GottmanTracker.update_conflict_details(
                details=details,
                is_positive=True,
                is_in_conflict=is_in_conflict,
            )

            # Apply repair delta directly (skip score-based temp logic)
            details = TemperatureEngine.update_conflict_details(
                details=details,
                temp_delta=repair_delta,
            )

            logger.info(
                f"Repair bypass: quality={analysis.repair_quality}, "
                f"temp_delta={repair_delta}, new_temp={details.temperature}"
            )
            return details.to_jsonb()

        # ── Normal path (no repair detected) ─────────────────────────

        # T8: Update Gottman counters
        is_positive = result.delta > Decimal("0")
        details = GottmanTracker.update_conflict_details(
            details=details,
            is_positive=is_positive,
            is_in_conflict=is_in_conflict,
        )

        # T9: Calculate temperature delta
        total_temp_delta = 0.0

        # T9a: Temperature delta from score change
        score_delta = float(result.delta)
        score_temp_delta = TemperatureEngine.calculate_delta_from_score(score_delta)
        total_temp_delta += score_temp_delta

        # T9b: Temperature delta from Four Horsemen
        horsemen = get_horsemen_from_behaviors(analysis.behaviors_identified)
        for horseman_str in horsemen:
            try:
                horseman = HorsemanType(horseman_str)
                total_temp_delta += TemperatureEngine.calculate_delta_from_horseman(horseman)
            except ValueError:
                pass

        # T9c: Temperature delta from Gottman ratio
        from nikita.conflicts.models import GottmanCounters

        counters = GottmanCounters(
            positive_count=details.positive_count,
            negative_count=details.negative_count,
            session_positive=details.session_positive,
            session_negative=details.session_negative,
        )
        gottman_delta = GottmanTracker.calculate_temperature_delta(
            counters=counters,
            is_in_conflict=is_in_conflict,
        )
        total_temp_delta += gottman_delta

        # Record horsemen in details
        for h in horsemen:
            if h not in details.horsemen_detected:
                details.horsemen_detected.append(h)

        # Apply temperature delta
        details = TemperatureEngine.update_conflict_details(
            details=details,
            temp_delta=total_temp_delta,
        )

        return details.to_jsonb()

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
