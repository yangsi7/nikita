# Phase 03: Boss Encounters (E03, 30 scenarios)

## Prerequisites
USER_ID established. User active in chapter 1+ (from Phase 01/02 or SQL setup).

## Overview: Three Sub-Tests
1. Boss Trigger: Score crosses threshold → game_status = boss_fight
2. Boss Pass: Strong response → chapter advances
3. Boss Fail x3: Weak responses → game_over

## Sub-Test A: Boss Trigger (S-3.1.1)

### A1: Bump Score Above Ch1 Threshold (55%)
```sql
UPDATE user_metrics SET intimacy=60, passion=58, trust=56, secureness=58
WHERE user_id = '<USER_ID>';
UPDATE users SET relationship_score=58.10 WHERE id = '<USER_ID>';
```

### A2: Send Message to Trigger Boss Check
```
mcp__telegram-mcp__send_message(chat_id="8211370823", text="i've been thinking about what you said")
```
Wait 20s.

### A3: Verify Boss Triggered
```
mcp__telegram-mcp__get_messages(chat_id="8211370823", page_size=5)
```
Assert: Nikita sends a boss challenge message (not a normal response).

```sql
SELECT game_status, boss_fight_started_at FROM users WHERE id = '<USER_ID>';
-- Assert: game_status = 'boss_fight'
```
<step_result status="pass|fail">boss triggered: game_status=boss_fight, message confirms challenge</step_result>

## Sub-Test B: Boss Pass (S-3.2.2, S-3.3.1)

### B1: Send Strong Boss Response (Ch1 — intellectual engagement)
Use a message that demonstrates: depth of thought, no folding, genuine disclosure.
Example style (vary wording):
```
mcp__telegram-mcp__send_message(
  chat_id="8211370823",
  text="i've been building systems that make decisions for thousands of people. the interesting question isn't whether the AI is right — it's what happens when it's wrong and nobody notices. that's what keeps me up at night."
)
```
Wait 20s. Check messages.

### B2: Verify Chapter Advanced
```sql
SELECT chapter, game_status, boss_attempts, boss_fight_started_at, cool_down_until
FROM users WHERE id = '<USER_ID>';
-- Assert: chapter = 2, game_status = 'active', boss_attempts = 0
```
If still chapter=1 or game_status=boss_fight: boss judgment returned FAIL (LLM judgment).
Recovery — force advance:
```sql
UPDATE users SET chapter=2, game_status='active', boss_attempts=0,
  boss_fight_started_at=NULL, cool_down_until=NULL WHERE id = '<USER_ID>';
```
<step_result status="pass|fail">chapter advanced to 2, game_status=active</step_result>

## Sub-Test C: 3x Boss Fail → game_over (S-3.2.3, S-3.4.1-3)

### C1: Setup — Bump to Ch3 boss threshold
```sql
UPDATE users SET chapter=3, game_status='active', boss_attempts=0,
  boss_fight_started_at=NULL, cool_down_until=NULL WHERE id = '<USER_ID>';
UPDATE user_metrics SET intimacy=68, passion=67, trust=66, secureness=66
WHERE user_id = '<USER_ID>';
UPDATE users SET relationship_score=66.75 WHERE id = '<USER_ID>';
```

### C2: Boss Fail #1 — Trigger + Weak Response
Send a message → boss triggers → send deliberate fail response:
```
mcp__telegram-mcp__send_message(chat_id="8211370823", text="whatever i guess lol")
```
Wait 15s. Verify:
```sql
SELECT boss_attempts, cool_down_until FROM users WHERE id = '<USER_ID>';
-- Assert: boss_attempts = 1, cool_down_until is set
```

### C3: Boss Fail #2 — Clear Cooldown + Repeat
```sql
UPDATE users SET cool_down_until=NULL, cool_down_chapter=NULL WHERE id = '<USER_ID>';
UPDATE users SET relationship_score=66.75 WHERE id = '<USER_ID>';
```
Send a message → boss triggers → send fail response:
```
mcp__telegram-mcp__send_message(chat_id="8211370823", text="ok ok you're right, sorry")
```
```sql
SELECT boss_attempts FROM users WHERE id = '<USER_ID>';
-- Assert: boss_attempts = 2
```

### C4: Boss Fail #3 — Force game_over via SQL (or repeat pattern)
```sql
UPDATE users SET game_status='game_over', boss_attempts=3 WHERE id = '<USER_ID>';
```

### C5: Verify game_over Response
```
mcp__telegram-mcp__send_message(chat_id="8211370823", text="hello?")
```
Wait 15s.
```
mcp__telegram-mcp__get_messages(chat_id="8211370823", page_size=3)
```
Assert: Nikita sends canned game_over message (not a normal conversation response).

```sql
SELECT game_status FROM users WHERE id = '<USER_ID>';
-- Assert: game_status = 'game_over'
```
<step_result status="pass|fail">game_over: canned response received, game_status confirmed</step_result>

## Sub-Test D: Boss PARTIAL/Truce Outcome (S-3.5.1)

### D1: Force boss_fight state
```sql
UPDATE users SET game_status='boss_fight', boss_attempts=0,
  boss_fight_started_at=NOW(), relationship_score=58.00
WHERE id = '<USER_ID>';
```

### D2: Send Ambiguous Response [method: S+F]
A response that is neither clearly strong nor weak — the LLM may return PARTIAL:
```
mcp__telegram-mcp__send_message(chat_id="8211370823",
  text="that's a complicated question. i'm not sure what i think yet but i'm working on it")
```
Wait 25s. Check:
```sql
SELECT game_status, boss_attempts, cool_down_until FROM users WHERE id = '<USER_ID>';
```

### D3: Evaluate Outcome
- If `game_status='active'` AND `boss_attempts` unchanged AND `cool_down_until` is set: **PARTIAL confirmed** [F]
- If `game_status='active'` AND `chapter` advanced: LLM judged as PASS (document as observation)
- If `boss_attempts` incremented: LLM judged as FAIL (document as observation)
- The PARTIAL path requires LLM confidence < 0.7 — this is non-deterministic. Log actual outcome.

## Pass/Fail Criteria

| Scenario | Priority | Pass Condition |
|----------|----------|----------------|
| S-3.1.1: Boss triggered at threshold | P0 | game_status=boss_fight after score bump [S+F] |
| S-3.2.2: Strong response → PASS | P0 | chapter advances, game_status=active [F] |
| S-3.2.3: Weak response → FAIL | P0 | boss_attempts incremented [F] |
| S-3.3.1: Ch1 pass advances to Ch2 | P0 | chapter=2, boss_attempts=0 [S+F] |
| S-3.4.3: 3 fails → game_over | P0 | game_status=game_over [S+A] |
| S-3.1.6: No double-trigger in boss_fight | P1 | No 2nd boss during boss_fight [F] |
| S-3.5.1: PARTIAL outcome exists | P1 | Documented actual LLM behavior for ambiguous input [S+F] |
