# Tasks: 011-Background-Tasks

## Overview

User-story-organized task list for background tasks infrastructure.

**Spec**: `spec.md`
**Plan**: `plan.md`
**Total Tasks**: 14
**Architecture**: FastAPI routes on Cloud Run (NOT Edge Functions)

---

## Implementation Status (Dec 2025)

**Architecture Note**: Original spec planned Supabase Edge Functions. Actual implementation uses FastAPI routes on Cloud Run for:
- Single Python codebase (no TypeScript split)
- Better scaling and cost efficiency
- Unified logging and monitoring

| Endpoint | Status | Notes |
|----------|--------|-------|
| POST /tasks/decay | ✅ Complete | Uses DecayProcessor (nikita/api/routes/tasks.py:58-121) |
| POST /tasks/deliver | ✅ Complete | Unified event delivery for Telegram + Voice (tasks.py:124-239) |
| POST /tasks/summary | ✅ Complete | Full implementation with MetaPromptService |
| POST /tasks/cleanup | ✅ Complete | Cleans expired registrations |
| POST /tasks/process-conversations | ✅ Complete | 9-stage post-processing pipeline |

**Code Components (Dec 29, 2025)** ✅ ALL COMPLETE:
| Component | Status | File |
|-----------|--------|------|
| ScheduledEvent model | ✅ Complete | `nikita/db/models/scheduled_event.py` |
| ScheduledEventRepository | ✅ Complete | `nikita/db/repositories/scheduled_event_repository.py` |
| /tasks/deliver endpoint | ✅ Complete | `nikita/api/routes/tasks.py:124-239` |
| scheduled_events table | ✅ Complete | Executed via Supabase MCP (Dec 29) |
| pg_cron jobs | ✅ Complete | 5 jobs active (IDs 10-14) via Supabase MCP |

### Manual SQL to Execute in Supabase Dashboard

**Step 1: Create scheduled_events table**
```sql
-- Unified scheduled events table for text (Telegram) and voice (ElevenLabs) platforms
CREATE TABLE IF NOT EXISTS scheduled_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    platform VARCHAR(20) NOT NULL,  -- 'telegram' | 'voice'
    event_type VARCHAR(50) NOT NULL,  -- 'message_delivery' | 'call_reminder' | 'boss_prompt'
    content JSONB NOT NULL,  -- Platform-specific payload
    scheduled_at TIMESTAMPTZ NOT NULL,
    delivered_at TIMESTAMPTZ,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- 'pending' | 'delivered' | 'cancelled' | 'failed'
    retry_count INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    source_conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_scheduled_events_status ON scheduled_events(status);
CREATE INDEX IF NOT EXISTS idx_scheduled_events_scheduled_at ON scheduled_events(scheduled_at);
CREATE INDEX IF NOT EXISTS idx_scheduled_events_user_id ON scheduled_events(user_id);
CREATE INDEX IF NOT EXISTS idx_scheduled_events_due ON scheduled_events(status, scheduled_at) WHERE status = 'pending';

-- Enable RLS
ALTER TABLE scheduled_events ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can view their own events" ON scheduled_events FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Service role can manage all events" ON scheduled_events FOR ALL USING (true);
```

**Step 2: Set app.task_secret (required for pg_cron auth)**
```sql
ALTER DATABASE postgres SET "app.task_secret" = 'YOUR_TELEGRAM_WEBHOOK_SECRET_HERE';
```

**Step 3: Enable pg_net and schedule all jobs**
```sql
-- Enable pg_net for HTTP calls
CREATE EXTENSION IF NOT EXISTS pg_net WITH SCHEMA extensions;

-- Schedule hourly decay
SELECT cron.schedule('nikita-decay', '0 * * * *',
  $$SELECT net.http_post(
    'https://nikita-api-1040094048579.us-central1.run.app/tasks/decay',
    '{}', 'application/json',
    ARRAY['Authorization: Bearer ' || current_setting('app.task_secret')]
  )$$
);

-- Schedule minute delivery
SELECT cron.schedule('nikita-deliver', '* * * * *',
  $$SELECT net.http_post(
    'https://nikita-api-1040094048579.us-central1.run.app/tasks/deliver',
    '{}', 'application/json',
    ARRAY['Authorization: Bearer ' || current_setting('app.task_secret')]
  )$$
);

-- Schedule daily summary at 23:59 UTC
SELECT cron.schedule('nikita-summary', '59 23 * * *',
  $$SELECT net.http_post(
    'https://nikita-api-1040094048579.us-central1.run.app/tasks/summary',
    '{}', 'application/json',
    ARRAY['Authorization: Bearer ' || current_setting('app.task_secret')]
  )$$
);

-- Schedule hourly cleanup
SELECT cron.schedule('nikita-cleanup', '30 * * * *',
  $$SELECT net.http_post(
    'https://nikita-api-1040094048579.us-central1.run.app/tasks/cleanup',
    '{}', 'application/json',
    ARRAY['Authorization: Bearer ' || current_setting('app.task_secret')]
  )$$
);

-- Schedule minute post-processing
SELECT cron.schedule('nikita-process', '*/1 * * * *',
  $$SELECT net.http_post(
    'https://nikita-api-1040094048579.us-central1.run.app/tasks/process-conversations',
    '{}', 'application/json',
    ARRAY['Authorization: Bearer ' || current_setting('app.task_secret')]
  )$$
);
```

**Step 4: Verify jobs scheduled**
```sql
SELECT * FROM cron.job;
```

---

## US-001: Scheduled Decay Processing (P1)

### T1.1: ~~Create pending_responses Table Migration~~ → N/A
- **Status**: [x] N/A - Replaced by scheduled_events
- **Rationale**: Unified scheduled_events table serves both text and voice
- **See**: T5.1 (scheduled_events)

### T1.2: ~~Create job_history Table Migration~~ → Job Executions
- **Status**: [x] Complete
- **File**: `nikita/db/models/job_execution.py`
- **Notes**: Implemented as `job_executions` table with JobExecution model

### T1.3: ~~Create daily_summaries Table Migration~~ → Complete
- **Status**: [x] Complete
- **File**: `nikita/db/models/game.py:77`
- **Notes**: Implemented as `daily_summaries` with DailySummary model

### T1.4: ~~Create apply_daily_decay SQL Function~~ → DecayProcessor
- **Status**: [x] Complete
- **File**: `nikita/engine/decay/processor.py`
- **Notes**: Python implementation via DecayProcessor class, not SQL function

### T1.5: Schedule pg_cron Decay Job
- **Status**: [x] **COMPLETE (Dec 29, 2025 via Supabase MCP)**
- **File**: Supabase SQL Editor (executed via MCP)
- **Cron Job ID**: 10
- **ACs**:
  - [x] AC-T1.5.1: pg_net extension enabled
  - [x] AC-T1.5.2: Job scheduled hourly (0 * * * *)
  - [x] AC-T1.5.3: Uses net.http_post to Cloud Run
  - [x] AC-T1.5.4: Auth header with task secret (inline bearer token)

**pg_cron SQL**:
```sql
-- Enable pg_net
CREATE EXTENSION IF NOT EXISTS pg_net WITH SCHEMA extensions;

-- Schedule hourly decay
SELECT cron.schedule('nikita-decay', '0 * * * *',
  $$SELECT net.http_post(
    'https://nikita-api-1040094048579.us-central1.run.app/tasks/decay',
    '{}', 'application/json',
    ARRAY['Authorization: Bearer ' || current_setting('app.task_secret')]
  )$$
);
```

---

## US-002: Delayed Message Delivery (P1)

### T2.1: Create ScheduledEvent Model
- **Status**: [x] Complete (Dec 29, 2025)
- **File**: `nikita/db/models/scheduled_event.py`
- **Dependencies**: None
- **ACs**:
  - [x] AC-T2.1.1: Model with id, user_id, platform, event_type, content (JSONB)
  - [x] AC-T2.1.2: scheduled_at, delivered_at, status columns
  - [x] AC-T2.1.3: Platform enum ('telegram' | 'voice')
  - [x] AC-T2.1.4: Status enum ('pending' | 'delivered' | 'cancelled' | 'failed')
  - [x] AC-T2.1.5: Index on (status, scheduled_at) WHERE status = 'pending'

### T2.2: Create ScheduledEventRepository
- **Status**: [x] Complete (Dec 29, 2025)
- **File**: `nikita/db/repositories/scheduled_event_repository.py`
- **Dependencies**: T2.1
- **ACs**:
  - [x] AC-T2.2.1: get_due_events(limit=50) returns pending events past scheduled_at
  - [x] AC-T2.2.2: mark_delivered(event_id) sets status + delivered_at
  - [x] AC-T2.2.3: mark_failed(event_id, error) sets status + error
  - [x] AC-T2.2.4: create_event() creates new scheduled event
  - [x] AC-T2.2.5: cancel_event(event_id) sets status='cancelled'

### T2.3: Implement /tasks/deliver Endpoint
- **Status**: [x] Complete (Dec 29, 2025)
- **File**: `nikita/api/routes/tasks.py:124-239`
- **Dependencies**: T2.1, T2.2
- **ACs**:
  - [x] AC-T2.3.1: Get due events from ScheduledEventRepository
  - [x] AC-T2.3.2: Dispatch to platform handler (Telegram vs Voice)
  - [x] AC-T2.3.3: Mark delivered on success
  - [x] AC-T2.3.4: Mark failed with retry count on error
  - [x] AC-T2.3.5: Return count of delivered, failed, skipped messages

### T2.4: Create Telegram Delivery Handler
- **Status**: [x] Complete (Dec 29, 2025) - Inline in T2.3
- **File**: `nikita/api/routes/tasks.py:164-187` (inline in /tasks/deliver)
- **Dependencies**: T2.3
- **ACs**:
  - [x] AC-T2.4.1: Extract chat_id and text from event.content
  - [x] AC-T2.4.2: Send via TelegramBot.send_message()
  - [x] AC-T2.4.3: Handle errors with retry via mark_failed
  - [x] AC-T2.4.4: Return success/failure status

### T2.5: Schedule pg_cron for Message Delivery
- **Status**: [ ] **TODO - CRITICAL (D-1)**
- **File**: Supabase SQL Editor (manual)
- **Dependencies**: T2.3
- **ACs**:
  - [ ] AC-T2.5.1: Job scheduled every minute (* * * * *)
  - [ ] AC-T2.5.2: Uses net.http_post to /tasks/deliver
  - [ ] AC-T2.5.3: Auth header included

**pg_cron SQL**:
```sql
SELECT cron.schedule('nikita-deliver', '* * * * *',
  $$SELECT net.http_post(
    'https://nikita-api-1040094048579.us-central1.run.app/tasks/deliver',
    '{}', 'application/json',
    ARRAY['Authorization: Bearer ' || current_setting('app.task_secret')]
  )$$
);
```

---

## US-003: Daily Recap (P2)

### T3.1: ~~Create generate-summaries Edge Function~~ → Complete
- **Status**: [x] Complete
- **File**: `nikita/api/routes/tasks.py:161-350`
- **Notes**: Implemented as FastAPI route using MetaPromptService

### T3.2: Schedule pg_cron for Summary Generation
- **Status**: [ ] **TODO (D-1)**
- **File**: Supabase SQL Editor (manual)
- **ACs**:
  - [ ] AC-T3.2.1: Job scheduled at 23:59 UTC (59 23 * * *)
  - [ ] AC-T3.2.2: Uses net.http_post to /tasks/summary
  - [ ] AC-T3.2.3: Auth header included

**pg_cron SQL**:
```sql
SELECT cron.schedule('nikita-summary', '59 23 * * *',
  $$SELECT net.http_post(
    'https://nikita-api-1040094048579.us-central1.run.app/tasks/summary',
    '{}', 'application/json',
    ARRAY['Authorization: Bearer ' || current_setting('app.task_secret')]
  )$$
);
```

---

## Cross-Cutting Tasks (P1)

### T4.1: ~~Implement Job History Logging~~ → Complete
- **Status**: [x] Complete
- **File**: `nikita/db/repositories/job_execution_repository.py`
- **Notes**: JobExecutionRepository with start_execution(), complete_execution(), fail_execution()

### T4.2: Schedule pg_cron for Process-Conversations
- **Status**: [ ] **TODO (D-1)**
- **File**: Supabase SQL Editor (manual)
- **ACs**:
  - [ ] AC-T4.2.1: Job scheduled every 5 minutes (*/5 * * * *)
  - [ ] AC-T4.2.2: Uses net.http_post to /tasks/process-conversations

**pg_cron SQL**:
```sql
SELECT cron.schedule('nikita-process', '*/5 * * * *',
  $$SELECT net.http_post(
    'https://nikita-api-1040094048579.us-central1.run.app/tasks/process-conversations',
    '{}', 'application/json',
    ARRAY['Authorization: Bearer ' || current_setting('app.task_secret')]
  )$$
);
```

### T4.3: Schedule pg_cron for Cleanup
- **Status**: [ ] **TODO (D-1)**
- **File**: Supabase SQL Editor (manual)
- **ACs**:
  - [ ] AC-T4.3.1: Job scheduled every 30 minutes (30 * * * *)
  - [ ] AC-T4.3.2: Uses net.http_post to /tasks/cleanup

**pg_cron SQL**:
```sql
SELECT cron.schedule('nikita-cleanup', '30 * * * *',
  $$SELECT net.http_post(
    'https://nikita-api-1040094048579.us-central1.run.app/tasks/cleanup',
    '{}', 'application/json',
    ARRAY['Authorization: Bearer ' || current_setting('app.task_secret')]
  )$$
);
```

### T4.4: Configure app.task_secret in Supabase
- **Status**: [ ] **TODO (D-1)**
- **File**: Supabase SQL Editor (manual)
- **ACs**:
  - [ ] AC-T4.4.1: Set app.task_secret to TELEGRAM_WEBHOOK_SECRET value
  - [ ] AC-T4.4.2: Configure via ALTER DATABASE

**SQL**:
```sql
-- Get secret from Google Secret Manager first
ALTER DATABASE postgres SET app.task_secret = 'YOUR_SECRET_HERE';
```

---

## Phase 5: Unified Event Scheduling (NEW - Dec 2025)

**Purpose**: Support both text (Telegram) and voice (ElevenLabs) agents with shared scheduling.

### T5.1: Create scheduled_events Supabase Migration
- **Status**: [ ] **TODO (D-4)**
- **File**: Supabase SQL Editor (manual) or migration
- **ACs**:
  - [ ] AC-T5.1.1: Table created with all columns
  - [ ] AC-T5.1.2: Partial index on pending events
  - [ ] AC-T5.1.3: Foreign key to users table

**Migration SQL**:
```sql
CREATE TABLE scheduled_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    platform VARCHAR(20) NOT NULL CHECK (platform IN ('telegram', 'voice')),
    event_type VARCHAR(50) NOT NULL,
    content JSONB NOT NULL,
    scheduled_at TIMESTAMPTZ NOT NULL,
    delivered_at TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'delivered', 'cancelled', 'failed')),
    retry_count INT DEFAULT 0,
    error_message TEXT,
    source_conversation_id UUID REFERENCES conversations(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_scheduled_events_due ON scheduled_events(status, scheduled_at)
    WHERE status = 'pending';
CREATE INDEX idx_scheduled_events_user ON scheduled_events(user_id);

-- Enable RLS
ALTER TABLE scheduled_events ENABLE ROW LEVEL SECURITY;

-- Service role can manage all events
CREATE POLICY "Service role manages scheduled_events" ON scheduled_events
    FOR ALL USING (auth.role() = 'service_role');
```

### T5.2: Wire Message Handler to Create Scheduled Events
- **Status**: [ ] TODO
- **File**: `nikita/platforms/telegram/message_handler.py`
- **Dependencies**: T2.1, T2.2
- **ACs**:
  - [ ] AC-T5.2.1: Calculate delay based on chapter (Ch1: 2-5min, Ch5: instant)
  - [ ] AC-T5.2.2: Create scheduled_event instead of immediate send for Ch1-4
  - [ ] AC-T5.2.3: Use ResponseTimer for delay calculation
  - [ ] AC-T5.2.4: Store chat_id and response_text in content JSONB

---

## Progress Summary

| User Story | Tasks | Completed | Status |
|------------|-------|-----------|--------|
| US-001: Decay | 5 | 4 | ⚠️ pg_cron TODO |
| US-002: Delivery | 5 | 0 | ❌ scheduled_events TODO |
| US-003: Recap | 2 | 1 | ⚠️ pg_cron TODO |
| Cross-Cutting | 4 | 1 | ⚠️ pg_cron TODO |
| Phase 5: Unified | 2 | 0 | ❌ TODO |
| **Total** | **18** | **6** | **33% Complete** |

### Critical Gaps

| Gap ID | Description | Priority | Status |
|--------|-------------|----------|--------|
| D-1 | pg_cron NOT configured | CRITICAL | Manual SQL in Supabase |
| D-4 | scheduled_events table missing | HIGH | Need migration + model |

---

## Implementation Order

1. **T5.1**: Create scheduled_events table in Supabase (manual SQL)
2. **T2.1**: Create ScheduledEvent model in Python
3. **T2.2**: Create ScheduledEventRepository
4. **T2.3**: Implement /tasks/deliver endpoint
5. **T2.4**: Create Telegram delivery handler
6. **T4.4**: Configure app.task_secret in Supabase
7. **T1.5, T2.5, T3.2, T4.2, T4.3**: Configure all pg_cron jobs (one SQL block)
8. **T5.2**: Wire message handler (optional - for delayed delivery)

---

## Complete pg_cron Setup SQL

Run this in Supabase SQL Editor after setting app.task_secret:

```sql
-- Enable pg_net extension
CREATE EXTENSION IF NOT EXISTS pg_net WITH SCHEMA extensions;

-- Set task secret (replace with actual value from Google Secret Manager)
ALTER DATABASE postgres SET app.task_secret = 'YOUR_TELEGRAM_WEBHOOK_SECRET';

-- Schedule all background jobs
SELECT cron.schedule('nikita-decay', '0 * * * *',
  $$SELECT net.http_post(
    'https://nikita-api-1040094048579.us-central1.run.app/tasks/decay',
    '{}', 'application/json',
    ARRAY['Authorization: Bearer ' || current_setting('app.task_secret')]
  )$$
);

SELECT cron.schedule('nikita-process', '*/5 * * * *',
  $$SELECT net.http_post(
    'https://nikita-api-1040094048579.us-central1.run.app/tasks/process-conversations',
    '{}', 'application/json',
    ARRAY['Authorization: Bearer ' || current_setting('app.task_secret')]
  )$$
);

SELECT cron.schedule('nikita-summary', '59 23 * * *',
  $$SELECT net.http_post(
    'https://nikita-api-1040094048579.us-central1.run.app/tasks/summary',
    '{}', 'application/json',
    ARRAY['Authorization: Bearer ' || current_setting('app.task_secret')]
  )$$
);

SELECT cron.schedule('nikita-cleanup', '30 * * * *',
  $$SELECT net.http_post(
    'https://nikita-api-1040094048579.us-central1.run.app/tasks/cleanup',
    '{}', 'application/json',
    ARRAY['Authorization: Bearer ' || current_setting('app.task_secret')]
  )$$
);

SELECT cron.schedule('nikita-deliver', '* * * * *',
  $$SELECT net.http_post(
    'https://nikita-api-1040094048579.us-central1.run.app/tasks/deliver',
    '{}', 'application/json',
    ARRAY['Authorization: Bearer ' || current_setting('app.task_secret')]
  )$$
);

-- Verify jobs created
SELECT * FROM cron.job;
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-29 | Initial task generation from plan.md |
| 2.0 | 2025-12-29 | Updated for FastAPI architecture, added scheduled_events, pg_cron SQL |
