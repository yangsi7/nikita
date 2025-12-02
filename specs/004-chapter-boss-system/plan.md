# Implementation Plan: Chapter & Boss System (004)

**Created**: 2025-11-29
**Spec**: specs/004-chapter-boss-system/spec.md
**Status**: Ready for Implementation

---

## Goal

Implement the Chapter & Boss System that provides progression mechanics and win/lose conditions. Users advance through 5 chapters by passing boss encounters (skill-based conversational challenges). Failing 3 bosses or reaching 0% score = game over. Passing Chapter 5 boss = victory.

**Success Definition**: Complete boss encounter state machine with detection, triggering, judgment, and all outcome paths (pass, fail, game over, victory).

---

## Summary

**Tech Stack**:
- **Backend**: Python 3.12 + Pydantic AI + FastAPI
- **Database**: Supabase PostgreSQL (existing models)
- **AI**: Claude Sonnet for boss judgment
- **Testing**: pytest + pytest-asyncio

**Deliverables**:
1. Boss state machine (`nikita/engine/chapters/boss.py`)
2. Boss judgment system (`nikita/engine/chapters/judgment.py`)
3. Repository methods for chapter/boss state updates
4. Integration with text agent for boss encounters
5. Comprehensive test coverage

---

## Technical Context

### Existing Architecture (from Explore)

**Constants (nikita/engine/constants.py)**:
- `BOSS_THRESHOLDS`: {1:60, 2:65, 3:70, 4:75, 5:80} ✓
- `BOSS_ENCOUNTERS`: 5 encounters with name, trigger, challenge ✓
- `GAME_STATUSES`: active, boss_fight, game_over, won ✓

**User Model (nikita/db/models/user.py)**:
- `chapter: int` (1-5) with constraints ✓
- `boss_attempts: int` (0-3) with constraints ✓
- `game_status: str` (active/boss_fight/game_over/won) ✓
- `relationship_score: Decimal` (0-100) ✓

**Agent Pattern (nikita/agents/text/)**:
- Pydantic AI + Claude Sonnet
- Dynamic system prompt with chapter behaviors
- Tool registration pattern established

---

## Architecture (CoD^Σ)

### Component Flow
```
Score_update → threshold_check → boss_trigger → encounter_mode
                                      ↓
                              judgment_phase → PASS → chapter_advance
                                    ↓
                                  FAIL → attempts++ → (3x) game_over
```

### Module Structure
```
nikita/engine/chapters/
├── __init__.py           # Exports
├── boss.py               # BossStateMachine class
├── judgment.py           # BossJudgment class (LLM-based)
└── prompts.py            # Boss encounter prompts
```

### Dependencies (CoD^Σ)
```
BossStateMachine ⇐ UserRepository (database state)
BossJudgment ⇐ LLM (Claude Sonnet)
TextAgent → BossStateMachine (integration)
ScoreUpdate → threshold_check (003 integration point)
```

---

## Tasks (By User Story)

### Phase 1: Setup (Foundation)

#### T1: Create Boss State Machine Module
- **ID**: T1
- **User Story**: Foundation for all US
- **Dependencies**: None
- **Estimated**: 3 hours

**Acceptance Criteria**:
- [ ] AC-T1-001: `nikita/engine/chapters/boss.py` exists with BossStateMachine class
- [ ] AC-T1-002: Class has methods: `check_threshold()`, `trigger_boss()`, `process_outcome()`
- [ ] AC-T1-003: All methods are async and accept user_id parameter

**Implementation Notes**:
- Pattern: Follow nikita/agents/text/agent.py async patterns
- Integration: Import from nikita/engine/constants.py

---

#### T2: Create Boss Prompts Module
- **ID**: T2
- **User Story**: Foundation for FR-003
- **Dependencies**: T1 ⊥ (parallel)
- **Estimated**: 2 hours

**Acceptance Criteria**:
- [ ] AC-T2-001: `nikita/engine/chapters/prompts.py` exists with 5 boss prompt templates
- [ ] AC-T2-002: Each prompt includes: challenge context, success criteria, in-character opening
- [ ] AC-T2-003: Prompts are parameterized by chapter number (1-5)

**Implementation Notes**:
- Reference: BOSS_ENCOUNTERS in constants.py:113-139
- Pattern: Similar to nikita/prompts/ structure

---

### Phase 2: US-1 Boss Trigger (P1)

#### T3: Implement Threshold Detection
- **ID**: T3
- **User Story**: US-1 (Boss Trigger)
- **Dependencies**: T1 → T3
- **Estimated**: 2 hours

**Acceptance Criteria**:
- [ ] AC-FR001-001: Given user at 59% in Ch1, When score rises to 60%, Then `should_trigger_boss()` returns True
- [ ] AC-T3-001: Method checks score >= BOSS_THRESHOLDS[chapter]
- [ ] AC-T3-002: Method returns False if already in boss_fight or game_over status

**Implementation Notes**:
- Input: user.relationship_score, user.chapter, user.game_status
- Output: bool (should trigger)

---

#### T4: Implement Boss Initiation
- **ID**: T4
- **User Story**: US-1 (Boss Trigger)
- **Dependencies**: T3 → T4
- **Estimated**: 3 hours

**Acceptance Criteria**:
- [ ] AC-FR002-001: Given boss triggered, When `initiate_boss()` called, Then game_status = 'boss_fight'
- [ ] AC-FR002-002: Given boss initiated, When status changes, Then boss challenge prompt returned
- [ ] AC-T4-001: Database updated atomically (status + logged to score_history)

**Implementation Notes**:
- Update UserRepository with `set_boss_fight_status()` method
- Log event_type='boss_initiated' to score_history

---

#### T5: Add UserRepository Boss Methods
- **ID**: T5
- **User Story**: US-1, US-2, US-3
- **Dependencies**: T1 → T5 (parallel with T3, T4)
- **Estimated**: 2 hours

**Acceptance Criteria**:
- [ ] AC-T5-001: UserRepository has `set_boss_fight_status(user_id)` method
- [ ] AC-T5-002: UserRepository has `advance_chapter(user_id)` method
- [ ] AC-T5-003: UserRepository has `increment_boss_attempts(user_id)` method
- [ ] AC-T5-004: All methods use atomic transactions with score_history logging

**Implementation Notes**:
- File: nikita/db/repositories/user.py (extend existing)
- Pattern: Follow existing async SQLAlchemy patterns

---

### Phase 3: US-2 Boss Pass (P1)

#### T6: Create Boss Judgment Module
- **ID**: T6
- **User Story**: US-2 (Boss Pass)
- **Dependencies**: T2 → T6
- **Estimated**: 4 hours

**Acceptance Criteria**:
- [ ] AC-FR004-001: Given user demonstrates required skill, When `judge_boss_outcome()` called, Then returns BossResult.PASS
- [ ] AC-T6-001: `nikita/engine/chapters/judgment.py` exists with BossJudgment class
- [ ] AC-T6-002: Judgment uses Claude Sonnet with chapter-specific criteria
- [ ] AC-T6-003: Returns structured result: {outcome: PASS|FAIL, reasoning: str}

**Implementation Notes**:
- LLM call with temperature=0 for consistency
- Include conversation history in judgment context
- Timeout: 5 seconds max

---

#### T7: Implement Chapter Advancement
- **ID**: T7
- **User Story**: US-2 (Boss Pass)
- **Dependencies**: T5, T6 → T7
- **Estimated**: 2 hours

**Acceptance Criteria**:
- [ ] AC-FR005-001: Given PASS result, When `process_pass()` called, Then chapter += 1
- [ ] AC-FR005-002: Given chapter advanced, When processed, Then boss_attempts reset to 0
- [ ] AC-T7-001: game_status set back to 'active'
- [ ] AC-T7-002: score_history logged with event_type='boss_pass'

**Implementation Notes**:
- Use UserRepository.advance_chapter() from T5
- Emit event for potential notifications

---

### Phase 4: US-3 Boss Fail (P1)

#### T8: Implement Boss Failure Handling
- **ID**: T8
- **User Story**: US-3 (Boss Fail)
- **Dependencies**: T6 → T8
- **Estimated**: 2 hours

**Acceptance Criteria**:
- [ ] AC-FR004-002: Given user fails to demonstrate skill, When judged, Then returns BossResult.FAIL
- [ ] AC-FR006-001: Given FAIL result, When `process_fail()` called, Then boss_attempts += 1
- [ ] AC-FR006-002: Given FAIL and attempts < 3, When processed, Then game_status remains 'boss_fight'
- [ ] AC-T8-001: Score penalty of -10% applied to composite score

**Implementation Notes**:
- Use UserRepository.increment_boss_attempts() from T5
- Apply score penalty through scoring engine integration

---

### Phase 5: US-4 Game Over - Boss Failures (P1)

#### T9: Implement Three-Strike Game Over
- **ID**: T9
- **User Story**: US-4 (Game Over - Boss)
- **Dependencies**: T8 → T9
- **Estimated**: 2 hours

**Acceptance Criteria**:
- [ ] AC-FR007-001: Given boss_attempts = 2, When third fail processed, Then game_status = 'game_over'
- [ ] AC-FR007-002: Given game_over, When triggered, Then breakup message returned
- [ ] AC-FR007-003: Given game_over, When user sends message, Then agent rejects (game ended)

**Implementation Notes**:
- Check boss_attempts after increment in T8
- Store game_over_reason in event_details: 'boss_failures'

---

### Phase 6: US-5 Game Over - Zero Score (P1)

#### T10: Implement Zero Score Game Over
- **ID**: T10
- **User Story**: US-5 (Game Over - Score)
- **Dependencies**: T1 → T10 (parallel with T3-T9)
- **Estimated**: 2 hours

**Acceptance Criteria**:
- [ ] AC-FR008-001: Given score at 5%, When decay applies -5%, Then game_status = 'game_over'
- [ ] AC-FR008-002: Given zero-score game over, When triggered, Then different message than boss fail
- [ ] AC-FR008-003: Given game_over, When status checked, Then reason = 'zero_score'

**Implementation Notes**:
- Hook into scoring engine (003) score update flow
- Different game_over_reason for distinct message selection

---

### Phase 7: US-6 Victory (P1)

#### T11: Implement Victory Condition
- **ID**: T11
- **User Story**: US-6 (Victory)
- **Dependencies**: T7 → T11
- **Estimated**: 2 hours

**Acceptance Criteria**:
- [ ] AC-FR009-001: Given Ch5 boss passed, When processed, Then game_status = 'won'
- [ ] AC-FR009-002: Given victory, When triggered, Then celebration message returned
- [ ] AC-FR009-003: Given victory, When continuing, Then post-game mode (no decay, no bosses)

**Implementation Notes**:
- Special case in T7's chapter advancement (chapter 5 → won)
- Post-game flag prevents decay and boss triggers

---

### Phase 8: Agent Integration

#### T12: Integrate Boss System with Text Agent
- **ID**: T12
- **User Story**: All US (Integration)
- **Dependencies**: T4, T6, T7, T8, T9, T11 → T12
- **Estimated**: 4 hours

**Acceptance Criteria**:
- [ ] AC-T12-001: Text agent checks boss trigger after each score update
- [ ] AC-T12-002: Boss encounter uses special system prompt with challenge
- [ ] AC-T12-003: Agent rejects normal chat during boss_fight (directs to challenge)
- [ ] AC-T12-004: Game over state prevents further agent interaction

**Implementation Notes**:
- Modify nikita/agents/text/handler.py
- Add boss mode to system prompt builder
- Gate messages based on game_status

---

### Phase 9: Testing

#### T13: Unit Tests for Boss State Machine
- **ID**: T13
- **User Story**: All US (Quality)
- **Dependencies**: T1-T11 → T13 (parallel with T12)
- **Estimated**: 3 hours

**Acceptance Criteria**:
- [ ] AC-T13-001: test_boss_threshold_detection covers all 5 chapters
- [ ] AC-T13-002: test_boss_pass covers chapter advancement
- [ ] AC-T13-003: test_boss_fail covers attempt increment
- [ ] AC-T13-004: test_game_over covers both 3-fail and 0-score paths
- [ ] AC-T13-005: test_victory covers Ch5 pass → won state

**Implementation Notes**:
- File: tests/engine/test_boss.py
- Use mock for LLM judgment calls

---

#### T14: Integration Tests
- **ID**: T14
- **User Story**: All US (Quality)
- **Dependencies**: T12, T13 → T14
- **Estimated**: 3 hours

**Acceptance Criteria**:
- [ ] AC-T14-001: Full boss encounter flow tested end-to-end
- [ ] AC-T14-002: Agent integration verified with mock messages
- [ ] AC-T14-003: Database state transitions verified

**Implementation Notes**:
- File: tests/integration/test_boss_flow.py
- Use test database with fixtures

---

## Dependency Graph (CoD^Σ)

```
T1 ──┬──→ T3 → T4 ──────────────────────┐
     │                                   │
     ├──→ T5 ────────────┬──────────────┤
     │                   │               │
     └──→ T10            ↓               ↓
                   T7 ← T6 → T8 → T9    T12 ← All
T2 ──────────────→ T6   ↓               ↓
                        T11             T13 → T14
```

**Critical Path**: T1 → T3 → T4 → T6 → T7 → T11 → T12 → T14

**Parallelizable**: {T2, T5, T10} ⊥ T3 (can run while T3 executes)

---

## Risks

### Risk 1: Boss Judgment Inconsistency
- **Likelihood**: 0.5 | **Impact**: 8 | **Score**: 4.0
- **Mitigation**:
  - Use temperature=0 for deterministic outputs
  - Clear judgment criteria in prompts
  - Log all judgments for audit
  - Consider caching identical conversation patterns

### Risk 2: State Transition Race Conditions
- **Likelihood**: 0.3 | **Impact**: 5 | **Score**: 1.5
- **Mitigation**:
  - Use database transactions with row-level locking
  - All state changes atomic (single commit)
  - Verify state before transitions

---

## Verification

### Test Coverage Target
- Unit tests: 95% for engine/chapters/
- Integration tests: Core flows (trigger → pass/fail → outcome)

### AC Coverage Map
```
FR-001 → T3 (AC-FR001-001)
FR-002 → T4 (AC-FR002-001, AC-FR002-002)
FR-003 → T2 (prompts for 5 bosses)
FR-004 → T6 (AC-FR004-001, AC-FR004-002)
FR-005 → T7 (AC-FR005-001, AC-FR005-002)
FR-006 → T8 (AC-FR006-001, AC-FR006-002)
FR-007 → T9 (AC-FR007-001, AC-FR007-002, AC-FR007-003)
FR-008 → T10 (AC-FR008-001, AC-FR008-002, AC-FR008-003)
FR-009 → T11 (AC-FR009-001, AC-FR009-002, AC-FR009-003)
FR-010 → T5 (repository tracks chapter state)
```

**Coverage**: 10/10 requirements = 100% ✓

---

## Critical Files to Modify

| File | Action | Purpose |
|------|--------|---------|
| `nikita/engine/chapters/boss.py` | CREATE | Boss state machine |
| `nikita/engine/chapters/judgment.py` | CREATE | LLM-based judgment |
| `nikita/engine/chapters/prompts.py` | CREATE | Boss encounter prompts |
| `nikita/engine/chapters/__init__.py` | MODIFY | Export new classes |
| `nikita/db/repositories/user.py` | MODIFY | Add boss/chapter methods |
| `nikita/agents/text/handler.py` | MODIFY | Integrate boss triggers |
| `tests/engine/test_boss.py` | CREATE | Unit tests |
| `tests/integration/test_boss_flow.py` | CREATE | Integration tests |

---

## Estimated Timeline

| Phase | Tasks | Hours | Parallel? |
|-------|-------|-------|-----------|
| Setup | T1, T2 | 5h | T1 ∥ T2 |
| Boss Trigger | T3, T4, T5 | 7h | T5 ∥ T3→T4 |
| Boss Pass | T6, T7 | 6h | Sequential |
| Boss Fail | T8 | 2h | Sequential |
| Game Over (Boss) | T9 | 2h | Sequential |
| Game Over (Score) | T10 | 2h | T10 ∥ T3-T9 |
| Victory | T11 | 2h | Sequential |
| Integration | T12 | 4h | Sequential |
| Testing | T13, T14 | 6h | T13 ∥ T12 |

**Total Estimated**: 34-38 hours (accounting for dependencies)
