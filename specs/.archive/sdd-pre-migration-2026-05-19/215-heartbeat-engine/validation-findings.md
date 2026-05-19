---
feature: 215-heartbeat-engine
phase: 7-audit
created: 2026-04-17
updated: 2026-04-18
status: ITER_2_PASS_PENDING_USER_APPROVAL
gate: GATE_2
iteration: 2
---

# GATE 2 Validation Findings: Spec 215 Heartbeat Engine

> **Per CLAUDE.md SDD enforcement #7+#8**: This is the durable manifest of all 6-validator findings. CRITICAL/HIGH require GH issues + spec fix + re-validation. MEDIUM require accept/defer decisions. LOW logged here for record. User must check the approval box at the bottom before /implement may run.

## Aggregate Tally

| Severity | Count | Action Required |
|---|---|---|
| CRITICAL | 1 | Block: GH issue + fix in spec/plan + re-validate |
| HIGH | 13 | Block: GH issue + fix in spec/plan + re-validate |
| MEDIUM | 23 | Decide accept/defer per item; log decision here |
| LOW | 14 | Logged for record; non-blocking |
| **Total** | **51** | |

Validator agent IDs (replay if needed; do NOT re-read raw outputs per orchestration rule Behavior 7):
- API: `add1fa26e927a2565` — verdict NEEDS_FIXES
- Architecture: `ab719679b958aa951` — verdict PASS
- Auth: `a889d5a7b681ea008` — verdict NEEDS_FIXES
- Data Layer: `a57ab41b98ac77ec6` — verdict NEEDS_FIXES
- Frontend: `a0db375ee2c17a48d` — verdict PASS (with 4 MEDIUM advisories)
- Testing: `ad3a6ebb0533cf982` — verdict NEEDS_FIXES

**Overall gate verdict**: NEEDS_FIXES (4/6 validators returned NEEDS_FIXES; gate fails on first iteration)

---

## CRITICAL findings (block until fixed)

### C-1: No Pydantic `response_model` on heartbeat or generate-daily-arcs endpoints
- **Source**: API validator
- **Location**: plan.md T4.2 + T4.3 acceptance criteria return bare `dict`
- **Impact**: OpenAPI doc ambiguous; FastAPI cannot validate response shape; clients (cron + monitoring) cannot type-check
- **Fix**: Add Pydantic models `HeartbeatResponse` + `GenerateDailyArcsResponse` with discriminated `status: Literal["ok","skipped","disabled","circuit_breaker_open","error"]` field. Add `response_model=` and `responses={401: ..., 503: ...}` to decorators
- **GH issue**: TODO file before re-validation
- **Spec/plan amendment**: required in plan.md T4.2 + T4.3

---

## HIGH findings (block until fixed)

### H-1: Cost circuit breaker returns 200 with status field instead of HTTP 503
- **Source**: API validator
- **Location**: plan.md T4.3 AC-T4.3-002
- **Impact**: Degraded service hidden behind 200; cron + alerting cannot detect via status code
- **Fix**: Return HTTP 503 with `Retry-After: <seconds-until-midnight-UTC>` header on circuit-breaker engagement
- **Spec/plan amendment**: T4.3 AC-002 + spec.md FR-014

### H-2: No structured error envelope; existing pattern leaks raw exception text
- **Source**: API validator
- **Location**: plan.md T4.2/T4.3, inherits from `apply_daily_decay` antipattern
- **Impact**: PII leak risk via `str(e)` in error response (FR-015 violation)
- **Fix**: Define uniform error envelope `{"error": "<code>", "detail": "<redacted>"}`; explicitly redact `str(e)` before returning
- **Spec/plan amendment**: spec.md FR-015 strengthening + plan.md T4.2/T4.3 ACs

### H-3: Idempotency window of 55 min is fragile
- **Source**: API validator
- **Location**: plan.md T4.2 AC-T4.2-002
- **Impact**: Cron drift to T+56 min runs as duplicate (violates AC-FR9-001 zero-side-effect)
- **Fix**: Use deterministic idempotency key `Idempotency-Key: heartbeat-{YYYY-MM-DD-HH-UTC}` per-tick rather than time-window
- **Spec/plan amendment**: plan.md T4.2 AC-002

### H-4: No request body schema specified
- **Source**: API validator
- **Location**: plan.md T4.2/T4.3
- **Impact**: FastAPI auto-doc ambiguous on body-less cron triggers
- **Fix**: Document explicitly via `Body(None)` or note "no body" in OpenAPI `description`
- **Spec/plan amendment**: T4.2 + T4.3 ACs

### H-5: RLS policy only specs SELECT side; UPDATE/DELETE/INSERT coverage missing
- **Source**: Auth + Data Layer validators (concurring)
- **Location**: plan.md T2.1 AC-T2.1-004
- **Impact**: Implicit-deny for authenticated role works today but is unauditable; future endpoint running as user role could escalate
- **Fix**: Use `FOR ALL ... USING (...) WITH CHECK (...)` OR add separate `FOR INSERT/UPDATE/DELETE` policies. Mirror `backstory_cache` migration's explicit `FOR ALL ... USING (false) WITH CHECK (false)` for deny-by-default-to-authenticated pattern
- **Spec/plan amendment**: T2.1 AC-004 expanded

### H-6: FR-015 admin-only-read pattern not pre-spec'd in Phase 1
- **Source**: Auth validator
- **Location**: spec.md FR-015 + plan.md scope
- **Impact**: Phase 3 (FR-018 `users.bayesian_state`) will need to invent admin-RLS helper from scratch
- **Fix**: Either (a) add Phase 1 task to define `is_admin()` SQL helper + admin-RLS policy template, OR (b) add explicit deferral note in plan.md "Out-of-Scope for Phase 1" calling out Phase 3 dependency
- **Spec/plan amendment**: scope section

### H-7: FK lacks ON DELETE CASCADE
- **Source**: Data Layer validator
- **Location**: plan.md T2.1 AC-T2.1-001
- **Impact**: Orphaned `nikita_daily_plan` rows on user deletion violate referential integrity
- **Fix**: `user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE`
- **Spec/plan amendment**: T2.1 AC-001

### H-8: Missing CHECK constraint on `plan_date` validity
- **Source**: Data Layer validator
- **Location**: plan.md T2.1
- **Impact**: Buggy planner could write plan_date='1970-01-01' or '2099-01-01' silently
- **Fix**: Add `CHECK (plan_date BETWEEN '2020-01-01' AND CURRENT_DATE + INTERVAL '7 days')`
- **Spec/plan amendment**: T2.1 new AC

### H-9: Midnight-UTC race condition unaddressed
- **Source**: Data Layer validator
- **Location**: plan.md T4.2/T4.3 + spec.md FR-008
- **Impact**: Heartbeat at 23:55 UTC loads plan for date D; at 00:05 UTC loads plan for D+1 which doesn't exist until 5 AM next day
- **Fix**: T4.2 fallback to D-1 plan if D plan absent before 5 AM; document in T3.1 docstring
- **Spec/plan amendment**: T4.2 new AC + T3.1 docstring

### H-10: Missing partial index for cron daily-arc query pattern
- **Source**: Data Layer validator
- **Location**: plan.md T2.1
- **Impact**: Bulk daily sweeps scan table unnecessarily; not catastrophic at MVP volumes (≤100 users) but documented as deferred
- **Fix**: Add `CREATE INDEX idx_nikita_daily_plan_recent ON nikita_daily_plan (plan_date) WHERE plan_date >= CURRENT_DATE - 1` OR document deferral rationale in T2.1
- **Spec/plan amendment**: T2.1 new AC

### H-11: Coverage gate ≥80% asserted in spec but never enforced in CI
- **Source**: Testing validator
- **Location**: spec.md NFR Observability + plan.md (no coverage task) + tasks.md (no coverage gate)
- **Impact**: NFR is unfalsifiable; coverage can drift below 80% silently
- **Fix**: Add task T9.x (or extend T7.3 nightly): configure `pytest --cov=nikita.heartbeat --cov-fail-under=80` in pre-merge CI; reference in PR-workflow rule
- **Spec/plan amendment**: new task T9.3 in plan.md + tasks.md; spec.md NFR clarification

### H-12: Pre-PR grep gates from `.claude/rules/testing.md` not wired into tasks.md PR sequence
- **Source**: Testing validator
- **Location**: plan.md "Suggested PR Sequence", tasks.md PR sequence
- **Impact**: Per-test ACs prevent zero-assert shells but no orchestrator-level grep before review; miss the 3 gates (zero-assertion shells, PII in log %s, raw cache_key)
- **Fix**: Add explicit "pre-PR grep gate" step in tasks.md per-PR checklist that runs the 3 greps from testing.md before opening PR
- **Spec/plan amendment**: tasks.md PR sequence checklist

### H-13: Phase 3 admin-RLS pattern absent (counts as parallel HIGH from Auth)
- See H-6 (consolidated)

---

## MEDIUM findings (decide accept/defer per item)

### M-1: Auth uses string compare, not constant-time `hmac.compare_digest`
- **Source**: API validator (timing-attack risk)
- **Location**: nikita/api/routes/tasks.py:69 (existing pattern Spec 215 inherits)
- **Decision**: **DEFER** to a separate hardening spec. Pre-existing across 6 cron jobs; fixing it here is scope-creep. File GH issue with `severity:medium label:security`.

### M-2: Missing OpenAPI tags/summary/description on new endpoints
- **Source**: API validator
- **Decision**: **ACCEPT** — add `tags=["tasks","heartbeat"]` + summary in plan.md T4.2/T4.3 (5-min cleanup, in scope)

### M-3: Missing explicit `status_code=200` and `responses={503: ...}` declarations
- **Source**: API validator
- **Decision**: **ACCEPT** — addressed by C-1 + H-1 fixes; mostly redundant once those land

### M-4: Advisory-lock collision via Python `hash()` per-process random
- **Source**: API + Architecture validators (concurring)
- **Decision**: **ACCEPT** — switch to `int.from_bytes(hashlib.sha256(user_id.bytes).digest()[:8], 'big', signed=True)` for stable cross-instance keys; tighten T4.2 AC-003

### M-5: Catch-up policy data source (`last_invocation_at`) undefined
- **Source**: API validator
- **Decision**: **ACCEPT** — pin to `JobExecution.completed_at` filtered by job_name='heartbeat' AND user_id=X; tighten T4.2 AC-008

### M-6: TouchpointEngine method existence not verified pre-implementation
- **Source**: Architecture validator
- **Decision**: **ACCEPT** — add 5-min grep precondition before T4.2 starts; verify `nikita/touchpoints/engine.py:523-595` actually has `evaluate_and_schedule_for_user` (Wave 1 codebase-intel cited it; spot-verify)

### M-7: Single-source-of-truth direction unconventional (production imports from scripts/)
- **Source**: Architecture validator
- **Decision**: **DEFER** — acknowledge in T1.2 docstring; revisit in Phase 1.5 if friction surfaces. Acceptable for P1 throwaway per Plan v4 R7

### M-8: Cost circuit breaker state location ambiguous (in-memory dies on Cloud Run scale-to-zero)
- **Source**: Architecture validator
- **Decision**: **ACCEPT** — pin to DB-backed counter; create `daily_cost_ledger` table OR reuse `JobExecution.metadata`; update T4.3 AC-002

### M-9: PII-in-logs surface area incomplete (T4.5 misses arc_json, narrative_text, posteriors)
- **Source**: Auth validator
- **Decision**: **ACCEPT** — extend T4.4 + T4.5 PII-leak ACs to cover full surface

### M-10: TASK_AUTH_SECRET rotation gotcha 6→8 jobs has no automated guard
- **Source**: Auth validator
- **Decision**: **DEFER** — add to backlog as separate enhancement; reusing existing manual rotation runbook for now. File GH issue with `severity:medium label:infrastructure`

### M-11: asyncpg JSONB codec choice not pinned in plan
- **Source**: Data Layer validator
- **Decision**: **ACCEPT** — add T2.2 AC-004 documenting strategy choice in module docstring

### M-12: Migration timestamp prefix unspecified
- **Source**: Data Layer validator
- **Decision**: **ACCEPT** — pin format `YYYYMMDDHHMMSS` and require `> 20260414213313` in T2.1

### M-13: Missing index on `generated_at` for cost/observability queries
- **Source**: Data Layer validator
- **Decision**: **ACCEPT** — add to T2.1 ACs

### M-14: Phase 3 `users.bayesian_state` migration ordering not documented
- **Source**: Data Layer validator
- **Decision**: **ACCEPT** — add note in plan.md "Out-of-Scope for Phase 1": "Phase 2 timezone column lands before Phase 3 bayesian_state to avoid Phase 3 backfill complexity"

### M-15: NOT NULL on user_id FK missing
- **Source**: Data Layer validator
- **Decision**: **ACCEPT** — already implied by FK but make explicit in T2.1 AC-001 (`user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE`)

### M-16: `@pytest.mark.requires_anthropic_api` lacks dedicated CI workflow
- **Source**: Testing validator
- **Decision**: **ACCEPT** — extend T7.3 OR add new `.github/workflows/heartbeat-llm-judge-nightly.yml`; pick after deciding ANTHROPIC_API_KEY budget

### M-17: T1.3 covers ~4 of ~9 declared `Final` constants
- **Source**: Testing validator
- **Decision**: **ACCEPT** — expand T1.3 ACs to cover all 9 (per `.claude/rules/tuning-constants.md` requires regression-guard PER constant)

### M-18: E2E count misclassified (T3.3 is integration, T7.3 is CI workflow)
- **Source**: Testing validator
- **Decision**: **ACCEPT** — reclassify in plan.md Test Pyramid Distribution; add real automated E2E (24h player-flow simulation via clock-mock) OR document as `/e2e-nikita` skill responsibility

### M-19: AC-FR5-001 24h tick-count test not automated
- **Source**: Testing validator
- **Decision**: **ACCEPT** — add `tests/api/routes/test_tasks_heartbeat.py::test_24h_simulation_invokes_each_active_user_once_per_hour` using `freezegun` clock + 24 ticks

### M-20: Concurrency test (AC-T4.4-008) using parallel asyncio not equivalent to cross-process pg_advisory_xact_lock
- **Source**: Testing validator
- **Decision**: **ACCEPT** — split into unit (lock requested) + integration (cross-connection observation); mark integration `@pytest.mark.integration`

### M-21: Constants parity check between Python + TS is purely manual
- **Source**: Frontend validator
- **Decision**: **ACCEPT** — emit JSON snapshot from Python at CI time; consume via generated `.ts` file in T8.1; OR add Playwright assertion vs `/api/admin/heartbeat-constants` endpoint

### M-22: T8.2 a11y-gate scope mismatch (admin routes currently SKIPPED in template)
- **Source**: Frontend validator
- **Decision**: **ACCEPT** — extend `portal/e2e/a11y-gate.spec.ts` to add admin Playwright project with `E2E_AUTH_BYPASS=true E2E_AUTH_ROLE=admin`; tighten T8.2 AC-004

### M-23: dev-server-monitoring.md compliance unspecified for T8.2
- **Source**: Frontend validator
- **Decision**: **ACCEPT** — add explicit AC: "T8.2 collects Turbopack stdout via `webServer.stdout` capture AND filters Playwright console for `error|warning|hydrat`"

### M-24: Tailwind/inline-style carve-out not documented
- **Source**: Frontend validator
- **Decision**: **ACCEPT** — add comment in T8.1 acknowledging research-lab pages are exempt from portal Tailwind/shadcn convention (matches response-timing/page.tsx:7-10 precedent)

---

## LOW findings (logged for record; non-blocking)

L-1 to L-14 grouped by validator (omitted detail — replay agent IDs above for full text):

- **API**: idempotency response shape with `Idempotency-Key` echo header; `X-RateLimit-Reset` header on circuit-breaker engagement
- **Architecture**: Phase 2 module sub-package naming reservation; advisory-lock hash truncation collision (overlaps M-4); JobName enum location grep verification (overlaps M-6); PII-redaction Phase-3 scope acknowledgment
- **Auth**: spec wording underspecifies "Bearer not JWT" (clarification only); FR-007 negative test missing (assert handler does NOT call ScheduledEventRepository.create directly)
- **Data Layer**: subquery form for `auth.uid()` already correct (preventive); service_role policy explicit-skip rationale comment in migration body
- **Frontend**: T8.1 auth-enforcement curl probe tied to verification block
- **Testing**: catch-up policy AC test missing; alert-emission half of FR-014 not asserted; a11y-gate only color-contrast (not full WCAG)

---

## Decision Required from User

Per CLAUDE.md SDD enforcement #7, the GATE 2 Analyze-Fix Loop requires user decision on:

### Decision A: How to handle CRITICAL + HIGH findings
- **Option A1**: Fix all 14 (1 CRIT + 13 HIGH) inline in spec.md/plan.md/tasks.md; re-dispatch 6 validators (iteration 2 of max 3); proceed to /implement only on PASS
- **Option A2**: Defer some HIGH items to a "Phase 1.5 hardening spec" (e.g., M-1 timing-attack auth, M-10 TASK_AUTH_SECRET rotation guard) — but C-1 + the data-layer + auth + idempotency HIGHs are too central to defer
- **Recommended**: A1 (full fix loop iteration 2)

### Decision B: GH issue creation
- 1 CRITICAL + 13 HIGH ⇒ 14 GH issues per CLAUDE.md SDD enforcement #7
- **Option B1**: Create all 14 issues now (5-10 min)
- **Option B2**: Create 1 umbrella issue "GATE 2 iter-1 findings" with 14 sub-tasks
- **Recommended**: B2 (umbrella + sub-tasks; less GH noise)

### Decision C: Iteration cadence
- After fixes applied, re-dispatch the same 6 validators (iteration 2)
- Max 3 iterations per gate; on iteration 3 failure, escalate (CLAUDE.md #7f)
- **Recommended**: re-dispatch after each major fix batch, not per-finding

### Decision D: Scope reconfirmation
- 4/6 validators flagged Phase 1 vs Phase 2/3 boundary issues (e.g., admin-RLS pre-spec'ing for Phase 3, weekend-mode deferral, timezone deferral)
- Some MEDIUMs propose pulling Phase 2 work forward (admin-RLS pattern, modality enum). Doing so violates Behavior 5 scope discipline
- **Recommended**: hold the line on Phase 1 / Phase 2 / Phase 3 boundaries; document Phase 1 limitations as known constraints

---

## User Approval Checkbox (ITER-1 — APPROVED 2026-04-18)

- [x] I have reviewed all 51 findings (1 CRITICAL + 13 HIGH + 23 MEDIUM + 14 LOW)
- [x] I approve fixing CRITICAL + HIGH per Decision A1 (full fix iter-2)
- [x] I approve GH issue strategy per Decision B1 (single umbrella issue: GH #323)
- [x] I approve iteration cadence per Decision C1 (single iter-2 dispatch)
- [x] I approve Phase 1/2/3 boundary discipline per Decision D (hold-the-line)
- [x] **I approve proceeding to GATE 2 iteration 2 (re-validate after fixes)** — DONE 2026-04-18

---

# ITER-2 Results (2026-04-18)

## ALL 6 VALIDATORS RETURNED PASS

| Validator | Iter-1 | Iter-2 | Resolution |
|---|---|---|---|
| API | NEEDS_FIXES (1C+4H+5M) | **PASS** | All resolved; 3 NEW LOW findings logged below |
| Architecture | PASS (3M) | **PASS** | M-6 partial via TDD compensation; M-7 + M-8 fully resolved |
| Auth | NEEDS_FIXES (2H+2M) | **PASS** | All resolved; H-6 phase-deferred per Decision D |
| Data Layer | NEEDS_FIXES (5H+5M) | **PASS** | All resolved; RLS syntax audit clean |
| Frontend | PASS (4M) | **PASS** | 4 MEDIUMs unchanged (ACCEPTed iter-1) |
| Testing | NEEDS_FIXES (2H+5M) | **PASS** | All resolved; pyramid + coverage gate + grep gate complete |

**Iter-2 verdict**: 0 CRITICAL + 0 HIGH + 0 NEW MEDIUM + 3 NEW LOW. All iter-1 CRITICAL+HIGH (14/14) RESOLVED. /implement CAN UNBLOCK pending final user approval.

Iter-2 validator agent IDs (replay if needed):
- API: `acfe022be2a985190` — PASS
- Architecture: `a2278f06e4fb5c666` — PASS
- Auth: `a0b45e2bbddf02dd9` — PASS
- Data Layer: `a7ad7bea848a2c08f` — PASS
- Frontend: `a651fbdec377c600a` — PASS
- Testing: `a6fc660a199f79fb2` — PASS

## Iter-2 NEW LOW findings (logged for record; non-blocking)

### N-1: T4.1 implicit method addition lacks dedicated subtask
- **Source**: API validator iter-2
- **Issue**: AC-T4.2-002 references `JobExecutionRepository.has_execution_with_key()` and notes "added in T4.1 (or co-shipped as T4.1.1)" but no T4.1.1 task is enumerated in plan.md
- **Decision**: ACCEPT — implementor will add the method as part of T4.1; if scope grows beyond enum extension, split into T4.1.1 at implementation time

### N-2: Pydantic schema models location undefined
- **Source**: API validator iter-2
- **Issue**: `ErrorEnvelope`, `HeartbeatResponse`, `GenerateDailyArcsResponse` referenced in ACs but no task defines their location (e.g., `nikita/api/schemas/heartbeat.py`)
- **Decision**: ACCEPT — implementor will create `nikita/api/schemas/heartbeat.py` as part of T4.2/T4.3; trivial scope

### N-3: heartbeat_cost_ledger table lacks discrete migration task
- **Source**: API + Architecture validators (concurring)
- **Issue**: AC-T4.3-002 says "NEW table heartbeat_cost_ledger OR JobExecution.metadata-aggregated query"; if table chosen, no T2.x migration task defined
- **Decision**: ACCEPT with implementation-time decision: implementor picks ONE strategy (table OR JobExecution.metadata) and either (a) adds T2.5 migration task if table, or (b) documents reuse of JobExecution.metadata in plan.md if aggregated query

### N-4: M-6 preflight grep not added as explicit T4.2 step (Architecture iter-2)
- **Source**: Architecture validator iter-2
- **Issue**: TouchpointEngine method existence verified only via behavioral test AC-T4.4-007 (TDD compensation), not explicit grep precondition
- **Decision**: ACCEPT — TDD test catches missing/wrong-signature method loudly; grep would be belt-and-suspenders. Acceptable.

---

## FINAL USER APPROVAL CHECKBOX (ITER-2)

The 14 CRITICAL+HIGH iter-1 findings are RESOLVED per all 6 sdd-*-validators iter-2 PASS. Only 4 NEW LOW findings logged (non-blocking, all ACCEPTed). `/implement` is gated on this final approval per CLAUDE.md SDD enforcement #2 + #8.

- [x] I have reviewed iter-2 results: all 6 validators PASS, 14/14 CRIT+HIGH resolved, 4 NEW LOW logged + ACCEPTed
- [x] I confirm GH umbrella #323 can be closed (sub-tasks reflect iter-2 fixes)
- [x] **I approve proceeding to /implement (SDD Phase 8) for Phase 1 MVE (Spec 215)** — APPROVED 2026-04-18; first scope = PR 215-A only (Foundation: DB layer + settings)

GATE 2 PASSED. /implement UNBLOCKED.

---

**Manifest version**: 2.0 (iter-2 results appended)
**Status**: ITER_2_PASS_PENDING_USER_APPROVAL
**Next action (after user approval)**: invoke /implement with TDD-per-user-story workflow → 8 PRs (215-A through 215-H) per tasks.md PR sequence → each PR through /qa-review to 0 findings → squash merge → smoke test → next PR
