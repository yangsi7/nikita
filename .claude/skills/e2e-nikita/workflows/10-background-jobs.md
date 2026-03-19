# Phase 10: Background Jobs & Pipeline (E10, 39 scenarios)

## Prerequisites
USER_ID established. Cloud Run healthy. TASK_AUTH_SECRET available in environment.

## Task Endpoints to Test
All use: `POST <endpoint> -H "Authorization: Bearer $TASK_AUTH_SECRET"`

## Step 1: Process-Conversations Pipeline (S-10.1.1)
```bash
curl -s -X POST https://nikita-api-1040094048579.us-central1.run.app/tasks/process-conversations \
  -H "Authorization: Bearer $TASK_AUTH_SECRET"
```
Assert: 200 response. Then:
```sql
SELECT id, job_name, status, started_at, completed_at, items_processed
FROM job_executions WHERE job_name = 'process-conversations'
ORDER BY started_at DESC LIMIT 1;
-- Assert: status='completed', items_processed >= 0
```

## Step 2: Decay Task (S-10.2.1)
```bash
curl -s -X POST https://nikita-api-1040094048579.us-central1.run.app/tasks/decay \
  -H "Authorization: Bearer $TASK_AUTH_SECRET"
```
Assert: 200 response.
```sql
SELECT status, items_processed FROM job_executions
WHERE job_name = 'decay' ORDER BY started_at DESC LIMIT 1;
-- Assert: status='completed'
```

## Step 3: Summary Task (S-10.3.1)
```bash
curl -s -X POST https://nikita-api-1040094048579.us-central1.run.app/tasks/summary \
  -H "Authorization: Bearer $TASK_AUTH_SECRET"
```
Assert: 200 response, no 500 error.

## Step 4: Touchpoints Task (S-10.4.1)
```bash
curl -s -X POST https://nikita-api-1040094048579.us-central1.run.app/tasks/touchpoints \
  -H "Authorization: Bearer $TASK_AUTH_SECRET"
```
Assert: 200 response.

## Step 5: Boss-Timeout Task (S-10.5.1 — Gap G06)
Set a user to boss_fight with old started_at to trigger timeout:
```sql
UPDATE users SET game_status='boss_fight',
  boss_fight_started_at = NOW() - INTERVAL '25 hours'
WHERE id = '<USER_ID>';
```
```bash
curl -s -X POST https://nikita-api-1040094048579.us-central1.run.app/tasks/boss-timeout \
  -H "Authorization: Bearer $TASK_AUTH_SECRET"
```
Wait 10s.
```sql
SELECT game_status, boss_attempts FROM users WHERE id = '<USER_ID>';
-- Assert: game_status='active' or boss_attempts incremented (boss auto-failed)
```
<step_result status="pass|fail">boss timeout: auto-fail triggered on 25h boss fight</step_result>

## Step 6: Psyche-Batch Task (S-10.6.1)
```bash
curl -s -X POST https://nikita-api-1040094048579.us-central1.run.app/tasks/psyche-batch \
  -H "Authorization: Bearer $TASK_AUTH_SECRET"
```
Assert: 200 response, no crash.

## Step 7: Auth Verification — Invalid Token Rejected (S-10.7.1)
```bash
curl -s -X POST https://nikita-api-1040094048579.us-central1.run.app/tasks/decay \
  -H "Authorization: Bearer wrong-token-123"
```
Assert: 401 or 403 response (not 200 or 500).

## Step 8: Pipeline Stage Verification (S-10.8.1)
After running process-conversations with active conversations present:
```sql
SELECT stage_name, status, duration_ms FROM pipeline_executions
WHERE user_id = '<USER_ID>'
ORDER BY started_at DESC LIMIT 10;
-- Assert: multiple stages present (extraction, memory_update, etc.)
-- Assert: no stage with status='failed' (unless expected)
```

## Pass/Fail Criteria

| Scenario | Priority | Pass Condition |
|----------|----------|----------------|
| S-10.1.1: process-conversations | P0 | 200 response, job_executions row completed |
| S-10.2.1: decay task | P0 | 200 response, status=completed |
| S-10.3.1: summary task | P1 | 200 response, no crash |
| S-10.4.1: touchpoints task | P1 | 200 response |
| S-10.5.1: boss-timeout auto-fail | P0 | boss auto-failed after 24h+ |
| S-10.6.1: psyche-batch | P1 | 200 response |
| S-10.7.1: auth rejects bad token | P0 | 401 or 403 response |
| S-10.8.1: pipeline stages created | P1 | multiple stages in pipeline_executions |
