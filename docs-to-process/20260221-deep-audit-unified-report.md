# Deep Project Audit — Vision vs Implementation

**Date**: 2026-02-21
**Scope**: All 63 specs, Gate 4.5 risks, cross-system integration, vision coverage
**Method**: 4-agent parallel audit team (sdd-compliance, gate45-risk-verifier, integration-auditor, vision-gap-analyzer)

---

## Executive Summary

| Dimension | Score | Detail |
|-----------|-------|--------|
| SDD Compliance | 84.2% | 48/57 specs compliant, 7 non-compliant (3 need full SDD) |
| Gate 4.5 Risk Resolution | 50% fully resolved | 8 RESOLVED, 4 PARTIAL, **2 CRITICAL OPEN**, 2 N/A |
| Cross-System Integration | 80% fully wired | 8 WIRED, 2 PARTIAL |
| Vision Coverage | 94% | 15/18 FULLY, 2 PARTIAL, 1 SUPERSEDED |

**Bottom line**: Implementation is strong (94% vision coverage, solid integration), but **2 CRITICAL unresolved risks** (prompt truncation no-op, no per-user locking) need immediate attention before production scaling. SDD artifacts need cleanup for 7 specs.

---

## CRITICAL Findings (Fix Before Production)

### CRIT-1: Prompt Truncation Is a No-Op (SR-10)

`prompt_builder.py:470-473` searches for `"## 11. VICE SHAPING"` etc., but rendered Jinja2 output uses `**What Makes You Light Up (Vice Profile):**` — headers never match, `_remove_section()` always returns -1. Only blunt hard-truncate fires.

**Impact**: Intelligent prompt truncation never happens. When prompts exceed token budget, the system does a dumb cut instead of removing low-priority sections.

**Fix**: Update section headers to match rendered template output. Add integration test with real rendered template.

**File**: `nikita/pipeline/stages/prompt_builder.py:470-473`

### CRIT-2: No Per-User Locking (SR-11)

Zero concurrency control in `message_handler.py`. No `SELECT FOR UPDATE`, no `asyncio.Lock` per user_id. Concurrent messages can cause double boss triggers, temperature race conditions, corrupt `boss_phase` state.

**Impact**: Multi-phase boss (Spec 058) is vulnerable to state corruption under concurrent messages.

**Fix**: Add `SELECT ... FOR UPDATE` on user row or Supabase advisory locks (`pg_advisory_xact_lock`).

**File**: `nikita/platforms/telegram/message_handler.py`

---

## HIGH Priority Findings

### HIGH-1: Skip Rates Disabled (Vision Gap)

`nikita/agents/text/skip.py:17-23` — All skip rates set to 0.00. Chapter 1 should skip 25-40% of messages for "Am I worth her time?" tension. Currently Nikita responds 100%.

### HIGH-2: Psyche Batch Missing Life Events (Integration Gap)

`nikita/agents/psyche/batch.py:130-179` — `_build_deps()` initializes `life_events=[]` and `npc_interactions=[]` but never populates them. Psyche agent generates state without life simulation context.

### HIGH-3: SDD Artifacts Missing for 3 Wave D Specs

Specs 061, 062, 063 have spec.md only — missing plan.md, tasks.md, audit-report.md. Full SDD bypass during Wave D implementation.

---

## MEDIUM Priority Findings

### MED-1: Boss Phase Timeout (SR-14 PARTIAL)

24h timeout covers entire multi-phase encounter with no reset on phase advance. Player responding after 20h leaves only 4h for RESOLUTION phase.

### MED-2: Conversation Context Splits (SR-16 PARTIAL)

Boss judgment is protected via `phase_state.conversation_history`, but conversation DB records may split between phases, confusing pipeline post-processing.

### MED-3: Memory Callback Rate Not Enforced (Vision Gap)

Vision: 2-3 natural memory references per week. Infrastructure exists but rate is emergent (LLM choice), not scheduled.

### MED-4: Boss Phase Has No Portal Surface (Integration Gap)

WarmthMeter shows generic intimacy, not boss phase progress. OPENING/RESOLUTION lifecycle invisible to portal users.

### MED-5: Master Plan Stale

`plans/master-plan.md` references Neo4j/Graphiti (replaced by SupabaseMemory), aiogram (actual: python-telegram-bot), says `specs_complete: 52` (actual: 63).

---

## LOW Priority Findings

### LOW-1: Life Sim Missing Feature Flag (Integration Gap)

No `life_sim_enabled` flag — relies on non-critical stage graceful degradation.

### LOW-2: Legacy Conflict Module Still Imported (SR-12 PARTIAL)

Pipeline conflict stage has BOTH old (`emotional_state.conflict`) and new (`conflicts.temperature`) behind feature flag. Legacy path still active when flag is OFF.

### LOW-3: pgVector Storage Concern (SR-09 PARTIAL)

No halfvec/float16 reduction implemented. Current scale is tiny (~14 memory facts). Future concern only.

---

## SDD Compliance Matrix

| Tier | Specs | Action | Effort |
|------|-------|--------|--------|
| Quick Fix | 056, 059 | Generate audit-report.md only | 25 min |
| Legacy Exempt | 049, 050 | Mark as pre-SDD in tracking | 5 min |
| Full SDD | 061, 062, 063 | Generate plan.md + tasks.md | 2-3 hrs |

**Immediate cleanup**:
- Delete empty orphan `specs/057-conflict-core/`
- Spec 045 (prompt-unification): no directory exists, no git history — mark as legacy pre-SDD
- Specs 051-054: intentionally unassigned numbers (Wave B restructuring)

---

## Gate 4.5 Risk Heat Map

```
CRITICAL [MUST FIX]
├─ SR-10 [OPEN]  Prompt truncation no-op — headers don't match template
└─ SR-11 [OPEN]  No per-user locking — race conditions in scoring

HIGH [SHOULD FIX]
├─ SR-01 [RESOLVED]  Decay notification — wired
├─ SR-02 [RESOLVED]  NPC fabrication — corrected
├─ SR-03 [RESOLVED]  Zero tests — 10 tests added
├─ SR-08 [RESOLVED]  Pydantic AI API — all output_type
├─ SR-15 [RESOLVED]  Voice agent — working
├─ SR-09 [PARTIAL]   pgVector storage — low scale OK
├─ SR-12 [PARTIAL]   Wrong conflict module — flag-gated
├─ SR-14 [PARTIAL]   Boss timeout — no phase reset
└─ SR-16 [PARTIAL]   Context splits — judgment protected, pipeline not

MEDIUM/LOW [RESOLVED OR N/A]
├─ SR-04 [N/A]       Pipeline stages — observation only
├─ SR-05 [RESOLVED]  Arc table naming — same table
├─ SR-06 [RESOLVED]  Test count — acknowledged
├─ SR-07 [RESOLVED]  pg_cron count — corrected
└─ SR-13 [N/A]       Engagement FSM — by design
```

---

## Integration Matrix

```
INTEGRATION_STATUS
├─ [WIRED] Conflict <-> Boss (conflict_details.boss_phase JSONB)
├─ [WIRED] Psyche <-> Prompt Caching (L3 section 3.5)
├─ [WIRED] Life Sim <-> Portal (API + timeline)
├─ [WIRED] Psyche <-> Portal (API + tips)
├─ [WIRED] Pipeline 9 Stages (correct order)
├─ [WIRED] Feature Flags (3: psyche, conflict temp, multi-phase boss)
├─ [WIRED] API Routes (life-events, psyche-tips, psyche-batch)
├─ [WIRED] DB Models (psyche_states, conflict_details, social_circle)
├─ [PARTIAL] Psyche <-> Life Sim (deps declared, batch never loads)
└─ [PARTIAL] Boss <-> Portal (WarmthMeter = generic intimacy)
```

---

## Vision Coverage Scorecard

```
VISION_COVERAGE [94%]
├─ [FULLY: 15/18]
│  ├─ Proactive Initiation    ├─ Vice System
│  ├─ Life Simulation         ├─ Conflict System
│  ├─ Darkness Levels         ├─ Multi-Phase Boss
│  ├─ Meta-Nikita Onboarding  ├─ Psyche System
│  ├─ Strategic Silence        ├─ Decay System
│  ├─ Social Circle / NPC     ├─ Chapter Progression
│  ├─ Behavioral Meta-Instr   ├─ Portal Dashboard
│  └─ Emotional State Engine  └─ Persona Adaptation
├─ [PARTIAL: 2/18]
│  ├─ Skip Rates [DISABLED — all 0.00, undermines Ch1]
│  └─ Memory Callback Rate [no enforcement, emergent only]
└─ [SUPERSEDED: 1/18]
   └─ Three Persona Types → Single Nikita + PersonaAdaptationService
```

---

## Prioritized Remediation Plan

### Priority 1: Critical Risk Resolution
| # | Task | File | Effort |
|---|------|------|--------|
| R-1 | Fix prompt section headers to match rendered template | `prompt_builder.py:470-473` | 1 hr |
| R-2 | Add per-user locking in message handler | `message_handler.py` | 2 hrs |

### Priority 2: High-Impact Gaps
| # | Task | File | Effort |
|---|------|------|--------|
| R-3 | Re-enable chapter-based skip rates | `skip.py:17-23` | 30 min |
| R-4 | Wire life events + NPC data into psyche batch | `batch.py:130-179` | 1 hr |
| R-5 | Generate plan.md + tasks.md for specs 061-063 | `specs/061-063/` | 2-3 hrs |

### Priority 3: Medium Cleanup
| # | Task | File | Effort |
|---|------|------|--------|
| R-6 | Add phase-specific timeout reset in boss | `phase_manager.py` | 1 hr |
| R-7 | Mark boss conversations to prevent context splits | `message_handler.py` | 30 min |
| R-8 | Update master-plan.md (Neo4j→pgVector, spec count) | `master-plan.md` | 1 hr |
| R-9 | Generate audit-report.md for specs 056, 059 | `specs/056,059/` | 25 min |

### Priority 4: Housekeeping
| # | Task | File | Effort |
|---|------|------|--------|
| R-10 | Delete empty `specs/057-conflict-core/` | filesystem | 1 min |
| R-11 | Mark specs 045, 049, 050 as legacy pre-SDD | `master-todo.md` | 5 min |
| R-12 | Fix master-todo test count (1248 → actual) | `master-todo.md` | 5 min |
| R-13 | Add life_sim feature flag | `settings.py` | 15 min |

**Total estimated remediation**: ~10-12 hours

---

## Source Reports

| Report | File |
|--------|------|
| SDD Compliance | `docs-to-process/20260221-audit-sdd-compliance.md` |
| Gate 4.5 Risks | `docs-to-process/20260221-audit-gate45-risks.md` |
| Integration Matrix | `docs-to-process/20260221-audit-integration.md` |
| Vision Gaps | `docs-to-process/20260221-audit-vision-gaps.md` |

---

*Generated by nikita-deep-audit team | 2026-02-21*
