---
description: Full user journey E2E test — onboarding through chapters, boss encounters, game over, restart, victory. Uses Telegram MCP, Gmail MCP, Supabase MCP, Chrome MCP.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Agent, mcp__telegram-mcp__*, mcp__gmail__*, mcp__supabase__*, mcp__claude-in-chrome__*, mcp__ElevenLabs__*, ToolSearch
argument-hint: [full|onboarding|chapter N|gameover|restart|victory|portal|debug-onboarding]
---

# E2E Journey Test

Simulate a complete user journey through the Nikita game using live MCP tools against the production deployment.

## Scope: `$ARGUMENTS` (default: `full`)

| Scope | Phases | Duration |
|-------|--------|----------|
| `full` | 0-7 (complete journey) | ~50 min |
| `onboarding` | 0-1 (registration + profile) | ~10 min |
| `chapter N` | Single chapter boss encounter | ~5 min |
| `gameover` | Phase 4 (3 boss fails) | ~8 min |
| `restart` | Phase 6 (game restart) | ~5 min |
| `victory` | Phase 7 (speed run to win) | ~8 min |
| `portal` | Phase 5 (portal verification) | ~5 min |
| `debug-onboarding` | Diagnose stuck onboarding | ~3 min |

## Test Account

- Email: `simon.yang.ch@gmail.com`
- Phone: `+41787950009`
- Telegram: `@youwontgetmyname` / `@to5meo`

## Pre-Requisites

Load MCP tools before starting:
```
ToolSearch: select:mcp__telegram-mcp__send_message,mcp__telegram-mcp__get_messages
ToolSearch: select:mcp__telegram-mcp__list_inline_buttons,mcp__telegram-mcp__press_inline_button
ToolSearch: select:mcp__supabase__execute_sql
ToolSearch: select:mcp__gmail__search_emails,mcp__gmail__read_email
ToolSearch: select:mcp__claude-in-chrome__tabs_context_mcp
```

## Context Recovery

Read before executing (refresh after compaction):
```
nikita/api/routes/telegram.py:549-771         # Webhook routing chain
nikita/platforms/telegram/commands.py:82-159    # /start handler
nikita/platforms/telegram/otp_handler.py:79-324 # OTP verification
nikita/platforms/telegram/onboarding/handler.py:167-504  # 7-step onboarding
nikita/platforms/telegram/message_handler.py:131-487     # Message gates
nikita/engine/chapters/boss.py:80-394           # Boss state machine
```

## Game Constants

| Ch | Boss Threshold | Decay/hr | Grace Period |
|----|----------------|----------|--------------|
| 1 | 55% | 0.8% | 8h |
| 2 | 60% | 0.6% | 16h |
| 3 | 65% | 0.4% | 24h |
| 4 | 70% | 0.3% | 48h |
| 5 | 75% | 0.2% | 72h |

Composite = intimacy*0.30 + passion*0.25 + trust*0.25 + secureness*0.20. Start: all 50.

---

## Phase 0: Environment Setup

### 0.1 Find bot chat
```
mcp__telegram-mcp__resolve_username("Nikita_my_bot") → BOT_CHAT_ID
```
Fallback: `get_chats()` + search for "Nikita"

### 0.2 Check existing user
```sql
SELECT u.id, u.telegram_id, u.game_status, u.chapter, u.onboarding_status
FROM users u WHERE u.id IN (SELECT id FROM auth.users WHERE email = 'simon.yang.ch@gmail.com');
```

### 0.3 Full wipe (if user exists)
```sql
DELETE FROM users WHERE id = '<USER_ID>';
DELETE FROM auth.users WHERE email = 'simon.yang.ch@gmail.com';
DELETE FROM pending_registrations WHERE email = 'simon.yang.ch@gmail.com';
DELETE FROM onboarding_states WHERE telegram_id = <TG_ID>;
```

### 0.4 Verify clean
```sql
SELECT count(*) FROM auth.users WHERE email = 'simon.yang.ch@gmail.com';
-- Expected: 0
```

---

## Phase 1: Registration + Onboarding

### Webhook Routing Chain (critical knowledge)
```
/start → CommandHandler._handle_start()
  New user → "I'll need your email"
  Game over/won → reset_game_state() + fresh onboarding
  Active → "Welcome back"

Email → RegistrationHandler.handle_email_input()
  → send_otp_code() → "I sent a code"

6-8 digit code → OTPHandler.handle()
  → verify → inline keyboard (Voice/Text)

Callback "onboarding_text" → OnboardingHandler.start()
  → intro + LOCATION prompt

Steps: LOCATION → LIFE_STAGE → SCENE → INTEREST → DRUG_TOLERANCE
  → VENUE_RESEARCH (auto) → SCENARIO_SELECTION → COMPLETE
```

### 1.1 /start → expect email prompt
```
send_message(BOT_CHAT_ID, "/start") → wait 10s
get_messages() → "I don't think we've met... email"
```

### 1.2 Email → OTP sent
```
send_message(BOT_CHAT_ID, "simon.yang.ch@gmail.com") → wait 5s
get_messages() → "I sent a code"
```

### 1.3 Extract OTP from Gmail
```
search_emails(query="from:noreply newer_than:5m", maxResults=3)
read_email(messageId) → extract 6-8 digit code
```
Retry every 10s for up to 60s if no email found.

### 1.4 Submit OTP → choose text onboarding
```
send_message(BOT_CHAT_ID, "<OTP>") → wait 5s
list_inline_buttons() → find "Text" button
press_inline_button(msg_id, button containing "Text")
```

### 1.5 Five profile answers (2-3s gaps)
```
"Zurich"      → LIFE_STAGE prompt
"tech"         → SCENE prompt
"techno"       → INTEREST prompt
"building AI"  → DRUG_TOLERANCE prompt
"4"            → venue research (wait 15s)
```

### 1.6 Scenario selection
```
get_messages() → 3 scenarios
send: "1" → backstory + first Nikita message
```

### 1.7 DB verification
```sql
SELECT u.id, u.relationship_score, u.chapter, u.game_status, u.onboarding_status,
       um.intimacy, um.passion, um.trust, um.secureness
FROM users u LEFT JOIN user_metrics um ON um.user_id = u.id
WHERE u.id = (SELECT id FROM auth.users WHERE email = 'simon.yang.ch@gmail.com');
-- Assert: score=50, ch=1, status=active, onboarding_status=completed, metrics=50
```
Save USER_ID for all subsequent phases.

---

## Phase 2: Chapter 1 — Boss Pass

### 2.1 Send 3 messages (5s gaps)
Natural conversation messages. Ch1 may delay responses (scheduled_events).

### 2.2 Bump score above threshold (55)
```sql
UPDATE user_metrics SET intimacy=60, passion=58, trust=56, secureness=58 WHERE user_id='<UID>';
UPDATE users SET relationship_score=58.10 WHERE id='<UID>';
```

### 2.3 Trigger boss + respond
Send message → wait for boss opening → give strong response → wait 15s

### 2.4 Verify/force ch=2
```sql
SELECT chapter, game_status, boss_attempts FROM users WHERE id='<UID>';
-- Force if needed:
UPDATE users SET chapter=2, game_status='active', boss_attempts=0,
  boss_fight_started_at=NULL, cool_down_until=NULL WHERE id='<UID>';
```

---

## Phase 3: Chapter 2 — Boss Pass

Same pattern: 2 msgs → bump to 62 → boss → pass → force ch=3 if needed.

---

## Phase 4: Chapter 3 — Game Over (3 Boss Fails)

### 4.1 Bump to 66 (above Ch3 threshold 65)
### 4.2 Boss Fail #1: trigger, bad response ("whatever"), force attempts=1
### 4.3 Boss Fail #2: clear cooldown, trigger, bad response, force attempts=2
### 4.4 Boss Fail #3: force game_over
```sql
UPDATE users SET game_status='game_over', boss_attempts=3 WHERE id='<UID>';
```
### 4.5 Verify: send message → expect canned game_over response

---

## Phase 5: Portal Verification

Navigate Chrome MCP to `https://portal-phi-orcin.vercel.app`.
Login via magic link (Gmail MCP). Screenshot dashboard, engagement, vices.

---

## Phase 6: Game Restart

Send `/start` → expect "Let's start fresh" + city question.
Re-onboarding (same answers). Verify score=50, ch=1.

---

## Phase 7: Speed Run to Victory

Fast-forward to Ch4 via SQL → play real messages → bump to 71 → boss pass → ch5 → bump to 76 → final boss → won.

---

## Debug: Stuck Onboarding (`debug-onboarding`)

When onboarding doesn't work, run this diagnostic:

```sql
-- 1. Check auth.users
SELECT id, email, created_at FROM auth.users WHERE email = 'simon.yang.ch@gmail.com';

-- 2. Check pending_registrations
SELECT telegram_id, email, otp_state, otp_attempts, created_at, expires_at
FROM pending_registrations WHERE email = 'simon.yang.ch@gmail.com';

-- 3. Check users table
SELECT id, telegram_id, game_status, onboarding_status, chapter
FROM users WHERE telegram_id = <TG_ID>;

-- 4. Check onboarding_states
SELECT telegram_id, current_step, collected_answers, created_at, updated_at
FROM onboarding_states WHERE telegram_id = <TG_ID>;

-- 5. Check user_profiles
SELECT * FROM user_profiles WHERE id = '<USER_ID>';
```

Common issues:
- **Limbo state**: user exists but no profile → /start triggers fresh start
- **Stale onboarding_states**: step=COMPLETE but no profile → webhook clears it
- **Expired OTP**: pending_registrations.expires_at < now() → /start again
- **No Telegram webhook**: Check Cloud Run logs for errors

---

## Error Recovery

| Error | Recovery |
|-------|----------|
| No bot response (15s) | Cold start — retry once |
| OTP email missing (60s) | Check spam, check pending_registrations |
| Onboarding stuck | Run `debug-onboarding`, check current_step |
| Boss judgment wrong | Force via SQL |
| Rate limited | Wait 60s |
| Cool-down blocking | `UPDATE users SET cool_down_until=NULL` |

## Evidence Collection

At each phase checkpoint:
1. Telegram messages: `get_messages(BOT_CHAT_ID, page=1, page_size=20)`
2. DB state: Run verification SQL
3. Portal: Chrome screenshots
4. Log to `event-stream.md`: `[TIMESTAMP] E2E_JOURNEY: Phase N — PASS/FAIL — details`

## Success Criteria

- [ ] Phase 1: User created, score=50, ch=1, profile complete
- [ ] Phase 2: Ch1 boss passed, advanced to ch=2
- [ ] Phase 3: Ch2 boss passed, advanced to ch=3
- [ ] Phase 4: 3 boss fails → game_over
- [ ] Phase 5: Portal shows correct state
- [ ] Phase 6: Game restarted, score reset to 50
- [ ] Phase 7: Won the game (game_status=won)
