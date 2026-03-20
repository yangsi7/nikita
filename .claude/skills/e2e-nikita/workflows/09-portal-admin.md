# Phase 09: Portal — Admin Pages (E09, 24 scenarios)

## Prerequisites
User `simon.yang.ch@gmail.com` must have `raw_user_meta_data.role = "admin"` in Supabase
AND email must be in Cloud Run ADMIN_EMAILS env var. Already configured per CLAUDE.md.
Chrome DevTools MCP loaded, portal session from Phase 08 may still be active.

## Step 1: Navigate to Admin Dashboard (S-9.1.1) [method: F]
```
mcp__chrome-devtools__navigate_page(url="https://portal-phi-orcin.vercel.app/admin")
mcp__chrome-devtools__take_screenshot()
```
Assert: Admin dashboard loads (cyan accent, NOT rose player accent). If redirected to /dashboard,
the admin role is not set — verify Supabase metadata.

## Step 2: Check Admin Role in Supabase [method: A]
```sql
SELECT id, email, raw_user_meta_data->>'role' as role
FROM auth.users WHERE email = 'simon.yang.ch@gmail.com';
-- Assert: role = 'admin'
```

## Step 3: Verify User List Page (S-9.1.2) [method: F]
```
mcp__chrome-devtools__navigate_page(url="https://portal-phi-orcin.vercel.app/admin/users")
mcp__chrome-devtools__take_screenshot()
```
Assert: User list shows at least 1 user (the test account). Table with game_status, chapter, score.

## Step 4: Verify Pipeline View (S-9.2.1) [method: F]
```
mcp__chrome-devtools__navigate_page(url="https://portal-phi-orcin.vercel.app/admin/pipeline")
mcp__chrome-devtools__take_screenshot()
```
Assert: Pipeline overview renders — no 500 error, shows stage counts or recent pipeline runs.

## Step 5: Verify Jobs Page (S-9.3.1) [method: F]
```
mcp__chrome-devtools__navigate_page(url="https://portal-phi-orcin.vercel.app/admin/jobs")
mcp__chrome-devtools__take_screenshot()
```
Assert: Job execution history shows. job_executions table visible.

## Step 6: Verify Admin-only Isolation (S-9.4.1) [method: F]
Verify a non-admin route redirects properly:
```
mcp__chrome-devtools__evaluate_script(script="window.location.href")
```
Assert: If on admin route, confirms admin access is active.

## Step 7: Verify Text Monitor (S-9.5.1) [method: F]
```
mcp__chrome-devtools__navigate_page(url="https://portal-phi-orcin.vercel.app/admin/text")
mcp__chrome-devtools__take_screenshot()
```
Assert: Page renders WITHOUT crash (regression for GH #152).
Assert: Table with conversation rows OR empty state. No TypeError in console.

## Step 8: Verify Voice Monitor (S-9.5.2) [method: F]
```
mcp__chrome-devtools__navigate_page(url="https://portal-phi-orcin.vercel.app/admin/voice")
mcp__chrome-devtools__take_screenshot()
```
Assert: "No voice conversations yet" empty state OR voice table.

## Step 9: Verify Prompts (S-9.6.1) [method: F]
```
mcp__chrome-devtools__navigate_page(url="https://portal-phi-orcin.vercel.app/admin/prompts")
mcp__chrome-devtools__take_screenshot()
```
Assert: "No prompts generated yet" empty state OR paginated table.

## Step 10: Verify Conversation Inspector (S-9.7.1) [method: F]
Get conversation ID from DB:
```sql
SELECT id FROM conversations WHERE user_id='<USER_ID>' LIMIT 1;
```
```
mcp__chrome-devtools__navigate_page(url="https://portal-phi-orcin.vercel.app/admin/conversations/<ID>")
mcp__chrome-devtools__take_screenshot()
```
Assert: "Conversation Inspector" heading with breadcrumbs. Pipeline events section visible.

## Step 11: JS Console Error Sweep (S-9.8.1) [method: F]
Same pattern as Phase 08 Step 18 — check all admin routes for console errors.
```
mcp__chrome-devtools__evaluate_script(
  script="(() => { const errorBoundaries = document.querySelectorAll('[class*=error], [data-error]'); const bodyText = document.body.innerText; const hasErrorText = /something went wrong|error occurred|500|TypeError/i.test(bodyText); return { errorBoundaries: errorBoundaries.length, hasErrorText }; })()"
)
```
Assert: Zero error-level console messages across all admin routes.

## Pass/Fail Criteria

| Scenario | Priority | Pass Condition |
|----------|----------|----------------|
| S-9.1.1: Admin dashboard loads | P0 | /admin renders with cyan accent [F] |
| S-9.1.2: User list shows data | P1 | At least 1 user row in /admin/users [F] |
| S-9.2.1: Pipeline view renders | P1 | No 500 error on /admin/pipeline [F] |
| S-9.3.1: Jobs view renders | P1 | job_executions visible in /admin/jobs [F] |
| S-9.4.1: Non-admin blocked | P0 | Player role user redirected from /admin [F] |
| S-9.4.2: Non-admin redirect confirmed | P0 | Non-admin user redirected from /admin [A] |
| S-9.5.1: /admin/text no crash | P1 | Renders without crash (GH #152 regression) [F] |
| S-9.5.2: /admin/voice renders | P1 | Empty state or table [F] |
| S-9.6.1: /admin/prompts renders | P1 | Empty state or table [F] |
| S-9.7.1: Conversation Inspector renders | P1 | Inspector with pipeline events [F] |
| S-9.8.1: No JS console errors | P1 | Zero errors across all admin routes [F] |

## Recovery: Admin Role Not Set
```sql
UPDATE auth.users
SET raw_user_meta_data = raw_user_meta_data || '{"role": "admin"}'::jsonb
WHERE email = 'simon.yang.ch@gmail.com';
```
Then refresh portal — admin routes should become accessible.
