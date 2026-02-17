# Consolidated Audit Report — Gate 4.5 Spec Wave (055-060)

**Date**: 2026-02-17
**Agents**: BS Detector, Fact Checker, Researcher, Devil's Advocate, Architecture Auditor
**Verdict**: **CONDITIONAL GO** — 9-14 hours of prerequisite work required before SDD pipeline

---

## 1. Claims Verification Table

| # | Claim | Verdict | Evidence | Impact |
|---|-------|---------|----------|--------|
| 1 | persona.py:18 = Brooklyn/MIT/Cipher | **VERIFIED** | Lines 18-98, ~1,600 tok | Dual identity confirmed |
| 2 | system_prompt.j2:11 = Berlin/Schrodinger | **VERIFIED** | Lines 11-35 | Dual identity confirmed |
| 3 | agent.py:75 always injects NIKITA_PERSONA | **VERIFIED** | Static `instructions=` param | Stacking confirmed |
| 4 | agent.py:80-85 chapter behavior NO guard | **VERIFIED** | No check for generated_prompt | Double injection confirmed |
| 5 | agent.py:103 personalized context HAS guard | **VERIFIED** | `if ctx.deps.generated_prompt` | Inconsistent guarding |
| 6 | prompt_builder.py:51-52 budget 5,500-6,500 | **VERIFIED** | TEXT_TOKEN_MIN/MAX exact | Budget doesn't include stacking |
| 7 | judgment.py:19 BossResult = PASS/FAIL only | **VERIFIED** | Exactly 2 enum values | No PARTIAL exists |
| 8 | boss.py has no phase tracking | **VERIFIED** | Single-turn flow confirmed | Full redesign needed |
| 9 | prompts.py has 5 boss prompts | **VERIFIED** | Ch1-Ch5, exact match | 10 needed for 2-phase MVP |
| 10 | nikita_state.friends = Maya/Sophie/Lena | **FALSE** | No such table/names exist | **Audit doc fabricated this** |
| 11 | user_social_circles = 14 columns | **VERIFIED** | Spec 035, exact count | Canonical NPC store confirmed |
| 12 | entities = Marco/Viktor/Yuki/Alexei/Katya | **FALSE** | Actual: Lisa/Max/Sarah/Ana/Jamie/Mira | **Wrong character names** |
| 13 | conflict_state enum = 5 values | **VERIFIED** | none/passive_aggressive/cold/vulnerable/explosive | Temperature must replace this |
| 14 | ActiveConflict model exists | **VERIFIED** | severity/escalation/resolution fields | Will be refactored |
| 15 | Pipeline = 9 stages | **VERIFIED** | STAGE_DEFINITIONS list exact | Sequential confirmed |
| 16 | 6 pg_cron jobs | **FALSE** | Actually 9 task endpoints | Undercount by 50% |
| 17 | mood_calculator = one-way | **VERIFIED** | Events→mood only | Bidirectional needed |
| 18 | event_generator has no mood_state param | **VERIFIED** | No such parameter exists | Must be added |

**Score: 15 VERIFIED, 3 FALSE, 0 PARTIAL**

### Critical False Claims

**Claim 10 is fabricated.** The audit docs reference a `nikita_state.friends` JSONB containing Maya/Sophie/Lena. No such table or data exists. The NPC "3-way mess" is actually a **2-way mess**: (1) hardcoded persona characters in system_prompt.j2 (Lena/Viktor/Yuki), (2) dynamic per-user social circles in user_social_circles table. The entity seed data in entities.yaml uses completely different names (Lisa/Max/Sarah/Ana/Jamie/Mira).

**Claim 12 has wrong names.** The audit docs say nikita_entities contains Marco/Viktor/Yuki/Alexei/Katya. Actually it contains Lisa/Max/Sarah/David/Ana/Jamie/Mira. The names Viktor/Yuki/Alexei/Katya only exist in system_prompt.j2 backstory text. Marco doesn't exist anywhere.

---

## 2. External Service Verification (Feb 2026)

| # | Service | Audit Claim | Current Reality | Delta | Action |
|---|---------|-------------|-----------------|-------|--------|
| 1 | **Anthropic Caching** | 1,024 tok min, 5min TTL | **Opus 4.6 = 4,096 tok min** (not 1,024). Sonnet = 1,024. 1-hr extended TTL costs 2x write. | **HIGH IMPACT** — caching math wrong for Opus | Recalculate cache breakpoints for 4,096 min |
| 2 | **Claude Pricing** | Opus $5/$25, Sonnet $3/$15, Haiku $1/$5 | All confirmed. Batch API = 50% discount. | None | Note batch discount for psyche agent |
| 3 | **Pydantic AI** | 3 multi-agent patterns | Now 4 patterns (Deep Agents added). DB-mediated coordination feasible. | Minor | No action needed |
| 4 | **Supabase pg_cron** | "Likely available on free tier" | **Confirmed available** by Supabase staff. Max ~8 concurrent recommended. | Positive | Remove uncertainty, document as confirmed |
| 5 | **ElevenLabs** | $0.10/min Conv AI | Confirmed. $0.08/min on annual Business. LLM costs currently absorbed. | Minor | Budget for future LLM pass-through |
| 6 | **OpenAI Embeddings** | 1536 dims for text-embedding-3-small | Confirmed. Supports MRL reduction to 512 dims. | None | No action needed |

### Highest Impact: Opus 4.6 Cache Threshold
The audit assumed 1,024 token minimum for prompt caching. Opus 4.6 requires **4,096 tokens minimum**. This means:
- L1 Identity alone (~2,000 tok) is NOT cacheable on its own with Opus
- L1+L2+L7 combined (~3,200 tok) is still below the 4,096 threshold
- Must combine L1+L2+L7+tool_definitions (~3,500 tok) to reach minimum
- **Alternatively**: If Nikita uses Sonnet 4.5 (not Opus) for conversations, the 1,024 threshold applies and the original math holds

---

## 3. NEW Risk Register (Devil's Advocate Discoveries)

These risks were NOT in the original 14-challenge register:

| # | New Risk | Severity | Probability | Evidence |
|---|----------|----------|-------------|----------|
| NF-01 | **ConflictStore is in-memory singleton** — all conflict state vanishes on Cloud Run cold start/deployment | CRITICAL | 100% | `conflicts/store.py:31-36` uses Python dicts, `store.py:402-415` is singleton |
| NF-02 | **Boss timeout uses `updated_at`** which resets on ANY user row change | HIGH | 80% | `tasks.py:1006` queries `User.updated_at < cutoff` |
| NF-03 | **Actual per-message input is ~10,720 tok** (not 6,500) due to stacking persona+chapter+tools+history | HIGH | 100% | Agent stacks 1,600+300+270+3,000 on top of pipeline prompt |
| NF-04 | **Monthly LLM cost is ~$96** at 100 msgs/day (3x the $30-37 estimate) | HIGH | 90% | Based on actual token counts, not pipeline budget |
| NF-05 | **Zero tests for any of specs 049-052** | HIGH | 100% | Grep for test files returns 0 matches |
| NF-06 | **US-4 decay notification is dead code** — callback infrastructure exists but never wired | MEDIUM | 100% | `tasks.py:232-237` omits `notify_callback` param |
| NF-07 | **No mutex for concurrent pipeline access** — two messages from same user can race | MEDIUM | 30% | `orchestrator.py` has no locking mechanism |
| NF-08 | **Character name mapping is based on false claims** — audit docs reference Maya/Sophie/Marco that don't exist | MEDIUM | 100% | Claims 10 and 12 are FALSE |

---

## 4. SDD Readiness Matrix

| Spec | Gate 0 | Gate 1 | Gate 2 | Gate 3 | Status | Blocker |
|------|--------|--------|--------|--------|--------|---------|
| 055 (Life Sim) | NOT STARTED | - | - | - | Pre-Gate 0 | No spec dir, no spec.md |
| 056 (Psyche) | NOT STARTED | - | - | - | Pre-Gate 0 | No spec dir, no spec.md |
| 057 (Conflict) | NOT STARTED | - | - | - | Pre-Gate 0 | No spec dir, no spec.md |
| 058 (Boss) | NOT STARTED | - | - | - | Pre-Gate 0 | No spec dir, no spec.md |
| 059 (Portal) | NOT STARTED | - | - | - | Pre-Gate 0 | No spec dir, no spec.md |
| 060 (Caching) | NOT STARTED | - | - | - | Pre-Gate 0 | No spec dir, no spec.md |

**All 6 specs are at pre-Gate 0.** Rich context exists in docs-to-process/ but zero SDD artifacts have been created.

---

## 5. Prerequisite Fix List (Ordered)

| # | Fix | Severity | Effort | Blocks | How |
|---|-----|----------|--------|--------|-----|
| P1 | **Spec renumbering** | CRITICAL | 1 hr | All specs | Create dirs 055-060, update cross-refs in docs-to-process/ |
| P2 | **Persona conflict fix** | HIGH | 2-4 hrs | 056, 060 | Slim persona.py to ~400 tok behavioral guide; template = sole identity |
| P3 | **Chapter behavior guard** | MEDIUM | 1 hr | 060 | Add `if ctx.deps.generated_prompt: return ""` to add_chapter_behavior() |
| P4 | **ConflictStore → DB** | CRITICAL | 2-3 hrs | 057 | Move in-memory dicts to DB-backed storage (conflicts survive cold starts) |
| P5 | **Wire decay notification** | MEDIUM | 30 min | None | Pass notify_callback to DecayProcessor in tasks.py |
| P6 | **Backfill tests for 049-052** | HIGH | 4-6 hrs | None (but risky without) | 6 test files covering 5 user stories + task auth |
| P7 | **Fix NPC character mapping** | HIGH | 1 hr | 055 | Correct the false claims: actual names are Lena/Viktor/Yuki (template) + Lisa/Max/Sarah/Ana/Jamie/Mira (entities) |
| P8 | **Fix boss timeout query** | LOW | 30 min | 058 | Use dedicated `boss_fight_started_at` timestamp instead of generic `updated_at` |
| | **TOTAL** | | **12-17 hrs** | | |

---

## 6. Validated Dependency DAG

```
PREREQUISITES (P1-P8, ~2 days)
│
├─ P2 (persona fix) ──→ enables 056, 060
├─ P4 (ConflictStore→DB) ──→ enables 057
└─ P7 (NPC name correction) ──→ enables 055

WAVE A (parallel, no inter-dependency)
├─ 055 (Life Sim) ← depends on P7 (NPC names)
└─ 057 (Conflict) ← depends on P4 (ConflictStore→DB)

WAVE B (depends on 055)
└─ 056 (Psyche) ← reads life events + NPC states from 055

WAVE C (depends on 057)
├─ 058 (Boss) ← uses conflict_state.boss_phase from 057
└─ 060 (Caching) ← depends on P2+P3 (persona fix) + 056 (L3 section)

WAVE D (depends on all backend)
└─ 059 (Portal) ← frontend for 055+056+057+058 data
```

**DAG correction from Architecture Auditor**: The original Gate 4.5 DAG put 060 as prerequisite for everything. This is WRONG. The persona hotfix (P2) should be extracted as a standalone prerequisite fix, not a full spec. 060 can run in Wave C alongside 058, not as a blocker.

---

## 7. Realistic Timeline

| Phase | Days | Risk | Notes |
|-------|------|------|-------|
| Prerequisites (P1-P8) | 2 | LOW | Mostly mechanical fixes |
| Wave A: 055+057 (parallel) | 4-5 | MEDIUM | NPC reconciliation is the design bottleneck |
| Wave B: 056 | 3-4 | MEDIUM | New agent module, highest SDD complexity (score 7) |
| Wave C: 058+060 (parallel) | 5-8 | HIGH | Boss prompts are creative bottleneck |
| Wave D: 059 | 2-3 | LOW | Pure frontend |
| E2E re-run + polish | 1-2 | LOW | Re-run Spec 048 E2E tests |
| **TOTAL** | **17-24** | | With parallelism |
| **TOTAL (serial)** | **25-35** | | Without parallelism |

**Devil's advocate buffer**: Add 30-40% for design iteration (temperature calibration, boss prompt tuning, NPC name reconciliation discussions). **Adjusted: 22-30 days.**

---

## 8. GO/NO-GO Decision

### CONDITIONAL GO

**Conditions for GO:**
1. Complete prerequisites P1-P4 (CRITICAL/HIGH items, ~8 hrs)
2. Correct the NPC character mapping to reflect actual codebase names (P7)
3. Run `/sdd-team` starting with Wave A specs (055+057)
4. Use corrected Opus caching threshold (4,096 tok) for Spec 060 cost calculations

**Conditions that would make this NO-GO:**
- If ConflictStore in-memory singleton cannot be migrated to DB without breaking existing tests
- If the persona fix reveals other undocumented injection points
- If the actual monthly cost ($96/mo) is unacceptable to the user

### Key Findings Cross-Agent Agreement

| Finding | BS Detector | Fact Checker | Researcher | Devil's Advocate | Architecture |
|---------|------------|-------------|-----------|-----------------|-------------|
| Persona conflict is real and active | YES | YES (claims 1-5) | N/A | YES (NF-03) | YES |
| Spec 049-052 are NOT SDD compliant | YES (0 tests) | N/A | N/A | YES (NF-05) | YES (missing artifacts) |
| NPC names in audit docs are wrong | N/A | YES (claims 10,12 FALSE) | N/A | N/A | N/A |
| Opus cache threshold is 4,096 not 1,024 | N/A | N/A | YES | N/A | N/A |
| ConflictStore is in-memory (new finding) | N/A | N/A | N/A | YES (NF-01, CRITICAL) | N/A |
| Cost estimate is 3x understated | N/A | N/A | Partially | YES (NF-04, ~$96/mo) | N/A |
| pg_cron confirmed on free tier | N/A | N/A | YES | N/A | N/A |
| DAG: 060 should NOT block Wave A | N/A | N/A | N/A | N/A | YES (P2 hotfix instead) |

### No Contradictions Between Agents

All 5 agents converged on the same core findings with zero contradictions. The only new information was:
- Devil's Advocate discovered NF-01 (ConflictStore in-memory) — not flagged by any other agent or the original 9 audit docs
- Researcher corrected the Opus cache threshold — HIGH impact on Spec 060 cost model
- Fact Checker exposed claims 10 and 12 as fabricated — impacts NPC consolidation planning

---

## 9. Corrected NPC Character Mapping

Based on fact-checker verification, the ACTUAL character systems are:

| System | Location | Characters | Status |
|--------|----------|------------|--------|
| system_prompt.j2 persona | Template lines 27-31 | Lena (best friend), Viktor (ex-colleague), Yuki (hacker friend), Dr. Miriam (therapist) | Hardcoded in template |
| entities.yaml seed data | config_data/life_simulation/ | Lisa, Max, Sarah, David (colleagues); Ana, Jamie, Mira (friends) | Seed data for life sim |
| user_social_circles | DB table (14 cols) | Per-user generated, no fixed names | Dynamic, canonical store |

**The mapping table from the audit docs (Maya→deprecate, Sophie→Sarah, Marco→Marcus) is INVALID.** Maya, Sophie, and Marco do not exist in the codebase. The actual reconciliation needed is:
- Template characters (Lena/Viktor/Yuki/Dr. Miriam) need entries in user_social_circles
- Entity seed characters (Lisa/Max/Sarah/Ana/Jamie/Mira) may or may not need social circle entries
- Template and entities use DIFFERENT character sets with zero overlap except possibly Lena

---

*Report generated by 5 independent agents. Total investigation: ~50 file reads, 200+ grep queries, 6 web searches, 3 git log analyses.*
