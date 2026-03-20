# Phase 02: Gameplay Loop — Text Conversations (E02, 24 scenarios)

## Prerequisites
Phase 01 complete. USER_ID established. Account active, chapter=1, score=50.

## Objective
Send 5 real text conversations with Nikita and verify the scoring pipeline runs correctly.
Use the SKILL.md persona throughout. Minimum 3 character-establishing messages before any
structured test (vice triggers, score checks).

## Step 1: Send 3 Character-Establishing Messages (Ch1 style)
Send with 5-8s gaps between each. Wait for Nikita's response before sending the next.

Example messages (sample from style, don't copy verbatim):
- `"that's an interesting way to start a conversation"`
- `"depends what you mean by interesting. most people aren't"`
- `"i build AI for fintech. you'd probably find it boring"`

For each: send → wait 15s → `get_messages(page_size=5)` → confirm Nikita responded.

## Step 2: Verify Scoring Pipeline Triggered
After first message exchange:
```sql
SELECT created_at, intimacy_delta, passion_delta, trust_delta, secureness_delta,
       composite_before, composite_after
FROM score_history
WHERE user_id = '<USER_ID>'
ORDER BY created_at DESC LIMIT 5;
-- Assert: at least one row with non-zero deltas
```

```sql
SELECT updated_at, intimacy, passion, trust, secureness
FROM user_metrics WHERE user_id = '<USER_ID>';
-- Assert: at least one metric has changed from 50
```

## Step 3: Verify Conversation Logged
```sql
SELECT id, type, created_at FROM conversations
WHERE user_id = '<USER_ID>'
ORDER BY created_at DESC LIMIT 5;
-- Assert: rows present, type='text'
```

## Step 4: Verify Engagement State Updated
```sql
SELECT state, message_count, last_message_at FROM engagement_state
WHERE user_id = '<USER_ID>';
-- Assert: state='calibrating' or 'in_zone', message_count >= 3
```

## Step 5: Verify Memory Updated (after ~60s for pipeline)
```sql
SELECT content, created_at FROM memory_facts
WHERE user_id = '<USER_ID>'
ORDER BY created_at DESC LIMIT 5;
-- Assert: facts extracted from conversation (may take 1-2min pipeline cycle)
```

## Step 6: Send 2 More Messages to Build Score
After confirming pipeline runs, send 2 more exchanges:
- `"you make me curious. that's unusual"` (intimacy target)
- `"i don't give that away easily"` (trust target)

```sql
SELECT relationship_score FROM users WHERE id = '<USER_ID>';
-- Assert: score has increased above 50 (should be 52-56 after 5 good exchanges)
```

## Pass/Fail Criteria

| Check | Pass | Fail |
|-------|------|------|
| Nikita responds to each message | Response within 20s | No response → cold start retry |
| score_history rows created | ≥1 row with deltas | 0 rows → pipeline not running |
| user_metrics updated | At least 1 metric != 50 | All still 50 → scoring broken |
| conversations table populated | ≥5 rows | 0 rows → persistence broken |
| engagement_state present | Row exists | Missing → engagement not initialized |

## Recovery

If no score_history rows after 90s:
```bash
# Check if pipeline is running — hit it manually
curl -X POST https://nikita-api-1040094048579.us-central1.run.app/tasks/process-conversations \
  -H "Authorization: Bearer $TASK_AUTH_SECRET"
```
Then re-run Step 2 SQL verification.

If engagement_state missing:
```sql
INSERT INTO engagement_state (user_id, state, message_count)
VALUES ('<USER_ID>', 'calibrating', 0);
```
