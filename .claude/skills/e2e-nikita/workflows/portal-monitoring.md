# Portal Monitoring — Chrome DevTools MCP Reference

## Load Chrome MCP
```
ToolSearch: select:mcp__chrome-devtools__navigate_page,mcp__chrome-devtools__take_screenshot
ToolSearch: select:mcp__chrome-devtools__evaluate_script,mcp__chrome-devtools__click
ToolSearch: select:mcp__chrome-devtools__fill
```

## Core Operations

### Navigate and Screenshot
```
mcp__chrome-devtools__navigate_page(url="https://portal-phi-orcin.vercel.app")
-- Wait 3s for hydration
mcp__chrome-devtools__take_screenshot()
```

### Check Current URL (verify redirect worked)
```
mcp__chrome-devtools__evaluate_script(script="window.location.href")
```

### Get Page Text (verify content loaded)
```
mcp__chrome-devtools__evaluate_script(script="document.body.innerText.substring(0, 500)")
```

### Fill Form Field
```
mcp__chrome-devtools__fill(selector="input[type='email']", value="simon.yang.ch@gmail.com")
mcp__chrome-devtools__click(selector="button[type='submit']")
```

### Check for Errors in DOM
```
mcp__chrome-devtools__evaluate_script(
  script="Array.from(document.querySelectorAll('[class*=error]')).map(e=>e.textContent).join(', ')"
)
```

### JS Console Error Check Pattern
After navigating each route:
```
mcp__chrome-devtools__evaluate_script(
  script="(() => { const errorBoundaries = document.querySelectorAll('[class*=error], [data-error]'); const bodyText = document.body.innerText; const hasErrorText = /something went wrong|error occurred|500|TypeError/i.test(bodyText); return { errorBoundaries: errorBoundaries.length, hasErrorText }; })()"
)
```
Also use `list_console_messages` and filter for `TypeError|ReferenceError|Unhandled` if available.

## Complete Portal Route Inventory (24 routes)

### Player Routes (15)
| Route | Expected Content | Method |
|-------|-----------------|--------|
| `/login` | Email input + "Send Magic Link" button | F |
| `/dashboard` | Score ring, chapter badge, score timeline, radar chart | F |
| `/dashboard/engagement` | 6 engagement states, active state highlighted, multiplier | F |
| `/dashboard/vices` | 8 vice category cards with intensity bars | F |
| `/dashboard/conversations` | Conversation list with All/Text/Voice/Boss filters | F |
| `/dashboard/conversations/[id]` | Message thread with timestamps | F |
| `/dashboard/insights` | Score Breakdown table with non-zero deltas | F |
| `/dashboard/diary` | Diary entries OR "No diary entries yet" | F |
| `/dashboard/nikita` | MoodOrb, Today's Events, What's on Her Mind, Storylines, Social Circle | F |
| `/dashboard/nikita/day` | Date navigation, Psyche Insights, WarmthMeter, Friends | F |
| `/dashboard/nikita/mind` | Thought feed with pagination OR empty state | F |
| `/dashboard/nikita/stories` | Active Arcs with "Show resolved" toggle | F |
| `/dashboard/nikita/circle` | Social circle gallery OR empty state | F |
| `/dashboard/settings` | Email, timezone, push notifications, Telegram status, Delete Account | F |
| `/auth/callback` | Redirect handler (not directly navigable) | — |

### Admin Routes (9)
| Route | Expected Content | Method |
|-------|-----------------|--------|
| `/admin` | System Overview KPIs (cyan accent) | F |
| `/admin/users` | User table with search, chapter/state filters | F |
| `/admin/users/[id]` | User detail page | F |
| `/admin/pipeline` | 10 stage health cards (extraction through prompt_builder) | F |
| `/admin/jobs` | Processing stats (success rate, duration, failed, pending, stuck) | F |
| `/admin/prompts` | Prompt table with detail panel OR empty state | F |
| `/admin/text` | Text conversation table with score_delta badges | F |
| `/admin/voice` | Voice conversation table OR empty state | F |
| `/admin/conversations/[id]` | Conversation Inspector with pipeline events | F |

## Common Failures

| Symptom | Likely Cause | Action |
|---------|-------------|--------|
| Blank page after navigate | Vercel cold start | Wait 5s, refresh screenshot |
| Redirected to / on /admin | Admin role not set | Fix Supabase metadata |
| 500 error on any route | API proxy failing | Check Cloud Run health |
| Loading spinner forever | Supabase client init | Check env vars in Vercel |
| TypeError on /admin/text | score_delta.toFixed on null | GH #152 — apply Number() guard |
| Delta always 0 on /insights | Only reads details.delta | GH #153 — use _compute_score_delta |
