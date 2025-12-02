# Implementation Plan: 011-Background-Tasks

## Overview

Implementation plan for background task infrastructure using pg_cron and Supabase Edge Functions for decay processing, delayed message delivery, and daily summaries.

**Spec Reference**: `spec.md`
**Priority**: P0 (blocks 002-telegram, 005-decay, 008-portal)
**Estimated Tasks**: 14 tasks across 3 user stories

---

## Dependency Analysis

```
┌─────────────────────────────────────────────────────────────┐
│                  011-Background-Tasks                        │
├─────────────────────────────────────────────────────────────┤
│  UPSTREAM (depends on)                                      │
│  ├── 009-database-infrastructure ✅ Done                    │
│  ├── 010-api-infrastructure ✅ Plan Complete                │
│  ├── pg_cron extension (Supabase Pro feature)               │
│  └── Supabase Edge Functions enabled                        │
├─────────────────────────────────────────────────────────────┤
│  DOWNSTREAM (blocks)                                        │
│  ├── 002-telegram-integration (message delivery)            │
│  ├── 005-decay-system (decay processing)                    │
│  └── 008-player-portal (daily summaries)                    │
└─────────────────────────────────────────────────────────────┘
```

---

## Database Schema Required

### pending_responses (for FR-002)
```sql
CREATE TABLE pending_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    telegram_chat_id BIGINT NOT NULL,
    response_text TEXT NOT NULL,
    scheduled_at TIMESTAMPTZ NOT NULL,
    delivered_at TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'pending'
        CHECK (status IN ('pending', 'delivered', 'failed')),
    retry_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_pending_due ON pending_responses(status, scheduled_at)
    WHERE status = 'pending';
```

### job_history (for FR-005)
```sql
CREATE TABLE job_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_name VARCHAR(50) NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'running'
        CHECK (status IN ('running', 'success', 'failed')),
    items_processed INT DEFAULT 0,
    error_message TEXT
);
CREATE INDEX idx_job_name_started ON job_history(job_name, started_at DESC);
```

### daily_summaries (for FR-003)
```sql
CREATE TABLE daily_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    summary_date DATE NOT NULL,
    score_start DECIMAL(5,2),
    score_end DECIMAL(5,2),
    conversations_count INT DEFAULT 0,
    nikita_recap TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, summary_date)
);
```

---

## User Story Tasks

### US-001: Decay Application (P1)

**As a** game designer **I want** decay applied consistently overnight **So that** players who ignore Nikita see score drop

#### T1.1: Create pending_responses Table Migration

**Implements**: FR-002 (AC-002.1)
**File**: Supabase migration

**Acceptance Criteria**:
- [ ] AC-T1.1.1: Table created with all columns from schema
- [ ] AC-T1.1.2: Foreign key to users table with CASCADE delete
- [ ] AC-T1.1.3: Partial index on pending+scheduled_at
- [ ] AC-T1.1.4: Check constraint on status values

#### T1.2: Create job_history Table Migration

**Implements**: FR-005 (AC-005.1, AC-005.3)
**File**: Supabase migration

**Acceptance Criteria**:
- [ ] AC-T1.2.1: Table created with all columns from schema
- [ ] AC-T1.2.2: Index on job_name + started_at DESC
- [ ] AC-T1.2.3: 30-day retention policy documented

#### T1.3: Create daily_summaries Table Migration

**Implements**: FR-003 (AC-003.5)
**File**: Supabase migration

**Acceptance Criteria**:
- [ ] AC-T1.3.1: Table created with all columns from schema
- [ ] AC-T1.3.2: Unique constraint on user_id + summary_date
- [ ] AC-T1.3.3: Foreign key to users table

#### T1.4: Create apply_daily_decay SQL Function

**Implements**: FR-001 (AC-001.1 to AC-001.5), FR-006 (AC-006.1)
**File**: Supabase migration (SQL function)

**Acceptance Criteria**:
- [ ] AC-T1.4.1: Function processes all active users
- [ ] AC-T1.4.2: Respects grace period per chapter
- [ ] AC-T1.4.3: Applies decay_rate from constants
- [ ] AC-T1.4.4: Triggers game_over when score reaches 0
- [ ] AC-T1.4.5: Inserts score_history record with event_type='decay'
- [ ] AC-T1.4.6: Idempotent (checks if already run today)

#### T1.5: Schedule pg_cron Decay Job

**Implements**: FR-001 (AC-001.1)
**File**: Supabase migration (pg_cron schedule)

**Acceptance Criteria**:
- [ ] AC-T1.5.1: Job scheduled at 0 0 * * * (midnight UTC)
- [ ] AC-T1.5.2: Job calls apply_daily_decay()
- [ ] AC-T1.5.3: Job logged to job_history table

---

### US-002: Delayed Response Delivery (P1)

**As a** player **I want** Nikita's messages to arrive at realistic times **So that** the experience feels authentic

#### T2.1: Create deliver-responses Edge Function

**Implements**: FR-002 (AC-002.2, AC-002.3, AC-002.4), FR-004 (AC-004.1 to AC-004.4)
**File**: `supabase/functions/deliver-responses/index.ts`

**Acceptance Criteria**:
- [ ] AC-T2.1.1: Polls pending_responses for due messages
- [ ] AC-T2.1.2: Sends via Telegram Bot API
- [ ] AC-T2.1.3: Marks delivered messages with timestamp
- [ ] AC-T2.1.4: Increments retry_count on failure
- [ ] AC-T2.1.5: Processes max 50 messages per invocation

#### T2.2: Implement Retry Logic with Exponential Backoff

**Implements**: FR-002 (AC-002.4)
**File**: `supabase/functions/deliver-responses/index.ts`

**Acceptance Criteria**:
- [ ] AC-T2.2.1: Retry delay = 2^retry_count minutes
- [ ] AC-T2.2.2: Max 3 retries before marking failed
- [ ] AC-T2.2.3: Failed messages have status='failed'

#### T2.3: Create cleanup-stale Edge Function

**Implements**: FR-002 (AC-002.5)
**File**: `supabase/functions/cleanup-stale/index.ts`

**Acceptance Criteria**:
- [ ] AC-T2.3.1: Marks pending messages >24h old as failed
- [ ] AC-T2.3.2: Logs cleanup count to job_history
- [ ] AC-T2.3.3: Runs daily at midnight UTC

#### T2.4: Schedule pg_cron for Message Delivery

**Implements**: FR-002 (AC-002.2)
**File**: Supabase migration (pg_cron schedule)

**Acceptance Criteria**:
- [ ] AC-T2.4.1: Job scheduled every 30 seconds
- [ ] AC-T2.4.2: Uses net.http_post to invoke Edge Function
- [ ] AC-T2.4.3: Includes Authorization header with service key

---

### US-003: Daily Recap (P2)

**As a** player **I want** to see Nikita's daily summary **So that** I understand how our relationship evolved

#### T3.1: Create generate-summaries Edge Function

**Implements**: FR-003 (AC-003.1 to AC-003.4), FR-006 (AC-006.3)
**File**: `supabase/functions/generate-summaries/index.ts`

**Acceptance Criteria**:
- [ ] AC-T3.1.1: Processes active users without today's summary
- [ ] AC-T3.1.2: Aggregates conversations from previous day
- [ ] AC-T3.1.3: Calculates score_start and score_end
- [ ] AC-T3.1.4: Calls Claude API for Nikita-voice recap
- [ ] AC-T3.1.5: Inserts into daily_summaries table

#### T3.2: Schedule pg_cron for Summary Generation

**Implements**: FR-003 (AC-003.1)
**File**: Supabase migration (pg_cron schedule)

**Acceptance Criteria**:
- [ ] AC-T3.2.1: Job scheduled at 0 6 * * * (6 AM UTC)
- [ ] AC-T3.2.2: Invokes generate-summaries Edge Function
- [ ] AC-T3.2.3: Logs to job_history table

---

### Cross-Cutting Tasks (P1)

#### T4.1: Implement Job History Logging

**Implements**: FR-005 (AC-005.1, AC-005.2)
**File**: `supabase/functions/_shared/job-logger.ts`

**Acceptance Criteria**:
- [ ] AC-T4.1.1: Shared function to log job start/end
- [ ] AC-T4.1.2: Records items_processed count
- [ ] AC-T4.1.3: Captures error_message on failure
- [ ] AC-T4.1.4: Webhook alert for failed jobs (configurable)

#### T4.2: Implement Advisory Locks for Idempotency

**Implements**: FR-006 (AC-006.4)
**File**: SQL function in migration

**Acceptance Criteria**:
- [ ] AC-T4.2.1: pg_advisory_xact_lock used per job
- [ ] AC-T4.2.2: Lock key derived from job_name + date
- [ ] AC-T4.2.3: Concurrent invocations wait or skip

#### T4.3: Create API Endpoint for Manual Job Trigger

**Implements**: FR-005, supports admin operations
**File**: `nikita/api/routes/admin.py`

**Acceptance Criteria**:
- [ ] AC-T4.3.1: POST /admin/trigger-decay callable
- [ ] AC-T4.3.2: POST /admin/trigger-summaries callable
- [ ] AC-T4.3.3: Protected by service key auth
- [ ] AC-T4.3.4: Returns job_history entry ID

---

## Task Dependency Graph

```
T1.1 (pending_responses) ────┐
T1.2 (job_history) ──────────┼──→ T1.4 (decay function)
T1.3 (daily_summaries) ──────┘          ↓
                                   T1.5 (decay cron)
                                        ↓
T2.1 (deliver Edge Fn) ←─────────── T2.4 (delivery cron)
    ↓
T2.2 (retry logic)
    ↓
T2.3 (cleanup Edge Fn)

T3.1 (summary Edge Fn) ←─────────── T3.2 (summary cron)

T4.1 (job logger) ←── All Edge Functions
T4.2 (advisory locks) ←── T1.4, T3.1
T4.3 (admin trigger) ←── T1.4
```

---

## Implementation Sequence

| Phase | Tasks | Est. Effort |
|-------|-------|-------------|
| 1. Schema | T1.1, T1.2, T1.3 | 1-2 hours |
| 2. Decay | T1.4, T1.5, T4.2 | 2-3 hours |
| 3. Delivery | T2.1, T2.2, T2.3, T2.4 | 3-4 hours |
| 4. Summaries | T3.1, T3.2 | 2-3 hours |
| 5. Monitoring | T4.1, T4.3 | 1-2 hours |

**Total Estimated**: 9-14 hours

---

## Files Created/Modified

| File | Action | Purpose |
|------|--------|---------|
| Supabase migration | Create | pending_responses, job_history, daily_summaries |
| Supabase migration | Create | apply_daily_decay() function |
| Supabase migration | Create | pg_cron schedules |
| `supabase/functions/deliver-responses/index.ts` | Create | Message delivery |
| `supabase/functions/cleanup-stale/index.ts` | Create | Stale message cleanup |
| `supabase/functions/generate-summaries/index.ts` | Create | Daily summary generation |
| `supabase/functions/_shared/job-logger.ts` | Create | Shared job logging |
| `nikita/api/routes/admin.py` | Modify | Add trigger endpoints |

---

## Test Strategy

1. **Unit Tests**: Decay calculation, retry logic
2. **Integration Tests**: Edge Function → Supabase → Telegram
3. **Manual Tests**: Trigger jobs via admin endpoint, verify Telegram delivery
4. **Monitoring**: Check job_history for success/failure patterns

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| pg_cron Pro-only feature | Verify Supabase plan includes pg_cron |
| Edge Function cold start | Keep-alive ping, batch processing |
| Telegram rate limits | Exponential backoff, 50 msg/batch limit |
| LLM API costs for summaries | Batch users, cache similar summaries |
