# API Validation Report — Spec 214 GATE 2 iter-2

**Spec**: `specs/214-portal-onboarding-wizard/spec.md` + `technical-spec.md`
**Status**: PASS
**Timestamp**: 2026-04-19 (post-amendment commit `35c1e38`)
**Iter-1 reference**: `api-validator-2026-04-19.md` (5 HIGH findings: H1-H5)

---

## Summary

| Severity | Count | Delta vs iter-1 |
|----------|-------|-----------------|
| CRITICAL | 0     | unchanged       |
| HIGH     | 0     | -5 (all resolved) |
| MEDIUM   | 1     | +1 (new, see M-NEW-1) |
| LOW      | 2     | +2 (new, see L-NEW-1, L-NEW-2) |

**Verdict: PASS**. All 5 HIGH findings from iter-1 are conclusively resolved by the amendment text. Zero CRITICAL + zero HIGH = pass bar met. New findings introduced by amendments are MEDIUM or LOW only and do not block planning.

---

## Iter-1 HIGH Resolution Audit

### H1 — Authz response code (resolves #350)

- **iter-1 finding**: tool-call referencing another user's `onboarding_profile` JSONB path returned 422 (validation error envelope), should be 403 (authz). Risk: client retries forever on phantom validation error.
- **Amendment evidence** (spec.md L731-732, tech-spec L179):
  - **AC-11d.3** explicitly splits the two cases: body-level `user_id` rejected at Pydantic layer with **422** via `ConfigDict(extra="forbid")`.
  - **AC-11d.3b** new AC: tool-call JSONB-path tampering returns **403** with generic body `{"detail": "forbidden"}` (no user_id leakage), structured security event `converse_authz_mismatch` logged.
  - tech-spec §2.3 step 4 codifies the gate: "any tool argument resolving to `onboarding_profile` of a user_id ≠ `current_user.id` → 403 generic body + log `converse_authz_mismatch`".
- **Server-derived identity guarantee**: `current_user: Annotated[AuthenticatedUser, Depends(get_authenticated_user)]` — body cannot carry `user_id` per `extra="forbid"`. Identity flows from Bearer JWT only. Single source of truth. Closes the body-vs-JWT mismatch class entirely.
- **Status**: **RESOLVED**. Two separate ACs cleanly separate validation (422) from authz (403); both have explicit tests.

### H2 — Rate-limit math (resolves #353)

- **iter-1 finding**: Single shared bucket of 10/min between `/converse` (15-turn wizard, ~15 turns/wizard) and `/preview-backstory` would 429 mid-wizard. Math didn't fit the use case.
- **Amendment evidence** (spec.md L719, L734-735, tech-spec L678-689):
  - **AC-11d.3d**: per-user `/converse` bucket = `CONVERSE_PER_USER_RPM` = **20/min**, separate from `/preview-backstory` (10/min, unchanged).
  - **AC-11d.3e**: per-IP secondary bucket `CONVERSE_PER_IP_RPM` = **30/min** for NAT/shared-IP cover.
  - **AC-11d.3d also**: durable per-user daily LLM-spend cap `CONVERSE_DAILY_LLM_CAP_USD` = **$2.00** via new `llm_spend_ledger` table (DDL §4.3b, RLS admin/service-role only, daily prune cron).
  - **AC-11d.9**: 429 UX is in-character bubble + `Retry-After: CONVERSE_429_RETRY_AFTER_SEC` (30) header + client transparent retry; `source="fallback"` preserved.
  - All constants are `Final[int|float]` in `nikita/onboarding/tuning.py` per `.claude/rules/tuning-constants.md`.
- **Status**: **RESOLVED**. Three independent rate-limit dimensions (per-user RPM, per-IP RPM, daily $ cap) with documented values and rationale. 20/min comfortably exceeds the 15-turn wizard expectation.

### H3 — Idempotency (resolves #352, AC-11d.3c)

- **iter-1 finding**: POST `/converse` was non-idempotent. Network retry would double-write to `onboarding_profile.conversation` JSONB array and double-decrement quota.
- **Amendment evidence** (spec.md L733, tech-spec L149, L194-201, L431-453):
  - **AC-11d.3c**: dedupe key = `(user_id, turn_id)`, 5-min TTL window. Replay returns cached body+status verbatim, MUST NOT re-call agent, MUST NOT write JSONB, MUST NOT decrement rate-limit, MUST NOT increment LLM-spend ledger (M5 = no-op on counters).
  - tech-spec §2.3 codifies short-circuit ordering: idempotency check **before** rate-limit decrement and **before** agent call. Step 9: store cache entry on the way out.
  - **DDL** (§4.3a): `llm_idempotency_cache(user_id, turn_id, response_body, status_code, created_at)` with PK `(user_id, turn_id)`, RLS `admin_and_service_role_only`, hourly pg_cron prune `llm_idempotency_cache_prune` of rows older than 5 min.
  - Header convention supports both `Idempotency-Key` HTTP header and body `turn_id: UUID`.
- **Status**: **RESOLVED**. Industry-standard idempotency pattern (key + TTL + cache table + cleanup cron). Insert-on-conflict-do-nothing-returning protects against the cache-lookup race.

### H4 — "Same transaction" fallacy (resolves #352, B5)

- **iter-1 finding**: Original spec said greeting send + flag clear "same transaction" — but `bot.send_message` is an external HTTP call that cannot be inside a Postgres transaction. Cloud Run instance eviction between flag-clear and greeting-send would silently drop the greeting forever.
- **Amendment evidence** (spec.md L780-787, tech-spec L247-287):
  - **AC-11e.3** completely restructures: 3-step protocol (claim intent → send greeting → clear flag on confirmed send) + pg_cron backstop (step 4).
  - Step 1: atomic SQL UPDATE claims `handoff_greeting_dispatched_at = now()` predicate-filtered on NULL + `pending_handoff = TRUE`. Concurrent `/start <code>` second caller sees rowcount==0 and skips.
  - Step 2: greeting dispatched via FastAPI `BackgroundTasks.add_task` (NOT `asyncio.create_task` — convention note in tech-spec §2.5 explicitly forbids the latter in HTTP routes).
  - Step 3: clear `pending_handoff = FALSE` ONLY on confirmed Telegram-send success. Retries exhausted → reset `handoff_greeting_dispatched_at = NULL` so backstop can pick up.
  - Step 4: pg_cron `nikita_handoff_greeting_backstop` every 60s with stale-row predicate (`handoff_greeting_dispatched_at IS NULL OR < now() - 30s`). Calls `POST /api/v1/tasks/retry-handoff-greetings` (Bearer auth).
  - **AC-11e.3c**: one-shot stranded-user migration script (`scripts/handoff_stranded_migration.py`) for legacy-regime users at deploy cutover.
- **Status**: **RESOLVED**. The "same transaction" language is gone. Three-phase commit-with-compensation pattern + durable backstop covers all eviction-between-steps scenarios. Tests enumerated for each: concurrent /start, instance crash between steps, Telegram 5xx exhaustion.

### H5 — 10s webhook timeout / blocking greeting

- **iter-1 finding**: Spec implied greeting generation runs inline in webhook response path. Generator is LLM-bound (potentially 1-3s) and `bot.send_message` adds another round-trip. Telegram webhook SLA is ~10s; bursting concurrent /start could cause webhook timeouts and Telegram-side retries.
- **Amendment evidence** (spec.md L786, tech-spec L249, L262-282, L287):
  - **AC-11e.3b**: `_handle_start_with_payload` MUST return webhook 200 within **2 seconds** wall-clock. Greeting generation + `bot.send_message` MUST execute inside FastAPI `BackgroundTasks` scheduled by the route handler, NOT in the request-handling coroutine.
  - tech-spec §2.5 step 3: "Webhook returns 200 first (AC-11e.3b). BackgroundTasks run after the HTTP response commits."
  - Convention note (§2.5): `BackgroundTasks` is the FastAPI HTTP-route convention; `asyncio.create_task` reserved for non-FastAPI contexts (e.g., voice-call completion paths).
  - Test: "measured webhook latency p99 under 2s with a deliberately slow greeting mock (3s sleep)"; pg_cron backstop covers Cloud-Run-eviction case where BackgroundTasks would otherwise drop on container shutdown.
- **Status**: **RESOLVED**. Webhook returns 200 fast; greeting fires post-response via `BackgroundTasks`; eviction safety net via pg_cron backstop. The Telegram-webhook timeout class is closed.

---

## Endpoint Inventory (post-amendment)

| Method | Path | Request Model | Response Model | Auth | Status Codes |
|--------|------|---------------|----------------|------|--------------|
| POST | `/portal/onboarding/converse` | `ConverseRequest` (extra=forbid, no user_id) | `ConverseResponse` | Bearer JWT (`Depends(get_authenticated_user)`) | 200, 403 (authz), 422 (validation), 429 (rate / IP / spend) + Retry-After, 500 (only if fallback itself fails) |
| POST | `/api/v1/tasks/retry-handoff-greetings` | (n/a — body unspecified, internal task endpoint) | (n/a) | Bearer (`TASK_AUTH_SECRET`) | 200, 401 |
| Telegram webhook handler | `_handle_start_with_payload` (downstream) | (Telegram Update payload) | (n/a — webhook ack) | Telegram secret-token header (existing) | 200 within 2s SLA |

Existing endpoints (`/portal/onboarding/profile` PATCH, `/portal/link-telegram` POST, `/preview-backstory` POST, etc.) unchanged by amendment.

---

## Error Envelope Consistency

- [✓] Uniform error shape — 422 from Pydantic-default; 403 explicitly specified as `{"detail": "forbidden"}`; 429 returns in-character bubble in `nikita_reply` + `source="fallback"` (intentional UX choice, not a leak).
- [✓] No stack-trace leakage — 403 body is generic; security events go to structured logs only.
- [✓] Semantic event codes — `converse_authz_mismatch`, `converse_output_leak`, `converse_tone_reject`, `converse_input_reject`, `handoff_greeting_retry_exhausted`. All distinct, machine-grep-able.

---

## Idempotency Audit

| Endpoint | Verb | Idempotency Strategy | Status |
|----------|------|----------------------|--------|
| `/portal/onboarding/converse` | POST | `Idempotency-Key` header OR `turn_id` UUID body field; `(user_id, turn_id)` cache; 5-min TTL via `llm_idempotency_cache` table + hourly prune cron | ✓ |
| `_handle_start_with_payload` (telegram) | (webhook) | Predicate-filtered SQL UPDATE on `handoff_greeting_dispatched_at IS NULL`; rowcount==0 = no-op | ✓ |
| `/api/v1/tasks/retry-handoff-greetings` | POST | Same predicate-filter as above; pg_cron retries are inherently idempotent | ✓ |

---

## OpenAPI Surface

- [✓] `response_model=` — implicit via `-> ConverseResponse` return annotation in tech-spec §2.3.
- [✓] `responses={}` — non-200 paths documented in AC-11d.3 (422), AC-11d.3b (403), AC-11d.3d/.3e (429), AC-11d.9 (429 + Retry-After + body shape). Recommend explicit `responses={...}` dict in implementation.
- [~] `tags=` — implied by router (`/portal/onboarding/...`), not explicitly named in spec. Minor; see L-NEW-1.
- [~] `summary` + `description` — not explicitly mentioned in tech-spec. Minor; see L-NEW-1.

---

## New Findings (introduced by or surfaced during iter-2 review)

### M-NEW-1 — Daily LLM-spend cap response shape under-specified

- **Severity**: MEDIUM
- **Location**: spec.md AC-11d.3d (L734), tech-spec §2.3 step 3 (L178)
- **Issue**: When daily $2 cap is hit, the spec says "short-circuit with 429" but does not specify whether the 429 body distinguishes "out of $$" from "RPM exceeded". From the user's perspective both look identical (`Retry-After: 30s`), but a $2-cap'd user retrying every 30s for 24h gets a frustrating loop. Either: (a) use a different `Retry-After` value (seconds until UTC midnight) for spend-cap 429s, or (b) include a distinct `error_code` field in the JSON body (e.g., `daily_spend_cap_exceeded` vs `rate_limit_exceeded`) so the client can render different copy.
- **Recommendation**: Add to AC-11d.9: "When the 429 cause is `CONVERSE_DAILY_LLM_CAP_USD`, `Retry-After` MUST be set to seconds-until-next-UTC-midnight (not 30s); the response body MUST include `source="fallback"` AND `cause="daily_spend_cap"` so the client can render a longer-form fallback bubble." Non-blocking; client-side retry would simply be ignored more times before the user gives up. Could be deferred to follow-up.

### L-NEW-1 — Explicit OpenAPI metadata on `/converse` route decorator

- **Severity**: LOW
- **Location**: tech-spec §2.3 (L162)
- **Issue**: Route decorator `@router.post("/onboarding/converse")` lacks explicit `tags=`, `summary=`, `description=`, `responses={...}` mapping. Implementation will auto-derive but `/docs` discoverability suffers.
- **Recommendation**: At implementation, add: `@router.post("/onboarding/converse", tags=["onboarding"], summary="Conversational wizard turn", responses={403: {...}, 422: {...}, 429: {...}})`. Spec already documents the contracts; this is a docs-quality fix, not a contract gap.

### L-NEW-2 — `Idempotency-Key` header vs body `turn_id` precedence undefined

- **Severity**: LOW
- **Location**: spec.md AC-11d.3c (L733), tech-spec §2.3 idempotency-handling block (L201)
- **Issue**: Both `Idempotency-Key` header and body `turn_id` are accepted. If a client sends BOTH and they differ, behavior is undefined. Could lead to inconsistent dedupe keys across SDK clients.
- **Recommendation**: Add to AC-11d.3c: "If both `Idempotency-Key` header and body `turn_id` are present and differ, the server MUST return 400 with `{detail: 'idempotency_key_mismatch'}`. If both are present and equal, treated as one key." Or simpler: "Header takes precedence over body when both present." Pick one; document.

---

## Verdict Rationale

PASS bar = 0 CRITICAL + 0 HIGH. Met.

The amendment text in commit `35c1e38` cleanly resolves all 5 iter-1 HIGH findings with concrete contract changes:
1. H1 → AC-11d.3 + AC-11d.3b (split 422 / 403 cases, server-derived identity)
2. H2 → AC-11d.3d + AC-11d.3e (split per-user / per-IP RPM + daily $ cap with documented constants)
3. H3 → AC-11d.3c + tech-spec §4.3a (idempotency table + 5-min TTL + cache HIT no-op semantics)
4. H4 → AC-11e.3 + AC-11e.3c (three-phase claim/dispatch/clear + pg_cron backstop + stranded migration)
5. H5 → AC-11e.3b + tech-spec §2.5 (BackgroundTasks pattern + 2s webhook SLA + `BackgroundTasks` vs `asyncio.create_task` convention)

The 1 MEDIUM (M-NEW-1) and 2 LOW (L-NEW-1, L-NEW-2) findings introduced are quality-of-life improvements, not contract violations. They should be tracked as follow-up GH issues (per `.claude/rules/issue-triage.md`) but do NOT block GATE 2 progression to Phase 5 (`/plan`).

Recommend orchestrator: proceed to Phase 5.
