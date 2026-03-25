# Portal Monitoring — agent-browser Reference

## About agent-browser

agent-browser is a CLI tool for browser automation in E2E testing. It replaces the
Chrome DevTools MCP and runs via Bash commands. All portal testing phases (08, 09)
use these patterns.

## Core Commands

### Navigate to a URL
```bash
agent-browser navigate "https://portal-phi-orcin.vercel.app"
```
Wait 3s for hydration before interacting.

### Take a Screenshot
```bash
agent-browser screenshot /tmp/e2e-screenshot-name.png
```

### Inspect Page (Accessibility Snapshot)
```bash
agent-browser snapshot
```
Returns the accessibility tree with `@ref` identifiers for interactive elements.
Always run this before `click` or `fill` to discover the correct refs.

### Click an Element
```bash
agent-browser click @ref-identifier
```

### Fill a Form Field
```bash
agent-browser fill @ref-identifier "value"
```

### Execute JavaScript
```bash
agent-browser execute "window.location.href"
```

```bash
agent-browser execute "document.body.innerText.substring(0, 500)"
```

### Check Current URL (verify redirect worked)
```bash
agent-browser execute "window.location.href"
```

### Get Page Text (verify content loaded)
```bash
agent-browser execute "document.body.innerText.substring(0, 500)"
```

### Check for Errors in DOM
```bash
agent-browser execute "Array.from(document.querySelectorAll('[class*=error]')).map(e=>e.textContent).join(', ')"
```

### JS Console Error Check Pattern
After navigating each route:
```bash
agent-browser execute "(() => { const errorBoundaries = document.querySelectorAll('[class*=error], [data-error]'); const bodyText = document.body.innerText; const hasErrorText = /something went wrong|error occurred|500|TypeError/i.test(bodyText); return { errorBoundaries: errorBoundaries.length, hasErrorText }; })()"
```
Also check for collected console errors:
```bash
agent-browser execute "JSON.stringify(window.__console_errors || [])"
```

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

## Workflow: Navigate + Verify Pattern

For each route, follow this pattern:
```bash
# 1. Navigate
agent-browser navigate "<url>"

# 2. Wait for hydration (3-5s)

# 3. Screenshot for evidence
agent-browser screenshot /tmp/e2e-<route-name>.png

# 4. Verify content (optional, when screenshot alone is insufficient)
agent-browser execute "<js expression>"

# 5. Check for errors
agent-browser execute "(() => { ... error check ... })()"
```

## Common Failures

| Symptom | Likely Cause | Action |
|---------|-------------|--------|
| Blank page after navigate | Vercel cold start | Wait 5s, re-navigate |
| Redirected to / on /admin | Admin role not set | Fix Supabase metadata |
| 500 error on any route | API proxy failing | Check Cloud Run health |
| Loading spinner forever | Supabase client init | Check env vars in Vercel |
| TypeError on /admin/text | score_delta.toFixed on null | GH #152 — apply Number() guard |
| Delta always 0 on /insights | Only reads details.delta | GH #153 — use _compute_score_delta |
| @ref not found | Page not fully loaded | Run `agent-browser snapshot` to inspect current state |
