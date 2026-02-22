# Database Schema Reference — Nikita

> 32 tables | 33 public FKs + 4 auth FKs | 2 pgVector tables | 9 pipeline stages
> Source: Supabase MCP + codebase audit | 2026-02-22
> Status: 4 dead tables DROPped, 2 zombies remaining, 2 zombies wired in this audit

---

## Table Registry (32 tables, 9 domains)

### 1. Core Identity [5 tables]

| Table | Health | RLS | Rows | Write Path | Read Path |
|-------|--------|-----|------|------------|-----------|
| `users` | ACTIVE | Y | 1 | `UserRepository.create/update_score/apply_decay`, `prompt_builder._sync_cached_voice_prompt`, `conflict.py` | message_handler, agent, all pipeline stages, portal |
| `user_metrics` | ACTIVE | Y | 1 | `MetricsRepository.update`, `scoring.engine` | message_handler, game_state stage, prompt_builder |
| `user_profiles` | ACTIVE | Y | 1 | Portal onboarding, `generate_user_profile()` | prompt_builder (template vars), portal |
| `user_backstories` | ACTIVE | Y | 1 | `generate_backstory()` (onboarding) | prompt_builder, portal |
| `user_social_circles` | EMPTY_BUT_WIRED | Y | 0 | `EventStore.update_npc_state()`, `generate_social_circle()` | life_sim stage, portal |

### 2. Conversations [4 tables]

| Table | Health | RLS | Rows | Write Path | Read Path |
|-------|--------|-----|------|------------|-----------|
| `conversations` | ACTIVE | Y | 3 | message_handler, summary stage, pipeline status updates | extraction, memory_update, summary, prompt_builder stages, portal |
| `conversation_threads` | EMPTY_BUT_WIRED | Y | 0 | extraction stage → `ConversationThread` model | prompt_builder (open_threads), portal |
| `message_embeddings` | **ZOMBIE** | Y | 0 | *None — no repo, no writes* | *None* |
| `daily_summaries` | EMPTY_BUT_WIRED | Y | 0 | summary stage → `SummaryRepository` | prompt_builder, portal |

### 3. Memory & Knowledge [2 tables]

| Table | Health | RLS | Rows | Write Path | Read Path |
|-------|--------|-----|------|------------|-----------|
| `memory_facts` | ACTIVE | Y | 14 | memory_update stage → `SupabaseMemory.add_fact()` | prompt_builder → `SupabaseMemory.search()`, agent context |
| `context_packages` | EMPTY_BUT_WIRED | Y | 0 | `ContextPackageBuilder.build()` | agent pre-fetch, prompt_builder |

### 4. Game Engine [3 tables]

| Table | Health | RLS | Rows | Write Path | Read Path |
|-------|--------|-----|------|------------|-----------|
| `score_history` | ACTIVE | Y | 55 | game_state stage → `ScoreHistoryRepository.create` | portal (score graphs), game_state validation |
| `user_vice_preferences` | ACTIVE | Y | 8 | `VicePreferenceRepository.update_engagement` | message_handler, prompt_builder (vices), portal |
| `user_narrative_arcs` | EMPTY_BUT_WIRED | Y | 0 | Portal admin, `UserNarrativeArc` model CRUD | portal (narrative tracking) |

### 5. Nikita Simulation [4 tables]

| Table | Health | RLS | Rows | Write Path | Read Path |
|-------|--------|-----|------|------------|-----------|
| `nikita_emotional_states` | EMPTY_BUT_WIRED | Y | 0 | emotional stage → `StateStore.save_state()` | emotional stage (base state), portal |
| `nikita_entities` | **ZOMBIE** | Y | 0 | *`EventStore.save_entity()` exists but never called from pipeline* | `EventStore.get_entities()` (read path exists) |
| `nikita_life_events` | EMPTY_BUT_WIRED | Y | 0 | `LifeSimulator.generate_next_day_events()` → `EventStore.save_event()` | life_sim stage, emotional stage |
| `nikita_narrative_arcs` | EMPTY_BUT_WIRED | Y | 0 | `LifeSimulator` → `EventStore.save_arc()` | life_sim stage (active arcs) |

### 6. Engagement System [2 tables]

| Table | Health | RLS | Rows | Write Path | Read Path |
|-------|--------|-----|------|------------|-----------|
| `engagement_state` | EMPTY_BUT_WIRED | Y | 0 | engagement engine → `EngagementState` model | message_handler, touchpoint stage, portal |
| `engagement_history` | EMPTY_BUT_WIRED | Y | 0 | engagement engine state transitions | portal (engagement analytics) |

### 7. Scheduling & Outreach [3 tables]

| Table | Health | RLS | Rows | Write Path | Read Path |
|-------|--------|-----|------|------------|-----------|
| `scheduled_events` | EMPTY_BUT_WIRED | Y | 0 | `ScheduledEvent` model, task endpoints | task runner (delivery), portal |
| `scheduled_touchpoints` | EMPTY_BUT_WIRED | Y | 0 | touchpoint stage → `ScheduledTouchpoint` model | task runner (proactive messages), portal |
| `nikita_thoughts` | EMPTY_BUT_WIRED | Y | 0 | extraction stage → `NikitaThought` model | prompt_builder (active_thoughts), portal |

### 8. Prompt Generation [3 tables]

| Table | Health | RLS | Rows | Write Path | Read Path |
|-------|--------|-----|------|------------|-----------|
| `ready_prompts` | ACTIVE | Y | 2 | prompt_builder stage → `ReadyPromptRepository.set_current()` | agent (system prompt), portal |
| `generated_prompts` | EMPTY_BUT_WIRED | Y | 0 | prompt_builder stage → `GeneratedPromptRepository.create_log()` | portal (prompt audit) |
| `psyche_states` | EMPTY_BUT_WIRED | Y | 0 | psyche agent → `PsycheStateRecord` model | prompt_builder (L3 injection), portal |

### 9. Platform & Ops [6 tables]

| Table | Health | RLS | Rows | Write Path | Read Path |
|-------|--------|-----|------|------------|-----------|
| `pending_registrations` | ACTIVE | Y | 0 | `PendingRegistrationRepository.create` | Telegram auth flow |
| `onboarding_states` | ACTIVE | Y | 1 | onboarding FSM → `OnboardingState` model | voice onboarding, portal |
| `venue_cache` | ACTIVE | Y | 1 | `VenueCache` model (backstory generation) | backstory generator |
| `job_executions` | ACTIVE | Y | 132K | pg_cron → `JobExecution` model | portal (job monitoring) |
| `error_logs` | ACTIVE | Y | 17 | `ErrorLog` model (error tracking) | portal (error dashboard) |
| `audit_logs` | EMPTY_BUT_WIRED | N | 0 | portal admin actions → `AuditLog` model | portal (admin audit trail) |

---

## Foreign Key Map (33 public + 4 auth)

```
auth.users [external]
├─ [→] users.id (PK FK)
├─ [→] context_packages.user_id
├─ [→] nikita_emotional_states.user_id
└─ [→] psyche_states.user_id

users [24 inbound FKs — central hub]
├─ [→] user_metrics.user_id (1:1, unique)
├─ [→] user_profiles.id (1:1, PK FK)
├─ [→] user_backstories.user_id (1:1, unique)
├─ [→] engagement_state.user_id (1:1, unique)
├─ [→] conversations.user_id (1:N)
├─ [→] score_history.user_id (1:N)
├─ [→] daily_summaries.user_id (1:N)
├─ [→] memory_facts.user_id (1:N)
├─ [→] user_vice_preferences.user_id (1:N)
├─ [→] user_social_circles.user_id (1:N)
├─ [→] user_narrative_arcs.user_id (1:N)
├─ [→] message_embeddings.user_id (1:N) [ZOMBIE]
├─ [→] conversation_threads.user_id (1:N)
├─ [→] nikita_thoughts.user_id (1:N)
├─ [→] nikita_entities.user_id (1:N) [ZOMBIE]
├─ [→] nikita_narrative_arcs.user_id (1:N)
├─ [→] nikita_life_events.user_id (1:N)
├─ [→] engagement_history.user_id (1:N)
├─ [→] generated_prompts.user_id (1:N)
├─ [→] ready_prompts.user_id (1:N)
├─ [→] scheduled_events.user_id (1:N)
├─ [→] scheduled_touchpoints.user_id (1:N)
└─ [→] error_logs.user_id (1:N)

conversations [8 inbound FKs — second hub]
├─ [→] message_embeddings.conversation_id (1:N) [ZOMBIE]
├─ [→] memory_facts.conversation_id (1:N)
├─ [→] conversation_threads.source_conversation_id (1:N)
├─ [→] nikita_thoughts.source_conversation_id (1:N)
├─ [→] generated_prompts.conversation_id (1:N)
├─ [→] ready_prompts.conversation_id (1:N)
├─ [→] scheduled_events.source_conversation_id (1:N)
└─ [⊙] conversations.user_id → users.id

nikita_narrative_arcs
└─ [→] nikita_life_events.narrative_arc_id (1:N)

memory_facts [self-referential]
└─ [→] memory_facts.superseded_by → memory_facts.id (dedup chain)
```

### Cardinality Summary

| Pattern | Count | Tables |
|---------|-------|--------|
| 1:1 via unique FK | 3 | user_metrics, user_backstories, engagement_state |
| 1:1 via PK FK | 1 | user_profiles |
| 1:N via user_id | 20 | All others with user_id FK |
| 1:N via conversation_id | 7 | memory_facts, threads, thoughts, prompts×2, events, message_embeddings |
| Self-referential | 1 | memory_facts.superseded_by |
| Cross-schema | 4 | users, context_packages, nikita_emotional_states, psyche_states → auth.users |

### Standalone Tables (no FKs)

| Table | Reason |
|-------|--------|
| `pending_registrations` | Pre-auth, keyed by telegram_id |
| `onboarding_states` | Pre-auth, keyed by telegram_id |
| `venue_cache` | Lookup cache, no user association |
| `job_executions` | System-level, no user FK |
| `audit_logs` | Admin-only, no FK constraints |

---

## pgVector Tables

| Table | Column | Dimension | Status | Usage |
|-------|--------|-----------|--------|-------|
| `memory_facts` | embedding | vector | ACTIVE | Semantic memory search (SupabaseMemory) |
| `message_embeddings` | embedding | vector(1536) | ZOMBIE | No writes. Replaced by `memory_facts` pgVector in Spec 042. |

> `user_facts` was DROPped — its pgVector column is no longer in the schema.

---

## Pipeline Data Flow (9 stages)

```
conversation.end_event
    │
    ▼
┌──────────────────────────────────────────────────────────┐
│ PipelineOrchestrator  (orchestrator.py:26)                │
│ Sequential execution, SAVEPOINT isolation per stage       │
└──────────────────────────────────────────────────────────┘
    │
    ▼
[1] EXTRACTION (CRITICAL)
    READ:  conversations.messages
    WRITE: ctx only (in-memory extracted entities, facts, threads, thoughts)
    │
    ▼
[2] MEMORY_UPDATE (CRITICAL)
    READ:  memory_facts (dedup check via embedding similarity)
    WRITE: memory_facts (new facts with embeddings)
    │
    ▼
[3] LIFE_SIM
    READ:  nikita_life_events, nikita_narrative_arcs (via EventStore)
    WRITE: nikita_life_events (conditional — only when generate_next_day_events fires)
    │
    ▼
[4] EMOTIONAL
    READ:  (no DB read — computes from ctx)
    WRITE: nikita_emotional_states (via StateStore.save_state)
    NOTE:  Also loads conflict_details from users for ConflictStage
    │
    ▼
[5] GAME_STATE
    READ:  users, score_history
    WRITE: score_history (validation records)
    │
    ▼
[6] CONFLICT
    READ:  users.conflict_details
    WRITE: users.conflict_details (temperature gauge update)
    │
    ▼
[7] TOUCHPOINT
    READ:  scheduled_touchpoints, engagement_state
    WRITE: scheduled_touchpoints (new proactive messages)
    │
    ▼
[8] SUMMARY
    READ:  conversations
    WRITE: conversations.conversation_summary, daily_summaries
    │
    ▼
[9] PROMPT_BUILDER
    READ:  users, user_metrics, conversations, memory_facts, ready_prompts
    WRITE: ready_prompts (via set_current), generated_prompts (via create_log),
           users.cached_voice_prompt (voice only)
```

### Stage Properties

| # | Stage | Critical | Retry | Tables Touched |
|---|-------|----------|-------|----------------|
| 1 | extraction | Y | 0 | conversations (R) |
| 2 | memory_update | Y | 0 | memory_facts (RW) |
| 3 | life_sim | N | 1 | nikita_life_events (RW), nikita_narrative_arcs (R) |
| 4 | emotional | N | 1 | nikita_emotional_states (W) |
| 5 | game_state | N | 1 | users (R), score_history (RW) |
| 6 | conflict | N | 1 | users (RW) |
| 7 | touchpoint | N | 1 | scheduled_touchpoints (RW), engagement_state (R) |
| 8 | summary | N | 1 | conversations (RW), daily_summaries (W) |
| 9 | prompt_builder | N | 1 | users (RW), user_metrics (R), conversations (R), memory_facts (R), ready_prompts (RW), generated_prompts (W) |

---

## Dead Tables — DROPped

These 4 tables had zero code references (no model, no repo, no pipeline path). DROPped via migration.

| Table | Origin | Why Dead |
|-------|--------|----------|
| `user_facts` | Spec 053 | Replaced by `memory_facts` (pgVector) in Spec 042. No SQLAlchemy model. |
| `research_queue` | Spec 042 | Never implemented. Zero code references in entire codebase. |
| `nikita_state` | Spec 058 | No model, no repo. `nikita.utils.nikita_state` is a utility module, not DB-backed. |
| `engagement_metrics` | Spec 049 | No model, no repo, zero code references. Engagement system uses `engagement_state` + `engagement_history`. |

### DROP Migration SQL

```sql
-- Schema Audit: Drop 4 dead tables (2026-02-22)
-- These tables have 0 rows, no SQLAlchemy models, no repositories, and no code paths.

DROP TABLE IF EXISTS user_facts CASCADE;
DROP TABLE IF EXISTS research_queue CASCADE;
DROP TABLE IF EXISTS nikita_state CASCADE;
DROP TABLE IF EXISTS engagement_metrics CASCADE;
```

---

## Zombie Tables — Diagnostic Cards

### `message_embeddings` [ZOMBIE → TO_DROP]

**Status**: SQLAlchemy model exists (`conversation.py:159-197`) but no repository, no writes, no pipeline usage. Replaced by `memory_facts` pgVector in Spec 042.

| Layer | Evidence |
|-------|----------|
| Table | Exists in Supabase, 0 rows, vector(1536) column |
| Model | `MessageEmbedding` class in `db/models/conversation.py:159` |
| Relationship | `Conversation.embeddings` back_populates |
| Repository | None |
| Pipeline write | None |
| Pipeline read | None |

**Action**: Remove model + relationship from code. Table DROP in future migration.

---

### `nikita_entities` [ZOMBIE]

**Status**: Store has full CRUD but pipeline never calls entity save methods.

| Layer | Evidence |
|-------|----------|
| Table | Exists in Supabase, 0 rows |
| Store | `life_simulation/store.py:EventStore` — `save_entity()`, `save_entities()`, `get_entities()` |
| Pipeline | `LifeSimStage._run()` calls `LifeSimulator.get_today_events()` / `generate_next_day_events()` |
| Gap | `LifeSimulator` generates events but never extracts entities from LLM responses to call `save_entity()` |

**Fix required**: `LifeSimulator.generate_next_day_events()` needs entity extraction + `EventStore.save_entities()` call. Non-trivial — requires LLM response parsing changes.

---

## Spec Origin Map

| Spec | Tables Introduced |
|------|-------------------|
| Core (pre-spec) | users, user_metrics, user_vice_preferences, conversations, score_history, daily_summaries, pending_registrations |
| Spec 007 (Voice) | conversations.elevenlabs_session_id, conversations.transcript_raw |
| Spec 021 (Context) | context_packages |
| Spec 022 (Life Sim) | nikita_entities, nikita_narrative_arcs, nikita_life_events |
| Spec 023 (Emotional) | nikita_emotional_states |
| Spec 028 (Onboarding) | onboarding_states, users.onboarding_* columns |
| Spec 034 (Voice Prompt) | users.cached_voice_prompt, users.cached_voice_prompt_at |
| Spec 042 (Pipeline) | memory_facts, ready_prompts, generated_prompts, conversation_threads, nikita_thoughts |
| Spec 044 (Portal) | user_profiles, user_backstories, venue_cache, audit_logs, job_executions, error_logs, user_social_circles, user_narrative_arcs |
| Spec 049 (Engagement) | engagement_state, engagement_history, scheduled_events, scheduled_touchpoints |
| Spec 056 (Psyche) | psyche_states |
| Spec 057 (Conflict) | users.conflict_details, nikita_emotional_states.conflict_details |

---

## Context Engineering Flow

```
User sends message (Telegram/Voice)
    │
    ▼
message_handler reads:
  users + user_metrics + engagement_state + user_vice_preferences
    │
    ▼
Agent reads ready_prompts.prompt_text (cached system prompt)
  + memory_facts (semantic search, top-K)
  + conversations.messages (recent history)
  + psyche_states (psychological state)
    │
    ▼
Agent generates response → writes to conversations.messages
    │
    ▼
pg_cron triggers pipeline (POST /tasks/process-conversations)
    │
    ▼
Pipeline reads conversations (status=active, ended)
  → runs 9 stages (see Pipeline Data Flow above)
  → marks conversations.status = processed
    │
    ▼
Next message: agent uses updated ready_prompts + memory_facts
```

---

## RLS Summary

- **31/32 tables**: RLS enabled
- **1 exception**: `audit_logs` (admin-only, no user data path)
- **Auth pattern**: 4 tables FK to `auth.users` directly (users, context_packages, nikita_emotional_states, psyche_states)
- **All other tables**: FK to `public.users.id`

---

## Health Status Legend

| Status | Meaning |
|--------|---------|
| **ACTIVE** | Has rows OR actively written to by production code paths |
| **EMPTY_BUT_WIRED** | 0 rows but write+read code paths exist; will populate with traffic |
| **ZOMBIE** | Store/model exists but pipeline never calls write methods |
