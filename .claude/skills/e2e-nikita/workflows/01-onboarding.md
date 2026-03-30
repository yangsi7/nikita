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
6-8 digit OTP → OTPHandler.handle() → verify → inline keyboard (Voice/Text)
"onboarding_text" callback → OnboardingHandler.start() → LOCATION prompt
Steps: LOCATION → LIFE_STAGE → SCENE → INTEREST → DRUG_TOLERANCE
  → VENUE_RESEARCH (auto, 10-15s LLM) → SCENARIO_SELECTION → COMPLETE
```

## Step 1: Send /start
```
mcp__telegram-mcp__send_message(chat_id="8211370823", text="/start")
```
Wait 10s. Then:
```
mcp__telegram-mcp__get_messages(chat_id="8211370823", page_size=5)
```
Assert: response contains "email"

## Step 2: Submit Email
```
mcp__telegram-mcp__send_message(chat_id="8211370823", text="simon.yang.ch@gmail.com")
```
Wait 5s. Assert response contains "sent a code" or similar OTP confirmation.

## Step 3: Retrieve OTP from Gmail
```
mcp__gmail__search_emails(query="from:onboarding@silent-agents.com newer_than:5m", maxResults=3)
mcp__gmail__read_email(id="<message_id>")
```
Extract 6-8 digit code from email body. Retry every 10s up to 90s if no email.
If still missing: check `pending_registrations` via Supabase (otp_state should be "pending").

## Step 4: Submit OTP and Start Onboarding
```
mcp__telegram-mcp__send_message(chat_id="8211370823", text="<OTP_CODE>")
```
Wait 5s.
```
mcp__telegram-mcp__list_inline_buttons(chat_id="8211370823")
```
Assert: Single URL button "Enter Nikita's World →" (portal link). No Text/Voice choice — Spec 081 unified onboarding.
Onboarding auto-triggers on next text message. Send any message (e.g., city name) to begin.
Assert: Nikita sends first onboarding question (scene/life_stage).

## Step 5: Answer 5 Profile Questions (2-3s between each)
Send in order — wait for each question to appear before answering:
1. Location: `"Zurich"`
2. Life stage: `"tech"`
3. Scene: `"techno"`
4. Interest: `"building AI"`
5. Drug tolerance: `"4"`

Wait 15s after drug tolerance answer — venue research LLM call takes 10-15s.

## Step 6: Select Scenario
```
mcp__telegram-mcp__get_messages(chat_id="8211370823", page_size=10)
```
Assert: 3 venue scenarios presented.
```
mcp__telegram-mcp__send_message(chat_id="8211370823", text="1")
```
Wait 10s. Assert: backstory generated + first Nikita in-character message received.

## Evidence Queries

```sql
-- Primary verification
SELECT u.id, u.telegram_id, u.relationship_score, u.chapter, u.game_status,
       u.onboarding_status, um.intimacy, um.passion, um.trust, um.secureness
FROM users u
LEFT JOIN user_metrics um ON um.user_id = u.id
WHERE u.id = (SELECT id FROM auth.users WHERE email = 'simon.yang.ch@gmail.com');
-- Assert: score=50, ch=1, game_status=active, onboarding_status=completed, metrics=50

-- Profile check
SELECT city, life_stage, scene, interest, drug_tolerance
FROM user_profiles
WHERE id = (SELECT id FROM auth.users WHERE email = 'simon.yang.ch@gmail.com');
-- Assert: all fields non-null, drug_tolerance present

-- Backstory check
SELECT backstory FROM user_profiles
WHERE id = (SELECT id FROM auth.users WHERE email = 'simon.yang.ch@gmail.com');
-- Assert: non-null, non-empty
```

Store USER_ID from this query — used in ALL subsequent phases.

## Pass/Fail Criteria

| Scenario | Priority | Pass Condition |
|----------|----------|----------------|
| S-1.1.1: /start for new user | P0 | Bot asks for email |
| S-1.1.3: Expired OTP rejected | P1 | See @references for simulation |
| S-1.1.4: Wrong OTP rejected | P1 | Bot says code incorrect |
| S-1.2.1: Complete 5 onboarding questions | P0 | onboarding_status=completed |
| S-1.2.6: Backstory generation | P1 | backstory non-null in user_profiles |
| S-1.2.5: Text vs Voice choice | P1 | Text button pressed, text onboarding starts |

## Recovery
If stuck at any step:
```sql
-- Check current state
SELECT telegram_id, current_step, collected_answers FROM onboarding_states WHERE telegram_id = 746410893;
-- If step is wrong, check: did the message actually arrive? Check messages again.
-- Nuclear option: wipe and restart from Step 1
DELETE FROM onboarding_states WHERE telegram_id = 746410893;
DELETE FROM users WHERE id = '<USER_ID>';
DELETE FROM auth.users WHERE email = 'simon.yang.ch@gmail.com';
DELETE FROM pending_registrations WHERE email = 'simon.yang.ch@gmail.com';
```
