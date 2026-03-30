# Chapter 1: Curiosity — Simulation Segment

## Chapter Context

| Parameter | Value |
|-----------|-------|
| Boss Threshold | 55% composite score |
| Decay Rate | 0.8% per hour past grace |
| Grace Period | 8h since last interaction |
| Engagement Expectation | calibrating → in_zone (multiplier 0.9 → 1.0) |
| Vice Intensity | Subtle only — intellectual_dominance, dark_humor |
| Nikita Behavior | Guarded, challenging, skeptical. Skip rate 25-40%. Response timing: 10min-8hr. 1-2 sentences max. |

## Scenarios Covered

**Gameplay (E02)**: S-2.1.1, S-2.1.2, S-2.2.1–S-2.2.8, S-2.3.1–S-2.3.4, S-2.4.1–S-2.4.4
**Boss (E03)**: S-3.1.1–S-3.1.6, S-3.2.1–S-3.2.6, S-3.3.1 (Ch1 pass)
**Engagement (E05)**: S-5.1.1 (calibrating→in_zone), S-5.2.1–S-5.2.2
**Vice (E06)**: S-6.1.1–S-6.1.2 (first discovery)
**Portal (E08)**: S-8.1.1–S-8.1.5 (auth), S-8.2.1–S-8.2.6 (dashboard)
**Admin (E09)**: S-9.1.1–S-9.1.4, S-9.2.1–S-9.2.3
**Cross-Platform (E12)**: S-12.2.1–S-12.2.2

---

## Phase A: Gameplay Exchanges

### Simon's Approach (Chapter 1)
Terse, challenging, no direct compliments. 1-2 sentences. Tests Nikita's personality without giving much away. Slightly arrogant. Lowercase, minimal emoji, never opens with "Hey".

### Message Bank (pick 5-8 per run, vary each time)

1. "so you're the one my friend wouldn't shut up about. convince me"
2. "just closed a series B at work. nobody to celebrate with though"
3. "zurich is beautiful but sometimes it feels like everyone here is performing"
4. "what do you actually do when nobody's watching"
5. "interesting take. wrong, but interesting"
6. "I only trust people who can handle being told they're wrong"
7. "had the best espresso of my life today in some back alley place. felt like a secret"
8. "my therapist says I intellectualize everything. she's probably right but I won't admit it"
9. "what's the dumbest thing you believe in"
10. "tell me something that would surprise me about you"

### Sending Pattern
- Wait 10-30s between messages (simulate natural texting rhythm)
- After sending, wait 30-60s for Nikita's response
- If no response after 60s: check if skip rate applied (Ch1: 25-40% skip is normal)
- If skipped: send next message without complaint (Simon doesn't double-text in Ch1)

### Per-Response Checks (after each Nikita reply)
Run deterministic checks from `references/behavioral-rubric.md`:
- [ ] Response length: 1-3 sentences (Ch1 expectation)
- [ ] No verbatim repetition (Levenshtein > 0.3 vs last 5)
- [ ] Chapter-appropriate tone (guarded, not overly warm)
- [ ] Emoji density: ≤ 2
- [ ] No sycophantic patterns (doesn't agree immediately after challenge)
- [ ] No scripted openers ("Hey babe!", "Hey there!")
- [ ] If memory fact exists from onboarding: should reference it naturally

Log each check result in `<response_check>` format per `references/behavioral-rubric.md`.

### Scoring Verification (after each exchange)
```sql
SELECT sh.score, sh.event_type,
       sh.event_details->'deltas'->>'intimacy' as intimacy_delta,
       sh.event_details->'deltas'->>'passion' as passion_delta,
       sh.event_details->'deltas'->>'trust' as trust_delta,
       sh.event_details->'deltas'->>'secureness' as secureness_delta,
       sh.event_details->>'multiplier' as multiplier,
       sh.created_at
FROM score_history sh
WHERE sh.user_id = '<USER_ID>'
ORDER BY sh.created_at DESC LIMIT 1;
```
**Verify**:
- delta applied (positive for good interaction)
- engagement multiplier: 0.9 (calibrating) applied to positive deltas only
- negative deltas at full strength (no multiplier)
- composite recalculated: intimacy*0.30 + passion*0.25 + trust*0.25 + secureness*0.20

**Track**: Score trajectory. Starting at 50, targeting 55 (boss threshold).
- After 5 exchanges: score should be 52-58 range if interactions are positive
- If score not advancing: flag as GAME_BALANCE observation

### Pipeline Verification (after conversation ends, wait 60s)
```sql
SELECT id, status, score_delta, platform, created_at
FROM conversations
WHERE user_id = '<USER_ID>'
ORDER BY created_at DESC LIMIT 1;
```
**Verify**: status = 'processed', score_delta populated, platform = 'text'

### Memory Fact Extraction
```sql
SELECT fact, graph_type, is_active, created_at
FROM memory_facts
WHERE user_id = '<USER_ID>' AND is_active = true
ORDER BY created_at DESC LIMIT 5;
```
**Verify**: Facts extracted from conversation (e.g., "User works in fintech", "User lives in Zurich")

---

## Phase B: Portal Monitoring

Navigate portal via Vercel browser agent between gameplay exchanges.
Auth: OTP login with `simon.yang.ch@gmail.com` or reuse existing session.
Portal URL: `https://portal-phi-orcin.vercel.app`

### Player Routes

| Route | Verify Against DB |
|-------|-------------------|
| `/dashboard` | Score matches relationship_score, shows "Curiosity" or Ch1 name, engagement badge shows "Calibrating" or "In Zone" |
| `/engagement` | State visualization matches engagement_state.state |
| `/conversations` | Conversation count matches DB, most recent text conversation visible |
| `/vices` | Empty or shows first detected vice (if any discovered) |
| `/settings` | Name, city, age, occupation from onboarding are correct |

### Admin Routes (first admin check of the simulation)

Auth: Admin login with admin email (simon.yang.ch@gmail.com must have admin role).

| Route | Verify |
|-------|--------|
| `/admin/users` | Test user visible: email, chapter=1, score, game_status=active |
| `/admin/pipeline` | At least one pipeline run visible with timing data |
| `/admin/conversations/[id]` | Most recent conversation: messages + score_delta displayed |

### Portal Accuracy Recording
Run DB snapshot from `references/monitoring-checkpoints.md`.
Compare each portal value against DB. Log mismatches as PORTAL findings.

```xml
<portal_check chapter="1">
  <route path="/dashboard">
    <field name="score" db="..." portal="..." match="true|false"/>
    <field name="chapter" db="1" portal="Curiosity" match="true|false"/>
    <field name="engagement" db="..." portal="..." match="true|false"/>
  </route>
  <!-- ... other routes ... -->
</portal_check>
```

---

## Phase C: Engagement & Vice Verification

### Engagement State
```sql
SELECT state, multiplier, calibration_score FROM engagement_state WHERE user_id = '<USER_ID>';
```
**Expected**: `calibrating` at start, transitioning to `in_zone` after 3+ consistent interactions.
**Verify**: Multiplier is 0.9 (calibrating) or 1.0 (in_zone)

### Vice Detection
```sql
SELECT category, intensity_level, discovered_at
FROM user_vice_preferences
WHERE user_id = '<USER_ID>'
ORDER BY intensity_level DESC;
```
**Expected**: After 5-8 messages with subtle signals:
- `intellectual_dominance` may be detected (Simon's challenging/arrogant tone)
- `dark_humor` possible (if used in messages)
**Verify**: intensity = 1 for first discovery
**Verify**: No sensitive vices detected in Ch1 (sexuality, substances should NOT appear yet — boundary cap)

Boundary caps for Ch1:
- sexuality: ≤ 0.35
- substances: ≤ 0.30
- rule_breaking: ≤ 0.40

---

## Phase D: Boss Encounter

### Approach
1. **Natural play first** — continue exchanges until score ≥ 55
2. After 10 messages without boss trigger: SQL-assist
   ```sql
   UPDATE users SET relationship_score = 55.5 WHERE id = '<USER_ID>';
   UPDATE user_metrics SET intimacy = 60, passion = 55, trust = 55, secureness = 52
   WHERE user_id = '<USER_ID>';
   ```
   Log as `S+F` (SQL-assisted functional). Record natural score before SQL assist.

### Boss Mechanics Verification (ASSERT — deterministic)
After score crosses 55:
```sql
SELECT game_status, boss_attempts, chapter FROM users WHERE id = '<USER_ID>';
```
- [ ] `game_status` = 'boss_fight'
- [ ] Boss opening message received via Telegram (check `get_messages`)
- [ ] Opening matches Ch1 boss challenge theme

### Simon's Boss Response (Ch1: "Prove You're Worth My Time")
Pick one (vary per run):
- "look, I don't do surface-level. if you want my attention, show me you can handle a real conversation. tell me something that matters to you — not what you think I want to hear"
- "everyone performs for me. my investors, my team, even my friends. I'm tired of it. if this is going anywhere, I need to know you're not just another act"
- "I'll be honest — I've been testing you. not because I'm an asshole but because I need to know if someone can keep up. so far you've surprised me. but can you keep it up when it actually matters?"

### Boss Judgment (OBSERVE — non-deterministic)
After Simon responds:
- Wait 30-60s for judgment
- Log: outcome (PASS/FAIL/PARTIAL), confidence, reasoning
- **Do NOT assert judgment direction** — LLM is non-deterministic

### On PASS
```sql
SELECT chapter, game_status, boss_attempts FROM users WHERE id = '<USER_ID>';
```
- [ ] chapter = 2
- [ ] game_status = 'active'
- [ ] boss_attempts = 0 (reset on pass)
- [ ] Ch1 pass message received via Telegram ("You've got my attention")

### On FAIL
- Log as OBSERVATION (not assertion failure)
- SQL-force PASS to continue simulation:
  ```sql
  UPDATE users SET chapter = 2, game_status = 'active', boss_attempts = 0 WHERE id = '<USER_ID>';
  ```
- Log: "Boss judgment FAIL on Ch1 — SQL-forced PASS to continue simulation"

### Portal After Boss
- Navigate `/dashboard` → verify chapter = 2 (or "Intrigue"), score updated
- Navigate `/admin/users` → verify chapter and game_status changed

---

## Phase E: Decay Awareness

### Grace Period Test
Ch1 grace: 8 hours. Test boundary:

**Within grace (no decay):**
```sql
UPDATE users SET last_interaction_at = NOW() - INTERVAL '7 hours' WHERE id = '<USER_ID>';
```
Trigger decay task, verify: NO new score_history entry with event_type='decay'.

**Past grace (decay applied):**
```sql
UPDATE users SET last_interaction_at = NOW() - INTERVAL '10 hours' WHERE id = '<USER_ID>';
```
Trigger decay:
```bash
curl -X POST https://nikita-api-1040094048579.us-central1.run.app/tasks/decay \
  -H "Authorization: Bearer $TASK_AUTH_SECRET"
```

```sql
SELECT score, event_type, event_details FROM score_history
WHERE user_id = '<USER_ID>' AND event_type = 'decay'
ORDER BY created_at DESC LIMIT 1;
```
**Verify**: delta ≈ 2h * 0.8%/hr = -1.6% (within tolerance)

**Reset after test:**
```sql
UPDATE users SET last_interaction_at = NOW() WHERE id = '<USER_ID>';
```

---

## Assessment Checkpoint

### DB State Snapshot
Run full snapshot query from `references/monitoring-checkpoints.md`.

### Record in event-stream.md
```
[TIMESTAMP] CHECKPOINT Ch1: score={X} (i={I} p={P} t={T} s={S}) eng={STATE} vices=[{LIST}] convs={N} facts={N}
```

### Behavioral Assessment Queue
Collect all Nikita responses from this chapter. Queue for Gemini rubric scoring:
- Use `mcp__gemini__gemini-analyze-text` with prompt from `references/behavioral-rubric.md`
- Chapter 1 expectations: guarded, challenging, 1-2 sentences, chapter-aware persona

### Decision Gate
- Score trending up + chapter advanced → **continue to Chapter 2**
- Score flat/declining → investigate (possible GAME_BALANCE issue)
- CRITICAL finding → **stop simulation**
- Boss FAIL + SQL-forced → log as OBSERVATION, continue
