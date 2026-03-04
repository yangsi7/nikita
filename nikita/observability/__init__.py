"""Pipeline observability module (Spec 110).

Provides EventEmitter for capturing typed events from pipeline stage execution.
Events are buffered in memory and flushed via single bulk INSERT after pipeline completes.

Usage:
    from nikita.observability import EventEmitter, NullEmitter

    emitter = EventEmitter(user_id, conversation_id) if enabled else NullEmitter()
    emitter.emit("extraction.complete", stage="extraction", data={...})
    await emitter.flush(session)
"""

from nikita.observability.emitter import EventEmitter, NullEmitter
from nikita.observability.snapshots import compute_delta, snapshot_ctx
from nikita.observability.types import STAGE_EVENT_TYPES

__all__ = [
    "EventEmitter",
    "NullEmitter",
    "compute_delta",
    "snapshot_ctx",
    "STAGE_EVENT_TYPES",
]
