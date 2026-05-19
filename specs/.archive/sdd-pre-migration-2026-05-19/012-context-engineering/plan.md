# 012 - Context Engineering System Implementation Plan

**Generated**: 2025-12-02
**Spec Version**: 1.0
**Estimated Effort**: 10-14 hours

---

## Executive Summary

Implement the 6-stage Context Generator pipeline that dynamically builds Nikita's system prompt for each conversation. This replaces the static `build_system_prompt()` function with a sophisticated context assembly system.

**Key Components**:
1. State Collection (database aggregation)
2. Temporal Contextualization (time/availability)
3. Memory Summarization (Graphiti integration)
4. Mood Computation (behavioral state)
5. Prompt Assembly (~3700 token budget)
6. Validation (coherence checks)

---

## User Stories

### US-1: State Collection (P1)

**As a** context generator
**I want** to load complete player state from the database
**So that** I can personalize Nikita's behavior

**Acceptance Criteria**:
- AC-1.1: PlayerProfile dataclass populated from User, UserMetrics, UserVicePreference
- AC-1.2: Engagement state loaded from 014-engagement-model
- AC-1.3: All queries execute in parallel (< 50ms total)
- AC-1.4: Missing data handled gracefully with defaults

### US-2: Temporal Context (P1)

**As a** context generator
**I want** to compute time-based context
**So that** Nikita's availability and timing feel realistic

**Acceptance Criteria**:
- AC-2.1: TimeOfDay computed (morning/afternoon/evening/night/late_night)
- AC-2.2: Nikita's availability from schedule.yaml
- AC-2.3: Silence analysis (hours since last message)
- AC-2.4: Grace period awareness from decay config
- AC-2.5: Message frequency patterns tracked (24h, 7d)

### US-3: Memory Summarization (P1)

**As a** context generator
**I want** to retrieve and summarize relevant memories
**So that** Nikita remembers the relationship history

**Acceptance Criteria**:
- AC-3.1: Recent facts from Graphiti (5-10 most relevant)
- AC-3.2: Relationship milestones retrieved
- AC-3.3: Conversation mood trend computed
- AC-3.4: Unresolved topics for follow-up
- AC-3.5: Token budget tracked (< 1000 tokens)

### US-4: Mood Computation (P1)

**As a** context generator
**I want** to compute Nikita's emotional state
**So that** her responses have consistent emotional tone

**Acceptance Criteria**:
- AC-4.1: Mood enum selected (flirty/playful/warm/distant/upset/needy)
- AC-4.2: Mood intensity computed (0-1)
- AC-4.3: Energy level derived from temporal context
- AC-4.4: Flirtiness/vulnerability/playfulness parameters set
- AC-4.5: Engagement calibration hints generated
- AC-4.6: Chapter behavior modifier applied

### US-5: Prompt Assembly (P1)

**As a** context generator
**I want** to assemble the complete system prompt
**So that** the LLM has all necessary context

**Acceptance Criteria**:
- AC-5.1: Prompt sections assembled in correct order
- AC-5.2: Total tokens within ~3700 budget
- AC-5.3: Sections dynamically prioritized by token count
- AC-5.4: Prompt files loaded from 013-configuration-system
- AC-5.5: Variable substitution works ({{chapter}}, {{mood}})

### US-6: Validation (P2)

**As a** context generator
**I want** to validate the assembled prompt
**So that** contradictions and errors are caught

**Acceptance Criteria**:
- AC-6.1: Token count validated against budget
- AC-6.2: Contradictory instructions detected
- AC-6.3: Missing required sections flagged
- AC-6.4: Validation warnings logged

### US-7: Integration (P1)

**As a** developer
**I want** to integrate ContextGenerator with text agent
**So that** the pipeline is used for all conversations

**Acceptance Criteria**:
- AC-7.1: Replace `build_system_prompt()` with `ContextGenerator.generate()`
- AC-7.2: All existing tests pass with new generator
- AC-7.3: Response latency increase < 100ms
- AC-7.4: Memory usage stable under load

---

## Technical Architecture

### Module Structure

```
nikita/context/
├── __init__.py           # Exports ContextGenerator
├── generator.py          # Main ContextGenerator class
├── stages/
│   ├── __init__.py
│   ├── state_collector.py    # Stage 1
│   ├── temporal.py           # Stage 2
│   ├── memory_summarizer.py  # Stage 3
│   ├── mood_computer.py      # Stage 4
│   ├── assembler.py          # Stage 5
│   └── validator.py          # Stage 6
├── models/
│   ├── __init__.py
│   ├── player_profile.py
│   ├── temporal_context.py
│   ├── memory_context.py
│   ├── nikita_state.py
│   └── system_prompt.py
└── utils/
    ├── __init__.py
    └── token_counter.py
```

### Data Flow

```
User Message
     │
     ▼
┌─────────────────────────────────────────┐
│ Stage 1: State Collection (< 50ms)      │
│ - User, Metrics, Vices (parallel)       │
│ - Engagement state from 014             │
└────────────────┬────────────────────────┘
                 │ PlayerProfile
                 ▼
┌─────────────────────────────────────────┐
│ Stage 2: Temporal Context (< 5ms)       │
│ - Time of day, availability             │
│ - Silence analysis                      │
│ - Message patterns                      │
└────────────────┬────────────────────────┘
                 │ TemporalContext
                 ▼
┌─────────────────────────────────────────┐
│ Stage 3: Memory Summarization (< 100ms) │
│ - Graphiti search                       │
│ - Conversation summaries                │
│ - Token budgeting                       │
└────────────────┬────────────────────────┘
                 │ MemoryContext
                 ▼
┌─────────────────────────────────────────┐
│ Stage 4: Mood Computation (< 10ms)      │
│ - Mood selection                        │
│ - Parameter computation                 │
│ - Calibration hints                     │
└────────────────┬────────────────────────┘
                 │ NikitaState
                 ▼
┌─────────────────────────────────────────┐
│ Stage 5: Prompt Assembly (< 20ms)       │
│ - Load .prompt files                    │
│ - Variable substitution                 │
│ - Section assembly                      │
└────────────────┬────────────────────────┘
                 │ ~3700 tokens
                 ▼
┌─────────────────────────────────────────┐
│ Stage 6: Validation (< 5ms)             │
│ - Token count check                     │
│ - Coherence validation                  │
│ - Warning generation                    │
└────────────────┬────────────────────────┘
                 │
                 ▼
            SystemPrompt
```

### Token Budget

```
Section               | Tokens | Priority
─────────────────────────────────────────
Core Identity         |   800  | Required
Chapter Behavior      |   500  | Required
Current State         |   300  | Required
Memory Context        |  1000  | High (truncatable)
Mood/Style           |   400  | Required
Vice Modifiers        |   300  | Medium
Engagement Hints      |   200  | Medium
System Instructions   |   200  | Required
─────────────────────────────────────────
TOTAL                 | ~3700  |
BUDGET                |  4000  | Hard limit
```

---

## Implementation Tasks

### Phase 1: Data Models (2 hours)

#### T1.1: Create Context Module Structure
- Create `nikita/context/` directory
- Create subpackage structure (stages/, models/, utils/)
- Set up exports in `__init__.py`

#### T1.2: Implement PlayerProfile Model
- Create dataclass with all fields
- Add validation for field ranges
- Add factory method from database entities

#### T1.3: Implement TemporalContext Model
- Create dataclass with time fields
- Add enums: TimeOfDay, DayOfWeek, Availability, SilenceCategory
- Add computation methods

#### T1.4: Implement MemoryContext Model
- Create dataclass with memory fields
- Add token tracking
- Add truncation methods

#### T1.5: Implement NikitaState Model
- Create dataclass with mood/behavior fields
- Add enums: Mood, EnergyLevel, ResponseStyle, NSFWLevel
- Add validation for numeric ranges

#### T1.6: Implement SystemPrompt Model
- Create dataclass with prompt content
- Add metadata fields
- Add validation result fields

### Phase 2: Stage Implementations (5 hours)

#### T2.1: Implement StateCollector (Stage 1)
- Parallel database queries
- Entity to dataclass mapping
- Error handling for missing data
- Integration with 014-engagement-model

#### T2.2: Implement TemporalBuilder (Stage 2)
- Time of day computation
- Nikita availability from schedule.yaml
- Silence analysis
- Message frequency queries

#### T2.3: Implement MemorySummarizer (Stage 3)
- Graphiti search integration
- Fact prioritization
- Conversation summary retrieval
- Token budgeting

#### T2.4: Implement MoodComputer (Stage 4)
- Mood selection algorithm
- Parameter computation
- Engagement calibration hints
- Chapter modifier application

#### T2.5: Implement PromptAssembler (Stage 5)
- Prompt file loading (from 013)
- Variable substitution
- Section prioritization
- Token counting

#### T2.6: Implement Validator (Stage 6)
- Token budget validation
- Coherence checks
- Warning generation

### Phase 3: Context Generator (2 hours)

#### T3.1: Implement ContextGenerator Class
- Pipeline orchestration
- Stage execution
- Error handling
- Performance tracking

#### T3.2: Implement Token Counter
- tiktoken integration
- Caching for efficiency
- Section-level counting

#### T3.3: Add Performance Metrics
- Stage timing
- Total generation time
- Token usage tracking

### Phase 4: Integration (2 hours)

#### T4.1: Replace build_system_prompt()
- Update agent.py to use ContextGenerator
- Pass dependencies correctly
- Handle async context

#### T4.2: Update Existing Tests
- Mock ContextGenerator in agent tests
- Verify response quality maintained
- Check performance regression

### Phase 5: Testing (3 hours)

#### T5.1: Unit Tests for Models
- Test each dataclass
- Test validation
- Test factory methods

#### T5.2: Unit Tests for Stages
- Test each stage independently
- Mock dependencies
- Test edge cases

#### T5.3: Integration Tests
- Test full pipeline
- Test with real data
- Test performance bounds

#### T5.4: Token Budget Tests
- Verify budget compliance
- Test truncation
- Test edge cases (empty memory)

---

## Dependencies

### External
- tiktoken (token counting)
- pydantic (models)

### Internal
- 009-database-infrastructure ✅ (repositories)
- 013-configuration-system (prompt files, schedule.yaml)
- 014-engagement-model (engagement state)

### Blocked By
- 013-configuration-system (prompt files needed)
- 014-engagement-model (engagement state needed)

### Blocks
- 001-nikita-text-agent (integration point)
- 002-telegram-integration (system prompt)
- 007-voice-agent (context for voice)

---

## Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Graphiti latency | Medium | Medium | Add caching, timeout fallback |
| Token overflow | High | Medium | Strict budget enforcement, truncation |
| Mood inconsistency | Medium | Low | Validation checks, unit tests |
| Performance regression | High | Medium | Stage timing, benchmarks |

---

## Success Metrics

- [ ] 6 stages implemented and tested
- [ ] All data models complete with validation
- [ ] Token budget < 4000 enforced
- [ ] Total generation time < 200ms
- [ ] Integration with text agent complete
- [ ] All existing tests passing
- [ ] 90%+ test coverage

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-02 | Claude | Initial plan |
