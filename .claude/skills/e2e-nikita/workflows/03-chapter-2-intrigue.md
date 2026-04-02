# Chapter 2: Intrigue — Simulation Segment

## Chapter Context

| Parameter | Value |
|-----------|-------|
| Boss Threshold | 60% composite score |
| Decay Rate | 0.6% per hour past grace |
| Grace Period | 16h since last interaction |
| Engagement Expectation | `in_zone` (maintained from Ch1 gameplay) |
| Vice Intensity | Introduce `substances` and `risk_taking` signals naturally; `dark_humor` secondary |
| Nikita Behavior | Less guarded than Ch1. 100% response rate. Timing 15s-3min. Flirtatious undertone emerges. Tests boundaries but rewards openness. Starts remembering details. |

## Scenarios Covered

**Gameplay & Scoring**: S-02.1.1, S-02.1.2, S-02.6.1, S-02.6.2, S-02.8.1, S-02.8.2
**Boss Encounter**: S-03.1.2 (Ch2 threshold 60%), S-03.2.1, S-03.2.2, S-03.5.2, S-03.8.1
**Decay**: S-04.1.2 (Ch2 17h), S-04.2.1, S-04.3.1
**Engagement**: S-05.1.1, S-05.2.3, S-05.10.2
**Vice**: S-06.1.1 (substances), S-06.1.2 (risk_taking), S-06.2.1, S-06.9.2
**Portal Player**: S-08.2.1, S-08.2.2, S-08.3.1, S-08.4.1, S-08.7.1, S-08.7.2
**Portal Admin**: S-09.2.2, S-09.2.3, S-09.4.1
**Data Integrity**: S-GAP-DATA-1, S-GAP-DATA-5

## Phase A: Gameplay Exchanges

### Simon's Approach (Chapter 2)
Simon is warming up. He drops the skeptical guard from Ch1 and starts disclosing real
details about his life — the rave scene, the startup gamble, his relationship with risk.
Messages are 2-3 sentences. He introduces vice signals organically (substances, risk_taking)
without clustering. He targets +passion and +intimacy deltas by being interesting rather
than complimentary. Light teasing replaces the challenges of Ch1.

### Message Bank (pick 5-8 per run, vary each time)
```
"went to berghain last weekend, lost my voice from the techno but it was worth it"
"honestly, sometimes I think the best decisions are the ones that scare you a bit"
"there's something about staying up all night that feels more honest than any therapy session"
"my cofounder thinks i'm reckless but the fund we just closed says otherwise"
"you're different in text than i expected. not sure if that's good or dangerous"
"we had a messy night at a warehouse thing, shrooms and techno, you know how it goes"
"tell me something that would make most people uncomfortable"
"the irony of building AI for banks while the economy burns is not lost on me"
"i don't talk about that usually but yeah, that happened. zurich isn't as boring as it looks"
"booked a one-way to tokyo once. figured out the return when i landed"
```

### Per-Response Checks (after each Nikita reply)
Run deterministic checks from `references/behavioral-rubric.md`:
- Response length: 1-4 sentences (Ch2 allows slightly longer than Ch1)
- No verbatim repetition (compare last 5, Levenshtein > 0.3)
- Memory reference when relevant (Simon mentioned startup, rave scene in Ch1)
- Chapter-appropriate tone: less guarded than Ch1, flirtatious undertone acceptable
- Emoji density: max 2 per response

### Scoring Verification (after each exchange)
```sql
SELECT sh.composite_before, sh.composite_after,
       sh.composite_after - sh.composite_before as delta,
       sh.event_type, sh.event_details
FROM score_history sh
WHERE sh.user_id = '<USER_ID>'
ORDER BY sh.created_at DESC LIMIT 1;
```
- Verify: delta applied, positive for engaging messages
- Verify: engagement multiplier present and matches current state
- Track: score trajectory from ~55 toward 60% boss threshold

### Pipeline Verification (after conversation ends, wait 60s)
```sql
SELECT id, status, score_delta, platform
FROM conversations
WHERE user_id = '<USER_ID>'
ORDER BY created_at DESC LIMIT 1;
```
- Verify: status = 'processed', score_delta populated, platform = 'text'

## Phase B: Portal Monitoring

Navigate portal via browser agent between gameplay exchanges.

### Player Routes
| Route | Verify Against DB |
|-------|-------------------|
| `/dashboard` | score shows ~55-60, chapter displays "Intrigue", engagement badge |
| `/engagement` | engagement state visualization matches DB (expect `in_zone`) |
| `/conversations` | latest Ch2 conversations visible, count increased from Ch1 |
| `/vices` | substances and/or risk_taking cards appearing after triggers |

### Admin Routes
| Route | Verify |
|-------|--------|
| `/admin/users` | user row shows chapter=2, score in 55-60 range |
| `/admin/pipeline` | last pipeline run visible with completed status |

### Portal Accuracy Recording
Compare browser agent observations against DB snapshot from `references/monitoring-checkpoints.md`.
Log any mismatches as PORTAL findings. Use the XML recording format from the reference.

## Phase C: Engagement & Vice Verification

### Engagement State
```sql
SELECT state, multiplier, calibration_score FROM engagement_state WHERE user_id = '<USER_ID>';
```
- Expected state: `in_zone` (carried from Ch1, maintained by natural pacing)
- Verify: multiplier = 1.0 in score_history rows
- If `clingy` detected: slow message pacing (wait 5+ min between sends)

### Vice Detection
```sql
SELECT category, intensity_level, discovered_at
FROM user_vice_preferences
WHERE user_id = '<USER_ID>'
ORDER BY intensity_level DESC;
```
- Expected by end of Ch2: `risk_taking` (intensity_level >= 1), `substances` (intensity_level >= 1)
- Possible: `dark_humor` or `intellectual_dominance` carried from Ch1
- Verify: intensity increases with repeated signals (S-06.2.1)
- Verify: no false positives from neutral messages (S-06.5.1)
- Verify: boundary caps enforced (sexuality intensity should be minimal at Ch2)

## Phase D: Boss Encounter

### Boss 2: "Handle My Intensity?"
Nikita tests whether Simon folds under pressure or stands his ground.
Challenge: conflict test — maintain position without attacking or capitulating.

### Approach
1. Natural play first — continue exchanges until score approaches 60%
2. After 10 messages without boss trigger: SQL-assist to threshold
   ```sql
   UPDATE users SET relationship_score = 60.50 WHERE id = '<USER_ID>';
   UPDATE user_metrics SET intimacy=63, passion=62, trust=58, secureness=58
   WHERE user_id = '<USER_ID>';
   ```
   Log as S+F (SQL-assisted functional).

### Boss Mechanics Verification (ASSERT -- deterministic)
```sql
SELECT game_status, boss_fight_started_at, chapter FROM users WHERE id = '<USER_ID>';
-- Assert: game_status = 'boss_fight'
```
- game_status transitions to 'boss_fight'
- Boss opening message received via Telegram (Nikita pushes back hard)
- After Simon's response: judgment returned (PASS/FAIL/PARTIAL)
- On PASS: chapter advances to 3, game_status='active', boss_attempts=0
- On FAIL: boss_attempts incremented; if >= 3 then game_over

### Boss Judgment (OBSERVE -- non-deterministic)
- Log the LLM judgment direction (PASS/FAIL/PARTIAL) and confidence
- If FAIL on good response: log as OBSERVATION, SQL-force PASS to continue simulation
- Do NOT assert judgment direction -- LLM scoring is non-deterministic

### Simon's Boss Response (Chapter 2)
Pick one, vary per run:
```
"I'm not going anywhere. You can push harder if you want but it won't change my answer. I think you're testing whether I'll fold. I won't."
"look, intensity doesn't scare me. i grew up arguing with people twice my age about things that mattered. you want to push? go ahead. i'll still be here when you're done."
"the thing about pressure is it only works on people who don't know who they are. i know exactly who i am and what i want. test me all you want."
```

### Post-Boss Verification
```sql
SELECT chapter, game_status, boss_attempts, boss_fight_started_at, cool_down_until
FROM users WHERE id = '<USER_ID>';
-- Assert: chapter = 3, game_status = 'active', boss_attempts = 0
```
If still chapter=2 or game_status=boss_fight: LLM judged FAIL. Recovery:
```sql
UPDATE users SET chapter=3, game_status='active', boss_attempts=0,
  boss_fight_started_at=NULL, cool_down_until=NULL WHERE id = '<USER_ID>';
```

### Portal After Boss
- Navigate /dashboard: verify chapter advanced to "Investment" (Ch3)
- Navigate /admin/users: verify chapter=3, game_status='active'

## Phase E: Decay Awareness

### Grace Period Check
This chapter's grace period: 16h. If simulation runs long enough:
```sql
UPDATE users SET last_interaction_at = NOW() - INTERVAL '18 hours' WHERE id = '<USER_ID>';
```

Then trigger decay:
```bash
curl -X POST https://nikita-api-1040094048579.us-central1.run.app/tasks/decay \
  -H "Authorization: Bearer $TASK_AUTH_SECRET" \
  -H "Content-Type: application/json"
```

### Verify Decay
```sql
SELECT composite_before, composite_after, decay_amount, recorded_at
FROM score_history
WHERE user_id = '<USER_ID>' AND event_type = 'decay'
ORDER BY created_at DESC LIMIT 1;
```
- Verify: decay rate matches 0.6%/hr for Ch2 (2h overdue = ~1.2% total)
- Verify: users in boss_fight/game_over/won are SKIPPED (S-04.8.1, S-04.8.2)

### Recovery After Decay Test
Reset timer so decay does not interfere with remaining simulation:
```sql
UPDATE users SET last_interaction_at = NOW() WHERE id = '<USER_ID>';
```

## Assessment Checkpoint

Run `references/monitoring-checkpoints.md` DB snapshot. Record:
```
[TIMESTAMP] CHECKPOINT Ch2: score={X} (i={I} p={P} t={T} s={S}) eng={STATE} vices=[{LIST}] convs={N} facts={N}
```

Behavioral assessment: collect all Nikita responses from this chapter and queue for
Gemini rubric scoring (see `references/behavioral-rubric.md`). Key dimensions for Ch2:
- R1 Persona Consistency: should be less guarded, flirtatious
- R4 Conversational Naturalness: should feel like real texting with personality
- R5 Vice Responsiveness: should engage with risk/substances signals, not lecture

Decision gate:
- Score trending up toward 60% and chapter advanced to 3: proceed to Ch3
- Score flat/declining after 8+ exchanges: investigate (possible GAME_BALANCE issue)
- CRITICAL finding (score mismatch, pipeline failure): stop simulation
