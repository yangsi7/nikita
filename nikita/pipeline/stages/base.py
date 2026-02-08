"""Lightweight base class for unified pipeline stages (Spec 042).

Simplified from nikita/context/stages/base.py — no tenacity, no OpenTelemetry.
Just timeout + structured logging + error handling.
"""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import logging

if TYPE_CHECKING:
    from nikita.pipeline.models import PipelineContext

logger = logging.getLogger(__name__)


@dataclass
class StageResult:
    """Result from a pipeline stage execution."""
    success: bool
    data: dict | None = None
    error: str | None = None
    duration_ms: float = 0.0

    @classmethod
    def ok(cls, data: dict | None = None, duration_ms: float = 0.0) -> StageResult:
        return cls(success=True, data=data, duration_ms=duration_ms)

    @classmethod
    def fail(cls, error: str, duration_ms: float = 0.0) -> StageResult:
        return cls(success=False, error=error, duration_ms=duration_ms)


class StageError(Exception):
    """Expected stage failure."""
    def __init__(self, stage_name: str, message: str, recoverable: bool = True):
        self.stage_name = stage_name
        self.recoverable = recoverable
        super().__init__(f"[{stage_name}] {message}")


class BaseStage(ABC):
    """Lightweight base for unified pipeline stages.

    Subclasses set name, is_critical, timeout_seconds and implement _run().
    execute() wraps _run() with timeout and error handling.
    """

    name: str = "unnamed"
    is_critical: bool = False
    timeout_seconds: float = 30.0

    def __init__(self, session: Any = None, **kwargs):
        self._session = session
        self._logger = logging.getLogger(f"{__name__}.{self.name}")

    async def execute(self, ctx: PipelineContext) -> StageResult:
        """Run stage with timeout + error handling."""
        start = time.perf_counter()
        try:
            data = await asyncio.wait_for(
                self._run(ctx),
                timeout=self.timeout_seconds,
            )
            duration_ms = (time.perf_counter() - start) * 1000
            self._logger.info("stage_complete duration_ms=%.1f", duration_ms)
            return StageResult.ok(data=data, duration_ms=duration_ms)

        except asyncio.TimeoutError:
            duration_ms = (time.perf_counter() - start) * 1000
            error = f"Stage {self.name} timed out after {self.timeout_seconds}s"
            self._logger.error("stage_timeout timeout=%s", self.timeout_seconds)
            # Rollback session after timeout to prevent dirty state
            await self._safe_rollback()
            return StageResult.fail(error=error, duration_ms=duration_ms)

        except StageError as e:
            duration_ms = (time.perf_counter() - start) * 1000
            self._logger.error("stage_error: %s", e)
            await self._safe_rollback()
            return StageResult.fail(error=str(e), duration_ms=duration_ms)

        except Exception as e:
            duration_ms = (time.perf_counter() - start) * 1000
            error = f"Unexpected error in {self.name}: {type(e).__name__}: {e}"
            self._logger.error("stage_failed: %s", e, exc_info=True)
            await self._safe_rollback()
            return StageResult.fail(error=error, duration_ms=duration_ms)

    async def _safe_rollback(self) -> None:
        """Best-effort session rollback after stage failure."""
        if self._session is not None:
            try:
                await self._session.rollback()
            except Exception as rb_err:
                self._logger.warning("rollback_failed: %s", rb_err)

    @abstractmethod
    async def _run(self, ctx: PipelineContext) -> dict | None:
        """Implement stage logic. Return data dict or None."""
        ...
