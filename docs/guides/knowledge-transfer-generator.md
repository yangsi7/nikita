# NIKITA KNOWLEDGE TRANSFER: Deep Audit Documentation Generator

## OBJECTIVE

Generate comprehensive documentation enabling another AI agent to rebuild Nikita from scratch with architectural improvements. This meta-prompt orchestrates parallel subagent research and produces **15 structured deliverables** that capture everything about the system - what works, what doesn't, and what should be done differently.

**Estimated Coverage**: 80-90% of rebuild requirements (up from 25-30% in v1)

---

## EXECUTION MODEL

### Parallel Subagent Strategy

Use the Task tool to launch specialized agents concurrently:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      KNOWLEDGE TRANSFER ORCHESTRATION (v2)                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  Phase 1: RESEARCH (Parallel - 8 Subagents)                                     │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐                   │
│  │ Context    │ │ Integration│ │ Database   │ │ External   │                   │
│  │ Engine     │ │ Patterns   │ │ Schema     │ │ Research   │                   │
│  │code-analyz │ │code-analyz │ │code-analyz │ │prompt-     │                   │
│  │            │ │            │ │            │ │researcher  │                   │
│  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └─────┬──────┘                   │
│        │              │              │              │                           │
│  ┌─────┴──────┐ ┌─────┴──────┐ ┌─────┴──────┐ ┌─────┴──────┐  NEW in v2       │
│  │ Game       │ │ Pipeline   │ │ Testing    │ │ Voice      │                   │
│  │ Engine     │ │ Stages     │ │ Patterns   │ │ Implement  │                   │
│  │code-analyz │ │code-analyz │ │code-analyz │ │code-analyz │                   │
│  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └─────┬──────┘                   │
│        │              │              │              │                           │
│        └──────────────┴──────┬───────┴──────────────┘                           │
│                              │                                                   │
│  Phase 2: SYNTHESIS                                                              │
│  ┌───────────────────────────┴─────────────────────────────────┐                │
│  │              Compile findings into 15 deliverables          │                │
│  │              Add ASCII diagrams, file:line refs             │                │
│  │              Mark "NEEDS RETHINKING" sections               │                │
│  │              Add YAML frontmatter for Claude Code           │                │
│  └─────────────────────────────────────────────────────────────┘                │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Token-Efficient Patterns

1. **Subagent Delegation**: Research-heavy tasks run in subagent context (preserves main context)
2. **Firecrawl Two-Step**: `firecrawl_search(query, limit=5)` → `firecrawl_scrape(url)` (never use scrapeOptions in search)
3. **Selective File Reading**: Use `project-intel.mjs --symbols` before reading full files
4. **Incremental Output**: Generate each deliverable independently (enables parallel writes)

---

## CLAUDE CODE OPTIMIZATION

### YAML Frontmatter Template

Every deliverable MUST start with this frontmatter for context efficiency:

```yaml
---
title: "Document Title"
type: tutorial | how-to | explanation | reference  # Diátaxis type
context_priority: critical | high | medium | low
c4_level: context | container | component | code  # C4 model level
primary_files:
  - path/to/file.py:line_start-line_end
  - path/to/other.py:specific_line
related_adrs:
  - specs/NNN-feature-name
  - memory/architecture.md
needs_rethinking:
  - Brief description of problematic area
  - Another area that needs attention
---
```

### Quick Entry Points Section

Every deliverable MUST include a "For Claude Code: Quick Entry Points" section:

```markdown
## For Claude Code: Quick Entry Points

# Find [relevant thing]:
rg "pattern" nikita/path/

# Trace [dependency]:
rg "ClassName" --type py -A 3

# Check [configuration]:
fd "filename" nikita/
```

### Evidence Requirements (CoD^Σ)

All claims MUST include file:line references:

**Bad**: "The context engine collects data from multiple sources"
**Good**: "ContextEngine.collect() at `engine.py:166` uses asyncio.gather with return_exceptions=True to run 8 collectors in parallel"

---

## 15 DELIVERABLES

### Deliverable Overview Table

| # | Document | Lines | Diátaxis Type | C4 Level | Priority |
|---|----------|-------|---------------|----------|----------|
| D1 | INDEX.md | 250-350 | Reference | - | Entry point |
| D2 | PROJECT_OVERVIEW.md | 450-550 | Explanation | Context (C1) | Start here |
| D3 | USER_JOURNEY.md | 550-650 | Tutorial | - | Game flow |
| D4 | CONTEXT_ENGINE.md | 1000-1200 | Explanation | Container (C2) | **CRITICAL** |
| D5 | DATABASE_SCHEMA.md | 450-550 | Reference | - | Data model |
| D6 | INTEGRATIONS.md | 600-700 | How-To | - | External |
| D7 | AUTHENTICATION.md | 350-450 | How-To | - | Auth flow |
| D8 | ANTI_PATTERNS.md | 350-450 | Explanation | - | Lessons |
| D9 | ARCHITECTURE_ALTERNATIVES.md | 500-600 | Reference | - | Research |
| D10 | ONBOARDING.md | 500-600 | Tutorial | - | Voice-first |
| **D11** | **GAME_ENGINE_MECHANICS.md** | **1000-1200** | **Explanation** | **Component (C3)** | **CRITICAL** |
| **D12** | **PIPELINE_STAGES.md** | **800-1000** | **Explanation** | **Component (C3)** | **CRITICAL** |
| **D13** | **TESTING_STRATEGY.md** | **500-600** | **How-To** | **-** | **HIGH** |
| **D14** | **DEPLOYMENT_OPERATIONS.md** | **600-700** | **How-To** | **-** | **HIGH** |
| **D15** | **VOICE_IMPLEMENTATION.md** | **600-700** | **Reference** | **Component (C3)** | **HIGH** |

**Total Estimated Lines**: 8,000-10,000

---

### D1: INDEX.md (250-350 lines)

Master navigation document with:
- Reading order (recommended path through docs)
- Document dependencies (which docs build on others)
- Key concepts per document (2-3 bullet summary)
- Quick reference: Most important files for each domain
- YAML frontmatter with all primary files

```yaml
---
title: "Nikita Knowledge Transfer Index"
type: reference
context_priority: critical
primary_files:
  - nikita/context_engine/engine.py:166-180
  - nikita/engine/scoring/calculator.py:45-80
  - nikita/context/post_processor.py:100-200
related_adrs: []
---
```

```markdown
# Nikita Knowledge Transfer Index

## Reading Order

### Foundation (Start Here)
1. **PROJECT_OVERVIEW.md** - Product concept, win conditions, tech stack
2. **USER_JOURNEY.md** - Game flow from signup to victory/loss
3. **DATABASE_SCHEMA.md** - Data model understanding

### Core Systems (Deep Dive)
4. **CONTEXT_ENGINE.md** - THE critical system. 3-layer architecture.
5. **GAME_ENGINE_MECHANICS.md** - Scoring, decay, chapters, boss, engagement
6. **PIPELINE_STAGES.md** - 11-stage async post-processing

### Integration Layer
7. **INTEGRATIONS.md** - Telegram webhook, handler chain
8. **VOICE_IMPLEMENTATION.md** - Server tools, dynamic variables
9. **AUTHENTICATION.md** - OTP and session flow
10. **ONBOARDING.md** - Voice-first onboarding process

### Operations & Quality
11. **DEPLOYMENT_OPERATIONS.md** - Cloud Run, env vars, migrations
12. **TESTING_STRATEGY.md** - Async patterns, fixtures, mocking

### Retrospective
13. **ANTI_PATTERNS.md** - What NOT to do
14. **ARCHITECTURE_ALTERNATIVES.md** - What to consider instead

## Key Files Quick Reference
| Domain | Critical Files |
|--------|----------------|
| Context Engine | nikita/context_engine/engine.py, models.py, generator.py |
| Game Engine | nikita/engine/scoring/calculator.py, chapters/state_machine.py |
| Pipeline | nikita/context/stages/*.py, post_processor.py |
| Text Agent | nikita/agents/text/agent.py, history.py |
| Voice Agent | nikita/agents/voice/server_tools.py, inbound.py |
| Telegram | nikita/platforms/telegram/message_handler.py |
| Database | nikita/db/models/user.py, conversation.py |
| Memory | nikita/memory/graphiti_client.py |
```

---

### D2: PROJECT_OVERVIEW.md (450-550 lines)

```yaml
---
title: "Nikita Project Overview"
type: explanation
context_priority: critical
c4_level: context
primary_files:
  - nikita/config/settings.py:all
  - CLAUDE.md:1-100
related_adrs:
  - memory/architecture.md
needs_rethinking:
  - Portal complexity (recommend skip in rebuild)
  - Graphiti cold start times
---
```

Product definition document:

**Required Sections:**
1. **Elevator Pitch** (50 words max)
2. **Target Audience** (demographics, psychographics)
3. **Win/Lose Conditions** (explicit game mechanics)
4. **Technology Stack** with rationale for each choice
5. **Cost Structure** (infrastructure costs at scale)
6. **Decision Rationale** for key architectural choices

**C1 Context Diagram Required:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         NIKITA SYSTEM CONTEXT (C1)                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                              ┌─────────────────┐                            │
│                              │    Players      │                            │
│                              │  (Target: 18-35 │                            │
│                              │   male, gaming) │                            │
│                              └────────┬────────┘                            │
│                                       │                                      │
│           ┌───────────────────────────┼───────────────────────────┐         │
│           │                           │                           │         │
│           v                           v                           v         │
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐       │
│  │    Telegram     │     │   Voice Call    │     │   Web Portal    │       │
│  │   (@Nikita_bot) │     │ (+1-XXX-XXX)    │     │  (portal.nikita)│       │
│  └────────┬────────┘     └────────┬────────┘     └────────┬────────┘       │
│           │                       │                       │                 │
│           └───────────────────────┼───────────────────────┘                 │
│                                   v                                          │
│                      ┌────────────────────────┐                             │
│                      │     NIKITA SYSTEM      │                             │
│                      │   AI Girlfriend Game   │                             │
│                      │                        │                             │
│                      │ - Text Agent (Claude)  │                             │
│                      │ - Voice Agent (11Labs) │                             │
│                      │ - Game Engine (Scoring)│                             │
│                      │ - Memory (Graphiti)    │                             │
│                      └────────────────────────┘                             │
│                                   │                                          │
│           ┌───────────────────────┼───────────────────────┐                 │
│           v                       v                       v                 │
│  ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐           │
│  │   Supabase      │   │   Neo4j Aura    │   │   Claude API    │           │
│  │   (PostgreSQL)  │   │   (Memory)      │   │   (LLM)         │           │
│  └─────────────────┘   └─────────────────┘   └─────────────────┘           │
│                                                                              │
│  Cost Model (at 100 users/day):                                             │
│  ├── Supabase: Free tier                                                    │
│  ├── Neo4j Aura: Free tier (pauses after 3 days idle)                       │
│  ├── Claude API: ~$20-30/month                                              │
│  ├── ElevenLabs: ~$10-20/month                                              │
│  ├── Cloud Run: ~$5-15/month                                                │
│  └── TOTAL: $35-65/month                                                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### D3: USER_JOURNEY.md (550-650 lines)

```yaml
---
title: "User Journey & Game Flow"
type: tutorial
context_priority: high
primary_files:
  - nikita/engine/chapters/state_machine.py:all
  - nikita/engine/constants.py:10-50
  - nikita/platforms/telegram/message_handler.py:200-300
related_adrs:
  - specs/004-chapter-boss-system
  - specs/003-scoring-engine
needs_rethinking:
  - Boss judgment LLM call reliability
---
```

Complete game flow documentation:

**Required Sections:**
1. **Signup Flow** (Telegram /start → OTP → Onboarding)
2. **Chapter Progression** (Ch1 → Ch5, score thresholds)
3. **Boss Encounters** (triggers, judgment, success/fail)
4. **Decay Mechanics** (hourly decay, chapter-specific rates)
5. **Game Over/Victory Conditions**
6. **Engagement System** (clingy/distant detection)

**For Claude Code: Quick Entry Points**
```bash
# Find chapter thresholds:
rg "CHAPTER_THRESHOLDS\|BOSS_THRESHOLDS" nikita/engine/

# Find decay rates:
rg "DECAY_RATES" nikita/engine/constants.py

# Trace boss judgment:
rg "BossJudgment" nikita/engine/chapters/ -A 5
```

**ASCII Flowchart Required:**
```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  /start  │────>│   OTP    │────>│ Onboard  │────>│  Ch 1    │────>│  Ch 2    │
│          │     │  Email   │     │  (Voice) │     │ Curiosity│     │ Testing  │
└──────────┘     └──────────┘     └──────────┘     └────┬─────┘     └────┬─────┘
                                                        │                │
                                                        v                v
                                                   Score: 25+       Score: 35+
                                                        │                │
                                                   ┌────┴────┐     ┌────┴────┐
                                                   │  BOSS   │     │  BOSS   │
                                                   │ Ch 1→2  │     │ Ch 2→3  │
                                                   └────┬────┘     └────┬────┘
                                                        │                │
                                               ┌────────┴────────┐       │
                                               v                 v       v
                                           [PASS]            [FAIL]   [...]
                                               │                 │
                                               v                 v
                                         Advance Ch         3 attempts?
                                                                 │
                                                        ┌────────┴────────┐
                                                        v                 v
                                                    [NO]              [YES]
                                                       │                 │
                                                       v                 v
                                                   Try Again        GAME OVER
```

---

### D4: CONTEXT_ENGINE.md (1000-1200 lines) **[CRITICAL]**

```yaml
---
title: "Context Engine Architecture"
type: explanation
context_priority: critical
c4_level: container
primary_files:
  - nikita/context_engine/engine.py:166-180
  - nikita/context_engine/models.py:all
  - nikita/context_engine/generator.py:287
  - nikita/context_engine/assembler.py:100-150
  - nikita/context_engine/collectors/base.py:45-80
  - nikita/context_engine/collectors/graphiti.py:66-67
  - nikita/context_engine/validators/coverage.py:all
related_adrs:
  - specs/039-unified-context-engine
  - specs/040-context-engine-enhancements
needs_rethinking:
  - GraphitiCollector 30s timeout (Neo4j cold start 60-83s)
  - PromptGenerator 45s timeout may not be enough
  - Coverage validation retry loop can take 30-45s worst case
  - Voice bypasses ContextEngine entirely (server_tools.py:331-337)
---
```

The most important document. This is the heart of Nikita's intelligence.

**Required Sections:**
1. **3-Layer Architecture**
   - Layer 1: ContextEngine (8 parallel collectors)
   - Layer 2: PromptGenerator (Claude Sonnet 4.5)
   - Layer 3: PromptAssembler (static + dynamic)
2. **8 Collectors Deep Dive**
   - DatabaseCollector, TemporalCollector, KnowledgeCollector
   - HistoryCollector, GraphitiCollector, HumanizationCollector
   - SocialCollector, ContinuityCollector
3. **ContextPackage Fields** (115+ typed fields by category)
4. **Token Budget Strategy** (tiered allocation)
5. **Parallel Execution Model** (asyncio.gather pattern)
6. **Error Handling & Fallbacks** (per-collector, tiered validation)
7. **Voice/Text Parity Gap** (CRITICAL: voice bypasses ContextEngine)
8. **Timeout Hierarchy** (45s generator, 120s agent, 30s Graphiti)
9. **NEEDS RETHINKING**: Graphiti issues, timeout concerns

**For Claude Code: Quick Entry Points**
```bash
# Find collector implementations:
rg "class.*Collector" nikita/context_engine/collectors/

# Find asyncio.gather pattern:
rg "asyncio\.gather" nikita/context_engine/ -A 3

# Find timeout configurations:
rg "timeout" nikita/context_engine/ --type py

# Trace voice bypass (CRITICAL):
rg "def get_context" nikita/agents/voice/server_tools.py -A 20
```

**C2 Container Architecture Diagram:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CONTEXT ENGINE ARCHITECTURE (C2)                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  LAYER 1: ContextEngine (engine.py:166)                                     │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐                           │
│  │Database │ │Temporal │ │Knowledge│ │ History │   8 collectors             │
│  │  5s     │ │   2s    │ │   2s    │ │   5s    │   run via                  │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘   asyncio.gather()        │
│       │          │          │          │           return_exceptions=True  │
│  ┌────┴────┐ ┌────┴────┐ ┌────┴────┐ ┌────┴────┐                           │
│  │Graphiti │ │Humanize │ │ Social  │ │Continuty│                           │
│  │ **30s** │ │   5s    │ │   3s    │ │   3s    │                           │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘                           │
│       └──────────┬┴──────────┬┴──────────┬┘                                │
│                  │           │           │                                  │
│                  v           v           v                                  │
│              ┌───────────────────────────────┐                              │
│              │      ContextPackage           │                              │
│              │   115+ typed fields           │                              │
│              │   (~5K tokens raw data)       │                              │
│              └──────────────┬────────────────┘                              │
│                             │                                               │
├─────────────────────────────┼───────────────────────────────────────────────┤
│  LAYER 2: PromptGenerator   │ (generator.py:287)                            │
│                             v                                               │
│              ┌───────────────────────────────┐                              │
│              │    Claude Sonnet 4.5          │                              │
│              │    45s timeout, 3 retries     │                              │
│              │    Template: generator.meta.md│                              │
│              │    Target: 3K-6K tokens       │                              │
│              └──────────────┬────────────────┘                              │
│                             │                                               │
│                             v                                               │
│              ┌───────────────────────────────┐                              │
│              │       PromptBundle            │                              │
│              │   text: 6K-12K tokens         │                              │
│              │   voice: 800-1500 tokens      │                              │
│              └──────────────┬────────────────┘                              │
│                             │                                               │
├─────────────────────────────┼───────────────────────────────────────────────┤
│  LAYER 3: PromptAssembler   │ (assembler.py:100)                            │
│                             v                                               │
│              ┌───────────────────────────────┐                              │
│              │  Static: persona + chapter    │                              │
│              │  Dynamic: generated blocks    │                              │
│              │  Validation: 80% coverage min │                              │
│              └───────────────────────────────┘                              │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│  ⚠️  VOICE/TEXT PARITY GAP                                                  │
│                                                                              │
│  Text Agent:  Uses ContextEngine → PromptGenerator → full 115 fields       │
│  Voice Agent: BYPASSES ContextEngine at server_tools.py:331-337            │
│               Uses direct repository queries → subset of fields             │
│                                                                              │
│  Impact: Voice agent has less context, inconsistent behavior                │
│  Fix: Wire ContextEngine.collect() into voice get_context server tool      │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Collector Details Table with Fallbacks:**
| # | Collector | Timeout | Retries | Data Source | Fallback Behavior | Key Fields |
|---|-----------|---------|---------|-------------|-------------------|------------|
| 1 | Database | 5s | 2 | Supabase | Use cached user data | user, metrics, vices, engagement |
| 2 | Temporal | 2s | 1 | Calculated | Use UTC defaults | local_time, hours_since_last |
| 3 | Knowledge | 2s | 1 | YAML files | Use base persona | persona_canon, chapter_behavior |
| 4 | History | 5s | 2 | Supabase | Empty history | threads, thoughts, summaries |
| 5 | Graphiti | **30s** | 2 | Neo4j | Empty facts (graceful) | user_facts, episodes, events |
| 6 | Humanization | 5s | 2 | Life sim | Neutral mood | mood_4d, conflict, daily_events |
| 7 | Social | 3s | 2 | Supabase | No friends | friends, best_friend |
| 8 | Continuity | 3s | 2 | Supabase | No past prompts | past_prompts |

---

### D5: DATABASE_SCHEMA.md (450-550 lines)

```yaml
---
title: "Database Schema & Data Model"
type: reference
context_priority: high
primary_files:
  - nikita/db/models/user.py:all
  - nikita/db/models/conversation.py:all
  - nikita/db/migrations/versions/:all
related_adrs:
  - specs/009-database-infrastructure
needs_rethinking:
  - Messages stored as JSONB in conversations table
  - Missing RLS on some newer tables
  - engagement_state enum duplicated in multiple places
---
```

Data model documentation:

**Required Sections:**
1. **Supabase PostgreSQL** (22 tables)
   - Core entities (users, user_metrics, user_vice_preferences)
   - Conversations (conversations, conversation_threads, nikita_thoughts)
   - Game mechanics (score_history, engagement_state, engagement_history)
   - Scheduling (scheduled_events, scheduled_touchpoints)
   - Onboarding (user_profiles, user_backstories, user_social_circles)
   - Operations (rate_limits, job_executions, generated_prompts)
2. **Neo4j/Graphiti** (3 knowledge graphs)
   - nikita_{user_id} - Her simulated life
   - user_{user_id} - Facts about the player
   - relationship_{user_id} - Shared history
3. **Data Split Rationale** (what goes where and why)
4. **RLS Policies** (row-level security implementation)
5. **Key Migrations** (schema evolution timeline)
6. **NEEDS RETHINKING**: Messages as JSONB, missing RLS on new tables

**For Claude Code: Quick Entry Points**
```bash
# Find all SQLAlchemy models:
rg "class.*Base\)" nikita/db/models/ --type py

# Find migrations:
fd ".py" nikita/db/migrations/versions/

# Check RLS policies:
rg "CREATE POLICY\|RLS" nikita/db/migrations/
```

**ASCII ERD Required:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CORE ENTITY RELATIONSHIPS                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                           ┌─────────────────┐                               │
│                           │   auth.users    │                               │
│                           │  (Supabase Auth)│                               │
│                           └────────┬────────┘                               │
│                                    │ id                                      │
│                                    v                                         │
│  ┌─────────────────────────────────┴─────────────────────────────────────┐  │
│  │                              users                                     │  │
│  │  id, telegram_id, phone, chapter, relationship_score, game_status     │  │
│  │  onboarding_status, cached_voice_prompt, graphiti_group_id            │  │
│  └───────────────┬───────────────┬───────────────┬───────────────────────┘  │
│                  │               │               │                           │
│         ┌────────┴──────┐ ┌──────┴──────┐ ┌─────┴───────┐                   │
│         v               v v             v v             v                    │
│  ┌─────────────┐ ┌───────────────┐ ┌────────────┐ ┌──────────────┐          │
│  │user_metrics │ │conversations  │ │engagement  │ │user_backstory│          │
│  │intimacy     │ │messages JSONB │ │_state      │ │how_we_met    │          │
│  │passion      │ │score_delta    │ │multiplier  │ │the_moment    │          │
│  │trust        │ │status         │ │clingy_days │ │unresolved    │          │
│  │secureness   │ │               │ │            │ │_hook         │          │
│  └─────────────┘ └───────┬───────┘ └────────────┘ └──────────────┘          │
│                          │                                                   │
│           ┌──────────────┼──────────────┬──────────────┐                    │
│           v              v              v              v                     │
│    ┌─────────────┐ ┌───────────┐ ┌───────────┐ ┌───────────────┐            │
│    │conversation │ │nikita_    │ │generated_ │ │message_       │            │
│    │_threads     │ │thoughts   │ │prompts    │ │embeddings     │            │
│    │type, status │ │inner life │ │debug log  │ │pgvector 1536d │            │
│    └─────────────┘ └───────────┘ └───────────┘ └───────────────┘            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### D6: INTEGRATIONS.md (600-700 lines)

```yaml
---
title: "External Integrations"
type: how-to
context_priority: high
primary_files:
  - nikita/platforms/telegram/message_handler.py:all
  - nikita/platforms/telegram/registration_handler.py:all
  - nikita/api/routes/telegram.py:all
  - nikita/agents/voice/inbound.py:all
related_adrs:
  - specs/002-telegram-integration
  - specs/007-voice-agent
needs_rethinking:
  - Background task pattern (webhook → task → handler) adds latency
---
```

External system integration documentation:

**Required Sections:**
1. **Telegram Integration**
   - Webhook flow (message → background task → handler → response)
   - Handler chain (CommandHandler → OnboardingHandler → MessageHandler)
   - Rate limiting (burst + daily caps with rate_limits table)
   - In-character error messages
2. **ElevenLabs Voice Integration**
   - Server Tools pattern (get_context, get_memory, score_turn, update_memory)
   - Dynamic variables (visible vs secret__)
   - Inbound call handling (accept/reject with dynamic_variables)
   - Tool descriptions (WHEN/HOW/RETURNS/ERROR format)
3. **Circuit Breaker Patterns**
   - External service timeouts
   - Graceful degradation strategies
4. **Error Handling Patterns**
   - Session recovery (rollback on exception)
   - Graceful degradation (fallback responses)
   - Timeout handling with fallback data

**For Claude Code: Quick Entry Points**
```bash
# Find handler chain:
rg "class.*Handler" nikita/platforms/telegram/ --type py

# Find rate limiting:
rg "rate_limit" nikita/db/models/ nikita/api/

# Find webhook signature validation:
rg "signature\|verify" nikita/platforms/telegram/
```

**ASCII Webhook Flow with Handler Chain:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       TELEGRAM WEBHOOK FLOW WITH HANDLER CHAIN               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                   │
│  │  Telegram   │────>│  FastAPI    │────>│ Background  │                   │
│  │  Servers    │     │  /webhook   │     │  Task       │                   │
│  └─────────────┘     └──────┬──────┘     └──────┬──────┘                   │
│                             │                    │                          │
│                             v                    v                          │
│                       Return 200          ┌─────────────────────────┐       │
│                       immediately         │   HANDLER CHAIN         │       │
│                       (< 1 second)        │                         │       │
│                                           │  1. CommandHandler      │       │
│                                           │     ├─ /start           │       │
│                                           │     ├─ /help            │       │
│                                           │     └─ /status          │       │
│                                           │                         │       │
│                                           │  2. OnboardingHandler   │       │
│                                           │     ├─ OTP validation   │       │
│                                           │     └─ Profile gate     │       │
│                                           │                         │       │
│                                           │  3. MessageHandler      │       │
│                                           │     ├─ Game-over check  │       │
│                                           │     ├─ Boss-fight check │       │
│                                           │     ├─ TextAgent call   │       │
│                                           │     └─ Post-processing  │       │
│                                           └───────────┬─────────────┘       │
│                                                       │                     │
│                                                       v                     │
│                                           ┌───────────────────────┐         │
│                                           │  Delayed Delivery     │         │
│                                           │  (typing simulation)  │         │
│                                           └───────────────────────┘         │
│                                                                              │
│  Rate Limiting (rate_limits table):                                         │
│  ├── Burst: 10 messages/minute                                              │
│  ├── Daily: 100 messages/day                                                │
│  └── Cooldown: 5 seconds between messages                                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### D7: AUTHENTICATION.md (350-450 lines)

```yaml
---
title: "Authentication Flow"
type: how-to
context_priority: medium
primary_files:
  - nikita/platforms/telegram/registration_handler.py:all
  - nikita/db/models/user.py:50-100
  - nikita/api/routes/onboarding.py:all
related_adrs:
  - specs/015-onboarding-fix
needs_rethinking:
  - Magic link deprecated but code still exists
---
```

Authentication flow documentation:

**Required Sections:**
1. **OTP Flow** (complete from /start to session)
2. **Session Management** (Supabase Auth integration)
3. **Telegram ID Linking** (telegram_id ↔ users.id)
4. **Phone Number Linking** (for voice)
5. **Security Measures** (max attempts, expiration, webhook signature)

**For Claude Code: Quick Entry Points**
```bash
# Find OTP handling:
rg "verify_otp\|signInWithOtp" nikita/ --type py

# Find pending registration:
rg "pending_registration" nikita/db/

# Find auth middleware:
rg "get_current_user\|Authorization" nikita/api/
```

**ASCII Auth Flow:**
```
┌────────────────────────────────────────────────────────────────────────────┐
│                           OTP AUTHENTICATION FLOW                           │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  User                  Backend                    Supabase                  │
│   │                       │                          │                      │
│   │  /start               │                          │                      │
│   │──────────────────────>│                          │                      │
│   │                       │                          │                      │
│   │  "Enter email"        │                          │                      │
│   │<──────────────────────│                          │                      │
│   │                       │                          │                      │
│   │  user@email.com       │                          │                      │
│   │──────────────────────>│                          │                      │
│   │                       │  signInWithOtp(email)    │                      │
│   │                       │─────────────────────────>│                      │
│   │                       │                          │  Send OTP email      │
│   │                       │<─────────────────────────│                      │
│   │                       │                          │                      │
│   │  pending_registration │                          │                      │
│   │  created (10min TTL)  │                          │                      │
│   │                       │                          │                      │
│   │  123456 (OTP code)    │                          │                      │
│   │──────────────────────>│                          │                      │
│   │                       │  verifyOtp(email, code)  │                      │
│   │                       │─────────────────────────>│                      │
│   │                       │                          │                      │
│   │                       │  user + session          │                      │
│   │                       │<─────────────────────────│                      │
│   │                       │                          │                      │
│   │                       │  Create/link user        │                      │
│   │                       │  Delete pending_reg      │                      │
│   │                       │                          │                      │
│   │  "Welcome! Onboard?"  │                          │                      │
│   │<──────────────────────│                          │                      │
│   │                       │                          │                      │
└────────────────────────────────────────────────────────────────────────────┘
```

---

### D8: ANTI_PATTERNS.md (350-450 lines)

```yaml
---
title: "Anti-Patterns & Lessons Learned"
type: explanation
context_priority: high
primary_files:
  - nikita/context/post_processor.py:all
  - nikita/memory/graphiti_client.py:all
related_adrs:
  - specs/037-pipeline-refactor
needs_rethinking:
  - This entire document is about what to rethink
---
```

What NOT to do in a rebuild:

**Required Sections:**
1. **Graphiti/Neo4j Issues**
   - 60-83 second cold starts (Neo4j Aura free tier pauses)
   - Connection pool exhaustion under load
   - Consider: Regular RAG with vector DB instead
2. **Portal Problems** (SKIP in rebuild)
   - Vercel deployment issues
   - SSR complexity
   - Recommendation: Focus on Telegram + Voice only
3. **Pipeline Lessons (NEW)**
   - 11-stage pipeline is complex but necessary
   - Circuit breaker pattern essential
   - Async isolation in tests is tricky
4. **Async Testing Pitfalls (NEW)**
   - NullPool required for function-scoped fixtures
   - Event loop isolation critical
   - Session "prepared state" errors from improper cleanup
5. **Timeout Hierarchy Issues (NEW)**
   - Neo4j 30s timeout vs 60-83s cold start
   - LLM 45s timeout + 3 retries = 135s worst case
   - Cloud Run 300s vs pipeline potential 180s+
6. **Lessons from 41 Specs**
   - What worked: SDD workflow, TDD enforcement
   - What didn't: Over-engineering humanization specs
   - What to simplify: 8 humanization specs could be 2-3
7. **Performance Pitfalls**
   - Messages as JSONB (use separate table)
   - Missing indexes on frequently queried columns
   - LLM timeout handling (streaming better than blocking)

**For Claude Code: Quick Entry Points**
```bash
# Find timeout configurations:
rg "timeout\s*=" nikita/ --type py | head -20

# Find circuit breaker patterns:
rg "CircuitBreaker\|fallback" nikita/context/

# Find async test fixtures:
rg "async_session\|NullPool" tests/
```

---

### D9: ARCHITECTURE_ALTERNATIVES.md (500-600 lines)

```yaml
---
title: "Architecture Alternatives Research"
type: reference
context_priority: medium
primary_files: []
related_adrs:
  - memory/architecture.md
needs_rethinking:
  - All current choices should be reconsidered for rebuild
---
```

Research-backed alternatives:

**Required Sections:**
1. **Memory Systems Comparison**
   | System | Approach | Pros | Cons | Recommendation |
   |--------|----------|------|------|----------------|
   | Graphiti (current) | Temporal KG | Relationship tracking | Neo4j reliability | Keep for relationships |
   | Zep | Session memory | Simple, fast | No temporal | Consider for simplification |
   | Mem0 | Open-source LTM | Flexible | Self-hosted | Alternative to Graphiti |
   | Simple RAG | Vector DB | Easy to implement | No relationships | Add for static knowledge |

2. **Agent Frameworks Comparison**
   | Framework | Best For | Pros | Cons | Nikita Fit |
   |-----------|----------|------|------|------------|
   | Pydantic AI (current) | Type-safe | Validation, structured | Tool binding | KEEP |
   | LangGraph | Complex flows | Visual DAG | Bloated | Consider for orchestration |
   | CrewAI | Multi-agent | Built-in memory | Overkill | NOT NEEDED |
   | AutoGen | Async agents | Event-driven | Complex | SKIP |

3. **Voice Platform Comparison**
   | Platform | Quality | Server Tools | Cost | Recommendation |
   |----------|---------|--------------|------|----------------|
   | ElevenLabs (current) | Best (37/100) | Native | $0.30/min | KEEP |
   | OpenAI Realtime | Good | Function calling | $0.30/min | Alternative |
   | PlayHT | Lower (19/100) | API | $0.08/min | Budget option |

4. **Simplification Recommendations**
   - If rebuilding simpler: Zep + Pydantic AI + ElevenLabs
   - If rebuilding equivalent: Keep current stack, fix Neo4j reliability
   - If rebuilding better: Hybrid (Graphiti + RAG), paid Neo4j tier

---

### D10: ONBOARDING.md (500-600 lines)

```yaml
---
title: "Voice-First Onboarding"
type: tutorial
context_priority: high
primary_files:
  - nikita/onboarding/meta_nikita.py:all
  - nikita/onboarding/handoff.py:all
  - nikita/agents/voice/server_tools.py:all
related_adrs:
  - specs/028-voice-onboarding
needs_rethinking:
  - Text fallback is minimal
  - Server tool configuration drift with ElevenLabs dashboard
---
```

Voice-first onboarding documentation:

**Required Sections:**
1. **Meta-Nikita Agent** (ElevenLabs agent for onboarding)
2. **Profile Collection** (what data is gathered)
3. **Backstory Generation** (venue, how_we_met, the_moment)
4. **Social Circle Creation** (Nikita's friends adapted to player)
5. **Handoff to Nikita** (transition from Meta-Nikita to Nikita)
6. **Text Fallback** (for users who skip voice)
7. **Server Tool Details** (implementation specifics)

**For Claude Code: Quick Entry Points**
```bash
# Find Meta-Nikita agent config:
rg "META_NIKITA\|meta_nikita" nikita/config/

# Find profile storage:
rg "user_profile\|user_backstory" nikita/db/models/

# Find handoff logic:
rg "handoff\|complete_onboarding" nikita/onboarding/
```

**ASCII Onboarding Flow:**
```
┌────────────────────────────────────────────────────────────────────────────┐
│                        VOICE ONBOARDING FLOW                                │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                   │
│  │  OTP Done   │────>│ Voice/Text? │────>│   Voice     │                   │
│  └─────────────┘     └──────┬──────┘     └──────┬──────┘                   │
│                             │                    │                          │
│                             │                    v                          │
│                        ┌────┴────┐       ┌──────────────┐                  │
│                        │  Text   │       │  Meta-Nikita │                  │
│                        │ Fallback│       │  (onboarding │                  │
│                        └────┬────┘       │   agent)     │                  │
│                             │            └──────┬───────┘                  │
│                             │                   │                          │
│                             │            ┌──────┴───────┐                  │
│                             │            │  Questions:  │                  │
│                             │            │  - City      │                  │
│                             │            │  - Scene     │                  │
│                             │            │  - Interests │                  │
│                             │            │  - Edge lvl  │                  │
│                             │            └──────┬───────┘                  │
│                             │                   │                          │
│                             │            ┌──────┴───────┐                  │
│                             │            │  Generate:   │                  │
│                             │            │  - Backstory │                  │
│                             │            │  - Friends   │                  │
│                             │            │  - First msg │                  │
│                             │            └──────┬───────┘                  │
│                             │                   │                          │
│                             v                   v                          │
│                      ┌──────────────────────────────────┐                  │
│                      │        Nikita Active             │                  │
│                      │  (onboarding_status: completed)  │                  │
│                      └──────────────────────────────────┘                  │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

---

### D11: GAME_ENGINE_MECHANICS.md (1000-1200 lines) **[NEW - CRITICAL]**

```yaml
---
title: "Game Engine Mechanics"
type: explanation
context_priority: critical
c4_level: component
primary_files:
  - nikita/engine/constants.py:10-50
  - nikita/engine/scoring/calculator.py:45-80
  - nikita/engine/scoring/analyzer.py:all
  - nikita/engine/chapters/state_machine.py:all
  - nikita/engine/chapters/judgment.py:all
  - nikita/engine/decay/calculator.py:30-60
  - nikita/engine/engagement/state_calculator.py:all
  - nikita/engine/vice/boundaries.py:all
related_adrs:
  - specs/003-scoring-engine
  - specs/004-chapter-boss-system
  - specs/005-decay-system
  - specs/006-vice-personalization
  - specs/014-engagement-model
needs_rethinking:
  - Boss judgment LLM reliability
  - Decay rates may be too aggressive in Ch4-5
  - Engagement multipliers need A/B testing
---
```

Complete game mechanics documentation covering all 5 core systems:

**Required Sections:**

**1. Scoring System (4 Metrics)**
```
┌────────────────────────────────────────────────────────────────────────────┐
│                           4-METRIC SCORING SYSTEM                           │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ResponseAnalyzer (analyzer.py)          ScoreCalculator (calculator.py)   │
│  ┌─────────────────────────────┐         ┌─────────────────────────────┐  │
│  │  Analyze player message     │         │  Calculate score deltas     │  │
│  │  for 4 metrics:             │────────>│  with engagement multiplier │  │
│  │                             │         │                             │  │
│  │  - Intimacy (emotional)     │         │  delta = base * multiplier  │  │
│  │  - Passion  (romantic)      │         │  multiplier = 0.5 to 1.5    │  │
│  │  - Trust    (reliability)   │         │                             │  │
│  │  - Secureness (commitment)  │         │  Store in score_history     │  │
│  └─────────────────────────────┘         └─────────────────────────────┘  │
│                                                                             │
│  Score Range per Metric: 0-25 (total possible: 100)                        │
│  Chapter Thresholds: Ch2=25, Ch3=35, Ch4=50, Ch5=65, Victory=80           │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

**2. Chapter Progression (5 Chapters)**
| Chapter | Name | Score Threshold | Decay Rate | Boss Trigger |
|---------|------|-----------------|------------|--------------|
| 1 | Curiosity | 0 | 0.8/hr | Score ≥ 25 |
| 2 | Testing | 25 | 0.6/hr | Score ≥ 35 |
| 3 | Connection | 35 | 0.5/hr | Score ≥ 50 |
| 4 | Commitment | 50 | 0.3/hr | Score ≥ 65 |
| 5 | Love | 65 | 0.2/hr | Score ≥ 80 (Victory) |

**3. Boss Encounters (Chapter Transitions)**
```
┌────────────────────────────────────────────────────────────────────────────┐
│                           BOSS ENCOUNTER FLOW                               │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐               │
│  │ Score ≥      │────>│ Boss Fight   │────>│ BossJudgment │               │
│  │ Threshold    │     │ Triggered    │     │ (LLM call)   │               │
│  └──────────────┘     └──────────────┘     └──────┬───────┘               │
│                                                    │                        │
│                                           ┌───────┴────────┐               │
│                                           v                v               │
│                                      [PASS]            [FAIL]              │
│                                           │                │               │
│                                           v                v               │
│                                      Advance         Attempt++             │
│                                      Chapter         (max 3)               │
│                                           │                │               │
│                                           │         ┌──────┴──────┐        │
│                                           │         v             v        │
│                                           │   Attempt < 3    Attempt = 3   │
│                                           │         │             │        │
│                                           │         v             v        │
│                                           │    Try Again      GAME OVER    │
│                                           │                                │
│                                           v                                │
│                                      [VICTORY]                             │
│                                      (Ch5 boss)                            │
│                                                                             │
│  BossJudgment uses Claude Sonnet to evaluate player's response to          │
│  Nikita's ultimatum. Judgment criteria in judgment.py:45-80                │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

**4. Decay System (Inactivity Penalty)**
- Decay runs hourly via pg_cron job
- Rate varies by chapter (higher chapters = less decay)
- Grace period: 6 hours after last message
- Formula: `new_score = current_score - (decay_rate * hours_since_grace)`

**5. Vice System (Personality Calibration)**
- 8 vice categories with tolerance bands
- Player-specific calibration via onboarding
- Boundaries soft (warn) and hard (refuse)
- Vice detection in post-processing pipeline

**6. Engagement System (6 States)**
| State | Definition | Multiplier | Detection |
|-------|------------|------------|-----------|
| OPTIMAL | Balanced messaging | 1.0x | Base state |
| ENGAGED | Active conversation | 1.2x | 3+ msgs/hour |
| CLINGY | Too many messages | 0.7x | 10+ msgs/hour |
| DISTANT | Too few messages | 0.8x | <1 msg/day |
| RECOVERING | Returning from distant | 0.9x | First msg after gap |
| AT_RISK | Near game over | 1.5x | Score < 15 |

**For Claude Code: Quick Entry Points**
```bash
# Find scoring algorithm:
rg "def calculate_score\|def analyze" nikita/engine/scoring/

# Find chapter thresholds:
rg "CHAPTER_THRESHOLDS\|BOSS_THRESHOLDS" nikita/engine/constants.py

# Find decay rates:
rg "DECAY_RATES\|decay_rate" nikita/engine/

# Find boss judgment:
rg "class BossJudgment\|_call_llm" nikita/engine/chapters/judgment.py

# Find engagement states:
rg "class EngagementState\|StateCalculator" nikita/engine/engagement/

# Find vice boundaries:
rg "ViceBoundary\|tolerance" nikita/engine/vice/
```

---

### D12: PIPELINE_STAGES.md (800-1000 lines) **[NEW - CRITICAL]**

```yaml
---
title: "Post-Processing Pipeline Stages"
type: explanation
context_priority: critical
c4_level: component
primary_files:
  - nikita/context/stages/base.py:100-150
  - nikita/context/stages/ingestion.py:all
  - nikita/context/stages/extraction.py:all
  - nikita/context/stages/psychology.py:all
  - nikita/context/stages/narrative_arcs.py:all
  - nikita/context/stages/threads.py:all
  - nikita/context/stages/thoughts.py:all
  - nikita/context/stages/graph_updates.py:all
  - nikita/context/post_processor.py:all
related_adrs:
  - specs/037-pipeline-refactor
  - specs/031-post-processing-unification
needs_rethinking:
  - 11 stages may be over-engineered
  - Some stages have interdependencies that complicate error handling
  - Consider reducing to 5-6 core stages
---
```

Complete documentation of the 11-stage async post-processing pipeline:

**C3 Component Diagram:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      POST-PROCESSING PIPELINE (C3)                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  PostProcessor.process_conversation() orchestrates 11 stages:               │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ PHASE 1: INGESTION                                                   │   │
│  │ ┌─────────────┐                                                      │   │
│  │ │ 1. Ingest   │  Pair user/assistant messages, validate structure   │   │
│  │ │    Stage    │  nikita/context/stages/ingestion.py                 │   │
│  │ └─────────────┘                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                               │
│                              v                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ PHASE 2: EXTRACTION (Parallel)                                       │   │
│  │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                     │   │
│  │ │ 2. Entity   │ │ 3. Vice     │ │ 4. Psych    │                     │   │
│  │ │    Extract  │ │    Detect   │ │    Insights │                     │   │
│  │ │  (LLM call) │ │  (LLM call) │ │  (LLM call) │                     │   │
│  │ └─────────────┘ └─────────────┘ └─────────────┘                     │   │
│  │ extraction.py   vice_processing.py  psychology.py                    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                               │
│                              v                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ PHASE 3: MEMORY UPDATES (Parallel)                                   │   │
│  │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐    │   │
│  │ │ 5. Neo4j    │ │ 6. Threads  │ │ 7. Thoughts │ │ 8. Narrative│    │   │
│  │ │    Graph    │ │    Update   │ │    Generate │ │    Arcs     │    │   │
│  │ │  (Graphiti) │ │  (Supabase) │ │  (LLM call) │ │  (Supabase) │    │   │
│  │ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘    │   │
│  │ graph_updates.py threads.py    thoughts.py     narrative_arcs.py   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                               │
│                              v                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ PHASE 4: ROLLUP & CACHE                                              │   │
│  │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                     │   │
│  │ │ 9. Summary  │ │ 10. Voice   │ │ 11. Final   │                     │   │
│  │ │    Rollups  │ │     Cache   │ │    ization  │                     │   │
│  │ │  (LLM call) │ │  (Supabase) │ │  (Supabase) │                     │   │
│  │ └─────────────┘ └─────────────┘ └─────────────┘                     │   │
│  │ summary_rollups.py voice_cache.py finalization.py                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  Circuit Breaker Pattern (base.py:100-150):                                 │
│  ├── Each stage has timeout + retry configuration                           │
│  ├── Failures logged but don't block pipeline                               │
│  ├── asyncio.gather(return_exceptions=True) for parallel stages            │
│  └── Job execution logged to job_executions table                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Stage Details Table:**
| # | Stage | Timeout | LLM? | Data Source | Output | Fallback |
|---|-------|---------|------|-------------|--------|----------|
| 1 | Ingestion | 5s | No | Conversation | MessagePairs | Skip conv |
| 2 | Extraction | 30s | Yes | Messages | Entities | Empty list |
| 3 | ViceProcessing | 30s | Yes | Messages | ViceDetection | No vices |
| 4 | Psychology | 30s | Yes | Messages | Insights | Generic |
| 5 | GraphUpdates | 45s | No | Entities | Neo4j facts | Skip update |
| 6 | Threads | 10s | No | Messages | Thread records | No threads |
| 7 | Thoughts | 30s | Yes | Context | NikitaThought | No thought |
| 8 | NarrativeArcs | 15s | No | Psych | Arc records | Skip |
| 9 | SummaryRollups | 45s | Yes | History | Summaries | Stale |
| 10 | VoiceCache | 10s | No | Prompts | Cache update | Stale |
| 11 | Finalization | 5s | No | All | Status update | Mark failed |

**For Claude Code: Quick Entry Points**
```bash
# Find all stage implementations:
fd ".py" nikita/context/stages/

# Find stage base class:
rg "class PipelineStage\|class StageContext" nikita/context/stages/base.py

# Find orchestrator:
rg "async def process_conversation" nikita/context/post_processor.py -A 20

# Find circuit breaker:
rg "CircuitBreaker\|return_exceptions" nikita/context/

# Find job logging:
rg "job_execution" nikita/db/models/ nikita/context/
```

---

### D13: TESTING_STRATEGY.md (500-600 lines) **[NEW - HIGH]**

```yaml
---
title: "Testing Strategy & Patterns"
type: how-to
context_priority: high
primary_files:
  - tests/conftest.py:20-50
  - tests/context/stages/conftest.py:all
  - tests/db/integration/conftest.py:all
  - tests/smoke/test_deployment.py:all
related_adrs:
  - memory/testing-patterns.md
needs_rethinking:
  - Async test isolation is fragile
  - Integration tests require manual Supabase setup
  - E2E tests depend on external services availability
---
```

Complete testing documentation for reproducing the test suite:

**Required Sections:**

**1. Test Organization (4300+ tests)**
```
tests/
├── conftest.py              # Global fixtures, singleton cache clearing
├── agents/
│   ├── text/               # 156 tests (agent, history, token_budget)
│   └── voice/              # 186 tests (server_tools, inbound, transcript)
├── context/
│   ├── stages/             # 133 tests (11 stage test files)
│   └── test_*.py           # 160+ tests (post_processor, pipeline)
├── context_engine/         # 326 tests (engine, collectors, validators)
├── db/
│   ├── models/             # 60 tests
│   ├── repositories/       # 80 tests
│   └── integration/        # 40 tests (real DB)
├── e2e/                    # 25 tests (full flow)
├── engine/                 # 400+ tests (scoring, chapters, decay, vice)
└── smoke/                  # 5 tests (deployment health)
```

**2. Async Testing Patterns (CRITICAL)**
```python
# CORRECT: Function-scoped async fixtures with NullPool
@pytest.fixture
async def async_session():
    engine = create_async_engine(
        DATABASE_URL,
        poolclass=NullPool,  # CRITICAL: prevents connection leaks
    )
    async with AsyncSession(engine) as session:
        yield session
    await engine.dispose()

# WRONG: Module-scoped async fixtures
@pytest.fixture(scope="module")  # BAD: causes "prepared state" errors
async def shared_session():
    ...
```

**3. Fixture Organization (Users at Different Game States)**
```python
# tests/conftest.py patterns
@pytest.fixture
def new_user():
    """User who just completed OTP, no onboarding"""
    return User(chapter=1, relationship_score=0, onboarding_status="pending")

@pytest.fixture
def chapter3_user():
    """User in middle of game"""
    return User(chapter=3, relationship_score=42, onboarding_status="completed")

@pytest.fixture
def boss_fight_user():
    """User in active boss encounter"""
    return User(chapter=2, relationship_score=35, in_boss_fight=True)

@pytest.fixture
def game_over_user():
    """User who lost"""
    return User(chapter=2, game_status="lost", boss_attempts=3)
```

**4. Stage Mocking Strategies**
```python
# Mock repositories (don't hit real DB)
@pytest.fixture
def mock_user_repo():
    repo = AsyncMock(spec=UserRepository)
    repo.get_by_id.return_value = make_test_user()
    return repo

# Mock external services (Neo4j, LLM)
@pytest.fixture
def mock_graphiti():
    client = AsyncMock(spec=NikitaMemory)
    client.search_memory.return_value = []
    return client
```

**5. Integration Test Setup**
```bash
# Required: Local Supabase running
supabase start
supabase db reset

# Run integration tests
pytest tests/db/integration/ -v

# Environment variable required
export DATABASE_URL_LOCAL="postgresql://..."
```

**For Claude Code: Quick Entry Points**
```bash
# Find fixture definitions:
rg "^@pytest.fixture" tests/ --type py | head -30

# Find async test patterns:
rg "async def test_" tests/ --type py | head -20

# Find mock patterns:
rg "AsyncMock\|MagicMock" tests/ --type py | head -20

# Run specific test file:
pytest tests/context/stages/test_ingestion.py -v
```

---

### D14: DEPLOYMENT_OPERATIONS.md (600-700 lines) **[NEW - HIGH]**

```yaml
---
title: "Deployment & Operations"
type: how-to
context_priority: high
primary_files:
  - nikita/config/settings.py:all
  - nikita/db/migrations/versions/:all
  - Dockerfile:all
  - .gcloudignore:all
related_adrs:
  - memory/architecture.md
needs_rethinking:
  - Cloud Run cold starts can be 10-30s
  - Neo4j Aura pauses after 3 days idle (free tier)
  - No automated rollback strategy
---
```

Complete deployment and operations documentation:

**Required Sections:**

**1. Cloud Run Setup**
```bash
# Initial deployment
gcloud config set project gcp-transcribe-test
gcloud run deploy nikita-api \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300s \
  --min-instances 0 \
  --max-instances 10
```

**2. Environment Variables (20+ required)**
| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| DATABASE_URL | Supabase PostgreSQL | Yes | postgresql://... |
| NEO4J_URI | Neo4j Aura connection | Yes | neo4j+s://xxx.databases.neo4j.io |
| NEO4J_USERNAME | Neo4j credentials | Yes | neo4j |
| NEO4J_PASSWORD | Neo4j credentials | Yes | (secret) |
| ANTHROPIC_API_KEY | Claude API | Yes | sk-ant-... |
| ELEVENLABS_API_KEY | Voice API | Yes | (secret) |
| TELEGRAM_BOT_TOKEN | Bot credentials | Yes | 123456:ABC... |
| SUPABASE_URL | Supabase project | Yes | https://xxx.supabase.co |
| SUPABASE_KEY | Supabase anon key | Yes | eyJ... |
| SUPABASE_SERVICE_ROLE_KEY | Supabase admin | Yes | eyJ... |
| ELEVENLABS_AGENT_ID | Main Nikita agent | Yes | agent_xxx |
| ELEVENLABS_AGENT_META_NIKITA | Onboarding agent | Yes | agent_xxx |
| CONTEXT_ENGINE_FLAG | enabled/disabled | No | enabled |

**3. Database Migration Strategy**
```bash
# Generate migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1

# Migration files location
nikita/db/migrations/versions/
```

**4. Health Check Endpoints**
| Endpoint | Purpose | Expected Response |
|----------|---------|-------------------|
| GET /health | Basic liveness | `{"status": "healthy"}` |
| GET /health/deep | Full dependency check | `{"status": "healthy", "db": "ok", "neo4j": "ok"}` |

**5. Observability Setup**
```python
# Structured logging (already configured)
import structlog
logger = structlog.get_logger()
logger.info("event", user_id=user_id, action="message_received")

# Cloud Run logs available via:
gcloud run logs read nikita-api --region us-central1
```

**6. Cold Start Handling**
- Cloud Run timeout: 300s (5 min)
- Neo4j Aura cold start: 60-83s
- ContextEngine total timeout: 120s
- Rationale: 60s Neo4j + 45s LLM + buffer = 120s max

**For Claude Code: Quick Entry Points**
```bash
# Find all environment variables:
rg "os\.getenv\|environ" nikita/config/settings.py

# Find migration files:
fd ".py" nikita/db/migrations/versions/

# Find health endpoints:
rg "@router.*health" nikita/api/routes/

# Check current deployment:
gcloud run services describe nikita-api --region us-central1
```

---

### D15: VOICE_IMPLEMENTATION.md (600-700 lines) **[NEW - HIGH]**

```yaml
---
title: "Voice Agent Implementation"
type: reference
context_priority: high
c4_level: component
primary_files:
  - nikita/agents/voice/server_tools.py:45-290
  - nikita/agents/voice/server_tools.py:331-337
  - nikita/agents/voice/inbound.py:all
  - nikita/agents/voice/models.py:all
related_adrs:
  - specs/007-voice-agent
  - specs/032-voice-agent-optimization
needs_rethinking:
  - Voice BYPASSES ContextEngine (server_tools.py:331-337)
  - Server tool configuration can drift from ElevenLabs dashboard
  - DynamicVariables schema must match ElevenLabs agent config exactly
---
```

Complete voice agent implementation documentation:

**Required Sections:**

**1. Server Tools (4 Tools)**

```
┌────────────────────────────────────────────────────────────────────────────┐
│                         VOICE SERVER TOOLS                                  │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────┐     ┌───────────────┐                                  │
│  │  get_context  │     │  get_memory   │                                  │
│  │               │     │               │                                  │
│  │  Returns:     │     │  Returns:     │                                  │
│  │  - user_name  │     │  - facts[]    │                                  │
│  │  - chapter    │     │  - threads[]  │                                  │
│  │  - score      │     │               │                                  │
│  │  - mood       │     │  Source:      │                                  │
│  │  - vices      │     │  Graphiti     │                                  │
│  │               │     │               │                                  │
│  │  ⚠️ BYPASSES  │     │               │                                  │
│  │  ContextEngine│     │               │                                  │
│  └───────────────┘     └───────────────┘                                  │
│                                                                             │
│  ┌───────────────┐     ┌───────────────┐                                  │
│  │  score_turn   │     │ update_memory │                                  │
│  │               │     │               │                                  │
│  │  Inputs:      │     │  Inputs:      │                                  │
│  │  - turn_text  │     │  - fact       │                                  │
│  │  - sentiment  │     │  - importance │                                  │
│  │               │     │               │                                  │
│  │  Returns:     │     │  Returns:     │                                  │
│  │  - deltas     │     │  - success    │                                  │
│  │  - new_score  │     │               │                                  │
│  └───────────────┘     └───────────────┘                                  │
│                                                                             │
│  Tool Descriptions follow WHEN/HOW/RETURNS/ERROR format                    │
│  See server_tools.py:45-150 for full descriptions                          │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

**2. Dynamic Variables (Visible vs Secret)**
```python
# models.py - DynamicVariables schema
class DynamicVariables(BaseModel):
    # Visible to ElevenLabs agent (in system prompt)
    user_id: str
    user_name: str
    chapter: int
    relationship_score: float
    nikita_mood: str
    hours_since_last: float

    # Secret (prefixed with secret__) - available to server tools only
    secret__api_key: str
    secret__session_id: str
```

**3. CRITICAL: Voice Bypasses ContextEngine**
```python
# server_tools.py:331-337 - THIS IS THE PROBLEM
async def get_context(user_id: str) -> dict:
    # Direct repository access - NOT using ContextEngine
    user = await user_repo.get_by_id(user_id)
    metrics = await metrics_repo.get_by_user_id(user_id)

    # Returns ~20 fields vs ContextEngine's 115 fields
    return {
        "user_name": user.name,
        "chapter": user.chapter,
        # Missing: humanization, social circle, narrative arcs, etc.
    }
```

**4. Inbound Call Handling**
```
┌────────────────────────────────────────────────────────────────────────────┐
│                       INBOUND VOICE CALL FLOW                               │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Phone Call              Backend                      ElevenLabs           │
│      │                      │                             │                │
│      │  Incoming call       │                             │                │
│      │─────────────────────>│                             │                │
│      │                      │  /voice/pre-call            │                │
│      │                      │  (lookup user by phone)     │                │
│      │                      │                             │                │
│      │                      │  dynamic_variables          │                │
│      │                      │─────────────────────────────>│               │
│      │                      │                             │                │
│      │                      │  Accept call                │                │
│      │<─────────────────────│                             │                │
│      │                      │                             │                │
│      │                      │  Server tool calls          │                │
│      │                      │<────────────────────────────│               │
│      │                      │  (get_context, score_turn)  │                │
│      │                      │────────────────────────────>│               │
│      │                      │                             │                │
│      │  Hang up             │                             │                │
│      │─────────────────────>│  /voice/webhook             │                │
│      │                      │  (store transcript, score)  │                │
│      │                      │                             │                │
└────────────────────────────────────────────────────────────────────────────┘
```

**5. Error Handling in Voice**
- Server tool failures return graceful error messages
- Transcript parsing has LLM fallback
- Call webhook retries on failure (3 attempts)

**For Claude Code: Quick Entry Points**
```bash
# Find server tool implementations:
rg "async def (get_context|get_memory|score_turn|update_memory)" nikita/agents/voice/

# Find dynamic variables schema:
rg "class DynamicVariables" nikita/agents/voice/models.py -A 20

# Find voice bypass (CRITICAL):
rg "user_repo\.get\|metrics_repo\.get" nikita/agents/voice/server_tools.py

# Find inbound call handling:
rg "pre_call\|webhook" nikita/api/routes/voice.py
```

---

## FORMAT REQUIREMENTS

### ASCII Diagrams
- Use box-drawing characters: ┌ ┐ └ ┘ │ ─ ┬ ┴ ├ ┤ ┼
- Use arrows: → ← ↑ ↓ ↔ ↕
- NO Mermaid syntax (not compatible with all viewers)
- NO image references (must be self-contained)

### Documentation Style
- **YAML frontmatter** for every deliverable (Claude Code optimization)
- **Quick Entry Points** section with rg/fd commands
- Bullet points over prose (easier to scan)
- Tables for comparisons (use markdown tables)
- `file:line` references for key code locations (50+ per doc)
- "Decision Rationale" sections explaining WHY choices were made
- "NEEDS RETHINKING" markers for problematic areas
- **CoD^Σ evidence chains** for claims

### Diátaxis Framework Organization
| Type | Documents | Purpose |
|------|-----------|---------|
| Tutorial | D3, D10 | Learning by following |
| How-To | D6, D7, D13, D14 | Goal-oriented tasks |
| Explanation | D2, D4, D8, D11, D12 | Conceptual understanding |
| Reference | D1, D5, D9, D15 | API specs and facts |

### C4 Model Requirements
| Level | Diagram | Document |
|-------|---------|----------|
| C1 Context | System overview | D2 |
| C2 Container | Service architecture | D4 |
| C3 Component | Stage pipeline, game engine, voice | D11, D12, D15 |

### Validation Checklist (per document)
- [ ] YAML frontmatter present with all fields
- [ ] Quick Entry Points section with rg/fd commands
- [ ] Self-contained (readable without other docs)
- [ ] Contains ≥1 ASCII diagram
- [ ] References source files with file:line (50+)
- [ ] Notes what new implementation should do differently
- [ ] No Portal references (excluded from scope)
- [ ] No assumption that Graphiti is correct choice
- [ ] Diátaxis type assigned and appropriate
- [ ] C4 level assigned (where applicable)

---

## ANTI-PATTERNS TO AVOID

1. **Don't reproduce current implementation exactly** - This is knowledge transfer, not code documentation
2. **Don't include Portal details** - User explicitly said "Portal sucks"
3. **Don't assume Graphiti is the right choice** - Document alternatives
4. **Don't skip pain points** - These are the most valuable learnings
5. **Don't use Mermaid diagrams** - Use ASCII for universal compatibility
6. **Don't write prose when tables work** - Scannable > readable
7. **Don't skip YAML frontmatter** - Critical for Claude Code context efficiency
8. **Don't omit file:line references** - Evidence-based documentation

---

## EXECUTION INSTRUCTIONS

### Step 1: Launch Research Subagents (Parallel - 8 Agents)

```javascript
// Launch 8 code-analyzer/prompt-researcher agents in parallel
// Original 4:
Task(subagent_type="code-analyzer", prompt="Context engine deep dive...")
Task(subagent_type="code-analyzer", prompt="Integration patterns...")
Task(subagent_type="code-analyzer", prompt="Database schema...")
Task(subagent_type="prompt-researcher", prompt="External research...")

// NEW 4 for v2:
Task(subagent_type="code-analyzer", prompt="Game engine mechanics - scoring, decay, chapters, boss, engagement...")
Task(subagent_type="code-analyzer", prompt="Pipeline stages - all 11 stages, circuit breaker, error handling...")
Task(subagent_type="code-analyzer", prompt="Testing patterns - async fixtures, mocking, integration tests...")
Task(subagent_type="code-analyzer", prompt="Voice implementation - server tools, dynamic variables, bypass issues...")
```

### Step 2: Synthesize Research

Combine subagent outputs into structured findings:
- Extract key insights
- Identify file:line references (50+ per document)
- Note NEEDS RETHINKING areas
- Build comparison tables
- Create ASCII diagrams

### Step 3: Generate Deliverables

For each of 15 documents:
1. Start with YAML frontmatter
2. Add Quick Entry Points section
3. Use template structure from this prompt
4. Include required ASCII diagrams
5. Add 50+ file:line references
6. Add validation checklist
7. Mark NEEDS RETHINKING sections
8. Write to `docs/knowledge-transfer/{document}.md`

### Step 4: Create INDEX.md

Final pass to create master navigation with:
- Reading order
- Document dependencies
- Quick reference table
- All primary files aggregated

---

## SUCCESS CRITERIA

Documentation is complete when:
- [ ] All 15 documents generated
- [ ] Each document has YAML frontmatter
- [ ] Each document has Quick Entry Points section
- [ ] Each document passes validation checklist
- [ ] ASCII diagrams present in D2, D3, D4, D5, D7, D10, D11, D12, D15
- [ ] NEEDS RETHINKING markers in D4, D5, D8, D11, D12, D13, D14, D15
- [ ] External research cited in D9
- [ ] No Portal references anywhere
- [ ] file:line references: 50+ per document (750+ total)
- [ ] Total documentation: 8000-10000 lines
- [ ] Diátaxis types assigned to all documents
- [ ] C4 diagrams in D2 (C1), D4 (C2), D11/D12/D15 (C3)
- [ ] Voice/Text parity gap documented in D4 and D15

---

## CRITICAL FILES TO REFERENCE (EXPANDED)

### Context Engine (D4, D12)
| File | Line Range | Purpose |
|------|------------|---------|
| `nikita/context_engine/engine.py` | 166-180 | asyncio.gather with return_exceptions=True |
| `nikita/context_engine/models.py` | all | ContextPackage (115+ typed fields) |
| `nikita/context_engine/generator.py` | 287 | 45s timeout for Sonnet 4.5 |
| `nikita/context_engine/assembler.py` | 100-150 | Static + dynamic prompt assembly |
| `nikita/context_engine/collectors/base.py` | 45-80 | CollectorContext, timeout/retry |
| `nikita/context_engine/collectors/graphiti.py` | 66-67 | 30s timeout, 2 retries |
| `nikita/context_engine/validators/coverage.py` | all | Tiered validation (80% min) |

### Game Engine (D11) **[NEW]**
| File | Line Range | Purpose |
|------|------------|---------|
| `nikita/engine/constants.py` | 10-50 | CHAPTER_NAMES, BOSS_THRESHOLDS, DECAY_RATES |
| `nikita/engine/scoring/calculator.py` | 45-80 | ScoreCalculator.calculate() |
| `nikita/engine/scoring/analyzer.py` | all | 4-metric response analysis |
| `nikita/engine/chapters/state_machine.py` | all | ChapterStateMachine |
| `nikita/engine/chapters/judgment.py` | all | BossJudgment with LLM |
| `nikita/engine/decay/calculator.py` | 30-60 | Decay rate formula |
| `nikita/engine/engagement/state_calculator.py` | all | 6-state engagement machine |
| `nikita/engine/vice/boundaries.py` | all | Vice tolerance bands |

### Post-Processing Pipeline (D12) **[NEW]**
| File | Line Range | Purpose |
|------|------------|---------|
| `nikita/context/stages/base.py` | 100-150 | PipelineStage abstract class |
| `nikita/context/stages/ingestion.py` | all | Stage 1: Message pairing |
| `nikita/context/stages/extraction.py` | all | Stage 2: Entity extraction |
| `nikita/context/stages/psychology.py` | all | Stage 3: Psychological insights |
| `nikita/context/stages/narrative_arcs.py` | all | Stage 4: Arc tracking |
| `nikita/context/stages/threads.py` | all | Stage 5: Open threads |
| `nikita/context/stages/thoughts.py` | all | Stage 6: Nikita thoughts |
| `nikita/context/stages/graph_updates.py` | all | Stage 7: Neo4j sync |
| `nikita/context/post_processor.py` | all | 11-stage orchestrator |

### Voice & Telegram (D6, D15) **[EXPANDED]**
| File | Line Range | Purpose |
|------|------------|---------|
| `nikita/agents/voice/server_tools.py` | 45-290 | 4 server tools implementation |
| `nikita/agents/voice/server_tools.py` | 331-337 | **BYPASSES ContextEngine** |
| `nikita/agents/voice/models.py` | all | DynamicVariables schema |
| `nikita/agents/voice/inbound.py` | all | Call handling |
| `nikita/platforms/telegram/message_handler.py` | all | Handler chain |
| `nikita/platforms/telegram/registration_handler.py` | all | OTP flow |

### Testing (D13) **[NEW]**
| File | Line Range | Purpose |
|------|------------|---------|
| `tests/conftest.py` | 20-50 | Singleton cache clearing pattern |
| `tests/context/stages/conftest.py` | all | Stage testing fixtures |
| `tests/db/integration/conftest.py` | all | NullPool, function-scoped fixtures |
| `tests/smoke/test_deployment.py` | all | Post-deployment health checks |

### Deployment (D14) **[NEW]**
| File | Line Range | Purpose |
|------|------------|---------|
| `nikita/config/settings.py` | all | 20+ environment variables |
| `nikita/db/migrations/versions/` | all | 8 migrations |
| `Dockerfile` | all | Cloud Run build |
| `.gcloudignore` | all | Deploy exclusions |
