# Phase 08: Portal — Player Pages (E08, 35 scenarios)

## Prerequisites
USER_ID established. User active with score data. Chrome DevTools MCP loaded.
See @workflows/portal-monitoring.md for Chrome MCP patterns.

## Step 1: Navigate to Portal [method: F]
```
mcp__chrome-devtools__navigate_page(url="https://portal-phi-orcin.vercel.app")
```
Wait 3s.
```
mcp__chrome-devtools__take_screenshot()
```
Assert: Login page visible (email input or Supabase magic link form).

## Step 2: Initiate Magic Link Login [method: F]
```
mcp__chrome-devtools__fill(selector="input[type='email']", value="simon.yang.ch@gmail.com")
mcp__chrome-devtools__click(selector="button[type='submit']")
```
Wait 5s.

## Step 3: Retrieve Magic Link from Gmail [method: F]
```
mcp__gmail__search_emails(query="from:noreply subject:magic newer_than:5m OR from:noreply subject:login newer_than:5m", maxResults=3)
mcp__gmail__read_email(id="<message_id>")
```
Extract the magic link URL from email body.

## Step 4: Navigate Magic Link [method: F]
```
mcp__chrome-devtools__navigate_page(url="<magic_link_url>")
```
Wait 5s.
```
mcp__chrome-devtools__take_screenshot()
```
Assert: Redirected to /dashboard (player home).

## Step 5: Verify Dashboard (S-8.1.1) [method: F]
```
mcp__chrome-devtools__evaluate_script(
  script="document.querySelector('[data-testid=relationship-score]')?.textContent || document.body.innerText.substring(0,200)"
)
```
Assert: Dashboard shows relationship score, chapter indicator, and Nikita's status.
Screenshot for evidence.

## Step 6: Verify Engagement Page (S-8.2.1) [method: F]
```
mcp__chrome-devtools__navigate_page(url="https://portal-phi-orcin.vercel.app/dashboard/engagement")
mcp__chrome-devtools__take_screenshot()
```
Assert: Engagement state displayed (clingy/in_zone/distant etc.), multiplier visible.

## Step 7: Verify Insights Page (S-8.2.2) [method: F]
```
mcp__chrome-devtools__navigate_page(url="https://portal-phi-orcin.vercel.app/dashboard/insights")
mcp__chrome-devtools__take_screenshot()
```
Assert: "Deep Insights" heading visible. Score Breakdown table has rows.
Assert: At least 1 row with non-zero Delta value (regression for GH #153).

## Step 8: Verify Vices Page (S-8.3.1) [method: F]
```
mcp__chrome-devtools__navigate_page(url="https://portal-phi-orcin.vercel.app/dashboard/vices")
mcp__chrome-devtools__take_screenshot()
```
Assert: Vice categories displayed (if any detected). Page renders without error.

## Step 9: Verify Conversations List (S-8.4.1) [method: F]
```
mcp__chrome-devtools__navigate_page(url="https://portal-phi-orcin.vercel.app/dashboard/conversations")
mcp__chrome-devtools__take_screenshot()
```
Assert: Conversation history listed. All/Text/Voice/Boss filters visible.

## Step 10: Verify Conversation Detail (S-8.4.2) [method: F]
Get conversation ID:
```sql
SELECT id FROM conversations WHERE user_id='<USER_ID>' LIMIT 1;
```
```
mcp__chrome-devtools__navigate_page(url="https://portal-phi-orcin.vercel.app/dashboard/conversations/<ID>")
mcp__chrome-devtools__take_screenshot()
```
Assert: Message thread visible with timestamps.

## Step 11: Verify Nikita's World Hub (S-8.6.1) [method: F]
```
mcp__chrome-devtools__navigate_page(url="https://portal-phi-orcin.vercel.app/dashboard/nikita")
mcp__chrome-devtools__take_screenshot()
```
Assert: MoodOrb renders. "Today's Events" and "What's on Her Mind" sections visible.

## Step 12: Verify Nikita's Day (S-8.6.2) [method: F]
```
mcp__chrome-devtools__navigate_page(url="https://portal-phi-orcin.vercel.app/dashboard/nikita/day")
mcp__chrome-devtools__take_screenshot()
```
Assert: Date navigation arrows visible. Psyche Insights section with tips. WarmthMeter present.

## Step 13: Verify Nikita's Mind (S-8.6.3) [method: F]
```
mcp__chrome-devtools__navigate_page(url="https://portal-phi-orcin.vercel.app/dashboard/nikita/mind")
mcp__chrome-devtools__take_screenshot()
```
Assert: "Nikita's Mind" heading with thought count. Empty state OR thought feed.

## Step 14: Verify Storylines (S-8.6.4) [method: F]
```
mcp__chrome-devtools__navigate_page(url="https://portal-phi-orcin.vercel.app/dashboard/nikita/stories")
mcp__chrome-devtools__take_screenshot()
```
Assert: "Storylines" heading. "Show resolved" toggle. Empty state OR arc cards.

## Step 15: Verify Social Circle (S-8.6.5) [method: F]
```
mcp__chrome-devtools__navigate_page(url="https://portal-phi-orcin.vercel.app/dashboard/nikita/circle")
mcp__chrome-devtools__take_screenshot()
```
Assert: "Social Circle" heading with friend count. Empty state OR gallery.

## Step 16: Verify Diary (S-8.7.1) [method: F]
```
mcp__chrome-devtools__navigate_page(url="https://portal-phi-orcin.vercel.app/dashboard/diary")
mcp__chrome-devtools__take_screenshot()
```
Assert: Diary page renders. Empty state "No diary entries yet" OR diary cards.

## Step 17: Verify Settings (S-8.8.1) [method: F]
```
mcp__chrome-devtools__navigate_page(url="https://portal-phi-orcin.vercel.app/dashboard/settings")
mcp__chrome-devtools__take_screenshot()
```
Assert: Email, timezone, push notifications, Telegram status, Delete Account visible.

## Step 18: JS Console Error Sweep (S-8.5.1) [method: F]
For EACH player route visited, check console:
```
mcp__chrome-devtools__evaluate_script(
  script="(() => { const errorBoundaries = document.querySelectorAll('[class*=error], [data-error]'); const bodyText = document.body.innerText; const hasErrorText = /something went wrong|error occurred|500|TypeError/i.test(bodyText); return { errorBoundaries: errorBoundaries.length, hasErrorText }; })()"
)
```
Also use `list_console_messages` and filter for error-level entries.
Assert: Zero error-level console messages across all player routes.

## Pass/Fail Criteria

| Scenario | Priority | Pass Condition |
|----------|----------|----------------|
| S-8.1.1: Dashboard loads | P0 | Relationship score visible on /dashboard [F] |
| S-8.1.2: Score data accurate | P1 | Score matches DB value ±0.5 [F] |
| S-8.1.3: Score ring shows correct score | P1 | Score ring matches DB within +-1 [F] |
| S-8.2.1: Engagement page renders | P1 | No 500 error, state visible [F] |
| S-8.2.2: Insights renders with non-zero deltas | P1 | Non-zero Delta in at least 1 row (GH #153) [F] |
| S-8.3.1: Vices page renders | P1 | No 500 error, renders without crash [F] |
| S-8.4.1: Conversations visible | P0 | At least 1 conversation entry listed [F] |
| S-8.4.2: Conversation detail renders | P1 | Message thread with timestamps [F] |
| S-8.5.1: No JS console errors | P1 | Zero error-level messages across all routes [F] |
| S-8.6.1: Nikita's World hub renders | P1 | MoodOrb and sections visible [F] |
| S-8.6.2: Nikita's Day renders | P1 | Date navigation and WarmthMeter [F] |
| S-8.6.3: Nikita's Mind renders | P1 | Thought feed or empty state [F] |
| S-8.6.4: Storylines renders | P1 | Show resolved toggle visible [F] |
| S-8.6.5: Social Circle renders | P1 | Gallery or empty state [F] |
| S-8.7.1: Diary page renders | P1 | Entries or empty state [F] |
| S-8.8.1: Settings page renders | P0 | Email, timezone, Telegram status [F] |
| S-8.9.1: Login page renders | P2 | Email input and submit button [F] |
| S-8.9.2: Magic link email received | P2 | Email within 30s [F] |
