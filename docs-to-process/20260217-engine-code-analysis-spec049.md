# Engine Code Analysis — Gate 4.5

Date: 2026-02-17
Analyst: engine-analyst agent
Sources: engine/, conflicts/, life_simulation/, doc 24

---

## 1. Current Architecture Overview

### Module Map

```
ENGINE_ROOT
├─ [→] engine/constants.py:1-236
│  ├─ CHAPTER_NAMES {1..5}
│  ├─ BOSS_THRESHOLDS {55..75}
│  ├─ DECAY_RATES {0.8..0.2}
│  ├─ GRACE_PERIODS {8h..72h}
│  ├─ METRIC_WEIGHTS {intimacy:0.30, passion:0.25, trust:0.25, secureness:0.20}
│  ├─ BOSS_ENCOUNTERS {1..5} [name, trigger, challenge]
│  ├─ CHAPTER_BEHAVIORS [lazy-loaded from prompts/chapters/]
│  └─ [DEPRECATED] → migrating to ConfigLoader (nikita.config.loader)
│
├─ [→] engine/scoring/
│  ├─ models.py:1-169
│  │  ├─ MetricDeltas [intimacy, passion, trust, secureness; -10..+10 each]
│  │  ├─ ResponseAnalysis [deltas, explanation, behaviors_identified, confidence]
│  │  ├─ ConversationContext [chapter, score, recent_msgs, engagement_state]
│  │  └─ ScoreChangeEvent [event_type, chapter, score_before/after, threshold]
│  ├─ analyzer.py:1-302 [LLM-based, Haiku model]
│  │  ├─ ScoreAnalyzer.analyze() → ResponseAnalysis
│  │  ├─ ScoreAnalyzer.analyze_batch() → ResponseAnalysis (voice)
│  │  └─ _build_analysis_prompt() [chapter-aware, recent history]
│  ├─ calculator.py:1-259
│  │  ├─ CALIBRATION_MULTIPLIERS [per EngagementState: 0.2..1.0]
│  │  ├─ ScoreCalculator.apply_multiplier() [positive only]
│  │  ├─ ScoreCalculator.calculate_composite() [weighted sum, 0-100]
│  │  ├─ ScoreCalculator.update_metrics() [clamp 0-100]
│  │  ├─ ScoreCalculator.calculate() → ScoreResult [full pipeline]
│  │  └─ _detect_events() [boss_threshold, critical_low(20), game_over(0)]
│  └─ service.py:1-241
│     ├─ ScoringService.score_interaction() [analyze → calculate → log]
│     ├─ ScoringService.score_batch() [voice transcripts]
│     └─ ScoringService._log_history() [score_history repo]
│
├─ [→] engine/engagement/state_machine.py:1-330
│  ├─ EngagementStateMachine [6-state FSM]
│  │  ├─ States: CALIBRATING, IN_ZONE, DRIFTING, CLINGY, DISTANT, OUT_OF_ZONE
│  │  ├─ Transition rules: score thresholds + consecutive counters
│  │  ├─ update() → StateTransition | None
│  │  └─ on_chapter_change() → reset to CALIBRATING
│  └─ THRESHOLDS dict [in_zone:0.8, drifting:0.6, low:0.5, recovery:0.7]
│
├─ [→] engine/chapters/
│  ├─ boss.py:1-259
│  │  ├─ BossStateMachine.should_trigger_boss() [pure: score >= threshold]
│  │  ├─ BossStateMachine.initiate_boss() → prompt dict
│  │  ├─ BossStateMachine.process_pass() → advance chapter
│  │  └─ BossStateMachine.process_fail() → increment attempts, game_over at 3
│  ├─ judgment.py:1-161
│  │  ├─ BossJudgment.judge_boss_outcome() → JudgmentResult(PASS|FAIL, reasoning)
│  │  └─ Uses Sonnet with temperature=0 for consistency
│  └─ prompts.py:1-147
│     ├─ BossPrompt TypedDict [challenge_context, success_criteria, in_character_opening]
│     └─ BOSS_PROMPTS {1..5} [detailed per-chapter boss scenarios]
│
├─ [→] conflicts/
│  ├─ models.py:1-249
│  │  ├─ TriggerType: DISMISSIVE, NEGLECT, JEALOUSY, BOUNDARY, TRUST
│  │  ├─ ConflictType: JEALOUSY, ATTENTION, BOUNDARY, TRUST
│  │  ├─ EscalationLevel: SUBTLE(1), DIRECT(2), CRISIS(3)
│  │  ├─ ResolutionType: FULL, PARTIAL, FAILED, NATURAL
│  │  ├─ ConflictTrigger [trigger_id, type, severity 0-1, context, messages]
│  │  ├─ ActiveConflict [type, severity, escalation_level, resolution_attempts]
│  │  ├─ ConflictConfig [escalation timings, natural resolution probs, breakup thresholds]
│  │  └─ ConflictSummary [total, resolved, unresolved crises, resolution_rate]
│  ├─ detector.py:1-482
│  │  ├─ TriggerDetector.detect() → DetectionResult
│  │  ├─ Rule-based: short_msg, time_gap, keywords (jealousy/boundary)
│  │  ├─ LLM-based: nuanced detection via Haiku agent
│  │  └─ CHAPTER_SENSITIVITY multipliers {1:1.5, 2:1.3, 3:1.0, 4:0.9, 5:0.8}
│  ├─ generator.py:1-351
│  │  ├─ ConflictGenerator.generate() → GenerationResult
│  │  ├─ Cooldown: 4 hours between conflicts
│  │  ├─ Severity calc: base × relationship_modifier × conflict_count × chapter
│  │  └─ Type selection: priority scoring + recency penalty
│  ├─ escalation.py:1-304
│  │  ├─ EscalationManager.check_escalation() → EscalationResult
│  │  ├─ Timeline: SUBTLE→DIRECT (2-6h), DIRECT→CRISIS (12-24h)
│  │  ├─ Natural resolution: 30% L1, 10% L2, 0% L3
│  │  └─ Acknowledge: resets timer, increments resolution attempts
│  ├─ resolution.py:1-407
│  │  ├─ ResolutionManager.evaluate() → ResolutionEvaluation
│  │  ├─ Quality: EXCELLENT, GOOD, ADEQUATE, POOR, HARMFUL
│  │  ├─ Score changes: +10 (excellent) to -10 (harmful)
│  │  └─ Level multiplier: CRISIS requires EXCELLENT for full resolution
│  └─ breakup.py:1-324
│     ├─ BreakupManager.check_threshold() → ThresholdResult
│     ├─ Risk levels: NONE, WARNING(<20), CRITICAL(<15), TRIGGERED(<10)
│     ├─ Breakup: score<10 OR 3 consecutive crises
│     └─ Type-specific breakup messages (jealousy, attention, boundary, trust)
│
└─ [→] life_simulation/
   ├─ models.py:1-246
   │  ├─ EventDomain: WORK, SOCIAL, PERSONAL
   │  ├─ EventType: 17 types across 3 domains
   │  ├─ EmotionalImpact [arousal, valence, dominance, intimacy deltas]
   │  ├─ LifeEvent [user_id, date, time, domain, type, description, entities, impact]
   │  ├─ NarrativeArc [domain, arc_type, status, entities, possible_outcomes]
   │  └─ NikitaEntity [type: colleague/friend/place/project, name, description]
   ├─ event_generator.py:1-342
   │  ├─ EventGenerator.generate_events_for_day() → 3-5 LifeEvents
   │  ├─ LLM-powered (Sonnet 4.5) with entity context + active arcs
   │  └─ Emotional impact: valence*0.3, arousal*0.2 conversion
   ├─ mood_calculator.py:1-198
   │  ├─ MoodState [arousal, valence, dominance, intimacy; 0.0-1.0]
   │  ├─ MoodCalculator.compute_from_events() → MoodState
   │  └─ Optional decay for older events (0.5-1.0 factor)
   ├─ simulator.py:1-347
   │  ├─ LifeSimulator [orchestrator for all life sim components]
   │  ├─ generate_next_day_events() → full pipeline with arc management
   │  ├─ get_today_events() → sorted by importance for context injection
   │  └─ get_events_for_context() → formatted dict for prompt
   ├─ arcs.py:1-528
   │  ├─ NarrativeArcSystem [10 predefined ArcTemplates]
   │  ├─ Categories: CAREER, SOCIAL, PERSONAL, RELATIONSHIP, FAMILY
   │  ├─ Stages: SETUP → RISING → CLIMAX → FALLING → RESOLVED
   │  ├─ Named characters: Marco, Lena, Viktor, Yuki, Alexei, Katya, Dr. Miriam
   │  ├─ Vulnerability-gated: requirement 0-4
   │  └─ should_start_new_arc() [max 2 active, min 3 days between, probability]
   ├─ entity_manager.py:1-327
   │  ├─ EntityManager [CRUD for colleagues, friends, places, projects]
   │  ├─ seed_entities() → from entities.yaml config
   │  └─ get_entity_context() → formatted string for prompt injection
   └─ store.py, narrative_manager.py, social_generator.py, psychology_mapper.py
      [persistence, arc lifecycle, social event generation, psychology mapping]
```

### Key Models and Data Structures

| Model | Location | Fields | Purpose |
|-------|----------|--------|---------|
| MetricDeltas | scoring/models.py:16 | intimacy, passion, trust, secureness (Decimal, -10..+10) | Per-interaction score changes |
| ResponseAnalysis | scoring/models.py:61 | deltas, explanation, behaviors, confidence | LLM scoring output |
| ScoreResult | scoring/calculator.py:32 | before/after scores+metrics, deltas, multiplier, events | Full scoring pipeline output |
| ScoreChangeEvent | scoring/models.py:141 | event_type, chapter, score_before/after, threshold | Threshold crossing alerts |
| ActiveConflict | conflicts/models.py:76 | type, severity, escalation_level, resolution_attempts | Active conflict state |
| ConflictTrigger | conflicts/models.py:50 | trigger_type, severity, context, messages | Detected trigger data |
| LifeEvent | life_simulation/models.py:133 | domain, type, description, entities, emotional_impact | Daily life event |
| MoodState | life_simulation/mood_calculator.py:20 | arousal, valence, dominance, intimacy (0.0-1.0) | Nikita's mood dimensions |
| ActiveArc | life_simulation/arcs.py:57 | template, category, stage, conversations_in_arc, characters | Running narrative storyline |
| EngagementStateMachine | engagement/state_machine.py:54 | _state, consecutive counters, history | 6-state engagement FSM |
| BossStateMachine | chapters/boss.py:20 | (stateless methods) | Boss encounter lifecycle |
| JudgmentResult | chapters/judgment.py:25 | outcome (PASS/FAIL), reasoning | Boss encounter verdict |

### Inter-Module Dependencies

```
scoring/service.py
├─ [→] scoring/analyzer.py (LLM analysis)
├─ [→] scoring/calculator.py (score computation)
├─ [→] scoring/models.py (data types)
├─ [→] db/repositories/score_history_repository.py (persistence)
└─ [→] config/enums.py (EngagementState)

scoring/calculator.py
├─ [→] constants.py (BOSS_THRESHOLDS, METRIC_WEIGHTS)
└─ [→] config/enums.py (EngagementState)

conflicts/detector.py
├─ [→] conflicts/models.py (types)
├─ [→] conflicts/store.py (persistence)
└─ [→] config/settings.py (LLM config)

conflicts/generator.py
├─ [→] conflicts/models.py (types)
└─ [→] conflicts/store.py (persistence)

life_simulation/simulator.py
├─ [→] entity_manager.py (entity CRUD)
├─ [→] event_generator.py (LLM event gen)
├─ [→] narrative_manager.py (arc lifecycle)
├─ [→] mood_calculator.py (mood computation)
└─ [→] store.py (persistence)

chapters/boss.py
├─ [→] constants.py (BOSS_ENCOUNTERS, BOSS_THRESHOLDS)
├─ [→] chapters/prompts.py (boss prompts)
└─ [→] db/repositories/user_repository.py (user state)

chapters/judgment.py
└─ [→] pydantic_ai.Agent (Sonnet for judgment)
```

---

## 2. Gap Analysis per Feature

### 2.1 Temperature Gauge

**Current**:
- No temperature gauge exists. Conflict severity is per-conflict (0.0-1.0), tracked on `ActiveConflict.severity` (`conflicts/models.py:96`).
- Escalation is time-based: SUBTLE(1) → DIRECT(2) → CRISIS(3) with fixed timelines (`escalation.py:86-109`).
- ConflictConfig has `warning_threshold=20` and `breakup_threshold=10` on relationship score (`models.py:160-171`), not on a separate temperature.
- Conflict cooldown is a flat 4 hours (`generator.py:90`).

**Target (Doc 24)**:
- Conflict temperature 0-100 per user, stored in `conflict_state` JSONB.
- Zones: 0-30 (normal), 30-60 (tension), 60-80 (active friction), 80-100 (crisis/boss).
- Temperature increases from: life sim stress, player behavior, score drops >3pt, boundary tests, NPC drama.
- Temperature decreases from: repair attempts, good interactions, time cooldown.

**Gap**: LARGE
- No `temperature` field anywhere in codebase. Must be created.
- Current system tracks conflict as discrete events (detect → generate → escalate → resolve). Doc 24 proposes a continuous temperature gauge that modulates behavior even without an active conflict.
- Current `ConflictConfig` escalation timing (2-6h, 12-24h) partially overlaps but operates on individual conflicts, not a global temperature.

**Extension Points**:
- `conflicts/models.py:115` — Add `ConflictTemperature` model with 0-100 field and zone computation.
- `conflicts/detector.py:145-202` — `detect()` method is the natural place to update temperature (currently returns triggers, could also update a temperature accumulator).
- `conflicts/generator.py:106-164` — `generate()` method's cooldown check (`_check_should_skip`) could be replaced by temperature zone checks.
- `scoring/calculator.py:189-258` — `_detect_events()` already detects threshold crossings; add temperature delta calculation alongside score events.
- New: `users.conflict_state` JSONB column (doc 24, Section 13) — stores temperature, gottman ratio, repair attempts.

### 2.2 Gottman Ratio

**Current**:
- No Gottman ratio tracking exists anywhere.
- `MetricDeltas.is_positive` (`scoring/models.py:55-58`) checks if total delta > 0 — this is the closest existing concept.
- Resolution quality (`resolution.py:26-32`) tracks quality per resolution attempt (EXCELLENT to HARMFUL), but no cumulative positive/negative counter.
- Score history is logged per interaction (`service.py:184-240`) with delta details, but not aggregated into a ratio.

**Target (Doc 24)**:
- 5:1 positive-to-negative interaction ratio tracked in `conflict_state` JSONB.
- Fields: `positive_count`, `negative_count`, `gottman_ratio`.
- Four Horsemen detection: criticism, contempt, defensiveness, stonewalling.
- Used as input to conflict injection probability.

**Gap**: LARGE
- No positive/negative counter exists. Must track per-interaction polarity.
- Four Horsemen detection requires new LLM prompts or rule-based detection.
- Current `behaviors_identified` field (`scoring/models.py:76`) captures behaviors but doesn't classify them as Four Horsemen.

**Extension Points**:
- `scoring/models.py:75-77` — `behaviors_identified: list[str]` could include Horsemen tags if analyzer prompt is updated.
- `scoring/analyzer.py:31-54` — `ANALYSIS_SYSTEM_PROMPT` is the key place to add Four Horsemen detection instructions.
- `scoring/service.py:52-107` — `score_interaction()` returns `ScoreResult`; after calculating, can check `deltas.is_positive` to increment positive/negative counters.
- `conflicts/models.py:115` — `ConflictConfig` could gain a `gottman_target_ratio` field.
- New: users.conflict_state JSONB — `positive_count`, `negative_count`, `gottman_ratio` fields.

### 2.3 Multi-Phase Boss

**Current**:
- Boss encounters are SINGLE-TURN judgment. Flow: `initiate_boss()` → player responds → `judge_boss_outcome()` → PASS/FAIL.
- `boss.py:83-113` — `initiate_boss()` returns one prompt (challenge_context + success_criteria + opening line).
- `judgment.py:39-63` — `judge_boss_outcome()` evaluates ONE user message against criteria.
- `prompts.py:19-147` — Each boss has exactly ONE in_character_opening, ONE challenge_context, ONE success_criteria.
- No concept of phases, escalation within a boss, or partial outcomes (PARTIAL).
- Result is binary: PASS or FAIL (`judgment.py:19-22`, `BossResult` enum).

**Target (Doc 24)**:
- 3-5 turn multi-phase boss encounters.
- Phases: [OPENING] → [ESCALATION] → [CRISIS PEAK] → [RESOLUTION].
- Three outcomes: PASS (breakthrough), PARTIAL (truce), FAIL (rupture).
- Boss encounter lasts across multiple messages, maintaining phase state.

**Gap**: VERY LARGE — requires fundamental redesign.
- Current boss is stateless single-turn. Doc 24 proposes stateful multi-turn.
- Need: boss phase tracking per user, per-phase prompts, multi-message conversation flow, PARTIAL outcome type.
- `BossResult` enum needs `PARTIAL` value.
- Boss prompts need per-phase variants (4 phases × 5 chapters = 20 prompt variants).
- Judgment needs to evaluate across the full multi-turn conversation, not just one message.

**Extension Points**:
- `chapters/boss.py:20-37` — `BossStateMachine` class: add `boss_phase: int` tracking and `advance_phase()` method.
- `chapters/prompts.py:10-16` — `BossPrompt` TypedDict: expand to include per-phase prompts dict.
- `chapters/judgment.py:19-22` — `BossResult` enum: add `PARTIAL = "PARTIAL"`.
- `chapters/judgment.py:39-63` — `judge_boss_outcome()`: modify to accept conversation history and phase context, evaluate based on phase progression.
- New: `users.conflict_state` JSONB — `boss_phase: int | null` field (doc 24, Section 9).
- DB: Need to persist boss phase state between messages (currently no boss state persisted).

### 2.4 Repair Attempts

**Current**:
- `escalation.py:134-157` — `EscalationManager.acknowledge()` method exists. It resets the escalation timer and increments `resolution_attempts`. This is the closest to "repair" but only delays escalation, doesn't reduce temperature.
- `resolution.py:150-202` — `ResolutionManager.evaluate()` evaluates resolution attempts with LLM, producing quality scores (EXCELLENT → HARMFUL). Resolution can fully resolve, partially reduce severity, or make things worse.
- `resolution.py:80-95` — Quality mappings: severity_reduction (0.0 to 1.0 for EXCELLENT, -0.2 for HARMFUL) and score_change (+10 to -10).
- `conflicts/models.py:103` — `ActiveConflict.resolution_attempts: int` tracks count.

**Target (Doc 24)**:
- "Repair attempts" tracked in conflict_state JSONB.
- Player can de-escalate conflicts through specific behaviors.
- Repair attempts interact with temperature gauge (reduce temperature).
- Integrated with Gottman ratio tracking.

**Gap**: MEDIUM
- Resolution machinery exists and is sophisticated (LLM + rule-based quality evaluation, severity reduction, score changes).
- Missing: connection to temperature gauge (temperature reduction on repair), repair attempt count in conflict_state JSONB, Gottman ratio update on repair.
- Current repair is per-conflict; doc 24 wants per-user ongoing tracking.

**Extension Points**:
- `conflicts/resolution.py:247-286` — `resolve()` method: after applying resolution, update temperature gauge and Gottman counters.
- `conflicts/escalation.py:134-157` — `acknowledge()`: extend to reduce temperature (not just reset timer).
- New: `users.conflict_state.repair_attempts` counter (doc 24).

### 2.5 Emotional-Driven Events

**Current**:
- `event_generator.py:82-122` — `generate_events_for_day()` takes: user_id, date, active_arcs, recent_events. NO emotional state input.
- `event_generator.py:124-234` — Prompt includes: day of week, entities, active arcs, recent events. NO mood/emotional state in the prompt.
- `mood_calculator.py:79-126` — `compute_from_events()` computes mood FROM events. The flow is events → mood (one-way).
- `simulator.py:98-159` — `generate_next_day_events()` pipeline: entities → arcs → recent events → generate. No mood/emotional state fed to generator.

**Target (Doc 24)**:
- Life events triggered by emotional state (4D model).
- Emotional state feeds INTO event generation (bidirectional: events affect mood AND mood affects events).
- Event cascade: morning events affect afternoon → evening trajectory.
- Stress events can override conflict minimum intervals.

**Gap**: MEDIUM-LARGE
- The one-way flow (events → mood) must become bidirectional (mood ↔ events).
- EventGenerator prompt needs emotional state context (mood, score trajectory, conflict state).
- Event cascade (intra-day progression) not implemented — events are generated as a batch, not sequentially.

**Extension Points**:
- `event_generator.py:82-98` — `generate_events_for_day()`: add `mood_state: MoodState` and `conflict_temperature: int` parameters.
- `event_generator.py:124-234` — `_build_generation_prompt()`: add mood context section to the LLM prompt.
- `simulator.py:98-159` — `generate_next_day_events()`: compute mood first, then pass to event generator.
- `mood_calculator.py:79-126` — No change needed (already computes mood from events correctly).
- New: bidirectional loop in simulator: compute mood → generate events → update mood.

### 2.6 Weekly Routine

**Current**:
- NO weekly routine system exists.
- `event_generator.py:177` — Day of week is included in the prompt ("Generate 3-5 realistic life events for Nikita on {day_name}") and the prompt mentions "Consider day of week ({day_name}) - weekends differ from weekdays" (line 206).
- This is the only nod to weekly patterns — it's a hint in the LLM prompt, not a structured routine.
- No `routine_config` column or data structure.

**Target (Doc 24)**:
- Predefined weekly schedule stored in `users.routine_config` JSONB.
- Mon: work from home; Tue: coffee with Lena; Wed: deep work; Thu: therapy; Fri: social; Sat: chemistry; Sun: recovery.
- Static config + monthly meta-instructions modify the routine.
- Determines base activity and availability.

**Gap**: LARGE
- No routine data structure, no storage, no consumption by event generator.
- Need: `RoutineConfig` model, default routine, per-day activity/availability, integration into event generation prompt.

**Extension Points**:
- `event_generator.py:124-234` — `_build_generation_prompt()`: add routine context for the specific day.
- `life_simulation/models.py` — Add `WeeklyRoutine` / `DayRoutine` models.
- New: `users.routine_config` JSONB column (doc 24, Section 13).
- `simulator.py:98-159` — Load routine config before event generation, pass to EventGenerator.
- Optional: `nikita/config_data/life_simulation/` — Add `routine.yaml` default config (alongside `entities.yaml`).

### 2.7 Meta-Instructions

**Current**:
- NO meta-instruction system exists.
- Chapter progression is score-based only: reach boss threshold → boss encounter → pass → advance chapter (`boss.py:39-66`).
- `CHAPTER_BEHAVIORS` loaded from `prompts/chapters/chapter_N.prompt` files are the closest concept — they define per-chapter behavioral guidelines.
- No monthly planning, no temporal behavioral arcs beyond chapters.
- Narrative arcs (`arcs.py:154-527`) provide multi-conversation storylines with named characters, but they're independent of meta-instructions.

**Target (Doc 24)**:
- Monthly meta-instructions that evolve Nikita's behavior.
- Hierarchy: Monthly → Weekly → Daily → Per-conversation guidance.
- Examples: "This month, Nikita is processing father's birthday", "Work project at crisis point".
- Stored in `users.meta_instructions` JSONB.
- Shapes which life events get generated and how she behaves.

**Gap**: LARGE
- No meta-instruction model, storage, generation, or consumption.
- Need: `MetaInstruction` model, monthly generation job (Opus 4.6), integration into event generator and prompt builder.
- Narrative arc system (`arcs.py`) is complementary but not a substitute — arcs are player-facing storylines, meta-instructions are behind-the-scenes behavioral guidance.

**Extension Points**:
- New: `users.meta_instructions` JSONB column (doc 24, Section 13).
- `event_generator.py:124-234` — `_build_generation_prompt()`: inject monthly context.
- `arcs.py:339-368` — `should_start_new_arc()`: meta-instructions could influence arc selection.
- New: Monthly batch job (pg_cron) to generate meta-instructions.
- Integration: Psyche Agent (doc 24) would read meta-instructions when computing psyche state.

### 2.8 NPC State Tracking

**Current**:
- `NikitaEntity` model (`life_simulation/models.py:220-245`) tracks name, type, description, relationship. This is STATIC — seeded once, rarely updated.
- `EntityManager` (`entity_manager.py:105-327`) provides CRUD but entities don't have state that evolves.
- `NarrativeArcSystem` (`arcs.py:154-527`) has NAMED CHARACTERS: Marco, Lena, Viktor, Yuki, Alexei, Katya, Dr. Miriam. But these are template-level references, not per-user stateful NPCs.
- `ActiveArc.involved_characters` (`arcs.py:70`) lists character names involved in an arc.
- No sentiment tracking, no event history per NPC, no dynamic relationship evolution.

**Target (Doc 24)**:
- `users.npc_states` JSONB column with 5 NPCs per user.
- Schema per NPC: `{name, relationship, last_event, sentiment, events[5]}`.
- NPCs: Emma/Lena, Marcus/Viktor, Sarah/Yuki, Mom, Ex.
- Updated by LifeSimStage and conversation mentions.
- Read as JSONB for fast injection (<5ms).

**Gap**: MEDIUM
- Entity infrastructure exists but lacks dynamic state.
- Named characters exist in arc templates but aren't tracked as stateful NPCs.
- Need: `npc_states` JSONB column, NPC state update logic in life sim and conversation pipeline, NPC context retrieval for prompt injection.

**Extension Points**:
- New: `users.npc_states` JSONB column (doc 24, Section 13).
- `life_simulation/models.py` — Add `NPCState` model (name, relationship, last_event, sentiment, events[5]).
- `arcs.py:430-463` — `create_arc()`: when arc starts, update NPC state for involved characters.
- `arcs.py:465-492` — `update_arc()`: when arc advances/resolves, update NPC states.
- `simulator.py:98-159` — `generate_next_day_events()`: update NPC states when events reference characters.
- `entity_manager.py:263-310` — `get_entity_context()`: enhance to include NPC dynamic state.

---

## 3. Shared Infrastructure Needs

### New Models/Types

| Model | Location (proposed) | Fields | Used By |
|-------|---------------------|--------|---------|
| `ConflictTemperature` | conflicts/models.py | temperature(0-100), zone, last_updated | Detector, Generator, Prompt |
| `GottmanTracker` | conflicts/models.py | positive_count, negative_count, ratio, horsemen_detected | Scoring, Conflicts |
| `ConflictState` (JSONB schema) | conflicts/models.py | temperature, type, repair_attempts, gottman, boss_phase | Users table |
| `NPCState` | life_simulation/models.py | name, relationship, last_event, sentiment, events[5] | Life Sim, Prompt |
| `WeeklyRoutine` / `DayRoutine` | life_simulation/models.py | day_of_week, activities, availability, energy_pattern | Event Generator |
| `MetaInstruction` | new module or config | month, theme, behavioral_arc, shaping_rules | Event Gen, Psyche Agent |
| `PsycheState` | new module | attachment, defense, guidance, monologue, vulnerability, tone, topics | Psyche Agent, Prompt |
| `BossPhaseState` | chapters/boss.py | current_phase(0-3), turn_count, phase_prompts, partial_allowed | Boss multi-phase |

### Database Changes

```sql
-- 1. New table: psyche_states
CREATE TABLE psyche_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    state JSONB NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    model TEXT NOT NULL,
    token_count INT,
    UNIQUE(user_id)
);

-- 2. New columns on users
ALTER TABLE users ADD COLUMN routine_config JSONB DEFAULT '{}';
ALTER TABLE users ADD COLUMN meta_instructions JSONB DEFAULT '{}';
ALTER TABLE users ADD COLUMN last_conflict_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN npc_states JSONB DEFAULT '[]';
ALTER TABLE users ADD COLUMN conflict_state JSONB DEFAULT '{}';

-- 3. New column on user_metrics
ALTER TABLE user_metrics ADD COLUMN vulnerability_exchanges INT DEFAULT 0;
```

**Migration Impact**: 1 new table, 6 new columns. All nullable/defaulted — zero-downtime migration. No data migration needed.

### Constants Additions

| Constant | Location | Value | Purpose |
|----------|----------|-------|---------|
| TEMPERATURE_ZONES | conflicts/models.py | {normal:0-30, tension:30-60, friction:60-80, crisis:80-100} | Zone thresholds |
| GOTTMAN_TARGET_RATIO | conflicts/models.py | 5.0 | Target positive:negative ratio |
| FOUR_HORSEMEN | scoring/models.py | [criticism, contempt, defensiveness, stonewalling] | Gottman detection |
| BOSS_PHASES | chapters/boss.py | [OPENING, ESCALATION, CRISIS_PEAK, RESOLUTION] | Multi-phase boss |
| DEFAULT_ROUTINE | life_simulation/models.py | {mon:..., sun:...} | Weekly schedule |
| CONFLICT_MIN_INTERVALS | conflicts/models.py | {ch1:5, ch2:7, ch3:10, ch4:12, ch5:15} | Per-chapter minimums |
| TEMPERATURE_DECAY_PER_HOUR | conflicts/models.py | 0.5 | Natural cooling |
| TEMPERATURE_INCREASE_RATES | conflicts/models.py | {score_drop:+5, neglect:+3, boundary:+8, ...} | Per-trigger temp change |

---

## 4. Risk Assessment

### Breaking Changes

| Area | Risk | Impact | Mitigation |
|------|------|--------|------------|
| Boss encounters | HIGH | Current single-turn boss flow changes to multi-turn. Pipeline, judgment, prompt all affected. | Feature flag: `multi_phase_boss_enabled`. Old flow preserved as fallback. |
| Conflict system | MEDIUM | Temperature gauge replaces discrete cooldown model. Existing conflicts need migration. | Temperature defaults to 0 for existing users. Gradual rollout via feature flag. |
| Scoring pipeline | LOW | Adding Gottman tracking is additive, doesn't change existing score calculation. | Gottman counters initialized to 0. No existing data affected. |
| Life sim events | LOW | Adding mood input to event generator is additive. Existing events unaffected. | New params have defaults (None). Old callers continue working. |
| NPC states | LOW | New JSONB column, no existing data changed. | Default `[]`. Seeded on first life sim run. |

### Migration Complexity

| Component | Complexity | Estimated Effort | Dependencies |
|-----------|-----------|-----------------|-------------|
| Temperature gauge | Medium | 2-3 days | ConflictState model, detector integration, prompt injection |
| Gottman ratio | Medium | 2 days | Scoring analyzer prompt update, counter tracking |
| Multi-phase boss | High | 3-4 days | Phase state model, per-phase prompts (20 variants), judgment rewrite |
| Repair attempts | Low | 1 day | Extends existing resolution system |
| Emotional-driven events | Medium | 2 days | Mood→EventGenerator bidirectional flow |
| Weekly routine | Low-Medium | 1-2 days | Config model, YAML, EventGenerator integration |
| Meta-instructions | Medium | 2-3 days | Monthly batch job, EventGenerator + Psyche integration |
| NPC state tracking | Medium | 2 days | JSONB schema, update hooks in life sim + arcs |
| **Total** | | **15-20 days** | (aligns with doc 24 estimate) |

### Test Impact

| Module | Current Tests | Expected New Tests | Risk |
|--------|--------------|-------------------|------|
| scoring/ | 60 | +20-30 (Gottman, Horsemen) | LOW — additive |
| engagement/ | 179 | +5-10 (temperature integration) | LOW — no breaking changes |
| chapters/ | 142 | +40-60 (multi-phase boss, 4 phases × 5 chapters) | HIGH — fundamental redesign |
| conflicts/ | (spec 027 tests) | +30-40 (temperature, repair tracking) | MEDIUM — extends existing |
| life_simulation/ | (spec 022 tests) | +20-30 (routine, emotional-driven, NPC state) | LOW — additive |
| **Total new tests** | | **~115-170** | |

Key testing patterns to preserve:
- Scoring uses async mocks for LLM calls (`tests/conftest.py` patterns)
- Conflict system uses in-memory `ConflictStore` for tests
- Life sim uses injected `llm_client` parameter for test isolation
- Boss judgment mocks `_call_llm` method
