# Spec 042: Unified Pipeline Refactor — Implementation Plan

## Executive Summary

**Problem**: 3 prompt paths (~5,400 lines), 2 post-processing pipelines (~1,114 lines), Neo4j 30-73s cold start.

**Solution**: Single `nikita/pipeline/` module with 9 stages, `SupabaseMemory` replacing Neo4j, Jinja2+Haiku prompt generation, pre-built prompts in `ready_prompts` table.

**Scope**: ~20 new files, ~6 modified files, ~11,000 lines deleted. ~39 tasks, ~440 new tests.

**Phased delivery**: 6 phases (linear dependency), feature-flagged, each independently deployable.

---

## Architecture Overview

```
BEFORE (3 paths, 2 pipelines, Neo4j):
┌─────────────────────────────────────────────────────────────┐
│ TEXT:  ContextEngine(8 collectors) → Sonnet 4.5 → prompt    │
│ VOICE: server_tools.py inline loading (935 lines)           │
│ FALLBACK: MetaPromptService v1 (1,918 lines)                │
│ POST-TEXT:  PostProcessor (11 stages)                        │
│ POST-VOICE: PostProcessingPipeline (8 steps, legacy)        │
│ MEMORY: Neo4j Aura (3 graphs, 30-73s cold start)            │
└─────────────────────────────────────────────────────────────┘

AFTER (1 path, 1 pipeline, Supabase only):
┌─────────────────────────────────────────────────────────────┐
│ TEXT+VOICE: ReadyPromptRepository.get_current() → 0ms load  │
│ PIPELINE:   PipelineOrchestrator (9 stages, 8-12s async)    │
│ MEMORY:     SupabaseMemory (pgVector, <100ms search)        │
│ PROMPTS:    Jinja2 (<5ms) + Haiku enrichment (~500ms)       │
└─────────────────────────────────────────────────────────────┘
```

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Memory backend | Supabase pgVector | Same embedding model, no cold start, single datastore |
| Prompt generation | Jinja2 + Haiku (hybrid) | Deterministic base (<5ms) + narrative enrichment (~500ms) |
| LLM for enrichment | Claude Haiku (not Sonnet) | 10x cheaper, sufficient for narrative wrapping |
| Pipeline architecture | Sequential stages | Simplicity, debuggability, per-stage error isolation |
| Data contract | Reuse ContextPackage fields | 45+ fields already defined, proven in production |
| Rollout strategy | Feature flag + canary | `UNIFIED_PIPELINE_ENABLED`, 10% → 50% → 100% |
| Index type | IVFFlat (not HNSW) | Better for batch inserts, adequate recall at our scale |
| Template engine | Jinja2 | Industry standard, fast, zero LLM cost |

---

## Implementation Phases

### Phase 0: Database Foundation (US-1)

**Goal**: Create tables + models + repositories for `memory_facts` and `ready_prompts`.

**Files to Create**:

| File | Lines | Purpose |
|------|-------|---------|
| `nikita/db/migrations/versions/20260206_0009_unified_pipeline_tables.py` | ~120 | Alembic migration |
| `nikita/db/models/memory_fact.py` | ~50 | SQLAlchemy model |
| `nikita/db/models/ready_prompt.py` | ~45 | SQLAlchemy model |
| `nikita/db/repositories/memory_fact_repository.py` | ~150 | CRUD + pgVector search |
| `nikita/db/repositories/ready_prompt_repository.py` | ~100 | Get/set current prompt |

**Files to Modify**:
- `nikita/db/models/__init__.py` — Register new models

**Tests**: 35 (model + repository)

**Deployment Gate**: Migration applied on staging, tables exist, RLS policies set.

---

### Phase 1: Memory Migration (US-2)

**Goal**: Replace Graphiti/Neo4j with SupabaseMemory using identical interface.

**Files to Create**:

| File | Lines | Purpose |
|------|-------|---------|
| `nikita/memory/supabase_memory.py` | ~300 | SupabaseMemory class |
| `scripts/migrate_neo4j_to_supabase.py` | ~250 | One-time migration |

**Files to Modify**:
- `nikita/memory/__init__.py` — Export SupabaseMemory

**Key Methods** (matching NikitaMemory interface):
```python
class SupabaseMemory:
    async def add_fact(fact, graph_type, source, confidence, metadata) -> MemoryFact
    async def search(query, graph_types, limit, min_confidence) -> list[MemoryFact]
    async def get_recent(user_id, graph_type, limit, hours) -> list[MemoryFact]
    async def find_similar(text, threshold=0.95) -> MemoryFact | None  # dedup
    async def update_fact(fact_id, new_text) -> MemoryFact  # supersede
```

**Embedding Strategy**: OpenAI `text-embedding-3-small` (1536 dims, already in settings).

**Migration Strategy**:
1. Export Neo4j graphs to JSON (3 files)
2. Generate embeddings for all facts
3. Bulk insert to memory_facts
4. Validate counts match
5. Keep Neo4j paused 30 days

**Tests**: 40 (add, search, dedup, temporal, migration)

**Deployment Gate**: 10 test users migrated, search quality validated vs Neo4j.

---

### Phase 2: Pipeline Core (US-3)

**Goal**: Single `PipelineOrchestrator` with 9 stages wrapping existing modules.

**Files to Create**:

| File | Lines | Purpose |
|------|-------|---------|
| `nikita/pipeline/__init__.py` | ~20 | Module exports |
| `nikita/pipeline/orchestrator.py` | ~250 | Sequential stage runner |
| `nikita/pipeline/models.py` | ~150 | PipelineContext, PipelineResult, StageResult |
| `nikita/pipeline/stages/__init__.py` | ~20 | Stage exports |
| `nikita/pipeline/stages/extraction.py` | ~200 | Port from context/stages/extraction.py |
| `nikita/pipeline/stages/memory_update.py` | ~150 | Write facts via SupabaseMemory |
| `nikita/pipeline/stages/life_sim.py` | ~80 | Wrap life_simulation/ |
| `nikita/pipeline/stages/emotional.py` | ~80 | Wrap emotional_state/ |
| `nikita/pipeline/stages/game_state.py` | ~150 | Score + chapter + decay |
| `nikita/pipeline/stages/conflict.py` | ~80 | Conflict evaluation |
| `nikita/pipeline/stages/touchpoint.py` | ~80 | Wrap touchpoints/ |
| `nikita/pipeline/stages/summary.py` | ~120 | Generate conversation summaries |

**Stage Reuse Map**:

| New Stage | Wraps Module | Key Import |
|-----------|-------------|------------|
| `extraction.py` | Port from `context/stages/extraction.py` | LLM extraction logic |
| `memory_update.py` | NEW (calls SupabaseMemory) | `supabase_memory.add_fact()` |
| `life_sim.py` | `nikita/life_simulation/` | `LifeSimulator.simulate()` |
| `emotional.py` | `nikita/emotional_state/computer.py` | `EmotionalStateComputer.compute()` |
| `game_state.py` | `nikita/engine/scoring/`, `chapters/`, `decay/` | ScoreCalculator, ChapterStateMachine, DecayProcessor |
| `conflict.py` | `nikita/engine/conflicts/` (if exists) | Conflict evaluator |
| `touchpoint.py` | `nikita/touchpoints/engine.py` | `TouchpointEngine.evaluate()` |
| `summary.py` | Port from `post_processing/summary_generator.py` | Summary LLM logic |

**PipelineOrchestrator Design**:
```python
class PipelineOrchestrator:
    STAGES = [
        ("extraction", ExtractionStage, True),     # name, class, is_critical
        ("memory_update", MemoryUpdateStage, True),
        ("life_sim", LifeSimStage, False),
        ("emotional", EmotionalStage, False),
        ("game_state", GameStateStage, False),
        ("conflict", ConflictStage, False),
        ("touchpoint", TouchpointStage, False),
        ("summary", SummaryStage, False),
        ("prompt_builder", PromptBuilderStage, False),
    ]

    async def process(self, conversation_id, session) -> PipelineResult:
        ctx = await self._build_context(conversation_id, session)
        for name, cls, critical in self.STAGES:
            result = await self._run_stage(name, cls, ctx, critical)
            if result.failed and critical:
                return PipelineResult.failed(ctx, name, result.error)
        return PipelineResult.success(ctx)
```

**Tests**: 70 (orchestrator + 9 stages × 6 tests each + integration)

**Deployment Gate**: Pipeline processes 10 conversations, all 9 stages complete.

---

### Phase 3: Prompt Generation (US-4)

**Goal**: Jinja2 templates + Haiku narrative enrichment → stored in ready_prompts.

**Files to Create**:

| File | Lines | Purpose |
|------|-------|---------|
| `nikita/pipeline/stages/prompt_builder.py` | ~300 | Render + enrich + store |
| `nikita/pipeline/templates/system_prompt.j2` | ~300 | Text prompt (11 sections) |
| `nikita/pipeline/templates/voice_prompt.j2` | ~150 | Voice prompt (condensed) |

**Files to Modify**:
- `pyproject.toml` — Add `jinja2` dependency

**Jinja2 Template Sections** (system_prompt.j2):

| # | Section | Tokens | Source |
|---|---------|--------|--------|
| 1 | Identity | ~400 | `base_personality.yaml` (static) |
| 2 | Immersion Rules | ~200 | Hardcoded (never reveal AI/game/scores) |
| 3 | Platform Style | ~300 | Text vs voice formatting rules |
| 4 | Current State | ~600 | Temporal: time, activity, mood, energy, daily events |
| 5 | Relationship State | ~500 | Chapter, score, engagement, conflict status |
| 6 | Memory | ~800 | 15 user facts + 8 relationship episodes + nikita events |
| 7 | Continuity | ~600 | Last conversation, open threads, today's moments |
| 8 | Inner Life | ~500 | Thoughts, recent events, inner monologue |
| 9 | Psychological Depth | ~400 | Vulnerability, defenses, triggers |
| 10 | Chapter Behavior | ~300 | Chapter-specific response playbook |
| 11 | Vice Shaping | ~200 | Top 3 vices with intensity |
| | **Total (text)** | **~4,800** | Pre-enrichment |

**Haiku Enrichment**: Transforms flat template into narratively rich prompt with emotional coherence, time-of-day awareness, and variability. Adds ~700-1,700 tokens. Falls back to raw Jinja2 on failure.

**Tests**: 45 (rendering, enrichment, storage, token validation, fallback)

**Deployment Gate**: 10 prompts generated, token counts within budget, A/B quality check.

---

### Phase 4: Agent Integration (US-5)

**Goal**: Wire text + voice agents to read from `ready_prompts` instead of generating on-the-fly.

**Files to Modify**:

| File | Change | Lines Changed |
|------|--------|---------------|
| `nikita/agents/text/agent.py` | `build_system_prompt()` reads from ready_prompts | ~50 |
| `nikita/agents/voice/server_tools.py` | Simplify `get_context()` from 935 → ~200 lines | ~735 removed |
| `nikita/agents/voice/inbound.py` | Use ready_prompt for initial context | ~30 |
| `nikita/api/routes/tasks.py` | Trigger unified pipeline | ~30 |
| `nikita/api/routes/voice.py` | Trigger unified pipeline on call.ended | ~20 |
| `nikita/config/settings.py` | Add `UNIFIED_PIPELINE_ENABLED` flag | ~5 |

**Feature Flag Logic**:
```python
if settings.UNIFIED_PIPELINE_ENABLED:
    prompt = await ready_prompt_repo.get_current(user_id, platform)
    if prompt:
        return prompt.prompt_text
    # Fallback: generate on-the-fly, log warning
    logger.warning(f"No ready_prompt for {user_id}, generating on-the-fly")
    return await generate_fallback_prompt(user_id, session)
else:
    # Existing path (ContextEngine v2)
    return await router.generate_text_prompt(...)
```

**Rollout Plan**:
1. Deploy with flag OFF (no behavior change)
2. Enable for 10% of users (monitor latency, errors)
3. Enable for 50% (48h, compare prompt quality)
4. Enable for 100% (full rollout)

**Tests**: 50 (agent loading, fallback, flag behavior, timing)

**Deployment Gate**: 10% canary with zero errors for 48h, latency under 5s.

---

### Phase 5: Cleanup (US-6)

**Goal**: Delete ~11,000 lines of dead code, remove Neo4j dependencies.

**Files to Delete**:

| Path | Lines | Tests Affected |
|------|-------|----------------|
| `nikita/context_engine/` | ~2,500 | ~326 tests |
| `nikita/meta_prompts/` | ~1,918 | ~150 tests |
| `nikita/context/template_generator.py` | 541 | ~20 tests |
| `nikita/context/layers/` | ~1,600 | ~50 tests |
| `nikita/context/post_processor.py` | 494 | ~30 tests |
| `nikita/context/stages/` | ~1,000 | ~133 tests |
| `nikita/post_processing/` | ~2,100 | ~50 tests |
| `nikita/memory/graphiti_client.py` | 451 | ~20 tests |
| `nikita/context_engine/router.py` | ~200 | ~10 tests |
| **Total** | **~11,000** | **~789 tests** |

**Dependencies to Remove** (pyproject.toml):
- `graphiti-core`
- `neo4j`

**Config to Remove** (settings.py):
- `neo4j_uri`, `neo4j_username`, `neo4j_password`
- `CONTEXT_ENGINE_FLAG`

**Documentation Updates**:
- `CLAUDE.md` — Remove context_engine references
- `memory/architecture.md` — Update to reflect unified pipeline
- `nikita/CLAUDE.md` — Update module table

**Tests**: Rewrite ~200 critical tests for new architecture. Target: 4,000+ total passing.

**Deployment Gate**: Zero failing tests, clean `rg` for deleted module imports.

---

## Error Response & API Schemas

### Pipeline Processing Response

```python
class PipelineProcessResponse(BaseModel):
    conversation_id: UUID
    status: Literal["success", "partial", "failed"]
    stages_completed: list[str]
    stages_failed: list[str]
    total_duration_ms: float
    prompt_generated: bool
    error: str | None = None

# HTTP Status Codes:
# 200 - All stages succeeded
# 207 - Partial success (non-critical stages failed)
# 500 - Critical stage failed (Extraction or MemoryUpdate)
```

### Pipeline Health Response

```python
class PipelineHealthResponse(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy"]
    stages: dict[str, StageHealthInfo]  # per-stage success rate, avg_ms, error_count
    last_24h: PipelineSummary  # total runs, success rate, avg duration

class StageHealthInfo(BaseModel):
    success_rate: float  # 0.0-1.0
    avg_duration_ms: float
    error_count: int
    last_error: str | None
```

### OpenAI Embedding Error Handling

```python
# In SupabaseMemory:
# - Timeout: 30s per embedding call
# - Retry: 3x with exponential backoff (1s, 2s, 4s)
# - Fallback: Store fact with is_active=FALSE, flag for retry
# - Rate limit: Respect OpenAI rate limits (3000 RPM for text-embedding-3-small)
```

---

## Token Budget Strategy

### Text Prompt Token Allocation

| Section | Pre-Enrichment | Post-Enrichment |
|---------|---------------|-----------------|
| Identity + Immersion | 600 | 700 |
| Platform + State | 900 | 1,100 |
| Relationship + Memory | 1,300 | 1,500 |
| Continuity + Inner Life | 1,100 | 1,300 |
| Psychology + Chapter + Vice | 900 | 1,100 |
| **Total** | **4,800** | **5,700** |

### Voice Prompt Token Allocation

Voice uses condensed template (no Psychology, shorter sections):
- Pre-enrichment: ~1,500 tokens
- Post-enrichment: ~2,000 tokens

---

## Verification Plan

### Unit Tests (~240)
- Phase 0: 35 (models, repositories, migrations)
- Phase 1: 40 (SupabaseMemory methods, embedding, migration script)
- Phase 2: 70 (orchestrator, 9 stages, error handling)
- Phase 3: 45 (Jinja2 rendering, Haiku enrichment, token validation)
- Phase 4: 50 (agent integration, fallback, feature flag)

### Integration Tests (~50)
- Full pipeline: conversation → pipeline → ready_prompt → agent reads
- Voice-text parity: same user, both platforms get equivalent context
- Memory migration: Supabase facts match Neo4j facts

### E2E Tests
- Telegram: Send message → response → verify pipeline ran → next message has updated context
- Voice: Call → transcript stored → pipeline → next text message has voice context

### Performance Benchmarks
- Prompt load: <100ms (DB read)
- Pipeline total: <12s
- Jinja2 render: <5ms
- Haiku enrichment: <1s
- Memory search: <100ms

---

## Rollback Strategy

| Scenario | Action | Recovery Time |
|----------|--------|---------------|
| Pipeline bugs | Toggle `UNIFIED_PIPELINE_ENABLED=false` | Instant |
| Memory search poor | Revert to ContextEngine v2 (still in codebase) | Instant |
| Prompt quality low | Increase Haiku budget or revert to Sonnet generation | Minutes |
| Data loss discovered | Resume Neo4j Aura instance (paused 30 days) | ~5 minutes |
| Test suite broken | Revert code, keep DB tables (additive) | Minutes |
