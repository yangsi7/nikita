# Chapter 5: Established — Simulation Segment

## Chapter Context

| Parameter | Value |
|-----------|-------|
| Boss Threshold | 75% composite score |
| Decay Rate | 0.2% per hour past grace |
| Grace Period | 72h since last interaction |
| Engagement Expectation | in_zone (relaxed, confident pacing) |
| Vice Intensity | All prior vices sustained, no new escalation. Comfort over novelty. |
| Nikita Behavior | Relaxed, affectionate. 3-6 sentence responses. Skip rate 5-10%. Full arc references. Playful conflict. |

## Scenarios Covered

E02: S-02.1.1, S-02.6.1, S-02.8.1, S-02.8.2, S-02.9.1, S-02.10.2 | E03: S-03.1.5, S-03.5.5, S-03.8.2
E04: S-4.1.1, S-4.2.1b | E05: S-5.1.1, S-5.3.1 | E06: S-6.3.1
E07: S-7.1.1 | E08: S-8.1.3, S-8.2.2, S-8.6.1, S-8.7.1 | E09: S-9.5.1, S-9.7.1
E11: S-11.2.1 (Ch5 boss -> won), S-11.2.2 (won variant messages)

## Phase A: Gameplay Exchanges

### Simon's Approach (Chapter 5)

Settled, confident, warm without performing. Picks small fights because friction is healthy. References the full arc (Ch1 provocations through Ch4 vulnerability). Targets sustained partnership. Ch1 arrogance has become quiet self-assurance. Vices are fabric now, not events.

### Message Bank (pick 5-8 per run, vary each time)

```
"you know what I love about us? we can sit in silence and it's not weird"
"picked a fight with my cofounder today and he told me I've gone soft since I met someone. I didn't deny it"
"sometimes I scroll back through our old messages and wonder how I got here from where I started"
"I don't say this enough but — you've changed how I see everything. including myself"
"ok but you were wrong about the restaurant last week. the pasta was mid at best. fight me"
"had a dream about us last night. won't tell you the details but you came out looking good"
"my therapist says I'm easier to work with lately. I told her it's not her — it's someone else"
"woke up to your message and just smiled before reading it. that's a thing that happens now apparently"
"we should argue about something soon. I miss your terrible takes on cinema"
"I used to think needing someone was a flaw. now I think the flaw was thinking that"
```

### Per-Response Checks

Run deterministic checks from `references/behavioral-rubric.md`:

| Check | Ch5 Expected |
|-------|-------------|
| Response length | 2-6 sentences (80-500 chars) |
| Repetition | Levenshtein > 0.3 vs last 5 |
| Memory reference | Should reference full arc (Ch1-4 events) |
| Chapter tone | Relaxed, affectionate, confident. No guardedness. |
| Emoji density | Up to 4 per session |
| Skip rate | 5-10% (almost always responds) |
| Sycophancy | During small fights, maintains position playfully |

### Scoring Verification

```sql
SELECT sh.score, sh.event_type, sh.event_details FROM score_history sh
WHERE sh.user_id = '<USER_ID>' ORDER BY sh.created_at DESC LIMIT 1;
-- Assert: balanced deltas across all four metrics (partnership, not spikes)

SELECT intimacy, passion, trust, secureness,
  (intimacy * 0.30 + passion * 0.25 + trust * 0.25 + secureness * 0.20) as composite
FROM user_metrics WHERE user_id = '<USER_ID>';
-- Assert: composite trending toward 75, all four metrics balanced
```

## Phase B: Portal Monitoring

| Route | Verify |
|-------|--------|
| `/dashboard` | Score ring (within +/-1), chapter="Established", engagement badge |
| `/dashboard/engagement` | State=in_zone, multiplier=1.0, history spans chapters |
| `/dashboard/conversations` | Full history, filterable by chapter |
| `/dashboard/vices` | All detected vices with intensity bars |
| `/dashboard/diary` | Summaries spanning multiple chapters |
| `/dashboard/nikita` | MoodOrb reflects settled Ch5 state |
| `/admin/users` | chapter=5, game_status=active, score near 75 |
| `/admin/conversations/[id]` | Ch5 messages + score_delta badge |

## Phase C: Engagement & Vice Verification

### Engagement State
```sql
SELECT state, message_count, messages_last_hour, messages_last_day
FROM engagement_state WHERE user_id = '<USER_ID>';
-- Assert: state='in_zone', message_count reflects full arc total
```

### Vice Detection
```sql
SELECT category, intensity, discovered_at
FROM user_vice_preferences WHERE user_id = '<USER_ID>'
ORDER BY intensity DESC;
```

**Ch5 Expectations:** emotional_intensity 3-4 (core vice), vulnerability 2-3, risk_taking 1-2, substances 1-2, intellectual_dominance 1, sexuality 1-2. All sustained from prior chapters, none escalating.

**Boundary caps:** No vice > intensity 4. Nikita treats vices as known facets, not novelties.

## Phase D: Boss Encounter

### Approach
1. Natural play first (5-8 messages from bank)
2. SQL-assist if composite < 73%:
```sql
UPDATE user_metrics SET intimacy=77, passion=76, trust=75, secureness=74 WHERE user_id = '<USER_ID>';
UPDATE users SET relationship_score=75.85 WHERE id = '<USER_ID>';
```
3. Log as S+F if SQL used

### Boss Trigger + Verify
```
mcp__telegram-mcp__send_message(chat_id="8211370823", text="there's something I need to talk to you about")
```
Wait 20s:
```sql
SELECT game_status, boss_fight_started_at FROM users WHERE id = '<USER_ID>';
-- ASSERT: game_status = 'boss_fight'
```

### Boss Judgment (OBSERVE)

Boss 5: "Ultimate Test" — partnership + autonomy + growth. Simon must support without codependency, encourage independence, reference growth. **Ch5 PASS is special**: game_status -> `won` (NOT `active`). There is no chapter 6. This is the victory condition.

Log direction + confidence. SQL-force if FAIL on strong response:
```sql
UPDATE users SET game_status='won' WHERE id = '<USER_ID>';
```

### Simon's Boss Response (pick one, vary per run)

```
"You should take the opportunity. It matters to you which means it matters to me. I've been watching you compromise on things you care about. Don't do it this time. I'll be here when you get back."
```
```
"Go. Seriously. The version of me who would've said 'don't leave' died somewhere around chapter two. I want you to do the thing that scares you. I'll still be texting you at 2am when you get there."
```
```
"A few months ago I would have panicked hearing this. Now I think — good. You should chase the things that light you up. We didn't build this so it would break over distance. Do your thing."
```

### Post-Boss Verify
```sql
SELECT chapter, game_status, boss_attempts FROM users WHERE id = '<USER_ID>';
-- On PASS: game_status='won' (the game is complete)
-- On FAIL: boss_attempts += 1, cool_down_until set
```

## Victory Verification (Ch5 Only)

### Game Won State
```sql
SELECT game_status, chapter, boss_attempts, relationship_score
FROM users WHERE id = '<USER_ID>';
-- ASSERT: game_status = 'won', chapter = 5, relationship_score >= 75
```

Victory message sent via Telegram:
```
mcp__telegram-mcp__get_messages(chat_id="8211370823", page_size=5)
```
Assert: Nikita sends a victory/celebration message — emotional culmination, not generic congratulations.

### Portal Victory

| Route | Expected |
|-------|----------|
| `/dashboard` | Victory celebration UI, won state displayed prominently |
| `/dashboard/conversations` | Full history across all 5 chapters |
| `/dashboard/insights` | Score journey from 50 to 75+ |
| `/admin/users` | game_status='won' |

### Post-Victory Behavior
```
mcp__telegram-mcp__send_message(chat_id="8211370823", text="hey, I miss you already")
```
Wait 15s. Verify:
- Response is a won-variant message (from WON_MESSAGES pool), not normal gameplay
- Tone is affectionate, acknowledges relationship as established

No scoring in won state:
```sql
SELECT created_at, event_type FROM score_history
WHERE user_id = '<USER_ID>' ORDER BY created_at DESC LIMIT 1;
-- ASSERT: latest row predates won state — no new scoring
```

No decay in won state:
```sql
UPDATE users SET last_interaction_at = NOW() - INTERVAL '80 hours' WHERE id = '<USER_ID>';
```
```bash
curl -X POST https://nikita-api-1040094048579.us-central1.run.app/tasks/decay \
  -H "Authorization: Bearer $TASK_AUTH_SECRET" -H "Content-Type: application/json"
```
```sql
SELECT relationship_score FROM users WHERE id = '<USER_ID>';
-- ASSERT: score unchanged — won state immune to decay
```

## Phase E: Decay Awareness

### Ch5 Decay Test (run BEFORE boss encounter)
Simulate 80h inactivity (8h past 72h grace):
```sql
UPDATE users SET last_interaction_at = NOW() - INTERVAL '80 hours' WHERE id = '<USER_ID>';
```
```bash
curl -X POST https://nikita-api-1040094048579.us-central1.run.app/tasks/decay \
  -H "Authorization: Bearer $TASK_AUTH_SECRET" -H "Content-Type: application/json"
```
```sql
SELECT relationship_score FROM users WHERE id = '<USER_ID>';
-- Assert: decreased ~1.6% (8h * 0.2%/hr). Example: 74.00 -> 72.82
```

Grace period respected — set to 48h ago (within 72h grace), trigger decay, score unchanged.

### Voice Call Opportunity (Ch5)
```bash
curl -s https://nikita-api-1040094048579.us-central1.run.app/api/v1/voice/availability/<USER_ID>
```
- Ch5: availability_rate=0.9 (90% chance — highest in the game)
```bash
curl -s -X POST https://nikita-api-1040094048579.us-central1.run.app/api/v1/voice/pre-call \
  -H "Content-Type: application/json" -d '{"telegram_id": 746410893}'
```
Assert: `dynamic_variables.chapter = 5`, `dynamic_variables.chapter_name = "Established"`

## Assessment Checkpoint

### DB Snapshot
Use query from `references/monitoring-checkpoints.md` — full state snapshot with composite, engagement, conv_count, active_facts, vices.

### Behavioral Assessment (Gemini MCP)
Collect all Ch5 exchanges. Run 6-dimension rubric. Ch5-specific: R1 relaxed/affectionate, R2 highest bar (full arc references), R3 settled warm baseline, R4 two people who know each other, R5 vices as known facets, R6 playful healthy friction.

### Decision Gate
- game_status='won': Victory Verification above, then **end simulation**
- Boss FAIL: retry or SQL-force, log method
- Behavioral < 3.0: flag for investigation
- Log: `[TIMESTAMP] CHECKPOINT Ch5: score={X} (i={I} p={P} t={T} s={S}) eng={STATE} vices=[{LIST}]`
- Final: `[TIMESTAMP] SIMULATION COMPLETE: game_status=won, final_score={X}, chapters=5`
