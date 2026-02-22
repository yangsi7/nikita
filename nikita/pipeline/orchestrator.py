"""Pipeline orchestrator for the unified pipeline (Spec 042 T2.2).

Runs 10 stages sequentially, handles critical vs non-critical failures,
logs per-stage timings, and records job execution in the database.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
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

    Runs 10 stages in order. Critical stage failure stops the pipeline;
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
        ("persistence", "nikita.pipeline.stages.persistence.PersistenceStage", False),
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

    async def process(
        self,
        conversation_id: UUID,
        user_id: UUID,
        platform: str = "text",
        conversation: Any = None,
        user: Any = None,
    ) -> PipelineResult:
        """Run the full pipeline for a conversation.

        Args:
            conversation_id: The conversation to process.
            user_id: Owner of the conversation.
            platform: "text" or "voice".
            conversation: The Conversation ORM object (with messages JSONB).
            user: The User ORM object (with metrics, engagement, vices).

        Returns:
            PipelineResult with success/failure status and full context.
        """
        ctx = PipelineContext(
            conversation_id=conversation_id,
            user_id=user_id,
            started_at=datetime.now(timezone.utc),
            platform=platform,
        )

        # BUG-001 fix: Populate conversation and user state from ORM objects
        if conversation is not None:
            ctx.conversation = conversation
        if user is not None:
            ctx.user = user
            ctx.chapter = getattr(user, "chapter", 1) or 1
            ctx.game_status = getattr(user, "game_status", "active") or "active"
            score = getattr(user, "relationship_score", None)
            if score is not None:
                from decimal import Decimal as _Dec
                ctx.relationship_score = _Dec(str(score))
            # Load metrics from eager-loaded user_metrics
            metrics_obj = getattr(user, "user_metrics", None)
            if metrics_obj:
                from decimal import Decimal as _Dec
                ctx.metrics = {
                    "intimacy": getattr(metrics_obj, "intimacy", _Dec("50")),
                    "passion": getattr(metrics_obj, "passion", _Dec("50")),
                    "trust": getattr(metrics_obj, "trust", _Dec("50")),
                    "secureness": getattr(metrics_obj, "secureness", _Dec("50")),
                }
            # Load engagement state
            engagement = getattr(user, "engagement_state", None)
            if engagement:
                ctx.engagement_state = getattr(engagement, "state", None)
            # Load vices from eager-loaded vice_preferences
            vice_prefs = getattr(user, "vice_preferences", None)
            if vice_prefs:
                ctx.vices = [
                    vp.category for vp in vice_prefs
                    if hasattr(vp, "category")
                ]

        # Spec 049 AC-3.1: Skip processing for terminal game states
        if ctx.game_status in ("game_over", "won"):
            self._logger.info(
                "pipeline_skipped_terminal_state",
                game_status=ctx.game_status,
                user_id=str(user_id),
            )
            return PipelineResult(
                context=ctx,
                success=True,
                stages_completed=0,
                stages_total=10,
                skipped=True,
                skip_reason=f"Terminal game_status: {ctx.game_status}",
            )

        self._logger.info(
            "pipeline_started conversation=%s user=%s platform=%s",
            conversation_id, user_id, platform,
        )

        stages = self._get_stages()
        pipeline_start = time.perf_counter()

        for name, stage, critical in stages:
            stage_start = time.perf_counter()

            max_attempts = 1 if critical else 2  # Non-critical get 1 retry
            last_error: str | None = None
            succeeded = False

            for attempt in range(max_attempts):
                try:
                    # SAVEPOINT isolation: each stage gets a nested transaction.
                    # If a stage fails, its DB changes are rolled back without
                    # poisoning the session for subsequent stages.
                    async with self._session.begin_nested():
                        result: StageResult = await stage.execute(ctx)

                    if result.success:
                        succeeded = True
                        break

                    last_error = result.error or "Unknown error"
                    if attempt < max_attempts - 1:
                        self._logger.info(
                            "stage_retry stage=%s attempt=%d/%d error=%s",
                            name, attempt + 1, max_attempts, last_error,
                        )
                        await asyncio.sleep(0.5)
                    continue

                except Exception as e:
                    last_error = f"Unexpected error in {name}: {type(e).__name__}: {e}"
                    if attempt < max_attempts - 1:
                        self._logger.info(
                            "stage_retry stage=%s attempt=%d/%d error=%s",
                            name, attempt + 1, max_attempts, e,
                        )
                        await asyncio.sleep(0.5)
                        continue

                    self._logger.error(
                        "stage_unexpected_error stage=%s critical=%s: %s",
                        name, critical, e,
                    )
                    break

            duration_ms = (time.perf_counter() - stage_start) * 1000
            # Spec 105 T4.1: record timing + success outcome for persistence
            ctx.record_stage_result(name, duration_ms, succeeded)

            if succeeded:
                self._logger.info(
                    "stage_completed stage=%s duration_ms=%.1f",
                    name, duration_ms,
                )
            elif critical:
                return PipelineResult.failed(ctx, name, last_error or "Unknown error")
            else:
                self._logger.warning(
                    "stage_failed stage=%s critical=%s duration_ms=%.1f: %s",
                    name, critical, duration_ms, last_error,
                )
                ctx.record_stage_error(name, last_error or "Unknown error")

        total_ms = (time.perf_counter() - pipeline_start) * 1000
        self._logger.info(
            "pipeline_completed total_ms=%.1f stages=%d errors=%d",
            total_ms, len(ctx.stage_timings), len(ctx.stage_errors),
        )

        return PipelineResult.succeeded(ctx)
