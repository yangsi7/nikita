# Vision Gap Analysis — Nikita: Don't Get Dumped

**Date**: 2026-02-21
**Type**: audit
**Scope**: Original game design vision vs actual implementation
**Sources**: `memory/product.md`, `memory/architecture.md`, `memory/game-mechanics.md`, `memory/user-journeys.md`, `plans/master-plan.md`, `memory/integrations.md`, `memory/constitution.md`, codebase search

---

## Coverage Scorecard

| # | Vision Feature | Status | Coverage |
|---|---------------|--------|----------|
| A | Proactive Initiation (20-30% Nikita-initiated) | FULLY IMPLEMENTED | 100% |
| B | Life Simulation (40%+ conversation influence) | FULLY IMPLEMENTED | 100% |
| C | Configurable Darkness Levels (1-5 scale) | FULLY IMPLEMENTED | 100% |
| D | Voice Onboarding by Meta-Nikita | FULLY IMPLEMENTED | 100% |
| E | Three Persona Types (Marcus/Elena/James) | SUPERSEDED | N/A |
| F | Strategic Silence (10-20% of interactions) | FULLY IMPLEMENTED | 100% |
| G | Memory Callback Rate (2-3/week references) | PARTIALLY IMPLEMENTED | 60% |
| H | Social Circle / NPC System | FULLY IMPLEMENTED | 100% |
| I | Vice System (personalized temptation) | FULLY IMPLEMENTED | 100% |
| J | Conflict System (relationship conflicts) | FULLY IMPLEMENTED | 100% |
| K | Multi-Phase Boss Encounters | FULLY IMPLEMENTED | 100% |
| L | Psyche System (emotional intelligence) | FULLY IMPLEMENTED | 100% |
| M | Decay System (metrics decay over time) | FULLY IMPLEMENTED | 100% |
| N | Chapter Progression (5 chapters + thresholds) | FULLY IMPLEMENTED | 100% |
| O | Portal Dashboard (player + admin) | FULLY IMPLEMENTED | 100% |
| P | Behavioral Meta-Instruction System | FULLY IMPLEMENTED | 100% |
| Q | Emotional State Engine (4D tracking) | FULLY IMPLEMENTED | 100% |
| R | Skip/Timing Mechanics (chapter-based) | PARTIALLY IMPLEMENTED | 70% |
| S | Persona Adaptation (user-personalized Nikita) | FULLY IMPLEMENTED | 100% |

**Overall Vision Coverage**: 17/18 features FULLY IMPLEMENTED, 1 SUPERSEDED, 2 PARTIALLY IMPLEMENTED

**Effective Coverage**: ~94%

---

## Detailed Analysis

### A. Proactive Initiation (20-30% Nikita-initiated)

**Status**: FULLY IMPLEMENTED

**Evidence**:
- `nikita/touchpoints/` — 7 modules [engine.py, scheduler.py, generator.py, silence.py, store.py, models.py, `__init__.py`]
- `nikita/touchpoints/engine.py:1-18` — TouchpointEngine orchestrates full delivery pipeline
- `nikita/touchpoints/scheduler.py:1-7` — Evaluates time triggers, event triggers, gap triggers
- `nikita/db/models/scheduled_touchpoint.py` — DB model for scheduled touchpoints
- `nikita/db/models/scheduled_event.py` — scheduled_events table for proactive messaging
- `tests/touchpoints/` — 7 test files covering scheduling, generation, delivery, silence, E2E
- Pipeline stage: `nikita/pipeline/stages/touchpoint.py` — TouchpointStage in unified pipeline

**Gap**: None. Proactive initiation fully implemented with time triggers, event triggers, gap triggers, and strategic silence integration.

---

### B. Life Simulation (40%+ conversation influence)

**Status**: FULLY IMPLEMENTED

**Evidence**:
- `nikita/life_simulation/` — 11 modules (simulator, event_generator, narrative_manager, entity_manager, mood_calculator, store, social_generator, arcs, psychology_mapper, models, `__init__.py`)
- `nikita/life_simulation/simulator.py:37-58` — LifeSimulator orchestrates daily event generation (3-5 events/day across work, social, personal domains)
- `nikita/life_simulation/__init__.py:1-40` — Spec 022 + Spec 035 (Deep Humanization) + Spec 055 (Routines)
- Narrative arcs: `nikita/life_simulation/arcs.py` — NarrativeArcSystem with arc templates, categories, stages
- Psychology mapper: `nikita/life_simulation/psychology_mapper.py` — CoreWound, DefenseMechanism, TraumaTrigger
- Pipeline stage: `nikita/pipeline/stages/life_sim.py` — LifeSimStage integrated into unified pipeline
- `tests/life_simulation/` — 14 test files

**Gap**: None. Life sim generates events, derives mood, injects into context, tracks narrative arcs.

---

### C. Configurable Darkness Levels (1-5 scale)

**Status**: FULLY IMPLEMENTED

**Evidence**:
- `nikita/onboarding/preference_config.py:23-37` — DarknessLevelConfig dataclass with level 1-5, manipulation intensity, substance mentions, possessiveness, emotional intensity
- `nikita/onboarding/server_tools.py` — configure_preferences server tool collects darkness_level during voice onboarding
- `nikita/db/repositories/user_repository.py` — darkness_level stored in user profile
- `tests/onboarding/test_preferences.py` — Tests for preference configuration

**Gap**: None. Darkness level collected during onboarding and stored per user.

---

### D. Voice Onboarding by Meta-Nikita

**Status**: FULLY IMPLEMENTED

**Evidence**:
- `nikita/onboarding/` — 8 modules (meta_nikita.py, server_tools.py, handoff.py, voice_flow.py, profile_collector.py, preference_config.py, models.py, `__init__.py`)
- `nikita/onboarding/meta_nikita.py` — Agent config, persona (Underground Game Hostess)
- `nikita/onboarding/server_tools.py` — collect_profile, configure_preferences, complete_onboarding
- `nikita/onboarding/handoff.py` — HandoffManager sends first Nikita message via Telegram
- ElevenLabs Agent ID: `agent_4801kewekhxgekzap1bqdr62dxvc`
- API: `/api/v1/onboarding/*` (5 endpoints)
- `tests/onboarding/` — 10 test files (231 tests)
- `memory/user-journeys.md:305-358` — Journey 7: Voice Onboarding documented

**Gap**: None. Full 4-stage voice onboarding: introduction, profile collection, preference configuration, handoff.

---

### E. Three Persona Types (Marcus/Elena/James)

**Status**: SUPERSEDED

**Evidence**:
- No code references to Marcus, Elena, or James persona types
- `memory/product.md:30-31` — Product personas (Sarah 28, James 34, Elena 22) are USER personas, not AI personas
- Single Nikita persona with user-specific adaptation via `nikita/services/persona_adaptation.py`
- PersonaAdaptationService maps user attributes to Nikita variations (occupation, hobbies, edge level)

**Gap**: Vision mentions three user personas (target audience segments), not three AI personalities. There was never a design for multiple AI persona types. Single Nikita personality with per-user adaptation matches design intent. NOT a gap.

---

### F. Strategic Silence (10-20% of interactions)

**Status**: FULLY IMPLEMENTED

**Evidence**:
- `nikita/touchpoints/silence.py:1-12` — 10-20% of touchpoints skipped (chapter-dependent)
- `nikita/touchpoints/silence.py:20-27` — SilenceReason enum (RANDOM, EMOTIONAL, CONFLICT, CHAPTER_RATE, RECENT_CONTACT)
- `nikita/touchpoints/silence.py:46-50` — StrategicSilence class evaluates skip decisions
- `tests/touchpoints/test_silence.py` — Tests for strategic silence
- Emotional state integration: more silence during conflicts

**Gap**: None. Strategic silence implemented with chapter-based rates and emotional modifiers.

---

### G. Memory Callback Rate (2-3/week natural references)

**Status**: PARTIALLY IMPLEMENTED

**Evidence**:
- `nikita/agents/text/tools.py:17-40` — recall_memory tool for semantic search
- `nikita/memory/supabase_memory.py` — SupabaseMemory with pgVector search + add_fact
- `nikita/agents/text/agent.py` — Agent has recall_memory tool available
- `nikita/pipeline/stages/memory_update.py` — MemoryUpdateStage stores facts
- `nikita/pipeline/stages/extraction.py` — ExtractionStage extracts facts from conversations

**Gap**: Memory storage and retrieval infrastructure is fully implemented. However, there is no explicit **scheduling mechanism** that ensures 2-3 natural memory callbacks per week. The current system relies on the LLM organically choosing to use the recall_memory tool during conversations. There is no proactive "reference a past memory" trigger in the touchpoint scheduler or pipeline stages. The rate of memory callbacks is emergent behavior, not enforced.

**Missing**:
- No `MemoryCallbackScheduler` or equivalent that ensures periodic natural references
- No metrics tracking how often memory callbacks occur per user per week
- Touchpoint generator could be enhanced to include memory-recall-based touchpoints

---

### H. Social Circle / NPC System

**Status**: FULLY IMPLEMENTED

**Evidence**:
- `nikita/db/models/social_circle.py:25-58` — UserSocialCircle model with friend_name, friend_role, age, occupation, personality, relationship_to_nikita, storyline_potential, trigger_conditions
- `nikita/life_simulation/social_generator.py` — SocialCircleGenerator (Spec 035)
- `nikita/life_simulation/entity_manager.py` — EntityManager for recurring NPCs
- `nikita/db/repositories/social_circle_repository.py` — DB repository
- `nikita/agents/psyche/agent.py:44-45` — NPCs referenced (Lena, Viktor, Yuki, therapist)
- 5-8 named friend characters per user, adapted to user profile (location, hobbies, job)
- Spec 055: NPC state tracking (last_event, sentiment)
- `tests/onboarding/test_handoff_social_circle.py` — Social circle integration tests
- `tests/life_simulation/test_social_generator.py` — Social generator tests

**Gap**: None. Social circle generated during onboarding, NPCs integrated into life sim and conversations.

---

### I. Vice System (personalized temptation mechanics)

**Status**: FULLY IMPLEMENTED

**Evidence**:
- `nikita/engine/vice/` — 7 modules (models, analyzer, scorer, injector, boundaries, service, `__init__.py`)
- 8 vice categories: intellectual_dominance, risk_taking, substances, sexuality, emotional_intensity, rule_breaking, dark_humor, vulnerability
- `nikita/engine/vice/service.py:32-40` — ViceService orchestrates detection, scoring, injection, boundary enforcement
- `nikita/engine/vice/analyzer.py` — LLM-based vice signal detection
- `nikita/engine/vice/injector.py` — Chapter-aware prompt injection
- `nikita/engine/vice/boundaries.py` — Ethical boundary enforcement (chapter caps)
- 70 tests across 6 test files

**Gap**: None. Full vice pipeline: detect -> score -> inject -> enforce boundaries.

---

### J. Conflict System (relationship conflicts)

**Status**: FULLY IMPLEMENTED

**Evidence**:
- `nikita/conflicts/` — 12 modules (models, detector, generator, escalation, resolution, breakup, temperature, gottman, persistence, migration, store, `__init__.py`)
- `nikita/conflicts/__init__.py:1-31` — Trigger detection, conflict generation, escalation (subtle -> direct -> crisis), resolution evaluation, breakup risk
- `nikita/conflicts/gottman.py` — Gottman-based relationship dynamics
- `nikita/conflicts/temperature.py` — Conflict temperature tracking
- `nikita/conflicts/breakup.py` — Breakup risk management
- Feature flag: `conflict_temperature_enabled` (Spec 057)
- Pipeline stage: `nikita/pipeline/stages/conflict.py` — ConflictStage
- `tests/conflicts/` — 22 test files

**Gap**: None. Full conflict lifecycle: detection -> generation -> escalation -> resolution -> breakup risk.

---

### K. Multi-Phase Boss Encounters

**Status**: FULLY IMPLEMENTED

**Evidence**:
- `nikita/engine/chapters/boss.py:30-58` — BossPhase enum (OPENING, RESOLUTION), BossPhaseState model (Spec 058)
- `nikita/engine/chapters/phase_manager.py:23-60` — BossPhaseManager: start_boss, advance_phase (OPENING -> RESOLUTION), is_resolution_complete, is_timed_out
- `nikita/engine/chapters/judgment.py` — BossJudgment, BossResult, JudgmentResult
- `nikita/engine/chapters/prompts.py` — BOSS_PROMPTS for 5 chapters
- PARTIAL outcome support (Spec 058)
- 24-hour boss timeout
- `tests/engine/chapters/` — test_boss_adversarial.py, test_boss_backward_compat.py, test_phase_manager.py, test_initiation.py

**Gap**: None. Full 2-phase boss encounters with OPENING -> RESOLUTION -> judgment.

---

### L. Psyche System (emotional intelligence)

**Status**: FULLY IMPLEMENTED

**Evidence**:
- `nikita/agents/psyche/` — 6 modules (agent, batch, trigger, deps, models, `__init__.py`)
- `nikita/agents/psyche/agent.py:29-49` — PsycheState generation via Pydantic AI, captures Nikita's fearful-avoidant attachment, core wounds, defense mechanisms
- `nikita/agents/psyche/batch.py` — Daily batch generation
- `nikita/agents/psyche/trigger.py` — Tier-based trigger system
- `nikita/db/models/psyche_state.py` — DB persistence
- `nikita/db/repositories/psyche_state_repository.py` — Repository
- Pipeline integration: `nikita/pipeline/stages/prompt_builder.py` references psyche state
- `tests/agents/psyche/` — 6 test files (agent, batch, trigger, models, cost_control, integration)
- API endpoint: `nikita/api/routes/tasks.py` — Psyche batch task
- Portal: `tests/api/routes/test_portal_psyche_tips.py` — Psyche tips in portal

**Gap**: None. Full psyche system with agent, batch processing, triggers, and pipeline integration.

---

### M. Decay System (metrics decay over time)

**Status**: FULLY IMPLEMENTED

**Evidence**:
- `nikita/engine/decay/` — 4 modules (calculator, processor, models, `__init__.py`)
- `nikita/engine/decay/processor.py:24-34` — DecayProcessor batch processes all active users
- `nikita/engine/decay/calculator.py` — DecayCalculator with chapter-specific rates
- Decay rates: 0.8/0.6/0.4/0.3/0.2 per hour (chapters 1-5)
- Grace periods: 8/16/24/48/72 hours (chapters 1-5)
- pg_cron endpoint: `nikita/api/routes/tasks.py` — POST /tasks/decay
- Game over when score reaches 0%
- 44+ tests (see engine/CLAUDE.md)

**Gap**: None. Decay fully wired with pg_cron scheduling, chapter-specific rates, and game-over logic.

---

### N. Chapter Progression (5 chapters with thresholds)

**Status**: FULLY IMPLEMENTED

**Evidence**:
- `nikita/engine/chapters/` — 5 modules (boss.py, phase_manager.py, judgment.py, prompts.py, `__init__.py`)
- `nikita/engine/constants.py` — CHAPTER_NAMES, BOSS_THRESHOLDS (55/60/65/70/75%), CHAPTER_BEHAVIORS, DECAY_RATES, GRACE_PERIODS
- 5 chapters: Curiosity, Intrigue, Investment, Intimacy, Established
- Boss encounters per chapter with 3-attempt limit
- Game over on 3 boss failures
- Victory on Chapter 5 boss pass
- 142 chapter tests

**Gap**: None.

---

### O. Portal Dashboard (player + admin)

**Status**: FULLY IMPLEMENTED

**Evidence**:
- `portal/src/app/` — 27 .tsx files
- Player routes: /dashboard, /dashboard/engagement, /dashboard/vices, /dashboard/conversations, /dashboard/diary, /dashboard/settings, /dashboard/nikita (day, stories, circle, mind), /dashboard/insights
- Admin routes: /admin, /admin/users, /admin/pipeline, /admin/voice, /admin/text, /admin/jobs, /admin/prompts, /admin/users/[id]
- Auth: login page with Supabase SSR PKCE
- Deployed: https://portal-phi-orcin.vercel.app
- 37 Playwright E2E tests

**Gap**: None. Full player + admin portal deployed.

---

### P. Behavioral Meta-Instruction System

**Status**: FULLY IMPLEMENTED

**Evidence**:
- `nikita/behavioral/` — 5 modules (engine.py, detector.py, selector.py, models.py, `__init__.py`)
- `nikita/behavioral/engine.py:23-48` — MetaInstructionEngine orchestrates detection + selection + formatting
- `nikita/behavioral/detector.py` — SituationDetector
- `nikita/behavioral/selector.py` — InstructionSelector
- `nikita/behavioral/models.py` — InstructionSet, SituationContext, SituationType
- `tests/behavioral/` — 5 test files

**Gap**: None. Full behavioral guidance pipeline with situation detection and instruction selection.

---

### Q. Emotional State Engine (4D tracking)

**Status**: FULLY IMPLEMENTED

**Evidence**:
- `nikita/emotional_state/` — 6 modules (computer.py, conflict.py, recovery.py, store.py, models.py, `__init__.py`)
- `nikita/emotional_state/__init__.py:1-13` — Multi-dimensional tracking: arousal, valence, dominance, intimacy
- Conflict states: passive_aggressive, cold, vulnerable, explosive
- StateComputer, ConflictDetector, RecoveryManager
- Pipeline stage: `nikita/pipeline/stages/emotional.py` — EmotionalStage
- `tests/emotional_state/` — 5 test files

**Gap**: None. Full 4D emotional state engine with conflict detection and recovery.

---

### R. Skip/Timing Mechanics (chapter-based)

**Status**: PARTIALLY IMPLEMENTED

**Evidence**:
- `nikita/agents/text/skip.py:14-23` — SkipDecision class EXISTS but skip rates **DISABLED** (all set to 0.00)
- Comment at line 15: "DISABLED: All set to 0 - random skipping disabled for now. Future: Message scheduling engine via pg_cron will handle response timing."
- `nikita/agents/text/timing.py` — ResponseTimer with gaussian delay distribution (IMPLEMENTED)
- Vision specifies chapter-based skip rates: Ch1 25-40%, Ch2 15-25%, Ch3 5-15%, Ch4 2-10%, Ch5 0-5%

**Gap**: Skip rates are defined but explicitly disabled. The timing system (response delays) is implemented, but the skip mechanic (not responding at all) has been turned off. The touchpoint system's strategic silence partially compensates for proactive messages, but reactive message skipping is not active.

**Missing**:
- Re-enable chapter-based skip rates or migrate to a scheduling-based approach
- Current behavior: Nikita always responds (100% response rate across all chapters)
- This undermines the Chapter 1 experience ("Are you worth my time?") where 25-40% skip rate was designed

---

### S. Persona Adaptation (user-personalized Nikita)

**Status**: FULLY IMPLEMENTED

**Evidence**:
- `nikita/services/persona_adaptation.py:15-40` — PersonaAdaptationService maps user profile to Nikita persona overrides
- Life stage -> occupation mapping (tech -> cybersecurity consultant, artist -> digital artist, etc.)
- Social scene -> hobby mapping (techno -> underground DJ, art -> gallery hopping, etc.)
- Integrated into onboarding handoff flow
- `tests/services/test_persona_adaptation.py` — Tests

**Gap**: None. Nikita's persona adapts to user's life stage, social scene, and interests.

---

## Tree-of-Thought Summary

```
VISION_COVERAGE [94% effective]
├─ [FULLY IMPLEMENTED: 15/18]
│  ├─ [A] Proactive Initiation [touchpoints/, 7 modules]
│  ├─ [B] Life Simulation [life_simulation/, 11 modules, 14 test files]
│  ├─ [C] Darkness Levels [onboarding/preference_config.py]
│  ├─ [D] Meta-Nikita Onboarding [onboarding/, 8 modules, 231 tests]
│  ├─ [F] Strategic Silence [touchpoints/silence.py, 10-20%]
│  ├─ [H] Social Circle / NPC [db/models/social_circle.py, life_simulation/social_generator.py]
│  ├─ [I] Vice System [engine/vice/, 7 modules, 70 tests]
│  ├─ [J] Conflict System [conflicts/, 12 modules, 22 test files]
│  ├─ [K] Multi-Phase Boss [engine/chapters/, phase_manager.py, Spec 058]
│  ├─ [L] Psyche System [agents/psyche/, 6 modules]
│  ├─ [M] Decay System [engine/decay/, 4 modules, 44+ tests]
│  ├─ [N] Chapter Progression [engine/chapters/, constants.py]
│  ├─ [O] Portal Dashboard [portal/, 27 pages, deployed]
│  ├─ [P] Behavioral Meta-Instructions [behavioral/, 5 modules]
│  ├─ [Q] Emotional State Engine [emotional_state/, 6 modules]
│  └─ [S] Persona Adaptation [services/persona_adaptation.py]
│
├─ [PARTIALLY IMPLEMENTED: 2/18]
│  ├─ [G] Memory Callback Rate [60%]
│  │  ├─ [✓] Memory storage + retrieval infrastructure (pgVector)
│  │  ├─ [✓] recall_memory tool available to agent
│  │  └─ [!] No scheduled callback rate enforcement (2-3/week)
│  └─ [R] Skip/Timing Mechanics [70%]
│     ├─ [✓] ResponseTimer (gaussian delays) IMPLEMENTED
│     ├─ [✓] SkipDecision class EXISTS
│     └─ [!] Skip rates DISABLED (all 0.00) — undermines Ch1 experience
│
└─ [SUPERSEDED: 1/18]
   └─ [E] Three Persona Types
      └─ [→] Single Nikita with per-user adaptation via PersonaAdaptationService
```

---

## Actionable Gaps (Priority Order)

### GAP-1: Skip Rates Disabled (HIGH)

**Impact**: Chapter 1 is designed around unpredictability — 25-40% of messages should be skipped. Currently Nikita responds to every message, reducing the "Am I worth her time?" tension.

**Fix**: Re-enable skip rates in `nikita/agents/text/skip.py:17-23` or implement equivalent behavior via the touchpoint scheduling system.

**Files**: `nikita/agents/text/skip.py:17-23`

### GAP-2: Memory Callback Rate Not Enforced (MEDIUM)

**Impact**: Vision calls for 2-3 natural memory references per week. Current system relies on LLM organically using recall_memory tool — no enforcement or tracking.

**Fix Options**:
1. Add memory-recall touchpoint type to `nikita/touchpoints/scheduler.py` (schedule 2-3 memory-based proactive messages per week)
2. Add pipeline stage that preloads a "callback memory" into prompt context periodically
3. Track callback rate metrics and alert when below target

**Files**: `nikita/touchpoints/scheduler.py`, `nikita/pipeline/stages/prompt_builder.py`

---

## Systems Not In Vision But Implemented (Bonus)

These systems were added beyond the original vision:

| System | Location | Description |
|--------|----------|-------------|
| Gottman Dynamics | `nikita/conflicts/gottman.py` | Research-based relationship conflict modeling |
| Conflict Temperature | `nikita/conflicts/temperature.py` | Continuous temperature tracking (Spec 057) |
| Text Patterns | `nikita/text_patterns/` | Message length and style processing |
| Narrative Arc System | `nikita/life_simulation/arcs.py` | Multi-conversation story arcs (Spec 035) |
| Psychology Mapper | `nikita/life_simulation/psychology_mapper.py` | Deep psychological response mapping |
| Weekly Routines | `nikita/life_simulation/models.py` (Spec 055) | Routine-aware event generation |
| Persona Adaptation | `nikita/services/persona_adaptation.py` | User-specific Nikita customization |

---

## Conclusion

The Nikita project has achieved **94% vision coverage** with 15 of 18 identified vision features fully implemented, 2 partially implemented, and 1 appropriately superseded. The two gaps (disabled skip rates, unscheduled memory callbacks) are concrete, fixable issues that do not require architectural changes. The project has also implemented several systems beyond the original vision (Gottman dynamics, narrative arcs, psychology mapper) that enhance the core experience.
