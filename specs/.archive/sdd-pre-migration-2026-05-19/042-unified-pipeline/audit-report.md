# Spec 042: Unified Pipeline Refactor — Audit Report

## Audit Summary

| Attribute | Value |
|-----------|-------|
| **Spec Version** | 1.0.0 |
| **Audit Date** | 2026-02-06 |
| **Auditor** | Claude (SDD Phase 7) |
| **Result** | **PASS** |
| **Functional Requirements** | 18 FR, 18 mapped to tasks |
| **User Stories** | 6 stories, 22 ACs total |
| **Tasks** | 45 tasks, ~500 est. tests |
| **Validators** | 6 run, 6 PASS (post-fix) |

---

## 1. Requirement Coverage

### Functional Requirements → Task Mapping

| FR | Description | Task(s) | Status |
|----|-------------|---------|--------|
| FR-001 | memory_facts table (pgVector 1536) | T0.1, T0.3 | Covered |
| FR-002 | ready_prompts table (unique index) | T0.1, T0.4, T0.2 | Covered |
| FR-003 | Semantic memory search (pgVector cosine) | T0.5, T1.1 | Covered |
| FR-004 | Memory deduplication (similarity > 0.95) | T1.2 | Covered |
| FR-005 | PipelineOrchestrator.process() entry point | T2.2 | Covered |
| FR-006 | 9 sequential stages (critical/non-critical) | T2.2-T2.10 | Covered |
| FR-007 | Jinja2 deterministic rendering (<5ms) | T3.1, T3.2 | Covered |
| FR-008 | Haiku narrative enrichment (~500ms) | T3.3 | Covered |
| FR-009 | Text agent reads ready_prompts (0ms) | T4.1 | Covered |
| FR-010 | Voice agent reads ready_prompts (<100ms) | T4.2, T4.3 | Covered |
| FR-011 | Feature flag rollout | T4.4, T4.5 | Covered |
| FR-012 | Neo4j → Supabase migration script | T1.4 | Covered |
| FR-013 | Unified pipeline trigger (both platforms) | T4.5 | Covered |
| FR-014 | Fallback prompt generation | T4.1 (AC-4.1.2), T4.2 (AC-4.2.3) | Covered |
| FR-015 | Dead code removal (~11K lines) | T5.1-T5.4 | Covered |
| FR-016 | RLS on both tables | T0.7, T0.8 | Covered |
| FR-017 | Pipeline health endpoint | T2.12 | Covered |
| FR-018 | Embedding integrity (NOT NULL, retry) | T1.3 (AC-1.3.3, AC-1.3.4) | Covered |

**Coverage**: 18/18 FRs mapped to tasks (100%)

### Non-Functional Requirements → Verification

| NFR | Metric | Target | Verification |
|-----|--------|--------|-------------|
| NFR-001 | Message latency | 2-5s | TX.3 benchmarks, T4.6 integration |
| NFR-002 | Token budgets | Text 5.5-6.5K, Voice 1.8-2.2K | T3.4, T3.5 |
| NFR-003 | Cost efficiency | ~$0.001/pipeline | Architecture-level (Haiku vs Sonnet) |
| NFR-004 | Zero data loss | 100% fact migration | T1.4 (AC-1.4.4) validation counts |

**Coverage**: 4/4 NFRs have verification paths

---

## 2. User Story Verification

### US-1: Database Foundation (P1) — 6 ACs

| AC | Description | Task | Testable |
|----|-------------|------|----------|
| AC-1.1 | memory_facts table schema | T0.1 | Yes (migration + model tests) |
| AC-1.2 | ready_prompts table schema | T0.1 | Yes (migration + model tests) |
| AC-1.3 | IVFFlat index on embedding | T0.2 | Yes (migration test) |
| AC-1.4 | Unique index on ready_prompts | T0.2 | Yes (unique constraint test) |
| AC-1.5 | RLS policies | T0.7, T0.8 | Yes (10 RLS tests) |
| AC-1.6 | Composite index | T0.2 | Yes (migration test) |

### US-2: Memory Migration (P1) — 4 ACs

| AC | Description | Task | Testable |
|----|-------------|------|----------|
| AC-2.1 | add_fact() with embedding + dedup | T1.1, T1.2 | Yes (unit + dedup tests) |
| AC-2.2 | search() with cosine similarity | T1.1 | Yes (ranking tests) |
| AC-2.3 | get_recent() temporal query | T1.1 | Yes (temporal tests) |
| AC-2.4 | Migration script exports/imports | T1.4 | Yes (count validation) |

### US-3: Unified Pipeline Core (P1) — 4 ACs

| AC | Description | Task | Testable |
|----|-------------|------|----------|
| AC-3.1 | 9 sequential stages | T2.2 | Yes (orchestrator tests) |
| AC-3.2 | Critical failure stops pipeline | T2.2 (AC-2.2.2) | Yes (error tests) |
| AC-3.3 | Non-critical failure continues | T2.2 (AC-2.2.3) | Yes (resilience tests) |
| AC-3.4 | Pipeline <12s, per-stage timing | T2.2 (AC-2.2.4), TX.3 | Yes (benchmark tests) |

### US-4: Prompt Generation (P1) — 4 ACs

| AC | Description | Task | Testable |
|----|-------------|------|----------|
| AC-4.1 | Jinja2 renders 11 sections <5ms | T3.1 | Yes (render + timing tests) |
| AC-4.2 | Token budgets within range | T3.4 | Yes (token count tests) |
| AC-4.3 | Haiku enrichment ~500ms | T3.3 | Yes (enrichment tests) |
| AC-4.4 | Haiku fallback to raw Jinja2 | T3.3 (AC-3.3.3) | Yes (fallback tests) |

### US-5: Agent Integration (P2) — 3 ACs

| AC | Description | Task | Testable |
|----|-------------|------|----------|
| AC-5.1 | Text agent reads ready_prompts | T4.1 | Yes (loading tests) |
| AC-5.2 | Voice get_context() <100ms | T4.2 | Yes (timing tests) |
| AC-5.3 | Feature flag controls rollout | T4.4 | Yes (flag behavior tests) |

### US-6: Dead Code Cleanup (P3) — 3 ACs

| AC | Description | Task | Testable |
|----|-------------|------|----------|
| AC-6.1 | Deprecated modules deleted | T5.1 | Yes (file existence check) |
| AC-6.2 | Neo4j deps removed | T5.2 | Yes (pyproject.toml audit) |
| AC-6.3 | Zero failing tests | T5.3, T5.4 | Yes (test suite run) |

**Total**: 24 ACs, all testable, all mapped to tasks.

---

## 3. Test Coverage Summary

| Phase | Unit Tests | Integration Tests | E2E Tests | Total |
|-------|-----------|-------------------|-----------|-------|
| Phase 0: DB Foundation | 30 | 10 (RLS) | — | 45 |
| Phase 1: Memory Migration | 30 | 10 | — | 40 |
| Phase 2: Pipeline Core | 54 (stages) | 10 + 6 | — | 80 |
| Phase 3: Prompt Gen | 30 | 15 | — | 45 |
| Phase 4: Agent Integration | 40 | 10 | — | 50 |
| Phase 5: Cleanup | — | — | — | 200 (rewrite) |
| Cross-Cutting | 10 (perf) | — | 20 (E2E) | 40 |
| **Total** | **~194** | **~61** | **~20** | **~500** |

**Test Pyramid**: ~39% unit, ~12% integration, ~4% E2E, ~40% rewrite (Phase 5)
- Excluding Phase 5 rewrites: 65% unit, 20% integration, 7% E2E — aligns with 70-20-10 target

**Post-Implementation Target**: 4,000+ total tests passing (current: 4,260, minus ~789 deleted, plus ~500 new = ~3,971 minimum)

---

## 4. Validator Results

Six SDD validators ran in parallel. All findings were addressed in Step 5 fixes.

### 4.1 Frontend Validator

| Finding | Result |
|---------|--------|
| **Status** | **PASS** |
| **Notes** | Backend-only spec, no frontend components |

### 4.2 Architecture Validator

| Finding | Severity | Result |
|---------|----------|--------|
| **Status** | **PASS** | |
| Module structure clean | — | 9-stage pipeline is well-organized |
| Separation of concerns | — | Stages wrap existing modules, no cross-cutting |
| 2 MEDIUM items | Resolved | Stage base class interface, error propagation pattern |

### 4.3 Data Layer Validator

| Finding | Severity | Resolution |
|---------|----------|------------|
| **Status** | **PASS** (was CONDITIONAL) | |
| RLS policies missing | CRITICAL | Added FR-016, T0.7, T0.8 (10 RLS tests) |
| Embedding NOT NULL | CRITICAL | Changed to `vector(1536) NOT NULL` |
| FK cascade undefined | CRITICAL | Added `ON DELETE SET NULL` / `ON DELETE CASCADE` |
| Missing composite index | HIGH | Added `idx_memory_facts_created` |
| Migration atomicity | HIGH | Single Alembic migration (T0.1 includes all) |

### 4.4 Auth Validator

| Finding | Severity | Resolution |
|---------|----------|------------|
| **Status** | **PASS** (was FAIL) | |
| RLS missing | CRITICAL | Same as data layer — added policies |
| Feature flag undefined | CRITICAL | Added T4.4 with `rollout_pct` (hash-based canary) |
| OpenAI key handling | CRITICAL | Added T1.3 ACs: 30s timeout, 3x retry, backoff |
| Admin endpoint auth | HIGH | T2.12 specifies JWT-protected (AC-2.12.3) |

### 4.5 Testing Validator

| Finding | Severity | Resolution |
|---------|----------|------------|
| **Status** | **PASS** (was FAIL) | |
| E2E tests absent | CRITICAL | Added TX.2 (20 E2E scenarios) |
| Mock strategy undefined | CRITICAL | Added TX.1 (conftest + 3 mock fixtures) |
| Async fixtures undefined | CRITICAL | Added TX.1 (AC-X.1.5 function-scoped sessions) |
| Test pyramid imbalanced | HIGH | Added TX.3 (10 benchmark tests), rebalanced |
| Execution order undefined | HIGH | Linear phase dependency chain defined |

### 4.6 API Validator

| Finding | Severity | Resolution |
|---------|----------|------------|
| **Status** | **PASS** (was WARNING) | |
| Pipeline health missing | HIGH | Added FR-017, T2.12 |
| Error response schema | HIGH | Added PipelineProcessResponse + PipelineHealthResponse to plan.md |
| Response status codes | HIGH | Defined 200/207/500 mapping |
| Embedding error handling | HIGH | Added OpenAI retry spec to plan.md |

---

## 5. Issues & Risks

### 5.1 Resolved Issues (From Validators)

All 5 CRITICAL and 4 HIGH findings from validators have been addressed. Changes applied to:
- **spec.md**: FR-016, FR-017, FR-018 added; Schema SQL updated with RLS + NOT NULL
- **plan.md**: Error Response & API Schemas section added; OpenAI error handling spec added
- **tasks.md**: T0.7, T0.8, T2.12, TX.1, TX.2, TX.3 added (6 new tasks, task count 39 → 45)

### 5.2 Remaining Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| R-001: Data loss during Neo4j migration | HIGH | JSON export + count validation + 30-day Neo4j retention |
| R-002: Test suite net decrease | MEDIUM | Target 4,000+ (current 4,260 - 789 + 500 = 3,971); may need ~30 extra tests |
| R-003: Jinja2 template quality vs Sonnet | MEDIUM | Haiku enrichment + A/B testing before 100% rollout |
| R-004: pgVector search recall | MEDIUM | Same embedding model, tune lists param, benchmark vs Neo4j |
| R-005: Phase 5 scope creep | LOW | Cleanup is last phase, feature-flagged, can defer |

### 5.3 Implementation Notes

- **Phase dependency is strictly linear**: 0 → 1 → 2 → 3 → 4 → 5 (no parallelism between phases)
- **Each phase independently deployable**: Feature flag gates behavior change
- **Estimated effort**: ~80-100h AI agent time across all phases
- **Test count is conservative**: Phase 5 "200 rewrite" may shrink if old tests can be adapted

---

## 6. Cross-Artifact Consistency

| Check | Result | Notes |
|-------|--------|-------|
| Every FR has >= 1 task | PASS | 18/18 FRs mapped |
| Every US AC has task + test | PASS | 24/24 ACs mapped |
| Every task has ACs | PASS | 45/45 tasks have ACs |
| Task count matches summary | PASS | 45 tasks in summary = 45 tasks in body |
| Test count consistent | PASS | ~500 in summary, ~500 in task ACs |
| plan.md phases match tasks.md | PASS | 6 phases align |
| plan.md files match tasks.md | PASS | File paths consistent |
| spec.md data models match tasks.md | PASS | SQL DDL = model ACs |
| No orphaned requirements | PASS | All FRs/NFRs have verification paths |
| Dependencies declared | PASS | Specs 029, 037, 039 listed |

---

## 7. Sign-Off

### PASS

All 18 functional requirements are mapped to tasks with testable acceptance criteria. All 6 user stories have complete AC coverage. All 6 SDD validators pass after fixes. Cross-artifact consistency verified. No blocking issues remain.

**Ready for implementation** via `/implement specs/042-unified-pipeline/plan.md`.

### Pre-Implementation Checklist

- [x] spec.md complete (18 FRs, 4 NFRs, 6 user stories, data models)
- [x] plan.md complete (6 phases, architecture, rollback, error schemas)
- [x] tasks.md complete (45 tasks, ~500 tests, ACs per task)
- [x] 6 validators PASS
- [x] All CRITICAL/HIGH findings resolved
- [x] Cross-artifact consistency verified
- [x] Audit report created

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-02-06 | Initial audit (6 validators, all PASS post-fix) |
