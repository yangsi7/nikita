# Phase 13: Gap Scenarios — Adversarial Testing (E13, 50 scenarios)

## Prerequisites
USER_ID established. Understanding of race conditions and security vectors.
These tests probe system robustness — some may confirm known limitations (log as LOW/MEDIUM).

## Category 1: Race Conditions (8 scenarios)

### RC-1: Concurrent Decay + Message Scoring (S-GAP-RC-1) [P0]
```sql
-- Check for SELECT...FOR UPDATE usage in calculator paths
-- Detect by looking at score_history for overlapping timestamps
SELECT recorded_at, composite_before, composite_after,
       LAG(recorded_at) OVER (ORDER BY recorded_at) as prev_at,
       recorded_at - LAG(recorded_at) OVER (ORDER BY recorded_at) as gap
FROM score_history WHERE user_id = '<USER_ID>'
ORDER BY recorded_at DESC LIMIT 10;
-- Watch for gap < 500ms between consecutive score updates (race risk)
```
Detection only — log finding. No fix expected without locking implementation.

### RC-3: Concurrent Pipeline Runs (S-GAP-RC-3) [P0]
```sql
SELECT COUNT(*) FROM job_executions
WHERE job_name = 'process-conversations' AND status = 'in_progress';
-- Assert: 0 or 1 row (never 2+ simultaneously for same user)
SELECT COUNT(*) FROM memory_facts
WHERE user_id = '<USER_ID>'
GROUP BY content HAVING COUNT(*) > 1;
-- Assert: 0 duplicate memory facts (duplication indicates concurrent pipeline)
```

### RC-7: Multiple /start in Rapid Succession (S-GAP-RC-7) [P0]
Wipe account (Phase 00), then:
```
mcp__telegram-mcp__send_message(chat_id="8211370823", text="/start")
mcp__telegram-mcp__send_message(chat_id="8211370823", text="/start")
mcp__telegram-mcp__send_message(chat_id="8211370823", text="/start")
```
Send all 3 within 2 seconds.
```sql
SELECT COUNT(*) FROM pending_registrations WHERE telegram_id = 746410893;
-- Assert: 1 row (upsert handled) OR <=3 rows (benign duplicate OTPs, no crash)
```
Assert: No 500 errors in Cloud Run logs. System handles gracefully.

## Category 2: Security (8 scenarios)

### SEC-1: Webhook Secret Rejected (S-GAP-SEC-1) [P0]
```bash
curl -s -X POST https://nikita-api-1040094048579.us-central1.run.app/api/v1/telegram/webhook \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-Api-Secret-Token: wrong-secret" \
  -d '{"update_id": 999, "message": {"text": "test", "chat": {"id": 8211370823}}}'
```
Assert: 401 or 403 response (not 200).

### SEC-2: Unauthenticated Task Endpoint (S-GAP-SEC-2) [P0]
```bash
curl -s -X POST https://nikita-api-1040094048579.us-central1.run.app/tasks/decay
# No Authorization header
```
Assert: 401 or 403 response.

### SEC-3: RLS — Access Other User's Data (S-GAP-SEC-3) [P0]
```sql
-- Try to SELECT another user's data with test account's auth context
-- In practice: verify RLS is enabled on sensitive tables
SELECT COUNT(*) FROM pg_tables WHERE tablename IN ('users', 'user_metrics', 'conversations')
AND rowsecurity = TRUE;
-- Assert: 3 (all 3 tables have RLS enabled)
```

### SEC-4: OTP Brute Force Protection (S-GAP-SEC-4) [P1]
```
-- Send /start, get OTP, then send 3 wrong codes
mcp__telegram-mcp__send_message(chat_id="8211370823", text="000000")
mcp__telegram-mcp__send_message(chat_id="8211370823", text="111111")
mcp__telegram-mcp__send_message(chat_id="8211370823", text="222222")
```
```sql
SELECT otp_attempts FROM pending_registrations WHERE telegram_id = 746410893;
-- Assert: otp_attempts = 3
```
Assert: After 3rd wrong attempt, bot informs user they're locked out.

## Category 3: Edge Cases (8 scenarios)

### EDGE-1: Empty Message Body (S-GAP-EDGE-1) [P1]
```
mcp__telegram-mcp__send_message(chat_id="8211370823", text=" ")
```
Assert: No 500 error. Bot either ignores or gracefully handles whitespace-only message.

### EDGE-2: Very Long Message (S-GAP-EDGE-2) [P1]
Send a 4000-character message:
```
mcp__telegram-mcp__send_message(chat_id="8211370823", text="<4000 chars of lorem ipsum>")
```
Assert: No crash. Bot responds or truncates gracefully.

### EDGE-3: SQL Injection Attempt (S-GAP-EDGE-3) [P0]
```
mcp__telegram-mcp__send_message(chat_id="8211370823", text="'; DROP TABLE users; --")
```
Assert: No crash. Bot responds normally. Verify users table still exists:
```sql
SELECT COUNT(*) FROM users;
-- Assert: Returns a number (table not dropped)
```

### EDGE-4: Decay While in boss_fight (S-GAP-G08) [P0]
```sql
UPDATE users SET game_status='boss_fight',
  boss_fight_started_at=NOW() - INTERVAL '2 hours' WHERE id = '<USER_ID>';
UPDATE users SET last_message_at=NOW() - INTERVAL '10 hours',
  grace_period_expires_at=NOW() - INTERVAL '2 hours' WHERE id = '<USER_ID>';
UPDATE users SET relationship_score = 0.3 WHERE id = '<USER_ID>';
```
Trigger decay:
```bash
curl -X POST https://nikita-api-1040094048579.us-central1.run.app/tasks/decay \
  -H "Authorization: Bearer $TASK_AUTH_SECRET"
```
```sql
SELECT game_status, relationship_score FROM users WHERE id = '<USER_ID>';
-- Expected: game_status='game_over' (decay-to-zero while in boss_fight)
-- OR game_status='boss_fight' preserved (implementation dependent)
-- Log actual behavior — no crash is the minimum bar
```

## Pass/Fail Criteria

| Scenario | Priority | Pass Condition |
|----------|----------|----------------|
| RC-7: Multiple /start | P0 | No 500 error, system handles gracefully |
| SEC-1: Webhook secret | P0 | 401/403 on wrong secret |
| SEC-2: Unauthenticated tasks | P0 | 401/403 without auth header |
| SEC-3: RLS enabled | P0 | rowsecurity=TRUE on sensitive tables |
| SEC-4: OTP brute force | P1 | otp_attempts tracked, lockout message |
| EDGE-3: SQL injection | P0 | No crash, users table intact |
| EDGE-4: Decay in boss_fight | P0 | No crash (behavior may vary) |

Log all findings via:
`[TIMESTAMP] E2E_NIKITA: Phase 13 GAP — [ID] — PASS/FAIL — [note]`
