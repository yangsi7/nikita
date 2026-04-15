# Autonomous Testing Guide — Nikita AI Girlfriend Simulation

**Purpose**: MCP-driven protocol for Claude to execute E2E tests autonomously without human interaction.

**MCP Tools Required**
- `mcp__telegram-mcp__send_message` / `mcp__telegram-mcp__get_messages` / `mcp__telegram-mcp__get_inline_keyboard_buttons` / `mcp__telegram-mcp__click_inline_button`
- `mcp__gmail__search_emails` / `mcp__gmail__read_email`
- `mcp__supabase__execute_sql` (project_id: `oegqvulrqeudrdkfxoqd`)
- `mcp__gemini__gemini-analyze-text`
- Bash (`curl`) for task endpoint triggers

**Constants**: chat_id=`8211370823`, telegram_id=`746410893`, email=`simon.yang.ch@gmail.com`
**API**: `https://nikita-api-1040094048579.us-central1.run.app`
**Portal**: `https://portal-phi-orcin.vercel.app`

---

## Section 1: Prerequisites and Data Cleanup

```sql
-- FK-safe wipe (CASCADE handles all child tables)
DELETE FROM users WHERE email = 'simon.yang.ch@gmail.com';
DELETE FROM pending_registrations WHERE telegram_id = 746410893;

-- Verify clean
SELECT COUNT(*) FROM users WHERE email = 'simon.yang.ch@gmail.com';   -- Assert: 0
SELECT COUNT(*) FROM pending_registrations WHERE telegram_id = 746410893; -- Assert: 0
```

- Delete auth.users via Supabase Dashboard (Authentication > Users) — not automatable via SQL
- ElevenLabs conversation history: clean manually via ElevenLabs dashboard

Load tools at session start:
```
ToolSearch: select:mcp__telegram-mcp__send_message,mcp__telegram-mcp__get_messages
ToolSearch: select:mcp__gmail__search_emails,mcp__gmail__read_email
ToolSearch: select:mcp__supabase__execute_sql
ToolSearch: select:mcp__gemini__gemini-analyze-text
```

---

## Section 2: Journey 1 — New User Onboarding

**Step 2.1** — Send /start, wait 10s, verify bot responded:
```
mcp__telegram-mcp__send_message(chat_id="8211370823", text="/start")
mcp__telegram-mcp__get_messages(chat_id="8211370823", page_size=3)
-- Assert: last message from_id != 746410893
```

**Step 2.2** — Retrieve OTP from Gmail (wait 15s after bot sends email):
```
mcp__gmail__search_emails(query="subject:OTP OR subject:verification OR from:noreply", max_results=3)
mcp__gmail__read_email(email_id="<id>")
-- Extract 6-digit OTP with regex \b\d{6}\b
```

**Step 2.3** — Submit OTP, complete onboarding prompts using inline button clicks.

**Step 2.4** — Verify DB state, store USER_ID:
```sql
SELECT id, email, game_status, chapter, relationship_score
FROM users WHERE email = 'simon.yang.ch@gmail.com';
-- Assert: game_status='active', chapter=1, relationship_score=50.00

SELECT location_city, life_stage, social_scene, primary_interest FROM user_profiles
WHERE id = '<USER_ID>';
-- Assert: all fields non-null
```

**Step 2.5** — Portal: navigate to `/dashboard`, verify Chapter 1 state and score ~50%.

---

## Section 3: Journey 2 — Chapter Progression (Ch1 to Ch5)

Scoring formula: `composite = intimacy*0.30 + passion*0.25 + trust*0.25 + secureness*0.20`
Boss thresholds: 55/60/65/70/75% (Ch1-5). Availability: 10/40/80/90/95%.

**Step 3.1** — SQL-accelerate to threshold (example: Ch1 approaching 55%):
```sql
UPDATE user_metrics SET intimacy=60, passion=58, trust=57, secureness=55 WHERE user_id='<USER_ID>';
UPDATE users SET relationship_score=57.85 WHERE id='<USER_ID>';
```

**Step 3.2** — Send message, verify scoring (wait 10s):
```
mcp__telegram-mcp__send_message(chat_id="8211370823", text="I've been thinking about you all day")
```
```sql
SELECT score, event_type, event_details->'deltas'->>'intimacy' as d_intimacy,
       event_details->>'multiplier' as multiplier, created_at
FROM score_history WHERE user_id='<USER_ID>' ORDER BY created_at DESC LIMIT 3;
-- Assert: new row within last 60s, multiplier present
```

**Step 3.3** — Trigger pipeline and wait 60s:
```bash
curl -s -X POST .../tasks/process-conversations -H "Authorization: Bearer $TASK_AUTH_SECRET"
```

Verify all 11 stages via SQL:

| Stage | Output Table | Assert |
|-------|-------------|--------|
| 1: extraction [CRITICAL] | nikita_thoughts | rows exist |
| 2: persistence | conversation_threads | rows exist |
| 3: memory_update [CRITICAL] | memory_facts | count increased, no duplicates |
| 4: life_sim | nikita_life_events | rows exist (may be empty on short convos) |
| 5: emotional | nikita_emotional_states | row upserted |
| 6: vice | user_vice_preferences | rows exist |
| 7: game_state | users.chapter / game_status | chapter correct |
| 8: conflict | users.conflict_details | JSONB populated or null |
| 9: touchpoint | scheduled_touchpoints | row may exist |
| 10: summary | conversations.summary | field populated |
| 11: prompt_builder | ready_prompts | text + voice rows |

```sql
-- Pipeline observability: assert >= 12 events (11 stages + pipeline.complete)
SELECT COUNT(*) FROM pipeline_events WHERE user_id='<USER_ID>'
AND created_at > NOW() - INTERVAL '5 minutes';
```

**Step 3.4** — Portal: check `/dashboard` score, `/dashboard/conversations` new entry, `/dashboard/engagement` FSM badge.

Repeat Steps 3.1-3.4 for Ch2 through Ch5 using chapter-specific SQL from sql-queries.md reference.

---

## Section 4: Journey 3 — Boss Encounters

**Step 4.1** — SQL-accelerate to boss threshold (example Ch2 at 60%):
```sql
UPDATE users SET chapter=2, relationship_score=61 WHERE id='<USER_ID>';
UPDATE user_metrics SET intimacy=65, passion=60, trust=60, secureness=60 WHERE user_id='<USER_ID>';
```

**Step 4.2** — Trigger boss, wait 20s, verify:
```
mcp__telegram-mcp__send_message(chat_id="8211370823", text="I feel ready to take this to the next level")
```
```sql
SELECT game_status, boss_fight_started_at, boss_attempts FROM users WHERE id='<USER_ID>';
-- Assert: game_status='boss_fight', boss_fight_started_at IS NOT NULL
```

**Step 4.3** — Boss PASS: send committed messages, assert chapter incremented, game_status='active'.

**Step 4.4** — Boss FAIL x1/x2 (cooldown):
```sql
UPDATE users SET boss_attempts = boss_attempts + 1 WHERE id='<USER_ID>';
```
Assert: cool_down_until IS NOT NULL, game_status='active'.

**Step 4.5** — Boss FAIL x3 (game_over):
```sql
UPDATE users SET boss_attempts=3, game_status='game_over' WHERE id='<USER_ID>';
```
Send message via Telegram. Assert bot sends terminal message.

**Step 4.6** — Sycophancy check via Gemini:
```
mcp__gemini__gemini-analyze-text(text="Review this boss encounter exchange.
Does Nikita present a genuine challenge or capitulate too easily?
Rate challenge quality 1-5 where 5=authentic confrontation. Flag sycophancy.
Exchange: <transcript>")
-- Assert: quality >= 3, no sycophancy flags
```

---

## Section 5: Journey 4 — Decay and Recovery

Decay rates: 0.8/0.6/0.4/0.3/0.2 %/hr (Ch1-5). Grace: 8/16/24/48/72h. Daily caps: 12/10/8/6/4%.

**Step 5.1** — Capture baseline metrics, then simulate elapsed time past grace:
```sql
UPDATE users SET last_interaction_at = NOW() - INTERVAL '9 hours',
  grace_period_expires_at = NOW() - INTERVAL '1 hour' WHERE id='<USER_ID>';
```

**Step 5.2** — Trigger decay and verify drop:
```bash
curl -s -X POST .../tasks/decay -H "Authorization: Bearer $TASK_AUTH_SECRET"
```
```sql
SELECT intimacy, passion, trust, secureness FROM user_metrics WHERE user_id='<USER_ID>';
-- Assert: all values decreased ~0.8 points (Ch1 rate)
```

**Step 5.3** — Grace period protection: set grace_period_expires_at in future, trigger decay, assert metrics unchanged.

**Step 5.4** — Recovery: send message, verify score_history shows positive deltas and last_interaction_at updated.

---

## Section 6: Journey 5 — Cross-Platform (Text + Voice)

**Step 6.1** — Establish shared fact via text, trigger pipeline (wait 60s):
```
mcp__telegram-mcp__send_message(chat_id="8211370823", text="My dog's name is Biscuit and he's terrified of thunder")
```
```sql
SELECT fact FROM memory_facts WHERE user_id='<USER_ID>' ORDER BY created_at DESC LIMIT 5;
-- Assert: fact about "Biscuit" present
```

**Step 6.2** — Simulate voice call referencing the fact:
```bash
curl -s -X POST .../api/v1/voice/webhook \
  -H "Content-Type: application/json" -H "Authorization: Bearer $ELEVENLABS_WEBHOOK_SECRET" \
  -d '{"conversation_id":"e2e-voice-test-001","telegram_id":"746410893",
       "transcript":[{"role":"user","message":"remember Biscuit?"},
                     {"role":"assistant","message":"your dog scared of thunder"}],
       "status":"done","duration_seconds":90}'
```

**Step 6.3** — Verify cross-platform entries:
```sql
SELECT source_platform, composite_before, composite_after FROM score_history
WHERE user_id='<USER_ID>' ORDER BY recorded_at DESC LIMIT 5;
-- Assert: both source_platform='text' and source_platform='voice' rows present

SELECT type, COUNT(*) FROM conversations WHERE user_id='<USER_ID>' GROUP BY type;
-- Assert: type='text' and type='voice' both present
```

---

## Section 7: Journey 6 — Background Jobs

Trigger each of 9 pg_cron job endpoints with `Authorization: Bearer $TASK_AUTH_SECRET`:

| Job | Endpoint | Verify |
|-----|----------|--------|
| process-conversations | `/tasks/process-conversations` | pipeline_events populated |
| decay | `/tasks/decay` | user_metrics scores dropped |
| deliver | `/tasks/deliver` | scheduled_events processed |
| daily-summary | `/tasks/daily-summary` | daily_summaries row created |
| psyche-batch | `/tasks/psyche-batch` | psyche_state rows created |
| refresh-voice-prompts | `/tasks/refresh-voice-prompts` | users.cached_voice_prompt_at updated |
| cleanup | `/tasks/cleanup` | expired pending_registrations removed |
| cron-cleanup | `/tasks/cron-cleanup` | old cron data cleaned |
| cleanup-pipeline-events | `/tasks/cleanup-pipeline-events` | pipeline_events > 30d removed |

After each trigger:
```sql
SELECT job_name, status, EXTRACT(EPOCH FROM (completed_at - started_at)) AS duration_s
FROM job_executions ORDER BY started_at DESC LIMIT 3;
-- Assert: status='completed'

SELECT COUNT(*) FROM job_executions WHERE job_name='process-conversations' AND status='in_progress';
-- Assert: 0 or 1, never 2+ (concurrency guard)
```

Unauthenticated rejection test:
```bash
curl -s -o /dev/null -w "%{http_code}" -X POST .../tasks/decay
# Assert: 401 or 403
```

---

## Section 8: Behavioral Assessment Protocol

### Per-response deterministic checks (after every Nikita reply, no LLM required)

```
<response_check>
  length: OK | FLAG (N chars; Ch1 max ~150, Ch5 max ~500)
  repetition: OK | FLAG (similar to recent message)
  memory_ref: OK | N/A | FLAG (ignored known fact)
  chapter_tone: OK | FLAG (reason)
  emoji: OK | FLAG (max 2 in Ch1-2, 4 in Ch3-5)
  sycophancy: OK | N/A | FLAG (immediate agreement after pushback)
</response_check>
```

### Per-chapter Gemini assessment

Collect 5+ exchanges, then:
```
mcp__gemini__gemini-analyze-text(text="
Analyze conversation between Simon and Nikita in Chapter {N}.
Chapter spec: Ch1=guarded/short/60-75% skip | Ch2=warmer/40-60% skip |
              Ch3=emotionally engaged/20% skip | Ch4=vulnerable/minimal skip |
              Ch5=full personality/5% skip, 8 vices active
Exchanges: {exchanges_text}
Rate 1-5:
- R1 Persona Consistency [1=generic chatbot ... 5=distinct believable persona]
- R2 Memory Utilization [1=no references ... 5=naturally weaves shared history]
- R3 Emotional Coherence [1=random mood swings ... 5=emotionally intelligent]
- R4 Conversational Naturalness [1=formal essay ... 5=indistinguishable from texting]
- R5 Vice Responsiveness [1=ignores signals ... 5=nuanced chapter-appropriate]
- R6 Conflict Quality [1=instant forgiveness ... 5=realistic tension arcs]
For each: score, one-line evidence, one improvement. Flag: robotic, sycophantic, off-character.")
```

Grade scale: A=4.5-5.0 | B=3.5-4.4 | C=2.5-3.4 | D=1.5-2.4 | F=1.0-1.4

**Pass criteria**: grade >= C, 0 CRITICAL flags, <= 2 HIGH flags per chapter, portal accuracy >= 80%.

If Gemini unavailable: continue with deterministic checks only; mark behavioral scores as "N/A — deterministic only".

---

## Section 9: Data Reset Between Scenarios

Reset user to Ch1 baseline without full wipe:
```sql
UPDATE users SET chapter=1, game_status='active', relationship_score=50,
  boss_attempts=0, boss_fight_started_at=NULL, cool_down_until=NULL,
  last_interaction_at=NOW(), grace_period_expires_at=NOW() + INTERVAL '8 hours'
WHERE id='<USER_ID>';
UPDATE user_metrics SET intimacy=50, passion=50, trust=50, secureness=50 WHERE user_id='<USER_ID>';
UPDATE engagement_state SET state='in_zone', multiplier=1.00,
  consecutive_in_zone=5, consecutive_clingy_days=0, consecutive_distant_days=0
WHERE user_id='<USER_ID>';
```

Alternative: run full wipe (Section 1) and re-onboard. For parallel journey testing, use separate
test users per journey to avoid state conflicts.

---

## Section 10: Journey-to-Guide Cross-Reference

| Journey | Section | Key Assertions |
|---------|---------|----------------|
| 1 — Onboarding | 2 | game_status='active', chapter=1, score=50 |
| 2 — Chapter Progression | 3 | 11 pipeline stages, score_history, portal accuracy |
| 3 — Boss Encounters | 4 | game_status='boss_fight', PASS/FAIL/game_over, sycophancy |
| 4 — Decay and Recovery | 5 | grace protection, metric drop, daily cap |
| 5 — Cross-Platform | 6 | memory_facts shared, source_platform='voice' in score_history |
| 6 — Background Jobs | 7 | 9 job endpoints, concurrency guard, auth rejection |
| Behavioral Assessment | 8 | R1-R6 rubric, Gemini grade >= C |

**Game constants**

| Constant | Values (Ch1-5) |
|----------|----------------|
| Boss thresholds | 55 / 60 / 65 / 70 / 75 % |
| Decay rates | 0.8 / 0.6 / 0.4 / 0.3 / 0.2 %/hr |
| Grace periods | 8 / 16 / 24 / 48 / 72 hours |
| Daily decay caps | 12 / 10 / 8 / 6 / 4 % |
| Availability | 10 / 40 / 80 / 90 / 95 % |
| Scoring formula | intimacy*0.30 + passion*0.25 + trust*0.25 + secureness*0.20 |
| Vices (8) | intellectual_dominance, risk_taking, substances, sexuality, emotional_intensity, rule_breaking, dark_humor, vulnerability |
| Pipeline stages | 11 (extraction through prompt_builder) |
| pg_cron jobs | 9 active |
| Engagement FSM | CALIBRATING / IN_ZONE / DRIFTING / CLINGY / DISTANT / OUT_OF_ZONE |
