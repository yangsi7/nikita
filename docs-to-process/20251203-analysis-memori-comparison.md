# Deep Analysis: Memori vs Nikita Memory Systems

**Date**: 2025-12-03
**Type**: Comparative Architecture Analysis
**Session ID**: 01FEbSsr1Ho9qCtqicaEoo1S

---

## Executive Summary

This document analyzes [Memori](https://github.com/MemoriLabs/Memori) (9.1k stars, Apache 2.0) and compares it with Nikita's current memory architecture. The goal is to identify learnings, integration opportunities, and architectural patterns that could enhance our system.

**Key Finding**: Memori excels at **zero-latency memory augmentation** and **universal database/LLM support**, while Nikita excels at **temporal knowledge graphs** and **character-aware memory processing**. These approaches are complementary rather than competitive.

---

## Part 1: Memori Architecture Deep Dive

### 1.1 Core Philosophy

Memori positions itself as "the memory fabric for enterprise AI" with three key principles:

| Principle | Description | Implementation |
|-----------|-------------|----------------|
| **LLM Agnostic** | Works with any LLM provider | Registry pattern with adapters (Anthropic, OpenAI, Google, xAI, Bedrock) |
| **Datastore Agnostic** | Any SQL/NoSQL database | Manager pattern with drivers (PostgreSQL, MySQL, SQLite, MongoDB, Supabase) |
| **Zero Latency** | No user-facing delays | Background "Advanced Augmentation" thread |

### 1.2 Memory Hierarchy

```
ENTITY (user/application)
    └── PROCESS (agent/program)
            └── SESSION (interaction group)
                    └── MEMORIES (individual facts)
```

**Critical Insight**: The **attribution model** requires explicit entity + process identification. Without it, memory creation fails:

```python
mem.attribution(entity_id="user_12345", process_id="nikita-text-agent")
```

This is fundamentally different from our approach where we implicitly scope by `user_id`.

### 1.3 Advanced Augmentation System

Memori's killer feature is **background memory enrichment** that categorizes memories into 8 types:

| Type | Description | Example |
|------|-------------|---------|
| **Attributes** | Properties of entities | "User is 28 years old" |
| **Events** | Temporal markers | "User got promoted on Dec 1" |
| **Facts** | Factual statements | "User works at Google" |
| **People** | Entity relationships | "User's sister is named Sarah" |
| **Preferences** | User settings | "User prefers dark mode" |
| **Relations** | Semantic connections | "User → works_at → Google" |
| **Rules** | Behavioral constraints | "Never discuss politics" |
| **Skills** | Acquired capabilities | "User knows Python" |

**Key Technical Detail**: This runs on a separate thread with rate limiting for free tier. Zero latency for the conversation.

### 1.4 Knowledge Graph Implementation

Memori uses a **third normal form schema with semantic triples**:

```
Subject → Predicate → Object (with temporal metadata)
```

Example: `("User", "works_at", "Google", created_at=2024-01-15)`

This enables structured queries like:
- "What do I know about User's job?"
- "When did I learn about User's family?"

### 1.5 Token Savings Claim

Memori claims **90% token savings** through intelligent context injection. Their multi-agent architecture promotes essential long-term memories to short-term storage for faster retrieval.

---

## Part 2: Nikita Memory Architecture

### 2.1 Three-Graph Temporal Architecture

```
NIKITA GRAPH                    USER GRAPH                    RELATIONSHIP GRAPH
(Her simulated life)            (What she knows about him)    (Shared history)
├── WorkProject                 ├── UserFact                  ├── Episode
├── LifeEvent                   ├── UserPreference            ├── Milestone
├── Opinion                     ├── UserPattern               ├── InsideJoke
└── Memory                      └── ...                       └── Conflict
```

**Key Advantage**: Separation of **character state** from **user knowledge** from **relationship dynamics**.

### 2.2 Processing Pipeline

```
PRE-CONVERSATION
    └── MetaPromptService.generate_system_prompt() (~200ms)
        └── Claude Haiku generates personalized prompt

DURING CONVERSATION
    └── Pure LLM conversation (no writes)

POST-CONVERSATION (8 stages, ~10-15s async)
    1. Ingestion - Load transcript
    2. Entity Extraction - Via MetaPromptService.extract_entities()
    3. Conversation Analysis - Summary, tone, key moments
    4. Thread Extraction - Unresolved topics, promises
    5. Inner Life Generation - Nikita's simulated thoughts
    6. Graph Updates - Neo4j knowledge graphs
    7. Summary Rollups - Daily summaries
    8. Cache Invalidation - Clear stale prompts
```

### 2.3 System Prompt Architecture (6 Layers)

| Layer | Purpose | Tokens | Update Frequency |
|-------|---------|--------|------------------|
| **L1: Core Identity** | Nikita's personality | ~400 | Static |
| **L2: Current Moment** | Time awareness | ~300 | Per-request |
| **L3: Relationship State** | Chapter, score, trend | ~500 | Per-request |
| **L4: Conversation History** | Summaries, threads | ~1800 | Daily |
| **L5: Knowledge & Inner Life** | Facts, thoughts | ~1000 | Per-session |
| **L6: Response Guidelines** | Behavioral tuning | ~500 | Per-chapter |

**Total Budget**: ~4500 tokens (within 5000 limit)

### 2.4 Meta-Prompt Architecture (New Dec 2025)

Replaced static f-string templates with Claude Haiku meta-prompts:

```python
# Before: Static template
def _layer1_core_identity(self) -> str:
    return """You are Nikita, 23..."""

# After: Intelligent generation
async def generate_system_prompt(self, user_id: UUID) -> GeneratedPrompt:
    context = await self._load_context(user_id)
    meta_prompt = self._format_template("system_prompt.meta.md", context)
    result = await self._agent.run(meta_prompt)  # Claude Haiku
```

---

## Part 3: Comparative Analysis

### 3.1 Feature Matrix

| Capability | Memori | Nikita | Winner |
|------------|--------|--------|--------|
| **Zero-latency augmentation** | Yes (threaded) | No (post-conversation) | Memori |
| **Temporal awareness** | Yes (triples) | Yes (Graphiti) | Tie |
| **Character simulation** | No | Yes (inner life) | Nikita |
| **Multi-provider LLM** | Yes (6 providers) | Yes (Anthropic/OpenAI) | Memori |
| **Multi-database** | Yes (10+ adapters) | Supabase + Neo4j | Memori |
| **Session management** | Explicit API | 15-min timeout | Memori |
| **Memory categorization** | 8 types | 3 graphs | Memori |
| **Relationship scoring** | No | Yes (4 metrics) | Nikita |
| **Game mechanics integration** | No | Yes (chapters, boss) | Nikita |
| **Vice personalization** | No | Yes (6 categories) | Nikita |

### 3.2 Architectural Patterns Comparison

#### Memory Scoping

**Memori**: Explicit triple: `(entity_id, process_id, session_id)`
```python
mem.attribution(entity_id="user_123", process_id="nikita")
mem.new_session()
```

**Nikita**: Implicit by `user_id`, explicit by `graph_type`
```python
memory = NikitaMemory(user_id)
await memory.add_episode(content, source, graph_type="relationship")
```

**Learning**: Memori's explicit attribution is cleaner for multi-agent systems. We could add a `process_id` dimension for voice vs text agents.

#### Memory Write Timing

**Memori**: Background thread during conversation (zero-latency)
```
User message → LLM response → [Thread: Augmentation happens here]
                            ↓
              User sees response immediately
```

**Nikita**: Post-conversation pipeline (10-15s async after session ends)
```
User message → LLM response → ... → Session ends → [Pipeline runs]
```

**Learning**: Memori's approach is better for real-time fact accumulation. Our approach is better for holistic analysis (emotional tone, key moments, summaries).

**Hybrid Opportunity**: Run **lightweight fact extraction** in background during conversation, save **deep analysis** for post-processing.

### 3.3 What We Can Learn

#### 1. Zero-Latency Fact Extraction

**Current**: We wait until session ends to extract any facts.

**Opportunity**: Like Memori, run a background thread during conversation:
```python
async def background_augment(message: str, user_id: UUID):
    """Fire-and-forget fact extraction during conversation."""
    facts = await quick_extract_facts(message)  # < 500ms
    for fact in facts:
        await memory.add_user_fact_fast(fact)  # Non-blocking
```

**Benefit**: Immediate memory updates without user delay.

#### 2. Explicit Attribution Model

**Current**: Single-user scope with implicit graph routing.

**Opportunity**: Add process dimension for multi-agent clarity:
```python
class NikitaMemory:
    def __init__(
        self,
        user_id: str,
        process_id: str = "text-agent",  # NEW: explicit agent source
    ):
```

**Benefit**: Clear provenance for voice vs text agent memories.

#### 3. Memory Type Taxonomy

**Current**: Free-form facts with implicit typing.

**Opportunity**: Adopt Memori's 8-type categorization:
```python
class MemoryType(Enum):
    ATTRIBUTE = "attribute"   # Properties
    EVENT = "event"           # Temporal markers
    FACT = "fact"             # Statements
    PERSON = "person"         # Relationships
    PREFERENCE = "preference" # User settings
    RELATION = "relation"     # Semantic links
    RULE = "rule"             # Constraints
    SKILL = "skill"           # Capabilities
```

**Benefit**: Structured retrieval, better context ranking.

#### 4. Session Management API

**Current**: 15-minute timeout detection via SessionDetector.

**Opportunity**: Explicit session control like Memori:
```python
# Explicit session boundaries
await memory.new_session()
session_id = memory.session_id
await memory.set_session(old_session_id)  # Resume
```

**Benefit**: Cleaner session tracking, cross-platform consistency.

#### 5. Multi-Agent Memory Promotion

**Current**: All memories equal; context selection at prompt time.

**Opportunity**: Memori's "memory promotion" pattern:
- Short-term: Recent interactions (7-30 days)
- Long-term: Important insights (permanent)
- Promoted: Essential memories surfaced to short-term

```python
# Background task: Promote important memories
async def promote_memories(user_id: UUID):
    long_term = await memory.get_long_term(user_id)
    for mem in long_term:
        if mem.importance_score > THRESHOLD:
            await memory.promote_to_short_term(mem)
```

**Benefit**: Better context selection, reduced token usage.

---

## Part 4: Integration Opportunities

### 4.1 Direct Integration: Use Memori as Backend

**Feasibility**: HIGH
**Effort**: MEDIUM

Memori supports Pydantic AI (which Nikita uses) and Supabase (which Nikita uses).

```python
from memori import Memori
from pydantic_ai import Agent

# Initialize Memori with Supabase
mem = Memori(conn=supabase_session).config.storage.build()
agent = mem.pydantic_ai.register(pydantic_agent)

# Attribution per user + agent
mem.attribution(entity_id=user.id, process_id="nikita-text")
```

**Pros**:
- Automatic memory capture
- Zero-latency augmentation
- Database-agnostic
- 8-type memory categorization

**Cons**:
- Lose our three-graph separation
- Lose temporal knowledge graph (Graphiti)
- Rate limiting on free tier
- External dependency for core feature

**Recommendation**: NOT for core replacement. Consider for **secondary fact storage** alongside Graphiti.

### 4.2 Hybrid Architecture: Memori + Graphiti

**Feasibility**: HIGH
**Effort**: HIGH

Use Memori for **real-time fact capture**, Graphiti for **temporal knowledge graphs**.

```
┌─────────────────────────────────────────────────────────────────┐
│                     MEMORY ARCHITECTURE                         │
├────────────────────────────┬────────────────────────────────────┤
│        MEMORI (Fast)       │          GRAPHITI (Deep)           │
├────────────────────────────┼────────────────────────────────────┤
│ - Zero-latency capture     │ - Temporal relationships           │
│ - 8-type categorization    │ - Three-graph separation           │
│ - Short-term storage       │ - Long-term knowledge              │
│ - Real-time augmentation   │ - Complex queries                  │
│ - Supabase backend         │ - Neo4j Aura backend               │
├────────────────────────────┴────────────────────────────────────┤
│                     SYNC LAYER (pg_cron)                        │
│  Every 5 min: Memori short-term → Graphiti for consolidation    │
└─────────────────────────────────────────────────────────────────┘
```

**Data Flow**:
1. During conversation: Memori captures facts (zero-latency)
2. Session ends: Memori short-term → Graphiti (deep processing)
3. Next conversation: Query both; Graphiti for context, Memori for recent facts

### 4.3 Pattern Adoption: Implement Memori Patterns

**Feasibility**: MEDIUM
**Effort**: LOW-MEDIUM

Adopt Memori's best patterns without using their library.

**Immediate Wins (Low Effort)**:

1. **Background Fact Extraction** - During conversation:
```python
# In message_handler.py, after LLM response
asyncio.create_task(background_fact_extract(message, user_id))
```

2. **Memory Type Enum** - Structured categorization:
```python
class MemoryType(Enum):
    ATTRIBUTE = "attribute"
    EVENT = "event"
    FACT = "fact"
    ...
```

3. **Explicit Session API** - Better session control:
```python
await memory.new_session()
await memory.set_session(session_id)
```

**Medium-Term (Medium Effort)**:

4. **Memory Promotion System** - Background memory curation:
```python
async def promote_important_memories(user_id: UUID):
    # Score memories by importance
    # Promote high-value to "promoted" category
    # Demote stale memories
```

5. **Multi-Process Attribution** - Voice vs Text clarity:
```python
memory.attribution(user_id=user_id, process_id="voice-agent")
```

---

## Part 5: Recommendations

### 5.1 Immediate Actions (This Sprint)

| Priority | Action | Effort | Impact |
|----------|--------|--------|--------|
| P1 | Add `MemoryType` enum to fact extraction | 2h | Better organization |
| P1 | Add background fact extraction during conversation | 4h | Zero-latency like Memori |
| P2 | Add `process_id` to NikitaMemory | 2h | Multi-agent clarity |

### 5.2 Near-Term (Next 2 Sprints)

| Priority | Action | Effort | Impact |
|----------|--------|--------|--------|
| P2 | Implement memory promotion system | 8h | Better context selection |
| P2 | Add explicit session management API | 4h | Cleaner session tracking |
| P3 | Evaluate Memori as secondary storage | 8h | Potential token savings |

### 5.3 Future Consideration

| Action | When | Why |
|--------|------|-----|
| Full Memori integration | After v1 launch | Consider if Graphiti proves insufficient |
| Custom memory LLM | Never | Memori's approach of using main LLM is better |
| Abandon Graphiti | Never | Temporal knowledge is our differentiator |

---

## Part 6: Conclusion

**Memori** is an impressive open-source memory system with excellent zero-latency architecture and database flexibility. However, it's designed for **generic enterprise AI** rather than **character-based games**.

**Nikita's memory system** is purpose-built for our use case:
- Three-graph separation (character/user/relationship)
- Temporal knowledge for narrative consistency
- Game mechanics integration (chapters, scoring)
- Character inner life simulation

**Best Path Forward**: Adopt Memori's best **patterns** (zero-latency, memory types, session management) while keeping our **infrastructure** (Graphiti + Neo4j + Supabase).

### Key Learnings to Implement

1. **Background fact extraction** during conversations (not just after)
2. **Memory type taxonomy** for structured categorization
3. **Explicit session management** API
4. **Memory promotion** for better context ranking

### What NOT to Do

1. Replace Graphiti with Memori's SQL-based approach
2. Abandon three-graph architecture
3. Add Memori as external dependency for core features

---

## Appendix: Memori Code Snippets for Reference

### Initialization
```python
from memori import Memori
mem = Memori(conn=db_session_factory)
mem.config.storage.build()  # Create schema
```

### Attribution
```python
mem.attribution(entity_id="user_123", process_id="nikita-text")
```

### Session Management
```python
mem.new_session()
session_id = mem.config.session_id
mem.set_session(old_session_id)
```

### Recall
```python
facts = mem.recall(query="user's job", limit=5)
```

### Integration with Pydantic AI
```python
from pydantic_ai import Agent
agent = Agent(model="claude-3-5-sonnet")
mem.pydantic_ai.register(agent)  # Automatic memory capture
```

---

*Document prepared for Nikita architecture review. Contact: engineering@nikita.game*
