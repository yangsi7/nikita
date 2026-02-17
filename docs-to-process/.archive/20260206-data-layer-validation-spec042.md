# Data Layer Validation Report: Spec 042 – Unified Pipeline Refactor

**Spec:** `/Users/yangsim/Nanoleq/sideProjects/nikita/specs/042-unified-pipeline/`
**Status:** **FAIL** (5 CRITICAL, 4 HIGH findings)
**Timestamp:** 2026-02-06T00:00:00Z
**Validator:** Data Layer Validation Specialist

---

## Executive Summary

Spec 042 defines two new Supabase tables (`memory_facts` and `ready_prompts`) to replace Neo4j-based memory and enable fast prompt pre-building. The specification is **detailed and well-structured**, but **6 critical data layer gaps** must be resolved before implementation can proceed:

1. **CRITICAL:** RLS policies completely absent for both new tables
2. **CRITICAL:** IVFFlat index strategy undefined (existing code uses HNSW)
3. **CRITICAL:** No data integrity constraints for pgVector embeddings (type, NOT NULL)
4. **CRITICAL:** Foreign key cascade behavior incompletely specified
5. **HIGH:** Migration script (1.4.4) has no rollback plan or transaction guarantees
6. **HIGH:** No indexes on frequently-queried columns (user_id, platform, conversation_id)

All issues are **correctable and low-effort** (1-2 hours remediation). Spec content is strong; implementation can proceed once these technical details are clarified.

---

## Pass/Fail Criteria

| Criteria | Status | Notes |
|----------|--------|-------|
| CRITICAL findings | 1/6 | RLS policies missing entirely |
| HIGH findings | 4/6 | Index + migration gaps |
| MEDIUM findings | 0 | None |
| LOW findings | 0 | None |
| **Overall** | **FAIL** | Must resolve 5 CRITICAL + 4 HIGH before implementation |

---

## Validation Findings

### CRITICAL Findings

| Severity | Category | Issue | Location | Recommendation |
|----------|----------|-------|----------|----------------|
| **CRITICAL** | Row-Level Security | **RLS policies completely absent** for `memory_facts` and `ready_prompts` tables | Spec section 6 (Data Models) | Add RLS policy definitions to both tables. Example for `memory_facts`: `ALTER TABLE memory_facts ENABLE ROW LEVEL SECURITY; CREATE POLICY "Users see own facts" ON memory_facts FOR ALL USING (user_id = auth.uid());` Ensure service role bypasses (for pipeline processing). Add to migration 0009. |
| **CRITICAL** | Indexing Strategy | **IVFFlat vs HNSW conflict unresolved** — spec specifies IVFFlat (line 327: "USING ivfflat"), but existing `message_embeddings` table uses HNSW index (migration 0001:294) | Spec section 6.1 + migration 0001 | Clarify index choice: IVFFlat (better batch inserts, lower memory) vs HNSW (lower latency, smaller index). Recommendation: Use **IVFFlat** for `memory_facts` (bulk migration scenario), but document consistency requirement in implementation notes. Verify Supabase supports both (should). |
| **CRITICAL** | Data Integrity | **Embedding column lacks NOT NULL + type validation** — spec defines `embedding vector(1536)` (line 316) but doesn't mandate NOT NULL or clarify handling of NULL embeddings during semantic search | Spec section 6.1 (memory_facts definition) | Add constraint: `embedding vector(1536) NOT NULL` in AC-0.1.1. Update AC-1.3.3 (embedding generation) to mandate: "All facts must have embeddings; if generation fails after 3 retries, reject fact insertion." Document query behavior: does NULL embedding get skipped in cosine similarity or treated as zero vector? |
| **CRITICAL** | Foreign Key Relationships | **Cascade behavior incompletely specified** — `superseded_by` self-reference (line 319) lacks ON DELETE/UPDATE rules; `conversation_id` (line 320) has no action specified | Spec section 6.1 (Data Models), AC-0.1.1 | Specify: `superseded_by UUID REFERENCES memory_facts(id) ON DELETE SET NULL` (preserve chain if old fact deleted) and `conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE` (delete facts if conversation is removed). Update AC-0.3.2 and AC-0.3.3 to include ON DELETE/UPDATE clauses. |
| **CRITICAL** | Query Performance | **No indexes on frequently-searched columns** — `memory_facts` query patterns (FR-003, AC-0.5.1) require fast lookups on `user_id`, `graph_type`, `is_active`, but only composite index defined | Spec section 6.1 (memory_facts definition), line 325 | Add to AC-0.2.2: `CREATE INDEX idx_memory_facts_user_graph_active ON memory_facts(user_id, graph_type) WHERE is_active = TRUE;` Add to `ready_prompts` (AC-0.2.3): `CREATE INDEX idx_ready_prompts_user_platform ON ready_prompts(user_id, platform) WHERE is_current = TRUE;` (complements unique index). Verify composite index covers (user_id, graph_type, is_active) query pattern. |
| **CRITICAL** | Storage Schema | **Ready_prompts missing unique index details** — AC-0.2.3 defines unique index on `(user_id, platform) WHERE is_current = TRUE`, but doesn't clarify: what happens to old `is_current=TRUE` record when new prompt is inserted? What prevents race conditions? | Spec section 6.2, AC-0.6.2 (ReadyPromptRepository.set_current) | Clarify in AC-0.2.3: "Unique constraint prevents more than one `is_current=TRUE` per user per platform. Repository method `set_current()` must atomically update old record `is_current := FALSE` before inserting new record `is_current := TRUE`." Document: use `ON CONFLICT DO UPDATE` in upsert, or two-statement transaction with explicit locks. Add test case: concurrent set_current() calls must preserve constraint. |

### HIGH Findings

| Severity | Category | Issue | Location | Recommendation |
|----------|----------|-------|----------|----------------|
| **HIGH** | Migration Strategy | **Neo4j → Supabase migration script lacks transaction semantics & rollback** — AC-1.4.4 specifies validation (count match) but no atomic guarantee that all facts inserted successfully or all rolled back on failure | Plan section "Phase 1: Memory Migration", T1.4, AC-1.4.3/1.4.4 | Update migration script requirements: Wrap bulk insert in explicit transaction (BEGIN/COMMIT). Document rollback: if count validation fails, execute ROLLBACK (delete all inserted facts). Add success marker: set `neo4j_migration_completed_at` timestamp in users table only after commit succeeds. Update AC-1.4.4: "Validates count match within same transaction; if mismatch, ROLLBACK all inserts and log error for manual review." |
| **HIGH** | Index Strategy | **No performance targets for pgVector search latency** — FR-003 & NFR-001 specify <100ms overall context load, but no SLA for pgVector `<=>` operator latency alone | Spec sections 3 (FR) and 4 (NFR-001, table line 94-100) | Add performance benchmark to plan: "pgVector cosine similarity search (100 facts, IVFFlat lists=50) must complete in <50ms (p95)." Add acceptance criterion to Phase 1 tests: "SupabaseMemory.search() benchmark: 10-user dataset, 1000 facts each, <50ms p95." Document: if p95 exceeds 50ms, investigate lists parameter or switch to HNSW. |
| **HIGH** | Feature Flag Logic | **Fallback prompt generation path undefined for ready_prompts misses** — FR-014 specifies fallback if no pre-built prompt exists, but doesn't clarify: does it trigger async pipeline re-run? Or use existing ContextEngine path? | Spec section 2 (FR-014), line 84 | Clarify in FR-014: "If no pre-built prompt exists (new user, first message), generate on-the-fly using same Jinja2+Haiku path in PromptBuilderStage, store in ready_prompts, and log warning. Do NOT fall back to deprecated ContextEngine; always use new pipeline." Add timeout: "On-the-fly generation must complete in 5s; if exceeds, use minimal fallback prompt (identity + immersion only, ~500 tokens)." Document in AC-5.1 (agent integration tests). |
| **HIGH** | Data Integrity | **No explicit handling of embedding model mismatch** — spec assumes OpenAI `text-embedding-3-small` throughout (1536 dims), but no guard against accidental use of different model or dimension mismatch | Spec section 6.1 (line 316) + Phase 1 (T1.3, AC-1.3.1) | Add validation: MemoryFact model must enforce `embedding.shape == (1536,)` at insertion time. Update AC-1.3.1: "All embeddings must be generated via OpenAI text-embedding-3-small (1536 dims). Reject any embedding with different dimension; log error and skip fact." Add settings validation: on app startup, verify `settings.embedding_model == "text-embedding-3-small"` and raise error if changed without migration. Document: changing embedding model requires re-embedding all 3 Neo4j graphs (expensive operation). |

---

## Entity Inventory

| Entity | Attributes (Count) | PK | FK | RLS | Constraints | Notes |
|--------|-------------------|----|----|-----|-------------|-------|
| `memory_facts` | 14 | id (UUID) | user_id → users.id | **MISSING** | graph_type, confidence, is_active CHECK; superseded_by self-ref | **CRITICAL:** RLS policy required. **HIGH:** ON DELETE rules for FKs. IVFFlat index strategy. |
| `ready_prompts` | 10 | id (UUID) | user_id → users.id | **MISSING** | platform, is_current CHECK | **CRITICAL:** RLS policy required. Unique index on (user_id, platform) WHERE is_current=TRUE. |
| `users` | (existing) | id (UUID) | — | ✅ Exists | — | Relationships to memory_facts, ready_prompts via CASCADE. |
| `conversations` | (existing) | id (UUID) | user_id → users.id | ✅ Exists | — | memory_facts references via conversation_id (optional FK). |

---

## Relationship Map

```
┌─────────────────────────────────┐
│          users                  │ (existing, RLS enabled)
│  id (PK, UUID)                  │
│  relationship_score, chapter    │
└──────────┬──────────────────────┘
           │ 1
           │
           ├─────N────────────┬──────────────────────────────┐
           │                  │                              │
    ┌──────▼────────┐   ┌──────▼──────────┐    ┌───────▼────────────┐
    │ memory_facts  │   │ ready_prompts   │    │  conversations     │
    │               │   │                 │    │                    │
    │ id (UUID) PK  │   │ id (UUID) PK    │    │ id (UUID) PK       │
    │ user_id FK    │   │ user_id FK      │    │ user_id FK         │
    │ graph_type    │   │ platform        │    │ messages (JSONB)   │
    │ fact (TEXT)   │   │ prompt_text     │    │ started_at         │
    │ embedding*    │   │ is_current      │    │ ended_at           │
    │ confidence    │   │ token_count     │    │ conversation_id FK │
    │ is_active     │   │ generation_ms   │    │   (optional)       │
    │ superseded_by │   │ context_snap    │    └────────────────────┘
    │   (self-ref)  │   │ conversation_id │
    │ conversation  │   │   (optional FK) │
    │   (opt FK)    │   └─────────────────┘
    │               │
    │ IVFFlat index │
    │ on embedding* │
    └───────────────┘
    *vector(1536) — NO NOT NULL CONSTRAINT (CRITICAL)

    KEY MISSING:
    - RLS policies on memory_facts and ready_prompts (CRITICAL)
    - ON DELETE rules on FK self-references and optional FKs (CRITICAL)
    - Performance indexes on user_id, platform, graph_type (HIGH)
    - NOT NULL constraint on embedding (CRITICAL)
```

---

## RLS Policy Checklist

| Policy Requirement | Status | Details |
|-------------------|--------|---------|
| **memory_facts RLS enabled?** | ❌ **MISSING** | AC-0.1.1 does not include `ALTER TABLE memory_facts ENABLE ROW LEVEL SECURITY` |
| **memory_facts isolation rule** | ❌ **MISSING** | No policy defined; spec should include: "Users see own facts only via `user_id = auth.uid()`" |
| **memory_facts admin bypass** | ❌ **MISSING** | Service role (for pipeline processing) must bypass RLS; spec should note: "RLS bypassed for service role (Cloud Run backend)" |
| **ready_prompts RLS enabled?** | ❌ **MISSING** | AC-0.4.1 does not include RLS enable statement |
| **ready_prompts isolation rule** | ❌ **MISSING** | No policy; spec should include: "Users see own prompts only" |
| **ready_prompts admin bypass** | ❌ **MISSING** | Service role must bypass for pipeline writes |
| **Testing** | ❌ **NOT MENTIONED** | Spec should include: "RLS policies must be tested in E2E (user A cannot read user B's facts/prompts)" |

**Recommendation**: Add RLS section to **Phase 0 migration (T0.1 or new T0.7)**:

```sql
-- Enable RLS on new tables
ALTER TABLE memory_facts ENABLE ROW LEVEL SECURITY;
ALTER TABLE ready_prompts ENABLE ROW LEVEL SECURITY;

-- Allow users to read own facts
CREATE POLICY "Users see own memory facts" ON memory_facts
    FOR SELECT USING (user_id = auth.uid());

-- Allow users to read own prompts
CREATE POLICY "Users see own ready prompts" ON ready_prompts
    FOR SELECT USING (user_id = auth.uid());

-- Service role (Cloud Run) bypasses RLS for writes
-- (RLS bypassed by default for service_role via is_bypassed=TRUE in Supabase)
```

---

## Index Requirements

### memory_facts Indexes

| Table | Column(s) | Type | Status | Query Pattern | Recommendation |
|-------|-----------|------|--------|---------------|-----------------|
| `memory_facts` | `(user_id, graph_type) WHERE is_active=TRUE` | Composite | ✅ Defined (AC-0.2.2) | `get_by_user(user_id, graph_type)` | Keep as-is. Covers filtering. |
| `memory_facts` | `embedding` | IVFFlat | ⚠️ Specified but strategy unclear | `semantic_search(query_embedding)` with user_id filter | **CLARIFY**: IVFFlat (line 327) vs HNSW (existing pattern in message_embeddings). Recommend IVFFlat for bulk migration. Add lists=50 parameter. Test p95 latency <50ms. |
| `memory_facts` | `user_id` | Simple | ❌ **MISSING** | `get_recent(user_id, graph_type, hours)` | Add: `CREATE INDEX idx_memory_facts_user_id ON memory_facts(user_id);` Covers WHERE clause before composite. |
| `memory_facts` | `(user_id, created_at DESC) WHERE is_active=TRUE` | Composite | ❌ **MISSING** | `get_recent()` temporal query | Add: `CREATE INDEX idx_memory_facts_user_created ON memory_facts(user_id, created_at DESC) WHERE is_active=TRUE;` Enables efficient ordering. |

### ready_prompts Indexes

| Table | Column(s) | Type | Status | Query Pattern | Recommendation |
|-------|-----------|------|--------|---------------|-----------------|
| `ready_prompts` | `(user_id, platform) WHERE is_current=TRUE` | Unique | ✅ Defined (AC-0.2.3) | `get_current(user_id, platform)` | Keep. Prevents duplicates. |
| `ready_prompts` | `(user_id, platform)` | Composite | ❌ **MISSING** | `get_history(user_id, platform, limit)` | Add: `CREATE INDEX idx_ready_prompts_user_platform ON ready_prompts(user_id, platform);` Complements unique index for non-current queries. |
| `ready_prompts` | `conversation_id` | Simple | ❌ **MISSING** | (Future: audit trail via conversation_id) | Optional. Add if audit queries needed: `CREATE INDEX idx_ready_prompts_conversation ON ready_prompts(conversation_id);` |

**Summary**: Add 3 missing indexes (2 HIGH priority for ready_prompts, 1 HIGH for memory_facts temporal).

---

## Migration Strategy Validation

### Migration 0009 (Spec Phase 0, T0.1-T0.6)

| Aspect | Specification | Status | Issues | Recommendation |
|--------|---------------|--------|--------|-----------------|
| **Table creation** | CREATE memory_facts with 14 columns | ✅ Defined | CHECK constraints for graph_type, confidence OK | Verify: embedding type in Alembic (use `op.execute("ALTER TABLE memory_facts ADD COLUMN embedding vector(1536) NOT NULL")` pattern from migration 0001) |
| **pgVector setup** | `embedding vector(1536)` column + extension | ✅ Defined | **CRITICAL**: No `NOT NULL` constraint specified | Add: NOT NULL constraint. Verify pgVector extension enabled (should be from migration 0001). |
| **IVFFlat index** | CREATE INDEX on embedding with vector_cosine_ops | ✅ Defined | **CRITICAL**: IVFFlat vs HNSW choice unresolved | Clarify in plan: use IVFFlat with lists=50 (batch-optimized). Test latency. Update migration SQL. |
| **Unique index** | (user_id, platform) WHERE is_current=TRUE on ready_prompts | ✅ Defined | Clear + sufficient | No changes needed. |
| **RLS setup** | ALTER TABLE ENABLE ROW LEVEL SECURITY + policies | ❌ **NOT DEFINED** | CRITICAL gap | Add RLS enable + 2 policies (see RLS section above). |
| **FK cascades** | ON DELETE rules for user_id, conversation_id, superseded_by | ⚠️ Partially defined | AC-0.1.1 mentions FKs but not ON DELETE actions | Add: ON DELETE CASCADE for user_id, ON DELETE SET NULL for conversation_id and superseded_by. Clarify in AC-0.3.2/0.3.3. |

### Migration 1.4.4 (Phase 1: Neo4j Export Script)

| Aspect | Specification | Status | Issues | Recommendation |
|--------|---------------|--------|--------|-----------------|
| **Export from Neo4j** | Connect, fetch all facts from 3 graphs | ✅ Defined | None | Implement. Use existing `NikitaMemory.search_all()` or raw Cypher. |
| **Generate embeddings** | Batch embed facts via OpenAI API | ✅ Defined | Retry logic mentioned (AC-1.3.3) but not in migration script | Add: 3-retry loop with exponential backoff for embedding API calls. Skip facts on persistent failure. |
| **Bulk insert** | Insert all facts to memory_facts table | ⚠️ Defined | **HIGH**: No transaction guarantee or rollback strategy | Add: Wrap in `BEGIN; ... INSERT ... ; COMMIT;` Validate count after commit. If count mismatch, log error (don't auto-rollback; manual review). Update AC-1.4.4. |
| **Validate counts** | Compare Supabase count vs Neo4j count per graph_type | ✅ Defined | Implementation unclear | Implement: `SELECT COUNT(*) FROM memory_facts WHERE graph_type = $1;` Compare to Neo4j counts. Return exit code 0 (success) or 1 (failure) for scripting. |
| **Rollback strategy** | (Not specified) | ❌ **MISSING** | HIGH: If validation fails, how do we recover? | Add: "On count mismatch, operator manually reviews error log and can: (1) re-run migration, (2) export Neo4j facts to JSON for manual inspection, or (3) pause Neo4j (don't delete) and investigate." Document Neo4j pause for 30 days (per spec line 116). |

---

## Data Integrity Constraints

### memory_facts Constraints

| Constraint | Specification | Status | Implementation |
|-----------|---------------|--------|-----------------|
| **Primary key** | id UUID | ✅ Defined (AC-0.1.1) | `id UUID DEFAULT gen_random_uuid() PRIMARY KEY` |
| **user_id NOT NULL** | Required FK to users | ✅ Defined | `user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE` |
| **graph_type CHECK** | IN ('user', 'relationship', 'nikita') | ✅ Defined (AC-0.1.3) | `CHECK (graph_type IN ('user', 'relationship', 'nikita'))` |
| **fact NOT NULL** | Text content required | ✅ Defined | `fact TEXT NOT NULL` |
| **confidence CHECK** | 0 ≤ confidence ≤ 1 | ✅ Defined (spec 6.1) | `confidence REAL DEFAULT 0.8 CHECK (confidence >= 0 AND confidence <= 1)` |
| **embedding NOT NULL** | 1536-dim vector required | ❌ **MISSING** | Should be: `embedding vector(1536) NOT NULL` (currently nullable per spec) |
| **embedding dimension** | Exactly 1536 dims (OpenAI small) | ❌ **NOT ENFORCED** | Add validation at application layer: reject embeddings with != 1536 dims. See AC-1.3.1 clarification above. |
| **is_active DEFAULT** | Boolean flag, default TRUE | ✅ Defined | `is_active BOOLEAN DEFAULT TRUE` |
| **superseded_by FK** | Optional self-reference | ⚠️ Defined but incomplete | Should be: `superseded_by UUID REFERENCES memory_facts(id) ON DELETE SET NULL` (to preserve chain if old fact deleted) |
| **conversation_id FK** | Optional reference to conversations | ⚠️ Defined but incomplete | Should be: `conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE` (delete facts if source conversation removed) |
| **Unique constraint** | (None specified; facts can be similar) | ✅ Correct | Deduplication via similarity check (AC-1.2.2), not unique constraint. Good design. |

### ready_prompts Constraints

| Constraint | Specification | Status | Implementation |
|-----------|---------------|--------|-----------------|
| **Primary key** | id UUID | ✅ Defined (AC-0.4.1) | `id UUID DEFAULT gen_random_uuid() PRIMARY KEY` |
| **user_id NOT NULL** | Required FK to users | ✅ Defined | `user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE` |
| **platform CHECK** | IN ('text', 'voice') | ✅ Defined (AC-0.1.4) | `CHECK (platform IN ('text', 'voice'))` |
| **prompt_text NOT NULL** | Required | ✅ Defined | `prompt_text TEXT NOT NULL` |
| **token_count NOT NULL** | Numeric, default 0 | ✅ Defined (spec 6.2, line 338) | `token_count INTEGER DEFAULT 0` |
| **is_current NOT NULL** | Boolean, default TRUE | ✅ Defined | `is_current BOOLEAN DEFAULT TRUE` |
| **Unique (user_id, platform, is_current=TRUE)** | Only one active per user per platform | ✅ Defined (AC-0.2.3) | `CREATE UNIQUE INDEX idx_ready_prompts_current ON ready_prompts(user_id, platform) WHERE is_current = TRUE;` |
| **conversation_id FK** | Optional reference | ⚠️ Defined but incomplete | Should be: `conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE` |

---

## Supabase-Specific Checks

| Check | Status | Details |
|-------|--------|---------|
| **pgVector extension enabled?** | ✅ **YES** | Migration 0001 includes `CREATE EXTENSION IF NOT EXISTS vector`. Verified in existing codebase. |
| **IVFFlat index available?** | ⚠️ **NEEDS CLARIFICATION** | Supabase supports both IVFFlat and HNSW. Existing message_embeddings uses HNSW. Spec specifies IVFFlat. No conflict, but clarify which to use for consistency. |
| **RLS with auth.uid() function** | ✅ **Supported** | Supabase auth.uid() function works. Existing migrations (0002-0004) use it. Service role bypasses automatically. |
| **JSONB columns** | ✅ **Yes** | ready_prompts.context_snapshot uses JSONB. Supabase + PostgreSQL support. No issues. |
| **Async/await patterns for async SQLAlchemy** | ✅ **Yes** | Existing repos (generated_prompt_repository.py) use AsyncSession. Pattern established. |
| **RLS policies for new tables** | ❌ **MISSING** | Must be added in migration 0009 or separate. See RLS section above. |

---

## Summary of Actionable Fixes

### BEFORE Implementation (Must Fix)

| Priority | Item | Effort | Location | Action |
|----------|------|--------|----------|--------|
| **P0** | Add RLS policies for memory_facts and ready_prompts | 30min | Spec section 6, T0.1 migration | Define 4 policies: SELECT on each table, filtered by user_id = auth.uid() |
| **P0** | Clarify embedding NOT NULL constraint | 10min | Spec AC-0.1.1, AC-0.3.1 | Update: `embedding vector(1536) NOT NULL` + reject NULL in AC-1.3.3 |
| **P0** | Specify FK cascade behavior | 10min | Spec AC-0.1.1, AC-0.3.2, AC-0.3.3 | Document ON DELETE rules: CASCADE for user_id, SET NULL for optional FKs |
| **P1** | Clarify IVFFlat vs HNSW index choice | 15min | Spec section 4.3 (Design Decisions) | Add row: "Index type: IVFFlat (batch-optimized for migration)" + rationale |
| **P1** | Add missing performance indexes | 20min | Spec Phase 0, T0.2 | Add 3 indexes: user_id simple, (user_id, created_at) composite on memory_facts; (user_id, platform) on ready_prompts |
| **P1** | Update migration script with transaction semantics | 1h | Plan Phase 1, T1.4, AC-1.4.3 | Add: BEGIN/COMMIT, count validation within transaction, rollback + logging strategy |
| **P2** | Document fallback prompt generation | 15min | Spec FR-014 | Clarify: use Jinja2+Haiku, not ContextEngine; timeout 5s; minimal fallback at 5s limit |

### AFTER Implementation (Nice to Have)

- Add pgVector search latency benchmark (target: <50ms p95)
- Add embedding dimension validation at app layer
- Add "ready_prompts history" query index
- Document ready_prompts atomicity pattern (ON CONFLICT DO UPDATE or explicit locks)

---

## Verification Commands

```bash
# 1. Verify pgVector extension
psql -d supabase_db -c "SELECT extname FROM pg_extension WHERE extname = 'vector';"
# Expected: vector (already created by migration 0001)

# 2. Check existing indexes (before migration 0009)
psql -d supabase_db -c "\d message_embeddings"
# Should show: ix_message_embeddings_embedding using hnsw

# 3. After migration 0009, verify new tables
psql -d supabase_db -c "SELECT table_name FROM information_schema.tables WHERE table_name IN ('memory_facts', 'ready_prompts');"
# Expected: memory_facts, ready_prompts

# 4. Check RLS on new tables (after RLS migration is added)
psql -d supabase_db -c "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename IN ('memory_facts', 'ready_prompts');"
# Then: SELECT * FROM pg_policies WHERE tablename IN ('memory_facts', 'ready_prompts');
# Expected: 2 policies per table (SELECT for users, no write policies needed for now)

# 5. Verify IVFFlat index syntax
psql -d supabase_db -c "CREATE INDEX test_ivf ON memory_facts USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);"
# Should succeed after extension enabled
```

---

## Recommendations

### 1. Pre-Implementation Spec Clarifications (Do These First)

**Update spec.md, section 6 (Data Models)**:

```markdown
### 6.1 memory_facts (UPDATED)

```sql
CREATE TABLE memory_facts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    graph_type TEXT NOT NULL CHECK (graph_type IN ('user', 'relationship', 'nikita')),
    fact TEXT NOT NULL,
    source TEXT DEFAULT 'conversation',
    confidence REAL DEFAULT 0.8 CHECK (confidence >= 0 AND confidence <= 1),
    embedding vector(1536) NOT NULL,  -- ← CLARIFICATION: Added NOT NULL
    metadata JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    superseded_by UUID REFERENCES memory_facts(id) ON DELETE SET NULL,  -- ← CLARIFICATION: Added ON DELETE SET NULL
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,  -- ← CLARIFICATION: Added ON DELETE CASCADE
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS Setup (NEW SECTION)
ALTER TABLE memory_facts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users see own facts" ON memory_facts
    FOR SELECT USING (user_id = auth.uid());

-- Indexes (UPDATED: added missing indexes)
CREATE INDEX idx_memory_facts_user ON memory_facts(user_id);
CREATE INDEX idx_memory_facts_user_graph ON memory_facts(user_id, graph_type) WHERE is_active = TRUE;
CREATE INDEX idx_memory_facts_created ON memory_facts(user_id, created_at DESC) WHERE is_active = TRUE;
CREATE INDEX idx_memory_facts_embedding ON memory_facts
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);
```

**And update ready_prompts similarly** with RLS + missing composite index.

### 2. Update Migration 0009 (Phase 0, T0.1)

Add to spec/042/tasks.md T0.1:

```markdown
AC-0.1.5: embedding column includes NOT NULL constraint
AC-0.1.6: superseded_by and conversation_id FKs include ON DELETE rules (SET NULL and CASCADE)
AC-0.1.7: RLS enabled on both tables with SELECT policies for auth.uid() filtering
```

### 3. Update Phase 1 Migration Script (T1.4)

Clarify AC-1.4.3 and AC-1.4.4:

```markdown
AC-1.4.3: Bulk insert wrapped in explicit transaction (BEGIN...COMMIT)
AC-1.4.4: Count validation occurs within transaction; on mismatch, manual review required (log error, don't auto-rollback)
AC-1.4.5: (NEW) Document rollback: "Keep Neo4j paused 30 days; on issues, can export Neo4j facts to JSON and re-import manually"
```

### 4. Test Coverage Additions

Update tasks.md Phase 0 tests (AC-0.5, AC-0.6):

```markdown
AC-0.5.6: RLS test — user A cannot query memory_facts for user B
AC-0.5.7: Embedding NOT NULL validation — inserting NULL embedding is rejected
AC-0.6.4: Ready prompt unique constraint test — duplicate (user_id, platform, is_current=TRUE) rejected
AC-0.6.5: Ready prompt atomic update test — concurrent set_current() calls preserve uniqueness
```

### 5. Implementation Checklist (Before T0.1 Starts)

- [ ] Review and approve updated Data Models section (6.1, 6.2)
- [ ] Approve RLS policy definitions (add to migration 0009)
- [ ] Confirm IVFFlat index choice (lists=50 parameter)
- [ ] Approve foreign key ON DELETE rules
- [ ] Verify pgVector extension is enabled (migration 0001 confirms yes)
- [ ] Plan Neo4j export script rollback strategy

---

## Conclusion

**Spec 042 is well-structured and mostly complete at the business logic level.** The data layer gaps are technical but straightforward to fix:

- **6 CRITICAL issues** (RLS, embeddings, cascades, indexes) — all correctable in 1-2 hours
- **4 HIGH issues** (migration atomicity, feature flag clarity, performance targets) — documentation/testing additions
- **0 MEDIUM/LOW issues** — no design flaws

**Recommendation: CONDITIONAL PASS**

Spec can proceed to implementation **if these 6 pre-implementation fixes are applied to spec.md and tasks.md first**. The fixes don't change architecture; they clarify PostgreSQL-specific details that are standard for Supabase.

**Estimated fix time: 2-3 hours** (spec updates + migration rewrite)
**Estimated implementation time (unchanged): ~39 tasks, ~440 tests, ~6 weeks**

---

## References

- **Spec:** `/Users/yangsim/Nanoleq/sideProjects/nikita/specs/042-unified-pipeline/spec.md`
- **Plan:** `/Users/yangsim/Nanoleq/sideProjects/nikita/specs/042-unified-pipeline/plan.md`
- **Tasks:** `/Users/yangsim/Nanoleq/sideProjects/nikita/specs/042-unified-pipeline/tasks.md`
- **Existing models:** `/Users/yangsim/Nanoleq/sideProjects/nikita/nikita/db/models/`
- **Existing migrations:** `/Users/yangsim/Nanoleq/sideProjects/nikita/nikita/db/migrations/versions/`
- **Supabase RLS docs:** https://supabase.com/docs/guides/auth/row-level-security
- **pgVector IVFFlat docs:** https://github.com/pgvector/pgvector#ivfflat

---

**Report prepared by:** Data Layer Validation Specialist
**Date:** 2026-02-06
