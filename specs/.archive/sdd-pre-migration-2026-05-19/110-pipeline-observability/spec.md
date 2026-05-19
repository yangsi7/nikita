# Spec 110: Pipeline Observability & Event Stream — Phase A

**Status**: APPROVED — Implementation in progress
**Domain**: Admin & Observability (Domain 7)
**Depends on**: Spec 042 (unified pipeline), Spec 044 (portal)

## Summary

Emit typed observability events from the pipeline orchestrator by snapshotting PipelineContext before/after each stage. Single `pipeline_events` table, EventEmitter with buffer+flush pattern, NullEmitter for feature flag OFF. One new portal page: Conversation Inspector (`/admin/conversations/[id]`).

## Key Design Decisions

- **Zero stage code changes** — all events emitted from orchestrator.py via ctx delta snapshots
- **Buffer-based writes** — single bulk INSERT after pipeline completes
- **Non-blocking** — flush failures logged and swallowed
- **Feature-flagged** — `OBSERVABILITY_ENABLED` (default: true)
- **30-day retention** — pg_cron cleanup job

## Event Types (11)

extraction.complete, memory_update.complete, persistence.complete, life_simulation.complete, emotional_state.complete, game_state.complete, conflict.complete, touchpoint.complete, summary.complete, prompt_builder.complete, pipeline.complete

## Files Impact

**New (7)**: observability/{__init__, emitter, types, snapshots}.py, db/models/pipeline_event.py, portal conversation inspector, 3 test files
**Modified (3)**: orchestrator.py (~40 lines), settings.py (2 lines), admin.py (~60 lines)

## Acceptance Criteria

See full spec in user's approved document (Sections 10.1-10.7).

## Deferred to Phase B/C

Event Stream page, Psyche Dashboard, Inner World, non-pipeline instrumentation, custom per-event rendering, psyche_state_history table.
