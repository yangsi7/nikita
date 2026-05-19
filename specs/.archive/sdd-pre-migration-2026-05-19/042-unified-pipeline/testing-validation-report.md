# Testing Validation Report: Spec 042 — Unified Pipeline Refactor

**Spec**: `/Users/yangsim/Nanoleq/sideProjects/nikita/specs/042-unified-pipeline/`
**Status**: **FAIL** (Critical gaps in testing strategy)
**Timestamp**: 2026-02-06T22:30:00Z
**Validator**: Testing Strategy Validation Specialist

---

## Executive Summary

**Overall Assessment**: **FAIL** — Spec 042 has **4 CRITICAL** findings that must be resolved before implementation can proceed.

The testing strategy lacks:
1. **NO E2E tests defined** for voice-text parity (critical user flow)
2. **Undefined Haiku LLM mock strategy** — will cause test flakiness and real API calls
3. **Neo4j migration validation untested** — 30-73s latency depends on data integrity
4. **Async pipeline orchestration fixtures undefined** — 9 stages with unclear isolation patterns

The plan specifies ~440 new tests across 5 phases, but **fails to address how these tests will isolate from LLM calls, manage async context, and validate data migration**.

| Severity | Count |
|----------|-------|
| **CRITICAL** | 4 |
| **HIGH** | 5 |
| **MEDIUM** | 3 |
| **LOW** | 2 |

**Pass Criteria**: 0 CRITICAL + 0 HIGH findings.
**Result**: **FAIL**

---

## Summary of Findings

| Severity | Category | Issue | Location | Recommendation |
|----------|----------|-------|----------|----------------|
| **CRITICAL** | Test Infrastructure | No E2E test scenarios defined for voice-text parity validation | plan.md:322-344, spec.md:74-75 | Add 3 E2E user stories (voice→text context inheritance, dual-platform prompt equivalence, migration rollback) |
| **CRITICAL** | Async Patterns | PipelineOrchestrator async fixture design undefined — no conftest strategy for managing 9 stateful stages | plan.md:118-174, tasks.md:240-247 | Create `tests/pipeline/conftest.py` with async fixtures for PipelineContext, PipelineOrchestrator, per-stage mocks |
| **CRITICAL** | LLM Mocking | No mock strategy for Haiku enrichment (500ms calls) — tests will fail intermittently or call real API | plan.md:182-215, spec.md:63-66 | Define `MockHaikuEnricher` fixture that returns deterministic enriched prompts; validate output format |
| **CRITICAL** | Data Migration | Neo4j→Supabase migration tests undefined — how is 789-fact loss validated? | plan.md:105-113, tasks.md:115-124 | Add migration validation layer: pre/post counts, embedding quality, graph_type distribution, reconciliation tests |
| **HIGH** | Test Cleanup | ~789 deleted tests (Phase 5) target not quantified against 4000+ requirement | tasks.md:384-391, plan.md:295 | Define explicit cleanup strategy: (1) list modules to delete, (2) identify 200+ tests to rewrite, (3) specify 4000+ baseline target |
| **HIGH** | Async Isolation | Supabase async fixtures not documented — will tests reuse DB session across stages? | plan.md:56-76, tasks.md:63-82 | Document: DB session lifecycle per test, rollback strategy for integration tests, how nested async operations maintain isolation |
| **HIGH** | Performance Testing | No benchmark tests defined for <12s pipeline target | spec.md:93-101, plan.md:341-345 | Add `tests/pipeline/test_performance.py` with benchmark fixtures; target: Jinja2 <5ms, Haiku <1s, memory search <100ms |
| **HIGH** | Test Organization | 6 phases with unclear test dependencies — Phase 0 tests need Phase 1 mocks | plan.md:56-298 | Document test execution order: Phase 0 (models only) → Phase 1 (mocks for Phase 2) → Phase 2-3 → Phase 4 (agent integration) → Phase 5 (cleanup) |
| **HIGH** | Coverage Gaps | ~440 tests planned; no unit/integration/E2E ratio defined (pyramid imbalance risk) | plan.md:322-344 | Specify: Unit ~280 (64%), Integration ~120 (27%), E2E ~40 (9%) to target 70-20-10 pyramid |
| **MEDIUM** | Feature Flag Testing | `UNIFIED_PIPELINE_ENABLED` toggle behavior not tested (canary rollout validation) | plan.md:235-249, tasks.md:331-338 | Add 10 feature flag tests: OFF→ON transition, prompt stale detection, fallback generation, instant rollback |
| **MEDIUM** | Jinja2 Template Testing | 11 sections + conditional blocks + both text/voice templates — template rendering parity tests missing | plan.md:197-213, tasks.md:253-272 | Add template validation: (1) both platforms render, (2) token counts within bounds, (3) conditional blocks handle NULL fields gracefully |
| **MEDIUM** | Voice-Text Parity | No explicit tests for "same user, both platforms get equivalent context" | spec.md:29, plan.md:332 | Add dual-platform integration tests: send message, trigger pipeline, verify ready_prompts(platform='text') == ready_prompts(platform='voice') context |
| **LOW** | Test Documentation | Task descriptions lack AC specificity (e.g., "10 orchestrator tests" but no breakdown) | tasks.md:240-247 | Add AC checklist to each test task: "test_happy_path", "test_critical_failure_stops", "test_noncritical_continues", etc. |
| **LOW** | Fixture Reuse | Existing async fixtures in conftest.py not referenced in plan (DB session, mock LLM, etc.) | plan.md:322-344, tests/conftest.py:1-50 | Document how Phase 0-5 tests will reuse: `async_session`, `mock_embedding_client`, `mock_conversation_factory` |

---

## Testing Pyramid Analysis

**Target (per project guidance)**: 70% unit, 20% integration, 10% E2E

**Planned (Spec 042)**:

```
Pyramid Assessment (440 tests total):

                    E2E (TBD)      ← UNDEFINED
                 ─────────────
               Integration (TBD)   ← UNDEFINED
             ───────────────────
           Unit Tests (~240)       ← 55% (below 70% target)
         ─────────────────────────
```

**Current Plan Breakdown** (from plan.md:322-344):
- Phase 0: 35 unit tests (models + repos)
- Phase 1: 40 unit tests (memory operations)
- Phase 2: 70 unit tests (orchestrator + stages)
- Phase 3: 45 unit tests (Jinja2 + Haiku)
- Phase 4: 50 unit tests (agent integration)
- Phase 5: 200+ tests (cleanup)
- **E2E Tests**: Mentioned but NO scenarios defined

**Unit Tests: ~240 (55%)**
**Integration Tests: ~50 (11%)**
**E2E Tests: 0 (0%)**

**IMBALANCE**: Missing E2E layer entirely. Should be ~44 E2E tests.

---

## TDD Enablement Check (SMART Criteria)

### User Story Testability Analysis

| AC ID | AC Description | Testable | Test Type | Issue |
|-------|----------------|----------|-----------|-------|
| AC-1.1 | `memory_facts` table exists with columns | ✅ YES | Unit | Clear schema check |
| AC-1.2 | `ready_prompts` table exists | ✅ YES | Unit | Clear schema check |
| AC-1.3 | IVFFlat index created | ✅ YES | Unit | Can verify via `pg_indexes` query |
| AC-2.1 | SupabaseMemory.add_fact() inserts with embedding | ⚠️ RISKY | Unit | **Embedding requires OpenAI API call** — needs mock |
| AC-2.2 | SupabaseMemory.search() returns top-k by similarity | ⚠️ RISKY | Unit | **pgVector search quality varies** — needs benchmark vs Neo4j baseline |
| AC-2.4 | Migration preserves all facts | ⚠️ RISKY | Integration | **No pre/post validation step defined** |
| AC-3.1 | Jinja2 renders in <5ms | ✅ YES | Unit | Timing test, but needs baseline |
| AC-3.3 | Haiku enrichment adds narrative | ❌ NO | Unit | **LLM output is non-deterministic** — cannot assert on content |
| AC-3.4 | Haiku failure falls back to raw Jinja2 | ⚠️ RISKY | Unit | **How do you inject Haiku failure?** No mock strategy |
| AC-4.1 | Text agent reads from ready_prompts | ✅ YES | Unit | Mock repo, verify call |
| AC-4.2 | Voice server_tools reduces to 200 lines | ✅ YES | Unit | Refactor + verify line count |
| AC-5.1 | Dead code deleted | ✅ YES | Unit | `rg` check for imports in codebase |
| AC-6.2 | Zero failing tests after cleanup | ⚠️ RISKY | Integration | **~789 tests deleted, how validated?** |

**Testable AC Count**: 8/13 (62%)
**Risky ACs** (need mock strategy): 5

**TDD Readiness**:
- ✅ Some ACs are clear and testable
- ⚠️ LLM-dependent ACs (Haiku, embedding) lack mock strategy
- ❌ Migration validation is undefined
- ❌ E2E scenarios completely missing

---

## Test Scenario Inventory

### E2E Scenarios: **NONE DEFINED**

**Missing Critical User Flows** (should be in spec.md § 5):

| Scenario | Priority | User Flow | Status |
|----------|----------|-----------|--------|
| Text→Voice Context Transfer | P1 | User sends text message → pipeline runs → voice call → voice agent has same context | **❌ MISSING** |
| Voice→Text Context Transfer | P1 | User makes voice call → pipeline runs → text message → text agent references call | **❌ MISSING** |
| Prompt Pre-Building | P1 | After conversation → pipeline builds text + voice prompts → both stored in ready_prompts | **❌ MISSING** |
| Migration Rollback | P1 | 10% canary enables unified pipeline → errors detected → toggle off → rollback to ContextEngine v2 | **❌ MISSING** |
| Neo4j Data Integrity | P2 | Export 5000 Neo4j facts → embed → insert to Supabase → query count matches, similarity search quality parity | **❌ MISSING** |
| Dual-Platform Equivalence | P2 | Same user, text + voice prompts should have equivalent context (not identical format, but same facts) | **❌ MISSING** |
| Fallback Generation | P2 | New user (no pre-built prompt) → pipeline generates one-time → text agent uses it | **❌ MISSING** |

**Recommendation**: Add ~7 E2E user stories to tasks.md with 5-10 test cases each = ~40-50 E2E tests.

### Integration Test Points

| Component | Integration Point | Mock Required | Test Strategy |
|-----------|-------------------|---------------|----------------|
| ExtractionStage | LLM entity extraction | ✅ Haiku LLM | Mock with deterministic entities; validate PipelineContext.extracted_facts |
| MemoryUpdateStage | pgVector search + insert | ✅ OpenAI embeddings | Mock embedding client, validate fact deduplication (similarity > 0.95) |
| LifeSimStage | Wraps life_simulation/ | ❌ No mock (unit already has 212 tests) | Call existing module, verify results stored in PipelineContext |
| EmotionalStage | Wraps emotional_state/ | ❌ No mock (unit already has 233 tests) | Call existing module, verify 4D mood computed |
| GameStateStage | Scoring + Chapter + Decay | ❌ No mock (unit already has 60+142+52=254 tests) | Call existing modules, verify state transitions |
| PromptBuilderStage | Jinja2 + Haiku + storage | ✅ Haiku LLM, pgVector | Mock Haiku, verify ready_prompts insertion, validate token counts |
| PipelineOrchestrator | Coordinates 9 stages | ✅ All stage mocks | Test happy path, critical failure stops, non-critical continues |
| ReadyPromptRepository | DB CRUD + unique constraint | ❌ Real DB (test SQLAlchemy) | Use test DB, verify unique(user_id, platform, is_current=TRUE) |
| SupabaseMemory | pgVector search + embedding | ✅ Embedding client mock | Mock OpenAI, test search ranking, deduplication logic |

**Integration Test Count Target**: ~120 tests (27% of pyramid)

### Unit Test Coverage

| Module | Functions | Coverage Target | Phase | Tests |
|--------|-----------|-----------------|-------|-------|
| MemoryFact model | 5 | 100% | 0 | 5 |
| ReadyPrompt model | 5 | 100% | 0 | 5 |
| MemoryFactRepository | 5 methods | 100% | 0 | 15 |
| ReadyPromptRepository | 3 methods | 100% | 0 | 10 |
| SupabaseMemory | 6 methods | 100% | 1 | 40 |
| PipelineOrchestrator | orchestration logic | 100% | 2 | 10 |
| ExtractionStage | extract_facts() | 100% | 2 | 8 |
| MemoryUpdateStage | write_facts() | 100% | 2 | 8 |
| LifeSimStage | compute_events() | 100% | 2 | 6 |
| EmotionalStage | compute_mood() | 100% | 2 | 6 |
| GameStateStage | score+chapter+decay | 100% | 2 | 8 |
| ConflictStage | evaluate_conflict() | 100% | 2 | 6 |
| TouchpointStage | schedule_touchpoints() | 100% | 2 | 6 |
| SummaryStage | summarize_conversation() | 100% | 2 | 8 |
| Jinja2 rendering | render_template() | 100% | 3 | 20 |
| Haiku enrichment | enrich_narrative() | 95% (mock) | 3 | 15 |
| Token validation | validate_token_counts() | 100% | 3 | 10 |
| Text agent integration | build_system_prompt() | 100% | 4 | 15 |
| Voice agent integration | get_context() | 100% | 4 | 15 |
| Feature flag logic | toggle UNIFIED_PIPELINE_ENABLED | 100% | 4 | 10 |
| **Total** | | | | **240** |

---

## Critical Gaps Detailed Analysis

### 1. E2E Tests Completely Missing (CRITICAL)

**Issue**: Spec defines no E2E test scenarios. The "E2E Tests" section of plan.md (line 336-344) merely lists requirements, not actual test cases.

**Evidence**:
```
plan.md:336-344:
"### E2E Tests
- Telegram: Send message → response → verify pipeline ran → next message has updated context
- Voice: Call → transcript stored → pipeline → next text message has voice context"
```

These are descriptions, not test implementations. No `tests/e2e/test_unified_pipeline.py` file is planned.

**Impact**:
- Cannot validate voice-text parity (critical for "one person" illusion)
- Migration rollback behavior untested
- Dual-platform prompt equivalence unverified

**Recommendation**:
Add to tasks.md Phase 5 (or new Phase 6):
```
T6.1: E2E Telegram→Text Pipeline
- Send text message
- Verify pipeline runs (check job_executions)
- Send next message
- Verify context includes previous exchange
- 5 tests: happy path, extraction failure + fallback, memory search quality, prompt stale detection, rollback

T6.2: E2E Voice→Text Context Transfer
- Make voice call (mock ElevenLabs webhook)
- Verify transcript stored
- Trigger pipeline
- Send text message
- Verify text agent sees voice context facts
- 5 tests: same as T6.1 + voice-text parity check

T6.3: E2E Migration + Dual-Platform
- Migrate 100 facts Neo4j → Supabase
- Verify counts + embedding quality
- Request prompt for text platform
- Request prompt for voice platform
- Verify both have equivalent facts (text section/voice section adjusted)
- 5 tests: pre-migration validation, post-migration counts, search quality, dual-platform equivalence, reconciliation
```

---

### 2. Haiku LLM Mock Strategy Undefined (CRITICAL)

**Issue**: Phase 3 (Prompt Generation) will call Claude Haiku ~500ms per prompt. No mock strategy defined.

**Evidence**:
- plan.md:182-215 describes Haiku enrichment but provides NO mock fixture
- tasks.md:T3.3 AC-3.3.2: "Calls Claude Haiku for narrative enrichment" — how is this tested?
- tasks.md:T3.5 specifies "15 Haiku enrichment tests" but no mock design

**Impact**:
- Tests will either call real Anthropic API (slow, flaky, $$) or fail
- No deterministic output for assertion (Haiku is non-deterministic by design)
- Cannot test fallback behavior (AC-3.3.4: "falls back to raw Jinja2 output if Haiku fails")

**Recommendation**:
Create `tests/pipeline/conftest.py`:
```python
@pytest.fixture
def mock_haiku_enricher():
    """Mock Claude Haiku with deterministic output.

    Returns: callable(jinja2_output) → "Enriched: " + jinja2_output

    Usage in tests:
        def test_haiku_enrichment(mock_haiku_enricher):
            builder = PromptBuilderStage(haiku_client=mock_haiku_enricher)
            result = builder.enrich_prompt("Raw Jinja2 output")
            assert result.startswith("Enriched: ")
            assert len(result) > len("Raw Jinja2 output")
    """
    def enricher(jinja2_output: str) -> str:
        return f"[HAIKU ENRICHED]\n{jinja2_output}\n[Token-aware narrative added]"
    return enricher

@pytest.fixture
def mock_haiku_failure():
    """Mock Haiku failure for fallback testing."""
    async def fail_enricher(jinja2_output: str) -> str:
        raise APIError("Haiku API timeout")
    return fail_enricher
```

Add to tasks.md T3.5:
```
AC-3.5.2a: Mock Haiku with deterministic enrichment
AC-3.5.2b: Test fallback when Haiku fails
AC-3.5.2c: Verify enriched output > raw output in tokens
```

---

### 3. Async Pipeline Orchestration Fixtures Undefined (CRITICAL)

**Issue**: PipelineOrchestrator manages 9 stateful stages in sequence. No conftest strategy for isolating async state.

**Evidence**:
- plan.md:152-174 shows PipelineOrchestrator design but no async fixture
- tasks.md:T2.2 (Create PipelineOrchestrator) doesn't specify async context isolation
- tests/conftest.py:20-50 clears singletons, but doesn't document pipeline-specific isolation

**Impact**:
- Tests may share PipelineContext across stages (state pollution)
- Async session lifecycle unclear — when committed vs rolled back?
- Stage failures may cascade instead of isolating

**Recommendation**:
Create `tests/pipeline/conftest.py`:
```python
@pytest.fixture
async def pipeline_context(async_session, mock_user, mock_conversation):
    """Isolated PipelineContext for each test."""
    from nikita.pipeline.models import PipelineContext
    ctx = PipelineContext(
        conversation_id=mock_conversation.id,
        user_id=mock_user.id,
        session=async_session,
        stage_results={},
        stage_timings={}
    )
    yield ctx
    # Cleanup: rollback transaction
    await async_session.rollback()

@pytest.fixture
async def pipeline_orchestrator(async_session):
    """Instantiate orchestrator with mocked stages."""
    from nikita.pipeline.orchestrator import PipelineOrchestrator
    from unittest.mock import AsyncMock

    # Mock all stages
    mock_stages = [
        AsyncMock(name="ExtractionStage"),
        AsyncMock(name="MemoryUpdateStage"),
        # ... 7 more
    ]
    return PipelineOrchestrator(stages=mock_stages)

@pytest.fixture
async def mock_extraction_stage():
    """ExtractionStage returning deterministic facts."""
    class MockExtractionStage:
        async def run(self, ctx) -> dict:
            ctx.extracted_facts = [
                {"text": "User fact", "graph_type": "user", "confidence": 0.9},
                {"text": "Relationship fact", "graph_type": "relationship", "confidence": 0.85},
            ]
            return {"success": True}
    return MockExtractionStage()
```

Add to tasks.md T2.11:
```
AC-2.11.4: Async fixtures for PipelineContext + per-stage mocks
AC-2.11.5: Stage failure isolation tests (critical vs non-critical)
AC-2.11.6: Session rollback on stage failure or test end
```

---

### 4. Neo4j→Supabase Migration Validation Untested (CRITICAL)

**Issue**: Migration script (T1.4) must export 3 Neo4j graphs, generate embeddings, bulk-insert to Supabase. Zero fact loss required. No validation tests defined.

**Evidence**:
- plan.md:105-113 describes migration but provides no test strategy
- tasks.md:T1.4 AC-1.4.4: "Validates: count of facts in Supabase matches Neo4j per graph_type" — UNDEFINED HOW
- No pre-migration audit (list Neo4j facts), no post-migration reconciliation

**Impact**:
- Potential silent fact loss (e.g., 5000 facts → 4998 facts inserted)
- Embedding quality degradation vs Neo4j undetected
- Search ranking differences (IVFFlat vs Neo4j vector index) unmeasured

**Recommendation**:
Create `tests/memory/test_neo4j_migration.py`:
```python
@pytest.mark.asyncio
async def test_migration_fact_count_preservation(neo4j_client, supabase_memory):
    """Count of facts in Supabase matches Neo4j."""
    # 1. Audit Neo4j
    neo4j_facts = await neo4j_client.query_all_facts()
    neo4j_counts = {
        'user': len([f for f in neo4j_facts if f['graph_type'] == 'user']),
        'relationship': len([f for f in neo4j_facts if f['graph_type'] == 'relationship']),
        'nikita': len([f for f in neo4j_facts if f['graph_type'] == 'nikita']),
    }

    # 2. Run migration
    await migrate_neo4j_to_supabase(neo4j_client, supabase_memory)

    # 3. Audit Supabase
    supabase_counts = {
        'user': await supabase_memory.count_facts(graph_type='user'),
        'relationship': await supabase_memory.count_facts(graph_type='relationship'),
        'nikita': await supabase_memory.count_facts(graph_type='nikita'),
    }

    # 4. Assert match
    assert neo4j_counts == supabase_counts, f"Fact loss detected: {neo4j_counts} != {supabase_counts}"

@pytest.mark.asyncio
async def test_migration_embedding_quality(neo4j_client, supabase_memory, embedding_client):
    """Embedding quality parity: cosine similarity > 0.98 for same text."""
    neo4j_fact = await neo4j_client.fetch_fact("user_fact_123")

    # Regenerate embedding for same text
    embedding_1 = embedding_client.embed(neo4j_fact['text'])
    embedding_2 = embedding_client.embed(neo4j_fact['text'])

    # Same text → same embedding
    similarity = cosine_similarity(embedding_1, embedding_2)
    assert similarity > 0.99  # Should be ~1.0 for identical text

@pytest.mark.asyncio
async def test_migration_search_quality(neo4j_client, supabase_memory):
    """Search ranking parity: IVFFlat returns same top-5 as Neo4j."""
    test_user_id = "test-user-123"
    query = "What is the user's job?"

    # 1. Neo4j search
    neo4j_results = await neo4j_client.semantic_search(test_user_id, query, top_k=5)

    # 2. Supabase search (post-migration)
    supabase_results = await supabase_memory.search(test_user_id, query, limit=5)

    # 3. Top-3 should match (allow for ranking differences due to algorithm)
    neo4j_texts = [r['text'] for r in neo4j_results[:3]]
    supabase_texts = [r['fact'] for r in supabase_results[:3]]
    assert set(neo4j_texts) == set(supabase_texts)
```

Add to tasks.md T1.4:
```
AC-1.4.4a: Pre-migration audit counts Neo4j facts per graph_type
AC-1.4.4b: Post-migration counts match within 1%
AC-1.4.4c: Embedding quality verified (same text → same embedding)
AC-1.4.4d: Search ranking parity (top-5 results match, allow <10% reordering)
AC-1.4.4e: Supersedence graph preserved (fact → superseded_by links)
```

---

## High-Priority Issues

### 5. Test Cleanup Strategy Undefined (HIGH)

**Issue**: Phase 5 deletes ~789 tests for deprecated modules. How is cleanup validated?

**Evidence**:
- tasks.md:384-391 AC-5.3.2: "No imports referencing deleted modules remain" — needs automated check
- tasks.md:AC-5.4.2: "Total test suite: 4,000+ passing" — where did this baseline come from?
- Current suite: 4260+ tests. After cleanup: 4260 - 789 + 200 = ~3671 tests. **Below target!**

**Impact**:
- Test suite shrinks from 4260 → 3671 (13% loss)
- 789 deleted tests have unclear equivalents
- Phase 5 might leave codebase without adequate coverage

**Recommendation**:
Update tasks.md T5.3 + T5.4:
```
T5.3.1: Automated cleanup check
  - Create script: find tests -name "*.py" | xargs grep -l "context_engine\|meta_prompts\|post_processing\|graphiti" → output = 0
  - Run in CI/CD, block merge if imports found

T5.4: Rewrite 200+ Critical Tests
  Phase 5 test rewrite strategy:

  Deleted Test Count: ~789 tests
  Rewritten Tests: ~200 new pipeline + memory tests
  Net Loss: -589 tests

  Target (from CLAUDE.md): 4,000+ total passing
  Current baseline: 4,260 tests
  Post-cleanup: 4,260 - 789 + 200 = 3,671 tests

  GAP: 3,671 < 4,000 (requires +329 additional tests)

  Solution:
  - Rewrite 200 critical tests for pipeline (included in Phase 3-4 targets)
  - Add 150 new E2E tests (Phase 6)
  - Expand Phase 0-2 unit tests to cover 100% of new code (+79 tests)

  Revised target: 200 + 150 + 79 = 429 additional tests
  Revised total: 4,260 - 789 + 429 = 3,900 tests (still < 4,000 by 100)

  Mitigation: Remove low-value test duplication from existing suites (e.g., context_engine has redundant collector tests)
```

---

### 6. Async Context Isolation (HIGH)

**Issue**: How do tests ensure async session isolation across 9 pipeline stages?

**Evidence**:
- plan.md:56-76 describes DB foundation but doesn't specify session lifecycle
- tests/conftest.py:20-50 clears singletons but doesn't address nested async operations
- No mention of transaction rollback or session scoping

**Recommendation**:
Add to tests/pipeline/conftest.py:
```python
@pytest.fixture
async def pipeline_with_isolated_session(async_session):
    """Pipeline with transaction-scoped session."""
    async with async_session.begin():  # Start transaction
        yield async_session
        # Implicit rollback on context exit cleans up all inserts/updates


# Usage in integration tests:
@pytest.mark.asyncio
async def test_pipeline_full_flow(pipeline_with_isolated_session):
    orchestrator = PipelineOrchestrator()
    result = await orchestrator.process(
        conversation_id="test-conv-123",
        session=pipeline_with_isolated_session
    )

    # Assertions
    assert result.success

    # Session auto-rolled-back on fixture cleanup
```

---

### 7. Performance Benchmarks Undefined (HIGH)

**Issue**: spec.md defines <12s pipeline target but no benchmark tests.

**Evidence**:
- spec.md:93-101 lists targets: pipeline <12s, Jinja2 <5ms, Haiku <500ms, memory search <100ms
- plan.md:341-345 mentions "Performance Benchmarks" but provides no test code
- No pytest-benchmark integration or baseline numbers

**Recommendation**:
Add `tests/pipeline/test_performance.py`:
```python
import pytest
import time

@pytest.mark.asyncio
@pytest.mark.benchmark
async def test_jinja2_rendering_under_5ms(benchmark):
    """AC-4.1: Jinja2 renders in <5ms."""
    from nikita.pipeline.stages.prompt_builder import render_jinja2_template

    context = {"identity": "Nikita", "memory": [...], ...}

    def render():
        return render_jinja2_template("system_prompt.j2", context)

    result = benchmark(render)
    assert len(result) > 4000  # Output is substantial
    # pytest-benchmark auto-asserts timing

@pytest.mark.asyncio
async def test_memory_search_under_100ms():
    """AC-5.2: Memory search <100ms."""
    start = time.perf_counter()
    results = await supabase_memory.search(
        user_id="test-user",
        query="What is the user's job?",
        limit=10
    )
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert elapsed_ms < 100, f"Search took {elapsed_ms}ms, target <100ms"

@pytest.mark.asyncio
async def test_pipeline_total_under_12s():
    """AC-3.1: Pipeline <12s."""
    start = time.perf_counter()
    result = await orchestrator.process(conversation_id="test")
    elapsed_s = time.perf_counter() - start
    assert elapsed_s < 12, f"Pipeline took {elapsed_s}s, target <12s"
```

---

### 8. Test Execution Order Dependency (HIGH)

**Issue**: Phases 0-5 have unclear dependencies. Can Phase 2 tests run before Phase 1 fixtures exist?

**Evidence**:
- plan.md:56-298 presents phases linearly but doesn't specify test execution order
- Phase 0 creates models; Phase 1 creates SupabaseMemory; Phase 2 uses SupabaseMemory
- No conftest strategy for phase-dependent fixtures

**Recommendation**:
Document in plan.md or tasks.md:
```
Phase Test Execution Order:

Phase 0: MemoryFact + ReadyPrompt models (self-contained)
  - Can run independently
  - conftest provides: async_session, migration runner

Phase 1: SupabaseMemory + migration (depends on Phase 0 models)
  - Requires: models from Phase 0 already migrated
  - conftest provides: SupabaseMemory instance, mock embedding client

Phase 2: PipelineOrchestrator + 9 stages (depends on Phase 0-1)
  - Requires: models, SupabaseMemory, existing modules (life_sim, emotional, etc.)
  - conftest provides: PipelineOrchestrator, stage mocks

Phase 3: Prompt generation (depends on Phase 0-2)
  - Requires: models, orchestrator, stage results
  - conftest provides: Jinja2 environment, mock Haiku, ready_prompts repo

Phase 4: Agent integration (depends on Phase 0-3)
  - Requires: ready_prompts table, feature flag
  - conftest provides: text/voice agent mocks, feature flag toggle

Phase 5: Cleanup (depends on Phase 0-4 passing)
  - Must run LAST
  - Deletes deprecated modules
  - conftest: clean room for import checks

E2E Tests (Phase 6, optional): Run after Phase 4 ready
  - Requires all integration working
  - Real conversation flow tests
```

---

## Coverage Targets

### Test Pyramid Specification (MISSING FROM SPEC 042)

**Add to tasks.md Summary**:
```
Test Pyramid Target (70-20-10):
  Unit Tests (70%):     308 tests (0.70 × 440)
  Integration (20%):    88 tests  (0.20 × 440)
  E2E (10%):            44 tests  (0.10 × 440)
  TOTAL:                440 tests

Current Plan:
  Unit Tests:           ~240 (55%) ← BELOW TARGET
  Integration:          ~50 (11%) ← BELOW TARGET
  E2E:                  0 (0%)   ← MISSING
  TOTAL:                ~290 (66% of 440)

Required Additions:
  Unit: +68 tests
  Integration: +38 tests
  E2E: +44 tests
  TOTAL: +150 tests (revision to 440 → 590 total)
```

---

## Test Infrastructure Requirements

### Async Fixture Architecture

**Current (tests/conftest.py)**:
```python
@pytest.fixture(autouse=True)
def clear_singleton_caches():
    yield
    get_async_engine.cache_clear()
    get_session_maker.cache_clear()
    get_settings.cache_clear()
```

**Required (tests/pipeline/conftest.py)**:
```python
# 1. Async session with transaction isolation
@pytest.fixture
async def async_session():
    """Transactional session rolled back after test."""
    async with SessionLocal() as session:
        async with session.begin():
            yield session

# 2. Pipeline-specific fixtures
@pytest.fixture
async def mock_embedding_client():
    """Mock OpenAI embedding client."""
    def embed(text: str) -> list[float]:
        return [hash(text) % 1536 for _ in range(1536)]  # Deterministic
    return embed

@pytest.fixture
async def mock_conversation_factory(async_session, mock_user):
    """Factory for creating test conversations."""
    async def create(messages=None):
        conv = Conversation(user_id=mock_user.id, ...)
        async_session.add(conv)
        return conv
    return create

# 3. Stage mocks
@pytest.fixture
def mock_extraction_stage():
    """Deterministic extraction stage."""
    class Mock:
        async def run(self, ctx):
            ctx.extracted_facts = [...]
            return StageResult(success=True)
    return Mock()
```

---

## Recommendations (Priority Order)

### CRITICAL (Block Implementation)

1. **Define E2E User Stories** (3-5h)
   - Add T6.1-T6.3 to tasks.md Phase 6
   - Scenarios: text→voice, voice→text, dual-platform parity, migration rollback
   - Target: 40-50 E2E tests

2. **Mock Strategy for Haiku** (2-3h)
   - Create `tests/pipeline/conftest.py` with `mock_haiku_enricher` fixture
   - Define deterministic output format
   - Add AC-3.5.2a/b/c to tasks.md T3.5

3. **Async Pipeline Fixtures** (4-5h)
   - Design `tests/pipeline/conftest.py` with phase-dependent fixtures
   - Document session lifecycle and rollback strategy
   - Add AC-2.11.4/5/6 to tasks.md T2.11

4. **Neo4j Migration Validation Tests** (4-6h)
   - Create `tests/memory/test_neo4j_migration.py`
   - Implement: fact count, embedding quality, search parity, reconciliation
   - Add AC-1.4.4a/b/c/d/e to tasks.md T1.4

### HIGH (Resolve Before Phase Completion)

5. **Test Cleanup Strategy** (2-3h)
   - Update T5.3 with automated import checks
   - Revise T5.4 to target 4,000+ (add +150 E2E tests, +79 unit tests)
   - Document net loss: 4,260 → 3,900 → 4,050+ (post-additions)

6. **Performance Benchmarks** (3-4h)
   - Create `tests/pipeline/test_performance.py`
   - Add pytest-benchmark integration
   - Validate: <5ms Jinja2, <100ms search, <12s pipeline

7. **Test Execution Order Documentation** (1-2h)
   - Update plan.md Phase Dependencies section
   - Document conftest progression: Phase 0 → Phase 1 → ... → Phase 6
   - Specify which conftest fixtures are available per phase

8. **Coverage Pyramid Balance** (2h)
   - Add "Test Pyramid Target" to tasks.md Summary
   - Specify: 308 unit / 88 integration / 44 E2E
   - Revise total from 440 → 590 tests

### MEDIUM (Before Phase Start)

9. **Feature Flag Testing** (2-3h)
   - Add T4.6a: 10 feature flag tests for UNIFIED_PIPELINE_ENABLED toggle
   - Scenarios: OFF→ON, stale detection, fallback, instant rollback

10. **Jinja2 Template Validation** (2-3h)
    - Add T3.5.1c: Template rendering parity tests
    - Verify: both text/voice render, conditional blocks, NULL field handling

11. **Fixture Reuse Documentation** (1h)
    - Reference existing fixtures: `async_session`, `mock_embedding_client`, `mock_conversation_factory`
    - Update plan.md Verification Plan section

---

## Acceptance Criteria for Testing Strategy

**For Spec 042 to proceed to implementation, testing strategy MUST achieve**:

- ✅ **All 4 CRITICAL findings resolved**
- ✅ **Pyramid balanced to 70-20-10** (or documented exception approved)
- ✅ **E2E user stories defined** (≥7 scenarios, 40-50 tests)
- ✅ **Mock strategies for LLM** (Haiku fixture, deterministic output)
- ✅ **Async fixture design documented** (phase dependencies, session isolation)
- ✅ **Migration validation tests written** (fact count, embedding quality, search parity)
- ✅ **Test cleanup strategy quantified** (4,000+ target with additions)
- ✅ **Performance benchmarks defined** (<5ms, <100ms, <12s)

---

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `specs/042-unified-pipeline/tasks.md` | MODIFY | Add Phase 6 E2E, revise coverage targets, add AC details |
| `specs/042-unified-pipeline/plan.md` | MODIFY | Add phase dependency documentation, migration validation, performance benchmarks |
| `tests/pipeline/conftest.py` | CREATE | Pipeline fixtures: async_session, mock_haiku, orchestrator, stage mocks |
| `tests/pipeline/test_performance.py` | CREATE | Benchmark tests: <5ms Jinja2, <100ms search, <12s pipeline |
| `tests/memory/test_neo4j_migration.py` | CREATE | Migration validation: fact count, embedding quality, search parity |
| `tests/pipeline/test_e2e_unified.py` | CREATE | E2E scenarios: text→voice, voice→text, dual-platform, rollback |

---

## Summary

Spec 042 testing strategy has **4 CRITICAL failures** that must be fixed before implementation:

1. **No E2E tests** for voice-text parity (critical user flow)
2. **Haiku LLM mock undefined** (will cause flaky/costly tests)
3. **Async fixture design missing** (9-stage orchestration untested)
4. **Migration validation absent** (zero fact loss unverified)

Additionally, **5 HIGH-priority gaps** must be addressed:

- Test cleanup strategy undefined (4,000+ target unclear)
- Performance benchmarks unspecified
- Async context isolation patterns missing
- Test execution dependencies undocumented
- Test pyramid imbalanced (55% unit, 0% E2E vs 70-20-10 target)

**Estimated effort to resolve**: 30-40 hours
- Critical (16-24h)
- High (10-14h)
- Medium (4-6h)

**Recommendation**: Do not proceed to implementation until all CRITICAL findings are resolved and HIGH-priority items documented. This will prevent implementation rework and test suite cleanup delays.

---

## Next Steps

1. **User reviews findings** and approves scope increase (440 → 590 tests)
2. **Planning phase adds E2E scenarios** and fixture designs to tasks.md
3. **Conftest infrastructure created** before Phase 0 implementation starts
4. **Migration validation script written** before Phase 1 begins
5. **Performance test baseline established** before Phase 3
6. **Phase 5 cleanup strategy revised** to maintain 4,000+ coverage
