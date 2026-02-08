> **SUPERSEDED**: This spec has been replaced by Spec 042. See specs/042-unified-pipeline/spec.md for current requirements.

# Spec 021: Hierarchical Prompt Composition

**Version**: 1.0.0
**Created**: 2026-01-12
**Status**: DRAFT
**Dependencies**: None (Foundation spec)
**Dependents**: 022, 023, 024, 025, 026, 027, 028

---

## Overview

### Problem Statement

The current MetaPromptService generates system prompts synchronously at conversation start, causing:
1. **Latency issues**: Context loading, memory queries, and prompt assembly add 500-2000ms to response time
2. **Limited personalization**: Static prompt assembly doesn't account for Nikita's simulated life events, emotional state, or situational context
3. **No pre-computation**: Every conversation starts fresh, repeating work that could be done in advance
4. **Monolithic prompts**: Single prompt template makes it hard to modulate different aspects independently

### Solution

Implement a **Hierarchical Prompt Composition** system with 6 layers, where most computation happens in **POST-PROCESSING** (after each conversation ends) to prepare a ready-to-use context package for the next conversation.

### Key Insight

> "Most work should be done in POST-PROCESSING to prepare for NEXT conversation. Latency managed by pre-computing layers asynchronously."

---

## User Stories

### US-1: Pre-computed Context Packages
**As** the Nikita system,
**I want** to pre-compute context packages after each conversation ends,
**So that** the next conversation can start with minimal latency (<150ms for context injection).

**Priority**: P1 (Critical)

**Acceptance Criteria**:
- AC-1.1: Post-processing pipeline runs asynchronously within 15 minutes of conversation end
- AC-1.2: Context package stored and retrievable by user_id
- AC-1.3: Context injection at conversation start completes in <150ms
- AC-1.4: System gracefully handles missing context package (generates minimal context synchronously)

### US-2: Base Personality Layer (Layer 1)
**As** the prompt composer,
**I want** a static base personality layer that defines core Nikita traits,
**So that** her fundamental identity remains consistent across all interactions.

**Priority**: P1 (Critical)

**Acceptance Criteria**:
- AC-2.1: Base personality template loaded from configuration (~2000 tokens)
- AC-2.2: Template includes: core traits, values, speaking style, backstory essentials
- AC-2.3: Layer never changes per-user (universal Nikita identity)
- AC-2.4: Layer can be versioned and A/B tested

### US-3: Chapter Layer (Layer 2)
**As** the prompt composer,
**I want** chapter-specific behavioral overlays,
**So that** Nikita's openness and availability evolve through game progression.

**Priority**: P1 (Critical)

**Acceptance Criteria**:
- AC-3.1: Chapter layer pre-computed when chapter advances
- AC-3.2: Layer includes: intimacy level, disclosure patterns, response behaviors
- AC-3.3: Chapter 1→5 progression shows measurable behavioral differences
- AC-3.4: Layer stored in context package (~200-400 tokens)

### US-4: Emotional State Layer (Layer 3)
**As** the prompt composer,
**I want** emotional state computed from life simulation and conversation history,
**So that** Nikita's mood authentically affects her responses.

**Priority**: P1 (Critical)

**Acceptance Criteria**:
- AC-4.1: Emotional state computed in post-processing from life events + recent conversations
- AC-4.2: State includes 4 dimensions: arousal, valence, dominance, intimacy
- AC-4.3: State affects response tone, timing, and content selection
- AC-4.4: Layer stored in context package (~100-200 tokens)

### US-5: Situation Layer (Layer 4)
**As** the prompt composer,
**I want** situational context pre-computed for likely scenarios,
**So that** Nikita can handle morning check-ins, evening conversations, and post-gap situations appropriately.

**Priority**: P2 (Important)

**Acceptance Criteria**:
- AC-5.1: Situation layer identifies conversation context (morning, evening, after-gap, mid-conversation)
- AC-5.2: Layer includes scenario-specific behavioral nudges
- AC-5.3: Situation computed at conversation start based on time and gap duration
- AC-5.4: Layer provides meta-instructions, not exact responses (~100-200 tokens)

### US-6: Context Injection Layer (Layer 5)
**As** the prompt composer,
**I want** real-time context injection from stored packages,
**So that** user-specific knowledge is available without query latency.

**Priority**: P1 (Critical)

**Acceptance Criteria**:
- AC-6.1: Context package loaded from storage in <50ms
- AC-6.2: Package includes: user facts, relationship history, active threads, summaries
- AC-6.3: Total injection latency <150ms including parsing
- AC-6.4: Fallback to minimal context if package unavailable

### US-7: On-the-Fly Modifications (Layer 6)
**As** the prompt composer,
**I want** real-time modifications during conversation,
**So that** mood shifts and contextual memory retrieval can happen dynamically.

**Priority**: P2 (Important)

**Acceptance Criteria**:
- AC-7.1: Mood shift detection triggers Layer 6 updates mid-conversation
- AC-7.2: Memory retrieval (Graphiti) available on-demand during generation
- AC-7.3: Layer 6 modifications don't exceed 200ms per retrieval
- AC-7.4: System tracks which modifications were applied for debugging

### US-8: Post-Processing Pipeline
**As** the system,
**I want** an async post-processing pipeline that runs after each conversation,
**So that** context packages are always ready for the next conversation.

**Priority**: P1 (Critical)

**Acceptance Criteria**:
- AC-8.1: Pipeline triggered automatically after conversation ends
- AC-8.2: Pipeline steps: update graphs → generate summaries → simulate life events → compute emotional state → compose layers → store package
- AC-8.3: Pipeline completes within 15 minutes (async, non-blocking)
- AC-8.4: Pipeline failures logged with retry mechanism

---

## Functional Requirements

### FR-001: Prompt Layer Architecture
The system SHALL compose prompts from 6 hierarchical layers:

| Layer | Name | Computation | Token Budget | Source |
|-------|------|-------------|--------------|--------|
| 1 | Base Personality | Static | ~2000 | Config file |
| 2 | Chapter Layer | Pre-computed | ~300 | Chapter state |
| 3 | Emotional State | Pre-computed | ~150 | Life sim + history |
| 4 | Situation Layer | Semi-realtime | ~150 | Time + gap analysis |
| 5 | Context Injection | Real-time | ~500 | Stored package |
| 6 | On-the-Fly | During conversation | ~200 | Dynamic retrieval |

**Total token budget**: ~3300 tokens for system prompt

### FR-002: Post-Processing Pipeline
The system SHALL execute these steps asynchronously after each conversation:

1. **Update Knowledge Graphs** (Graphiti)
   - User facts extracted from conversation
   - Relationship events logged
   - Entity resolution performed

2. **Generate Summaries**
   - Daily summary updated
   - Weekly summary updated (if applicable)
   - Thread status updated

3. **Simulate Life Events** (Spec 022 dependency)
   - Generate tomorrow's events
   - Update Nikita's calendar/state

4. **Compute Emotional State** (Spec 023 dependency)
   - Calculate 4-dimensional state
   - Factor in life events + conversation tone

5. **Compose Prompt Layers**
   - Assemble Layers 2-4 from computed state
   - Validate token budgets

6. **Store Context Package**
   - Serialize to storage (Redis/Supabase)
   - Set TTL (24 hours)

### FR-003: Context Package Schema
The context package SHALL include:

```python
class ContextPackage(BaseModel):
    user_id: str
    created_at: datetime
    expires_at: datetime

    # Pre-computed layers
    chapter_layer: str  # Layer 2
    emotional_state_layer: str  # Layer 3
    situation_hints: dict  # For Layer 4 computation

    # Context data for Layer 5
    user_facts: list[str]  # Top 20 relevant facts
    relationship_events: list[str]  # Recent 10 events
    active_threads: list[dict]  # Unresolved conversation threads
    today_summary: str | None
    week_summaries: list[str]

    # Metadata
    nikita_mood: dict  # arousal, valence, dominance, intimacy
    nikita_energy: float  # 0.0-1.0
    life_events_today: list[str]  # What happened to Nikita today

    # Version for cache invalidation
    version: str
```

### FR-004: Real-Time Composition
At conversation start, the system SHALL:

1. Load context package (< 50ms)
2. Load base personality (cached, < 10ms)
3. Compute situation layer from current time/gap (< 20ms)
4. Assemble full prompt (< 30ms)
5. Validate token count (< 10ms)

**Total target**: < 150ms

### FR-005: Graceful Degradation
If context package unavailable, the system SHALL:

1. Use base personality + chapter layer only
2. Generate minimal context synchronously (user name, chapter, score)
3. Log degradation event for monitoring
4. Schedule immediate post-processing

---

## Non-Functional Requirements

### NFR-001: Latency
- Context injection: P99 < 150ms
- On-the-fly retrieval: P99 < 200ms per query
- Post-processing: Complete within 15 minutes

### NFR-002: Reliability
- Context package availability: 99.5%
- Post-processing success rate: 99%
- Graceful degradation: Always available (may be degraded)

### NFR-003: Storage
- Context package size: < 50KB per user
- Retention: 24 hours (auto-expire)
- Storage backend: Redis (preferred) or Supabase JSONB

### NFR-004: Observability
- Metrics: composition_latency_ms, package_hit_rate, layer_token_counts
- Logs: Each layer composition logged with tokens used
- Alerts: Degradation rate > 5% triggers alert

---

## Technical Design

### Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    POST-PROCESSING SERVICE                       │
├─────────────────────────────────────────────────────────────────┤
│  PostProcessingPipeline                                          │
│    ├── GraphUpdater (Graphiti integration)                      │
│    ├── SummaryGenerator (daily/weekly)                          │
│    ├── LifeSimulator (Spec 022)                                 │
│    ├── EmotionalStateComputer (Spec 023)                        │
│    ├── LayerComposer (Layers 2-4)                               │
│    └── PackageStore (Redis/Supabase)                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ async (15 min)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CONTEXT PACKAGE STORE                         │
│                    (Redis TTL 24h / Supabase JSONB)             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ load (<50ms)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PROMPT COMPOSER SERVICE                       │
├─────────────────────────────────────────────────────────────────┤
│  HierarchicalPromptComposer                                      │
│    ├── Layer1Loader (static, cached)                            │
│    ├── Layer2Injector (from package)                            │
│    ├── Layer3Injector (from package)                            │
│    ├── Layer4Computer (real-time situation)                     │
│    ├── Layer5Injector (from package)                            │
│    ├── Layer6Handler (on-demand during conversation)            │
│    └── TokenValidator (budget enforcement)                       │
└─────────────────────────────────────────────────────────────────┘
```

### File Structure

```
nikita/
├── context/
│   ├── __init__.py
│   ├── composer.py          # HierarchicalPromptComposer
│   ├── layers/
│   │   ├── __init__.py
│   │   ├── base_personality.py    # Layer 1
│   │   ├── chapter.py             # Layer 2
│   │   ├── emotional_state.py     # Layer 3
│   │   ├── situation.py           # Layer 4
│   │   ├── context_injection.py   # Layer 5
│   │   └── on_the_fly.py          # Layer 6
│   ├── package.py           # ContextPackage model
│   └── store.py             # PackageStore (Redis/Supabase)
├── post_processing/
│   ├── __init__.py
│   ├── pipeline.py          # PostProcessingPipeline
│   ├── graph_updater.py     # Graphiti integration
│   ├── summary_generator.py # Daily/weekly summaries
│   └── layer_composer.py    # Pre-compose Layers 2-4
```

### Integration Points

| Component | Integration | Direction |
|-----------|-------------|-----------|
| MetaPromptService | Replaced by HierarchicalPromptComposer | Replace |
| ConversationRepository | Triggers post-processing after save | Outbound |
| Graphiti | Graph updates in post-processing | Bidirectional |
| LifeSimulator (022) | Called by post-processing pipeline | Outbound |
| EmotionalStateEngine (023) | Called by post-processing pipeline | Outbound |
| BehavioralMetaInstructions (024) | Consumed by Layer 4 | Inbound |

---

## API Contracts

### Internal APIs

```python
class HierarchicalPromptComposer:
    async def compose(
        self,
        user_id: str,
        conversation_context: dict | None = None
    ) -> ComposedPrompt:
        """
        Compose full system prompt from 6 layers.

        Args:
            user_id: User identifier
            conversation_context: Optional current conversation state

        Returns:
            ComposedPrompt with full text and metadata
        """
        pass

    async def get_layer_6_modification(
        self,
        user_id: str,
        trigger: str,  # "mood_shift" | "memory_retrieval"
        context: dict
    ) -> str:
        """
        Get on-the-fly modification during conversation.
        """
        pass


class PostProcessingPipeline:
    async def process(
        self,
        user_id: str,
        conversation_id: str
    ) -> ProcessingResult:
        """
        Run full post-processing pipeline.

        Called after conversation ends.
        """
        pass


class PackageStore:
    async def get(self, user_id: str) -> ContextPackage | None:
        """Load context package (<50ms target)."""
        pass

    async def set(
        self,
        user_id: str,
        package: ContextPackage,
        ttl_hours: int = 24
    ) -> None:
        """Store context package with TTL."""
        pass
```

### Data Models

```python
from pydantic import BaseModel
from datetime import datetime


class ComposedPrompt(BaseModel):
    """Output of HierarchicalPromptComposer."""
    full_text: str
    total_tokens: int
    layer_breakdown: dict[str, int]  # layer_name -> token_count
    package_version: str | None
    degraded: bool = False  # True if using fallback


class ProcessingResult(BaseModel):
    """Output of PostProcessingPipeline."""
    user_id: str
    conversation_id: str
    success: bool
    steps_completed: list[str]
    errors: list[str]
    duration_ms: int
    package_stored: bool


class EmotionalState(BaseModel):
    """4-dimensional emotional state."""
    arousal: float  # 0.0-1.0 (tired → energetic)
    valence: float  # 0.0-1.0 (sad → happy)
    dominance: float  # 0.0-1.0 (submissive → dominant)
    intimacy: float  # 0.0-1.0 (guarded → vulnerable)
```

---

## Migration Strategy

### Phase 1: Parallel Implementation
1. Build HierarchicalPromptComposer alongside existing MetaPromptService
2. Add feature flag `use_hierarchical_composer`
3. Shadow-run both, compare outputs

### Phase 2: Post-Processing Pipeline
1. Implement pipeline with stub dependencies (022, 023)
2. Add trigger after conversation save
3. Monitor pipeline success rate

### Phase 3: Switch Primary
1. Enable `use_hierarchical_composer` for 10% users
2. Monitor latency, quality metrics
3. Gradual rollout to 100%

### Phase 4: Deprecate MetaPromptService
1. Remove feature flag
2. Archive MetaPromptService code
3. Update documentation

---

## Testing Strategy

### Unit Tests
- Each layer composer: input → output validation
- Token budget enforcement
- Graceful degradation logic

### Integration Tests
- Full composition flow with mock package
- Post-processing pipeline end-to-end
- Package store operations

### Performance Tests
- Context injection latency P99 < 150ms
- Package load P99 < 50ms
- Post-processing duration < 15 min

### E2E Tests
- Conversation → post-processing → next conversation flow
- Degradation scenario (no package available)
- Layer 6 modification during conversation

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Context injection latency | P99 < 150ms | Prometheus histogram |
| Package hit rate | > 95% | Counter ratio |
| Post-processing success | > 99% | Error rate |
| Layer token compliance | 100% within budget | Validation logs |
| Degradation rate | < 5% | Counter |

---

## Open Questions

1. **Redis vs Supabase JSONB**: Which storage backend for context packages? Redis is faster but adds infrastructure; Supabase JSONB is simpler but slower.
   - **Recommendation**: Start with Supabase JSONB, migrate to Redis if latency is an issue.

2. **Layer 6 scope**: How much modification is allowed during conversation? Should it include personality drift?
   - **Recommendation**: Limit to mood shifts and memory retrieval; personality drift is spec 024 scope.

3. **Package invalidation**: When should packages be invalidated early (before 24h TTL)?
   - **Recommendation**: Invalidate on chapter change, game-over, or user preference update.

---

## Version History

### v1.0.0 - 2026-01-12
- Initial specification
- 8 user stories, 5 FRs, 4 NFRs
- Technical design with 6-layer architecture
