# Spec 110 — Tasks

## US-1: Observability Module

- [ ] T1.1: Create `nikita/observability/types.py` with 11 event type constants
- [ ] T1.2: Create `nikita/observability/emitter.py` — EventEmitter + NullEmitter
- [ ] T1.3: Create `nikita/observability/snapshots.py` — snapshot + delta functions
- [ ] T1.4: Create `nikita/observability/__init__.py` — exports

## US-2: Database

- [ ] T2.1: Create `nikita/db/models/pipeline_event.py`
- [ ] T2.2: Apply migration via Supabase MCP
- [ ] T2.3: Create migration stub

## US-3: Orchestrator Integration

- [ ] T3.1: Add `OBSERVABILITY_ENABLED` to `nikita/config/settings.py`
- [ ] T3.2: Instrument `orchestrator.py` with snapshot/emit/flush loop

## US-4: Admin API

- [ ] T4.1: Add Pydantic schemas for event responses
- [ ] T4.2: Add `GET /admin/conversations/{id}/events` endpoint
- [ ] T4.3: Add `GET /admin/events` paginated endpoint

## US-5: Conversation Inspector

- [ ] T5.1: Create `/admin/conversations/[id]/page.tsx`

## US-6: Tests

- [ ] T6.1: Write `tests/test_observability/test_emitter.py`
- [ ] T6.2: Write `tests/test_observability/test_snapshots.py`
- [ ] T6.3: Write `tests/test_observability/test_endpoints.py`
