# MCP Tool Patterns Reference — E2E Nikita

## Load All Required Tools (run at session start)

```
ToolSearch: select:mcp__telegram-mcp__send_message,mcp__telegram-mcp__get_messages
ToolSearch: select:mcp__telegram-mcp__get_inline_keyboard_buttons,mcp__telegram-mcp__click_inline_button
ToolSearch: select:mcp__gmail__search_emails,mcp__gmail__read_email
ToolSearch: select:mcp__supabase__execute_sql
ToolSearch: select:mcp__chrome-devtools__navigate_page,mcp__chrome-devtools__take_screenshot
ToolSearch: select:mcp__chrome-devtools__evaluate_script,mcp__chrome-devtools__click
ToolSearch: select:mcp__chrome-devtools__fill
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

## Chrome DevTools MCP

### Navigate to portal URL
```
mcp__chrome-devtools__navigate_page(url="https://portal-phi-orcin.vercel.app")
-- Wait 3s for hydration before next action
mcp__chrome-devtools__take_screenshot()
```

### Navigate to specific portal route
```
mcp__chrome-devtools__navigate_page(url="https://portal-phi-orcin.vercel.app/dashboard")
```

### Take screenshot (verify page state)
```
mcp__chrome-devtools__take_screenshot()
```

### Check current URL (verify redirect)
```
mcp__chrome-devtools__evaluate_script(script="window.location.href")
```

### Get page text (verify content loaded)
```
mcp__chrome-devtools__evaluate_script(script="document.body.innerText.substring(0, 500)")
```

### Fill form field
```
mcp__chrome-devtools__fill(selector="input[type='email']", value="simon.yang.ch@gmail.com")
```

### Click element
```
mcp__chrome-devtools__click(selector="button[type='submit']")
```

### Check for DOM errors
```
mcp__chrome-devtools__evaluate_script(
  script="Array.from(document.querySelectorAll('[class*=error]')).map(e=>e.textContent).join(', ')"
)
```

### Check network failures (4xx/5xx)
```
mcp__chrome-devtools__evaluate_script(
  script="performance.getEntriesByType('resource').filter(r=>r.responseStatus>=400).map(r=>({url:r.name,status:r.responseStatus}))"
)
```

### Check JS console errors
```
mcp__chrome-devtools__evaluate_script(
  script="window.__e2eErrors || 'no errors captured'"
)
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
| Portal navigation | 3s (hydration) |
| Pipeline (full run) | 60s |
| Boss fight check | 20s |
| Magic link email | 15s |
