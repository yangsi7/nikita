# Phase 12: Cross-Platform (E12, 12 scenarios)

## Prerequisites
Phase 01 complete (real onboarding done). USER_ID established, user active.
Tests that text and voice scoring both update shared metrics.

## Step 1: Establish Text Baseline Score
After onboarding, send 2 text messages and verify scoring occurred:
```sql
SELECT relationship_score, intimacy, passion, trust, secureness
FROM users u JOIN user_metrics um ON um.user_id = u.id
WHERE u.id = '<USER_ID>';
-- Record baseline values
```

## Step 2: Simulate Voice Scoring via Webhook
Simulate a completed voice call with the post-call webhook:
```bash
curl -s -X POST https://nikita-api-1040094048579.us-central1.run.app/api/v1/voice/webhook \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ELEVENLABS_WEBHOOK_SECRET" \
  -d '{
    "conversation_id": "cross-platform-test-001",
    "telegram_id": "746410893",
    "transcript": [
      {"role": "user", "message": "i feel closer to you on voice than text"},
      {"role": "assistant", "message": "voice shows more than words"},
      {"role": "user", "message": "honest answer? this is different. i wasn'\''t expecting to feel something"}
    ],
    "status": "done",
    "duration_seconds": 180
  }'
```
Wait 10s.

## Step 3: Verify Voice Score Updated Shared Metrics
```sql
SELECT relationship_score, intimacy, passion, trust, secureness
FROM users u JOIN user_metrics um ON um.user_id = u.id
WHERE u.id = '<USER_ID>';
-- Assert: relationship_score increased from baseline (voice scoring applied)
```
```sql
SELECT source_platform, composite_before, composite_after, recorded_at
FROM score_history WHERE user_id = '<USER_ID>'
ORDER BY recorded_at DESC LIMIT 3;
-- Assert: row with source_platform='voice' present
```

## Step 4: Verify Memory Shared Across Platforms (S-12.3.1)
After voice call, send a text message that references the call:
```
mcp__telegram-mcp__send_message(
  chat_id="8211370823",
  text="still thinking about what we talked about on the call"
)
```
Wait 15s.
```
mcp__telegram-mcp__get_messages(chat_id="8211370823", page_size=3)
```
Qualitative check: does Nikita's text response reference the voice conversation?
(May require pipeline processing — wait 60s and check memory_facts if needed)

## Step 5: Verify Conversation History Shows Both Platforms
```sql
SELECT type, created_at FROM conversations
WHERE user_id = '<USER_ID>'
ORDER BY created_at DESC LIMIT 10;
-- Assert: both 'text' and 'voice' type rows present
```

## Pass/Fail Criteria

| Scenario | Priority | Pass Condition |
|----------|----------|----------------|
| S-12.1.1: Voice webhook updates score | P0 | relationship_score increases after voice webhook |
| S-12.1.2: Source platform tracked | P1 | score_history row has source_platform='voice' |
| S-12.2.1: Text score also updates shared metrics | P0 | Both platforms write to same user_metrics table |
| S-12.3.1: Memory shared across platforms | P1 | memory_facts include voice context (qualitative) |
| S-12.4.1: Both conversation types in history | P1 | type='text' and type='voice' rows exist |
