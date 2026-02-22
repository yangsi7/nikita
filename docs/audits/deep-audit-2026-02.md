# Deep Audit — Vision vs Implementation

**Date**: 2026-02-21
**Scope**: All 63 specs, Gate 4.5 risks, cross-system integration, vision coverage
**Method**: 4-agent parallel audit team (sdd-compliance, gate45-risk-verifier, integration-auditor, vision-gap-analyzer)
**Source files**: Processed from `docs-to-process/` on 2026-02-22

---

## Executive Summary

| Dimension | Score | Detail |
|-----------|-------|--------|
| SDD Compliance | 84.2% | 48/57 specs compliant, 7 non-compliant (3 need full SDD) |
| Gate 4.5 Risk Resolution | 50% fully resolved | 8 RESOLVED, 4 PARTIAL, **2 CRITICAL OPEN**, 2 N/A |
| Cross-System Integration | 80% fully wired | 8 WIRED, 2 PARTIAL |
| Vision Coverage | 94% | 15/18 FULLY, 2 PARTIAL, 1 SUPERSEDED |

**Bottom line**: Implementation is strong (94% vision coverage, solid integration), but **2 CRITICAL unresolved risks** need immediate attention before production scaling. SDD artifacts need cleanup for 7 specs.

---

## CRITICAL Findings (Fix Before Production)

### CRIT-1: Prompt Truncation Is a No-Op (SR-10)

`nikita/pipeline/stages/prompt_builder.py:470-473` searches for `"## 11. VICE SHAPING"` etc., but rendered Jinja2 output uses `**What Makes You Light Up (Vice Profile):**` — headers never match, `_remove_section()` always returns -1. Only blunt hard-truncate fires.

**Fix**: Update section headers to match rendered template output:
```python
sections_to_remove = [
    "**What Makes You Light Up (Vice Profile):**",
    "**Chapter ",  # partial match for "**Chapter N Behavior Guide:**"
    "**Psychological Reality:**",
]
```
Add integration test with real rendered template.

### CRIT-2: No Per-User Locking (SR-11)

Zero concurrency control in `nikita/platforms/telegram/message_handler.py`. No `SELECT FOR UPDATE`, no `asyncio.Lock` per user_id. Concurrent messages can cause double boss triggers, temperature race conditions, corrupt `boss_phase` state.

**Fix**: Add `SELECT ... FOR UPDATE` on user row or Supabase advisory locks (`pg_advisory_xact_lock`). Option 2/3 recommended for Cloud Run (multiple instances possible).

---

## HIGH Priority Findings

### HIGH-1: Skip Rates Disabled

`nikita/agents/text/skip.py:17-23` — All skip rates set to 0.00. Chapter 1 should skip 25-40% of messages. Currently Nikita responds 100%.

### HIGH-2: Psyche Batch Missing Life Events

`nikita/agents/psyche/batch.py:130-179` — `_build_deps()` initializes `life_events=[]` and `npc_interactions=[]` but never populates them. Psyche agent runs daily with zero life simulation context.

### HIGH-3: SDD Artifacts Missing for 3 Wave D Specs

Specs 061, 062, 063 have spec.md only — missing plan.md, tasks.md, audit-report.md.

---

## MEDIUM Priority Findings

### MED-1: Boss Phase Timeout (SR-14 PARTIAL)

`nikita/engine/chapters/phase_manager.py:20` — 24h timeout for entire multi-phase encounter, no reset on phase advance. Player responding after 20h leaves only 4h for RESOLUTION phase.

### MED-2: Conversation Context Splits (SR-16 PARTIAL)

Boss judgment is protected via `phase_state.conversation_history`, but conversation DB records may split between phases, confusing pipeline post-processing. Fix: mark boss conversations with `is_boss_fight=True`.

### MED-3: Memory Callback Rate Not Enforced

Vision: 2-3 natural memory references per week. Infrastructure exists but rate is emergent (LLM choice), not scheduled.

### MED-4: Boss Phase Has No Portal Surface

WarmthMeter shows generic intimacy, not boss phase progress. OPENING/RESOLUTION lifecycle invisible to portal users.

### MED-5: Master Plan Stale

`plans/master-plan.md` references Neo4j/Graphiti (replaced by SupabaseMemory), aiogram (actual: python-telegram-bot), says `specs_complete: 52` (actual: 63).

---

## LOW Priority Findings

### LOW-1: Life Sim Missing Feature Flag

No `life_sim_enabled` flag — relies on non-critical stage graceful degradation.

### LOW-2: Legacy Conflict Module Still Imported (SR-12 PARTIAL)

Pipeline conflict stage has BOTH old (`emotional_state.conflict`) and new (`conflicts.temperature`) behind feature flag. Legacy path still active when flag is OFF.

### LOW-3: pgVector Storage Concern (SR-09 PARTIAL)

No halfvec/float16 reduction implemented. Current scale is tiny (~14 memory facts). Future concern only.

---

## Gate 4.5 Risk Heat Map

```
CRITICAL [MUST FIX]
├─ SR-10 [OPEN]  Prompt truncation no-op — prompt_builder.py:470-473 headers don't match rendered template
└─ SR-11 [OPEN]  No per-user locking — message_handler.py has zero concurrency control

HIGH [RESOLVED/PARTIAL]
├─ SR-01 [RESOLVED]  Decay notification — wired at tasks.py:246
├─ SR-02 [RESOLVED]  NPC fabrication — corrected in npc-character-map.md
├─ SR-03 [RESOLVED]  Zero tests — test_spec_049.py has 10 tests
├─ SR-08 [RESOLVED]  Pydantic AI API — all code uses output_type
├─ SR-15 [RESOLVED]  Voice agent — working, imports stable APIs
├─ SR-09 [PARTIAL]   pgVector storage — no halfvec yet, low scale OK
├─ SR-12 [PARTIAL]   Wrong conflict module — flag-gated, both paths work
├─ SR-14 [PARTIAL]   Boss timeout — 24h for full encounter, no phase reset
└─ SR-16 [PARTIAL]   Context splits — boss judgment protected, pipeline not

MEDIUM/LOW [RESOLVED OR N/A]
├─ SR-04 [N/A]       Pipeline stages — observation only
├─ SR-05 [RESOLVED]  Arc table naming — same table
├─ SR-06 [RESOLVED]  Test count — acknowledged
├─ SR-07 [RESOLVED]  pg_cron count — corrected to 9
└─ SR-13 [N/A]       Engagement FSM — by design
```

---

## Integration Matrix

```
INTEGRATION_STATUS
├─ [WIRED]   Conflict <-> Boss (conflict_details.boss_phase JSONB)
├─ [WIRED]   Psyche <-> Prompt Caching (L3 section 3.5)
├─ [WIRED]   Life Sim <-> Portal (API + timeline)
├─ [WIRED]   Psyche <-> Portal (API + tips)
├─ [WIRED]   Pipeline 9 Stages (correct order)
├─ [WIRED]   Feature Flags (3: psyche, conflict temp, multi-phase boss)
├─ [WIRED]   API Routes (life-events, psyche-tips, psyche-batch)
├─ [WIRED]   DB Models (psyche_states, conflict_details, social_circle)
├─ [PARTIAL] Psyche <-> Life Sim (deps declared, batch.py:130-179 never loads)
└─ [PARTIAL] Boss <-> Portal (WarmthMeter = generic intimacy, not boss phase)
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
│  ├─ Strategic Silence       ├─ Decay System
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

## SDD Compliance Matrix

| Tier | Specs | Action | Effort |
|------|-------|--------|--------|
| Quick Fix | 056, 059 | Generate audit-report.md only | 25 min |
| Legacy Exempt | 049, 050 | Mark as pre-SDD in tracking | 5 min |
| Full SDD | 061, 062, 063 | Generate plan.md + tasks.md | 2-3 hrs |

**Housekeeping**:
- Delete empty orphan `specs/057-conflict-core/`
- Spec 045 (prompt-unification): no directory, no git history — mark as legacy pre-SDD
- Specs 051-054: intentionally unassigned numbers (Wave B restructuring)

---

## Prioritized Remediation Plan

### Priority 1: Critical
| Task | File | Effort |
|------|------|--------|
| Fix prompt section headers to match rendered template | `prompt_builder.py:470-473` | 1 hr |
| Add per-user locking in message handler | `message_handler.py` | 2 hrs |

### Priority 2: High-Impact Gaps
| Task | File | Effort |
|------|------|--------|
| Re-enable chapter-based skip rates | `skip.py:17-23` | 30 min |
| Wire life events + NPC data into psyche batch | `batch.py:130-179` | 1 hr |
| Generate plan.md + tasks.md for specs 061-063 | `specs/061-063/` | 2-3 hrs |

### Priority 3: Medium Cleanup
| Task | File | Effort |
|------|------|--------|
| Add phase-specific timeout reset in boss | `phase_manager.py` | 1 hr |
| Mark boss conversations with is_boss_fight=True | `message_handler.py` | 30 min |
| Update master-plan.md (Neo4j→pgVector, spec count) | `master-plan.md` | 1 hr |
| Generate audit-report.md for specs 056, 059 | `specs/056,059/` | 25 min |

### Priority 4: Housekeeping
| Task | Effort |
|------|--------|
| Delete empty `specs/057-conflict-core/` | 1 min |
| Mark specs 045, 049, 050 as legacy pre-SDD | 5 min |
| Add life_sim feature flag to settings.py | 15 min |

---

*Consolidated from 4-agent parallel audit | 2026-02-21 | Processed 2026-02-22*
