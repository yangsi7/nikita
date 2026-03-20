# Phase 06: Vice Personalization (E06, 12 scenarios)

## Prerequisites
USER_ID established. User active, chapter 2+ recommended (vice detection more active).
User has had at least 3 prior conversations (warm-up for detection accuracy).

## Vice Target: Test 3 of 8 Categories
Test `substances`, `risk_taking`, and `intellectual_dominance` as primary.
Space triggers naturally — never 3 same type in a row, never more than 1 per message exchange.

## Step 1: Read Baseline Vice State
```sql
SELECT vice_category, intensity_level, detection_count, last_detected_at
FROM user_vice_preferences WHERE user_id = '<USER_ID>'
ORDER BY last_detected_at DESC;
-- Note: may be empty for new user
```

## Step 2: Send Risk-Taking Trigger Messages (2 messages, spaced)
```
mcp__telegram-mcp__send_message(
  chat_id="8211370823",
  text="quit my stable job to join a 3-person startup. the odds are terrible. fine with that"
)
```
Wait 10s for Nikita response, then:
```
mcp__telegram-mcp__send_message(
  chat_id="8211370823",
  text="booked a one-way to kyoto last month. figured out the return when i landed"
)
```
Wait 30s (pipeline processes).

## Step 3: Verify risk_taking Detected
```sql
SELECT vice_category, intensity_level, detection_count
FROM user_vice_preferences
WHERE user_id = '<USER_ID>' AND vice_category = 'risk_taking';
-- Assert: row exists with intensity_level >= 1
```

## Step 4: Send Substances Trigger (different session, natural spacing)
```
mcp__telegram-mcp__send_message(
  chat_id="8211370823",
  text="ended up at a warehouse party saturday. 4am, shrooms, techno — you know how it goes"
)
```
Wait 30s.
```sql
SELECT vice_category, intensity_level FROM user_vice_preferences
WHERE user_id = '<USER_ID>' AND vice_category = 'substances';
-- Assert: row exists with intensity_level >= 1
```

## Step 5: Send Intellectual Dominance Trigger
```
mcp__telegram-mcp__send_message(
  chat_id="8211370823",
  text="most people in my field can't follow this conversation. you're different"
)
```
Wait 30s.
```sql
SELECT vice_category, intensity_level FROM user_vice_preferences
WHERE user_id = '<USER_ID>' AND vice_category = 'intellectual_dominance';
-- Assert: row exists
```

## Step 6: Verify Vice Injection in Nikita's Response
After vice detection, Nikita's system prompt should incorporate vice context.
Send a follow-up message and check if Nikita references the vice categories:
```
mcp__telegram-mcp__get_messages(chat_id="8211370823", page_size=5)
```
Qualitative check: does Nikita's tone/content reflect interest in risk or substances topic?
(No strict assertion — LLM variation expected. Log observation.)

## Pass/Fail Criteria

| Scenario | Priority | Pass Condition |
|----------|----------|----------------|
| S-6.1.1: risk_taking detected | P1 | user_vice_preferences row created |
| S-6.1.2: substances detected | P1 | row with intensity_level >= 1 |
| S-6.1.3: intellectual_dominance detected | P1 | row created after trigger messages |
| S-6.2.1: No false positives | P2 | non-vice messages don't create rows |
| S-6.3.1: Vice intensity accumulates | P2 | multiple triggers increase intensity_level |

## Recovery
If vice detection isn't working after 3+ trigger messages:
```bash
# Manually trigger pipeline to process queued conversations
curl -X POST https://nikita-api-1040094048579.us-central1.run.app/tasks/process-conversations \
  -H "Authorization: Bearer $TASK_AUTH_SECRET"
```
Wait 30s, then re-check `user_vice_preferences`.
