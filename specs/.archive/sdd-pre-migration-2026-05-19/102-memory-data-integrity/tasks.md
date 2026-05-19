# Tasks: Spec 102 — Memory & Data Integrity

## Story 1: Fix Embedding Double-Call

- [ ] T1.1: Update `find_similar()` to accept optional pre-computed embedding
  - AC: `find_similar(text, embedding=emb)` uses provided embedding, skips generation
  - Red: Call with embedding param → `_generate_embedding` NOT called
  - File: `nikita/memory/supabase_memory.py`

- [ ] T1.2: Update `add_fact()` to pass embedding to `find_similar()`
  - AC: `add_fact()` calls `_generate_embedding()` exactly ONCE
  - Red: Mock `_generate_embedding`, call `add_fact()`, assert_called_once
  - File: `nikita/memory/supabase_memory.py`

- [ ] T1.3: Write tests for embedding reuse
  - AC: 3 tests — single call, skip with param, backward compat without param
  - File: `tests/memory/test_embedding_reuse.py`

## Story 2: Batch Memory Search

- [ ] T2.1: Add `semantic_search_batch()` to `MemoryFactRepository`
  - AC: Single query with `graph_type = ANY(:types)` returns results across all types
  - Red: Call with 3 types → 1 SQL execution
  - File: `nikita/db/repositories/memory_fact_repository.py`

- [ ] T2.2: Refactor `search()` to use batch query
  - AC: `search(graph_types=["user", "relationship", "nikita"])` makes 1 DB call
  - Red: Mock repo, call search → `semantic_search_batch` called once
  - File: `nikita/memory/supabase_memory.py`

- [ ] T2.3: Write tests for batch search
  - AC: 3 tests — single call for multi-type, correct sorting, empty results
  - File: `tests/memory/test_batch_search.py`

## Story 3: Score Reconciliation

- [ ] T3.1: Add `reconcile_score()` to `UserRepository`
  - AC: Corrects user.relationship_score when drift > 0.01 from metrics composite
  - Red: Set metrics to 65.5 composite, user score to 64.2 → corrected to 65.5
  - File: `nikita/db/repositories/user_repository.py`

- [ ] T3.2: Wire reconciliation into decay job
  - AC: After decay processing, reconcile called for each processed user
  - Red: Mock decay + reconcile, run endpoint → reconcile called
  - File: `nikita/api/routes/tasks.py`

- [ ] T3.3: Write tests for score reconciliation
  - AC: 3 tests — corrects drift, ignores small drift, wired into decay
  - File: `tests/db/test_score_reconciliation.py`

## Story 4: Score History Composite Index

- [ ] T4.1: Apply Supabase migration for composite index
  - AC: Index `idx_score_history_user_time` exists on `(user_id, recorded_at DESC)`
  - Red: Query EXPLAIN shows sequential scan → after migration shows index scan
  - Tool: Supabase MCP `apply_migration`

- [ ] T4.2: Verify index usage with EXPLAIN ANALYZE
  - AC: Query plan shows Index Scan on idx_score_history_user_time
  - Tool: Supabase MCP `execute_sql`

---

**Total**: 10 tasks | **Estimated tests**: 12+
