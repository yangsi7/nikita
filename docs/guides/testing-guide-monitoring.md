# Testing Guide: Observability and Monitoring

This guide documents how to observe, verify, and alert on the Nikita system across all 5 observation layers. Use it during E2E testing, post-deployment verification, and ongoing production monitoring.

---

## Section 1: Observation Points Inventory

### Layer 1 — Database (Supabase MCP)

**Project ID**: `oegqvulrqeudrdkfxoqd`  
**Tool**: Supabase MCP `execute_sql`

| Table | What it stores | Key columns |
|-------|---------------|-------------|
| `pipeline_events` | Per-stage observability events | `stage`, `status`, `duration_ms`, `data` JSONB |
| `job_executions` | Cron job run records | `job_name`, `status`, `started_at`, `duration_ms`, `stage_timings` |
| `score_history` | Per-turn score delta rows | `score`, `chapter`, `event_type`, `event_details` JSONB, `source_platform` |
| `engagement_state` | Current FSM state per user | `state`, `multiplier`, `calibration_score` |
| `engagement_history` | FSM transition log | `from_state`, `to_state`, `reason` |
| `memory_facts` | pgVector embeddings (dedup 0.95) | `content`, `embedding`, `is_active`, `user_id` |
| `conversations` | Message JSONB, status, summary | `messages`, `status`, `summary`, `platform` |
| `conversation_threads` | Open topics (persistence stage) | `topic`, `thread_data` |
| `nikita_thoughts` | Extracted facts (extraction stage) | `fact_type`, `content`, `user_id` |
| `nikita_emotional_states` | Computed state (emotional stage) | `mood`, `intensity`, `user_id` |
| `nikita_life_events` | Simulated events (life_sim stage) | `event_type`, `description` |
| `user_metrics` | 4 relationship metrics | `intimacy`, `passion`, `trust`, `secureness` |
| `user_vice_preferences` | Vice categories + intensity | `category`, `intensity_level`, `engagement_score` |
| `scheduled_touchpoints` | Proactive message queue | `scheduled_for`, `content_type` |
| `voice_calls` | Inbound and outbound call records | `session_id`, `duration_s`, `ended_at` |
| `ready_prompts` | Pre-built text and voice prompts | `platform`, `prompt_text`, `created_at` |

### Layer 2 — API (Admin Endpoints)

Base URL: `https://nikita-api-1040094048579.us-central1.run.app`  
Auth: Admin JWT required (Supabase JWT with `@silent-agents.com` domain or `settings.admin_emails` allowlist).

| Endpoint | Returns |
|----------|---------|
| `GET /health` | 200 if service is up |
| `GET /admin/pipeline-health` | `job_executions` + `pipeline_events` summary, stage stats |
| `GET /admin/users` | Paginated user list with game state and engagement |
| `GET /admin/users/{id}` | Full user detail |
| `GET /admin/users/{id}/metrics` | Live `user_metrics` read (intimacy/passion/trust/secureness) |
| `GET /admin/users/{id}/engagement` | `engagement_state` + recent transitions |
| `GET /admin/users/{id}/memory` | `memory_facts` paginated (30s timeout, 503 on overload) |
| `GET /admin/users/{id}/conversations` | Conversation list + message counts |
| `GET /admin/users/{id}/scores` | Score timeline (default 7 days) |
| `GET /admin/users/{id}/vices` | Vice preferences list |
| `GET /admin/users/{id}/pipeline-history` | Paginated pipeline execution history |

### Layer 3 — MCP Tools

| Tool | Use |
|------|-----|
| Supabase MCP `execute_sql` | Direct SQL against live DB — table counts, row assertions, JSONB reads |
| Telegram MCP `get_messages` | Assert Nikita response content and timing. Session expires — re-run `session_string_generator.py` in `../telegram-mcp/` if all calls fail |
| Gmail MCP | Assert magic link emails delivered; portal auth flow verification |
| ElevenLabs `list_conversations` | Fetch voice call transcripts for post-call verification |

### Layer 4 — Cloud Run Logs

```bash
gcloud run logs read nikita-api --project gcp-transcribe-test --region us-central1 --limit 100
```

Key log markers (structlog, JSON format):

| Marker | Meaning |
|--------|---------|
| `pipeline_started` | Includes `conversation_id`, `user_id`, `platform` |
| `stage_completed` | Includes `stage=N`, `duration_ms=X` |
| `stage_failed` | Includes `stage=N`, `critical=True/False` |
| `pipeline_completed` | Includes `total_ms=X`, `stages=11`, `errors=N` |
| `pipeline_skipped_terminal_state` | `game_status=game_over` or `won` — pipeline did not run |
| `voice_prompt_stale` | `age_hours > 4` — cached_voice_prompt needs refresh |
| `observability_flush` | `pipeline_events` bulk INSERT completed |

### Layer 5 — Portal (Next.js)

Portal URL: `https://portal-phi-orcin.vercel.app`  
Auth: Supabase magic link, JWT in session.

| Page | Data source |
|------|------------|
| `/dashboard/metrics` | `GET /portal/metrics` — 4-metric radar chart |
| `/dashboard/engagement` | `GET /portal/engagement` — FSM state + history timeline |
| `/dashboard/memory` | `GET /admin/users/{id}/memory` — memory_facts browser |
| `/dashboard/chapters` | `GET /portal/stats` — chapter + boss status |
| `/dashboard/voice` | voice_calls table — voice call history |
| `/admin/` | Admin panel: user list, metrics drill-down, pipeline health, engagement timeline |

---

## Section 2: Pipeline Stage Observability (11 Stages)

For each stage: event type written to `pipeline_events`, expected duration, verification SQL, and red flags.

**Quick check — all stages for one pipeline run:**
```sql
SELECT stage, status, duration_ms, data
FROM pipeline_events
WHERE conversation_id = '<CONV_ID>'
ORDER BY created_at ASC;
```

### Stage 1: extraction [CRITICAL]

- **event_type**: `extraction.complete` / `extraction.failed`
- **Duration**: 500–3000ms (LLM call for fact extraction)
- **Verification**:
```sql
SELECT COUNT(*) FROM nikita_thoughts
WHERE conversation_id = '<CONV_ID>';
-- Expect > 0 rows for a substantive conversation
```
- **Red flags**: `status='failed'` in pipeline_events; zero nikita_thoughts after a long conversation; duration > 5000ms (LLM timeout)

### Stage 2: persistence [non-critical]

- **event_type**: `persistence.complete`
- **Duration**: 50–200ms
- **Verification**:
```sql
SELECT COUNT(*) FROM conversation_threads
WHERE conversation_id = '<CONV_ID>';
-- Expect rows for open topics
```
- **Red flags**: Missing event after extraction.complete; runs after memory_update (check ordering in `job_executions.stage_timings`)

### Stage 3: memory_update [CRITICAL]

- **event_type**: `memory_update.complete` / `memory_update.failed`
- **Duration**: 100–500ms
- **Verification**:
```sql
SELECT COUNT(*) FROM memory_facts
WHERE user_id = '<USER_ID>' AND is_active = true;
-- Should increase after a fact-rich conversation

SELECT COUNT(*) FROM memory_facts
WHERE user_id = '<USER_ID>' AND is_active = false;
-- Superseded (deduped) facts — non-zero indicates dedup is working
```
- **Red flags**: Count unchanged after a conversation with new personal facts; duplicate facts created (cosine threshold 0.95 should prevent this); duration > 2000ms

### Stage 4: life_sim [non-critical]

- **event_type**: `life_sim.complete`
- **Duration**: 200–2000ms (LLM call)
- **Verification**:
```sql
SELECT COUNT(*) FROM nikita_life_events
WHERE created_at > NOW() - INTERVAL '10 minutes';
-- Absence is OK for short conversations
```
- **Red flags**: Duration > 5000ms; errors in `data` JSONB field

### Stage 5: emotional [non-critical]

- **event_type**: `emotional.complete`
- **Duration**: 50–200ms
- **Verification**:
```sql
SELECT mood, intensity, updated_at FROM nikita_emotional_states
WHERE user_id = '<USER_ID>';
-- Expect upserted row with fresh updated_at
```
- **Red flags**: Row not updated after pipeline run; stale `updated_at` (> 30 min from conversation end)

### Stage 6: vice [non-critical]

- **event_type**: `vice.complete`
- **Duration**: 200–1000ms
- **Verification**:
```sql
SELECT category, intensity_level, engagement_score
FROM user_vice_preferences
WHERE user_id = '<USER_ID>';
```
- **Red flags**: No rows after many conversations containing vice-relevant topics; intensity_level never advancing

### Stage 7: game_state [non-critical]

- **event_type**: `game_state.complete`
- **Duration**: 10–50ms
- **Verification**:
```sql
SELECT chapter, game_status, relationship_score FROM users
WHERE id = '<USER_ID>';

SELECT score, chapter, event_type, recorded_at FROM score_history
WHERE user_id = '<USER_ID>'
ORDER BY recorded_at DESC LIMIT 5;
```
- **Red flags**: `game_status='boss_fight'` not clearing after boss resolution; chapter not advancing when score exceeds threshold; score_history row missing after scoring

### Stage 8: conflict [non-critical]

- **event_type**: `conflict.complete`
- **Duration**: 10–50ms
- **Verification**:
```sql
SELECT conflict_details FROM users WHERE id = '<USER_ID>';
-- JSONB populated during conflict, null when resolved
```
- **Red flags**: conflict_details remaining populated after resolution; null JSONB during an active conflict scenario

### Stage 9: touchpoint [non-critical]

- **event_type**: `touchpoint.complete`
- **Duration**: 50–200ms
- **Verification**:
```sql
SELECT scheduled_for, content_type, status
FROM scheduled_touchpoints
WHERE user_id = '<USER_ID>'
ORDER BY scheduled_for DESC LIMIT 5;
```
- **Red flags**: No rows ever scheduled for an active user; `ctx.touchpoint_scheduled` mismatch with DB row

### Stage 10: summary [non-critical]

- **event_type**: `summary.complete`
- **Duration**: 200–2000ms (LLM call)
- **Verification**:
```sql
SELECT summary, emotional_tone FROM conversations
WHERE id = '<CONV_ID>';
-- Both fields should be non-null after this stage
```
- **Red flags**: `summary` field null after pipeline completes; duration > 5000ms

### Stage 11: prompt_builder [non-critical]

- **event_type**: `prompt_builder.complete`
- **Duration**: 500–3000ms (LLM call for prompt generation)
- **Verification**:
```sql
SELECT platform, created_at FROM ready_prompts
WHERE user_id = '<USER_ID>'
ORDER BY created_at DESC LIMIT 4;
-- Expect rows for platform='text' AND platform='voice'

SELECT cached_voice_prompt_at FROM users WHERE id = '<USER_ID>';
-- Should be within last 4 hours
```
- **Red flags**: Missing `voice` platform row; `cached_voice_prompt_at` older than 4 hours (logged as `voice_prompt_stale`); duration > 10000ms

---

## Section 3: Scoring Consistency Monitoring

### Composite Formula Verification

The relationship score is a weighted composite:

```
composite = intimacy*0.30 + passion*0.25 + trust*0.25 + secureness*0.20
```

Verify against live metrics:
```sql
SELECT
  intimacy * 0.30 + passion * 0.25 + trust * 0.25 + secureness * 0.20 AS expected_composite,
  (SELECT relationship_score FROM users WHERE id = um.user_id) AS actual_score
FROM user_metrics um
WHERE user_id = '<USER_ID>';
```

Small divergence is normal (score updates are async); divergence > 5 points indicates a bug.

### Score Delta Anomaly Detection

```sql
-- Deltas exceeding ±10 in any single metric
SELECT id, user_id, event_type, recorded_at,
  event_details->'deltas'->>'intimacy' AS intimacy_delta,
  event_details->'deltas'->>'passion' AS passion_delta,
  event_details->'deltas'->>'trust' AS trust_delta,
  event_details->'deltas'->>'secureness' AS secureness_delta
FROM score_history
WHERE
  ABS(CAST(event_details->'deltas'->>'intimacy' AS DECIMAL)) > 10
  OR ABS(CAST(event_details->'deltas'->>'passion' AS DECIMAL)) > 10
  OR ABS(CAST(event_details->'deltas'->>'trust' AS DECIMAL)) > 10
  OR ABS(CAST(event_details->'deltas'->>'secureness' AS DECIMAL)) > 10
ORDER BY recorded_at DESC LIMIT 20;
```

### Engagement Multiplier Range Check

Valid range: [0.5, 1.0]. Values outside this indicate an engagement FSM bug.
```sql
SELECT user_id, state, multiplier FROM engagement_state
WHERE multiplier < 0.5 OR multiplier > 1.0;
```

### Cross-Channel Scoring Comparison

Compare text vs voice scoring for the same user:
```sql
SELECT
  source_platform,
  AVG(CAST(event_details->>'delta' AS DECIMAL)) AS avg_delta,
  COUNT(*) AS event_count
FROM score_history
WHERE user_id = '<USER_ID>'
  AND event_type = 'conversation_scored'
GROUP BY source_platform;
```

Voice and text should produce similar average deltas for comparable conversation quality.

---

## Section 4: Memory Health

### Memory Fact Count Per User
```sql
SELECT COUNT(*) FROM memory_facts
WHERE user_id = '<USER_ID>' AND is_active = true;
```

Expected growth: 5–15 new facts per substantive conversation. Zero growth after many conversations indicates a memory_update stage failure.

### Dedup Health Check
```sql
SELECT COUNT(*) FROM memory_facts
WHERE user_id = '<USER_ID>' AND is_active = false;
```

A non-zero count is healthy — it means the 0.95 cosine similarity threshold is correctly superseding near-duplicate facts. Zero across many conversations may indicate dedup is not running.

### Memory Staleness Check
```sql
SELECT MAX(created_at) AS last_fact_added
FROM memory_facts
WHERE user_id = '<USER_ID>' AND is_active = true;
```

If the user is active but no facts were added in > 24 hours, investigate the memory_update stage.

---

## Section 5: Background Job Health

**Active pg_cron jobs** (authoritative registry in `docs/deployment.md`):

| Job name | Schedule | Endpoint |
|----------|----------|----------|
| `process-conversations` | Every minute | `POST /tasks/process-conversations` |
| `deliver-messages` | Every minute | `POST /tasks/deliver` |
| `decay-hourly` | `0 * * * *` | `POST /tasks/decay` |
| `cleanup-hourly` | `0 * * * *` | `POST /tasks/cleanup` |
| `touchpoints-5min` | `*/5 * * * *` | `POST /tasks/touchpoints` |
| `boss-timeout-6h` | `0 */6 * * *` | `POST /tasks/boss-timeout` |
| `summary-daily` | `59 23 * * *` | `POST /tasks/summary` |
| `psyche-batch-daily` | `0 5 * * *` | `POST /tasks/psyche-batch` |
| `health-check` | `*/5 * * * *` | `GET /health` |
| `engagement-hourly` | `30 * * * *` | `POST /tasks/engagement` |

### Recent Job Execution Monitor
```sql
SELECT job_name, status, started_at, completed_at, duration_ms
FROM job_executions
ORDER BY started_at DESC
LIMIT 20;
```

### Failed Jobs in Last Hour
```sql
SELECT job_name, status, started_at, duration_ms, error_message
FROM job_executions
WHERE status = 'failed'
  AND started_at > NOW() - INTERVAL '1 hour'
ORDER BY started_at DESC;
```

### Pipeline Processing Lag
```sql
-- Conversations waiting longer than 5 minutes for processing
SELECT id, user_id, platform, started_at, status
FROM conversations
WHERE status = 'pending'
  AND started_at < NOW() - INTERVAL '5 minutes'
ORDER BY started_at ASC;
```

### Decay Job Verification
After `decay-hourly` runs, score_history should contain rows with `event_type = 'decay'`:
```sql
SELECT user_id, score, recorded_at,
  event_details->>'decay_amount' AS decay_applied
FROM score_history
WHERE event_type = 'decay'
ORDER BY recorded_at DESC LIMIT 10;
```

---

## Section 6: Portal/Dashboard Verification Checklist

### Portal User-Facing Endpoints (JWT auth, user_id from token)

| Endpoint | Data source | What to verify | Common discrepancies |
|----------|------------|----------------|---------------------|
| `GET /portal/stats` | `users`, `user_metrics` | score, chapter, boss_threshold, progress_to_boss | Score lags composite by up to one pipeline run |
| `GET /portal/metrics` | `user_metrics` | All 4 metrics present, values in [0, 100] | Metrics missing if pipeline never ran |
| `GET /portal/engagement` | `engagement_state`, `engagement_history` | state, multiplier in [0.5, 1.0], recent transitions | Returns default calibrating state for new users — not a bug |
| `GET /portal/vices` | `user_vice_preferences` | category, intensity_level, engagement_score normalized to 0–100 | Empty list is normal for new users with < 5 conversations |
| `GET /portal/score-history` | `score_history` | Points array, recorded_at ordering | Default window is 30 days; pass `?days=7` for recent |
| `GET /portal/daily-summaries` | Daily summaries table | summary_text, emotional_tone, score delta | Populated by `summary-daily` cron (23:59 UTC) |
| `GET /portal/conversations` | `conversations` | Paginated list, platform, score_delta | Voice conversations appear with `platform='voice'` |
| `GET /portal/conversations/{id}` | `conversations.messages` JSONB | Full message array, is_boss_fight flag | conversation_summary populated after pipeline |
| `GET /portal/decay` | `users`, decay engine | Decay projection, hours_until_loss | Projection is estimated, not exact |
| `GET /portal/settings` | `users`, `auth.users` | email, timezone, telegram_id linkage | email from JWT auth.users, not public.users |

### Admin Endpoints (Admin JWT required)

| Endpoint | What to verify |
|----------|---------------|
| `GET /admin/users` | All registered users visible, game_status and chapter accurate |
| `GET /admin/pipeline-health` | Stage success rates, recent failures, no stage stuck at > 5% error rate |
| `GET /admin/conversations` | Conversation inspector matches DB content |
| `GET /admin/stats` | Aggregate stats match DB counts |
| `GET /admin/users/{id}/metrics` | Matches `user_metrics` table directly |
| `GET /admin/users/{id}/engagement` | Multiplier in [0.5, 1.0]; state is one of 6 FSM states |
| `GET /admin/users/{id}/memory` | Returns user_facts, relationship_episodes, nikita_events; 503 if pgVector under load |

---

## Section 7: Production Alerting Patterns

### Health Probe
```bash
curl -f https://nikita-api-1040094048579.us-central1.run.app/health
```
Alert if: non-200 response, or response time > 5s. Note: cold starts take 5–15s; first request after scale-to-zero may be slow.

### Pipeline Processing Lag Alert
```sql
SELECT COUNT(*) FROM conversations
WHERE status = 'pending'
  AND started_at < NOW() - INTERVAL '5 minutes';
```
Alert if count > 0. Means `process-conversations` cron is not running or conversations are stuck.

### Job Failure Alert
```sql
SELECT COUNT(*) FROM job_executions
WHERE status = 'failed'
  AND started_at > NOW() - INTERVAL '1 hour';
```
Alert if count > 3 in any rolling hour window.

### Score Anomaly Alert
```sql
SELECT COUNT(*) FROM score_history
WHERE recorded_at > NOW() - INTERVAL '1 hour'
  AND ABS(CAST(event_details->>'delta' AS DECIMAL)) > 15;
```
Alert if count > 0. A composite change of > 15 in a single pipeline run is outside expected bounds and may indicate a scoring bug.

### Voice Prompt Staleness Alert
```sql
SELECT COUNT(*) FROM users
WHERE cached_voice_prompt_at < NOW() - INTERVAL '4 hours'
  AND game_status = 'active';
```
Alert if count > 0. Voice calls for these users will use stale prompts.

---

## Section 8: Journey-to-Guide Cross-Reference

| Test scenario | Monitoring sections |
|--------------|-------------------|
| New user registration | Section 2 (pipeline stages 1-11), Section 4 (memory baseline) |
| Text conversation | Section 2 (all stages), Section 3 (scoring), Section 4 (memory growth) |
| Voice call inbound | Section 1 (voice_calls table), Section 3 (source_platform='voice') |
| Chapter advancement | Section 2 (Stage 7 game_state), Section 6 (portal/stats) |
| Boss encounter | Section 2 (Stage 7 game_status=boss_fight), Section 6 (admin/users) |
| Score decay | Section 5 (decay-hourly job), Section 3 (anomaly detection) |
| Portal login | Section 6 (portal checklist), Section 1 (Gmail MCP) |
| Background job failure | Section 5 (job health queries), Section 7 (alerting) |
| Memory dedup | Section 4 (dedup check), Section 2 (Stage 3 red flags) |
| Engagement FSM transition | Section 3 (multiplier range), Section 6 (portal/engagement) |
