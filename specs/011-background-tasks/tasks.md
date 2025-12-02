# Tasks: 011-Background-Tasks

## Overview

User-story-organized task list for background tasks infrastructure.

**Spec**: `spec.md`
**Plan**: `plan.md`
**Total Tasks**: 14

---

## US-001: Decay Application (P1)

### T1.1: Create pending_responses Table Migration
- **Status**: [ ] Pending
- **File**: Supabase migration
- **Dependencies**: None
- **ACs**:
  - [ ] AC-T1.1.1: Table created with all columns from schema
  - [ ] AC-T1.1.2: Foreign key to users table with CASCADE delete
  - [ ] AC-T1.1.3: Partial index on pending+scheduled_at
  - [ ] AC-T1.1.4: Check constraint on status values

### T1.2: Create job_history Table Migration
- **Status**: [ ] Pending
- **File**: Supabase migration
- **Dependencies**: None
- **ACs**:
  - [ ] AC-T1.2.1: Table created with all columns from schema
  - [ ] AC-T1.2.2: Index on job_name + started_at DESC
  - [ ] AC-T1.2.3: 30-day retention policy documented

### T1.3: Create daily_summaries Table Migration
- **Status**: [ ] Pending
- **File**: Supabase migration
- **Dependencies**: None
- **ACs**:
  - [ ] AC-T1.3.1: Table created with all columns from schema
  - [ ] AC-T1.3.2: Unique constraint on user_id + summary_date
  - [ ] AC-T1.3.3: Foreign key to users table

### T1.4: Create apply_daily_decay SQL Function
- **Status**: [ ] Pending
- **File**: Supabase migration (SQL function)
- **Dependencies**: T1.2 (job_history)
- **ACs**:
  - [ ] AC-T1.4.1: Function processes all active users
  - [ ] AC-T1.4.2: Respects grace period per chapter
  - [ ] AC-T1.4.3: Applies decay_rate from constants
  - [ ] AC-T1.4.4: Triggers game_over when score reaches 0
  - [ ] AC-T1.4.5: Inserts score_history record with event_type='decay'
  - [ ] AC-T1.4.6: Idempotent (checks if already run today)

### T1.5: Schedule pg_cron Decay Job
- **Status**: [ ] Pending
- **File**: Supabase migration (pg_cron schedule)
- **Dependencies**: T1.4
- **ACs**:
  - [ ] AC-T1.5.1: Job scheduled at 0 0 * * * (midnight UTC)
  - [ ] AC-T1.5.2: Job calls apply_daily_decay()
  - [ ] AC-T1.5.3: Job logged to job_history table

---

## US-002: Delayed Response Delivery (P1)

### T2.1: Create deliver-responses Edge Function
- **Status**: [ ] Pending
- **File**: `supabase/functions/deliver-responses/index.ts`
- **Dependencies**: T1.1, T1.2
- **ACs**:
  - [ ] AC-T2.1.1: Polls pending_responses for due messages
  - [ ] AC-T2.1.2: Sends via Telegram Bot API
  - [ ] AC-T2.1.3: Marks delivered messages with timestamp
  - [ ] AC-T2.1.4: Increments retry_count on failure
  - [ ] AC-T2.1.5: Processes max 50 messages per invocation

### T2.2: Implement Retry Logic with Exponential Backoff
- **Status**: [ ] Pending
- **File**: `supabase/functions/deliver-responses/index.ts`
- **Dependencies**: T2.1
- **ACs**:
  - [ ] AC-T2.2.1: Retry delay = 2^retry_count minutes
  - [ ] AC-T2.2.2: Max 3 retries before marking failed
  - [ ] AC-T2.2.3: Failed messages have status='failed'

### T2.3: Create cleanup-stale Edge Function
- **Status**: [ ] Pending
- **File**: `supabase/functions/cleanup-stale/index.ts`
- **Dependencies**: T1.1
- **ACs**:
  - [ ] AC-T2.3.1: Marks pending messages >24h old as failed
  - [ ] AC-T2.3.2: Logs cleanup count to job_history
  - [ ] AC-T2.3.3: Runs daily at midnight UTC

### T2.4: Schedule pg_cron for Message Delivery
- **Status**: [ ] Pending
- **File**: Supabase migration (pg_cron schedule)
- **Dependencies**: T2.1
- **ACs**:
  - [ ] AC-T2.4.1: Job scheduled every 30 seconds
  - [ ] AC-T2.4.2: Uses net.http_post to invoke Edge Function
  - [ ] AC-T2.4.3: Includes Authorization header with service key

---

## US-003: Daily Recap (P2)

### T3.1: Create generate-summaries Edge Function
- **Status**: [ ] Pending
- **File**: `supabase/functions/generate-summaries/index.ts`
- **Dependencies**: T1.3, T4.1
- **ACs**:
  - [ ] AC-T3.1.1: Processes active users without today's summary
  - [ ] AC-T3.1.2: Aggregates conversations from previous day
  - [ ] AC-T3.1.3: Calculates score_start and score_end
  - [ ] AC-T3.1.4: Calls Claude API for Nikita-voice recap
  - [ ] AC-T3.1.5: Inserts into daily_summaries table

### T3.2: Schedule pg_cron for Summary Generation
- **Status**: [ ] Pending
- **File**: Supabase migration (pg_cron schedule)
- **Dependencies**: T3.1
- **ACs**:
  - [ ] AC-T3.2.1: Job scheduled at 0 6 * * * (6 AM UTC)
  - [ ] AC-T3.2.2: Invokes generate-summaries Edge Function
  - [ ] AC-T3.2.3: Logs to job_history table

---

## Cross-Cutting Tasks (P1)

### T4.1: Implement Job History Logging
- **Status**: [ ] Pending
- **File**: `supabase/functions/_shared/job-logger.ts`
- **Dependencies**: T1.2
- **ACs**:
  - [ ] AC-T4.1.1: Shared function to log job start/end
  - [ ] AC-T4.1.2: Records items_processed count
  - [ ] AC-T4.1.3: Captures error_message on failure
  - [ ] AC-T4.1.4: Webhook alert for failed jobs (configurable)

### T4.2: Implement Advisory Locks for Idempotency
- **Status**: [ ] Pending
- **File**: SQL function in migration
- **Dependencies**: None
- **ACs**:
  - [ ] AC-T4.2.1: pg_advisory_xact_lock used per job
  - [ ] AC-T4.2.2: Lock key derived from job_name + date
  - [ ] AC-T4.2.3: Concurrent invocations wait or skip

### T4.3: Create API Endpoint for Manual Job Trigger
- **Status**: [ ] Pending
- **File**: `nikita/api/routes/admin.py`
- **Dependencies**: T1.4 (decay function exists)
- **ACs**:
  - [ ] AC-T4.3.1: POST /admin/trigger-decay callable
  - [ ] AC-T4.3.2: POST /admin/trigger-summaries callable
  - [ ] AC-T4.3.3: Protected by service key auth
  - [ ] AC-T4.3.4: Returns job_history entry ID

---

## Progress Summary

| User Story | Tasks | Completed | Status |
|------------|-------|-----------|--------|
| US-001: Decay | 5 | 0 | Pending |
| US-002: Delivery | 4 | 0 | Pending |
| US-003: Recap | 2 | 0 | Pending |
| Cross-Cutting | 3 | 0 | Pending |
| **Total** | **14** | **0** | **Not Started** |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-29 | Initial task generation from plan.md |
