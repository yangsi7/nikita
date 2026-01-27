"""Narrative arcs stage for pipeline.

Stage 2.6 in the post-processing pipeline. Manages ongoing
narrative arcs for story-like game progression.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.context.stages.base import PipelineStage
from nikita.db.models.conversation import Conversation

if TYPE_CHECKING:
    from nikita.context.pipeline_context import PipelineContext


@dataclass
class NarrativeArcsInput:
    """Input for NarrativeArcsStage."""

    user: Any  # User model
    conversation: Conversation
    vulnerability_level: int
    days_since_last_arc: int


@dataclass
class NarrativeArcsResult:
    """Result from narrative arcs update."""

    arcs_updated: int = 0
    created: str | None = None
    completed: list[str] = field(default_factory=list)
    advanced: list[str] = field(default_factory=list)
    error: str | None = None


class NarrativeArcsStage(PipelineStage[NarrativeArcsInput, NarrativeArcsResult]):
    """Stage 2.6: Update narrative arcs.

    Manages ongoing narrative arcs:
    1. Check if new arc should start (max 2 active arcs)
    2. Increment conversation count on active arcs
    3. Advance arc stages when thresholds reached
    4. Complete arcs that reach max_conversations

    Non-critical: Pipeline continues with defaults if this stage fails.
    """

    name = "narrative_arcs"
    is_critical = False
    timeout_seconds = 20.0
    max_retries = 2

    def __init__(
        self,
        session: AsyncSession,
        logger: structlog.BoundLogger | None = None,
    ):
        """Initialize NarrativeArcsStage.

        Args:
            session: Database session.
            logger: Optional pre-bound logger.
        """
        super().__init__(session, logger)

    async def _run(
        self,
        context: PipelineContext,
        input_data: NarrativeArcsInput,
    ) -> NarrativeArcsResult:
        """Execute narrative arc updates.

        Args:
            context: Pipeline context with conversation data.
            input_data: User, conversation, and arc parameters.

        Returns:
            NarrativeArcsResult with update information.
        """
        from nikita.db.repositories.narrative_arc_repository import (
            NarrativeArcRepository,
        )
        from nikita.life_simulation.arcs import ArcCategory, get_arc_system

        result = NarrativeArcsResult()
        user = input_data.user
        vulnerability_level = input_data.vulnerability_level
        days_since_last_arc = input_data.days_since_last_arc

        try:
            arc_repo = NarrativeArcRepository(self._session)
            arc_system = get_arc_system()

            # Get active arcs
            active_arcs = await arc_repo.get_active_arcs(user.id)
            active_categories = [
                ArcCategory(arc.category) if isinstance(arc.category, str)
                else arc.category
                for arc in active_arcs
            ]

            # Check if we should start a new arc (max 2 active)
            if len(active_arcs) < 2 and arc_system.should_start_new_arc(
                active_arcs=active_arcs,
                vulnerability_level=vulnerability_level,
                chapter=user.chapter,
                days_since_last_arc=days_since_last_arc,
            ):
                # Select a template
                template = arc_system.select_arc_template(
                    vulnerability_level=vulnerability_level,
                    active_categories=active_categories,
                )

                # Check if we should start this category
                if template and self._should_start_arc(
                    category=template.category,
                    active_categories=active_categories,
                    chance=0.3,
                ):
                    # Create the arc
                    await arc_repo.create_arc(
                        user_id=user.id,
                        template_name=template.name,
                        category=template.category.value,
                        involved_characters=template.involved_characters,
                        max_conversations=template.duration_conversations[1],
                    )
                    result.created = template.name
                    result.arcs_updated += 1
                    self._logger.info(
                        "narrative_arc_created",
                        user_id=str(user.id),
                        arc_name=template.name,
                    )

            # Increment conversation count on active arcs
            for arc in active_arcs:
                await arc_repo.increment_conversation_count(arc.id)
                result.arcs_updated += 1

                # Check if arc should advance to next stage
                if arc.conversations_in_arc >= arc.max_conversations // 2:
                    if arc.current_stage in ("setup", "rising"):
                        await arc_repo.advance_arc(arc.id)
                        result.advanced.append(arc.template_name)
                        self._logger.info(
                            "narrative_arc_advanced",
                            user_id=str(user.id),
                            arc_name=arc.template_name,
                        )

                # Check if arc should complete
                if arc.conversations_in_arc >= arc.max_conversations:
                    await arc_repo.resolve_arc(
                        arc_id=arc.id,
                        resolution="completed",
                    )
                    result.completed.append(arc.template_name)
                    self._logger.info(
                        "narrative_arc_completed",
                        user_id=str(user.id),
                        arc_name=arc.template_name,
                    )

            return result

        except Exception as e:
            self._logger.warning(
                "narrative_arc_update_failed",
                user_id=str(user.id) if user else "unknown",
                error=str(e),
                exc_info=True,
            )
            return NarrativeArcsResult(arcs_updated=0, error=str(e))

    def _should_start_arc(
        self,
        category: Any,
        active_categories: list[Any],
        chance: float = 0.3,
    ) -> bool:
        """Determine if a new arc should start.

        Rules:
        1. Cannot start arc in same category as active arc
        2. Random chance to start (default 30%)

        Args:
            category: The ArcCategory to potentially start.
            active_categories: List of currently active arc categories.
            chance: Probability of starting (0.0-1.0).

        Returns:
            True if arc should start.
        """
        # Cannot have two arcs in same category
        if category in active_categories:
            return False

        # Random chance
        return random.random() < chance
