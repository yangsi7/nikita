# Nikita Next-Level Brainstorming — Master Index

## Event Timeline

| Date | Event | Outcome |
|------|-------|---------|
| 2026-02-16 AM | Phase 1: Research (12 agents) | 12 research documents (01-11) |
| 2026-02-16 PM | Phase 2: Ideation (8 agents) | 8 brainstorming documents (12-19) |
| 2026-02-16 PM | Gate 2 Audio Summary generated | `gate-2-review-audio-summary.md` |
| 2026-02-17 | User reviews Gate 2 audio | 13 decisions recorded via audio feedback |
| 2026-02-17 | **Gate 2 APPROVED** | Major reprioritization: Life Sim + Psyche Agent elevated, Boss + Photos deferred |
| 2026-02-17 | Phase 3: Evaluation (6 agents) | 5 evaluation documents (20-23 + gate-2-decisions) |
| 2026-02-17 | Gate 3 Audio Summary generated | `gate-3-review-audio-summary.md` |
| 2026-02-17 | User reviews Gate 3 audio | Conflict=CORE, psyche=cheap, simplify everything |
| 2026-02-17 | **Gate 3 APPROVED** | Critical overrides: paired agents, context modules, no over-engineering |
| 2026-02-17 | **Gate 4 COMPLETE** | System architecture diagram produced (doc 24) |

## Gate 2 Decision Log

| # | Decision | Verdict |
|---|----------|---------|
| 1 | Warmth Meter vs Visible Decay | **Warmth Meter APPROVED** — step decay, gentle nudges, no exact time-to-zero |
| 2 | Multi-turn Boss | **DEFERRED** — single-session (Option A) if revisited |
| 3 | Boss System Overall | **DEFERRED** — not priority |
| 4 | Psyche Agent | **HIGH PRIORITY** — batch-only start, hybrid later |
| 5 | Life Simulator | **ELEVATED #1** — weekly routine, meta-instructions, daily story, social circle |
| 6 | Portal: Nikita's Day | **NEW REQUIREMENT** — daily timeline, summary, tips |
| 7 | Social Circle | **IMPORTANT** — 5 NPCs, portal visualization, memory-backed |
| 8 | Portal Transparency | **HIGH** — engaging visuals, Nikita's Day as centerpiece |
| 9 | Photos | **DEFERRED** — ~10 starter photos only |
| 10 | Ethical Guardrails | **REMOVED** — prototype, no guardrails |
| 11 | Conflict Frequency | **Organic + Scheduled** — Bayesian randomness with mean conflict time |
| 12 | Vice Content | **Top 3** — sex and drugs welcomed, go raw |
| 13 | Emotional Vulnerability | **CRITICAL** — mutual vulnerability IS the retention mechanic |

> **Authoritative decisions document**: [`evaluation/gate-2-decisions.md`](evaluation/gate-2-decisions.md) — supersedes priority tiers from doc 19.

---

## Phase 1: Research & Context — COMPLETE

| # | Document | Status | Summary |
|---|----------|--------|---------|
| 01 | [Game Progression Design](research/01-game-progression.md) | COMPLETE | S-curve XP, 5 achievement types, daily/weekly loops, streak mechanics, collection system, gacha-inspired memory drops |
| 02 | [Gamification Frameworks](research/02-gamification-frameworks.md) | COMPLETE | Octalysis audit: 60% Black Hat overreliance; Hook Model triggers; SDT autonomy/competence/relatedness; Flow channel |
| 03 | [Attachment Psychology](research/03-attachment-psychology.md) | COMPLETE | Bowlby 4 styles, Gottman 4 horsemen, anxious-avoidant dynamics, defense mechanisms; **prevalence figures need correction** |
| 04 | [Companion & Dating Sim Design](research/04-companion-design.md) | COMPLETE | Replika/DDLC/Persona analysis; market gap: "only AI companion where you can fail"; retention; monetization ethics |
| 05 | [Character Building & Narrative](research/05-character-building.md) | COMPLETE | Id/Ego/Superego modeling, parasocial calibration (lambda=0.5), backstory pacing, discovery-as-reward, NPC depth |
| 06 | [Life Simulation Mechanics](research/06-life-simulation.md) | COMPLETE | 10 design principles; "check in and see what happened" pattern; flexible modes (Quick/Daily/Deep); circadian modeling |
| 07 | [Engagement UX & Dashboard](research/07-engagement-ux.md) | COMPLETE | 10 portal UX principles; F-pattern layout; real-time freshness; narrative metrics; anti-patterns (info dump, empty states) |
| 08 | [Multi-Agent Cognitive Architecture](research/08-cognitive-architecture.md) | COMPLETE | ACT-R/SOAR/dual-process; Psyche Agent architecture; 3 trigger tiers; cost model ($21.50/user/mo); prompt caching strategy |
| 09 | [Fact-Check & Critique](research/09-fact-check-critique.md) | COMPLETE | 3 major contradictions; 24 challenged claims; 8 research gaps; 4 ethical flags; confidence ratings A/B per doc |
| 10 | [System Analysis (ToT)](research/10-system-analysis-tot.md) | COMPLETE | Full architecture tree; data flow map; 5 leverage points; 5 constraints; extension point templates with code |
| 10b | [Library Docs Audit](research/10b-library-docs-audit.md) | COMPLETE | Latest docs: Pydantic AI, LangGraph 0.3.6, Claude API (prompt caching), Supabase Realtime, Next.js 16, ElevenLabs |
| 11 | [Idea Document Synthesis](research/11-idea-document-synthesis.md) | COMPLETE | 6 idea docs analyzed; 14 already implemented; 15 aspirational; 10 gap areas; top 5 high-impact features ranked |

## Phase 2: Brainstorm & Ideate — COMPLETE

| # | Document | Status | Summary |
|---|----------|--------|---------|
| 12 | [Progression & Achievements](ideas/12-progression-achievements.md) | COMPLETE | 40+ achievements, 4 rarity tiers, organic daily goals, 4 streak options evaluated (warmth meter recommended), decay as gentle nudge |
| 13 | [Life Simulation Enhanced](ideas/13-life-simulation-enhanced.md) | COMPLETE | 4D emotional state → life events, psychology discovery system, 5 NPCs, narrative arcs, circadian modeling |
| 14 | [Boss/Conflict Redesign](ideas/14-boss-conflict-redesign.md) | COMPLETE | Multi-phase bosses (5 attachment-driven types), defense mechanisms, wound system, conflict injection with ethics guardrails |
| 15 | [Psyche Agent Architecture](ideas/15-psyche-agent-architecture.md) | COMPLETE | 3 options (batch/real-time/hybrid), hybrid recommended at +$4.80/user/mo, 3-tier triggers, phased rollout |
| 16 | [Portal Game Dashboard](ideas/16-portal-game-dashboard.md) | COMPLETE | 10 dashboard sections, ASCII wireframes, F-pattern layout, Supabase Realtime strategy, 4-sprint migration |
| 17 | [Vice Side-Quests](ideas/17-vice-sidequests.md) | COMPLETE | Vice discovery exploration, 8 per-category storylines, vice×chapter matrix, boss variants, pipeline integration |
| 18 | [Photo/Media System](ideas/18-photo-media-system.md) | COMPLETE | 5 trigger types, ~210 photos, Telegram/portal delivery, photo×vice×chapter matrix, variable reinforcement |
| 19 | [Cross-Expert Synthesis](ideas/19-cross-expert-synthesis.md) | COMPLETE | Synergy matrix, 4 conflicts resolved, integrated feature map, dependency graph, +$5.92-7.22/mo cost, 4 priority tiers |

## Phase 3: Evaluate & Score — COMPLETE

| # | Document | Status | Summary |
|---|----------|--------|---------|
| G2 | [Gate 2 Decisions](evaluation/gate-2-decisions.md) | COMPLETE | 13 user decisions, priority shift from doc 19 tiers, new Tier 1: Life Sim + Psyche Agent |
| 20 | [Scoring Matrix](evaluation/20-scoring-matrix.md) | COMPLETE | 8×8 scoring with user-priority multipliers; Life Sim #1 (87.0), Psyche Agent #2 (81.0), Vice Quests #3 (76.7) |
| 21 | [Feasibility Analysis](evaluation/21-feasibility-analysis.md) | COMPLETE | All 5 priorities FEASIBLE; Life Sim has 11 existing files; total 23-35 days; +$4-7/user/mo |
| 22 | [Devil's Advocate](evaluation/22-devils-advocate.md) | COMPLETE | 5 challenges: Life Sim complexity (HIGH), Psyche meta-hallucination (MEDIUM), Nikita's Day as surveillance (HIGH), guardrails removal (CRITICAL) |
| 23 | [Ranked Feature Roadmap](evaluation/23-ranked-feature-roadmap.md) | COMPLETE | 4 tiers, 6 specs (049-054), 4 milestones, Tier 1 = 4-6 weeks, all tiers = 12-16 weeks |

## Phase 4: Propose & Architect — IN PROGRESS

| # | Document | Status | Summary |
|---|----------|--------|---------|
| 24 | [System Architecture Diagram](proposal/24-system-architecture-diagram.md) | COMPLETE | Full system diagram, 5 context modules, paired agents, conflict CORE, DB changes, cost profile |
| 25 | [Architecture Proposal](proposal/25-architecture-proposal.md) | BLOCKED | |
| 26 | [Portal Design Proposal](proposal/26-portal-design-proposal.md) | BLOCKED | |
| 27 | [Psyche Agent Proposal](proposal/27-psyche-agent-proposal.md) | BLOCKED | |
| 28 | [Database Schema Changes](proposal/28-database-schema-changes.md) | BLOCKED | |
| 29 | [Effort & Cost Estimate](proposal/29-effort-cost-estimate.md) | BLOCKED | |

---

## Gate Audio Summaries (TTS-friendly reviews)

| Gate | File | Purpose |
|------|------|---------|
| Gate 2 | [gate-2-review-audio-summary.md](gate-2-review-audio-summary.md) | Full Phase 1+2 walkthrough, 10 decisions for user |
| Gate 3 | [gate-3-review-audio-summary.md](gate-3-review-audio-summary.md) | Phase 3 evaluation results, roadmap, 5 decisions for user |

---

## Relevance Ranking (for next agent)

**Read first** (most current/authoritative):
1. `evaluation/gate-2-decisions.md` — supersedes doc 19 priority tiers
2. `evaluation/23-ranked-feature-roadmap.md` — authoritative roadmap with spec order
3. `evaluation/21-feasibility-analysis.md` — codebase evidence for all priorities

**Read for depth**:
4. `evaluation/20-scoring-matrix.md` — weighted scoring with rationale
5. `evaluation/22-devils-advocate.md` — risk mitigations to incorporate
6. `ideas/13-life-simulation-enhanced.md` — base Life Sim proposal (user wants MORE)
7. `ideas/15-psyche-agent-architecture.md` — Psyche Agent options (user chose batch-first)

**Partially superseded**:
8. `ideas/19-cross-expert-synthesis.md` — priority tiers superseded by gate-2-decisions; integration analysis still valid

**Deferred (skip unless revisiting)**:
- `ideas/14-boss-conflict-redesign.md` — boss system deferred
- `ideas/18-photo-media-system.md` — photo system deferred

---

**Current Phase**: 4 — IN PROGRESS
**Gate Status**: **GATE 3 APPROVED** — User reviewed, provided critical overrides. **GATE 4 COMPLETE** — Architecture diagram produced.
**Next Action**: User validates architecture diagram (doc 24) → proceed to Gate 5 (Implementation Spec → Spec 049) (Life Sim)

---

## Bayesian Inference Research (future roadmap)

> **Status**: Research complete, not for current implementation cycle.
> **Location**: [`bayesian-inference/`](bayesian-inference/00-research-index.md) (27 documents, ~27K lines)
>
> Explores replacing LLM-based scoring with zero-token Bayesian inference (Beta distributions, Thompson Sampling, DBNs). This is a **long-term optimization** — much later in the roadmap after the current brainstorming features are implemented.
