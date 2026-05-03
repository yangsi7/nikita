# Spec Preparation Context -- Gate 4.5 Final Synthesis

Date: 2026-02-17
Sources: 9 agent outputs + doc 24 (24-system-architecture-diagram.md)
Purpose: INPUT for SDD spec generation team (6 independent specs)

---

## Section 1: Requirements Tree

```
DOC 24 REQUIREMENTS
|
+-- [1] PAIRED AGENT MODEL (Section 2)
|   +-- [NEW] Psyche Agent (Opus 4.6)
|   |   +-- create: nikita/agents/psyche/{agent,models,deps,batch}.py
|   |   +-- create: nikita/db/repositories/psyche_state_repository.py
|   |   +-- create: nikita/db/models/psyche_state.py
|   |   +-- create: nikita/api/routes/tasks/psyche.py
|   |   +-- depends: psyche_states table, pg_cron job
|   +-- [EXISTS] Conversation Agent (Sonnet 4.5)
|   |   +-- agents/text/agent.py:56 -- no structural change
|   |   +-- changes: add psyche_state to NikitaDeps (deps.py:20)
|   |   +-- changes: add @agent.instructions for psyche briefing (agent.py)
|   +-- [NEW] Trigger Detector (rule-based, <5ms)
|   |   +-- create: logic in message_handler.py before agent call
|   |   +-- Tier 1 (90%): read cached, Tier 2 (8%): Sonnet, Tier 3 (2%): Opus
|   +-- [NEW] Pre-conversation psyche read
|       +-- changes: message_handler.py:235 (before text_agent_handler.handle)
|
+-- [2] CONTEXT RETRIEVAL MODULES (Section 3)
|   +-- Module 1: Memories (pgVector)
|   |   +-- [EXISTS] memory_facts table, SupabaseMemory -- no changes needed
|   +-- Module 2: Friends/NPCs
|   |   +-- [PARTIAL] user_social_circles exists (14 cols, Spec 035)
|   |   +-- [PARTIAL] nikita_state.friends JSONB (Maya/Sophie/Lena)
|   |   +-- [PARTIAL] nikita_entities + arcs (Marco/Lena/Viktor/Yuki/Alexei/Katya)
|   |   +-- [CONFLICT] doc 24 proposes users.npc_states JSONB (Emma/Marcus/Sarah/Mom/Ex)
|   |   +-- DECISION: use user_social_circles as canonical; add sentiment + last_event cols
|   +-- Module 3: Timeline/Life Events
|   |   +-- [PARTIAL] nikita_life_events table exists (11 cols)
|   |   +-- changes: event_generator.py:82 -- add mood_state + conflict_temperature params
|   |   +-- changes: simulator.py:98 -- bidirectional mood-event flow
|   +-- Module 4: Conflicts
|   |   +-- [PARTIAL] nikita_emotional_states.conflict_state enum (5 values)
|   |   +-- [PARTIAL] conflicts/ module (7 files) -- discrete event model
|   |   +-- changes: add temperature gauge (0-100), Gottman ratio, repair tracking
|   |   +-- changes: add conflict_details JSONB to nikita_emotional_states
|   +-- Module 5: Psyche State
|       +-- [NEW] psyche_states table (JSONB, 1 row/user)
|       +-- create: PsycheState Pydantic model (8 fields)
|       +-- create: pg_cron daily batch job
|
+-- [3] PROMPT ASSEMBLY (Section 4)
|   +-- L1: IDENTITY (~2K tok)
|   |   +-- [PARTIAL] system_prompt.j2:1-35 (~400 tok, Berlin backstory)
|   |   +-- [CONFLICT] persona.py:18 (~1600 tok, Brooklyn backstory)
|   |   +-- DECISION: slim persona.py to behavioral guide only; template = sole identity
|   +-- L2: IMMERSION + PLATFORM (~500 tok)
|   |   +-- [EXISTS] system_prompt.j2:37-119 -- rename only
|   +-- L3: PSYCHE STATE (~150 tok)
|   |   +-- [NEW] insert between L2 and L4 in template
|   |   +-- source: psyche_states table JSONB
|   +-- L4: DYNAMIC CONTEXT (~3K tok)
|   |   +-- [EXISTS] S4-S8 in template -- repackage as L4a-L4e
|   +-- L5: CHAPTER BEHAVIOR (~300 tok)
|   |   +-- [EXISTS] system_prompt.j2:418-594 -- rename only
|   +-- L6: VICE SHAPING (~200 tok)
|   |   +-- [EXISTS] system_prompt.j2:597-624 -- rename only
|   +-- L7: RESPONSE GUIDELINES (~700 tok)
|   |   +-- [EXISTS] system_prompt.j2:627-731 -- rename only
|   +-- S9: PSYCHOLOGICAL DEPTH (~540 tok)
|       +-- [ORPHANED] not mapped in doc 24's 7-layer model
|       +-- DECISION: split -- static parts -> L1, dynamic vulnerability -> L3
|
+-- [4] CONFLICT SYSTEM (Section 9)
|   +-- Temperature Gauge (0-100)
|   |   +-- [NEW] ConflictTemperature model, zones {0-30,30-60,60-80,80-100}
|   |   +-- changes: detector.py:detect() -- update temperature accumulator
|   |   +-- changes: generator.py -- use temperature zones instead of flat 4h cooldown
|   +-- Gottman Ratio (5:1 target)
|   |   +-- [NEW] positive/negative counters, Four Horsemen detection
|   |   +-- changes: scoring/analyzer.py:31 -- add Horsemen to ANALYSIS_SYSTEM_PROMPT
|   |   +-- changes: scoring/service.py:52 -- increment counters post-scoring
|   +-- Repair Attempts
|   |   +-- [PARTIAL] resolution.py:150 has quality-scored resolution
|   |   +-- changes: connect resolution to temperature reduction + Gottman update
|   +-- Multi-Phase Boss (3-5 turns)
|   |   +-- [NEW] BossPhaseState (4 phases x 5 chapters)
|   |   +-- [NEW] PARTIAL outcome type in BossResult enum
|   |   +-- changes: boss.py, judgment.py, prompts.py -- fundamental redesign
|   |   +-- changes: message_handler.py:_handle_boss_response() -- multi-turn loop
|
+-- [5] LIFE SIMULATION ENHANCED (Section 6)
|   +-- Weekly Routine
|   |   +-- [NEW] WeeklyRoutine/DayRoutine models
|   |   +-- [NEW] routine.yaml default config
|   |   +-- [NEW] users.routine_config JSONB column
|   |   +-- changes: event_generator.py:124 -- inject routine context per day
|   +-- Emotional-Driven Events
|   |   +-- [PARTIAL] mood_calculator.py:79 computes mood FROM events (one-way)
|   |   +-- changes: make bidirectional -- mood feeds INTO event generation
|   |   +-- changes: event_generator.py:82 -- add mood_state param
|   +-- Meta-Instructions
|   |   +-- [NEW] users.meta_instructions JSONB column
|   |   +-- [NEW] monthly generation job (DEFERRED per devil's advocate M1)
|   |   +-- changes: event_generator.py -- inject monthly context
|   +-- NPC Consolidation
|       +-- [PARTIAL] 3 existing systems -> 1 canonical (user_social_circles)
|       +-- changes: entity_manager.py, arcs.py -- reference user_social_circles
|       +-- changes: user_social_circles ADD last_event, sentiment columns
|
+-- [6] WARMTH METER + VULNERABILITY (Section implied)
|   +-- [NEW] user_metrics.vulnerability_exchanges INT column
|   +-- changes: scoring/analyzer.py -- detect V-exchanges
|   +-- changes: scoring/calculator.py -- apply +2 trust bonus (diminishing returns)
|   +-- Portal: warmth meter component = relationship_score gauge
|
+-- [7] PROMPT CACHING (Section 4, cache strategy)
|   +-- [NEW] Anthropic cache_control breakpoints (max 4)
|   |   +-- BP1: L1+L2+L7 (~3,200 tok, 99% hit) -- static
|   |   +-- BP2: L3+L5+L6 (~650 tok, 90% hit) -- semi-static
|   |   +-- BP3: tool definitions (~300 tok, 99% hit)
|   |   +-- Dynamic: L4 (~3,400 tok) -- never cached
|   +-- [CONFLICT] prompt stacking: NIKITA_PERSONA + pipeline prompt = ~7,400 tok unbudgeted
|   +-- changes: agent.py -- guard add_chapter_behavior() when pipeline prompt exists
|   +-- changes: system_prompt.j2 -- reorder for cache optimization
|   +-- changes: prompt_builder.py -- disable Haiku enrichment on cached sections
|
+-- [8] PORTAL: NIKITA'S DAY (Section implied)
|   +-- [NEW] /nikita-day page with timeline, social circle, tips, warmth meter
|   +-- create: portal/src/app/(player)/nikita-day/page.tsx
|   +-- create: portal/src/components/{timeline,social-circle,warmth-meter}/*.tsx
|   +-- depends: backend data from Specs 049, 050, 052
|
+-- [9] BATCH JOBS (Section 5, pg_cron)
    +-- [EXISTS] 6 active pg_cron jobs -- no changes needed
    +-- [NEW] nikita-psyche-batch (daily 5AM) -- Opus 4.6 psyche generation
    +-- [NEW] nikita-life-gen (daily 4AM) -- next-day life events (or enhance existing pipeline)
```

---

## Section 2: Final Spec Decomposition

| Spec | Name | Scope | Tasks Est | Days | Risk | Wave |
|------|------|-------|-----------|------|------|------|
| 049 | Life Simulation Enhanced | Weekly routine, emotional-driven events, NPC consolidation (3->1), meta-instructions column (generation deferred), bidirectional mood | 20-25 | 4-5 | MEDIUM | A |
| 050 | Psyche Agent | New Opus 4.6 agent, PsycheState model, psyche_states table, daily batch, 3-tier trigger, pre-conv read, prompt L3 | 22-28 | 3-4 | MEDIUM | B |
| 051 | Conflict System CORE | Temperature gauge (0-100), Gottman ratio, repair tracking, Four Horsemen, conflict_details JSONB, temperature-based injection | 18-22 | 3-4 | MEDIUM | A |
| 052 | Multi-Phase Boss + Warmth | 2-phase MVP boss (OPENING->RESOLUTION), PARTIAL outcome, boss phase persistence, vulnerability exchanges, warmth scoring | 20-25 | 5-8 | HIGH | C |
| 053 | Portal: Nikita's Day | Timeline page, social circle viz, tips section, warmth meter display | 15-20 | 2-3 | LOW | D |
| 054 | Prompt Caching + Context Engineering | cache_control blocks, persona reconciliation, layer restructure, prompt stacking fix, compaction, token budget | 15-18 | 2-3 | LOW-MED | C |

**Total**: 110-138 tasks, 19-27 days

### Per-Spec Detail

#### SPEC 049: Life Simulation Enhanced

**Scope IN**: Weekly routine system, bidirectional mood-event flow, NPC consolidation (3 systems -> 1 canonical: `user_social_circles`), NPC character name mapping, `routine_config` JSONB column, `meta_instructions` JSONB column (schema only, generation deferred), emotional state + conflict temperature inputs to event generation

**Scope OUT**: Monthly meta-instruction generation job (deferred per M1), pre-seeding 8 NPCs per user (lazy init per M2), daily batch job for life events (use existing pipeline S3)

**Acceptance Criteria**:
1. Routine-aware events generated: Monday work-from-home events differ from Saturday leisure events
2. Mood state feeds into event generation (bidirectional): stressed Nikita generates stress-related events
3. NPC states updated when life events reference named characters
4. `user_social_circles` is the single authoritative NPC store with sentiment + last_event columns
5. Character name mapping is explicit and documented (Marco->Marcus, Sophie->Sarah, Maya->Mom/deprecated)
6. Existing life sim tests continue to pass
7. Timezone handling: Nikita lives in Berlin (CET), events use Berlin time
8. New params have defaults -- old callers still work

**Files to modify**: `life_simulation/models.py`, `life_simulation/event_generator.py`, `life_simulation/simulator.py`, `life_simulation/arcs.py`, `life_simulation/entity_manager.py`, `life_simulation/store.py`
**Files to create**: `nikita/config_data/life_simulation/routine.yaml`
**DB migrations**: (1) ALTER TABLE users ADD routine_config JSONB DEFAULT '{}', meta_instructions JSONB DEFAULT '{}'; (2) ALTER TABLE user_social_circles ADD last_event TIMESTAMPTZ, sentiment TEXT
**Dependencies**: none (first in chain)
**Key risks**: NPC 3-way reconciliation complexity; bidirectional mood feedback loops; character name mapping has no clean 1:1
**Critical decisions**: Character name mapping table; whether to deprecate `nikita_state.friends` immediately or mark as legacy

#### SPEC 050: Psyche Agent

**Scope IN**: PsycheState Pydantic model (8 fields), Opus 4.6 psyche agent (structured output), psyche_states table + repository, daily batch job (pg_cron), 3-tier trigger detector (rule-based), pre-conversation psyche read in message_handler, prompt L3 section in template, NikitaDeps extension

**Scope OUT**: Dual-process routing (trigger detector IS the router), conversation compaction (Spec 054), meta-instruction integration (Spec 049 provides column), quality monitoring dashboard (defer to post-100-states review)

**Acceptance Criteria**:
1. Daily psyche batch generates valid PsycheState with all 8 fields populated
2. Trigger detector routes correctly: 90% Tier 1 (cached read), 8% Tier 2 (Sonnet), 2% Tier 3 (Opus)
3. Psyche briefing (~150 tok) injected in system prompt Layer 3
4. Conversation agent behavior visibly influenced by psyche state (behavioral_guidance shapes responses)
5. Tier 3 latency handled gracefully (typing indicator, narrative-appropriate delay)
6. Failure graceful: psyche read failure -> L3 renders empty, conversation proceeds normally
7. Costs within $7/mo psyche budget (batch + triggers)
8. Circuit breaker: max 5 Tier 3 calls/user/day

**Files to modify**: `agents/text/deps.py`, `agents/text/agent.py`, `platforms/telegram/message_handler.py`, `pipeline/stages/prompt_builder.py`, `pipeline/models.py`, `pipeline/templates/system_prompt.j2`
**Files to create**: `nikita/agents/psyche/agent.py`, `nikita/agents/psyche/models.py`, `nikita/agents/psyche/deps.py`, `nikita/agents/psyche/batch.py`, `nikita/db/repositories/psyche_state_repository.py`, `nikita/db/models/psyche_state.py`, `nikita/api/routes/tasks/psyche.py`
**DB migrations**: CREATE TABLE psyche_states (+ index + RLS); pg_cron job `nikita-psyche-batch` at 5 AM
**Dependencies**: Spec 049 (psyche agent reads life events + NPC states for analysis context)
**Key risks**: Opus cost if trigger rate >10%; psyche prompt quality; Tier 3 latency (~3s) blocking UX
**Critical decisions**: Sonnet 4.5 vs Opus 4.6 for daily batch (devil's advocate H1 recommends Sonnet for batch, Opus only for Tier 3); `psyche_model` config parameter

#### SPEC 051: Conflict System CORE

**Scope IN**: ConflictTemperature model (0-100, 4 zones), temperature REPLACES existing conflict_state enum (not layers on top), Gottman ratio tracking (two-ratio: 5:1 conflict, 20:1 normal), repair attempt tracking connected to temperature, Four Horsemen detection in scoring analyzer, conflict_details JSONB on nikita_emotional_states, users.last_conflict_at column, temperature-based conflict injection probability

**Scope OUT**: Multi-phase boss (Spec 052), boss phase state (Spec 052), vulnerability exchanges (Spec 052), portal visualization (Spec 053)

**Acceptance Criteria**:
1. Temperature increases on negative interactions, score drops >3pt, neglect, boundary violations
2. Temperature decreases on positive interactions, successful repairs, time cooldown (0.5/hr)
3. Gottman ratio tracked: two-ratio system (5:1 during active conflict, 20:1 during normal)
4. Four Horsemen behaviors (criticism, contempt, defensiveness, stonewalling) identified by scoring analyzer
5. Conflict injection probability driven by temperature zones, not flat cooldown
6. Repair attempts reduce temperature (not just reset timer as current)
7. Existing conflict_state enum DEPRECATED in favor of temperature model
8. All existing conflict tests updated for new model

**Files to modify**: `conflicts/models.py`, `conflicts/detector.py`, `conflicts/generator.py`, `conflicts/escalation.py`, `conflicts/resolution.py`, `conflicts/breakup.py`, `scoring/analyzer.py`, `scoring/service.py`, `scoring/models.py`, `pipeline/stages/conflict.py`
**Files to create**: none (extends existing module)
**DB migrations**: ALTER TABLE nikita_emotional_states ADD conflict_details JSONB DEFAULT '{}'; ALTER TABLE users ADD last_conflict_at TIMESTAMPTZ
**Dependencies**: none (operates on existing infrastructure)
**Key risks**: Temperature zone calibration (too tight = constant conflict, too wide = no tension); Gottman ratio cold start for existing user; Four Horsemen LLM detection accuracy
**Critical decisions**: conflict_details stored on nikita_emotional_states (co-located with emotional data) vs users table; temperature zone boundaries; initialization values for existing user

#### SPEC 052: Multi-Phase Boss + Warmth

**Scope IN**: 2-phase MVP boss encounters (OPENING -> RESOLUTION), PARTIAL outcome type, BossPhaseState model, boss phase persistence in conflict_state.boss_phase, per-phase prompts (2 phases x 5 chapters = 10 variants), multi-turn judgment, vulnerability exchange counter, warmth meter scoring bonus (+2 trust with diminishing returns), feature flag `multi_phase_boss_enabled`

**Scope OUT**: 4-phase boss (ESCALATION + CRISIS_PEAK deferred to follow-up), portal warmth meter display (Spec 053), A/B testing infrastructure

**Acceptance Criteria**:
1. Boss encounters span 2 turns minimum (OPENING -> RESOLUTION)
2. Phase progression tracked correctly across messages via conflict_state.boss_phase
3. PARTIAL outcome supported: truce that doesn't advance chapter but doesn't count as fail
4. Vulnerability exchanges detected by scoring analyzer (mutual: Nikita shares + player responds with empathy)
5. Vulnerability scoring bonus: +2 trust first V-exchange/conv, +1 second, +0 third+ (diminishing returns)
6. Boss phase persisted between messages (survives server restart)
7. Old single-turn boss preserved behind `multi_phase_boss_enabled` feature flag
8. 10 phase-prompt variants written and tested (2 phases x 5 chapters)

**Files to modify**: `chapters/boss.py`, `chapters/judgment.py`, `chapters/prompts.py`, `platforms/telegram/message_handler.py`, `scoring/analyzer.py`, `scoring/calculator.py`
**Files to create**: `nikita/engine/chapters/phase_manager.py`
**DB migrations**: ALTER TABLE user_metrics ADD vulnerability_exchanges INT DEFAULT 0
**Dependencies**: Spec 051 (uses conflict_state.boss_phase from conflict_details JSONB)
**Key risks**: HIGHEST RISK SPEC -- fundamental boss redesign; 10 prompt variants to write; multi-turn state management; judgment quality with conversation context; feature flag fallback complexity
**Critical decisions**: 2-phase vs 4-phase MVP (devil's advocate H3 recommends 2-phase); how PARTIAL interacts with boss_attempts counter; vulnerability exchange detection prompt quality

#### SPEC 053: Portal: Nikita's Day

**Scope IN**: New /nikita-day page, timeline component (today's life events with time-of-day markers), social circle visualization (NPC relationship map from user_social_circles), tips section (psyche behavioral_guidance), warmth meter display (relationship_score gauge + vulnerability milestones)

**Scope OUT**: Backend API changes (reads existing data), mobile optimization, real-time updates

**Acceptance Criteria**:
1. Timeline shows today's life events with morning/afternoon/evening markers
2. Social circle renders NPC relationships with sentiment indicators
3. Tips section shows psyche agent's behavioral_guidance text
4. Warmth meter displays relationship_score as visual gauge
5. All components use shadcn/ui + Tailwind + glassmorphism dark theme
6. Graceful fallback when backend data not available (empty state components)
7. Responsive design for desktop and mobile
8. Page loads in <2s

**Files to modify**: none backend-side
**Files to create**: `portal/src/app/(player)/nikita-day/page.tsx`, `portal/src/components/timeline/*.tsx`, `portal/src/components/social-circle/*.tsx`, `portal/src/components/warmth-meter/*.tsx`
**DB migrations**: none
**Dependencies**: Spec 049 (life events data), Spec 050 (psyche tips), Spec 052 (warmth meter data)
**Key risks**: Low technical risk; main risk is data availability if backend specs delayed; design fidelity
**Critical decisions**: Separate page vs expand existing dashboard; API endpoints (new thin endpoints vs existing)

#### SPEC 054: Prompt Caching + Context Engineering

**Scope IN**: Persona.py reconciliation (slim to behavioral guide ~400 tok), prompt stacking fix (guard add_chapter_behavior), template section reorder for cache optimization, Anthropic cache_control breakpoints (3 BPs), S9 psychological depth split (static->L1, dynamic->L3), Haiku enrichment disabled on cached sections, conversation compaction at 15-turn threshold, per-layer token tracking in ready_prompts.context_snapshot, 1-hour TTL for voice sessions

**Scope OUT**: Dual-process model routing (implicit in Spec 050 trigger tiers), full legacy path removal (keep persona.py import for 1 release cycle)

**Acceptance Criteria**:
1. Cache hit rates >80% on static layers (L1+L2+L7) measured via Anthropic usage metrics
2. persona.py deprecated to behavioral guide only (~400 tok), no backstory/location/NPC content
3. add_chapter_behavior() returns "" when pipeline prompt exists (no double-injection)
4. S9 psychological depth split: static (attachment, wounds, triggers) -> L1; dynamic (vulnerability gates) -> L3
5. Conversation compacted at 15-turn threshold: summarize older turns, keep last 5 verbatim
6. Per-layer token counts tracked in ready_prompts.context_snapshot JSONB
7. Total system prompt within 6,150 tok (text) / 2,400 tok (voice) budget
8. Legacy fallback path (no pipeline prompt) still works for first conversation

**Files to modify**: `agents/text/agent.py`, `agents/text/persona.py`, `agents/text/history.py`, `pipeline/stages/prompt_builder.py`, `pipeline/templates/system_prompt.j2`
**Files to create**: none
**DB migrations**: none
**Dependencies**: Spec 050 (prompt L3 must exist for proper cache boundary placement)
**Key risks**: Cache miss sensitivity to exact character matching; persona deprecation breaking legacy path; compaction losing important context
**Critical decisions**: Whether to move L7 (Response Guidelines) above BP1 for caching (context-engineer recommends yes); Haiku enrichment: disable entirely or pin enriched output

---

## Section 3: Dependency Graph (ASCII DAG)

```
BUILD WAVE PLAN
===============

    WAVE A (days 1-5)               WAVE B (days 5-10)
    parallel start                  sequential

    +------------------+            +------------------+
    | Spec 049         |            | Spec 050         |
    | Life Sim Enhanced|---[049]-->| Psyche Agent     |
    | 20-25 tasks      |            | 22-28 tasks      |
    | risk: MEDIUM     |            | risk: MEDIUM     |
    +------------------+            +--------+---------+
                                             |
    +------------------+                     |
    | Spec 051         |                     |
    | Conflict CORE    |---[051]--+          |
    | 18-22 tasks      |          |          |
    | risk: MEDIUM     |          |          |
    +------------------+          |          |
                                  v          v
                         WAVE C (days 10-15)
                         parallel

                         +------------------+
                    +--->| Spec 052         |
                    |    | Boss + Warmth    |
                    |    | 20-25 tasks      |
                    |    | risk: HIGH       |
                    |    +--------+---------+
                    |             |
                    |    +------------------+
                    +--->| Spec 054         |
                         | Prompt Caching   |
                         | 15-18 tasks      |
                         | risk: LOW-MED    |
                         +--------+---------+
                                  |
                         WAVE D (days 15-19)

                         +------------------+
                         | Spec 053         |
                         | Portal           |
                         | 15-20 tasks      |
                         | risk: LOW        |
                         +------------------+


DEPENDENCY EDGES:
  049 --> 050  (psyche reads life events + NPC states)
  051 --> 052  (boss uses conflict_state.boss_phase)
  050 --> 054  (caching needs L3 psyche section)
  049 --> 053  (portal reads life events)
  050 --> 053  (portal reads psyche tips)
  052 --> 053  (portal reads warmth data)

CRITICAL PATH (longest chain):
  049 (5d) -> 050 (4d) -> 052 (8d) -> 053 (3d) = 20 days

PARALLEL OPPORTUNITIES:
  049 + 051 can run simultaneously (Wave A, no shared deps)
  052 + 054 can run simultaneously (Wave C, no shared deps)
  053 UI scaffolding can start in Wave A with mock data (per L5)
```

---

## Section 4: Gap Analysis Matrix

| Component | Current State | Target (Doc 24) | Gap Size | Effort | Spec |
|-----------|--------------|-----------------|----------|--------|------|
| **Psyche Agent** | Does not exist | Opus 4.6 daily + triggered hybrid | FULL | 3-4 days | 050 |
| **psyche_states table** | Does not exist | New table (JSONB, 1 row/user) | FULL | 0.5 day | 050 |
| **Trigger detector** | None | 3-tier rule-based routing | FULL | 1 day | 050 |
| **Temperature gauge** | No temperature field | 0-100 continuous, 4 zones | FULL | 2 days | 051 |
| **Gottman ratio** | No tracking | 5:1 conflict / 20:1 normal | FULL | 1.5 days | 051 |
| **Four Horsemen detection** | behaviors_identified[] exists but no Horsemen | Classify criticism/contempt/defensiveness/stonewalling | FULL | 1 day | 051 |
| **Weekly routine** | Day-of-week hint in LLM prompt only | Structured routine_config JSONB | FULL | 1.5 days | 049 |
| **routine_config column** | Does not exist | JSONB on users | FULL | 0.25 day | 049 |
| **meta_instructions column** | Does not exist | JSONB on users | FULL | 0.25 day | 049 |
| **Meta-instruction generation** | Does not exist | Monthly batch job | DEFERRED | -- | -- |
| **last_conflict_at column** | Does not exist | TIMESTAMPTZ on users | FULL | 0.1 day | 051 |
| **vulnerability_exchanges** | Does not exist | INT on user_metrics | FULL | 0.1 day | 052 |
| **Multi-phase boss** | Single-turn, binary PASS/FAIL | 2-phase, 3 outcomes | VERY LARGE | 5-8 days | 052 |
| **Boss phase persistence** | No boss state persisted | boss_phase in conflict_state JSONB | FULL | 0.5 day | 052 |
| **Boss prompt variants** | 5 prompts (1 per chapter) | 10 prompts (2 phases x 5 chapters) MVP | LARGE | 2-3 days | 052 |
| **NPC state tracking** | 3 overlapping systems, no dynamic state | 1 canonical (user_social_circles) + sentiment | MEDIUM | 2 days | 049 |
| **Emotional-driven events** | One-way: events -> mood | Bidirectional: mood <-> events | MEDIUM | 1.5 days | 049 |
| **Prompt L3 (psyche)** | Does not exist | New template section ~150 tok | MEDIUM | 0.5 day | 050 |
| **Prompt caching** | No Anthropic cache_control | 3 breakpoints, layer reorder | MEDIUM | 1.5 days | 054 |
| **Persona conflict** | Brooklyn vs Berlin, dual identity | Single canonical identity (Berlin) | MEDIUM | 1 day | 054 |
| **Prompt stacking** | ~7,400 tok unbudgeted | ~6,150 tok within budget | MEDIUM | 0.5 day | 054 |
| **S9 split** | Standalone 540 tok section | Static -> L1, dynamic -> L3 | SMALL | 0.5 day | 054 |
| **Conversation compaction** | No compaction (80 turns, 3K tok) | Compact at 15 turns | SMALL | 0.5 day | 054 |
| **Portal Nikita's Day** | Does not exist | New page with 4 components | FULL | 2-3 days | 053 |
| **Life events table** | nikita_life_events (11 cols) | Same concept, enhanced generation | NO GAP (schema) | 0 | -- |
| **Memory (pgVector)** | memory_facts with ivfflat, hash dedup | Same (no changes) | NO GAP | 0 | -- |
| **Score history** | score_history exists | Same (no changes) | NO GAP | 0 | -- |
| **Conversations** | 22-column table, pipeline processing | Same (no changes) | NO GAP | 0 | -- |
| **Engagement FSM** | 3 tables (state/history/metrics) | Same (no changes) | NO GAP | 0 | -- |
| **Daily summaries** | daily_summaries exists | Same (no changes) | NO GAP | 0 | -- |
| **pg_cron decay** | Hourly decay job | Same (no changes) | NO GAP | 0 | -- |
| **Conflict module** | 7 files, discrete event model | Same structure, enhanced models | PARTIAL | -- | 051 |
| **Emotional state** | nikita_emotional_states (4D + basic conflict) | Same + richer conflict model via JSONB | PARTIAL | -- | 051 |

---

## Section 5: Critical Decisions Register

| # | Decision | Options | Recommendation | Evidence | Spec |
|---|----------|---------|---------------|----------|------|
| D1 | **Persona conflict resolution** | (A) Slim persona.py to behavioral guide; (B) Align persona.py to Berlin; (C) Remove persona.py entirely when pipeline prompt exists | **Option A**: Slim persona.py to ~400 tok behavioral guide (communication style + values only). Template = sole identity source. Keep persona.py import for legacy fallback. | Context-engineer 7.1: "Model may reference Brooklyn OR Berlin unpredictably." Devil's advocate C1: "100% probability, currently happening." | 054 |
| D2 | **Prompt stacking fix** | (A) Guard add_chapter_behavior() to return "" when pipeline prompt exists; (B) Remove @agent.instructions decorators entirely for pipeline path; (C) Make generated_prompt the full system prompt, bypass NIKITA_PERSONA | **Option A**: Minimal change -- add `if ctx.deps.generated_prompt: return ""` to add_chapter_behavior(). Agent.py:80 already has the pattern at 103. | Context-engineer 7.3: "Chapter behavior appears TWICE." Pipeline-analyst confirms double-injection. | 054 |
| D3 | **NPC character name canonicalization** | (A) Use doc 24 names (Emma/Marcus/Sarah); (B) Keep existing arc names (Marco/Lena/Viktor); (C) Map: Marco->Marcus, Sophie->Sarah, keep Lena/Viktor/Yuki, add Mom/Ex | **Option C**: Explicit mapping. Keep shared names (Lena, Viktor, Yuki). Rename divergent ones. Add Mom and Ex as new entries. Maya and Sophie are deprecated or mapped. | Engine-analyst 2.8: "DIFFERENT friend sets." Devil's advocate C3: "Mapping table is missing." Backend-DB: 3 systems with zero overlap reconciliation. | 049 |
| D4 | **Sonnet vs Opus for psyche batch** | (A) Opus 4.6 for all psyche (per doc 24); (B) Sonnet 4.5 for batch, Opus only Tier 3; (C) Configurable via `psyche_model` setting | **Option C (default B)**: Start with Sonnet 4.5 for daily batch ($0.90/mo vs $2.25/mo). Add `psyche_model` config. Reserve Opus for Tier 3 only. Upgrade if Sonnet quality is insufficient. | Devil's advocate H1: "Psyche analysis is fundamentally summarization + classification, not deep reasoning." Fact-check: $2.25/mo Opus vs $0.90/mo Sonnet. | 050 |
| D5 | **2-phase vs 4-phase boss MVP** | (A) Full 4-phase (OPENING/ESCALATION/CRISIS_PEAK/RESOLUTION); (B) 2-phase MVP (OPENING/RESOLUTION); (C) 3-phase (OPENING/ESCALATION/RESOLUTION) | **Option B**: 2-phase MVP. 10 prompt variants (not 20). Add ESCALATION + CRISIS_PEAK in follow-up spec. Reduces highest-risk spec's scope by ~50%. | Devil's advocate H3: "VERY LARGE gap. 4-5 days underestimated for 20 variants." Engine-analyst: "fundamental redesign." Integration reviewer: "HIGHEST RISK SPEC." | 052 |
| D6 | **Meta-instructions: include or defer** | (A) Full implementation (monthly generation job + event gen integration); (B) Column only, generation deferred; (C) Skip entirely | **Option B**: Add JSONB column (cheap). Don't build monthly generation job. Chapters + arcs + psyche already provide 3 timescales of behavioral shaping. Build generation when the other 3 systems are proven. | Devil's advocate M1: "Third behavioral shaping system on top of chapters + arcs. What specific behavior does this enable?" | 049 |
| D7 | **conflict_details storage location** | (A) New JSONB column on nikita_emotional_states (co-located with emotional data); (B) New JSONB column on users table (per doc 24); (C) New separate table | **Option A**: Co-locate with emotional state data. nikita_emotional_states already has conflict_state enum + trigger fields. Adding conflict_details JSONB keeps all emotional + conflict state in one row per user. | Backend-DB 5.5: "Best approach: add conflict_details JSONB to nikita_emotional_states." Integration reviewer: "Co-locating avoids data scatter." | 051 |
| D8 | **S9 Psychological Depth: fold into L3 or keep separate** | (A) Fold static parts into L1, dynamic into L3 (eliminate S9); (B) Keep as L4f (part of dynamic context); (C) Keep as standalone section | **Option A**: Static psychology (attachment style, wounds, triggers, ~350 tok) -> L1 Identity. Dynamic vulnerability gates (~100 tok) -> L3 Psyche State. Clean cache separation. Eliminates orphaned section. | Context-engineer 7.2: "Option C (split) recommended. Static IS identity. Dynamic IS psyche." Total: L1 grows to ~2,350 tok (still cacheable), L3 grows to ~250 tok. | 054 |
| D9 | **Gottman ratio calibration** | (A) Single 5:1 ratio always; (B) Two ratios: 5:1 conflict, 20:1 normal; (C) Sliding window only, no per-session | **Option B**: Two-ratio system matches actual Gottman research. 5:1 during active conflicts, 20:1 during normal play. Track per-session AND rolling 7-day window. | Devil's advocate H4: "5:1 designed for conflict periods. Non-conflict is 20:1." Researcher: "20:1 everyday interactions, 5:1 conflict." | 051 |
| D10 | **NPC initialization strategy** | (A) Pre-seed 8 NPCs per user on registration; (B) Lazy init -- only create when NPC first mentioned; (C) Seed 3 core NPCs, lazy-init others | **Option B**: Lazy initialization avoids YAGNI. Only track NPCs that appear in conversation or life events. Saves 15-25 JSONB operations/day for never-mentioned NPCs. | Devil's advocate M2: "Tracking 5-8 NPCs per user when player may never interact with any of them." | 049 |
| D11 | **Temperature replaces or layers on conflict_state enum** | (A) Temperature replaces existing enum (deprecate); (B) Temperature layers on top (3rd system) | **Option A**: Temperature REPLACES. Map existing enum values: none=0, passive_aggressive=40, cold=50, vulnerable=30, explosive=85. Deprecate old fields. | Devil's advocate H2: "Three conflict tracking systems is too many." Integration reviewer confirms. | 051 |
| D12 | **Haiku enrichment vs cache stability** | (A) Disable Haiku entirely; (B) Disable on cached sections only; (C) Run once, pin output | **Option B**: Disable Haiku enrichment on L1/L2/L5/L6/L7 (cached). Apply only to L4 (dynamic, not cached). Preserves cache stability while retaining enrichment value. | Context-engineer 7.4: "Non-determinism breaks cache." Devil's advocate M4 confirms. | 054 |

---

## Section 6: Risk Register (Top 10)

| Rank | Risk | Prob | Impact | Mitigation | Spec |
|------|------|------|--------|------------|------|
| 1 | **Persona conflict corrupts identity** -- player experiences Brooklyn AND Berlin Nikita in same conversation | 100% | HIGH | Spec 054 prerequisite: slim persona.py to behavioral guide, template = sole identity. Consider hotfixing before specs start. | 054 |
| 2 | **Multi-phase boss content bottleneck** -- 10 prompt variants (2-phase MVP) require writing, testing, tuning for quality and balance | 80% | HIGH | Start with 2-phase MVP (10 variants, not 20). Add phases incrementally. Content writing is the bottleneck, not code. | 052 |
| 3 | **Temperature zones miscalibrated** -- too aggressive = constant conflict, too mild = no tension | 70% | MEDIUM | Tunable constants (not hardcoded). Feature flag to disable. Playtest cycle after initial implementation. Initialize at 0 for existing user. | 051 |
| 4 | **NPC 3-way reconciliation fails** -- character names don't map cleanly, data conflicts across systems | 60% | MEDIUM | Explicit mapping table in spec. Lazy initialization. Keep nikita_entities for static data. Map only characters that overlap (Lena, Viktor, Yuki). | 049 |
| 5 | **Psyche agent output quality is poor** -- behavioral_guidance is nonsensical or miscalibrated | 40% | HIGH | Start with Sonnet (cheaper iteration). Human review first 100 states. Quality heuristics (field presence, guidance length). Sonnet fallback from Opus. | 050 |
| 6 | **Gottman ratio too punitive in short sessions** -- 1-2 bad messages cross threshold, triggering premature conflict | 50% | MEDIUM | Two-ratio system (5:1 conflict, 20:1 normal). Per-session AND rolling 7-day window. Diminishing returns on negative scoring. | 051 |
| 7 | **Prompt caching breaks on edge cases** -- Haiku enrichment non-determinism, platform switches, tool definition changes | 40% | MEDIUM | Disable Haiku on cached sections. Separate cache per platform. Pin tool schemas. Test cache stability before deployment. | 054 |
| 8 | **Opus cost escalation** -- trigger detector mis-calibrates, >10% messages routed to Tier 3 | 20% | HIGH | Circuit breaker: max 5 Tier 3 calls/user/day. Start with Sonnet for batch. Config parameter to switch models. Cost monitoring. | 050 |
| 9 | **Voice pipeline not integrated** -- new psyche/conflict state doesn't reach voice prompt assembly | 60% | LOW | Add explicit voice integration tasks to Specs 050 and 051. Voice uses same ready_prompts table but may need separate psyche injection. | 050, 051 |
| 10 | **Existing E2E tests break** -- Spec 048 tests assume current boss/conflict behavior | 80% | LOW | Re-run E2E after all specs complete. Update test expectations. Feature flags preserve old behavior for test isolation. | Post-052 |

---

## Section 7: Shared Infrastructure

### Pre-Spec Fixes (before feature spec work begins)

**1. Persona Conflict Hotfix** (C1, risk rank #1)
- File: `nikita/agents/text/persona.py`
- Action: Slim NIKITA_PERSONA to ~400 tok behavioral guide (communication style, values, negative examples). Remove ALL backstory, location, NPC, career details.
- File: `nikita/agents/text/agent.py:80`
- Action: Guard `add_chapter_behavior()` to return "" when `ctx.deps.generated_prompt` is truthy
- This can be done as a pre-spec hotfix. Every subsequent spec depends on a non-conflicting identity.

**2. NPC Character Mapping** (C3)
- Must be decided before Spec 049 writing begins
- Proposed mapping:

| Existing Name | System | Doc 24 Name | Decision |
|---------------|--------|-------------|----------|
| Maya | nikita_state.friends | -- | DEPRECATE (not in doc 24 or arcs) |
| Sophie | nikita_state.friends | Sarah? | RENAME to Sarah or DEPRECATE |
| Lena | nikita_state.friends + arcs | Lena | KEEP (shared across all systems) |
| Marco | arcs (career arc) | Marcus | RENAME to Marcus in user_social_circles |
| Viktor | arcs (social arc) | Viktor | KEEP |
| Yuki | arcs (social arc) | Yuki | KEEP |
| Alexei | arcs (personal arc) | -- | KEEP in arcs, add to user_social_circles if mentioned |
| Katya | arcs (personal arc) | -- | KEEP in arcs, add to user_social_circles if mentioned |
| Dr. Miriam | arcs (therapy) | -- | KEEP in arcs, NOT an NPC (professional relationship) |
| -- | -- | Emma | ADD to user_social_circles (doc 24 Module 2) |
| -- | -- | Mom | ADD to user_social_circles |
| -- | -- | Ex (Max/Andrei) | ADD to user_social_circles (use template backstory names) |

### Common Types/Models (used by multiple specs)

| Model | File | Fields | Used By |
|-------|------|--------|---------|
| `ConflictState` (JSONB schema) | conflicts/models.py | temperature, type, started_at, repair_attempts, positive_count, negative_count, gottman_ratio, boss_phase | 051 (writes), 052 (reads boss_phase), prompt_builder (reads) |
| `PsycheState` | agents/psyche/models.py | attachment_activation, defense_mode, behavioral_guidance, internal_monologue, vulnerability_level, emotional_tone, topics_to_encourage, topics_to_avoid | 050 (writes), prompt_builder (reads), 053 (reads guidance) |
| `WeeklyRoutine` / `DayRoutine` | life_simulation/models.py | day_of_week, activities, availability, energy_pattern | 049 (writes/reads), 050 (reads for psyche context) |
| `NPCState` update fields | user_social_circles table | last_event TIMESTAMPTZ, sentiment TEXT | 049 (writes), 050 (reads), 053 (reads) |

### Shared DB Migration Patterns

All migrations are additive (nullable columns with defaults, new tables). Zero-downtime deployment:
- Column additions: `ALTER TABLE ... ADD COLUMN ... DEFAULT ...`
- New tables: `CREATE TABLE ... + index + RLS`
- pg_cron jobs: `SELECT cron.schedule(...)`
- No existing data migration required (all new fields have safe defaults)
- Each spec owns its own migrations -- no shared infra spec needed

### Feature Flags Plan

| Flag | Spec | Default | Fallback Behavior |
|------|------|---------|-------------------|
| `life_sim_enhanced` | 049 | OFF | Current event generation (no routine, one-way mood) |
| `psyche_agent_enabled` | 050 | OFF | No psyche read, L3 renders empty, no trigger detection |
| `conflict_temperature` | 051 | OFF | Current discrete cooldown model (4h flat) |
| `multi_phase_boss_enabled` | 052 | OFF | Current single-turn PASS/FAIL boss |
| `prompt_caching_enabled` | 054 | OFF | Current prompt assembly (no cache_control blocks) |

Rollout order: 049 -> 051 -> 050 -> 054 -> 052 (boss last, highest risk)

---

## Section 8: Per-Spec Context Packages

### SPEC 049: Life Simulation Enhanced

**Scope**: Weekly routine, emotional-driven events, NPC consolidation, meta-instructions column, bidirectional mood
**Files to modify**: `life_simulation/models.py` (add WeeklyRoutine, DayRoutine, NPCState models), `life_simulation/event_generator.py:82-234` (add mood_state + conflict_temperature params, inject routine context), `life_simulation/simulator.py:98-159` (compute mood first, pass to EventGenerator, update NPC states), `life_simulation/arcs.py:430-492` (update NPC states on arc create/advance), `life_simulation/entity_manager.py:263-310` (enhance get_entity_context with dynamic state), `life_simulation/store.py` (NPC state persistence)
**Files to create**: `nikita/config_data/life_simulation/routine.yaml` (default weekly schedule per doc 24 Section 6)
**DB migrations**: (1) ALTER TABLE users ADD routine_config JSONB DEFAULT '{}', meta_instructions JSONB DEFAULT '{}'; (2) ALTER TABLE user_social_circles ADD last_event TIMESTAMPTZ, sentiment TEXT
**Dependencies**: none (Wave A)
**Research context**: Researcher topic 6 (Gottman/attachment psychology) informs NPC personality design. Researcher topic 3 (dual-process) not applicable to this spec. pg_cron topic 5 confirms existing batch infrastructure is sufficient.
**Library patterns**: Pydantic AI not directly used (life sim uses standalone LLM calls via event_generator.py:82). JSONB partial updates for NPC state: `jsonb_set(data, '{key}', '"value"')`.
**Current code state**: EventGenerator generates 3-5 events/day via LLM (Sonnet 4.5). MoodCalculator computes mood FROM events (one-way). NarrativeArcSystem has 10 templates with named characters. EntityManager seeds from entities.yaml. nikita_state.friends has 3 hardcoded NPCs (Maya/Sophie/Lena). user_social_circles has 14 columns (Spec 035) with rich NPC data but no dynamic state tracking.
**Challenges**: (C3) NPC 3-way reconciliation -- must explicitly map character names. (M2) Don't pre-seed 8 NPCs -- use lazy init. (M7) Timezone: Nikita lives in Berlin, use CET for routine. (H4) Gottman-informed NPC interactions need careful calibration.
**Critical decisions**: D3 (NPC name mapping), D6 (meta-instructions deferred), D10 (lazy NPC init)
**Acceptance criteria**: See Section 2 above (8 themes)
**Estimated tasks**: 20-25
**Existing user migration**: Seed default routine_config from doc 24 Section 6 for existing user. Leave meta_instructions empty. Migrate nikita_state.friends data into user_social_circles entries (Lena maps directly, Maya/Sophie deprecated or mapped).

---

### SPEC 050: Psyche Agent

**Scope**: New agent (Opus/Sonnet), psyche_states table, batch job, trigger detector, pre-conv read, prompt L3
**Files to modify**: `agents/text/deps.py:20` (add psyche_state: dict | None = None), `agents/text/agent.py` (add @agent.instructions for psyche briefing), `platforms/telegram/message_handler.py:235` (add psyche read + trigger detect before agent call), `pipeline/stages/prompt_builder.py:102` (add PsycheStateRepository.get_current in _enrich_context), `pipeline/models.py:16` (add psyche_state field to PipelineContext), `pipeline/templates/system_prompt.j2` (add L3 section between S2/S3 and S4)
**Files to create**: `nikita/agents/psyche/agent.py` (Agent with structured PsycheState output), `nikita/agents/psyche/models.py` (PsycheState Pydantic model: 8 fields), `nikita/agents/psyche/deps.py` (PsycheDeps dataclass), `nikita/agents/psyche/batch.py` (batch orchestration for pg_cron), `nikita/db/repositories/psyche_state_repository.py` (upsert + get_current), `nikita/db/models/psyche_state.py` (SQLAlchemy model), `nikita/api/routes/tasks/psyche.py` (Cloud Run task endpoint)
**DB migrations**: CREATE TABLE psyche_states (id UUID PK, user_id UUID UNIQUE FK, state JSONB NOT NULL, generated_at TIMESTAMPTZ, model TEXT, token_count INT) + btree index + RLS (user SELECT own, service_role ALL); pg_cron job `nikita-psyche-batch` at `0 5 * * *`
**Dependencies**: Spec 049 (psyche agent reads life events + NPC states for analysis context)
**Research context**: Researcher topic 2 (Pydantic AI multi-agent): Agent delegation pattern, output_type=PsycheState for structured output. Topic 3 (dual-process): Psyche batch = System 2, cached read = System 1. Topic 7 (context engineering): sub-agent isolation -- psyche gets narrow context.
**Library patterns**: `Agent("anthropic:claude-opus-4-6", output_type=PsycheState)` for structured output (lib-reviewer Section 1). No @agent.instructions decorators (fixed system prompt). No tools (read-only analysis). UsageLimits to cap costs. Pydantic AI does NOT manage cache_control natively (lib-reviewer Section 2).
**Current code state**: Single agent at agents/text/agent.py:56 using Sonnet 4.5. NikitaDeps has memory, user, settings, generated_prompt, conversation_messages, conversation_id, session. generate_response() at agent.py:368 loads ready_prompt then runs agent. Message handler at message_handler.py:129 does auth -> profile -> boss -> agent -> scoring -> delivery.
**Challenges**: (H1) Opus may be overkill for batch -- start with Sonnet. (H6) JSONB read is 10-50ms, not <5ms. (L1) No quality monitoring for psyche output. Circuit breaker needed for Tier 3 cost control. Voice pipeline integration for psyche state.
**Critical decisions**: D4 (Sonnet vs Opus for batch -- recommend Sonnet default with config switch), D8 (S9 psychology split -- static to L1, dynamic to L3)
**Acceptance criteria**: See Section 2 above (8 themes)
**Estimated tasks**: 22-28
**Existing user migration**: Run first psyche batch immediately on deploy (don't wait for daily cron). Seed initial psyche state from current emotional_states (arousal/valence/dominance/intimacy) + score trajectory (48 score_history entries) + 14 memory_facts.

---

### SPEC 051: Conflict System CORE

**Scope**: Temperature gauge, Gottman ratio, repair tracking, Four Horsemen, conflict_details JSONB
**Files to modify**: `conflicts/models.py:115` (add ConflictTemperature, GottmanTracker, ConflictState models; DEPRECATE existing conflict_state enum mapping), `conflicts/detector.py:145-202` (update detect() to modify temperature accumulator), `conflicts/generator.py:90-164` (replace flat 4h cooldown with temperature zone checks), `conflicts/escalation.py:134-157` (extend acknowledge() to reduce temperature), `conflicts/resolution.py:247-286` (connect resolve() to temperature reduction + Gottman update), `conflicts/breakup.py` (update thresholds for temperature-based model), `scoring/analyzer.py:31-54` (add Four Horsemen detection to ANALYSIS_SYSTEM_PROMPT), `scoring/service.py:52-107` (add Gottman counter increment post-scoring), `scoring/models.py:75-77` (add horsemen tags to behaviors_identified), `pipeline/stages/conflict.py:22` (consume temperature model)
**Files to create**: none (extends existing module)
**DB migrations**: ALTER TABLE nikita_emotional_states ADD conflict_details JSONB DEFAULT '{}'; ALTER TABLE users ADD last_conflict_at TIMESTAMPTZ
**Dependencies**: none (operates on existing scoring/conflict infrastructure)
**Research context**: Researcher topic 6 (Gottman): 5:1 ratio during conflict, 20:1 everyday. Four Horsemen predict relationship failure. Repair attempts: humor, affection, validation. Emotional bank account = composite metrics.
**Library patterns**: No new library usage. Scoring analyzer uses existing Pydantic AI Haiku agent for analysis. JSONB partial updates via `jsonb_set()` for conflict_state.
**Current code state**: ConflictDetector (rule + LLM) at detector.py:145. ConflictGenerator (4h cooldown) at generator.py:90. EscalationManager (3-level time-based) at escalation.py:86. ResolutionManager (LLM quality eval) at resolution.py:150. BreakupManager at breakup.py with score-based thresholds. nikita_emotional_states has conflict_state enum (none/passive_aggressive/cold/vulnerable/explosive) + conflict_trigger + ignored_message_count. ActiveConflict in-memory model with severity/escalation_level/resolution_attempts.
**Challenges**: (H2) Temperature must REPLACE existing enum, not layer on top. (H4) 5:1 ratio is for conflict periods; need two-ratio system. (M3) Vulnerability bonus gaming exploit -- add diminishing returns. Temperature zone calibration needs playtesting.
**Critical decisions**: D7 (conflict_details on nikita_emotional_states, not users), D9 (two-ratio Gottman system), D11 (temperature replaces, not layers on)
**Acceptance criteria**: See Section 2 above (8 themes)
**Estimated tasks**: 18-22
**Existing user migration**: Initialize conflict_details JSONB from current conflict_state enum value: map none->temperature:0, passive_aggressive->temperature:40, cold->temperature:50, vulnerable->temperature:30, explosive->temperature:85. Initialize Gottman counters from score_history: count positive/negative deltas from 48 existing entries.

---

### SPEC 052: Multi-Phase Boss + Warmth

**Scope**: 2-phase boss MVP, PARTIAL outcome, boss phase persistence, vulnerability exchanges, warmth scoring
**Files to modify**: `chapters/boss.py:20-113` (add BossPhaseState, phase tracking, advance_phase()), `chapters/judgment.py:19-63` (add PARTIAL to BossResult, modify judge_boss_outcome for multi-turn), `chapters/prompts.py:10-147` (expand BossPrompt to per-phase variants, 10 total), `platforms/telegram/message_handler.py:179` (modify _handle_boss_response for multi-turn loop), `scoring/analyzer.py` (detect vulnerability exchanges -- mutual sharing + empathetic response), `scoring/calculator.py` (apply +2 trust bonus with diminishing returns)
**Files to create**: `nikita/engine/chapters/phase_manager.py` (multi-phase boss orchestration, phase advancement logic)
**DB migrations**: ALTER TABLE user_metrics ADD vulnerability_exchanges INT DEFAULT 0 (boss_phase stored in conflict_state JSONB from Spec 051)
**Dependencies**: Spec 051 (uses conflict_state.boss_phase for phase persistence)
**Research context**: Researcher topic 6 (attachment): Boss encounters = Four Horsemen moments requiring player skill. Repair attempts = player's chance to recover. Ch1-5 map to attachment dynamics (abandonment, intensity, trust, vulnerability, independence).
**Library patterns**: Boss judgment uses Pydantic AI Agent with Sonnet 4.5 (temperature=0). Multi-turn judgment needs conversation history passed to agent, not single message.
**Current code state**: BossStateMachine at boss.py:20 is stateless (pure functions). initiate_boss() returns 1 prompt. judge_boss_outcome() evaluates 1 user message. BossResult enum has PASS/FAIL only. BossPrompt TypedDict has challenge_context + success_criteria + in_character_opening. 5 prompts total (1 per chapter). No phase tracking, no state persistence between messages.
**Challenges**: (H3) HIGHEST RISK -- fundamental redesign. 10 prompt variants are content bottleneck. Multi-turn state management across messages. Judgment quality with conversation context. Feature flag complexity. Estimated 5-8 days (not 3-4).
**Critical decisions**: D5 (2-phase MVP, not 4-phase), how PARTIAL interacts with boss_attempts counter (recommendation: PARTIAL does NOT increment boss_attempts but also does NOT advance chapter)
**Acceptance criteria**: See Section 2 above (8 themes)
**Estimated tasks**: 20-25
**Existing user migration**: boss_attempts=0, chapter=1 for existing user. No boss in progress. Multi-phase boss starts fresh on next boss trigger. Feature flag OFF by default.

---

### SPEC 053: Portal: Nikita's Day

**Scope**: New portal page, timeline, social circle, tips, warmth meter
**Files to modify**: none backend-side (reads existing API data via Supabase client)
**Files to create**: `portal/src/app/(player)/nikita-day/page.tsx` (main page), `portal/src/components/timeline/timeline.tsx` (event timeline), `portal/src/components/timeline/timeline-event.tsx` (individual event card), `portal/src/components/social-circle/social-circle.tsx` (NPC relationship map), `portal/src/components/social-circle/npc-card.tsx` (individual NPC), `portal/src/components/warmth-meter/warmth-meter.tsx` (relationship score gauge), `portal/src/components/tips/tips-panel.tsx` (psyche guidance display)
**DB migrations**: none
**Dependencies**: Spec 049 (life_events data in nikita_life_events table), Spec 050 (psyche_states.behavioral_guidance for tips), Spec 052 (user_metrics.vulnerability_exchanges for warmth milestones)
**Research context**: Not directly applicable. Portal is pure frontend. Uses existing Portal architecture (Spec 044): Next.js 16.1.6, React 19, shadcn/ui, TanStack Query v5, Supabase SSR, glassmorphism dark theme, oklch tokens, rose accents.
**Library patterns**: shadcn/ui components (Card, Avatar, Badge, Progress, Tooltip). TanStack Query for data fetching. Supabase SSR client for auth + data access. Recharts potentially for warmth meter gauge.
**Current code state**: Portal has 6 player routes (/dashboard, /engagement, /vices, /conversations, /diary, /settings) and 7 admin routes. Dark-only glassmorphism design with rose(player)/cyan(admin) accents. Build: `source ~/.nvm/nvm.sh && nvm use 22 && cd portal && npm run build`.
**Challenges**: (L5) Can start UI scaffold with mock data in Wave A (parallel with 049/051), wire to real APIs in Wave D. Data availability if backend specs delayed. Design fidelity with existing glassmorphism theme.
**Critical decisions**: Separate /nikita-day page (recommended) vs expanding existing /dashboard. Whether to add new API endpoints or read directly from Supabase tables via client.
**Acceptance criteria**: See Section 2 above (8 themes)
**Estimated tasks**: 15-20
**Existing user migration**: Page will show empty states gracefully until backend data is populated by Specs 049/050/052.

---

### SPEC 054: Prompt Caching + Context Engineering

**Scope**: Persona reconciliation, prompt stacking fix, template reorder, cache_control blocks, S9 split, Haiku enrichment, compaction, token tracking
**Files to modify**: `agents/text/agent.py` (guard add_chapter_behavior, add cache_control construction in generate_response), `agents/text/persona.py` (slim to ~400 tok behavioral guide), `agents/text/history.py` or new (conversation compaction at 15 turns), `pipeline/stages/prompt_builder.py` (reorder sections, disable Haiku on cached, add per-layer tracking, adjust truncation order), `pipeline/templates/system_prompt.j2` (reorder: L1+L2+L7 -> BP1 -> L3+L5+L6 -> BP2 -> L4; split S9; add L3 placeholder if not from Spec 050)
**Files to create**: none
**DB migrations**: none (per-layer counts stored in existing ready_prompts.context_snapshot JSONB)
**Dependencies**: Spec 050 (prompt L3 must exist for proper cache boundary placement)
**Research context**: Researcher topic 1 (prompt caching): max 4 breakpoints, 90% discount on reads, 5-min TTL, exact-match. Topic 7 (context engineering): 32K+ degrades accuracy, smaller high-signal > large noisy, primacy/recency bias, progressive disclosure.
**Library patterns**: Pydantic AI does NOT manage cache_control natively (lib-reviewer). Must implement at HTTP/AnthropicModel layer. `cache_control: {"type": "ephemeral"}` on content blocks. Usage metrics: cache_creation_input_tokens, cache_read_input_tokens. tiktoken cl100k_base for counting (existing token_counter.py:173).
**Current code state**: NIKITA_PERSONA (~1600 tok) injected via Agent(instructions=...). Chapter behavior injected via @agent.instructions (always, even when pipeline prompt exists). Pipeline prompt (~5500 tok) injected via @agent.instructions personalized_context. Total: ~7400 tok (exceeds pipeline's 6500 budget awareness). Truncation order: Vice -> Chapter -> Psychology. Haiku enrichment adds non-determinism. system_prompt.j2 has 11 sections in identity->relationship order (not cache-optimized).
**Challenges**: (C1) Persona conflict is 100% probability, currently happening in production. (C2) Prompt stacking adds ~1900 unbudgeted tokens. (M4) Haiku enrichment vs cache stability unresolved. (M6) S9 is 540 tok, not 400 as estimated. Cache miss sensitivity to exact character matching.
**Critical decisions**: D1 (persona slim to behavioral guide), D2 (guard add_chapter_behavior), D8 (S9 split), D12 (Haiku enrichment disabled on cached sections)
**Acceptance criteria**: See Section 2 above (8 themes)
**Estimated tasks**: 15-18
**Existing user migration**: Prompt structure changes immediately on deploy. ready_prompts table entries rebuilt on next pipeline run. No data migration needed. Legacy fallback (no pipeline prompt) continues to work with slimmed persona.py.

---

## Appendix: Evidence Log

| Query | Source | Agent | Key Finding |
|-------|--------|-------|-------------|
| Anthropic prompt caching | External research | researcher | Max 4 breakpoints, 90% discount, 5-min TTL, exact-match required |
| Pydantic AI multi-agent | External research + lib docs | researcher, lib-reviewer | Agent delegation pattern, output_type for structured output, no native cache_control |
| Dual-process AI | External research | researcher | System 1/2 maps to trigger tiers, database-mediated coordination is sound |
| ElevenLabs Conv AI 2.0 | External research | researcher | Server Tools pattern, Custom LLM via MCP, $0.10/min voice cost |
| pg_cron + Supabase | External research + lib docs | researcher, lib-reviewer | 32 concurrent jobs max, pg_net for HTTP, free tier availability unconfirmed |
| Gottman psychology | External research | researcher | 5:1 conflict ratio, 20:1 everyday, Four Horsemen, repair attempts |
| Context engineering | External research | researcher | 32K+ degrades accuracy, 4-tier hierarchy, progressive disclosure |
| Supabase schema | MCP queries | backend-db-analyst | 35 tables, 84 RLS, 110+ indexes, 6 pg_cron jobs, 3 NPC overlap systems |
| Cloud Run config | gcloud CLI | backend-db-analyst | 512Mi/1CPU, 14 env vars (2 legacy Neo4j), scale-to-zero |
| Pipeline architecture | Code analysis | pipeline-analyst | 9 stages, 40+ PipelineContext fields, best psyche point = pre-conversation |
| Prompt building | Code analysis | pipeline-analyst | 11-section template, 731 lines, ~5500 tok text, double-injection problem |
| Agent architecture | Code analysis | pipeline-analyst | Single Sonnet 4.5 agent, 2 tools, NikitaDeps, ready_prompts loading |
| Scoring engine | Code analysis | engine-analyst | 4 metrics, 6-state FSM, Haiku analyzer, MetricDeltas -10..+10 |
| Conflict system | Code analysis | engine-analyst | 7 files, discrete model, 3-level escalation, 4h cooldown, binary boss |
| Life simulation | Code analysis | engine-analyst | 11 files, 10 arc templates, 7 named characters, one-way mood flow |
| Persona conflict | Template + code analysis | context-engineer | Brooklyn (persona.py) vs Berlin (template), dual identity in production |
| Prompt stacking | Agent code analysis | context-engineer | ~7400 tok actual vs 6500 budget, ~1900 unbudgeted from @instructions |
| Cache strategy | Template analysis | context-engineer | 3 breakpoints, ~4150 tok cacheable (57%), ~51% cost reduction |
| S9 orphan | Template mapping | context-engineer | 540 tok, not mapped in doc 24, recommend split to L1 + L3 |
| Spec decomposition | All Wave 1 outputs | tech-integrator | 6 specs, 110-138 tasks, 19-27 days, 4 build waves |
| Dependency DAG | Cross-spec analysis | tech-integrator | Critical path: 049->050->052->053 = 20 days |
| Integration points | Cross-spec analysis | tech-integrator | 11 spec-to-spec interfaces documented with contracts |
| Cost verification | External pricing data | fact-checker | $30-37 LLM-only achievable; voice adds $90/mo; Supabase free tier works for 1 user |
| JSONB latency | Benchmarks | fact-checker | 10-50ms realistic (not <5ms); architecture still sound |
| pg_cron free tier | Community + docs | fact-checker | Working in current project but not officially confirmed on free tier |
| Over-engineering | Challenge analysis | devils-advocate | Defer meta-instruction generation, 2-phase boss MVP, lazy NPC init |
| Timeline estimate | Historical throughput | devils-advocate | 19-27 days adjusted; boss prompts are content bottleneck |
| Missing pieces | Gap analysis | devils-advocate | 12 items identified; existing user migration plan most critical |

---

*Generated by tot-synthesizer agent, 2026-02-17*
*Framework: Tree-of-Thought Synthesis for Gate 4.5 Spec Preparation*
*Input: 9 agent outputs (3,758 lines) + doc 24 (862 lines) = 4,620 lines analyzed*
*Output: ~800 lines, 8 sections, 6 per-spec context packages*
