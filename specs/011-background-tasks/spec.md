# 011: Background Tasks Infrastructure

## Overview

Cross-cutting infrastructure specification defining asynchronous task processing for Nikita, including pg_cron scheduled jobs, Supabase Edge Functions, and delayed message delivery.

**Type**: Infrastructure
**Blocks**: 002-telegram-integration, 005-decay-system
**References**: `memory/integrations.md#telegram-integration`

---

## Functional Requirements

### FR-001: Scheduled Decay Processing

The system SHALL apply daily relationship decay via pg_cron.

**Acceptance Criteria**:
- AC-001.1: Decay job runs daily at 00:00 UTC
- AC-001.2: Only affects users past grace period
- AC-001.3: Decay rate matches current chapter
- AC-001.4: Game over triggered when score reaches 0
- AC-001.5: All decay events logged to score_history

**Decay Logic**:
```sql
-- pg_cron job: apply_daily_decay
FOR user IN (SELECT * FROM users WHERE game_status = 'active')
  IF now() - last_interaction_at > grace_periods[chapter]
    new_score = max(0, relationship_score - decay_rates[chapter])
    UPDATE users SET relationship_score = new_score
    INSERT INTO score_history (event_type = 'decay')
    IF new_score = 0 THEN
      UPDATE users SET game_status = 'game_over'
```

### FR-002: Delayed Message Delivery

The system SHALL deliver Nikita's responses after calculated delays.

**Acceptance Criteria**:
- AC-002.1: Pending responses stored in `pending_responses` table
- AC-002.2: Edge Function polls for due messages every 30 seconds
- AC-002.3: Messages delivered via Telegram API
- AC-002.4: Delivery failures retry 3 times with exponential backoff
- AC-002.5: Stale messages (>24h) marked failed and skipped

**Pending Responses Schema**:
```sql
pending_responses
├── id: UUID (PK)
├── user_id: UUID FK
├── telegram_chat_id: BIGINT NOT NULL
├── response_text: TEXT NOT NULL
├── scheduled_at: TIMESTAMPTZ NOT NULL
├── delivered_at: TIMESTAMPTZ
├── status: VARCHAR(20) DEFAULT 'pending'
│   CHECK (status IN ('pending', 'delivered', 'failed'))
├── retry_count: INT DEFAULT 0
└── created_at: TIMESTAMPTZ DEFAULT NOW()
   INDEX (status, scheduled_at) WHERE status = 'pending'
```

### FR-003: Daily Summary Generation

The system SHALL generate daily summaries for each active user.

**Acceptance Criteria**:
- AC-003.1: Summary job runs daily at 06:00 UTC
- AC-003.2: Aggregates conversations from previous day
- AC-003.3: Calculates score delta (end - start)
- AC-003.4: Generates Nikita's in-character recap via LLM
- AC-003.5: Stores in daily_summaries table

### FR-004: Edge Function Execution

The system SHALL use Supabase Edge Functions for async processing.

**Acceptance Criteria**:
- AC-004.1: Edge Functions deployed via Supabase CLI
- AC-004.2: Functions have 10-second timeout
- AC-004.3: Environment variables injected from Supabase secrets
- AC-004.4: Logs captured in Supabase dashboard

**Edge Functions Required**:
| Function | Trigger | Purpose |
|----------|---------|---------|
| deliver-responses | pg_cron (*/30 * * * * *) | Poll and send pending messages |
| generate-summaries | pg_cron (0 6 * * *) | Create daily summaries |
| cleanup-stale | pg_cron (0 0 * * *) | Archive old pending messages |

### FR-005: Job Monitoring

The system SHALL track background job execution health.

**Acceptance Criteria**:
- AC-005.1: Job runs logged with duration and status
- AC-005.2: Failed jobs trigger alerts (via webhook)
- AC-005.3: Job history retained for 30 days
- AC-005.4: Dashboard shows recent job status

**Job History Schema**:
```sql
job_history
├── id: UUID (PK)
├── job_name: VARCHAR(50) NOT NULL
├── started_at: TIMESTAMPTZ NOT NULL
├── completed_at: TIMESTAMPTZ
├── status: VARCHAR(20) DEFAULT 'running'
│   CHECK (status IN ('running', 'success', 'failed'))
├── items_processed: INT DEFAULT 0
├── error_message: TEXT
└── INDEX (job_name, started_at DESC)
```

### FR-006: Task Idempotency

The system SHALL ensure tasks can be safely retried.

**Acceptance Criteria**:
- AC-006.1: Decay applies once per day per user (date-keyed)
- AC-006.2: Message delivery idempotent (check delivered_at)
- AC-006.3: Summary generation checks for existing entry
- AC-006.4: Concurrent execution prevented via advisory locks

---

## Non-Functional Requirements

### NFR-001: Performance

- Decay job processes 10,000 users in <60 seconds
- Message delivery latency <5 seconds from scheduled_at
- Summary generation <30 seconds per user

### NFR-002: Reliability

- Jobs survive Edge Function cold starts
- Partial failures don't block remaining items
- Dead letter queue for permanently failed tasks

### NFR-003: Observability

- Job execution logged with timing
- Failure rates tracked per job type
- Pending message queue depth monitored

---

## pg_cron Configuration

**Reference**: `memory/integrations.md#pg_cron`

```sql
-- Enable pg_cron extension
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Daily decay at midnight UTC
SELECT cron.schedule(
    'apply-daily-decay',
    '0 0 * * *',
    $$SELECT apply_daily_decay()$$
);

-- Deliver pending messages every 30 seconds
SELECT cron.schedule(
    'deliver-responses',
    '*/30 * * * * *',
    $$SELECT net.http_post(
        url := 'https://<project>.supabase.co/functions/v1/deliver-responses',
        headers := '{"Authorization": "Bearer <service_key>"}'::jsonb
    )$$
);

-- Daily summaries at 6 AM UTC
SELECT cron.schedule(
    'generate-daily-summaries',
    '0 6 * * *',
    $$SELECT net.http_post(
        url := 'https://<project>.supabase.co/functions/v1/generate-summaries',
        headers := '{"Authorization": "Bearer <service_key>"}'::jsonb
    )$$
);
```

---

## User Stories

### US-001: Decay Application

**As a** game designer
**I want** decay applied consistently overnight
**So that** players who ignore Nikita see score drop

**Acceptance Criteria**:
- [ ] AC-US001.1: Decay runs regardless of player activity
- [ ] AC-US001.2: Grace period respected per chapter
- [ ] AC-US001.3: Score never goes negative
- [ ] AC-US001.4: Game over notification sent when 0

### US-002: Delayed Response Delivery

**As a** player
**I want** Nikita's messages to arrive at realistic times
**So that** the experience feels authentic

**Acceptance Criteria**:
- [ ] AC-US002.1: Response arrives within 5s of scheduled_at
- [ ] AC-US002.2: Failed deliveries retry automatically
- [ ] AC-US002.3: Player sees message even if app was closed

### US-003: Daily Recap

**As a** player
**I want** to see Nikita's daily summary
**So that** I understand how our relationship evolved

**Acceptance Criteria**:
- [ ] AC-US003.1: Summary available by 7 AM player timezone
- [ ] AC-US003.2: Includes score change and key events
- [ ] AC-US003.3: Written in Nikita's voice

---

## Dependencies

### Upstream (this spec depends on)
- 009-database-infrastructure (pending_responses, job_history tables)
- 010-api-infrastructure (Edge Function invocation)
- Supabase pg_cron extension enabled
- Supabase Edge Functions enabled

### Downstream (depends on this spec)
- 002-telegram-integration (delayed message delivery)
- 005-decay-system (daily decay processing)
- 008-player-portal (daily summary display)

---

## Implementation Notes

**Pattern Reference**: `memory/integrations.md#edge-functions`

```typescript
// supabase/functions/deliver-responses/index.ts
import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from "https://esm.sh/@supabase/supabase-js@2"

serve(async (req) => {
  const supabase = createClient(
    Deno.env.get("SUPABASE_URL")!,
    Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
  )

  // Get pending messages due for delivery
  const { data: pending } = await supabase
    .from("pending_responses")
    .select("*")
    .eq("status", "pending")
    .lte("scheduled_at", new Date().toISOString())
    .limit(50)

  for (const msg of pending ?? []) {
    try {
      await sendTelegramMessage(msg.telegram_chat_id, msg.response_text)
      await supabase
        .from("pending_responses")
        .update({ status: "delivered", delivered_at: new Date() })
        .eq("id", msg.id)
    } catch (error) {
      await supabase
        .from("pending_responses")
        .update({ retry_count: msg.retry_count + 1 })
        .eq("id", msg.id)
    }
  }

  return new Response(JSON.stringify({ processed: pending?.length ?? 0 }))
})
```

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| pg_cron job overlap | Medium | Advisory locks, job_history check |
| Edge Function timeout | High | Batch processing, 50 item limit |
| Telegram rate limits | Medium | Exponential backoff, queue throttling |
| Missing decay (job failure) | High | Catch-up logic, manual trigger |
| Cold start latency | Low | Keep-alive pings, warm instances |
