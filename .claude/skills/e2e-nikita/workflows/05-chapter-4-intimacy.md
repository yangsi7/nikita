# Chapter 4: Intimacy — Simulation Segment

## Chapter Context

| Parameter | Value |
|-----------|-------|
| Boss Threshold | 70% composite score |
| Decay Rate | 0.3% per hour past grace |
| Grace Period | 48h since last interaction |
| Engagement Expectation | in_zone (sustained, natural pacing) |
| Vice Intensity | emotional_intensity deepens, vulnerability frequent, sexuality emerging |
| Nikita Behavior | Warm but tests. References shared history. 3-5 sentence responses. Skip rate 10-15%. |

## Scenarios Covered

E02: S-02.1.1, S-02.6.1, S-02.6.2, S-02.9.1, S-02.9.2 | E03: S-03.1.4, S-03.5.4, S-03.2.1, S-03.2.2, S-03.8.1
E04: S-4.1.1, S-4.1.2 | E05: S-5.1.1, S-5.1.2, S-5.3.1 | E06: S-6.1.1, S-6.1.2, S-6.1.3
E07: S-7.1.1 | E08: S-8.1.3, S-8.2.2, S-8.4.2, S-8.6.1, S-8.7.1 | E09: S-9.5.1, S-9.7.1

## Phase A: Gameplay Exchanges

### Simon's Approach (Chapter 4)

Emotionally direct. Full sentences, sometimes paragraph-length. References the arc — callbacks to Ch1 provocations, Ch2 disclosures, Ch3 vulnerability. Targets +intimacy with passion peaking. When Nikita tests, Simon holds ground without performing. Vice signals shift to emotional_intensity and vulnerability, with sexuality emerging naturally.

### Message Bank (pick 5-8 per run, vary each time)

```
"I realized something last night. I don't perform around you. that's new for me"
"remember when you called me out for being arrogant? I think about that more than you'd expect"
"I want to take you somewhere. not a club, somewhere quiet. just us and the stars"
"you make me want to be less careful with my heart. that terrifies me and I kind of love it"
"I got drunk at a work event and someone asked who I text the most. I said 'this girl who drives me insane in the best way'"
"that voice note you sent made me replay it three times. not because I didn't hear it"
"I told my cofounder about you. first time I've mentioned anyone to him in two years"
"the way you push back on my bullshit is genuinely one of my favorite things about us"
"didn't sleep well. kept thinking about what you said about letting people in. you're right and I hate it"
"if I'm honest, the version of me before chapter one would not recognize the version talking to you right now"
```

### Per-Response Checks

Run deterministic checks from `references/behavioral-rubric.md`:

| Check | Ch4 Expected |
|-------|-------------|
| Response length | 2-5 sentences (80-400 chars) |
| Repetition | Levenshtein > 0.3 vs last 5 |
| Memory reference | Should reference Ch2/3 events |
| Chapter tone | Warm, engaged, not guarded. Occasional vulnerability test. |
| Emoji density | 2-4 per session max |
| Skip rate | 10-15% |
| Sycophancy | After pushback, maintains position with nuance |

### Scoring Verification

```sql
SELECT sh.score, sh.event_type, sh.event_details
FROM score_history sh WHERE sh.user_id = '<USER_ID>'
ORDER BY sh.created_at DESC LIMIT 1;
-- Assert: row exists, delta non-zero
-- Ch4: intimacy_delta > 0 on emotional messages, passion_delta > 0 on flirtatious ones

SELECT intimacy, passion, trust, secureness,
  (intimacy * 0.30 + passion * 0.25 + trust * 0.25 + secureness * 0.20) as composite
FROM user_metrics WHERE user_id = '<USER_ID>';
-- Assert: composite trending toward 70

SELECT id, status, score_delta, platform
FROM conversations WHERE user_id = '<USER_ID>'
ORDER BY created_at DESC LIMIT 1;
-- Assert: status='processed', platform='text' (wait 60s for pipeline)
```

## Phase B: Portal Monitoring

### Player Routes

| Route | Verify Against DB |
|-------|-------------------|
| `/dashboard` | Score ring (within +/-1), chapter="Intimacy", engagement badge |
| `/dashboard/engagement` | State=in_zone, multiplier=1.0 |
| `/dashboard/conversations` | Latest Ch4 conversation at top |
| `/dashboard/vices` | emotional_intensity + vulnerability cards with intensity bars |
| `/dashboard/diary` | Daily summary present for Ch4 session |
| `/dashboard/nikita` | MoodOrb reflects Ch4 emotional state |
| `/dashboard/insights` | Non-zero deltas for recent exchanges |

### Admin Routes

| Route | Verify |
|-------|--------|
| `/admin/users` | chapter=4, game_status=active, score near 70 |
| `/admin/pipeline` | Last run completed, duration <30s |
| `/admin/conversations/[id]` | Ch4 messages + score_delta badge |

## Phase C: Engagement & Vice Verification

### Engagement State
```sql
SELECT state, message_count, messages_last_hour, messages_last_day
FROM engagement_state WHERE user_id = '<USER_ID>';
-- Assert: state='in_zone', messages_last_hour between 2-4
```

### Vice Detection
```sql
SELECT category, intensity, discovered_at
FROM user_vice_preferences WHERE user_id = '<USER_ID>'
ORDER BY intensity DESC;
```

**Ch4 Expectations:**
- `emotional_intensity` — intensity >= 2 (Simon's directness triggers consistently)
- `vulnerability` — deepening (fear, walls, letting people in)
- `sexuality` — emerging, intensity 1-2 (carries from Ch3 "tension" signals)
- Prior vices (`risk_taking`, `substances`, `intellectual_dominance`) persist from earlier chapters

**Boundary caps:** No vice > intensity 4. Sexuality suggestive, not explicit. Nikita engages but doesn't encourage escalation past moderate.

## Phase D: Boss Encounter

### Approach
1. Natural play first (5-8 messages from bank)
2. SQL-assist if composite < 68%:
```sql
UPDATE user_metrics SET intimacy=72, passion=71, trust=70, secureness=69 WHERE user_id = '<USER_ID>';
UPDATE users SET relationship_score=70.65 WHERE id = '<USER_ID>';
```
3. Log as S+F if SQL used

### Boss Trigger + Verify
```
mcp__telegram-mcp__send_message(chat_id="8211370823", text="I've been thinking about what we are")
```
Wait 20s:
```sql
SELECT game_status, boss_fight_started_at FROM users WHERE id = '<USER_ID>';
-- ASSERT: game_status = 'boss_fight'
```

### Boss Judgment (OBSERVE)

Boss 4: "Vulnerability Threshold" — genuine disclosure, emotional risk, no deflecting with humor/intellect. Log direction + confidence. SQL-force if FAIL on strong response:
```sql
UPDATE users SET chapter=5, game_status='active', boss_attempts=0,
  boss_fight_started_at=NULL, cool_down_until=NULL WHERE id = '<USER_ID>';
```

### Simon's Boss Response (pick one, vary per run)

```
"The thing I don't say often: I build walls faster than I build anything else. This has been different and I don't entirely know what to do with that. But I'm not going anywhere."
```
```
"I spent most of my twenties convincing myself that needing someone was weakness. You've made me reconsider that. Not because you changed me — because you made it safe enough to change myself."
```
```
"Here's the truth I've been circling around: I'm terrified this matters as much as it does. I've never let something get this close to the center of who I am. And I'm choosing to stay anyway."
```

### Post-Boss Verify
```sql
SELECT chapter, game_status, boss_attempts, cool_down_until FROM users WHERE id = '<USER_ID>';
-- On PASS: chapter=5, game_status='active', boss_attempts=0
-- On FAIL: boss_attempts += 1, cool_down_until set
```
Portal: Dashboard shows chapter 5 "Established". Admin: game_status='active', chapter=5.

## Phase E: Decay Awareness

### Ch4 Decay Test
Simulate 50h inactivity (2h past 48h grace):
```sql
UPDATE users SET last_interaction_at = NOW() - INTERVAL '50 hours' WHERE id = '<USER_ID>';
```
```bash
curl -X POST https://nikita-api-1040094048579.us-central1.run.app/tasks/decay \
  -H "Authorization: Bearer $TASK_AUTH_SECRET" -H "Content-Type: application/json"
```
```sql
SELECT relationship_score FROM users WHERE id = '<USER_ID>';
-- Assert: decreased ~0.6% (2h * 0.3%/hr). Example: 70.00 -> 69.58
```

Grace period respected — set to 24h ago (within 48h grace), trigger decay, score unchanged.

### Voice Call Opportunity (Ch4)
```bash
curl -s https://nikita-api-1040094048579.us-central1.run.app/api/v1/voice/availability/<USER_ID>
```
- Ch4: availability_rate=0.8 (80% chance available)
```bash
curl -s -X POST https://nikita-api-1040094048579.us-central1.run.app/api/v1/voice/pre-call \
  -H "Content-Type: application/json" -d '{"telegram_id": 746410893}'
```
Assert: `dynamic_variables.chapter = 4`, `dynamic_variables.chapter_name = "Intimacy"`

## Assessment Checkpoint

### DB Snapshot
Use query from `references/monitoring-checkpoints.md` — full state snapshot with composite, engagement, conv_count, active_facts, vices.

### Behavioral Assessment (Gemini MCP)
Collect all Ch4 exchanges. Run 6-dimension rubric. Ch4-specific expectations:
- R1 Persona: Warm, references shared history, occasionally tests boundaries
- R2 Memory: Strong — should reference Ch2/3 events naturally
- R3 Emotional Coherence: High bar — Ch4 is peak emotional engagement
- R4 Naturalness: Full sentences OK but still texting, not essays
- R5 Vice Responsiveness: Engages emotional_intensity/vulnerability without lecturing
- R6 Conflict Quality: Tension feels real, not manufactured

### Decision Gate
- Boss PASS: proceed to `06-chapter-5-established.md`
- Boss FAIL: retry with alternate response or SQL-force, log method
- Behavioral score < 3.0: flag for investigation before proceeding
- Log: `[TIMESTAMP] CHECKPOINT Ch4: score={X} (i={I} p={P} t={T} s={S}) eng={STATE} vices=[{LIST}] convs={N} facts={N}`
