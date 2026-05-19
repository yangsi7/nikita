# Spec 100: Cron Infrastructure Hardening

**Status**: DRAFT | **Wave**: H (Foundation) | **Effort**: M
**Depends on**: None | **Blocks**: Spec 101, 105

---

## Problem Statement

The background task infrastructure has 4 issues that risk data integrity and operational stability:

1. **Overlapping cron jobs** (B2/G6): `detect-stuck` and `recover-stuck` are separate endpoints performing overlapping work — detecting stuck conversations and recovering them. They should be a single idempotent `/tasks/recover` job.

2. **Decay double-fire** (B3/G5): The `/tasks/decay` endpoint starts a `job_executions` record but does NOT check if a recent execution already ran. If pg_cron fires twice in the same cycle (network retry, Edge Function restart), users suffer double decay.

3. **Pipeline concurrency explosion** (G20): `/tasks/process-conversations` fetches ALL unprocessed conversations and processes them concurrently with no limiter. A backlog of 50+ conversations causes memory spikes and API cost overruns.

4. **No per-stage error tracking** (I15): Pipeline stage errors are logged but not persisted. Admin dashboard has no visibility into which stages fail most often.

---

## Requirements

### FR-001: Consolidate Stuck Recovery (B2/G6)

- Merge `detect-stuck` and `recover-stuck` into single `POST /tasks/recover` endpoint
- Recover logic: find conversations with `status='processing'` AND `updated_at < now() - interval '30 minutes'`, set status to `failed`, log recovery
- Remove old separate endpoints
- AC: Single endpoint handles both detection and recovery; old endpoints return 410 Gone

### FR-002: Decay Idempotency Guard (B3/G5)

- Before running decay, query `job_executions` for `job_name='decay'` with `status='completed'` AND `completed_at > now() - interval '50 minutes'`
- If recent successful run exists, return early with `{"status": "skipped", "reason": "recent_execution"}`
- Window is 50 minutes (for hourly cron) to allow slight drift without blocking
- AC: Calling `/tasks/decay` twice within 50 minutes — second call returns skipped

### FR-003: Pipeline Concurrency Limiter (G20)

- Add `MAX_CONCURRENT_PIPELINES = 10` constant
- Use `asyncio.Semaphore(10)` to limit concurrent pipeline executions
- Add `MAX_PIPELINE_BUDGET_CENTS = 50` per batch — track estimated LLM cost per pipeline run, stop processing when budget exceeded
- If more conversations than limit, process first 10, log remainder for next cycle
- AC: With 25 pending conversations, only 10 are processed per cycle; remaining 15 deferred

### FR-004: Pipeline Per-Stage Error Tracking (I15)

- After pipeline completion, persist `stage_errors` dict from `PipelineContext` to `job_executions.result` JSONB
- Include per-stage timing data in the JSONB result
- AC: Admin can query `job_executions` for pipeline runs and see per-stage error rates

---

## Non-Functional Requirements

- No new database tables (reuse `job_executions`)
- Backward compatible — old pg_cron schedules continue working
- All changes covered by tests (target: 15+ new tests)
- Zero downtime deployment

---

## Key Files

| File | Changes |
|------|---------|
| `nikita/api/routes/tasks.py` | FR-001 (consolidate), FR-002 (idempotency), FR-003 (concurrency) |
| `nikita/pipeline/orchestrator.py` | FR-004 (persist stage errors/timings) |
| `nikita/db/repositories/job_execution_repository.py` | FR-002 (recent execution check) |

---

## Acceptance Criteria Summary

| ID | Criterion | Testable |
|----|-----------|----------|
| AC-001 | Single `/tasks/recover` replaces detect-stuck + recover-stuck | Yes: call endpoint, verify stuck conversations recovered |
| AC-002 | Old stuck endpoints return 410 Gone | Yes: call old endpoints, verify 410 |
| AC-003 | Decay skipped if recent run within 50min | Yes: run twice, verify second returns skipped |
| AC-004 | Max 10 concurrent pipelines | Yes: mock 25 conversations, verify only 10 processed |
| AC-005 | Pipeline stage errors persisted in job_executions | Yes: run pipeline with failing stage, verify JSONB |
| AC-006 | Stage timing data in job result | Yes: run pipeline, verify timing keys in JSONB |
