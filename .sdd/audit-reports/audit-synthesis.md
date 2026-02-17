# SDD Audit Synthesis — Nikita Project

## Date: 2026-02-17
## Auditors: 5-agent deep audit + 3-agent MapReduce team
## Verdict: CONDITIONAL GO — Prerequisites required before SDD pipeline

---

## Executive Summary

- **Total specs audited**: 53 (048 completed) + 6 proposed (055-060)
- **Specs with full SDD compliance**: ~44 (pre-049 specs with all artifacts)
- **Specs partially compliant**: 4 (049-052: code committed, no tasks.md/audit-report.md, 0 tests)
- **Specs not started**: 6 (055-060: zero artifacts, only context docs exist)
- **Critical blockers**: 5 (must resolve before SDD pipeline)
- **Remediation items**: 8 prerequisites (P1-P8), 12-17 hours
- **Alignment rate**: ~85% for pre-049 specs; ~62% for specs 049-052

---

## Spec Numbering Resolution

**CRITICAL**: Specs 049-052 have a naming collision. Two different feature sets use the same numbers.

| Number | Existing (COMPLETED) | Gate 4.5 (PROPOSED) | Resolution |
|--------|---------------------|-------------------|------------|
| 049 | Game Mechanics Remediation | Life Simulation Enhanced | Keep existing → Rename proposed to **055** |
| 050 | Portal Fixes | Psyche Agent | Keep existing → Rename proposed to **056** |
| 051 | Voice Pipeline Polish | Conflict System CORE | Keep existing → Rename proposed to **057** |
| 052 | Infrastructure Cleanup | Multi-Phase Boss | Keep existing → Rename proposed to **058** |
| 053 | (available) | Portal: Nikita's Day | Rename to **059** |
| 054 | (available) | Prompt Caching | Rename to **060** |

---

## Claims Verification (Cross-Agent Consensus)

| # | Claim | Verdict | Source |
|---|-------|---------|--------|
| 1 | persona.py = Brooklyn/MIT/Cipher | **TRUE** | BS Detector + Fact Checker |
| 2 | system_prompt.j2 = Berlin/Schrodinger | **TRUE** | BS Detector + Fact Checker |
| 3 | Agent always injects NIKITA_PERSONA | **TRUE** | Fact Checker (agent.py:75) |
| 4 | Chapter behavior has NO guard | **TRUE** | Fact Checker (agent.py:80-85) |
| 5 | prompt_builder budget 5,500-6,500 | **TRUE** | Fact Checker (prompt_builder.py:51-52) |
| 6 | BossResult = PASS/FAIL only | **TRUE** | Fact Checker (judgment.py:19) |
| 7 | boss.py has no phase tracking | **TRUE** | Devil's Advocate |
| 8 | nikita_state.friends = Maya/Sophie/Lena | **FALSE** | Fact Checker — fabricated, no such table |
| 9 | entities = Marco/Viktor/Yuki/Alexei | **FALSE** | Fact Checker — actual: Lisa/Max/Sarah/Ana/Jamie/Mira |
| 10 | ConflictStore is in-memory singleton | **TRUE** | Devil's Advocate (NEW, store.py:31-36) |
| 11 | Opus cache min = 1,024 tokens | **FALSE** | Researcher — actually 4,096 for Opus 4.6 |
| 12 | pg_cron available on free tier | **TRUE** | Researcher — confirmed |
| 13 | ElevenLabs = $0.10/min | **TRUE** | Researcher |
| 14 | $30-37/mo total cost | **PARTIAL** | Researcher + Devil's Advocate — LLM only, actual ~$96/mo with stacking |
| 15 | Specs 049-052 = "100% PASS" | **FALSE** | BS Detector — 0 tests, 3 functional gaps, missing SDD artifacts |

**Score: 10 TRUE, 3 FALSE, 2 PARTIAL**

---

## SDD Readiness Matrix — Wave 055-060

| Spec | Gate 0 | Gate 1 | Gate 2 | Gate 3 | Status | Prerequisites |
|------|--------|--------|--------|--------|--------|---------------|
| 055 Life Sim | NOT STARTED | - | - | - | **CONDITIONAL GO** | P1 (renumber), P7 (NPC names) |
| 056 Psyche Agent | NOT STARTED | - | - | - | **NO-GO** (wait 055) | P2 (persona fix), depends on 055 |
| 057 Conflict CORE | NOT STARTED | - | - | - | **CONDITIONAL GO** | P1 (renumber), P4 (ConflictStore→DB) |
| 058 Boss + Warmth | NOT STARTED | - | - | - | **NO-GO** (wait 057) | Depends on 057 conflict_state |
| 059 Portal | NOT STARTED | - | - | - | **NO-GO** (wait all) | Depends on 055+056+057+058 data |
| 060 Caching | NOT STARTED | - | - | - | **CONDITIONAL GO** | P2 (persona fix), P3 (chapter guard) |

---

## Prerequisites (Ordered by Dependency)

| # | Fix | Severity | Effort | Blocks | Action |
|---|-----|----------|--------|--------|--------|
| **P1** | Spec renumbering | CRITICAL | 1 hr | All | Create dirs specs/055-060/, update cross-refs |
| **P2** | Persona conflict | CRITICAL | 2-4 hrs | 056, 060 | Slim persona.py to ~400 tok behavioral guide |
| **P3** | Chapter behavior guard | MEDIUM | 1 hr | 060 | Add `if ctx.deps.generated_prompt: return ""` |
| **P4** | ConflictStore → DB | CRITICAL | 2-3 hrs | 057 | Move in-memory dicts to DB-backed storage |
| **P5** | Wire decay notification | MEDIUM | 30 min | None | Pass notify_callback to DecayProcessor |
| **P6** | Backfill tests 049-052 | HIGH | 4-6 hrs | None | 6 test files for 5 user stories + task auth |
| **P7** | NPC name correction | HIGH | 1 hr | 055 | Document actual names: template (Lena/Viktor/Yuki) + entities (Lisa/Max/Sarah/Ana/Jamie/Mira) |
| **P8** | Boss timeout query fix | LOW | 30 min | 058 | Use dedicated timestamp instead of generic updated_at |
| | **TOTAL** | | **12-17 hrs** | | |

---

## Risk Register (Combined)

### CRITICAL
| # | Risk | Source |
|---|------|--------|
| C1 | Persona conflict (Brooklyn vs Berlin) in production | Original + verified |
| C2 | Prompt stacking (+1,900 unbudgeted tokens) | Original + verified |
| C3 | NPC names in audit docs are WRONG | Fact Checker (NEW) |
| C4 | ConflictStore in-memory singleton | Devil's Advocate (NEW) |

### HIGH
| # | Risk | Source |
|---|------|--------|
| H1 | Opus 4.6 cache threshold = 4,096 (not 1,024) | Researcher (NEW) |
| H2 | Zero tests for specs 049-052 | BS Detector |
| H3 | US-4 decay notification is dead code | BS Detector |
| H4 | Actual cost ~$96/mo (3x estimate) | Devil's Advocate (NEW) |
| H5 | Boss timeout uses generic updated_at | Devil's Advocate (NEW) |
| H6 | Multi-phase boss content bottleneck (10 prompts) | Original |
| H7 | No existing user migration plan | Original |

### MEDIUM
| # | Risk | Source |
|---|------|--------|
| M1-M7 | Temperature calibration, Gottman ratio, pipeline mutex, Haiku cache conflict, cache TTL, pgVector growth, voice costs | Various |

---

## Validated Dependency DAG

```
PREREQUISITES [P1-P8, ~2 days]
├─ P2+P3 (persona) ──→ 060
├─ P4 (ConflictStore→DB) ──→ 057
└─ P7 (NPC names) ──→ 055

WAVE A [parallel]
├─ 055 Life Sim ← P7
├─ 057 Conflict ← P4
└─ 060 Caching ← P2, P3

WAVE B [depends on 055]
└─ 056 Psyche ← reads life events + NPC states

WAVE C [depends on 057]
└─ 058 Boss ← conflict_state.boss_phase

WAVE D [depends on all backend]
└─ 059 Portal ← frontend for all data
```

---

## SDD-Team Recommendations

| Spec | Complexity Score | Recommendation |
|------|-----------------|---------------|
| 055 | 3 | Solo `/sdd` |
| 056 | **7** | Full `/sdd-team` |
| 057 | 3 | Solo `/sdd` |
| 058 | **5** | `/sdd-team` recommended |
| 059 | 2 | Solo `/sdd` |
| 060 | 2 | Solo `/sdd` |

### Execution Timeline

| Phase | Days | Content |
|-------|------|---------|
| Prerequisites | 2 | P1-P8 |
| Wave A (055+057+060) | 3-4 | Parallel, solo /sdd |
| Wave B (056) | 3-4 | Full /sdd-team |
| Wave C (058) | 5-8 | /sdd-team, boss bottleneck |
| Wave D (059) | 2-3 | Solo /sdd, frontend |
| E2E re-run | 1 | Spec 048 tests |
| **Total** | **16-22** | Realistic with parallelism |

---

## Next Steps

1. Execute prerequisites P1-P8 (~2 days)
2. Run `/sdd feature` for Wave A specs (055, 057, 060)
3. GATE 2 validation per spec
4. `/sdd-team implement` for spec 056 (Psyche Agent)
5. `/sdd-team implement` for spec 058 (Boss)
6. `/sdd feature` + `/sdd implement` for spec 059 (Portal)
7. E2E re-run
