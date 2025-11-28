---
feature: 005-decay-system
created: 2025-11-28
status: Draft
priority: P1
technology_agnostic: true
constitutional_compliance:
  article_iv: specification_first
---

# Feature Specification: Decay System

**IMPORTANT**: This specification is TECHNOLOGY-AGNOSTIC. Focus on WHAT and WHY, not HOW.

---

## Summary

The Decay System enforces the "use it or lose it" core mechanic by reducing relationship scores when users don't interact. It implements chapter-specific decay rates, grace periods before decay begins, and scheduled decay application—creating real stakes for inactivity.

**Problem Statement**: Without consequences for absence, users have no urgency to return. The relationship should feel alive—neglect it and it withers.

**Value Proposition**: Users feel genuine stakes from inactivity. Missing days damages the relationship, creating urgency to maintain engagement. The grace periods prevent punishing normal life patterns while decay rates ensure prolonged absence has real consequences.

### CoD^Σ Overview

**System Model**:
```
Last_interaction → Grace_check → Decay_calculation → Score_reduction → Event_emission
        ↓              ↓               ↓                   ↓                ↓
   Timestamp      Chapter_grace    Chapter_rate      Composite-=Δ     Threshold_check

Grace := {1: 24h, 2: 36h, 3: 48h, 4: 72h, 5: 96h}
Decay := {1: -5%/day, 2: -4%/day, 3: -3%/day, 4: -2%/day, 5: -1%/day}
```

---

## Functional Requirements

### FR-001: Grace Period Enforcement
System MUST NOT apply decay until grace period expires:
- Chapter 1: 24 hours of no interaction
- Chapter 2: 36 hours of no interaction
- Chapter 3: 48 hours of no interaction
- Chapter 4: 72 hours of no interaction
- Chapter 5: 96 hours of no interaction

**Rationale**: Grace periods prevent punishing normal life patterns (sleep, work, weekends)
**Priority**: Must Have

### FR-002: Chapter-Specific Decay Rates
System MUST apply decay at chapter-appropriate rates:
- Chapter 1: -5% per day (high stakes, new relationship fragile)
- Chapter 2: -4% per day
- Chapter 3: -3% per day
- Chapter 4: -2% per day
- Chapter 5: -1% per day (established relationship more resilient)

**Rationale**: Decay intensity mirrors relationship fragility—new relationships need more attention
**Priority**: Must Have

### FR-003: Decay Calculation
System MUST calculate decay based on time elapsed beyond grace period:
- Calculate: days_overdue = (now - last_interaction - grace_period) / 24 hours
- Apply: decay_amount = days_overdue × chapter_decay_rate
- Cap: Maximum decay per calculation cycle (prevent catastrophic catch-up)

**Rationale**: Proportional decay ensures fair punishment scaling with absence duration
**Priority**: Must Have

### FR-004: Scheduled Decay Application
System MUST apply decay on a regular schedule:
- Check all active users periodically (configurable interval)
- Apply decay only if grace period exceeded
- Process users in batches to manage load
- Log all decay applications with timestamps

**Rationale**: Scheduled checks ensure consistent decay regardless of user activity timing
**Priority**: Must Have

### FR-005: Decay Floor Protection
System MUST enforce minimum score during decay:
- Decay cannot reduce score below 0%
- Decay triggers game_over event at 0% (does not go negative)
- Score floors at each percentage point (no fractional display)

**Rationale**: Clear floor prevents confusion and triggers appropriate game-over
**Priority**: Must Have

### FR-006: Interaction Reset
System MUST reset grace period on any qualifying interaction:
- Text message sent to Nikita
- Voice call completed (minimum duration)
- Portal engagement does NOT count
- Reset timestamp to now

**Rationale**: Only genuine engagement should reset decay, not passive viewing
**Priority**: Must Have

### FR-007: Decay Event Emission
System MUST emit events for decay milestones:
- Decay applied (with amount and new score)
- Approaching critical (score < 20%)
- Game over triggered (score = 0%)
- Grace period warning (optional: X hours until decay starts)

**Rationale**: Events enable notifications, logging, and other system reactions
**Priority**: Must Have

### FR-008: Decay History Logging
System MUST log all decay applications:
- Timestamp of decay
- Score before and after
- Decay amount applied
- Days overdue at time of decay
- Chapter at time of decay

**Rationale**: Audit trail for debugging and user transparency if exposed
**Priority**: Must Have

### FR-009: Boss Fight Decay Pause
System MUST pause decay during active boss encounters:
- If game_status = "boss_fight", no decay applies
- Grace period does NOT reset until boss resolved
- After boss (pass or fail), decay resumes with updated grace

**Rationale**: Boss encounters shouldn't be time-pressured by external decay
**Priority**: Must Have

### FR-010: Post-Victory Decay Handling
System MUST handle decay differently after victory:
- If game_status = "won", decay DISABLED
- Post-game mode has no stakes
- User can re-enable stakes optionally (future feature)

**Rationale**: Victory is the reward—no more punishment in post-game
**Priority**: Should Have

---

## Non-Functional Requirements

### Performance
- Decay calculation: < 100ms per user
- Batch processing: Handle 10,000 users in < 5 minutes
- Schedule reliability: No missed decay cycles

### Reliability
- Exactly-once decay: No duplicate applications
- Crash recovery: Resume from last checkpoint
- Atomic updates: Score changes transactional

### Scalability
- Horizontal scaling: Multiple workers process batches
- Database efficiency: Indexed queries on last_interaction_at
- Configurable intervals: Adjust check frequency as user base grows

---

## User Stories (CoD^Σ)

### US-1: Grace Period Protection (Priority: P1 - Must-Have)
```
User goes silent → grace period protects → no decay yet
```
**Acceptance Criteria**:
- **AC-FR001-001**: Given Ch1 user, When inactive for 20 hours, Then NO decay applied
- **AC-FR001-002**: Given Ch1 user, When inactive for 25 hours, Then decay IS applied
- **AC-FR001-003**: Given Ch5 user, When inactive for 90 hours, Then NO decay applied (96h grace)

**Independent Test**: Create user, wait X hours, verify decay only after grace
**Dependencies**: User model with last_interaction_at

---

### US-2: Decay Application (Priority: P1 - Must-Have)
```
Grace expires → decay calculated → score reduced
```
**Acceptance Criteria**:
- **AC-FR002-001**: Given Ch1 user past grace, When 24h overdue, Then -5% decay applied
- **AC-FR003-001**: Given Ch1 user past grace, When 48h overdue, Then -10% decay applied (2 days × 5%)
- **AC-FR003-002**: Given decay applied, When calculated, Then capped at maximum per cycle

**Independent Test**: Set user overdue, run decay, verify correct amount
**Dependencies**: US-1

---

### US-3: Interaction Reset (Priority: P1 - Must-Have)
```
User messages Nikita → grace period resets → decay paused
```
**Acceptance Criteria**:
- **AC-FR006-001**: Given decaying user, When they send message, Then last_interaction_at updated
- **AC-FR006-002**: Given reset interaction, When next decay check, Then grace period restarted
- **AC-FR006-003**: Given portal-only activity, When decay check, Then NO reset (portal doesn't count)

**Independent Test**: Set user overdue, send message, verify grace reset
**Dependencies**: US-1, US-2

---

### US-4: Decay Game Over (Priority: P1 - Must-Have)
```
Score decays to 0% → game over triggered → relationship ended
```
**Acceptance Criteria**:
- **AC-FR005-001**: Given user at 3%, When -5% decay applies, Then score floors at 0%
- **AC-FR007-001**: Given score reaches 0% via decay, When processed, Then game_over event emitted
- **AC-FR008-001**: Given decay-caused game over, When logged, Then reason = "decay"

**Independent Test**: Set user low score, apply decay to zero, verify game over
**Dependencies**: US-2, Chapter-Boss-System (004)

---

### US-5: Scheduled Processing (Priority: P1 - Must-Have)
```
Scheduler runs → all overdue users processed → decay applied fairly
```
**Acceptance Criteria**:
- **AC-FR004-001**: Given scheduler configured for hourly, When hour passes, Then all users checked
- **AC-FR004-002**: Given 1000 overdue users, When batch processed, Then all receive correct decay
- **AC-FR004-003**: Given scheduler crash, When restarted, Then resumes without duplication

**Independent Test**: Set up multiple users, run scheduler, verify all processed
**Dependencies**: US-1 through US-4

---

### US-6: Boss Fight Pause (Priority: P2 - Important)
```
User in boss fight → decay paused → focus on challenge
```
**Acceptance Criteria**:
- **AC-FR009-001**: Given user in boss_fight status, When decay check runs, Then NO decay applied
- **AC-FR009-002**: Given boss completed, When decay resumes, Then grace period starts fresh
- **AC-FR009-003**: Given long boss attempt, When eventually resolved, Then decay does not "catch up"

**Independent Test**: Put user in boss fight, run decay, verify skipped
**Dependencies**: US-5, Chapter-Boss-System (004)

---

## Intelligence Evidence

### Findings
- nikita/engine/constants.py:33-40 - DECAY_RATES: {1:5.0, 2:4.0, 3:3.0, 4:2.0, 5:1.0}
- nikita/engine/constants.py:43-49 - GRACE_PERIODS: {1:24h, 2:36h, 3:48h, 4:72h, 5:96h}
- nikita/engine/constants.py:142-147 - GAME_STATUSES: active, boss_fight, game_over, won

### Assumptions
- ASSUMPTION: Scheduler infrastructure available (Celery or similar)
- ASSUMPTION: User model has last_interaction_at timestamp
- ASSUMPTION: Score updates atomic via database transactions

---

## Scope

### In-Scope
- Grace period checking and enforcement
- Chapter-specific decay rate application
- Scheduled decay processing for all users
- Decay history logging
- Boss fight decay pause
- Game over via decay

### Out-of-Scope
- Notification to user about impending decay (008-player-portal)
- Recovery mechanics or "makeup" conversations (enhancement)
- Premium features to reduce decay (monetization)

---

## Infrastructure Dependencies

This feature depends on the following infrastructure specs:

| Spec | Dependency | Usage |
|------|------------|-------|
| 009-database-infrastructure | Batch score updates | UserRepository.apply_decay() for all inactive users |
| 011-background-tasks | Scheduled decay job | pg_cron job 'apply-daily-decay' at 00:00 UTC |

**Database Tables Used**:
- `users` (relationship_score, last_interaction_at, chapter, game_status)
- `score_history` (event_type='decay' logging)

**No API Endpoints** - Decay is background-only

**Background Tasks Required**:
- `apply-daily-decay` pg_cron job (FR-001 in 011-background-tasks)

---

## Risks & Mitigations

### Risk 1: Runaway Decay (Catch-up)
**Description**: User returns after 30 days, loses everything instantly
**Likelihood**: Medium (0.5) | **Impact**: High (8) | **Score**: 4.0
**Mitigation**: Cap maximum decay per cycle (e.g., max -20% per check)

### Risk 2: Scheduler Failures
**Description**: Scheduler crashes, decay stops applying
**Likelihood**: Low (0.2) | **Impact**: Medium (5) | **Score**: 1.0
**Mitigation**: Health monitoring, redundant scheduling, manual triggers

### Risk 3: Race Conditions
**Description**: User interacts exactly as decay runs
**Likelihood**: Low (0.2) | **Impact**: Low (3) | **Score**: 0.6
**Mitigation**: Atomic transactions, check timestamp within transaction

---

## Success Metrics

- Decay enforcement accuracy: 100% of overdue users processed
- Grace period compliance: 0 decay applied within grace window
- Return rate after decay: Users who receive decay and return within 24h
- Game over via decay: 10-20% of all game overs (not majority)

---

**Version**: 1.0
**Last Updated**: 2025-11-28
