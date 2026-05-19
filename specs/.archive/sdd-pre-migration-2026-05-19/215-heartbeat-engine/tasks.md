---
feature: 215-heartbeat-engine
phase: 1
created: 2026-04-17
status: Draft
sources:
  spec: specs/215-heartbeat-engine/spec.md
  plan: specs/215-heartbeat-engine/plan.md
---

# Tasks: Spec 215 Heartbeat Engine, Phase 1 (User-Story View)

> Re-organization of `plan.md` task breakdown by user story (US-1..US-4 = Phase 1 P1). Each task is the same task referenced in plan.md (T-IDs preserved); this view shows which user story each task contributes to + execution order per story.
>
> **TDD enforcement**: per `.claude/CLAUDE.md` SDD enforcement #4, write FAILING tests FIRST, commit tests separately from implementation. Two commits minimum per user story.

---

## US-1: Daily life arc generation (P1)

**Spec ACs**: AC-FR2-001 (plan exists with both forms), AC-FR2-002 (idempotent), AC-FR8-001 (game_over filter)

**Tasks** (TDD order):

| # | Task | File(s) | Commit |
|---|---|---|---|
| 1 | T2.1 — Migration nikita_daily_plan + RLS | supabase/migrations/{ts}_create_nikita_daily_plan.sql | tests-only |
| 2 | T2.4 — RED: integration tests for repo (4 tests) | tests/db/test_heartbeat_repository_integration.py | tests-only |
| 3 | T2.2 — SQLAlchemy model | nikita/db/models/heartbeat.py | impl |
| 4 | T2.3 — Repository | nikita/db/repositories/heartbeat_repository.py | impl |
| 5 | T2.4 — GREEN: integration tests pass | (verify only) | n/a |
| 6 | T3.2 — RED: planner unit tests | tests/heartbeat/test_planner.py | tests-only |
| 7 | T3.1 — LLM-driven daily-arc planner | nikita/heartbeat/planner.py | impl |
| 8 | T3.2 — GREEN: planner tests pass | (verify) | n/a |
| 9 | T4.5 — RED: /tasks/generate-daily-arcs tests | tests/api/routes/test_tasks_generate_daily_arcs.py | tests-only |
| 10 | T4.1 — JobName enum entries | nikita/db/models/job_execution.py | impl |
| 11 | T4.3 — POST /tasks/generate-daily-arcs handler | nikita/api/routes/tasks.py | impl |
| 12 | T4.5 — GREEN: endpoint tests pass | (verify) | n/a |
| 13 | T5.2 — RED: settings tests | tests/config/test_settings.py | tests-only |
| 14 | T5.1 — settings.py additions | nikita/config/settings.py | impl |
| 15 | T5.2 — GREEN: settings tests pass | (verify) | n/a |

**Independent test (after US-1 complete)**: trigger /tasks/generate-daily-arcs for 5 throwaway players in staging, query persisted plans, assert each non-game_over has exactly one plan with both arc_json + narrative_text.

**Estimated effort**: ~28 hours (T2.1 4h + T2.2 2h + T2.3 4h + T2.4 4h + T3.1 8h + T3.2 4h + T4.1 1h + T4.3 6h + T4.5 5h + T5.1 2h + T5.2 2h, with TDD overhead included).

---

## US-2: Safety-net hourly heartbeat (P1)

**Spec ACs**: AC-FR5-001 (1 invocation per active player per hour), AC-FR9-001 (idempotency), AC-FR10-001 (concurrent-update lock), AC-FR13-001 (catch-up drop)

**Tasks** (TDD order; reuses T1.x, T2.x, T3.x, T5.x from US-1):

| # | Task | File(s) | Commit |
|---|---|---|---|
| 1 | T1.3 — RED: tuning-constants regression tests | tests/heartbeat/test_intensity.py | tests-only |
| 2 | T1.1 — Refactor MC validator constants for import | scripts/models/heartbeat_intensity_mc.py | impl |
| 3 | T1.2 — Production heartbeat module | nikita/heartbeat/intensity.py | impl |
| 4 | T1.3 — GREEN: regression tests pass | (verify) | n/a |
| 5 | T1.4 — Model documentation | docs/models/heartbeat-intensity.md | docs |
| 6 | T4.4 — RED: /tasks/heartbeat tests (10 tests covering idempotency, concurrency, fan-out cap, telegram_id filter, game-state filter, dispatcher delegation) | tests/api/routes/test_tasks_heartbeat.py | tests-only |
| 7 | T4.2 — POST /tasks/heartbeat handler | nikita/api/routes/tasks.py | impl |
| 8 | T4.4 — GREEN: all 10 tests pass | (verify) | n/a |
| 9 | T6.1 — Register pg_cron jobs (after deploy) | (Supabase MCP execute_sql) | infra |
| 10 | T6.2 — Cron verification script | scripts/check_heartbeat_cron_jobs.py | infra |

**Independent test (after US-2 complete)**: deploy with feature flag on, observe over 24h that each active test player receives at least 24 invocations of /tasks/heartbeat. Idempotency probe: two manual invocations within 55 min → second returns "skipped". Concurrency probe: two parallel asyncio tasks → only one acquires lock per user.

**Estimated effort**: ~32 hours (T1.1 3h + T1.2 5h + T1.3 4h + T1.4 4h + T4.2 8h + T4.4 6h + T6.1 2h + T6.2 2h with TDD overhead).

---

## US-3: Plan-driven proactive touchpoint (P1)

**Spec ACs**: AC-FR6-001 (touchpoint references plan element), AC-FR6-002 (rate limit honored), AC-FR7-001 (delegates to dispatcher)

**Tasks**:

| # | Task | File(s) | Commit |
|---|---|---|---|
| 1 | (Reuses T4.2 from US-2 — heartbeat handler delegates to TouchpointEngine.evaluate_and_schedule_for_user with trigger_reason="heartbeat") | nikita/api/routes/tasks.py | (already covered) |
| 2 | T3.3 — LLM-judge eval harness for AC-FR6-001 | tests/heartbeat/test_arc_reference_llm_judge.py + fixtures | impl |
| 3 | (Verify dispatcher rate-limit honored — implicit in TouchpointEngine, no new code) | (verify only) | n/a |

**Independent test**: 24h observation across 5 controlled players in staging; query touchpoints generated; assert each player receives between 1-3 touchpoints; LLM judge confirms each references plan element with success rate ≥0.80.

**Estimated effort**: ~5 hours (T3.3 5h; rest reused from US-1 + US-2).

---

## US-4: Live-versus-offline parity validator (P1)

**Spec ACs**: AC-FR16-001 (per-chapter report), AC-FR16-002 (alerts on divergence), AC-FR16-003 (artifact on pass)

**Tasks** (TDD order):

| # | Task | File(s) | Commit |
|---|---|---|---|
| 1 | T7.2 — RED: synthetic-drift detection tests | tests/scripts/test_heartbeat_live_parity.py | tests-only |
| 2 | T7.1 — Live parity script | scripts/models/heartbeat_live_parity.py | impl |
| 3 | T7.2 — GREEN: drift tests pass | (verify) | n/a |
| 4 | T7.3 — GitHub Actions nightly workflow | .github/workflows/heartbeat-parity-nightly.yml | infra |

**Independent test**: inject synthetic drift into a test cohort; run validator; assert detects drift + alerts. Restore baseline; rerun; assert pass.

**Estimated effort**: ~12 hours (T7.1 6h + T7.2 4h + T7.3 2h).

---

## Cross-Story: Portal admin observability + docs

These are NOT P1 user stories themselves but are part of the Phase 1 contract for "we can SEE what's happening" (FR-016 observability + research-lab visualization parity with Spec 210 pattern).

| # | Task | File(s) | Commit |
|---|---|---|---|
| 1 | T8.1 — Portal admin recharts page | portal/src/app/admin/research-lab/heartbeat/page.tsx | impl |
| 2 | T8.2 — Playwright rendering test | portal/e2e/admin-heartbeat-page.spec.ts | tests |
| 3 | T9.1 — README + memory updates | memory/integrations.md, memory/architecture.md, memory/game-mechanics.md | docs |
| 4 | T9.2 — validation-findings.md skeleton | specs/215-heartbeat-engine/validation-findings.md | docs |

**Estimated effort**: ~15 hours (T8.1 8h + T8.2 3h + T9.1 3h + T9.2 1h).

---

## Total Phase 1 Effort

- US-1: 28 hours
- US-2: 32 hours
- US-3: 5 hours
- US-4: 12 hours
- Cross-Story: 15 hours
- **Total: ~92 hours** (factors in TDD overhead + verification + buffer)

Plan.md cited 52-78 hours as "raw task time"; this view adds the TDD discipline overhead (write tests first, separate commits, verification cycles, fixture authoring) which roughly adds 15-30%.

---

## Story Independence Verification

Per spec.md Article VII (User-Story-Centric Organization):

- ✅ US-1 (planner) is independently shippable: completes daily-arc generation, persists to DB, no runtime tick yet
- ✅ US-2 (heartbeat tick) depends on US-1 (needs plans to load) — sequential
- ✅ US-3 (proactive touchpoint) depends on US-1 (plan to reference) + US-2 (handler that triggers it)
- ✅ US-4 (parity validator) depends on US-2 (production data to compare) — sequential
- All can be implemented as separate PRs per `.claude/rules/pr-workflow.md` (max 400 lines per PR; some may need multi-PR splits)

---

## Suggested PR Sequence

Per `.claude/rules/pr-workflow.md`:

1. **PR 215-A**: Foundation — T2.1 + T2.2 + T2.3 + T2.4 + T5.1 + T5.2 (DB layer + settings; ≤400 LOC)
2. **PR 215-B**: Math production module — T1.1 + T1.2 + T1.3 + T1.4 (intensity.py + tests + docs; ≤400 LOC)
3. **PR 215-C**: Planner — T3.1 + T3.2 + T3.3 + fixtures (LLM planner; ≤400 LOC)
4. **PR 215-D**: API endpoints — T4.1 + T4.2 + T4.3 + T4.4 + T4.5 (heartbeat + generate-arcs; possibly split if >400 LOC)
5. **PR 215-E**: Cron registration + verification — T6.1 + T6.2 (infra-only PR; small)
6. **PR 215-F**: Parity validator — T7.1 + T7.2 + T7.3 (script + workflow; ≤400 LOC)
7. **PR 215-G**: Portal page — T8.1 + T8.2 (frontend; standalone)
8. **PR 215-H**: Docs + manifest — T9.1 + T9.2 + T9.3 + T9.4 (memory updates + validation findings + coverage gate CI + pre-PR grep gate)

Each PR follows: branch → TDD → /qa-review → 0 findings → squash merge → smoke test → next PR.

### MANDATORY pre-PR checklist (per CLAUDE.md SDD enforcement + GATE 2 iter-1 H-12 fix)

BEFORE running `gh pr create` on ANY of the 8 PRs above, the implementor MUST:

1. **Run pre-PR test-quality grep gate**: `bash scripts/pre_pr_test_quality_grep.sh` (created by T9.4); MUST exit 0
   - Gate 1: zero-assertion `async def test_*` shells in changed test files
   - Gate 2: PII (name|age|occupation|phone) in `logger.<level>(...%s...)` format strings
   - Gate 3: raw `cache_key=` in logs (outside `cache_key_hash|sha256` context)
   - If any gate fails → fix the offending file BEFORE opening PR (one extra commit)
2. **Run local coverage check**: `uv run pytest <changed test files> --cov=nikita.heartbeat --cov-fail-under=80` MUST exit 0 (per T9.3 CI gate; verify locally first to avoid CI red)
3. **Verify no PII in newly-added log statements**: manual rg sweep `rg "logger\.(info|warning|error|exception|debug)" <changed .py files>` for any `user.name`, `user.email`, `user.telegram_id`, `arc_json`, `narrative_text`, `bayesian_state` references → use `user_id_hash[:8]` instead
4. **Run dispatched `/qa-review --pr N`** after PR opens; iterate to 0 findings ALL severities (per `.claude/rules/pr-workflow.md` step 4)

Skipping any of these 4 steps invalidates the PR's compliance with GATE 2 commitments.

### Hold-the-line note (per GATE 2 iter-1 Decision D, user 2026-04-18)

When fixing or extending Phase 1 PRs, do NOT pull forward Phase 2/3 work even when adjacent files are touched. Specifically the following stay deferred:

- `users.timezone` IANA column → Phase 2
- `ModalityState` enum (vacation/sick/normal/crunch) → Phase 2
- Weekend rave-mode ACTIVITY_PARAMS overlay → Phase 2
- `users.bayesian_state` JSONB column + admin-RLS pattern + `is_admin()` SQL helper → Phase 3 (P3 will own first definition; P1 documents the deferral)

Scope creep on these items is a Behavior 5 violation per `~/.claude/rules/operating-principles.md`. If genuinely required to fix a P1 finding, file a separate spec amendment and re-run GATE 2.

---

## Phase 1 Definition of Done

- [ ] All 8 PRs merged to master
- [ ] All Phase 1 acceptance criteria from plan.md "Phase 1 Acceptance" section pass
- [ ] 24h E2E observation in staging produces 1-3 touchpoints per active player
- [ ] LLM-judge eval ≥0.80 pass rate (T3.3)
- [ ] MC validator + parity validator both exit 0
- [ ] No PII in any heartbeat-emitted log line (manual grep audit)
- [ ] `validation-findings.md` shows user approval checkbox checked
- [ ] ROADMAP.md updated with Spec 215 status COMPLETE
- [ ] Memory files (integrations.md, architecture.md) reflect new heartbeat subsystem

---

**Tasks-version**: 1.0
**Status**: Draft → ready for /audit (Phase 7) with mandatory 6-validator GATE 2
**Next**: `/audit 215-heartbeat-engine` invokes 6 parallel sdd-*-validator agents per `.claude/CLAUDE.md` SDD enforcement #3
