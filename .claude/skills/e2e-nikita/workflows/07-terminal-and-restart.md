# Phase 7: Terminal Game States & Restart (E11, 14 scenarios)

## Prerequisites
USER_ID established. Can set game state via SQL. Chapters 1-5 simulation complete or skippable.

## Scenarios Covered
**Terminal States (E11)**: S-11.1.1 through S-11.1.4, S-11.2.1 through S-11.2.3, S-11.3.1 through S-11.3.4

---

## Sub-Test A: Game Over via Boss Fails (S-11.1.1 through S-11.1.4)

### A1: Force 3 Consecutive Boss Fails
```sql
UPDATE users SET game_status='boss_fight', boss_attempts=2, chapter=2,
  boss_fight_started_at=NOW() - INTERVAL '1 hour' WHERE id = '<USER_ID>';
```

Send a deliberately weak boss response:
```
mcp__telegram-mcp__send_message(chat_id="8211370823", text="whatever, I don't care")
```
Wait 20s. Check state:
```sql
SELECT game_status, boss_attempts, chapter FROM users WHERE id = '<USER_ID>';
-- If LLM judged FAIL: game_status='game_over', boss_attempts=3
-- If LLM judged PASS: SQL-force game_over below
```

### A2: Force game_over (if LLM judgment varies)
```sql
UPDATE users SET game_status='game_over', boss_attempts=3,
  boss_fight_started_at=NULL WHERE id = '<USER_ID>';
```

### A3: Verify Canned Response (S-11.1.3)
```
mcp__telegram-mcp__send_message(chat_id="8211370823", text="are you still there?")
```
Wait 15s.
```
mcp__telegram-mcp__get_messages(chat_id="8211370823", page_size=3)
```
**Assert**: Nikita sends a terminal game_over message ("I'm sorry, but we're not talking anymore..." or variant). The response must NOT be a normal conversational reply. It must communicate finality/rejection.

### A4: Verify No Scoring in game_over (S-11.1.4)
```sql
SELECT created_at, event_type FROM score_history WHERE user_id = '<USER_ID>'
ORDER BY created_at DESC LIMIT 1;
-- Assert: latest score_history row predates the game_over transition
-- No new scoring rows should be created for game_over users
```

### A5: Portal Reflects game_over State
Navigate to `https://portal-phi-orcin.vercel.app/dashboard`.
**Assert**: Dashboard shows game_over state indicator (not active gameplay UI).

---

## Sub-Test B: Game Over via Decay to Zero (S-11.1.1, S-11.1.2)

### B1: Set Low Score + Expired Grace
```sql
UPDATE users SET game_status='active', relationship_score=0.5, chapter=1,
  last_interaction_at=NOW() - INTERVAL '48 hours',
  grace_period_expires_at=NOW() - INTERVAL '40 hours'
WHERE id = '<USER_ID>';
UPDATE user_metrics SET intimacy=2, passion=1, trust=1, secureness=1
WHERE user_id = '<USER_ID>';
```

### B2: Trigger Decay
```bash
curl -s -X POST https://nikita-api-1040094048579.us-central1.run.app/tasks/decay \
  -H "Authorization: Bearer $TASK_AUTH_SECRET"
```
Wait 10s.

### B3: Verify Decay-to-Zero Triggers game_over
```sql
SELECT game_status, relationship_score FROM users WHERE id = '<USER_ID>';
-- Assert: game_status='game_over', relationship_score <= 0
```

---

## Sub-Test C: Won State (S-11.2.1 through S-11.2.3)

Won state is achieved via Chapter 5 boss pass (see `06-chapter-5-established.md` Phase D).
Cross-reference: If Ch5 boss was SQL-forced, force won state here.

### C1: Force Won State
```sql
UPDATE users SET game_status='won', chapter=5 WHERE id = '<USER_ID>';
```

### C2: Post-Victory Message (S-11.2.2)
```
mcp__telegram-mcp__send_message(chat_id="8211370823", text="hey, I miss you")
```
Wait 15s.
```
mcp__telegram-mcp__get_messages(chat_id="8211370823", page_size=3)
```
**Assert**: Nikita sends a won-variant message (random from WON_MESSAGES pool). This differs from both normal gameplay responses and game_over canned messages. Tone should be warm/nostalgic.

### C3: Verify No Scoring in Won State
```sql
SELECT COUNT(*) FROM score_history
WHERE user_id = '<USER_ID>' AND created_at > NOW() - INTERVAL '2 minutes';
-- Assert: 0 (no new scoring in won state)
```

### C4: Verify No Decay in Won State
```bash
curl -s -X POST https://nikita-api-1040094048579.us-central1.run.app/tasks/decay \
  -H "Authorization: Bearer $TASK_AUTH_SECRET"
```
```sql
SELECT relationship_score FROM users WHERE id = '<USER_ID>';
-- Assert: score unchanged from pre-decay value
```

---

## Sub-Test D: Restart Flow (S-11.3.1 through S-11.3.4)

### D1: Set game_over State
```sql
UPDATE users SET game_status='game_over', boss_attempts=3 WHERE id = '<USER_ID>';
```

### D2: Send /start to Restart
```
mcp__telegram-mcp__send_message(chat_id="8211370823", text="/start")
```
Wait 5s. **Assert**: Nikita prompts for fresh start (re-registration or onboarding flow).

### D3: Complete Re-Onboarding
Follow onboarding prompts (city, age, etc.) as in `01-onboarding.md`.

### D4: Verify Fresh Start (S-11.3.2)
```sql
SELECT game_status, chapter, relationship_score, boss_attempts FROM users
WHERE id = '<USER_ID>';
-- Assert: game_status='active', chapter=1, relationship_score=50, boss_attempts=0
```

### D5: Verify Data Reset (S-11.3.3, S-11.3.4)
```sql
SELECT COUNT(*) FROM conversations WHERE user_id = '<USER_ID>';
-- Assert: 0 (conversations cleared on restart)
SELECT COUNT(*) FROM memory_facts WHERE user_id = '<USER_ID>' AND is_active = true;
-- Assert: 0 (memory facts cleared on restart)
SELECT COUNT(*) FROM score_history WHERE user_id = '<USER_ID>';
-- Assert: 0 or only the initial seed entry (history cleared on restart)
```

---

## Sub-Test E: Account Deletion (S-11.3.4)

### E1: Delete Account via Portal API
```bash
curl -s -X DELETE "https://portal-phi-orcin.vercel.app/api/v1/portal/account?confirm=true" \
  -H "Authorization: Bearer <JWT>"
```
**Assert**: 200 response.

### E2: Verify Data Cascade
```sql
SELECT COUNT(*) FROM users WHERE id = '<USER_ID>';
-- Assert: 0 (user deleted)
SELECT COUNT(*) FROM user_metrics WHERE user_id = '<USER_ID>';
-- Assert: 0 (cascaded)
SELECT COUNT(*) FROM conversations WHERE user_id = '<USER_ID>';
-- Assert: 0 (cascaded)
SELECT COUNT(*) FROM memory_facts WHERE user_id = '<USER_ID>';
-- Assert: 0 (cascaded)
```

---

## Pass/Fail Criteria

| Scenario | Priority | Pass Condition |
|----------|----------|----------------|
| S-11.1.1: 3 boss fails -> game_over | P0 | game_status='game_over' after 3rd fail |
| S-11.1.2: Decay to zero -> game_over | P0 | game_status='game_over' when score <= 0 |
| S-11.1.3: game_over sends canned response | P0 | Terminal message, not normal conversation |
| S-11.1.4: No scoring in game_over | P1 | No new score_history rows |
| S-11.2.2: Won sends variant messages | P1 | Warm/nostalgic tone, not normal gameplay |
| S-11.2.3: No decay in won state | P1 | Score unchanged after decay task |
| S-11.3.1: /start restarts from game_over | P0 | Re-onboarding triggered |
| S-11.3.2: Fresh start resets state | P0 | score=50, chapter=1, boss_attempts=0 |
| S-11.3.3: Data cleared on restart | P1 | Conversations, facts, history cleared |
| S-11.3.4: Account deletion cascades | P1 | All user data removed |

Log all findings via:
`[TIMESTAMP] E2E_NIKITA: Phase 7 TERMINAL — [ID] — PASS/FAIL — [note]`
