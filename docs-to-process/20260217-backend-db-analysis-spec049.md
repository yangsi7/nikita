# Backend + DB Analysis -- Gate 4.5 Spec Preparation
Date: 2026-02-17
Source: Supabase MCP queries, gcloud CLI, doc 24 review

---

## 1. Current Schema

### Tables (31 total, public schema)

| # | Table | Rows | Cols | RLS | Purpose |
|---|-------|------|------|-----|---------|
| 1 | users | 1 | 21 | Y | Core user + game state |
| 2 | user_metrics | 1 | 8 | Y | 4 scoring sub-metrics |
| 3 | user_vice_preferences | 8 | 8 | Y | 8 vice categories |
| 4 | conversations | 2 | 22 | Y | Messages (JSONB), platform, status |
| 5 | score_history | 48 | 8 | Y | Score timeline |
| 6 | daily_summaries | 0 | 15 | Y | Daily recaps |
| 7 | message_embeddings | 0 | 7 | Y | pgVector (legacy) |
| 8 | pending_registrations | 0 | 7 | Y | Telegram OTP flow |
| 9 | conversation_threads | 0 | 8 | Y | Open threads/cliffhangers |
| 10 | nikita_thoughts | 0 | 9 | Y | Nikita's inner thoughts |
| 11 | engagement_state | 0 | 11 | Y | 6-state FSM |
| 12 | engagement_history | 0 | 9 | Y | State transitions |
| 13 | engagement_metrics | 0 | 12 | Y | Daily engagement stats |
| 14 | generated_prompts | 0 | 10 | Y | Legacy prompt generation |
| 15 | job_executions | 129,564 | 9 | Y | pg_cron tracking |
| 16 | user_profiles | 1 | 9 | Y | Location, life stage |
| 17 | user_backstories | 1 | 11 | Y | How-we-met narrative |
| 18 | venue_cache | 1 | 6 | Y | Onboarding venue cache |
| 19 | onboarding_states | 1 | 5 | Y | Telegram onboarding FSM |
| 20 | scheduled_events | 0 | 13 | Y | Pending message deliveries |
| 21 | context_packages | 0 | 5 | Y | Pre-computed context (Spec 021) |
| 22 | nikita_entities | 0 | 7 | Y | NPCs/places (Spec 022) |
| 23 | nikita_narrative_arcs | 0 | 11 | Y | Story arcs (Spec 022) |
| 24 | nikita_life_events | 0 | 11 | Y | Daily life events |
| 25 | nikita_emotional_states | 0 | 12 | Y | 4D emotional state |
| 26 | audit_logs | 0 | 9 | N | Admin audit trail |
| 27 | error_logs | 17 | 13 | Y | Error tracking |
| 28 | user_social_circles | 0 | 14 | Y | Personalized NPCs (Spec 035) |
| 29 | user_narrative_arcs | 0 | 16 | Y | Multi-conv storylines |
| 30 | user_facts | 0 | 10 | Y | User facts (pgVector) |
| 31 | memory_facts | 14 | 13 | Y | Unified memory (Spec 042) |
| 32 | ready_prompts | 2 | 11 | Y | Pre-built prompts |
| 33 | scheduled_touchpoints | 0 | 12 | Y | Proactive messages |
| 34 | research_queue | 0 | 9 | Y | Research task queue |
| 35 | nikita_state | 0 | 10 | Y | Nikita internal state |

### Key Table Details

#### users (21 columns)
```
id                    UUID PK          -- links to auth.users
telegram_id           BIGINT UNIQUE    -- Telegram user ID
phone                 VARCHAR(20)      -- phone number
relationship_score    NUMERIC(5,2)     -- composite score, default 50.00
chapter               INT              -- 1-5, CHECK constraint
boss_attempts         INT              -- 0-3, CHECK constraint
days_played           INT              -- counter
last_interaction_at   TIMESTAMPTZ      -- nullable
game_status           VARCHAR(20)      -- active|boss_fight|game_over|won
graphiti_group_id     TEXT             -- LEGACY (Neo4j reference, unused)
timezone              VARCHAR(50)      -- default 'UTC'
notifications_enabled BOOL             -- default true
created_at            TIMESTAMPTZ
updated_at            TIMESTAMPTZ
cached_voice_prompt   TEXT             -- voice prompt cache (FR-034)
cached_voice_prompt_at TIMESTAMPTZ
cached_voice_context  JSONB            -- voice context snapshot
onboarding_status     TEXT             -- pending|in_progress|completed|skipped
onboarding_profile    JSONB            -- onboarding data
onboarded_at          TIMESTAMPTZ
onboarding_call_id    TEXT             -- ElevenLabs call ID
```

**Notable MISSING columns (vs doc 24):**
- NO `routine_config` JSONB
- NO `meta_instructions` JSONB
- NO `last_conflict_at` TIMESTAMPTZ
- NO `npc_states` JSONB

#### user_metrics (8 columns)
```
id          UUID PK
user_id     UUID FK -> users, UNIQUE
intimacy    NUMERIC(5,2) default 50.00
passion     NUMERIC(5,2) default 50.00
trust       NUMERIC(5,2) default 50.00
secureness  NUMERIC(5,2) default 50.00
created_at  TIMESTAMPTZ
updated_at  TIMESTAMPTZ
```

**Notable MISSING:** NO `vulnerability_exchanges` INT

#### nikita_emotional_states (12 columns)
```
state_id              UUID PK
user_id               UUID FK -> auth.users (NOT public.users!)
arousal               NUMERIC  0-1 scale, default 0.5
valence               NUMERIC  0-1 scale, default 0.5
dominance             NUMERIC  0-1 scale, default 0.5
intimacy              NUMERIC  0-1 scale, default 0.5
conflict_state        TEXT     none|passive_aggressive|cold|vulnerable|explosive
conflict_started_at   TIMESTAMPTZ
conflict_trigger      TEXT
ignored_message_count INT      default 0
last_updated          TIMESTAMPTZ
created_at            TIMESTAMPTZ
metadata              JSONB
```

**Key insight:** This table already has basic conflict tracking (conflict_state, conflict_trigger). Doc 24 proposes a richer conflict model with temperature gauge, Gottman ratio, repair attempts, boss phase. This is a PARTIAL overlap.

#### nikita_state (10 columns)
```
id                UUID PK
user_id           UUID FK, UNIQUE
energy            FLOAT    0-100, default 50
social            FLOAT    0-100, default 50
stress            FLOAT    0-100, default 30
happiness         FLOAT    0-100, default 60
current_activity  VARCHAR  default 'relaxing'
recent_events     JSONB    default []
active_conflict   TEXT     nullable
friends           JSONB    default [Maya, Sophie, Lena] (3 hardcoded NPCs)
updated_at        TIMESTAMPTZ
```

**Key insight:** This table already has `friends` JSONB with 3 NPCs. Doc 24 proposes `npc_states` on `users` with 5 NPCs (Emma/Lena, Marcus/Viktor, Sarah/Yuki, Mom, Ex). These are DIFFERENT friend sets -- existing = Maya/Sophie/Lena, proposed = Emma/Lena/Marcus/Viktor/Sarah/Yuki/Mom/Ex.

#### user_social_circles (14 columns)
```
id                     UUID PK
user_id                UUID FK
friend_name            TEXT
friend_role            TEXT
age                    INT
occupation             TEXT
personality            TEXT
relationship_to_nikita TEXT
storyline_potential    JSONB
trigger_conditions     JSONB
adapted_traits         JSONB
is_active              BOOL
created_at             TIMESTAMPTZ
updated_at             TIMESTAMPTZ
```

**Key insight:** Spec 035 already created a rich NPC tracking system (`user_social_circles`). Doc 24 proposes simpler `npc_states` JSONB on users. Decision needed: USE existing `user_social_circles` or ADD simpler JSONB column?

#### memory_facts (13 columns) -- PRIMARY MEMORY TABLE (Spec 042)
```
id               UUID PK
user_id          UUID FK -> users
graph_type       TEXT     user|relationship|nikita
fact             TEXT
source           TEXT
confidence       REAL     0.0-1.0
embedding        VECTOR   (1536 dims, ivfflat cosine index)
metadata         JSONB
is_active        BOOL     default true
superseded_by    UUID FK -> self
conversation_id  UUID FK -> conversations
created_at       TIMESTAMPTZ
updated_at       TIMESTAMPTZ
```

#### nikita_life_events (11 columns) -- EXISTING LIFE SIM
```
event_id          UUID PK
user_id           UUID FK
event_date        DATE
time_of_day       VARCHAR  morning|afternoon|evening|night
domain            VARCHAR  work|social|personal
event_type        VARCHAR
description       TEXT
entities          JSONB    default []
emotional_impact  JSONB    {arousal_delta, valence_delta, intimacy_delta, dominance_delta}
importance        FLOAT    0.0-1.0, default 0.5
narrative_arc_id  UUID FK -> nikita_narrative_arcs
created_at        TIMESTAMPTZ
```

**Key insight:** Life events table already exists with emotional_impact JSONB. Doc 24 describes "JSONB per day per user" but current schema has one row per event. Current design is MORE normalized (better for querying individual events).

### RLS Policies (84 total)

All tables have RLS enabled except `audit_logs`. Key patterns:
- User own-data: `auth.uid() = user_id` or `auth.uid() = id`
- Service role bypass: `auth.role() = 'service_role'`
- Admin access: `is_admin()` function
- Most tables have both user SELECT + service role ALL

Tables with NO user write policies (service-role only):
- `nikita_entities` -- service_role only
- `nikita_life_events` -- service_role only
- `nikita_narrative_arcs` -- service_role only
- `nikita_state` -- user SELECT only, no write

### Indexes (110+ total)

Key performance indexes:
- `idx_memory_facts_embedding_cosine` -- ivfflat(lists=50) on memory_facts.embedding
- `idx_memory_facts_user_graph_active` -- btree(user_id, graph_type, created_at) WHERE is_active
- `idx_user_facts_embedding_hnsw` -- hnsw(m=16, ef=64) on user_facts.embedding
- `idx_conversations_session_detection` -- btree(user_id, status, last_message_at) WHERE active
- `idx_conversations_stuck_detection` -- btree(status, processing_started_at) WHERE processing
- `idx_ready_prompts_current` -- UNIQUE btree(user_id, platform) WHERE is_current
- `idx_emotional_states_conflict` -- btree(user_id, conflict_state) WHERE != 'none'
- `idx_life_events_user_date` -- btree(user_id, event_date)

### Extensions (9 installed)

| Extension | Version | Schema | Purpose |
|-----------|---------|--------|---------|
| plpgsql | 1.0 | pg_catalog | PL/pgSQL |
| pg_cron | 1.6.4 | pg_catalog | Job scheduler |
| pg_net | 0.19.5 | extensions | Async HTTP (for pg_cron -> Cloud Run) |
| vector | 0.8.0 | extensions | pgVector (1536 dims) |
| uuid-ossp | 1.1 | extensions | UUID generation |
| pgcrypto | 1.3 | extensions | Cryptographic functions |
| pg_stat_statements | 1.11 | extensions | Query stats |
| pg_trgm | 1.6 | extensions | Trigram similarity |
| pg_graphql | 1.5.11 | graphql | GraphQL support |
| supabase_vault | 0.3.1 | vault | Secrets management |

### pg_cron Jobs (6 active)

| Job | Schedule | Endpoint | Purpose |
|-----|----------|----------|---------|
| nikita-decay | `0 * * * *` (hourly) | `/api/v1/tasks/decay` | Score decay |
| nikita-summary | `59 23 * * *` (daily 23:59) | `/api/v1/tasks/summary` | Daily summaries |
| nikita-cleanup | `30 * * * *` (half-hourly) | `/api/v1/tasks/cleanup` | Expired data cleanup |
| nikita-process-conversations | `*/5 * * * *` (every 5 min) | `/api/v1/tasks/process-conversations` | Pipeline processing |
| nikita-cron-cleanup | `0 3 * * *` (daily 3AM) | SQL direct | Delete old cron.job_run_details (7d) |
| nikita-deliver | `*/5 * * * *` (every 5 min) | `/api/v1/tasks/deliver` | Scheduled message delivery |

All jobs use `pg_net.http_post` to call Cloud Run endpoints with Bearer token auth.

### Migrations (65 applied)

65 migrations from 2025-11-29 to 2026-02-06. Latest: `unified_pipeline_tables` (Spec 042).

---

## 2. Cloud Run Config

### Service Details
```
Name:           nikita-api
Region:         us-central1
Project:        gcp-transcribe-test
CPU:            1
Memory:         512Mi
Max instances:  10
Min instances:  null (scales to zero -- CORRECT per project rules)
```

### Environment Variables (14)
```
SUPABASE_SERVICE_KEY      -- Supabase admin access
DATABASE_URL              -- Direct PostgreSQL connection
NEO4J_PASSWORD            -- LEGACY (unused, should be removed)
NEO4J_URI                 -- LEGACY (unused, should be removed)
ANTHROPIC_API_KEY         -- Claude API
OPENAI_API_KEY            -- Embeddings
ELEVENLABS_API_KEY        -- Voice
TELEGRAM_BOT_TOKEN        -- Telegram bot
TELEGRAM_WEBHOOK_SECRET   -- Webhook verification
SUPABASE_JWT_SECRET       -- JWT auth
FIRECRAWL_API_KEY         -- Venue research
ELEVENLABS_WEBHOOK_SECRET -- Voice webhook HMAC
CONTEXT_ENGINE_FLAG       -- Feature flag
SUPABASE_URL              -- Supabase project URL
```

**Cleanup needed:** `NEO4J_PASSWORD` and `NEO4J_URI` are legacy (Spec 042 removed Neo4j). Should be deleted from Cloud Run env.

### Resource Limits Assessment
- 512Mi memory may be tight for Opus 4.6 psyche batch (large prompt assembly)
- CPU=1 is fine for async pipeline (not CPU-bound)
- Max instances=10 is generous for current user count (1 active user)

---

## 3. Doc 24 Proposed Changes vs Current State

### New Tables Needed

#### psyche_states -- DOES NOT EXIST
Doc 24 proposes:
```sql
CREATE TABLE psyche_states (
    id UUID PRIMARY KEY,
    user_id UUID FK -> users, UNIQUE,
    state JSONB,            -- PsycheState model
    generated_at TIMESTAMPTZ,
    model TEXT,             -- 'opus-4.6' or 'sonnet-4.5'
    token_count INT
);
```

**Current partial overlap:** `nikita_emotional_states` has 4D state (arousal/valence/dominance/intimacy) + basic conflict tracking. But psyche_states is a DIFFERENT concept: behavioral guidance, attachment activation, defense mode, internal monologue, vulnerability level. These are complementary, not duplicative.

**Verdict:** NEW TABLE NEEDED. psyche_states stores LLM-generated behavioral guidance; nikita_emotional_states stores computed emotional dimensions.

### Column Additions to Existing Tables

| Column | Table | Type | Current Status | Verdict |
|--------|-------|------|----------------|---------|
| `routine_config` | users | JSONB | MISSING | NEEDED -- weekly routine template |
| `meta_instructions` | users | JSONB | MISSING | NEEDED -- monthly behavioral arc |
| `last_conflict_at` | users | TIMESTAMPTZ | MISSING | NEEDED -- conflict cooldown |
| `npc_states` | users | JSONB | MISSING | DEBATABLE -- `user_social_circles` exists |
| `vulnerability_exchanges` | user_metrics | INT | MISSING | NEEDED -- V-exchange counter |

**NPC states decision point:**
- `user_social_circles` (Spec 035): 14-column relational table with rich NPC data
- `nikita_state.friends` JSONB: 3 hardcoded NPCs (Maya, Sophie, Lena)
- Doc 24 proposes: `users.npc_states` JSONB with 5 NPCs (different names)

Recommendation: Leverage `user_social_circles` as the authoritative NPC store. Add a `last_event` and `sentiment` column to it instead of creating `npc_states` JSONB. This avoids data duplication and uses the existing relational design.

### New Indexes Needed

| Index | Table | Type | Purpose |
|-------|-------|------|---------|
| `idx_psyche_states_user` | psyche_states | btree(user_id) | Fast lookup |
| (none additional) | -- | -- | Existing indexes cover life_events, emotional_states, memory_facts |

### New RLS Policies Needed

| Table | Policy | Pattern |
|-------|--------|---------|
| psyche_states | User SELECT own | `auth.uid() = user_id` |
| psyche_states | Service role ALL | `auth.role() = 'service_role'` |

### New pg_cron Jobs Needed

| Job | Schedule | Purpose |
|-----|----------|---------|
| nikita-psyche-batch | `0 5 * * *` (daily 5AM) | Opus 4.6 psyche state generation |
| nikita-life-gen | `0 4 * * *` (daily 4AM) | Next-day life event generation |

**Existing jobs that partially cover:**
- `nikita-process-conversations` (every 5 min) already runs the 9-stage pipeline which includes emotional state updates and life sim
- `nikita-decay` (hourly) covers score decay
- `nikita-summary` (daily) covers summaries

New batch jobs needed specifically for: (1) Opus psyche batch (1x/day), (2) proactive life event generation (1x/day).

---

## 4. Gap Matrix

| Component | Current State | Doc 24 Target | Gap | Migration Effort |
|-----------|---------------|---------------|-----|------------------|
| **psyche_states table** | Does not exist | New table (JSONB, 1 row/user) | FULL GAP | S -- 1 migration |
| **Psyche Agent** | No Opus batch | Opus 4.6 daily + triggered hybrid | FULL GAP | L -- new agent code |
| **Trigger detection** | None | 3-tier (90/8/2% routing) | FULL GAP | M -- new module |
| **routine_config** | No column | JSONB on users | FULL GAP | S -- ALTER TABLE |
| **meta_instructions** | No column | JSONB on users | FULL GAP | S -- ALTER TABLE |
| **last_conflict_at** | No column | TIMESTAMPTZ on users | FULL GAP | S -- ALTER TABLE |
| **NPC tracking** | `user_social_circles` (14 cols), `nikita_state.friends` (3 NPCs) | `npc_states` JSONB (5 NPCs) | PARTIAL -- existing system covers this, needs reconciliation | S -- decide approach |
| **vulnerability_exchanges** | No column | INT on user_metrics | FULL GAP | S -- ALTER TABLE |
| **Life events** | `nikita_life_events` exists (11 cols) | Same concept, emotional-driven | PARTIAL -- table exists, generation logic needs enhancement | M -- update LifeSimStage |
| **Emotional state** | `nikita_emotional_states` (4D + conflict) | Same + richer conflict model | PARTIAL -- table exists, needs conflict model enhancement | M -- add columns or JSONB |
| **Conflict system** | Basic `conflict_state` enum (5 values) | Temperature gauge, Gottman ratio, boss phases | PARTIAL -- schema exists, model needs expansion | M -- enhance JSONB metadata |
| **Prompt caching** | `ready_prompts` table exists | Same + psyche layer + cache strategy | PARTIAL -- table exists, needs prompt assembly refactor | M -- code change |
| **Memory (pgVector)** | `memory_facts` with ivfflat, hash dedup | Same (no changes) | NO GAP | None |
| **Score history** | `score_history` exists | Same (no changes) | NO GAP | None |
| **Conversations** | 22-column table, pipeline processing | Same (no changes) | NO GAP | None |
| **Engagement FSM** | 3 tables (state/history/metrics) | Same (no changes) | NO GAP | None |
| **Daily summaries** | `daily_summaries` exists | Same (no changes) | NO GAP | None |
| **pg_cron decay** | Hourly decay job | Same (no changes) | NO GAP | None |
| **pg_cron psyche batch** | Does not exist | Daily Opus 4.6 job | FULL GAP | S -- add cron job |
| **pg_cron life gen** | Does not exist (pipeline handles it) | Daily batch generation | PARTIAL -- pipeline exists, need dedicated batch job | S -- add cron job |
| **Cloud Run env** | 14 vars (2 legacy Neo4j) | Remove Neo4j, same otherwise | CLEANUP needed | S -- delete 2 vars |
| **Cloud Run resources** | 512Mi/1CPU | May need 1Gi for Opus batch | MONITOR | TBD |

### Migration Effort Legend
- **S** (Small): < 1 hour, single migration or config change
- **M** (Medium): 1-4 hours, code + migration
- **L** (Large): 1-2 days, new module/agent

---

## 5. Critical Findings

### 5.1 Existing Table Overlap -- Reconciliation Needed
Doc 24 was written without awareness of several existing tables. The spec must decide:
1. `nikita_state` vs new psyche/state model -- `nikita_state` has energy/social/stress/happiness/friends/conflict. Overlap with both `nikita_emotional_states` and proposed `psyche_states`. Consider deprecating `nikita_state` in favor of the other two.
2. `user_social_circles` vs `npc_states` JSONB -- rich relational model already exists. Use it.
3. `nikita_entities` + `nikita_narrative_arcs` vs doc 24's simpler NPC tracking -- existing is MORE sophisticated.
4. `user_facts` vs `memory_facts` -- both have pgVector. `memory_facts` (Spec 042) is the canonical store. `user_facts` may be legacy.

### 5.2 Tables That May Be Deprecated
- `nikita_state` -- superseded by `nikita_emotional_states` + proposed `psyche_states`
- `user_facts` -- superseded by `memory_facts` (Spec 042)
- `context_packages` -- superseded by `ready_prompts` (Spec 042)
- `generated_prompts` -- superseded by `ready_prompts`
- `nikita_entities` -- potentially merged into `user_social_circles`

### 5.3 Legacy Cleanup
- `graphiti_group_id` column on users -- Neo4j reference, no longer used
- `NEO4J_URI` and `NEO4J_PASSWORD` env vars on Cloud Run
- `message_embeddings` table -- replaced by `memory_facts` pgVector

### 5.4 pg_cron Job Security
All 5 HTTP-based cron jobs use the same Bearer token (`f3eaba50...`). This is the `TASK_AUTH_SECRET` from settings. The token is stored in plaintext in cron.job commands. Consider: (1) rotating this secret, (2) using Supabase Vault for storage.

### 5.5 Conflict Model Enhancement Path
Current `nikita_emotional_states.conflict_state` uses a 5-value enum. Doc 24 proposes a richer JSONB model with: temperature (0-100), type, repair_attempts, positive/negative counts, gottman_ratio, boss_phase. Best approach: add a `conflict_details` JSONB column to `nikita_emotional_states` rather than creating a new table.

---

## 6. Recommended Migration Plan (Ordered)

1. **Phase 1: Schema additions** (zero downtime)
   - CREATE TABLE `psyche_states` (+ index + RLS)
   - ALTER TABLE `users` ADD `routine_config`, `meta_instructions`, `last_conflict_at`
   - ALTER TABLE `user_metrics` ADD `vulnerability_exchanges`
   - ALTER TABLE `nikita_emotional_states` ADD `conflict_details` JSONB
   - Add `last_event` and `sentiment` columns to `user_social_circles`

2. **Phase 2: pg_cron jobs**
   - Add `nikita-psyche-batch` daily job
   - Add `nikita-life-gen` daily job (or enhance existing pipeline)

3. **Phase 3: Cleanup** (can be deferred)
   - Remove `NEO4J_URI`, `NEO4J_PASSWORD` from Cloud Run env
   - Deprecate `nikita_state` table (migrate data to emotional_states)
   - Deprecate `user_facts` (migrate to memory_facts)
   - Deprecate `generated_prompts` (using ready_prompts)
   - Drop `graphiti_group_id` column from users

All Phase 1 changes are additive (nullable/defaulted columns, new table) = zero downtime migration.
