"""Tests for context snapshot and delta computation (Spec 110 AC-2)."""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from nikita.observability.snapshots import (
    STAGE_FIELDS,
    compute_delta,
    snapshot_ctx,
)
from nikita.pipeline.models import PipelineContext


def _make_ctx(**kwargs) -> PipelineContext:
    """Create a PipelineContext with defaults + overrides."""
    defaults = {
        "conversation_id": uuid4(),
        "user_id": uuid4(),
        "started_at": datetime.now(timezone.utc),
        "platform": "text",
    }
    defaults.update(kwargs)
    return PipelineContext(**defaults)


class TestSnapshotCtx:
    """Test that snapshot_ctx captures the right fields per stage."""

    def test_snapshot_extraction_fields(self):
        ctx = _make_ctx(
            extracted_facts=[{"text": "likes dogs", "type": "preference"}],
            emotional_tone="happy",
        )
        snap = snapshot_ctx(ctx, "extraction")

        assert "extracted_facts" in snap
        assert "emotional_tone" in snap
        assert snap["emotional_tone"] == "happy"

    def test_snapshot_game_state_fields(self):
        ctx = _make_ctx(score_delta=Decimal("3.5"), chapter_changed=True)
        snap = snapshot_ctx(ctx, "game_state")

        assert "score_delta" in snap
        assert "chapter_changed" in snap
        assert snap["score_delta"] == 3.5  # Decimal → float

    def test_snapshot_unknown_stage_returns_empty(self):
        ctx = _make_ctx()
        snap = snapshot_ctx(ctx, "nonexistent_stage")

        assert snap == {}

    def test_snapshot_all_stages_have_fields(self):
        """Every stage in STAGE_FIELDS can be snapshotted without error."""
        ctx = _make_ctx()
        for stage_name in STAGE_FIELDS:
            snap = snapshot_ctx(ctx, stage_name)
            assert isinstance(snap, dict)


class TestComputeDelta:
    """Test that compute_delta produces correct event payloads."""

    def test_extraction_delta(self):
        """AC-2: extraction.complete includes facts_count, emotional_tone."""
        ctx = _make_ctx(
            extracted_facts=[
                {"text": "likes dogs", "type": "preference"},
                {"text": "works in tech", "type": "fact"},
            ],
            extracted_threads=[{"topic": "pets"}],
            extracted_thoughts=[{"content": "she seems nice"}],
            extraction_summary="Discussion about pets and work",
            emotional_tone="positive",
        )
        before = snapshot_ctx(ctx, "extraction")
        # Simulate stage already ran — delta is based on current ctx
        delta = compute_delta(before, ctx, "extraction")

        assert delta["facts_count"] == 2
        assert delta["threads_count"] == 1
        assert delta["thoughts_count"] == 1
        assert delta["emotional_tone"] == "positive"
        assert len(delta["facts"]) == 2

    def test_memory_update_delta(self):
        ctx = _make_ctx(facts_stored=5, facts_deduplicated=2)
        before = {}
        delta = compute_delta(before, ctx, "memory_update")

        assert delta["facts_stored"] == 5
        assert delta["facts_deduplicated"] == 2

    def test_persistence_delta(self):
        ctx = _make_ctx(thoughts_persisted=3, threads_persisted=1)
        before = {}
        delta = compute_delta(before, ctx, "persistence")

        assert delta["thoughts_persisted"] == 3
        assert delta["threads_persisted"] == 1

    def test_game_state_delta(self):
        """AC-2: game_state.complete includes score_delta, chapter_changed."""
        ctx = _make_ctx(
            score_delta=Decimal("2.5"),
            score_events=["boss_pass", "engagement_bonus"],
            chapter_changed=True,
            chapter=3,
        )
        before = {}
        delta = compute_delta(before, ctx, "game_state")

        assert delta["score_delta"] == 2.5
        assert len(delta["score_events"]) == 2
        assert delta["chapter_changed"] is True
        assert delta["chapter"] == 3

    def test_conflict_delta(self):
        """AC-2: conflict.complete includes active_conflict, temperature."""
        ctx = _make_ctx(
            active_conflict=True,
            conflict_type="jealousy",
            conflict_temperature=0.7,
        )
        before = {}
        delta = compute_delta(before, ctx, "conflict")

        assert delta["active_conflict"] is True
        assert delta["conflict_temperature"] == 0.7

    def test_prompt_builder_delta(self):
        """AC-2: prompt_builder.complete includes prompt_token_count."""
        ctx = _make_ctx(prompt_token_count=4500, platform="text")
        before = {}
        delta = compute_delta(before, ctx, "prompt_builder")

        assert delta["prompt_token_count"] == 4500
        assert delta["platform"] == "text"

    def test_touchpoint_delta(self):
        ctx = _make_ctx(touchpoint_scheduled=True)
        before = {}
        delta = compute_delta(before, ctx, "touchpoint")

        assert delta["touchpoint_scheduled"] is True

    def test_summary_delta(self):
        ctx = _make_ctx(daily_summary_updated=True)
        before = {}
        delta = compute_delta(before, ctx, "summary")

        assert delta["daily_summary_updated"] is True

    def test_emotional_delta(self):
        ctx = _make_ctx(
            emotional_state={"arousal": 0.5, "valence": 0.8, "dominance": 0.3}
        )
        before = {}
        delta = compute_delta(before, ctx, "emotional")

        assert delta["emotional_state"]["valence"] == 0.8

    def test_life_sim_delta_with_dict_events(self):
        ctx = _make_ctx(
            life_events=[
                {"domain": "social", "description": "Coffee with best friend"},
                {"domain": "work", "description": "Late meeting"},
            ]
        )
        before = {}
        delta = compute_delta(before, ctx, "life_sim")

        assert delta["events_count"] == 2
        assert delta["events"][0]["domain"] == "social"

    def test_extraction_truncates_summary(self):
        """Long summaries are truncated to 200 chars in extraction delta."""
        long_summary = "x" * 500
        ctx = _make_ctx(extraction_summary=long_summary)
        before = {}
        delta = compute_delta(before, ctx, "extraction")

        assert len(delta["summary"]) == 200

    def test_extraction_limits_facts_to_10(self):
        """Facts list is capped at 10 items in extraction delta."""
        ctx = _make_ctx(
            extracted_facts=[{"text": f"fact {i}", "type": "test"} for i in range(20)]
        )
        before = {}
        delta = compute_delta(before, ctx, "extraction")

        assert len(delta["facts"]) == 10
        assert delta["facts_count"] == 20
