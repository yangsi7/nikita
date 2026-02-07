# Spec 039: Unified Context Engine & Intelligent Prompt Generation

## Executive Summary

**Problem**: Current system prompt generation produces only ~424 tokens via mechanical template substitution. User expects 6K-15K tokens of rich, narrative, human-feeling prompts.

**Solution**: 2-layer architecture with unified ContextEngine + Sonnet 4.5 PromptGenerator agent.

**Scope**:
- Spec 039: Context Engine + Prompt Generation (this spec)
- Spec 040: Canon Alignment (separate - persona consistency based on onboarding)

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                    CURRENT (Scattered, Mechanical)               │
├──────────────────────────────────────────────────────────────────┤
│  12+ modules → MetaPromptService → Template substitution → 424t  │
│  - meta_prompts/     - context/          - life_simulation/      │
│  - emotional_state/  - post_processing/  - prompts/ (dead)       │
│  - config_data/      - behavioral/       - conflicts/            │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│                    TARGET (Unified, Intelligent)                 │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              LAYER 1: ContextEngine                        │  │
│  │  Unified collector with 8 typed sources                    │  │
│  │  Output: ContextPackage (typed, ~5K tokens structured)     │  │
│  └─────────────────────────┬──────────────────────────────────┘  │
│                            │ RunContext[ContextPackage]          │
│                            ▼                                     │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              LAYER 2: PromptGenerator                      │  │
│  │  Claude Sonnet 4.5 agentic narrative generation            │  │
│  │  Output: PromptBundle (text + voice blocks, 6K-15K tokens) │  │
│  │  Features: Past prompt continuity, time-awareness,         │  │
│  │            output validators, ModelRetry                   │  │
│  └─────────────────────────┬──────────────────────────────────┘  │
│                            │                                     │
│                            ▼                                     │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              PromptAssembler                               │  │
│  │  Static persona + chapter rules + generated blocks         │  │
│  │  Output: Final system prompt for Nikita agent              │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## User Requirements (Captured)

1. **Intelligent agentic layer** that GENERATES prompts (not template substitution)
2. **Past prompt continuity** - reference previous prompts naturally
3. **Time-awareness** - adapt based on hours/days since last contact
4. **Comprehensive Graphiti queries** - relationship, friends, past conversations
5. **Social circle backstory** - friends context surfaced
6. **Knowledge base access** - static persona files loaded
7. **Unified clean architecture** - deprecate scattered modules
8. **Voice/text parity** - same context for both modalities
9. **Adaptive token budget** - 6K-10K typical, up to 15K for complex situations

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Architecture | Option D: 2-layer ContextEngine + Sonnet | Most powerful, full narrative capability |
| Module structure | New `nikita/context_engine/` | Clean architecture, deprecate old modules |
| Token budget | Adaptive (6K-10K typical, 15K dense) | Coverage-first, not token-floor |
| LLM for generation | Claude Sonnet 4.5 | Deep reasoning needed for narrative |
| Canon fixes | Separate Spec 040 | Faster progress, canon adapts to onboarding |

---

## Data Models (PydanticAI)

### ContextPackage (Layer 1 Output)

```python
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID

class ContextPackage(BaseModel):
    """Unified context collected from all sources."""

    # Identity
    user_id: UUID
    conversation_id: UUID | None

    # Temporal
    local_time: datetime
    day_of_week: str
    hours_since_last_contact: float
    recency_interpretation: str  # "just talked", "been a while", "worried"

    # Relationship State
    chapter: int
    chapter_name: str
    relationship_score: float
    engagement_state: str
    vulnerability_level: int  # 0-5
    active_conflict: dict | None

    # Memory (from Graphiti)
    user_facts: list[str]  # Top 50 from user graph
    relationship_episodes: list[str]  # Top 50 from relationship graph
    nikita_events: list[str]  # Top 50 from nikita graph
    social_circle: list[dict]  # Friends with backstories

    # Humanization (Specs 022-028)
    nikita_mood_4d: dict  # arousal, valence, dominance, intimacy
    nikita_daily_events: list[str]
    nikita_recent_events: list[str]
    psychological_state: dict  # attachment, wounds, defenses
    behavioral_instructions: str

    # Conversation Context
    open_threads: list[dict]
    recent_thoughts: list[str]
    last_conversation_summary: str | None
    today_key_moments: list[str]

    # Continuity
    past_prompts: list[dict]  # Last 3-5 prompts with timestamps

    # Knowledge Base
    persona_canon: str  # From base_personality.yaml
    chapter_behavior: str  # Chapter-specific rules
    vice_profile: dict  # User's vice preferences

class PromptBundle(BaseModel):
    """Output from PromptGenerator agent."""

    text_system_prompt_block: str = Field(
        ...,
        description="Dynamic system prompt block for TEXT chat (6K-12K tokens)"
    )
    voice_system_prompt_block: str = Field(
        ...,
        description="Dynamic system prompt block for VOICE (800-1500 tokens)"
    )
    coverage_notes: str | None = Field(
        None,
        description="Internal checklist of what was included"
    )
```

---

## Module Structure (New)

```
nikita/context_engine/           # NEW - Unified module
├── __init__.py                  # Exports: ContextEngine, PromptGenerator
├── models.py                    # ContextPackage, PromptBundle, cards
├── engine.py                    # ContextEngine class (Layer 1)
├── generator.py                 # PromptGenerator agent (Layer 2)
├── assembler.py                 # PromptAssembler (static + dynamic)
├── collectors/                  # 8 typed collectors
│   ├── __init__.py
│   ├── database.py              # Users, metrics, vices from Supabase
│   ├── graphiti.py              # 3 graphs: user, relationship, nikita
│   ├── humanization.py          # Specs 022-028 aggregated
│   ├── history.py               # Threads, thoughts, summaries
│   ├── knowledge.py             # Static persona files (YAML)
│   ├── temporal.py              # Time calculations, mood shift
│   ├── social.py                # Social circle with backstories
│   └── continuity.py            # Past prompts for reference
├── validators/                  # Output validators
│   ├── __init__.py
│   ├── coverage.py              # Required sections present
│   ├── guardrails.py            # No stage directions, no meta terms
│   └── speakability.py          # Voice block is speakable
├── cache.py                     # L1 (memory) + L2 (Redis) + L3 (DB)
└── prompts/                     # Generator agent prompts
    └── generator.meta.md        # System prompt for PromptGenerator
```

### Deprecation Plan

| Old Module | Status | Migration |
|------------|--------|-----------|
| `nikita/meta_prompts/` | DEPRECATE | → context_engine/generator.py |
| `nikita/context/` | DEPRECATE | → context_engine/collectors/ |
| `nikita/post_processing/` | KEEP (async) | Uses context_engine for prompts |
| `nikita/prompts/` | DELETE | Dead code |
| `nikita/config_data/prompts/` | KEEP | Loaded by collectors/knowledge.py |

---

## Implementation Phases

### Phase 0: Foundation (Week 1)
**Tasks:**
- T0.1: Create `nikita/context_engine/` module structure
- T0.2: Define `ContextPackage` and `PromptBundle` models
- T0.3: Create collector base class with RunContext[T] pattern
- T0.4: Set up unit test structure

**Tests:** 15 tests (models + base patterns)

### Phase 1: Collectors (Week 2-3)
**Tasks:**
- T1.1: DatabaseCollector (users, metrics, vices)
- T1.2: GraphitiCollector (3 graphs with specific queries)
- T1.3: HumanizationCollector (aggregate Specs 022-028)
- T1.4: HistoryCollector (threads, thoughts, summaries)
- T1.5: KnowledgeCollector (load YAMLs)
- T1.6: TemporalCollector (time delta, recency interpretation)
- T1.7: SocialCollector (social circle with backstories)
- T1.8: ContinuityCollector (past prompts)

**Tests:** 40 tests (5 per collector)

### Phase 2: ContextEngine (Week 3)
**Tasks:**
- T2.1: ContextEngine class orchestrating all collectors
- T2.2: Parallel collection with timeout handling
- T2.3: Token budget allocation (ROI-weighted)
- T2.4: Error handling with graceful degradation

**Tests:** 20 tests

### Phase 3: PromptGenerator Agent (Week 4)
**Tasks:**
- T3.1: Create generator.meta.md (Sonnet system prompt)
- T3.2: PromptGenerator PydanticAI agent with deps injection
- T3.3: Output validators (coverage, guardrails, speakability)
- T3.4: ModelRetry logic for validation failures

**Tests:** 30 tests

### Phase 4: Assembly & Integration (Week 5)
**Tasks:**
- T4.1: PromptAssembler (static + dynamic blocks)
- T4.2: Wire to text agent (agents/text/agent.py)
- T4.3: Wire to voice agent (agents/voice/service.py)
- T4.4: Cache layer (L1/L2/L3)

**Tests:** 25 tests

### Phase 5: Deprecation & Cleanup (Week 6)
**Tasks:**
- T5.1: Mark old modules as deprecated
- T5.2: Update imports across codebase
- T5.3: Delete dead code (nikita/prompts/)
- T5.4: Documentation update

**Tests:** 10 regression tests

---

## Token Budget Strategy (ROI-Weighted)

| Category | Budget | Priority | Compression |
|----------|--------|----------|-------------|
| Core persona | 2000 | P0 (always) | None |
| Recent facts (7d) | 2000 | P1 | Full text |
| Older facts | 1000 | P2 | Summarized |
| Threads (open) | 1500 | P1 | Full text |
| Threads (resolved) | 500 | P3 | One-liner |
| Life events (today) | 800 | P1 | Full text |
| Life events (week) | 400 | P2 | Summarized |
| Psychological state | 600 | P1 | Full text |
| Past prompt summary | 500 | P2 | Key points only |
| Social circle | 700 | P2 | Top 5 friends |
| **Total Input** | ~10K | - | - |
| **Output Target** | 6K-15K | - | Adaptive |

---

## Prompt Caching Strategy (93% Cost Reduction)

```
┌─────────────────────────────────────────────────────────────┐
│                    CACHE BOUNDARIES                         │
├─────────────────────────────────────────────────────────────┤
│  STATIC (cache 1h)          │  DYNAMIC (no cache)          │
│  - Base persona             │  - Current mood               │
│  - Chapter behavior         │  - Recent events              │
│  - Knowledge base           │  - Open threads               │
│  - Guardrails               │  - Conversation history       │
│  ≥1024 tokens               │  Fresh each request           │
└─────────────────────────────────────────────────────────────┘
```

**Expected savings**: 85-90% cost reduction on prompt generation.

---

## Output Validators

### 1. Coverage Validator
```python
REQUIRED_SECTIONS_TEXT = [
    "DO NOT REVEAL",
    "TEXTING STYLE RULES",
    "PRIVATE CONTEXT — CURRENT STATE",
    "PRIVATE CONTEXT — WHAT'S ON MY MIND",
    "PRIVATE CONTEXT — MY LIFE LATELY",
    "PRIVATE CONTEXT — WHERE WE STAND",
    "PRIVATE CONTEXT — MY WORLD",
    "PRIVATE CONTEXT — FOLLOW UPS",
    "PRIVATE CONTEXT — WHAT I'M REALLY FEELING",
    "RESPONSE PLAYBOOK"
]
```

### 2. Guardrails Validator
```python
BANNED_PATTERNS = [
    r"\*[^*]+\*",           # Stage directions *smiles*
    r"\([^)]+\)",           # Actions (laughs)
    r"\[[^\]]+\]",          # Meta [action]
    r"system prompt",       # Meta terms
    r"tokens?",             # Token references
    r"LLM|language model",  # Model references
    r"terminal|dashboard",  # Implementation refs
]
```

### 3. Speakability Validator (Voice)
```python
def validate_speakable(text: str) -> bool:
    """Voice block must be speakable."""
    if re.search(r"[\U0001F300-\U0001F9FF]", text):  # Emojis
        return False
    if len(text) > 2000:  # Too long for voice
        return False
    return True
```

---

## Success Criteria

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Prompt tokens | ~424 | 6,000-15,000 | `generated_prompts.token_count` |
| Past prompt reference | 0% | 100% | Manual inspection |
| Time-awareness | 0% | 100% | Check for "hours since" logic |
| Voice/text parity | 70% | 100% | Same ContextPackage |
| Coverage validation | 0% | 100% | All sections present |
| Guardrail violations | Unknown | <1% | Validator pass rate |
| Cost per prompt | $0.02 | $0.003 | With caching |

---

## Verification Plan

### Unit Tests
```bash
pytest tests/context_engine/ -v  # 140 tests
```

### Integration Tests
```bash
pytest tests/context_engine/test_integration.py -v  # 20 tests
```

### E2E Verification
1. Deploy to Cloud Run
2. Send test message via Telegram MCP
3. Query generated_prompts:
```sql
SELECT token_count,
       context_snapshot->>'sections_present' as sections,
       context_snapshot->>'past_prompts_referenced' as continuity
FROM generated_prompts
ORDER BY created_at DESC LIMIT 1;
```

**Pass Criteria:**
- `token_count` between 6,000 and 15,000
- All 10 required sections present
- `past_prompts_referenced = true` for returning users

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Sonnet cost increase | HIGH | Prompt caching (93% reduction) |
| Collector failures | MEDIUM | Graceful degradation per collector |
| Neo4j cold start | LOW | Already handled (Spec 036) |
| Validation loops | MEDIUM | Max 3 retries, then fallback |
| Token overflow | MEDIUM | ROI-weighted budgeting |

---

## Files to Create

| File | Purpose | Lines |
|------|---------|-------|
| `nikita/context_engine/__init__.py` | Module exports | 20 |
| `nikita/context_engine/models.py` | ContextPackage, PromptBundle | 150 |
| `nikita/context_engine/engine.py` | ContextEngine orchestrator | 200 |
| `nikita/context_engine/generator.py` | PromptGenerator agent | 250 |
| `nikita/context_engine/assembler.py` | Static + dynamic assembly | 100 |
| `nikita/context_engine/collectors/*.py` | 8 collector files | 800 |
| `nikita/context_engine/validators/*.py` | 3 validator files | 150 |
| `nikita/context_engine/cache.py` | 3-layer caching | 100 |
| `nikita/context_engine/prompts/generator.meta.md` | Generator system prompt | 200 |
| `tests/context_engine/**/*.py` | 140+ tests | 2000 |
| **Total** | | ~4000 |

---

## Timeline

| Week | Phase | Deliverable |
|------|-------|-------------|
| 1 | Phase 0: Foundation | Models, structure, 15 tests |
| 2-3 | Phase 1: Collectors | 8 collectors, 40 tests |
| 3 | Phase 2: Engine | Orchestrator, 20 tests |
| 4 | Phase 3: Generator | PydanticAI agent, 30 tests |
| 5 | Phase 4: Integration | Wiring, cache, 25 tests |
| 6 | Phase 5: Cleanup | Deprecation, docs, 10 tests |

**Total: 6 weeks, 140 tests**

---

---

## Database Analysis (via Supabase MCP)

### Current Schema (38 tables - Production Ready)

| Table | Rows | Purpose | Migration Impact |
|-------|------|---------|-----------------|
| `generated_prompts` | 11 | Prompt logging | Add `engine_version` column |
| `conversations` | 24 | Message exchanges | No change |
| `user_metrics` | 1 | 4 core metrics | No change |
| `conversation_threads` | 1 | Open threads | No change |
| `nikita_thoughts` | 2 | Simulated thoughts | No change |
| `daily_summaries` | 3 | Daily rollups | No change |
| `nikita_emotional_states` | - | 4D mood | No change |
| `nikita_narrative_arcs` | - | Story arcs | No change |
| `user_social_circles` | - | Friends | No change |

### Required Migrations

```sql
-- Migration 1: Add engine version tracking
ALTER TABLE generated_prompts
ADD COLUMN engine_version VARCHAR(20) DEFAULT 'v1_meta_prompt';

-- Migration 2: Feature flags table
CREATE TABLE feature_flags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    flag_name VARCHAR(100) UNIQUE NOT NULL,
    flag_value VARCHAR(100) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Migration 3: Migration metrics (optional, for A/B comparison)
CREATE TABLE migration_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    user_id UUID NOT NULL,
    engine_used VARCHAR(20) NOT NULL,
    prompt_hash VARCHAR(64),
    token_count INTEGER,
    generation_ms FLOAT
);
```

**Status**: Schema is production-ready. Only 2-3 small migrations needed.

---

## Dependency Analysis

### Critical Integration Points (BLOCKING)

| File | Line | Dependency | Risk |
|------|------|-----------|------|
| `nikita/context/post_processor.py` | 507 | `MetaPromptService.extract_entities()` | 🔴 BLOCKING |
| `nikita/context/stages/extraction.py` | 88 | `MetaPromptService(session)` | 🔴 BLOCKING |
| `nikita/context/template_generator.py` | 99 | `MetaPromptService.generate_system_prompt()` | 🟠 HIGH |
| `nikita/agents/text/agent.py` | 22 | `from nikita.prompts.nikita_persona` | 🟠 MEDIUM |
| `nikita/api/routes/admin_debug.py` | 688 | `MetaPromptService(session)` | 🟡 LOW |

### Import Dependency Graph

```
nikita.prompts/ (base - static personas)
    ↓
nikita.meta_prompts/ (builds on prompts)
    ↓
nikita.context/ (uses meta_prompts)
    ↓
nikita.agents/ (uses context)
    ↓
nikita.api/ (uses agents)
```

**CRITICAL**: Cannot remove MetaPromptService until context_engine can replace:
1. `generate_system_prompt()` - prompt generation
2. `extract_entities()` - fact/thread/thought extraction

---

## Test Migration Plan

### Test Inventory (725 total tests affected)

| Category | Count | Action | Effort |
|----------|-------|--------|--------|
| **DELETE** | 143 | Layer 1-6, composer tests | Low |
| **MIGRATE** | 219 | Core prompt generation logic | Medium |
| **KEEP** | 363 | Pipeline stages, post-processor | None |

### DELETE Tests (143)
- `tests/context/test_layer*.py` (122 tests) - Layer abstraction removed
- `tests/context/test_composer*.py` (41 tests) - Composer pattern replaced
- `tests/meta_prompts/test_timezone_safety.py` (10 tests) - No longer relevant

### MIGRATE Tests (219)
- `tests/meta_prompts/*.py` (109 tests) → `tests/context_engine/test_generator.py`
- `tests/context/test_template_generator.py` (23 tests) → `tests/context_engine/test_engine.py`
- Voice prompt tests (77 tests) → Update imports only

### KEEP Tests (363)
- `tests/context/stages/*.py` (133 tests) - Pipeline stages unchanged
- `tests/context/test_post_processor*.py` (31 tests) - Orchestrator unchanged
- Voice operation tests (159 tests) - Non-prompt logic

---

## Migration Strategy (8 Weeks)

### Phase A: Foundation (Week 1-2)
- Create `nikita/context_engine/` module alongside existing
- Implement feature flag infrastructure
- Add database migrations
- Build ContextEngine and PromptGenerator

### Phase B: Shadow Mode (Week 2-3)
- Run BOTH engines in parallel
- v1 result returned to user (no risk)
- Log comparison metrics
- Identify discrepancies

**Success Criteria**:
- Content similarity > 85%
- Token variance < 20%
- Zero v2 errors
- Latency increase < 50ms

### Phase C: Gradual Traffic Shift (Week 3-5)

| Day | Flag | New Engine % | Rollback Trigger |
|-----|------|--------------|------------------|
| 1 | canary | 5% | Any error spike |
| 3 | gradual_10 | 10% | Error > 0.5% |
| 6 | gradual_25 | 25% | Error > 0.3% |
| 10 | gradual_50 | 50% | Error > 0.2% |
| 14 | gradual_75 | 75% | Error > 0.1% |
| 18 | enabled | 100% | Manual only |

### Phase D: Full Cutover (Week 5-6)
- 100% traffic on v2
- Monitor for 2 weeks
- Product team sign-off

### Phase E: Deprecation & Cleanup (Week 7-8)
- Mark old modules deprecated
- Delete old code
- Clean up migration tables
- Update documentation

---

## Rollback Procedures

### Instant Rollback (< 1 minute)
```bash
# Via admin API
curl -X POST https://nikita-api.run.app/admin/migration-flag \
  -d '{"flag": "rollback"}'

# Or direct DB
UPDATE feature_flags SET flag_value = 'rollback'
WHERE flag_name = 'context_engine_flag';
```

### Automated Rollback Triggers
- Error rate > 1% for 5 min → Auto-rollback
- Latency > 2x baseline for 5 min → Auto-throttle
- Any 500 errors in v2 → Per-request fallback to v1

---

## Files to Create/Modify Summary

### New Files (~4000 lines)

| File | Purpose | Lines |
|------|---------|-------|
| `nikita/context_engine/__init__.py` | Module exports | 20 |
| `nikita/context_engine/models.py` | ContextPackage, PromptBundle | 150 |
| `nikita/context_engine/engine.py` | ContextEngine orchestrator | 200 |
| `nikita/context_engine/generator.py` | PromptGenerator agent | 250 |
| `nikita/context_engine/router.py` | V1/V2 routing | 100 |
| `nikita/context_engine/collectors/*.py` | 8 collector files | 800 |
| `nikita/context_engine/validators/*.py` | 3 validator files | 150 |
| `nikita/context_engine/cache.py` | 3-layer caching | 100 |
| `nikita/context_engine/prompts/generator.meta.md` | Generator prompt | 200 |
| `tests/context_engine/**/*.py` | 140+ tests | 2000 |

### Files to Update

| File | Change | Risk |
|------|--------|------|
| `nikita/agents/text/agent.py` | Use context_engine.router | Medium |
| `nikita/agents/voice/service.py` | Use context_engine.router | Medium |
| `nikita/context/post_processor.py` | Use context_engine for extraction | High |
| `nikita/context/stages/extraction.py` | Use context_engine | High |
| `nikita/api/routes/admin.py` | Add migration endpoints | Low |

### Files to Deprecate (Week 7)

| Module | Files | Lines | Tests |
|--------|-------|-------|-------|
| `nikita/meta_prompts/` | 3 | ~2000 | 119 |
| `nikita/prompts/` | 3 | ~200 | 0 |
| `nikita/context/template_generator.py` | 1 | ~500 | 23 |

---

## Go/No-Go Criteria

### Phase A → Phase B
- [ ] All new module files created and tested
- [ ] Feature flag infrastructure deployed
- [ ] Migrations applied
- [ ] Rollback procedure tested

### Phase B → Phase C
- [ ] Shadow mode run for 48+ hours
- [ ] Content similarity > 85%
- [ ] Zero v2 errors
- [ ] Latency increase < 50ms

### Phase C → Phase D
- [ ] 100% traffic on v2 for 48+ hours
- [ ] Error rate < 0.1%
- [ ] No rollbacks triggered
- [ ] Product sign-off

### Phase D → Phase E
- [ ] 2 weeks stable at 100%
- [ ] No user complaints
- [ ] Documentation updated
- [ ] Team trained

---

## Related Specs

- **Spec 040** (separate): Canon Alignment - persona consistency based on onboarding
- **Spec 029**: Context Comprehensive (superseded by this spec)
- **Spec 030**: Text Continuity (integrated into this spec)
- **Specs 021-028**: Humanization (consumed by HumanizationCollector)

---

## SDD Workflow (Next Steps)

After plan approval, execute SDD workflow:

1. **Create spec.md**: `specs/039-unified-context-engine/spec.md`
2. **Auto-chain to /plan**: Creates `plan.md`, `research.md`
3. **Auto-chain to /tasks**: Creates `tasks.md` with TDD sub-steps
4. **Auto-chain to /audit**: Creates `audit-report.md`
5. **On PASS**: Execute `/implement` with TDD discipline

**Estimated Total**: 8 weeks implementation + 2 weeks buffer = 10 weeks

---

## Parallel Documentation Sync

**IMPORTANT**: Launch a parallel agent to perform documentation sync during implementation:

```
Task agent with subagent_type="general-purpose":

Prompt: "Execute /doc-sync to consolidate documentation in docs-to-process/ into docs/:

1. Scan docs-to-process/ for unprocessed artifacts
2. Consolidate findings into appropriate docs/ subdirectories:
   - docs/architecture/ for system design (context_engine architecture)
   - docs/patterns/ for reusable patterns (PydanticAI agent patterns)
   - docs/decisions/ for ADRs (Spec 039 architectural decisions)
3. Update docs/README.md with new navigation entries
4. Log changes in docs/CHANGELOG.md
5. Delete processed files from docs-to-process/
6. Update memory/architecture.md with context_engine module

Focus on consolidating Spec 039 research findings and architectural documentation."
```

**Trigger**: Launch this agent after Phase 0 (Foundation) is complete, to keep documentation in sync with implementation.

**Files to sync**:
- Research from 4 subagents (database, tests, dependencies, migration)
- Architecture decisions (2-layer ContextEngine + PromptGenerator)
- New module documentation (nikita/context_engine/)
