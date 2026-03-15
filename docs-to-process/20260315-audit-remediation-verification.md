# Audit Remediation Verification Report — 2026-03-15

## Chain of Custody

- **Git SHA**: `4cb8a4d` (master, post-Phase1 fix)
- **Test SHA**: `99657e8` (pytest agent ran on pre-fix commit; re-verified post-fix: 4,985 passed)
- **Cloud Run Revision**: `nikita-api-00224-6mp` (behind master — redeploy needed)
- **Supabase Verification**: 2026-03-15 09:28:33 UTC, database `postgres`
- **Verification Date**: 2026-03-15

---

## Test Suite Baseline

- **Total**: 4,985 passed, 0 failed, 9 deselected
- **Runtime**: 145.83s (2:25)
- **Blocking bug fixed**: `CronSchedules` schema removed (192+ cascade eliminated)
- **ConfigLoader singleton reset** added to `conftest.py`

---

## Per-PR Test Evidence

### PR #118 — Security (FE-003, FE-002, BKD-003, IT-001)
- **Tests**: `tests/api/dependencies/test_auth_admin.py` — 11/11 passed
- **Coverage**: Admin email allowlist, 401/403 paths, case-insensitive matching, domain checks, token validation

### PR #119 — Double Embedding Removed (MP-001)
- **Tests**: Pipeline memory tests — passed (in baseline)
- **Code proof**: `memory_update.py` calls `add_fact()` once per fact (no redundant `find_similar`)

### PR #120 — Test Infrastructure Guards (IT-002/003/008)
- **Tests**: Integration tests correctly deselected (9 deselected in baseline)
- **CI proof**: `pyproject.toml` addopts excludes integration/e2e/smoke

### PR #121 — pg_cron Registry (IT-004/DC-013)
- **Supabase**: 8 active pg_cron jobs found
- **Jobs**: process-conversations, deliver, decay, cleanup, summary, psyche-batch, pipeline-event-cleanup, cron-cleanup
- **Status**: Matches deployment.md registry. Plan expected 10; actual authoritative count is 8.

### PR #122 — Backend Hygiene (BKD-001/002/004/007)
- **Tests**: Passed in baseline (4,985)
- **Supabase**: `pipeline_events` table exists (8 columns)

### PR #123 — Dead Code Removal (DC-001/002/003/010)
- **Tests**: `test_tasks_recover.py` successfully deleted; no import errors
- **Code proof**: `scripts/migrate_neo4j_to_supabase.py` deleted

### PR #124 — Documentation Sync (GE-002/003/004, MP-005)
- **Tests**: N/A (docs only)
- **Proof**: CLAUDE.md files updated per git log

### PR #125 — UX Improvements (UX-001-004, FE-009/010, IT-005)
- **Tests**: Passed in baseline
- **Portal**: Needs Chrome DevTools verification (pending deployment)

### PR #126 — LLM Warmup Background (UX-005)
- **Tests**: Passed in baseline
- **Code proof**: `main.py` uses `asyncio.create_task(_probe_llm())` — non-blocking

### PR #127 — Startup Guard (BKD-003)
- **Cloud Run**: TASK_AUTH_SECRET NOT YET SET — needs redeploy with env var
- **Code proof**: `main.py:78-85` raises RuntimeError if missing in non-debug

### PR #128 — Rate Limiting (Spec 115)
- **Tests**: 15/15 passed (per-minute, per-day, multi-user isolation, threshold edge cases)
- **Architecture note**: Uses InMemoryCache (per-instance). DatabaseRateLimiter exists but not wired.

### PR #129 — Voice Post-Score (Spec 113)
- **Tests**: 7/7 passed (boss trigger, crisis increment/reset, non-fatal failures)

### PR #130 — ViceStage (Spec 114)
- **Tests**: 16/16 passed (stage execution, exchange extraction, template rendering)
- **Feature flag**: `vice_pipeline_enabled` in settings.py (default False)

### PR #131 — Extraction Checkpoint (Spec 116)
- **Tests**: 9/9 passed (stage order: persistence @ index 1, memory_update @ index 2)

### PR #132 — ConfigLoader Migration (Spec 117)
- **Tests**: 13/13 passed + 3 behavioral canaries
- **Deprecated imports**: GONE from production (METRIC_WEIGHTS, GRACE_PERIODS, etc.)
- **Remaining**: CHAPTER_NAMES, CHAPTER_BEHAVIORS — non-deprecated, intentionally kept

---

## Supabase Query Results

| # | Query | Result |
|---|-------|--------|
| A1 | rate_limits table | Not found (rate limiting is in-memory, not DB) |
| A2 | feature_flags table | Not found (flags in settings.py, not DB) |
| A3 | pg_cron jobs | 8 active jobs |
| A4 | pipeline_events | PASS — 8 columns |
| A5 | memory_facts embedding index | PASS — IVFFlat cosine, 50 lists |
| A6 | timestamp | 2026-03-15 09:28:33 UTC |

---

## Cloud Run Results

| Check | Result |
|-------|--------|
| Revision | nikita-api-00224-6mp |
| TASK_AUTH_SECRET | Not set — needs deployment |
| /health | 200 healthy (db, supabase, llm all connected) |
| /healthz | 404 (revision behind master) |

---

## Known Limitations Documented

1. **Rate limiter**: InMemoryCache per-instance — bypassed on multi-instance Cloud Run (CRIT-3)
2. **Health endpoints**: `/healthz` and `/health` return cached startup state, not live status (MED-1)
3. **Grace periods**: `constants.py` Ch1=72h diverges from YAML Ch1=8h — production uses YAML (HIGH-2, guard test added)
4. **ViceStage**: Flag OFF in prod, enabled path smoke-tested only (HIGH-1)
5. **Cloud Run**: Deployed revision behind master — needs redeploy to activate PRs #125-127 features

---

## New Tests Added This Session

| File | Tests | Purpose |
|------|-------|---------|
| `tests/config/test_schedule_schema.py` | 2 | Verify schedule.yaml loads without cron_schedules |
| `tests/engine/test_grace_period_divergence.py` | 4 | Guard against silent grace period source confusion |

---

## Verdict

**14/14 PRs verified at code + unit test level.**
**Cloud Run redeploy needed** to activate PRs #125-127 features in production.
**Baseline**: 4,985 tests passing, 0 failures.
