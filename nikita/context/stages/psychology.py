"""Psychology analysis stage for pipeline.

Stage 2.5 in the post-processing pipeline. Analyzes conversation
through psychological lens for relationship dynamics and insights.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.context.stages.base import PipelineStage
from nikita.db.models.conversation import Conversation

if TYPE_CHECKING:
    from nikita.context.pipeline_context import PipelineContext
    from nikita.context.stages.extraction import ExtractionResult
    from nikita.context.relationship_analyzer import (
        PsychologicalInsight,
        RelationshipHealth,
    )


@dataclass
class PsychologyInput:
    """Input for PsychologyStage."""

    conversation: Conversation
    extraction: "ExtractionResult"


@dataclass
class PsychologyResult:
    """Result from psychology analysis."""

    insight: "PsychologicalInsight"
    health: "RelationshipHealth"


class PsychologyStage(PipelineStage[PsychologyInput, PsychologyResult]):
    """Stage 2.5: Analyze conversation psychology.

    Uses RelationshipAnalyzer to:
    1. Analyze conversation dynamics (power balance, vulnerability)
    2. Detect trauma triggers and defense mechanisms
    3. Generate psychological insights for next conversation
    4. Track relationship health indicators
    5. Create psychological thoughts when triggers detected

    Non-critical: Pipeline continues with defaults if this stage fails.
    """

    name = "psychology"
    is_critical = False
    timeout_seconds = 30.0
    max_retries = 2

    def __init__(
        self,
        session: AsyncSession,
        logger: structlog.BoundLogger | None = None,
    ):
        """Initialize PsychologyStage.

        Args:
            session: Database session.
            logger: Optional pre-bound logger.
        """
        super().__init__(session, logger)
        # Lazy imports to avoid circular dependencies
        from nikita.db.repositories.user_repository import UserRepository
        from nikita.db.repositories.thought_repository import NikitaThoughtRepository

        self._user_repo = UserRepository(session)
        self._thought_repo = NikitaThoughtRepository(session)

    async def _run(
        self,
        context: PipelineContext,
        input_data: PsychologyInput,
    ) -> PsychologyResult:
        """Execute psychology analysis.

        Args:
            context: Pipeline context with conversation data.
            input_data: Conversation and extraction data.

        Returns:
            PsychologyResult with insight and health data.
        """
        from nikita.context.relationship_analyzer import (
            get_relationship_analyzer,
            PsychologicalInsight,
            RelationshipHealth,
        )

        conversation = input_data.conversation

        try:
            # Get user for chapter info
            user = await self._user_repo.get(conversation.user_id)
            chapter = user.chapter if user else 1
            relationship_score = float(user.relationship_score) if user else 50.0

            # Initialize analyzer
            analyzer = get_relationship_analyzer()

            # Analyze conversation dynamics
            dynamics = analyzer.analyze_conversation(
                messages=conversation.messages or [],
                user_chapter=chapter,
                relationship_score=relationship_score,
            )

            # Calculate relationship health
            health = analyzer.calculate_relationship_health(
                conversation_dynamics=dynamics,
                existing_health=None,  # Fresh calculation
                chapter=chapter,
            )

            # Calculate hours since last interaction
            hours_since = 0.0
            if conversation.started_at:
                started_at = conversation.started_at
                if started_at.tzinfo is None:
                    started_at = started_at.replace(tzinfo=UTC)
                delta = datetime.now(UTC) - started_at
                hours_since = delta.total_seconds() / 3600

            # Generate psychological insight
            insight = analyzer.generate_psychological_insight(
                conversation_dynamics=dynamics,
                relationship_health=health,
                chapter=chapter,
                hours_since_last=hours_since,
            )

            self._logger.info(
                "psychology_analysis_complete",
                conversation_id=str(conversation.id),
                emotional_state=insight.nikita_emotional_state,
                health_rating=health.health_rating,
                triggers_count=len(dynamics.detected_triggers),
            )

            # Store psychological thoughts if triggers detected
            if dynamics.detected_triggers:
                await self._create_psychological_thoughts(
                    user_id=conversation.user_id,
                    conversation_id=conversation.id,
                    insight=insight,
                    dynamics=dynamics,
                )

            return PsychologyResult(insight=insight, health=health)

        except Exception as e:
            self._logger.warning(
                "psychology_analysis_failed",
                conversation_id=str(conversation.id),
                error=str(e),
                exc_info=True,
            )
            # Return defaults - don't fail the pipeline
            default_insight = PsychologicalInsight(
                triggers_activated=[],
                wounds_touched=[],
                defenses_employed=[],
                nikita_emotional_state="neutral",
                emotional_temperature=0.0,
                suggested_approach="Warm and engaged",
                topics_to_avoid=[],
                topics_to_explore=[],
            )
            default_health = RelationshipHealth()
            return PsychologyResult(insight=default_insight, health=default_health)

    async def _create_psychological_thoughts(
        self,
        user_id: Any,
        conversation_id: Any,
        insight: Any,
        dynamics: Any,
    ) -> None:
        """Create psychological thoughts based on analysis.

        Generates NikitaThoughts that reflect psychological processing
        of the conversation - her fears, defenses, hopes.

        Args:
            user_id: User UUID.
            conversation_id: Source conversation UUID.
            insight: PsychologicalInsight from analysis.
            dynamics: ConversationDynamics from analysis.
        """
        thoughts_data = []

        # If triggers were activated, create worry thought
        if dynamics.detected_triggers:
            trigger_names = ", ".join(dynamics.detected_triggers)
            thoughts_data.append({
                "thought_type": "worry",
                "content": f"Something about that conversation touched something in me... {trigger_names}",
            })

        # If healing opportunity, create anticipation thought
        if getattr(insight, "healing_opportunity", None) and getattr(insight, "healing_context", None):
            thoughts_data.append({
                "thought_type": "anticipation",
                "content": f"Maybe this time could be different... {insight.healing_context}",
            })

        # If emotional temperature is positive, create reflection
        if insight.emotional_temperature > 0.3:
            thoughts_data.append({
                "thought_type": "reflection",
                "content": "That conversation felt good. He's actually listening.",
            })

        # If avoidant state, create desire thought (wanting connection despite fear)
        if insight.nikita_emotional_state == "avoidant":
            thoughts_data.append({
                "thought_type": "desire",
                "content": "I want to let him in, but it's hard. Old patterns die hard.",
            })

        # Create the thoughts
        if thoughts_data:
            from nikita.db.models.context import THOUGHT_TYPES

            valid_thoughts = [
                t for t in thoughts_data
                if t["thought_type"] in THOUGHT_TYPES
            ]
            if valid_thoughts:
                await self._thought_repo.bulk_create_thoughts(
                    user_id=user_id,
                    thoughts_data=valid_thoughts,
                    source_conversation_id=conversation_id,
                )
                self._logger.debug(
                    "psychological_thoughts_created",
                    user_id=str(user_id),
                    count=len(valid_thoughts),
                )
