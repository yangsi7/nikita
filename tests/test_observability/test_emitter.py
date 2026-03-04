"""Tests for EventEmitter and NullEmitter (Spec 110 AC-1)."""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from nikita.observability.emitter import EventEmitter, NullEmitter, MAX_EVENT_DATA_SIZE


# ============================================================================
# EventEmitter Tests
# ============================================================================


class TestEventEmitter:
    """Test EventEmitter buffer, emit, and flush behavior."""

    def setup_method(self):
        self.user_id = uuid4()
        self.conversation_id = uuid4()
        self.emitter = EventEmitter(self.user_id, self.conversation_id)

    def test_emit_adds_to_buffer(self):
        """AC-1: Events accumulate in memory buffer."""
        self.emitter.emit("extraction.complete", stage="extraction", data={"facts_count": 5})

        assert self.emitter.event_count == 1
        assert self.emitter.events[0]["event_type"] == "extraction.complete"
        assert self.emitter.events[0]["stage"] == "extraction"
        assert self.emitter.events[0]["data"]["facts_count"] == 5

    def test_emit_inherits_user_and_conversation(self):
        """AC-1: All events inherit user_id and conversation_id."""
        self.emitter.emit("pipeline.complete", data={"success": True})

        event = self.emitter.events[0]
        assert event["user_id"] == self.user_id
        assert event["conversation_id"] == self.conversation_id

    def test_emit_multiple_events(self):
        """AC-1: Pipeline run emits multiple events to buffer."""
        self.emitter.emit("extraction.complete", stage="extraction", data={})
        self.emitter.emit("memory_update.complete", stage="memory_update", data={})
        self.emitter.emit("pipeline.complete", data={"success": True})

        assert self.emitter.event_count == 3

    def test_emit_with_duration(self):
        """Events record stage duration."""
        self.emitter.emit("extraction.complete", stage="extraction", duration_ms=150)

        assert self.emitter.events[0]["duration_ms"] == 150

    def test_emit_with_none_data(self):
        """Emit with no data defaults to empty dict."""
        self.emitter.emit("touchpoint.complete", stage="touchpoint")

        assert self.emitter.events[0]["data"] == {}

    def test_emit_timestamps_are_utc(self):
        """Events have UTC timestamps."""
        self.emitter.emit("extraction.complete", data={})

        ts = self.emitter.events[0]["created_at"]
        assert ts.tzinfo is not None

    def test_emit_truncates_oversized_payload(self):
        """AC-2: Event data payloads <= 16KB, truncated if over."""
        big_data = {"items": [{"text": "x" * 200} for _ in range(200)]}
        self.emitter.emit("extraction.complete", data=big_data)

        event = self.emitter.events[0]
        serialized = json.dumps(event["data"], default=str)
        # Should be truncated + have _truncated flag
        assert event["data"].get("_truncated") is True

    def test_emit_handles_unserializable_data(self):
        """Gracefully handle non-serializable data."""
        class Custom:
            pass

        self.emitter.emit("test.event", data={"obj": Custom()})
        # Should not raise — falls back to _serialization_error
        assert self.emitter.event_count == 1

    @pytest.mark.asyncio
    async def test_flush_creates_pipeline_events(self):
        """AC-1: flush() performs bulk INSERT via session."""
        self.emitter.emit("extraction.complete", stage="extraction", data={"facts": 3})
        self.emitter.emit("pipeline.complete", data={"success": True})

        mock_session = AsyncMock()
        mock_session.add_all = MagicMock()
        mock_session.flush = AsyncMock()

        with patch("nikita.db.models.pipeline_event.PipelineEvent") as MockPE:
            # Make PipelineEvent constructor return mock instances
            MockPE.side_effect = lambda **kwargs: MagicMock(**kwargs)

            await self.emitter.flush(mock_session)

        # Should have called add_all with 2 events
        mock_session.add_all.assert_called_once()
        events_added = mock_session.add_all.call_args[0][0]
        assert len(events_added) == 2

        # Buffer should be cleared after flush
        assert self.emitter.event_count == 0

    @pytest.mark.asyncio
    async def test_flush_empty_buffer_is_noop(self):
        """AC-1: flush() with empty buffer does nothing."""
        mock_session = AsyncMock()

        await self.emitter.flush(mock_session)

        mock_session.add_all.assert_not_called()

    @pytest.mark.asyncio
    async def test_flush_failure_does_not_raise(self):
        """AC-1: EventEmitter failure does not fail the pipeline."""
        self.emitter.emit("extraction.complete", data={"test": True})

        mock_session = AsyncMock()
        mock_session.add_all = MagicMock(side_effect=Exception("DB connection lost"))

        # Should NOT raise
        await self.emitter.flush(mock_session)

        # Buffer should be cleared even on failure
        assert self.emitter.event_count == 0

    @pytest.mark.asyncio
    async def test_flush_clears_buffer(self):
        """Buffer is always cleared after flush, success or failure."""
        self.emitter.emit("test.event", data={})

        mock_session = AsyncMock()
        mock_session.add_all = MagicMock()
        mock_session.flush = AsyncMock()

        with patch("nikita.db.models.pipeline_event.PipelineEvent") as MockPE:
            MockPE.side_effect = lambda **kwargs: MagicMock(**kwargs)
            await self.emitter.flush(mock_session)

        assert self.emitter.event_count == 0


# ============================================================================
# NullEmitter Tests
# ============================================================================


class TestNullEmitter:
    """Test NullEmitter no-op behavior."""

    def test_emit_is_noop(self):
        """AC-1: NullEmitter used when OBSERVABILITY_ENABLED=false."""
        emitter = NullEmitter()
        emitter.emit("extraction.complete", data={"big": "payload"})

        assert emitter.event_count == 0
        assert emitter.events == []

    @pytest.mark.asyncio
    async def test_flush_is_noop(self):
        """NullEmitter flush does nothing."""
        emitter = NullEmitter()
        emitter.emit("test.event", data={})

        mock_session = AsyncMock()
        await emitter.flush(mock_session)

        # No calls to session
        assert not mock_session.called
