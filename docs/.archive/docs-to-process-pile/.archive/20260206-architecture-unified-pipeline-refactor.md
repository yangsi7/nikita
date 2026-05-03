# Unified Pipeline Refactor: Nikita Architecture Simplification

**Date**: 2026-02-06
**Type**: Architecture Decision + Implementation Spec
**Status**: Approved for SDD workflow

---

## Problem Statement

The Nikita codebase has accumulated severe architectural fragmentation through 41 specs of incremental development:

- **Three parallel prompt generation paths**: MetaPromptService v1 (1918 lines), context_engine v2 (8 collectors + Sonnet LLM generator + assembler), and voice server_tools (935 lines of inline context loading)
- **Two post-processing pipelines**: `context/post_processor.py` (11-stage, used by voice) and `post_processing/pipeline.py` (8-step, used by text)
- **Neo4j/Graphiti adds 30-73s cold start latency** for what amounts to storing text strings with timestamps
- **Voice and text have diverged**: different context, different prompts, different history — breaking the "one person" illusion
- **7 humanization modules** (1575 tests) wired through multiple fragmented paths

## Target Architecture

```
User Message → Agent reads pre-built prompt from Supabase → LLM responds → Deliver

                        [Async, after conversation ends]
Conversation ends → UNIFIED PIPELINE:
  1. Extract entities/facts from transcript
  2. Update memory facts in Supabase (replaces Neo4j)
  3. Run life simulation (generate events)
  4. Compute emotional state (4D mood)
  5. Compute game state (score, chapter, decay)
  6. Evaluate conflicts
  7. Schedule touchpoints
  8. Generate summaries
  9. Build next system prompt (Jinja2 template + Haiku narrative enrichment)
  10. Store prompt in `ready_prompts` table
                        ↓
Both text + voice agents read from `ready_prompts`
```

## Guiding Constraints

1. **No Neo4j**: Store memory facts as JSONB rows in Supabase with pgVector embeddings for semantic search
2. **Hybrid prompt generation**: Jinja2 templates render structured context, then Claude Haiku enriches with narrative texture (~500ms, ~$0.001/call). Haiku specializes in transforming the filled template into thematic narrative with variability, time-of-day contextualization, and emotional coherence
3. **One pipeline**: Context collection + humanization + prompt building all happen in post-processing
4. **Voice-text parity**: Both agents read the same `ready_prompts` row; conversation history shared via `conversations` table
5. **Reuse existing modules**: Keep life_simulation/, emotional_state/, touchpoints/, scoring/, chapters/, decay/ — they work and have 1500+ tests
6. **Supabase only**: Single datastore, no Redis, no Neo4j

---

## Database Schema

### `memory_facts` — replaces 3 Neo4j knowledge graphs

```sql
CREATE TABLE memory_facts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    graph_type TEXT NOT NULL CHECK (graph_type IN ('user', 'relationship', 'nikita')),
    fact TEXT NOT NULL,
    source TEXT DEFAULT 'conversation',
    confidence REAL DEFAULT 0.8 CHECK (confidence >= 0 AND confidence <= 1),
    embedding vector(1536),
    metadata JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    superseded_by UUID REFERENCES memory_facts(id),
    conversation_id UUID REFERENCES conversations(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_memory_facts_user_graph ON memory_facts(user_id, graph_type) WHERE is_active = TRUE;
CREATE INDEX idx_memory_facts_user_recent ON memory_facts(user_id, created_at DESC) WHERE is_active = TRUE;
CREATE INDEX idx_memory_facts_embedding ON memory_facts
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);
```

### `ready_prompts` — pre-generated system prompts

```sql
CREATE TABLE ready_prompts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    platform TEXT NOT NULL CHECK (platform IN ('text', 'voice')),
    prompt_text TEXT NOT NULL,
    token_count INTEGER DEFAULT 0,
    context_snapshot JSONB DEFAULT '{}',
    pipeline_version TEXT DEFAULT 'v1',
    generation_time_ms REAL DEFAULT 0,
    is_current BOOLEAN DEFAULT TRUE,
    conversation_id UUID REFERENCES conversations(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_ready_prompts_current
    ON ready_prompts(user_id, platform) WHERE is_current = TRUE;
```

---

## New Module Structure

```
nikita/pipeline/
    __init__.py
    orchestrator.py              # Single entry point: process(conversation_id)
    models.py                    # PipelineContext, PipelineResult, StageResult
    stages/
        __init__.py
        extraction.py            # LLM entity/fact extraction from transcript
        memory_update.py         # Write facts to memory_facts via SupabaseMemory
        life_sim.py              # Wrap nikita/life_simulation/
        emotional.py             # Wrap nikita/emotional_state/
        game_state.py            # Score + chapter + decay computation
        conflict.py              # Wrap conflict evaluation
        touchpoint.py            # Wrap nikita/touchpoints/
        summary.py               # Generate conversation summaries
        prompt_builder.py        # Jinja2 render + Haiku narrative enrichment
    templates/
        system_prompt.j2         # Main system prompt template (~4.8K tokens)
        voice_prompt.j2          # Voice variant (~1.5K tokens)
        enrichment_prompt.md     # Haiku enrichment instructions

nikita/memory/
    supabase_memory.py           # SupabaseMemory (replaces graphiti_client.py)

nikita/db/models/
    memory_fact.py               # SQLAlchemy model
    ready_prompt.py              # SQLAlchemy model

nikita/db/repositories/
    memory_fact_repository.py    # CRUD + pgVector semantic search
    ready_prompt_repository.py   # Get current prompt for user+platform
```

---

## Hybrid Prompt Generation (Jinja2 + Haiku)

### Stage A: Jinja2 Template Render (~5ms, deterministic)

Template sections:
1. **Identity** (~400 tokens) — Static persona from `base_personality.yaml`
2. **Immersion Rules** (~200 tokens) — Never reveal AI/game/scores
3. **Platform Style** (~300 tokens) — Text vs voice formatting
4. **Current State** (~600 tokens) — Time, activity, mood, energy, daily events
5. **Relationship State** (~500 tokens) — Chapter, score, engagement, conflict
6. **Memory** (~800 tokens) — User facts (15), relationship episodes (8), nikita events
7. **Continuity** (~600 tokens) — Last conversation summary, open threads, today's moments
8. **Inner Life** (~500 tokens) — Thoughts, recent events, inner monologue
9. **Psychological Depth** (~400 tokens) — Vulnerability level, defenses, triggers
10. **Chapter Behavior** (~300 tokens) — Chapter-specific response playbook
11. **Vice Shaping** (~200 tokens) — Top 3 vices with intensity

### Stage B: Haiku Narrative Enrichment (~500ms, ~$0.001/call)

Takes filled template, transforms each section into thematic narrative:
- Matches Nikita's current emotional state
- Contextualizes for time of day / day of week
- Adds variability (word choice, emphasis, tone shifts)
- Weaves connections between sections (mood ↔ events ↔ relationship)
- Preserves ALL facts — enriches presentation, never fabricates
- Optimizes for response LLM to have rich material

**Fallback**: If Haiku fails, raw Jinja2 output is complete and usable.

---

## What Gets Deleted (~11,000+ lines)

| Path | Lines | Reason |
|------|-------|--------|
| `nikita/context_engine/` | ~2500 | 8 collectors + LLM generator + assembler + router — replaced by pipeline |
| `nikita/meta_prompts/` | ~1918 | v1 LLM prompt service — replaced by Jinja2+Haiku |
| `nikita/context/template_generator.py` | 541 | Old v1 prompt generator |
| `nikita/context/layers/` | ~1600 | 6-layer system, long deprecated |
| `nikita/context/post_processor.py` | 494 | Old 11-stage orchestrator |
| `nikita/post_processing/` | ~2100 | Current 8-step pipeline + adapter — replaced |
| `nikita/memory/graphiti_client.py` | 451 | Neo4j client |
| `nikita/context/stages/` | ~1000 | Old pipeline stages (logic ported) |
| `nikita/prompts/nikita_persona.py` | ~200 | Static persona (moved to YAML) |

## What Gets Kept (Unchanged)

| Module | Tests | Pipeline Stage |
|--------|-------|----------------|
| `nikita/life_simulation/` | 212 | `stages/life_sim.py` wraps it |
| `nikita/emotional_state/` | 233 | `stages/emotional.py` wraps it |
| `nikita/touchpoints/` | 189 | `stages/touchpoint.py` wraps it |
| `nikita/engine/scoring/` | 60 | `stages/game_state.py` uses it |
| `nikita/engine/chapters/` | 142 | `stages/game_state.py` uses it |
| `nikita/engine/decay/` | 52 | `stages/game_state.py` uses it |
| `nikita/engine/vice/` | 81 | Template reads vice profile |
| `nikita/engine/engagement/` | 179 | Template reads engagement state |
| `nikita/agents/text/history.py` | 23 | Still loads message history |
| `nikita/agents/text/token_budget.py` | 13 | Still manages tokens |
| `nikita/onboarding/` | 231 | Separate flow, untouched |
| `nikita/platforms/telegram/` | 74 | Trigger point, minor changes |

---

## Implementation Phases

### Phase 0: Foundation
- Create Supabase tables (memory_facts, ready_prompts)
- Create module structure (nikita/pipeline/)
- Create Pydantic models (PipelineContext, PipelineResult)
- Create SupabaseMemory class with pgVector search
- Create repositories (MemoryFactRepository, ReadyPromptRepository)

### Phase 1: Pipeline Core
- Pipeline orchestrator with sequential stage execution
- Port extraction stage (keep LLM extraction, write to Supabase)
- Memory update stage (SupabaseMemory, embedding generation, dedup)
- Wrap existing humanization modules as thin pipeline stages
- Game state stage (score + chapter + decay)
- Summary generation stage

### Phase 2: Prompt Building
- Jinja2 templates (text + voice variants)
- Haiku narrative enrichment prompt
- PromptBuilder stage (render + enrich + validate + store)
- ReadyPrompt storage with is_current flag

### Phase 3: Agent Integration
- Text agent reads from ready_prompts instead of running context_engine
- Voice server_tools simplified to read ready_prompts (~935→200 lines)
- Shared conversation history (both platforms use same table)
- Fallback: generate on-the-fly if no pre-built prompt

### Phase 4: Migration + Cleanup
- Neo4j → Supabase data migration script
- Delete dead modules (~11K lines)
- Remove Neo4j dependencies from pyproject.toml
- Remove feature flags (CONTEXT_ENGINE_FLAG, MEMORY_BACKEND)
- Update all affected tests
- Update documentation

---

## Performance Targets

| Metric | Before | After |
|--------|--------|-------|
| Message latency | 85s | 2-5s (LLM response only) |
| Context collection | 27.5s (Neo4j) | 0s (pre-built) |
| Prompt generation | 2-5s (Sonnet) | 0s (pre-built) |
| Pipeline processing | ~15s | ~8-12s (Haiku ~500ms, no Neo4j) |
| Voice context load | 2-30s | <100ms (DB read) |
| Prompt cost/msg | ~$0.01 (Sonnet) | ~$0.001 (Haiku, async) |

---

## Reference Documents

- `docs-to-process/system_diagram.md` — Actor/Archivist/Director split
- `docs-to-process/problem-structure-spec.md` — ToT diagram specification, entity definitions, state machines
- `nikita/context_engine/models.py` — ContextPackage data contract (reuse in templates)
- `nikita/config_data/prompts/base_personality.yaml` — Static persona (keep, load in template)
