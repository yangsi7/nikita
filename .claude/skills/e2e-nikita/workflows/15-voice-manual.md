# Workflow 15: Voice Manual E2E

**Scope**: Voice-specific end-to-end scenarios covering all 6 API endpoints, 4 server tools, voice onboarding,
outbound scheduling, and background jobs. Supplements existing S-07.* and S-12.* scenarios with depth tests
and previously unverified paths.

## Scenarios Covered

**Phase A — Availability + Signed URL**: S-15.1.1, S-15.1.2, S-15.1.3, S-15.1.4, S-15.1.5
**Phase B — Opening Selector**: S-15.2.1, S-15.2.2, S-15.2.3, S-15.2.4
**Phase C — Mid-Call Server Tools**: S-15.3.1, S-15.3.2, S-15.3.3, S-15.3.4, S-15.3.5, S-15.3.6, S-15.3.7
**Phase D — Post-Call Scoring**: S-15.4.1, S-15.4.2, S-15.4.3, S-15.4.4, S-15.4.5, S-15.4.6, S-15.4.7, S-15.4.8
**Phase E — Summaries + Cross-Platform**: S-15.5.1, S-15.5.2, S-15.5.3, S-15.5.4
**Phase F — Voice Onboarding** (in `15b`): S-15.6.1, S-15.6.2, S-15.6.3, S-15.6.4, S-15.6.5, S-15.6.6, S-15.6.7
**Phase G — Outbound Delivery** (in `15b`): S-15.7.1, S-15.7.2, S-15.7.3, S-15.7.4, S-15.7.5
**Phase H — Background Jobs** (in `15b`): S-15.8.1, S-15.8.2, S-15.8.3, S-15.8.4, S-15.8.5

**Required MCP Tools**:
- `mcp__supabase__execute_sql` (project_id: `oegqvulrqeudrdkfxoqd`)
- Bash (`curl`) for API calls against `https://nikita-api-1040094048579.us-central1.run.app`
- ElevenLabs dashboard (manual, for call verification and session cleanup)
- `mcp__telegram-mcp__get_messages` (for onboarding handoff verification, Phase F)

**Estimated Duration**: 90-120 minutes for full run. Phase F (onboarding) requires live ElevenLabs call.

**Constants**:
- `API=https://nikita-api-1040094048579.us-central1.run.app`
- `chat_id=8211370823`, `telegram_id=746410893`
- `TASK_AUTH_SECRET` — from Cloud Run env

**Reference**: See `testing-guide-autonomous.md` for SQL observability patterns.
See `16-voice-audit-summary.md` for module dependency map and gap rationale.

---

## Prerequisites: Data Cleanup

```sql
-- FK-safe wipe (CASCADE handles all child tables)
DELETE FROM users WHERE email = 'simon.yang.ch@gmail.com';
DELETE FROM pending_registrations WHERE telegram_id = 746410893;
DELETE FROM onboarding_states WHERE telegram_id = 746410893;

-- Verify clean
SELECT COUNT(*) FROM users WHERE email = 'simon.yang.ch@gmail.com';      -- Assert: 0
SELECT COUNT(*) FROM pending_registrations WHERE telegram_id = 746410893; -- Assert: 0
```

ElevenLabs cleanup: delete any leftover onboarding conversation history via ElevenLabs dashboard manually.

Create an active Ch3 user for Phases A–E (SQL-assisted, skip text onboarding):
```sql
-- Use the active-user INSERT template from references/sql-queries.md#create-active-user
-- Set chapter=3, relationship_score=62.00
-- Store USER_ID for all subsequent queries
```

SQL setup for contrasting drug_tolerance profiles (used in Phase B):
```sql
-- Profile LOW (warm_intro path)
UPDATE user_profiles SET drug_tolerance = 1 WHERE id = '<USER_ID>';

-- Profile HIGH (noir path) — run between S-15.2.1 and S-15.2.2
UPDATE user_profiles SET drug_tolerance = 5, social_scene = 'techno' WHERE id = '<USER_ID>';

-- Reset after Phase B
UPDATE user_profiles SET drug_tolerance = 3, social_scene = NULL WHERE id = '<USER_ID>';
```

---

## Phase A: Voice Availability + Signed URL (~5 scenarios)

### S-15.1.1: GET /availability at Ch1 — probabilistic low [NEW]
- Priority: P1
- Method: A (API)
- Preconditions: User at chapter=1
- Steps:
  1. `UPDATE users SET chapter=1 WHERE id='<USER_ID>';`
  2. Call `GET /api/v1/voice/availability/<USER_ID>` ten times in a loop
  3. Count `available=true` responses
- Pass criteria: Between 0 and 4 true results (10% rate — expect 0-4/10)
- SQL verify: `SELECT chapter FROM users WHERE id='<USER_ID>';` — Assert chapter=1
- Note: Probabilistic; retry if result is implausible (all true or all false)

### S-15.1.2: GET /availability at Ch3 — probabilistic mid [NEW]
- Priority: P1
- Method: A (API)
- Preconditions: User at chapter=3
- Steps:
  1. `UPDATE users SET chapter=3 WHERE id='<USER_ID>';`
  2. Call `GET /api/v1/voice/availability/<USER_ID>` ten times
  3. Count `available=true` responses
- Pass criteria: Between 5 and 10 true results (80% rate — expect 6-10/10)
- SQL verify: `SELECT chapter FROM users WHERE id='<USER_ID>';` — Assert chapter=3

### S-15.1.3: GET /availability at Ch5 — near-certain [NEW]
- Priority: P1
- Method: A (API)
- Preconditions: User at chapter=5
- Steps:
  1. `UPDATE users SET chapter=5 WHERE id='<USER_ID>';`
  2. Call `GET /api/v1/voice/availability/<USER_ID>` ten times
- Pass criteria: 8 or more true results (95% rate)
- SQL verify: `SELECT chapter FROM users WHERE id='<USER_ID>';`

### S-15.1.4: Unavailable response contains in-character excuse [NEW]
- Priority: P2
- Method: A (API)
- Preconditions: User at chapter=1 (low availability maximizes unavailable responses)
- Steps:
  1. Loop GET /availability until `available=false` returned
  2. Inspect `reason` field in response JSON
- Pass criteria: `reason` is a non-empty string, not a technical error message (e.g., "Nikita is busy" or similar from UNAVAILABILITY_REASONS)

### S-15.1.5: GET /signed-url returns valid ElevenLabs signed URL [NEW]
- Priority: P0
- Method: A (API)
- Preconditions: User at chapter=3 (80% available, reset if needed)
- Steps:
  1. `UPDATE users SET chapter=3 WHERE id='<USER_ID>';`
  2. `GET /api/v1/voice/signed-url/<USER_ID>` with valid JWT auth header
  3. Inspect response fields
- Pass criteria: Response contains `signed_url` (starts with `wss://`), `signed_token` (non-empty string), `dynamic_variables` (object), `conversation_config_override` (object or null)
- Note: If chapter availability check returns 403, retry or SQL-force `chapter=3`.

---

## Phase B: Opening Selector (~4 scenarios)

### S-15.2.1: warm_intro template selected for low drug_tolerance [EXISTING: S-07.5.2]
- Priority: P1
- Method: A (API)
- Preconditions: `drug_tolerance=1`, `social_scene=NULL`
- Steps:
  1. `POST /api/v1/voice/initiate` with `{"user_id": "<USER_ID>"}`
  2. Inspect `conversation_config_override.agent.first_message` in response
- Pass criteria: `opening_id` in response or first_message text matches warm/standard tone (not noir/challenge)
- SQL setup: `UPDATE user_profiles SET drug_tolerance=1, social_scene=NULL WHERE id='<USER_ID>';`

### S-15.2.2: noir template selected for high drug_tolerance + techno scene [EXISTING: S-07.5.3]
- Priority: P1
- Method: A (API)
- Preconditions: `drug_tolerance=5`, `social_scene='techno'`
- Steps:
  1. `POST /api/v1/voice/initiate` with `{"user_id": "<USER_ID>"}`
  2. Inspect first_message or opening metadata in response
- Pass criteria: first_message reflects higher-darkness tone (noir/challenge register) vs warm_intro
- SQL setup: `UPDATE user_profiles SET drug_tolerance=5, social_scene='techno' WHERE id='<USER_ID>';`

### S-15.2.3: TTS settings in initiate response match chapter constants [NEW]
- Priority: P1
- Method: A (API)
- Preconditions: User at chapter=3 with `drug_tolerance=3` (reset to defaults)
- Steps:
  1. `UPDATE users SET chapter=3 WHERE id='<USER_ID>';`
  2. `POST /api/v1/voice/initiate` with `{"user_id": "<USER_ID>"}`
  3. Inspect `tts_settings` field in response
- Pass criteria: `stability=0.42`, `similarity_boost=0.80`, `speed=0.98` (matches `CHAPTER_TTS_SETTINGS[3]`)

### S-15.2.4: Opening line behavioral check via Gemini [NEW]
- Priority: P2
- Method: G (Gemini behavioral)
- Preconditions: Both profiles tested (low and high darkness)
- Steps:
  1. Collect first_message from S-15.2.1 (warm) and S-15.2.2 (noir)
  2. Submit both to `mcp__gemini__gemini-analyze-text` with rubric: R1 (persona consistency), R5 (vice responsiveness)
- Pass criteria: Warm opening scores R1 >= 3 for approachable tone; noir opening scores R5 >= 3 for vice awareness

---

## Phase C: Mid-Call Server Tools (~7 scenarios)

Use `POST /api/v1/voice/server-tool` for all scenarios. Obtain a `signed_token` by calling `/initiate` first and extracting the token from the response.

```bash
TOKEN=$(curl -s -X POST $API/api/v1/voice/initiate \
  -H "Content-Type: application/json" \
  -d '{"user_id":"<USER_ID>"}' | jq -r '.signed_token')
```

### S-15.3.1: get_context returns 200 + context JSON [EXISTING: S-07.1.4]
- Priority: P0
- Method: A (API)
- Steps:
  1. `POST /api/v1/voice/server-tool` with `{"tool_name":"get_context","signed_token":"$TOKEN","data":{}}`
- Pass criteria: HTTP 200, `success=true`, response contains `chapter`, `relationship_score`, `engagement_state`
- SQL verify: `SELECT chapter, relationship_score FROM users WHERE id='<USER_ID>';` — values match response

### S-15.3.2: get_memory returns semantic matches [EXISTING: S-07.1.3]
- Priority: P0
- Method: A (API)
- Steps:
  1. `POST /api/v1/voice/server-tool` with `{"tool_name":"get_memory","signed_token":"$TOKEN","data":{"query":"work job career","limit":5}}`
- Pass criteria: HTTP 200, `success=true`, `data.facts` is an array (may be empty if no memory seeded)

### S-15.3.3: score_turn creates score_history row [EXISTING: S-07.2.1]
- Priority: P0
- Method: A (API)
- Steps:
  1. Note `COUNT(*)` in score_history before call
  2. `POST /api/v1/voice/server-tool` with `{"tool_name":"score_turn","signed_token":"$TOKEN","data":{"user_message":"I haven't been sleeping well, work is stressful","nikita_response":"That sounds really hard"}}`
  3. Wait 3s
- Pass criteria: `score_history` count increased by 1
- SQL verify: `SELECT source_platform, intimacy_delta, trust_delta FROM score_history WHERE user_id='<USER_ID>' ORDER BY created_at DESC LIMIT 1;`

### S-15.3.4: score_turn source_platform = 'voice' [EXISTING: S-07.2.2]
- Priority: P1
- Method: A (API)
- Steps: Same as S-15.3.3 (can reuse that row)
- Pass criteria: `source_platform='voice'` in the score_history row from S-15.3.3

### S-15.3.5: update_memory stores new fact [NEW]
- Priority: P1
- Method: A (API)
- Steps:
  1. `POST /api/v1/voice/server-tool` with `{"tool_name":"update_memory","signed_token":"$TOKEN","data":{"fact":"User's cat is named Mochi and is a tabby","category":"personal"}}`
- Pass criteria: HTTP 200, `success=true`, `data.stored=true`, `data.fact` echoes the fact string

### S-15.3.6: get_memory retrieves newly stored fact — round-trip [NEW]
- Priority: P1
- Method: A (API)
- Preconditions: S-15.3.5 completed successfully
- Steps:
  1. Wait 3s (pgVector indexing)
  2. `POST /api/v1/voice/server-tool` with `{"tool_name":"get_memory","signed_token":"$TOKEN","data":{"query":"cat Mochi tabby","limit":5}}`
- Pass criteria: `data.facts` array contains a string mentioning "Mochi" or "cat"
- SQL verify: `SELECT content FROM memory_facts WHERE user_id='<USER_ID>' AND content ILIKE '%mochi%' LIMIT 1;`

### S-15.3.7: server-tool auth required [EXISTING: S-07.4.1]
- Priority: P0
- Method: A (API)
- Steps:
  1. `POST /api/v1/voice/server-tool` with `{"tool_name":"get_context","signed_token":"invalid-token","data":{}}`
- Pass criteria: HTTP 401 or `success=false` with error message indicating auth failure

---

## Phase D: Post-Call Scoring + Transcript (~8 scenarios)

Simulate a complete call lifecycle by POSTing a webhook payload. Use a realistic transcript array.

```bash
WEBHOOK_PAYLOAD='{
  "conversation_id":"test-conv-001",
  "telegram_id":746410893,
  "event":"call_ended",
  "duration_seconds":240,
  "transcript":[
    {"role":"user","message":"Hey, how are you?"},
    {"role":"agent","message":"I missed you. How was your day?"},
    {"role":"user","message":"Better now that we are talking. Work was brutal."},
    {"role":"agent","message":"Tell me everything. I want to hear it."}
  ]
}'
```

### S-15.4.1: Webhook updates relationship_score [EXISTING: S-07.3.1]
- Priority: P0
- Method: A (API)
- Steps:
  1. Record `relationship_score` before: `SELECT relationship_score FROM users WHERE id='<USER_ID>';`
  2. `POST /api/v1/voice/webhook` with WEBHOOK_PAYLOAD and valid `X-ElevenLabs-Signature` header
  3. Wait 5s
- Pass criteria: `relationship_score` changed (increased for emotionally resonant transcript)

### S-15.4.2: Webhook creates conversations row with platform='voice' [EXISTING: S-07.3.2]
- Priority: P1
- Method: A (API)
- Steps: Verify after S-15.4.1
- Pass criteria: `SELECT id, platform, duration_seconds FROM conversations WHERE user_id='<USER_ID>' ORDER BY created_at DESC LIMIT 1;` — `platform='voice'`

### S-15.4.3: duration_seconds populated [EXISTING: S-07.8.1]
- Priority: P2
- Method: A (API)
- Steps: Inspect the conversations row from S-15.4.2
- Pass criteria: `duration_seconds=240` (matches webhook payload value)

### S-15.4.4: memory_facts created from transcript [EXISTING: S-07.3.3]
- Priority: P1
- Method: A (API)
- Steps: Wait 10s after webhook, then query
- SQL verify: `SELECT content FROM memory_facts WHERE user_id='<USER_ID>' ORDER BY created_at DESC LIMIT 5;`
- Pass criteria: At least 1 new memory_fact referencing content from the transcript (work, day, etc.)

### S-15.4.5: Composite formula verified: intimacy*0.30+passion*0.25+trust*0.25+secureness*0.20 [NEW]
- Priority: P0
- Method: A (API)
- Steps:
  1. Read `user_metrics` before webhook: `SELECT intimacy, passion, trust, secureness FROM user_metrics WHERE user_id='<USER_ID>';`
  2. Read `relationship_score` before webhook
  3. Post webhook (S-15.4.1), wait 5s
  4. Read both tables again
- Pass criteria: `new_relationship_score` equals `intimacy*0.30 + passion*0.25 + trust*0.25 + secureness*0.20` (within 0.5 rounding tolerance)

### S-15.4.6: Webhook idempotent — no duplicate memory_facts [EXISTING: S-07.7.1]
- Priority: P1
- Method: A (API)
- Steps:
  1. Note memory_facts count: `SELECT COUNT(*) FROM memory_facts WHERE user_id='<USER_ID>';`
  2. POST identical webhook payload second time (same `conversation_id`)
  3. Wait 5s, check count again
- Pass criteria: Count unchanged (dedup working) or idempotency header prevents re-processing

### S-15.4.7: Long transcript (50+ turns) no crash [EXISTING: S-07.8.2]
- Priority: P1
- Method: A (API)
- Steps:
  1. Build a 50-turn transcript array (alternate user/agent with single-sentence messages)
  2. POST to `/api/v1/voice/webhook`
- Pass criteria: HTTP 200, no 500 error

### S-15.4.8: Portal /conversations shows voice entry [EXISTING: S-07.6.1]
- Priority: P1
- Method: F (Functional, browser agent)
- Steps:
  1. Navigate portal to `/conversations` (authenticate with test account magic link)
  2. Look for entry with "Voice" label or similar indicator
- Pass criteria: At least one voice-type conversation visible in list, timestamp recent
- Portal recording:
  ```xml
  <portal_check route="/conversations">
    <field db="conversations.platform" portal="conversation list label" match="true|false"/>
    <field db="conversations.created_at" portal="timestamp display" match="true|false"/>
    <field db="conversations.duration_seconds" portal="duration badge" match="true|false"/>
  </portal_check>
  ```

---

## Phase E: Conversation Summaries + Cross-Platform (~4 scenarios)

### S-15.5.1: process-conversations cron processes voice conversation [NEW]
- Priority: P1
- Method: A (API)
- Preconditions: Voice conversation created in Phase D (status should be 'pending' or 'completed')
- Steps:
  1. `curl -X POST $API/tasks/process-conversations -H "Authorization: Bearer $TASK_AUTH_SECRET"`
- Pass criteria: HTTP 200, `pipeline_events` count increased
- SQL verify: `SELECT COUNT(*) FROM pipeline_events WHERE user_id='<USER_ID>' AND created_at > NOW() - INTERVAL '5 minutes';`

### S-15.5.2: Pipeline all 11 stages complete for voice conversation [NEW]
- Priority: P1
- Method: A (API)
- Steps: After S-15.5.1, wait 30s, then query
- SQL verify:
  ```sql
  SELECT stage_name, status FROM pipeline_events
  WHERE user_id='<USER_ID>'
  ORDER BY created_at DESC LIMIT 11;
  ```
- Pass criteria: All 11 expected stage names present with `status='done'`; none stuck on 'error'

### S-15.5.3: conversation_summary generated [NEW]
- Priority: P1
- Method: A (API)
- Steps: After S-15.5.1-2 complete
- SQL verify: `SELECT conversation_summary FROM conversations WHERE user_id='<USER_ID>' AND platform='voice' ORDER BY created_at DESC LIMIT 1;`
- Pass criteria: `conversation_summary` is non-null and non-empty string

### S-15.5.4: Cross-platform memory — voice fact appears in text context [NEW]
- Priority: P1
- Method: A (API)
- Steps:
  1. Ensure S-15.3.5 (update_memory "Mochi the cat") completed earlier
  2. Call `POST /api/v1/voice/server-tool` with `tool_name=get_context` for the same user
  3. Inspect `data.user_facts` array in response
- Pass criteria: "Mochi" or "cat" appears in `user_facts` — confirming voice-stored memory surfaces in context regardless of call origin
- Note: This verifies the pgVector memory is platform-agnostic

---

## Phases F-H: Voice Onboarding, Outbound & Background

**Continued in** `workflows/15b-voice-onboarding-outbound.md` — contains:
- **Phase F**: Voice Onboarding (~7 scenarios, S-15.6.*)
- **Phase G**: Outbound Call Delivery (~5 scenarios, S-15.7.*)
- **Phase H**: Background Jobs (~5 scenarios, S-15.8.*)

---

## Assessment Summary

| Phase | Scenarios | P0 | P1 | P2 | Behavioral |
|-------|-----------|----|----|----|----|
| A: Availability + Signed URL | 5 | 1 | 3 | 1 | 0 |
| B: Opening Selector | 4 | 0 | 2 | 2 | 1 |
| C: Mid-Call Server Tools | 7 | 3 | 3 | 0 | 1 |
| D: Post-Call Scoring | 8 | 2 | 4 | 2 | 0 |
| E: Summaries + Cross-Platform | 4 | 0 | 4 | 0 | 0 |
| F: Voice Onboarding | 7 | 2 | 3 | 2 | 0 |
| G: Outbound Delivery | 5 | 0 | 2 | 3 | 0 |
| H: Background Jobs | 5 | 1 | 2 | 2 | 0 |
| **Total** | **45** | **9** | **23** | **12** | **1** |

### Coverage Classification

- **[EXISTING]**: Scenario already present in S-07.* or S-12.*; included here for completeness and because it fits the logical phase grouping
- **[NEW]**: Net-new test not covered in any existing scenario set

### Exit Criteria

- All P0 scenarios: PASS (no failures)
- P1 failures: create GH issue with `high` label before closing session
- P2 failures: create GH issue with `medium` label, non-blocking
- Phase F requires live ElevenLabs; skip if agent credentials unavailable, log as NOT_TESTED

### Event-Stream Checkpoint Format

```
[TIMESTAMP] CHECKPOINT: voice-manual phase={A-H} scenarios_passed={N}/45 findings={list}
```

### Failure Recovery

For voice-specific failures:
- **ElevenLabs API timeout**: Retry after 30s. If persistent, check ElevenLabs status page and agent dashboard.
- **signed_token expired**: Re-call `POST /initiate` to get fresh token. Tokens expire after ~15 min.
- **Onboarding agent not responding**: Verify Meta-Nikita agent ID in ElevenLabs dashboard. Check `nikita/onboarding/meta_nikita.py` for config.
- **Webhook signature invalid**: Check `X-ElevenLabs-Signature` header generation. May need to update shared secret.
- **Server-tool returns 500**: Check Cloud Run logs: `gcloud run logs read nikita-api --project gcp-transcribe-test --region us-central1 --limit 20`

For general failures, see `references/failure-recovery.md`.
