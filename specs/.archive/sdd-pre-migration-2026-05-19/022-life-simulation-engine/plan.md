# Implementation Plan: 022 Life Simulation Engine

**Spec Version**: 1.0.0
**Plan Version**: 1.0.0
**Created**: 2026-01-12

---

## Executive Summary

This plan implements the Life Simulation Engine that generates daily events for Nikita across work, social, and personal domains. Implementation organized into 3 phases with ~20 tasks.

---

## Implementation Phases

### Phase A: Core Infrastructure (US-1, US-5)
**Goal**: Event models, storage, and mood calculation

| Task | Description | Estimate | Dependencies |
|------|-------------|----------|--------------|
| T001 | Create `nikita/life_simulation/` module | 30m | None |
| T002 | Implement `LifeEvent` and `NarrativeArc` models | 1h | T001 |
| T003 | Add database migrations (3 tables) | 1h | T002 |
| T004 | Implement `EventStore` (Supabase) | 1.5h | T003 |
| T005 | Implement `MoodCalculator` | 1.5h | T002 |
| T006 | Unit tests for models and calculator | 1.5h | T004, T005 |

### Phase B: Event Generation (US-2, US-3, US-4)
**Goal**: LLM-based event generation for all domains

| Task | Description | Estimate | Dependencies |
|------|-------------|----------|--------------|
| T007 | Implement `EntityManager` | 1.5h | T006 |
| T008 | Create entity seed data (colleagues, friends, places) | 1h | T007 |
| T009 | Implement `EventGenerator` (LLM-based) | 3h | T007 |
| T010 | Create event generation prompts | 1.5h | T009 |
| T011 | Implement `NarrativeArcManager` | 2h | T009 |
| T012 | Unit tests for generation | 2h | T009, T011 |

### Phase C: Integration (US-6, US-7)
**Goal**: Wire to post-processing pipeline and context package

| Task | Description | Estimate | Dependencies |
|------|-------------|----------|--------------|
| T013 | Implement `LifeSimulator` orchestrator | 2h | T012 |
| T014 | Wire to PostProcessingPipeline (021) | 1h | T013 |
| T015 | Update ContextPackage with life_events_today | 30m | T014 |
| T016 | Integration tests for pipeline | 2h | T015 |
| T017 | E2E test: event generation → context injection | 2h | T016 |
| T018 | Quality tests (diversity, authenticity) | 1.5h | T017 |

---

## Technical Decisions

### TD-001: Event Generation Method
**Decision**: LLM-based generation with structured prompts
**Rationale**: Natural language events feel authentic; templates feel robotic

### TD-002: Entity Seeding
**Decision**: Pre-seed entities per user at game start
**Rationale**: Consistency from day 1; entities evolve but don't appear randomly

### TD-003: Narrative Arc Resolution
**Decision**: Probabilistic resolution (70% resolve, 20% fade, 10% escalate)
**Rationale**: Realistic arc endings without guaranteed drama

---

## Definition of Done

- [ ] All 18 tasks completed
- [ ] Database migrations applied
- [ ] Unit test coverage > 85%
- [ ] Integration with PostProcessingPipeline working
- [ ] E2E test passing
- [ ] 40%+ life mention rate achievable

---

## Version History

### v1.0.0 - 2026-01-12
- Initial implementation plan
- 18 tasks across 3 phases
