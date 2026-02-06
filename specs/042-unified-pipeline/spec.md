# Spec 042: Unified Pipeline Refactor

## Status: SPECIFICATION COMPLETE

| Attribute | Value |
|-----------|-------|
| **Version** | 1.0.0 |
| **Created** | 2026-02-06 |
| **Status** | Ready for Implementation |
| **Dependencies** | Specs 039 (Context Engine), 037 (Pipeline Refactor), 029 (Context Comprehensive) |
| **Architecture Doc** | [docs-to-process/20260206-architecture-unified-pipeline-refactor.md](../../docs-to-process/20260206-architecture-unified-pipeline-refactor.md) |

---

## 1. Problem Statement

**Current State**: The Nikita codebase has accumulated severe architectural fragmentation through 41 specs of incremental development:

- **Three parallel prompt generation paths** (~5,400 lines):
  1. `MetaPromptService` v1 (1,918 lines) — LLM-based, fallback only
  2. `ContextEngine` v2 (8 collectors + Sonnet 4.5 generator + assembler) — production
  3. Voice `server_tools.py` (935 lines) — inline context loading, bypasses ContextEngine
- **Two post-processing pipelines** (~1,114 lines):
  1. `context/post_processor.py` (11 stages) — used by text agent
  2. `post_processing/pipeline.py` (8 steps) — legacy, used by voice agent
- **Neo4j/Graphiti adds 30-73s cold start latency** for what amounts to storing text strings with timestamps
- **Voice and text have diverged**: different context, different prompts, different history — breaking the "one person" illusion

**Desired State**: One clean pipeline that produces one pre-built system prompt consumed by both text and voice agents, backed entirely by Supabase.

**Business Impact**:
- Message latency: 85s → 2-5s (94% reduction)
- Prompt cost: ~$0.01/msg (Sonnet) → ~$0.001/pipeline (Haiku, async)
- Codebase: Delete ~11,000 lines of redundant/deprecated code
- Voice-text parity: Both agents share identical context
- Infrastructure: Single datastore (Supabase), no Neo4j

---

## 2. Functional Requirements

### FR-001: Memory Facts Table
The system SHALL store memory facts in a `memory_facts` Supabase table with pgVector embeddings (1536 dimensions via `text-embedding-3-small`), graph_type classification (user/relationship/nikita), confidence scoring, and supersedence tracking.

### FR-002: Ready Prompts Table
The system SHALL store pre-generated system prompts in a `ready_prompts` table with a unique index on (user_id, platform, is_current) ensuring at most one active prompt per user per platform.

### FR-003: Semantic Memory Search
The system SHALL implement `SupabaseMemory.search()` using pgVector cosine similarity (`<=>` operator) with IVFFlat indexing, supporting graph_type filtering and minimum confidence thresholds.

### FR-004: Memory Deduplication
The system SHALL detect duplicate facts (cosine similarity > 0.95) and update existing facts via supersedence rather than inserting duplicates.

### FR-005: Unified Pipeline Entry Point
The system SHALL provide `PipelineOrchestrator.process(conversation_id)` as a single entry point for all post-conversation processing, replacing both existing pipelines.

### FR-006: Sequential Pipeline Stages
The system SHALL execute 9 sequential stages with critical/non-critical classification:
- **Critical** (stop on failure): Extraction, MemoryUpdate
- **Non-critical** (log and continue): LifeSim, Emotional, GameState, Conflict, Touchpoint, Summary, PromptBuilder

### FR-007: Jinja2 Deterministic Prompt Rendering
The system SHALL use Jinja2 templates to render system prompts with 11 structured sections (Identity, Immersion, Platform, State, Relationship, Memory, Continuity, Inner Life, Psychology, Chapter, Vice) in <5ms.

### FR-008: Haiku Narrative Enrichment
The system SHALL optionally enrich Jinja2 output with Claude Haiku narrative transformation (~500ms, ~$0.001/call) that adds emotional coherence and variability without altering facts. Haiku failure SHALL fall back to raw Jinja2 output.

### FR-009: Text Agent Prompt Loading
The text agent SHALL read pre-built prompts from `ready_prompts` table (0ms generation, DB read only), falling back to on-the-fly generation if no prompt exists.

### FR-010: Voice Agent Context Loading
Voice `server_tools.get_context()` SHALL read from `ready_prompts` table (<100ms), replacing the current 935-line inline context loading.

### FR-011: Feature Flag Rollout
The system SHALL use `UNIFIED_PIPELINE_ENABLED` feature flag for gradual rollout (10% → 50% → 100%), with instant rollback by toggling flag off.

### FR-012: Neo4j Data Migration
The system SHALL provide a migration script to export all facts from 3 Neo4j graphs and import into `memory_facts` table, preserving graph_type, content, and timestamps.

### FR-013: Unified Pipeline Trigger
Both text (pg_cron `process-conversations`) and voice (ElevenLabs `call.ended` webhook) SHALL trigger the same `PipelineOrchestrator.process()`.

### FR-014: Fallback Prompt Generation
If no pre-built prompt exists for a user (new user, first message), the system SHALL generate a prompt on-the-fly using the same Jinja2+Haiku path and log a warning.

### FR-015: Dead Code Removal
After full migration, the system SHALL delete ~11,000 lines of deprecated code: `context_engine/`, `meta_prompts/`, `post_processing/`, `context/stages/`, `context/layers/`, `memory/graphiti_client.py`.

### FR-016: Row-Level Security
Both `memory_facts` and `ready_prompts` tables SHALL have RLS enabled with policies ensuring users can only access their own rows (`user_id = auth.uid()`). Service role access SHALL bypass RLS for pipeline processing.

### FR-017: Pipeline Health Endpoint
The system SHALL expose `GET /admin/pipeline/health` returning per-stage success rates, average timing, and error counts from the last 24h.

### FR-018: Embedding Integrity
The system SHALL require non-NULL embeddings on all active memory facts. If OpenAI embedding generation fails after 3 retries, the fact SHALL be stored with `is_active=FALSE` and flagged for retry.

---

## 3. Non-Functional Requirements

### NFR-001: Performance
| Metric | Before | Target |
|--------|--------|--------|
| Message latency (total) | 85s | 2-5s |
| Context collection | 27.5s (Neo4j cold) | 0s (pre-built) |
| Prompt generation | 2-5s (Sonnet LLM) | 0s (pre-built) |
| Pipeline processing | ~15s | 8-12s |
| Voice context load | 2-30s | <100ms |

### NFR-002: Token Budgets
| Platform | Pre-Enrichment | Post-Enrichment |
|----------|---------------|-----------------|
| Text | ~4,800 tokens | 5,500-6,500 tokens |
| Voice | ~1,500 tokens | 1,800-2,200 tokens |

### NFR-003: Cost Efficiency
- Pipeline prompt cost: ~$0.001/pipeline (Haiku) vs ~$0.01/msg (Sonnet)
- 90% cost reduction per message
- No Neo4j hosting costs ($0/mo vs potential scaling costs)

### NFR-004: Data Integrity
- Zero fact loss during Neo4j → Supabase migration
- Embedding quality parity (same model: text-embedding-3-small)
- 30-day Neo4j retention (paused, not deleted) for rollback

---

## 4. Architecture

### 4.1 Target Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    TARGET (Unified Pipeline)                      │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              RUNTIME: Agent Prompt Loading                  │  │
│  │  Text/Voice → ReadyPromptRepository.get_current()           │  │
│  │  Result: Pre-built prompt from ready_prompts table (0ms)    │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              ASYNC: Unified Pipeline (after conversation)   │  │
│  │                                                              │
│  │  Trigger: pg_cron OR voice webhook                          │
│  │           ↓                                                  │
│  │  PipelineOrchestrator.process(conversation_id)              │
│  │           ↓                                                  │
│  │  1. ExtractionStage     (LLM fact extraction)    CRITICAL   │
│  │  2. MemoryUpdateStage   (→ memory_facts)         CRITICAL   │
│  │  3. LifeSimStage        (wrap life_simulation/)             │
│  │  4. EmotionalStage      (wrap emotional_state/)             │
│  │  5. GameStateStage      (score + chapter + decay)           │
│  │  6. ConflictStage       (conflict evaluation)               │
│  │  7. TouchpointStage     (wrap touchpoints/)                 │
│  │  8. SummaryStage        (conversation summaries)            │
│  │  9. PromptBuilderStage  (Jinja2 + Haiku → ready_prompts)   │
│  │                                                              │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              STORAGE: Supabase Only                         │  │
│  │  memory_facts   (pgVector, replaces Neo4j)                  │  │
│  │  ready_prompts  (pre-built prompts, text + voice)           │  │
│  │  conversations  (shared history, both platforms)             │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 4.2 Module Structure

```
nikita/pipeline/                    # NEW: Unified pipeline
    __init__.py
    orchestrator.py                 # PipelineOrchestrator.process()
    models.py                       # PipelineContext, PipelineResult, StageResult
    stages/
        __init__.py
        extraction.py               # LLM entity/fact extraction
        memory_update.py            # Write to memory_facts via SupabaseMemory
        life_sim.py                 # Wrap nikita/life_simulation/
        emotional.py                # Wrap nikita/emotional_state/
        game_state.py               # Score + chapter + decay
        conflict.py                 # Conflict evaluation
        touchpoint.py               # Wrap nikita/touchpoints/
        summary.py                  # Conversation summaries
        prompt_builder.py           # Jinja2 + Haiku → ready_prompts
    templates/
        system_prompt.j2            # Text prompt (~4.8K tokens)
        voice_prompt.j2             # Voice prompt (~1.5K tokens)

nikita/memory/
    supabase_memory.py              # NEW: Replaces graphiti_client.py

nikita/db/models/
    memory_fact.py                  # NEW: SQLAlchemy model
    ready_prompt.py                 # NEW: SQLAlchemy model

nikita/db/repositories/
    memory_fact_repository.py       # NEW: pgVector semantic search
    ready_prompt_repository.py      # NEW: get_current_prompt()
```

### 4.3 Modules Kept (Wrapped by Pipeline Stages)

| Module | Tests | Pipeline Stage |
|--------|-------|----------------|
| `nikita/life_simulation/` | 212 | `stages/life_sim.py` |
| `nikita/emotional_state/` | 233 | `stages/emotional.py` |
| `nikita/touchpoints/` | 189 | `stages/touchpoint.py` |
| `nikita/engine/scoring/` | 60 | `stages/game_state.py` |
| `nikita/engine/chapters/` | 142 | `stages/game_state.py` |
| `nikita/engine/decay/` | 52 | `stages/game_state.py` |
| `nikita/engine/vice/` | 81 | Template reads vice profile |
| `nikita/engine/engagement/` | 179 | Template reads engagement state |
| `nikita/agents/text/history.py` | 23 | Still loads message history |
| `nikita/agents/text/token_budget.py` | 13 | Still manages token allocation |
| `nikita/onboarding/` | 231 | Separate flow, untouched |

### 4.4 Modules Deleted (After Migration, US-6)

| Path | Lines | Replaced By |
|------|-------|-------------|
| `nikita/context_engine/` | ~2,500 | `nikita/pipeline/` |
| `nikita/meta_prompts/` | ~1,918 | `nikita/pipeline/stages/prompt_builder.py` |
| `nikita/context/template_generator.py` | 541 | Jinja2 templates |
| `nikita/context/layers/` | ~1,600 | Jinja2 template sections |
| `nikita/context/post_processor.py` | 494 | `nikita/pipeline/orchestrator.py` |
| `nikita/context/stages/` | ~1,000 | `nikita/pipeline/stages/` |
| `nikita/post_processing/` | ~2,100 | `nikita/pipeline/orchestrator.py` |
| `nikita/memory/graphiti_client.py` | 451 | `nikita/memory/supabase_memory.py` |
| **Total** | **~11,000** | |

---

## 5. User Stories

### US-1: Database Foundation (P1)

**As a** system architect,
**I want** memory facts and pre-built prompts stored in Supabase,
**So that** we eliminate Neo4j dependency and support instant prompt retrieval.

**Acceptance Criteria**:
- AC-1.1: `memory_facts` table exists with columns: id, user_id, graph_type, fact, source, confidence, embedding (vector 1536), metadata, is_active, superseded_by, conversation_id, created_at, updated_at
- AC-1.2: `ready_prompts` table exists with columns: id, user_id, platform, prompt_text, token_count, context_snapshot, pipeline_version, generation_time_ms, is_current, conversation_id, created_at
- AC-1.3: IVFFlat index on memory_facts.embedding with vector_cosine_ops
- AC-1.4: Unique index on ready_prompts(user_id, platform) WHERE is_current = TRUE
- AC-1.5: RLS enabled on both tables with user_id = auth.uid() policy + service_role bypass
- AC-1.6: Composite index on memory_facts(user_id, created_at DESC) for temporal queries

### US-2: Memory Migration (P1)

**As a** developer,
**I want** a SupabaseMemory class that replaces Graphiti/Neo4j,
**So that** memory operations are faster and use a single datastore.

**Acceptance Criteria**:
- AC-2.1: `SupabaseMemory.add_fact()` inserts with OpenAI embedding, detects duplicates (similarity > 0.95)
- AC-2.2: `SupabaseMemory.search()` returns top-k facts by cosine similarity with graph_type filter
- AC-2.3: `SupabaseMemory.get_recent()` returns facts by created_at DESC with graph_type filter
- AC-2.4: Migration script exports all Neo4j facts and imports to memory_facts with embeddings

### US-3: Unified Pipeline Core (P1)

**As a** developer,
**I want** a single post-processing pipeline that wraps existing modules,
**So that** we have one code path for both text and voice.

**Acceptance Criteria**:
- AC-3.1: `PipelineOrchestrator.process(conversation_id)` executes 9 stages sequentially
- AC-3.2: Critical stage failure (Extraction, MemoryUpdate) stops pipeline, returns error
- AC-3.3: Non-critical stage failure logs error, continues to next stage
- AC-3.4: Pipeline completes in <12s with all stages, logging per-stage timing

### US-4: Prompt Generation (P1)

**As a** developer,
**I want** Jinja2 templates with optional Haiku enrichment,
**So that** prompts are fast, deterministic, cost-efficient, and narratively rich.

**Acceptance Criteria**:
- AC-4.1: Jinja2 template renders all 11 sections in <5ms
- AC-4.2: Text prompt: 5,500-6,500 tokens post-enrichment; Voice prompt: 1,800-2,200 tokens
- AC-4.3: Haiku enrichment adds narrative variability without altering facts (~500ms)
- AC-4.4: Haiku failure falls back to raw Jinja2 output (still complete and usable)

### US-5: Agent Integration (P2)

**As a** developer,
**I want** text and voice agents to read from ready_prompts,
**So that** prompt load time is 0ms instead of 27.5s.

**Acceptance Criteria**:
- AC-5.1: Text agent reads from `ready_prompts` via `ReadyPromptRepository.get_current(user_id, 'text')`
- AC-5.2: Voice `get_context()` reads from `ready_prompts` (<100ms, down from 2-30s)
- AC-5.3: Feature flag `UNIFIED_PIPELINE_ENABLED` controls rollout with instant rollback

### US-6: Dead Code Cleanup (P3)

**As a** maintainer,
**I want** deprecated modules deleted,
**So that** the codebase is clean and ~11,000 lines of dead code are removed.

**Acceptance Criteria**:
- AC-6.1: All deprecated modules deleted (context_engine/, meta_prompts/, post_processing/, context/stages/, context/layers/, memory/graphiti_client.py)
- AC-6.2: Neo4j dependencies removed from pyproject.toml (graphiti-core, neo4j)
- AC-6.3: Zero failing tests after cleanup (all tests rewritten or deleted)

---

## 6. Data Models

### 6.1 memory_facts

```sql
CREATE TABLE memory_facts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    graph_type TEXT NOT NULL CHECK (graph_type IN ('user', 'relationship', 'nikita')),
    fact TEXT NOT NULL,
    source TEXT DEFAULT 'conversation',
    confidence REAL DEFAULT 0.8 CHECK (confidence >= 0 AND confidence <= 1),
    embedding vector(1536) NOT NULL,
    metadata JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    superseded_by UUID REFERENCES memory_facts(id) ON DELETE SET NULL,
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_memory_facts_user_graph ON memory_facts(user_id, graph_type) WHERE is_active = TRUE;
CREATE INDEX idx_memory_facts_embedding ON memory_facts
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);
CREATE INDEX idx_memory_facts_created ON memory_facts(user_id, created_at DESC)
    WHERE is_active = TRUE;

-- RLS
ALTER TABLE memory_facts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "memory_facts_own_data" ON memory_facts
    FOR ALL USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
CREATE POLICY "memory_facts_service_role" ON memory_facts
    FOR ALL USING (auth.role() = 'service_role');
```

### 6.2 ready_prompts

```sql
CREATE TABLE ready_prompts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    platform TEXT NOT NULL CHECK (platform IN ('text', 'voice')),
    prompt_text TEXT NOT NULL,
    token_count INTEGER DEFAULT 0,
    context_snapshot JSONB DEFAULT '{}',
    pipeline_version TEXT DEFAULT 'v1',
    generation_time_ms REAL DEFAULT 0,
    is_current BOOLEAN DEFAULT TRUE,
    conversation_id UUID REFERENCES conversations(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_ready_prompts_current
    ON ready_prompts(user_id, platform) WHERE is_current = TRUE;
CREATE INDEX idx_ready_prompts_user_platform
    ON ready_prompts(user_id, platform);

-- RLS
ALTER TABLE ready_prompts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "ready_prompts_own_data" ON ready_prompts
    FOR ALL USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
CREATE POLICY "ready_prompts_service_role" ON ready_prompts
    FOR ALL USING (auth.role() = 'service_role');
```

---

## 7. Risk Assessment

### R-001: Data Loss During Migration (HIGH)
- **Risk**: Loss of memory facts when migrating Neo4j → Supabase
- **Mitigation**: Export to JSON first, validate counts, keep Neo4j paused 30 days
- **Rollback**: Resume Neo4j, toggle feature flag off

### R-002: Test Suite Breakage (HIGH)
- **Risk**: ~500 tests reference deleted modules (context_engine, meta_prompts)
- **Mitigation**: Phase cleanup last (US-6), keep both paths live during migration
- **Target**: 4000+ tests passing after full cleanup

### R-003: Jinja2 Template Quality (MEDIUM)
- **Risk**: Mechanical templates produce flat, un-engaging prompts compared to Sonnet-generated
- **Mitigation**: Haiku enrichment layer adds narrative texture; A/B test before full rollout
- **Fallback**: Increase Haiku token budget or revert to LLM generation

### R-004: pgVector Search Quality (MEDIUM)
- **Risk**: IVFFlat approximate search may miss relevant facts compared to Neo4j
- **Mitigation**: Same embedding model (text-embedding-3-small), tune lists parameter, benchmark against Neo4j results
- **Fallback**: Switch to HNSW index if IVFFlat insufficient

### R-005: Pipeline Timing (LOW)
- **Risk**: 9-stage pipeline exceeds 12s target
- **Mitigation**: Non-critical stages already run fast (thin wrappers), only Extraction + Haiku use LLM
- **Monitoring**: Per-stage timing logged, can parallelize non-critical stages later
