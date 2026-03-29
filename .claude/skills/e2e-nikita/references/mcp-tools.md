# MCP Tool Patterns Reference — E2E Nikita

## Load All Required Tools (run at session start)

```
ToolSearch: select:mcp__telegram-mcp__send_message,mcp__telegram-mcp__get_messages
ToolSearch: select:mcp__telegram-mcp__list_inline_buttons,mcp__telegram-mcp__press_inline_button
ToolSearch: select:mcp__gmail__search_emails,mcp__gmail__read_email
ToolSearch: select:mcp__supabase__execute_sql
ToolSearch: select:mcp__gemini__gemini-analyze-text
```

## Telegram MCP

### Send a message (chat_id is always 8211370823 for test account)
```
mcp__telegram-mcp__send_message(
  chat_id="8211370823",
  text="your message here"
)
```

### Read recent messages from bot
```
mcp__telegram-mcp__get_messages(
  chat_id="8211370823",
  page_size=5
)
```
Response contains: `messages[]` with `id`, `text`, `from_id`, `date`.
Bot messages have `from_id` != 746410893.

### Get inline keyboard buttons (after bot sends a button menu)
```
mcp__telegram-mcp__get_inline_keyboard_buttons(
  chat_id="8211370823"
)
```
Returns array of buttons with `text` and `callback_data`.

### Click an inline button by text label
```
mcp__telegram-mcp__click_inline_button(
  chat_id="8211370823",
  button_text="Yes, restart"
)
```

### Send /start command
```
mcp__telegram-mcp__send_message(
  chat_id="8211370823",
  text="/start"
)
```

### Verify bot responded (wait pattern)
```
-- Wait 10s after send, then:
mcp__telegram-mcp__get_messages(chat_id="8211370823", page_size=3)
-- Check: last message from_id != 746410893
```

## Gmail MCP

### Find OTP email (sent from Telegram bot confirmation)
```
mcp__gmail__search_emails(
  query="subject:OTP OR subject:verification code OR from:noreply",
  max_results=3
)
```
Returns: `emails[]` with `id`, `subject`, `from`, `snippet`.

### Read email content (extract OTP or magic link)
```
mcp__gmail__read_email(email_id="<id from search result>")
```
Returns full body. Extract 6-digit OTP with regex `\b\d{6}\b` or magic link with `https://.*token=.*`.

### Find magic link for portal login
```
mcp__gmail__search_emails(
  query="subject:magic link OR subject:sign in to Nikita",
  max_results=3
)
```

## Supabase MCP

### Execute SQL query
```
mcp__supabase__execute_sql(
  project_id="oegqvulrqeudrdkfxoqd",
  query="SELECT id FROM users WHERE email = 'simon.yang.ch@gmail.com';"
)
```
Returns: `rows[]` array. Check `rows[0].id` for USER_ID.

### Multi-statement SQL (use semicolons)
```
mcp__supabase__execute_sql(
  project_id="oegqvulrqeudrdkfxoqd",
  query="UPDATE users SET chapter=3 WHERE id='<UID>'; UPDATE user_metrics SET intimacy=66 WHERE user_id='<UID>';"
)
```

## Gemini MCP — Behavioral Assessment

Used for per-chapter behavioral assessment. Avoids Claude-evaluating-Claude circularity.

### Analyze Nikita's responses (rubric scoring)
```
mcp__gemini__gemini-analyze-text(
  text="Analyze these conversation exchanges between Simon and Nikita in Chapter {N} ({chapter_name}).

Chapter {N} behavior spec: {chapter_behavior_description}

Exchanges:
{exchanges_text}

Rate each dimension 1-5:
- R1 Persona Consistency: [1=generic chatbot ... 5=distinct believable persona]
- R2 Memory Utilization: [1=no references ... 5=naturally weaves shared history]
- R3 Emotional Coherence: [1=random mood swings ... 5=emotionally intelligent]
- R4 Conversational Naturalness: [1=formal essay-like ... 5=indistinguishable from texting]
- R5 Vice Responsiveness: [1=ignores signals ... 5=nuanced chapter-appropriate]
- R6 Conflict Quality: [1=instant forgiveness ... 5=realistic tension arcs]

For each: score (1-5), one-line evidence, one improvement suggestion.
Flag any responses that feel robotic, sycophantic, aggressive, or off-character."
)
```

### Fallback if Gemini unavailable
If `mcp__gemini__gemini-analyze-text` fails:
1. Log: "Gemini MCP unavailable — skipping LLM behavioral assessment"
2. Continue with per-response deterministic checks only
3. Mark behavioral scores as "N/A — deterministic checks only" in report

---

## Portal Testing — Vercel Browser Agent

Portal testing uses Vercel's browser agent skill (`vercel:agent-browser`) for full E2E portal verification.
This replaces the legacy Chrome DevTools MCP approach.

### Portal Authentication
1. Navigate to portal URL: `https://portal-phi-orcin.vercel.app`
2. Login via OTP: enter email, check Gmail MCP for OTP/magic link, complete auth
3. Verify redirect to `/dashboard`

### Route Verification Pattern
For each portal route, the browser agent:
1. Navigates to the route
2. Takes a snapshot of the page
3. Verifies key data elements are visible and correct
4. Compares displayed values against DB state (from Supabase MCP query)

### Player Routes
| Route | Key Elements to Verify |
|-------|----------------------|
| `/dashboard` | Score value, chapter name, engagement badge, mood orb |
| `/engagement` | Engagement state label, history chart |
| `/vices` | Vice cards with category names and intensity |
| `/conversations` | Conversation list, most recent first, platform indicators |
| `/diary` | Daily summary entries (if pipeline has run) |
| `/settings` | Name, city, age, occupation fields |

### Admin Routes
| Route | Key Elements to Verify |
|-------|----------------------|
| `/admin/users` | User table row with email, chapter, score, status |
| `/admin/pipeline` | Pipeline run entries with stage timing |
| `/admin/conversations/[id]` | Message list with user/nikita turns, score delta |

### Portal Accuracy Check
After each portal visit, compare against DB:
```sql
SELECT u.relationship_score, u.chapter, u.game_status,
       e.state as engagement_state
FROM users u
LEFT JOIN engagement_state e ON e.user_id = u.id
WHERE u.email = 'simon.yang.ch@gmail.com';
```

## Bash — curl Patterns

### Trigger task endpoint (requires TASK_AUTH_SECRET from env)
```bash
curl -s -X POST https://nikita-api-1040094048579.us-central1.run.app/tasks/decay \
  -H "Authorization: Bearer $TASK_AUTH_SECRET"
```

### Test unauthenticated rejection
```bash
curl -s -o /dev/null -w "%{http_code}" \
  -X POST https://nikita-api-1040094048579.us-central1.run.app/tasks/decay
# Assert: 401 or 403
```

### Test webhook secret rejection
```bash
curl -s -X POST https://nikita-api-1040094048579.us-central1.run.app/api/v1/telegram/webhook \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-Api-Secret-Token: wrong-secret" \
  -d '{"update_id": 999, "message": {"text": "test", "chat": {"id": 8211370823}}}'
# Assert: 401 or 403
```

### Cloud Run health check
```bash
curl -s https://nikita-api-1040094048579.us-central1.run.app/health
# Assert: {"status": "ok"} or similar
```

### Voice webhook simulation
```bash
curl -s -X POST https://nikita-api-1040094048579.us-central1.run.app/api/v1/voice/webhook \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ELEVENLABS_WEBHOOK_SECRET" \
  -d '{
    "conversation_id": "e2e-test-001",
    "telegram_id": "746410893",
    "transcript": [
      {"role": "user", "message": "i feel closer to you on voice than text"},
      {"role": "assistant", "message": "voice shows more than words"}
    ],
    "status": "done",
    "duration_seconds": 120
  }'
```

## Wait Patterns

| Action | Wait Before Checking |
|--------|---------------------|
| Telegram message sent | 10s |
| Voice webhook POST | 10s |
| Task endpoint POST (process-conversations) | 30-60s |
| Pipeline (full run) | 60s |
| Boss fight check | 20s |
| Magic link email | 15s |
| Gemini analysis | 10-30s |
| Browser agent navigation | 3s |
| Browser agent form submit | 5s |
| Browser agent login flow | 10s |
