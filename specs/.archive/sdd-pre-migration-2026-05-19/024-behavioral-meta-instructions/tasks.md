# Tasks: 024 Behavioral Meta-Instructions

**Spec Version**: 1.0.0
**Created**: 2026-01-12

---

## Progress Summary

| Phase | Tasks | Completed | Status |
|-------|-------|-----------|--------|
| A: Infrastructure | 4 | 4 | ✅ Complete |
| B: Situation Detection | 6 | 6 | ✅ Complete |
| C: Instruction Selection | 4 | 4 | ✅ Complete |
| D: Engine & Formatting | 3 | 3 | ✅ Complete |
| E: Integration | 3 | 3 | ✅ Complete |
| **Total** | **20** | **20** | **100%** |

---

## Phase A: Core Infrastructure

### T001: Create behavioral module
- **Status**: [x] Complete
- **Estimate**: 30m
- **ACs**:
  - [x] AC-T001.1: Create `nikita/behavioral/__init__.py`
  - [x] AC-T001.2: Module structure matches spec file layout

### T002: Implement MetaInstruction model
- **Status**: [x] Complete
- **Estimate**: 1h
- **Dependencies**: T001
- **ACs**:
  - [x] AC-T002.1: `MetaInstruction` Pydantic model
  - [x] AC-T002.2: `SituationContext` Pydantic model
  - [x] AC-T002.3: Validation for situation types and categories
  - [x] AC-T002.4: Unit tests for models (32 tests)

### T003: Create instruction library YAML
- **Status**: [x] Complete
- **Estimate**: 2h
- **Dependencies**: T001
- **ACs**:
  - [x] AC-T003.1: `nikita/config_data/behavioral/situations.yaml`
  - [x] AC-T003.2: `nikita/config_data/behavioral/instructions.yaml`
  - [x] AC-T003.3: Instructions for: after_gap, morning, evening, mid_conversation, conflict
  - [x] AC-T003.4: 3-5 instructions per situation (30+ total)
  - [x] AC-T003.5: Instructions use directional language ("lean toward", "consider")

### T004: Unit tests for models
- **Status**: [x] Complete
- **Estimate**: 1h
- **Dependencies**: T002, T003
- **ACs**:
  - [x] AC-T004.1: Test file `tests/behavioral/test_models.py` (32 tests)
  - [x] AC-T004.2: YAML loading tests (6 tests)
  - [x] AC-T004.3: Model validation tests (26 tests)

---

## Phase B: Situation Detection

### T005: Implement SituationDetector class
- **Status**: [x] Complete
- **Estimate**: 1.5h
- **Dependencies**: T004
- **ACs**:
  - [x] AC-T005.1: `SituationDetector` class
  - [x] AC-T005.2: `detect()` method returns SituationContext
  - [x] AC-T005.3: Handles multiple situation types
  - [x] AC-T005.4: Unit tests for detector

### T006: Implement situation classification logic
- **Status**: [x] Complete
- **Estimate**: 1h
- **Dependencies**: T005
- **ACs**:
  - [x] AC-T006.1: Situations are mutually exclusive
  - [x] AC-T006.2: Priority ordering: conflict > after_gap > time_based > mid_conversation
  - [x] AC-T006.3: Unit tests for classification

### T007: Add time-based detection
- **Status**: [x] Complete
- **Estimate**: 1h
- **Dependencies**: T006
- **ACs**:
  - [x] AC-T007.1: Morning detection (6am-11am user timezone)
  - [x] AC-T007.2: Evening detection (6pm-10pm user timezone)
  - [x] AC-T007.3: Timezone handling from user profile
  - [x] AC-T007.4: Unit tests for time detection

### T008: Add gap detection
- **Status**: [x] Complete
- **Estimate**: 1h
- **Dependencies**: T006
- **ACs**:
  - [x] AC-T008.1: Detect gaps > 6 hours
  - [x] AC-T008.2: Detect gaps > 24 hours (longer gap)
  - [x] AC-T008.3: Calculate time since last message
  - [x] AC-T008.4: Unit tests for gap detection

### T009: Add conflict detection integration
- **Status**: [x] Complete
- **Estimate**: 1h
- **Dependencies**: T006
- **ACs**:
  - [x] AC-T009.1: Read conflict_state from EmotionalState (023)
  - [x] AC-T009.2: Map conflict_state to conflict situation
  - [x] AC-T009.3: Unit tests for conflict detection

### T010: Phase B tests
- **Status**: [x] Complete
- **Estimate**: 1h
- **Dependencies**: T009
- **ACs**:
  - [x] AC-T010.1: Test file `tests/behavioral/test_detection.py`
  - [x] AC-T010.2: Coverage > 85% for Phase B modules (45 tests)

---

## Phase C: Instruction Selection

### T011: Implement InstructionSelector class
- **Status**: [x] Complete
- **Estimate**: 1.5h
- **Dependencies**: T010
- **ACs**:
  - [x] AC-T011.1: `InstructionSelector` class
  - [x] AC-T011.2: `select()` method returns relevant instructions
  - [x] AC-T011.3: Loads from instruction library YAML
  - [x] AC-T011.4: Unit tests for selector

### T012: Implement priority-based selection
- **Status**: [x] Complete
- **Estimate**: 1h
- **Dependencies**: T011
- **ACs**:
  - [x] AC-T012.1: Instructions sorted by priority (1 = highest)
  - [x] AC-T012.2: Top N instructions selected (configurable, default 5)
  - [x] AC-T012.3: Unit tests for priority selection

### T013: Implement condition evaluation
- **Status**: [x] Complete
- **Estimate**: 1h
- **Dependencies**: T011
- **ACs**:
  - [x] AC-T013.1: Evaluate `conditions` dict against context
  - [x] AC-T013.2: Support: chapter_min, chapter_max, relationship_score_min
  - [x] AC-T013.3: Filter out non-applicable instructions
  - [x] AC-T013.4: Unit tests for condition evaluation

### T014: Phase C tests
- **Status**: [x] Complete
- **Estimate**: 1h
- **Dependencies**: T013
- **ACs**:
  - [x] AC-T014.1: Test file `tests/behavioral/test_selection.py`
  - [x] AC-T014.2: Coverage > 85% for Phase C modules (24 tests)

---

## Phase D: Engine & Formatting

### T015: Implement MetaInstructionEngine
- **Status**: [x] Complete
- **Estimate**: 1.5h
- **Dependencies**: T014
- **ACs**:
  - [x] AC-T015.1: `MetaInstructionEngine` class orchestrates components
  - [x] AC-T015.2: `get_instructions_for_context()` main method
  - [x] AC-T015.3: Caches instruction library
  - [x] AC-T015.4: Unit tests for engine

### T016: Implement format_for_prompt()
- **Status**: [x] Complete
- **Estimate**: 1h
- **Dependencies**: T015
- **ACs**:
  - [x] AC-T016.1: `format_for_prompt()` returns formatted string
  - [x] AC-T016.2: Groups instructions by category
  - [x] AC-T016.3: Clean, readable format for LLM consumption
  - [x] AC-T016.4: Unit tests for formatting

### T017: Integration tests
- **Status**: [x] Complete
- **Estimate**: 1.5h
- **Dependencies**: T016
- **ACs**:
  - [x] AC-T017.1: Test full pipeline: context → detection → selection → format
  - [x] AC-T017.2: Test different situations produce different outputs
  - [x] AC-T017.3: Test empty situations (mid_conversation) work (32 tests)

---

## Phase E: Integration

### T018: Wire to HierarchicalPromptComposer (021)
- **Status**: [x] Complete
- **Estimate**: 1.5h
- **Dependencies**: T017
- **ACs**:
  - [x] AC-T018.1: PostProcessingPipeline calls MetaInstructionEngine
  - [x] AC-T018.2: Instructions stored in ContextPackage.situation_hints
  - [x] AC-T018.3: Layer 4 uses formatted instructions

### T019: E2E tests
- **Status**: [x] Complete
- **Estimate**: 2h
- **Dependencies**: T018
- **ACs**:
  - [x] AC-T019.1: Full pipeline: conversation → situation → instructions → prompt
  - [x] AC-T019.2: Verify instructions affect response style
  - [x] AC-T019.3: Verify conflict instructions work

### T020: Quality tests
- **Status**: [x] Complete
- **Estimate**: 1.5h
- **Dependencies**: T019
- **ACs**:
  - [x] AC-T020.1: Test response variability (CV > 0.3)
  - [x] AC-T020.2: Test personality consistency
  - [x] AC-T020.3: Test no exact templates in responses

---

## Version History

### v1.0.0 - 2026-01-12
- Initial task breakdown
- 20 tasks with acceptance criteria
