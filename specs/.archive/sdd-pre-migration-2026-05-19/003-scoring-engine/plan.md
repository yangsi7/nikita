# Implementation Plan: 003-Scoring-Engine

## Goal

**Objective**: Build the core scoring engine that transforms conversations into game mechanics by analyzing interactions and updating relationship scores.

**Success Definition**: Every user message is analyzed, metric deltas calculated, composite score updated, and threshold events emitted.

**Based On**: `spec.md` (FR-001 to FR-010, US-1 to US-6)

---

## Summary

**Overview**: The scoring engine uses Claude to analyze user-Nikita exchanges and determine impact on four relationship metrics (intimacy, passion, trust, secureness). It calculates deltas within [-10, +10] range, applies them to metrics, recalculates composite score using fixed 30/25/25/20 weights, logs to score history, and emits threshold events.

**Tech Stack**:
- **Backend**: Python + Pydantic AI (Claude analysis)
- **Database**: Supabase PostgreSQL (via existing repositories)
- **Testing**: pytest + pytest-asyncio

**Deliverables**:
1. `ScoreAnalyzer` - LLM-based interaction analysis
2. `ScoreCalculator` - Delta application and composite calculation
3. `ThresholdEmitter` - Event emission for boss/critical thresholds

---

## Technical Context

### Existing Architecture (Intelligence Evidence)

**Intelligence Queries Executed**:
```bash
# Existing scoring patterns
rg -l "score|metric|intimacy" --type py
# Found: 20 files with scoring-related code

# Constants check
rg "METRIC_WEIGHTS|BOSS_THRESHOLDS" nikita/engine/constants.py
# Found: Lines 25-31 (thresholds), 51-57 (weights)
```

**Patterns Discovered** (CoD^Σ Evidence):
- **Pattern 1**: `METRIC_WEIGHTS` @ `nikita/engine/constants.py:51-57`
  - Usage: Fixed weights {intimacy: 0.30, passion: 0.25, trust: 0.25, secureness: 0.20}
  - Applicability: Direct use in composite calculation
- **Pattern 2**: `UserMetricsRepository.update_metrics()` @ `nikita/db/repositories/metrics_repository.py:39-75`
  - Usage: Atomic delta application with clamping
  - Applicability: Reuse for score updates
- **Pattern 3**: `ScoreHistoryRepository.log_event()` @ `nikita/db/repositories/score_history_repository.py:28-57`
  - Usage: Score event logging
  - Applicability: Reuse for history

**CoD^Σ Evidence Chain**:
```
spec.requirements ∘ existing_repositories → engine_design
Evidence: spec.md + metrics_repository.py:39 + score_history_repository.py:28 → plan.md
```

---

## Constitution Check (Article VI)

### Pre-Design Gates

```
Gate₁: Project Count (≤3)
  Status: PASS ✓
  Count: 1 project (Nikita scoring engine)
  Decision: PROCEED

Gate₂: Abstraction Layers (≤2 per concept)
  Status: PASS ✓
  Details: ScoreAnalyzer → ScoreCalculator (2 layers)
  Decision: PROCEED

Gate₃: Framework Trust (use directly)
  Status: PASS ✓
  Details: Using Pydantic AI directly, existing repositories
  Decision: PROCEED
```

**Overall Pre-Design Gate**: PASS ✓

---

## Architecture (CoD^Σ)

### Component Breakdown

**System Flow**:
```
Conversation → ScoreAnalyzer → MetricDeltas → ScoreCalculator → History
      ↓            ↓              ↓               ↓              ↓
  User+Nikita   LLM_eval      [-10,+10]      Composite    Audit_trail
                                                 ↓
                                          ThresholdEmitter
                                                 ↓
                                          BossEvent | GameOver
```

**Dependencies** (CoD^Σ Notation):
```
ScoreAnalyzer ⇐ Claude_API (external)
ScoreCalculator ⇐ UserMetricsRepository (existing)
ScoreCalculator ⇐ ScoreHistoryRepository (existing)
ThresholdEmitter → BossSystem (downstream, spec 004)
```

**Modules**:
1. **scoring/analyzer.py**: `nikita/engine/scoring/`
   - Purpose: LLM-based interaction analysis
   - Exports: ScoreAnalyzer, ResponseAnalysis
   - Imports: Pydantic AI, Claude client

2. **scoring/calculator.py**: `nikita/engine/scoring/`
   - Purpose: Delta application, composite calculation
   - Exports: ScoreCalculator
   - Imports: UserMetricsRepository, ScoreHistoryRepository, METRIC_WEIGHTS

3. **scoring/events.py**: `nikita/engine/scoring/`
   - Purpose: Threshold event emission
   - Exports: ThresholdEmitter, ScoreEvent
   - Imports: BOSS_THRESHOLDS

---

## User Story Implementation Plan

### User Story P1: Exchange Scoring (Priority: Must-Have)

**Goal**: Analyze each exchange and update metrics

**Acceptance Criteria** (from spec.md):
- AC-FR001-001: Given thoughtful message, Then positive deltas calculated
- AC-FR002-001: Given deltas, Then each within -10 to +10
- AC-FR003-001: Given metrics, Then composite uses 30/25/25/20 weights

**Implementation Approach**:
1. Create ScoreAnalyzer with LLM prompt
2. Create ResponseAnalysis Pydantic model
3. Integrate with ScoreCalculator

**Evidence**: Based on pattern at `metrics_repository.py:39` (update_metrics)

---

### User Story P1: Score History (Priority: Must-Have)

**Goal**: Log all score changes with context

**Acceptance Criteria** (from spec.md):
- AC-FR005-001: Given change, Then timestamp, before, after, deltas, source recorded
- AC-FR005-002: Given history query, Then complete history retrievable
- AC-FR005-003: Given context, Then excerpt stored

**Implementation Approach**:
1. Extend ScoreHistoryRepository.log_event() with deltas
2. Add conversation excerpt to event_details

**Evidence**: Based on pattern at `score_history_repository.py:28`

---

### User Story P1: Threshold Events (Priority: Must-Have)

**Goal**: Emit events at score milestones

**Acceptance Criteria** (from spec.md):
- AC-FR010-001: Given score 60%+ in Ch1, Then boss_threshold_reached emitted
- AC-FR010-002: Given score 0%, Then game_over emitted
- AC-FR010-003: Given events, Then boss system can react

**Implementation Approach**:
1. Create ThresholdEmitter class
2. Check thresholds after each score update
3. Return events from ScoreCalculator

**Evidence**: Based on `BOSS_THRESHOLDS` at `constants.py:25`

---

### User Story P2: Context-Aware Analysis (Priority: Important)

**Goal**: Same message, different context → different scoring

**Acceptance Criteria** (from spec.md):
- AC-FR006-001: Given Ch1 user, Then more positive for personal questions
- AC-FR006-002: Given recent conflict, Then apology has higher impact
- AC-FR006-003: Given context, Then reasoning reflects it

**Implementation Approach**:
1. Add chapter context to analysis prompt
2. Include recent conversation summary
3. Add relationship state

---

### User Story P2: Analysis Explanation (Priority: Important)

**Goal**: Provide reasoning for score changes

**Acceptance Criteria** (from spec.md):
- AC-FR007-001: Given change, Then explanation included
- AC-FR007-002: Given explanation, Then specific behaviors identified

**Implementation Approach**:
1. Add explanation field to ResponseAnalysis
2. Store explanation in score_history.event_details

---

### User Story P3: Voice Call Batch Analysis (Priority: Nice-to-Have)

**Goal**: Analyze multi-turn voice transcripts as single unit

**Acceptance Criteria** (from spec.md):
- AC-FR008-001: Given 20-turn transcript, Then single aggregate calculated
- AC-FR008-002: Given batch, Then completes within 10 seconds

**Implementation Approach**:
1. Add batch_analyze method to ScoreAnalyzer
2. Aggregate deltas across turns

---

## Tasks

### Task 1: [US1] Create ResponseAnalysis Pydantic Model
- **ID:** T1
- **User Story**: P1 - Exchange Scoring
- **Owner:** executor-agent
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): None
- **Estimated Complexity:** Low

**Acceptance Criteria**:
- [ ] AC-T1.1: ResponseAnalysis has intimacy_delta, passion_delta, trust_delta, secureness_delta fields
- [ ] AC-T1.2: All delta fields are Decimal with range validation (-10 to +10)
- [ ] AC-T1.3: Model includes optional explanation field
- [ ] AC-T1.4: Model includes behaviors_identified list

**Implementation Notes:**
- **Pattern Evidence**: Based on Pydantic patterns in `nikita/api/schemas/`
- **File**: `nikita/engine/scoring/models.py`

---

### Task 2: [US1] Create ScoreAnalyzer Class
- **ID:** T2
- **User Story**: P1 - Exchange Scoring
- **Owner:** executor-agent
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T1 → T2
- **Estimated Complexity:** High

**Acceptance Criteria**:
- [ ] AC-T2.1: `analyze()` method accepts user_message, nikita_response, context
- [ ] AC-T2.2: Uses Claude via Pydantic AI to generate ResponseAnalysis
- [ ] AC-T2.3: Prompt includes chapter-specific behavior expectations
- [ ] AC-T2.4: Temperature=0 for consistent analysis
- [ ] AC-T2.5: Returns ResponseAnalysis with all fields populated

**Implementation Notes:**
- **Pattern Evidence**: Based on text agent at `nikita/agents/text/agent.py`
- **File**: `nikita/engine/scoring/analyzer.py`

---

### Task 3: [US1] Create ScoreCalculator Class
- **ID:** T3
- **User Story**: P1 - Exchange Scoring
- **Owner:** executor-agent
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T1 → T3
- **Estimated Complexity:** Medium

**Acceptance Criteria**:
- [ ] AC-T3.1: `apply_deltas()` uses UserMetricsRepository.update_metrics()
- [ ] AC-T3.2: Calculates composite using METRIC_WEIGHTS (30/25/25/20)
- [ ] AC-T3.3: Updates User.relationship_score with new composite
- [ ] AC-T3.4: Returns score_before, score_after, events
- [ ] AC-T3.5: Enforces metric bounds (0-100) and delta bounds (-10 to +10)

**Implementation Notes:**
- **Pattern Evidence**: Based on `metrics_repository.py:39` and `constants.py:51`
- **File**: `nikita/engine/scoring/calculator.py`

---

### Task 4: [US1] Create ThresholdEmitter Class
- **ID:** T4
- **User Story**: P1 - Threshold Events
- **Owner:** executor-agent
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T3 ⊥ T4 (can be parallel)
- **Estimated Complexity:** Medium

**Acceptance Criteria**:
- [ ] AC-T4.1: Checks BOSS_THRESHOLDS (60, 65, 70, 75, 80) per chapter
- [ ] AC-T4.2: Emits boss_threshold_reached when score crosses threshold
- [ ] AC-T4.3: Emits critical_low when score drops below 20%
- [ ] AC-T4.4: Emits game_over when score reaches 0%
- [ ] AC-T4.5: Emits recovery when score rises above 20% from below

**Implementation Notes:**
- **Pattern Evidence**: Based on `constants.py:25` (BOSS_THRESHOLDS)
- **File**: `nikita/engine/scoring/events.py`

---

### Task 5: [US1] Integrate Scoring with History Logging
- **ID:** T5
- **User Story**: P1 - Score History
- **Owner:** executor-agent
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T3 → T5, T2 → T5
- **Estimated Complexity:** Low

**Acceptance Criteria**:
- [ ] AC-T5.1: ScoreCalculator logs to ScoreHistoryRepository after updates
- [ ] AC-T5.2: event_details includes all 4 metric deltas
- [ ] AC-T5.3: event_details includes conversation excerpt (first 200 chars)
- [ ] AC-T5.4: event_details includes explanation from ResponseAnalysis

**Implementation Notes:**
- **Pattern Evidence**: Based on `score_history_repository.py:28`
- **File**: `nikita/engine/scoring/calculator.py` (extend)

---

### Task 6: [US2] Add Context-Aware Analysis
- **ID:** T6
- **User Story**: P2 - Context-Aware Analysis
- **Owner:** executor-agent
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T2 → T6
- **Estimated Complexity:** Medium

**Acceptance Criteria**:
- [ ] AC-T6.1: ConversationContext model includes chapter, recent_history, relationship_state
- [ ] AC-T6.2: Analysis prompt includes CHAPTER_BEHAVIORS for current chapter
- [ ] AC-T6.3: Same message with different chapters produces different deltas
- [ ] AC-T6.4: Conflict/makeup context affects scoring appropriately

**Implementation Notes:**
- **Pattern Evidence**: Based on `constants.py:60` (CHAPTER_BEHAVIORS)
- **File**: `nikita/engine/scoring/analyzer.py` (extend)

---

### Task 7: [US3] Add Batch Analysis for Voice
- **ID:** T7
- **User Story**: P3 - Voice Call Batch Analysis
- **Owner:** executor-agent
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T6 → T7
- **Estimated Complexity:** Medium

**Acceptance Criteria**:
- [ ] AC-T7.1: `batch_analyze()` accepts list of (user_msg, nikita_msg) tuples
- [ ] AC-T7.2: Produces single aggregated ResponseAnalysis
- [ ] AC-T7.3: Aggregate deltas capped at reasonable maximums (+/-30)
- [ ] AC-T7.4: Completes 20-turn analysis within 10 seconds

**Implementation Notes:**
- **File**: `nikita/engine/scoring/analyzer.py` (extend)

---

### Task 8: [US1] Create Unit Tests for Scoring Engine
- **ID:** T8
- **User Story**: P1 - Exchange Scoring
- **Owner:** executor-agent
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T1 ∧ T2 ∧ T3 ∧ T4 ∧ T5 → T8
- **Estimated Complexity:** Medium

**Acceptance Criteria**:
- [ ] AC-T8.1: Test ResponseAnalysis validation (delta bounds)
- [ ] AC-T8.2: Test ScoreCalculator composite calculation
- [ ] AC-T8.3: Test ThresholdEmitter event generation
- [ ] AC-T8.4: Test score history logging
- [ ] AC-T8.5: 80%+ code coverage for scoring module

**Implementation Notes:**
- **File**: `tests/engine/scoring/`

---

## Dependencies

### Task Dependency Graph (CoD^Σ)
```
T1 (models) → T2 (analyzer)
    ↘ T3 (calculator) → T5 (history integration)
T4 (events) ∥ T3             ↘
                              T8 (tests)
T6 (context) → T7 (batch)   ↗
```

**Critical Path**: T1 → T2 → T6 → T7 (analysis complexity)
**Parallelizable**: {T3, T4} ⊥ T2 (can run after T1)

### External Dependencies
- **Library**: pydantic-ai (already installed)
- **API**: Claude Sonnet (ANTHROPIC_API_KEY required)
- **Database**: Supabase (existing repositories)

### File Dependencies
```
constants.py → calculator.py (METRIC_WEIGHTS, BOSS_THRESHOLDS)
metrics_repository.py → calculator.py (update_metrics)
score_history_repository.py → calculator.py (log_event)
```

---

## Risks (CoD^Σ)

### Risk 1: Analysis Inconsistency
- **Likelihood (p):** Medium (0.5)
- **Impact:** Medium (5)
- **Risk Score:** r = 2.5
- **Mitigation**:
  - Temperature=0 for deterministic output
  - Detailed prompts with specific criteria
  - Caching for identical inputs

### Risk 2: Gaming/Farming Detection
- **Likelihood (p):** Medium (0.5)
- **Impact:** High (8)
- **Risk Score:** r = 4.0
- **Mitigation**:
  - Context-aware analysis
  - Pattern detection for repeated phrases
  - Diminishing returns for similar messages

---

## Verification (CoD^Σ)

### Test Strategy
```
Unit → Integration → Manual
  ↓         ↓          ↓
Fast     Medium      Slow
```

- **Unit Tests**: `tests/engine/scoring/test_analyzer.py`, `test_calculator.py`
- **Integration Tests**: Full scoring flow with mock LLM
- **Manual Tests**: Real conversations with expected outcomes

### AC Coverage Map
```
AC-FR001-001 → test_analyzer.py:test_positive_deltas ✓
AC-FR002-001 → test_models.py:test_delta_bounds ✓
AC-FR003-001 → test_calculator.py:test_composite_weights ✓
AC-FR005-001 → test_calculator.py:test_history_logging ✓
AC-FR010-001 → test_events.py:test_boss_threshold ✓
```

---

## Files Created/Modified

| File | Action | Purpose |
|------|--------|---------|
| `nikita/engine/scoring/__init__.py` | Create | Package init |
| `nikita/engine/scoring/models.py` | Create | ResponseAnalysis, ConversationContext |
| `nikita/engine/scoring/analyzer.py` | Create | ScoreAnalyzer class |
| `nikita/engine/scoring/calculator.py` | Create | ScoreCalculator class |
| `nikita/engine/scoring/events.py` | Create | ThresholdEmitter class |
| `tests/engine/scoring/` | Create | Unit tests |

---

## Progress Tracking

**Total Tasks (N):** 8
**Completed (X):** 0
**In Progress (Y):** 0
**Blocked (Z):** 0

**Progress Ratio:** 0/8 = 0%

---

## Notes

**Constitutional Compliance**:
- §III.1: Fixed 30/25/25/20 weights enforced in ScoreCalculator
- §III.2: Score bounds 0-100 enforced via _clamp()
- §III.3: Delta bounds -10 to +10 enforced in ResponseAnalysis validation
