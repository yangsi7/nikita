# Tasks: Spec 105 — Schema Cleanup & Observability

## Story 1: Drop Dead Columns

### T1.1: Apply migration [S]
- Supabase migration: `ALTER TABLE users DROP COLUMN IF EXISTS graphiti_group_id`
- **Verify**: Column gone via `\d users`

### T1.2: Remove from model [S]
- **Red**: Test User model has no `graphiti_group_id` attribute
- **Green**: Delete field from `nikita/db/models/user.py`
- **File**: `nikita/db/models/user.py`

### T1.3: Grep clean [S]
- `rg "graphiti_group_id" --type py` returns 0 results (excluding migrations)

## Story 2: Game Status Audit Trail

### T2.1: Create audit_logs table [S]
- Supabase migration: CREATE TABLE audit_logs (id UUID PK, user_id UUID, event_type TEXT, old_value TEXT, new_value TEXT, metadata JSONB, created_at TIMESTAMPTZ DEFAULT now())
- Index: `(user_id, created_at DESC)`

### T2.2: AuditLogRepository [S]
- **Red**: Test `log_transition()` inserts row with correct fields
- **Green**: Implement repository with insert method
- **File**: `nikita/db/repositories/audit_log_repository.py`

### T2.3: Wire into UserRepository [S]
- **Red**: Test `update_game_status()` calls `log_transition()`
- **Green**: Add audit logging call
- **File**: `nikita/db/repositories/user_repository.py`

### T2.4: Wire into BossStateMachine [S]
- **Red**: Test process_pass/fail/partial log status transitions
- **Green**: Add audit logging calls
- **File**: `nikita/engine/chapters/boss.py`

### T2.5: Tests [S]
- **File**: `tests/db/repositories/test_audit_log.py`
- 4 tests: log_transition creates row, includes metadata, user_repo integration, boss integration

## Story 3: LLM Scoring Fallback

### T3.1: Zero-delta fallback [S]
- **Red**: Test analyze() returns zero deltas on LLM exception
- **Green**: Wrap LLM call in try/except, return neutral ResponseAnalysis
- **File**: `nikita/engine/scoring/analyzer.py`

### T3.2: Confidence + warning [S]
- **Red**: Test fallback result has confidence=0.0, warning logged
- **Green**: Set confidence field, add logger.warning
- **File**: `nikita/engine/scoring/analyzer.py`

### T3.3: Error counter [S]
- **Red**: Test error counter increments on failure
- **Green**: Module-level dict counter, exposed via function
- **File**: `nikita/engine/scoring/analyzer.py`

### T3.4: Tests [S]
- **File**: `tests/engine/scoring/test_scoring_fallback.py`
- 3 tests: zero-delta on error, confidence=0.0, counter increment

## Story 4: Pipeline Timing

### T4.1: Record stage timings [M]
- **Red**: Test orchestrator records duration_ms per stage
- **Green**: Wrap each stage.run() with timer, store in result
- **File**: `nikita/pipeline/orchestrator.py`

### T4.2: Store in job_executions [S]
- **Red**: Test stage_timings persisted in metadata JSONB
- **Green**: Add stage_timings to job execution metadata
- **File**: `nikita/pipeline/orchestrator.py`

### T4.3: Admin timings endpoint [M]
- **Red**: Test GET /admin/pipeline/timings returns structured data
- **Green**: Create route with p50/p95/p99 calculation
- **File**: `nikita/api/routes/admin.py`

### T4.4: Tests [S]
- **File**: `tests/pipeline/test_pipeline_timing.py`
- 3 tests: timing recorded, stored in metadata, endpoint returns stats

## Story 5: Engagement Analytics

### T5.1: Analytics endpoint [M]
- **Red**: Test GET /admin/analytics/engagement returns user list
- **Green**: Create route with query
- **File**: `nikita/api/routes/admin.py`

### T5.2: Date filter [S]
- **Red**: Test ?since=2026-01-01 filters results
- **Green**: Add query parameter handling
- **File**: `nikita/api/routes/admin.py`

### T5.3: Tests [S]
- **File**: `tests/api/routes/test_admin_analytics.py`
- 3 tests: returns data, date filter works, empty result

---

**Total**: 15 tasks, 16 tests, 6 source files modified, 5 test files created
