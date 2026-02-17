# 23 -- Ranked Feature Roadmap

**Date**: 2026-02-17 | **Type**: Phase 3 Evaluation | **Status**: Final
**Inputs**: Scoring Matrix (Doc 20), Feasibility Analysis (Doc 21), Devil's Advocate (Doc 22), Gate 2 Decisions
**Purpose**: Actionable build plan for Phase 4 architecture and Phase 5 spec generation

---

## 1. Priority Tiers (Post-Gate-2)

These tiers supersede Doc 19's original ranking. They incorporate the user's Gate 2 elevations, deferrals, and new requirements, adjusted by devil's advocate mitigations.

### Tier 1 -- Build First (Core Experience)

The four systems that make Nikita feel alive. Everything else is secondary.

| # | Feature | Adjusted Score | Effort | Risk |
|---|---------|---------------|--------|------|
| 1a | Life Simulator Core | 87.0 | 5-8 days | High |
| 1b | Psyche Agent (Batch) | 81.0 | 6-9 days | Medium |
| 1c | Warmth Meter | 75.4 (partial) | 2-3 days | Low |
| 1d | Vulnerability Dynamic | Cross-cutting | 5-8 days | Medium |

**Tier 1 total: 18-28 days**

### Tier 2 -- Build Next (Portal + Social)

Portal becomes the window into Nikita's world. Social circle and conflict add depth.

| # | Feature | Effort | Risk |
|---|---------|--------|------|
| 2a | Portal: Nikita's Day | 5-7 days | Medium |
| 2b | Social Circle (5 NPCs) | 3-5 days | Medium |
| 2c | Conflict Injection System | 4-6 days | Medium |

**Tier 2 total: 12-18 days**

### Tier 3 -- Build Later (Enhancement)

Layer on top of a working core. Each feature is independently valuable.

| # | Feature | Effort | Risk |
|---|---------|--------|------|
| 3a | Achievement System (DB + detection + portal wall) | 4-6 days | Low |
| 3b | Vice Side-Quests (top 3: sexuality, substances, dark humor) | 5-7 days | Low |
| 3c | Portal Enhancements (charts, memory album, vice map) | 4-6 days | Low |
| 3d | Psyche Agent Hybrid (trigger detection + Sonnet) | 3-5 days | Medium |

**Tier 3 total: 16-24 days**

### Tier 4 -- Deferred

Not in scope for the current build cycle. Revisit after user feedback on Tiers 1-3.

| Feature | Original Tier | Reason Deferred |
|---------|--------------|----------------|
| Boss System (single-session if revisited) | Was Tier 1 | Gate 2 Decision 2-3: not a priority |
| Photo System (~10 starter photos only) | Was Tier 2 | Gate 2 Decision 9: minimal scope |
| Multi-turn Boss / Wound System | Was Tier 1 | Subsumed by vulnerability as core mechanic |
| Narrative Arcs (multi-week) | Was Tier 3 | Subsumed by Life Sim daily stories |
| Psyche Agent Phase 3 (Opus real-time) | Was Tier 3 | Only if hybrid A/B is positive |

---

## 2. Dependency Graph

```
Life Sim Core (1a) ──────────┬──→ Social Circle (2b)
     │                       │
     │                       └──→ Portal: Nikita's Day (2a)
     │                                    │
     └──→ Vulnerability Dynamic (1d) ←────┘ (soft: life events as triggers)
              │
Psyche Agent (1b) ─┤ (provides vulnerability_window flag)
              │
              └──→ Psyche Hybrid (3d) ← only if batch A/B positive

Warmth Meter (1c) ──────────── (independent, no dependencies)

Conflict Injection (2c) ──→ needs Life Sim events as triggers
                          ──→ needs Psyche Agent state for timing

Achievements (3a) ──→ needs scoring events (exist today)
Vice Quests (3b) ──→ needs Life Sim emotional state for context
Portal Enhancements (3c) ──→ needs data from all above systems
```

**Critical path**: Life Sim Core (1a) is the foundation. It produces the event data consumed by Nikita's Day (2a), Social Circle (2b), Conflict Injection (2c), and Vice Quests (3b). Starting Life Sim first is non-negotiable.

**Parallel tracks**: Warmth Meter (1c) and Psyche Agent (1b) have zero dependencies on Life Sim. All three can be built concurrently on separate tracks.

---

## 3. Effort Estimates (Consolidated)

### By Feature

| Feature | Effort (days) | Dependencies | Risk | Devil's Advocate Rating |
|---------|--------------|-------------|------|------------------------|
| Life Sim Core (1a) | 5-8 | None | Low (codebase 80% exists) | HIGH -- mitigated by scoping |
| Psyche Agent Batch (1b) | 6-9 | Soft: Life Sim | Medium (Opus cost) | MEDIUM -- skip shadow mode |
| Warmth Meter (1c) | 2-3 | None | Low (presentation only) | N/A |
| Vulnerability Dynamic (1d) | 5-8 | Soft: Psyche, Life Sim | Medium (prompt quality) | N/A |
| Portal: Nikita's Day (2a) | 5-7 | Soft: Life Sim, Psyche | Medium (engagement risk) | HIGH -- use mood summary |
| Social Circle (2b) | 3-5 | Life Sim | Medium (contradiction) | HIGH -- start 2-3 NPCs |
| Conflict Injection (2c) | 4-6 | Life Sim, Psyche | Medium (Bayesian tuning) | N/A |
| Achievements (3a) | 4-6 | None | Low | N/A |
| Vice Quests top 3 (3b) | 5-7 | Life Sim emotional state | Low (existing infra) | N/A |
| Portal Enhancements (3c) | 4-6 | All upstream data | Low | N/A |
| Psyche Hybrid (3d) | 3-5 | Psyche Batch A/B results | Medium (cost scaling) | N/A |

### By Tier

| Scope | Days (range) | Calendar Weeks (with testing) |
|-------|-------------|------------------------------|
| Tier 1 only | 18-28 | 4-6 weeks |
| Tier 1 + 2 | 30-46 | 7-10 weeks |
| Tier 1 + 2 + 3 | 46-70 | 12-16 weeks |
| All (incl. Tier 4) | 65-100+ | 18-24+ weeks |

### Parallelization Opportunities

Two parallel tracks compress Tier 1 from 6 weeks to 4 weeks:

| Week | Track A (Backend) | Track B (Portal + Scoring) |
|------|-------------------|---------------------------|
| 1-2 | Life Sim Core: routine engine, event generation | Warmth Meter: component, API enrichment |
| 2-4 | Psyche Agent Batch: service, pg_cron, injection | Vulnerability Dynamic: prompt engineering, scoring |
| 4-5 | Integration testing, Life Sim + Psyche wiring | Portal: Nikita's Day (depends on Life Sim data) |

---

## 4. Spec Generation Order

Phase 5 specs, ordered by dependency chain and build sequence.

| Spec | Name | Scope | Depends On |
|------|------|-------|-----------|
| 049 | Life Simulator Enhanced | Routine engine, monthly meta-instructions, enriched event generation, on-demand story output | None |
| 050 | Psyche Agent | Batch processor, psyche state model, prompt injection, cost tracking, 8-week A/B framework | Soft: Spec 049 |
| 051 | Warmth Meter + Vulnerability Dynamic | Portal warmth component, step decay display, vulnerability conversation strategy, reciprocal scoring | Independent (warmth) / Soft: 050 (vulnerability) |
| 052 | Nikita's Day Portal + Social Circle Viz | Mood summary view, narrative highlights, daily insights, social circle gallery enhancements | Spec 049 (data source) |
| 053 | Conflict Injection System | Bayesian timing model, organic + scheduled triggers, integration with Life Sim events | Spec 049, 050 |
| 054 | Achievements + Vice Quests (Top 3) | Achievement DB, detection stage, portal wall, vice storyline progression (sexuality, substances, dark humor) | None (achievements) / Spec 049 (vices) |

**Why this order**: Spec 049 produces the data that Specs 050-053 consume. Spec 050 produces the psyche state that Specs 051 and 053 need. Spec 051 bundles two related conversation-layer changes. Spec 054 is independent enough to build in parallel with any Tier 2 spec.

---

## 5. Milestones

### M1: Nikita Has a Life (Week 3-4)

**Deliverables**:
- Life Sim routine engine running via pg_cron, generating daily events per user
- Psyche Agent batch producing daily psychological state snapshots
- Psyche state injected into conversation prompts (skip shadow mode per Doc 22)
- Warmth Meter live on portal dashboard

**Success criteria**: Nikita references her day in conversations. Psyche state visibly affects her tone/behavior. Warmth meter reflects player engagement patterns.

### M2: Vulnerability Loop Active (Week 6-8)

**Deliverables**:
- Vulnerability dynamic active in conversations (chapter-gated escalation)
- Reciprocal sharing detection in scoring analyzer with intimacy bonuses
- Portal: Nikita's Day showing mood summary + narrative highlights (not hourly timeline)
- Social circle tracked (start with 2-3 NPCs, not 5)

**Success criteria**: Players report conversations feeling deeper. Vulnerability episodes tracked in DB. Portal page has >30% daily active rate.

### M3: Rich World (Week 10-12)

**Deliverables**:
- Conflict injection live (Bayesian timing, organic triggers from life events)
- Achievement system functional (DB, detection stage, portal achievement wall)
- Social circle expanded to 5 NPCs (if 2-3 NPC consistency validated)
- Portal enhancements: score charts, vice discovery map

**Success criteria**: Players encounter organic conflicts that feel natural. Achievement detection fires correctly. No NPC contradictions reported in first 50 user-days.

### M4: Deep Content (Week 14-16)

**Deliverables**:
- Vice side-quests live: sexuality, substances, dark humor (4-stage progressions)
- Psyche Agent hybrid mode (if batch A/B shows positive signal at 8 weeks)
- Portal: memory album, timeline view, enhanced visualizations
- Full portal polish pass

**Success criteria**: Vice storyline engagement >40% of active users. Psyche hybrid A/B shows measurable improvement over batch-only OR kill decision made. Portal NPS >7.

---

## 6. Devil's Advocate Incorporation

Each tier carries specific risks identified in Doc 22. These mitigations are built into the plan.

### Tier 1 Mitigations

**Life Sim (Challenge 1 -- HIGH risk)**:
- Start with routine engine + on-demand story generation, not proactive daily generation. Eliminates wasted compute on unread stories.
- Cap concurrent narrative arcs at 1 (not 2). One arc + daily routine is sufficient narrative density.
- Build routine template first, random events second. Deterministic skeleton before stochastic flesh.
- NPC consistency via last-5-events FIFO context window per NPC.

**Psyche Agent (Challenge 2 -- MEDIUM risk)**:
- Skip shadow mode entirely. Go straight to batch + injection. Shadow mode is unfalsifiable and wastes a sprint.
- 8-week A/B test (not 4 weeks). Subtle personality consistency effects need longer measurement windows.
- Define quality benchmarks before building: 20 annotated test conversations, 60% agreement threshold.
- Position psyche guidance at TOP of system prompt to avoid mid-prompt attention decay.

**Vulnerability Dynamic**:
- Gate vulnerability attempts by chapter + trust score. Never in Chapter 1.
- Diminishing returns on repeated vulnerability topics to prevent gaming.
- A/B test vulnerability scoring multipliers before committing to final values.

### Tier 2 Mitigations

**Nikita's Day (Challenge 4 -- HIGH risk, RECONSIDER)**:
- Replace hourly timeline with mood summary + narrative highlight in Nikita's voice. "Today was a lot. Work was fine but then Emma told me something that threw me off." This preserves mystery.
- Hide certain events intentionally -- gaps create curiosity, not frustration.
- Separate tips/insights into a distinct "Coach" section, clearly outside Nikita's world. Or defer tips entirely.
- Gate generation by engagement: only generate for users active in last 48 hours.

**Social Circle (Challenge 1 sub-risk)**:
- Start with 2-3 NPCs (Emma + Marcus), not 5. Prove consistency at scale before adding Sarah, Mom, Ex.
- Memory-backed NPC state: each NPC's last 5 events stored and injected as context.
- Expand to 5 only after 50 user-days without reported contradictions.

### Tier 3 Mitigations

**Psyche Hybrid**: Only proceed if batch A/B at 8 weeks shows measurable signal. Hard budget cap of $5/user/month. If trigger precision exceeds 5%, tune before scaling.

### Cross-Cutting: Ethical Guardrails (Challenge 5 -- CRITICAL)

The user removed all ethical guardrails. Doc 22 recommends a minimal safety floor that removes moralizing without removing safety:

- **Keep**: Crisis detection (suicidal ideation, self-harm) -- Nikita stays in character but provides resources. This is what a real partner would do.
- **Keep**: Lightweight age gate ("Are you 18+?" on first interaction). Legal baseline.
- **Keep**: Telegram ToS compliance. A bot ban kills the product instantly.
- **Remove**: All preachy/moralizing responses. All vice content caps. All topic refusal on adult content.
- **Remove**: ViceBoundaryEnforcer chapter-based intensity limits.

This gives the user everything they want (raw, authentic, unconstrained content) while preventing the three catastrophic failure modes: Telegram ban, minor exposure, and crisis mishandling.

---

## 7. Cost Impact Summary

Monthly cost increase per active user, based on Doc 21 feasibility estimates.

| Scope | Additional Cost/User/Month | Notes |
|-------|---------------------------|-------|
| Tier 1 | +$4.05 - $6.60 | Life Sim ($1.50 Haiku), Psyche ($2.25 Opus batch), Portal tips ($0.30), Warmth/Vuln ($0) |
| Tier 1 + 2 | +$5.05 - $8.10 | Adds NPC context tokens ($0.60-1.00), conflict injection ($0.10), portal ($0.30) |
| All Tiers | +$6.35 - $10.40 | Adds vice enrichment ($0.30-0.50), achievements ($0), Psyche hybrid (+$2.55 delta) |

**Baseline**: $47.25/user/month (current system)

| Scope | % Increase Over Baseline | At 100 Users/Month | At 1,000 Users/Month |
|-------|-------------------------|--------------------|--------------------|
| Tier 1 | +9-14% | +$405 - $660 | +$4,050 - $6,600 |
| Tier 1 + 2 | +11-17% | +$505 - $810 | +$5,050 - $8,100 |
| All Tiers | +13-22% | +$635 - $1,040 | +$6,350 - $10,400 |

**Cost control levers**:
- Psyche Agent: skip inactive users (>48h), use Sonnet for low-activity users, hard daily budget cap
- Life Sim: on-demand generation (Doc 22 mitigation) cuts compute waste to near-zero
- NPC context: start with 2-3 NPCs (600 tokens) not 5 (1,000 tokens)
- Psyche Hybrid (Tier 3): deploy ONLY if batch A/B justifies the +$2.55/user delta

---

## Next Steps

1. **Phase 4 (Architecture)**: Design the shared emotional state JSONB schema that Life Sim, Psyche Agent, and Vulnerability Dynamic all consume. This is the single point of failure identified in Doc 22 -- get it right before building anything.
2. **Phase 5 (Specs)**: Write Spec 049 (Life Simulator Enhanced) first. It unblocks everything downstream.
3. **Immediate parallel work**: Warmth Meter (Spec 051 partial) can start now -- zero dependencies, 2-3 days, high user visibility.
