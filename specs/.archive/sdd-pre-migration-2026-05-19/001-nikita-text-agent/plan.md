---
feature: 001-nikita-text-agent
created: 2025-11-28
status: Draft
spec_file: spec.md
technology_stack:
  - pydantic-ai
  - claude-sonnet-4
  - graphiti
  - supabase-postgresql
  - celery (P3 only)
---

# Implementation Plan: Nikita Text Agent

## Executive Summary

This plan implements the foundational Nikita Text Agent using Pydantic AI with Claude Sonnet. The agent enables text conversations with Nikita's distinctive personality, chapter-based behavior adaptation, and memory-enriched responses.

**Scope**: P1 (US-1,2,3) + P2 (US-4,5,6) = Core text experience
**P3 Deferred**: US-7 (initiation), US-8 (flow management) - requires Celery scheduler

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      NikitaTextAgent                         │
├─────────────────────────────────────────────────────────────┤
│  Pydantic AI Agent with NikitaDeps                          │
│                                                             │
│  @agent.system_prompt                                       │
│  ├── NIKITA_PERSONA (base personality)                      │
│  ├── CHAPTER_BEHAVIORS[chapter] (behavior overlay)          │
│  └── memory.get_context_for_prompt() (dynamic context)      │
│                                                             │
│  @agent.tool                                                │
│  ├── recall_memory(query) → search memory for context       │
│  └── extract_user_fact(fact) → store new user knowledge     │
│                                                             │
│  Post-processing                                            │
│  ├── response_timer.schedule_response()                     │
│  ├── skip_decision.should_skip()                            │
│  └── fact_extractor.extract_facts(user_msg, response)       │
└─────────────────────────────────────────────────────────────┘

Data Flow:
User_message → skip_check → agent.run() → fact_extraction → timing_schedule → response_delivery
```

---

## Research Summary

### Pydantic AI Patterns (from plan research)

```python
@dataclass
class NikitaDeps:
    memory: NikitaMemory
    user_id: UUID
    chapter: int
    settings: Settings

agent = Agent('anthropic:claude-sonnet', deps_type=NikitaDeps)

@agent.system_prompt
async def nikita_persona(ctx: RunContext[NikitaDeps]) -> str:
    context = await ctx.deps.memory.get_context_for_prompt(...)
    return f"{NIKITA_PERSONA}\n{CHAPTER_BEHAVIORS[ctx.deps.chapter]}\n{context}"

@agent.tool(retries=2)
async def recall_memory(ctx: RunContext[NikitaDeps], query: str) -> str:
    return await ctx.deps.memory.search(query)
```

### Existing Infrastructure

| Component | Location | Status |
|-----------|----------|--------|
| CHAPTER_BEHAVIORS | nikita/engine/constants.py:60-110 | ✅ Complete |
| NikitaMemory | nikita/memory/graphiti_client.py | ✅ Complete |
| User model | nikita/db/models/user.py | ✅ Complete |
| Settings | nikita/config/settings.py | ✅ Complete |

---

## User Story Implementation

### US-1: Basic Conversation (P1)

**Tasks**:

#### T1.1: Create Nikita Persona Prompt
- **File**: `nikita/prompts/nikita_persona.py`
- **Content**: Detailed persona with:
  - Backstory (Russian security consultant, 29, lives alone)
  - Communication style rules (direct, challenging, intellectual)
  - Interests (cryptography, psychology, dark humor, philosophy)
  - Values (intelligence, authenticity, earned respect)
  - Negative examples ("Nikita would NEVER say...")
  - Response format guidelines
- **ACs**: AC-FR001-001, AC-FR001-002, AC-FR001-003

#### T1.2: Create NikitaDeps Dataclass
- **File**: `nikita/agents/text/deps.py`
- **Content**:
```python
@dataclass
class NikitaDeps:
    memory: NikitaMemory
    user: User
    settings: Settings

    @property
    def chapter(self) -> int:
        return self.user.chapter
```

#### T1.3: Implement NikitaTextAgent
- **File**: `nikita/agents/text/agent.py`
- **Content**:
  - Pydantic AI Agent with NikitaDeps
  - Dynamic system prompt combining persona + chapter + memory
  - Basic message handling
- **Dependencies**: T1.1, T1.2

#### T1.4: Create Agent Factory
- **File**: `nikita/agents/text/__init__.py`
- **Content**:
```python
async def get_nikita_agent(user_id: UUID) -> tuple[Agent, NikitaDeps]:
    """Factory to get configured agent with deps for user."""
```

---

### US-2: Memory-Enriched Responses (P1)

**Tasks**:

#### T2.1: Implement Memory Context Injection
- **File**: `nikita/agents/text/agent.py` (update T1.3)
- **Content**:
  - Add memory context to system prompt
  - Format memories with timestamps and graph labels
- **ACs**: AC-FR003-001, AC-FR003-002, AC-FR003-003

#### T2.2: Create recall_memory Tool
- **File**: `nikita/agents/text/tools.py`
- **Content**:
```python
@agent.tool(retries=2)
async def recall_memory(ctx: RunContext[NikitaDeps], query: str) -> str:
    """Search memory for relevant information about a topic."""
    results = await ctx.deps.memory.search_memory(query, limit=5)
    return format_memory_results(results)
```

---

### US-3: Chapter-Based Behavior (P1)

**Tasks**:

#### T3.1: Integrate Chapter Behavior Injection
- **File**: `nikita/agents/text/agent.py` (update T1.3)
- **Content**:
  - Import CHAPTER_BEHAVIORS from constants
  - Inject appropriate behavior overlay in system prompt
- **ACs**: AC-FR002-001, AC-FR002-002, AC-FR002-003

#### T3.2: Create Chapter Behavior Tests
- **File**: `tests/agents/text/test_chapter_behavior.py`
- **Content**:
  - Test Ch1 user gets guarded/skeptical responses
  - Test Ch3 user gets emotional vulnerability
  - Test Ch5 user gets consistent/authentic responses

---

### US-4: Response Timing Variability (P2)

**Tasks**:

#### T4.1: Create ResponseTimer Class
- **File**: `nikita/agents/text/timing.py`
- **Content**:
```python
class ResponseTimer:
    TIMING_RANGES: dict[int, tuple[int, int]] = {
        1: (600, 28800),    # 10min to 8h (seconds)
        2: (300, 14400),    # 5min to 4h
        3: (300, 7200),     # 5min to 2h
        4: (300, 3600),     # 5min to 1h
        5: (300, 1800),     # 5min to 30min (consistent)
    }

    def calculate_delay(self, chapter: int) -> int:
        """Calculate response delay using gaussian distribution."""
        min_delay, max_delay = self.TIMING_RANGES[chapter]
        # Use normal distribution centered in range
        return random_delay_in_range(min_delay, max_delay, chapter)
```
- **ACs**: AC-FR005-001, AC-FR005-002, AC-FR005-003

#### T4.2: Integrate Timing with Agent Response
- **File**: `nikita/agents/text/handler.py`
- **Content**:
  - Create MessageHandler that wraps agent
  - Schedule response delivery after calculated delay
  - Store pending response in database for delivery

---

### US-5: Message Skipping (P2)

**Tasks**:

#### T5.1: Create SkipDecision Class
- **File**: `nikita/agents/text/skip.py`
- **Content**:
```python
class SkipDecision:
    SKIP_RATES: dict[int, tuple[float, float]] = {
        1: (0.25, 0.40),  # 25-40% skip rate
        2: (0.15, 0.25),
        3: (0.05, 0.15),
        4: (0.02, 0.10),
        5: (0.00, 0.05),
    }

    def should_skip(self, chapter: int) -> bool:
        """Decide whether to skip this message."""
        min_rate, max_rate = self.SKIP_RATES[chapter]
        skip_probability = random.uniform(min_rate, max_rate)
        return random.random() < skip_probability
```
- **ACs**: AC-FR004-001, AC-FR004-002, AC-FR004-003

#### T5.2: Integrate Skip Logic with Handler
- **File**: `nikita/agents/text/handler.py` (update T4.2)
- **Content**:
  - Check skip decision before generating response
  - Log skipped messages for analytics
  - Store skip state so next message processes normally

---

### US-6: User Fact Learning (P2)

**Tasks**:

#### T6.1: Create FactExtractor Class
- **File**: `nikita/agents/text/facts.py`
- **Content**:
```python
class FactExtractor:
    """Extract facts from user messages using LLM analysis."""

    async def extract_facts(
        self,
        user_message: str,
        nikita_response: str,
        existing_facts: list[str],
    ) -> list[ExtractedFact]:
        """Use LLM to identify new facts about user."""
```
- **ACs**: AC-FR008-001, AC-FR008-002, AC-FR008-003

#### T6.2: Create extract_user_fact Tool
- **File**: `nikita/agents/text/tools.py` (update T2.2)
- **Content**:
```python
@agent.tool
async def note_user_fact(ctx: RunContext[NikitaDeps], fact: str, confidence: float) -> str:
    """Store a new fact learned about the user."""
    await ctx.deps.memory.add_user_fact(fact, confidence)
    return f"Noted: {fact}"
```

#### T6.3: Integrate Fact Extraction Post-Response
- **File**: `nikita/agents/text/handler.py` (update)
- **Content**:
  - After response generated, run fact extraction
  - Store extracted facts to memory

---

## Data Model Additions

### No Schema Changes Required

Existing models support all US-1 through US-6:
- `User.chapter` - chapter-based behavior
- `User.last_interaction_at` - timing decisions
- `User.game_status` - conversation eligibility
- `NikitaMemory` - all memory operations
- `Conversation` model - message logging (exists)

### New Application Types (not DB)

```python
# nikita/agents/text/types.py

@dataclass
class ExtractedFact:
    fact: str
    confidence: float
    source_message: str

@dataclass
class ResponseDecision:
    should_respond: bool
    delay_seconds: int | None
    skip_reason: str | None

@dataclass
class AgentResponse:
    content: str
    facts_extracted: list[ExtractedFact]
    timing: ResponseDecision
```

---

## File Structure

```
nikita/
├── agents/
│   ├── __init__.py
│   └── text/
│       ├── __init__.py          # Factory function (T1.4)
│       ├── agent.py             # NikitaTextAgent (T1.3, T2.1, T3.1)
│       ├── deps.py              # NikitaDeps dataclass (T1.2)
│       ├── tools.py             # Agent tools (T2.2, T6.2)
│       ├── handler.py           # MessageHandler (T4.2, T5.2, T6.3)
│       ├── timing.py            # ResponseTimer (T4.1)
│       ├── skip.py              # SkipDecision (T5.1)
│       ├── facts.py             # FactExtractor (T6.1)
│       └── types.py             # Type definitions
├── prompts/
│   ├── __init__.py
│   └── nikita_persona.py        # Persona prompt (T1.1)
└── tests/
    └── agents/
        └── text/
            ├── test_agent.py
            ├── test_chapter_behavior.py  (T3.2)
            ├── test_timing.py
            ├── test_skip.py
            └── test_facts.py
```

---

## Implementation Sequence

### Phase 1: Core Agent (P1 Stories)

```
T1.1 (persona) → T1.2 (deps) → T1.3 (agent) → T1.4 (factory)
                                    ↓
                              T2.1 (memory injection)
                                    ↓
                              T2.2 (recall tool)
                                    ↓
                              T3.1 (chapter behavior)
                                    ↓
                              T3.2 (tests)
```

**Deliverable**: Working agent with persona, memory, chapter behaviors

### Phase 2: Timing & Skip (P2 Stories)

```
T4.1 (timer) ─────┐
                  ├──→ T4.2 (handler with timing)
T5.1 (skip) ──────┘           ↓
                        T5.2 (handler with skip)
```

**Deliverable**: Handler that schedules responses with timing/skip logic

### Phase 3: Fact Learning (P2 Stories)

```
T6.1 (extractor) → T6.2 (tool) → T6.3 (integration)
```

**Deliverable**: Agent learns user facts from conversations

---

## Dependencies (External)

| Dependency | Version | Purpose |
|------------|---------|---------|
| pydantic-ai | ^0.0.15 | Agent framework |
| anthropic | ^0.41 | Claude API |
| graphiti-core | ^0.3 | Knowledge graphs |
| sqlalchemy | ^2.0 | Database ORM |

---

## Testing Strategy

### Unit Tests
- `test_nikita_persona.py` - Persona prompt generation
- `test_timing.py` - Response delay calculation
- `test_skip.py` - Skip rate compliance
- `test_facts.py` - Fact extraction accuracy

### Integration Tests
- `test_agent_e2e.py` - Full conversation flow
- `test_memory_integration.py` - Memory context injection
- `test_chapter_transitions.py` - Behavior changes across chapters

### Manual Testing
- Ch1 conversation: Verify guarded, challenging tone
- Ch3 conversation: Verify emotional vulnerability
- Ch5 conversation: Verify consistent, authentic responses
- Memory test: Share fact, verify recall in later conversation

---

## Risk Mitigations

### Risk 1: Persona Inconsistency (Score: 4.0)
**Mitigation**:
- Detailed persona doc with 50+ example responses
- Negative examples section
- Consistency testing with comparison prompts
- Review by human evaluators

### Risk 2: Memory Irrelevance (Score: 2.5)
**Mitigation**:
- Relevance threshold (0.7) before injection
- Limit to 5 most relevant memories
- Monitor hit rates in analytics

### Risk 3: Timing Feels Artificial (Score: 1.0)
**Mitigation**:
- Gaussian distribution, not uniform
- Add random jitter within ranges
- Ch4+ Nikita explains delays ("Sorry, was in a meeting")

---

## Success Criteria

| Metric | Target | Measurement |
|--------|--------|-------------|
| Response latency | < 5s (95th) | Prometheus metrics |
| Memory relevance | 80%+ | Human eval sample |
| Persona consistency | 90%+ | Blind comparison test |
| Ch1 skip rate | 25-40% | Analytics |
| Ch5 skip rate | 0-5% | Analytics |

---

## P3 Features (Deferred)

### US-7: Nikita-Initiated Conversations
- Requires Celery scheduler
- Will be implemented in 005-decay-system or separate feature

### US-8: Conversation Flow Management
- Natural endings, future hooks, callbacks
- Can be added to persona prompt as enhancement
- Lower priority than core functionality

---

## Next Steps

1. Run `/tasks` to generate tasks.md with acceptance criteria
2. Run `/audit` to verify plan completeness
3. Run `/implement` to begin TDD implementation

---

**Version**: 1.0
**Last Updated**: 2025-11-28
