"""Pipeline orchestrator for the unified pipeline (Spec 042 T2.2).

Runs 9 stages sequentially, handles critical vs non-critical failures,
logs per-stage timings, and records job execution in the database.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import logging

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from nikita.pipeline.stages.base import StageResult
from nikita.pipeline.models import PipelineContext, PipelineResult

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """Sequential stage runner for the unified pipeline.

    Runs 9 stages in order. Critical stage failure stops the pipeline;
    non-critical stage failure logs and continues.

    Usage:
        orchestrator = PipelineOrchestrator(session)
        result = await orchestrator.process(conversation_id, user_id, platform)
    """

    # (name, stage_class_path, is_critical)
    # Stage classes are imported lazily to avoid circular imports
    STAGE_DEFINITIONS: list[tuple[str, str, bool]] = [
        ("extraction", "nikita.pipeline.stages.extraction.ExtractionStage", True),
        ("memory_update", "nikita.pipeline.stages.memory_update.MemoryUpdateStage", True),
        ("life_sim", "nikita.pipeline.stages.life_sim.LifeSimStage", False),
        ("emotional", "nikita.pipeline.stages.emotional.EmotionalStage", False),
        ("game_state", "nikita.pipeline.stages.game_state.GameStateStage", False),
        ("conflict", "nikita.pipeline.stages.conflict.ConflictStage", False),
        ("touchpoint", "nikita.pipeline.stages.touchpoint.TouchpointStage", False),
        ("summary", "nikita.pipeline.stages.summary.SummaryStage", False),
        ("prompt_builder", "nikita.pipeline.stages.prompt_builder.PromptBuilderStage", False),
    ]

    def __init__(
        self,
        session: AsyncSession,
        stages: list[tuple[str, Any, bool]] | None = None,
    ) -> None:
        """Initialize orchestrator.

        Args:
            session: Database session for pipeline execution.
            stages: Optional override for stage list (for testing).
                    Each tuple is (name, stage_instance, is_critical).
        """
        self._session = session
        self._stages = stages
        self._logger = logger

    def _get_stages(self) -> list[tuple[str, Any, bool]]:
        """Get stage instances, using injected stages or lazy-loading defaults."""
        if self._stages is not None:
            return self._stages

        import importlib

        instances = []
        for name, class_path, critical in self.STAGE_DEFINITIONS:
            try:
                module_path, class_name = class_path.rsplit(".", 1)
                module = importlib.import_module(module_path)
                cls = getattr(module, class_name)
                instances.append((name, cls(session=self._session), critical))
            except (ImportError, AttributeError) as e:
                self._logger.warning(
                    "stage_import_failed stage=%s: %s", name, e,
                )
                continue
        return instances

    async def _load_context(self, ctx: PipelineContext) -> None:
        """Load conversation and user state into pipeline context.

        Fetches the conversation and user (with relationships) from DB,
        populating ctx with all the state downstream stages need.
        """
        from nikita.db.repositories.conversation_repository import ConversationRepository
        from nikita.db.repositories.user_repository import UserRepository

        # Load conversation
        conv_repo = ConversationRepository(self._session)
        conversation = await conv_repo.get(ctx.conversation_id)
        if conversation is None:
            raise ValueError(
                f"Conversation {ctx.conversation_id} not found"
            )
        ctx.conversation = conversation

        # Load user with eager-loaded metrics, engagement_state, vice_preferences
        user_repo = UserRepository(self._session)
        user = await user_repo.get(ctx.user_id)
        if user is None:
            raise ValueError(f"User {ctx.user_id} not found")
        ctx.user = user

        # Populate user state fields used by downstream stages
        ctx.chapter = user.chapter
        ctx.game_status = user.game_status
        ctx.relationship_score = user.relationship_score

        if user.metrics:
            ctx.metrics = {
                "intimacy": user.metrics.intimacy or Decimal("50"),
                "passion": user.metrics.passion or Decimal("50"),
                "trust": user.metrics.trust or Decimal("50"),
                "secureness": user.metrics.secureness or Decimal("50"),
            }

        if user.engagement_state:
            ctx.engagement_state = user.engagement_state.current_state or "calibrating"

        if user.vice_preferences:
            ctx.vices = [vp.category for vp in user.vice_preferences[:5]]

        self._logger.info(
            "context_loaded conversation=%s user=%s chapter=%d score=%s vices=%d",
            ctx.conversation_id, ctx.user_id, ctx.chapter,
            ctx.relationship_score, len(ctx.vices),
        )

    async def process(
        self,
        conversation_id: UUID,
        user_id: UUID,
        platform: str = "text",
    ) -> PipelineResult:
        """Run the full pipeline for a conversation.

        Args:
            conversation_id: The conversation to process.
            user_id: Owner of the conversation.
            platform: "text" or "voice".

        Returns:
            PipelineResult with success/failure status and full context.
        """
        ctx = PipelineContext(
            conversation_id=conversation_id,
            user_id=user_id,
            started_at=datetime.now(timezone.utc),
            platform=platform,
        )

        self._logger.info(
            "pipeline_started conversation=%s user=%s platform=%s",
            conversation_id, user_id, platform,
        )

        # Load conversation + user state into context before running stages
        try:
            await self._load_context(ctx)
        except Exception as e:
            self._logger.error(
                "pipeline_context_load_failed conversation=%s: %s",
                conversation_id, e,
            )
            return PipelineResult.failed(ctx, "context_load", str(e))

        stages = self._get_stages()
        pipeline_start = time.perf_counter()

        for name, stage, critical in stages:
            stage_start = time.perf_counter()

            try:
                # SAVEPOINT isolation: each stage gets a nested transaction.
                # If a stage fails, its DB changes are rolled back without
                # poisoning the session for subsequent stages.
                async with self._session.begin_nested():
                    result: StageResult = await stage.execute(ctx)
            except Exception as e:
                duration_ms = (time.perf_counter() - stage_start) * 1000
                ctx.record_stage_timing(name, duration_ms)
                error_msg = f"Unexpected error in {name}: {type(e).__name__}: {e}"

                self._logger.error(
                    "stage_unexpected_error stage=%s critical=%s: %s",
                    name, critical, e,
                )

                if critical:
                    return PipelineResult.failed(ctx, name, error_msg)

                ctx.record_stage_error(name, error_msg)
                continue

            duration_ms = (time.perf_counter() - stage_start) * 1000
            ctx.record_stage_timing(name, duration_ms)

            if not result.success:
                self._logger.warning(
                    "stage_failed stage=%s critical=%s duration_ms=%.1f: %s",
                    name, critical, duration_ms, result.error,
                )

                if critical:
                    return PipelineResult.failed(
                        ctx, name, result.error or "Unknown error"
                    )

                ctx.record_stage_error(name, result.error or "Unknown error")
            else:
                self._logger.info(
                    "stage_completed stage=%s duration_ms=%.1f",
                    name, duration_ms,
                )

        total_ms = (time.perf_counter() - pipeline_start) * 1000
        self._logger.info(
            "pipeline_completed total_ms=%.1f stages=%d errors=%d",
            total_ms, len(ctx.stage_timings), len(ctx.stage_errors),
        )

        return PipelineResult.succeeded(ctx)
