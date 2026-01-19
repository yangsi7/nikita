# Tasks: 022 Life Simulation Engine

**Spec Version**: 1.0.0
**Created**: 2026-01-12

---

## Progress Summary

| Phase | Tasks | Completed | Status |
|-------|-------|-----------|--------|
| A: Infrastructure | 6 | 6 | ✅ Complete |
| B: Generation | 6 | 6 | ✅ Complete |
| C: Integration | 6 | 6 | ✅ Complete |
| **Total** | **18** | **18** | **100%** |

---

## Phase A: Core Infrastructure

### T001: Create life_simulation module
- **Status**: [x] Complete
- **Estimate**: 30m
- **ACs**:
  - [x] AC-T001.1: Create `nikita/life_simulation/__init__.py`
  - [x] AC-T001.2: Module structure matches spec file layout

### T002: Implement data models
- **Status**: [x] Complete
- **Estimate**: 1h
- **Dependencies**: T001
- **ACs**:
  - [x] AC-T002.1: `LifeEvent` Pydantic model with all fields
  - [x] AC-T002.2: `NarrativeArc` Pydantic model
  - [x] AC-T002.3: Validation for domains and event types
  - [x] AC-T002.4: Unit tests for models (32 tests)

### T003: Add database migrations
- **Status**: [x] Complete
- **Estimate**: 1h
- **Dependencies**: T002
- **ACs**:
  - [x] AC-T003.1: Migration creates `nikita_life_events` table
  - [x] AC-T003.2: Migration creates `nikita_narrative_arcs` table
  - [x] AC-T003.3: Migration creates `nikita_entities` table
  - [x] AC-T003.4: Indexes on user_id, event_date

### T004: Implement EventStore
- **Status**: [x] Complete
- **Estimate**: 1.5h
- **Dependencies**: T003
- **ACs**:
  - [x] AC-T004.1: `EventStore` class with CRUD operations
  - [x] AC-T004.2: `get_events_for_date()` method
  - [x] AC-T004.3: `get_recent_events()` method (7-day lookback)
  - [x] AC-T004.4: Unit tests for store (19 tests)

### T005: Implement MoodCalculator
- **Status**: [x] Complete
- **Estimate**: 1.5h
- **Dependencies**: T002
- **ACs**:
  - [x] AC-T005.1: `MoodCalculator` class
  - [x] AC-T005.2: `compute_from_events()` returns mood dict
  - [x] AC-T005.3: Mood dimensions: arousal, valence, dominance, intimacy
  - [x] AC-T005.4: Correct delta application per event
  - [x] AC-T005.5: Unit tests for calculator (20 tests)

### T006: Phase A tests
- **Status**: [x] Complete
- **Estimate**: 1.5h
- **Dependencies**: T004, T005
- **ACs**:
  - [x] AC-T006.1: Test files in `tests/life_simulation/` (models, store, mood_calculator)
  - [x] AC-T006.2: Coverage > 85% for Phase A modules (71 tests total)

---

## Phase B: Event Generation

### T007: Implement EntityManager
- **Status**: [x] Complete
- **Estimate**: 1.5h
- **Dependencies**: T006
- **ACs**:
  - [x] AC-T007.1: `EntityManager` class manages recurring entities
  - [x] AC-T007.2: `get_entities_by_type()` method
  - [x] AC-T007.3: `seed_entities()` method for new users
  - [x] AC-T007.4: Unit tests for manager (23 tests)

### T008: Create entity seed data
- **Status**: [x] Complete
- **Estimate**: 1h
- **Dependencies**: T007
- **ACs**:
  - [x] AC-T008.1: Seed data for 4 colleagues
  - [x] AC-T008.2: Seed data for 3 friends
  - [x] AC-T008.3: Seed data for 5 recurring places
  - [x] AC-T008.4: Config file `nikita/config_data/life_simulation/entities.yaml`

### T009: Implement EventGenerator
- **Status**: [x] Complete
- **Estimate**: 3h
- **Dependencies**: T007
- **ACs**:
  - [x] AC-T009.1: `EventGenerator` class uses LLM for event creation
  - [x] AC-T009.2: `generate_events_for_day()` returns 3-5 events
  - [x] AC-T009.3: Events distributed across domains
  - [x] AC-T009.4: Events reference known entities
  - [x] AC-T009.5: Emotional impact computed per event
  - [x] AC-T009.6: Unit tests with mocked LLM (22 tests)

### T010: Create event generation prompts
- **Status**: [x] Complete
- **Estimate**: 1.5h
- **Dependencies**: T009
- **ACs**:
  - [x] AC-T010.1: Prompt template for work events
  - [x] AC-T010.2: Prompt template for social events
  - [x] AC-T010.3: Prompt template for personal events
  - [x] AC-T010.4: Prompts reference Nikita's persona consistently (built into EventGenerator._build_generation_prompt())

### T011: Implement NarrativeArcManager
- **Status**: [x] Complete
- **Estimate**: 2h
- **Dependencies**: T009
- **ACs**:
  - [x] AC-T011.1: `NarrativeArcManager` class
  - [x] AC-T011.2: `create_arc()` starts new narrative arc
  - [x] AC-T011.3: `progress_arc()` advances arc state
  - [x] AC-T011.4: `resolve_arc()` ends arc
  - [x] AC-T011.5: Probabilistic resolution (70/20/10)
  - [x] AC-T011.6: Unit tests for arc lifecycle (32 tests)

### T012: Phase B tests
- **Status**: [x] Complete
- **Estimate**: 2h
- **Dependencies**: T009, T011
- **ACs**:
  - [x] AC-T012.1: Test files in `tests/life_simulation/` (entity_manager, event_generator, narrative_manager)
  - [x] AC-T012.2: Coverage > 85% for Phase B modules (77 tests: 23 + 22 + 32)

---

## Phase C: Integration

### T013: Implement LifeSimulator
- **Status**: [x] Complete
- **Estimate**: 2h
- **Dependencies**: T012
- **ACs**:
  - [x] AC-T013.1: `LifeSimulator` class orchestrates all components
  - [x] AC-T013.2: `generate_next_day_events()` full pipeline
  - [x] AC-T013.3: `get_today_events()` for context injection
  - [x] AC-T013.4: Handles new users (entity seeding)
  - [x] AC-T013.5: Unit tests for simulator (31 tests)

### T014: Wire to PostProcessingPipeline
- **Status**: [x] Complete
- **Estimate**: 1h
- **Dependencies**: T013
- **ACs**:
  - [x] AC-T014.1: PostProcessingPipeline calls LifeSimulator
  - [x] AC-T014.2: Events generated after each conversation
  - [x] AC-T014.3: Errors logged but don't fail pipeline

### T015: Update ContextPackage
- **Status**: [x] Complete
- **Estimate**: 30m
- **Dependencies**: T014
- **ACs**:
  - [x] AC-T015.1: `life_events_today` field populated (via LifeSimulator)
  - [x] AC-T015.2: Events formatted as natural language (TimeOfDay: description)
  - [x] AC-T015.3: Top 3 events by importance selected (field_validator)

### T016: Integration tests
- **Status**: [x] Complete
- **Estimate**: 2h
- **Dependencies**: T015
- **ACs**:
  - [x] AC-T016.1: Test full event generation pipeline
  - [x] AC-T016.2: Test context package population
  - [x] AC-T016.3: Test mood derivation from events

### T017: E2E test
- **Status**: [x] Complete
- **Estimate**: 2h
- **Dependencies**: T016
- **ACs**:
  - [x] AC-T017.1: Conversation triggers event generation
  - [x] AC-T017.2: Next conversation has events in context
  - [x] AC-T017.3: Events referenced naturally in responses

### T018: Quality tests
- **Status**: [x] Complete
- **Estimate**: 1.5h
- **Dependencies**: T017
- **ACs**:
  - [x] AC-T018.1: Test event diversity (no domain empty > 2 days)
  - [x] AC-T018.2: Test entity consistency
  - [x] AC-T018.3: Test narrative arc progression

---

## Version History

### v1.0.0 - 2026-01-12
- Initial task breakdown
- 18 tasks with acceptance criteria
