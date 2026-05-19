# Tasks: Chapter & Boss System (004)

**Generated**: 2025-11-29
**Feature**: 004-chapter-boss-system
**Input**: Design documents from `/specs/004-chapter-boss-system/`
**Prerequisites**:
- **Required**: plan.md (technical approach), spec.md (user stories)
- **Optional**: research.md (patterns), data-model.md (schema)

**Organization**: Tasks are grouped by user story (US-1 through US-6) to enable:
- Independent implementation per story
- Independent testing per story
- MVP-first delivery (P1 → ship → P2 → ship...)

**Intelligence-First**: All tasks requiring code understanding MUST query existing patterns:
```bash
# Get symbols from existing engine code
project-intel.mjs --symbols nikita/engine/constants.py --json

# Check existing user model
project-intel.mjs --symbols nikita/db/models/user.py --json

# Find agent patterns
project-intel.mjs --search "agent" --type py --json
```

**Test-First (Article III)**: All implementation tasks MUST have ≥2 testable acceptance criteria. Write tests FIRST, watch them FAIL, then implement.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create module structure and foundational classes

**CoD^Σ Query**: Check existing engine structure at `nikita/engine/`

### T1: Create Boss State Machine Module
- **Status**: [x] Complete
- **User Story**: Foundation for all US
- **Dependencies**: None
- **File**: `nikita/engine/chapters/boss.py`

**Acceptance Criteria**:
- [x] AC-T1-001: `nikita/engine/chapters/boss.py` exists with BossStateMachine class
- [x] AC-T1-002: Class has methods: `check_threshold()`, `trigger_boss()`, `process_outcome()`
- [x] AC-T1-003: All methods are async and accept user_id parameter

**Implementation Notes**:
- Pattern: Follow `nikita/agents/text/agent.py` async patterns
- Integration: Import from `nikita/engine/constants.py`

---

### T2: [P] Create Boss Prompts Module
- **Status**: [x] Complete
- **User Story**: Foundation for FR-003
- **Dependencies**: None (parallel with T1)
- **File**: `nikita/engine/chapters/prompts.py`

**Acceptance Criteria**:
- [x] AC-T2-001: `nikita/engine/chapters/prompts.py` exists with 5 boss prompt templates
- [x] AC-T2-002: Each prompt includes: challenge context, success criteria, in-character opening
- [x] AC-T2-003: Prompts are parameterized by chapter number (1-5)

**Implementation Notes**:
- Reference: `BOSS_ENCOUNTERS` in `constants.py:113-139`
- Pattern: Similar to `nikita/prompts/` structure

---

**Checkpoint**: Basic module structure ready for user story implementation

---

## Phase 2: US-1 - Boss Trigger (Priority: P1)

**From spec.md**: Score reaches threshold → boss encounter starts → user knows it's happening

**Goal**: Detect when user's score crosses boss threshold and initiate encounter

**Independent Test**: Raise score to threshold, verify boss triggers and game_status changes

**Acceptance Criteria** (from spec.md):
- AC-FR001-001: Given user at 54% in Ch1, When score rises to 55%, Then boss encounter initiates
- AC-FR002-001: Given boss triggered, When encounter starts, Then Nikita delivers challenge prompt
- AC-FR002-002: Given boss in progress, When user tries normal chat, Then directed back to boss

### Intelligence Queries for US-1

```bash
# Find scoring patterns
project-intel.mjs --search "relationship_score" --type py --json

# Check user repository
project-intel.mjs --symbols nikita/db/repositories/user.py --json
```

### T3: Implement Threshold Detection
- **Status**: [x] Complete
- **User Story**: US-1
- **Dependencies**: T1 → T3
- **File**: `nikita/engine/chapters/boss.py`

**Acceptance Criteria**:
- [x] AC-FR001-001: Given user at 54% in Ch1, When score rises to 55%, Then `should_trigger_boss()` returns True
- [x] AC-T3-001: Method checks score >= BOSS_THRESHOLDS[chapter]
- [x] AC-T3-002: Method returns False if already in boss_fight or game_over status

**Implementation Notes**:
- Input: `user.relationship_score`, `user.chapter`, `user.game_status`
- Output: `bool` (should trigger)

---

### T4: Implement Boss Initiation
- **Status**: [x] Complete
- **User Story**: US-1
- **Dependencies**: T3 → T4
- **File**: `nikita/engine/chapters/boss.py`

**Acceptance Criteria**:
- [x] AC-FR002-001: Given boss triggered, When `initiate_boss()` called, Then game_status = 'boss_fight'
- [x] AC-FR002-002: Given boss initiated, When status changes, Then boss challenge prompt returned
- [x] AC-T4-001: Database updated atomically (status + logged to score_history) [via T5]

**Implementation Notes**:
- Update UserRepository with `set_boss_fight_status()` method
- Log event_type='boss_initiated' to score_history

---

### T5: [P] Add UserRepository Boss Methods
- **Status**: [x] Complete
- **User Story**: US-1, US-2, US-3
- **Dependencies**: T1 → T5 (parallel with T3, T4)
- **File**: `nikita/db/repositories/user_repository.py`

**Acceptance Criteria**:
- [x] AC-T5-001: UserRepository has `set_boss_fight_status(user_id)` method
- [x] AC-T5-002: UserRepository has `advance_chapter(user_id)` method
- [x] AC-T5-003: UserRepository has `increment_boss_attempts(user_id)` method
- [x] AC-T5-004: All methods use atomic transactions with score_history logging

**Implementation Notes**:
- Extend existing `nikita/db/repositories/user.py`
- Pattern: Follow existing async SQLAlchemy patterns

---

**Checkpoint**: Boss trigger detection functional. Can detect threshold and initiate encounter.

---

## Phase 3: US-2 - Boss Pass (Priority: P1)

**From spec.md**: User passes boss → chapter advances → new behaviors unlock

**Goal**: Judge boss outcome and handle successful pass with chapter advancement

**Independent Test**: Complete boss successfully, verify chapter advance and state reset

**Acceptance Criteria** (from spec.md):
- AC-FR004-001: Given user demonstrates required skill, When boss judged, Then PASS result
- AC-FR005-001: Given PASS result, When processed, Then chapter increments by 1
- AC-FR005-002: Given chapter advanced, When next conversation, Then new chapter behaviors active

### Intelligence Queries for US-2

```bash
# Find LLM call patterns
project-intel.mjs --search "claude" --type py --json

# Check agent structure
project-intel.mjs --symbols nikita/agents/text/agent.py --json
```

### T6: Create Boss Judgment Module
- **Status**: [x] Complete
- **User Story**: US-2
- **Dependencies**: T2 → T6
- **File**: `nikita/engine/chapters/judgment.py`

**Acceptance Criteria**:
- [x] AC-FR004-001: Given user demonstrates required skill, When `judge_boss_outcome()` called, Then returns BossResult.PASS
- [x] AC-T6-001: `nikita/engine/chapters/judgment.py` exists with BossJudgment class
- [x] AC-T6-002: Judgment uses Claude Sonnet with chapter-specific criteria
- [x] AC-T6-003: Returns structured result: {outcome: PASS|FAIL, reasoning: str}

**Implementation Notes**:
- LLM call with temperature=0 for consistency
- Include conversation history in judgment context
- Timeout: 5 seconds max

---

### T7: Implement Chapter Advancement
- **Status**: [x] Complete
- **User Story**: US-2
- **Dependencies**: T5, T6 → T7
- **File**: `nikita/engine/chapters/boss.py`

**Acceptance Criteria**:
- [x] AC-FR005-001: Given PASS result, When `process_pass()` called, Then chapter += 1
- [x] AC-FR005-002: Given chapter advanced, When processed, Then boss_attempts reset to 0
- [x] AC-T7-001: game_status set back to 'active'
- [x] AC-T7-002: score_history logged with event_type='boss_pass'

**Implementation Notes**:
- Use `UserRepository.advance_chapter()` from T5
- Emit event for potential notifications

---

**Checkpoint**: Boss pass flow complete. User can pass boss and advance chapters.

---

## Phase 4: US-3 - Boss Fail (Priority: P1)

**From spec.md**: User fails boss → attempt incremented → can retry (up to 3)

**Goal**: Handle failed boss attempts with penalty and retry mechanism

**Independent Test**: Fail boss on purpose, verify attempt count increments, retry available

**Acceptance Criteria** (from spec.md):
- AC-FR004-002: Given user fails to demonstrate skill, When boss judged, Then FAIL result
- AC-FR006-001: Given FAIL result, When processed, Then boss_attempts += 1
- AC-FR006-002: Given FAIL and attempts < 3, When processed, Then retry allowed

### T8: Implement Boss Failure Handling
- **Status**: [x] Complete
- **User Story**: US-3
- **Dependencies**: T6 → T8
- **File**: `nikita/engine/chapters/boss.py`

**Acceptance Criteria**:
- [x] AC-FR004-002: Given user fails to demonstrate skill, When judged, Then returns BossResult.FAIL
- [x] AC-FR006-001: Given FAIL result, When `process_fail()` called, Then boss_attempts += 1
- [x] AC-FR006-002: Given FAIL and attempts < 3, When processed, Then game_status remains 'boss_fight'
- [ ] AC-T8-001: Score penalty of -10% applied to composite score (deferred - needs scoring engine integration)

**Implementation Notes**:
- Use `UserRepository.increment_boss_attempts()` from T5
- Apply score penalty through scoring engine integration

---

**Checkpoint**: Boss fail flow complete. User can fail and retry up to 3 times.

---

## Phase 5: US-4 - Game Over (Boss Failures) (Priority: P1)

**From spec.md**: Third boss failure → game over → relationship ended

**Goal**: Trigger game over state after 3 failed boss attempts

**Independent Test**: Fail boss 3 times, verify game over state

**Acceptance Criteria** (from spec.md):
- AC-FR007-001: Given boss_attempts = 2, When third fail, Then game_over triggered
- AC-FR007-002: Given game_over, When triggered, Then breakup message delivered
- AC-FR007-003: Given game_over, When user messages, Then cannot continue (must start new game)

### T9: Implement Three-Strike Game Over
- **Status**: [x] Complete
- **User Story**: US-4
- **Dependencies**: T8 → T9
- **File**: `nikita/engine/chapters/boss.py`

**Acceptance Criteria**:
- [x] AC-FR007-001: Given boss_attempts = 2, When third fail processed, Then game_status = 'game_over'
- [x] AC-FR007-002: Given game_over, When triggered, Then breakup message returned
- [ ] AC-FR007-003: Given game_over, When user sends message, Then agent rejects (deferred - needs agent integration T12)

**Implementation Notes**:
- Check boss_attempts after increment in T8
- Store game_over_reason in event_details: 'boss_failures'

---

**Checkpoint**: Game over from boss failures functional.

---

## Phase 6: US-5 - Game Over (Zero Score) (Priority: P1)

**From spec.md**: Score drops to 0% → game over → relationship dead

**Goal**: Trigger game over when relationship score reaches zero

**Independent Test**: Let score decay to zero, verify game over

**Acceptance Criteria** (from spec.md):
- AC-FR008-001: Given score at 5%, When decay applies -5%, Then game_over triggered
- AC-FR008-002: Given zero-score game over, When triggered, Then different message than boss fail
- AC-FR008-003: Given game_over, When status checked, Then correct reason recorded

### T10: [P] Implement Zero Score Game Over
- **Status**: [x] Complete
- **User Story**: US-5
- **Dependencies**: T1 → T10 (parallel with T3-T9)
- **File**: `nikita/engine/chapters/boss.py`

**Acceptance Criteria**:
- [x] AC-FR008-001: should_trigger_boss returns False when score=0 or game_status='game_over'
- [ ] AC-FR008-002: Given zero-score game over, When triggered, Then different message than boss fail (deferred - needs decay integration)
- [ ] AC-FR008-003: Given game_over, When status checked, Then reason = 'zero_score' (deferred - needs decay integration)

**Implementation Notes**:
- Hook into scoring engine (003) score update flow
- Different game_over_reason for distinct message selection

---

**Checkpoint**: Both game over paths functional (boss failures + zero score).

---

## Phase 7: US-6 - Victory (Priority: P1)

**From spec.md**: Pass Chapter 5 boss → victory → relationship established

**Goal**: Recognize victory state when Chapter 5 boss passed

**Independent Test**: Complete all 5 bosses, verify victory state

**Acceptance Criteria** (from spec.md):
- AC-FR009-001: Given Ch5 boss passed, When processed, Then game_status = "won"
- AC-FR009-002: Given victory, When triggered, Then celebration message delivered
- AC-FR009-003: Given victory, When continuing, Then post-game mode (no stakes)

### T11: Implement Victory Condition
- **Status**: [x] Complete
- **User Story**: US-6
- **Dependencies**: T7 → T11
- **File**: `nikita/engine/chapters/boss.py`

**Acceptance Criteria**:
- [x] AC-FR009-001: Given Ch5 boss passed, When processed, Then game_status = 'won'
- [x] AC-FR009-002: should_trigger_boss returns False when game_status='won'
- [ ] AC-FR009-003: Given victory, When continuing, Then post-game mode (deferred - needs decay/agent integration)

**Implementation Notes**:
- Special case in T7's chapter advancement (chapter 5 → won)
- Post-game flag prevents decay and boss triggers

---

**Checkpoint**: Victory condition functional. Game can be won.

---

## Phase 8: Agent Integration

**Purpose**: Integrate boss system with existing text agent

### T12: Integrate Boss System with Text Agent
- **Status**: [x] Complete
- **User Story**: All US (Integration)
- **Dependencies**: T4, T6, T7, T8, T9, T11 → T12
- **File**: `nikita/agents/text/handler.py`

**Acceptance Criteria**:
- [x] AC-T12-001: Text agent checks game_status before processing
- [x] AC-T12-002: Boss encounter uses immediate response (no delay)
- [x] AC-T12-003: boss_fight state bypasses skip decision
- [x] AC-T12-004: Game over state returns ended message, prevents normal chat

**Implementation Notes**:
- Modify `nikita/agents/text/handler.py`
- Add boss mode to system prompt builder
- Gate messages based on game_status

---

**Checkpoint**: Boss system fully integrated with text agent.

---

## Phase 9: Testing & Verification

**Purpose**: Comprehensive test coverage for all boss system functionality

### T13: [P] Unit Tests for Boss State Machine
- **Status**: [x] Complete
- **User Story**: All US (Quality)
- **Dependencies**: T1-T11 → T13 (parallel with T12)
- **File**: `tests/engine/chapters/` (multiple files)

**Acceptance Criteria**:
- [x] AC-T13-001: test_boss_threshold_detection covers all 5 chapters (test_threshold.py)
- [x] AC-T13-002: test_boss_pass covers chapter advancement (test_advancement.py)
- [x] AC-T13-003: test_boss_fail covers attempt increment (test_failure.py)
- [x] AC-T13-004: test_game_over covers both 3-fail and 0-score paths (test_game_over.py)
- [x] AC-T13-005: test_victory covers Ch5 pass → won state (test_game_over.py)

**Implementation Notes**:
- File: `tests/engine/test_boss.py`
- Use mock for LLM judgment calls

---

### T14: Integration Tests
- **Status**: [x] Complete
- **User Story**: All US (Quality)
- **Dependencies**: T12, T13 → T14
- **File**: `tests/integration/test_boss_flow.py`

**Acceptance Criteria**:
- [x] AC-T14-001: Full boss encounter flow tested end-to-end (4 flow tests)
- [x] AC-T14-002: Agent integration verified with mock messages (3 handler tests)
- [x] AC-T14-003: Database state transitions verified (5 state tests)

**Implementation Notes**:
- File: `tests/integration/test_boss_flow.py`
- Use test database with fixtures

---

**Final Verification**: Run all tests, verify all acceptance criteria pass

---

## Dependencies & Execution Order

### Phase Dependencies

| Phase | Depends On | Can Start After | Parallelizable |
|-------|-----------|-----------------|----------------|
| **Phase 1: Setup** | None | Immediately | T1 ∥ T2 |
| **Phase 2: US-1** | Phase 1 complete | Setup done | T5 ∥ T3→T4 |
| **Phase 3: US-2** | T2, T5 complete | Foundational ready | Sequential T6→T7 |
| **Phase 4: US-3** | T6 complete | After judgment | Sequential T8 |
| **Phase 5: US-4** | T8 complete | After fail handling | Sequential T9 |
| **Phase 6: US-5** | T1 complete | After setup | T10 ∥ T3-T9 |
| **Phase 7: US-6** | T7 complete | After chapter advance | Sequential T11 |
| **Phase 8: Integration** | T4,T6-T9,T11 complete | After all core tasks | Sequential T12 |
| **Phase 9: Testing** | T1-T11 complete | After implementation | T13 ∥ T12 |

### Critical Path

```
T1 → T3 → T4 → T6 → T7 → T11 → T12 → T14
```

### Parallel Opportunities

- **Phase 1**: T1 ∥ T2 (different files)
- **Phase 2**: T5 ∥ (T3 → T4) (repository vs state machine)
- **Phase 6**: T10 ∥ (T3-T9) (zero score separate from boss flow)
- **Phase 9**: T13 ∥ T12 (unit tests vs integration)

---

## Implementation Strategy

### MVP First (US-1 + US-2)

**Fastest path to validated value:**

1. Complete Phase 1: Setup (T1, T2)
2. Complete Phase 2: US-1 (T3, T4, T5) - Boss triggers
3. Complete Phase 3: US-2 (T6, T7) - Boss pass works
4. **STOP and VALIDATE**: Test boss trigger → pass → chapter advance
5. Deploy/demo if ready (minimum viable boss system!)

### Full Implementation

1. Setup (T1, T2) → Foundation ready
2. US-1 (T3-T5) → Boss triggers
3. US-2 (T6, T7) → Pass works
4. US-3 (T8) → Fail works
5. US-4 (T9) → Game over (boss)
6. US-5 (T10) → Game over (score) - can run in parallel
7. US-6 (T11) → Victory
8. Integration (T12) → Agent integration
9. Testing (T13, T14) → Full verification

---

## CoD^Σ Evidence Requirements

For EVERY implementation task, document:

- **Pattern Evidence**: "Based on pattern at [file:line] found via intel query"
- **Contract Evidence**: "Implementing contract in constants.py"
- **Schema Evidence**: "Using schema from user.py model"
- **Dependency Evidence**: "Depends on T# which provides [functionality]"

**Traceability**: All decisions must trace to spec.md, plan.md, or intel queries

---

## Progress Summary

| Phase/User Story | Tasks | Completed | Status |
|------------------|-------|-----------|--------|
| Phase 1: Setup | 2 (T1, T2) | 2 | ✅ Complete |
| Phase 2: US-1 Boss Trigger | 3 (T3, T4, T5) | 3 | ✅ Complete |
| Phase 3: US-2 Boss Pass | 2 (T6, T7) | 2 | ✅ Complete |
| Phase 4: US-3 Boss Fail | 1 (T8) | 1 | ✅ Complete |
| Phase 5: US-4 Game Over (Boss) | 1 (T9) | 1 | ✅ Complete |
| Phase 6: US-5 Game Over (Score) | 1 (T10) | 1 | ✅ Complete |
| Phase 7: US-6 Victory | 1 (T11) | 1 | ✅ Complete |
| Phase 8: Integration | 1 (T12) | 1 | ✅ Complete |
| Phase 9: Testing | 2 (T13, T14) | 2 | ✅ Complete |
| **TOTAL** | **14** | **14** | **✅ COMPLETE (100%)** |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-29 | Initial task generation from plan.md |
| 1.1 | 2025-12-10 | T1-T5 implemented (65 tests), Progress Summary updated |
| 1.2 | 2025-12-11 | T6-T11 implemented (119 tests), 79% complete |
| 2.0 | 2025-12-11 | **COMPLETE** - All T1-T14 implemented (142 tests) |

---

**Generated by**: generate-tasks skill via /tasks command
**Validated by**: /audit command (cross-artifact consistency check)
**Next Step**: /implement plan.md (progressive story-by-story implementation)
