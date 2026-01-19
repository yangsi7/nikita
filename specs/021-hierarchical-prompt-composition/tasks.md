# Tasks: 021 Hierarchical Prompt Composition

**Spec Version**: 1.0.0
**Plan Version**: 1.0.0
**Created**: 2026-01-12

---

## Progress Summary

| Phase | User Story | Tasks | Completed | Status |
|-------|------------|-------|-----------|--------|
| A | US-1: Pre-computed Packages | 4 | 4 | ✅ Complete |
| A | US-2: Base Personality | 2 | 2 | ✅ Complete |
| B | US-3: Chapter Layer | 2 | 2 | ✅ Complete |
| B | US-4: Emotional State | 1 | 1 | ✅ Complete |
| B | US-5: Situation Layer | 2 | 2 | ✅ Complete |
| B | - | 1 | 1 | ✅ Complete |
| C | US-6: Context Injection | 2 | 2 | ✅ Complete |
| C | US-7: On-the-Fly | 1 | 1 | ✅ Complete |
| C | - | 3 | 3 | ✅ Complete |
| D | US-8: Post-Processing | 8 | 8 | ✅ Complete |
| **Total** | | **26** | **26** | **100%** |

---

## Phase A: Foundation

### US-1: Pre-computed Context Packages

#### T001: Create context module structure
- **Status**: [ ] Pending
- **Estimate**: 30m
- **Dependencies**: None
- **ACs**:
  - [x] AC-T001.1: Create `nikita/context/__init__.py`
  - [x] AC-T001.2: Create `nikita/context/layers/` directory
  - [x] AC-T001.3: Module importable from `nikita.context`

#### T002: Implement ContextPackage model
- **Status**: [ ] Pending
- **Estimate**: 1h
- **Dependencies**: T001
- **ACs**:
  - [ ] AC-T002.1: `ContextPackage` Pydantic model with all fields from spec
  - [ ] AC-T002.2: Serialization to/from JSON working
  - [ ] AC-T002.3: Validation for required fields
  - [ ] AC-T002.4: Unit tests for model

#### T003: Implement PackageStore
- **Status**: [ ] Pending
- **Estimate**: 2h
- **Dependencies**: T002
- **ACs**:
  - [ ] AC-T003.1: `PackageStore` class with `get()` and `set()` methods
  - [ ] AC-T003.2: Supabase JSONB storage implementation
  - [ ] AC-T003.3: TTL support (24h default)
  - [ ] AC-T003.4: `get()` completes in <50ms (mocked test)
  - [ ] AC-T003.5: Unit tests for store operations

#### T004: Add context_packages table migration
- **Status**: [ ] Pending
- **Estimate**: 30m
- **Dependencies**: T003
- **ACs**:
  - [ ] AC-T004.1: Migration creates `context_packages` table
  - [ ] AC-T004.2: Columns: `user_id`, `package`, `created_at`, `expires_at`
  - [ ] AC-T004.3: Index on `user_id`
  - [ ] AC-T004.4: RLS policy for user isolation

### US-2: Base Personality Layer

#### T005: Implement Layer1Loader
- **Status**: [ ] Pending
- **Estimate**: 1h
- **Dependencies**: T001
- **ACs**:
  - [ ] AC-T005.1: `Layer1Loader` class loads base personality from config
  - [ ] AC-T005.2: Caching mechanism (load once, reuse)
  - [ ] AC-T005.3: Token count validation (~2000 tokens)
  - [ ] AC-T005.4: Unit tests for loader

#### T006: Create base personality config
- **Status**: [ ] Pending
- **Estimate**: 1h
- **Dependencies**: T005
- **ACs**:
  - [ ] AC-T006.1: `nikita/config_data/prompts/base_personality.yaml`
  - [ ] AC-T006.2: Content includes: core traits, values, speaking style, backstory
  - [ ] AC-T006.3: Token count within budget (~2000)
  - [ ] AC-T006.4: Versioned (v1.0.0 in file)

---

## Phase B: Pre-computed Layers

### US-3: Chapter Layer

#### T007: Implement Layer2Composer
- **Status**: [ ] Pending
- **Estimate**: 2h
- **Dependencies**: T006
- **ACs**:
  - [ ] AC-T007.1: `Layer2Composer` class generates chapter-specific prompt
  - [ ] AC-T007.2: Accepts chapter number (1-5) as input
  - [ ] AC-T007.3: Output includes intimacy level, disclosure patterns, behaviors
  - [ ] AC-T007.4: Token count within budget (~300)
  - [ ] AC-T007.5: Unit tests for each chapter

#### T010: Create chapter behavior configs
- **Status**: [ ] Pending
- **Estimate**: 1h
- **Dependencies**: T007
- **ACs**:
  - [ ] AC-T010.1: `nikita/config_data/prompts/chapters/` directory
  - [ ] AC-T010.2: Config files for chapters 1-5
  - [ ] AC-T010.3: Each config defines behavioral overlays
  - [ ] AC-T010.4: Consistent schema across all chapters

### US-4: Emotional State Layer

#### T008: Implement Layer3Composer (stub)
- **Status**: [ ] Pending
- **Estimate**: 2h
- **Dependencies**: T007
- **ACs**:
  - [ ] AC-T008.1: `Layer3Composer` class generates emotional state prompt
  - [ ] AC-T008.2: Accepts `EmotionalState` as input
  - [ ] AC-T008.3: STUB implementation returns neutral state (0.5 all dimensions)
  - [ ] AC-T008.4: Interface ready for Spec 023 integration
  - [ ] AC-T008.5: Token count within budget (~150)
  - [ ] AC-T008.6: Unit tests for composer

### US-5: Situation Layer

#### T009: Implement Layer4Computer
- **Status**: [ ] Pending
- **Estimate**: 2h
- **Dependencies**: T008
- **ACs**:
  - [ ] AC-T009.1: `Layer4Computer` class analyzes conversation context
  - [ ] AC-T009.2: Determines situation type: morning, evening, after-gap, mid-conversation
  - [ ] AC-T009.3: Generates situational meta-instructions
  - [ ] AC-T009.4: Token count within budget (~150)
  - [ ] AC-T009.5: Unit tests for each situation type

#### T011: Create situation scenario configs
- **Status**: [ ] Pending
- **Estimate**: 1h
- **Dependencies**: T009
- **ACs**:
  - [ ] AC-T011.1: `nikita/config_data/prompts/situations/` directory
  - [ ] AC-T011.2: Config files for: morning, evening, after_gap, mid_conversation
  - [ ] AC-T011.3: Each config defines behavioral nudges
  - [ ] AC-T011.4: Nudges are high-level (not specific responses)

### Phase B Tests

#### T012: Unit tests for Layers 2-4
- **Status**: [ ] Pending
- **Estimate**: 2h
- **Dependencies**: T007, T008, T009
- **ACs**:
  - [ ] AC-T012.1: Test file `tests/context/test_layers.py`
  - [ ] AC-T012.2: Tests for Layer2Composer (all 5 chapters)
  - [ ] AC-T012.3: Tests for Layer3Composer (stub behavior)
  - [ ] AC-T012.4: Tests for Layer4Computer (all 4 situations)
  - [ ] AC-T012.5: Coverage > 90% for layers module

---

## Phase C: Composition & Injection

### US-6: Context Injection Layer

#### T013: Implement HierarchicalPromptComposer
- **Status**: [ ] Pending
- **Estimate**: 3h
- **Dependencies**: T012
- **ACs**:
  - [ ] AC-T013.1: `HierarchicalPromptComposer` class orchestrates all layers
  - [ ] AC-T013.2: `compose()` method returns `ComposedPrompt`
  - [ ] AC-T013.3: Loads context package and injects into prompt
  - [ ] AC-T013.4: Graceful degradation when package unavailable
  - [ ] AC-T013.5: Logs layer breakdown for debugging
  - [ ] AC-T013.6: Unit tests for composer

#### T014: Implement Layer5Injector
- **Status**: [ ] Pending
- **Estimate**: 2h
- **Dependencies**: T013
- **ACs**:
  - [ ] AC-T014.1: `Layer5Injector` class injects context from package
  - [ ] AC-T014.2: Formats user_facts, relationship_events, active_threads, summaries
  - [ ] AC-T014.3: Token count within budget (~500)
  - [ ] AC-T014.4: Unit tests for injector

### US-7: On-the-Fly Modifications

#### T015: Implement Layer6Handler
- **Status**: [ ] Pending
- **Estimate**: 2h
- **Dependencies**: T014
- **ACs**:
  - [ ] AC-T015.1: `Layer6Handler` class handles mid-conversation modifications
  - [ ] AC-T015.2: Supports mood_shift and memory_retrieval triggers
  - [ ] AC-T015.3: Memory retrieval via Graphiti
  - [ ] AC-T015.4: Latency < 200ms per modification
  - [ ] AC-T015.5: Unit tests for handler

### Phase C Infrastructure

#### T016: Implement TokenValidator
- **Status**: [ ] Pending
- **Estimate**: 1h
- **Dependencies**: T013
- **ACs**:
  - [ ] AC-T016.1: `TokenValidator` class counts tokens via tiktoken
  - [ ] AC-T016.2: Validates total prompt < 4000 tokens
  - [ ] AC-T016.3: Truncates layers that exceed budget with warning
  - [ ] AC-T016.4: Unit tests for validator

#### T017: Integration tests for composer
- **Status**: [ ] Pending
- **Estimate**: 2h
- **Dependencies**: T013, T014, T015, T016
- **ACs**:
  - [ ] AC-T017.1: Test file `tests/context/test_composer_integration.py`
  - [ ] AC-T017.2: Test full composition with mock package
  - [ ] AC-T017.3: Test degradation scenario (no package)
  - [ ] AC-T017.4: Test Layer 6 modifications

#### T018: Performance tests
- **Status**: [ ] Pending
- **Estimate**: 1h
- **Dependencies**: T017
- **ACs**:
  - [ ] AC-T018.1: Test file `tests/context/test_composer_performance.py`
  - [ ] AC-T018.2: Context injection P99 < 150ms
  - [ ] AC-T018.3: Package load P99 < 50ms
  - [ ] AC-T018.4: Run with realistic data sizes

---

## Phase D: Post-Processing Pipeline

### US-8: Post-Processing Pipeline

#### T019: Create post_processing module
- **Status**: [x] Complete
- **Estimate**: 30m
- **Dependencies**: T018
- **ACs**:
  - [x] AC-T019.1: Create `nikita/post_processing/__init__.py`
  - [x] AC-T019.2: Module importable from `nikita.post_processing`

#### T020: Implement PostProcessingPipeline
- **Status**: [x] Complete
- **Estimate**: 2h
- **Dependencies**: T019
- **ACs**:
  - [x] AC-T020.1: `PostProcessingPipeline` class orchestrates all steps
  - [x] AC-T020.2: `process()` method runs all steps in sequence
  - [x] AC-T020.3: Returns `ProcessingResult` with step status
  - [x] AC-T020.4: Error handling with partial completion support
  - [x] AC-T020.5: Unit tests for pipeline (18 tests)

#### T021: Implement GraphUpdater
- **Status**: [x] Complete
- **Estimate**: 1h
- **Dependencies**: T020
- **ACs**:
  - [x] AC-T021.1: `GraphUpdater` class wraps existing Graphiti integration
  - [x] AC-T021.2: Updates user_graph, relationship_graph after conversation
  - [x] AC-T021.3: Extracts facts from conversation
  - [x] AC-T021.4: Unit tests for updater (9 tests)

#### T022: Implement SummaryGenerator
- **Status**: [x] Complete
- **Estimate**: 1h
- **Dependencies**: T020
- **ACs**:
  - [x] AC-T022.1: `SummaryGenerator` class wraps existing summary logic
  - [x] AC-T022.2: Generates/updates daily summary
  - [x] AC-T022.3: Generates/updates weekly summary (if applicable)
  - [x] AC-T022.4: Unit tests for generator

#### T023: Implement LayerComposer
- **Status**: [x] Complete
- **Estimate**: 2h
- **Dependencies**: T020, T012
- **ACs**:
  - [x] AC-T023.1: `LayerComposer` class pre-composes Layers 2-4
  - [x] AC-T023.2: Fetches current chapter, emotional state, situation hints
  - [x] AC-T023.3: Stores composed layers in context package
  - [x] AC-T023.4: Unit tests for composer

#### T024: Wire pipeline trigger
- **Status**: [x] Complete
- **Estimate**: 1h
- **Dependencies**: T020
- **ACs**:
  - [x] AC-T024.1: `trigger_pipeline_background()` and `add_pipeline_trigger_to_background_tasks()` implemented
  - [x] AC-T024.2: Pipeline runs async (non-blocking) via BackgroundTasks
  - [x] AC-T024.3: Logging for pipeline trigger
  - [x] AC-T024.4: Feature flag `enable_post_processing_pipeline` (10 tests)

#### T025: Integration tests for pipeline
- **Status**: [x] Complete
- **Estimate**: 2h
- **Dependencies**: T024
- **ACs**:
  - [x] AC-T025.1: Integration tests in `tests/post_processing/test_pipeline.py` (TestPipelineIntegration class)
  - [x] AC-T025.2: Test full pipeline execution
  - [x] AC-T025.3: Test partial failure handling
  - [x] AC-T025.4: Test package storage verification (3 tests)

#### T026: E2E test: conversation cycle
- **Status**: [x] Complete
- **Estimate**: 2h
- **Dependencies**: T025
- **ACs**:
  - [x] AC-T026.1: Test file `tests/e2e/test_conversation_cycle.py`
  - [x] AC-T026.2: Simulate conversation → post-process → next conversation
  - [x] AC-T026.3: Verify context package used in second conversation
  - [x] AC-T026.4: Verify degradation when package missing (8 tests)

---

## Acceptance Criteria Summary

| User Story | AC Count | Key Criteria |
|------------|----------|--------------|
| US-1 | 4 | Post-processing in 15 min, injection < 150ms |
| US-2 | 4 | Base personality ~2000 tokens, cached |
| US-3 | 4 | Chapter-specific behaviors, 1-5 progression |
| US-4 | 4 | 4 emotional dimensions, affects response |
| US-5 | 4 | Situation detection, meta-instructions |
| US-6 | 4 | Package load < 50ms, graceful degradation |
| US-7 | 4 | Mood shift + memory retrieval < 200ms |
| US-8 | 4 | Pipeline success > 99%, async execution |

---

## Version History

### v1.0.0 - 2026-01-12
- Initial task breakdown
- 26 tasks with acceptance criteria
- Progress tracking table
