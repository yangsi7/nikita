# Phase 07: Voice Interactions (E07, 24 scenarios)

## Prerequisites
USER_ID established. Cloud Run healthy. ElevenLabs MCP available (optional).
Note: Full voice call testing requires phone access (+41445056044). API endpoint testing does not.

## Step 1: Test Pre-Call Endpoint (S-7.1.1)
```bash
curl -s -X POST https://nikita-api-1040094048579.us-central1.run.app/api/v1/voice/pre-call \
  -H "Content-Type: application/json" \
  -d '{"telegram_id": 746410893}'
```
Assert: Response contains `dynamic_variables` with chapter, relationship_score, chapter_name fields.
```json
{"dynamic_variables": {"chapter": 1, "relationship_score": 50.0, "chapter_name": "Curiosity"}}
```

## Step 2: Test Voice Context Server Tool (S-7.2.1)
```bash
curl -s -X POST https://nikita-api-1040094048579.us-central1.run.app/api/v1/voice/tools/get_context \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ELEVENLABS_WEBHOOK_SECRET" \
  -d '{"telegram_id": "746410893"}'
```
Assert: Returns user context (chapter, metrics, recent topics).

## Step 3: Test Voice Memory Server Tool (S-7.2.2)
```bash
curl -s -X POST https://nikita-api-1040094048579.us-central1.run.app/api/v1/voice/tools/get_memory \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ELEVENLABS_WEBHOOK_SECRET" \
  -d '{"telegram_id": "746410893", "query": "recent conversations"}'
```
Assert: Returns memory facts or empty list — no 500 error.

## Step 4: Test Score Turn Server Tool (S-7.2.3)
```bash
curl -s -X POST https://nikita-api-1040094048579.us-central1.run.app/api/v1/voice/tools/score_turn \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ELEVENLABS_WEBHOOK_SECRET" \
  -d '{"telegram_id": "746410893", "turn": "this call is making me think about things differently", "chapter": 1}'
```
Assert: Returns score deltas (intimacy_delta, passion_delta, trust_delta, secureness_delta).

## Step 5: Test Voice Webhook (Post-Call) (S-7.3.1)
Simulate a post-call webhook with a minimal transcript:
```bash
curl -s -X POST https://nikita-api-1040094048579.us-central1.run.app/api/v1/voice/webhook \
  -H "Content-Type: application/json" \
  -H "ElevenLabs-Signature: <computed_sig>" \
  -d '{
    "conversation_id": "test-conv-123",
    "telegram_id": "746410893",
    "transcript": [
      {"role": "user", "message": "this feels different than texting"},
      {"role": "assistant", "message": "voice reveals things text can hide"}
    ],
    "status": "done"
  }'
```
Assert: 200 response. Then verify:
```sql
SELECT created_at, type FROM conversations
WHERE user_id = '<USER_ID>' AND type = 'voice'
ORDER BY created_at DESC LIMIT 1;
-- Assert: row created with type='voice'
```

## Step 6: Verify Opening Template Selection
```bash
curl -s https://nikita-api-1040094048579.us-central1.run.app/api/v1/voice/opening \
  -H "Content-Type: application/json" \
  -d '{"telegram_id": "746410893"}'
```
Assert: Returns an opening template name (warm_intro, challenge, mysterious, playful, or noir)
and the opening text. Template should vary based on user profile/chapter.

## Pass/Fail Criteria

| Scenario | Priority | Pass Condition |
|----------|----------|----------------|
| S-7.1.1: Pre-call returns dynamic_variables | P0 | dynamic_variables field present |
| S-7.2.1: get_context tool works | P0 | 200 response, chapter/score present |
| S-7.2.2: get_memory tool works | P0 | 200 response, no crash |
| S-7.2.3: score_turn returns deltas | P0 | score delta fields present |
| S-7.3.1: Webhook processes transcript | P0 | conversation row created type='voice' |
| S-7.4.1: Opening template selected | P1 | template name in 5 valid options |
| S-7.3.2: Webhook rejects invalid signature | P0 | 401 or 403 response |

## Note on Phone Testing
Full inbound call test (Twilio → ElevenLabs → server tools) requires calling +41445056044.
This is manual-only. API endpoint tests (Steps 1-6) cover the critical paths without a phone.
