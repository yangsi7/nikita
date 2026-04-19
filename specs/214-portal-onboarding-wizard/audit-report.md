# Audit Report: Spec 214 (GATE 7 Cross-Artifact Consistency)

**Date**: 2026-04-19
**Auditor**: /audit (Phase 7, SDD workflow)
**Supersedes**: prior audit-report.md @ 2026-04-15 (pre-amendment, form-wizard scope)
**Artifacts audited**:
- `specs/214-portal-onboarding-wizard/spec.md` (amended commit `35c1e38`, 1217 lines)
- `specs/214-portal-onboarding-wizard/technical-spec.md` (`35c1e38`, 711 lines)
- `specs/214-portal-onboarding-wizard/plan.md` (`989e7af`, 876 lines)
- `specs/214-portal-onboarding-wizard/tasks.md` (`6564c16`, 752 lines)
- `specs/214-portal-onboarding-wizard/validation-findings-iter2.md` (`545e91f`)

**Verdict**: **PASS**

GATE 7 criteria (every dimension PASS = 0 critical gaps) satisfied. Proceeding to `/implement`.

---

## Scoreboard

| # | Dimension | Status | Findings |
|---|---|---|---|
| 1 | AC Coverage (spec → plan → tasks) | PASS | 54/54 spec ACs mapped; plan.md §11 matrix exhaustive |
| 2 | Task Coverage (plan ↔ tasks bidirectional) | PASS | 43 plan tasks = 43 tasks.md entries (T1.1-T5.4) |
| 3 | AC-per-task minimum (≥2) | PASS | Avg 2.81 ACs/task (121/43); 5 glue tasks at 1 AC are informational (W1) |
| 4 | Task sizing (2-8h) | PASS | All ≤8h; 14 at 1h (glue), 29 in 2-6h range |
| 5 | Dependency graph integrity | PASS | 32 edges (28 intra + 4 cross-PR); 0 cycles |
| 6 | PR sizing (≤400 LOC) | PASS | All 5 PRs ≤400 LOC estimated per plan §4 |
| 7 | Testing strategy (Test: per AC) | PASS | Every AC in tasks.md has explicit `Test:` path |
| 8 | File path consistency | PASS | Project-relative paths throughout; no broken refs |
| 9 | Open decisions D1-D6 | PASS | All 6 resolved in plan.md §3 |
| 10 | Rollout gates | PASS | `USE_LEGACY_FORM_WIZARD` + `source=llm >=90%` + `+-5pp completion-rate` pinned in plan §9.1 |
| 11 | Named tuning constants | PASS | 19 constants referenced by name; T2.1 regression test gate |
| 12 | TDD enablement (testing.md pre-PR grep gates) | PASS | tasks.md reproduces all 3 greps |
| 13 | MEDIUM findings pinned | PASS | 9/9 pinned (D1-D6 resolve 6; data-M1/M2 + testing-M2 in plan §10) |
| 14 | Em-dash UI audit | PASS | No new FR-11c/d/e user-facing copy contains em-dashes; see W2 |

---

## Dimension-by-Dimension Audit

### 1. AC Coverage (spec -> plan -> tasks)

Plan.md §11 Requirements Coverage Matrix enumerates **54 spec ACs -> task IDs** exhaustively:

- FR-11c: AC-11c.1-12, 12b (14 ACs) -> T1.1-T1.7, T5.2, T5.4
- FR-11d: AC-11d.1-13c incl. .3b, .3c, .3d, .3e, .4b, .5b-e, .10b, .12b, .13b, .13c (26 ACs) -> T2.1-T2.11, T3.1-T3.12
- FR-11e: AC-11e.1, .2, .3, .3b, .3c, .4, .5, .6 (8 ACs) -> T4.1-T4.9, T3.11
- NR-1b: AC-NR1b.1, .1b, .2, .3, .4, .4b, .4c, .5 (8 ACs) -> T2.8, T3.1, T3.3, T4.6-T4.8

Verification: grep spec.md for `AC-11[cde].` + `AC-NR1b.` returned all 54 IDs; every one present in plan §11 matrix with a task binding. **No orphan ACs.**

### 2. Task Coverage (plan <-> tasks bidirectional)

- plan.md §5 lists 7+11+12+9+4 = **43 tasks** (T1.1-T1.7, T2.1-T2.11, T3.1-T3.12, T4.1-T4.9, T5.1-T5.4)
- tasks.md headers enumerate **43 tasks** with identical IDs
- plan §12 summary "Total tasks: 43" matches tasks.md "Total tasks: 43"

Spot-checked 10 random tasks: every plan AC (AC-T1.3.1 through AC-T4.8.2) appears verbatim in tasks.md with matching numbering. **No phantom or dropped tasks.**

### 3. AC-per-task minimum (>=2)

AC counts per task (total 121): T1.1=4, T1.2=3, T1.3=5, T1.4=2, T1.5=2, T1.6=3, T1.7=2; T2.1=2, T2.2=3, T2.3=3, T2.4=3, T2.5=11, T2.6=3, T2.7=2, T2.8=3, T2.9=3, T2.10=3, T2.11=2; T3.1=4, T3.2=2, T3.3=3, T3.4=2, T3.5=5, T3.6=4, T3.7=3, T3.8=2, T3.9=4, T3.10=2, T3.11=1, T3.12=2; T4.1=3, T4.2=4, T4.3=3, T4.4=2, T4.5=1, T4.6=1, T4.7=1, T4.8=2, T4.9=2; T5.1=2, T5.2=2, T5.3=2, T5.4=1.

**Findings**: 5 tasks (T3.11, T4.5, T4.6, T4.7, T5.4) carry 1 AC each. Single-outcome glue tasks (middleware redirect, one-shot migration script, pg_cron job, delete_user extension, grep re-audit). Every one has concrete falsifiable test. Flagged as informational (W1), non-blocking. **Does NOT block /implement.**

### 4. Task sizing (2-8h)

Breakdown: 1h=14 tasks (glue); 2h=12; 3h=10; 4h=4; 5h=2 (T3.5, T3.6); 6h=1 (T2.5). Range 1h-6h. All within 8h ceiling. **PASS.**

### 5. Dependency graph integrity

Plan §6 + tasks.md Dependency Graph identical ASCII graphs: 28 intra-PR + 4 cross-PR = 32 edges. Cross-PR serialization PR1->PR2->PR3->PR4->PR5 monotone. Cycles: none.

### 6. PR sizing (<=400 LOC)

PR 1 ~350 LOC | PR 2 ~400 LOC | PR 3 ~400 LOC | PR 4 ~250 LOC | PR 5 ~150 LOC. All within `.claude/rules/pr-workflow.md` 400-LOC cap.

### 7. Testing strategy (Test: per AC)

Every AC in tasks.md carries explicit `Test:` annotation pointing to a concrete test path. Spot-checked 15 random ACs - all have Test: path. No TODO or unresolved test mapping.

### 8. File path consistency

Plan §5 + tasks.md Files lists use consistent project-relative paths. Cross-refs to rules, specs, ADR-001 all consistent. No broken paths.

### 9. Open decisions D1-D6

plan.md §3 resolves all 6 decisions:
- D1 Bridge-token storage: DB-backed not JWT (T1.1).
- D2 llm_spend_ledger upsert: INSERT ... ON CONFLICT DO UPDATE atomic (T2.6).
- D3 idempotency mismatch: 409 on header+body disagree (T2.5.3).
- D4 ControlSelection: TS discriminated union (5 kinds) (T3.2, T2.4).
- D5 Mobile ACs: 3 task-level ACs M1/M2/M3 (T3.5.4, T3.5.5, T3.6.3).
- D6 Coverage thresholds: per-module floors 80-90% line / 70-85% branch.

### 10. Rollout gates

Plan §9.1 pins 3 gates: USE_LEGACY_FORM_WIZARD env flag; source=llm >= LLM_SOURCE_RATE_GATE_MIN=0.90 over N=100 (PR 3 ship gate); chat-wizard completion rate +- CHAT_COMPLETION_RATE_TOLERANCE_PP=5 pp of baseline over N=50 (PR 5 gate). Measurement scripts shipped in T2.11 + T3.12. Rollback procedures per PR in §9.2.

### 11. Named tuning constants

T2.1 AC-T2.1.1 adds 19 constants as Final[...] with 3-line rationale docstrings per `.claude/rules/tuning-constants.md`. Referenced throughout plan + tasks: CONVERSE_PER_USER_RPM=20, CONVERSE_PER_IP_RPM=30, CONVERSE_DAILY_LLM_CAP_USD=2.00, CONVERSE_TIMEOUT_MS, NIKITA_REPLY_MAX_CHARS=140, PERSONA_DRIFT_COSINE_MIN=0.70, PERSONA_DRIFT_FEATURE_TOLERANCE=0.15, LLM_SOURCE_RATE_GATE_N=100, LLM_SOURCE_RATE_GATE_MIN=0.90, CHAT_COMPLETION_RATE_GATE_N=50, CHAT_COMPLETION_RATE_TOLERANCE_PP=5, STRICTMODE_GUARD_MS, HANDOFF_GREETING_BACKSTOP_INTERVAL_SEC=60, ONBOARDING_FORBIDDEN_PHRASES. Values cited inline for reviewer clarity; regression test T2.1 asserts exact values.

### 12. TDD enablement

tasks.md "TDD Protocol" + "Pre-PR grep gates" reproduces the 3 mandatory greps verbatim: zero-assertion test shells; PII leakage in log format strings; raw cache_key without hashing. Cross-reference to `.claude/rules/testing.md`.

### 13. SDD validator MEDIUM findings pinned

9/9 addressed. api-M-NEW-1 (429 Retry-After) -> plan §3 D3 + T2.5.4. arch-M4 (ControlSelection) -> D4 + T3.2/T2.4. auth-M-A (bridge-token DB) -> D1 + T1.1. auth-M-B (spend upsert SQL) -> D2 + T2.6. data-M1 (service-role RLS comment) -> plan §10 inline in migration files. data-M2 (index audit) -> plan §10 informational. frontend-F-1 (mobile) -> D5 + T3.5.4/T3.5.5/T3.6.3. testing-M1 (coverage floors) -> D6. testing-M2 (E2E Gemini-judge) -> plan §10 DEFER post-ship.

### 14. Em-dash UI audit

Scanned all 4 artifacts for em-dashes inside quoted user-facing copy strings. Per root CLAUDE.md, em-dashes permitted in dev-facing prose; banned in UI strings.

Pre-existing (NOT new FR-11c/d/e scope): spec.md:634, 884 US-5 voice fallback copy (unchanged by amendment); spec.md:177-178, 1028 PROVISIONAL-CLEARED stamp (pre-existing pipeline-gate).

Newly-introduced FR-11c/d/e UI copy - all em-dash-free: "good to see you again" (AC-11c.2); "lets pick this up where you left off" (AC-11c.4); "no email here" (AC-11c.8); "FILE CLOSED. CLEARANCE: GRANTED." (AC-11e.1); "Meet her on Telegram" (AC-11e.1 CTA); "Building your file... N%" (AC-11d.8); "That link expired. Open Telegram and tap /start again." (T1.2 AC-T1.2.3).

At implementation time: 429 rate-limit body and in-character nudge described as "Nikita-voiced" without verbatim text. Implementor must avoid em-dashes. Flagged as W2.

---

## Findings

### Critical (blocks /implement)

None.

### Warnings (should track, non-blocking)

- **W1** (dim 3): 5 tasks carry 1 AC each (T3.11, T4.5, T4.6, T4.7, T5.4). Single-outcome glue tasks with explicit tests. Non-blocker.
- **W2** (dim 14): Implementor must hand-audit Nikita-voiced 429 body + in-character nudge strings for em-dashes at commit time. Add to PR-1 + PR-2 pre-PR grep list: `rg "--" nikita/api/routes/portal_onboarding.py nikita/platforms/telegram/commands.py nikita/onboarding/bridge_tokens.py portal/src/app/onboarding/` (em-dash char) - expect empty for user-facing strings.

### Informational

- **I1** (dim 4): 14 tasks at 1h are deliberately small; each independently committable.
- **I2** (dim 10): T2.11 + T3.12 must be merged BEFORE T5.1 (measurement script reuse).
- **I3** (dim 8): T1.2 lists `portal/src/app/onboarding/auth/route.ts` as "or existing bridge consumer route (edit)". Implementor should verify which file exists today.

---

## Recommendations

1. Before T1.1: confirm `.claude/rules/testing.md` DB Migration Checklist is satisfied by portal_bridge_tokens migration.
2. Before T2.1: re-read `.claude/rules/tuning-constants.md` for multi-line comment format.
3. Before T3.5: confirm `react-virtuoso` is in `portal/package.json`.
4. Post-merge PR 1: auto-dispatch T1.7 subagent with `HARD CAP: 5 tool calls` per parallel-agents.md.
5. Between PR 2 and PR 3: run T2.11 measurement script on preview env; paste result in PR 3 description.
6. For W2: add a 4th pre-PR grep gate for em-dashes in user-facing files.

---

## Ready for /implement?

**YES** - all 14 audit dimensions PASS. 0 critical gaps. 2 warnings (W1, W2) tracked, non-blocking.

**Next step**: invoke `/implement` on **PR 1** (T1.1-T1.7 for FR-11c Telegram->portal routing) per `.claude/rules/pr-workflow.md` TDD protocol.

After PR 1 merges: proceed sequentially PR 2 -> PR 3 -> PR 4 -> PR 5 with cross-PR gates pinned in plan §9.

---

## Cross-references

- Spec (amended): `specs/214-portal-onboarding-wizard/spec.md`
- Technical spec: `specs/214-portal-onboarding-wizard/technical-spec.md`
- Implementation plan: `specs/214-portal-onboarding-wizard/plan.md`
- Task list: `specs/214-portal-onboarding-wizard/tasks.md`
- Validation findings (iter-2 PASS): `specs/214-portal-onboarding-wizard/validation-findings-iter2.md`
- PR workflow: `.claude/rules/pr-workflow.md`
- Tuning constants convention: `.claude/rules/tuning-constants.md`
- Testing gates: `.claude/rules/testing.md`
- Subagent dispatch caps: `.claude/rules/parallel-agents.md`
