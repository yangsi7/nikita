# Time Simulation — SQL Reference

## Purpose
Manipulate timestamps to simulate time passage for decay, grace period, and engagement tests.
Never use sleep() — always move timestamps backward via SQL.

## Core Pattern: Push Time Back
```sql
-- Move last_message_at back N hours (simulates N hours of silence)
UPDATE users SET
  last_message_at = NOW() - INTERVAL 'N hours',
  grace_period_expires_at = NOW() - INTERVAL 'M hours'  -- M > N for expired grace
WHERE id = '<USER_ID>';
```

## Decay Simulation by Chapter

### Ch1: Decay after 9h (grace=8h)
```sql
UPDATE users SET
  last_message_at = NOW() - INTERVAL '9 hours',
  grace_period_expires_at = NOW() - INTERVAL '1 hour'
WHERE id = '<USER_ID>';
```

### Ch2: Decay after 17h (grace=16h)
```sql
UPDATE users SET
  last_message_at = NOW() - INTERVAL '17 hours',
  grace_period_expires_at = NOW() - INTERVAL '1 hour'
WHERE id = '<USER_ID>';
```

### Ch3: Decay after 25h (grace=24h)
```sql
UPDATE users SET
  last_message_at = NOW() - INTERVAL '25 hours',
  grace_period_expires_at = NOW() - INTERVAL '1 hour'
WHERE id = '<USER_ID>';
```

### Ch4: Decay after 49h (grace=48h)
```sql
UPDATE users SET
  last_message_at = NOW() - INTERVAL '49 hours',
  grace_period_expires_at = NOW() - INTERVAL '1 hour'
WHERE id = '<USER_ID>';
```

### Ch5: Decay after 73h (grace=72h)
```sql
UPDATE users SET
  last_message_at = NOW() - INTERVAL '73 hours',
  grace_period_expires_at = NOW() - INTERVAL '1 hour'
WHERE id = '<USER_ID>';
```

## Grace Period Test (should NOT decay)
```sql
-- Place within grace period — decay should be skipped
UPDATE users SET
  last_message_at = NOW() - INTERVAL '2 hours',
  grace_period_expires_at = NOW() + INTERVAL '6 hours'
WHERE id = '<USER_ID>';
```

## Decay to Zero (game_over trigger)
```sql
UPDATE users SET relationship_score = 0.3,
  last_message_at = NOW() - INTERVAL '10 hours',
  grace_period_expires_at = NOW() - INTERVAL '2 hours'
WHERE id = '<USER_ID>';
UPDATE user_metrics SET intimacy=0.3, passion=0.3, trust=0.3, secureness=0.3
WHERE user_id = '<USER_ID>';
```

## Boss Timeout Simulation (boss_timeout task)
```sql
UPDATE users SET game_status='boss_fight',
  boss_fight_started_at = NOW() - INTERVAL '25 hours'
WHERE id = '<USER_ID>';
```

## Engagement State Simulation
```sql
-- Simulate distant (low frequency)
UPDATE engagement_state SET
  last_message_at = NOW() - INTERVAL '48 hours',
  messages_last_hour = 0,
  messages_last_day = 1
WHERE user_id = '<USER_ID>';

-- Simulate clingy (high frequency)
UPDATE engagement_state SET
  last_message_at = NOW() - INTERVAL '5 minutes',
  messages_last_hour = 8,
  messages_last_day = 30
WHERE user_id = '<USER_ID>';

-- Reset to normal
UPDATE engagement_state SET
  last_message_at = NOW() - INTERVAL '30 minutes',
  messages_last_hour = 2,
  messages_last_day = 6,
  state = 'in_zone'
WHERE user_id = '<USER_ID>';
```
