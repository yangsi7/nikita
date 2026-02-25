# Plan: Spec 100 — Cron Infrastructure Hardening

## Implementation Strategy

Sequential implementation in 4 user stories, ordered by dependency. Each story follows TDD (red → green → refactor).

---

## Story 1: Consolidate Stuck Recovery (FR-001)

### Tasks

**T1.1** Add `has_recent_execution()` to `JobExecutionRepository`
- Query: `SELECT 1 FROM job_executions WHERE job_name = :name AND status = 'completed' AND completed_at > now() - :window LIMIT 1`
- Returns `bool`
- File: `nikita/db/repositories/job_execution_repository.py`

**T1.2** Create `POST /tasks/recover` endpoint
- Find conversations with `status='processing'` AND `updated_at < now() - 30min`
- Set status to `failed`, log each recovery
- Record job execution via `job_repo`
- File: `nikita/api/routes/tasks.py`

**T1.3** Deprecate old endpoints
- If `detect-stuck` or `recover-stuck` endpoints exist, make them return 410 Gone
- File: `nikita/api/routes/tasks.py`

**T1.4** Tests for recover endpoint
- Test: stuck conversation recovered
- Test: non-stuck conversations untouched
- Test: job execution recorded
- File: `tests/api/test_tasks_recover.py`

---

## Story 2: Decay Idempotency Guard (FR-002)

### Tasks

**T2.1** Add idempotency check to decay endpoint
- Before processing, call `job_repo.has_recent_execution("decay", minutes=50)`
- If true, return `{"status": "skipped", "reason": "recent_execution"}`
- File: `nikita/api/routes/tasks.py`

**T2.2** Tests for decay idempotency
- Test: first call processes normally
- Test: second call within 50min returns skipped
- Test: call after 50min processes normally
- File: `tests/api/test_tasks_decay_idempotency.py`

---

## Story 3: Pipeline Concurrency Limiter (FR-003)

### Tasks

**T3.1** Add concurrency constants
- `MAX_CONCURRENT_PIPELINES = 10` in tasks.py or constants
- File: `nikita/api/routes/tasks.py`

**T3.2** Implement semaphore-based limiter in process-conversations
- Wrap pipeline execution in `asyncio.Semaphore(MAX_CONCURRENT_PIPELINES)`
- If more conversations than limit, process first batch, log deferred count
- File: `nikita/api/routes/tasks.py`

**T3.3** Tests for concurrency limiter
- Test: 25 conversations → only 10 processed
- Test: deferred count logged
- Test: all 5 conversations processed when under limit
- File: `tests/api/test_tasks_concurrency.py`

---

## Story 4: Pipeline Stage Error Tracking (FR-004)

### Tasks

**T4.1** Persist stage errors and timings in job result
- After pipeline completion, include `stage_errors` and `stage_timings` in the `result` JSONB written to `job_executions`
- File: `nikita/api/routes/tasks.py` (process-conversations endpoint)

**T4.2** Tests for stage error persistence
- Test: pipeline with failing stage → stage_errors in job_executions result
- Test: pipeline timings present in result JSONB
- File: `tests/api/test_tasks_pipeline_tracking.py`

---

## Reusable Patterns

- `JobExecutionRepository.has_recent_execution()` — reusable by any cron endpoint
- Semaphore pattern — reusable for other batch endpoints

## Risk Mitigation

- Old endpoint deprecation is non-breaking (410 with migration message)
- Semaphore defaults to 10 — conservative, adjustable via config later
- Idempotency window (50min) leaves 10min buffer for hourly cron drift
