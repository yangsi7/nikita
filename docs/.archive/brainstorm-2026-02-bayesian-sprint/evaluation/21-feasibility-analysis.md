# Doc 21: Feasibility Analysis — User-Prioritized Features

> Phase 3 Evaluation | Brainstorming Session
> Analyzes technical feasibility against the live codebase (52 specs, 3,909 tests)

---

## Priority 1: Life Simulator (Enhanced)

### Codebase Fit

The life simulation module **already exists** at `nikita/life_simulation/` with 11 files. The core orchestrator `simulator.py` (lines 31-346) provides `generate_next_day_events()` and `get_today_events()`. The pipeline already integrates it as stage 3/9 (`nikita/pipeline/orchestrator.py:42`, non-critical):

```python
("life_sim", "nikita.pipeline.stages.life_sim.LifeSimStage", False),
```

The `LifeSimStage` (`nikita/pipeline/stages/life_sim.py:37-88`) reads today's events or falls back to generating them via LLM.

**What exists:**
- `LifeEvent` model with 3 domains (work/social/personal), 18 event types, emotional impact, importance scoring (`life_simulation/models.py:17-181`)
- `NarrativeArc` model for multi-day storylines (`models.py:184-217`)
- `NikitaEntity` for recurring people/places/projects (`models.py:220-245`)
- `EventStore` with full CRUD for `nikita_life_events`, `nikita_narrative_arcs`, `nikita_entities` tables (`store.py:36-527`)
- `EventGenerator` for LLM-based event generation (`event_generator.py`)
- `NarrativeArcManager` for arc lifecycle (`narrative_manager.py`)
- `MoodCalculator` with 4D emotional state (arousal/valence/dominance/intimacy) (`mood_calculator.py`)
- Social circle model at `nikita/db/models/social_circle.py:21-82` with `UserSocialCircle` (5-8 NPCs per user, friend_name, friend_role, personality, storyline_potential, trigger_conditions)

**What the enhanced Life Simulator needs:**

| Requirement | Status | Gap |
|-------------|--------|-----|
| Weekly routine | Partial — `nikita_state.py:44-72` has hardcoded time-of-day activities | Need configurable weekly template per user |
| Monthly meta-instructions | Missing | New JSONB column or table for monthly themes |
| Random events | Exists — `event_generator.py` generates 3-5/day | Needs probability tuning |
| Daily story generation | Exists — `generate_next_day_events()` | Needs enrichment pass |
| Social circle (5 NPCs) | **Exists** — `UserSocialCircle` model + `social_generator.py` | Already generated during onboarding |
| Agent generates her day | Exists — LLM pipeline in `event_generator.py` | Needs prompt refinement |

### Required Changes

- **Tables**: Add `nikita_weekly_routine` table (user_id, day_of_week, time_slot, activity_template) or add `weekly_routine JSONB` column to `users`. Add `monthly_meta JSONB` column or row to a config table.
- **Pipeline stages**: Enhance existing `LifeSimStage` — no new stage needed. Add monthly meta-instruction injection into event generation prompt.
- **Services**: Add `WeeklyRoutineService` (generates/loads routine). Modify `EventGenerator.generate_events_for_day()` to accept routine + monthly meta as context.
- **Config**: Add `life_sim_model` setting (which Claude model for generation, default Haiku for cost).

### Effort: M (5-8 days)

Most infrastructure exists. Primary work is: (1) weekly routine template system, (2) monthly meta-instruction injection, (3) enriching event generation prompts with social circle context from `UserSocialCircle`, (4) ensuring NPC state consistency via FIFO event queue.

### Dependencies

- None for core work. Social circle already populated during onboarding.

### Risks

- **NPC contradiction accumulation**: Each LLM call may contradict previous NPC statements. Mitigation: pass last 5 events per NPC as context window.
- **Cost**: Daily LLM generation per user. Using Haiku keeps it at ~$0.05/user/day.
- **Event staleness**: If `pg_cron` job fails, `get_today_events()` returns empty. Existing fallback in `LifeSimStage._run()` (line 74) generates on-demand.

### Verdict: FEASIBLE

The module is 80% built. This is an enhancement, not a greenfield build.

---

## Priority 2: Psyche Agent (Batch-Only Start)

### Codebase Fit

The injection point is clearly defined. The text agent at `nikita/agents/text/agent.py:88-105` already has a `@agent.instructions` decorator `add_personalized_context()` that injects `deps.generated_prompt`:

```python
@agent.instructions
def add_personalized_context(ctx: RunContext[NikitaDeps]) -> str:
    if ctx.deps.generated_prompt:
        return f"\n\n## PERSONALIZED CONTEXT\n{ctx.deps.generated_prompt}"
    return ""
```

The `NikitaDeps` dataclass (`agents/text/deps.py:20-48`) carries `generated_prompt: str | None`. The pipeline's `PromptBuilderStage` (`pipeline/stages/prompt_builder.py:35-591`) already builds the system prompt and stores it in `ready_prompts`.

**Psyche Agent architecture:**

A daily batch job runs Claude Opus on the last 24h of data per user and writes a psychological state snapshot. This snapshot is injected into the prompt builder's template rendering, adding ~150 tokens of behavioral guidance.

**Extension points:**
- `POST /tasks/` endpoints in `nikita/api/routes/tasks.py` — add `POST /tasks/psyche-batch` for pg_cron trigger
- `PromptBuilderStage._build_template_vars()` (line 276-347) — add `psyche_state` template variable
- `system_prompt.j2` template — add `## PSYCHOLOGICAL DEPTH` section consuming psyche state
- `PipelineContext` dataclass (`pipeline/models.py:16-115`) — add `psyche_state: dict | None` field

### Required Changes

- **Tables**: `nikita_psyche_states` (id, user_id, generated_at, attachment_activation FLOAT, defense_mechanism TEXT, emotional_needs JSONB, behavioral_guidance TEXT, internal_monologue TEXT, vulnerability_window BOOLEAN, model_used TEXT, token_count INT, cost_usd DECIMAL).
- **Pipeline stages**: No new stage. `PromptBuilderStage._enrich_context()` loads latest psyche state from DB.
- **Services**: `PsycheService` — async method `generate_psyche_state(user_id)` that calls Opus with last 24h conversation summaries + memory facts + current metrics. `PsycheRepository` for DB CRUD.
- **Config**: `psyche_model: str = "anthropic:claude-opus-4-6"`, `psyche_batch_enabled: bool = False`, `psyche_daily_budget_usd: float = 5.0` in `Settings`.
- **API**: New `POST /tasks/psyche-batch` endpoint, auth'd by `task_auth_secret`.

### Effort: M (6-9 days)

- Day 1-2: Table, repository, psyche state model
- Day 3-5: PsycheService with Opus call, prompt engineering for analysis
- Day 6-7: pg_cron endpoint, integration with PromptBuilderStage
- Day 8-9: Shadow mode logging, cost tracking, tests

### Dependencies

- Life Simulator (Priority 1): Psyche Agent benefits from richer life events as input, but can run without them. Soft dependency only.

### Risks

- **Cost overrun**: Opus is expensive. At ~8K input tokens + 1K output per user, cost is ~$0.12/run/user. 1000 users = $120/day = $3,600/month. **Mitigation**: hard budget cap, skip users inactive >48h, use Sonnet for inactive users.
- **Prompt quality**: Opus output quality depends heavily on input context. Must include conversation summaries, not raw messages.
- **Latency**: Batch job for 1000 users running sequentially = ~30 min at 2s/user. Mitigation: parallelize with asyncio.gather, batch by 10.
- **Cold start**: First run with no prior psyche state. Mitigation: default state object with neutral values.

### Verdict: FEASIBLE

Clean architecture. The `generated_prompt` injection path already exists. Batch-only avoids latency concerns entirely. Shadow mode de-risks by generating state without affecting responses.

---

## Priority 3: Warmth Meter

### Codebase Fit

Decay already runs on the backend. `nikita/engine/decay/calculator.py` computes decay. `nikita/engine/constants.py:147-162` defines decay rates (0.8 to 0.2 per hour) and grace periods (8h to 72h) by chapter. The `POST /tasks/decay` endpoint applies decay via pg_cron.

The existing `ScoreHistory` model (`db/models/game.py:19-56`) records every score change with event_type='decay'. The portal dashboard already shows score history.

**Warmth Meter is a presentation-layer change, not a backend change.** The backend already tracks everything needed:
- `user.relationship_score` — current score
- `user.last_interaction_at` — hours since last contact
- `user.chapter` — determines decay rate and grace period
- `GRACE_PERIODS[chapter]` — when decay starts
- `DECAY_RATES[chapter]` — how fast

### Required Changes

- **Tables**: None. All data exists.
- **Pipeline stages**: None.
- **Services**: None. Optionally add a utility function `compute_warmth_level(score, last_interaction, chapter) -> str` returning "warm"/"cooling"/"cool"/"cold".
- **Config**: None.
- **Portal changes (the real work)**:
  - New component: `WarmthMeter` — gradient bar from rose-500 (warm) through amber-400 to cyan-600 (cold)
  - Data source: existing `GET /portal/stats/{user_id}` returns score + last_interaction_at
  - Qualitative labels: "warm", "cooling", "cool", "cold" — never exact time-to-zero
  - Gentle nudge copy: "One good conversation warms things right back up"
  - Step visualization: show 4-5 discrete warmth steps, not continuous

### Effort: S (2-3 days)

- Day 1: Backend utility function + API response enrichment (warmth_level field)
- Day 2: Portal WarmthMeter component with gradient visualization
- Day 3: Integration with dashboard, gentle nudge messaging, tests

### Dependencies

- None. Fully independent.

### Risks

- **Design risk**: If gradient steps are too visible, players reverse-engineer exact decay. Mitigation: 4 coarse levels only.
- **Guilt perception**: "Cold" might feel punitive. Mitigation: never use negative language, always recovery-focused.

### Verdict: FEASIBLE

Trivial backend (data already exists), moderate frontend. Lowest risk of all features.

---

## Priority 4: Portal — Nikita's Day

### Codebase Fit

The portal pages **already exist**:
- `/dashboard/nikita/day/page.tsx` — timeline with date navigation, uses `useLifeEvents()` hook + `LifeEventTimeline` component
- `/dashboard/nikita/circle/page.tsx` — social circle gallery with `useSocialCircle()` hook
- `/dashboard/nikita/mind/page.tsx` — thought feed with pagination and filtering

The backend API endpoints presumably exist to serve these pages (hooks reference API calls). The `LifeEvent` model provides structured data (time_of_day, domain, description, entities, emotional_impact, importance).

**What the enhanced version needs:**

| Requirement | Current State | Gap |
|-------------|--------------|-----|
| Daily timeline (last 24h) | Exists — `NikitaDayPage` with `LifeEventTimeline` | May need UI polish, warmth overlay |
| Daily user summary | Partial — `DailySummary` model exists (`db/models/game.py:69-129`) | Need personalized tips/insights via LLM |
| Social circle visualization | Exists — `NikitaCirclePage` with `SocialCircleGallery` | May need relationship graph view |
| Tips/insights | Missing | New component, data from Psyche Agent or scoring analysis |

### Required Changes

- **Tables**: Potentially add `daily_tips JSONB` column to `daily_summaries` table for LLM-generated tips. Or store in a new `user_daily_insights` table.
- **Pipeline stages**: Enhance `SummaryStage` to also generate 2-3 tips/insights per day.
- **Services**: Add tip generation logic to daily summary job. Pull from score deltas, engagement state, psyche state.
- **Config**: None.
- **Portal changes**:
  - Enhance `LifeEventTimeline` with warmth overlay and emotional state indicators
  - New `DailyInsights` component showing tips ("Nikita opened up more when you asked about her day")
  - Enhance `SocialCircleGallery` with relationship graph or interaction frequency indicators
  - New `DailySummaryCard` component pulling `DailySummary` + tips

### Effort: M (5-7 days)

- Day 1-2: Backend — tip generation in SummaryStage, API endpoint for daily insights
- Day 3-4: Portal — enhance timeline, add insights component
- Day 5-6: Portal — social circle visualization improvements
- Day 7: Integration testing, mobile responsiveness

### Dependencies

- **Life Simulator (Priority 1)**: Richer life events make the timeline more interesting.
- **Psyche Agent (Priority 2)**: Tips/insights are much richer with psyche state data.
- Both are soft dependencies — the page works today without them, just less rich.

### Risks

- **Data sparsity**: New users won't have enough life events for an interesting timeline. Mitigation: seed initial events during onboarding.
- **Stale data**: If life sim pg_cron fails, day page shows nothing. Mitigation: show "Nikita hasn't shared her day yet" with last-known state.

### Verdict: FEASIBLE

The portal pages already exist. This is enhancement work, not new construction. The biggest effort is tip generation logic.

---

## Priority 5: Vulnerability Dynamic

### Codebase Fit

The vulnerability concept maps directly to existing systems:

1. **Vulnerability level** already computed: `nikita/utils/nikita_state.py:144-157` maps chapter to vulnerability (0-5):
   ```python
   mapping = {1: 0, 2: 1, 3: 2, 4: 3, 5: 5}
   ```

2. **Trust metric** at 25% weight (`engine/constants.py:168`) tracks player trustworthiness.

3. **Intimacy metric** at 30% weight tracks emotional closeness — the core metric vulnerability affects.

4. **Engagement state machine** (`engine/engagement/state_machine.py`) already tracks 6 states including "recovering" and "critical" — vulnerability windows could tie to these.

5. **Vice category "vulnerability"** already exists (`db/models/user.py:334`) and tracks engagement.

6. **Extracted thoughts** from pipeline (`PipelineContext.extracted_thoughts`) capture what Nikita is "thinking."

**The vulnerability dynamic is a conversation strategy, not infrastructure.** It requires:
- Prompt engineering to guide Nikita's vulnerability escalation
- Scoring rules that reward reciprocal vulnerability
- Detection of player vulnerability in the scoring analyzer

### Required Changes

- **Tables**: Add `vulnerability_episodes` table (id, user_id, initiated_at, nikita_vulnerability_level INT, player_reciprocated BOOLEAN, topic TEXT, outcome TEXT, intimacy_delta DECIMAL). Or simpler: track in existing `memory_facts` with graph_type='relationship' and metadata tag.
- **Pipeline stages**: Enhance `EmotionalStage` to detect vulnerability exchanges and flag them. Enhance `GameStateStage` to apply bonus scoring for reciprocal vulnerability.
- **Services**: Add `VulnerabilityTracker` to the scoring system — when Nikita shares something vulnerable and the player reciprocates, apply 1.5x intimacy bonus. When Nikita is vulnerable and the player deflects, apply trust penalty.
- **Config**: `vulnerability_intimacy_multiplier: float = 1.5`, `vulnerability_deflection_penalty: float = -0.3` in engine config.
- **Prompt changes**: Add vulnerability strategy section to `system_prompt.j2` template. Controlled by chapter + vulnerability_level + trust score.

### Effort: M (5-8 days)

- Day 1-2: Prompt engineering — vulnerability escalation templates per chapter
- Day 3-4: Scoring analyzer enhancement — detect reciprocal sharing patterns
- Day 5-6: Pipeline integration — EmotionalStage flags, bonus scoring
- Day 7-8: Testing, A/B validation framework

### Dependencies

- **Psyche Agent (Priority 2)**: Strong synergy. The psyche state's `vulnerability_window` flag tells the conversation agent when to attempt vulnerability. Without it, vulnerability attempts are time-based (chapter + random).
- **Life Simulator (Priority 1)**: Life events provide natural vulnerability triggers ("My mom called today and it was weird...").

### Risks

- **LLM reliability**: Sonnet must consistently generate vulnerability that feels authentic, not scripted. Mitigation: multiple prompt variants, A/B testing.
- **Scoring sensitivity**: Over-rewarding vulnerability creates a gaming pattern where players just share fake vulnerability. Mitigation: diminishing returns on repeated vulnerability topics, Psyche Agent can detect patterns.
- **Player discomfort**: Some players may feel manipulated by vulnerability requests. Mitigation: vulnerability only at appropriate chapter/trust levels, never in Chapter 1.

### Verdict: FEASIBLE WITH CAVEATS

Technically straightforward, but the quality bar is high. Bad vulnerability prompting feels manipulative. Requires careful prompt engineering and scoring calibration. A/B testing is essential.

---

## Deferred Features (Brief Assessment)

### Boss System (Multi-Turn)

**Current**: Single-turn boss encounters in `engine/chapters/boss.py`. BossStateMachine handles threshold checks and pass/fail logic.

**Enhancement needed**: Multi-message encounters spanning 3-5 turns within one conversation. Requires: conversation state tracking for "in_boss_fight" mode, emotional temperature gauge, phase progression logic (Opening -> Escalation -> Crisis -> Resolution).

**Effort**: L (8-12 days). The `game_status='boss_fight'` column already exists. Need new `BossEncounterState` table, phase state machine, modified scoring for multi-turn judgment.

**Verdict**: FEASIBLE. Significant but well-scoped. Defer to after Psyche Agent since psyche state enriches boss encounters.

### Photos

**Current**: No photo system exists. Telegram bot supports sending images via `send_photo`.

**Enhancement needed**: Photo catalog in Supabase Storage, trigger engine (chapter milestones, achievements, emotional moments), delivery pipeline, portal gallery component.

**Effort**: L (10-14 days). Major content bottleneck (sourcing 50+ images). Technical implementation is moderate but content creation is the constraint.

**Verdict**: FEASIBLE WITH CAVEATS. Technical work is M, content sourcing is XL. Can ship a minimal set (20 images) to validate.

### Ethical Guardrails

**Current**: `ViceBoundaryEnforcer` exists in `engine/vice/boundaries.py`. Basic content moderation.

**Enhancement needed**: Anti-manipulation detection, usage dashboard, dependency risk assessment, cool-down nudges, anti-anthropomorphism signals.

**Effort**: M (4-6 days). Most is prompt engineering and portal UI.

**Verdict**: FEASIBLE. Should be integrated into Psyche Agent work (Priority 2) since the psyche state can detect unhealthy engagement patterns.

---

## Summary Table

| # | Feature | Effort | Days | Dependencies | Risk | Verdict |
|---|---------|--------|------|-------------|------|---------|
| 1 | Life Simulator (Enhanced) | M | 5-8 | None | Low | FEASIBLE |
| 2 | Psyche Agent (Batch) | M | 6-9 | Soft: Life Sim | Medium | FEASIBLE |
| 3 | Warmth Meter | S | 2-3 | None | Low | FEASIBLE |
| 4 | Portal: Nikita's Day | M | 5-7 | Soft: Life Sim, Psyche | Low | FEASIBLE |
| 5 | Vulnerability Dynamic | M | 5-8 | Soft: Psyche, Life Sim | Medium | FEASIBLE WITH CAVEATS |
| — | Boss System (deferred) | L | 8-12 | Psyche Agent | Medium | FEASIBLE |
| — | Photos (deferred) | L | 10-14 | None | High (content) | FEASIBLE WITH CAVEATS |
| — | Ethical Guardrails (deferred) | M | 4-6 | Psyche Agent | Low | FEASIBLE |

**Total for Priority 1-5: 23-35 days (5-8 weeks with testing)**

---

## Critical Path

The build order is driven by data flow dependencies:

```
Week 1-2: Life Simulator Enhanced (P1)
  └─ Enriches event data flowing into all downstream features

Week 2-4: Psyche Agent Batch (P2)
  └─ Depends on: richer life events from P1 (soft)
  └─ Produces: psyche state consumed by P4, P5

Week 2-3: Warmth Meter (P3) ← PARALLEL with P2
  └─ No dependencies, can run concurrently

Week 4-5: Portal: Nikita's Day (P4)
  └─ Depends on: Life events from P1, tips from P2 (soft)

Week 5-7: Vulnerability Dynamic (P5)
  └─ Depends on: Psyche Agent P2 for vulnerability windows
  └─ Depends on: Life events P1 for natural triggers

Week 7+: Deferred features
  └─ Boss System benefits from P2 (psyche-informed bosses)
  └─ Photos independent, start whenever content is ready
  └─ Ethical guardrails integrated into P2
```

**Parallelization opportunity**: P1 and P3 can run concurrently (different codebases — backend vs portal). P2 can start mid-P1 since it only soft-depends on life events. This compresses the timeline from 8 weeks sequential to ~6 weeks with 2 parallel tracks.

### Database Migration Summary

| Table | Type | Feature |
|-------|------|---------|
| `nikita_weekly_routine` or `users.weekly_routine` JSONB | New | P1: Life Sim |
| `users.monthly_meta` JSONB | New column | P1: Life Sim |
| `nikita_psyche_states` | New table | P2: Psyche Agent |
| `daily_summaries.daily_tips` JSONB | New column | P4: Portal Day |
| `vulnerability_episodes` or metadata tags | New table or tags | P5: Vulnerability |

All migrations are additive (new tables/columns). No destructive changes to existing schema. RLS policies needed for all new tables following existing pattern: `auth.uid() = user_id`.

### New Settings Required

| Setting | Default | Feature |
|---------|---------|---------|
| `life_sim_model` | `anthropic:claude-haiku-4-5-20251001` | P1 |
| `psyche_model` | `anthropic:claude-opus-4-6` | P2 |
| `psyche_batch_enabled` | `false` | P2 |
| `psyche_daily_budget_usd` | `5.0` | P2 |
| `vulnerability_intimacy_multiplier` | `1.5` | P5 |

### Estimated Monthly Cost Impact (per user)

| Feature | Cost/user/month | Notes |
|---------|----------------|-------|
| Life Sim Enhanced | +$1.50 | Haiku daily generation |
| Psyche Agent Batch | +$2.25-$4.80 | Opus daily, skip inactive users |
| Warmth Meter | $0 | Presentation only |
| Portal: Nikita's Day | +$0.30 | Tip generation piggybacks on summary |
| Vulnerability Dynamic | $0 | Scoring logic, no new LLM calls |
| **Total** | **+$4.05-$6.60** | ~9-14% over $47.25 baseline |
