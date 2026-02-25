"""Conflict evaluation stage (T2.8).

Non-critical: logs error on failure, continues.
Uses real ConflictDetector from emotional_state module.

Spec 057: Temperature-based conflict detection (behind feature flag).
When temperature flag is ON, reads temperature from conflict_details
and uses zones instead of discrete ConflictState enum.
Also applies passive time decay to temperature.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from nikita.pipeline.stages.base import BaseStage

if TYPE_CHECKING:
    from nikita.pipeline.models import PipelineContext
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


class ConflictStage(BaseStage):
    """Evaluate conflict triggers using ConflictDetector.

    Non-critical: failure does not stop the pipeline.
    Spec 057: Supports temperature-based detection behind feature flag.
    """

    name = "conflict"
    is_critical = False
    timeout_seconds = 15.0

    def __init__(self, session: AsyncSession = None, **kwargs) -> None:
        super().__init__(session=session, **kwargs)

    async def _run(self, ctx: PipelineContext) -> dict | None:
        """Temperature-based conflict detection (Spec 057).

        Reads conflict_details from ctx, applies passive time decay,
        maps temperature zones to active_conflict boolean.
        """
        try:
            from nikita.conflicts.models import ConflictDetails, TemperatureZone
            from nikita.conflicts.temperature import TemperatureEngine

            # Read conflict_details from ctx (set by earlier stages or DB)
            raw_details = getattr(ctx, "conflict_details", None) or {}
            details = ConflictDetails.from_jsonb(raw_details)

            # T17: Apply passive time decay
            if details.last_temp_update:
                from datetime import UTC, datetime

                try:
                    last_update = datetime.fromisoformat(details.last_temp_update)
                    now = datetime.now(UTC)
                    hours_elapsed = (now - last_update).total_seconds() / 3600
                    if hours_elapsed > 0:
                        new_temp = TemperatureEngine.apply_time_decay(
                            current=details.temperature,
                            hours_elapsed=hours_elapsed,
                        )
                        details = TemperatureEngine.update_conflict_details(
                            details=details,
                            temp_delta=new_temp - details.temperature,
                            now=now,
                        )
                except (ValueError, TypeError):
                    pass  # Invalid timestamp format — skip decay

            # Get zone and determine active conflict
            zone = TemperatureEngine.get_zone(details.temperature)
            active = zone in (TemperatureZone.HOT, TemperatureZone.CRITICAL)
            conflict_type = zone.value if active else None

            ctx.active_conflict = active
            ctx.conflict_type = conflict_type

            # Store temperature value for prompt builder access
            ctx.conflict_temperature = details.temperature
            ctx.conflict_details = details.to_jsonb()

            # Spec 057: Persist updated conflict_details (with decay applied) back to DB
            if self._session is not None:
                try:
                    from nikita.conflicts.persistence import save_conflict_details
                    await save_conflict_details(
                        ctx.user_id, details.to_jsonb(), self._session
                    )
                except Exception as save_err:
                    logger.warning("conflict_details_save_failed", error=str(save_err))

            if active:
                self._logger.info(
                    "temperature_conflict_detected",
                    temperature=details.temperature,
                    zone=zone.value,
                    chapter=ctx.chapter,
                )

            # Check breakup with temperature data
            self._check_breakup(ctx, conflict_details=details.to_jsonb())

            return {
                "active": active,
                "type": conflict_type,
                "temperature": details.temperature,
                "zone": zone.value,
            }

        except Exception as e:
            logger.error("temperature_conflict_detection_failed", exc_info=True)
            ctx.active_conflict = False
            ctx.conflict_type = None
            return {"active": False, "type": None, "error": str(e)[:100]}

    def _check_breakup(
        self,
        ctx: PipelineContext,
        conflict_details: dict[str, Any] | None = None,
    ) -> None:
        """Check breakup threshold (shared by both modes)."""
        if ctx.relationship_score is not None:
            try:
                from nikita.conflicts.breakup import BreakupManager

                breakup_mgr = BreakupManager()
                threshold_result = breakup_mgr.check_threshold(
                    user_id=str(ctx.user_id),
                    relationship_score=int(ctx.relationship_score),
                    conflict_details=conflict_details,
                )
                if threshold_result.should_breakup:
                    ctx.game_over_triggered = True
                    self._logger.warning(
                        "breakup_threshold_triggered",
                        user_id=str(ctx.user_id),
                        score=int(ctx.relationship_score),
                        reason=threshold_result.reason,
                    )
            except Exception as breakup_error:
                self._logger.error(
                    "breakup_check_failed", error=str(breakup_error)
                )
