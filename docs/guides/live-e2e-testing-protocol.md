# Live E2E Testing Protocol

**Purpose**: Enable any Claude Code agent to run a full live E2E verification of the Nikita game system using MCP tools against the production environment.

**Last Updated**: 2026-02-10 | **Expected Duration**: 10-20 minutes

---

## Prerequisites

### MCP Tools Required

| Tool | Purpose |
|------|---------|
| `mcp__telegram-mcp__send_message` | Send messages to Nikita bot |
| `mcp__telegram-mcp__get_messages` | Read bot responses |
| `mcp__telegram-mcp__list_chats` / `get_chat` | Find bot chat |
| `mcp__supabase__execute_sql` | All database evidence queries |
| `mcp__gmail__search_emails` + `read_email` | OTP retrieval (if auth needed) |

### Test Account & Infrastructure

| Field | Value |
|-------|-------|
| Telegram Bot | `@Nikita_my_bot` (Chat ID: `8211370823`) |
| User ID (Supabase) | `1ae5ba4c-35cc-476a-a64c-b9a995be4c27` |
| Telegram ID | `746410893` |
| Backend URL | `https://nikita-api-1040094048579.us-central1.run.app` |
| GCP Project / Region | `gcp-transcribe-test` / `us-central1` |

### Timing Expectations

Cold start: up to 60s. Warm response: 1-5s. Pipeline completion: 5-15s after response. Evidence query: 1-3s each.

---

## Phase 0: Account Preparation

### Step 1: Query User State

```sql
SELECT id, telegram_id, relationship_score, chapter, boss_attempts,
       game_status, onboarding_status, last_interaction_at, days_played
FROM users WHERE id = '1ae5ba4c-35cc-476a-a64c-b9a995be4c27';
```

If `game_status = 'game_over'`: send `/start` via Telegram MCP to reset (chapter=1, score=50.00).
If `game_status = 'active'` or `'boss_fight'`: proceed directly.

### Step 2: Capture Baseline Snapshot

```sql
-- Metrics
SELECT intimacy, passion, trust, secureness
FROM user_metrics WHERE user_id = '1ae5ba4c-35cc-476a-a64c-b9a995be4c27';

-- Engagement
SELECT state, multiplier, calibration_score, days_in_state, updated_at
FROM engagement_state WHERE user_id = '1ae5ba4c-35cc-476a-a64c-b9a995be4c27';

-- Conversation count
SELECT count(*) as total, count(*) FILTER (WHERE status = 'processed') as processed,
       max(created_at) as last_conversation
FROM conversations WHERE user_id = '1ae5ba4c-35cc-476a-a64c-b9a995be4c27';

-- Memory facts count
SELECT count(*) as total_facts,
       count(*) FILTER (WHERE graph_type = 'user') as user_facts,
       count(*) FILTER (WHERE graph_type = 'relationship') as rel_facts
FROM memory_facts WHERE user_id = '1ae5ba4c-35cc-476a-a64c-b9a995be4c27' AND is_active = true;

-- Score history count
SELECT count(*) as total_events FROM score_history
WHERE user_id = '1ae5ba4c-35cc-476a-a64c-b9a995be4c27';
```

---

## Phase 1: Test Execution (5 Tests)

### Async Completion Detection (use after EVERY message)

Poll every 5-10s. Wait until `status != 'active'` or timeout at 90s.

```sql
SELECT id, status, processed_at, score_delta, emotional_tone,
       conversation_summary, extracted_entities
FROM conversations
WHERE user_id = '1ae5ba4c-35cc-476a-a64c-b9a995be4c27'
ORDER BY created_at DESC LIMIT 1;
```

- `processed` = pipeline succeeded
- `failed` = pipeline failed (check error_logs)
- `active` after 90s = pipeline stuck (check job_executions)

### Test 1: Normal Conversation (Fact Extraction + Memory)

**Goal**: Bot responds, 9-stage pipeline processes message.
**Send**: `Hey babe, I just got back from a trip to Tokyo. The ramen there was incredible.`
**After**: Poll for completion, then read response via `get_messages`.

### Test 2: Continuity Test (Prior Context Reference)

**Goal**: Nikita remembers context from Test 1.
**Send**: `I'm already craving that food again. Do you think I should plan another trip?`
**Evaluate**: Response should reference Tokyo or ramen (proving memory works).

### Test 3: Emotional/Vice Probing

**Goal**: Trigger vice detection and emotional state computation.
**Send**: `I went out last night and had way too many cocktails. Woke up at some stranger's place lol`

### Test 4: Engagement / Inner Life

**Goal**: Verify life simulation and inner thoughts generation.
**Send**: `What have you been up to today? I feel like I barely know what's going on in your life`

### Test 5: Conflict Seed (Jealousy Trigger)

**Goal**: Test conflict detection and emotional arousal spike.
**Send**: `This girl at work keeps texting me. She's pretty cute actually, kinda reminds me of you`

---

## Phase 2: Evidence Collection (14 Queries)

Run after all 5 tests complete. Each query targets a specific pipeline stage.

### E1: Conversations Created

```sql
SELECT id, status, processed_at, score_delta, emotional_tone,
       conversation_summary, jsonb_array_length(messages) as msg_count
FROM conversations WHERE user_id = '1ae5ba4c-35cc-476a-a64c-b9a995be4c27'
ORDER BY created_at DESC LIMIT 5;
```

### E2: Facts Extracted (Stage 1 - Extraction)

```sql
SELECT id, graph_type, fact, confidence, source, created_at
FROM memory_facts WHERE user_id = '1ae5ba4c-35cc-476a-a64c-b9a995be4c27' AND is_active = true
ORDER BY created_at DESC LIMIT 10;
```

### E3: Conversation Threads (Stage 1 - Extraction)

```sql
SELECT id, thread_type, content, status, created_at
FROM conversation_threads WHERE user_id = '1ae5ba4c-35cc-476a-a64c-b9a995be4c27'
ORDER BY created_at DESC LIMIT 10;
```

### E4: Nikita Thoughts (Stage 1 - Extraction)

```sql
SELECT id, thought_type, content, created_at
FROM nikita_thoughts WHERE user_id = '1ae5ba4c-35cc-476a-a64c-b9a995be4c27'
ORDER BY created_at DESC LIMIT 10;
```

### E5: Score History (Stage 5 - Game State)

```sql
SELECT id, score, chapter, event_type, event_details, recorded_at
FROM score_history WHERE user_id = '1ae5ba4c-35cc-476a-a64c-b9a995be4c27'
ORDER BY recorded_at DESC LIMIT 10;
```

### E6: User State After Tests

```sql
SELECT relationship_score, chapter, game_status, boss_attempts, last_interaction_at
FROM users WHERE id = '1ae5ba4c-35cc-476a-a64c-b9a995be4c27';
```

### E7: Metrics After Tests

```sql
SELECT intimacy, passion, trust, secureness
FROM user_metrics WHERE user_id = '1ae5ba4c-35cc-476a-a64c-b9a995be4c27';
```

### E8: Engagement State

```sql
SELECT state, multiplier, calibration_score, days_in_state, updated_at
FROM engagement_state WHERE user_id = '1ae5ba4c-35cc-476a-a64c-b9a995be4c27';
```

### E9: Ready Prompts (Stage 9 - Prompt Builder)

```sql
SELECT id, platform, token_count, generation_time_ms, is_current,
       created_at, LEFT(prompt_text, 200) as prompt_preview
FROM ready_prompts WHERE user_id = '1ae5ba4c-35cc-476a-a64c-b9a995be4c27'
ORDER BY created_at DESC LIMIT 5;
```

### E10: Narrative Arcs (Stage 3 - Life Simulation)

```sql
SELECT id, template_name, category, current_stage, conversations_in_arc,
       is_active, current_description
FROM user_narrative_arcs
WHERE user_id = '1ae5ba4c-35cc-476a-a64c-b9a995be4c27' AND is_active = true;
```

### E11: Daily Summary (Stage 8)

```sql
SELECT id, date, conversations_count, emotional_tone, summary_text, score_start, score_end
FROM daily_summaries WHERE user_id = '1ae5ba4c-35cc-476a-a64c-b9a995be4c27'
ORDER BY date DESC LIMIT 1;
```

### E12: Error Logs (System Health)

```sql
SELECT id, level, message, source, occurred_at
FROM error_logs WHERE user_id = '1ae5ba4c-35cc-476a-a64c-b9a995be4c27'
  AND occurred_at > now() - interval '1 hour'
ORDER BY occurred_at DESC LIMIT 10;
```

### E13: Job Executions (Pipeline Health)

```sql
SELECT job_name, status, started_at, completed_at,
       EXTRACT(EPOCH FROM (completed_at - started_at)) * 1000 as duration_ms
FROM job_executions WHERE started_at > now() - interval '1 hour'
ORDER BY started_at DESC LIMIT 10;
```

### E14: Prompt Sections Verification (11 sections)

```sql
SELECT
  prompt_text LIKE '%IDENTITY%' as has_identity,
  prompt_text LIKE '%IMMERSION RULES%' as has_immersion,
  prompt_text LIKE '%PLATFORM STYLE%' as has_platform,
  prompt_text LIKE '%CURRENT STATE%' as has_current_state,
  prompt_text LIKE '%RELATIONSHIP STATE%' as has_relationship,
  prompt_text LIKE '%MEMORY%' as has_memory,
  prompt_text LIKE '%CONTINUITY%' as has_continuity,
  prompt_text LIKE '%INNER LIFE%' as has_inner_life,
  prompt_text LIKE '%PSYCHOLOGICAL DEPTH%' as has_psych,
  prompt_text LIKE '%CHAPTER BEHAVIOR%' as has_chapter,
  prompt_text LIKE '%VICE SHAPING%' as has_vice,
  token_count
FROM ready_prompts
WHERE user_id = '1ae5ba4c-35cc-476a-a64c-b9a995be4c27'
  AND is_current = true AND platform = 'text'
LIMIT 1;
```

---

## Phase 3: Pass/Fail Evaluation

### Per-Test Criteria

| # | Test | PASS | FAIL |
|---|------|------|------|
| 1 | Normal conversation | Bot responds within 60s, status = 'processed' | No response OR stuck > 90s |
| 2 | Continuity | Response references Tokyo/ramen from Test 1 | No context carryover |
| 3 | Vice probing | Processed, emotional_tone not null | Pipeline fails or no extraction |
| 4 | Inner life | Bot describes her day/activities | Generic non-personalized response |
| 5 | Conflict seed | Pipeline completes | Pipeline failure |

### Pipeline Evidence Criteria

| Evidence | PASS | FAIL |
|----------|------|------|
| Bot responds | Response within 60s per test | No response on any test |
| Conversation status | All 5 reach 'processed' | Any stuck 'active' > 90s |
| Facts extracted (E2) | >= 1 new fact (Tokyo/ramen) | 0 new facts after 5 msgs |
| Score updated (E5) | >= 1 score_history row per conversation | No score events |
| Prompt generated (E9) | ready_prompts updated | No prompt generation |
| 11 sections (E14) | All 11 LIKE checks true | Any section missing |
| No critical errors (E12) | 0 critical-level rows | Critical errors present |
| Threads created (E3) | >= 1 thread from 5 conversations | 0 threads |
| Thoughts generated (E4) | >= 1 thought from 5 conversations | 0 thoughts |

### Overall Verdict

- **ALL PASS**: All 5 tests respond, all evidence criteria met
- **PARTIAL PASS**: Bot responds on all tests but some non-critical pipeline evidence missing
- **FAIL**: Bot does not respond, OR critical stages fail, OR conversation stuck > 90s

---

## Pipeline Stages Reference

| # | Stage | Critical | DB Evidence |
|---|-------|----------|-------------|
| 1 | Extraction | YES | `memory_facts`, `conversation_threads`, `nikita_thoughts`, `conversations.extracted_entities` |
| 2 | Memory Update | YES | `memory_facts` (pgVector embeddings) |
| 3 | Life Simulation | No | `user_narrative_arcs` |
| 4 | Emotional State | No | In-memory; surfaced in prompt CURRENT STATE section |
| 5 | Game State | No | `score_history`, `users.relationship_score`, `users.chapter` |
| 6 | Conflict Detection | No | In-memory; surfaced in prompt RELATIONSHIP STATE section |
| 7 | Touchpoint Scheduling | No | `scheduled_touchpoints` |
| 8 | Summary Update | No | `daily_summaries` |
| 9 | Prompt Builder | No | `ready_prompts` (11-section Jinja2, token-budgeted: text 5500-6500, voice 1800-2200) |

Stages 1-2 are critical: failure stops the pipeline. Stages 3-9 are non-critical: failure is logged and pipeline continues.

### 11 System Prompt Sections

IDENTITY, IMMERSION RULES, PLATFORM STYLE, CURRENT STATE, RELATIONSHIP STATE, MEMORY, CONTINUITY, INNER LIFE, PSYCHOLOGICAL DEPTH, CHAPTER BEHAVIOR, VICE SHAPING.

---

## Troubleshooting

### Bot Does Not Respond

1. Check Cloud Run: `gcloud run services describe nikita-api --region us-central1 --project gcp-transcribe-test --format="value(status.url)"`
2. Check errors: `SELECT level, message, source, occurred_at FROM error_logs ORDER BY occurred_at DESC LIMIT 5;`
3. First message after idle may take 60s (cold start). Wait and retry.

### Pipeline Stuck ('active' > 90s)

1. Check job failures: `SELECT job_name, status, error_message FROM job_executions WHERE status = 'failed' ORDER BY started_at DESC LIMIT 5;`
2. Check stuck conversations: `SELECT id, status, processing_started_at FROM conversations WHERE status = 'processing' AND processing_started_at < now() - interval '30 minutes';`
3. The `process-conversations` pg_cron job runs every 2 minutes and picks up stale conversations.

### OTP Needed (Re-authentication)

1. Send `/start` via Telegram MCP
2. When prompted for email, send the registered email address
3. Find OTP: `mcp__gmail__search_emails query:"Nikita verification" newer_than:"1h"`
4. Read email, extract 6-8 digit code, send to bot

### Game Over State

Send `/start` via Telegram MCP. Resets: chapter=1, score=50.00, game_status='active', boss_attempts=0.

---

## Key Tables Quick Reference

| Table | Key Columns | Purpose |
|-------|-------------|---------|
| `users` | game_status, chapter, relationship_score, onboarding_status | Core game state |
| `user_metrics` | intimacy, passion, trust, secureness | 4-dimension scoring |
| `engagement_state` | state, multiplier, calibration_score | Engagement tracking |
| `conversations` | status, processed_at, score_delta, emotional_tone, messages | Conversation logs |
| `memory_facts` | fact, graph_type, confidence, source, is_active | Semantic memory (pgVector) |
| `conversation_threads` | thread_type, content, status | Unresolved topics |
| `nikita_thoughts` | thought_type, content | Nikita inner life |
| `score_history` | score, event_type, event_details, recorded_at | Score timeline |
| `ready_prompts` | prompt_text, token_count, is_current, platform | Pre-built system prompts |
| `generated_prompts` | prompt_content, token_count, generation_time_ms | Prompt audit log |
| `user_narrative_arcs` | template_name, current_stage, is_active | Storylines |
| `daily_summaries` | summary_text, conversations_count, emotional_tone | Daily recaps |
| `error_logs` | level, message, source, occurred_at | Error monitoring |
| `job_executions` | job_name, status, started_at | Job tracking |
| `user_profiles` | location_city, life_stage, social_scene, primary_interest | Onboarding profile |
| `user_backstories` | backstory fields | Generated backstory |
| `user_vice_preferences` | category, intensity_level, engagement_score | Vice tracking |
| `onboarding_states` | current_step, completed fields | Onboarding progress |
| `scheduled_touchpoints` | scheduling data | Proactive messages |
