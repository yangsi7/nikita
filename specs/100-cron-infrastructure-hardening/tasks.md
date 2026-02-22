# Tasks: Spec 100 — Cron Infrastructure Hardening

## Story 1: Consolidate Stuck Recovery

- [ ] T1.1: Add `has_recent_execution(job_name, minutes)` to `JobExecutionRepository`
  - AC: Returns True if completed execution exists within window, False otherwise
  - Red: Test with no executions → False; test with recent → True
  - File: `nikita/db/repositories/job_execution_repository.py`

- [ ] T1.2: Create `POST /tasks/recover` endpoint
  - AC: Finds stuck conversations (processing > 30min), sets to failed, logs recovery count
  - Red: Mock 3 stuck + 2 active conversations → only 3 recovered
  - File: `nikita/api/routes/tasks.py`

- [ ] T1.3: Deprecate old detect-stuck/recover-stuck endpoints (if they exist)
  - AC: Old endpoints return 410 Gone with migration message
  - Red: Call old endpoint → 410 response
  - File: `nikita/api/routes/tasks.py`

- [ ] T1.4: Write tests for recover endpoint
  - AC: 4 tests — recovery, no-op, job tracking, auth
  - File: `tests/api/test_tasks_recover.py`

## Story 2: Decay Idempotency Guard

- [ ] T2.1: Add idempotency check to `/tasks/decay`
  - AC: Second call within 50min returns `{"status": "skipped", "reason": "recent_execution"}`
  - Red: Call decay twice → second call returns skipped
  - File: `nikita/api/routes/tasks.py`

- [ ] T2.2: Write tests for decay idempotency
  - AC: 3 tests — normal run, skipped on double-fire, processes after window expires
  - File: `tests/api/test_tasks_decay_idempotency.py`

## Story 3: Pipeline Concurrency Limiter

- [ ] T3.1: Add `MAX_CONCURRENT_PIPELINES = 10` constant
  - AC: Constant defined, used by process-conversations
  - File: `nikita/api/routes/tasks.py`

- [ ] T3.2: Implement semaphore limiter in process-conversations
  - AC: Only MAX_CONCURRENT_PIPELINES conversations processed per cycle; remainder deferred
  - Red: 25 pending → only 10 processed, log shows 15 deferred
  - File: `nikita/api/routes/tasks.py`

- [ ] T3.3: Write tests for concurrency limiter
  - AC: 3 tests — over-limit (10 processed), under-limit (all processed), deferred logging
  - File: `tests/api/test_tasks_concurrency.py`

## Story 4: Pipeline Stage Error Tracking

- [ ] T4.1: Persist stage_errors and stage_timings in job_executions result JSONB
  - AC: After pipeline, job_executions.result contains `stage_errors` and `stage_timings` keys
  - Red: Run pipeline with mocked failing stage → verify JSONB contains error details
  - File: `nikita/api/routes/tasks.py`

- [ ] T4.2: Write tests for stage error persistence
  - AC: 2 tests — errors persisted, timings persisted
  - File: `tests/api/test_tasks_pipeline_tracking.py`

---

**Total**: 11 tasks | **Estimated tests**: 15+
