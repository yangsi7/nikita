# Failure Recovery Reference — E2E Nikita

## Failure Mode 1: Bot Not Responding

**Detection:**
```
mcp__telegram-mcp__get_messages(chat_id="8211370823", page_size=3)
-- Last message is your own (from_id=746410893), no bot reply
```

**Recovery steps:**
1. Check Cloud Run health: `curl -s https://nikita-api-1040094048579.us-central1.run.app/health`
2. If 200: wait 30s, send message again (cold start delay)
3. If error/timeout: Cloud Run is down — log BLOCKED, skip to next phase
4. If health OK but still no reply after 60s: check webhook registration via Telegram Bot API
5. Log: `[TIMESTAMP] E2E_NIKITA: BLOCKED — bot not responding, Cloud Run status: <result>`

---

## Failure Mode 2: OTP Email Not Arriving

**Detection:**
```
mcp__gmail__search_emails(query="subject:OTP OR subject:verification", max_results=3)
-- Empty results after 30s
```

**Recovery steps:**
1. Check spam folder: `mcp__gmail__search_emails(query="in:spam OTP", max_results=3)`
2. If in spam: read and extract OTP from there
3. If not found after 60s: check pending_registrations:
   ```sql
   SELECT telegram_id, otp_code, created_at FROM pending_registrations
   WHERE telegram_id = 746410893;
   ```
4. If row exists with `otp_code`: use it directly (bypasses email check)
5. If no row: resend `/start` and retry
6. Log: `[TIMESTAMP] E2E_NIKITA: OTP extracted directly from DB (email delayed)`

---

## Failure Mode 3: Onboarding Stuck Mid-Flow

**Detection:** Bot stopped responding mid-onboarding (after /start, before completion).

**Symptom SQL:**
```sql
SELECT telegram_id, current_step, created_at FROM pending_registrations
WHERE telegram_id = 746410893;
```

**Recovery steps:**
1. If `current_step` is stale (>5 min old): wipe and restart
   ```sql
   DELETE FROM pending_registrations WHERE telegram_id = 746410893;
   ```
2. Send `/start` again — fresh flow
3. If repeatedly sticking on same step: log as FAIL with step name, proceed to next phase via SQL setup

---

## Failure Mode 4: Boss Encounter LLM Judgment Inconsistent

**Detection:** Sent PASS-quality boss response but `game_status` still = `boss_fight` after 20s.

**Recovery steps:**
1. Check boss_attempts count:
   ```sql
   SELECT boss_attempts, boss_fight_started_at FROM users WHERE id = '<USER_ID>';
   ```
2. Retry with stronger response from conversation-style.md boss template
3. If 2nd attempt still in boss_fight: force via SQL
   ```sql
   UPDATE users SET game_status='active', chapter=chapter+1, boss_attempts=0,
     boss_fight_started_at=NULL, cool_down_until=NULL WHERE id='<USER_ID>';
   ```
4. Log: `[TIMESTAMP] E2E_NIKITA: Boss judgment non-deterministic — forced via SQL, chapter advanced`
5. Note: This does NOT count as a test failure for the boss trigger test itself

---

## Failure Mode 5: Score Not Increasing After Messages

**Detection:**
```sql
SELECT COUNT(*) FROM score_history
WHERE user_id = '<USER_ID>' AND recorded_at > NOW() - INTERVAL '5 minutes';
-- Returns 0
```

**Recovery steps:**
1. Check if pipeline ran:
   ```sql
   SELECT status, started_at FROM job_executions
   ORDER BY started_at DESC LIMIT 3;
   ```
2. If no recent job: trigger manually:
   ```bash
   curl -X POST https://nikita-api-1040094048579.us-central1.run.app/tasks/process-conversations \
     -H "Authorization: Bearer $TASK_AUTH_SECRET"
   ```
3. Wait 30s, recheck score_history
4. If pipeline errored: check job status = 'failed', log as HIGH issue
5. Proceed with SQL score adjustment for dependent tests

---

## Failure Mode 6: Admin Portal Redirect Loop

**Detection:**
```
mcp__chrome-devtools__evaluate_script(script="window.location.href")
-- Returns "/" instead of "/admin" after navigating to /admin
```

**Recovery steps:**
1. Verify admin role in Supabase:
   ```sql
   SELECT raw_user_meta_data->>'role' FROM auth.users
   WHERE email = 'simon.yang.ch@gmail.com';
   ```
2. If role != 'admin': set it:
   ```sql
   UPDATE auth.users SET raw_user_meta_data = raw_user_meta_data || '{"role":"admin"}'
   WHERE email = 'simon.yang.ch@gmail.com';
   ```
3. Also verify ADMIN_EMAILS env var on Cloud Run includes the test email
4. Clear browser cookies, re-login via magic link
5. Log: `[TIMESTAMP] E2E_NIKITA: Admin role was missing — fixed via Supabase, re-tested`

---

## Failure Mode 7: Telegram MCP Session Expired

**Detection:**
```
mcp__telegram-mcp__send_message(...)
-- Error: "session expired" or "unauthorized" or no tool available
```

**Recovery steps:**
1. This requires manual intervention — cannot be fixed programmatically
2. Log: `[TIMESTAMP] E2E_NIKITA: BLOCKED — Telegram MCP session expired`
3. Instructions for user: `cd ../telegram-mcp && python session_string_generator.py`
4. After new session: resume test from current phase (do NOT re-wipe account)

---

## Failure Mode 8: Portal Cold Start (Blank Page)

**Detection:**
```
mcp__chrome-devtools__take_screenshot()
-- Screenshot shows blank/white page or loading spinner
```

**Recovery steps:**
1. Wait 5s, take another screenshot
2. If still blank: navigate again to same URL
3. If Vercel cold start: evaluate body text:
   ```
   mcp__chrome-devtools__evaluate_script(script="document.body.innerText.substring(0,100)")
   ```
4. If HTML returned but UI not visible: JS hydration delay — wait 5s more
5. Log blank page as LOW if recovers within 10s, MEDIUM if requires navigation retry

---

## Failure Mode 9: Decay Did Not Apply

**Detection:** Triggered `/tasks/decay` but `relationship_score` unchanged.

**Recovery steps:**
1. Verify preconditions were met:
   ```sql
   SELECT last_message_at, grace_period_expires_at, relationship_score
   FROM users WHERE id = '<USER_ID>';
   -- Assert: last_message_at is in the past, grace_period_expires_at < NOW()
   ```
2. If grace_period_expires_at is in future: decay correctly SKIPPED (grace protection working)
3. If both timestamps are past and score unchanged: log as HIGH — decay logic bug
4. Apply manual score reduction to continue dependent tests

---

## Quick Reference: Failure Severity Guide

| Mode | Severity | Can Continue Test? |
|------|----------|-------------------|
| Bot not responding (Cloud Run down) | CRITICAL | BLOCKED — stop |
| OTP email delay | LOW | Yes — read from DB |
| Onboarding stuck | MEDIUM | Yes — wipe + restart |
| Boss judgment inconsistent | LOW | Yes — force via SQL |
| Score not increasing | HIGH | Partial — trigger manually |
| Admin redirect loop | MEDIUM | Yes — fix role |
| Telegram session expired | CRITICAL | BLOCKED — manual fix |
| Portal blank page (recovers) | LOW | Yes — retry |
| Decay did not apply | HIGH | Partial — verify grace |
