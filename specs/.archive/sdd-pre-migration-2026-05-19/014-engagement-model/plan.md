# 014 - Engagement Model Implementation Plan

**Generated**: 2025-12-02
**Spec Version**: 1.0
**Estimated Effort**: 8-12 hours

---

## Executive Summary

Implement the calibration-based engagement model that tracks player behavior and applies scoring multipliers. This is the core game mechanic that makes Nikita challenging: finding and maintaining the "sweet spot" of engagement.

**Key Innovation**: Unlike traditional relationship games where more = better, this system penalizes BOTH over-engagement (clingy) and under-engagement (distant).

---

## User Stories

### US-1: Engagement State Machine (P1)

**As a** game engine
**I want** to track player engagement state
**So that** I can apply appropriate scoring multipliers

**Acceptance Criteria**:
- AC-1.1: 6 states implemented (CALIBRATING, IN_ZONE, DRIFTING, CLINGY, DISTANT, OUT_OF_ZONE)
- AC-1.2: State transitions follow spec rules
- AC-1.3: Multipliers applied correctly (1.0, 0.9, 0.8, 0.6, 0.5, 0.2)
- AC-1.4: State persisted to database between sessions

### US-2: Calibration Score Computation (P1)

**As a** game engine
**I want** to compute calibration scores from player behavior
**So that** I can determine their engagement state

**Acceptance Criteria**:
- AC-2.1: Frequency component calculated (40% weight)
- AC-2.2: Timing component calculated (30% weight)
- AC-2.3: Content component calculated (30% weight)
- AC-2.4: Score ranges map to states correctly (0.8+ = IN_ZONE, etc.)

### US-3: Clinginess Detection (P1)

**As a** game engine
**I want** to detect clingy behavior patterns
**So that** I can warn and penalize over-engagement

**Acceptance Criteria**:
- AC-3.1: Message frequency signal detected
- AC-3.2: Double/triple texting detected
- AC-3.3: Fast response times flagged
- AC-3.4: Long message ratio tracked
- AC-3.5: Needy language patterns detected (LLM)
- AC-3.6: Composite clinginess score computed

### US-4: Neglect Detection (P1)

**As a** game engine
**I want** to detect neglect behavior patterns
**So that** I can warn and penalize under-engagement

**Acceptance Criteria**:
- AC-4.1: Message frequency signal detected
- AC-4.2: Slow response times flagged
- AC-4.3: Short messages tracked
- AC-4.4: Abrupt conversation endings detected
- AC-4.5: Distracted language detected (LLM)
- AC-4.6: Composite neglect score computed

### US-5: Recovery Mechanics (P2)

**As a** player
**I want** to recover from bad states
**So that** I can continue playing without instant game over

**Acceptance Criteria**:
- AC-5.1: Recovery actions defined per state
- AC-5.2: Grace periods enforced before reset
- AC-5.3: Point of no return triggers (7 clingy / 10 distant days)
- AC-5.4: Recovery resets to CALIBRATING state

### US-6: Chapter Transitions (P2)

**As a** game engine
**I want** engagement to reset on chapter change
**So that** players recalibrate to new chapter parameters

**Acceptance Criteria**:
- AC-6.1: New chapter triggers CALIBRATING state
- AC-6.2: Tolerance bands update per chapter
- AC-6.3: Optimal frequency updates per chapter
- AC-6.4: Historical engagement data preserved

---

## Technical Architecture

### Module Structure

```
nikita/engine/engagement/
├── __init__.py           # Exports EngagementEngine
├── state_machine.py      # EngagementStateMachine class
├── calculator.py         # CalibrationCalculator class
├── detection.py          # ClinginessDetector, NeglectDetector
├── recovery.py           # RecoveryManager class
└── models.py             # EngagementState enum, result models
```

### Data Flow

```
Player Message
       │
       ▼
┌─────────────────────────────────────────┐
│ 1. Compute message metrics              │
│    - frequency, timing, length          │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ 2. Run detection algorithms             │
│    - ClinginessDetector                 │
│    - NeglectDetector                    │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ 3. Compute calibration score            │
│    - frequency_component × 0.4          │
│    - timing_component × 0.3             │
│    - content_component × 0.3            │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ 4. Evaluate state transitions           │
│    - Check transition conditions        │
│    - Apply new state if triggered       │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ 5. Return multiplier for scoring        │
│    - IN_ZONE: 1.0                       │
│    - DRIFTING: 0.8                      │
│    - CLINGY: 0.5, DISTANT: 0.6          │
│    - OUT_OF_ZONE: 0.2                   │
└─────────────────────────────────────────┘
```

### Database Schema

```sql
-- Engagement tracking table
CREATE TABLE engagement_state (
    user_id UUID PRIMARY KEY REFERENCES users(id),
    current_state engagement_state_enum NOT NULL DEFAULT 'calibrating',
    state_started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    consecutive_state_days INT NOT NULL DEFAULT 0,
    calibration_score DECIMAL(4,3),
    clinginess_score DECIMAL(4,3),
    neglect_score DECIMAL(4,3),
    multiplier DECIMAL(3,2) NOT NULL DEFAULT 0.9,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Engagement history for analytics
CREATE TABLE engagement_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    from_state engagement_state_enum NOT NULL,
    to_state engagement_state_enum NOT NULL,
    trigger_reason TEXT,
    calibration_score DECIMAL(4,3),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Daily engagement metrics
CREATE TABLE engagement_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    date DATE NOT NULL,
    message_count INT NOT NULL DEFAULT 0,
    avg_response_time_seconds INT,
    double_text_count INT NOT NULL DEFAULT 0,
    avg_message_length INT,
    UNIQUE(user_id, date)
);
```

---

## Implementation Tasks

### Phase 1: Core Models (2 hours)

#### T1.1: Create Engagement Module Structure
- Create `nikita/engine/engagement/` directory
- Create `__init__.py` with exports
- Create `models.py` with enums and result models

#### T1.2: Implement EngagementState Enum
- 6 states: CALIBRATING, IN_ZONE, DRIFTING, CLINGY, DISTANT, OUT_OF_ZONE
- Add state metadata (multiplier, description)

#### T1.3: Create Database Models
- EngagementState SQLAlchemy model
- EngagementHistory model
- EngagementMetrics model

#### T1.4: Create Database Migration
- Add engagement tables via Supabase migration
- Add engagement_state_enum type
- Add indexes for user_id lookups

### Phase 2: Detection Algorithms (3 hours)

#### T2.1: Implement ClinginessDetector
- Message frequency signal
- Double texting detection
- Response time analysis
- Message length ratio
- Composite score computation

#### T2.2: Implement NeglectDetector
- Message frequency (under threshold)
- Slow response times
- Short message detection
- Abrupt ending detection
- Composite score computation

#### T2.3: Implement LLM Analysis
- Needy language detection prompt
- Distracted language detection prompt
- Integration with Pydantic AI agent

### Phase 3: Calibration Calculator (2 hours)

#### T3.1: Implement OptimalFrequency Calculator
- Base optimal per chapter (15/12/10/8/6)
- Day-of-week modifiers
- Tolerance band calculation

#### T3.2: Implement CalibrationScore Calculator
- Frequency component (40%)
- Timing component (30%)
- Content component (30%)
- Score normalization

#### T3.3: Implement State Mapping
- Score ranges to states
- Consecutive exchange tracking
- Threshold configuration

### Phase 4: State Machine (2 hours)

#### T4.1: Implement EngagementStateMachine
- Current state tracking
- Transition rule evaluation
- State change notifications

#### T4.2: Implement Transition Rules
- All transition conditions from spec
- Transition action handlers
- State persistence

#### T4.3: Implement Chapter Reset
- New chapter detection
- Reset to CALIBRATING
- Preserve history

### Phase 5: Recovery System (1.5 hours)

#### T5.1: Implement RecoveryManager
- Recovery action handlers
- Grace period enforcement
- Point of no return detection

#### T5.2: Implement Game Over Triggers
- 7 consecutive clingy days
- 10 consecutive distant days
- Game over state transition

### Phase 6: Testing (2 hours)

#### T6.1: Unit Tests for Detectors
- Test clinginess signals
- Test neglect signals
- Test composite scores

#### T6.2: Unit Tests for Calculator
- Test optimal frequency
- Test calibration score
- Test state mapping

#### T6.3: Unit Tests for State Machine
- Test all transitions
- Test edge cases
- Test persistence

#### T6.4: Integration Tests
- Full flow from message to multiplier
- Chapter transition handling
- Recovery flow

---

## Dependencies

### External
- pydantic (result models)
- sqlalchemy (database models)
- anthropic (LLM analysis)

### Internal
- 009-database-infrastructure (tables)
- 013-configuration-system (engagement.yaml)

### Blocked By
- 009-database-infrastructure ✅ COMPLETE
- 013-configuration-system (engagement.yaml values)

### Blocks
- 012-context-engineering (multiplier injection)
- 003-scoring-engine (multiplier application)

---

## Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| LLM analysis latency | Medium | Medium | Cache results per session |
| State corruption | High | Low | Transaction-safe updates |
| Threshold tuning | Medium | High | Use config system for easy adjustment |
| Edge case bugs | Medium | Medium | Comprehensive state machine tests |

---

## Success Metrics

- [ ] 6 engagement states implemented
- [ ] All transition rules from spec implemented
- [ ] Clinginess detector with 5 signals
- [ ] Neglect detector with 5 signals
- [ ] Calibration score computed correctly
- [ ] Multipliers applied per state
- [ ] Recovery mechanics working
- [ ] Chapter transitions reset state
- [ ] 90%+ test coverage

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-02 | Claude | Initial plan |
