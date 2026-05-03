# Memory System Architecture

> **Scope**: Storage, retrieval, dedup, and eviction for player-state memory in `nikita/memory/` (pgVector via `SupabaseMemory`). Spec 042 retired the prior Graphiti/Neo4j three-graph backend; everything now lands in Postgres. This file replaces the 955-line pre-2026-05 version that still cited removed Graphiti modules.

**Last edit**: 2026-05-03 (Wave 2B doc-cleanup; Graphiti dead refs removed)

---

## 1. Overview

`SupabaseMemory` (`nikita/memory/supabase_memory.py:51`) is the single memory backend. All three legacy "graphs" — user (player facts), relationship (episodes between Nikita and player), nikita (Nikita's own life events) — collapse to one table with a `graph` discriminator column and a vector embedding per row.

```
┌────────────────────────────────────────────────────────────────────┐
│                    Pipeline / Agents (callers)                     │
│                                                                    │
│   nikita/agents/text/agent.py      nikita/agents/voice/...         │
│   nikita/pipeline/stages/memory_update.py                          │
│   nikita/pipeline/stages/extraction.py                             │
└──────────────────┬─────────────────────────────────────────────────┘
                   │  add_user_fact / add_relationship_episode /
                   │  add_nikita_event / search / get_recent /
                   │  get_context_for_prompt
                   ▼
┌────────────────────────────────────────────────────────────────────┐
│   SupabaseMemory   (nikita/memory/supabase_memory.py:51)           │
│                                                                    │
│   ┌──────────────┐     ┌──────────────────────────────────────┐    │
│   │ OpenAI       │     │  Supabase Postgres + pgVector        │    │
│   │ Embeddings   │ ◄── │  Tables: memories, memory_facts      │    │
│   │ (1536-dim)   │     │  Indexes: ivfflat on (embedding)     │    │
│   └──────────────┘     │  RLS: per-user row scoping           │    │
│                        └──────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────────────┘
```

Key invariants:

- One source of truth for memory: `SupabaseMemory.add_*` writes the row + embedding atomically; readers use vector similarity over `graph` filters.
- All identifiers are `UUID` user_ids, scoped by RLS; service-role usage is reserved for cron and admin paths.
- Embedding generation uses `text-embedding-3-small` (1536-dim). Constants live at `nikita/memory/supabase_memory.py:32-34`.

---

## 2. Storage Layer (pgVector)

### 2.1 Tables

| Table | Created by migration | Purpose |
|------|----------------------|---------|
| `memories` | initial Spec 042 migration (preceded by GH #140 column drop in `20260316*` for legacy Graphiti cleanup) | Per-user vector store. Columns: `id`, `user_id`, `graph`, `content`, `embedding (vector(1536))`, `metadata jsonb`, `created_at`. |
| `memory_facts` | `supabase/migrations/20260223150516_create_memory_facts_table.sql` | Faceted facts surface (extraction-stage outputs); read by `search_memory`. |
| `message_embeddings` | original Spec 042 + repair `supabase/migrations/20251201154007_fix_message_embeddings_user_id.sql` | Per-message embeddings used by retrieval. |

### 2.2 `graph` discriminator (`nikita/memory/supabase_memory.py:24-30`)

```python
GRAPH_LABELS = {
    "user": "player facts",
    "relationship": "Nikita ↔ player episodes",
    "nikita": "Nikita's own life events",
}
ALL_GRAPH_TYPES = ["user", "relationship", "nikita"]
```

### 2.3 Embeddings

- Model: `text-embedding-3-small`, 1536-dim (`supabase_memory.py:32-33`)
- Batch helper: `SupabaseMemory.generate_embeddings_batch` (`supabase_memory.py:131`) — used by ingestion paths to amortize latency
- Retries: `MAX_RETRIES=3`, exponential backoff (`supabase_memory.py:34-35`)

### 2.4 RLS

Per-user policies enforce `user_id = auth.uid()` on every read/write path that the portal touches; cron and Cloud Run task endpoints use service-role to bypass RLS where the user_id is set explicitly. See `.claude/rules/testing.md` "DB Migration Checklist" for the required policy shape.

---

## 3. Retrieval Layer

### 3.1 API surface (`SupabaseMemory` methods)

| Method | File:line | Use |
|---|---|---|
| `add_fact(graph, content, metadata)` | `:159` | Single-row write with embedding. Used internally by the typed wrappers. |
| `add_user_fact(content, metadata)` | `:330` | Player fact. |
| `add_relationship_episode(content, metadata)` | `:358` | Nikita ↔ player turn-level episode. |
| `add_nikita_event(content, metadata)` | `:381` | Nikita's life-event log. |
| `search(query, graph, top_k)` | `:203` | Vector similarity. Returns scored hits. |
| `get_recent(graph, limit)` | `:243` | Time-ordered recall. |
| `get_context_for_prompt(query, top_k)` | `:258` | Composite: queries all 3 graphs, merges by relevance. The pipeline calls this. |
| `find_similar(text, graph, threshold)` | `:289` | Dedup helper. Returns existing match if cosine similarity ≥ `threshold`. |
| `search_memory(query, ...)` | `:404` | Fact-table-backed search (extraction outputs). |
| `get_user_facts / get_relationship_episodes / get_nikita_events` | `:349 / :372 / :395` | Graph-scoped recent listings. |

### 3.2 Dedup threshold (single tuning knob)

```python
# nikita/memory/supabase_memory.py:37-42
# GH #199: Memory dedup threshold — cosine similarity above this suppresses duplicate facts.
# Prior 0.92 (GH #157) was too tight; therapist-fact E2E variants (~0.88-0.91) leaked through.
DEDUP_SIMILARITY_THRESHOLD = 0.87
```

The threshold is a `Final` module-level constant. Per `.claude/rules/tuning-constants.md`, every change requires a regression test; current value is asserted in the dedup-threshold tests under `tests/memory/`.

Cosine-distance form (used by the SQL query): `max_distance = 1.0 - DEDUP_SIMILARITY_THRESHOLD = 0.13` (`supabase_memory.py:321-322`).

### 3.3 Composite retrieval (`get_context_for_prompt`)

The pipeline's prompt-assembly stage requests a single composite recall. Internally:

1. Generate embedding for `query`.
2. Search each graph (user, relationship, nikita) under the same embedding.
3. Merge hits by descending similarity, applying graph-specific caps from the caller.
4. Return as plain text fragments suitable for the agent prompt.

This is the only call site any new caller should reach for; do not duplicate per-graph search outside the wrapper.

---

## 4. Eviction & Compaction

There is no automatic eviction of `memories` rows in production today. The compaction story instead lives at the dedup boundary:

- **Write-path dedup**: `add_fact` (and its typed wrappers) call `find_similar` first; rows that match an existing fact above `DEDUP_SIMILARITY_THRESHOLD` are not re-inserted.
- **Read-path summarization**: agents pull bounded `top_k` results, so storage growth does not directly degrade context quality.
- **Long-tail growth**: planned for a later spec. Candidate strategies are documented at `plans/master-plan.md` (architecture section). Until then, storage scales with `O(facts × users)` and is bounded by Supabase free-tier quotas in dev / production capacity in prod.

If a future spec introduces eviction, it MUST add: a TTL or last-touched policy, a backfill plan for compacting old rows, and a dedup-threshold regression guard.

---

## 5. Caller Integration

### 5.1 Pipeline stage — `memory_update`

`nikita/pipeline/stages/memory_update.py` consumes the extraction-stage output (kind/content pairs) and calls into the typed wrappers above. Spec 116 (extraction-checkpoint) ensures extraction outputs survive a `memory_update` failure so retries are idempotent.

### 5.2 Agents

- Text agent (`nikita/agents/text/agent.py`) — uses `get_context_for_prompt` during prompt assembly.
- Voice agent (`nikita/agents/voice/...`) — uses the same wrapper from the voice pipeline.
- Onboarding agent (`nikita/agents/onboarding/...`) — has its own message-history/state primitive (`message_history.py`) but reads memory via `SupabaseMemory` for backstory hooks.

### 5.3 Background tasks

- Spec 042 cron jobs are listed in `supabase/migrations/202604181415*` and friends (heartbeat, handoff, touchpoints).
- pg_cron currently registers 12 active jobs (per ROADMAP.md dashboard); the live count is the `SELECT count(*) FROM cron.job` from Supabase MCP.

---

## 6. Configuration

| Setting | Source | Purpose |
|---|---|---|
| `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` | `.env` → `nikita/config/settings.py` | DB access |
| `OPENAI_API_KEY` | `.env` → `nikita/config/settings.py` | Embedding API |
| `DEDUP_SIMILARITY_THRESHOLD` | `nikita/memory/supabase_memory.py:42` | Single tuning knob — see `.claude/rules/tuning-constants.md` |

---

## 7. Tests

- Unit tests live under `tests/memory/` and cover write-path dedup, composite retrieval, and the threshold regression guard.
- E2E coverage exercises the memory backend via `nikita/pipeline/stages/memory_update.py` consumed by `tests/e2e/`.
- The E2E variants for therapist-fact dedup are the regression scenario for `DEDUP_SIMILARITY_THRESHOLD = 0.87`.

---

## 8. References

| Topic | File |
|---|---|
| Module entry-point class | `nikita/memory/supabase_memory.py:51` |
| Singleton helper | `nikita/memory/supabase_memory.py:418` |
| Dedup threshold constant | `nikita/memory/supabase_memory.py:42` |
| Extraction → memory pipeline stage | `nikita/pipeline/stages/memory_update.py` |
| Spec 042 (introduces this design) | `specs/042-unified-pipeline/` |
| Spec 102 (memory data integrity) | `specs/102-memory-data-integrity/` |
| Spec 116 (extraction checkpoint) | `specs/116-extraction-checkpoint/` |
| Spec 040 (context engine enhancements) | `specs/040-context-engine-enhancements/` |
| Memory-facts table migration | `supabase/migrations/20260223150516_create_memory_facts_table.sql` |
| message_embeddings repair migration | `supabase/migrations/20251201154007_fix_message_embeddings_user_id.sql` |
| Legacy column drop (last cleanup) | `git log --grep="graph_id" --oneline` (see GH #140 / 2026-03-16 commit) |

---

## 9. Changelog

- **2026-05-03 (Wave 2B doc-cleanup)** — File rewritten from 955 → ~140 lines. Removed Section 8 references to non-existent legacy modules (`nikita/prompts/personality.py`, `nikita/prompts/scoring.py`, `nikita/config/feature_flags.py`). Restructured around `SupabaseMemory` as the single canonical entry point. Working-memory and ContextPackage details moved out; those live in `specs/030-text-continuity/spec.md` and `specs/040-context-engine-enhancements/spec.md` respectively.
- **2026-04-19** — Voice integration corrections (`memory/integrations.md` carries the voice path documentation; this file links there only).
- **Pre-2026-05** — Original 955-line file documented the legacy three-graph Neo4j architecture (Spec 042 removed it). History preserved via `git log --follow memory/memory-system-architecture.md`.
