# Phase 9: Adversarial Testing — Gaps, Security & Race Conditions (E13, 50 scenarios)

## Prerequisites
USER_ID established. Understanding of race conditions and security vectors.
These tests probe system robustness. Some may confirm known limitations (log as LOW/MEDIUM via `references/classification-system.md`).

## Scenarios Covered
**Gap Scenarios (E13)**: 50 adversarial scenarios across 5 categories

---

## Category 1: Race Conditions (10 scenarios)

### RC-1: Decay + Message Scoring Simultaneously (S-GAP-RC-1) [P0]
Trigger decay task while sending a message in rapid succession:
```sql
-- Set user past grace so decay will fire
UPDATE users SET last_interaction_at=NOW() - INTERVAL '10 hours',
  grace_period_expires_at=NOW() - INTERVAL '2 hours',
  game_status='active' WHERE id = '<USER_ID>';
```
Execute simultaneously:
```bash
curl -s -X POST https://nikita-api-1040094048579.us-central1.run.app/tasks/decay \
  -H "Authorization: Bearer $TASK_AUTH_SECRET" &
```
```
mcp__telegram-mcp__send_message(chat_id="8211370823", text="thinking about you")
```
Wait 30s. Verify:
```sql
SELECT recorded_at, composite_before, composite_after, event_type,
       recorded_at - LAG(recorded_at) OVER (ORDER BY recorded_at) as gap
FROM score_history WHERE user_id = '<USER_ID>'
ORDER BY recorded_at DESC LIMIT 5;
-- Watch for gap < 500ms between consecutive updates (race risk)
-- Assert: no duplicate event_type entries at same timestamp
-- Assert: composite_after values are consistent (no lost updates)
```
Detection only — log finding. No fix expected without row-level locking.

### RC-2: Concurrent Pipeline Runs (S-GAP-RC-3) [P0]
```sql
SELECT COUNT(*) FROM job_executions
WHERE job_name = 'process-conversations' AND status = 'in_progress';
-- Assert: 0 or 1 (never 2+ simultaneously)
SELECT content, COUNT(*) as dupes FROM memory_facts
WHERE user_id = '<USER_ID>'
GROUP BY content HAVING COUNT(*) > 1;
-- Assert: 0 duplicate memory facts (duplication indicates concurrent pipeline)
```

### RC-3: Boss Threshold + Decay Reversal (S-GAP-RC-5) [P0]
Score is at threshold boundary. Decay fires and drops score below threshold while boss was about to trigger.
```sql
UPDATE users SET relationship_score=55.1, game_status='active', chapter=1
WHERE id = '<USER_ID>';
UPDATE user_metrics SET intimacy=58, passion=55, trust=55, secureness=53
WHERE user_id = '<USER_ID>';
UPDATE users SET last_interaction_at=NOW() - INTERVAL '10 hours',
  grace_period_expires_at=NOW() - INTERVAL '2 hours' WHERE id = '<USER_ID>';
```
Trigger decay:
```bash
curl -s -X POST https://nikita-api-1040094048579.us-central1.run.app/tasks/decay \
  -H "Authorization: Bearer $TASK_AUTH_SECRET"
```
```sql
SELECT relationship_score, game_status FROM users WHERE id = '<USER_ID>';
-- Assert: score dropped below 55, game_status still 'active' (no phantom boss trigger)
-- Assert: no crash
```

### RC-4: Multiple /start in Rapid Succession (S-GAP-RC-7) [P0]
Wipe account (Phase 00), then send 3 /start commands within 2 seconds:
```
mcp__telegram-mcp__send_message(chat_id="8211370823", text="/start")
mcp__telegram-mcp__send_message(chat_id="8211370823", text="/start")
mcp__telegram-mcp__send_message(chat_id="8211370823", text="/start")
```
```sql
SELECT COUNT(*) FROM pending_registrations WHERE telegram_id = 746410893;
-- Assert: 1 row (upsert) OR <=3 rows (benign, no crash)
```
**Assert**: No 500 errors in Cloud Run logs. System handles gracefully.

---

## Category 2: Security (10 scenarios)

### SEC-1: IDOR — User A Reads User B Data (S-GAP-SEC-3) [P0]
```sql
-- Verify RLS is enabled on sensitive tables
SELECT tablename, rowsecurity FROM pg_tables
WHERE tablename IN ('users', 'user_metrics', 'conversations', 'memory_facts', 'score_history')
AND schemaname = 'public';
-- Assert: rowsecurity = TRUE on all listed tables
```

### SEC-2: Admin Bypass — Non-Admin Hits Admin Endpoints (S-GAP-SEC-5) [P0]
```bash
# Use a regular (non-admin) JWT token
curl -s -o /dev/null -w "%{http_code}" \
  https://portal-phi-orcin.vercel.app/api/v1/admin/users \
  -H "Authorization: Bearer <NON_ADMIN_JWT>"
```
**Assert**: 401 or 403 (not 200).

### SEC-3: SQL Injection via Telegram Message (S-GAP-EDGE-3) [P0]
```
mcp__telegram-mcp__send_message(chat_id="8211370823", text="'; DROP TABLE users; --")
```
Wait 15s. **Assert**: No crash. Bot responds normally.
```sql
SELECT COUNT(*) FROM users;
-- Assert: returns a number (table not dropped)
```

### SEC-4: XSS via Portal Input (S-GAP-SEC-6) [P1]
If portal has any user-editable fields (settings, name):
Submit: `<script>alert('xss')</script>` as name value.
**Assert**: Input is sanitized or escaped. No script execution in browser.

### SEC-5: Webhook Replay Attack (S-GAP-SEC-7) [P1]
Capture a valid webhook payload, replay it 10 seconds later:
```bash
curl -s -X POST https://nikita-api-1040094048579.us-central1.run.app/api/v1/telegram/webhook \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-Api-Secret-Token: <VALID_SECRET>" \
  -d '{"update_id": <PREVIOUSLY_USED_ID>, "message": {"text": "replay test", "chat": {"id": 8211370823}}}'
```
**Assert**: Either rejected (idempotency) or processed harmlessly (no duplicate scoring).

### SEC-6: TASK_AUTH_SECRET Brute Force (S-GAP-SEC-8) [P1]
```bash
for token in "admin" "password" "12345" "Bearer" "null"; do
  curl -s -o /dev/null -w "%{http_code} " -X POST \
    https://nikita-api-1040094048579.us-central1.run.app/tasks/decay \
    -H "Authorization: Bearer $token"
done
```
**Assert**: All return 401 or 403. No 200 or 500 responses.

---

## Category 3: Data Integrity (10 scenarios)

### DI-1: Score Updated but score_history Write Fails (S-GAP-DI-1) [P0]
```sql
-- Check for orphaned score updates (score changed but no history entry)
SELECT u.relationship_score,
  (SELECT score FROM score_history WHERE user_id = u.id ORDER BY created_at DESC LIMIT 1) as last_recorded
FROM users u WHERE u.id = '<USER_ID>';
-- Assert: relationship_score == last_recorded (within 0.01 tolerance)
```

### DI-2: Memory Fact Duplication (S-GAP-DI-3) [P1]
```sql
SELECT content, COUNT(*) as dupes FROM memory_facts
WHERE user_id = '<USER_ID>' AND is_active = true
GROUP BY content HAVING COUNT(*) > 1;
-- Assert: 0 rows (no duplicate active facts)
```

### DI-3: Composite Score Consistency (S-GAP-DI-4) [P0]
```sql
SELECT u.relationship_score,
  ROUND((m.intimacy * 0.30 + m.passion * 0.25 + m.trust * 0.25 + m.secureness * 0.20)::numeric, 2) as computed
FROM users u JOIN user_metrics m ON m.user_id = u.id
WHERE u.id = '<USER_ID>';
-- Assert: relationship_score == computed (within 0.05 tolerance)
```

### DI-4: Empty Conversation Processing (S-GAP-DI-5) [P1]
```sql
SELECT id, status, message_count FROM conversations
WHERE user_id = '<USER_ID>' AND message_count = 0;
-- Assert: 0 rows OR status != 'processed' (empty conversations should not be processed)
```

---

## Category 4: Timing Edge Cases (10 scenarios)

### TIME-1: Exact Grace Boundary (S-GAP-TIME-1) [P1]
```sql
-- Set user exactly at grace boundary
UPDATE users SET last_interaction_at=NOW() - INTERVAL '8 hours',
  grace_period_expires_at=NOW(),
  game_status='active' WHERE id = '<USER_ID>';
```
Trigger decay. Verify: either no decay (grace inclusive) or minimal decay (boundary behavior).
Log actual behavior as OBSERVATION.

### TIME-2: Decimal Precision at Boss Threshold (S-GAP-TIME-2) [P1]
```sql
UPDATE users SET relationship_score=54.9999 WHERE id = '<USER_ID>';
UPDATE user_metrics SET intimacy=58, passion=55, trust=54, secureness=53
WHERE user_id = '<USER_ID>';
```
Send a message that should add +0.5 delta. Verify:
```sql
SELECT relationship_score, game_status FROM users WHERE id = '<USER_ID>';
-- Does 54.9999 + 0.5 = 55.4999 trigger boss? Or does 55.0000 exact?
-- Log: threshold comparison behavior (>=55 vs >55)
```

### TIME-3: pg_cron Overlap — Two Decay Jobs Fire (S-GAP-TIME-3) [P1]
```sql
SELECT COUNT(*) FROM job_executions
WHERE job_name = 'decay' AND status = 'in_progress';
-- Assert: 0 or 1 (mutex/advisory lock prevents overlap)
-- If 2+: log as HIGH finding (double-decay risk)
```

---

## Category 5: Missing Journeys (10 scenarios)

### MJ-1: /help Command (S-GAP-MJ-1) [P1]
```
mcp__telegram-mcp__send_message(chat_id="8211370823", text="/help")
```
Wait 10s. **Assert**: Either a help message or graceful ignore (no crash, no 500).

### MJ-2: /status Command (S-GAP-MJ-2) [P1]
```
mcp__telegram-mcp__send_message(chat_id="8211370823", text="/status")
```
Wait 10s. **Assert**: Either a status summary or graceful ignore.

### MJ-3: Non-English Messages (S-GAP-MJ-3) [P1]
```
mcp__telegram-mcp__send_message(chat_id="8211370823", text="Ich vermisse dich so sehr")
```
Wait 15s. **Assert**: Nikita responds (likely in English). No crash. Scoring still applies.

### MJ-4: Speed Run Detection (S-GAP-MJ-4) [P1]
Send 20 messages in under 60 seconds. Verify:
- No rate limiting crash (log if rate limiting exists)
- Score deltas still applied correctly
- No duplicate pipeline runs

---

## Pass/Fail Criteria

| Scenario | Priority | Pass Condition |
|----------|----------|----------------|
| RC-1: Decay + message race | P0 | No lost updates, no crash |
| RC-3: Threshold + decay reversal | P0 | No phantom boss, no crash |
| RC-4: Multiple /start | P0 | Graceful handling, no 500 |
| SEC-1: RLS enabled | P0 | rowsecurity=TRUE on all tables |
| SEC-2: Admin bypass rejected | P0 | 401/403 for non-admin |
| SEC-3: SQL injection harmless | P0 | Bot responds normally, table intact |
| DI-1: Score/history consistency | P0 | Values match within tolerance |
| DI-3: Composite consistency | P0 | Formula matches stored score |
| SEC-6: Brute force rejected | P1 | All invalid tokens get 401/403 |
| MJ-3: Non-English handled | P1 | No crash, response received |

Classify all findings using `references/classification-system.md`.
Log all findings via:
`[TIMESTAMP] E2E_NIKITA: Phase 9 ADVERSARIAL — [ID] — PASS/FAIL/OBSERVATION — [note]`
