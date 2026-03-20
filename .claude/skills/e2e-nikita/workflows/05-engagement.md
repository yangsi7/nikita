# Phase 05: Engagement Model (E05, 22 scenarios)

## Prerequisites
USER_ID established. User active. Engagement state initialized.

## Overview
Test 6 engagement states and verify multipliers affect scoring.
States: calibrating (0.9) | in_zone (1.0) | drifting (0.8) | clingy (0.5) | distant (0.6) | out_of_zone (0.2)

## Step 1: Read Baseline Engagement State
```sql
SELECT state, message_count, last_message_at, messages_last_hour,
       messages_last_day, updated_at
FROM engagement_state WHERE user_id = '<USER_ID>';
```

## Step 2: Test Clingy State (5+ messages/hr → multiplier 0.5)
Send 6 messages in rapid succession (2s gaps — simulating spam):
```
mcp__telegram-mcp__send_message(chat_id="8211370823", text="are you there")
-- repeat 5 more times with 2-3s gaps
```
```sql
SELECT state, messages_last_hour FROM engagement_state WHERE user_id = '<USER_ID>';
-- Assert: state = 'clingy' or approaching threshold
```
Now send one more message and check score delta is reduced:
```sql
SELECT composite_after - composite_before as delta
FROM score_history WHERE user_id = '<USER_ID>'
ORDER BY recorded_at DESC LIMIT 1;
-- Assert: delta is lower than typical (0.5x multiplier effect)
```

## Step 3: Reset to Normal Then Test Distant State
```sql
-- Reset engagement state
UPDATE engagement_state SET state='in_zone', messages_last_hour=2,
  messages_last_day=8, last_message_at=NOW() WHERE user_id = '<USER_ID>';
```
Simulate distant behavior by moving last_message_at far back:
```sql
UPDATE engagement_state SET last_message_at = NOW() - INTERVAL '48 hours',
  messages_last_day=1 WHERE user_id = '<USER_ID>';
```
Send one message and check engagement state updates:
```sql
SELECT state FROM engagement_state WHERE user_id = '<USER_ID>';
-- Assert: state = 'distant' or 'out_of_zone'
```

## Step 4: Verify Multiplier Affects Scoring (Key Scenario)
Compare score deltas between in_zone and clingy states:
```sql
SELECT state, AVG(sh.composite_after - sh.composite_before) as avg_delta
FROM score_history sh
JOIN engagement_state es ON es.user_id = sh.user_id
WHERE sh.user_id = '<USER_ID>'
GROUP BY state
ORDER BY avg_delta DESC;
-- Assert: in_zone avg_delta > clingy avg_delta (1.0 > 0.5 effect)
```

## Step 5: Test Recovery to in_zone
```sql
UPDATE engagement_state SET state='calibrating', messages_last_hour=3,
  messages_last_day=6, last_message_at=NOW() - INTERVAL '30 minutes'
WHERE user_id = '<USER_ID>';
```
Send 2 messages with natural timing:
```sql
SELECT state FROM engagement_state WHERE user_id = '<USER_ID>';
-- Assert: state transitions toward in_zone
```

## Verification Method Note
Clingy state (S-5.1.1) can be triggered functionally [F] by sending 6+ messages in
rapid succession. Distant state (S-5.2.1) requires 48h+ silence which is impractical
in E2E — use SQL time manipulation [S+F]. out_of_zone requires 5+ consecutive distant
days — use SQL setup [S+A]. These are documented inherently-SQL-forced scenarios.

## Pass/Fail Criteria

| Scenario | Priority | Pass Condition |
|----------|----------|----------------|
| S-5.1.1: Clingy state triggered | P0 | state='clingy' after 5+ msg/hr [F] |
| S-5.1.2: Multiplier reduces score delta | P1 | clingy delta < in_zone delta [F] |
| S-5.2.1: Distant state triggered | P1 | state='distant' after low activity [S+F] |
| S-5.3.1: Recovery to in_zone | P1 | state transitions on normal activity [F] |
| S-5.4.1: out_of_zone extreme reduction | P1 | multiplier 0.2 measurable [S+A] |
