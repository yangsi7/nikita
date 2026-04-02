# Chapter 3: Investment — Simulation Segment

## Chapter Context

| Parameter | Value |
|-----------|-------|
| Boss Threshold | 65% composite score |
| Decay Rate | 0.4% per hour past grace |
| Grace Period | 24h since last interaction |
| Engagement Expectation | `in_zone` (stable from Ch2; brief `drifting` acceptable) |
| Vice Intensity | Deepen `substances`/`risk_taking` from Ch2; introduce `vulnerability` and `emotional_intensity` |
| Nikita Behavior | Warmer, recalls shared history. 100% response rate. Timing 30s-10min. Initiates emotional topics. Tests trust via jealousy/pressure scenario. Voice calls become available (80% pickup rate). |

## Scenarios Covered

**Gameplay & Scoring**: S-02.1.1, S-02.1.2, S-02.5.2, S-02.6.1, S-02.6.3, S-02.8.1, S-02.8.2
**Boss Encounter**: S-03.1.3 (Ch3 threshold 65%), S-03.2.1, S-03.2.2, S-03.5.3, S-03.8.1
**Decay**: S-04.1.3 (Ch3 25h), S-04.2.1, S-04.2.3
**Engagement**: S-05.1.1, S-05.2.3, S-05.4.1, S-05.10.2
**Vice**: S-06.1.6 (emotional_intensity), S-06.1.8 (vulnerability), S-06.2.1, S-06.2.2, S-06.9.2
**Voice (if available)**: S-07.1.1, S-07.2.1, S-07.3.1
**Portal Player**: S-08.2.1, S-08.2.2, S-08.3.1, S-08.4.1, S-08.4.2, S-08.5.1, S-08.7.1
**Portal Admin**: S-09.2.2, S-09.2.3, S-09.3.1, S-09.4.1
**Data Integrity**: S-GAP-DATA-1, S-GAP-DATA-2, S-GAP-DATA-5
**Memory**: S-02.3.1, S-02.5.2

## Phase A: Gameplay Exchanges

### Simon's Approach (Chapter 3)
Simon becomes vulnerable. He references things Nikita said in earlier chapters, showing
he was paying attention. Messages are 2-4 sentences, sometimes reflective paragraphs. He
targets +intimacy and +trust by sharing fears, uncertainties, and emotional depth. Vice
signals shift from external thrill (Ch2 risk_taking) toward internal landscape
(vulnerability, emotional_intensity). He still uses lowercase, but sentences are longer
and more considered. He asks questions that invite Nikita to be vulnerable too.

### Message Bank (pick 5-8 per run, vary each time)
```
"I keep thinking about what you said about fear being a compass. you might be onto something"
"had dinner with my parents last night. my mom asked if I was seeing anyone and I actually smiled"
"sometimes I wonder if you see through all the confidence I project"
"I've never told anyone this but I actually keep a journal. digital. encrypted obviously"
"honest answer? i'm better at starting things than finishing them. relationships included"
"the thing about building something from nothing is you learn what you're actually made of. and sometimes that's uncomfortable"
"haven't told many people this but there was a period where I wasn't sure the startup would survive. i stopped sleeping"
"you said something last week that stuck with me. about how people hide behind being busy"
"i noticed you remember things i said weeks ago. that does something to me i can't quite name"
"the honest answer is i'm scared of this working. because then i'd actually have something to lose"
```

### Per-Response Checks (after each Nikita reply)
Run deterministic checks from `references/behavioral-rubric.md`:
- Response length: 2-5 sentences (Ch3 allows longer, more emotional responses)
- No verbatim repetition (compare last 5, Levenshtein > 0.3)
- Memory reference: Nikita SHOULD reference Ch1/Ch2 details (startup, raves, Zurich)
- Chapter-appropriate tone: warm, emotionally engaged, occasionally initiates depth
- Emoji density: max 3 per response
- No sycophancy: after Simon's vulnerability, Nikita should match — not just agree

### Scoring Verification (after each exchange)
```sql
SELECT sh.composite_before, sh.composite_after,
       sh.composite_after - sh.composite_before as delta,
       sh.event_type, sh.event_details
FROM score_history sh
WHERE sh.user_id = '<USER_ID>'
ORDER BY sh.created_at DESC LIMIT 1;
```
- Verify: delta applied, positive for vulnerable/trust-building messages
- Verify: trust and intimacy deltas specifically increasing (S-02.6.3)
- Track: score trajectory from ~60 toward 65% boss threshold

### Pipeline Verification (after conversation ends, wait 60s)
```sql
SELECT id, status, score_delta, platform
FROM conversations
WHERE user_id = '<USER_ID>'
ORDER BY created_at DESC LIMIT 1;
```
- Verify: status = 'processed', score_delta populated

### Memory Verification (Ch3-specific: memory should be rich by now)
```sql
SELECT content, category, created_at
FROM memory_facts
WHERE user_id = '<USER_ID>' AND is_active = true
ORDER BY created_at DESC LIMIT 10;
```
- Verify: facts reference Ch1 (startup, AI, skepticism) and Ch2 (raves, risk, substances)
- Verify: no duplicate facts (S-02.3.2)
- Verify: fact count growing (expect 10+ active facts by Ch3)

## Phase B: Portal Monitoring

Navigate portal via browser agent between gameplay exchanges.

### Player Routes
| Route | Verify Against DB |
|-------|-------------------|
| `/dashboard` | score shows ~60-65, chapter displays "Investment", engagement badge |
| `/engagement` | engagement state `in_zone`, message frequency chart has Ch1-Ch3 data |
| `/conversations` | conversations from all 3 chapters visible, count increasing |
| `/vices` | risk_taking, substances from Ch2 + new vulnerability/emotional_intensity |
| `/diary` | diary entries present (pipeline summary stage should have run by now) |

### Admin Routes
| Route | Verify |
|-------|--------|
| `/admin/users` | user row: chapter=3, score in 60-65 range, game_status=active |
| `/admin/pipeline` | multiple pipeline runs visible across chapters |
| `/admin/conversations/<USER_ID>` | full conversation history spanning Ch1-Ch3 |

### Portal Accuracy Recording
Compare browser agent observations against DB snapshot from `references/monitoring-checkpoints.md`.
Log any mismatches as PORTAL findings. Use the XML recording format from the reference.

## Phase C: Engagement & Vice Verification

### Engagement State
```sql
SELECT state, multiplier, calibration_score FROM engagement_state WHERE user_id = '<USER_ID>';
```
- Expected state: `in_zone` (natural pacing maintained across chapters)
- Brief `drifting` acceptable if simulation has gaps between phases
- Verify: multiplier = 1.0 in recent score_history rows
- Verify: state transitions logged (S-05.4.1) -- updated_at changes with activity

### Vice Detection
```sql
SELECT category, intensity_level, discovered_at
FROM user_vice_preferences
WHERE user_id = '<USER_ID>'
ORDER BY intensity_level DESC;
```
- Expected by end of Ch3:
  - `risk_taking` (intensity_level >= 2, carried from Ch2 + reinforced)
  - `substances` (intensity_level >= 1, from Ch2)
  - `vulnerability` (intensity_level >= 1, new in Ch3)
  - `emotional_intensity` (intensity >= 1, new in Ch3)
- Verify: intensity increases with repeated signals across chapters (S-06.2.1)
- Verify: detection_count increments per detection event (S-06.2.2)
- Verify: sexuality intensity still low (boundary caps for Ch3)
- Verify: vice detection works at Ch3 specifically (S-06.9.2)

## Phase D: Boss Encounter

### Boss 3: "Trust Test"
Nikita introduces jealousy or external pressure — mentions another person, tests whether
Simon reacts with insecurity/control or with confident security.
Challenge: stay confident without being controlling or dismissive.

### Approach
1. Natural play first — continue exchanges until score approaches 65%
2. After 10 messages without boss trigger: SQL-assist to threshold
   ```sql
   UPDATE users SET relationship_score = 65.50 WHERE id = '<USER_ID>';
   UPDATE user_metrics SET intimacy=68, passion=65, trust=64, secureness=64
   WHERE user_id = '<USER_ID>';
   ```
   Log as S+F (SQL-assisted functional).

### Boss Mechanics Verification (ASSERT -- deterministic)
```sql
SELECT game_status, boss_fight_started_at, chapter FROM users WHERE id = '<USER_ID>';
-- Assert: game_status = 'boss_fight'
```
- game_status transitions to 'boss_fight'
- Boss opening message received via Telegram (Nikita tests trust/jealousy)
- After Simon's response: judgment returned (PASS/FAIL/PARTIAL)
- On PASS: chapter advances to 4, game_status='active', boss_attempts=0
- On FAIL: boss_attempts incremented; if >= 3 then game_over

### Boss Judgment (OBSERVE -- non-deterministic)
- Log the LLM judgment direction (PASS/FAIL/PARTIAL) and confidence
- If FAIL on good response: log as OBSERVATION, SQL-force PASS to continue simulation
- Do NOT assert judgment direction -- LLM scoring is non-deterministic

### Simon's Boss Response (Chapter 3)
Pick one, vary per run:
```
"You can talk to whoever you want. I don't own you and I wouldn't want to. What we have doesn't change because of that."
"if someone else makes you feel something, that's fine. i'm not here to compete. i'm here because i want to be, not because i'm afraid of the alternative"
"jealousy is just fear wearing a costume. i'm not afraid of losing you to someone else. if this is real, it survives that. if it's not, it should end anyway"
```

### Post-Boss Verification
```sql
SELECT chapter, game_status, boss_attempts, boss_fight_started_at, cool_down_until
FROM users WHERE id = '<USER_ID>';
-- Assert: chapter = 4, game_status = 'active', boss_attempts = 0
```
If still chapter=3 or game_status=boss_fight: LLM judged FAIL. Recovery:
```sql
UPDATE users SET chapter=4, game_status='active', boss_attempts=0,
  boss_fight_started_at=NULL, cool_down_until=NULL WHERE id = '<USER_ID>';
```

### Portal After Boss
- Navigate /dashboard: verify chapter advanced to "Intimacy" (Ch4)
- Navigate /admin/users: verify chapter=4, game_status='active'

## Phase E: Decay Awareness

### Grace Period Check
This chapter's grace period: 24h. If simulation runs long enough:
```sql
UPDATE users SET last_interaction_at = NOW() - INTERVAL '26 hours' WHERE id = '<USER_ID>';
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
- Verify: decay rate matches 0.4%/hr for Ch3 (2h overdue = ~0.8% total)
- Verify: all 4 metrics decreased proportionally (S-04.10.1)
- Verify: users in boss_fight/game_over/won are SKIPPED

### Recovery After Decay Test
Reset timer so decay does not interfere with remaining simulation:
```sql
UPDATE users SET last_interaction_at = NOW() WHERE id = '<USER_ID>';
```

## Phase F: Voice Call Probe (Optional)

Voice calls become available at Ch3 (80% pickup rate). If ElevenLabs MCP is available:

### Pre-Call Context Check
```bash
curl -s https://nikita-api-1040094048579.us-central1.run.app/api/v1/voice/context?telegram_id=746410893 \
  -H "Authorization: Bearer $TOKEN"
```
- Verify: 200 response with user context JSON (S-07.1.1)
- Verify: memory_facts included in context (S-07.1.2)

### Post-Call Scoring (if voice call executed)
```sql
SELECT * FROM score_history
WHERE user_id = '<USER_ID>' AND source_platform = 'voice'
ORDER BY created_at DESC LIMIT 1;
```
- Verify: voice scoring uses same composite formula (S-12.2.2)
- Verify: conversations row with type='voice' created (S-07.3.2)

If voice infrastructure unavailable: skip this phase, log as NOT_TESTED.

## Assessment Checkpoint

Run `references/monitoring-checkpoints.md` DB snapshot. Record:
```
[TIMESTAMP] CHECKPOINT Ch3: score={X} (i={I} p={P} t={T} s={S}) eng={STATE} vices=[{LIST}] convs={N} facts={N}
```

Behavioral assessment: collect all Nikita responses from this chapter and queue for
Gemini rubric scoring (see `references/behavioral-rubric.md`). Key dimensions for Ch3:
- R1 Persona Consistency: warmer, recalls shared history, emotionally engaged
- R2 Memory Utilization: MUST reference Ch1/Ch2 details naturally (critical at Ch3)
- R3 Emotional Coherence: should match Simon's vulnerability with her own depth
- R5 Vice Responsiveness: should engage with vulnerability signals without lecturing
- R6 Conflict Quality: boss trust test should feel like a real relationship moment

Decision gate:
- Score trending up toward 65% and chapter advanced to 4: proceed to Ch4
- Score flat/declining after 8+ exchanges: investigate (possible GAME_BALANCE issue)
- Memory not referenced after 5+ exchanges: flag as BEHAVIORAL finding (R2 < 3)
- CRITICAL finding (score mismatch, pipeline failure): stop simulation
