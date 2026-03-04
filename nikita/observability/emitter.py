"""EventEmitter for pipeline observability (Spec 110).

Buffer-based event emission with single bulk INSERT on flush.
Non-blocking: flush failures are logged and swallowed.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Protocol
from uuid import UUID

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Max event data payload size (16KB)
MAX_EVENT_DATA_SIZE = 16_384


class EventEmitterProtocol(Protocol):
    """Protocol for event emitters (real + null)."""

    def emit(
        self,
        event_type: str,
        *,
        stage: str | None = None,
        data: dict[str, Any] | None = None,
        duration_ms: int | None = None,
    ) -> None: ...

    async def flush(self, session: AsyncSession) -> None: ...

    @property
    def event_count(self) -> int: ...


class EventEmitter:
    """Buffered event emitter for pipeline observability.

    Events accumulate in memory (list of dicts). Single bulk INSERT on flush().
    If flush() fails, log warning and continue — pipeline never fails due to observability.

    Usage:
        emitter = EventEmitter(user_id, conversation_id)
        emitter.emit("extraction.complete", stage="extraction", data={...}, duration_ms=150)
        emitter.emit("pipeline.complete", data={...})
        await emitter.flush(session)
    """

    def __init__(self, user_id: UUID, conversation_id: UUID | None = None) -> None:
        self._user_id = user_id
        self._conversation_id = conversation_id
        self._buffer: list[dict[str, Any]] = []

    def emit(
        self,
        event_type: str,
        *,
        stage: str | None = None,
        data: dict[str, Any] | None = None,
        duration_ms: int | None = None,
    ) -> None:
        """Append an event to the buffer. No I/O — just memory."""
        payload = data or {}

        # Truncate oversized payloads
        try:
            serialized = json.dumps(payload, default=str)
            if len(serialized) > MAX_EVENT_DATA_SIZE:
                payload = _truncate_payload(payload)
                payload["_truncated"] = True
                logger.warning(
                    "event_payload_truncated event_type=%s size=%d",
                    event_type,
                    len(serialized),
                )
        except (TypeError, ValueError):
            payload = {"_serialization_error": True}

        self._buffer.append(
            {
                "user_id": self._user_id,
                "conversation_id": self._conversation_id,
                "event_type": event_type,
                "stage": stage,
                "data": payload,
                "duration_ms": duration_ms,
                "created_at": datetime.now(timezone.utc),
            }
        )

    async def flush(self, session: AsyncSession) -> None:
        """Bulk INSERT all buffered events. Non-blocking on failure."""
        if not self._buffer:
            return

        try:
            from nikita.db.models.pipeline_event import PipelineEvent

            events = [PipelineEvent(**event_data) for event_data in self._buffer]
            session.add_all(events)
            # Don't commit — let the caller's transaction handle it.
            # The orchestrator already commits after pipeline completes.
            await session.flush()
            logger.info(
                "observability_flush_ok events=%d user=%s conversation=%s",
                len(self._buffer),
                self._user_id,
                self._conversation_id,
            )
        except Exception as e:
            logger.warning(
                "observability_flush_failed events=%d error=%s",
                len(self._buffer),
                e,
            )
            # Log to error_logs for observability-of-observability
            try:
                from nikita.db.models.error_log import ErrorLog

                error_entry = ErrorLog(
                    level="warning",
                    message=f"EventEmitter flush failed: {e}",
                    source="observability",
                    user_id=self._user_id,
                    conversation_id=self._conversation_id,
                    context={"event_count": len(self._buffer)},
                )
                session.add(error_entry)
                await session.flush()
            except Exception:
                pass  # Best-effort error logging
        finally:
            self._buffer.clear()

    @property
    def event_count(self) -> int:
        """Number of events in the buffer."""
        return len(self._buffer)

    @property
    def events(self) -> list[dict[str, Any]]:
        """Read-only access to buffer (for testing)."""
        return list(self._buffer)


class NullEmitter:
    """No-op emitter for when observability is disabled. Zero overhead."""

    def emit(
        self,
        event_type: str,
        *,
        stage: str | None = None,
        data: dict[str, Any] | None = None,
        duration_ms: int | None = None,
    ) -> None:
        """No-op."""

    async def flush(self, session: AsyncSession) -> None:
        """No-op."""

    @property
    def event_count(self) -> int:
        return 0

    @property
    def events(self) -> list[dict[str, Any]]:
        return []


def _truncate_payload(data: dict[str, Any], max_items: int = 10) -> dict[str, Any]:
    """Truncate lists in payload to max_items to reduce size."""
    result: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, list) and len(value) > max_items:
            result[key] = value[:max_items]
            result[f"_{key}_total"] = len(value)
        elif isinstance(value, dict):
            result[key] = _truncate_payload(value, max_items)
        else:
            result[key] = value
    return result
