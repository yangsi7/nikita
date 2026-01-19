# Implementation Plan: 021 Hierarchical Prompt Composition

**Spec Version**: 1.0.0
**Plan Version**: 1.0.0
**Created**: 2026-01-12

---

## Executive Summary

This plan implements the Hierarchical Prompt Composition system with 6 prompt layers and async post-processing. The implementation is organized into 4 phases across 8 user stories, with a total of ~25 tasks.

**Key Architecture Decision**: Use Supabase JSONB for context package storage (simpler, sufficient performance for MVP).

---

## Implementation Phases

### Phase A: Foundation (US-1, US-2)
**Goal**: Core infrastructure for context packages and base personality

| Task | Description | Estimate | Dependencies |
|------|-------------|----------|--------------|
| T001 | Create `nikita/context/` module structure | 30m | None |
| T002 | Implement `ContextPackage` Pydantic model | 1h | T001 |
| T003 | Implement `PackageStore` with Supabase JSONB | 2h | T002 |
| T004 | Add `context_packages` table migration | 30m | T003 |
| T005 | Implement `Layer1Loader` (base personality) | 1h | T001 |
| T006 | Create base personality config file | 1h | T005 |

**Deliverable**: Context package storage + Layer 1 working

### Phase B: Pre-computed Layers (US-3, US-4, US-5)
**Goal**: Implement Layers 2-4 with pre-computation logic

| Task | Description | Estimate | Dependencies |
|------|-------------|----------|--------------|
| T007 | Implement `Layer2Composer` (chapter layer) | 2h | T006 |
| T008 | Implement `Layer3Composer` (emotional state stub) | 2h | T007 |
| T009 | Implement `Layer4Computer` (situation analysis) | 2h | T008 |
| T010 | Create chapter behavior config files | 1h | T007 |
| T011 | Create situation scenario config files | 1h | T009 |
| T012 | Unit tests for Layers 2-4 | 2h | T007-T009 |

**Deliverable**: All pre-computed layers functional

### Phase C: Composition & Injection (US-6, US-7)
**Goal**: Full prompt composition with real-time injection

| Task | Description | Estimate | Dependencies |
|------|-------------|----------|--------------|
| T013 | Implement `HierarchicalPromptComposer` | 3h | T012 |
| T014 | Implement `Layer5Injector` (context injection) | 2h | T013 |
| T015 | Implement `Layer6Handler` (on-the-fly mods) | 2h | T014 |
| T016 | Implement `TokenValidator` | 1h | T013 |
| T017 | Integration tests for composer | 2h | T013-T016 |
| T018 | Performance tests (latency validation) | 1h | T017 |

**Deliverable**: Full composition flow working

### Phase D: Post-Processing Pipeline (US-8)
**Goal**: Async pipeline that prepares context for next conversation

| Task | Description | Estimate | Dependencies |
|------|-------------|----------|--------------|
| T019 | Create `nikita/post_processing/` module | 30m | T018 |
| T020 | Implement `PostProcessingPipeline` orchestrator | 2h | T019 |
| T021 | Implement `GraphUpdater` (existing Graphiti) | 1h | T020 |
| T022 | Implement `SummaryGenerator` (existing logic) | 1h | T020 |
| T023 | Implement `LayerComposer` (pre-compose 2-4) | 2h | T020, T012 |
| T024 | Wire pipeline trigger after conversation save | 1h | T020 |
| T025 | Integration tests for pipeline | 2h | T024 |
| T026 | E2E test: conversation → post-process → next conv | 2h | T025 |

**Deliverable**: Full system operational

---

## Parallel Execution Map

```
Week 1: Foundation
├── [P] T001, T005 (module structure, Layer 1 loader)
├── [S] T002 → T003 → T004 (package model → store → migration)
└── [S] T006 (base personality config)

Week 2: Layers
├── [S] T007 → T008 → T009 (Layers 2 → 3 → 4)
├── [P] T010, T011 (config files)
└── [S] T012 (unit tests)

Week 3: Composition
├── [S] T013 → T014 → T015 (composer → injection → on-the-fly)
├── [P] T016 (token validator)
└── [S] T017 → T018 (integration + perf tests)

Week 4: Pipeline
├── [S] T019 → T020 → T024 (module → orchestrator → trigger)
├── [P] T021, T022, T023 (graph, summary, layer composer)
└── [S] T025 → T026 (integration + E2E tests)
```

---

## Technical Decisions

### TD-001: Storage Backend
**Decision**: Supabase JSONB for context packages
**Rationale**:
- No new infrastructure (already have Supabase)
- Latency acceptable for <50KB packages
- Can migrate to Redis later if needed

### TD-002: Token Budget Enforcement
**Decision**: Hard enforcement with graceful degradation
**Rationale**:
- If layer exceeds budget, truncate with warning log
- Never exceed total 4000 token budget
- Monitor truncation rate for tuning

### TD-003: Post-Processing Trigger
**Decision**: Use FastAPI BackgroundTasks (existing pattern)
**Rationale**:
- Consistent with current architecture
- No new dependencies
- Retry via pg_cron fallback job

### TD-004: Layer 3 Stub
**Decision**: Stub emotional state until Spec 023 complete
**Rationale**:
- Allows parallel development
- Stub returns neutral state (0.5 for all dimensions)
- Interface defined, implementation pluggable

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Latency exceeds 150ms | Medium | High | Performance test early (T018), optimize or add Redis |
| Token budget overflow | Low | Medium | Hard enforcement in TokenValidator |
| Post-processing failures | Low | Medium | Retry mechanism + pg_cron fallback |
| Layer composition complexity | Medium | Medium | Keep layers independent, clear interfaces |

---

## Integration Points

### Existing Code Changes

| File | Change Type | Description |
|------|-------------|-------------|
| `nikita/agents/text/agent.py` | Modify | Replace MetaPromptService call with HierarchicalPromptComposer |
| `nikita/db/repositories/conversation_repository.py` | Modify | Add post-processing trigger after save |
| `nikita/meta_prompts/service.py` | Deprecate | Keep as fallback, add feature flag |

### New Dependencies (Specs 022-024)

| Dependency | Used By | Status |
|------------|---------|--------|
| LifeSimulator (022) | PostProcessingPipeline | STUB until 022 |
| EmotionalStateEngine (023) | Layer3Composer | STUB until 023 |
| BehavioralMetaInstructions (024) | Layer4Computer | STUB until 024 |

---

## Definition of Done

- [ ] All 26 tasks completed
- [ ] Unit test coverage > 90% for new modules
- [ ] Integration tests passing
- [ ] Performance tests: P99 < 150ms for context injection
- [ ] E2E test: full conversation cycle working
- [ ] Feature flag `use_hierarchical_composer` operational
- [ ] Documentation updated (memory/architecture.md)

---

## Version History

### v1.0.0 - 2026-01-12
- Initial implementation plan
- 26 tasks across 4 phases
- Parallel execution map defined
