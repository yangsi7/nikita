"""Voice call scoring for ElevenLabs conversations.

T020: VoiceCallScorer - analyzes voice transcripts and produces aggregate scores
T021: Score application - updates user metrics and logs to history

Implements:
- AC-FR006-001: Call ends → transcript analyzed → single aggregate score
- AC-FR006-002: Good call → positive metric deltas
- AC-FR006-003: Score history logged with source = "voice_call"
"""

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from nikita.engine.scoring.analyzer import ScoreAnalyzer
from nikita.engine.scoring.models import (
    ConversationContext,
    MetricDeltas,
    ResponseAnalysis,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass
class CallScore:
    """Result of scoring a voice call.

    Holds the aggregate deltas for the entire call, plus metadata.
    """

    session_id: str
    deltas: MetricDeltas
    explanation: str = ""
    duration_seconds: int = 0
    behaviors_identified: list[str] = field(default_factory=list)
    confidence: Decimal = Decimal("0.5")


class VoiceCallScorer:
    """Scores voice call transcripts and applies deltas to user metrics.

    Uses the same ScoreAnalyzer as the text agent for consistency,
    but analyzes entire transcripts at once for aggregate scoring.

    Implementation Notes:
    - apply_score() writes to score_history table with event_type="voice_call"
    - This ensures voice calls appear in Portal score graphs (Spec 051)
    - score_history entries include session_id, duration, deltas in event_details
    """

    def __init__(self):
        """Initialize the voice call scorer."""
        self._analyzer = ScoreAnalyzer()

    async def score_call(
        self,
        user_id: UUID,
        session_id: str,
        transcript: list[tuple[str, str]],
        context: ConversationContext,
        duration_seconds: int = 0,
    ) -> CallScore:
        """Score a complete voice call transcript.

        Args:
            user_id: User UUID
            session_id: Voice session ID from ElevenLabs
            transcript: List of (user_message, nikita_response) tuples
            context: Conversation context for scoring
            duration_seconds: Call duration in seconds

        Returns:
            CallScore with aggregate deltas and metadata

        Implements:
            AC-FR006-001: Single aggregate score for entire call
            AC-T020.1: analyze full conversation
            AC-T020.3: considers call duration
            AC-T020.4: uses same LLM analysis as text agent
        """
        # Handle empty transcript
        if not transcript:
            logger.info(f"[VOICE SCORING] Empty transcript for session {session_id}")
            return CallScore(
                session_id=session_id,
                deltas=MetricDeltas(
                    intimacy=Decimal("0"),
                    passion=Decimal("0"),
                    trust=Decimal("0"),
                    secureness=Decimal("0"),
                ),
                explanation="Empty call - no scoring",
                duration_seconds=duration_seconds,
            )

        try:
            # Use batch analysis for entire transcript (AC-T020.1, AC-T020.4)
            analysis = await self._analyzer.analyze_batch(transcript, context)

            return CallScore(
                session_id=session_id,
                deltas=analysis.deltas,
                explanation=analysis.explanation,
                duration_seconds=duration_seconds,
                behaviors_identified=analysis.behaviors_identified,
                confidence=analysis.confidence,
            )

        except Exception as e:
            logger.error(f"[VOICE SCORING] Error scoring call: {e}", exc_info=True)
            return CallScore(
                session_id=session_id,
                deltas=MetricDeltas(
                    intimacy=Decimal("0"),
                    passion=Decimal("0"),
                    trust=Decimal("0"),
                    secureness=Decimal("0"),
                ),
                explanation=f"Scoring error: {type(e).__name__}",
                duration_seconds=duration_seconds,
            )

    async def apply_score(
        self,
        user_id: UUID,
        call_score: CallScore,
    ) -> Decimal:
        """Apply call score to user metrics and log to history.

        Args:
            user_id: User UUID
            call_score: CallScore from score_call()

        Returns:
            New composite relationship score

        Implements:
            AC-T021.1: updates user_metrics
            AC-T021.2: logs to score_history with event_type='voice_call'
            AC-T021.3: includes session_id in event_details
        """
        from nikita.db.database import get_session_maker
        from nikita.db.repositories.metrics_repository import UserMetricsRepository
        from nikita.db.repositories.score_history_repository import ScoreHistoryRepository
        from nikita.db.repositories.user_repository import UserRepository

        session_maker = get_session_maker()
        async with session_maker() as session:
            user_repo = UserRepository(session)
            metrics_repo = UserMetricsRepository(session)
            history_repo = ScoreHistoryRepository(session)

            # Get user for chapter info
            user = await user_repo.get(user_id)
            if user is None:
                logger.error(f"[VOICE SCORING] User {user_id} not found")
                return Decimal("0")

            # Get current score before update
            old_metrics = await metrics_repo.get_by_user_id(user_id)
            if old_metrics is None:
                logger.error(f"[VOICE SCORING] Metrics not found for user {user_id}")
                return Decimal("0")

            old_score = old_metrics.calculate_composite_score()

            # Apply deltas to metrics (AC-T021.1) - uses delta-based update
            updated_metrics = await metrics_repo.update_metrics(
                user_id,
                intimacy_delta=call_score.deltas.intimacy,
                passion_delta=call_score.deltas.passion,
                trust_delta=call_score.deltas.trust,
                secureness_delta=call_score.deltas.secureness,
            )

            new_score = updated_metrics.calculate_composite_score()

            # Log to score_history with voice_call source (AC-T021.2, AC-T021.3)
            await history_repo.log_event(
                user_id=user_id,
                score=new_score,
                chapter=user.chapter,
                event_type="voice_call",  # AC-FR006-003: source = "voice_call"
                event_details={
                    "session_id": call_score.session_id,  # AC-T021.3
                    "duration_seconds": call_score.duration_seconds,
                    "old_score": str(old_score),
                    "deltas": {
                        "intimacy": str(call_score.deltas.intimacy),
                        "passion": str(call_score.deltas.passion),
                        "trust": str(call_score.deltas.trust),
                        "secureness": str(call_score.deltas.secureness),
                    },
                    "explanation": call_score.explanation,
                    "behaviors": call_score.behaviors_identified,
                },
            )

            await session.commit()

            logger.info(
                f"[VOICE SCORING] Applied score for {user_id}: "
                f"{old_score} → {new_score} (session: {call_score.session_id})"
            )

            return new_score
