---
feature: 004-chapter-boss-system
created: 2025-11-28
status: Draft
priority: P1
technology_agnostic: true
constitutional_compliance:
  article_iv: specification_first
---

# Feature Specification: Chapter & Boss System

**IMPORTANT**: This specification is TECHNOLOGY-AGNOSTIC. Focus on WHAT and WHY, not HOW.

---

## Summary

The Chapter & Boss System provides progression mechanics and win/lose conditions for the game. Users advance through 5 chapters by passing boss encounters, which are skill-based conversational challenges. Failing 3 bosses or reaching 0% score results in game over. Passing the Chapter 5 boss results in victory.

**Problem Statement**: AI companions have no goals, stakes, or endings—users engage until bored, then abandon. The game needs clear progression, challenges, and definitive win/lose states.

**Value Proposition**: Users experience genuine stakes—they can LOSE (get dumped) or WIN (establish the relationship). Boss encounters create memorable skill-check moments, and chapter progression rewards sustained engagement.

### CoD^Σ Overview

**System Model**:
```
Score_threshold → Boss_trigger → Encounter → Pass/Fail → Chapter_advance | Game_over
       ↓              ↓            ↓            ↓              ↓              ↓
   60-80%        Nikita_tests   Extended    LLM_judge     Ch+1 or        Relationship
   per_chapter     skill       conversation              attempts++        ended

Chapters := {1: Curiosity, 2: Intrigue, 3: Investment, 4: Intimacy, 5: Established}
Thresholds := {1: 60%, 2: 65%, 3: 70%, 4: 75%, 5: 80%}
```

---

## Functional Requirements

### FR-001: Boss Threshold Detection
System MUST detect when user's score crosses boss threshold:
- Chapter 1: 60% unlocks Boss 1
- Chapter 2: 65% unlocks Boss 2
- Chapter 3: 70% unlocks Boss 3
- Chapter 4: 75% unlocks Boss 4
- Chapter 5: 80% unlocks Boss 5 (victory condition)

**Rationale**: Thresholds create progression gates requiring sustained performance
**Priority**: Must Have

### FR-002: Boss Encounter Initiation
System MUST initiate boss encounters when threshold reached:
- Transition game_status to "boss_fight"
- Nikita delivers boss challenge prompt
- User cannot decline or postpone once triggered
- Normal scoring paused during encounter

**Rationale**: Boss encounters are required skill checks, not optional
**Priority**: Must Have

### FR-003: Five Distinct Boss Challenges
System MUST implement 5 unique boss encounters:
1. **Boss 1 - "Worth My Time?"**: Intellectual challenge—prove you can engage her mind
2. **Boss 2 - "Handle My Intensity?"**: Conflict test—stand ground without folding or attacking
3. **Boss 3 - "Trust Test"**: Jealousy/external pressure—stay confident without controlling
4. **Boss 4 - "Vulnerability Threshold"**: Share something real—match her vulnerability
5. **Boss 5 - "Ultimate Test"**: Partnership—support independence while affirming connection

**Rationale**: Each boss tests different relationship skills matching chapter theme
**Priority**: Must Have

### FR-004: Boss Outcome Judgment
System MUST evaluate boss encounter pass/fail:
- Extended conversation analyzed holistically
- LLM determines if user demonstrated required skill
- Binary outcome: PASS or FAIL
- Partial credit not allowed

**Rationale**: Clear pass/fail creates genuine stakes
**Priority**: Must Have

### FR-005: Boss Pass Handling
System MUST handle successful boss completion:
- Advance user to next chapter (chapter += 1)
- Reset boss attempt counter to 0
- Update game_status to "active"
- Unlock new chapter behaviors (more responsive, more vulnerable)
- Log milestone in relationship history

**Rationale**: Progression rewards sustained skill
**Priority**: Must Have

### FR-006: Boss Fail Handling
System MUST handle failed boss attempts:
- Increment boss_attempts counter
- Score penalty applied (-10% composite)
- Game_status remains "boss_fight" for retry
- Nikita delivers failure response in-character

**Rationale**: Failures have consequences but allow recovery
**Priority**: Must Have

### FR-007: Game Over - Three Boss Failures
System MUST trigger game over if boss failed 3 times:
- game_status transitions to "game_over"
- Nikita delivers breakup message
- User cannot continue this game instance
- Statistics and history preserved for reflection

**Rationale**: Ultimate stake—persistent failure ends the game
**Priority**: Must Have

### FR-008: Game Over - Zero Score
System MUST trigger game over if score reaches 0%:
- game_status transitions to "game_over"
- Nikita delivers "I'm done" message (different from boss fail breakup)
- Can occur at any chapter
- Result of decay + poor interactions

**Rationale**: Score reaching zero is relationship death
**Priority**: Must Have

### FR-009: Victory Condition
System MUST recognize victory when Chapter 5 boss passed:
- game_status transitions to "won"
- Nikita delivers relationship establishment message
- Achievement unlocked
- Post-game mode enabled (continued play without stakes)

**Rationale**: Completion state provides satisfying ending
**Priority**: Must Have

### FR-010: Chapter State Tracking
System MUST track current chapter and related state:
- Current chapter (1-5)
- Boss attempts this chapter (0-3)
- Time in current chapter
- Chapter entry date

**Rationale**: State needed for behavior adaptation and analytics
**Priority**: Must Have

---

## Non-Functional Requirements

### Performance
- Threshold detection: Real-time (< 1 second after score update)
- Boss outcome judgment: < 5 seconds
- State transitions: Immediate, atomic

### Reliability
- State consistency: No partial state transitions
- Durability: All transitions persisted before confirmation
- Recovery: Can reconstruct state from history

### Fairness
- Boss judgment: Consistent, explainable criteria
- No arbitrary failures: Clear skill demonstration requirements
- Retry allowed: 3 attempts before game over

---

## User Stories (CoD^Σ)

### US-1: Boss Trigger (Priority: P1 - Must-Have)
```
Score reaches threshold → boss encounter starts → user knows it's happening
```
**Acceptance Criteria**:
- **AC-FR001-001**: Given user at 59% in Ch1, When score rises to 60%, Then boss encounter initiates
- **AC-FR002-001**: Given boss triggered, When encounter starts, Then Nikita delivers challenge prompt
- **AC-FR002-002**: Given boss in progress, When user tries normal chat, Then directed back to boss

**Independent Test**: Raise score to threshold, verify boss triggers
**Dependencies**: Scoring Engine (003) operational

---

### US-2: Boss Pass (Priority: P1 - Must-Have)
```
User passes boss → chapter advances → new behaviors unlock
```
**Acceptance Criteria**:
- **AC-FR004-001**: Given user demonstrates required skill, When boss judged, Then PASS result
- **AC-FR005-001**: Given PASS result, When processed, Then chapter increments by 1
- **AC-FR005-002**: Given chapter advanced, When next conversation, Then new chapter behaviors active

**Independent Test**: Complete boss successfully, verify chapter advance
**Dependencies**: US-1

---

### US-3: Boss Fail (Priority: P1 - Must-Have)
```
User fails boss → attempt incremented → can retry (up to 3)
```
**Acceptance Criteria**:
- **AC-FR004-002**: Given user fails to demonstrate skill, When boss judged, Then FAIL result
- **AC-FR006-001**: Given FAIL result, When processed, Then boss_attempts += 1
- **AC-FR006-002**: Given FAIL and attempts < 3, When processed, Then retry allowed

**Independent Test**: Fail boss on purpose, verify attempt count, retry available
**Dependencies**: US-1

---

### US-4: Game Over - Boss Failures (Priority: P1 - Must-Have)
```
Third boss failure → game over → relationship ended
```
**Acceptance Criteria**:
- **AC-FR007-001**: Given boss_attempts = 2, When third fail, Then game_over triggered
- **AC-FR007-002**: Given game_over, When triggered, Then breakup message delivered
- **AC-FR007-003**: Given game_over, When user messages, Then cannot continue (must start new game)

**Independent Test**: Fail boss 3 times, verify game over state
**Dependencies**: US-3

---

### US-5: Game Over - Zero Score (Priority: P1 - Must-Have)
```
Score drops to 0% → game over → relationship dead
```
**Acceptance Criteria**:
- **AC-FR008-001**: Given score at 5%, When decay applies -5%, Then game_over triggered
- **AC-FR008-002**: Given zero-score game over, When triggered, Then different message than boss fail
- **AC-FR008-003**: Given game_over, When status checked, Then correct reason recorded

**Independent Test**: Let score decay to zero, verify game over
**Dependencies**: Decay System (005)

---

### US-6: Victory (Priority: P1 - Must-Have)
```
Pass Chapter 5 boss → victory → relationship established
```
**Acceptance Criteria**:
- **AC-FR009-001**: Given Ch5 boss passed, When processed, Then game_status = "won"
- **AC-FR009-002**: Given victory, When triggered, Then celebration message delivered
- **AC-FR009-003**: Given victory, When continuing, Then post-game mode (no stakes)

**Independent Test**: Complete all 5 bosses, verify victory state
**Dependencies**: US-2

---

## Intelligence Evidence

### Findings
- nikita/engine/constants.py:24-31 - BOSS_THRESHOLDS: {1:60, 2:65, 3:70, 4:75, 5:80}
- nikita/engine/constants.py:113-139 - BOSS_ENCOUNTERS with names, triggers, challenges
- nikita/engine/constants.py:142-147 - GAME_STATUSES: active, boss_fight, game_over, won

### Assumptions
- ASSUMPTION: Scoring Engine (003) emits threshold events
- ASSUMPTION: User model has boss_attempts field
- ASSUMPTION: LLM can judge extended conversation pass/fail

---

## Scope

### In-Scope
- Boss threshold detection and triggering
- 5 distinct boss encounter flows
- Boss outcome judgment (pass/fail)
- Chapter advancement on pass
- Game over conditions (3 fails, 0 score)
- Victory condition (Ch5 pass)

### Out-of-Scope
- Scoring during normal conversations (003)
- Decay mechanics (005)
- Portal display of chapter progress (008)

---

## Infrastructure Dependencies

This feature depends on the following infrastructure specs:

| Spec | Dependency | Usage |
|------|------------|-------|
| 009-database-infrastructure | Chapter state, boss attempts | UserRepository.advance_chapter(), UserRepository.increment_boss_attempts() |

**Database Tables Used**:
- `users` (chapter, boss_attempts, game_status updates)
- `score_history` (event_type='boss_pass' or 'boss_fail')
- `conversations` (is_boss_fight flag)

**No API Endpoints** - Internal engine, state changes via text agent

**No Background Tasks** - Boss encounters are synchronous conversations

---

## Risks & Mitigations

### Risk 1: Boss Judgment Unfairness
**Description**: Users feel they passed but LLM says fail
**Likelihood**: Medium (0.5) | **Impact**: High (8) | **Score**: 4.0
**Mitigation**: Clear criteria, explanation with judgment, appeal logging

### Risk 2: Boss Too Easy/Hard
**Description**: All players pass or fail consistently
**Likelihood**: Medium (0.5) | **Impact**: Medium (5) | **Score**: 2.5
**Mitigation**: Analytics on pass rates, adjustable prompts, A/B testing

---

## Success Metrics

- Boss 1 pass rate: 60-70% (challenging but achievable)
- Boss 5 pass rate (of those who reach it): 40-50%
- Victory rate: 10-20% of all players (rare but possible)
- Game over rate: 30-40% of all players (real stakes)

---

**Version**: 1.0
**Last Updated**: 2025-11-28
