# Spec 102: Memory & Data Integrity

**Status**: DRAFT | **Wave**: H (Foundation) | **Effort**: M
**Depends on**: None | **Blocks**: None (foundation)

---

## Problem Statement

The memory subsystem and scoring data layer have 4 issues affecting performance, cost, and data integrity:

1. **Embedding double-call** (B4/G12/I6): `add_fact()` at `supabase_memory.py:166` calls `_generate_embedding(fact)`, then `find_similar()` at line 169 calls `_generate_embedding(text)` again with the SAME text. This doubles OpenAI API calls (~$0.0001/call × thousands of facts = measurable waste).

2. **Sequential memory search** (G13/I7): `search()` at `supabase_memory.py:207-213` iterates through `graph_types` list and calls `semantic_search()` separately for each type. With 3 graph types (user, relationship, nikita), this makes 3 sequential DB round-trips where 1 batched query with `WHERE graph_type IN (...)` suffices.

3. **Score drift** (G3): `users.relationship_score` is updated independently from `user_metrics` composite calculation. Over time, these can drift apart (e.g., if a scoring operation updates metrics but crashes before updating the composite). No reconciliation mechanism exists.

4. **Missing index** (G21): `score_history` table is queried by `(user_id, recorded_at DESC)` for timeline charts but has no composite index, causing sequential scans on large datasets.

---

## Requirements

### FR-001: Fix Embedding Double-Call (B4/G12/I6)

- In `add_fact()`: pass the pre-computed embedding to `find_similar()` instead of re-computing
- Change `find_similar()` signature to accept optional `embedding: list[float] | None = None` parameter
- If embedding provided, skip `_generate_embedding()` call inside `find_similar()`
- AC: `add_fact()` calls `_generate_embedding()` exactly ONCE (verified via mock call count)

### FR-002: Batch Memory Search (G13/I7)

- In `search()`: replace the `for graph_type in graph_types` loop with a single batched query
- Add `semantic_search_batch()` method to `MemoryFactRepository` that accepts `graph_types: list[str]`
- SQL: `WHERE user_id = :uid AND graph_type = ANY(:types) AND is_active = true ORDER BY embedding <=> :query_embedding LIMIT :limit`
- AC: `search()` with 3 graph types makes exactly 1 DB query (verified via mock)

### FR-003: Score Reconciliation (G3)

- Add `reconcile_score()` method to `UserRepository` that recalculates composite from metrics and updates `users.relationship_score` if drift > 0.01
- Wire into decay job (runs hourly) — after decay processing, reconcile all processed users
- Log reconciliation events when drift is detected
- AC: If metrics composite = 65.5 but user.relationship_score = 64.2, reconciliation corrects to 65.5

### FR-004: Score History Composite Index (G21)

- Supabase migration: `CREATE INDEX idx_score_history_user_time ON score_history (user_id, recorded_at DESC)`
- AC: `EXPLAIN ANALYZE` on score_history query shows index scan instead of sequential scan

---

## Non-Functional Requirements

- Embedding cost reduction: ~50% fewer OpenAI calls for `add_fact()` operations
- Memory search latency: ~3x improvement (1 DB call vs 3)
- Score reconciliation: transparent, no user-visible behavior change
- Migration is additive-only (CREATE INDEX), no downtime risk

---

## Key Files

| File | Changes |
|------|---------|
| `nikita/memory/supabase_memory.py` | FR-001 (embedding reuse), FR-002 (batch search) |
| `nikita/db/repositories/memory_fact_repository.py` | FR-002 (batch query method) |
| `nikita/db/repositories/user_repository.py` | FR-003 (reconcile_score) |
| `nikita/api/routes/tasks.py` | FR-003 (wire reconciliation into decay) |
| Supabase migration | FR-004 (composite index) |

---

## Acceptance Criteria Summary

| ID | Criterion | Testable |
|----|-----------|----------|
| AC-001 | `add_fact()` calls `_generate_embedding()` exactly once | Yes: mock + call count |
| AC-002 | `find_similar()` accepts pre-computed embedding | Yes: pass embedding, verify no embedding call |
| AC-003 | `search()` with 3 types makes 1 DB call | Yes: mock repo, verify single call |
| AC-004 | Score reconciliation corrects drift > 0.01 | Yes: set drift, run reconcile, verify correction |
| AC-005 | Reconciliation runs during decay job | Yes: mock decay, verify reconcile called |
| AC-006 | Composite index exists on score_history | Yes: Supabase migration applied |
