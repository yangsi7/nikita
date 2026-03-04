"""Tests for pipeline events admin endpoints (Spec 110 AC-4)."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.api.schemas.admin import (
    ConversationEventsResponse,
    PaginatedEventsResponse,
    PipelineEventItem,
)


class TestConversationEventsEndpoint:
    """Test GET /admin/conversations/{id}/events."""

    def test_conversation_events_response_model(self):
        """AC-4: Response includes events list and count."""
        event = PipelineEventItem(
            id=uuid4(),
            user_id=uuid4(),
            conversation_id=uuid4(),
            event_type="extraction.complete",
            stage="extraction",
            data={"facts_count": 5},
            duration_ms=150,
            created_at=datetime.now(timezone.utc),
        )

        response = ConversationEventsResponse(
            conversation_id=uuid4(),
            events=[event],
            count=1,
        )

        assert response.count == 1
        assert response.events[0].event_type == "extraction.complete"

    def test_empty_events_response(self):
        """AC-3: Graceful degradation for pre-Spec-110 conversations."""
        response = ConversationEventsResponse(
            conversation_id=uuid4(),
            events=[],
            count=0,
        )

        assert response.count == 0
        assert response.events == []


class TestPaginatedEventsEndpoint:
    """Test GET /admin/events."""

    def test_paginated_events_response_model(self):
        """AC-4: GET /admin/events supports pagination."""
        response = PaginatedEventsResponse(
            events=[
                PipelineEventItem(
                    id=uuid4(),
                    user_id=uuid4(),
                    event_type="pipeline.complete",
                    data={"success": True},
                    created_at=datetime.now(timezone.utc),
                ),
            ],
            total_count=100,
            page=1,
            page_size=50,
        )

        assert response.total_count == 100
        assert response.page == 1
        assert len(response.events) == 1

    def test_pipeline_event_item_optional_fields(self):
        """PipelineEventItem works with nullable fields."""
        event = PipelineEventItem(
            id=uuid4(),
            user_id=uuid4(),
            conversation_id=None,
            event_type="pipeline.complete",
            stage=None,
            data={},
            duration_ms=None,
            created_at=datetime.now(timezone.utc),
        )

        assert event.conversation_id is None
        assert event.stage is None
        assert event.duration_ms is None


class TestPipelineEventDataPayloads:
    """Test event data payload shapes match AC-2 requirements."""

    def test_extraction_complete_payload(self):
        """AC-2: extraction.complete has facts_count, emotional_tone."""
        event = PipelineEventItem(
            id=uuid4(),
            user_id=uuid4(),
            conversation_id=uuid4(),
            event_type="extraction.complete",
            stage="extraction",
            data={
                "facts_count": 5,
                "threads_count": 2,
                "thoughts_count": 1,
                "emotional_tone": "happy",
                "summary": "Talked about dogs",
                "facts": [{"text": "likes dogs", "type": "preference"}],
            },
            duration_ms=1200,
            created_at=datetime.now(timezone.utc),
        )

        assert event.data["facts_count"] == 5
        assert event.data["emotional_tone"] == "happy"

    def test_game_state_complete_payload(self):
        """AC-2: game_state.complete has score_delta, chapter_changed."""
        event = PipelineEventItem(
            id=uuid4(),
            user_id=uuid4(),
            conversation_id=uuid4(),
            event_type="game_state.complete",
            stage="game_state",
            data={
                "score_delta": 2.5,
                "score_events": ["engagement_bonus"],
                "chapter_changed": False,
                "chapter": 2,
            },
            duration_ms=50,
            created_at=datetime.now(timezone.utc),
        )

        assert event.data["score_delta"] == 2.5
        assert event.data["chapter_changed"] is False

    def test_pipeline_complete_payload(self):
        """AC-2: pipeline.complete has per-stage timings and success."""
        event = PipelineEventItem(
            id=uuid4(),
            user_id=uuid4(),
            conversation_id=uuid4(),
            event_type="pipeline.complete",
            data={
                "stages": [
                    {"name": "extraction", "duration_ms": 1200, "status": "success"},
                    {"name": "memory_update", "duration_ms": 300, "status": "success"},
                ],
                "total_duration_ms": 3500,
                "success": True,
            },
            created_at=datetime.now(timezone.utc),
        )

        assert event.data["success"] is True
        assert len(event.data["stages"]) == 2
        assert event.data["total_duration_ms"] == 3500
