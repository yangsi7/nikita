# Diagram 11 — Heartbeat Engine (Spec 215, Phase 1 ship state)

**Generated**: 2026-04-18 post-merge of 215-A/B/C/D/F (master `02911f0`).
**Status**: Phase 1 — cron registered, flag OFF, planner output write-only, intensity math offline-only.
**Companion**: `docs/models/heartbeat-intensity.md` (math), `docs/models/heartbeat-*.png` (7 distribution plots), `specs/215-heartbeat-engine/contracts.md` (frozen cross-PR shapes).

---

## A — Activation flow (cron tick → user-visible message)

```
ROOT pg_cron tick fires
  │
  ├── BRANCH 1 — Hourly heartbeat ("0 * * * *")  [pg_cron: nikita-heartbeat-hourly, registered by 215-E]
  │   │
  │   ├─ [⊙] supabase.cron → net.http_post → POST /api/v1/tasks/heartbeat
  │   │      Bearer: hardcoded literal (matches Cloud Run TASK_AUTH_SECRET)
  │   │
  │   ├─ [⊙] FastAPI → tasks.py:1199-1326  heartbeat_tick()
  │   │      ∘ verify_task_secret              [tasks.py:47-73]
  │   │      ∘ if !heartbeat_engine_enabled    → 200 {"status":"disabled"}     [tasks.py:1228-1231]
  │   │      ∘ has_recent_execution(55min)     → 200 {"status":"skipped"}      [tasks.py:1239-1244]
  │   │      ∘ start_execution(JobName.HEARTBEAT) + commit
  │   │      ∘ get_active_users_for_heartbeat() — game_status IN ('active','boss_fight')
  │   │            AND telegram_id IS NOT NULL AND last_interaction_at > now()-14d
  │   │            limit=1000                   [user_repository.py:1268-1305]
  │   │      ∘ fan-out cap = min(eligible, 40) [tasks.py:1255-1256, _HEARTBEAT_FAN_OUT_CAP]
  │   │
  │   └─ for user in eligible[:40]:           [tasks.py:1262-1298]
  │        ├─ [⊗] pg_advisory_lock(hashtext(user_id)::bigint)   ← BLOCKING (B3)
  │        │      session-scoped + try/finally pg_advisory_unlock
  │        │      slow user U serializes U+1..U+39
  │        ├─ [⊙] TouchpointEngine.evaluate_and_schedule_for_user(user_id)
  │        │      [touchpoints/engine.py:523-595]
  │        │      ∘ store.get_recent_touchpoints(since=now-min_gap)  → dedup
  │        │      ∘ user_repo.get_by_id(user_id) → chapter, tz, last_interaction_at
  │        │      ∘ scheduler.evaluate_user(...)
  │        │            ⊕ time-based, gap-based, event-based (Spec 071)
  │        │      ∘ store.create(...)  → INSERT INTO touchpoints (NOT scheduled_events!)
  │        └─ pg_advisory_unlock
  │
  │   ─── DELIVERY DECOUPLING [⊗ B1 — STANDING BUG] ───
  │
  │   ╔════════════════════════════════════════════════════════════╗
  │   ║  touchpoints table written  ✓                              ║
  │   ║  ↓                                                          ║
  │   ║  /api/v1/tasks/touchpoints route exists  [tasks.py:992]    ║
  │   ║  ↓                                                          ║
  │   ║  TouchpointEngine.deliver_due_touchpoints()                ║
  │   ║      → _send_telegram_message → bot.send_message            ║
  │   ║      → store.mark_delivered                                 ║
  │   ║  ↑                                                          ║
  │   ║  CRON CALLER:    [⊗ MISSING IN PROD]                       ║
  │   ║      cron.job query 2026-04-18 → no nikita-touchpoints      ║
  │   ║      row. Heartbeat-fan-out + ALL other touchpoint          ║
  │   ║      producers currently land in a queue with no consumer.  ║
  │   ╚════════════════════════════════════════════════════════════╝
  │
  └── BRANCH 2 — Daily arc generator ("0 5 * * *") [pg_cron: nikita-generate-daily-arcs, registered by 215-E]
      │
      ├─ [⊙] supabase.cron → POST /api/v1/tasks/generate-daily-arcs
      │
      ├─ [⊙] FastAPI → tasks.py:1329-1490  generate_daily_arcs()
      │      ∘ feature flag gate                              [tasks.py:1363-1365]
      │      ∘ idempotency 1440-min                            [tasks.py:1372-1377]
      │      ∘ FR-014 cost circuit-breaker
      │            today_cost = job_repo.get_today_cost_usd()
      │            [⊗ B2: method does NOT exist; fallback $0; breaker disarmed]
      │            if today_cost ≥ ceiling → 503 + Retry-After-to-midnight
      │      ∘ active-user filter (same as heartbeat, NO 40-cap)
      │
      └─ for user in eligible:                                [tasks.py:1439-1465]
           ├─ [⊙] planner.generate_daily_arc(user, today, session) → DailyArc
           │       [heartbeat/planner.py:161-207]
           │       ∘ Pydantic AI Agent(model=Models.haiku())  ← claude-haiku-4-5-20251001
           │       ∘ output_type=DailyArc (steps: 6-12, narrative, model_used)
           │       ∘ system prompt: 6-12 chronologically ordered ArcStep entries
           │       [⊗ B4: NO timeout on agent.run() — single hang blocks tick]
           │
           └─ [⊙] NikitaDailyPlanRepository.upsert_plan(...)
                  [db/repositories/heartbeat_repository.py:79-148]
                  INSERT … ON CONFLICT (user_id, plan_date) DO UPDATE
                  arc_json passed as Python dict (NOT json.dumps — PR #319 burn)
                  RETURNING * → row id + server-stamped generated_at
                  [⊗ DOWNSTREAM CONSUMER GAP — Phase 2 wiring not yet shipped]
```

USER-VISIBLE OUTCOME (with current code, when flag flips ON):
- Daily LLM cost burn writing `nikita_daily_plan` rows that nothing reads at runtime
- Hourly TouchpointEngine fan-out writing `touchpoints` rows that no cron drains
- Net: $$$/day spend, 0 user-visible behavior change
- Once B1 cron is registered, hourly proactive Telegram messages start landing per existing Spec 071 trigger logic (NOT yet using planner arc data)

---

## B — Module dependency graph

```
nikita.heartbeat (Spec 215 surface)
  │
  ├─ intensity.py           [✓ 215-B]
  │   ⇄ scripts/models/heartbeat_intensity_mc.py    [SOT seam, MC imports prod constants]
  │   ⇄ scripts/models/heartbeat_live_parity.py     [215-F nightly KS-test]
  │   → math, random, typing.Final
  │   [⊗ NO RUNTIME CONSUMER — Phase 1 offline only]
  │
  ├─ planner.py             [✓ 215-C]
  │   → pydantic_ai.Agent  ⇄  Anthropic API (HTTPS)
  │   → nikita.config.models.Models.haiku()
  │   exports: DailyArc, ArcStep, generate_daily_arc()
  │   ↳ CONSUMER: tasks.generate_daily_arcs (215-D handler)
  │
  ├─ db.models.heartbeat.NikitaDailyPlan       [✓ 215-A]
  │   ⇄ supabase.public.nikita_daily_plan
  │       PK uuid, FK user_id ON DELETE CASCADE, plan_date date
  │       UNIQUE(user_id, plan_date) — idempotency anchor
  │       RLS: user-scoped read; service-role writes
  │   [⊗ asyncpg JSONB invariant — never json.dumps()]
  │
  └─ db.repositories.heartbeat_repository.NikitaDailyPlanRepository  [✓ 215-A]
      .get_plan_for_date()    [⊗ NO CONSUMER]
      .upsert_plan()          ↳ CONSUMER: tasks.generate_daily_arcs

nikita.api.routes.tasks (215-D handlers)
  → verify_task_secret  [⊗ TASK_AUTH_SECRET coupling — 9 existing crons + 2 new = 11 hardcoded literals]
  → settings.heartbeat_engine_enabled / heartbeat_cost_circuit_breaker_usd_per_day
  → JobExecutionRepository  [⊗ B2: get_today_cost_usd missing]
  → UserRepository.get_active_users_for_heartbeat
  → TouchpointEngine.evaluate_and_schedule_for_user  ⊙ heartbeat-only call site
  → planner.generate_daily_arc                       ⊙ daily-arcs-only call site
  → NikitaDailyPlanRepository.upsert_plan            ⊙ daily-arcs-only call site

nikita.touchpoints.engine.TouchpointEngine          [pre-existing Spec 025]
  → store.{TouchpointStore, ScheduledTouchpoint}    ⇄ touchpoints table (NOT scheduled_events)
  → scheduler.{TouchpointScheduler, TriggerContext, TriggerType}
  → silence.StrategicSilence
  → emotional_state.{models, store}
  → platforms.telegram.bot.get_bot                  (used by deliver_due_touchpoints)
  → db.repositories.{user, vice}                    (chat_id, vice prefs)

pg_cron platform
  ⇄ supabase.public.cron.job   (9 prod rows pre-215; +2 after 215-E lands)
  ⇄ Cloud Run nikita-api  rev 00258 (HTTPS, app-layer Bearer auth)
  [⊗ NO HTTP retry — fire-and-forget; cold-start caveats apply]
```

---

## C — Failure-mode tree (Phase 1 ship + flag-flip risk)

```
Heartbeat engine fails to deliver value
  │
  ├─ B1 [CRITICAL] — touchpoints queue has no drain cron
  │       Symptom: heartbeat tick succeeds, touchpoints rows accumulate, 0 messages sent
  │       Detection: SELECT count(*) FROM touchpoints WHERE delivered_at IS NULL
  │       Mitigation: register `nikita-touchpoints` cron (`*/5 * * * *` →
  │                   POST /api/v1/tasks/touchpoints) BEFORE flag-flip
  │       Pre-existing bug, surfaced by Spec 215 deployment intent
  │
  ├─ B2 [HIGH] — cost circuit breaker disarmed
  │       Symptom: uncapped Anthropic spend on flag-flip; no 503 on overspend
  │       Detection: GCP billing alert (out-of-band), or grep logs for
  │                  `cost_breaker_degraded` warning
  │       Mitigation: implement JobExecutionRepository.get_today_cost_usd OR
  │                   add hard cap on len(eligible) in /generate-daily-arcs
  │
  ├─ B3 [HIGH] — pg_advisory_lock blocking serializes whole tick on slow user
  │       Symptom: tick takes >60s, processed << to_process, fan-out stalls
  │       Detection: log line `processed=N to_process=40` divergence
  │       Mitigation: convert to pg_try_advisory_lock with skip semantics
  │
  ├─ B4 [MEDIUM] — planner LLM call has no timeout
  │       Symptom: hung Anthropic request blocks daily-arc tick to 15min
  │                Cloud Run timeout
  │       Detection: tick latency p99 spike; `errors_pct` rises
  │       Mitigation: asyncio.wait_for(agent.run, timeout=30s) in
  │                   planner._run_planner_agent
  │
  ├─ Cold start [LOW] — first cron tick after idle = 2-5s extra latency
  │       Mitigation: idempotency window 55min absorbs single missed tick
  │
  ├─ Schema drift [LOW] — planner output ↔ DailyArc Pydantic model
  │       Mitigation: pydantic_ai validation enforces shape; defensive
  │                   model_used backfill at planner.py:195-197
  │
  ├─ DB connection exhaustion [LOW] — fan-out shares one session
  │       Mitigation: heartbeat_tick uses 1 session for whole tick;
  │                   advisory locks are session-bound
  │
  └─ Schema-rotation pain [INFRA] — 11 hardcoded Bearer literals after 215-E
        Mitigation: vault/templating cleanup tracked separately as hygiene work
```

---

## D — Pre-flag-flip checklist

Before setting `HEARTBEAT_ENGINE_ENABLED=true` in Cloud Run env:

1. [ ] B1 fixed (nikita-touchpoints cron registered + verified delivering)
2. [ ] B2 fixed (cost ledger primitive shipped OR fan-out hard cap added)
3. [ ] B3 fixed (try-lock with skip semantics)
4. [ ] B4 fixed (planner timeout)
5. [ ] 24h baseline observation: cron.job_run_details for both 215-E jobs all green w/ `{"status":"disabled"}`
6. [ ] log-based alert routed for `cost_breaker_degraded` warning + `errors_pct > 0.20`
7. [ ] Staging dry-run: flip flag in staging, observe 24h, then production

Phase 1 ship state (current target) = items 5-6 done, items 1-4 deferred to follow-up PRs. Flag stays OFF.
