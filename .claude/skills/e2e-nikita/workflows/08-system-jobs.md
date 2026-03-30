# Phase 8: System Jobs & Background Tasks (E10, 39 scenarios)

## Prerequisites
USER_ID established. Cloud Run healthy. TASK_AUTH_SECRET available in environment.
These are non-player-facing background endpoints triggered by pg_cron in production.

## Scenarios Covered
**Background Jobs (E10)**: S-10.1.1 through S-10.10

## Auth Pattern
All task endpoints use Bearer token authentication:
```bash
curl -s -X POST https://nikita-api-1040094048579.us-central1.run.app/tasks/{name} \
  -H "Authorization: Bearer $TASK_AUTH_SECRET"
```

---

## Step 1: Decay Job (S-10.2.1) [P0]

### 1a: Setup — Active User Past Grace Period
```sql
UPDATE users SET game_status='active', last_interaction_at=NOW() - INTERVAL '12 hours',
  grace_period_expires_at=NOW() - INTERVAL '4 hours'
WHERE id = '<USER_ID>';
SELECT relationship_score FROM users WHERE id = '<USER_ID>';
-- Record: score_before = {value}
```

### 1b: Execute Decay
```bash
curl -s -X POST https://nikita-api-1040094048579.us-central1.run.app/tasks/decay \
  -H "Authorization: Bearer $TASK_AUTH_SECRET"
```
**Assert**: 200 response.

### 1c: Verify Decay Applied
```sql
SELECT relationship_score FROM users WHERE id = '<USER_ID>';
-- Assert: score < score_before (decay applied)
SELECT status, items_processed FROM job_executions
WHERE job_name = 'decay' ORDER BY started_at DESC LIMIT 1;
-- Assert: status='completed'
```

### 1d: Verify Skip Logic — boss_fight, game_over, won Users NOT Decayed
```sql
UPDATE users SET game_status='boss_fight' WHERE id = '<USER_ID>';
SELECT relationship_score FROM users WHERE id = '<USER_ID>';
-- Record: score_before_boss = {value}
```
Run decay again. Then:
```sql
SELECT relationship_score FROM users WHERE id = '<USER_ID>';
-- Assert: score_before_boss == current score (no decay during boss_fight)
```
Repeat for `game_status='game_over'` and `game_status='won'`.

---

## Step 2: Process Conversations (S-10.1.1) [P0]

```bash
curl -s -X POST https://nikita-api-1040094048579.us-central1.run.app/tasks/process-conversations \
  -H "Authorization: Bearer $TASK_AUTH_SECRET"
```
**Assert**: 200 response.
```sql
SELECT id, job_name, status, started_at, completed_at, items_processed
FROM job_executions WHERE job_name = 'process-conversations'
ORDER BY started_at DESC LIMIT 1;
-- Assert: status='completed', items_processed >= 0
```

Verify conversations processed:
```sql
SELECT id, status, score_delta FROM conversations
WHERE user_id = '<USER_ID>' AND status = 'processed'
ORDER BY created_at DESC LIMIT 3;
-- Assert: recent conversations have status='processed'
```

---

## Step 3: Deliver Touchpoints (S-10.4.1) [P1]

```bash
curl -s -X POST https://nikita-api-1040094048579.us-central1.run.app/tasks/touchpoints \
  -H "Authorization: Bearer $TASK_AUTH_SECRET"
```
**Assert**: 200 response, no 500 error.

---

## Step 4: Summary (S-10.3.1) [P1]

```bash
curl -s -X POST https://nikita-api-1040094048579.us-central1.run.app/tasks/summary \
  -H "Authorization: Bearer $TASK_AUTH_SECRET"
```
**Assert**: 200 response.

Verify summary created:
```sql
SELECT id, created_at FROM daily_summaries
WHERE user_id = '<USER_ID>'
ORDER BY created_at DESC LIMIT 1;
-- Assert: row exists (if user had recent activity)
```

---

## Step 5: Boss Timeout (S-10.5.1) [P0]

### 5a: Setup — Stale Boss Fight (>24h)
```sql
UPDATE users SET game_status='boss_fight',
  boss_fight_started_at=NOW() - INTERVAL '25 hours',
  boss_attempts=1
WHERE id = '<USER_ID>';
```

### 5b: Execute Boss Timeout
```bash
curl -s -X POST https://nikita-api-1040094048579.us-central1.run.app/tasks/boss-timeout \
  -H "Authorization: Bearer $TASK_AUTH_SECRET"
```
Wait 10s.

### 5c: Verify Auto-Fail
```sql
SELECT game_status, boss_attempts FROM users WHERE id = '<USER_ID>';
-- Assert: game_status='active' (returned from boss), boss_attempts=2 (incremented)
-- OR if boss_attempts was 2 before: game_status='game_over', boss_attempts=3
```

---

## Step 6: Psyche Batch (S-10.6.1) [P1]

```bash
curl -s -X POST https://nikita-api-1040094048579.us-central1.run.app/tasks/psyche-batch \
  -H "Authorization: Bearer $TASK_AUTH_SECRET"
```
**Assert**: 200 response, no crash.

Verify psyche state updated:
```sql
SELECT updated_at FROM psyche_state
WHERE user_id = '<USER_ID>'
ORDER BY updated_at DESC LIMIT 1;
-- Assert: updated_at is recent (if user has enough conversation history)
```

---

## Step 7: Auth — Invalid Secret Rejected (S-10.7.1) [P0]

```bash
curl -s -o /dev/null -w "%{http_code}" -X POST \
  https://nikita-api-1040094048579.us-central1.run.app/tasks/decay \
  -H "Authorization: Bearer wrong-token-123"
```
**Assert**: 401 or 403 (not 200 or 500).

```bash
curl -s -o /dev/null -w "%{http_code}" -X POST \
  https://nikita-api-1040094048579.us-central1.run.app/tasks/decay
```
**Assert**: 401 or 403 (no auth header at all).

---

## Pass/Fail Criteria

| Scenario | Priority | Pass Condition |
|----------|----------|----------------|
| S-10.1.1: process-conversations | P0 | 200 response, job completed, conversations processed |
| S-10.2.1: decay task | P0 | 200 response, active users decayed, skip logic works |
| S-10.3.1: summary task | P1 | 200 response, daily_summaries row created |
| S-10.4.1: touchpoints task | P1 | 200 response, no crash |
| S-10.5.1: boss-timeout auto-fail | P0 | Boss auto-failed after 24h+, attempts incremented |
| S-10.6.1: psyche-batch | P1 | 200 response, psyche_state updated |
| S-10.7.1: auth rejects bad token | P0 | 401 or 403 for invalid/missing token |

Log all findings via:
`[TIMESTAMP] E2E_NIKITA: Phase 8 JOBS — [ID] — PASS/FAIL — [note]`
