# Spec 055: Implementation Plan

**Spec**: Life Simulation Enhanced
**Estimated tasks**: 22
**Estimated days**: 4-5
**Feature flag**: `life_sim_enhanced`

---

## Phase 1: Foundation (Day 1)

### 1.1 Data Models & Config
- Add `WeeklyRoutine` and `DayRoutine` Pydantic models to `life_simulation/models.py`
- Create `nikita/config_data/life_simulation/routine.yaml` with default weekly schedule
- Add routine loader with YAML parsing and validation
- Add `life_sim_enhanced` feature flag to `settings.py`

### 1.2 Database Migrations
- Migration 1: `users.routine_config JSONB DEFAULT '{}'`, `users.meta_instructions JSONB DEFAULT '{}'`
- Migration 2: `user_social_circles.last_event TIMESTAMPTZ`, `user_social_circles.sentiment TEXT DEFAULT 'neutral'`

### 1.3 NPC Mapping Setup
- Update `entities.yaml`: rename Max -> Max K., remove Ana (redirect to Lena)
- Create NPC name resolution helper: given a character name, find it in `user_social_circles` or `nikita_entities`

**Deliverables**: Models, config, migrations, feature flag
**Tests**: 8-10 unit tests for models and routine loading

---

## Phase 2: Routine-Aware Event Generation (Day 2)

### 2.1 EventGenerator Enhancement
- Add `routine` and `mood_state` optional params to `generate_events_for_day()`
- Add routine context section to `_build_generation_prompt()`
- Add mood bias section to `_build_generation_prompt()`
- Ensure defaults preserve existing behavior (flag OFF = no change)

### 2.2 Simulator Pipeline Update
- Modify `generate_next_day_events()` to compute mood first
- Load routine for target date's day of week
- Pass mood + routine to EventGenerator
- Gate all new logic behind `life_sim_enhanced` flag

**Deliverables**: Enhanced event generation with routine + mood awareness
**Tests**: 6-8 tests for prompt injection, mood bias, routine context

---

## Phase 3: NPC Consolidation (Day 3)

### 3.1 NPC State Tracking
- Add `update_npc_from_event()` method to store or simulator
- Implement sentiment computation from event emotional impact
- Update `user_social_circles.last_event` and `sentiment` when NPCs referenced

### 3.2 Entity Manager Integration
- Add NPC name resolution: check `user_social_circles` first, fall back to `nikita_entities`
- Enhance `get_entity_context()` to merge social circle + entity data
- Lazy NPC init: create `user_social_circles` row on first reference if not exists

### 3.3 Arc System Integration
- Update `NarrativeArcSystem` to check `user_social_circles` for NPC metadata
- Arc character lookup falls through: social_circle -> hardcoded template -> skip

**Deliverables**: Single NPC source of truth with dynamic state
**Tests**: 8-10 tests for NPC resolution, state updates, lazy init

---

## Phase 4: Integration & Testing (Day 4)

### 4.1 LifeSimStage Integration
- Verify `LifeSimStage` works with enhanced simulator (no changes needed — transparent)
- Test feature flag ON/OFF behavior in pipeline context

### 4.2 Regression Testing
- Run full test suite: `pytest tests/life_simulation/ -v`
- Ensure all existing tests pass with flag OFF
- Add integration test: full day generation with routine + mood + NPC updates

### 4.3 Edge Cases
- Missing routine config (fallback to default)
- No mood data available (skip mood bias)
- Unknown NPC name in event (skip NPC update)
- Empty social circle (lazy init creates on first reference)

**Deliverables**: All tests passing, feature flag verified
**Tests**: 4-6 integration tests + regression verification

---

## Phase 5: Polish & Cleanup (Day 5, if needed)

### 5.1 Documentation
- Update `nikita/life_simulation/__init__.py` exports
- Update module CLAUDE.md if exists

### 5.2 Code Quality
- Ensure type hints complete
- Log all significant operations (structlog)
- Verify no breaking changes to existing callers

---

## Task Effort Estimates

| Phase | Tasks | Estimated Hours |
|-------|-------|-----------------|
| Phase 1: Foundation | 7 | 4-5h |
| Phase 2: Event Generation | 5 | 3-4h |
| Phase 3: NPC Consolidation | 6 | 4-5h |
| Phase 4: Integration | 3 | 2-3h |
| Phase 5: Polish | 1 | 1h |
| **Total** | **22** | **14-18h** |

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| NPC name collisions in prompts | 60% | MEDIUM | Explicit mapping table; Max -> Max K. rename; Ana deprecated |
| Bidirectional mood feedback loop | 30% | MEDIUM | Mood from PREVIOUS day only; no same-day feedback |
| Existing test breakage | 20% | HIGH | Feature flag OFF preserves all current behavior; new params have safe defaults |
| LLM prompt quality with routine context | 40% | LOW | Routine context is additive to existing prompt; can be removed without side effects |

---

## Dependencies

```
Phase 1 (foundation)
  |
  +---> Phase 2 (event gen) --+
  |                            |
  +---> Phase 3 (NPC)  -------+--> Phase 4 (integration) --> Phase 5 (polish)
```

Phases 2 and 3 can run in parallel after Phase 1.

---

## Testing Strategy

### Unit Tests (per phase)
- **Phase 1**: `WeeklyRoutine.from_yaml()`, `DayRoutine` validation, routine loader, feature flag
- **Phase 2**: Prompt injection with routine, prompt injection with mood, domain distribution bias
- **Phase 3**: NPC name resolution, sentiment computation, lazy init, entity context merge

### Integration Tests
- Full `generate_next_day_events()` with all new params
- Pipeline `LifeSimStage` with enhanced simulator
- NPC state update after event generation

### Mock Strategy
- LLM calls: inject `llm_client` callable returning predefined `GeneratedEventList`
- DB calls: use in-memory store or mock `EventStore` methods
- Feature flag: parametrize tests with flag ON/OFF
