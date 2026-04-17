---
feature: 215-heartbeat-engine
phase: 1
created: 2026-04-17
status: Draft
sources:
  spec: specs/215-heartbeat-engine/spec.md
  brief: .claude/plans/delightful-orbiting-ladybug.md
  math: .claude/plans/delightful-orbiting-ladybug.md  # Plan v3 Appendix A, line ~701
  mc-validator: scripts/models/heartbeat_intensity_mc.py
---

# Implementation Plan: Spec 215 Heartbeat Engine, Phase 1 MVE

> **Scope**: Phase 1 only (MVE). Phase 2 (self-scheduling, Hawkes) and Phase 3 (Bayesian, reflection) get separate plans after Phase 1 monitors clean for 7 days (Phase 2) and 14 days (Phase 3).
>
> **Architecture**: Approach A1 (new endpoint + new `nikita_daily_plan` table) per Plan v4 §4.1, scored 7.75 vs alternatives by pr-approach-evaluator.
>
> **Math model authority**: Plan v3 Appendix A (von Mises mixture × ν_a baseline). Phase 1 ships the math infrastructure offline (`nikita/heartbeat/intensity.py` + `scripts/models/heartbeat_intensity_mc.py`); the runtime planner is rule-based + LLM-narrative for Phase 1, with Hawkes self-scheduling deferred to Phase 2.

---

## Architecture Overview

```
DAILY 5AM (cron `nikita-generate-daily-arcs`)
  FOR each active non-game-over non-won player:
    LLM(Haiku 4.5) generates structured arc + narrative → nikita_daily_plan
    Cost-circuit-breaker gates aggregate spend (FR-014)
                     │
                     ▼
HOURLY (cron `nikita-heartbeat-hourly`)
  has_recent_execution(JobName.HEARTBEAT, 55 min) guard (FR-009/R2)
  pg_advisory_xact_lock(user_id::bigint) per-user (FR-010/R3)
  FOR each active player (limit 40, telegram_id NOT NULL):
    Load today's plan
    IF current plan step is due AND outreach condition met:
      delegate to TouchpointEngine.evaluate_and_schedule_for_user(
        user_id, trigger_reason='heartbeat'
      )  # NEVER write scheduled_events directly (FR-007/R1)
    Drop heartbeats older than 6h on resume (FR-013)
                     │
                     ▼
EVERY 5 MIN (existing cron `nikita-deliver` — unchanged)
  drains scheduled_events (touchpoint rows produced by TouchpointEngine)

NIGHTLY (CI / GitHub Actions, NOT pg_cron)
  scripts/models/heartbeat_live_parity.py --since-days 7 --p-threshold 0.01
  KS-test production heartbeat distribution vs MC predictions per chapter
  Exit 1 + alert on divergence (FR-016)
```

---

## Task Breakdown

Total estimated effort: **52-78 hours** across 9 task groups, all P1, all sized 2-8 hours.

Dependency graph at end of doc.

---

### Group 1: Math model production module

#### T1.1: Refactor MC validator to expose constants for production import
- **ID**: T1.1
- **Owner**: implementor agent
- **Estimated**: 3 hours
- **Dependencies**: None
- **Files**:
  - EDIT: `scripts/models/heartbeat_intensity_mc.py` (add `__all__` for constants; ensure ACTIVITY_PARAMS, DIRICHLET_PRIOR, EPSILON_FLOOR, NU_PER_ACTIVITY, CHAPTER_MULT, T_HALF_HRS, BETA, ALPHA, R_MAX are module-level Final and importable)
- **Acceptance Criteria**:
  - **AC-T1.1-001**: `python -c "from scripts.models.heartbeat_intensity_mc import EPSILON_FLOOR, BETA, ACTIVITY_PARAMS"` exits 0
  - **AC-T1.1-002**: All exported constants are typed `Final` per `.claude/rules/tuning-constants.md`
  - **AC-T1.1-003**: `uv run python scripts/models/heartbeat_intensity_mc.py` still exits 0 with all 8 sanity assertions PASS
- **Source**: Plan v4.3 deliverable #9 (clarified: KEEP IN PLACE, treat as P1 source-of-truth)

#### T1.2: Create production heartbeat module
- **ID**: T1.2
- **Owner**: implementor agent
- **Estimated**: 5 hours
- **Dependencies**: T1.1
- **Files**:
  - CREATE: `nikita/heartbeat/__init__.py` (empty for now)
  - CREATE: `nikita/heartbeat/intensity.py` (~200 LOC; imports constants from MC script; provides `activity_distribution(t_hours, day_of_week=0)`, `lambda_baseline(t, chapter, engagement)`, `compute_hawkes_residual(R_prev, dt, beta=BETA)`, `update_hawkes_residual(R, alpha_k, w)`; class `HeartbeatIntensity` wrapping with per-instance random.Random)
- **Acceptance Criteria**:
  - **AC-T1.2-001**: `activity_distribution(0.0)` returns dict with keys = ACTIVITIES and values summing to 1.0 ± 1e-6
  - **AC-T1.2-002**: `min(activity_distribution(t).values()) >= EPSILON_FLOOR / len(ACTIVITIES)` for all t in [0, 24)
  - **AC-T1.2-003**: `lambda_baseline(3.0, chapter=3, engagement="in_zone") > 0` (sleep trough still positive)
  - **AC-T1.2-004**: Module docstring contains the math formula from Plan v3 §A.5
- **Source**: Plan v4.3 deliverable #2 + R7 throwaway acknowledgment

#### T1.3: Tuning-constants regression tests
- **ID**: T1.3
- **Owner**: implementor agent
- **Estimated**: 4 hours
- **Dependencies**: T1.2
- **Files**:
  - CREATE: `tests/heartbeat/__init__.py`
  - CREATE: `tests/heartbeat/test_intensity.py` (~150 LOC; one regression test per Final constant per `.claude/rules/tuning-constants.md`)
- **Acceptance Criteria** (UPDATED iter-2 per M-17: regression test PER constant, not sample):
  - **AC-T1.3-001**: Test file imports every constant from `nikita.heartbeat.intensity` AND `scripts.models.heartbeat_intensity_mc`; asserts they are the same object (single source of truth)
  - **AC-T1.3-002**: `test_epsilon_floor_value` asserts `EPSILON_FLOOR == 0.03`
  - **AC-T1.3-003**: `test_chapter_mult_monotonic` asserts CHAPTER_MULT[1] > CHAPTER_MULT[2] > CHAPTER_MULT[3] > CHAPTER_MULT[4] > CHAPTER_MULT[5] (early infatuation > settled)
  - **AC-T1.3-004**: `test_branching_ratio_stable` asserts `ALPHA["user_msg"]*1.2 + ALPHA["game_event"]*1.0 + ALPHA["internal"]*1.0 < 1.0`
  - **AC-T1.3-005**: `test_t_half_value` asserts `T_HALF_HRS == 3.0`
  - **AC-T1.3-006**: `test_beta_derived_from_t_half` asserts `abs(BETA - math.log(2) / T_HALF_HRS) < 1e-9`
  - **AC-T1.3-007**: `test_r_max_value` asserts `R_MAX == 1.5` with rationale comment citing branching-ratio cap
  - **AC-T1.3-008**: `test_nu_per_activity_values` asserts each NU_PER_ACTIVITY[a] matches Plan v3 §A.2 v2 table (sleep=0.05, work=0.30, eating=0.30, personal=1.00, social=0.40)
  - **AC-T1.3-009**: `test_dirichlet_prior_sums_to_100` asserts `sum(DIRICHLET_PRIOR.values()) == 100` (weekday baseline normalization)
  - **AC-T1.3-010**: `test_activity_params_keys_match_dirichlet` asserts `set(ACTIVITY_PARAMS.keys()) == set(DIRICHLET_PRIOR.keys())` (5 activities consistent across all tables)
  - **AC-T1.3-011**: `test_activity_params_kappas_positive` asserts every κ in every component > 0 (von Mises requirement)
  - **AC-T1.3-012**: `test_alpha_positive` asserts every ALPHA value > 0 (Hawkes excitation requirement)
  - **AC-T1.3-013**: `pytest tests/heartbeat/test_intensity.py -v` all 12 tests pass

#### T1.4: Model documentation
- **ID**: T1.4
- **Owner**: implementor agent
- **Estimated**: 4 hours
- **Dependencies**: T1.2
- **Files**:
  - CREATE: `docs/models/heartbeat-intensity.md` (~250 LOC, mirrors `docs/models/response-timing.md` template per `.claude/rules/stochastic-models.md` step 4)
- **Acceptance Criteria**:
  - **AC-T1.4-001**: Doc contains all 6 layers from Plan v3 Appendix A (§A.1 through §A.6)
  - **AC-T1.4-002**: Doc references the 7 PNG plots already in `docs/models/heartbeat-*.png` with relative links
  - **AC-T1.4-003**: Doc cites at least 5 academic sources (Sparklen 2025, tick library, Park et al., TiDeH, scipy)
  - **AC-T1.4-004**: Pitfalls section lists at least 5 production gotchas from Wave 1 research (branching drift, thinning bound staleness, intensity underflow, Mardia-Jupp bias, novel-territory burden)

---

### Group 2: Database layer

#### T2.1: Migration for nikita_daily_plan table
- **ID**: T2.1
- **Owner**: implementor agent
- **Estimated**: 4 hours
- **Dependencies**: None
- **Files**:
  - CREATE: `supabase/migrations/{TIMESTAMP}_create_nikita_daily_plan.sql`
- **Acceptance Criteria** (UPDATED iter-2 per GATE 2 fixes H-5, H-7, H-8, H-10, M-12, M-13, M-15):
  - **AC-T2.1-001**: Table columns include explicit nullability + FK CASCADE + plan_date validity CHECK:
    ```sql
    CREATE TABLE IF NOT EXISTS public.nikita_daily_plan (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
      plan_date DATE NOT NULL CHECK (plan_date BETWEEN '2020-01-01' AND CURRENT_DATE + INTERVAL '7 days'),
      arc_json JSONB NOT NULL,
      narrative_text TEXT NOT NULL,
      generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      model_used TEXT
    );
    ```
  - **AC-T2.1-002**: Unique index `idx_nikita_daily_plan_user_date` on `(user_id, plan_date)` for idempotency (FR-002 AC-FR2-002)
  - **AC-T2.1-003**: `ALTER TABLE public.nikita_daily_plan ENABLE ROW LEVEL SECURITY;`
  - **AC-T2.1-004** (H-5 fix): RLS policies use explicit per-verb form for unambiguous intent + WITH CHECK clauses to prevent silent privilege escalation:
    ```sql
    -- Authenticated users: read own plans only
    CREATE POLICY nikita_daily_plan_select_own ON public.nikita_daily_plan
      FOR SELECT TO authenticated
      USING (user_id = (SELECT auth.uid()));
    -- Authenticated users: deny all writes (service-role only)
    CREATE POLICY nikita_daily_plan_no_write_authenticated ON public.nikita_daily_plan
      FOR ALL TO authenticated
      USING (false) WITH CHECK (false);
    -- Anon: deny everything
    CREATE POLICY nikita_daily_plan_no_anon ON public.nikita_daily_plan
      FOR ALL TO anon
      USING (false) WITH CHECK (false);
    ```
  - **AC-T2.1-005**: NO explicit service_role policy (per Wave 1 ref-doc finding: service_role bypasses RLS by default; explicit policy misleading). Migration body MUST include comment: `-- Service-role token bypasses RLS entirely (standard Supabase pattern). DO NOT add a service_role policy here.`
  - **AC-T2.1-006**: Migration applied via `mcp__supabase__apply_migration`; `mcp__supabase__list_policies('public', 'nikita_daily_plan')` shows exactly 3 policies (select_own + no_write_authenticated + no_anon)
  - **AC-T2.1-007** (H-10 fix): Partial index for cron daily-arc query pattern: `CREATE INDEX idx_nikita_daily_plan_recent ON public.nikita_daily_plan (plan_date) WHERE plan_date >= CURRENT_DATE - INTERVAL '1 day';`
  - **AC-T2.1-008** (M-13 fix): Index on `generated_at` for cost/observability queries: `CREATE INDEX idx_nikita_daily_plan_generated_at ON public.nikita_daily_plan (generated_at DESC);`
  - **AC-T2.1-009** (M-12 fix): Migration filename uses format `YYYYMMDDHHMMSS_create_nikita_daily_plan.sql` and timestamp MUST be greater than `20260414213313` (latest existing migration in `supabase/migrations/`).
- **Source**: Plan v4 R5 regression guard + `.claude/rules/testing.md` DB Migration Checklist + GATE 2 iter-1 fixes H-5/H-7/H-8/H-10/M-12/M-13/M-15
- **Reference**: `supabase/migrations/20260414213313_add_profile_fields_and_backstory_cache.sql` mirror (use `FOR ALL ... USING (false) WITH CHECK (false)` pattern)

#### T2.2: SQLAlchemy model
- **ID**: T2.2
- **Owner**: implementor agent
- **Estimated**: 2 hours
- **Dependencies**: T2.1
- **Files**:
  - CREATE: `nikita/db/models/heartbeat.py` (`NikitaDailyPlan(Base, TimestampMixin)`)
- **Acceptance Criteria**:
  - **AC-T2.2-001**: Model has all columns from T2.1 with correct types (JSONB → `Mapped[dict]`, DATE → `Mapped[date]`, etc.)
  - **AC-T2.2-002**: `arc_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)` matches existing `users.onboarding_profile` JSONB pattern (per Wave 1 codebase-intel)
  - **AC-T2.2-003**: Type imports correct (`from sqlalchemy.dialects.postgresql import JSONB`, `from datetime import date`)
  - **AC-T2.2-004** (M-11 fix): Module docstring documents the asyncpg JSONB strategy choice EXPLICITLY: "This module uses SQLAlchemy native dict↔JSONB mapping via `Mapped[dict] + mapped_column(JSONB)`. Do NOT call `json.dumps()` on `arc_json` before assignment — that produces double-encoded jsonb (PR #319 burn). The `JSONB` type adapter handles serialization." A module-level comment at the top references this rule + the PR #319 root-cause commit.

#### T2.3: Repository
- **ID**: T2.3
- **Owner**: implementor agent
- **Estimated**: 4 hours
- **Dependencies**: T2.2
- **Files**:
  - CREATE: `nikita/db/repositories/heartbeat_repository.py` (`NikitaDailyPlanRepository(BaseRepository[NikitaDailyPlan])`)
- **Acceptance Criteria**:
  - **AC-T2.3-001**: `async def get_plan_for_date(user_id: UUID, plan_date: date) -> NikitaDailyPlan | None`
  - **AC-T2.3-002**: `async def upsert_plan(user_id, plan_date, arc_json, narrative_text, model_used) -> NikitaDailyPlan` (ON CONFLICT (user_id, plan_date) DO UPDATE for idempotency per FR-002 AC-FR2-002)
  - **AC-T2.3-003**: Repository follows existing `nikita/db/repositories/user_repository.py` pattern (constructor takes session, methods async)

#### T2.4: Real-DB integration test (R5 regression guard)
- **ID**: T2.4
- **Owner**: implementor agent
- **Estimated**: 4 hours
- **Dependencies**: T2.1, T2.2, T2.3
- **Files**:
  - CREATE: `tests/db/test_heartbeat_repository_integration.py`
- **Acceptance Criteria**:
  - **AC-T2.4-001**: `test_arc_json_stores_native_dict_not_string` — inserts dict, queries via raw SQL `SELECT jsonb_typeof(arc_json)`, asserts `'object'` not `'string'` (PR #319 burn regression guard per Plan v4 R5)
  - **AC-T2.4-002**: `test_upsert_idempotency` — calls upsert twice with same (user_id, plan_date), asserts only 1 row exists, asserts second call updates `generated_at` not creates duplicate
  - **AC-T2.4-003**: `test_rls_user_scoped_read` — switches role to authenticated user A, attempts SELECT on user B's plan, asserts 0 rows returned
  - **AC-T2.4-004**: `test_rls_service_role_full_access` — service-role client SELECTs all rows, asserts works (FR-008 game-state respect tested at endpoint layer)
  - **AC-T2.4-005**: All 4 tests marked `@pytest.mark.integration` (skipped in CI without DB; runnable locally via `pytest -m integration`)
- **Source**: Plan v4 R5 + `.claude/rules/testing.md` "Tests That Don't Test" anti-pattern

---

### Group 3: Planner + LLM integration

#### T3.1: LLM-driven daily-arc planner
- **ID**: T3.1
- **Owner**: implementor agent
- **Estimated**: 8 hours
- **Dependencies**: T2.3
- **Files**:
  - CREATE: `nikita/heartbeat/planner.py` (~200 LOC)
- **Acceptance Criteria**:
  - **AC-T3.1-001**: Pydantic structured-output schema: `class DailyArc(BaseModel)` with fields `steps: list[ArcStep]`, `narrative: str`. `ArcStep` has `at: time`, `state: str`, `action: ArcAction | None`. `ArcAction` has `type: Literal["schedule_touchpoint_if"]`, `condition: Literal["no_contact_today", "morning_block", "evening_block"]`
  - **AC-T3.1-002**: `async def generate_daily_arc(user: User, target_date: date, llm_client: AnthropicClient) -> DailyArc` uses Haiku 4.5 (per OD1) with explicit model ID `claude-haiku-4-5-20251001`
  - **AC-T3.1-003**: Module docstring annotates "Phase 1 throwaway schema per Plan v4 R7; Phase 2 introduces parallel continuous-distribution table"
  - **AC-T3.1-004**: Cost-tracking: every LLM call records token usage to a metrics counter readable by FR-014 circuit breaker
  - **AC-T3.1-005**: Game-state filter: caller (T4.3) filters out won + game_over users; planner asserts `user.status == "active"` and raises if not (defense in depth)

#### T3.2: Planner unit tests
- **ID**: T3.2
- **Owner**: implementor agent
- **Estimated**: 4 hours
- **Dependencies**: T3.1
- **Files**:
  - CREATE: `tests/heartbeat/test_planner.py`
- **Acceptance Criteria**:
  - **AC-T3.2-001**: `test_generate_daily_arc_happy_path` — mocks Anthropic API, verifies returns `DailyArc` with ≥6 steps and non-empty narrative
  - **AC-T3.2-002**: `test_generate_daily_arc_rejects_inactive_user` — passes a `game_over` user, asserts raises `ValueError`
  - **AC-T3.2-003**: `test_arc_steps_have_increasing_times` — verifies steps are sorted by `at`
  - **AC-T3.2-004**: `test_cost_tracking_increments` — mocks API to return token usage, verifies counter incremented
  - **AC-T3.2-005**: All tests follow `tests/conftest.py` async-mock patterns; zero-assertion shells forbidden per `.claude/rules/testing.md`

#### T3.3: LLM-judge eval harness for AC-FR6-001
- **ID**: T3.3
- **Owner**: implementor agent
- **Estimated**: 5 hours
- **Dependencies**: T3.1
- **Files**:
  - CREATE: `tests/heartbeat/test_arc_reference_llm_judge.py`
  - CREATE: `tests/heartbeat/fixtures/arc_reference_judge_prompt.txt`
- **Acceptance Criteria**:
  - **AC-T3.3-001**: Test fixture `arc_reference_judge_prompt.txt` is a Claude Haiku prompt template scoring 0-1 whether a touchpoint message references ≥1 element of a daily arc
  - **AC-T3.3-002**: Test queries last 24h of touchpoints + matching `nikita_daily_plan.arc_json`, invokes judge, asserts `pass_rate >= 0.80` (4/5)
  - **AC-T3.3-003**: Test marked `@pytest.mark.requires_anthropic_api`; CI runs nightly via separate workflow
  - **AC-T3.3-004**: `uv run pytest tests/heartbeat/test_arc_reference_llm_judge.py -v` runs without import errors when Anthropic API key absent (skip with marker)
- **Source**: Spec 215 AC-FR6-001 + Plan v4 fix #4 (concrete falsifiable test)

---

### Group 4: API endpoints

#### T4.1: JobName enum entries
- **ID**: T4.1
- **Owner**: implementor agent
- **Estimated**: 1 hour
- **Dependencies**: None
- **Files**:
  - EDIT: `nikita/db/models/job_execution.py` (add `HEARTBEAT = "heartbeat"` and `GENERATE_DAILY_ARCS = "generate_daily_arcs"` to `JobName` enum)
- **Acceptance Criteria**:
  - **AC-T4.1-001**: `JobName.HEARTBEAT.value == "heartbeat"`
  - **AC-T4.1-002**: `JobName.GENERATE_DAILY_ARCS.value == "generate_daily_arcs"`
  - **AC-T4.1-003**: Existing `JobExecutionRepository.has_recent_execution()` accepts these values without code changes (test by reading repository code)

#### T4.2: POST /tasks/heartbeat handler
- **ID**: T4.2
- **Owner**: implementor agent
- **Estimated**: 8 hours
- **Dependencies**: T1.2, T2.3, T3.1, T4.1, T5.1
- **Files**:
  - EDIT: `nikita/api/routes/tasks.py` (add `@router.post("/heartbeat")` handler)
- **Acceptance Criteria** (UPDATED iter-2 per C-1, H-3, H-4, M-4, M-5, H-9):
  - **AC-T4.2-001**: Handler signature uses Pydantic response_model + explicit body-less declaration:
    ```python
    @router.post(
        "/heartbeat",
        response_model=HeartbeatResponse,
        responses={401: {"model": ErrorEnvelope}, 503: {"model": ErrorEnvelope}},
        tags=["tasks", "heartbeat"],
        summary="Per-tick heartbeat handler (pg_cron only; no body)",
    )
    async def heartbeat_handler(
        _body: None = Body(None),
        _: None = Depends(verify_task_secret),
    ) -> HeartbeatResponse:
    ```
    where `HeartbeatResponse` and `ErrorEnvelope` are Pydantic models defined at top of module (C-1, H-4 fix).
  - **AC-T4.2-002** (H-3 fix): Idempotency uses deterministic per-tick key, NOT a fragile time window. First statement:
    ```python
    tick_key = f"heartbeat-{datetime.now(UTC).strftime('%Y-%m-%dT%H')}"  # one key per UTC hour
    if await job_repo.has_execution_with_key(JobName.HEARTBEAT, tick_key):
        return HeartbeatResponse(status="skipped", reason="duplicate_tick", tick_key=tick_key)
    ```
    `JobExecutionRepository.has_execution_with_key()` is added in T4.1 (or co-shipped as T4.1.1). This guarantees zero side-effect on legitimate next-tick boundary regardless of cron drift.
  - **AC-T4.2-003** (M-4 fix): Per-user advisory lock uses stable SHA256-derived key, NOT Python `hash()` (per-process random):
    ```python
    import hashlib
    user_lock_key = int.from_bytes(
        hashlib.sha256(user.id.bytes).digest()[:8], 'big', signed=True
    )
    await session.execute(
        text("SELECT pg_advisory_xact_lock(:k)"), {"k": user_lock_key}
    )
    ```
  - **AC-T4.2-004**: Active-user filter via `UserRepository.get_active_users_for_heartbeat()` (NEW method mirroring `get_active_users_for_decay()` at user_repository.py:373; excludes `won` + `game_over` per FR-008/OD4)
  - **AC-T4.2-005**: Fan-out cap: `users = users[:40]` (R4: leave headroom for /tasks/deliver limit=50)
  - **AC-T4.2-006**: Pre-filter `[u for u in users if u.telegram_id is not None]`
  - **AC-T4.2-007**: Heartbeat MUST call `TouchpointEngine.evaluate_and_schedule_for_user(user_id=u.id, trigger_reason="heartbeat")` (FR-007/R1; NO direct scheduled_events insert)
  - **AC-T4.2-008** (M-5 fix): Catch-up policy data source pinned to `JobExecution`: drop user iteration if `last_invocation = await job_repo.last_completed_for_user(JobName.HEARTBEAT, user.id); if last_invocation and (now - last_invocation.completed_at) > timedelta(hours=6): logger.info("[HEARTBEAT] dropped stale user", extra={"user_id_hash": hashlib.sha256(user.id.bytes).hexdigest()[:8]}); continue`. NO PII per FR-015.
  - **AC-T4.2-009** (H-9 fix): Midnight-UTC race fallback — when loading today's plan, fallback to D-1 if D plan absent before 5 AM UTC (the daily-arc cron runs at 5 AM): `plan = await plan_repo.get_for_user_date(user.id, today); if plan is None and now.hour < 5: plan = await plan_repo.get_for_user_date(user.id, today - timedelta(days=1))`
  - **AC-T4.2-010**: Feature flag check: `if not settings.heartbeat_engine_enabled: return HeartbeatResponse(status="disabled")`
  - **AC-T4.2-011**: Error path uses redacted envelope (H-2): `except Exception as e: logger.exception("heartbeat error", extra={"error_class": type(e).__name__}); return JSONResponse(status_code=500, content=ErrorEnvelope(error="heartbeat_failed", detail="see logs").dict())`. NEVER includes `str(e)` in response body.

#### T4.3: POST /tasks/generate-daily-arcs handler
- **ID**: T4.3
- **Owner**: implementor agent
- **Estimated**: 6 hours
- **Dependencies**: T2.3, T3.1, T4.1, T5.1
- **Files**:
  - EDIT: `nikita/api/routes/tasks.py` (add `@router.post("/generate-daily-arcs")` handler)
- **Acceptance Criteria** (UPDATED iter-2 per C-1, H-1, H-2, H-4, M-8):
  - **AC-T4.3-001** (C-1, H-4 fix): Pydantic response_model + body-less declaration:
    ```python
    @router.post(
        "/generate-daily-arcs",
        response_model=GenerateDailyArcsResponse,
        responses={401: {"model": ErrorEnvelope}, 503: {"model": ErrorEnvelope}, 500: {"model": ErrorEnvelope}},
        tags=["tasks", "heartbeat"],
        summary="Daily 5am LLM-driven arc generation (pg_cron only; no body)",
    )
    async def generate_daily_arcs_handler(
        _body: None = Body(None),
        _: None = Depends(verify_task_secret),
    ) -> GenerateDailyArcsResponse | JSONResponse:
    ```
    Delegates per-user to `planner.generate_daily_arc(user, target_date=date.today())` then `repo.upsert_plan(...)`.
  - **AC-T4.3-002** (H-1 + M-8 fix): Cost circuit breaker uses durable DB-backed counter (NOT in-memory; Cloud Run scale-to-zero would lose it). Tracks aggregate USD spent today via NEW table `heartbeat_cost_ledger` (date PK, total_usd FLOAT, last_updated TIMESTAMPTZ) OR via `JobExecution.metadata`-aggregated query. When ceiling reached:
    ```python
    if await cost_ledger.get_today_spend_usd() >= settings.heartbeat_cost_circuit_breaker_usd_per_day:
        seconds_to_midnight = (datetime.combine(date.today() + timedelta(days=1), time(), UTC) - datetime.now(UTC)).seconds
        return JSONResponse(
            status_code=503,
            content=ErrorEnvelope(error="circuit_breaker_open", detail="daily LLM cost ceiling reached").dict(),
            headers={"Retry-After": str(seconds_to_midnight)},
        )
    # Also emit structured alert
    if just_engaged: logger.warning("circuit_breaker_engaged", extra={"spent_usd": current_spend, "ceiling_usd": settings.heartbeat_cost_circuit_breaker_usd_per_day})
    ```
  - **AC-T4.3-003**: Game-state filter: only `status == "active"` users (FR-008/OD4)
  - **AC-T4.3-004**: Idempotency: `repo.upsert_plan` enforces unique (user_id, plan_date) per T2.3 AC-T2.3-002
  - **AC-T4.3-005**: Logger emits per-user start/end with `user_id_hash` (sha256[:8]) only (FR-015 no PII)
  - **AC-T4.3-006**: Returns Pydantic `GenerateDailyArcsResponse(status="ok", users_planned=N, users_skipped=M, cost_usd=X)` on success
  - **AC-T4.3-007** (H-2 fix): Error path uses redacted envelope, NEVER `str(e)` in response: `except Exception as e: logger.exception("generate-daily-arcs error", extra={"error_class": type(e).__name__}); return JSONResponse(status_code=500, content=ErrorEnvelope(error="generate_arcs_failed", detail="see logs").dict())`

#### T4.4: Tests for /tasks/heartbeat
- **ID**: T4.4
- **Owner**: implementor agent
- **Estimated**: 6 hours
- **Dependencies**: T4.2
- **Files**:
  - CREATE: `tests/api/routes/test_tasks_heartbeat.py`
- **Acceptance Criteria** (UPDATED iter-2 per M-9 PII expansion, M-19 24h test, M-20 concurrency split, L-? FR-007 negative test):
  - **AC-T4.4-001**: `test_heartbeat_disabled_when_flag_off` — flag=False → returns `HeartbeatResponse(status="disabled")`, zero side effects
  - **AC-T4.4-002**: `test_heartbeat_idempotency_dedups_per_tick_key` — first call with tick_key=`heartbeat-2026-04-18T14` succeeds; second call with same tick_key returns `status="skipped" reason="duplicate_tick"`; THIRD call with tick_key=`heartbeat-2026-04-18T15` (next hour) succeeds (proves deterministic key, not fragile time window)
  - **AC-T4.4-003**: `test_heartbeat_filters_game_over_users` — set 1 of 5 users to `game_over` → only 4 reach TouchpointEngine
  - **AC-T4.4-004**: `test_heartbeat_filters_won_users` — set 1 user to `won` → not in active filter
  - **AC-T4.4-005**: `test_heartbeat_filters_telegram_id_null` — user without telegram_id excluded
  - **AC-T4.4-006**: `test_heartbeat_fans_out_max_40` — 100 active users → only 40 processed
  - **AC-T4.4-007**: `test_heartbeat_delegates_to_touchpoint_engine` — verify `TouchpointEngine.evaluate_and_schedule_for_user` called with `trigger_reason="heartbeat"` (per FR-007/R1)
  - **AC-T4.4-008** (FR-007 negative-test fix): `test_heartbeat_does_NOT_call_scheduled_event_repository_directly` — patch `ScheduledEventRepository.create_event`; assert never called by heartbeat handler (regression guard against future refactor bypassing dispatcher rate limits)
  - **AC-T4.4-009** (M-20 fix): `test_heartbeat_advisory_lock_requested_per_user` (UNIT) — assert SQL `pg_advisory_xact_lock(:k)` is invoked per-user with stable SHA256-derived key. `test_heartbeat_advisory_lock_observed_across_connections` (INTEGRATION, marked `@pytest.mark.integration`) — uses 2 separate asyncpg connections, asserts second blocks until first txn ends. asyncio-only mocking insufficient because lock serializes across connections, not coroutines.
  - **AC-T4.4-010**: `test_heartbeat_catch_up_drops_stale_user` (FR-013 + L-? fix) — set `JobExecution.completed_at` to 8h ago for one user; assert that user dropped from iteration AND drop count emitted as `logger.info("[HEARTBEAT] dropped stale user", ...)` log record AND log record contains `user_id_hash` ONLY (no full user_id, no name, no telegram_id)
  - **AC-T4.4-011** (M-9 PII surface expansion): `test_heartbeat_no_pii_in_logs` — captures all log records emitted during a heartbeat invocation; asserts NONE contain ANY of: full `user_id` (UUID), `user.name`, `user.telegram_id`, raw `arc_json` payload, narrative_text content, planner LLM prompt body, Hawkes residual `R_now` value (Phase 2 prep), bayesian_state values (Phase 3 prep)
  - **AC-T4.4-012** (M-19 fix): `test_heartbeat_24h_simulation_one_per_active_user_per_hour` — uses `freezegun.freeze_time` to advance through 24 hourly ticks; with 5 active users; asserts each user receives exactly 24 invocations (FR-005 AC-FR5-001 falsifiable instead of staging-only manual observation)
  - **AC-T4.4-013**: ALL tests have ≥1 `assert` or `assert_*` call; no zero-assertion shells per `.claude/rules/testing.md`
  - **AC-T4.4-014**: Unit tests run via `pytest tests/api/routes/test_tasks_heartbeat.py -v`; integration test (AC-009 second half) runs via `pytest -m integration tests/api/routes/test_tasks_heartbeat.py`

#### T4.5: Tests for /tasks/generate-daily-arcs
- **ID**: T4.5
- **Owner**: implementor agent
- **Estimated**: 5 hours
- **Dependencies**: T4.3
- **Files**:
  - CREATE: `tests/api/routes/test_tasks_generate_daily_arcs.py`
- **Acceptance Criteria** (UPDATED iter-2 per H-1, H-2, M-9, L-2):
  - **AC-T4.5-001**: `test_generate_arcs_creates_one_per_active_user` — 5 active + 1 game_over → 5 plans created
  - **AC-T4.5-002**: `test_generate_arcs_idempotent_within_day` — calls twice on same day → 0 duplicate rows (upsert)
  - **AC-T4.5-003** (H-1 + L-2 fix): `test_generate_arcs_circuit_breaker_returns_503` — set ceiling to $0.01, run on 5 users; assert response status_code=503, response includes `Retry-After` header pointing to next midnight UTC, response body matches ErrorEnvelope(error="circuit_breaker_open", ...), AND `logger.warning("circuit_breaker_engaged", ...)` log record emitted
  - **AC-T4.5-004** (M-9 PII surface expansion): `test_generate_arcs_no_pii_in_logs` — captures all log records, asserts NONE contain ANY of: `user.name`, `user.email`, `user.telegram_id`, raw `arc_json` payload, narrative_text content, planner LLM prompt body (FR-015 strengthened)
  - **AC-T4.5-005** (H-2 fix): `test_generate_arcs_error_path_uses_redacted_envelope` — mock planner to raise; assert response status_code=500, body matches ErrorEnvelope(error="generate_arcs_failed", detail="see logs"); assert response body does NOT contain `str(exception)` content
  - **AC-T4.5-006**: ALL tests have non-zero assertions per `.claude/rules/testing.md`

---

### Group 5: Settings + feature flags

#### T5.1: settings.py additions
- **ID**: T5.1
- **Owner**: implementor agent
- **Estimated**: 2 hours
- **Dependencies**: None
- **Files**:
  - EDIT: `nikita/config/settings.py` (add 2 fields, mirroring `momentum_enabled` at lines 243-250)
- **Acceptance Criteria**:
  - **AC-T5.1-001**: `heartbeat_engine_enabled: bool = Field(default=False, description="Spec 215: enable Heartbeat Engine continuous self-driven life-simulation loop. Rollback: HEARTBEAT_ENGINE_ENABLED=false (no-op all heartbeat code paths).")`
  - **AC-T5.1-002**: `heartbeat_cost_circuit_breaker_usd_per_day: float = Field(default=50.0, description="Spec 215 FR-014: daily aggregate USD ceiling for heartbeat LLM ops. Engages graceful degradation when reached.")`
  - **AC-T5.1-003**: Both fields readable from env: `HEARTBEAT_ENGINE_ENABLED=true` flips flag (per Pydantic Settings v2 documented case-insensitive default)
  - **AC-T5.1-004**: `get_settings.cache_clear()` works after env mutation (singleton pattern, per `tests/conftest.py`)

#### T5.2: Settings tests update
- **ID**: T5.2
- **Owner**: implementor agent
- **Estimated**: 2 hours
- **Dependencies**: T5.1
- **Files**:
  - EDIT: `tests/config/test_settings.py` (add 2 new tests)
- **Acceptance Criteria**:
  - **AC-T5.2-001**: `test_heartbeat_engine_enabled_default_false` — `Settings()` has `.heartbeat_engine_enabled == False` (rollback contract per FR-020)
  - **AC-T5.2-002**: `test_heartbeat_cost_circuit_breaker_default_50` — default value matches plan; mutation via `monkeypatch.setenv("HEARTBEAT_COST_CIRCUIT_BREAKER_USD_PER_DAY", "100.0")` reflects after `cache_clear()`

---

### Group 6: Cron jobs

#### T6.1: pg_cron registration
- **ID**: T6.1
- **Owner**: implementor agent (via mcp__supabase__execute_sql)
- **Estimated**: 2 hours
- **Dependencies**: T4.2, T4.3 deployed to Cloud Run
- **Operation**: Register 2 new pg_cron jobs via Supabase MCP (NOT migration — pg_cron jobs live in Supabase dashboard per Wave 1 codebase-intel)
- **Acceptance Criteria**:
  - **AC-T6.1-001**: `nikita-heartbeat-hourly` registered with schedule `0 * * * *` and SQL invoking `net.http_post(url := 'https://nikita-api-1040094048579.us-central1.run.app/tasks/heartbeat', headers := '{"Authorization": "Bearer <TASK_AUTH_SECRET>"}'::jsonb)`
  - **AC-T6.1-002**: `nikita-generate-daily-arcs` registered with schedule `0 5 * * *` (5 AM UTC daily) invoking `/tasks/generate-daily-arcs`
  - **AC-T6.1-003**: `mcp__supabase__execute_sql("SELECT jobname FROM cron.job WHERE jobname IN ('nikita-heartbeat-hourly', 'nikita-generate-daily-arcs')")` returns 2 rows
  - **AC-T6.1-004**: Project CLAUDE.md gotcha (TASK_AUTH_SECRET sync — 6 cron jobs → 8 cron jobs) updated in `memory/integrations.md`
- **Source**: Plan v4 R6 (UTC-only Phase 1; Phase 2 honors per-user TZ)

#### T6.2: Cron registration verification script
- **ID**: T6.2
- **Owner**: implementor agent
- **Estimated**: 2 hours
- **Dependencies**: T6.1
- **Files**:
  - CREATE: `scripts/check_heartbeat_cron_jobs.py` (~30 LOC)
- **Acceptance Criteria**:
  - **AC-T6.2-001**: Script queries `cron.job` via Supabase Python client; asserts 2 expected job names exist
  - **AC-T6.2-002**: Script exits 0 on success, 1 with diagnostic on missing jobs
  - **AC-T6.2-003**: Script invocable as `uv run python scripts/check_heartbeat_cron_jobs.py` from CI

---

### Group 7: Parity validator (FR-016)

#### T7.1: Live-vs-MC parity script
- **ID**: T7.1
- **Owner**: implementor agent
- **Estimated**: 6 hours
- **Dependencies**: T1.1
- **Files**:
  - CREATE: `scripts/models/heartbeat_live_parity.py` (~200 LOC)
- **Acceptance Criteria**:
  - **AC-T7.1-001**: CLI accepts `--since-days N` (default 7) and `--p-threshold X` (default 0.01)
  - **AC-T7.1-002**: Pulls last N days of `scheduled_events` rows where dispatcher attributed source = heartbeat (via metadata column or inferred via dispatcher trace)
  - **AC-T7.1-003**: For each chapter, computes empirical inter-wake distribution + runs `scipy.stats.kstest(observed, mc_samples)` against MC predictions from `nikita.heartbeat.intensity` constants
  - **AC-T7.1-004**: Exits 0 if all chapters `p > p_threshold`; exits 1 with per-chapter divergence report otherwise
  - **AC-T7.1-005**: Produces artifact `parity-report-{YYYY-MM-DD}.json` with raw stats per chapter
  - **AC-T7.1-006**: NO PII in output — only chapter index + counts + p-values, never user IDs (FR-015)

#### T7.2: Synthetic-drift detection test
- **ID**: T7.2
- **Owner**: implementor agent
- **Estimated**: 4 hours
- **Dependencies**: T7.1
- **Files**:
  - CREATE: `tests/scripts/test_heartbeat_live_parity.py`
- **Acceptance Criteria**:
  - **AC-T7.2-001**: `test_parity_passes_on_baseline` — synthetic data drawn from MC model itself → script exits 0
  - **AC-T7.2-002**: `test_parity_detects_drift` — synthetic data with shifted mean → script exits 1, report cites the shifted chapter
  - **AC-T7.2-003**: `test_parity_handles_empty_data` — 0 production rows → exits with diagnostic, not crash

#### T7.3: GitHub Actions nightly workflow
- **ID**: T7.3
- **Owner**: implementor agent
- **Estimated**: 2 hours
- **Dependencies**: T7.1
- **Files**:
  - CREATE: `.github/workflows/heartbeat-parity-nightly.yml`
- **Acceptance Criteria**:
  - **AC-T7.3-001**: Workflow runs on `schedule: cron: '0 9 * * *'` (9 AM UTC daily)
  - **AC-T7.3-002**: Step "parity-check" invokes `uv run python scripts/models/heartbeat_live_parity.py --since-days 7 --p-threshold 0.01`
  - **AC-T7.3-003**: Step "llm-judge" (M-16 fix; same workflow file, separate step) invokes `uv run pytest -m requires_anthropic_api tests/heartbeat/test_arc_reference_llm_judge.py -v`. Requires `ANTHROPIC_API_KEY` GitHub secret. Skipped step (with warning log) if secret absent — never blocks the workflow on missing secret config.
  - **AC-T7.3-004**: On non-zero exit of EITHER step, workflow runs `gh issue create --title "Heartbeat nightly failed: $(date) (parity|llm-judge)" --label "high,test-debt"` to trigger triage; specify which step failed in title
  - **AC-T7.3-005**: Workflow uses existing repo secret for Supabase service role key + `ANTHROPIC_API_KEY` for LLM-judge step
- **Source**: Plan v4 fix #5 + GATE 2 iter-1 M-16 (CI workflow for `@pytest.mark.requires_anthropic_api`)

---

### Group 8: Portal admin page

#### T8.1: Client-side recharts page
- **ID**: T8.1
- **Owner**: implementor agent
- **Estimated**: 8 hours
- **Dependencies**: T1.2 (constants must be stable for in-browser mirror)
- **Files**:
  - CREATE: `portal/src/app/admin/research-lab/heartbeat/page.tsx`
- **Acceptance Criteria**:
  - **AC-T8.1-001**: Mirrors `portal/src/app/admin/research-lab/response-timing/page.tsx` pattern: `"use client"`, design-token const `T = {bg, surface, accent, ...}`, recharts imports, in-browser MC via Box-Muller `function bm()` and explicit von Mises sampler `function vm()`
  - **AC-T8.1-002**: Page renders 7 plots mirroring the existing PNGs: activity-distribution stacked area, baseline-per-chapter, Hawkes scenarios, typical day, silent-vs-chatty, inter-wake distribution, replan effect
  - **AC-T8.1-003**: Interactive sliders for: chapter (1-5), engagement state, ε noise floor, T_half, R_now, day-of-week
  - **AC-T8.1-004**: Constants in TS PRESETS object MUST match Python constants from `nikita/heartbeat/intensity.py` (manually-checked parity per AC-T8.1-005)
  - **AC-T8.1-005**: Page header includes a "Constants parity" section listing TS values vs Python values; visual divergence triggers manual update of TS file
  - **AC-T8.1-006**: NO PNG embedding — all plots computed client-side via recharts (per Wave 1 pattern-scout finding on response-timing/page.tsx)
  - **AC-T8.1-007**: Page route `/admin/research-lab/heartbeat` requires admin role (existing layout enforces; spot-check)

#### T8.2: Playwright rendering test
- **ID**: T8.2
- **Owner**: implementor agent
- **Estimated**: 3 hours
- **Dependencies**: T8.1
- **Files**:
  - CREATE: `portal/e2e/admin-heartbeat-page.spec.ts`
- **Acceptance Criteria**:
  - **AC-T8.2-001**: Test navigates to `/admin/research-lab/heartbeat` with admin auth bypass enabled
  - **AC-T8.2-002**: Asserts ≥7 SVG chart elements present (one per plot)
  - **AC-T8.2-003**: Asserts no console errors (per `.claude/rules/dev-server-monitoring.md`)
  - **AC-T8.2-004**: Asserts a11y gate (color-contrast serious+ violations = 0) per `portal/e2e/a11y-gate.spec.ts` template

---

### Group 9: Documentation + release

#### T9.1: README + memory updates
- **ID**: T9.1
- **Owner**: implementor agent
- **Estimated**: 3 hours
- **Dependencies**: T6.1
- **Files**:
  - EDIT: `memory/integrations.md` (update pg_cron section: 6 → 8 jobs; document TASK_AUTH_SECRET sync impact)
  - EDIT: `memory/architecture.md` (add Heartbeat Engine subsystem block under Domain 3)
  - EDIT: `memory/game-mechanics.md` (mention heartbeat as proactive-touchpoint timing layer)
- **Acceptance Criteria**:
  - **AC-T9.1-001**: `memory/integrations.md` lists nikita-heartbeat-hourly + nikita-generate-daily-arcs in pg_cron table with schedule + endpoint
  - **AC-T9.1-002**: Project CLAUDE.md gotcha (currently "6 HTTP cron jobs") updated to 8 — but only after T6.1 ships
  - **AC-T9.1-003**: `memory/architecture.md` heartbeat block ≤30 lines, references docs/models/heartbeat-intensity.md for math depth

#### T9.2: validation-findings.md skeleton
- **ID**: T9.2
- **Owner**: implementor agent
- **Estimated**: 1 hour
- **Dependencies**: None (created during Phase 7 audit, not implementation)
- **Files**:
  - CREATE: `specs/215-heartbeat-engine/validation-findings.md` (skeleton — populated during /audit GATE 2 per CLAUDE.md SDD enforcement #8)
- **Acceptance Criteria**:
  - **AC-T9.2-001**: File exists with sections: Critical findings (with GH issue links), High findings (with GH issue links), Medium findings (accept/defer decisions), Low findings (logged), User approval checkbox
  - **AC-T9.2-002**: Per CLAUDE.md gate rule: presence of file is mandatory after 6-validator suite completes; absent = gate INCOMPLETE
- **Source**: Plan v4 fix #6 (validation-findings.md mandate)

#### T9.3: Coverage gate CI enforcement (NEW iter-2 per H-11)
- **ID**: T9.3
- **Owner**: implementor agent
- **Estimated**: 3 hours
- **Dependencies**: All test tasks (T1.3, T2.4, T3.2, T3.3, T4.4, T4.5, T7.2)
- **Files**:
  - EDIT: `pyproject.toml` (add `[tool.coverage.run]` section if absent; ensure heartbeat module included)
  - EDIT: `.github/workflows/test.yml` (or current pre-merge CI definition) — add coverage step
  - CREATE: `.github/workflows/heartbeat-coverage-gate.yml` if no existing test.yml exists
- **Acceptance Criteria**:
  - **AC-T9.3-001**: Pre-merge CI step runs `uv run pytest tests/heartbeat/ tests/api/routes/test_tasks_heartbeat.py tests/api/routes/test_tasks_generate_daily_arcs.py --cov=nikita.heartbeat --cov=nikita.db.repositories.heartbeat_repository --cov-report=term-missing --cov-fail-under=80`
  - **AC-T9.3-002**: CI fails (red status check) when coverage on `nikita.heartbeat.*` falls below 80% line coverage
  - **AC-T9.3-003**: Coverage scope is precisely the new module (NOT entire `nikita/`); avoids dragging legacy under-tested modules into Phase 1 gate
  - **AC-T9.3-004**: Verification: locally run with `--cov-fail-under=99` to force failure → assert non-zero exit; restore to 80 → exit 0
- **Source**: GATE 2 iter-1 H-11 (testing validator: NFR ≥80% coverage was unfalsifiable without CI gate)

#### T9.4: Pre-PR grep gates wired into PR workflow (NEW iter-2 per H-12)
- **ID**: T9.4
- **Owner**: implementor agent
- **Estimated**: 2 hours
- **Dependencies**: None
- **Files**:
  - EDIT: `tasks.md` "Suggested PR Sequence" section to include grep gate
  - CREATE: `scripts/pre_pr_test_quality_grep.sh` (~40 LOC; runs the 3 greps from `.claude/rules/testing.md` against staged Python test files)
- **Acceptance Criteria**:
  - **AC-T9.4-001**: Script runs 3 greps: zero-assertion `async def test_*` shells, PII (`name|age|occupation|phone`) in `logger.<level>(...%s...)` format strings, raw `cache_key=` outside `cache_key_hash|sha256` context
  - **AC-T9.4-002**: Script exits 0 if all 3 greps return empty; exits 2 with diagnostic if any match
  - **AC-T9.4-003**: tasks.md PR sequence checklist updated with explicit "Run `bash scripts/pre_pr_test_quality_grep.sh` BEFORE `gh pr create`; if exit ≠ 0, fix the test file BEFORE opening PR" step
  - **AC-T9.4-004**: Verification: stage a fixture test file with zero-assertion shell → script exits 2; remove the shell → script exits 0
- **Source**: GATE 2 iter-1 H-12 (testing validator: per-test ACs forbid these but no orchestrator-level gate before review)

---

## Dependency Graph

```
T1.1 ──→ T1.2 ──┬──→ T1.3
                │
                └──→ T1.4

T2.1 ──→ T2.2 ──→ T2.3 ──→ T2.4

T2.3 ──→ T3.1 ──┬──→ T3.2
                │
                └──→ T3.3

T4.1 ──┐
T1.2 ──┤
T2.3 ──┼──→ T4.2 ──→ T4.4
T3.1 ──┤
T5.1 ──┘

T2.3 ──┐
T3.1 ──┤
T4.1 ──┼──→ T4.3 ──→ T4.5
T5.1 ──┘

T5.1 ──→ T5.2

T4.2 + T4.3 deployed ──→ T6.1 ──→ T6.2

T1.1 ──→ T7.1 ──┬──→ T7.2
                │
                └──→ T7.3

T1.2 ──→ T8.1 ──→ T8.2

T6.1 ──→ T9.1
(no deps) ──→ T9.2
```

**Critical path** (longest chain): T1.1 → T1.2 → T2.3 → T3.1 → T4.2 → deployed → T6.1 → T9.1.

**Parallelizable groups**: Group 1 + Group 2 + Group 5 can start in parallel (no inter-group deps within Phase 1 setup).

---

## Test Pyramid Distribution (per pr-test-coverage-auditor)

- **Unit (70%)**: T1.3, T3.2, T4.4 (most), T4.5 (most), T5.2 — total ~30 tests
- **Integration (20%)**: T2.4, T4.4 (advisory lock), T7.2 — total ~10 tests, marked `@pytest.mark.integration`
- **E2E (10%)**: T3.3 (LLM judge eval), T8.2 (Playwright), T7.3 (live parity) — total ~3 workflows

---

## Verification Dashboard (post-Phase-1 ship)

```bash
cd /Users/yangsim/Nanoleq/sideProjects/nikita

# All artifacts present
for f in spec plan tasks audit-report validation-findings; do
  test -f specs/215-heartbeat-engine/$f.md && echo "✓ $f.md"
done

# Production module
test -f nikita/heartbeat/intensity.py && echo "✓ intensity.py"
test -f nikita/heartbeat/planner.py && echo "✓ planner.py"

# DB migration applied
mcp__supabase__list_tables filter=public | grep -q nikita_daily_plan && echo "✓ table exists"
mcp__supabase__list_policies schema=public table=nikita_daily_plan | wc -l   # ≥1

# Cron jobs registered
mcp__supabase__execute_sql "SELECT jobname FROM cron.job WHERE jobname LIKE 'nikita-%heartbeat%' OR jobname='nikita-generate-daily-arcs'"   # 2 rows

# MC validator + parity validator pass
uv run python scripts/models/heartbeat_intensity_mc.py    # exit 0
uv run python scripts/models/heartbeat_live_parity.py --since-days 1 --p-threshold 0.001   # exit 0 (loose threshold for first day)

# Tests pass
uv run pytest tests/heartbeat/ tests/api/routes/test_tasks_heartbeat.py tests/api/routes/test_tasks_generate_daily_arcs.py -v
uv run pytest tests/db/test_heartbeat_repository_integration.py -m integration -v   # requires DB

# Portal page renders
curl -sI https://nikita-mygirl.com/admin/research-lab/heartbeat   # 200 (or 307 to /login if not authed)

# Feature flag default-off
uv run python -c "from nikita.config.settings import get_settings; print(get_settings().heartbeat_engine_enabled)"   # False
```

---

## Phase 1 Acceptance (mirrors spec.md US-1 through US-4 ACs)

After Phase 1 ships and 24h E2E observation completes:
1. `SELECT user_id, COUNT(*) FROM scheduled_events WHERE source='heartbeat' AND created_at > now()-interval '24h' GROUP BY user_id` over 5 throwaway test users: each between 1 and 3 rows
2. `tests/heartbeat/test_arc_reference_llm_judge.py` PASS rate ≥0.80
3. Game-over user: 0 rows
4. Idempotency probe (manual): `curl -X POST .../tasks/heartbeat` twice within 5 min → second returns `"skipped"`
5. MC validator exit 0
6. Live parity validator (after 7 days production data): KS-test `p > 0.01` per chapter via `uv run python scripts/models/heartbeat_live_parity.py --since-days 7 --p-threshold 0.01`
7. JSONB regression: `SELECT jsonb_typeof(arc_json) FROM nikita_daily_plan LIMIT 1` returns `'object'` (R5 guard)
8. RLS audit: `mcp__supabase__list_policies('public', 'nikita_daily_plan')` shows ≥1 user-scoped policy + 0 service-role policy

---

## Risk Mitigation Map (from spec.md Risks)

| Spec Risk | Mitigated by Tasks |
|---|---|
| R1 (Dispatcher branch on platform not event_type) | T4.2 AC-007 (delegate to TouchpointEngine, never direct write) |
| R2 (Cron double-fire) | T4.2 AC-002 (has_recent_execution guard) |
| R3 (Concurrent updates) | T4.2 AC-003 (pg_advisory_xact_lock) |
| R4 (Per-user param leak) | T4.2 AC-008, T4.5 AC-004 (no PII in logs); T2.4 AC-003 (RLS user-scoped) |
| R5 (asyncpg JSONB) | T2.4 AC-001 (jsonb_typeof regression test) |
| R6 (Server TZ) | T6.1 AC-002 (5 AM UTC, gated to UTC ± 3h users in Phase 1; Phase 2 honors per-user TZ) |
| R7 (Schema not surviving Phase 2) | T1.2 AC-003 + T3.1 AC-003 (throwaway docstring acknowledgment) |
| R8 (TZ misfire) | Same as R6 |

---

## Out-of-Scope for Phase 1 (deferred to Phase 2 or Phase 3)

- Hawkes self-scheduling layer (FR-017, deferred to Phase 2)
- Activity-aware runtime intensity (FR-003, FR-004 wired to runtime, deferred to Phase 2)
- Replan-on-message (FR-011, FR-012, deferred to Phase 2)
- Bayesian per-user posteriors (FR-018, deferred to Phase 3)
- End-of-day reflection (FR-019, deferred to Phase 3)
- Per-user IANA timezone (deferred to Phase 2)
- Modality state (vacation/sick/normal/crunch, deferred to Phase 2)
- Weekend rave-mode overlay (deferred to Phase 2)

### Phase ordering for cross-cutting items (per GATE 2 iter-1 H-6 + M-14)

When Phase 2 + Phase 3 ship, observe this strict order to avoid backfill complexity:

1. **Phase 2 ships FIRST**: `users.timezone` IANA column lands. Backfill from `onboarding_profile.timezone` if present, else NULL → defaults to UTC behavior. ModalityState enum + weekend overlay also Phase 2.
2. **Phase 3 ships SECOND**: `users.bayesian_state` JSONB column lands AFTER `users.timezone` exists. This avoids Phase 3 having to backfill timezone-aware posteriors retroactively.
3. **Phase 3 also ships the admin-RLS pattern FIRST CLASS** (per H-6 deferral note in spec.md): `is_admin()` SQL helper + `bayesian_state_admin_only_select` policy. This pattern becomes the template for any future admin-only-readable column. Phase 1 explicitly does NOT pre-spec this; doing so would violate hold-the-line discipline (Decision D, user 2026-04-18).

---

**Plan-version**: 1.1 (iter-2 fixes applied)
**Phase**: 1 (MVE)
**Status**: Draft (iter-2)
**Total estimated effort**: ~62-90 hours (iter-2 added T9.3 + T9.4 + extended ACs ≈ +10h)
**Critical path length**: 7 sequential tasks (T1.1 → T9.1)
**Parallelizable**: Group 1, 2, 5 can start in parallel; Group 7 + 8 mostly independent
**Iter-2 amendments**: T1.3 (5→13 ACs), T2.1 (6→9 ACs incl FK CASCADE/CHECK/RLS-explicit/indexes), T2.2 (3→4 ACs JSONB strategy doc), T4.2 (9→11 ACs incl idempotency-key/SHA256-lock/midnight-fallback/response_model/error envelope), T4.3 (6→7 ACs incl HTTP 503/Retry-After/durable-counter/error envelope), T4.4 (10→14 ACs incl 24h-test/concurrency-split/PII-expansion/FR-007-negative), T4.5 (5→6 ACs incl 503-assert/error-envelope), T7.3 (4→5 ACs incl LLM-judge step), T9.3 NEW (coverage CI gate), T9.4 NEW (pre-PR grep gate)
**Next**: re-dispatch GATE 2 iter-2 (6 sdd-*-validators in parallel)
