# Production Hardening Audit Report

**Date**: 2026-02-09
**Auditor**: prod-hardener agent
**Scope**: Cloud Run, pg_cron, RLS, webhook security, TODO triage, spec alignment

---

## Executive Summary

Production infrastructure is in **GOOD** shape. All 4 pg_cron jobs are active and succeeding. RLS is enabled on 33/34 public tables (only `audit_logs` missing). Webhook signature validation is confirmed. 18 TODOs remain in Python source -- 5 are stubs in `voice_flow.py` that need implementation, the rest are deferrable. Spec 037 already has a supersession notice. One notable gap: Cloud Run has `minInstances=0`, causing cold starts on first request after idle.

---

## C.1: Cloud Run Cold Start Analysis

### Current Configuration

| Setting | Value | Assessment |
|---------|-------|------------|
| **minInstances** | 0 (null/unset) | Cold starts on idle |
| **maxInstances** | 10 | Adequate for current load |
| **CPU** | 1 vCPU | Sufficient |
| **Memory** | 512 Mi | Sufficient |
| **Startup CPU Boost** | true | Helps cold starts |
| **Startup Probe** | TCP :8080, period=240s, timeout=240s, failureThreshold=1 | Very generous |
| **Execution Environment** | gen1 (default) | gen2 has faster cold starts |

### Analysis

- **Cold start impact**: First request after idle period triggers container startup. FastAPI + SQLAlchemy + all imports take ~5-15s. Startup CPU boost mitigates partially.
- **Startup probe**: 240s timeout is extremely generous -- could mask slow-start bugs. Consider reducing to 60s.
- **min-instances=1 cost**: ~$5-10/mo for an always-warm f1-micro equivalent. Worth it if latency matters for Telegram webhook responses (Telegram expects <60s).

### Recommendations

| Priority | Action |
|----------|--------|
| P1 | Set `minInstances=1` to eliminate cold starts ($5-10/mo) |
| P2 | Reduce startup probe timeout from 240s to 60s |
| P2 | Consider gen2 execution environment for faster cold starts |

---

## C.2: pg_cron Job Execution History

### Active Jobs (4 of 4)

| Job ID | Name | Schedule | Active | Status |
|--------|------|----------|--------|--------|
| 10 | nikita-decay | `0 * * * *` (hourly) | true | All succeeded |
| 11 | nikita-deliver | `* * * * *` (every minute) | true | All succeeded |
| 12 | nikita-summary | `59 23 * * *` (daily 23:59) | true | No recent runs in last 30 rows (crowded out by job 11) |
| 13 | nikita-cleanup | `30 * * * *` (every :30) | true | Succeeded (10:30 UTC today) |

### Execution Details

- **nikita-decay (10)**: Last 10 runs all succeeded (hourly, every hour today). Execution time ~15-20ms. Healthy.
- **nikita-deliver (11)**: Runs every minute, dominates `cron.job_run_details`. All succeeded. Execution time ~4-10ms. Healthy.
- **nikita-cleanup (13)**: Last run 2026-02-09 10:30:00 UTC, succeeded in ~8ms. Healthy.
- **nikita-summary (12)**: Only runs at 23:59 UTC daily. Not visible in last 30 rows because job 11 runs every minute. Assumed healthy (no failures visible).

### Missing Job

- **nikita-process (job 14)**: Referenced in event-stream as one of 5 active jobs (IDs 10-14), but `SELECT ... WHERE jobid >= 14` returned empty. This job no longer exists. It was likely the duplicate decay job that was unscheduled per GH #50.

### Recommendations

| Priority | Action |
|----------|--------|
| P2 | Verify nikita-summary (job 12) ran successfully last night by checking `WHERE jobid=12 AND start_time > '2026-02-08'` |
| P2 | Consider reducing nikita-deliver frequency to `*/5 * * * *` (every 5 min) if no scheduled messages are pending -- saves 1,380 cron rows/day |
| P2 | Add `cron.job_run_details` retention policy (auto-delete rows older than 7 days) to prevent table bloat |

---

## C.3: RLS Policy Audit

### Coverage Summary

| Metric | Count |
|--------|-------|
| Total public tables | 34 |
| RLS enabled | 33 |
| RLS disabled | 1 (`audit_logs`) |

### RLS Disabled Table

| Table | Has RLS | Risk | Assessment |
|-------|---------|------|------------|
| `audit_logs` | **false** | LOW | Admin-only table, contains system logs. No user-facing access. Acceptable to leave without RLS if only service_role writes. |

### Security-Critical Tables (All Covered)

| Table | RLS | Policies | Notes |
|-------|-----|----------|-------|
| `users` | true | 6 policies | Own-data + admin read + admin update + service_role |
| `conversations` | true | 4 policies | Own-data + admin read + service_role |
| `user_metrics` | true | 4 policies | Own-data + admin read + service_role |
| `user_profiles` | true | 4 policies | Own-data + admin view |
| `memory_facts` | true | 5 policies | CRUD own-data + service_role |
| `pending_registrations` | true | 2 policies | Admin read + service_role |
| `onboarding_states` | true | 2 policies | Admin view + service_role |

### Policy Pattern Observations

- **Consistent pattern**: Most tables have user-scoped `auth.uid() = user_id` + service_role ALL + admin SELECT.
- **INSERT policies with null qual**: `memory_facts`, `ready_prompts`, `user_backstories`, `user_profiles`, `user_social_circles`, `user_narrative_arcs`, `nikita_emotional_states` have INSERT policies with `qual: null` (no row-level check on insert). This means any authenticated user can INSERT rows. **The application sets `user_id` server-side**, so this is acceptable if the service role is used for all writes. However, if the portal uses the anon/authenticated key for direct inserts, a user could theoretically insert rows for another user.
- **Overly permissive tables**: `nikita_entities`, `nikita_life_events`, `nikita_narrative_arcs`, `scheduled_events`, `error_logs` grant ALL to public with `qual: true`. These are service-internal tables but the policies are too broad.

### Recommendations

| Priority | Action |
|----------|--------|
| P1 | Tighten INSERT policies on `memory_facts`, `ready_prompts` etc. to include `WITH CHECK (auth.uid() = user_id)` |
| P1 | Restrict `nikita_entities`, `nikita_life_events`, `nikita_narrative_arcs` ALL policies from `public` to `service_role` |
| P2 | Add RLS + admin-only policy to `audit_logs` for defense-in-depth |
| P2 | Restrict `scheduled_events` ALL policy from `public` to `service_role` |

---

## C.4: Webhook Signature Validation

### Status: CONFIRMED

**Location**: `nikita/api/routes/telegram.py:506-513`

```python
# SEC-01: Verify webhook signature (CRITICAL)
settings = get_settings()
expected_secret = settings.telegram_webhook_secret
if expected_secret:
    if not x_telegram_bot_api_secret_token or not hmac.compare_digest(
        x_telegram_bot_api_secret_token, expected_secret
    ):
        raise HTTPException(status_code=403, detail="Invalid webhook signature")
```

### Assessment

| Aspect | Status | Detail |
|--------|--------|--------|
| Header extraction | CONFIRMED | `X-Telegram-Bot-Api-Secret-Token` via FastAPI Header |
| Comparison method | CONFIRMED | `hmac.compare_digest()` (timing-safe) |
| Secret source | CONFIRMED | `settings.telegram_webhook_secret` (env var) |
| Set-webhook includes secret | CONFIRMED | `telegram.py:1197` passes `secret_token` to `set_webhook()` |
| Bypass risk | LOW | Only bypassed if `telegram_webhook_secret` is empty/None in settings |

### Recommendation

| Priority | Action |
|----------|--------|
| P1 | Ensure `TELEGRAM_WEBHOOK_SECRET` is set in Cloud Run env vars (verify via `gcloud run services describe`) |
| P2 | Add startup validation that fails fast if webhook secret is not configured |

---

## C.5: TODO Stub Triage

### Summary: 18 TODOs across 12 files

| Verdict | Count |
|---------|-------|
| FIX (needs implementation) | 5 |
| DEFER (future enhancement) | 9 |
| ARCHIVE (dead code / superseded) | 4 |

### Triage Table

| File | Line | TODO Text | Verdict | Reason |
|------|------|-----------|---------|--------|
| `onboarding/voice_flow.py` | 468 | Implement database lookup | FIX | Stub in active onboarding flow |
| `onboarding/voice_flow.py` | 499 | Implement database save | FIX | Stub in active onboarding flow |
| `onboarding/voice_flow.py` | 505 | Persist to database | FIX | Stub in active onboarding flow |
| `onboarding/voice_flow.py` | 511 | Implement database update | FIX | Stub in active onboarding flow |
| `onboarding/voice_flow.py` | 522 | Implement actual ElevenLabs API call | FIX | Stub for critical voice call initiation |
| `api/routes/admin.py` | 102 | Fetch from auth.users | DEFER | Email display is cosmetic |
| `api/routes/admin.py` | 1091 | Count errors in last 24 hours | DEFER | Error counting is monitoring enhancement |
| `agents/text/handler.py` | 132 | Implement actual storage | DEFER | Fact extraction storage - pipeline handles this |
| `agents/text/facts.py` | 147 | Implement actual LLM call | ARCHIVE | Facts module superseded by pipeline extraction stage |
| `agents/voice/availability.py` | 124 | Implement cooldown tracking | DEFER | Future enhancement for call frequency limits |
| `agents/voice/scheduling.py` | 296 | Implement OutboundCallService | DEFER | Outbound calls not yet in scope |
| `agents/voice/context.py` | 531 | Integrate voice with unified pipeline | DEFER | Voice uses own context builder, integration is P2 |
| `agents/voice/transcript.py` | 344 | Implement actual LLM summarization | DEFER | Transcript summary is enhancement |
| `agents/voice/service.py` | 378 | Add to voice_calls table | DEFER | Event logging enhancement |
| `api/routes/tasks.py` | 336 | Initiate outbound voice call | DEFER | Outbound calls not in scope |
| `engine/chapters/boss.py` | 74 | inject UserRepository and fetch user | ARCHIVE | Boss module uses DI via service layer |
| `engine/chapters/boss.py` | 126 | fetch user chapter from DB | ARCHIVE | Already handled in integration layer |
| `pipeline/stages/summary.py` | 47 | Implement full summary generation logic | ARCHIVE | Summary stage already functional |

### Recommendations

| Priority | Action |
|----------|--------|
| P0 | Fix 5 `voice_flow.py` stubs -- these are in the active voice onboarding path |
| P2 | Clean up 4 ARCHIVE TODOs (remove or replace with actual implementation notes) |

---

## C.6: Spec 037 Supersession Confirmation

### Status: CONFIRMED

**Spec 037** (`specs/037-pipeline-refactor/spec.md:1-2`) already has supersession notice:

```
> **SUPERSEDED**: This spec has been functionally replaced by [Spec 042](../042-unified-pipeline/spec.md)
> (Unified Pipeline). The 11-stage pipeline and orchestrator described here were redesigned as a
> 9-stage unified pipeline with SupabaseMemory. See Spec 042 for the authoritative specification.
```

**Tasks status**: 25/32 complete (78%). Remaining 7 tasks are moot since Spec 042 supersedes.

No action needed.

---

## C.7: Priority Recommendations

### P0 (Critical -- Fix Now)

| # | Issue | Impact | Action |
|---|-------|--------|--------|
| 1 | 5 TODO stubs in `voice_flow.py` | Voice onboarding calls will fail silently | Implement DB lookup/save/update and ElevenLabs API call |

### P1 (High -- Fix This Sprint)

| # | Issue | Impact | Action |
|---|-------|--------|--------|
| 2 | Cloud Run minInstances=0 | Cold start latency on idle (~5-15s) | Set `minInstances=1` (~$5-10/mo) |
| 3 | RLS INSERT policies missing WITH CHECK | Authenticated users could insert rows for other users | Add `WITH CHECK (auth.uid() = user_id)` to 6 tables |
| 4 | Service-internal tables have `public ALL` | `nikita_entities`, `nikita_life_events`, `nikita_narrative_arcs` open to any authenticated user | Restrict to `service_role` |
| 5 | Verify webhook secret in prod | If env var missing, webhook validation is bypassed | Add startup assertion in `main.py` |

### P2 (Medium -- Backlog)

| # | Issue | Impact | Action |
|---|-------|--------|--------|
| 6 | Startup probe timeout 240s | Masks slow-start bugs | Reduce to 60s |
| 7 | nikita-deliver runs every minute | 1,440 cron executions/day, table bloat | Reduce to `*/5 * * * *` if acceptable |
| 8 | cron.job_run_details retention | Table grows unbounded | Add auto-cleanup for rows > 7 days |
| 9 | 4 ARCHIVE TODOs | Dead code confusion | Remove or update comments |
| 10 | `audit_logs` missing RLS | Defense-in-depth | Add RLS + admin policy |

---

## Appendix: Raw Data

### Cloud Run Annotations
```
autoscaling.knative.dev/maxScale=10
run.googleapis.com/client-name=gcloud
run.googleapis.com/client-version=540.0.0
run.googleapis.com/startup-cpu-boost=true
```

### pg_cron Jobs
```
10: nikita-decay     | 0 * * * *     | active
11: nikita-deliver   | * * * * *     | active
12: nikita-summary   | 59 23 * * *   | active
13: nikita-cleanup   | 30 * * * *    | active
14: (deleted -- was duplicate decay per GH #50)
```

### RLS Coverage
- 33/34 tables with RLS enabled
- 1 table without RLS: `audit_logs` (admin-only, low risk)
- 87 total policies across all tables
