# Spec 042: Unified Pipeline Refactor - Tasks

**Status**: IN PROGRESS
**Total Tasks**: 45
**Completed**: 14

---

## Summary

| Phase | User Story | Tasks | Est. Tests | Status |
|-------|-----------|-------|------------|--------|
| Phase 0 | US-1: Database Foundation | T0.1-T0.8 | 45 | **COMPLETE** (43 pass, 10 skip) |
| Phase 1 | US-2: Memory Migration | T1.1-T1.6 | 40 | **COMPLETE** (38 pass) |
| Phase 2 | US-3: Pipeline Core | T2.1-T2.12 | 80 | Pending |
| Phase 3 | US-4: Prompt Generation | T3.1-T3.5 | 45 | Pending |
| Phase 4 | US-5: Agent Integration | T4.1-T4.6 | 50 | Pending |
| Phase 5 | US-6: Cleanup | T5.1-T5.5 | 200 | Pending |
| Cross | E2E + Test Infra | TX.1-TX.3 | 40 | Pending |
| **Total** | | **45** | **~500** | |

---

## Phase 0: Database Foundation (US-1)

### T0.1: Create Alembic Migration 0009
- **Status**: [x] Complete
- **Effort**: 1-2h
- **Files**: `nikita/db/migrations/versions/20260206_0009_unified_pipeline_tables.py`
- **ACs**:
  - [x] AC-0.1.1: `memory_facts` table created with all columns (id, user_id, graph_type, fact, source, confidence, embedding vector(1536), metadata, is_active, superseded_by, conversation_id, created_at, updated_at)
  - [x] AC-0.1.2: `ready_prompts` table created with all columns (id, user_id, platform, prompt_text, token_count, context_snapshot, pipeline_version, generation_time_ms, is_current, conversation_id, created_at)
  - [x] AC-0.1.3: `graph_type` CHECK constraint enforces ('user', 'relationship', 'nikita')
  - [x] AC-0.1.4: `platform` CHECK constraint enforces ('text', 'voice')

### T0.2: Create IVFFlat + Unique Indexes
- **Status**: [x] Complete
- **Effort**: 30min
- **Files**: Same migration file as T0.1
- **ACs**:
  - [x] AC-0.2.1: IVFFlat index on `memory_facts.embedding` with `vector_cosine_ops` and `lists=50`
  - [x] AC-0.2.2: Composite index on `memory_facts(user_id, graph_type)` WHERE `is_active = TRUE`
  - [x] AC-0.2.3: Unique index on `ready_prompts(user_id, platform)` WHERE `is_current = TRUE`

### T0.3: Create MemoryFact SQLAlchemy Model
- **Status**: [x] Complete
- **Effort**: 1h
- **Files**: `nikita/db/models/memory_fact.py`, `nikita/db/models/__init__.py`
- **ACs**:
  - [x] AC-0.3.1: MemoryFact model with all columns mapped, including `Vector(1536)` for embedding
  - [x] AC-0.3.2: Relationship to `users` table (ForeignKey, cascade delete)
  - [x] AC-0.3.3: Relationship to `conversations` table (ForeignKey, nullable)
  - [x] AC-0.3.4: Self-referential relationship for `superseded_by`

### T0.4: Create ReadyPrompt SQLAlchemy Model
- **Status**: [x] Complete
- **Effort**: 45min
- **Files**: `nikita/db/models/ready_prompt.py`, `nikita/db/models/__init__.py`
- **ACs**:
  - [x] AC-0.4.1: ReadyPrompt model with all columns mapped
  - [x] AC-0.4.2: `context_snapshot` as JSONB type
  - [x] AC-0.4.3: Relationship to `users` and `conversations`

### T0.5: Create MemoryFactRepository
- **Status**: [x] Complete
- **Effort**: 3-4h
- **Files**: `nikita/db/repositories/memory_fact_repository.py`
- **ACs**:
  - [x] AC-0.5.1: `semantic_search(user_id, query_embedding, graph_type, limit, min_confidence)` uses pgVector `<=>` operator
  - [x] AC-0.5.2: `add_fact(user_id, fact, graph_type, embedding, source, confidence, metadata)` inserts new fact
  - [x] AC-0.5.3: `get_recent(user_id, graph_type, limit, hours)` returns by `created_at DESC`
  - [x] AC-0.5.4: `deactivate(fact_id, superseded_by_id)` sets `is_active=FALSE`
  - [x] AC-0.5.5: `get_by_user(user_id, graph_type, active_only)` returns all facts for a user

### T0.6: Create ReadyPromptRepository
- **Status**: [x] Complete
- **Effort**: 2h
- **Files**: `nikita/db/repositories/ready_prompt_repository.py`
- **ACs**:
  - [x] AC-0.6.1: `get_current(user_id, platform)` returns active prompt or None
  - [x] AC-0.6.2: `set_current(user_id, platform, prompt_text, token_count, context_snapshot, pipeline_version, generation_time_ms, conversation_id)` deactivates old prompt and inserts new
  - [x] AC-0.6.3: `get_history(user_id, platform, limit)` returns past prompts

### T0.7: Add RLS Policies
- **Status**: [x] Complete
- **Effort**: 30min
- **Files**: Same migration file as T0.1
- **ACs**:
  - [x] AC-0.7.1: RLS enabled on `memory_facts` with `user_id = auth.uid()` policy
  - [x] AC-0.7.2: RLS enabled on `ready_prompts` with `user_id = auth.uid()` policy
  - [x] AC-0.7.3: `service_role` bypass policy on both tables (for pipeline processing)

### T0.8: RLS Integration Tests
- **Status**: [x] Complete
- **Effort**: 2h
- **Files**: `tests/db/integration/test_rls_pipeline_tables.py`
- **ACs**:
  - [x] AC-0.8.1: User A cannot read User B's memory_facts
  - [x] AC-0.8.2: User A cannot read User B's ready_prompts
  - [x] AC-0.8.3: Service role can read/write all rows
  - [x] AC-0.8.4: 10 RLS tests passing

---

## Phase 1: Memory Migration (US-2)

### T1.1: Create SupabaseMemory Class
- **Status**: [x] Complete
- **Effort**: 4-5h
- **Files**: `nikita/memory/supabase_memory.py`
- **ACs**:
  - [x] AC-1.1.1: `SupabaseMemory.__init__(session, embedding_client)` accepts async session + OpenAI client
  - [x] AC-1.1.2: `add_fact(user_id, fact, graph_type, source, confidence, metadata)` generates embedding + inserts
  - [x] AC-1.1.3: `search(user_id, query, graph_types, limit, min_confidence)` embeds query + pgVector cosine search
  - [x] AC-1.1.4: `get_recent(user_id, graph_type, limit, hours)` temporal query

### T1.2: Implement Duplicate Detection
- **Status**: [x] Complete
- **Effort**: 2-3h
- **Files**: `nikita/memory/supabase_memory.py`
- **ACs**:
  - [x] AC-1.2.1: `find_similar(user_id, text, threshold=0.95)` finds near-duplicate facts
  - [x] AC-1.2.2: If similar fact exists, `add_fact()` supersedes old instead of inserting duplicate
  - [x] AC-1.2.3: Superseded fact has `is_active=FALSE` and `superseded_by` pointing to new fact

### T1.3: Implement Embedding Generation
- **Status**: [x] Complete
- **Effort**: 2h
- **Files**: `nikita/memory/supabase_memory.py`
- **ACs**:
  - [x] AC-1.3.1: Uses OpenAI `text-embedding-3-small` (1536 dims) via `settings.openai_api_key`
  - [x] AC-1.3.2: Batch embedding support for migration (up to 100 texts per call)
  - [x] AC-1.3.3: Retry 3x with exponential backoff (1s, 2s, 4s), 30s timeout per call
  - [x] AC-1.3.4: On persistent failure: raises EmbeddingError with details

### T1.4: Create Neo4j → Supabase Migration Script
- **Status**: [x] Complete
- **Effort**: 4-5h
- **Files**: `scripts/migrate_neo4j_to_supabase.py`
- **ACs**:
  - [x] AC-1.4.1: Connects to Neo4j, exports all facts from 3 graphs (user, relationship, nikita)
  - [x] AC-1.4.2: Generates embeddings for all exported facts
  - [x] AC-1.4.3: Bulk inserts to `memory_facts` table
  - [x] AC-1.4.4: Validates: count of facts in Supabase matches Neo4j per graph_type

### T1.5: Update Memory Module Exports
- **Status**: [x] Complete
- **Effort**: 30min
- **Files**: `nikita/memory/__init__.py`
- **ACs**:
  - [x] AC-1.5.1: Exports `SupabaseMemory` alongside existing `NikitaMemory`
  - [x] AC-1.5.2: Deprecation warning on `NikitaMemory` import

### T1.6: SupabaseMemory Test Suite
- **Status**: [x] Complete
- **Effort**: 4-5h
- **Files**: `tests/memory/test_supabase_memory.py`
- **ACs**:
  - [x] AC-1.6.1: 15 tests for `add_fact` (insert, update, confidence, metadata, graph_type)
  - [x] AC-1.6.2: 15 tests for `search` (similarity ranking, graph filter, limit, min_confidence)
  - [x] AC-1.6.3: 10 tests for dedup, `get_recent`, error handling

---

## Phase 2: Pipeline Core (US-3)

### T2.1: Create PipelineContext and PipelineResult Models
- **Status**: [ ] Pending
- **Effort**: 2h
- **Files**: `nikita/pipeline/models.py`
- **ACs**:
  - [ ] AC-2.1.1: `PipelineContext` holds conversation, user, metrics, vices, engagement, stage results, timing
  - [ ] AC-2.1.2: `PipelineResult` holds success/failure, context, error info, total duration
  - [ ] AC-2.1.3: `StageResult` holds success, data dict, errors list, duration_ms

### T2.2: Create PipelineOrchestrator
- **Status**: [ ] Pending
- **Effort**: 4-5h
- **Files**: `nikita/pipeline/orchestrator.py`
- **ACs**:
  - [ ] AC-2.2.1: `process(conversation_id, session)` runs 9 stages sequentially
  - [ ] AC-2.2.2: Critical stage failure stops pipeline, returns PipelineResult with error
  - [ ] AC-2.2.3: Non-critical stage failure logs error, continues to next stage
  - [ ] AC-2.2.4: Per-stage timing logged in PipelineContext.stage_timings
  - [ ] AC-2.2.5: Job execution logged in `job_executions` table

### T2.3: Create ExtractionStage (CRITICAL)
- **Status**: [ ] Pending
- **Effort**: 3-4h
- **Files**: `nikita/pipeline/stages/extraction.py`
- **ACs**:
  - [ ] AC-2.3.1: Uses Pydantic AI to extract entities/facts/threads/thoughts from conversation
  - [ ] AC-2.3.2: Output stored in PipelineContext.extracted_facts, .extracted_threads, .extracted_thoughts
  - [ ] AC-2.3.3: Port extraction logic from `nikita/context/stages/extraction.py`
  - [ ] AC-2.3.4: Timeout: 30s, retry: 2x

### T2.4: Create MemoryUpdateStage (CRITICAL)
- **Status**: [ ] Pending
- **Effort**: 2-3h
- **Files**: `nikita/pipeline/stages/memory_update.py`
- **ACs**:
  - [ ] AC-2.4.1: Writes extracted facts to `memory_facts` via `SupabaseMemory.add_fact()`
  - [ ] AC-2.4.2: Deduplicates against existing facts (similarity > 0.95)
  - [ ] AC-2.4.3: Classifies facts into graph_type (user/relationship/nikita)

### T2.5: Create LifeSimStage
- **Status**: [ ] Pending
- **Effort**: 1-2h
- **Files**: `nikita/pipeline/stages/life_sim.py`
- **ACs**:
  - [ ] AC-2.5.1: Wraps `nikita/life_simulation/` — calls existing simulator
  - [ ] AC-2.5.2: Stores generated events in PipelineContext
  - [ ] AC-2.5.3: Non-critical: logs error on failure, continues

### T2.6: Create EmotionalStage
- **Status**: [ ] Pending
- **Effort**: 1-2h
- **Files**: `nikita/pipeline/stages/emotional.py`
- **ACs**:
  - [ ] AC-2.6.1: Wraps `nikita/emotional_state/computer.py` — computes 4D mood
  - [ ] AC-2.6.2: Stores emotional state in PipelineContext
  - [ ] AC-2.6.3: Non-critical: logs error on failure, continues

### T2.7: Create GameStateStage
- **Status**: [ ] Pending
- **Effort**: 2-3h
- **Files**: `nikita/pipeline/stages/game_state.py`
- **ACs**:
  - [ ] AC-2.7.1: Calls ScoreCalculator to compute score deltas
  - [ ] AC-2.7.2: Calls ChapterStateMachine to check chapter transitions
  - [ ] AC-2.7.3: Calls DecayProcessor to apply decay if needed
  - [ ] AC-2.7.4: Stores updated score, chapter, decay_applied in PipelineContext

### T2.8: Create ConflictStage
- **Status**: [ ] Pending
- **Effort**: 1-2h
- **Files**: `nikita/pipeline/stages/conflict.py`
- **ACs**:
  - [ ] AC-2.8.1: Evaluates conflict triggers based on score/chapter/engagement
  - [ ] AC-2.8.2: Stores active_conflict state in PipelineContext
  - [ ] AC-2.8.3: Non-critical: logs error on failure, continues

### T2.9: Create TouchpointStage
- **Status**: [ ] Pending
- **Effort**: 1-2h
- **Files**: `nikita/pipeline/stages/touchpoint.py`
- **ACs**:
  - [ ] AC-2.9.1: Wraps `nikita/touchpoints/engine.py` — evaluates and schedules
  - [ ] AC-2.9.2: Creates scheduled_messages if touchpoint triggered
  - [ ] AC-2.9.3: Non-critical: logs error on failure, continues

### T2.10: Create SummaryStage
- **Status**: [ ] Pending
- **Effort**: 2-3h
- **Files**: `nikita/pipeline/stages/summary.py`
- **ACs**:
  - [ ] AC-2.10.1: Generates conversation summary via LLM (Haiku)
  - [ ] AC-2.10.2: Stores in `daily_summaries` table
  - [ ] AC-2.10.3: Port logic from `nikita/post_processing/summary_generator.py`

### T2.11: Pipeline Integration Tests
- **Status**: [ ] Pending
- **Effort**: 4-5h
- **Files**: `tests/pipeline/test_orchestrator.py`, `tests/pipeline/stages/test_*.py`
- **ACs**:
  - [ ] AC-2.11.1: 10 orchestrator tests (happy path, critical failure, non-critical failure, timing)
  - [ ] AC-2.11.2: 6 tests per stage (9 stages × 6 = 54 stage tests)
  - [ ] AC-2.11.3: 6 integration tests (full pipeline, voice trigger, text trigger)

### T2.12: Pipeline Health Endpoint
- **Status**: [ ] Pending
- **Effort**: 2-3h
- **Files**: `nikita/api/routes/admin.py`, `nikita/api/schemas/admin.py`
- **ACs**:
  - [ ] AC-2.12.1: `GET /admin/pipeline/health` returns per-stage success rates, avg timing, error counts
  - [ ] AC-2.12.2: Response includes last_24h summary (total runs, success rate, avg duration)
  - [ ] AC-2.12.3: JWT-protected (admin only)
  - [ ] AC-2.12.4: 6 tests for health endpoint

---

## Phase 3: Prompt Generation (US-4)

### T3.1: Create Jinja2 Text Template (system_prompt.j2)
- **Status**: [ ] Pending
- **Effort**: 4-5h
- **Files**: `nikita/pipeline/templates/system_prompt.j2`
- **ACs**:
  - [ ] AC-3.1.1: 11 sections: Identity, Immersion, Platform, State, Relationship, Memory, Continuity, Inner Life, Psychology, Chapter, Vice
  - [ ] AC-3.1.2: Renders in <5ms
  - [ ] AC-3.1.3: Output ~4,800 tokens pre-enrichment
  - [ ] AC-3.1.4: Handles missing fields gracefully (conditional blocks)

### T3.2: Create Jinja2 Voice Template (voice_prompt.j2)
- **Status**: [ ] Pending
- **Effort**: 2-3h
- **Files**: `nikita/pipeline/templates/voice_prompt.j2`
- **ACs**:
  - [ ] AC-3.2.1: Condensed version (no Psychology section, shorter sections)
  - [ ] AC-3.2.2: Output ~1,500 tokens pre-enrichment
  - [ ] AC-3.2.3: Voice-specific formatting rules

### T3.3: Create PromptBuilderStage
- **Status**: [ ] Pending
- **Effort**: 4-5h
- **Files**: `nikita/pipeline/stages/prompt_builder.py`
- **ACs**:
  - [ ] AC-3.3.1: Loads Jinja2 template, renders with PipelineContext data
  - [ ] AC-3.3.2: Calls Claude Haiku for narrative enrichment
  - [ ] AC-3.3.3: Falls back to raw Jinja2 output if Haiku fails
  - [ ] AC-3.3.4: Stores result in `ready_prompts` via `ReadyPromptRepository.set_current()`
  - [ ] AC-3.3.5: Generates BOTH text and voice prompts in one pass

### T3.4: Token Budget Validation
- **Status**: [ ] Pending
- **Effort**: 2h
- **Files**: `nikita/pipeline/stages/prompt_builder.py`
- **ACs**:
  - [ ] AC-3.4.1: Text prompt post-enrichment: 5,500-6,500 tokens (warn if outside range)
  - [ ] AC-3.4.2: Voice prompt post-enrichment: 1,800-2,200 tokens (warn if outside range)
  - [ ] AC-3.4.3: If over budget, truncate lower-priority sections (Vice → Chapter → Psychology)

### T3.5: Prompt Generation Test Suite
- **Status**: [ ] Pending
- **Effort**: 5-6h
- **Files**: `tests/pipeline/stages/test_prompt_builder.py`, `tests/pipeline/templates/test_rendering.py`
- **ACs**:
  - [ ] AC-3.5.1: 15 Jinja2 rendering tests (all sections, missing fields, edge cases)
  - [ ] AC-3.5.2: 15 Haiku enrichment tests (variability, fact preservation, fallback)
  - [ ] AC-3.5.3: 15 storage tests (ready_prompts CRUD, is_current flag, both platforms)

---

## Phase 4: Agent Integration (US-5)

### T4.1: Wire Text Agent to ReadyPrompts
- **Status**: [ ] Pending
- **Effort**: 2-3h
- **Files**: `nikita/agents/text/agent.py`
- **ACs**:
  - [ ] AC-4.1.1: `build_system_prompt()` reads from `ready_prompts` when `UNIFIED_PIPELINE_ENABLED=true`
  - [ ] AC-4.1.2: Falls back to on-the-fly generation if no prompt exists
  - [ ] AC-4.1.3: Logs warning on fallback with user_id

### T4.2: Simplify Voice server_tools
- **Status**: [ ] Pending
- **Effort**: 3-4h
- **Files**: `nikita/agents/voice/server_tools.py`
- **ACs**:
  - [ ] AC-4.2.1: `get_context()` reads from `ready_prompts` (<100ms)
  - [ ] AC-4.2.2: Reduced from 935 → ~200 lines
  - [ ] AC-4.2.3: Falls back to cached DynamicVariables if no prompt exists

### T4.3: Wire Voice Inbound to ReadyPrompts
- **Status**: [ ] Pending
- **Effort**: 1-2h
- **Files**: `nikita/agents/voice/inbound.py`
- **ACs**:
  - [ ] AC-4.3.1: Initial voice context loaded from `ready_prompts(platform='voice')`
  - [ ] AC-4.3.2: Falls back to existing DynamicVariables loading if no prompt

### T4.4: Add Feature Flag
- **Status**: [ ] Pending
- **Effort**: 1h
- **Files**: `nikita/config/settings.py`
- **ACs**:
  - [ ] AC-4.4.1: `unified_pipeline_enabled: bool = False` in Settings (env var `UNIFIED_PIPELINE_ENABLED`)
  - [ ] AC-4.4.2: `unified_pipeline_rollout_pct: int = 0` in Settings for canary (0-100, hash-based user sampling)
  - [ ] AC-4.4.3: Toggle controls both text + voice prompt loading paths
  - [ ] AC-4.4.4: Toggle controls pipeline trigger (tasks.py + voice.py)

### T4.5: Wire Pipeline Triggers
- **Status**: [ ] Pending
- **Effort**: 2h
- **Files**: `nikita/api/routes/tasks.py`, `nikita/api/routes/voice.py`
- **ACs**:
  - [ ] AC-4.5.1: `POST /tasks/process-conversations` calls `PipelineOrchestrator.process()` when flag enabled
  - [ ] AC-4.5.2: Voice webhook `call.ended` triggers `PipelineOrchestrator.process()` when flag enabled
  - [ ] AC-4.5.3: Falls back to existing pipeline when flag disabled

### T4.6: Agent Integration Test Suite
- **Status**: [ ] Pending
- **Effort**: 5-6h
- **Files**: `tests/agents/text/test_ready_prompt_loading.py`, `tests/agents/voice/test_ready_prompt_loading.py`
- **ACs**:
  - [ ] AC-4.6.1: 20 text agent tests (prompt loading, fallback, timing, flag behavior)
  - [ ] AC-4.6.2: 20 voice agent tests (context loading, fallback, timing)
  - [ ] AC-4.6.3: 10 integration tests (conversation flow end-to-end)

---

## Phase 5: Cleanup (US-6)

### T5.1: Delete Deprecated Modules
- **Status**: [ ] Pending
- **Effort**: 2-3h
- **Files**: See deletion list in plan.md
- **ACs**:
  - [ ] AC-5.1.1: `nikita/context_engine/` deleted (~2,500 lines)
  - [ ] AC-5.1.2: `nikita/meta_prompts/` deleted (~1,918 lines)
  - [ ] AC-5.1.3: `nikita/post_processing/` deleted (~2,100 lines)
  - [ ] AC-5.1.4: `nikita/context/post_processor.py`, `stages/`, `layers/` deleted (~3,100 lines)
  - [ ] AC-5.1.5: `nikita/memory/graphiti_client.py` deleted (451 lines)
  - [ ] AC-5.1.6: `nikita/context/template_generator.py` deleted (541 lines)

### T5.2: Remove Neo4j Dependencies
- **Status**: [ ] Pending
- **Effort**: 1h
- **Files**: `pyproject.toml`, `nikita/config/settings.py`
- **ACs**:
  - [ ] AC-5.2.1: `graphiti-core` and `neo4j` removed from pyproject.toml
  - [ ] AC-5.2.2: `neo4j_uri`, `neo4j_username`, `neo4j_password` removed from settings.py
  - [ ] AC-5.2.3: `CONTEXT_ENGINE_FLAG` removed from settings.py
  - [ ] AC-5.2.4: `UNIFIED_PIPELINE_ENABLED` removed (now always on)

### T5.3: Delete Obsolete Tests
- **Status**: [ ] Pending
- **Effort**: 2-3h
- **Files**: `tests/context_engine/`, `tests/meta_prompts/`, `tests/post_processing/`
- **ACs**:
  - [ ] AC-5.3.1: Tests for deleted modules removed (~789 tests)
  - [ ] AC-5.3.2: No imports referencing deleted modules remain (`rg "from nikita.context_engine" tests/` returns 0)
  - [ ] AC-5.3.3: No imports referencing deleted modules in source (`rg "from nikita.meta_prompts" nikita/` returns 0)

### T5.4: Rewrite Critical Tests
- **Status**: [ ] Pending
- **Effort**: 8-10h
- **Files**: Various test files
- **ACs**:
  - [ ] AC-5.4.1: ~200 new tests covering pipeline, memory, prompt generation
  - [ ] AC-5.4.2: Total test suite: 4,000+ passing
  - [ ] AC-5.4.3: No test references deleted modules

### T5.5: Update Documentation
- **Status**: [ ] Pending
- **Effort**: 2-3h
- **Files**: `CLAUDE.md`, `nikita/CLAUDE.md`, `memory/architecture.md`, `README.md`
- **ACs**:
  - [ ] AC-5.5.1: `CLAUDE.md` updated with pipeline architecture (no context_engine references)
  - [ ] AC-5.5.2: `memory/architecture.md` updated with unified pipeline diagram
  - [ ] AC-5.5.3: `nikita/CLAUDE.md` module table updated
  - [ ] AC-5.5.4: `README.md` updated (no Neo4j, no context_engine)

---

## Cross-Cutting: E2E Tests + Test Infrastructure

### TX.1: Test Infrastructure — Conftest + Mocks
- **Status**: [ ] Pending
- **Effort**: 4-5h
- **Files**: `tests/pipeline/conftest.py`, `tests/pipeline/mocks.py`
- **ACs**:
  - [ ] AC-X.1.1: `tests/pipeline/conftest.py` with async session fixtures, PipelineContext factory, stage isolation
  - [ ] AC-X.1.2: `MockHaikuEnricher` fixture returning deterministic enriched text (no real LLM calls)
  - [ ] AC-X.1.3: `MockEmbeddingClient` fixture returning deterministic 1536-dim vectors
  - [ ] AC-X.1.4: `MockExtractionAgent` fixture returning deterministic facts/threads/thoughts
  - [ ] AC-X.1.5: Stage fixtures with clean DB state per test (function-scoped sessions)

### TX.2: E2E Test Scenarios — Voice-Text Parity
- **Status**: [ ] Pending
- **Effort**: 6-8h
- **Files**: `tests/pipeline/test_e2e_unified.py`
- **ACs**:
  - [ ] AC-X.2.1: Text conversation → pipeline → ready_prompt stored → next text message reads pre-built prompt
  - [ ] AC-X.2.2: Voice call → transcript stored → pipeline → next text message has voice context
  - [ ] AC-X.2.3: Text + voice same user → both ready_prompts reflect identical facts
  - [ ] AC-X.2.4: Pipeline with feature flag OFF → falls back to existing path
  - [ ] AC-X.2.5: Pipeline with feature flag ON → uses unified pipeline
  - [ ] AC-X.2.6: 20 E2E tests covering conversation lifecycle

### TX.3: Performance Benchmark Tests
- **Status**: [ ] Pending
- **Effort**: 3-4h
- **Files**: `tests/pipeline/test_performance.py`
- **ACs**:
  - [ ] AC-X.3.1: Jinja2 template rendering <5ms (measured with pytest-benchmark or time.perf_counter)
  - [ ] AC-X.3.2: SupabaseMemory.search() <100ms (with mock DB)
  - [ ] AC-X.3.3: Full pipeline <12s (with mocked LLM calls)
  - [ ] AC-X.3.4: Ready prompt loading <100ms
  - [ ] AC-X.3.5: 10 benchmark tests

---

## Progress Summary

| Phase | Tasks | Completed | Status |
|-------|-------|-----------|--------|
| Phase 0: Database Foundation | 8 | 0 | Pending |
| Phase 1: Memory Migration | 6 | 0 | Pending |
| Phase 2: Pipeline Core | 12 | 0 | Pending |
| Phase 3: Prompt Generation | 5 | 0 | Pending |
| Phase 4: Agent Integration | 6 | 0 | Pending |
| Phase 5: Cleanup | 5 | 0 | Pending |
| Cross-Cutting: E2E + Infra | 3 | 0 | Pending |
| **Total** | **45** | **0** | **Pending** |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-02-06 | Initial task generation from Spec 042 |
