# Phase 13: Portal Admin

## Scope

All admin routes including God Mode mutations with real DB verification. Admin routes require `user_metadata.role = 'admin'` — the test account `simon.yang.ch@gmail.com` must have admin role.

Portal URL: `https://portal-phi-orcin.vercel.app`

## Prerequisites

- Authenticated admin session (user_metadata.role = 'admin')
- If current session is player-only, re-login with admin account
- Test user exists with gameplay data for management views

### Admin Role Verification
```sql
SELECT raw_user_meta_data->>'role' as role
FROM auth.users
WHERE email = 'simon.yang.ch@gmail.com';
```
**Required**: `role = 'admin'`. If not set:
```sql
UPDATE auth.users
SET raw_user_meta_data = raw_user_meta_data || '{"role": "admin"}'::jsonb
WHERE email = 'simon.yang.ch@gmail.com';
```

## Scenarios Covered

**Admin (S-PA)**: S-PA-001–S-PA-030

---

## Route: /admin

### Steps

1. Navigate to `/admin`
2. Wait 3s for data load

### Verification

- [ ] 5 KPI cards visible: Total Users, Active Users, Boss Fights, Game Overs, Won
- [ ] KPI values are numeric (not NaN, not loading skeleton)
- [ ] Page title or heading indicates admin overview

### DB Cross-check
```sql
SELECT
  COUNT(*) as total_users,
  COUNT(*) FILTER (WHERE game_status = 'active') as active_users,
  COUNT(*) FILTER (WHERE game_status = 'boss_fight') as boss_fights,
  COUNT(*) FILTER (WHERE game_status = 'game_over') as game_overs,
  COUNT(*) FILTER (WHERE game_status = 'won') as won
FROM users;
```
**Verify**: KPI card values match query results.

---

## Route: /admin/users

### Steps

1. Navigate to `/admin/users`
2. Wait 3s for data load

### Verification

- [ ] User table visible (data-testid: `table-users`)
- [ ] Search input present — type test email, verify row filters
- [ ] Chapter filter present — select a chapter, verify rows filter
- [ ] Engagement filter present — select a state, verify rows filter
- [ ] Test user row visible (data-testid: `row-{user_id}`)
- [ ] Row shows: email, chapter, score, game_status
- [ ] Click row → navigates to `/admin/users/[id]`

### Empty State
- [ ] If filters match no users: EmptyState visible (data-testid: `empty-users`)

---

## Route: /admin/users/[id]

### Steps

1. Navigate to `/admin/users/<TEST_USER_ID>` (from row click)
2. Wait 3s for data load

### Verification

- [ ] User detail header: name, email, chapter, score, game_status displayed
- [ ] GodModePanel visible (amber GlassCard with Shield icon)

---

## Route: /admin/users/[id] — God Mode Panel

### Prerequisites

Note the test user's current DB state before mutations:
```sql
SELECT id, relationship_score, chapter, game_status, boss_attempts
FROM users WHERE email = 'simon.yang.ch@gmail.com';
```

### God Mode: Set Score

1. In GodModePanel, find "Set Score (0-100)" input
2. Enter value: `75`
3. Click "Set" button → MutationDialog opens
4. Verify dialog title: "Set Score", description contains "75"
5. Click "Confirm"
6. Wait 3s

**Verification**:
```sql
SELECT relationship_score FROM users WHERE email = 'simon.yang.ch@gmail.com';
```
- [ ] `relationship_score` = 75 (or close — may recalculate composite)
- [ ] Score on page updates to reflect new value

### God Mode: Set Chapter

1. Find "Set Chapter" select
2. Select "Ch III" (chapter 3)
3. Click "Set" → MutationDialog opens
4. Verify dialog description contains "3"
5. Click "Confirm"
6. Wait 3s

**Verification**:
```sql
SELECT chapter FROM users WHERE email = 'simon.yang.ch@gmail.com';
```
- [ ] `chapter` = 3
- [ ] Page reflects updated chapter

### God Mode: Set Game Status

1. Find "Set Game Status" select
2. Select "active"
3. Click "Set" → MutationDialog opens
4. Click "Confirm"
5. Wait 3s

**Verification**:
```sql
SELECT game_status FROM users WHERE email = 'simon.yang.ch@gmail.com';
```
- [ ] `game_status` = 'active'

### God Mode: Set Engagement

1. Find "Set Engagement" select
2. Select "distant"
3. Click "Set" → MutationDialog opens
4. Click "Confirm"
5. Wait 3s

**Verification**:
```sql
SELECT state FROM engagement_state WHERE user_id = '<USER_ID>';
```
- [ ] `state` = 'distant'

### God Mode: Reset Boss

1. First, set boss_attempts to a non-zero value if needed:
   ```sql
   UPDATE users SET boss_attempts = 2 WHERE email = 'simon.yang.ch@gmail.com';
   ```
2. Click "Reset Boss" button → MutationDialog opens
3. Click "Confirm"
4. Wait 3s

**Verification**:
```sql
SELECT boss_attempts FROM users WHERE email = 'simon.yang.ch@gmail.com';
```
- [ ] `boss_attempts` = 0

### God Mode: Clear Engagement

1. Click "Clear Engagement" → MutationDialog opens
2. Click "Confirm"
3. Wait 3s

**Verification**:
```sql
SELECT state FROM engagement_state WHERE user_id = '<USER_ID>';
```
- [ ] `state` reset to default (e.g., 'in_zone' or null)

### God Mode: Cancel Dialog (No DB Change)

1. Click "Set Score" → enter value 99 → click "Set" → Dialog opens
2. Click "Cancel"
3. Wait 2s

**Verification**:
```sql
SELECT relationship_score FROM users WHERE email = 'simon.yang.ch@gmail.com';
```
- [ ] Score unchanged from before the cancel action
- [ ] Dialog dismissed, no toast

### God Mode: Trigger Pipeline

1. Click "Trigger Pipeline" button (cyan variant) → MutationDialog opens
2. Click "Confirm"
3. Wait 5s

**Verification**:
```sql
SELECT id, status, created_at FROM pipeline_executions
WHERE user_id = '<USER_ID>' ORDER BY created_at DESC LIMIT 1;
```
- [ ] New pipeline execution row created

### Restore Test User State
After God Mode testing, restore to a known good state:
```sql
UPDATE users SET relationship_score = 50, chapter = 1, game_status = 'active', boss_attempts = 0
WHERE email = 'simon.yang.ch@gmail.com';
UPDATE engagement_state SET state = 'in_zone' WHERE user_id = '<USER_ID>';
```

---

## Route: /admin/pipeline

### Steps

1. Navigate to `/admin/pipeline`
2. Wait 3s for data load

### Verification

- [ ] PipelineBoard renders (data-testid: `card-pipeline`)
- [ ] Pipeline execution entries visible with stage timing
- [ ] Status indicators (done, failed, pending) displayed

---

## Route: /admin/text

### Steps

1. Navigate to `/admin/text`
2. Wait 3s for data load

### Verification

- [ ] Conversation table renders with text conversations
- [ ] Pagination controls present if > page size
- [ ] Columns include: user, date, score delta, status

---

## Route: /admin/voice

### Steps

1. Navigate to `/admin/voice`
2. Wait 3s for data load

### Verification

- [ ] Conversation table renders with voice conversations
- [ ] Columns include: user, date, duration, status
- [ ] Empty state if no voice conversations exist

---

## Route: /admin/conversations/[id]

### Prerequisites

Note a conversation ID from `/admin/text` or `/admin/voice`.

### Steps

1. Navigate to `/admin/conversations/<ID>`
2. Wait 3s for data load

### Verification

- [ ] SummaryCards visible (score delta, platform, duration)
- [ ] StageTimelineBar renders pipeline stages
- [ ] Event expansion: click a stage → details expand
- [ ] Message transcript visible (user + nikita turns)

---

## Route: /admin/jobs

### Steps

1. Navigate to `/admin/jobs`
2. Wait 3s for data load

### Verification

- [ ] 5 stat cards visible (one per job type: decay, process, deliver, summary, boss-timeout, psyche-batch — or subset)
- [ ] Each card shows: job name, last run time, status, success/fail count (data-testid: `card-job-{name}`)

---

## Route: /admin/prompts

### Steps

1. Navigate to `/admin/prompts`
2. Wait 3s for data load

### Verification

- [ ] Prompts table renders with rows
- [ ] Click a row → Sheet (side panel) opens with prompt details
- [ ] Sheet shows: prompt name, content, metadata
- [ ] Close sheet → table visible again

---

## Portal Accuracy Recording

```xml
<portal_check phase="13-admin">
  <route path="/admin">
    <field name="total_users" db="..." portal="..." match="true|false"/>
    <field name="active_users" db="..." portal="..." match="true|false"/>
    <field name="kpi_cards_count" expected="5" actual="..."/>
  </route>
  <route path="/admin/users">
    <field name="test_user_visible" value="true|false"/>
    <field name="search_works" value="true|false"/>
    <field name="filters_work" value="true|false"/>
  </route>
  <route path="/admin/users/[id]">
    <field name="god_mode_set_score" db_before="..." db_after="..." match="true|false"/>
    <field name="god_mode_set_chapter" db_before="..." db_after="..." match="true|false"/>
    <field name="god_mode_reset_boss" db_before="..." db_after="..." match="true|false"/>
    <field name="god_mode_cancel_no_change" value="true|false"/>
  </route>
  <route path="/admin/pipeline">
    <field name="board_renders" value="true|false"/>
  </route>
  <route path="/admin/jobs">
    <field name="stat_cards_visible" value="true|false"/>
  </route>
</portal_check>
```

---

## Decision Gate

- All admin routes render without error → **continue to Phase 14**
- God Mode mutations verified against DB → PASS
- KPI accuracy ≥ 80% → PASS
- God Mode mutation fails (DB unchanged after confirm) → **HIGH finding**
- Admin route returns 403 for admin user → **CRITICAL finding**
- Non-admin accessing admin route NOT redirected → **CRITICAL finding**
