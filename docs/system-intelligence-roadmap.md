# System Intelligence Roadmap — Audit-Driven Remediation

**Created**: 2026-02-23 | **Source**: System intelligence audit (3-agent team) | **Phase**: 7
**Status**: COMPLETE | **Specs**: 100-106 | **Waves**: H-K

---

## Gap Inventory

### Bugs (B1-B5) — Must Fix

| ID | Subsystem | Description | Severity | Spec | Status |
|----|-----------|-------------|----------|------|--------|
| B1 | Boss | PARTIAL outcome `cool_down_until` not persisted on User model | HIGH | 101 | RESOLVED |
| B2 | Cron | `detect-stuck` + `recover-stuck` are separate jobs doing overlapping work | MEDIUM | 100 | RESOLVED |
| B3 | Decay | Decay job lacks idempotency guard — double-fire applies double decay | HIGH | 100 | RESOLVED |
| B4 | Memory | `add_fact()` calls OpenAI embedding twice — once for the fact, once for `find_similar()` | MEDIUM | 102 | RESOLVED |
| B5 | Schema | Dead column `graphiti_group_id` still on user model (Neo4j remnant) | LOW | 105 | RESOLVED |

### Gaps (G1-G21) — Missing Functionality

| ID | Subsystem | Description | Spec | Status |
|----|-----------|-------------|------|--------|
| G1 | Game | `days_played` column never incremented — dead field | 101 | RESOLVED |
| G2 | Boss | PARTIAL cool_down enforcement missing in `should_trigger_boss()` | 101 | RESOLVED |
| G3 | Scoring | `users.relationship_score` can drift from `user_metrics` composite | 102 | RESOLVED |
| G4 | Decay | Ch1 decay (0.8/hr) punishes new players too harshly | 101 | RESOLVED |
| G5 | Cron | Decay job has no `job_executions` idempotency check | 100 | RESOLVED |
| G6 | Cron | `detect-stuck` and `recover-stuck` are redundant separate endpoints | 100 | RESOLVED |
| G7 | Touchpoints | `ctx.life_events` not wired to `MessageGenerator.generate()` | 103 | RESOLVED |
| G8 | Touchpoints | `PsycheState.defense_mode` not loaded into `StrategicSilence` | 103 | RESOLVED |
| G9 | Touchpoints | No dedup — can send near-identical proactive messages | 103 | RESOLVED |
| G10 | Schema | `graphiti_group_id` dead column (Neo4j migration remnant) | 105 | RESOLVED |
| G11 | Conflict | EXPLOSIVE state has no timeout — player stays trapped | 101 | RESOLVED |
| G12 | Memory | Embedding computed twice in `add_fact()` flow | 102 | RESOLVED |
| G13 | Memory | 3 sequential `search()` calls where 1 batched query suffices | 102 | RESOLVED |
| G14 | Agent | No semantic repetition penalty on Nikita responses | 101 | RESOLVED |
| G15 | Scoring | LLM scoring failure returns no fallback — silent zero | 105 | RESOLVED |
| G16 | Boss | Boss judgment prompt lacks vice profile + engagement context | 104 | RESOLVED |
| G17 | Portal | Vice discovery data exists but no player-facing visualization | 106 | RESOLVED |
| G18 | Pipeline | Extracted thoughts never auto-resolved when facts confirm them | 104 | RESOLVED |
| G19 | Game | Game status transitions have no audit trail | 105 | RESOLVED |
| G20 | Pipeline | `process-conversations` has no concurrency limiter | 100 | RESOLVED |
| G21 | DB | Missing composite index `(user_id, recorded_at DESC)` on `score_history` | 102 | RESOLVED |

### Improvements (I1-I18) — High-Leverage Enhancements

| ID | Subsystem | Description | Spec | Status |
|----|-----------|-------------|------|--------|
| I1 | Touchpoints | Inject open `conversation_threads` into touchpoint prompt | 103 | RESOLVED |
| I2 | Touchpoints | Wire `life_event_description` param in generator | 103 | RESOLVED |
| I3 | Touchpoints | Load `PsycheState` defense_mode + attachment into silence | 103 | RESOLVED |
| I4 | Touchpoints | Load top 2 vice categories into touchpoint message prompt | 103 | RESOLVED |
| I5 | Onboarding | Map `darkness_level` + `style` to initial vice weights | 104 | RESOLVED |
| I6 | Memory | Pre-computed embedding passed to `find_similar()` to avoid double-call | 102 | RESOLVED |
| I7 | Memory | Single `WHERE graph_type IN (...)` query replaces 3 sequential searches | 102 | RESOLVED |
| I8 | Decay | Decay-triggered warning touchpoints ("you've been quiet...") | 106 | RESOLVED |
| I9 | Agent | Skip rate feedback loop from engagement quality metric | 101 | RESOLVED |
| I10 | Pipeline | Inject active narrative arcs into daily summary prompt | 104 | RESOLVED |
| I11 | Pipeline | Cross-ref extracted facts against active thoughts (auto-resolve) | 104 | RESOLVED |
| I12 | Pipeline | Active "wants_to_share" thoughts as conversation openers | 104 | RESOLVED |
| I13 | Vice | Chapter-adaptive discovery sensitivity (1.5x early, 0.5x late) | 106 | RESOLVED |
| I14 | Voice | Cross-platform conversation continuity (voice summaries in text) | 106 | RESOLVED |
| I15 | Admin | Pipeline per-stage error tracking surfaced in admin dashboard | 100 | RESOLVED |
| I16 | Admin | Pipeline timing dashboard (per-stage durations + error rates) | 105 | RESOLVED |
| I17 | Conflict | Backstory-aware conflict detection (attachment_style in temp calc) | 104 | RESOLVED |
| I18 | Admin | Engagement analytics export (CSV/JSON for A/B testing) | 105 | RESOLVED |

---

## Spec Mapping

### Wave H — Foundation (Parallel)

**Spec 100: Cron Infrastructure Hardening** [Effort: M]
- B2/G6: Consolidate detect-stuck + recover-stuck → single `/tasks/recover`
- B3/G5: Decay idempotency guard via `job_executions`
- G20: process-conversations concurrency limiter (max 10, budget cap)
- I15: Pipeline per-stage error tracking → admin dashboard
- Key files: `nikita/api/routes/tasks.py`, `nikita/pipeline/orchestrator.py`

**Spec 102: Memory & Data Integrity** [Effort: M]
- B4/G12/I6: Fix embedding double-call — pass pre-computed to `find_similar()`
- G13/I7: Batch memory search — single `WHERE graph_type IN (...)`
- G3: Score reconciliation trigger
- G21: Composite index `(user_id, recorded_at DESC)` on `score_history`
- Key files: `nikita/memory/supabase_memory.py`, Supabase migration

### Wave I — Game Core (After Wave H, Parallel)

**Spec 101: Game Mechanics Remediation** [Effort: L]
- B1/G2: Persist boss PARTIAL `cool_down_until` + enforce in `should_trigger_boss()`
- G1: `days_played` — implement daily increment via decay job OR drop column
- G4: Rebalance Ch1 decay (invert grace: longest early, shortest late)
- G11: EXPLOSIVE conflict timeout-based de-escalation
- G14/I9: Semantic repetition penalty + skip rate feedback loop
- Key files: `nikita/engine/chapters/boss.py`, `nikita/engine/decay/calculator.py`, `nikita/engine/constants.py`

**Spec 103: Touchpoint Intelligence** [Effort: M]
- G7/I2: Wire `ctx.life_events` → `MessageGenerator.generate(life_event_description=...)`
- G8/I3: Load `PsycheState.defense_mode` + `attachment_activation` → `StrategicSilence`
- G9: Content dedup — track last 5 touchpoint hashes, skip if similar
- I1: Inject open `conversation_threads` into touchpoint generation prompt
- I4: Load top 2 vice categories into touchpoint message prompt
- Key files: `nikita/touchpoints/generator.py`, `nikita/touchpoints/engine.py`, `nikita/touchpoints/silence.py`

### Wave J — Enrichment (After Wave I, Parallel)

**Spec 104: Context Engineering Enrichment** [Effort: L]
- I5: Onboarding profile → vice seeding
- I10: Narrative arc refs in daily summaries
- I11/G18: Thought auto-resolution
- I12: Thought-driven conversation openers
- G16: Boss judgment + relationship context enrichment
- I17: Backstory-aware conflict detection
- Key files: `nikita/pipeline/stages/prompt_builder.py`, `nikita/pipeline/stages/summary.py`, `nikita/engine/chapters/judgment.py`

**Spec 105: Schema Cleanup & Observability** [Effort: M]
- B5/G10: Drop dead columns (`graphiti_group_id`; `days_played` per Spec 101 decision)
- G19: Game status transition audit trail → `audit_logs` table
- G15: LLM scoring fallback alerting (confidence=0.0, warning, error counter)
- I16: Pipeline timing admin dashboard
- I18: Engagement analytics export
- Key files: `nikita/db/models/user.py`, `nikita/engine/scoring/analyzer.py`, `portal/src/app/admin/pipeline/`

### Wave K — Experience (After Wave J, Sequential)

**Spec 106: Player-Facing Experience** [Effort: M]
- G17: Vice discovery player-facing portal insights
- I8: Decay-triggered warning touchpoints
- I14: Cross-platform conversation continuity
- I13: Chapter-adaptive vice discovery sensitivity
- Key files: `portal/src/app/(player)/vices/`, `nikita/engine/vice/discovery.py`

---

## Execution Schedule

```
WAVE H (Foundation) ─── Parallel
├─ Spec 100: Cron Infrastructure Hardening
└─ Spec 102: Memory & Data Integrity

WAVE I (Game Core) ─── Parallel (after Wave H)
├─ Spec 101: Game Mechanics Remediation
└─ Spec 103: Touchpoint Intelligence

WAVE J (Enrichment) ─── Parallel (after Wave I)
├─ Spec 104: Context Engineering Enrichment
└─ Spec 105: Schema Cleanup & Observability

WAVE K (Experience) ─── Sequential (after Wave J)
└─ Spec 106: Player-Facing Experience
```

## Completion Summary

**Completed**: 2026-02-23 | **Specs**: 100-106 + 070 all implemented and audited
**Bugs**: 5/5 resolved | **Gaps**: 21/21 resolved | **Improvements**: 18/18 resolved
**Total items**: 44/44 RESOLVED
**Tests added**: ~200 new tests across 7 specs
**Deployments**: Cloud Run rev nikita-api-00209-zf6, Vercel portal-iqdcswesd

## Verification Criteria

- Each spec passes 6-validator GATE 2 before planning
- Each spec passes `/audit` before implementation
- Each task passes TDD cycle (red → green → refactor)
- Full test suite green after each wave
- Portal builds clean after frontend-touching specs
