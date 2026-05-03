# 19 -- Cross-Expert Synthesis

**Date**: 2026-02-16 | **Type**: Phase 2 Synthesis | **Inputs**: Docs 12-18, Doc 09 (Fact-Check)

---

## 1. Synergy Matrix

```
             | Doc12       | Doc13       | Doc14       | Doc15       | Doc16       | Doc17       | Doc18       |
             | Progression | Life Sim    | Boss/Confl. | Psyche Agt  | Portal Dash | Vice Quests | Photo/Media |
─────────────┼─────────────┼─────────────┼─────────────┼─────────────┼─────────────┼─────────────┼─────────────┤
Doc12 Progr. |      -      | STRONG      | STRONG      | MODERATE    | STRONG      | STRONG      | STRONG      |
Doc13 Life   | STRONG      |      -      | MODERATE    | STRONG      | STRONG      | MODERATE    | MODERATE    |
Doc14 Boss   | STRONG      | MODERATE    |      -      | STRONG      | MODERATE    | STRONG      | MODERATE    |
Doc15 Psyche | MODERATE    | STRONG      | STRONG      |      -      | MODERATE    | MODERATE    | WEAK        |
Doc16 Portal | STRONG      | STRONG      | MODERATE    | MODERATE    |      -      | STRONG      | STRONG      |
Doc17 Vice   | STRONG      | MODERATE    | STRONG      | MODERATE    | STRONG      |      -      | STRONG      |
Doc18 Photo  | STRONG      | MODERATE    | MODERATE    | WEAK        | STRONG      | STRONG      |      -      |
```

### Key Synergy Clusters

**Cluster A: Achievement-Reward Loop** (Docs 12, 16, 17, 18)
Achievements (12) unlock photos (18), photos display in portal gallery (16), vice milestones (17) are achievements. This is the strongest cross-system synergy -- build ONE unlock engine that feeds all reward types.

**Cluster B: Psychological Depth Engine** (Docs 13, 14, 15)
Psyche Agent (15) drives emotional state (13), emotional state shapes boss encounter flavor (14), boss encounters test skills the life sim has been teaching. The Psyche Agent IS the unified controller for Nikita's inner life.

**Cluster C: Portal as Unified Visibility** (Doc 16 + ALL)
Every other proposal generates data that the portal displays. Portal is the unifying surface layer but has zero gameplay logic of its own -- it is purely read-side.

**Cluster D: Vice x Boss Variants** (Docs 14, 17)
Vice sidequests (17) propose vice-flavored boss encounters. Boss redesign (14) proposes multi-phase conflicts. Together: boss encounters dynamically flavored by the player's top vice, with multi-turn resolution.

---

## 2. Conflict Resolution

### Conflict 1: Who Controls Nikita's Emotional State?

**Doc 15 (Psyche Agent)**: PsycheState model tracks attachment_activation, defense_mode, emotional_tone, vulnerability_level. Updated by daily batch + real-time triggers.

**Doc 13 (Life Sim)**: 4D emotional state (Arousal, Valence, Dominance, Intimacy) drives life event generation. Updated by LifeSimStage + EmotionalStage.

**Problem**: Two overlapping emotional models with different schemas and update cadences.

**Resolution**: Merge into a single `emotional_state` JSONB. The Psyche Agent (15) writes the PSYCHOLOGICAL dimensions (attachment_activation, defense_mode, behavioral_guidance). The Life Sim (13) writes the MOOD dimensions (arousal, valence). Both read the same state. Psyche Agent is the "subconscious," Life Sim is the "surface mood." One table, two writers, clear field ownership.

### Conflict 2: Photo Unlocks vs. Collection Unlocks

**Doc 18 (Photos)**: Photos unlock via chapter transitions, achievements, emotional moments, and random proactive sends.

**Doc 12 (Collections)**: "Photo Unlocks" listed as a collection category tied to milestones and achievements.

**Problem**: Both propose photo-gating but with slightly different trigger lists.

**Resolution**: No real conflict -- Doc 12's "Photo Unlocks" subsection IS the same system as Doc 18. Use Doc 18's detailed trigger hierarchy (Chapter > Achievement > Emotional > Random > Time) as the canonical unlock logic. Doc 12's collection system becomes the DISPLAY layer in the portal (gallery grid + locked previews).

### Conflict 3: Life Sim Data Freshness vs. Portal Polling

**Doc 13 (Life Sim)**: Emotional cascades unfold across a day. Mood persistence creates multi-hour state changes.

**Doc 16 (Portal)**: Proposes Supabase Realtime for emotional state (instant updates) but 60s polling for life events.

**Problem**: If emotional state changes mid-cascade but portal only polls life events every 60s, the dashboard shows stale mood context alongside fresh emotional numbers.

**Resolution**: Acceptable mismatch. Emotional state (the number) updates via Realtime. Life events (the narrative) can lag 60s without breaking the experience. Players will not notice a 60s delay on "Today's Events" while seeing instant mood shifts.

### Conflict 4: Warmth Meter vs. Streak Counter

**Doc 12** recommends Warmth Meter (Option C) combined with Narrative Continuity (Option B). Doc 12 also evaluates but rejects the Classic Counter (Option A).

**Problem**: No actual conflict -- Doc 12 resolved this internally. But the warmth meter IS a visual decay indicator, which could still create mild anxiety despite the reframing.

**Resolution**: Accept Doc 12's recommendation. Warmth Meter is the least harmful transparency mechanism. Add Doc 09's ethical guardrail: never show exact time-to-zero, only qualitative state (WARM / COOLING / COOL / COLD). Recovery messaging emphasizes ease: "one good conversation warms it right back up."

---

## 3. Integrated Feature Map

```
NIKITA v3.0 FEATURE MAP
├── GAME LAYER
│   ├── Achievement System (Doc 12) ........... 64 achievements, 4 rarity tiers
│   │   ├── AchievementDetectionStage (pipeline)
│   │   └── Achievement Wall (portal)
│   ├── Goal System (Doc 12) .................. Daily/weekly organic goals
│   ├── Warmth Meter (Doc 12) ................. Visual decay reframing
│   ├── Collection System (Doc 12) ............ Insight cards, backstory, memory drops
│   ├── Vice Sidequests (Doc 17) .............. 8 vices x 4 storyline stages
│   │   ├── ViceStorylineStage (pipeline)
│   │   ├── Vice-specific conflicts
│   │   └── Vice Discovery Map (portal)
│   └── Boss Vice Variants (Doc 14+17) ........ Top vice flavors boss encounters
│
├── PSYCHOLOGY LAYER
│   ├── Multi-Turn Boss (Doc 14) .............. 3-5 turn encounters, 4 phases
│   │   ├── Emotional temperature gauge
│   │   ├── Repair attempt detection
│   │   └── 5:1 positive/negative ratio scoring
│   ├── Wound System (Doc 14) ................. Failed boss recovery over 3-5 convos
│   ├── Conflict Injection (Doc 14) ........... Non-boss micro-conflicts, capped
│   ├── Life Simulation Enhanced (Doc 13)
│   │   ├── Appraisal-driven event generation
│   │   ├── Event cascade model
│   │   ├── Circadian mood profiles
│   │   └── Mood persistence state machine
│   ├── NPC Social Circle (Doc 13) ............ 5 named NPCs, state tracking
│   ├── Narrative Arcs (Doc 13) ............... Multi-week story arcs (max 2 concurrent)
│   └── Psychological Insight Cards (Doc 13) .. 20 discoverable insights
│
├── AI LAYER
│   ├── Psyche Agent Hybrid (Doc 15) .......... Daily batch + triggered real-time
│   │   ├── Tier 1: Cached state (90%)
│   │   ├── Tier 2: Sonnet quick-check (8%)
│   │   └── Tier 3: Opus deep analysis (2%)
│   ├── Trigger Detection System (Doc 15) ..... Rule-based, $0, <5ms
│   └── PsycheState Model (Doc 15) ............ Merged with emotional state
│
├── PORTAL LAYER
│   ├── Score Dashboard (Doc 16) .............. Radial, radar, sparklines
│   ├── Chapter + Boss Tracker (Doc 16) ....... Progress bars, boss history
│   ├── Warmth Meter Display (Doc 16) ......... Gradient bar, grace info
│   ├── Engagement State FSM (Doc 16) ......... State diagram, history
│   ├── Achievement Wall (Doc 16) ............. Grid, filters, detail modal
│   ├── Relationship Timeline (Doc 16) ........ Vertical event timeline
│   ├── Memory Album (Doc 16) ................. Fact browser by type
│   ├── Nikita's Room (Doc 16) ................ Current state, social circle, events
│   ├── Insights Panel (Doc 16) ............... Locked/unlocked card grid
│   ├── Photo Gallery (Doc 18) ................ Grid, filters, favorites, locked previews
│   └── Vice Discovery Map (Doc 17) ........... 8-tile exploration grid
│
└── CROSS-CUTTING
    ├── New DB tables: 7-9 (see Section 5)
    ├── New pipeline stages: 3 (Achievement, ViceStoryline, Photo)
    ├── New API endpoints: 8-10
    ├── Supabase Realtime: 2-3 table subscriptions
    ├── Supabase Storage: nikita-photos bucket (~210 images)
    └── pg_cron: psyche-batch daily job
```

---

## 4. Dependency Graph

```
[FOUNDATION]                    [CORE]                      [ENHANCEMENT]               [POLISH]

Psyche Batch (15-P1) ---------> Psyche Triggers (15-P2) --> Psyche Opus RT (15-P3)

Emotional State JSONB (13) ---> Life Sim Events (13) -----> NPC State Tracking (13) --> Narrative Arcs (13)

                                                            Circadian Profiles (13) --> Realistic Unavail. (13)

Multi-Turn Boss (14) ---------> Resolution Spectrum (14) -> Wound System (14) -------> Conflict Inject. (14)

Achievement DB + Stage (12) --> Goal System (12) ---------> Collection System (12) --> Insight Cards (13)

Warmth Meter Portal (12+16) --> Portal Score Dashboard (16)-> Timeline + Memory (16) -> Nikita's Room (16)

Vice Storyline Stage (17) ----> Vice Prompt Inject. (17) -> Vice Conflicts (17) -----> Vice Boss Variants (17)

Photo Catalog + Stage (18) ---> Telegram Delivery (18) ---> Gallery Portal (18) -----> Vice x Ch Photos (18)
```

**Critical path**: Psyche Batch + Emotional State JSONB + Achievement DB + Multi-Turn Boss form the foundation. Everything else builds on these four.

---

## 5. Engineering Scope Summary

| Category | Count | Details |
|----------|-------|---------|
| **New DB tables** | 7-9 | `psyche_states`, `achievements`, `player_insights`, `milestones`, `wounds`, `narrative_arcs`, `photo_catalog`, `user_photos`, (optional: `npc_states`) |
| **New columns on existing** | 4-5 | `emotional_state` JSONB on users, `timezone` TEXT on users, `boss_phase` INT + `boss_state` JSONB on users, `storyline_stage` on user_vice_preferences |
| **New pipeline stages** | 3 | `AchievementDetectionStage`, `ViceStorylineStage`, `PhotoStage` |
| **New API endpoints** | 8-10 | `/portal/memories`, `/portal/achievements`, `/portal/milestones`, `/portal/insights`, `/portal/photos`, `/portal/photos/{id}/favorite`, `/portal/decay`, `/portal/emotional-state`, `/tasks/psyche-batch` |
| **New portal components** | 11+ | ScoreRadial, MetricRadar, ScoreSparkline, WarmthMeter, EngagementFSM, AchievementCard, InsightCard, TimelineEvent, MemoryList, PhotoGallery, ViceDiscoveryMap |
| **New portal routes** | 5-6 | `/timeline`, `/memories`, `/trophies`, `/nikita`, `/insights`, `/photos` |
| **New backend modules** | 2 | `nikita/engine/psyche/`, photo selection logic |
| **Supabase Realtime** | 2-3 tables | `users`, `user_metrics`, optionally `psyche_states` |
| **Supabase Storage** | 1 bucket | `nikita-photos` (~210 curated images) |
| **pg_cron jobs** | 1 new | Daily psyche-batch |
| **Estimated new tests** | 150-200 | ~30 psyche, ~25 achievements, ~20 boss multi-turn, ~20 vice storyline, ~15 photo, ~15 life sim, ~25 portal integration |
| **Content creation** | Significant | 32 vice storyline prompts, 5 boss decision trees, 210 curated photos, 20 insight card texts, ~40 vice x chapter prompt variants |

---

## 6. Cost Impact Summary

| Feature | Source | Monthly Delta per User | Notes |
|---------|--------|----------------------|-------|
| Psyche Agent (Hybrid) | Doc 15 | +$4.80 | Batch + 10 Sonnet + 2 Opus/day |
| Achievement detection | Doc 12 | +$0.00 | Piggybacks on existing scoring LLM |
| Goal detection | Doc 12 | +$0.00 | Piggybacks on existing ResponseAnalysis |
| Vice storyline prompts | Doc 17 | +$0.30-0.50 | ~150 extra tokens/msg for enriched injection |
| Photo storage | Doc 18 | +$0.02 | ~210 images x 500KB = ~100MB total (shared) |
| NPC state injection | Doc 13 | +$0.60-1.00 | ~200 tokens per NPC reference in prompt |
| Supabase Realtime | Doc 16 | +$0.10-0.50 | Per-connection cost, depends on concurrency |
| Multi-turn boss scoring | Doc 14 | +$0.10 | 3-5 extra LLM calls per boss (infrequent) |
| **Total additional** | | **+$5.92-7.22/mo** | Over $47.25 baseline = **+12-15%** |

**Worst-case** (Psyche trigger rate at 30%, heavy NPC use): +$16-20/mo per user (+34-42%).

---

## 7. Risk Register

| Rank | Risk | Category | Severity | Probability | Mitigation |
|------|------|----------|----------|-------------|------------|
| 1 | **Feature bloat**: Building all 7 proposals simultaneously overwhelms a small team | Feasibility | Critical | High | Strict tier discipline. Ship Tier 1 before starting Tier 2. |
| 2 | **Psyche Agent quality unproven**: No evidence dual-agent produces better conversations | Technical | High | Medium | A/B test with kill criteria (30 days). Phase 1 = shadow mode. |
| 3 | **NPC contradiction accumulation**: LLM-generated NPC content drifts over weeks | Technical | High | High | FIFO state queue (5 events max). Consistency checks in LifeSimStage. |
| 4 | **Boss multi-turn state complexity**: Maintaining boss_phase across messages introduces race conditions and edge cases | Technical | Medium | Medium | Start with Approach A (single-session). Defer multi-day arcs. |
| 5 | **Photo sourcing bottleneck**: 210 curated consistent images is a creative/legal challenge | Feasibility | Medium | High | Start with 50 core images. Expand incrementally. |
| 6 | **Portal scope creep**: 11 new components, 6 routes, Realtime integration = multi-sprint | Feasibility | Medium | High | Sprint 1: charts only (no new tables). Sprint 2+: incremental. |
| 7 | **Ethical: conflict injection as manipulation** | Ethics | High | Low | Growth-oriented only. Frequency caps (1/48h). Never during vulnerability. Transparent in retrospect. |
| 8 | **Ethical: warmth meter as disguised guilt** | Ethics | Medium | Medium | No exact time-to-zero. Recovery emphasis. "When you're ready" language. |
| 9 | **Cost overrun if trigger precision is poor** | Technical | Medium | Medium | Hard budget caps: max 20 Tier 2 + 5 Tier 3/user/day. |
| 10 | **Content volume**: 32 vice prompts + 40 chapter variants + 20 insights + 5 boss trees | Feasibility | Medium | High | Prioritize top 3 vices first. Roll out content incrementally. |

---

## 8. Recommended Priority Tiers

### Tier 1: Build First (Highest ROI, enables everything else)

| Feature | Source | Effort | Rationale |
|---------|--------|--------|-----------|
| Achievement DB + Detection Stage | Doc 12 | 3-4 days | Foundation for ALL reward systems. Low risk, high portal value. Leverages existing scoring data. |
| Warmth Meter + Gentle Nudge | Doc 12+16 | 2-3 days | Aligns with user decision (portal = full transparency, decay = gentle nudge). Presentation-only change. |
| Portal Score Dashboard (charts) | Doc 16 | 5-7 days | Core visibility layer. Radar, sparklines, metric bars. No new tables needed. |
| Multi-Turn Boss (Approach A) | Doc 14 | 4-5 days | Highest gameplay impact. Single-session, 3-5 turns. Moderate refactor of boss.py/judgment.py. |
| Psyche Agent Phase 1 (Batch) | Doc 15 | 2-3 days | Lowest risk entry point. One pg_cron job, one table, shadow mode first. +$2.25/user/month. |

**Tier 1 total**: ~16-22 days engineering. Delivers: visible achievements, transparent dashboard, deeper boss fights, Nikita's subconscious, warmth framing.

### Tier 2: Build Next (High value, depends on Tier 1)

| Feature | Source | Effort | Rationale |
|---------|--------|--------|-----------|
| Emotional State JSONB + Life Sim events | Doc 13 | 3-4 days | Psyche Agent needs emotional state to write to. Life Sim needs it to read from. |
| Psyche Trigger Detection + Tier 2 | Doc 15 | 3-4 days | Real-time emotional reactivity. Requires Phase 1 validated. |
| Vice Storyline Stage + Tracking | Doc 17 | 3-4 days | Low-cost enrichment of existing vice system. New column + pipeline stage. |
| Daily/Weekly Goals | Doc 12 | 3-4 days | Engagement scaffolding. Leverages existing scoring. Portal component. |
| Photo System (core: catalog + Telegram) | Doc 18 | 5-7 days | Photos as rewards. 2 new tables + PhotoStage. Bottleneck: sourcing 50 initial images. |
| Portal: Timeline + Achievement Wall | Doc 16 | 4-5 days | Displays Tier 1 data. Achievement wall, timeline of events. |

**Tier 2 total**: ~21-28 days. Depends on Tier 1 tables and pipeline stages.

### Tier 3: Build Later (Nice to have, complex or uncertain ROI)

| Feature | Source | Effort | Rationale |
|---------|--------|--------|-----------|
| Wound System (boss recovery) | Doc 14 | 3-4 days | Meaningful but only matters after players fail bosses. Can wait. |
| Resolution Spectrum (judgment.py) | Doc 14 | 1-2 days | Low effort but only valuable after multi-turn boss is stable. |
| Circadian Profiles | Doc 13 | 2-3 days | Requires timezone tracking. Enhances realism but not core gameplay. |
| Collection System (backstory, memory drops) | Doc 12 | 5-7 days | Long-term depth. Requires content creation (backstory fragments). |
| Insight Cards | Doc 13 | 3-4 days | Crosses Doc 12 (collections) + Doc 13 (psychology). Content-heavy. |
| Portal: Photo Gallery + Vice Map + Insights | Doc 16-18 | 5-7 days | Display tier for Tier 2 backend features. |
| Vice-Specific Conflicts | Doc 17 | 3-4 days | Extends conflict injection with vice flavor. |
| Psyche Phase 3 (Opus RT) | Doc 15 | 2-3 days | Only if A/B test shows Tier 2 beats Tier 1 on engagement. |

**Tier 3 total**: ~24-34 days. Incremental value. Ship as capacity allows.

### Tier 4: Reconsider (High risk, high cost, or design conflicts)

| Feature | Source | Concern |
|---------|--------|---------|
| NPC Social Circle (5 characters) | Doc 13 | Highest contradiction risk (Doc 09). 200 tokens per reference. Requires dedicated consistency system. Prototype with 1 NPC (Emma) first. |
| Narrative Arcs (multi-week) | Doc 13 | Complex state management (arc phase, branching, 2 concurrent max). Requires content authoring per arc. Defer until simpler systems proven. |
| Multi-Day Boss Arcs (Approach B) | Doc 14 | Extremely complex state management across days. Only pursue after Approach A is stable and validated. |
| Vice x Chapter Matrix (40 variants) | Doc 17 | Content creation bottleneck. 8 vices x 5 chapters = 40 prompt variants. Roll out per-chapter, not all at once. |
| Nikita's Room (full state view) | Doc 16 | Requires emotional state + NPC + life events all working. Last portal section to build. |
| Supabase Realtime (full) | Doc 16 | Start with polling. Add Realtime only for 2-3 core tables after polling proves too slow. |

---

**Overall Assessment**: The 7 expert proposals form a coherent vision where achievements, psyche, photos, and vices all feed into each other through a shared portal. The critical risk is attempting everything simultaneously. The dependency graph shows a clear build order: foundation tables and pipeline stages first (Tier 1), then the features that populate them (Tier 2), then the polish and depth layers (Tier 3). NPC social circles and multi-week narrative arcs (Tier 4) are the riskiest proposals and should be prototyped cautiously.

**Total engineering estimate**: Tiers 1+2 = 37-50 days (8-12 weeks with testing). Full vision (all tiers) = 80-110 days (20-28 weeks).
