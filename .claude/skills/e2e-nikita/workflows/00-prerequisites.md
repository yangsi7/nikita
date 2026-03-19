# Phase 00: Prerequisites

## Purpose
Verify MCP tools, Cloud Run health, and account state. Wipe test account for fresh run.
For scopes that use SQL setup (boss, decay, engagement, vice, terminal): establish active user.

## Prerequisites
None — this is always first.

## Step 1: Load MCP Tools
```
ToolSearch: select:mcp__telegram-mcp__send_message,mcp__telegram-mcp__get_messages
ToolSearch: select:mcp__telegram-mcp__list_inline_buttons,mcp__telegram-mcp__press_inline_button
ToolSearch: select:mcp__telegram-mcp__resolve_username
ToolSearch: select:mcp__supabase__execute_sql
ToolSearch: select:mcp__gmail__search_emails,mcp__gmail__read_email
ToolSearch: select:mcp__chrome-devtools__navigate_page,mcp__chrome-devtools__take_screenshot
```

## Step 2: Verify Telegram Session
```
mcp__telegram-mcp__get_me
```
If error: Telegram MCP session expired. Run `session_string_generator.py` in `../telegram-mcp/`.
If ok: confirm username is `@youwontgetmyname` or `@to5meo`.

## Step 3: Verify Cloud Run Health
```bash
curl -s https://nikita-api-1040094048579.us-central1.run.app/health
```
Expected: `{"status": "ok"}` within 30s (first hit may be cold start).
If timeout: retry once after 30s.

## Step 4: Check Existing Account State
```sql
SELECT u.id, u.telegram_id, u.game_status, u.chapter, u.onboarding_status,
       u.relationship_score, u.boss_attempts
FROM users u
WHERE u.id IN (SELECT id FROM auth.users WHERE email = 'simon.yang.ch@gmail.com');
```
Record USER_ID if user exists. Note current state.

## Step 5: Account Wipe (for full, onboarding, gameplay, crossplatform scopes)
Only wipe if fresh start is needed. For SQL-setup scopes, skip to Step 6.

```sql
-- Get user ID first
SELECT id FROM auth.users WHERE email = 'simon.yang.ch@gmail.com';
-- Then wipe (replace <USER_ID> and <TG_ID> = 746410893)
DELETE FROM onboarding_states WHERE telegram_id = 746410893;
DELETE FROM users WHERE id = '<USER_ID>';
DELETE FROM auth.users WHERE email = 'simon.yang.ch@gmail.com';
DELETE FROM pending_registrations WHERE email = 'simon.yang.ch@gmail.com';
```

## Step 6: Verify Clean State
```sql
SELECT count(*) FROM auth.users WHERE email = 'simon.yang.ch@gmail.com';
-- Expected: 0
SELECT count(*) FROM pending_registrations WHERE telegram_id = 746410893;
-- Expected: 0
```

## Step 7 (SQL-Setup Scopes Only): Create Active User
For boss/decay/engagement/vice/terminal scopes that skip onboarding, use SQL to create an
active user at the required chapter. See @references/sql-queries.md#create-active-user for
the full INSERT template.

## Step 7.5: Verify Critical Feature Flags [method: A]

```sql
-- Verify vice_preferences table exists (required for ViceStage)
SELECT count(*) FROM information_schema.tables WHERE table_name = 'user_vice_preferences';
-- Must be 1
```

Then verify ViceStage isn't skipped by checking a recent pipeline execution:
```sql
SELECT event_details->>'vice_stage' as vice_status
FROM pipeline_events
WHERE created_at > NOW() - INTERVAL '24 hours'
ORDER BY created_at DESC LIMIT 1;
```
If vice_stage = 'skipped': log HIGH issue — `VICE_PIPELINE_ENABLED` must be set to true on Cloud Run.

## Pass/Fail Criteria

| Check | Pass | Fail |
|-------|------|------|
| Telegram MCP loaded | `get_me` returns user profile | Auth error → re-auth |
| Cloud Run health | `{"status": "ok"}` ≤ 30s | Timeout → escalate |
| Account clean | count = 0 | Manual check needed |
| Feature flags verified | vice_pipeline_enabled=true | Set env var on Cloud Run |

## Debug Mode: debug-onboarding Diagnostic
If scope is `debug-onboarding`, run only Steps 1-4, then execute this diagnostic:
```sql
SELECT id, email, created_at FROM auth.users WHERE email = 'simon.yang.ch@gmail.com';
SELECT telegram_id, email, otp_state, otp_attempts, created_at, expires_at
FROM pending_registrations WHERE email = 'simon.yang.ch@gmail.com';
SELECT id, telegram_id, game_status, onboarding_status, chapter
FROM users WHERE telegram_id = 746410893;
SELECT telegram_id, current_step, collected_answers, created_at, updated_at
FROM onboarding_states WHERE telegram_id = 746410893;
SELECT * FROM user_profiles WHERE id = '<USER_ID>';
```
Common causes: limbo state (user exists, no profile), stale onboarding_states, expired OTP.
