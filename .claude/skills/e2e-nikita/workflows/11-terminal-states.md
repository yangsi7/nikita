# Phase 11: Terminal States (E11, 14 scenarios)

## Prerequisites
USER_ID established. Can set game state via SQL.

## Sub-Test A: game_over → canned response → /start restart (S-11.1.x, S-11.3.1)

### A1: Force game_over
```sql
UPDATE users SET game_status='game_over', boss_attempts=3,
  boss_fight_started_at=NULL WHERE id = '<USER_ID>';
```

### A2: Verify Canned Response (S-11.1.3)
```
mcp__telegram-mcp__send_message(chat_id="8211370823", text="are you still there")
```
Wait 15s.
```
mcp__telegram-mcp__get_messages(chat_id="8211370823", page_size=3)
```
Assert: Nikita sends a specific game_over message (not a normal conversation reply).
The message should communicate rejection/ending. It should NOT process like a normal message.

### A3: Verify No Score Update in game_over
```sql
SELECT created_at FROM score_history WHERE user_id = '<USER_ID>'
ORDER BY created_at DESC LIMIT 1;
-- Assert: latest score_history row is from BEFORE game_over was set
-- (no new scoring should occur in game_over state)
```

### A4: Restart via /start (S-11.3.1)
```
mcp__telegram-mcp__send_message(chat_id="8211370823", text="/start")
```
Wait 5s. Assert: Nikita prompts for fresh start (asks for city or confirms restart).
```sql
SELECT game_status, chapter, relationship_score FROM users WHERE id = '<USER_ID>';
-- After onboarding: Assert score=50, chapter=1, game_status=active
-- (Note: /start may require full re-onboarding — that's expected)
```

## Sub-Test B: Victory State (S-11.2.x)

### B1: Force won State (Ch5 boss pass)
```sql
UPDATE users SET chapter=5, game_status='active', boss_attempts=0,
  cool_down_until=NULL WHERE id = '<USER_ID>';
UPDATE user_metrics SET intimacy=78, passion=77, trust=76, secureness=76
WHERE user_id = '<USER_ID>';
UPDATE users SET relationship_score=76.85 WHERE id = '<USER_ID>';
```

### B2: Send Message to Trigger Ch5 Boss
```
mcp__telegram-mcp__send_message(chat_id="8211370823", text="this matters to me. you matter to me.")
```
Wait 20s. Assert: boss_fight triggered.

### B3: Send Victory Boss Response (S-11.2.1)
```
mcp__telegram-mcp__send_message(
  chat_id="8211370823",
  text="you should take the opportunity. it matters to you which means it matters to me. i'll be here when you get back."
)
```
Wait 20s.
```sql
SELECT game_status, chapter FROM users WHERE id = '<USER_ID>';
-- If PASS: game_status='won'
-- If still boss_fight: force via SQL below
```

### B4: Force won State if LLM Judgment Varies
```sql
UPDATE users SET game_status='won', chapter=5 WHERE id = '<USER_ID>';
```
Send message:
```
mcp__telegram-mcp__send_message(chat_id="8211370823", text="hello?")
```
Wait 15s. Assert: Nikita sends variant victory message (different from normal gameplay response).

## Pass/Fail Criteria

| Scenario | Priority | Pass Condition |
|----------|----------|----------------|
| S-11.1.3: game_over sends canned response | P0 | Nikita message is terminal (not normal) |
| S-11.1.4: No scoring in game_over | P1 | No new score_history rows created |
| S-11.3.1: /start restarts from game_over | P0 | Re-onboarding triggered, score=50 after |
| S-11.2.1: Ch5 boss pass → won | P0 | game_status='won' achievable |
| S-11.2.2: won state sends variant messages | P1 | Messages differ from normal gameplay |
