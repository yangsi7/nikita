# SQL Queries Reference — E2E Nikita

All queries use `<USER_ID>` as placeholder. Replace with actual UUID after Phase 01.
Run via: `mcp__supabase__execute_sql(project_id="oegqvulrqeudrdkfxoqd", query="...")`

## Account Management

### Wipe test account (Phase 00)
```sql
DELETE FROM users WHERE email = 'simon.yang.ch@gmail.com';
DELETE FROM pending_registrations WHERE telegram_id = 746410893;
```

### Verify clean wipe
```sql
SELECT COUNT(*) FROM users WHERE email = 'simon.yang.ch@gmail.com';
SELECT COUNT(*) FROM pending_registrations WHERE telegram_id = 746410893;
-- Assert: both = 0
```

### Get USER_ID after onboarding
```sql
SELECT id, email, game_status, chapter, relationship_score
FROM users WHERE email = 'simon.yang.ch@gmail.com';
```

## User State Verification

### Full user state snapshot
```sql
SELECT u.id, u.email, u.chapter, u.game_status, u.relationship_score,
       u.last_message_at, u.grace_period_expires_at, u.boss_attempts,
       u.cool_down_until, u.boss_fight_started_at,
       um.intimacy, um.passion, um.trust, um.secureness
FROM users u
JOIN user_metrics um ON um.user_id = u.id
WHERE u.id = '<USER_ID>';
```

### Composite score calculation (verify formula)
```sql
SELECT
  intimacy * 0.30 + passion * 0.25 + trust * 0.25 + secureness * 0.20 AS composite,
  (intimacy * 0.30 + passion * 0.25 + trust * 0.25 + secureness * 0.20) / 100.0 AS pct
FROM user_metrics WHERE user_id = '<USER_ID>';
```

### Onboarding profile verification
```sql
SELECT u.city, up.scenario_name, up.backstory_summary
FROM users u
LEFT JOIN user_profiles up ON up.user_id = u.id
WHERE u.id = '<USER_ID>';
-- Assert: city='Zurich', scenario_name present, backstory_summary not null
```

## Score History

### Recent score history (last 10 entries)
```sql
SELECT score, chapter, event_type,
       event_details->'deltas'->>'intimacy' as intimacy_delta,
       event_details->'deltas'->>'passion' as passion_delta,
       event_details->'deltas'->>'trust' as trust_delta,
       event_details->'deltas'->>'secureness' as secureness_delta,
       event_details->>'multiplier' as engagement_multiplier,
       created_at
FROM score_history
WHERE user_id = '<USER_ID>'
ORDER BY created_at DESC LIMIT 10;
```

### Verify scoring occurred after message
```sql
SELECT COUNT(*) FROM score_history
WHERE user_id = '<USER_ID>'
AND created_at > NOW() - INTERVAL '5 minutes';
-- Assert: >= 1
```

### Race condition check (gap < 500ms)
```sql
SELECT created_at,
       created_at - LAG(created_at) OVER (ORDER BY created_at) AS gap
FROM score_history WHERE user_id = '<USER_ID>'
ORDER BY created_at DESC LIMIT 10;
-- Watch for gap < 500ms (race risk indicator)
```

## Engagement State

### Current engagement state
```sql
SELECT state, messages_last_hour, messages_last_day, last_message_at
FROM engagement_state WHERE user_id = '<USER_ID>';
```

### Force distant state
```sql
UPDATE engagement_state SET
  last_message_at = NOW() - INTERVAL '48 hours',
  messages_last_hour = 0,
  messages_last_day = 1
WHERE user_id = '<USER_ID>';
```

### Force clingy state
```sql
UPDATE engagement_state SET
  last_message_at = NOW() - INTERVAL '5 minutes',
  messages_last_hour = 8,
  messages_last_day = 30
WHERE user_id = '<USER_ID>';
```

### Reset to in_zone
```sql
UPDATE engagement_state SET
  last_message_at = NOW() - INTERVAL '30 minutes',
  messages_last_hour = 2,
  messages_last_day = 6,
  state = 'in_zone'
WHERE user_id = '<USER_ID>';
```

## Decay & Time Simulation

### Force decay condition (chapter-specific)
```sql
-- Ch1: decay after 9h (grace=8h)
UPDATE users SET
  last_message_at = NOW() - INTERVAL '9 hours',
  grace_period_expires_at = NOW() - INTERVAL '1 hour'
WHERE id = '<USER_ID>';

-- Ch2: decay after 17h (grace=16h)
UPDATE users SET
  last_message_at = NOW() - INTERVAL '17 hours',
  grace_period_expires_at = NOW() - INTERVAL '1 hour'
WHERE id = '<USER_ID>';
```

### Grace period protection (should NOT decay)
```sql
UPDATE users SET
  last_message_at = NOW() - INTERVAL '2 hours',
  grace_period_expires_at = NOW() + INTERVAL '6 hours'
WHERE id = '<USER_ID>';
```

### Force decay to zero (game_over trigger)
```sql
UPDATE users SET relationship_score = 0.3,
  last_message_at = NOW() - INTERVAL '10 hours',
  grace_period_expires_at = NOW() - INTERVAL '2 hours'
WHERE id = '<USER_ID>';
UPDATE user_metrics SET intimacy=0.3, passion=0.3, trust=0.3, secureness=0.3
WHERE user_id = '<USER_ID>';
```

## Boss Encounters

### Force boss threshold (generic score bump)
```sql
UPDATE users SET relationship_score = 56 WHERE id = '<USER_ID>';
UPDATE user_metrics SET intimacy=60, passion=55, trust=55, secureness=56
WHERE user_id = '<USER_ID>';
```

### Force boss threshold per chapter
```sql
-- Ch1 boss (55%): threshold 55
UPDATE users SET chapter=1, relationship_score=56 WHERE id = '<USER_ID>';
UPDATE user_metrics SET intimacy=60, passion=55, trust=55, secureness=56 WHERE user_id='<USER_ID>';

-- Ch2 boss (60%):
UPDATE users SET chapter=2, relationship_score=61 WHERE id = '<USER_ID>';
UPDATE user_metrics SET intimacy=65, passion=60, trust=60, secureness=60 WHERE user_id='<USER_ID>';

-- Ch3 boss (65%):
UPDATE users SET chapter=3, relationship_score=66 WHERE id = '<USER_ID>';
UPDATE user_metrics SET intimacy=70, passion=65, trust=65, secureness=65 WHERE user_id='<USER_ID>';

-- Ch4 boss (70%):
UPDATE users SET chapter=4, relationship_score=71 WHERE id = '<USER_ID>';
UPDATE user_metrics SET intimacy=75, passion=70, trust=70, secureness=70 WHERE user_id='<USER_ID>';

-- Ch5 boss (75%):
UPDATE users SET chapter=5, game_status='active', boss_attempts=0 WHERE id = '<USER_ID>';
UPDATE user_metrics SET intimacy=78, passion=77, trust=76, secureness=76 WHERE user_id='<USER_ID>';
UPDATE users SET relationship_score=76.85 WHERE id = '<USER_ID>';
```

### Verify boss triggered
```sql
SELECT game_status, boss_fight_started_at, boss_attempts
FROM users WHERE id = '<USER_ID>';
-- Assert: game_status='boss_fight', boss_fight_started_at IS NOT NULL
```

### Force boss fail (increment attempt)
```sql
UPDATE users SET boss_attempts = boss_attempts + 1 WHERE id = '<USER_ID>';
```

### Force game_over
```sql
UPDATE users SET game_status='game_over', boss_attempts=3,
  boss_fight_started_at=NULL WHERE id = '<USER_ID>';
```

### Force won state
```sql
UPDATE users SET game_status='won', chapter=5 WHERE id = '<USER_ID>';
```

### Boss timeout simulation
```sql
UPDATE users SET game_status='boss_fight',
  boss_fight_started_at = NOW() - INTERVAL '25 hours'
WHERE id = '<USER_ID>';
```

## Memory & Conversations

### Recent memory facts
```sql
SELECT content, created_at FROM memory_facts
WHERE user_id = '<USER_ID>'
ORDER BY created_at DESC LIMIT 10;
-- Assert: rows exist (pipeline ran)
```

### Duplicate memory check (concurrent pipeline indicator)
```sql
SELECT COUNT(*) FROM memory_facts
WHERE user_id = '<USER_ID>'
GROUP BY content HAVING COUNT(*) > 1;
-- Assert: 0 rows
```

### Conversation history
```sql
SELECT type, created_at, id FROM conversations
WHERE user_id = '<USER_ID>'
ORDER BY created_at DESC LIMIT 10;
```

### Verify both text + voice conversation types
```sql
SELECT type, COUNT(*) FROM conversations
WHERE user_id = '<USER_ID>'
GROUP BY type;
-- Assert: rows for 'text' and 'voice' both present
```

## Vice Preferences

### Current vice preferences
```sql
SELECT vice_category, intensity_level, detection_count, updated_at
FROM user_vice_preferences
WHERE user_id = '<USER_ID>'
ORDER BY intensity_level DESC;
```

### Verify specific vice detected
```sql
SELECT vice_category, intensity_level
FROM user_vice_preferences
WHERE user_id = '<USER_ID>'
AND vice_category = 'risk_taking';
-- Assert: row exists AND intensity_level >= 1
```

## Background Jobs

### Recent job executions
```sql
SELECT job_name, status, started_at, completed_at,
       EXTRACT(EPOCH FROM (completed_at - started_at)) AS duration_s
FROM job_executions
ORDER BY started_at DESC LIMIT 20;
```

### Verify job completed successfully
```sql
SELECT status FROM job_executions
WHERE job_name = 'process-conversations'
ORDER BY started_at DESC LIMIT 1;
-- Assert: status = 'completed'
```

### Concurrent pipeline detection
```sql
SELECT COUNT(*) FROM job_executions
WHERE job_name = 'process-conversations' AND status = 'in_progress';
-- Assert: 0 or 1 (never 2+)
```

### Pipeline stage breakdown
```sql
SELECT stage_name, COUNT(*) as runs,
       AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) AS avg_s
FROM pipeline_executions
WHERE user_id = '<USER_ID>'
GROUP BY stage_name ORDER BY stage_name;
```

## Security & RLS

### Verify RLS enabled on sensitive tables
```sql
SELECT tablename, rowsecurity FROM pg_tables
WHERE tablename IN ('users', 'user_metrics', 'conversations')
ORDER BY tablename;
-- Assert: rowsecurity = TRUE for all 3
```

### OTP brute force check
```sql
SELECT otp_attempts FROM pending_registrations
WHERE telegram_id = 746410893;
-- Assert: otp_attempts = N (matches wrong attempts sent)
```

### Pending registrations count
```sql
SELECT COUNT(*) FROM pending_registrations WHERE telegram_id = 746410893;
-- Assert: 1 (upsert handled) or ≤3 (benign) for rapid /start test
```

## Voice / Cross-Platform

### Score history with platform
```sql
SELECT source_platform, composite_before, composite_after, recorded_at
FROM score_history WHERE user_id = '<USER_ID>'
ORDER BY recorded_at DESC LIMIT 3;
-- Assert: row with source_platform='voice' present after voice webhook
```
