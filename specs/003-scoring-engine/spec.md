---
feature: 003-scoring-engine
created: 2025-11-28
status: Draft
priority: P1
technology_agnostic: true
constitutional_compliance:
  article_iv: specification_first
---

# Feature Specification: Scoring Engine

**IMPORTANT**: This specification is TECHNOLOGY-AGNOSTIC. Focus on WHAT and WHY, not HOW.

---

## Summary

The Scoring Engine transforms conversations into game mechanics by analyzing each interaction and calculating how it affects the player's relationship with Nikita. It manages the four core metrics (intimacy, passion, trust, secureness), calculates composite scores, and maintains score history.

**Problem Statement**: Without scoring, conversations have no stakes. Users need feedback on whether their interactions are helping or hurting the relationship, turning conversations into gameplay.

**Value Proposition**: Every message matters. Users receive implicit feedback through Nikita's responses and explicit progress through score changes, creating the "game you can lose" experience.

### CoD^Σ Overview

**System Model**:
```
Conversation → Analysis → Metric_Deltas → Score_Update → History_Log
      ↓           ↓            ↓              ↓              ↓
  User+Nikita   LLM_eval    +/-Δ[i,p,t,s]   Composite    Audit_trail

Metrics := {intimacy: 0.30, passion: 0.25, trust: 0.25, secureness: 0.20}
Composite := Σ(metric_i × weight_i) for i ∈ {intimacy, passion, trust, secureness}
```

---

## Functional Requirements

**Current [NEEDS CLARIFICATION] Count**: 0 / 3

### FR-001: Interaction Analysis
System MUST analyze each user-Nikita exchange and determine:
- Intimacy impact: Did this exchange deepen emotional closeness?
- Passion impact: Did this exchange increase excitement/desire?
- Trust impact: Did this exchange build or damage trust?
- Secureness impact: Did this exchange make her feel secure in the relationship?

**Rationale**: Four-metric model captures relationship health dimensions (constitution §III.1)
**Priority**: Must Have

### FR-002: Metric Delta Calculation
System MUST calculate score changes (deltas) for each metric:
- Range: -10 to +10 per interaction
- Positive: Exchange improved this dimension
- Negative: Exchange damaged this dimension
- Zero: Neutral impact on this dimension

**Rationale**: Bounded deltas prevent single exchanges from being catastrophic or game-breaking
**Priority**: Must Have

### FR-003: Composite Score Calculation
System MUST calculate composite relationship score using fixed weights:
- Intimacy: 30%
- Passion: 25%
- Trust: 25%
- Secureness: 20%
- Formula: composite = (intimacy × 0.30) + (passion × 0.25) + (trust × 0.25) + (secureness × 0.20)

**Rationale**: Fixed weights per constitution §III.1 - prevents gamification exploitation
**Priority**: Must Have

### FR-004: Score Bounds Enforcement
System MUST enforce score boundaries:
- Individual metrics: 0 to 100
- Composite score: 0% to 100%
- No negative scores (floor at 0)
- No over-100 scores (ceiling at 100)

**Rationale**: Clear bounds make progress understandable
**Priority**: Must Have

### FR-005: Score History Logging
System MUST maintain complete score history:
- Timestamp of each change
- Score before and after
- Metric deltas applied
- Source of change (interaction, decay, boss result)
- Conversation excerpt that triggered change

**Rationale**: Audit trail enables debugging, prevents disputes, enables visualization
**Priority**: Must Have

### FR-006: Context-Aware Analysis
System MUST consider context when analyzing:
- Current chapter (Ch1 standards differ from Ch5)
- Recent conversation history
- User's established patterns
- Relationship state (conflict, makeup, stable)

**Rationale**: Same words can mean different things in different contexts
**Priority**: Must Have

### FR-007: Analysis Explanation
System MUST provide reasoning for score changes:
- Brief explanation of why each delta was assigned
- Specific behaviors identified (good and bad)
- Stored with score history for audit

**Rationale**: Enables debugging and user understanding if exposed later
**Priority**: Should Have

### FR-008: Bulk Analysis Support
System MUST support analyzing multiple exchanges at once:
- Voice call transcripts (multiple turns)
- Catch-up sessions (multiple messages)
- Batch processing for efficiency

**Rationale**: Voice calls produce multi-turn transcripts needing unified analysis
**Priority**: Should Have

### FR-009: Real-time Score Access
System MUST provide current scores on demand:
- Current composite score
- Individual metric values
- Time since last update
- Chapter and game status

**Rationale**: Other features need current scores (boss triggers, portal display)
**Priority**: Must Have

### FR-010: Score Change Events
System MUST emit events when scores change significantly:
- Boss threshold reached (60%, 65%, 70%, 75%, 80%)
- Critical low (below 20%)
- Game over condition (0%)
- Recovery from critical (back above 20%)

**Rationale**: Other systems need to react to score milestones
**Priority**: Must Have

---

## Non-Functional Requirements

### Performance
- Analysis latency: < 3 seconds per exchange
- Score retrieval: < 100ms
- Batch analysis: < 10 seconds for 20-turn voice call

### Reliability
- Score consistency: No race conditions in concurrent updates
- Durability: Score changes persisted before confirmation
- Recovery: Reconstruct current score from history if needed

### Accuracy
- Analysis quality: Consistent with human judgment in 85%+ cases
- No gaming: Obvious "farming" patterns should not improve scores
- Contextual: Same input different context yields different analysis

### Scalability
- Per-user: Handle 100+ daily interactions per active user
- System-wide: 1M+ score updates per day

---

## User Stories (CoD^Σ)

### US-1: Exchange Scoring (Priority: P1 - Must-Have)
```
Conversation exchange → analyzed → metrics updated
```
**Why P1**: Core functionality—without scoring, no game mechanics

**Acceptance Criteria**:
- **AC-FR001-001**: Given user sends thoughtful message, When Nikita responds positively, Then positive deltas are calculated
- **AC-FR002-001**: Given calculated deltas, When applied, Then each delta is within -10 to +10 range
- **AC-FR003-001**: Given metric updates, When composite calculated, Then formula uses 30/25/25/20 weights exactly

**Independent Test**: Have conversation, verify metrics updated with reasonable deltas
**Dependencies**: Text Agent (001) operational

---

### US-2: Score History (Priority: P1 - Must-Have)
```
Score changes → logged with context → retrievable
```
**Why P1**: Required for audit, debugging, and portal display

**Acceptance Criteria**:
- **AC-FR005-001**: Given score change, When logged, Then timestamp, before, after, deltas, source recorded
- **AC-FR005-002**: Given score history, When queried, Then complete history retrievable in order
- **AC-FR005-003**: Given conversation context, When logged, Then relevant excerpt stored with change

**Independent Test**: Make score changes, query history, verify complete record
**Dependencies**: None (database only)

---

### US-3: Threshold Events (Priority: P1 - Must-Have)
```
Score crosses threshold → event emitted → other systems react
```
**Why P1**: Boss system depends on threshold events

**Acceptance Criteria**:
- **AC-FR010-001**: Given score rises to 60%+, When in Chapter 1, Then boss_threshold_reached event emitted
- **AC-FR010-002**: Given score drops to 0%, When any chapter, Then game_over event emitted
- **AC-FR010-003**: Given events emitted, When consumed by boss system, Then appropriate action taken

**Independent Test**: Manipulate score to threshold, verify event emitted
**Dependencies**: None (event emission)

---

### US-4: Context-Aware Analysis (Priority: P2 - Important)
```
Same message + different context → different scoring
```
**Why P2**: Improves accuracy but basic scoring works without it

**Acceptance Criteria**:
- **AC-FR006-001**: Given Ch1 user, When they ask personal question, Then more positive than Ch5 user asking same
- **AC-FR006-002**: Given recent conflict, When user apologizes, Then higher positive impact than random apology
- **AC-FR006-003**: Given context considered, When analyzing, Then reasoning reflects context

**Independent Test**: Same message at different chapters, verify different scores
**Dependencies**: P1 complete

---

### US-5: Analysis Explanation (Priority: P2 - Important)
```
Score change → explanation available → debugging possible
```
**Why P2**: Important for debugging and potential user feedback feature

**Acceptance Criteria**:
- **AC-FR007-001**: Given score change, When stored, Then explanation of reasoning included
- **AC-FR007-002**: Given explanation, When reviewed, Then specific behaviors identified
- **AC-FR007-003**: Given poor score, When explanation reviewed, Then actionable insight available

**Independent Test**: Get score change, retrieve explanation, verify it's meaningful
**Dependencies**: P1 complete

---

### US-6: Voice Call Batch Analysis (Priority: P3 - Nice-to-Have)
```
Voice transcript (multi-turn) → single analysis → aggregate impact
```
**Why P3**: Voice feature (007) dependent, not blocking text MVP

**Acceptance Criteria**:
- **AC-FR008-001**: Given 20-turn voice transcript, When analyzed, Then single aggregate impact calculated
- **AC-FR008-002**: Given batch analysis, When processing, Then completes within 10 seconds
- **AC-FR008-003**: Given batch result, When applied, Then history shows single "voice_call" entry

**Independent Test**: Submit multi-turn transcript, verify single aggregate score change
**Dependencies**: P1 ∧ P2 complete, Voice Agent (007)

---

## Intelligence Evidence

### Findings

**Related Features**:
- nikita/engine/constants.py:51-57 - METRIC_WEIGHTS already defined (30/25/25/20)
- nikita/db/models/user.py - UserMetrics model exists (intimacy, passion, trust, secureness)
- constitution.md §III.1 - Fixed scoring formula requirement

**Existing Patterns**:
- BOSS_THRESHOLDS defined: 60%, 65%, 70%, 75%, 80%
- score_history table mentioned in database models
- Decimal precision used for scores

### Assumptions
- ASSUMPTION: Text Agent provides conversation for analysis
- ASSUMPTION: LLM available for analysis (Claude API)
- ASSUMPTION: Database can handle high-frequency score updates

---

## Scope

### In-Scope
- Exchange analysis (LLM-based evaluation)
- Four-metric delta calculation
- Composite score calculation (fixed formula)
- Score history logging with audit trail
- Threshold event emission
- Context-aware analysis

### Out-of-Scope
- Boss encounter logic (004-chapter-boss-system)
- Decay mechanics (005-decay-system)
- Score visualization (008-player-portal)
- Vice-based personalization (006-vice-personalization)

---

## Constraints

### Constitutional Constraints
- §III.1: Fixed 30/25/25/20 weights (CANNOT be changed)
- §III.2: Score bounds 0-100 per metric
- §III.3: Delta bounds -10 to +10 per exchange

### Technical Constraints
- LLM calls have latency and cost
- Analysis must be consistent (same input → same output)
- History grows linearly with interactions

---

## Infrastructure Dependencies

This feature depends on the following infrastructure specs:

| Spec | Dependency | Usage |
|------|------------|-------|
| 009-database-infrastructure | Score persistence, history logging | UserRepository.update_score(), ScoreHistoryRepository.log_event() |

**Database Tables Used**:
- `users` (relationship_score updates)
- `user_metrics` (intimacy, passion, trust, secureness deltas)
- `score_history` (event logging with event_type='conversation')

**No API Endpoints** - Internal engine, called by agents

**No Background Tasks** - Synchronous scoring per interaction

---

## Risks & Mitigations

### Risk 1: Analysis Inconsistency
**Description**: Same conversation analyzed differently on retry
**Likelihood**: Medium (0.5) | **Impact**: Medium (5) | **Score**: 2.5
**Mitigation**: Temperature=0, detailed prompts, caching identical inputs

### Risk 2: Gaming/Farming
**Description**: Users discover phrases that always give positive scores
**Likelihood**: Medium (0.5) | **Impact**: High (8) | **Score**: 4.0
**Mitigation**: Context-aware analysis, pattern detection, diminishing returns

### Risk 3: LLM Cost at Scale
**Description**: Analysis cost unsustainable with high message volume
**Likelihood**: Low (0.2) | **Impact**: High (8) | **Score**: 1.6
**Mitigation**: Batch analysis, caching, skip analysis for trivial messages

---

## Success Metrics

### Technical Metrics
- Analysis accuracy: 85%+ agreement with human judgment
- Latency: < 3s p95 for single exchange analysis
- Consistency: 95%+ same result on identical inputs

### Game Metrics
- Score distribution: Bell curve around 50% (not clustered at 0 or 100)
- Boss trigger rate: 60%+ of players eventually hit first threshold
- Engagement correlation: Higher scores → higher retention

---

**Version**: 1.0
**Last Updated**: 2025-11-28
**Next Step**: Create implementation plan with `/plan specs/003-scoring-engine/spec.md`
