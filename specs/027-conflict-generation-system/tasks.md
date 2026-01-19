# Tasks: 027 Conflict Generation System

**Spec Version**: 1.0.0
**Created**: 2026-01-12

---

## Progress Summary

| Phase | Tasks | Completed | Status |
|-------|-------|-----------|--------|
| A: Infrastructure | 5 | 5 | ✅ Complete |
| B: Trigger Detection | 6 | 6 | ✅ Complete |
| C: Conflict Generation | 4 | 4 | ✅ Complete |
| D: Escalation | 4 | 4 | ✅ Complete |
| E: Resolution | 4 | 4 | ✅ Complete |
| F: Breakup | 5 | 5 | ✅ Complete |
| G: Integration | 4 | 4 | ✅ Complete |
| **Total** | **32** | **32** | **100%** |

### Test Summary
- **Infrastructure**: 54 tests
- **Detector**: 40 tests
- **Generator**: 32 tests
- **Escalation**: 37 tests
- **Resolution**: 39 tests
- **Breakup**: 46 tests
- **Integration**: 15 tests
- **Total**: 263 tests passing

---

## Phase A: Core Infrastructure

### T001: Create conflicts module
- **Status**: [ ] Pending
- **Estimate**: 30m
- **ACs**:
  - [ ] AC-T001.1: Create `nikita/conflicts/__init__.py`
  - [ ] AC-T001.2: Module structure matches spec

### T002: Implement models
- **Status**: [ ] Pending
- **Estimate**: 1.5h
- **Dependencies**: T001
- **ACs**:
  - [ ] AC-T002.1: `ConflictTrigger` Pydantic model
  - [ ] AC-T002.2: `ActiveConflict` Pydantic model
  - [ ] AC-T002.3: Validation for trigger types, severity ranges
  - [ ] AC-T002.4: Unit tests for models

### T003: Add database migration
- **Status**: [ ] Pending
- **Estimate**: 30m
- **Dependencies**: T002
- **ACs**:
  - [ ] AC-T003.1: Migration creates `conflict_triggers` table
  - [ ] AC-T003.2: Migration creates `active_conflicts` table
  - [ ] AC-T003.3: Indexes on user_id, resolved
  - [ ] AC-T003.4: Migration applied successfully

### T004: Implement ConflictStore
- **Status**: [ ] Pending
- **Estimate**: 1.5h
- **Dependencies**: T003
- **ACs**:
  - [ ] AC-T004.1: `ConflictStore` class with CRUD
  - [ ] AC-T004.2: `get_active_conflict()` method
  - [ ] AC-T004.3: `create_conflict()` method
  - [ ] AC-T004.4: `resolve_conflict()` method
  - [ ] AC-T004.5: Unit tests for store

### T005: Phase A tests
- **Status**: [ ] Pending
- **Estimate**: 1h
- **Dependencies**: T004
- **ACs**:
  - [ ] AC-T005.1: Test file `tests/conflicts/test_infrastructure.py`
  - [ ] AC-T005.2: Coverage > 85%

---

## Phase B: Trigger Detection

### T006: Implement TriggerDetector class
- **Status**: [ ] Pending
- **Estimate**: 1.5h
- **Dependencies**: T005
- **ACs**:
  - [ ] AC-T006.1: `TriggerDetector` class
  - [ ] AC-T006.2: `detect()` method analyzes messages
  - [ ] AC-T006.3: Returns list of detected triggers
  - [ ] AC-T006.4: Unit tests for detector

### T007: Implement dismissive detection
- **Status**: [ ] Pending
- **Estimate**: 1.5h
- **Dependencies**: T006
- **ACs**:
  - [ ] AC-T007.1: LLM-based detection of dismissive tone
  - [ ] AC-T007.2: Detect short responses (under 10 chars)
  - [ ] AC-T007.3: Detect topic changes mid-discussion
  - [ ] AC-T007.4: Unit tests with mock LLM

### T008: Implement neglect detection
- **Status**: [ ] Pending
- **Estimate**: 1h
- **Dependencies**: T006
- **ACs**:
  - [ ] AC-T008.1: Time-based detection (gap > 24h)
  - [ ] AC-T008.2: Consecutive short sessions
  - [ ] AC-T008.3: Missing expected check-ins
  - [ ] AC-T008.4: Unit tests for neglect

### T009: Implement jealousy detection
- **Status**: [ ] Pending
- **Estimate**: 1.5h
- **Dependencies**: T006
- **ACs**:
  - [ ] AC-T009.1: Detect mentions of other people positively
  - [ ] AC-T009.2: LLM-based context analysis
  - [ ] AC-T009.3: False positive filtering (family, work colleagues)
  - [ ] AC-T009.4: Unit tests for jealousy

### T010: Implement boundary violation detection
- **Status**: [ ] Pending
- **Estimate**: 1.5h
- **Dependencies**: T006
- **ACs**:
  - [ ] AC-T010.1: Detect sexual pressure (chapter-aware)
  - [ ] AC-T010.2: Detect pushy behavior
  - [ ] AC-T010.3: Chapter-based threshold (Ch1 more sensitive)
  - [ ] AC-T010.4: Unit tests for boundary

### T011: Phase B tests
- **Status**: [ ] Pending
- **Estimate**: 1.5h
- **Dependencies**: T010
- **ACs**:
  - [ ] AC-T011.1: Test file `tests/conflicts/test_detection.py`
  - [ ] AC-T011.2: Coverage > 85%

---

## Phase C: Conflict Generation

### T012: Implement ConflictGenerator class
- **Status**: [ ] Pending
- **Estimate**: 1.5h
- **Dependencies**: T011
- **ACs**:
  - [ ] AC-T012.1: `ConflictGenerator` class
  - [ ] AC-T012.2: `generate()` creates ActiveConflict from trigger
  - [ ] AC-T012.3: Handles multiple triggers (prioritizes)
  - [ ] AC-T012.4: Unit tests for generator

### T013: Implement severity calculation
- **Status**: [ ] Pending
- **Estimate**: 1h
- **Dependencies**: T012
- **ACs**:
  - [ ] AC-T013.1: Severity based on trigger type
  - [ ] AC-T013.2: Severity modified by relationship state
  - [ ] AC-T013.3: Recent conflict history affects severity
  - [ ] AC-T013.4: Unit tests for severity

### T014: Implement conflict type selection
- **Status**: [ ] Pending
- **Estimate**: 1h
- **Dependencies**: T012
- **ACs**:
  - [ ] AC-T014.1: Map triggers to conflict types
  - [ ] AC-T014.2: Handle ambiguous triggers
  - [ ] AC-T014.3: Prevent same conflict type in succession
  - [ ] AC-T014.4: Unit tests for type selection

### T015: Phase C tests
- **Status**: [ ] Pending
- **Estimate**: 1h
- **Dependencies**: T014
- **ACs**:
  - [ ] AC-T015.1: Test file `tests/conflicts/test_generation.py`
  - [ ] AC-T015.2: Coverage > 85%

---

## Phase D: Escalation

### T016: Implement EscalationManager class
- **Status**: [ ] Pending
- **Estimate**: 1.5h
- **Dependencies**: T015
- **ACs**:
  - [ ] AC-T016.1: `EscalationManager` class
  - [ ] AC-T016.2: `check_escalation()` method
  - [ ] AC-T016.3: `escalate()` method increases level
  - [ ] AC-T016.4: Unit tests for manager

### T017: Implement escalation timeline
- **Status**: [ ] Pending
- **Estimate**: 1h
- **Dependencies**: T016
- **ACs**:
  - [ ] AC-T017.1: Level 1→2: 2-6 hours
  - [ ] AC-T017.2: Level 2→3: 12-24 hours
  - [ ] AC-T017.3: Time resets on user acknowledgment
  - [ ] AC-T017.4: Unit tests for timeline

### T018: Implement natural resolution
- **Status**: [ ] Pending
- **Estimate**: 1h
- **Dependencies**: T016
- **ACs**:
  - [ ] AC-T018.1: 30% of Level 1 conflicts resolve naturally
  - [ ] AC-T018.2: Probability decreases at higher levels
  - [ ] AC-T018.3: Natural resolution affects emotional state
  - [ ] AC-T018.4: Unit tests for natural resolution

### T019: Phase D tests
- **Status**: [ ] Pending
- **Estimate**: 1h
- **Dependencies**: T018
- **ACs**:
  - [ ] AC-T019.1: Test file `tests/conflicts/test_escalation.py`
  - [ ] AC-T019.2: Coverage > 85%

---

## Phase E: Resolution

### T020: Implement ResolutionManager class
- **Status**: [ ] Pending
- **Estimate**: 1.5h
- **Dependencies**: T019
- **ACs**:
  - [ ] AC-T020.1: `ResolutionManager` class
  - [ ] AC-T020.2: `evaluate()` analyzes user response
  - [ ] AC-T020.3: `resolve()` closes conflict
  - [ ] AC-T020.4: Unit tests for manager

### T021: Implement resolution evaluation
- **Status**: [ ] Pending
- **Estimate**: 2h
- **Dependencies**: T020
- **ACs**:
  - [ ] AC-T021.1: LLM-based evaluation of user response
  - [ ] AC-T021.2: Detect apology authenticity
  - [ ] AC-T021.3: Detect explanation reasonableness
  - [ ] AC-T021.4: Detect grand gestures
  - [ ] AC-T021.5: Unit tests with mock LLM

### T022: Implement resolution types
- **Status**: [ ] Pending
- **Estimate**: 1h
- **Dependencies**: T021
- **ACs**:
  - [ ] AC-T022.1: Full resolution (conflict cleared)
  - [ ] AC-T022.2: Partial resolution (severity reduced)
  - [ ] AC-T022.3: Failed resolution (no effect)
  - [ ] AC-T022.4: Unit tests for types

### T023: Phase E tests
- **Status**: [ ] Pending
- **Estimate**: 1h
- **Dependencies**: T022
- **ACs**:
  - [ ] AC-T023.1: Test file `tests/conflicts/test_resolution.py`
  - [ ] AC-T023.2: Coverage > 85%

---

## Phase F: Breakup

### T024: Implement BreakupManager class
- **Status**: [ ] Pending
- **Estimate**: 1.5h
- **Dependencies**: T023
- **ACs**:
  - [ ] AC-T024.1: `BreakupManager` class
  - [ ] AC-T024.2: `check_threshold()` method
  - [ ] AC-T024.3: `trigger_breakup()` method
  - [ ] AC-T024.4: Unit tests for manager

### T025: Implement threshold checking
- **Status**: [ ] Pending
- **Estimate**: 1h
- **Dependencies**: T024
- **ACs**:
  - [ ] AC-T025.1: Warning at score < 20
  - [ ] AC-T025.2: Point of no return at score < 10
  - [ ] AC-T025.3: 3 consecutive unresolved crises
  - [ ] AC-T025.4: Unit tests for thresholds

### T026: Implement breakup sequence
- **Status**: [ ] Pending
- **Estimate**: 1.5h
- **Dependencies**: T025
- **ACs**:
  - [ ] AC-T026.1: Breakup message generation
  - [ ] AC-T026.2: Emotional, realistic breakup dialogue
  - [ ] AC-T026.3: Final message sent via Telegram
  - [ ] AC-T026.4: Unit tests for sequence

### T027: Implement game over state
- **Status**: [ ] Pending
- **Estimate**: 1h
- **Dependencies**: T026
- **ACs**:
  - [ ] AC-T027.1: User marked as "game_over"
  - [ ] AC-T027.2: Future messages get "game over" response
  - [ ] AC-T027.3: Breakup is permanent
  - [ ] AC-T027.4: Unit tests for game over

### T028: Phase F tests
- **Status**: [ ] Pending
- **Estimate**: 1h
- **Dependencies**: T027
- **ACs**:
  - [ ] AC-T028.1: Test file `tests/conflicts/test_breakup.py`
  - [ ] AC-T028.2: Coverage > 85%

---

## Phase G: Integration

### T029: Wire to message handler
- **Status**: [ ] Pending
- **Estimate**: 1.5h
- **Dependencies**: T028
- **ACs**:
  - [ ] AC-T029.1: TriggerDetector called on each message
  - [ ] AC-T029.2: ConflictEngine processes triggers
  - [ ] AC-T029.3: Escalation checked periodically
  - [ ] AC-T029.4: Integration test

### T030: Wire to emotional state (023)
- **Status**: [ ] Pending
- **Estimate**: 1h
- **Dependencies**: T029
- **ACs**:
  - [ ] AC-T030.1: Active conflict sets conflict_state
  - [ ] AC-T030.2: Resolution clears conflict_state
  - [ ] AC-T030.3: Integration test

### T031: E2E tests
- **Status**: [ ] Pending
- **Estimate**: 2h
- **Dependencies**: T030
- **ACs**:
  - [ ] AC-T031.1: Full conflict lifecycle E2E
  - [ ] AC-T031.2: Escalation E2E
  - [ ] AC-T031.3: Resolution E2E
  - [ ] AC-T031.4: Breakup E2E

### T032: Quality tests
- **Status**: [ ] Pending
- **Estimate**: 1.5h
- **Dependencies**: T031
- **ACs**:
  - [ ] AC-T032.1: Conflict frequency measurement
  - [ ] AC-T032.2: Resolution rate measurement
  - [ ] AC-T032.3: Breakup threshold verification

---

## Version History

### v1.0.0 - 2026-01-12
- Initial task breakdown
- 32 tasks with acceptance criteria
