# Tasks: 005-Decay-System

**Generated**: 2025-11-29
**Feature**: 005 - Decay System
**Input**: Design documents from `/specs/005-decay-system/`
**Prerequisites**:
- **Required**: plan.md (technical approach), spec.md (user stories)
- **Optional**: nikita/engine/constants.py (DECAY_RATES, GRACE_PERIODS)

**Organization**: Tasks grouped by user story (US1-US6) for independent implementation and testing.

---

## Phase 1: Setup

**Purpose**: Create decay module structure

- [ ] T001 Create `nikita/engine/decay/__init__.py` with module exports
- [ ] T002 Create `tests/engine/decay/__init__.py` for test package

**Checkpoint**: Module structure ready for implementation

---

## Phase 2: Foundational Models

**Purpose**: Core data models required by all decay components

### T003: Create DecayResult Model
- **Status**: [ ] Pending
- **File**: `nikita/engine/decay/models.py`
- **Dependencies**: None
- **ACs**:
  - [ ] AC-T003.1: user_id, decay_amount, score_before, score_after as required fields
  - [ ] AC-T003.2: days_overdue field for audit trail
  - [ ] AC-T003.3: chapter and timestamp fields for context
  - [ ] AC-T003.4: Optional game_over_triggered boolean field

**Checkpoint**: Data models ready for service implementation

---

## Phase 3: US-1 Grace Period Protection (P1 - Must-Have)

**From spec.md**: System MUST NOT apply decay until grace period expires

**Goal**: Protect users from decay during chapter-specific grace periods

**Independent Test**: Create user, check after X hours, verify NO decay within grace period

**Acceptance Criteria** (from spec.md):
- AC-FR001-001: Given Ch1 user, When inactive for 6 hours, Then NO decay applied (8h grace)
- AC-FR001-002: Given Ch1 user, When inactive for 10 hours, Then decay IS applied (past 8h grace)
- AC-FR001-003: Given Ch5 user, When inactive for 70 hours, Then NO decay applied (72h grace)

### Tests for US-1 ⚠️ WRITE TESTS FIRST

- [ ] T004 [P] [US1] Unit test for is_overdue() in `tests/engine/decay/test_calculator.py`
  - **Tests**: AC-FR001-001, AC-FR001-002, AC-FR001-003
  - **Verify**: Test FAILS before implementation

### Implementation for US-1

### T005: Implement DecayCalculator.is_overdue() Method
- **Status**: [ ] Pending
- **File**: `nikita/engine/decay/calculator.py`
- **Dependencies**: T003
- **ACs**:
  - [ ] AC-T005.1: `is_overdue(user)` returns bool based on GRACE_PERIODS[chapter]
  - [ ] AC-T005.2: Uses GRACE_PERIODS from constants.py
  - [ ] AC-T005.3: Returns False if within grace period
  - [ ] AC-T005.4: Returns True if past grace period

### Verification for US-1

- [ ] T006 [US1] Run all US-1 tests - verify all pass
- [ ] T007 [US1] Verify grace periods: Ch1=8h, Ch2=16h, Ch3=24h, Ch4=48h, Ch5=72h (compressed)

**Checkpoint**: Grace period protection functional. Users protected within grace window.

---

## Phase 4: US-2 Decay Application (P1 - Must-Have)

**From spec.md**: System MUST apply decay at chapter-appropriate rates

**Goal**: Calculate and apply correct decay amounts based on chapter and time overdue

**Independent Test**: Set user overdue by N days, run decay calculation, verify correct amount

**Acceptance Criteria** (from spec.md):
- AC-FR002-001: Given Ch1 user past grace, When 2h overdue, Then -1.6% decay applied (2h × 0.8%/h)
- AC-FR003-001: Given Ch1 user past grace, When 48h overdue, Then -10% decay applied
- AC-FR003-002: Given decay applied, When calculated, Then capped at maximum per cycle

### Tests for US-2 ⚠️ WRITE TESTS FIRST

- [ ] T008 [P] [US2] Unit test for calculate_decay() in `tests/engine/decay/test_calculator.py`
  - **Tests**: AC-FR002-001, AC-FR003-001, AC-FR003-002
  - **Verify**: Test FAILS before implementation

### Implementation for US-2

### T009: Implement DecayCalculator.calculate_decay() Method
- **Status**: [ ] Pending
- **File**: `nikita/engine/decay/calculator.py`
- **Dependencies**: T003, T005
- **ACs**:
  - [ ] AC-T009.1: `calculate_decay(user)` returns DecayResult or None if within grace
  - [ ] AC-T009.2: Uses DECAY_RATES from constants.py {1: 0.8%/h, 2: 0.6%/h, 3: 0.4%/h, 4: 0.3%/h, 5: 0.2%/h}
  - [ ] AC-T009.3: Calculates days_overdue correctly
  - [ ] AC-T009.4: Decay capped at MAX_DECAY_PER_CYCLE (default 20%)
  - [ ] AC-T009.5: Handles edge case where score would go negative (floor at 0)

### Verification for US-2

- [ ] T010 [US2] Run all US-2 tests - verify all pass
- [ ] T011 [US2] Verify decay rates: Ch1=5%, Ch2=4%, Ch3=3%, Ch4=2%, Ch5=1%

**Checkpoint**: Decay calculation functional. Correct amounts computed per chapter.

---

## Phase 5: US-3 Interaction Reset (P1 - Must-Have)

**From spec.md**: System MUST reset grace period on qualifying interaction

**Goal**: Reset grace period when user sends message or completes voice call

**Independent Test**: Set user overdue, send message, verify last_interaction_at updated

**Acceptance Criteria** (from spec.md):
- AC-FR006-001: Given decaying user, When they send message, Then last_interaction_at updated
- AC-FR006-002: Given reset interaction, When next decay check, Then grace period restarted
- AC-FR006-003: Given portal-only activity, When decay check, Then NO reset

### Tests for US-3 ⚠️ WRITE TESTS FIRST

- [ ] T012 [P] [US3] Unit test for update_last_interaction() in `tests/db/repositories/test_user_repository.py`
  - **Tests**: AC-FR006-001, AC-FR006-002
  - **Verify**: Test FAILS before implementation

### Implementation for US-3

### T013: Implement UserRepository.update_last_interaction() Method
- **Status**: [ ] Pending
- **File**: `nikita/db/repositories/user_repository.py`
- **Dependencies**: None (can run parallel with US-1/US-2)
- **ACs**:
  - [ ] AC-T013.1: `update_last_interaction(user_id, timestamp)` method exists
  - [ ] AC-T013.2: Updates `last_interaction_at` atomically
  - [ ] AC-T013.3: Called from text agent after message processing
  - [ ] AC-T013.4: Called from voice agent after call completion

### Verification for US-3

- [ ] T014 [US3] Run all US-3 tests - verify all pass
- [ ] T015 [US3] Verify portal activity does NOT reset grace (AC-FR006-003)

**Checkpoint**: Interaction reset functional. Messages and calls reset grace period.

---

## Phase 6: US-4 Decay Game Over (P1 - Must-Have)

**From spec.md**: Score decays to 0% → game over triggered

**Goal**: Trigger game over when decay reduces score to 0%

**Independent Test**: Set user low score (3%), apply decay, verify floors at 0% and game_over

**Acceptance Criteria** (from spec.md):
- AC-FR005-001: Given user at 3%, When -5% decay applies, Then score floors at 0%
- AC-FR007-001: Given score reaches 0% via decay, Then game_over event emitted
- AC-FR008-001: Given decay-caused game over, Then reason = "decay" logged

### Tests for US-4 ⚠️ WRITE TESTS FIRST

- [ ] T016 [P] [US4] Unit test for score flooring in `tests/engine/decay/test_calculator.py`
  - **Tests**: AC-FR005-001
  - **Verify**: Test FAILS before implementation

- [ ] T017 [P] [US4] Unit test for game over emission in `tests/engine/decay/test_calculator.py`
  - **Tests**: AC-FR007-001, AC-FR008-001
  - **Verify**: Test FAILS before implementation

### Implementation for US-4

### T018: Implement Decay Score Flooring and Game Over
- **Status**: [ ] Pending
- **File**: `nikita/engine/decay/calculator.py`
- **Dependencies**: T009
- **ACs**:
  - [ ] AC-T018.1: DecayCalculator floors score at 0 (never negative)
  - [ ] AC-T018.2: When score = 0, returns game_over_triggered = True in DecayResult
  - [ ] AC-T018.3: DecayResult includes reason = "decay" for game over logging

### T019: Integrate Game Over Event Emission
- **Status**: [ ] Pending
- **File**: `nikita/engine/decay/calculator.py`
- **Dependencies**: T018
- **ACs**:
  - [ ] AC-T019.1: Emit game_over event with reason="decay"
  - [ ] AC-T019.2: Update user.game_status to "game_over"
  - [ ] AC-T019.3: Log to score_history with event_type='decay_game_over'

### Verification for US-4

- [ ] T020 [US4] Run all US-4 tests - verify all pass
- [ ] T021 [US4] Verify game over reason logged correctly

**Checkpoint**: Decay game over functional. Score floors at 0%, game ends.

---

## Phase 7: US-5 Scheduled Processing (P1 - Must-Have)

**From spec.md**: Scheduler runs → all overdue users processed

**Goal**: Run decay on schedule for all users needing decay

**Independent Test**: Set up multiple users, run processor, verify all processed correctly

**Acceptance Criteria** (from spec.md):
- AC-FR004-001: Given scheduler configured, When triggered, Then all users checked
- AC-FR004-002: Given 1000 overdue users, When batch processed, Then all receive correct decay
- AC-FR004-003: Given scheduler crash, When restarted, Then resumes without duplication

### Tests for US-5 ⚠️ WRITE TESTS FIRST

- [ ] T022 [P] [US5] Unit test for DecayProcessor.process_all() in `tests/engine/decay/test_processor.py`
  - **Tests**: AC-FR004-001, AC-FR004-002
  - **Verify**: Test FAILS before implementation

- [ ] T023 [P] [US5] Unit test for idempotency in `tests/engine/decay/test_processor.py`
  - **Tests**: AC-FR004-003
  - **Verify**: Test FAILS before implementation

### Implementation for US-5

### T024: Implement DecayProcessor Class
- **Status**: [ ] Pending
- **File**: `nikita/engine/decay/processor.py`
- **Dependencies**: T009, T018
- **ACs**:
  - [ ] AC-T024.1: `process_all()` fetches all active users needing decay check
  - [ ] AC-T024.2: Filters out game_status in ['boss_fight', 'game_over', 'won']
  - [ ] AC-T024.3: Batches users to prevent memory issues (configurable batch size)
  - [ ] AC-T024.4: Calls DecayCalculator for each user past grace
  - [ ] AC-T024.5: Returns summary: {processed: N, decayed: M, game_overs: K}

### T025: Implement Decay History Logging
- **Status**: [ ] Pending
- **File**: `nikita/engine/decay/processor.py`
- **Dependencies**: T024
- **ACs**:
  - [ ] AC-T025.1: Each decay application logged to score_history
  - [ ] AC-T025.2: event_type = 'decay' for normal decay
  - [ ] AC-T025.3: event_details includes days_overdue, chapter, decay_rate
  - [ ] AC-T025.4: Idempotency: same decay period not logged twice

### T026: Create Decay Edge Function
- **Status**: [ ] Pending
- **File**: `supabase/functions/decay-check/index.ts`
- **Dependencies**: T024, T025
- **ACs**:
  - [ ] AC-T026.1: Edge Function `decay-check` responds to pg_cron webhook
  - [ ] AC-T026.2: Authenticates via service role key
  - [ ] AC-T026.3: Calls DecayProcessor.process_all() via internal API
  - [ ] AC-T026.4: Returns JSON summary {processed, decayed, game_overs}
  - [ ] AC-T026.5: Handles errors gracefully with logging

### Verification for US-5

- [ ] T027 [US5] Run all US-5 tests - verify all pass
- [ ] T028 [US5] Integration test: Full decay cycle with mock time
- [ ] T029 [US5] Verify idempotency (re-running doesn't double-decay)

**Checkpoint**: Scheduled processing functional. All overdue users processed correctly.

---

## Phase 8: US-6 Boss Fight Pause (P2 - Important)

**From spec.md**: User in boss fight → decay paused

**Goal**: Pause decay during boss encounters so users can focus on challenge

**Independent Test**: Put user in boss_fight status, run decay, verify skipped

**Acceptance Criteria** (from spec.md):
- AC-FR009-001: Given user in boss_fight status, When decay check runs, Then NO decay applied
- AC-FR009-002: Given boss completed, When decay resumes, Then grace period starts fresh
- AC-FR009-003: Given long boss attempt, When eventually resolved, Then decay does not "catch up"

### Tests for US-6 ⚠️ WRITE TESTS FIRST

- [ ] T030 [P] [US6] Unit test for boss fight pause in `tests/engine/decay/test_processor.py`
  - **Tests**: AC-FR009-001, AC-FR009-002, AC-FR009-003
  - **Verify**: Test FAILS before implementation

### Implementation for US-6

### T031: Implement Boss Fight Decay Pause
- **Status**: [ ] Pending
- **File**: `nikita/engine/decay/processor.py`
- **Dependencies**: T024
- **ACs**:
  - [ ] AC-T031.1: DecayProcessor.should_skip_user() checks game_status
  - [ ] AC-T031.2: Skips users with game_status in ['boss_fight', 'game_over', 'won']
  - [ ] AC-T031.3: Does NOT catch up on missed decay after boss resolved
  - [ ] AC-T031.4: Grace period resets to now after boss_pass or boss_fail

### Verification for US-6

- [ ] T032 [US6] Run all US-6 tests - verify all pass
- [ ] T033 [US6] Verify P1 still works (regression check)

**Checkpoint**: Boss fight pause complete. Users can focus on boss without decay pressure.

---

## Phase 9: Final Verification

**Purpose**: Full integration test and polish

- [ ] T034 Run all tests: `pytest tests/engine/decay/ -v`
- [ ] T035 Verify 80%+ code coverage
- [ ] T036 Integration test: Full decay cycle → multiple users → game overs → history logged
- [ ] T037 Update `nikita/engine/decay/CLAUDE.md` with implementation notes
- [ ] T038 Update `nikita/engine/CLAUDE.md` status to reflect decay complete

**Final Checkpoint**: Decay system complete and verified.

---

## Dependencies & Execution Order

### Phase Dependencies

| Phase | Depends On | Can Start After |
|-------|-----------|-----------------|
| Phase 1: Setup | None | Immediately |
| Phase 2: Models | Phase 1 | Setup done |
| Phase 3: US-1 | Phase 2 | Models ready |
| Phase 4: US-2 | Phase 3 | US-1 done |
| Phase 5: US-3 | Phase 2 | Models ready (parallel with US-1/2) |
| Phase 6: US-4 | Phase 4 | US-2 done |
| Phase 7: US-5 | Phase 6 | US-4 done |
| Phase 8: US-6 | Phase 7 | US-5 done |
| Phase 9: Final | All prior | All stories done |

### Parallel Opportunities

- **T004, T008** (tests) can run in parallel after models
- **Phase 5 (US-3)** can run in parallel with Phases 3-4 (US-1/US-2) after Phase 2
- **T022, T023** (US-5 tests) can run in parallel
- **T016, T017** (US-4 tests) can run in parallel

---

## Progress Summary

| Phase/User Story | Tasks | Completed | Status |
|------------------|-------|-----------|--------|
| Phase 1: Setup | 2 | 0 | Pending |
| Phase 2: Models | 1 | 0 | Pending |
| US-1: Grace Period | 4 | 0 | Pending |
| US-2: Decay Application | 4 | 0 | Pending |
| US-3: Interaction Reset | 4 | 0 | Pending |
| US-4: Decay Game Over | 6 | 0 | Pending |
| US-5: Scheduled Processing | 8 | 0 | Pending |
| US-6: Boss Fight Pause | 4 | 0 | Pending |
| Phase 9: Final | 5 | 0 | Pending |
| **Total** | **38** | **0** | **Not Started** |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-29 | Initial task generation from plan.md |
