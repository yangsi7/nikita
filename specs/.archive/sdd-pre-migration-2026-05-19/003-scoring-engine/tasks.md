# Tasks: 003-Scoring-Engine

**Generated**: 2025-11-29
**Feature**: 003 - Scoring Engine
**Input**: Design documents from `/specs/003-scoring-engine/`
**Prerequisites**:
- **Required**: plan.md (technical approach), spec.md (user stories)
- **Optional**: nikita/engine/constants.py (existing patterns)

**Organization**: Tasks grouped by user story (US1-US6) for independent implementation and testing.

---

## Phase 1: Setup

**Purpose**: Create scoring module structure

- [ ] T001 Create `nikita/engine/scoring/__init__.py` with module exports
- [ ] T002 Create `tests/engine/scoring/__init__.py` for test package

**Checkpoint**: Module structure ready for implementation

---

## Phase 2: Foundational Models

**Purpose**: Core data models required by all scoring components

### T003: Create ResponseAnalysis Model
- **Status**: [ ] Pending
- **File**: `nikita/engine/scoring/models.py`
- **Dependencies**: None
- **ACs**:
  - [ ] AC-T003.1: intimacy_delta, passion_delta, trust_delta, secureness_delta as Decimal fields
  - [ ] AC-T003.2: All delta fields have validator enforcing -10 to +10 range
  - [ ] AC-T003.3: Optional `explanation: str` field for reasoning
  - [ ] AC-T003.4: `behaviors_identified: list[str]` field for identified behaviors

### T004: Create ConversationContext Model
- **Status**: [ ] Pending
- **File**: `nikita/engine/scoring/models.py`
- **Dependencies**: None
- **ACs**:
  - [ ] AC-T004.1: chapter field (1-5 int)
  - [ ] AC-T004.2: recent_history: list[tuple[str, str]] for last N exchanges
  - [ ] AC-T004.3: relationship_state: str (e.g., "stable", "conflict", "recovery")
  - [ ] AC-T004.4: Optional user_patterns field for detected patterns

### T005: Create ScoreEvent Model
- **Status**: [ ] Pending
- **File**: `nikita/engine/scoring/models.py`
- **Dependencies**: None
- **ACs**:
  - [ ] AC-T005.1: event_type: Literal["boss_threshold", "critical_low", "game_over", "recovery"]
  - [ ] AC-T005.2: threshold value and chapter context included
  - [ ] AC-T005.3: timestamp field

**Checkpoint**: All data models ready for service implementation

---

## Phase 3: US-1 Exchange Scoring (P1 - Must-Have)

**From spec.md**: Analyze each user-Nikita exchange and update metrics

**Goal**: Every conversation exchange is analyzed and scored

**Independent Test**: Send message, verify metrics updated with reasonable deltas

**Acceptance Criteria** (from spec.md):
- AC-FR001-001: Given thoughtful message, Then positive deltas calculated
- AC-FR002-001: Given deltas, Then each within -10 to +10
- AC-FR003-001: Given metrics, Then composite uses 30/25/25/20 weights

### Tests for US-1 ⚠️ WRITE TESTS FIRST

- [ ] T006 [P] [US1] Unit test for ResponseAnalysis validation in `tests/engine/scoring/test_models.py`
  - **Tests**: AC-FR002-001 (delta bounds)
  - **Verify**: Test FAILS before implementation

- [ ] T007 [P] [US1] Unit test for ScoreCalculator in `tests/engine/scoring/test_calculator.py`
  - **Tests**: AC-FR003-001 (composite weights)
  - **Verify**: Test FAILS before implementation

- [ ] T008 [P] [US1] Integration test for analyze→calculate flow in `tests/engine/scoring/test_integration.py`
  - **Tests**: AC-FR001-001 (positive deltas)
  - **Verify**: Test FAILS before implementation

### Implementation for US-1

### T009: Implement ScoreAnalyzer Class
- **Status**: [ ] Pending
- **File**: `nikita/engine/scoring/analyzer.py`
- **Dependencies**: T003, T004
- **ACs**:
  - [ ] AC-T009.1: `analyze(user_msg, nikita_msg, context)` method returns ResponseAnalysis
  - [ ] AC-T009.2: Uses Claude via Pydantic AI with temperature=0
  - [ ] AC-T009.3: Prompt includes chapter-specific behavior from CHAPTER_BEHAVIORS
  - [ ] AC-T009.4: Handles LLM errors gracefully with default neutral response
  - [ ] AC-T009.5: Analysis latency <3 seconds (per NFR)

### T010: Implement ScoreCalculator Class
- **Status**: [ ] Pending
- **File**: `nikita/engine/scoring/calculator.py`
- **Dependencies**: T003, T009
- **ACs**:
  - [ ] AC-T010.1: `apply_deltas(user_id, analysis)` uses UserMetricsRepository.update_metrics()
  - [ ] AC-T010.2: Calculates composite using METRIC_WEIGHTS from constants.py
  - [ ] AC-T010.3: Updates User.relationship_score with new composite
  - [ ] AC-T010.4: Returns dict with score_before, score_after, events
  - [ ] AC-T010.5: Enforces bounds (metrics 0-100, deltas -10 to +10)

### Verification for US-1

- [ ] T011 [US1] Run all US-1 tests - verify all pass
- [ ] T012 [US1] Verify composite calculation: intimacy*0.30 + passion*0.25 + trust*0.25 + secureness*0.20

**Checkpoint**: Exchange scoring functional. Conversations update scores.

---

## Phase 4: US-2 Score History (P1 - Must-Have)

**From spec.md**: Maintain complete score history with context

**Goal**: All score changes logged with full audit trail

**Independent Test**: Make score change, query history, verify complete record

**Acceptance Criteria** (from spec.md):
- AC-FR005-001: Given change, Then timestamp, before, after, deltas, source recorded
- AC-FR005-002: Given history query, Then complete history retrievable
- AC-FR005-003: Given context, Then conversation excerpt stored

### Tests for US-2 ⚠️ WRITE TESTS FIRST

- [ ] T013 [P] [US2] Unit test for history logging in `tests/engine/scoring/test_calculator.py`
  - **Tests**: AC-FR005-001, AC-FR005-003
  - **Verify**: Test FAILS before implementation

### Implementation for US-2

### T014: Integrate History Logging with ScoreCalculator
- **Status**: [ ] Pending
- **File**: `nikita/engine/scoring/calculator.py`
- **Dependencies**: T010
- **ACs**:
  - [ ] AC-T014.1: `apply_deltas()` calls ScoreHistoryRepository.log_event() after update
  - [ ] AC-T014.2: event_details includes all 4 metric deltas
  - [ ] AC-T014.3: event_details includes conversation excerpt (first 200 chars)
  - [ ] AC-T014.4: event_details includes explanation from ResponseAnalysis
  - [ ] AC-T014.5: event_type set to "conversation" for exchange scoring

### Verification for US-2

- [ ] T015 [US2] Run history tests - verify log_event called with correct data
- [ ] T016 [US2] Verify history retrievable via ScoreHistoryRepository.get_history()

**Checkpoint**: Score history logging complete. Full audit trail available.

---

## Phase 5: US-3 Threshold Events (P1 - Must-Have)

**From spec.md**: Emit events when scores cross thresholds

**Goal**: Boss system can react to score milestones

**Independent Test**: Manipulate score to threshold, verify event emitted

**Acceptance Criteria** (from spec.md):
- AC-FR010-001: Given score 60%+ in Ch1, Then boss_threshold_reached emitted
- AC-FR010-002: Given score 0%, Then game_over emitted
- AC-FR010-003: Given events, Then boss system can react

### Tests for US-3 ⚠️ WRITE TESTS FIRST

- [ ] T017 [P] [US3] Unit test for ThresholdEmitter in `tests/engine/scoring/test_events.py`
  - **Tests**: AC-FR010-001, AC-FR010-002
  - **Verify**: Test FAILS before implementation

### Implementation for US-3

### T018: Implement ThresholdEmitter Class
- **Status**: [ ] Pending
- **File**: `nikita/engine/scoring/events.py`
- **Dependencies**: T005
- **ACs**:
  - [ ] AC-T018.1: `check_thresholds(score_before, score_after, chapter)` returns list[ScoreEvent]
  - [ ] AC-T018.2: Checks BOSS_THRESHOLDS (60, 65, 70, 75, 80) per chapter
  - [ ] AC-T018.3: Emits boss_threshold_reached when score crosses from below
  - [ ] AC-T018.4: Emits critical_low when score drops below 20%
  - [ ] AC-T018.5: Emits game_over when score reaches 0%
  - [ ] AC-T018.6: Emits recovery when score rises above 20% from below

### T019: Integrate ThresholdEmitter with ScoreCalculator
- **Status**: [ ] Pending
- **File**: `nikita/engine/scoring/calculator.py`
- **Dependencies**: T010, T018
- **ACs**:
  - [ ] AC-T019.1: `apply_deltas()` calls ThresholdEmitter.check_thresholds()
  - [ ] AC-T019.2: Events included in return dict
  - [ ] AC-T019.3: Events can be consumed by caller (boss system)

### Verification for US-3

- [ ] T020 [US3] Run threshold tests - verify events emitted correctly
- [ ] T021 [US3] Test edge cases: exactly at threshold, crossing multiple thresholds

**Checkpoint**: Threshold events emitted. Boss system integration ready.

---

## Phase 6: US-4 Context-Aware Analysis (P2 - Important)

**From spec.md**: Same message + different context → different scoring

**Goal**: Analysis considers chapter, history, relationship state

**Independent Test**: Same message at Ch1 vs Ch5 produces different deltas

**Acceptance Criteria** (from spec.md):
- AC-FR006-001: Given Ch1 user, Then more positive for personal questions
- AC-FR006-002: Given recent conflict, Then apology has higher impact
- AC-FR006-003: Given context, Then reasoning reflects it

### Tests for US-4 ⚠️ WRITE TESTS FIRST

- [ ] T022 [P] [US4] Unit test for context-aware analysis in `tests/engine/scoring/test_analyzer.py`
  - **Tests**: AC-FR006-001, AC-FR006-002
  - **Verify**: Test FAILS before implementation

### Implementation for US-4

### T023: Enhance ScoreAnalyzer with Context
- **Status**: [ ] Pending
- **File**: `nikita/engine/scoring/analyzer.py`
- **Dependencies**: T009
- **ACs**:
  - [ ] AC-T023.1: Prompt includes CHAPTER_BEHAVIORS[context.chapter]
  - [ ] AC-T023.2: Prompt includes recent_history summary
  - [ ] AC-T023.3: Prompt includes relationship_state context
  - [ ] AC-T023.4: Same message with different chapters produces different deltas

### Verification for US-4

- [ ] T024 [US4] Run context tests - verify different contexts yield different scores
- [ ] T025 [US4] Verify P1 still works (regression check)

**Checkpoint**: Context-aware analysis complete. Scoring reflects relationship state.

---

## Phase 7: US-5 Analysis Explanation (P2 - Important)

**From spec.md**: Provide reasoning for score changes

**Goal**: Debugging and potential user feedback enabled

**Acceptance Criteria** (from spec.md):
- AC-FR007-001: Given change, Then explanation included
- AC-FR007-002: Given explanation, Then specific behaviors identified

### Implementation for US-5

### T026: Add Explanation to ResponseAnalysis
- **Status**: [ ] Pending
- **File**: `nikita/engine/scoring/analyzer.py`
- **Dependencies**: T023
- **ACs**:
  - [ ] AC-T026.1: LLM prompt requests explanation for each delta
  - [ ] AC-T026.2: LLM prompt requests specific behaviors identified
  - [ ] AC-T026.3: ResponseAnalysis.explanation always populated
  - [ ] AC-T026.4: ResponseAnalysis.behaviors_identified list populated

### Verification for US-5

- [ ] T027 [US5] Verify explanations are meaningful (manual review)
- [ ] T028 [US5] Verify behaviors_identified contains actionable insights

**Checkpoint**: Explanations available. Ready for debugging and user feedback.

---

## Phase 8: US-6 Voice Batch Analysis (P3 - Nice-to-Have)

**From spec.md**: Analyze multi-turn voice transcripts as single unit

**Goal**: Voice calls produce single aggregate score impact

**Acceptance Criteria** (from spec.md):
- AC-FR008-001: Given 20-turn transcript, Then single aggregate calculated
- AC-FR008-002: Given batch, Then completes within 10 seconds

### Implementation for US-6

### T029: Add Batch Analysis to ScoreAnalyzer
- **Status**: [ ] Pending
- **File**: `nikita/engine/scoring/analyzer.py`
- **Dependencies**: T026
- **ACs**:
  - [ ] AC-T029.1: `batch_analyze(exchanges: list[tuple[str,str]], context)` method
  - [ ] AC-T029.2: Produces single aggregated ResponseAnalysis
  - [ ] AC-T029.3: Aggregate deltas capped at reasonable maximums (+/-30)
  - [ ] AC-T029.4: 20-turn analysis completes within 10 seconds

### Verification for US-6

- [ ] T030 [US6] Verify batch analysis returns single result
- [ ] T031 [US6] Verify performance: 20 turns < 10 seconds

**Checkpoint**: Voice call batch analysis ready.

---

## Phase 9: Final Verification

**Purpose**: Full integration test and polish

- [ ] T032 Run all tests: `pytest tests/engine/scoring/ -v`
- [ ] T033 Verify 80%+ code coverage
- [ ] T034 Integration test: Full conversation → analysis → score update → history → events
- [ ] T035 Update `nikita/engine/scoring/CLAUDE.md` with implementation notes
- [ ] T036 Update `nikita/engine/CLAUDE.md` status to reflect scoring complete

**Final Checkpoint**: Scoring engine complete and verified.

---

## Dependencies & Execution Order

### Phase Dependencies

| Phase | Depends On | Can Start After |
|-------|-----------|-----------------|
| Phase 1: Setup | None | Immediately |
| Phase 2: Models | Phase 1 | Setup done |
| Phase 3: US-1 | Phase 2 | Models ready |
| Phase 4: US-2 | Phase 3 | US-1 done |
| Phase 5: US-3 | Phase 2 | Models ready (parallel with US-1) |
| Phase 6: US-4 | Phase 3 | US-1 done |
| Phase 7: US-5 | Phase 6 | US-4 done |
| Phase 8: US-6 | Phase 7 | US-5 done |
| Phase 9: Final | All prior | All stories done |

### Parallel Opportunities

- **T003, T004, T005** (models) can run in parallel
- **T006, T007, T008** (tests) can run in parallel
- **Phase 5 (US-3)** can run in parallel with Phase 3 (US-1) after Phase 2

---

## Progress Summary

| Phase/User Story | Tasks | Completed | Status |
|------------------|-------|-----------|--------|
| Phase 1: Setup | 2 | 0 | Pending |
| Phase 2: Models | 3 | 0 | Pending |
| US-1: Exchange Scoring | 7 | 0 | Pending |
| US-2: Score History | 4 | 0 | Pending |
| US-3: Threshold Events | 5 | 0 | Pending |
| US-4: Context Analysis | 4 | 0 | Pending |
| US-5: Explanation | 3 | 0 | Pending |
| US-6: Batch Analysis | 3 | 0 | Pending |
| Phase 9: Final | 5 | 0 | Pending |
| **Total** | **36** | **0** | **Not Started** |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-29 | Initial task generation from plan.md |
