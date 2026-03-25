# Phase 01: Registration & Onboarding (E01, 28 scenarios)

## Prerequisites
Phase 00 complete. Account wiped. MCP tools loaded.

## Routing Chain (Know Before Executing)
```
/start → CommandHandler._handle_start()
  New user → "I'll need your email"
  game_over/won → reset + fresh onboarding
  Active → "Welcome back"

Email → RegistrationHandler.handle_email_input() → send_otp_code()
6-8 digit OTP → OTPHandler.handle() → verify → "You're in!" + inline button "Enter Nikita's World →"
Button URL → Portal /onboarding (cinematic scroll, Spec 081)
Portal onboarding: 5 sections → The Score, The Chapters, The Rules, Who Are You (form), Your Mission (CTA)
Form submit → redirect to t.me/Nikita_my_bot → game_status=active
```

## Step 1: Send /start [method: F]
```
mcp__telegram-mcp__send_message(chat_id="8211370823", text="/start")
```
Wait 10s. Then:
```
mcp__telegram-mcp__get_messages(chat_id="8211370823", page_size=5)
```
Assert: response contains "email"

## Step 2: Submit Email [method: F]
```
mcp__telegram-mcp__send_message(chat_id="8211370823", text="simon.yang.ch@gmail.com")
```
Wait 5s. Assert response contains "sent a code" or similar OTP confirmation.

## Step 3: Retrieve OTP from Gmail [method: F]
```
mcp__gmail__search_emails(query="from:onboarding@silent-agents.com newer_than:5m", maxResults=3)
mcp__gmail__read_email(id="<message_id>")
```
Extract 6-8 digit code from email body. Retry every 10s up to 90s if no email.
If still missing: check `pending_registrations` via Supabase (otp_state should be "pending").

## Step 4: Submit OTP [method: F]
```
mcp__telegram-mcp__send_message(chat_id="8211370823", text="<OTP_CODE>")
```
Wait 5s. Assert: bot responds with "You're in!" (or similar confirmation) and an inline button
with text "Enter Nikita's World" linking to the portal onboarding URL.
```
mcp__telegram-mcp__get_messages(chat_id="8211370823", page_size=5)
```
Extract the portal onboarding URL from the inline button (points to portal `/onboarding`).

## Step 5: Navigate to Portal Onboarding [method: F]
Open the portal onboarding page via agent-browser:
```bash
agent-browser navigate "https://portal-phi-orcin.vercel.app/onboarding"
```
Wait 3s for hydration.
```bash
agent-browser screenshot /tmp/e2e-onboarding-landing.png
```
Assert: Cinematic onboarding page loads with 5 scroll sections visible:
1. **The Score** — explains the 4 relationship metrics
2. **The Chapters** — explains chapter progression 1-5
3. **The Rules** — explains decay, boss encounters, engagement
4. **Who Are You** — profile form with city input + scene selector
5. **Your Mission** — CTA button "Start Talking to Nikita"

## Step 6: Fill Profile Form and Submit [method: F]
Scroll to the "Who Are You" section and fill the profile form:
```bash
agent-browser fill @city-input "Zurich"
```
Select a scene option (e.g., techno):
```bash
agent-browser click @scene-techno
```
Scroll to the final CTA and click:
```bash
agent-browser click @start-talking-cta
```
Wait 5s.
```bash
agent-browser screenshot /tmp/e2e-onboarding-complete.png
```
Assert: Redirect to `t.me/Nikita_my_bot` or a confirmation page indicating onboarding is complete.

**Note on @ref selectors:** The exact `@ref` identifiers depend on the portal's accessibility tree.
Use `agent-browser snapshot` to inspect the current page and find the correct refs for form fields
and buttons before interacting.

## Step 7: Verify DB State [method: A]
Wait 5s after form submission for backend processing.

```sql
-- Primary verification
SELECT u.id, u.telegram_id, u.relationship_score, u.chapter, u.game_status,
       u.onboarding_status, um.intimacy, um.passion, um.trust, um.secureness
FROM users u
LEFT JOIN user_metrics um ON um.user_id = u.id
WHERE u.id = (SELECT id FROM auth.users WHERE email = 'simon.yang.ch@gmail.com');
-- Assert: score=50, ch=1, game_status=active, onboarding_status=completed, metrics=50
```

```sql
-- Profile check
SELECT city, scene FROM user_profiles
WHERE id = (SELECT id FROM auth.users WHERE email = 'simon.yang.ch@gmail.com');
-- Assert: city='Zurich', scene non-null
```

Store USER_ID from this query — used in ALL subsequent phases.

## Evidence Queries

```sql
-- Primary verification (same as Step 7)
SELECT u.id, u.telegram_id, u.relationship_score, u.chapter, u.game_status,
       u.onboarding_status, um.intimacy, um.passion, um.trust, um.secureness
FROM users u
LEFT JOIN user_metrics um ON um.user_id = u.id
WHERE u.id = (SELECT id FROM auth.users WHERE email = 'simon.yang.ch@gmail.com');
-- Assert: score=50, ch=1, game_status=active, onboarding_status=completed, metrics=50

-- Profile check
SELECT city, scene FROM user_profiles
WHERE id = (SELECT id FROM auth.users WHERE email = 'simon.yang.ch@gmail.com');
-- Assert: city and scene non-null
```

## Pass/Fail Criteria

| Scenario | Priority | Pass Condition |
|----------|----------|----------------|
| S-1.1.1: /start for new user | P0 | Bot asks for email |
| S-1.1.2: Email accepted, OTP sent | P0 | Bot confirms code sent |
| S-1.1.3: Expired OTP rejected | P1 | See @references for simulation |
| S-1.1.4: Wrong OTP rejected | P1 | Bot says code incorrect |
| S-1.2.1: OTP verified, portal link shown | P0 | "You're in!" + portal URL button |
| S-1.2.2: Portal onboarding page loads | P0 | 5 cinematic sections visible |
| S-1.2.3: Profile form submission | P0 | City + scene submitted, redirect to Telegram |
| S-1.2.4: DB state after onboarding | P0 | game_status=active, score=50, onboarding_status=completed |
| S-1.2.5: Profile data persisted | P1 | city and scene non-null in user_profiles |

## Recovery
If stuck at any step:
```sql
-- Check current state
SELECT telegram_id, game_status, onboarding_status FROM users
WHERE id = (SELECT id FROM auth.users WHERE email = 'simon.yang.ch@gmail.com');
-- If onboarding stuck, check portal logs or agent-browser screenshot for errors.
-- Nuclear option: wipe and restart from Step 1
DELETE FROM onboarding_states WHERE telegram_id = 746410893;
DELETE FROM users WHERE id = '<USER_ID>';
DELETE FROM auth.users WHERE email = 'simon.yang.ch@gmail.com';
DELETE FROM pending_registrations WHERE email = 'simon.yang.ch@gmail.com';
```
