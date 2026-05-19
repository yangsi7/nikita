# Implementation Plan: 005-Decay-System

## Goal

**Objective**: Build the decay system that enforces "use it or lose it" mechanics by reducing relationship scores when users don't interact.

**Success Definition**: Scheduled decay applies correctly to inactive users based on chapter-specific rates and grace periods, with proper game over handling at 0%.

**Based On**: `spec.md` (FR-001 to FR-010, US-1 to US-6)

---

## Summary

**Overview**: The decay system uses pg_cron scheduled jobs to check all active users periodically. For each user past their grace period, it calculates decay based on chapter-specific rates, applies the reduction atomically, logs to score_history, and emits events for critical thresholds (0% = game over).

**Tech Stack**:
- **Backend**: Python + Supabase Edge Functions (pg_cron triggers)
- **Database**: Supabase PostgreSQL (batch updates)
- **Scheduling**: pg_cron (from 011-background-tasks)
- **Testing**: pytest + pytest-asyncio

**Deliverables**:
1. `DecayCalculator` - Calculates decay amounts based on time overdue
2. `DecayProcessor` - Batch processes all users due for decay
3. `decay_check` Edge Function - Triggered by pg_cron for scheduled decay
4. Score history logging with event_type='decay'

---

## Technical Context

### Existing Architecture (Intelligence Evidence)

**Intelligence Queries Executed**:
```bash
# Existing decay constants
rg "DECAY_RATES|GRACE_PERIODS" nikita/engine/constants.py
# Found: Lines 33-49

# User model with last_interaction_at
rg "last_interaction_at" nikita/db/models/
# Found: nikita/db/models/user.py:66
```

**Patterns Discovered** (CoD^Σ Evidence):
- **Pattern 1**: `DECAY_RATES` @ `nikita/engine/constants.py:33-40`
  - Usage: Chapter-indexed decay rates {1: 5.0%, 2: 4.0%, 3: 3.0%, 4: 2.0%, 5: 1.0%}
  - Applicability: Direct use in decay calculation
- **Pattern 2**: `GRACE_PERIODS` @ `nikita/engine/constants.py:43-49`
  - Usage: Chapter-indexed grace periods as timedelta
  - Applicability: Direct use in overdue calculation
- **Pattern 3**: `ScoreHistoryRepository.log_event()` @ `nikita/db/repositories/score_history_repository.py`
  - Usage: Score event logging
  - Applicability: Reuse for decay history with event_type='decay'

**CoD^Σ Evidence Chain**:
```
spec.requirements ∘ existing_constants → decay_engine_design
Evidence: spec.md + constants.py:33-49 + score_history_repository.py → plan.md
```

---

## Constitution Check (Article VI)

### Pre-Design Gates

```
Gate₁: Project Count (≤3)
  Status: PASS ✓
  Count: 1 project (Nikita decay system)
  Decision: PROCEED

Gate₂: Abstraction Layers (≤2 per concept)
  Status: PASS ✓
  Details: DecayCalculator → DecayProcessor (2 layers)
  Decision: PROCEED

Gate₃: Framework Trust (use directly)
  Status: PASS ✓
  Details: Using pg_cron directly, existing repositories
  Decision: PROCEED
```

**Overall Pre-Design Gate**: PASS ✓

---

## Architecture (CoD^Σ)

### Component Breakdown

**System Flow**:
```
pg_cron_trigger → Edge_Function → DecayProcessor → DecayCalculator → Database
       ↓               ↓               ↓                ↓             ↓
    Schedule        HTTP_call       Batch_users     Calculate_Δ    Update_scores
                                        ↓                             ↓
                                   User_filter                   Log_history
                                        ↓                             ↓
                                   Past_grace?                  Emit_events
```

**Dependencies** (CoD^Σ Notation):
```
DecayCalculator ⇐ DECAY_RATES, GRACE_PERIODS (constants.py)
DecayProcessor ⇐ UserRepository, ScoreHistoryRepository (existing)
EdgeFunction → DecayProcessor (triggers)
DecayProcessor → ThresholdEmitter (downstream, for game_over)
```

**Modules**:
1. **decay/calculator.py**: `nikita/engine/decay/`
   - Purpose: Calculate decay amount based on time overdue
   - Exports: DecayCalculator, DecayResult
   - Imports: DECAY_RATES, GRACE_PERIODS from constants.py

2. **decay/processor.py**: `nikita/engine/decay/`
   - Purpose: Batch process all users due for decay
   - Exports: DecayProcessor
   - Imports: DecayCalculator, UserRepository, ScoreHistoryRepository

3. **supabase/functions/decay-check/**: Edge Function
   - Purpose: pg_cron triggered function for scheduled decay
   - Exports: HTTP endpoint
   - Imports: Calls DecayProcessor via internal API

---

## User Story Implementation Plan

### User Story P1: Grace Period Protection (Priority: Must-Have)

**Goal**: Protect users from decay during grace period

**Acceptance Criteria** (from spec.md):
- AC-FR001-001: Given Ch1 user, When inactive for 20 hours, Then NO decay applied
- AC-FR001-002: Given Ch1 user, When inactive for 25 hours, Then decay IS applied
- AC-FR001-003: Given Ch5 user, When inactive for 90 hours, Then NO decay applied

**Implementation Approach**:
1. Create DecayCalculator with is_overdue() check
2. Use GRACE_PERIODS from constants.py
3. Return None if within grace period

**Evidence**: Based on `constants.py:43-49` (GRACE_PERIODS)

---

### User Story P1: Decay Application (Priority: Must-Have)

**Goal**: Calculate and apply correct decay amounts

**Acceptance Criteria** (from spec.md):
- AC-FR002-001: Given Ch1 user past grace, When 2h overdue, Then -1.6% decay applied (2h × 0.8%/h)
- AC-FR003-001: Given Ch1 user past grace, When 10h overdue, Then -8.0% decay applied (10h × 0.8%/h)
- AC-FR003-002: Given decay applied, When calculated, Then capped at daily max (Ch1: 15pts)

**Implementation Approach**:
1. Calculate hours_overdue from (now - last_interaction - grace)
2. Apply chapter-specific hourly rate × hours_overdue
3. Cap at daily maximum per chapter

**Evidence**: Based on `constants.py:33-40` (DECAY_RATES)

---

### User Story P1: Interaction Reset (Priority: Must-Have)

**Goal**: Reset grace period on qualifying interactions

**Acceptance Criteria** (from spec.md):
- AC-FR006-001: Given decaying user, When they send message, Then last_interaction_at updated
- AC-FR006-002: Given reset interaction, When next decay check, Then grace period restarted
- AC-FR006-003: Given portal-only activity, When decay check, Then NO reset

**Implementation Approach**:
1. Text agent calls update_last_interaction()
2. Voice agent calls update_last_interaction()
3. Portal does NOT call update (explicitly excluded)

**Evidence**: User model has `last_interaction_at` field

---

### User Story P1: Decay Game Over (Priority: Must-Have)

**Goal**: Trigger game over when decay reduces score to 0%

**Acceptance Criteria** (from spec.md):
- AC-FR005-001: Given user at 3%, When -5% decay applies, Then score floors at 0%
- AC-FR007-001: Given score reaches 0% via decay, Then game_over event emitted
- AC-FR008-001: Given decay-caused game over, Then reason = "decay" logged

**Implementation Approach**:
1. Floor score at 0 during decay application
2. Emit game_over event with reason="decay"
3. Log to score_history with event_type='decay_game_over'

**Evidence**: Based on ThresholdEmitter from 003-scoring-engine

---

### User Story P1: Scheduled Processing (Priority: Must-Have)

**Goal**: Run decay on schedule for all users

**Acceptance Criteria** (from spec.md):
- AC-FR004-001: Given scheduler configured for hourly, When hour passes, Then all users checked
- AC-FR004-002: Given 1000 overdue users, When batch processed, Then all receive correct decay
- AC-FR004-003: Given scheduler crash, When restarted, Then resumes without duplication

**Implementation Approach**:
1. pg_cron job triggers Edge Function at midnight UTC
2. Edge Function calls DecayProcessor.process_all()
3. Batch processing with idempotency (last_decay_applied_at tracking)

**Evidence**: Based on 011-background-tasks infrastructure

---

### User Story P2: Boss Fight Pause (Priority: Important)

**Goal**: Pause decay during boss encounters

**Acceptance Criteria** (from spec.md):
- AC-FR009-001: Given user in boss_fight status, When decay check runs, Then NO decay applied
- AC-FR009-002: Given boss completed, When decay resumes, Then grace period starts fresh
- AC-FR009-003: Given long boss attempt, When eventually resolved, Then decay does not "catch up"

**Implementation Approach**:
1. DecayProcessor.should_apply_decay() checks game_status
2. Skip users with game_status='boss_fight' or 'won' or 'game_over'
3. Grace period resets on boss resolution

**Evidence**: User model has `game_status` field

---

## Tasks

### Task 1: [US1] Create DecayResult Model
- **ID:** T1
- **User Story**: P1 - Grace Period Protection, Decay Application
- **Owner:** executor-agent
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): None
- **Estimated Complexity:** Low

**Acceptance Criteria**:
- [ ] AC-T1.1: DecayResult has user_id, decay_amount, score_before, score_after fields
- [ ] AC-T1.2: DecayResult has days_overdue field for audit
- [ ] AC-T1.3: DecayResult has chapter and timestamp fields

**Implementation Notes:**
- **Pattern Evidence**: Based on Pydantic patterns in `nikita/api/schemas/`
- **File**: `nikita/engine/decay/models.py`

---

### Task 2: [US1] Create DecayCalculator Class
- **ID:** T2
- **User Story**: P1 - Grace Period Protection, Decay Application
- **Owner:** executor-agent
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T1 → T2
- **Estimated Complexity:** Medium

**Acceptance Criteria**:
- [ ] AC-T2.1: `is_overdue(user)` returns bool based on GRACE_PERIODS
- [ ] AC-T2.2: `calculate_decay(user)` returns DecayResult or None if within grace
- [ ] AC-T2.3: Uses DECAY_RATES from constants.py
- [ ] AC-T2.4: Decay capped at MAX_DECAY_PER_CYCLE (configurable, default 20%)
- [ ] AC-T2.5: Handles edge case where score would go negative (floor at 0)

**Implementation Notes:**
- **Pattern Evidence**: Based on `constants.py:33-49` (DECAY_RATES, GRACE_PERIODS)
- **File**: `nikita/engine/decay/calculator.py`

---

### Task 3: [US3] Create Interaction Reset Method
- **ID:** T3
- **User Story**: P1 - Interaction Reset
- **Owner:** executor-agent
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T1 ⊥ T3 (independent of T1)
- **Estimated Complexity:** Low

**Acceptance Criteria**:
- [ ] AC-T3.1: `UserRepository.update_last_interaction(user_id, timestamp)` method
- [ ] AC-T3.2: Updates `last_interaction_at` atomically
- [ ] AC-T3.3: Called from text agent after message processing
- [ ] AC-T3.4: Called from voice agent after call completion

**Implementation Notes:**
- **File**: `nikita/db/repositories/user_repository.py` (extend)

---

### Task 4: [US4] Integrate Decay with Game Over
- **ID:** T4
- **User Story**: P1 - Decay Game Over
- **Owner:** executor-agent
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T2 → T4
- **Estimated Complexity:** Medium

**Acceptance Criteria**:
- [ ] AC-T4.1: DecayCalculator floors score at 0 (never negative)
- [ ] AC-T4.2: When score = 0, emit game_over event with reason="decay"
- [ ] AC-T4.3: Update user.game_status to "game_over"
- [ ] AC-T4.4: Log to score_history with event_type='decay_game_over'

**Implementation Notes:**
- **Pattern Evidence**: Based on ThresholdEmitter from 003-scoring-engine
- **File**: `nikita/engine/decay/calculator.py` (extend)

---

### Task 5: [US5] Create DecayProcessor Class
- **ID:** T5
- **User Story**: P1 - Scheduled Processing
- **Owner:** executor-agent
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T2 → T5, T4 → T5
- **Estimated Complexity:** High

**Acceptance Criteria**:
- [ ] AC-T5.1: `process_all()` fetches all active users needing decay check
- [ ] AC-T5.2: Filters out game_status in ['boss_fight', 'game_over', 'won']
- [ ] AC-T5.3: Batches users to prevent memory issues (configurable batch size)
- [ ] AC-T5.4: Calls DecayCalculator for each user past grace
- [ ] AC-T5.5: Returns summary: {processed: N, decayed: M, game_overs: K}

**Implementation Notes:**
- **File**: `nikita/engine/decay/processor.py`

---

### Task 6: [US5] Create Decay History Logging
- **ID:** T6
- **User Story**: P1 - Scheduled Processing, Decay Game Over
- **Owner:** executor-agent
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T5 → T6
- **Estimated Complexity:** Low

**Acceptance Criteria**:
- [ ] AC-T6.1: Each decay application logged to score_history
- [ ] AC-T6.2: event_type = 'decay' for normal decay
- [ ] AC-T6.3: event_details includes days_overdue, chapter, decay_rate
- [ ] AC-T6.4: Idempotency: same decay period not logged twice

**Implementation Notes:**
- **Pattern Evidence**: Based on `score_history_repository.py:log_event()`
- **File**: `nikita/engine/decay/processor.py` (integrate)

---

### Task 7: [US6] Implement Boss Fight Decay Pause
- **ID:** T7
- **User Story**: P2 - Boss Fight Pause
- **Owner:** executor-agent
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T5 → T7
- **Estimated Complexity:** Low

**Acceptance Criteria**:
- [ ] AC-T7.1: DecayProcessor.should_skip_user() checks game_status
- [ ] AC-T7.2: Skips users with game_status in ['boss_fight', 'game_over', 'won']
- [ ] AC-T7.3: Does NOT catch up on missed decay after boss resolved
- [ ] AC-T7.4: Grace period resets to now after boss_pass or boss_fail

**Implementation Notes:**
- **File**: `nikita/engine/decay/processor.py` (extend)

---

### Task 8: [US5] Create Decay Edge Function
- **ID:** T8
- **User Story**: P1 - Scheduled Processing
- **Owner:** executor-agent
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T5 → T8, T6 → T8, T7 → T8
- **Estimated Complexity:** Medium

**Acceptance Criteria**:
- [ ] AC-T8.1: Edge Function `decay-check` responds to pg_cron webhook
- [ ] AC-T8.2: Authenticates via service role key
- [ ] AC-T8.3: Calls DecayProcessor.process_all() via internal API
- [ ] AC-T8.4: Returns JSON summary {processed, decayed, game_overs}
- [ ] AC-T8.5: Handles errors gracefully with logging

**Implementation Notes:**
- **Pattern Evidence**: Based on 011-background-tasks Edge Function pattern
- **File**: `supabase/functions/decay-check/index.ts`

---

### Task 9: [US1-US6] Create Unit Tests for Decay System
- **ID:** T9
- **User Story**: All user stories
- **Owner:** executor-agent
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T1 ∧ T2 ∧ T3 ∧ T4 ∧ T5 ∧ T6 ∧ T7 → T9
- **Estimated Complexity:** Medium

**Acceptance Criteria**:
- [ ] AC-T9.1: Test DecayCalculator.is_overdue() for all chapters
- [ ] AC-T9.2: Test DecayCalculator.calculate_decay() for various overdue durations
- [ ] AC-T9.3: Test decay cap at MAX_DECAY_PER_CYCLE
- [ ] AC-T9.4: Test score floor at 0
- [ ] AC-T9.5: Test boss_fight pause logic
- [ ] AC-T9.6: 80%+ code coverage for decay module

**Implementation Notes:**
- **File**: `tests/engine/decay/`

---

## Dependencies

### Task Dependency Graph (CoD^Σ)
```
T1 (models) → T2 (calculator)
                  ↘ T4 (game over integration)
                      ↘ T5 (processor) → T6 (logging)
                                   ↘ T7 (boss pause)
                                       ↘ T8 (edge function)
                                            ↘ T9 (tests)
T3 (interaction reset) ⊥ T2 (can run in parallel)
```

**Critical Path**: T1 → T2 → T5 → T8 (processor complexity)
**Parallelizable**: T3 ⊥ {T1, T2} (independent repository method)

### External Dependencies
- **Library**: pydantic (already installed)
- **Infrastructure**: pg_cron (from 011-background-tasks)
- **Database**: Supabase (existing repositories)

### File Dependencies
```
constants.py → calculator.py (DECAY_RATES, GRACE_PERIODS)
user_repository.py → processor.py (batch user queries)
score_history_repository.py → processor.py (logging)
```

---

## Risks (CoD^Σ)

### Risk 1: Runaway Decay (Catch-up)
- **Likelihood (p):** Medium (0.5)
- **Impact:** High (8)
- **Risk Score:** r = 4.0
- **Mitigation**:
  - MAX_DECAY_PER_CYCLE cap (default 20%)
  - No "catch up" after boss fight
  - Warning logs for unusually large decay amounts

### Risk 2: Scheduler Failures
- **Likelihood (p):** Low (0.2)
- **Impact:** Medium (5)
- **Risk Score:** r = 1.0
- **Mitigation**:
  - pg_cron is reliable (PostgreSQL native)
  - Health check endpoint for monitoring
  - Manual trigger capability via API

### Risk 3: Race Conditions
- **Likelihood (p):** Low (0.2)
- **Impact:** Low (3)
- **Risk Score:** r = 0.6
- **Mitigation**:
  - Atomic transactions for score updates
  - Check last_interaction_at within transaction
  - Idempotency via last_decay_applied_at

---

## Verification (CoD^Σ)

### Test Strategy
```
Unit → Integration → Manual
  ↓         ↓          ↓
Fast     Medium      Slow
```

- **Unit Tests**: `tests/engine/decay/test_calculator.py`, `test_processor.py`
- **Integration Tests**: Full decay cycle with mock time
- **Manual Tests**: Edge Function invocation, pg_cron verification

### AC Coverage Map
```
AC-FR001-001 → test_calculator.py:test_within_grace_no_decay ✓
AC-FR001-002 → test_calculator.py:test_past_grace_decay_applies ✓
AC-FR002-001 → test_calculator.py:test_ch1_decay_rate ✓
AC-FR003-001 → test_calculator.py:test_multi_day_decay ✓
AC-FR005-001 → test_calculator.py:test_score_floor_zero ✓
AC-FR006-001 → test_processor.py:test_interaction_resets_grace ✓
AC-FR009-001 → test_processor.py:test_boss_fight_skipped ✓
```

---

## Files Created/Modified

| File | Action | Purpose |
|------|--------|---------|
| `nikita/engine/decay/__init__.py` | Create | Package init |
| `nikita/engine/decay/models.py` | Create | DecayResult model |
| `nikita/engine/decay/calculator.py` | Create | DecayCalculator class |
| `nikita/engine/decay/processor.py` | Create | DecayProcessor class |
| `nikita/db/repositories/user_repository.py` | Modify | Add update_last_interaction() |
| `supabase/functions/decay-check/index.ts` | Create | pg_cron triggered function |
| `tests/engine/decay/` | Create | Unit tests |

---

## Progress Tracking

**Total Tasks (N):** 9
**Completed (X):** 0
**In Progress (Y):** 0
**Blocked (Z):** 0

**Progress Ratio:** 0/9 = 0%

---

## Notes

**Constitutional Compliance**:
- §III.3: Decay enforces "use it or lose it" per spec
- §VII.1: Test-first approach with comprehensive coverage

**Infrastructure Dependency**:
- Requires 011-background-tasks pg_cron job setup
- Edge Function pattern from that spec applies here
