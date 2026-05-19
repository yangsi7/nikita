# Plan: Spec 102 — Memory & Data Integrity

## Implementation Strategy

4 user stories ordered by isolation (least coupling first). Each follows TDD.

---

## Story 1: Fix Embedding Double-Call (FR-001)

### Tasks

**T1.1** Update `find_similar()` signature to accept optional pre-computed embedding
- Add `embedding: list[float] | None = None` parameter
- If provided, skip `_generate_embedding()` call
- File: `nikita/memory/supabase_memory.py`

**T1.2** Update `add_fact()` to pass pre-computed embedding to `find_similar()`
- Line 166 computes `embedding = await self._generate_embedding(fact)`
- Line 169 calls `find_similar(fact, threshold=0.95)` — change to `find_similar(fact, threshold=0.95, embedding=embedding)`
- File: `nikita/memory/supabase_memory.py`

**T1.3** Tests for embedding reuse
- Test: `add_fact()` calls `_generate_embedding` exactly once (mock + assert_called_once)
- Test: `find_similar()` with embedding param skips generation
- Test: `find_similar()` without embedding still generates (backward compat)
- File: `tests/memory/test_embedding_reuse.py`

---

## Story 2: Batch Memory Search (FR-002)

### Tasks

**T2.1** Add `semantic_search_batch()` to `MemoryFactRepository`
- SQL: `WHERE user_id = :uid AND graph_type = ANY(:types) AND is_active = true ORDER BY embedding <=> :query_embedding LIMIT :limit`
- File: `nikita/db/repositories/memory_fact_repository.py`

**T2.2** Refactor `search()` to use batch query
- Replace `for graph_type in graph_types` loop with single `semantic_search_batch()` call
- Maintain same return format (list of dicts with fact, graph_type, distance, etc.)
- File: `nikita/memory/supabase_memory.py`

**T2.3** Tests for batch search
- Test: search with 3 types makes 1 DB call (mock repo, assert_called_once)
- Test: results sorted by distance across all types
- Test: empty results handled
- File: `tests/memory/test_batch_search.py`

---

## Story 3: Score Reconciliation (FR-003)

### Tasks

**T3.1** Add `reconcile_score()` to `UserRepository`
- Calculate composite from metrics: `intimacy*0.30 + passion*0.25 + trust*0.25 + secureness*0.20`
- If `abs(composite - user.relationship_score) > 0.01`, update user.relationship_score
- Return `(user_id, old_score, new_score, drift)` if corrected, None if no drift
- File: `nikita/db/repositories/user_repository.py`

**T3.2** Wire reconciliation into decay job
- After `processor.process_all()`, iterate processed users and call `reconcile_score()`
- Log any corrections
- File: `nikita/api/routes/tasks.py`

**T3.3** Tests for score reconciliation
- Test: drift of 1.3 → corrected
- Test: drift of 0.005 → no correction (below threshold)
- Test: reconciliation called during decay
- File: `tests/db/test_score_reconciliation.py`

---

## Story 4: Score History Composite Index (FR-004)

### Tasks

**T4.1** Create Supabase migration for composite index
- `CREATE INDEX CONCURRENTLY idx_score_history_user_time ON score_history (user_id, recorded_at DESC)`
- Use `CONCURRENTLY` to avoid table lock
- Apply via Supabase MCP

**T4.2** Verify index usage
- Run EXPLAIN ANALYZE on typical query pattern
- Verify index scan in plan

---

## Risk Mitigation

- `find_similar()` backward compatibility: default `embedding=None` preserves existing behavior
- Batch search maintains exact same output format — transparent to callers
- Reconciliation is additive (only corrects drift) — never makes things worse
- Index creation uses CONCURRENTLY — zero downtime
