"""Context snapshot and delta computation for pipeline observability (Spec 110).

Each pipeline stage writes to known fields on PipelineContext. This module
snapshots those fields before a stage runs, then computes the delta after
to generate the event payload. Zero coupling to stage internals.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from nikita.pipeline.models import PipelineContext


# Fields each stage is known to write (from PipelineContext dataclass)
STAGE_FIELDS: dict[str, list[str]] = {
    "extraction": [
        "extracted_facts",
        "extracted_threads",
        "extracted_thoughts",
        "extraction_summary",
        "emotional_tone",
    ],
    "memory_update": [
        "facts_stored",
        "facts_deduplicated",
    ],
    "persistence": [
        "thoughts_persisted",
        "threads_persisted",
    ],
    "life_sim": [
        "life_events",
    ],
    "emotional": [
        "emotional_state",
    ],
    "game_state": [
        "score_delta",
        "score_events",
        "chapter_changed",
        "decay_applied",
    ],
    "conflict": [
        "active_conflict",
        "conflict_type",
        "conflict_temperature",
        "conflict_details",
    ],
    "touchpoint": [
        "touchpoint_scheduled",
    ],
    "summary": [
        "daily_summary_updated",
    ],
    "prompt_builder": [
        "prompt_token_count",
    ],
}


def snapshot_ctx(ctx: PipelineContext, stage_name: str) -> dict[str, Any]:
    """Capture relevant ctx fields before a stage runs.

    Args:
        ctx: The pipeline context.
        stage_name: Name of the stage about to run.

    Returns:
        Dict of field_name → current_value for the stage's known fields.
    """
    fields = STAGE_FIELDS.get(stage_name, [])
    snapshot: dict[str, Any] = {}
    for field_name in fields:
        value = getattr(ctx, field_name, None)
        snapshot[field_name] = _serialize_value(value)
    return snapshot


def compute_delta(
    before: dict[str, Any],
    ctx: PipelineContext,
    stage_name: str,
) -> dict[str, Any]:
    """Compute event payload from before-snapshot and current ctx state.

    Returns a typed event payload derived from what changed.
    """
    builder = _DELTA_BUILDERS.get(stage_name)
    if builder:
        return builder(before, ctx)

    # Generic fallback: return all stage fields from ctx
    fields = STAGE_FIELDS.get(stage_name, [])
    return {
        field_name: _serialize_value(getattr(ctx, field_name, None))
        for field_name in fields
    }


# --- Stage-specific delta builders ---


def _extraction_delta(before: dict[str, Any], ctx: PipelineContext) -> dict[str, Any]:
    facts = ctx.extracted_facts or []
    return {
        "facts_count": len(facts),
        "threads_count": len(ctx.extracted_threads or []),
        "thoughts_count": len(ctx.extracted_thoughts or []),
        "summary": (ctx.extraction_summary or "")[:200],
        "emotional_tone": ctx.emotional_tone,
        "facts": [
            {"text": f.get("text", "")[:100], "type": f.get("type", "unknown")}
            for f in facts[:10]
        ],
    }


def _memory_update_delta(before: dict[str, Any], ctx: PipelineContext) -> dict[str, Any]:
    return {
        "facts_stored": ctx.facts_stored,
        "facts_deduplicated": ctx.facts_deduplicated,
    }


def _persistence_delta(before: dict[str, Any], ctx: PipelineContext) -> dict[str, Any]:
    return {
        "thoughts_persisted": ctx.thoughts_persisted,
        "threads_persisted": ctx.threads_persisted,
    }


def _life_sim_delta(before: dict[str, Any], ctx: PipelineContext) -> dict[str, Any]:
    events = ctx.life_events or []
    return {
        "events_count": len(events),
        "events": [
            {
                "domain": getattr(e, "domain", str(e)[:50]) if not isinstance(e, dict) else e.get("domain", ""),
                "description": getattr(e, "description", str(e)[:100]) if not isinstance(e, dict) else e.get("description", "")[:100],
            }
            for e in events[:10]
        ],
    }


def _emotional_delta(before: dict[str, Any], ctx: PipelineContext) -> dict[str, Any]:
    return {
        "emotional_state": ctx.emotional_state or {},
    }


def _game_state_delta(before: dict[str, Any], ctx: PipelineContext) -> dict[str, Any]:
    return {
        "score_delta": _serialize_value(ctx.score_delta),
        "score_events": ctx.score_events or [],
        "chapter_changed": ctx.chapter_changed,
        "chapter": ctx.chapter,
    }


def _conflict_delta(before: dict[str, Any], ctx: PipelineContext) -> dict[str, Any]:
    return {
        "active_conflict": ctx.active_conflict,
        "conflict_type": ctx.conflict_type,
        "conflict_temperature": ctx.conflict_temperature,
        "conflict_details": ctx.conflict_details,
    }


def _touchpoint_delta(before: dict[str, Any], ctx: PipelineContext) -> dict[str, Any]:
    return {
        "touchpoint_scheduled": ctx.touchpoint_scheduled,
    }


def _summary_delta(before: dict[str, Any], ctx: PipelineContext) -> dict[str, Any]:
    return {
        "daily_summary_updated": ctx.daily_summary_updated,
    }


def _prompt_builder_delta(before: dict[str, Any], ctx: PipelineContext) -> dict[str, Any]:
    return {
        "prompt_token_count": ctx.prompt_token_count,
        "platform": ctx.platform,
    }


_DELTA_BUILDERS: dict[str, Any] = {
    "extraction": _extraction_delta,
    "memory_update": _memory_update_delta,
    "persistence": _persistence_delta,
    "life_sim": _life_sim_delta,
    "emotional": _emotional_delta,
    "game_state": _game_state_delta,
    "conflict": _conflict_delta,
    "touchpoint": _touchpoint_delta,
    "summary": _summary_delta,
    "prompt_builder": _prompt_builder_delta,
}


def _serialize_value(value: Any) -> Any:
    """Convert non-JSON-serializable values."""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, list):
        return [_serialize_value(v) for v in value]
    if isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in value.items()}
    return value
