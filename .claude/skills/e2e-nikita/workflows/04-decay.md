# Phase 04: Decay System (E04, 18 scenarios)

## Prerequisites
USER_ID established. User active (any chapter). Time manipulation via SQL.
See @workflows/time-simulation.md for full SQL patterns.

## Step 1: Read Baseline State
```sql
SELECT id, chapter, relationship_score, last_message_at, grace_period_expires_at
FROM users WHERE id = '<USER_ID>';
SELECT intimacy, passion, trust, secureness FROM user_metrics WHERE user_id = '<USER_ID>';
```

## Step 2: Simulate Grace Period Expiry (S-4.1.1)
Move `last_message_at` back past the grace period for current chapter.
Ch1 grace=8h, Ch2=16h, Ch3=24h, Ch4=48h, Ch5=72h.

```sql
-- For Ch1: push last_message_at back 9 hours (past 8h grace)
UPDATE users SET last_message_at = NOW() - INTERVAL '9 hours'
WHERE id = '<USER_ID>';
-- Also update grace_period_expires_at if stored separately
UPDATE users SET grace_period_expires_at = NOW() - INTERVAL '1 hour'
WHERE id = '<USER_ID>';
```

## Step 3: Trigger Decay Manually
```bash
curl -X POST https://nikita-api-1040094048579.us-central1.run.app/tasks/decay \
  -H "Authorization: Bearer $TASK_AUTH_SECRET" \
  -H "Content-Type: application/json"
```
Wait 15s for Cloud Run to process (may cold start).

## Step 4: Verify Decay Applied (S-4.1.2)
```sql
SELECT relationship_score, updated_at FROM users WHERE id = '<USER_ID>';
-- Assert: score decreased by ~0.8% (Ch1) from prior reading

SELECT composite_before, composite_after, decay_amount, recorded_at
FROM score_history WHERE user_id = '<USER_ID>'
ORDER BY recorded_at DESC LIMIT 3;
-- Assert: newest row has decay_amount > 0
```

## Step 5: Test Grace Period Respected (S-4.1.3)
Reset to fresh message time (within grace period):
```sql
UPDATE users SET last_message_at = NOW() - INTERVAL '1 hour'
WHERE id = '<USER_ID>';
UPDATE users SET grace_period_expires_at = NOW() + INTERVAL '7 hours'
WHERE id = '<USER_ID>';
```
Trigger decay again:
```bash
curl -X POST https://nikita-api-1040094048579.us-central1.run.app/tasks/decay \
  -H "Authorization: Bearer $TASK_AUTH_SECRET"
```
```sql
SELECT relationship_score FROM users WHERE id = '<USER_ID>';
-- Assert: score unchanged — grace period protected user
```

## Step 6: Test Decay-to-Zero → game_over (S-4.2.3)
```sql
-- Set score just above 0
UPDATE users SET relationship_score = 0.5 WHERE id = '<USER_ID>';
UPDATE user_metrics SET intimacy=0.5, passion=0.5, trust=0.5, secureness=0.5
WHERE user_id = '<USER_ID>';
UPDATE users SET last_message_at = NOW() - INTERVAL '9 hours',
  grace_period_expires_at = NOW() - INTERVAL '1 hour' WHERE id = '<USER_ID>';
```
Trigger decay:
```bash
curl -X POST https://nikita-api-1040094048579.us-central1.run.app/tasks/decay \
  -H "Authorization: Bearer $TASK_AUTH_SECRET"
```
```sql
SELECT game_status, relationship_score FROM users WHERE id = '<USER_ID>';
-- Assert: game_status = 'game_over', relationship_score = 0
```

## Step 7: Multi-Chapter Decay Verification [method: S+A]

Test Ch1 and Ch5 in addition to the Ch2 test above.

### Ch1 (0.8%/hr, 8h grace):
```sql
UPDATE users SET chapter=1, relationship_score=60.00,
  last_message_at = NOW() - INTERVAL '9 hours' WHERE id = '<USER_ID>';
DELETE FROM job_executions WHERE job_name='decay' AND started_at > NOW() - INTERVAL '1 hour';
```
Trigger decay. Verify:
```sql
SELECT relationship_score FROM users WHERE id = '<USER_ID>';
-- Assert: ~59.52 (60 * 0.992 = 59.52, 1hr overdue * 0.8%)
```

### Ch5 (0.2%/hr, 72h grace):
```sql
UPDATE users SET chapter=5, relationship_score=75.00,
  last_message_at = NOW() - INTERVAL '73 hours' WHERE id = '<USER_ID>';
DELETE FROM job_executions WHERE job_name='decay' AND started_at > NOW() - INTERVAL '1 hour';
```
Trigger decay. Verify:
```sql
SELECT relationship_score FROM users WHERE id = '<USER_ID>';
-- Assert: ~74.85 (75 * 0.998 = 74.85, 1hr overdue * 0.2%)
```

## Pass/Fail Criteria

| Scenario | Priority | Pass Condition |
|----------|----------|----------------|
| S-4.1.1: Decay applies after grace | P0 | score decreased after grace expiry [S+A] |
| S-4.1.2: Decay rate correct (Ch1 = 0.8%/hr) | P1 | actual decay within ±0.1% [S+A] |
| S-4.1.3: Grace period prevents decay | P0 | score unchanged when within grace [S+A] |
| S-4.2.3: Decay-to-zero → game_over | P1 | game_status=game_over at score=0 [S+A] |
| S-4.2.1: Decay per-chapter rates | P1 | different rates per chapter [S+A] |
| S-4.2.1a: Ch1 decay rate correct | P1 | ~0.8%/hr within +-0.1% [S+A] |
| S-4.2.1b: Ch5 decay rate correct | P1 | ~0.2%/hr within +-0.1% [S+A] |
