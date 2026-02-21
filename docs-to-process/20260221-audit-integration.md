# Integration Audit: Waves A-D Cross-System Integration

**Date**: 2026-02-21
**Auditor**: integration-auditor
**Scope**: All 10 integration points across Wave A (Life Sim, Psyche), Wave B (Boss, Conflict), Wave C-D (Portal)

---

## Integration Matrix

| # | Integration Pair | Status | Evidence | Notes |
|---|-----------------|--------|----------|-------|
| 1 | Psyche Agent <-> Life Sim | PARTIAL | See IP-1 | PsycheDeps declares `life_events` field but batch never populates it |
| 2 | Conflict System <-> Boss | WIRED | See IP-2 | Boss reads/writes `conflict_details.boss_phase` JSONB |
| 3 | Psyche <-> Prompt Caching | WIRED | See IP-3 | L3 section 3.5 in `system_prompt.j2`, `psyche_state` in template vars |
| 4 | Life Sim <-> Portal | WIRED | See IP-4 | `/portal/life-events` API route + day page + timeline component |
| 5 | Psyche <-> Portal | WIRED | See IP-5 | `/portal/psyche-tips` API route + hook + day page component |
| 6 | Multi-Phase Boss <-> Portal | PARTIAL | See IP-6 | WarmthMeter uses `intimacy`, not boss-specific warmth data |
| 7 | Pipeline Stages | WIRED | See IP-7 | All 9 stages present, conflict + life_sim properly ordered |
| 8 | Feature Flags | WIRED | See IP-8 | 3 flags: psyche, conflict temp, multi-phase boss; no life_sim flag |
| 9 | API Routes | WIRED | See IP-9 | Portal routes cover life-events, psyche-tips; task route for psyche-batch |
| 10 | Database Models | WIRED | See IP-10 | psyche_states table exists; conflict_details in user model |

---

## Detailed Findings

### IP-1: Psyche Agent <-> Life Sim [PARTIAL]

**What's wired:**
- `PsycheDeps` dataclass declares `life_events: list[dict]` and `npc_interactions: list[dict]` fields
  - `nikita/agents/psyche/deps.py:28-31`
- Psyche agent instructions reference life events and NPC interactions for state generation
  - `nikita/agents/psyche/agent.py:44-46` — "Life events affecting mood", "NPC interactions (Lena, Viktor, Yuki, therapist)"
- Agent `add_context` injects `deps.life_events` and `deps.npc_interactions` into prompt
  - `nikita/agents/psyche/agent.py:88-96`

**What's missing:**
- `_build_deps()` in batch.py initializes `life_events = []` and `npc_interactions = []` but **never populates them**
  - `nikita/agents/psyche/batch.py:130-131` — initialized as empty lists
  - `nikita/agents/psyche/batch.py:174-179` — passed as empty to PsycheDeps
- No code exists to load life events from `EventStore` or NPC data from `SocialCircleRepository`
- The agent CAN consume this data (deps + prompt reference it), but the batch orchestrator never feeds it

**Gap**: Psyche agent runs daily but receives zero life simulation context. NPC interactions are similarly absent. The integration surface exists but the data pipeline is incomplete.

---

### IP-2: Conflict System <-> Boss [WIRED]

**Evidence:**
- `BossPhaseState` persisted in `conflict_details.boss_phase` JSONB
  - `nikita/engine/chapters/boss.py:41-58` — BossPhaseState model
  - `nikita/engine/chapters/phase_manager.py:119-136` — `persist_phase()` writes to `conflict_details["boss_phase"]`
  - `nikita/engine/chapters/phase_manager.py:138-165` — `load_phase()` reads from `conflict_details["boss_phase"]`
- Message handler loads conflict_details, extracts boss_phase, manages lifecycle
  - `nikita/platforms/telegram/message_handler.py:997-1003` — loads conflict_details, calls `phase_mgr.load_phase()`
  - `nikita/platforms/telegram/message_handler.py:1025-1026` — clears boss_phase via `clear_boss_phase()`
  - `nikita/platforms/telegram/message_handler.py:1051-1052` — persists phase transitions
- Scoring service reads conflict_details for temperature-based scoring
  - `nikita/platforms/telegram/message_handler.py:545-555` — loads conflict_details for scoring
  - `nikita/platforms/telegram/message_handler.py:569` — passes to scoring service
  - `nikita/platforms/telegram/message_handler.py:577-585` — persists updated conflict_details after scoring

**Status**: Fully wired. Boss phases live inside conflict_details JSONB, with full read/write/clear lifecycle in the message handler.

---

### IP-3: Psyche <-> Prompt Caching [WIRED]

**Evidence:**
- PipelineContext has `psyche_state: dict | None` field
  - `nikita/pipeline/models.py:94-95`
- Prompt builder passes `psyche_state` to template vars
  - `nikita/pipeline/stages/prompt_builder.py:348` — `"psyche_state": ctx.psyche_state`
- Jinja2 template has Section 3.5 for psyche state injection
  - `nikita/pipeline/templates/system_prompt.j2:123-137` — "SECTION 3.5: PSYCHE STATE / L3"
  - Renders emotional_tone, behavioral_guidance, topics_to_encourage, topics_to_avoid
  - Conditional: renders only when `psyche_state` is truthy (zero tokens when None)
- Message handler injects psyche_state into text agent call
  - `nikita/platforms/telegram/message_handler.py:224-294` — pre-conversation psyche read
  - `nikita/platforms/telegram/message_handler.py:313` — passes `psyche_state=psyche_state_dict` to agent

**Status**: Fully wired end-to-end. Psyche state flows from DB -> message handler -> agent -> prompt template.

---

### IP-4: Life Sim <-> Portal [WIRED]

**Evidence:**
- API route: `GET /portal/life-events`
  - `nikita/api/routes/portal.py:615-658` — reads from `EventStore.get_events_for_date()`
  - Returns `LifeEventsResponse` with event items including emotional_impact, entities, narrative_arc_id
- Portal page: `Nikita's Day` page consumes life events
  - `portal/src/app/dashboard/nikita/day/page.tsx:4` — imports `useLifeEvents`
  - `portal/src/app/dashboard/nikita/day/page.tsx:34` — calls `useLifeEvents(dateStr)`
  - `portal/src/app/dashboard/nikita/day/page.tsx:83-93` — renders `LifeEventTimeline` component
- Date navigation with back/forward controls
  - `portal/src/app/dashboard/nikita/day/page.tsx:41-51` — goBack/goForward functions

**Status**: Fully wired. Life events flow from EventStore -> API -> frontend timeline.

---

### IP-5: Psyche <-> Portal [WIRED]

**Evidence:**
- API route: `GET /portal/psyche-tips`
  - `nikita/api/routes/portal.py:804-848` — reads from `PsycheStateRepository.get_current()`
  - Returns `PsycheTipsResponse` with attachment_style, defense_mode, behavioral_tips, etc.
  - Falls back to `PsycheState.default()` when no state exists
- Portal hook: `usePsycheTips`
  - `portal/src/hooks/use-psyche-tips.ts:6-13` — TanStack Query hook calling `portalApi.getPsycheTips`
- Portal page: renders psyche tips in day page
  - `portal/src/app/dashboard/nikita/day/page.tsx:7,12` — imports usePsycheTips and PsycheTips components
  - `portal/src/app/dashboard/nikita/day/page.tsx:96-102` — renders PsycheTips or PsycheTipsEmpty

**Status**: Fully wired. Psyche state flows from DB -> API -> frontend tips component.

---

### IP-6: Multi-Phase Boss <-> Portal [PARTIAL]

**What's wired:**
- `WarmthMeter` component exists and renders a warmth gauge
  - `portal/src/components/dashboard/warmth-meter.tsx:1-72` — horizontal gauge, Cold/Cool/Neutral/Warm/Hot labels
- Used on Nikita's Day page sidebar
  - `portal/src/app/dashboard/nikita/day/page.tsx:10` — imports WarmthMeter
  - `portal/src/app/dashboard/nikita/day/page.tsx:117-119` — renders `<WarmthMeter value={emotionalState.data.intimacy} />`

**What's missing:**
- WarmthMeter reads from `emotionalState.data.intimacy` (generic 4D emotional state), NOT from boss-specific warmth data
- No portal component displays boss phase state (OPENING vs RESOLUTION)
- No API route exposes current boss phase to the portal
- The `conflict_details.boss_phase` data (managed by BossPhaseManager) has no portal surface

**Gap**: WarmthMeter exists but shows generic intimacy, not boss encounter warmth/progress. Boss phase lifecycle (OPENING -> RESOLUTION) has no portal visibility.

---

### IP-7: Pipeline Stages [WIRED]

**Evidence:**
- 9 stages defined in correct order:
  - `nikita/pipeline/orchestrator.py:39-49`
  ```
  1. extraction     (CRITICAL)
  2. memory_update  (CRITICAL)
  3. life_sim       (non-critical)
  4. emotional      (non-critical)
  5. game_state     (non-critical)
  6. conflict       (non-critical)
  7. touchpoint     (non-critical)
  8. summary        (non-critical)
  9. prompt_builder (non-critical)
  ```
- Conflict stage (stage 6) supports both legacy enum and temperature mode
  - `nikita/pipeline/stages/conflict.py:41-53` — dispatches based on `is_conflict_temperature_enabled()`
  - Persists updated conflict_details back to DB: `nikita/pipeline/stages/conflict.py:148-156`
- Life sim stage (stage 3) reads/generates events
  - `nikita/pipeline/stages/life_sim.py:52-88` — reads today's events, falls back to generation
- Prompt builder stage (stage 9) includes psyche_state in template vars
  - `nikita/pipeline/stages/prompt_builder.py:348`

**Note**: No dedicated psyche stage in the pipeline. Psyche analysis happens pre-conversation in the message handler (inline), not as a pipeline stage. Pipeline only consumes psyche_state in the prompt builder via `ctx.psyche_state`.

**Status**: All 9 stages wired, conflict and life_sim properly integrated. Psyche is pre-conversation, not pipeline-staged (by design per Spec 056).

---

### IP-8: Feature Flags [WIRED]

**Evidence:**
- 3 feature flags defined in settings:
  1. `conflict_temperature_enabled` (Spec 057): `nikita/config/settings.py:145-147`
  2. `psyche_agent_enabled` (Spec 056): `nikita/config/settings.py:151-153`
  3. `multi_phase_boss_enabled` (Spec 058): `nikita/config/settings.py:161-163`
- Feature flag check functions:
  - `nikita/conflicts/__init__.py:77-84` — `is_conflict_temperature_enabled()`
  - `nikita/agents/psyche/__init__.py:12-20` — `is_psyche_agent_enabled()`
- All gated at entry points:
  - Psyche: batch job checks flag at `nikita/agents/psyche/batch.py:33-35`
  - Psyche: message handler checks flag at `nikita/platforms/telegram/message_handler.py:228`
  - Conflict temperature: ConflictStage checks at `nikita/pipeline/stages/conflict.py:48-53`
  - Conflict temperature: message handler scoring at `nikita/platforms/telegram/message_handler.py:548-549`

**Missing flag**: Life simulation has no dedicated feature flag. It runs unconditionally as pipeline stage 3 (non-critical, so failure is graceful).

**Status**: Core Wave A-B features properly flagged. Life sim relies on non-critical stage graceful degradation rather than an explicit flag.

---

### IP-9: API Routes [WIRED]

**Evidence:**
- Portal routes in `nikita/api/routes/portal.py`:
  - `GET /portal/life-events` (line 615) — life sim data
  - `GET /portal/psyche-tips` (line 804) — psyche tips
  - `GET /portal/emotional-state` (line 557) — 4D emotional state
  - `GET /portal/social-circle` (line 726) — NPC friend data
  - `GET /portal/narrative-arcs` (line 699) — story arcs
  - `GET /portal/thoughts` (line 661) — inner thoughts
- Task routes in `nikita/api/routes/tasks.py`:
  - `POST /tasks/psyche-batch` (line 796) — daily psyche generation
- Admin routes in `nikita/api/routes/admin.py` and `admin_debug.py`:
  - Admin debug includes conflict and scoring endpoints

**No dedicated routes for**: boss phase state (current phase, turn count, timeout status). Boss lifecycle is entirely in-band via Telegram message handler.

---

### IP-10: Database Models [WIRED]

**Evidence:**
- `PsycheStateRecord` model:
  - `nikita/db/models/psyche_state.py:19-64` — user_id (UNIQUE), state (JSONB), generated_at, model, token_count
  - Foreign key to users with CASCADE delete
- `conflict_details` on User model:
  - `nikita/db/models/user.py` — conflict_details JSONB column (stores temperature + boss_phase)
- Supporting models:
  - `nikita/db/models/social_circle.py` — NPC friend entities
  - `nikita/db/models/narrative_arc.py` — story arcs
  - `nikita/db/models/scheduled_event.py` — life sim events
  - `nikita/db/repositories/psyche_state_repository.py` — upsert, get_current, get_tier3_count_today

**Status**: All required models and repositories exist.

---

## Summary

```
INTEGRATION_MATRIX
├─ [WIRED] IP-2: Conflict <-> Boss (conflict_details.boss_phase JSONB lifecycle)
├─ [WIRED] IP-3: Psyche <-> Prompt Caching (L3 section 3.5 in system_prompt.j2)
├─ [WIRED] IP-4: Life Sim <-> Portal (API + timeline component)
├─ [WIRED] IP-5: Psyche <-> Portal (API + tips component)
├─ [WIRED] IP-7: Pipeline 9 Stages (all present, correct order)
├─ [WIRED] IP-8: Feature Flags (3 flags: psyche, conflict temp, multi-phase boss)
├─ [WIRED] IP-9: API Routes (life-events, psyche-tips, psyche-batch, emotional-state)
├─ [WIRED] IP-10: DB Models (psyche_states, conflict_details, social_circle, etc.)
├─ [PARTIAL] IP-1: Psyche <-> Life Sim (deps declared but batch never loads events/NPC)
└─ [PARTIAL] IP-6: Boss <-> Portal (WarmthMeter shows intimacy, not boss phase)
```

## Gaps Requiring Action

### GAP-1: Psyche Batch Missing Life Events + NPC Data [MEDIUM]
- **File**: `nikita/agents/psyche/batch.py:130-179`
- **Issue**: `_build_deps()` initializes `life_events=[]` and `npc_interactions=[]` but has no code to populate them from `EventStore` or `SocialCircleRepository`
- **Impact**: Psyche agent generates state without knowledge of Nikita's simulated life or NPC dynamics
- **Fix**: Add data loading blocks in `_build_deps()` similar to existing score_history and emotional_states patterns

### GAP-2: Boss Phase Has No Portal Surface [LOW]
- **File**: `portal/src/app/dashboard/nikita/day/page.tsx:117-119`
- **Issue**: WarmthMeter displays generic intimacy from emotional state, not boss-specific data. Boss phase lifecycle (OPENING/RESOLUTION/timeout) is invisible to portal users
- **Impact**: Portal users cannot see boss encounter progress or phase transitions
- **Fix**: Add API route for boss phase state and a portal component showing phase + turn count + timeout

### GAP-3: Life Sim Has No Feature Flag [LOW]
- **File**: `nikita/config/settings.py` — missing `life_sim_enabled` flag
- **Issue**: Life sim stage runs unconditionally. Graceful degradation via non-critical stage, but no toggle
- **Impact**: Cannot disable life sim independently without code change
- **Fix**: Add `life_sim_enabled` flag, check in LifeSimStage._run()
