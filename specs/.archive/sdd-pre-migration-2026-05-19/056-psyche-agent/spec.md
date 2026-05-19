# Spec 056: Psyche Agent

**Status**: READY FOR PLAN
**Wave**: B (parallel with 058)
**Dependencies**: Spec 055 (Life Sim Enhanced) - COMPLETE
**Feature Flag**: `psyche_agent_enabled` (default: OFF)
**Risk**: MEDIUM
**Estimated Tasks**: 22-28
**Budget**: $7/mo psyche (batch + triggers)

---

## Overview

New Opus 4.6/Sonnet 4.5 psyche agent that generates a daily PsycheState model capturing Nikita's psychological state. This state is read before each conversation and injected into the system prompt (Layer 3), giving the conversation agent context about Nikita's current emotional/psychological disposition.

### Key Components
1. **PsycheState Model** (8 fields) - structured output from psyche agent
2. **psyche_states table** - Supabase table storing 1 row per user
3. **Daily batch job** (pg_cron 5AM UTC) - regenerates psyche state from recent data
4. **3-tier trigger detector** - routes messages to appropriate analysis tier
5. **Pre-conversation psyche read** - injects psyche briefing into system prompt
6. **Prompt Layer 3** - new template section between L2 and L4

---

## User Stories

### US-1: Daily Psyche State Generation
**As** the system, **I want** to generate a daily PsycheState for each active user at 5AM UTC, **so that** Nikita's psychological disposition reflects recent interactions.

**Acceptance Criteria**:
- AC-1.1: Batch job generates valid PsycheState with all 8 fields populated
- AC-1.2: Input context includes: last 48h of score_history, emotional_states, life_events, NPC interactions
- AC-1.3: Sonnet 4.5 used for daily batch (configurable via `psyche_model` setting)
- AC-1.4: Batch completes within 30s per user
- AC-1.5: Failure for one user doesn't block others (isolated per-user execution)
- AC-1.6: Token usage tracked per generation (stored in psyche_states.token_count)

### US-2: PsycheState Model
**As** the psyche agent, **I want** a structured output model with 8 fields, **so that** the conversation agent has actionable psychological context.

**Acceptance Criteria**:
- AC-2.1: Model fields: attachment_activation (str), defense_mode (str), behavioral_guidance (str), internal_monologue (str), vulnerability_level (float 0-1), emotional_tone (str), topics_to_encourage (list[str]), topics_to_avoid (list[str])
- AC-2.2: All fields have validation (non-empty strings, bounded floats)
- AC-2.3: Model serializes to/from JSONB cleanly
- AC-2.4: Default state exists for first-time users (no psyche data yet)

### US-3: Trigger Detector (3-Tier Routing)
**As** the message handler, **I want** to route messages through a 3-tier trigger detector, **so that** important moments get deeper psyche analysis.

**Acceptance Criteria**:
- AC-3.1: Tier 1 (90%): Read cached psyche state from DB (no LLM call)
- AC-3.2: Tier 2 (8%): Sonnet 4.5 quick analysis for moderate triggers
- AC-3.3: Tier 3 (2%): Opus 4.6 deep analysis for critical moments
- AC-3.4: Trigger detection is rule-based (<5ms for tier routing decision)
- AC-3.5: Tier 3 circuit breaker: max 5 calls/user/day
- AC-3.6: Triggers: first message of day, score drop >5pts, horseman detected, boss adjacent, explicit emotional disclosure

### US-4: Pre-Conversation Psyche Read
**As** the conversation agent, **I want** psyche state available in my context, **so that** my responses reflect Nikita's current psychological state.

**Acceptance Criteria**:
- AC-4.1: Psyche state read in message_handler before agent call (~line 200)
- AC-4.2: PsycheState added to NikitaDeps (psyche_state field)
- AC-4.3: Failure graceful: psyche read failure -> L3 renders empty string, conversation proceeds
- AC-4.4: Psyche read latency <50ms (single JSONB read)

### US-5: Prompt Layer 3 Injection
**As** the prompt builder, **I want** to inject psyche briefing (~150 tokens) as Layer 3, **so that** the conversation agent sees Nikita's psychological context.

**Acceptance Criteria**:
- AC-5.1: L3 section added to system_prompt.j2 between S2/S3 and S4
- AC-5.2: Content includes: behavioral_guidance, emotional_tone, topics_to_encourage, topics_to_avoid
- AC-5.3: When psyche_state is None, L3 renders as empty string (zero tokens)
- AC-5.4: L3 content ~150 tokens when populated
- AC-5.5: PipelineContext extended with psyche_state field

### US-6: Database + Infrastructure
**As** the system, **I want** proper data storage and scheduling, **so that** psyche state persists and regenerates reliably.

**Acceptance Criteria**:
- AC-6.1: psyche_states table created with: id, user_id (UNIQUE), state (JSONB), generated_at, model, token_count
- AC-6.2: RLS: user can SELECT own row, service_role can do ALL
- AC-6.3: btree index on user_id
- AC-6.4: pg_cron job `nikita-psyche-batch` at `0 5 * * *` (5AM UTC)
- AC-6.5: Cloud Run task endpoint at `/tasks/psyche-batch`
- AC-6.6: Feature flag `psyche_agent_enabled` gates all new behavior

### US-7: Cost Control
**As** the operator, **I want** psyche costs within $7/mo budget, **so that** the feature is economically viable.

**Acceptance Criteria**:
- AC-7.1: Sonnet 4.5 default for batch (~$0.90/mo at 1 user/day)
- AC-7.2: Configurable via `psyche_model` setting (can switch to Opus)
- AC-7.3: Circuit breaker on Tier 3 (max 5/user/day)
- AC-7.4: Token count logged per generation for cost monitoring

---

## Technical Design

### Files to Modify
- `agents/text/deps.py` — add `psyche_state: dict | None = None` to NikitaDeps
- `agents/text/agent.py` — add `@agent.instructions` for psyche briefing
- `platforms/telegram/message_handler.py:~200` — add psyche read + trigger detect before agent call
- `pipeline/stages/prompt_builder.py` — add psyche state enrichment
- `pipeline/models.py` — add `psyche_state` field to PipelineContext
- `pipeline/templates/system_prompt.j2` — add L3 section

### Files to Create
- `nikita/agents/psyche/__init__.py`
- `nikita/agents/psyche/agent.py` — Pydantic AI agent with structured PsycheState output
- `nikita/agents/psyche/models.py` — PsycheState model (8 fields)
- `nikita/agents/psyche/deps.py` — PsycheDeps dataclass
- `nikita/agents/psyche/batch.py` — batch orchestration for pg_cron
- `nikita/agents/psyche/trigger.py` — 3-tier trigger detector
- `nikita/db/repositories/psyche_state_repository.py` — upsert + get_current
- `nikita/db/models/psyche_state.py` — SQLAlchemy model
- `nikita/api/routes/tasks/psyche.py` — Cloud Run task endpoint

### DB Migrations
```sql
CREATE TABLE psyche_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
    state JSONB NOT NULL DEFAULT '{}',
    generated_at TIMESTAMPTZ DEFAULT now(),
    model TEXT NOT NULL DEFAULT 'sonnet',
    token_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_psyche_states_user_id ON psyche_states(user_id);

-- RLS
ALTER TABLE psyche_states ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can read own psyche state" ON psyche_states
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Service role full access" ON psyche_states
    FOR ALL USING (auth.role() = 'service_role');
```

### PsycheState Model Schema
```python
class PsycheState(BaseModel):
    attachment_activation: str  # "secure", "anxious", "avoidant", "disorganized"
    defense_mode: str           # "open", "guarded", "deflecting", "withdrawing"
    behavioral_guidance: str    # Free-text guidance for conversation agent (~50 words)
    internal_monologue: str     # Nikita's inner thoughts (~30 words)
    vulnerability_level: float  # 0.0 (guarded) to 1.0 (fully open)
    emotional_tone: str         # "playful", "serious", "warm", "distant", "volatile"
    topics_to_encourage: list[str]  # Max 3 topics to lean into
    topics_to_avoid: list[str]      # Max 3 topics to avoid
```

### Trigger Tier Rules
| Tier | % | Trigger Condition | Action |
|------|---|-------------------|--------|
| 1 | 90% | Default | Read cached psyche_state from DB |
| 2 | 8% | First message of day, score drop >5pts, moderate emotional content | Quick Sonnet 4.5 analysis, update psyche_state |
| 3 | 2% | Horseman detected, boss adjacent, explicit crisis/vulnerability | Full Opus 4.6 analysis, update psyche_state |

---

## Critical Decisions

| # | Decision | Choice |
|---|----------|--------|
| D1 | Batch model | Sonnet 4.5 default, Opus 4.6 configurable via `psyche_model` |
| D2 | Trigger detection | Rule-based routing (<5ms), NOT LLM-based |
| D3 | Psyche read failure | Graceful degradation — L3 renders empty, conversation proceeds |
| D4 | Circuit breaker | Max 5 Tier 3 calls/user/day |

---

## Feature Flag

```python
# nikita/config/settings.py
psyche_agent_enabled: bool = False

# nikita/agents/psyche/__init__.py
def is_psyche_agent_enabled() -> bool:
    return get_settings().psyche_agent_enabled
```

When OFF: no psyche read, no trigger detection, L3 renders empty, no batch job execution.
