# Plan: Spec 105 — Schema Cleanup & Observability

## Stories (5 stories, 15 tasks)

### Story 1: Drop Dead Columns (FR-001)
**Goal**: Remove `graphiti_group_id` from User model and DB.

- T1.1: Apply Supabase migration: `DROP COLUMN IF EXISTS graphiti_group_id` [S]
- T1.2: Remove field from `nikita/db/models/user.py` [S]
- T1.3: Verify no code references (grep clean) [S]

### Story 2: Game Status Audit Trail (FR-002)
**Goal**: Log every game_status transition for debugging.

- T2.1: Create `audit_logs` table via Supabase migration [S]
- T2.2: Create `AuditLogRepository` with `log_transition()` method [S]
- T2.3: Wire into `UserRepository.update_game_status()` [S]
- T2.4: Wire into BossStateMachine process_pass/fail/partial [S]
- T2.5: Tests — 4 tests [S]

### Story 3: LLM Scoring Fallback (FR-003)
**Goal**: Graceful degradation when LLM scoring fails.

- T3.1: Modify `ScoreAnalyzer.analyze()` to return zero-delta on failure [S]
- T3.2: Add confidence=0.0 and warning log [S]
- T3.3: Add in-memory error counter [S]
- T3.4: Tests — 3 tests [S]

### Story 4: Pipeline Timing Data (FR-004)
**Goal**: Track per-stage execution timing, expose via admin API.

- T4.1: Add `stage_timings` recording in `PipelineOrchestrator.process()` [M]
- T4.2: Store timings in `job_executions.metadata` JSONB [S]
- T4.3: Create `GET /api/v1/admin/pipeline/timings` endpoint [M]
- T4.4: Tests — 3 tests [S]

### Story 5: Engagement Analytics Export (FR-005)
**Goal**: Admin endpoint for engagement data export.

- T5.1: Create `GET /api/v1/admin/analytics/engagement` endpoint [M]
- T5.2: Implement query with date filter [S]
- T5.3: Tests — 3 tests [S]

## Dependencies
- Spec 100 (pipeline tracking) — done (job_executions table exists)

## Risk Mitigation
- Migrations use IF EXISTS/IF NOT EXISTS for safety
- Audit logging is non-blocking (fire-and-forget async)
- All admin endpoints behind role check
