# Spec 105: Schema Cleanup & Observability

## Overview
Drop dead database columns, add game status audit trail, improve LLM scoring fallback, add pipeline timing dashboard data, and create engagement analytics export endpoint.

## Functional Requirements

### FR-001: Drop Dead Columns
Remove `graphiti_group_id` from User model (legacy Neo4j field, never populated after Spec 042 migration to SupabaseMemory).

**Acceptance Criteria:**
- AC-1.1: Supabase migration: `ALTER TABLE users DROP COLUMN IF EXISTS graphiti_group_id`
- AC-1.2: Remove `graphiti_group_id` from `nikita/db/models/user.py`
- AC-1.3: No code references `graphiti_group_id` after removal (grep clean)

### FR-002: Game Status Transition Audit Trail
Log every `game_status` change to an `audit_logs` table for debugging and analytics.

**Acceptance Criteria:**
- AC-2.1: New `audit_logs` table: `(id, user_id, event_type, old_value, new_value, metadata JSONB, created_at)`
- AC-2.2: `AuditLogRepository.log_transition(user_id, old_status, new_status, metadata)` method
- AC-2.3: Called from `UserRepository.update_game_status()` automatically
- AC-2.4: Called from `BossStateMachine.process_pass/process_fail/process_partial()`

### FR-003: LLM Scoring Fallback Alerting
When LLM scoring fails, set `confidence=0.0` on the result, log a warning, and increment an error counter accessible via admin API.

**Acceptance Criteria:**
- AC-3.1: `ScoreAnalyzer.analyze()` returns `ResponseAnalysis(confidence=0.0, ...)` on LLM failure
- AC-3.2: Warning logged: `"LLM scoring failed, using zero-delta fallback"`
- AC-3.3: Error counter stored in `pipeline_metrics` (in-memory dict, exposed via `/admin/metrics`)
- AC-3.4: Fallback returns zero deltas (no score change) rather than raising

### FR-004: Pipeline Timing Data
Track per-stage execution duration and error counts, expose via admin API endpoint.

**Acceptance Criteria:**
- AC-4.1: `PipelineOrchestrator` records `stage_name`, `duration_ms`, `success`, `error` per execution
- AC-4.2: Stored in `job_executions` table (existing) with `stage_timings` JSONB field
- AC-4.3: `GET /api/v1/admin/pipeline/timings` returns last 100 pipeline runs with stage breakdowns
- AC-4.4: Includes p50/p95/p99 duration stats per stage

### FR-005: Engagement Analytics Export
Admin endpoint to export engagement data as JSON for A/B testing analysis.

**Acceptance Criteria:**
- AC-5.1: `GET /api/v1/admin/analytics/engagement` endpoint
- AC-5.2: Returns: `{users: [{user_id, chapter, days_played, relationship_score, game_status, engagement_state, skip_rate, last_active}]}`
- AC-5.3: Supports `?since=YYYY-MM-DD` filter for date range
- AC-5.4: Admin-only access (role check via middleware)

## Non-Functional Requirements
- Migrations are backward-compatible (DROP IF EXISTS, ADD IF NOT EXISTS)
- Audit logging is fire-and-forget (async, non-blocking)
- Pipeline timing adds <5ms overhead per stage
- Tests: 20+ new tests across 5 stories
