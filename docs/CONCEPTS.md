# Concept Glossary

Cross-reference for project-specific concepts. Each entry: 1-sentence definition + canonical home + relevant spec(s). Updated 2026-05-05 (W6).

> **Auto-refresh trigger**: this file should be kept in sync via `/roadmap sync` per `.claude/rules/doc-lifecycle.md` (W9). Each spec edit that introduces a new concept appends a row here; superseded concepts link to their replacement.

| Concept | Definition | Canonical home | Spec(s) |
|---|---|---|---|
| **11-Stage Pipeline** | Async per-turn processing pipeline at `nikita/pipeline/orchestrator.py:47-59`. Stages: extraction → persistence → memory_update → life_sim → emotional → vice → game_state → conflict → touchpoint → summary → prompt_builder. | `memory/architecture.md` §"11-Stage Async Pipeline" | 042, 067, 068, 110, 114, 116 |
| **Archetype** | Big-5 personality cluster the system targets for compatibility-floor matching during onboarding. 12 archetypes per Spec 216-D. | `memory/user-journeys.md` §"Onboarding Plumbing" + `nikita/agents/onboarding/archetypes.py` | 216-D |
| **Backstory** | Per-user persona-tailored narrative produced by the LLM during onboarding (Spec 216-E firecrawl + WebSearchTool). Cached in `backstory_cache` table. | `nikita/agents/onboarding/` | 213, 216-E |
| **Big-5 Judge** | Pydantic AI judge that scores onboarding answers against Big-5 personality dimensions (Spec 216-D). | `nikita/agents/onboarding/big5_judge.py` | 216-D |
| **Boss Encounter** | Per-chapter gate at score thresholds (55/60/65/70/75% Ch1-5). 3 attempts; 3rd fail = game over. Multi-phase (OPENING → RESOLUTION) per Spec 058. | `memory/game-mechanics.md` §"Multi-Phase Boss" | 004, 058, 101, 111, 113 |
| **BossPhase enum** | OPENING / RESOLUTION (`nikita/engine/chapters/boss.py:33-41`). | `memory/game-mechanics.md` §"Multi-Phase Boss" | 058 |
| **BossResult enum** | PASS / FAIL / PARTIAL / ERROR (`nikita/engine/chapters/judgment.py:26-31`). ERROR doesn't count toward 3-fail game-over. | `memory/game-mechanics.md` | 058 |
| **Calibration Multipliers** | Engagement-zone scoring multipliers at `nikita/engine/scoring/calculator.py:20-27`. IN_ZONE=1.0, CALIBRATING=0.9, DRIFTING=0.8, DISTANT=0.6, CLINGY=0.5, OUT_OF_ZONE=0.2. Apply only to POSITIVE deltas. | `memory/game-mechanics.md` §"Score Calculator" | 026, 210 |
| **Chapter** | Relationship phase 1-5 (Curiosity / Intrigue / Investment / Intimacy / Established) per `nikita/config_data/chapters.yaml`. Gated by boss thresholds. | `memory/game-mechanics.md` §"Chapter Names" | 003 |
| **CHAPTER_DELTA_CAPS** | Per-chapter cap on score deltas (3.0/2.5/2.0/1.5/1.0 per Ch1-5) at `calculator.py:31-37`. GH #196 score-acceleration guard. | `memory/game-mechanics.md` | — |
| **Composite Score** | Weighted relationship score 0-100% = intimacy×0.30 + passion×0.25 + trust×0.25 + secureness×0.20. | `memory/game-mechanics.md` §"Scoring System" | 003 |
| **Conflict** | Active relationship friction state set by pipeline `conflict` stage; visible to player via portal `<ConflictBanner />`. | `nikita/pipeline/stages/conflict.py:27` | 028, 030 |
| **Consecutive Crises** | Cross-session JSONB tracking (Spec 111, GH #91) of cumulative crisis events; exposed via voice path in Spec 113. | `memory/game-mechanics.md` | 111, 113 |
| **ContextPackage** | Pydantic cache surface at `nikita/context/package.py:95`. NOT a 115-field "ContextEngine" output (KT framing was wrong; W4 audit). | `memory/architecture.md` | 042 |
| **Cron Jobs** | pg_cron schedules in `supabase/migrations/*` (heartbeat hourly, daily-arcs 05:00, touchpoints */5min, +DB-only prunes). | `nikita/api/routes/tasks.py` + `supabase/migrations/20260418141500_cron_heartbeat_engine.sql` | 215 |
| **Dedup Threshold** | Memory cosine similarity threshold `DEDUP_SIMILARITY_THRESHOLD = 0.87` HARDCODED at `nikita/memory/supabase_memory.py:42`. History 0.95→0.92→0.87 per GH #199. | `memory/architecture.md` §"Memory Subsystem" | 042, 102 |
| **Decay** | Hourly score decay 0.8/0.6/0.4/0.3/0.2 (Ch1-5) after grace period. yaml-authoritative. `constants.py GRACE_PERIODS` is INVERTED + DEPRECATED. | `memory/game-mechanics.md` §"Decay" | 005, 106, 148 |
| **Discriminated Union Output** | Pydantic AI agent pattern `output_type=[X, Y]` mixing structured-or-text. Used in onboarding agent (`conversation_agent.py:266`). | `.claude/rules/agentic-design-patterns.md` | 214, 216 |
| **E2E_AUTH_BYPASS** | Test-only env var that hard-codes `userId="e2e-player-id"` at `portal/src/app/onboarding/page.tsx:42-50`. Production-build with this set bypasses auth (smell). | `memory/user-journeys.md` §"Auth Smells" | — |
| **EMBEDDING_DIMS** | Vector dimension 1536 (`nikita/memory/supabase_memory.py:33`); model `text-embedding-3-small`. | `memory/architecture.md` | 042 |
| **Engagement State** | 6-state FSM at `nikita/engine/engagement/state_machine.py:8-13`: CALIBRATING / IN_ZONE / DRIFTING / CLINGY / DISTANT / OUT_OF_ZONE. | `memory/game-mechanics.md` §"Engagement States" | 026 |
| **EventEmitter** | Pipeline observability emitter (Spec 110 Phase A); writes to `pipeline_events` table; viewable in admin Conversation Inspector. | `memory/architecture.md` | 110 |
| **GodModePanel** | Admin destructive-action panel in `portal/src/components/admin/god-mode-panel.tsx`. Force chapter advance, score override, game-status reset. Audit-emitting. | `portal/src/app/admin/users/CLAUDE.md` §"Gotchas" | — |
| **Grace Period** | Per-chapter no-decay window 8/16/24/48/72h (Ch1-5, natural). yaml authoritative; `constants.py GRACE_PERIODS` is INVERTED + DEPRECATED. | `memory/game-mechanics.md` §"Decay" | 005, 101 |
| **Heartbeat** | Hourly system tick (Spec 215) at `nikita/api/routes/tasks.py:1213 heartbeat_tick`; cron at `cron_heartbeat_engine.sql:56`. | `memory/architecture.md` | 215 |
| **Idempotency Cache** | LLM-call dedup table `llm_idempotency_cache` (Spec 215); pg_cron prune. | `supabase/migrations/20260419120000_llm_idempotency_cache.sql` | 215 |
| **Life Simulator** | NPC + life-event generator at `nikita/life_simulation/simulator.py:37`. Both request-driven (`LifeSimStage`) and cron-driven (`/generate-daily-arcs`). | `memory/architecture.md` §"Life Simulator" + diagram E (W6.5) | — |
| **Magic Link** | `signInWithOtp` flow. Two surfaces: `/login/` and `/onboarding/auth/` (dual-surface smell, W4 audit). | `memory/user-journeys.md` §"Real Entry Points" | — |
| **max_decay_per_cycle** | Decay cap = `Decimal("20.0")` at `nikita/engine/decay/calculator.py:45,103-104`. Prevents catastrophic decay from long absences. | `memory/game-mechanics.md` §"Decay" | 005 |
| **Memory Fact** | `memory_facts` table row (id, content, embedding, is_active, superseded_by). Migration at `db/migrations/versions/20260206_0009_unified_pipeline_tables.py:29`. | `memory/architecture.md` §"Memory Subsystem" | 042, 102 |
| **METRIC_WEIGHTS** | Composite-score weights {intimacy:0.30, passion:0.25, trust:0.25, secureness:0.20}. yaml-authoritative; `constants.py:139-144` deprecated mirror. | `memory/game-mechanics.md` §"Scoring System" | 003 |
| **MoodOrb** | Player-dashboard mood visual at `portal/src/components/dashboard/mood-orb.tsx`. Driven by `useEmotionalState()`. | `portal/src/app/dashboard/nikita/CLAUDE.md` | — |
| **Note User Fact** | `@agent.tool` at `nikita/agents/text/agent.py:220-247`. Deprecated comment at `tools.py:107` but still registered (GH #478, folds into W7b). | `.claude/rules/agentic-design-patterns.md` | — |
| **Pipeline Event** | Row in `pipeline_events` (Spec 110 Phase A); 30-day retention via pg_cron. | `memory/architecture.md` | 110 |
| **Psyche Agent** | Pydantic AI agent at `nikita/agents/psyche/agent.py:66`. `output_type=PsycheState`, no tools. State written to DB, injected into text agent via `add_psyche_briefing` instructions. | `memory/architecture.md` §"Pydantic AI Agents" | 113 |
| **PROJECT_INDEX.json** | Auto-generated codebase index (1.9 MB, 988+ files). Queryable via `bash ~/.claude/skills/project-intel/scripts/graph-ops.sh <cmd>`. Refresh via `/index`. | `.claude/CLAUDE.md` §"Code Intelligence" | — |
| **Prompt Builder** | Pipeline stage 10 (`nikita/pipeline/stages/prompt_builder.py:36`); writes 24 ctx fields. Heaviest stage. Replaces KT's "PromptGenerator" framing. | `memory/architecture.md` §"11-Stage Async Pipeline" | 042 |
| **Scheduled Events** | Queue table `scheduled_events`; `/deliver` endpoint pops + delivers via Telegram. Worker at `nikita/api/routes/tasks.py:274`. | `memory/architecture.md` | 070 |
| **SDD** | Specification-Driven Development. 8-phase workflow (`/feature` → `/plan` → `/tasks` → `/audit` → `/implement` → ...). | `.claude/CLAUDE.md` §"SDD Enforcement" | — |
| **Skip Variable Response** | Spec 210 humanization layer: response timing log-normal × chapter × momentum (EWMA). Replaces uniform skip rates from earlier specs. | `docs/models/response-timing.md` + `nikita/agents/text/timing.py` | 210 |
| **Server Tools (ElevenLabs)** | ElevenLabs Conversational AI 2.0 callback pattern. Live voice loop is NOT Pydantic AI. | `memory/architecture.md` §"Pydantic AI Agents" | — |
| **State Collisions** | Pipeline ctx fields written by multiple stages: `extraction_summary` (stage 0 + 9 overwrite), `conflict_details` (stages 4 + 7). Smell flagged in W6.5 Diagram A. | `memory/architecture.md` §"11-Stage Async Pipeline" | — |
| **SupabaseMemory** | pgVector memory backend at `nikita/memory/supabase_memory.py:51`. Replaced Graphiti/Neo4j in Spec 042. | `memory/architecture.md` §"Memory Subsystem" | 042, 102 |
| **Supersession** | Memory fact deactivation: `is_active=False` + `superseded_by` FK self-ref (`memory_fact_repository.py:194-196`). | `memory/architecture.md` | 102 |
| **TASK_AUTH_SECRET** | Bearer token for cron→/tasks/* HTTP calls. **Hardcoded** in migration SQL `cron_heartbeat_engine.sql:63,75,87` (smell). Rotation requires `cron.alter_job`. | `memory/integrations.md` + `nikita/api/routes/tasks.py:48 verify_task_secret` | — |
| **Touchpoint** | Proactive scheduled message from Nikita. Pipeline stage 8 (`nikita/pipeline/stages/touchpoint.py:21`); cron job `*/5 * * * *` at `cron_heartbeat_engine.sql:80`. | `memory/architecture.md` | 070, 215 |
| **Vice** | Personalized engagement modifier (8 categories). Real categories at `nikita/db/models/user.py:393-403`: intellectual_dominance, risk_taking, substances, sexuality, emotional_intensity, rule_breaking, dark_humor, vulnerability. | `memory/game-mechanics.md` §"Real Vice Taxonomy" | 040, 114 |
| **VICE_CATEGORIES** | Constant list of 8 vice category names at `nikita/db/models/user.py:393-403`. | `memory/game-mechanics.md` | 040 |
| **VicePromptInjector** | Vice→prompt assembly at `nikita/engine/vice/injector.py:62`. Wired into `ViceService` at `nikita/engine/vice/service.py`. | `memory/game-mechanics.md` | 040, 114 |
| **Walk (live-E2E)** | Manual end-to-end dogfood pass following `.claude/rules/live-testing-protocol.md` 12-step protocol. NEVER fabricate datastore state. | `.claude/rules/live-testing-protocol.md` | — |
| **Warmth Bonus** | Vulnerability-exchange trust bonus +2/+1/+0 (diminishing) at `nikita/engine/scoring/calculator.py:227-255`. Spec 058. | `memory/game-mechanics.md` | 058 |

## Conventions

- **File:line citations required**: every concept entry should point to an actual location in `nikita/` / `portal/` / `supabase/migrations/` / `memory/`. Stale citations are a drift signal.
- **Auto-refresh on spec edit**: when a spec adds/modifies a concept, edit this file in the same PR. `/roadmap sync` will surface drift.
- **Superseded concepts**: keep the row, mark `[SUPERSEDED by X]`, link to replacement.
