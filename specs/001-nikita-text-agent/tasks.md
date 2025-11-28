---
feature: 001-nikita-text-agent
created: 2025-11-28
status: Complete
plan_file: plan.md
spec_file: spec.md
---

# Implementation Tasks: Nikita Text Agent

## Overview

**Total User Stories**: 8 (3 P1 + 3 P2 + 2 P3)
**Scope**: P1 + P2 = 6 user stories (P3 deferred)
**Total Tasks**: 15

---

## US-1: Basic Conversation (Priority: P1 - Must-Have) ✅

> Player → send text message → receive Nikita response with personality

### T1.1: Create Nikita Persona Prompt
- **Status**: [x] Complete
- **File**: `nikita/prompts/nikita_persona.py`
- **Description**: Create comprehensive persona document with backstory, communication style, interests, values, and negative examples
- **Acceptance Criteria**:
  - [x] AC-1.1.1: Persona includes complete backstory (Russian, 29, security consultant, lives alone, brilliant, cynical)
  - [x] AC-1.1.2: Communication style rules defined (direct, challenging, intellectually demanding)
  - [x] AC-1.1.3: Interests listed (cryptography, psychology, dark humor, philosophy)
  - [x] AC-1.1.4: Values defined (intelligence, authenticity, earned respect)
  - [x] AC-1.1.5: Negative examples section ("Nikita would NEVER say...")
  - [x] AC-1.1.6: At least 10 example responses for different scenarios
- **Dependencies**: None

### T1.2: Create NikitaDeps Dataclass
- **Status**: [x] Complete
- **File**: `nikita/agents/text/deps.py`
- **Description**: Create dependency injection container for agent with memory, user, and settings
- **Acceptance Criteria**:
  - [x] AC-1.2.1: NikitaDeps contains memory: NikitaMemory
  - [x] AC-1.2.2: NikitaDeps contains user: User
  - [x] AC-1.2.3: NikitaDeps contains settings: Settings
  - [x] AC-1.2.4: chapter property returns user.chapter
  - [x] AC-1.2.5: Type hints complete for Pydantic AI compatibility
- **Dependencies**: None

### T1.3: Implement NikitaTextAgent
- **Status**: [x] Complete
- **File**: `nikita/agents/text/agent.py`
- **Description**: Create Pydantic AI agent with dynamic system prompt combining persona, chapter behavior, and memory context
- **Acceptance Criteria**:
  - [x] AC-1.3.1: Agent uses anthropic:claude-sonnet-4-20250514 model
  - [x] AC-1.3.2: Agent has deps_type=NikitaDeps
  - [x] AC-1.3.3: @agent.system_prompt combines NIKITA_PERSONA + CHAPTER_BEHAVIORS + memory_context
  - [x] AC-1.3.4: Agent accepts user message and returns string response
  - [x] AC-1.3.5: Agent can be invoked with `await agent.run(message, deps=deps)`
- **Dependencies**: T1.1, T1.2

### T1.4: Create Agent Factory
- **Status**: [x] Complete
- **File**: `nikita/agents/text/__init__.py`
- **Description**: Factory function to create configured agent with deps for a specific user
- **Acceptance Criteria**:
  - [x] AC-1.4.1: `get_nikita_agent(user_id: UUID)` async function exists
  - [x] AC-1.4.2: Function loads user from database
  - [x] AC-1.4.3: Function initializes NikitaMemory for user
  - [x] AC-1.4.4: Function returns tuple (Agent, NikitaDeps)
  - [x] AC-1.4.5: Function handles user not found with appropriate error
- **Dependencies**: T1.3

---

## US-2: Memory-Enriched Responses (Priority: P1 - Must-Have) ✅

> Player → send message referencing past → Nikita remembers and responds contextually

### T2.1: Implement Memory Context Injection
- **Status**: [x] Complete
- **File**: `nikita/agents/text/agent.py` (update)
- **Description**: Add memory context retrieval to system prompt generation
- **Acceptance Criteria**:
  - [x] AC-2.1.1: System prompt calls `memory.get_context_for_prompt(user_message)`
  - [x] AC-2.1.2: Memory context formatted with timestamps and graph labels
  - [x] AC-2.1.3: Maximum 5 memories injected per response
  - [x] AC-2.1.4: Memory section clearly labeled in prompt (RELEVANT_MEMORIES:)
- **Dependencies**: T1.3

### T2.2: Create recall_memory Tool
- **Status**: [x] Complete
- **File**: `nikita/agents/text/tools.py`
- **Description**: Agent tool to actively search memory during conversation
- **Acceptance Criteria**:
  - [x] AC-2.2.1: Tool decorated with `@agent.tool(retries=2)`
  - [x] AC-2.2.2: Tool accepts query: str parameter
  - [x] AC-2.2.3: Tool calls `memory.search_memory(query, limit=5)`
  - [x] AC-2.2.4: Tool returns formatted string of results
  - [x] AC-2.2.5: Tool handles empty results gracefully
- **Dependencies**: T2.1

---

## US-3: Chapter-Based Behavior (Priority: P1 - Must-Have) ✅

> Player in Chapter X → conversation → behavior matches chapter expectations

### T3.1: Integrate Chapter Behavior Injection
- **Status**: [x] Complete
- **File**: `nikita/agents/text/agent.py` (update)
- **Description**: Import and inject CHAPTER_BEHAVIORS based on user's current chapter
- **Acceptance Criteria**:
  - [x] AC-3.1.1: CHAPTER_BEHAVIORS imported from nikita.engine.constants
  - [x] AC-3.1.2: Correct chapter behavior selected based on deps.chapter
  - [x] AC-3.1.3: Chapter behavior injected after persona, before memory
  - [x] AC-3.1.4: Behavior injection clearly labeled (CURRENT_CHAPTER_BEHAVIOR:)
- **Dependencies**: T1.3

### T3.2: Create Chapter Behavior Tests
- **Status**: [x] Complete
- **File**: `tests/agents/text/test_chapter_behavior.py`
- **Description**: Tests verifying behavior changes appropriately across chapters
- **Acceptance Criteria**:
  - [x] AC-3.2.1: Test Ch1 user receives skeptical/evaluating responses
  - [x] AC-3.2.2: Test Ch3 user receives emotionally vulnerable responses
  - [x] AC-3.2.3: Test Ch5 user receives consistent/authentic responses
  - [x] AC-3.2.4: Tests mock agent to verify prompt content by chapter
- **Dependencies**: T3.1

---

## US-4: Response Timing Variability (Priority: P2 - Important) ✅

> Player sends message → system delays response → timing matches chapter expectations

### T4.1: Create ResponseTimer Class
- **Status**: [x] Complete
- **File**: `nikita/agents/text/timing.py`
- **Description**: Class to calculate response delays using gaussian distribution within chapter-specific ranges
- **Acceptance Criteria**:
  - [x] AC-4.1.1: TIMING_RANGES dict maps chapter to (min_seconds, max_seconds)
  - [x] AC-4.1.2: Ch1 range: 600-28800s (10min-8h)
  - [x] AC-4.1.3: Ch5 range: 300-1800s (5min-30min)
  - [x] AC-4.1.4: `calculate_delay(chapter)` returns int seconds
  - [x] AC-4.1.5: Distribution is gaussian, not uniform (natural feel)
  - [x] AC-4.1.6: Random jitter added to prevent exact patterns
- **Dependencies**: None

### T4.2: Create MessageHandler with Timing
- **Status**: [x] Complete
- **File**: `nikita/agents/text/handler.py`
- **Description**: Handler that wraps agent and schedules response delivery
- **Acceptance Criteria**:
  - [x] AC-4.2.1: `MessageHandler.handle(user_id, message)` async method exists
  - [x] AC-4.2.2: Handler generates response via agent
  - [x] AC-4.2.3: Handler calculates delay via ResponseTimer
  - [x] AC-4.2.4: Handler stores pending response with scheduled delivery time
  - [x] AC-4.2.5: Handler returns ResponseDecision with delay_seconds
- **Dependencies**: T1.4, T4.1

---

## US-5: Message Skipping (Priority: P2 - Important) ✅

> Player sends message → system may skip → creates unpredictability

### T5.1: Create SkipDecision Class
- **Status**: [x] Complete
- **File**: `nikita/agents/text/skip.py`
- **Description**: Class to decide whether to skip responding to a message
- **Acceptance Criteria**:
  - [x] AC-5.1.1: SKIP_RATES dict maps chapter to (min_rate, max_rate)
  - [x] AC-5.1.2: Ch1 rate: 25-40% skip
  - [x] AC-5.1.3: Ch5 rate: 0-5% skip
  - [x] AC-5.1.4: `should_skip(chapter)` returns bool
  - [x] AC-5.1.5: Skip probability randomized within range each call
- **Dependencies**: None

### T5.2: Integrate Skip Logic with Handler
- **Status**: [x] Complete
- **File**: `nikita/agents/text/handler.py` (update)
- **Description**: Add skip decision check before generating response
- **Acceptance Criteria**:
  - [x] AC-5.2.1: Handler checks `SkipDecision.should_skip()` before agent.run()
  - [x] AC-5.2.2: Skipped messages logged with reason
  - [x] AC-5.2.3: Skip state stored so consecutive messages don't all skip
  - [x] AC-5.2.4: Next message after skip processes normally
  - [x] AC-5.2.5: ResponseDecision.should_respond = False when skipped
- **Dependencies**: T4.2, T5.1

---

## US-6: User Fact Learning (Priority: P2 - Important) ✅

> Player reveals information → system extracts fact → stored for future reference

### T6.1: Create FactExtractor Class
- **Status**: [x] Complete
- **File**: `nikita/agents/text/facts.py`
- **Description**: Class to extract facts from user messages using LLM analysis
- **Acceptance Criteria**:
  - [x] AC-6.1.1: `extract_facts(user_message, nikita_response, existing_facts)` async method
  - [x] AC-6.1.2: Uses LLM to identify explicit facts (user states directly)
  - [x] AC-6.1.3: Uses LLM to identify implicit facts (inferred from context)
  - [x] AC-6.1.4: Returns list[ExtractedFact] with fact, confidence, source
  - [x] AC-6.1.5: Avoids extracting already-known facts (deduplication)
- **Dependencies**: None

### T6.2: Create note_user_fact Tool
- **Status**: [x] Complete
- **File**: `nikita/agents/text/tools.py` (update)
- **Description**: Agent tool to actively store facts during conversation
- **Acceptance Criteria**:
  - [x] AC-6.2.1: Tool decorated with `@agent.tool`
  - [x] AC-6.2.2: Tool accepts fact: str and confidence: float parameters
  - [x] AC-6.2.3: Tool calls `memory.add_user_fact(fact, confidence)`
  - [x] AC-6.2.4: Tool returns confirmation string
- **Dependencies**: T2.2

### T6.3: Integrate Fact Extraction Post-Response
- **Status**: [x] Complete
- **File**: `nikita/agents/text/handler.py` (update)
- **Description**: Run fact extraction after response generation
- **Acceptance Criteria**:
  - [x] AC-6.3.1: Handler calls FactExtractor after agent generates response
  - [x] AC-6.3.2: Extracted facts stored via memory.add_user_fact()
  - [x] AC-6.3.3: Facts include source_message reference
  - [x] AC-6.3.4: ResponseDecision includes facts_extracted list
- **Dependencies**: T5.2, T6.1, T6.2

---

## Deferred (P3)

### US-7: Nikita-Initiated Conversations
- **Status**: Deferred to 005-decay-system or separate feature
- **Reason**: Requires Celery scheduler infrastructure

### US-8: Conversation Flow Management
- **Status**: Deferred
- **Reason**: Polish feature, can be added to persona prompt later

---

## Task Dependencies Graph

```
T1.1 ─┐
      ├──→ T1.3 ─→ T1.4 ─→ T2.1 ─→ T2.2
T1.2 ─┘                       ↓
                           T3.1 ─→ T3.2
                              ↓
T4.1 ───────────────────→ T4.2
                              ↓
T5.1 ───────────────────→ T5.2
                              ↓
T6.1 ─→ T6.2 ───────────→ T6.3
```

---

## Implementation Order

### Phase 1: Core Agent (US-1, US-2, US-3) ✅
1. T1.1 - Nikita Persona Prompt ✅
2. T1.2 - NikitaDeps Dataclass ✅
3. T1.3 - NikitaTextAgent ✅
4. T1.4 - Agent Factory ✅
5. T2.1 - Memory Context Injection ✅
6. T2.2 - recall_memory Tool ✅
7. T3.1 - Chapter Behavior Injection ✅
8. T3.2 - Chapter Behavior Tests ✅

### Phase 2: Timing & Skip (US-4, US-5) ✅
9. T4.1 - ResponseTimer Class ✅
10. T4.2 - MessageHandler with Timing ✅
11. T5.1 - SkipDecision Class ✅
12. T5.2 - Skip Logic Integration ✅

### Phase 3: Fact Learning (US-6) ✅
13. T6.1 - FactExtractor Class ✅
14. T6.2 - note_user_fact Tool ✅
15. T6.3 - Fact Extraction Integration ✅

---

## Progress Summary

| User Story | Tasks | Completed | Status |
|------------|-------|-----------|--------|
| US-1: Basic Conversation | 4 | 4 | ✅ Complete |
| US-2: Memory-Enriched | 2 | 2 | ✅ Complete |
| US-3: Chapter-Based | 2 | 2 | ✅ Complete |
| US-4: Response Timing | 2 | 2 | ✅ Complete |
| US-5: Message Skipping | 2 | 2 | ✅ Complete |
| US-6: Fact Learning | 3 | 3 | ✅ Complete |
| **Total** | **15** | **15** | **100%** |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-28 | Initial task breakdown |
| 2.0 | 2025-11-28 | All tasks complete (T1.1-T6.3), 156 tests passing |

---

## Test Coverage

**Total Tests**: 156 passed, 5 skipped
**Test Files**:
- `test_agent.py` - Agent and system prompt tests
- `test_deps.py` - NikitaDeps tests
- `test_chapter_behavior.py` - Chapter behavior injection tests
- `test_timing.py` - ResponseTimer tests
- `test_handler.py` - MessageHandler tests
- `test_handler_skip.py` - Skip integration tests
- `test_handler_facts.py` - Fact extraction integration tests
- `test_skip.py` - SkipDecision tests
- `test_tools.py` - recall_memory and note_user_fact tool tests
- `test_facts.py` - FactExtractor tests

