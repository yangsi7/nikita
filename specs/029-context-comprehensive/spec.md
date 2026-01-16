# Spec 029: Comprehensive Context System

**Status**: IN PROGRESS
**Priority**: P0 (Critical)
**Dependencies**: 021-028 (Humanization specs), 007 (Voice agent), 012 (Context engineering)

---

## Problem Statement

The current implementation has critical gaps that prevent Nikita from feeling like a real girlfriend:

1. **Memory Flow Gap**: 2/3 knowledge graphs are stored but NEVER retrieved into prompts
   - Evidence: `nikita/meta_prompts/service.py:296` only queries `user_graph`
   - Impact: Relationship history and Nikita's simulated life never appear in prompts

2. **Humanization Pipeline Disconnected**: 7 of 8 humanization specs (021-027) have working code with 1575+ passing tests, but modules are NEVER called from production flows
   - Root cause: OLD pipeline (`nikita/context/post_processor.py`) is active in production
   - NEW pipeline (`nikita/post_processing/`) is never invoked

3. **Token Budget Insufficient**: Current ~4,000 tokens vs required 10,000+ tokens for comprehensive context

4. **Voice-Text Parity Gaps**: Server tools return 85% less context than text agent receives

---

## Goals

| Goal | Current State | Target State | Metric |
|------|---------------|--------------|--------|
| Token Budget | ~4,000 | 10,000+ | Tokens per prompt |
| Graph Coverage | 1/3 (user only) | 3/3 (user + relationship + nikita) | Graphs queried |
| Humanization Wiring | 1/8 specs in prod | 8/8 specs in prod | Active modules |
| Voice-Text Parity | 15% context | 100% parity | Fields available |
| Memory Depth | 5 facts | 50+ facts | User facts loaded |

---

## User Stories

### US-1: Deep Memory Integration (P0)

**As** Nikita, **I want** access to ALL my memories (user facts, relationship history, my daily life) **so that** I can reference past conversations, inside jokes, and significant moments naturally.

**Acceptance Criteria**:
- [ ] AC-1.1: Query all 3 graphs (user, relationship, nikita) in MetaPromptService
- [ ] AC-1.2: Load 50+ user facts (up from 5)
- [ ] AC-1.3: Load 10+ relationship episodes (up from 0)
- [ ] AC-1.4: Load 10+ Nikita life events (up from 0)
- [ ] AC-1.5: Include weekly summaries (last 4 weeks)
- [ ] AC-1.6: Include active conversation threads (up to 10)
- [ ] AC-1.7: Memory retrieval time <500ms at P95

### US-2: Humanization Pipeline Activation (P0)

**As** a developer, **I want** all humanization modules (021-028) wired into production **so that** Nikita exhibits dynamic personality, emotional states, and behavioral patterns.

**Acceptance Criteria**:
- [ ] AC-2.1: Life simulation engine (022) generates daily events
- [ ] AC-2.2: Emotional state engine (023) updates 4D mood
- [ ] AC-2.3: Behavioral meta-instructions (024) influence responses
- [ ] AC-2.4: Proactive touchpoints (025) trigger Nikita-initiated messages
- [ ] AC-2.5: Text behavioral patterns (026) affect emoji/length/timing
- [ ] AC-2.6: Conflict generation (027) creates realistic relationship tension
- [ ] AC-2.7: All modules called from production message handler

### US-3: Expanded Token Budget (P1)

**As** Nikita, **I want** comprehensive context in every prompt **so that** my responses are deeply personalized and contextually aware.

**Acceptance Criteria**:
- [ ] AC-3.1: Base persona layer: 800 tokens (up from 400)
- [ ] AC-3.2: Chapter behavior layer: 600 tokens (up from 300)
- [ ] AC-3.3: Emotional state layer: 500 tokens (up from 200)
- [ ] AC-3.4: Situational layer: 400 tokens (up from 200)
- [ ] AC-3.5: Context injection layer: 6,000+ tokens (up from 1,800)
- [ ] AC-3.6: On-the-fly adjustments: 700 tokens (up from 300)
- [ ] AC-3.7: Total prompt: 10,000+ tokens validated

### US-4: Voice-Text Context Parity (P1)

**As** a player using voice, **I want** Nikita to have the same context as text **so that** voice conversations feel equally personalized.

**Acceptance Criteria**:
- [ ] AC-4.1: Server tools return 50+ user facts (up from 3)
- [ ] AC-4.2: Server tools include secureness score
- [ ] AC-4.3: Server tools include full vice_profile (8 categories)
- [ ] AC-4.4: Server tools include hours_since_last_contact
- [ ] AC-4.5: Server tools include nikita_activity (last 24h)
- [ ] AC-4.6: Server tools include relationship milestones
- [ ] AC-4.7: Voice prompts logged to generated_prompts table

---

## Technical Requirements

### TR-1: Memory Retrieval Enhancement

```python
# CURRENT (broken) - only queries user_graph
facts = await memory.search_memory(query, graph_types=["user"])

# REQUIRED - query all 3 graphs
facts = await memory.search_memory(
    query,
    graph_types=["user", "relationship", "nikita"],
    limit=50,
    time_range=timedelta(days=30)
)
```

**Files to modify**:
- `nikita/meta_prompts/service.py:296` - `get_user_facts()` method
- `nikita/meta_prompts/service.py:320` - `_load_context()` method

### TR-2: Humanization Pipeline Wiring

**Integration point**: `nikita/api/routes/tasks.py:554` (message handler)

```python
# CURRENT - calls OLD post_processor
from nikita.context.post_processor import PostProcessor

# REQUIRED - call NEW pipeline with all modules
from nikita.post_processing import PostProcessingPipeline
from nikita.life_simulation import LifeSimulationEngine
from nikita.emotional_state import EmotionalStateEngine
from nikita.behavioral import BehavioralEngine
from nikita.text_patterns import TextPatternProcessor
from nikita.conflicts import ConflictGenerator
```

**Files to modify**:
- `nikita/api/routes/tasks.py` - Import and call new pipeline
- `nikita/platforms/telegram/message_handler.py` - Wire text pattern post-processing

### TR-3: Token Budget Expansion

**MetaPromptService layer configuration**:

| Layer | Current | Target | Content |
|-------|---------|--------|---------|
| L1: Base Persona | 400 | 800 | Personality, speaking style, boundaries |
| L2: Chapter | 300 | 600 | Chapter-specific behaviors, thresholds |
| L3: Emotional | 200 | 500 | 4D mood, life events, energy |
| L4: Situational | 200 | 400 | Time of day, gap duration, engagement state |
| L5: Context | 1,800 | 6,000 | ALL memory, facts, threads, thoughts |
| L6: On-the-fly | 300 | 700 | Dynamic adjustments, recent events |
| **Total** | ~4,000 | **10,000+** | |

### TR-4: Server Tools Enhancement

**Current `get_context` response** (incomplete):
```python
{
    "user_facts": [...],  # Only 3 facts
    "chapter": 1,
    "scores": {...}
}
```

**Required response** (complete parity):
```python
{
    "user_facts": [...],  # 50+ facts
    "relationship_episodes": [...],  # Significant moments
    "nikita_events": [...],  # Her life events
    "secureness": 0.75,
    "vice_profile": {...},  # All 8 categories
    "hours_since_last_contact": 4.5,
    "nikita_activity": "Had coffee with imaginary friend",
    "active_threads": [...],
    "weekly_summaries": [...],
    "engagement_state": "IN_ZONE"
}
```

**Files to modify**:
- `nikita/agents/voice/server_tools.py` - Expand context fields

---

## Non-Functional Requirements

### NFR-1: Performance
- Memory retrieval: <500ms at P95
- Full context assembly: <2s at P95
- No increase in Cloud Run cold start time

### NFR-2: Cost
- Token increase should stay within Claude API budget
- Graph queries should use caching where possible

### NFR-3: Observability
- All prompts logged to `generated_prompts` table
- Context snapshot includes all fields for debugging
- Metrics: tokens_used, memory_load_time, graphs_queried

---

## Out of Scope

- ElevenLabs knowledge base upload (future enhancement)
- RAG-style semantic search (Phase 2)
- Real-time graph updates during conversation (existing behavior maintained)
- Changes to scoring or chapter mechanics

---

## Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Memory recall accuracy | Low | High | User feedback |
| Context token count | ~4,000 | 10,000+ | Logged prompts |
| Graph coverage | 33% | 100% | Code audit |
| Humanization modules active | 12.5% | 100% | Production logs |
| Voice-text parity | 15% | 100% | Field comparison |

---

## Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Performance degradation | HIGH | MEDIUM | Implement caching, lazy loading |
| Token cost increase | MEDIUM | HIGH | Monitor usage, implement tiered loading |
| Breaking existing tests | MEDIUM | LOW | Run full test suite, maintain backwards compat |
| Neo4j cold start | HIGH | LOW | Already optimized, monitor only |

---

## References

- **Audit findings**: `workbook.md` (CRITICAL FINDINGS section)
- **Research**: `docs-to-process/20260115-research-ai-companion-memory-systems-comprehensive-a8f3.md`
- **Memory architecture**: `memory/architecture.md`
- **Humanization specs**: `specs/021-028/`
