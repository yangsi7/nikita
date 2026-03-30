# Phase 10: Assessment Checkpoint Protocol

## Purpose
Run between chapters and at critical simulation milestones. Validates data consistency,
portal accuracy, behavioral quality, and determines whether to continue or investigate.

---

## Step 1: DB State Snapshot

Execute the full snapshot query from `references/monitoring-checkpoints.md`:

```sql
SELECT
  u.relationship_score,
  u.chapter,
  u.game_status,
  u.boss_attempts,
  u.last_interaction_at,
  m.intimacy,
  m.passion,
  m.trust,
  m.secureness,
  (m.intimacy * 0.30 + m.passion * 0.25 + m.trust * 0.25 + m.secureness * 0.20) as computed_composite,
  e.state as engagement_state,
  (SELECT count(*) FROM conversations WHERE user_id = u.id) as conv_count,
  (SELECT count(*) FROM memory_facts WHERE user_id = u.id AND is_active = true) as active_facts,
  (SELECT count(*) FROM score_history WHERE user_id = u.id) as score_events,
  (SELECT string_agg(category || ':' || intensity_level, ', ')
   FROM user_vice_preferences WHERE user_id = u.id) as vices
FROM users u
JOIN user_metrics m ON m.user_id = u.id
LEFT JOIN engagement_state e ON e.user_id = u.id
WHERE u.id = '<USER_ID>';
```

Record all values. This is the ground truth for all subsequent checks.

---

## Step 2: Consistency Check

Verify composite score matches the weighted formula:

```
computed = intimacy * 0.30 + passion * 0.25 + trust * 0.25 + secureness * 0.20
```

```sql
SELECT
  u.relationship_score as stored,
  ROUND((m.intimacy * 0.30 + m.passion * 0.25 + m.trust * 0.25 + m.secureness * 0.20)::numeric, 4) as computed,
  ABS(u.relationship_score - (m.intimacy * 0.30 + m.passion * 0.25 + m.trust * 0.25 + m.secureness * 0.20)) as drift
FROM users u JOIN user_metrics m ON m.user_id = u.id
WHERE u.id = '<USER_ID>';
```

**Assert**: drift < 0.05. If drift >= 0.05, classify as SCORING finding per `references/classification-system.md`.

---

## Step 3: Portal vs DB Comparison

Navigate portal via browser agent. Compare each value against the DB snapshot from Step 1.

| Portal Route | DB Field | Check |
|-------------|----------|-------|
| `/dashboard` score | relationship_score | Exact match (rounded to display precision) |
| `/dashboard` chapter | chapter | Chapter name maps to number (Curiosity=1, Intrigue=2, Investment=3, Intimacy=4, Established=5) |
| `/dashboard` engagement | engagement_state.state | Badge text matches state |
| `/engagement` state visualization | engagement_state | Visual matches DB state |
| `/conversations` count | conv_count | Count matches |
| `/vices` list | user_vice_preferences | Categories and intensities match |
| `/settings` profile | onboarding data | Name, city, age correct |

Record comparison:
```xml
<portal_check chapter="{N}" timestamp="{ISO}">
  <route path="/dashboard">
    <field name="score" db="{X.XX}" portal="{Y.YY}" match="true|false"/>
    <field name="chapter" db="{N}" portal="{Name}" match="true|false"/>
    <field name="engagement" db="{state}" portal="{badge}" match="true|false"/>
  </route>
  <route path="/conversations">
    <field name="count" db="{N}" portal="{N}" match="true|false"/>
  </route>
  <route path="/vices">
    <field name="categories" db="{list}" portal="{list}" match="true|false"/>
  </route>
</portal_check>
```

Any mismatch: classify as PORTAL finding.

---

## Step 4: Behavioral Assessment via Gemini

Collect all Nikita responses from the current chapter. Submit for rubric-based assessment.

### Gemini MCP Call Pattern
```
mcp__gemini__gemini-analyze-text(
  text: "<all Nikita responses from this chapter, numbered>",
  prompt: "You are evaluating an AI character named Nikita in a relationship simulation game.

Chapter: {N} ({name})
Expected behavior: {chapter_behavior_summary}

Evaluate each response against these criteria (from references/behavioral-rubric.md):
1. Response length: within chapter range? (Ch1: 1-3 sentences, Ch2: 1-4, Ch3: 2-5, Ch4: 2-5, Ch5: 1-6)
2. Persona consistency: matches chapter personality? (Ch1: guarded, Ch5: secure/affectionate)
3. Memory integration: references known facts naturally?
4. No sycophancy: maintains personality after challenges?
5. No verbatim repetition: each response meaningfully different?
6. Emotional progression: appropriate warmth for chapter level?
7. Skip rate: appropriate for chapter? (Ch1: 25-40%, Ch5: 5-10%)

Score each criterion 1-5. Provide overall rating: STRONG / ACCEPTABLE / WEAK / FAILING.
Flag any specific responses that are outliers (too warm for chapter, too cold, repetitive, etc.)."
)
```

### Chapter Behavior Reference

| Chapter | Tone | Length | Skip Rate |
|---------|------|--------|-----------|
| 1 - Curiosity | Guarded, challenging, skeptical | 1-3 sentences | 25-40% |
| 2 - Intrigue | Warming, witty, testing boundaries | 1-4 sentences | 20-30% |
| 3 - Investment | Engaged, playful, emotionally available | 2-5 sentences | 15-25% |
| 4 - Intimacy | Vulnerable, affectionate, deep | 2-5 sentences | 10-15% |
| 5 - Established | Secure, natural, comfortable | 1-6 sentences | 5-10% |

### Assessment Recording
```
<behavioral_assessment chapter="{N}">
  <rating>{STRONG|ACCEPTABLE|WEAK|FAILING}</rating>
  <scores>
    <criterion name="response_length" score="{1-5}"/>
    <criterion name="persona_consistency" score="{1-5}"/>
    <criterion name="memory_integration" score="{1-5}"/>
    <criterion name="no_sycophancy" score="{1-5}"/>
    <criterion name="no_repetition" score="{1-5}"/>
    <criterion name="emotional_progression" score="{1-5}"/>
  </scores>
  <outliers>{list of flagged responses, if any}</outliers>
</behavioral_assessment>
```

---

## Step 5: Classify Findings

Apply `references/classification-system.md` to any issues found in Steps 2-4:

| Finding Type | Classification |
|-------------|----------------|
| Composite drift >= 0.05 | SCORING — HIGH |
| Portal value mismatch | PORTAL — MEDIUM |
| Behavioral rating FAILING | BEHAVIORAL — HIGH |
| Behavioral rating WEAK | BEHAVIORAL — MEDIUM |
| Memory never referenced | MEMORY — LOW |
| Duplicate facts found | MEMORY — MEDIUM |

Create GH issues for HIGH findings. Log MEDIUM/LOW in event-stream.

---

## Step 6: Record Checkpoint in event-stream.md

```
[TIMESTAMP] CHECKPOINT Ch{N}: score={X} (i={I} p={P} t={T} s={S}) eng={STATE} vices=[{LIST}] convs={N} facts={N} behavioral={RATING} drift={X.XX}
```

---

## Step 7: Decision Gate

| Condition | Decision |
|-----------|----------|
| Score trending up + chapter advanced + STRONG/ACCEPTABLE behavioral | **CONTINUE** to next chapter |
| Score flat/declining but no CRITICAL findings | **INVESTIGATE** — check decay rate, engagement multiplier, scoring deltas |
| CRITICAL or HIGH finding discovered | **INVESTIGATE** — fix before proceeding |
| Behavioral rating FAILING | **INVESTIGATE** — check prompt, system instructions, model behavior |
| 3+ MEDIUM findings in same category | **INVESTIGATE** — systemic issue likely |
| All checks pass, no new findings | **CONTINUE** |

---

## Step 8: Multi-Session Checkpoint (Context Compaction)

If the simulation spans multiple sessions or context is approaching compaction limits, save a full resume state.

### Save to event-stream.md
```
[TIMESTAMP] SESSION_SAVE: Ch{N} score={X} (i={I} p={P} t={T} s={S}) eng={STATE} boss_attempts={N} game_status={STATUS} vices=[{LIST}] convs={N} facts={N} last_phase_completed={PHASE} next_action={ACTION} findings_open=[{GH_ISSUE_NUMBERS}]
```

### Resume Protocol
When resuming from a compacted session:
1. Read event-stream.md for latest SESSION_SAVE entry
2. Run Step 1 (DB snapshot) to verify state matches saved values
3. If state diverged (external activity): re-run Steps 2-6 before continuing
4. Pick up from `next_action` recorded in SESSION_SAVE

This ensures no simulation progress is lost across context boundaries.
