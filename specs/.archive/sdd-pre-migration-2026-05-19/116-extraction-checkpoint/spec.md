# Spec 116 — Extraction Checkpoint (MP-004)

## Problem

`ExtractionStage` populates `ctx.extracted_facts`, `ctx.extracted_threads`, and
`ctx.extracted_thoughts` in-memory only. Stage 2 (`memory_update`) is CRITICAL and
writes `extracted_facts` to pgVector (SupabaseMemory via OpenAI embeddings).

If `memory_update` fails (e.g. OpenAI outage, embedding rate limit), the orchestrator
returns `PipelineResult.failed()` immediately. Because `PersistenceStage` (which writes
`extracted_thoughts` → `nikita_thoughts` and `extracted_threads` → `conversation_threads`)
runs AFTER `memory_update`, those DB writes never execute.

The API handler (`tasks.py`) calls `conv_session.commit()` even on failure (to persist
the `mark_failed` status). This means any SAVEPOINT-released (committed) stages that
ran before the failure WILL be durably saved.

**Root cause**: `PersistenceStage` is positioned at index 2 (after `memory_update`),
so a `memory_update` failure discards all extracted thoughts and threads permanently.

## Chosen Solution: Option A — Reorder PersistenceStage before MemoryUpdateStage

Move `PersistenceStage` to index 1 (immediately after `ExtractionStage`, before
`MemoryUpdateStage`) in `STAGE_DEFINITIONS`. This ensures:

- `extracted_thoughts` → `nikita_thoughts` persisted before any pgVector call
- `extracted_threads` → `conversation_threads` persisted before any pgVector call
- If `memory_update` then fails, the session commit in the API handler saves
  the persistence writes durably

This is the minimal viable change: no new DB tables, no new migration, no schema changes.
`PersistenceStage` is non-critical so its failure cannot block `memory_update`.

### Why not Option B?

Option B (new `pipeline_checkpoints` table) requires schema migration, new repository,
retry/recovery logic, and replay mechanism. The same durability outcome is achieved
by Option A at minimal cost.

---

## Functional Requirements

### FR-001 — Stage Reorder

Change `STAGE_DEFINITIONS` in `nikita/pipeline/orchestrator.py`:

**Before:**
```
("extraction",    ..., True),   # index 0
("memory_update", ..., True),   # index 1
("persistence",   ..., False),  # index 2
```

**After:**
```
("extraction",    ..., True),   # index 0
("persistence",   ..., False),  # index 1
("memory_update", ..., True),   # index 2
```

### FR-002 — PersistenceStage Docstring Update

Update the module docstring comment in `nikita/pipeline/stages/persistence.py` from
`"Runs after memory_update, before life_sim."` to
`"Runs after extraction, before memory_update."` to reflect the new ordering.

### FR-003 — Observability Registration

`nikita/observability/snapshots.py` maps stage names to `PipelineContext` fields for
delta computation. Verify that `"persistence"` and `"memory_update"` entries are
order-independent (they are — keyed by name, not by position). No change needed.

### FR-004 — No Stage Count Change

This spec does not add or remove stages. Stage count remains 10 on master (Spec 114
ViceStage is on a separate branch). No changes to `stages_total` in `orchestrator.py`
or `models.py`.

---

## Acceptance Criteria

| ID | Criterion |
|----|-----------|
| AC-001 | `STAGE_DEFINITIONS[1]` is `("persistence", ..., False)` |
| AC-002 | `STAGE_DEFINITIONS[2]` is `("memory_update", ..., True)` |
| AC-003 | `PersistenceStage` docstring no longer says "after memory_update" |
| AC-004 | All 11 pipeline stages remain present in `STAGE_DEFINITIONS` |
| AC-005 | All existing pipeline tests pass without modification |

---

## Files to Modify

| File | Change |
|------|--------|
| `nikita/pipeline/orchestrator.py` | Swap persistence (index 2→1) and memory_update (index 1→2) in STAGE_DEFINITIONS |
| `nikita/pipeline/stages/persistence.py` | Update docstring: "after extraction, before memory_update" |

---

## Data Design

No schema changes. No new tables. No migrations.

---

## Security / Reliability

- `PersistenceStage` is non-critical (`is_critical=False`). A DB write failure in
  persistence will NOT prevent `memory_update` from running.
- If persistence fails AND memory_update fails, both sets of data are lost — this is
  accepted as the two-critical-stage failure path (same as today).
- Rollback: revert the STAGE_DEFINITIONS list order. Feature flag not required
  (this is a pure ordering fix, not a behavioral flag).
