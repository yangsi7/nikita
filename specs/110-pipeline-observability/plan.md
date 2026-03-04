# Spec 110 — Implementation Plan

## Overview

~942 lines across 10 files. 7 new + 3 modified. Zero pipeline stage code changes.

## Task Breakdown

### US-1: Observability Module (nikita/observability/)
- T1.1: Create `types.py` — 11 event type string constants
- T1.2: Create `emitter.py` — EventEmitter (buffer, emit, flush) + NullEmitter
- T1.3: Create `snapshots.py` — per-stage ctx field snapshot + delta computation
- T1.4: Create `__init__.py` — package exports

### US-2: Database Model + Migration
- T2.1: Create `nikita/db/models/pipeline_event.py` — PipelineEvent SQLAlchemy model
- T2.2: Apply pipeline_events table + 4 indexes via Supabase MCP
- T2.3: Create migration stub in `supabase/migrations/`

### US-3: Orchestrator Integration
- T3.1: Add `OBSERVABILITY_ENABLED` to settings.py
- T3.2: Modify orchestrator.py — snapshot/emit loop + flush after pipeline

### US-4: Admin API Endpoints
- T4.1: Add response schemas to admin schemas
- T4.2: Add `GET /admin/conversations/{id}/events` endpoint
- T4.3: Add `GET /admin/events` endpoint with pagination + filters

### US-5: Conversation Inspector Page
- T5.1: Create `/admin/conversations/[id]/page.tsx` with:
  - Conversation metadata header
  - Stage timeline bar (proportional durations)
  - Summary cards (facts, score delta, tone, tokens, duration)
  - Event timeline with collapsible JSON viewer
  - Graceful degradation for pre-110 conversations

### US-6: Tests (TDD)
- T6.1: `test_emitter.py` — buffer, flush, NullEmitter, truncation, failure handling
- T6.2: `test_snapshots.py` — per-stage snapshot + delta computation
- T6.3: `test_endpoints.py` — admin endpoint tests with auth

## Dependencies

US-1 → US-3 (emitter needed for orchestrator)
US-2 → US-4 (model needed for endpoints)
US-6 written BEFORE US-1/US-3 (TDD)
US-5 independent (API contract defined)

## Estimated Lines

| Component | Lines |
|-----------|-------|
| observability/ | ~215 |
| DB model | ~30 |
| Orchestrator changes | ~40 |
| Settings | ~2 |
| API endpoints + schemas | ~60 |
| Portal page | ~350 |
| Tests | ~220 |
| **Total** | **~917** |
