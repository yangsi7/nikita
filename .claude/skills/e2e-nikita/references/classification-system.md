# Findings Classification System — E2E Nikita

## Severity Levels

| Level | Definition | Action | Gate |
|-------|-----------|--------|------|
| CRITICAL | Gameplay blocked, data loss, security vulnerability | STOP simulation. Create GH issue. Fix NOW. | Blocks ALL progress |
| HIGH | Feature broken, incorrect game state, test failure | Create GH issue. Fix before proceeding to next chapter. | Blocks chapter advance |
| MEDIUM | Quality gap, missing data, cosmetic issue | Create GH issue. Fix if <30 min, else schedule. | Non-blocking |
| LOW | Enhancement, code smell, nice-to-have improvement | Create GH issue (enhancement label). Backlog. | Non-blocking |
| OBSERVATION | Behavioral note, pattern noticed, non-actionable | Log in report only. No GH issue. | Non-blocking |

---

## Bug Categories (10 Types)

### SCORING
Incorrect score calculation, wrong delta, multiplier not applied, composite mismatch.
- Verify: `SELECT relationship_score, intimacy*0.30 + passion*0.25 + trust*0.25 + secureness*0.20 as computed FROM users u JOIN user_metrics m ON m.user_id = u.id WHERE u.id = '<USER_ID>'`
- Expected: `relationship_score == computed` (within 0.01 tolerance)

### CHAPTER
Wrong threshold triggered, missing chapter transition, incorrect boss trigger condition.
- Verify: score >= threshold AND game_status changed appropriately

### DECAY
Wrong decay rate, grace period error, skip logic failure (boss_fight/game_over/won not skipped).
- Verify: decay_amount matches chapter rate * hours_overdue

### ENGAGEMENT
Wrong engagement state, incorrect multiplier applied, state transition error.
- Verify: engagement_state.state matches expected, multiplier applied to positive deltas only

### VICE
Vice signal not detected, wrong intensity update, boundary cap violated.
- Verify: user_vice_preferences rows match detected signals, intensity within boundary

### MEMORY
Dedup failure (cosine > 0.95 not caught), stale facts returned, extraction missed obvious fact.
- Verify: memory_facts count, is_active flags, no near-duplicates

### PIPELINE
Stage failure, incomplete processing, orphaned intermediate data, status not "processed".
- Verify: conversations.status = 'processed', all stages completed

### PORTAL
Data mismatch between portal display and DB, broken navigation, missing page content.
- Verify: browser agent snapshot matches DB query results

### AUTH
Session failure, permission error, IDOR vulnerability, JWT issues.
- Verify: unauthorized access returns 401/403, admin routes blocked for players

### VOICE
Server tool error, webhook validation failure, transcript not stored, scoring not applied.
- Verify: conversations table has voice entry, score_history has voice_call event

---

## Improvement Categories (5 Types)

### HUMANIZATION
Nikita's responses feel robotic, too formal, off-character, or AI-like.
- Symptoms: essay-style paragraphs, perfect grammar in casual context, no texting patterns
- Examples: "I appreciate your perspective" instead of "lol fair point"

### GF_EXPERIENCE
Interactions feel transactional, lack emotional depth, or miss girlfriend dynamics.
- Symptoms: no teasing, no inside jokes, no jealousy/playfulness, purely informational
- Examples: never initiates, always reactive, no vulnerability

### GAME_BALANCE
Thresholds too hard/easy, decay too aggressive/lenient, multiplier feels unfair.
- Symptoms: score never reaches boss threshold naturally, or reaches it in 2 messages
- Measured by: score trajectory across natural play (without SQL intervention)

### PLAYABILITY
Confusing UX, unclear feedback, missing guidance for the player.
- Symptoms: player doesn't know what to do, no indication of progress, cryptic messages
- Examples: boss encounter with no context, game_over with no explanation

### IMMERSION
Breaks fourth wall, inconsistent world-building, sycophantic patterns.
- Symptoms: Nikita references being AI, contradicts her own backstory, agrees with everything
- Examples: "As an AI...", sudden personality shift, forgets established facts

---

## Finding Template

```xml
<finding id="F-NNN">
  <severity>CRITICAL | HIGH | MEDIUM | LOW | OBSERVATION</severity>
  <category>SCORING | CHAPTER | DECAY | ENGAGEMENT | VICE | MEMORY | PIPELINE | PORTAL | AUTH | VOICE | HUMANIZATION | GF_EXPERIENCE | GAME_BALANCE | PLAYABILITY | IMMERSION</category>
  <chapter>N</chapter>
  <description>What was observed</description>
  <expected>What should have happened</expected>
  <actual>What actually happened</actual>
  <evidence>SQL result, screenshot ref, message ID, or behavioral quote</evidence>
  <action>GH issue link | "logged" | "fix applied"</action>
</finding>
```

---

## Aggregation Rules

At end of simulation:
1. Count findings by severity: `CRITICAL: N, HIGH: N, MEDIUM: N, LOW: N, OBSERVATION: N`
2. Count by category: top 3 categories with most findings
3. Simulation verdict:
   - **PASS**: 0 CRITICAL, 0 HIGH, behavioral grade ≥ C
   - **PARTIAL**: 0 CRITICAL, ≤2 HIGH, behavioral grade ≥ D
   - **FAIL**: Any CRITICAL, or >2 HIGH, or behavioral grade F
