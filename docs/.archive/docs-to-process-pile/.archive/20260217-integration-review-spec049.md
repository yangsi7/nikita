# Tech Integration Review + Spec Decomposition -- Gate 4.5
Date: 2026-02-17

---

## 1. Implementation Approaches

### 1.1 Life Simulation Enhanced

**Current**: `nikita/life_simulation/` (11 files) -- EventGenerator, MoodCalculator, NarrativeArcSystem, EntityManager, Simulator orchestrator. Events generated daily via LLM (Sonnet 4.5). Mood computed one-way: events -> mood. Day-of-week is a hint in LLM prompt, not a structured routine.

**Approach**:
- Add `WeeklyRoutine` / `DayRoutine` Pydantic models in `life_simulation/models.py`
- Store default routine in `routine.yaml` config (Mon-Sun schedule per doc 24 Section 6)
- Add `users.routine_config` JSONB column (ALTER TABLE, nullable, default `{}`)
- Modify `EventGenerator._build_generation_prompt()` (`event_generator.py:124-234`) to inject routine context for the specific day
- Make mood bidirectional: `simulator.py:98-159` compute mood FIRST, then pass to EventGenerator as new param `mood_state: MoodState`
- Add emotional state + conflict temperature inputs to event generation prompt
- NPC state updates: when life events reference named characters, update `user_social_circles` sentiment/last_event columns (add 2 cols)
- Add `users.meta_instructions` JSONB column -- monthly behavioral arc that shapes event generation
- **NPC consolidation**: Use existing `user_social_circles` (14 cols, Spec 035) as the authoritative NPC store. Add `last_event TIMESTAMPTZ` and `sentiment TEXT` columns. Do NOT create separate `npc_states` JSONB on users table (avoids 3-way NPC system overlap: `nikita_state.friends`, `user_social_circles`, proposed `npc_states`)
- Reconcile NPC character names: existing arcs use Marco/Lena/Viktor/Yuki/Alexei/Katya; doc 24 uses Emma/Lena/Marcus/Viktor/Sarah/Yuki/Mom/Ex. Decision: keep arc character names as canonical, add Mom/Ex as new entries in `user_social_circles`

**Files changed**: `life_simulation/models.py`, `life_simulation/event_generator.py`, `life_simulation/simulator.py`, `life_simulation/arcs.py`, `life_simulation/entity_manager.py`
**New files**: `nikita/config_data/life_simulation/routine.yaml`
**DB migrations**: ALTER TABLE users ADD routine_config JSONB, meta_instructions JSONB; ALTER TABLE user_social_circles ADD last_event TIMESTAMPTZ, sentiment TEXT

### 1.2 Psyche Agent

**Current**: No psyche system. Single Sonnet 4.5 conversation agent (`agents/text/agent.py`). No Opus 4.6 usage.

**Approach**:
- New module: `nikita/agents/psyche/` with `agent.py`, `models.py`, `deps.py`, `batch.py`
- `PsycheState` Pydantic model with structured output: attachment_activation, defense_mode, behavioral_guidance, internal_monologue, vulnerability_level, emotional_tone, topics_to_encourage, topics_to_avoid
- Psyche Agent: `Agent("anthropic:claude-opus-4-6", output_type=PsycheState)` -- no tools, no instructions decorators, stateless per-call
- Database-mediated coordination: Psyche writes to `psyche_states` table, Conversation Agent reads from it
- New `psyche_states` table: id, user_id (UNIQUE), state (JSONB), generated_at, model, token_count
- New repository: `PsycheStateRepository` with `upsert()` and `get_current(user_id)` methods
- Batch mode: pg_cron daily job (5 AM) calls Cloud Run endpoint `/api/v1/tasks/psyche-batch`
- Trigger detector: Rule-based (<5ms) in `message_handler.py` before agent call. Checks: score_delta > 5 (Tier 2), boss encounter / crisis / chapter transition (Tier 3)
- Tier 2: Sonnet 4.5 quick psyche update (~300ms). Tier 3: Opus 4.6 deep analysis (~3s)
- Pre-conversation read: Add `psyche_state: dict | None` to `NikitaDeps` (`agents/text/deps.py:20`)
- New `@agent.instructions` in `agent.py` that injects psyche briefing (~150 tokens)

**Files changed**: `agents/text/deps.py`, `agents/text/agent.py`, `platforms/telegram/message_handler.py`, `pipeline/stages/prompt_builder.py`, `pipeline/models.py`, `pipeline/templates/system_prompt.j2`
**New files**: `nikita/agents/psyche/agent.py`, `nikita/agents/psyche/models.py`, `nikita/agents/psyche/deps.py`, `nikita/agents/psyche/batch.py`, `nikita/db/repositories/psyche_state_repository.py`, `nikita/db/models/psyche_state.py`, `nikita/api/routes/tasks/psyche.py`
**DB migrations**: CREATE TABLE psyche_states + index + RLS; new pg_cron job

### 1.3 Conflict System

**Current**: `nikita/conflicts/` (7 files) -- TriggerDetector (rule + LLM), ConflictGenerator (cooldown-based), EscalationManager (3-level time-based), ResolutionManager (LLM quality eval), BreakupManager. Discrete event model: detect -> generate -> escalate -> resolve. Boss encounters: single-turn, binary PASS/FAIL.

**Approach -- split into two sub-systems**:

**A. Temperature Gauge + Gottman Ratio (non-boss conflicts)**:
- New `ConflictTemperature` model in `conflicts/models.py`: temperature (0-100), zone computation, last_updated
- New `GottmanTracker` model: positive_count, negative_count, ratio, horsemen_detected[]
- Composite `ConflictState` JSONB schema: {temperature, type, started_at, repair_attempts, positive_count, negative_count, gottman_ratio, boss_phase}
- Add `conflict_state` JSONB column to `nikita_emotional_states` table (not `users` -- keeps conflict data co-located with emotional data)
- Modify `conflicts/detector.py:detect()` to update temperature accumulator
- Modify `conflicts/generator.py` to use temperature zones instead of flat 4h cooldown
- Modify `scoring/analyzer.py:ANALYSIS_SYSTEM_PROMPT` to detect Four Horsemen behaviors
- Add Gottman counter update in `scoring/service.py:score_interaction()` post-scoring
- Modify `conflicts/resolution.py:resolve()` to reduce temperature + update Gottman counters on repair
- Modify `conflicts/escalation.py:acknowledge()` to reduce temperature (not just reset timer)
- Add `users.last_conflict_at` TIMESTAMPTZ column for cross-conflict cooldown tracking

**B. Multi-Phase Boss Encounters** (separate concern, higher risk):
- Add `BossPhaseState` model in `chapters/boss.py`: current_phase (0-3), turn_count, phase_prompts
- Add `PARTIAL` to `BossResult` enum (`chapters/judgment.py:19`)
- Expand `BossPrompt` TypedDict to include per-phase prompts: 4 phases x 5 chapters = 20 variants
- Modify `BossStateMachine` to track phase progression between messages
- Modify `judgment.py:judge_boss_outcome()` to evaluate multi-turn conversation against phase context
- Add boss phase state persistence to `conflict_state.boss_phase` JSONB
- Feature flag: `multi_phase_boss_enabled` -- old single-turn flow preserved as fallback
- Modify `message_handler.py:_handle_boss_response()` to loop through phases instead of single-shot judgment

**Files changed**: `conflicts/models.py`, `conflicts/detector.py`, `conflicts/generator.py`, `conflicts/escalation.py`, `conflicts/resolution.py`, `conflicts/breakup.py`, `scoring/analyzer.py`, `scoring/service.py`, `scoring/models.py`, `chapters/boss.py`, `chapters/judgment.py`, `chapters/prompts.py`, `platforms/telegram/message_handler.py`
**New files**: `nikita/engine/chapters/phase_manager.py` (multi-phase boss orchestration)
**DB migrations**: ALTER TABLE nikita_emotional_states ADD conflict_details JSONB; ALTER TABLE users ADD last_conflict_at TIMESTAMPTZ

### 1.4 Warmth Meter + Vulnerability Dynamic

**Current**: `nikita_emotional_states` has 4D state (arousal/valence/dominance/intimacy). `vulnerability_level` is semi-static in prompt template Section 9. No vulnerability exchange counter.

**Approach**:
- This is primarily a **presentation layer** change for the portal + a **scoring bonus** mechanic
- Add `vulnerability_exchanges INT DEFAULT 0` to `user_metrics` table
- Warmth Meter = visual representation of the existing composite relationship_score (0-100)
- Vulnerability Dynamic: when Nikita shares vulnerability AND player responds with empathy, increment `vulnerability_exchanges` counter. Triggers: LLM-detected in scoring analyzer
- Scoring bonus: vulnerability exchanges give +2 trust bonus on top of normal metric deltas
- Portal: "Warmth Meter" component = relationship_score gauge + vulnerability milestone markers
- Prompt template Section 9 (PSYCHOLOGICAL DEPTH) enriched with dynamic vulnerability from psyche_state

**Files changed**: `scoring/analyzer.py` (detect V-exchanges), `scoring/calculator.py` (apply bonus), `pipeline/templates/system_prompt.j2` (Section 9 enrichment)
**New files**: None (portal changes are portal-side)
**DB migrations**: ALTER TABLE user_metrics ADD vulnerability_exchanges INT DEFAULT 0

### 1.5 Portal: Nikita's Day

**Current**: Portal has 6 player routes and 7 admin routes. No "Nikita's Day" timeline view.

**Approach**:
- New page: `/nikita-day` (or expand existing `/dashboard`)
- Timeline component: reads `nikita_life_events` table for today's events, renders as vertical timeline
- Social Circle viz: reads `user_social_circles` for NPC state, renders as relationship map
- Tips section: reads `psyche_states.behavioral_guidance` for contextual advice
- Data comes from existing API endpoints (or new thin endpoints proxied through Vercel)
- This is a **pure frontend spec** -- depends on backend data being populated by Life Sim and Psyche specs
- Uses shadcn/ui components: Card, Avatar, Badge, Progress for timeline items

**Files changed**: None (backend already serves the data)
**New files**: `portal/src/app/(player)/nikita-day/page.tsx`, `portal/src/components/timeline/`.*, `portal/src/components/social-circle/`.*
**DB migrations**: None (reads existing tables)

### 1.6 Prompt Caching

**Current**: Prompt is pre-built by pipeline stage 9 and stored in `ready_prompts`. Injected via `@agent.instructions` decorators. No Anthropic API-level caching. `NIKITA_PERSONA` in persona.py conflicts with template Section 1 (Brooklyn vs Berlin backstory).

**Approach**:
- Restructure prompt assembly to place static content at top (for Anthropic prefix caching)
- Resolve NIKITA_PERSONA conflict: deprecate `persona.py`, use only template Section 1 (Berlin/Prenzlauer Berg is canonical)
- Add `cache_control: {"type": "ephemeral"}` breakpoints to the 4 most stable layers:
  - Breakpoint 1: L1 IDENTITY + L2 IMMERSION (~2.5K tok, static)
  - Breakpoint 2: L5 CHAPTER + L6 VICE + L7 RESPONSE GUIDELINES (~1.2K tok, slow-changing)
  - L3 PSYCHE (~150 tok) and L4 DYNAMIC (~3K tok) NOT cached (change frequently)
- Modify `agents/text/agent.py:generate_response()` to construct system prompt with cache_control blocks
- Modify prompt builder to track per-layer token counts in `ready_prompts.context_snapshot` JSONB
- Add 1-hour TTL option for voice sessions: `"cache_control": {"type": "ephemeral", "ttl": "3600"}`
- Adjust truncation order: Vice -> Chapter -> Inner Life -> Psychology (keep psyche state untouched)

**Files changed**: `agents/text/agent.py`, `agents/text/persona.py` (deprecate), `pipeline/stages/prompt_builder.py`, `pipeline/templates/system_prompt.j2`
**New files**: None
**DB migrations**: None

### 1.7 NPC State Management (Consolidation)

**Current**: Three overlapping NPC systems:
1. `nikita_state.friends` JSONB: 3 hardcoded NPCs (Maya, Sophie, Lena)
2. `user_social_circles` (14 cols, Spec 035): rich relational NPC tracking
3. `nikita_entities` + `nikita_narrative_arcs`: template-level arc characters (Marco, Lena, Viktor, etc.)

**Approach**:
- Designate `user_social_circles` as the SINGLE authoritative NPC store
- Add `last_event TIMESTAMPTZ` and `sentiment TEXT` columns to `user_social_circles`
- Migrate existing `nikita_state.friends` data into `user_social_circles` entries
- Seed 8 canonical NPCs per user: Emma/Lena, Marcus/Viktor, Sarah/Yuki, Mom, Ex (merge with arc characters: map Lena->Lena, Viktor->Viktor, add new ones)
- Deprecate `nikita_state.friends` JSONB (mark as legacy, stop reading)
- `nikita_entities` remains as the static entity registry (places, projects, colleagues) -- not overlapping
- Update `entity_manager.py:get_entity_context()` to include dynamic state from `user_social_circles`
- Update `arcs.py` character references to look up `user_social_circles` for current sentiment/state

**Decision**: This consolidation is part of Spec 049 (Life Sim Enhanced), NOT its own spec. It's a prerequisite for proper NPC-driven life events. Keeping it separate would create a chicken-and-egg dependency.

**Files changed**: `life_simulation/entity_manager.py`, `life_simulation/arcs.py`, `life_simulation/simulator.py`
**DB migrations**: ALTER TABLE user_social_circles ADD last_event TIMESTAMPTZ, sentiment TEXT; data migration seed script

### 1.8 Context Engineering (Dual-Process Routing + Budget Optimization)

**Current**: Single model (Sonnet 4.5) for all messages. No routing. Token budget: 5,500-6,500 text, 1,800-2,200 voice. Counting via tiktoken.

**Approach**:
- Dual-process routing is IMPLICIT in the Psyche Agent trigger tier system:
  - Tier 1 (90%): cached psyche state read, Sonnet 4.5 conversation = "System 1"
  - Tier 2 (8%): Sonnet quick psyche update = "System 1.5"
  - Tier 3 (2%): Opus deep analysis = "System 2"
- No separate "router" model needed -- trigger detector IS the router (rule-based, <5ms)
- Context window optimization:
  - Implement 4-tier hierarchy in prompt assembly: system prompt (cached) -> tools -> dynamic context -> conversation
  - Add conversation compaction at every 15 turns: summarize older messages, keep last 5 verbatim
  - Memory retrieval includes relevance scores and timestamps
  - Sub-agent isolation: scoring agent gets narrow context (message + metrics only, ~2K tok)
- Token budgeting: target ~4K system + ~2K memory + ~2K history = ~8K total input
- Progressive disclosure: memory loaded on-demand via `recall_memory()` tool, not dumped upfront

**Decision**: This is NOT its own spec. Dual-process routing is part of Psyche Agent (Spec 050). Context optimization is part of Prompt Caching (Spec 054). No separate spec needed.

**Files changed**: `agents/text/agent.py` (compaction), `agents/text/history.py` (sliding window), `pipeline/stages/prompt_builder.py` (budget optimization)

---

## 2. Spec Decomposition

### Final Spec List

| Spec | Name | Scope Summary | Task Est | Days Est |
|------|------|---------------|----------|----------|
| 049 | Life Simulation Enhanced | Weekly routine, emotional-driven events, NPC consolidation, meta-instructions, bidirectional mood | 20-25 | 4-5 |
| 050 | Psyche Agent | New agent (Opus 4.6), psyche_states table, batch job, trigger detector, pre-conv read, prompt L3 injection | 22-28 | 4-5 |
| 051 | Conflict System CORE | Temperature gauge, Gottman ratio, repair tracking, Four Horsemen detection, conflict_state JSONB | 18-22 | 3-4 |
| 052 | Multi-Phase Boss + Warmth | Multi-turn boss encounters, PARTIAL outcome, boss phase persistence, vulnerability exchanges, warmth meter scoring | 20-25 | 3-5 |
| 053 | Portal: Nikita's Day | Timeline page, social circle viz, tips section, warmth meter display | 15-20 | 3-4 |
| 054 | Prompt Caching + Context Engineering | Anthropic cache_control, persona reconciliation, layer restructure, compaction, budget optimization | 15-18 | 2-3 |

**Total**: 110-138 tasks, 19-26 days

### Spec Boundaries Detail

#### Spec 049: Life Simulation Enhanced
- **Scope**: Weekly routine system, emotional-driven event generation, NPC consolidation (3 systems -> 1), meta-instruction hierarchy, bidirectional mood-event flow
- **Files changed**: `life_simulation/models.py`, `life_simulation/event_generator.py`, `life_simulation/simulator.py`, `life_simulation/arcs.py`, `life_simulation/entity_manager.py`, `life_simulation/store.py`
- **New files**: `nikita/config_data/life_simulation/routine.yaml`, NPC seed migration script
- **DB migrations**: (1) ALTER TABLE users ADD routine_config JSONB DEFAULT '{}', meta_instructions JSONB DEFAULT '{}'; (2) ALTER TABLE user_social_circles ADD last_event TIMESTAMPTZ, sentiment TEXT; (3) Seed 8 canonical NPCs per existing user
- **Dependencies**: none (first in chain)
- **Key risks**: NPC reconciliation complexity (3 systems, different character names); bidirectional mood requires careful testing to avoid feedback loops
- **Acceptance criteria themes**: routine-aware events generated per day-of-week; mood state feeds into event generation; NPC states updated on life events; meta-instructions shape event themes; all existing life sim tests still pass

#### Spec 050: Psyche Agent
- **Scope**: New Opus 4.6 psyche agent, PsycheState model, psyche_states table, daily batch job, 3-tier trigger detector, pre-conversation psyche read, prompt Layer 3 injection
- **Files changed**: `agents/text/deps.py`, `agents/text/agent.py`, `platforms/telegram/message_handler.py`, `pipeline/stages/prompt_builder.py`, `pipeline/models.py`, `pipeline/templates/system_prompt.j2`
- **New files**: `nikita/agents/psyche/agent.py`, `nikita/agents/psyche/models.py`, `nikita/agents/psyche/deps.py`, `nikita/agents/psyche/batch.py`, `nikita/db/repositories/psyche_state_repository.py`, `nikita/db/models/psyche_state.py`, `nikita/api/routes/tasks/psyche.py`
- **DB migrations**: CREATE TABLE psyche_states (+ index + RLS); pg_cron job `nikita-psyche-batch`
- **Dependencies**: Spec 049 (psyche agent reads life events + NPC states for analysis context)
- **Key risks**: Opus 4.6 cost if trigger rate exceeds 10%; psyche batch prompt quality (garbage-in-garbage-out); latency for Tier 3 triggers (~3s blocks message response)
- **Acceptance criteria themes**: daily psyche batch generates valid PsycheState; trigger detector routes correctly (90/8/2); psyche briefing injected in system prompt; conversation agent behavior influenced by psyche state; costs within $7/mo budget

#### Spec 051: Conflict System CORE
- **Scope**: Temperature gauge (0-100), Gottman ratio tracking (5:1 target), repair attempt tracking, Four Horsemen detection in scoring, conflict_state JSONB, temperature-based conflict injection
- **Files changed**: `conflicts/models.py`, `conflicts/detector.py`, `conflicts/generator.py`, `conflicts/escalation.py`, `conflicts/resolution.py`, `scoring/analyzer.py`, `scoring/service.py`, `scoring/models.py`, `pipeline/stages/conflict.py`
- **New files**: None (extends existing conflict module)
- **DB migrations**: ALTER TABLE nikita_emotional_states ADD conflict_details JSONB DEFAULT '{}'; ALTER TABLE users ADD last_conflict_at TIMESTAMPTZ
- **Dependencies**: none (operates on existing scoring/conflict infrastructure)
- **Key risks**: Temperature calibration (zones need game-testing); Gottman ratio initialization for existing users; Four Horsemen LLM detection accuracy
- **Acceptance criteria themes**: temperature increases on negative interactions; temperature decreases on positive/repair; Gottman ratio tracked per user; Four Horsemen behaviors identified by scoring analyzer; conflict injection probability driven by temperature zones; all existing conflict tests updated

#### Spec 052: Multi-Phase Boss + Warmth
- **Scope**: 3-5 turn boss encounters with 4 phases (OPENING/ESCALATION/CRISIS_PEAK/RESOLUTION), PARTIAL outcome, boss phase persistence, vulnerability exchange counter, warmth meter scoring bonus
- **Files changed**: `chapters/boss.py`, `chapters/judgment.py`, `chapters/prompts.py`, `platforms/telegram/message_handler.py`, `scoring/analyzer.py`, `scoring/calculator.py`
- **New files**: `nikita/engine/chapters/phase_manager.py`
- **DB migrations**: ALTER TABLE user_metrics ADD vulnerability_exchanges INT DEFAULT 0 (boss_phase stored in conflict_state JSONB from Spec 051)
- **Dependencies**: Spec 051 (uses conflict_state.boss_phase for phase persistence)
- **Key risks**: HIGHEST RISK SPEC -- fundamental redesign of boss encounters; 20 phase-prompt variants needed (4 phases x 5 chapters); multi-turn state management across messages; judgment quality with multi-turn context; feature flag complexity
- **Acceptance criteria themes**: boss encounters span 3-5 messages; phase progression tracked correctly; PARTIAL outcome supported; vulnerability exchanges detected and scored; boss_phase persisted between messages; old single-turn boss preserved behind feature flag

#### Spec 053: Portal: Nikita's Day
- **Scope**: New portal page with timeline, social circle visualization, tips section, warmth meter display
- **Files changed**: None backend-side (reads existing API data)
- **New files**: `portal/src/app/(player)/nikita-day/page.tsx`, `portal/src/components/timeline/*.tsx`, `portal/src/components/social-circle/*.tsx`, `portal/src/components/warmth-meter/*.tsx`
- **DB migrations**: None
- **Dependencies**: Spec 049 (life events data), Spec 050 (psyche tips), Spec 052 (warmth meter data)
- **Key risks**: Low technical risk; main risk is data availability if backend specs not complete; design fidelity with glassmorphism dark theme
- **Acceptance criteria themes**: timeline shows today's life events with time-of-day markers; social circle renders NPC relationship map; tips section shows psyche behavioral guidance; warmth meter displays relationship score with vulnerability milestones

#### Spec 054: Prompt Caching + Context Engineering
- **Scope**: Anthropic cache_control blocks, persona.py deprecation, prompt layer restructure for caching, conversation compaction, token budget optimization, per-layer token tracking
- **Files changed**: `agents/text/agent.py`, `agents/text/persona.py`, `agents/text/history.py`, `pipeline/stages/prompt_builder.py`, `pipeline/templates/system_prompt.j2`
- **New files**: None
- **DB migrations**: None
- **Dependencies**: Spec 050 (prompt Layer 3 must exist for proper cache boundary placement)
- **Key risks**: Prompt caching sensitivity to exact character matching (cache misses); persona.py deprecation may break legacy fallback path; compaction quality (losing important context)
- **Acceptance criteria themes**: cache hit rates >80% on static layers; persona.py deprecated with no regressions; conversation compacted at 15-turn threshold; per-layer token counts tracked in ready_prompts; total input tokens reduced by 20-30%

### Boundary Decisions

**1. NPC consolidation is part of Spec 049 (Life Sim), NOT its own spec.**
Rationale: NPC state is consumed by life event generation. Separating it creates a chicken-and-egg: Life Sim needs NPC data to generate events, NPC data is updated by life events. Clean solution: bundle NPC consolidation as the first tasks of Spec 049, then build event generation on top.

**2. Shared DB migrations are NOT a separate infrastructure spec.**
Rationale: Each spec owns its own migrations. Migrations are additive (nullable columns, new tables) -- no ordering conflicts. Running `supabase db push` handles them sequentially. A separate infra spec adds process overhead without reducing risk.

**3. Dual-process routing is NOT its own spec.**
Rationale: The "router" is just the trigger detector in Spec 050 (Psyche Agent). It's 50-100 lines of rule-based code, not a separate system. Context optimization folds into Spec 054 (Prompt Caching). No standalone spec needed.

**4. Multi-phase boss is SEPARATED from temperature gauge into its own spec (052).**
Rationale: Engine analysis flags multi-phase boss as "HIGHEST RISK -- requires fundamental redesign". Temperature gauge (Spec 051) is a continuous improvement to existing conflict system. Boss redesign is a breaking change that needs a feature flag. Separating them means Spec 051 can ship and be tested while Spec 052 is still in development. Also enables: if Spec 052 is cut for timeline, Spec 051 still delivers value.

**5. Portal spec (053) is last because it depends on backend data from 049, 050, 052.**
Rationale: Pure frontend -- can start UI scaffolding early but needs backend APIs to populate. Mock data during development, wire to real APIs when backend specs merge.

**6. Conflict state stored in `nikita_emotional_states.conflict_details` JSONB, NOT new column on `users`.**
Rationale: Backend-DB analysis shows `nikita_emotional_states` already has `conflict_state` enum + trigger fields. Co-locating the richer conflict model here avoids data scatter. One table for all emotional + conflict state per user.

---

## 3. Dependency DAG

```
Spec 049: Life Sim Enhanced
    |
    v
Spec 050: Psyche Agent  ----+
    |                        |
    v                        |
Spec 051: Conflict CORE      |   (051 has no hard dep on 049/050,
    |                        |    but benefits from life event data)
    v                        |
Spec 052: Multi-Phase Boss   |
    |                        |
    v                        v
Spec 053: Portal Nikita's Day
    |
    v
Spec 054: Prompt Caching + Context Engineering


PARALLEL OPPORTUNITIES:
=======================
             Phase 1           Phase 2           Phase 3
           (days 1-5)        (days 5-10)       (days 10-16)

  [049 Life Sim]  ------+
                        |---> [050 Psyche] ---+
  [051 Conflict] ------+                      |---> [052 Boss]
                        |                     |---> [053 Portal]
                        +---> [054 Caching] --+


CRITICAL PATH (longest chain):
  049 (5d) -> 050 (5d) -> 052 (5d) -> 053 (4d) = 19 days

PARALLEL PATH:
  051 (4d) can run in parallel with 049
  054 (3d) can start after 050 completes, parallel with 052


BUILD ORDER (recommended):
  Wave A (parallel): 049 + 051 (days 1-5)
  Wave B (sequential): 050 (days 5-10, needs 049 data)
  Wave C (parallel): 052 + 054 (days 10-15, 052 needs 051, 054 needs 050)
  Wave D: 053 (days 15-19, needs 049+050+052 data)
```

---

## 4. Integration Points

| Interface | Spec A | Spec B | Contract |
|-----------|--------|--------|----------|
| `nikita_life_events` table rows | 049 (writes) | 050 (reads for psyche analysis) | EventGenerator writes; PsycheAgent reads 7-day window |
| `user_social_circles` enriched NPC data | 049 (writes sentiment/last_event) | 050 (reads for psyche context) | NPC state fields: sentiment, last_event |
| `psyche_states` table | 050 (writes) | prompt_builder, message_handler (reads) | PsycheState JSONB schema: 8 fields |
| `psyche_states.behavioral_guidance` | 050 (writes) | 053 (reads for tips section) | String field, portal displays as-is |
| `conflict_details` JSONB on emotional_states | 051 (writes temperature, gottman) | 052 (reads boss_phase) | ConflictState schema: temperature, gottman_ratio, boss_phase |
| `conflict_state.boss_phase` field | 052 (writes during boss) | 051 (reads for temperature zone calc) | INT 0-3 or null |
| `user_metrics.vulnerability_exchanges` | 052 (writes) | 053 (reads for warmth meter) | INT counter |
| `users.routine_config` JSONB | 049 (writes) | 050 (reads for psyche context) | WeeklyRoutine schema |
| `users.meta_instructions` JSONB | 049 (writes) | 050 (reads for psyche), prompt_builder (reads for context) | MetaInstruction schema |
| prompt Layer 3 (psyche section) | 050 (creates section) | 054 (wraps with cache_control) | Template section in system_prompt.j2 |
| `ready_prompts.context_snapshot` | 054 (writes per-layer counts) | monitoring (reads) | JSONB with per-layer token counts |
| `scoring/analyzer.py` horsemen detection | 051 (adds detection) | 052 (uses for vulnerability detection) | behaviors_identified[] includes horsemen tags |

---

## 5. Migration Strategy

### Shared Infrastructure (before all specs)

None required. Each spec owns its own additive migrations. No breaking changes.

### Per-Spec Migrations

| Spec | Migration Name | Type | Downtime |
|------|---------------|------|----------|
| 049 | `add_life_sim_enhanced_columns` | ALTER TABLE (3 cols) | Zero |
| 049 | `seed_canonical_npcs` | INSERT data | Zero |
| 050 | `create_psyche_states_table` | CREATE TABLE + index + RLS | Zero |
| 050 | `add_psyche_batch_cron_job` | pg_cron schedule | Zero |
| 051 | `add_conflict_details_column` | ALTER TABLE (2 cols) | Zero |
| 052 | `add_vulnerability_exchanges` | ALTER TABLE (1 col) | Zero |
| 053 | None | -- | -- |
| 054 | None | -- | -- |

All migrations are additive: nullable columns with defaults, new tables, new indexes. Zero-downtime deployment.

### Feature Flag Plan

| Flag | Spec | Default | Purpose |
|------|------|---------|---------|
| `life_sim_enhanced` | 049 | OFF | Gates: routine-aware events, bidirectional mood, NPC-driven events |
| `psyche_agent_enabled` | 050 | OFF | Gates: psyche batch, trigger detection, L3 prompt injection |
| `conflict_temperature` | 051 | OFF | Gates: temperature gauge, Gottman tracking (falls back to current cooldown model) |
| `multi_phase_boss_enabled` | 052 | OFF | Gates: multi-turn boss, PARTIAL outcome (falls back to single-turn) |
| `prompt_caching_enabled` | 054 | OFF | Gates: cache_control blocks, compaction (falls back to current prompt assembly) |

Rollout order: 049 -> 051 -> 050 -> 054 -> 052 (boss last, highest risk).

---

## 6. Risk Matrix

| Spec | Risk Level | Main Threat | Mitigation |
|------|-----------|-------------|------------|
| 049 | MEDIUM | NPC 3-way consolidation complexity; character name reconciliation across arc templates | Phased: consolidate first, then build on top. Keep `nikita_entities` for static data. Map character names explicitly. |
| 050 | MEDIUM | Opus 4.6 cost overrun if trigger rate > 10%; psyche prompt quality; Tier 3 latency (3s) blocking UX | Cost monitoring dashboard. Hardcode Tier 3 max 2% with circuit breaker. Async Tier 3 with fallback to cached state. |
| 051 | MEDIUM | Temperature zone calibration (zones too tight = constant conflict, too wide = no conflict); Gottman ratio cold start | Default temperature 0 for all existing users. Calibrate zones via playtesting. Initialize Gottman from existing score_history. |
| 052 | **HIGH** | Fundamental boss redesign; 20 phase-prompt variants; multi-turn state management; judgment quality across turns | Feature flag with fallback. Implement phase 1 (OPENING) first, add phases incrementally. Test each chapter independently. |
| 053 | LOW | Data availability if backend specs delayed; design polish | Mock data during development. Design-first approach with Storybook. |
| 054 | LOW-MEDIUM | Cache miss sensitivity to exact character matching; persona.py deprecation breaking legacy path | Verify cache hits with metrics before disabling fallback. Keep persona.py import for 1 release cycle. |

---

## 7. Recommendations

**Ordered implementation plan:**

1. **Wave A (days 1-5, parallel)**:
   - Start Spec 049 (Life Sim Enhanced) -- it has no dependencies and feeds data to everything downstream
   - Start Spec 051 (Conflict CORE) in parallel -- it also has no dependencies and the temperature/Gottman model is self-contained

2. **Wave B (days 5-10)**:
   - Start Spec 050 (Psyche Agent) -- depends on 049 for life events and NPC data
   - Spec 051 should be finishing -- its output (conflict_state JSONB) feeds into Spec 052

3. **Wave C (days 10-15, parallel)**:
   - Start Spec 052 (Multi-Phase Boss) -- depends on 051 for conflict_state.boss_phase
   - Start Spec 054 (Prompt Caching) -- depends on 050 for L3 psyche section existence
   - Begin portal component scaffolding for Spec 053 with mock data

4. **Wave D (days 15-19)**:
   - Complete Spec 053 (Portal) -- wire to real APIs from 049, 050, 052
   - Finalize Spec 054 (verify cache hit rates, deprecate persona.py)

**Key decision points:**
- After Wave A: validate NPC consolidation worked cleanly, temperature zones feel right
- After Wave B: validate psyche agent cost is within budget, trigger routing accuracy
- After Wave C: validate multi-phase boss playtesting, cache hit rates meet targets
- After Wave D: full integration test, feature flag rollout plan

**Deferred items (not in these specs):**
- Legacy table cleanup (nikita_state deprecation, user_facts removal, graphiti_group_id drop) -- separate cleanup spec
- Neo4j env var removal from Cloud Run -- can do anytime
- Supabase Vault for pg_cron auth tokens -- security hardening spec
- Cloud Run memory increase (512Mi -> 1Gi) -- monitor during Spec 050 Opus batch, increase if needed
- pgVector dimension reduction (1536 -> 768) -- optimization if storage exceeds free tier

---

## Appendix: Evidence Log

| Query | Source | Key Finding |
|-------|--------|-------------|
| Backend-DB analysis | `20260217-backend-db-analysis-spec049.md` | 35 tables, 84 RLS policies, 110+ indexes, 6 pg_cron jobs; 3 NPC overlap systems identified |
| Pipeline analysis | `20260217-pipeline-code-analysis-spec049.md` | 9 stages, PipelineContext 40+ fields; best psyche injection point = pre-conversation in message_handler |
| Engine analysis | `20260217-engine-code-analysis-spec049.md` | Multi-phase boss = HIGHEST RISK (VERY LARGE gap); temperature gauge = LARGE gap; 15-20 day total estimate |
| Fact-check | `20260217-fact-check-spec049.md` | $30-37/mo LLM costs confirmed; pg_cron free tier unconfirmed; JSONB <5ms optimistic (realistic 10-50ms) |
| Research | `20260217-research-spec049-context.md` | Prompt caching max 4 breakpoints; dual-process = 60-80% cost savings; Gottman 5:1 ratio maps to scoring |
| Doc 24 | `docs/brainstorm/proposal/24-system-architecture-diagram.md` | 7-layer prompt model, paired agents, 5 context modules, conflict is CORE |
