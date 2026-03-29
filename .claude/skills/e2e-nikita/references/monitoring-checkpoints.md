# Monitoring Checkpoints — E2E Nikita

Run between chapters and at key moments during simulation.

## DB State Snapshot Query

Execute via `mcp__supabase__execute_sql(project_id="oegqvulrqeudrdkfxoqd", query="...")`:

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
  (SELECT string_agg(category || ':' || ROUND(intensity::numeric, 2), ', ') FROM user_vice_preferences WHERE user_id = u.id) as vices
FROM users u
JOIN user_metrics m ON m.user_id = u.id
LEFT JOIN engagement_state e ON e.user_id = u.id
WHERE u.id = '<USER_ID>';
```

### Consistency Check
After snapshot, verify: `relationship_score == computed_composite` (within 0.01).
If mismatch → CRITICAL finding (SCORING category).

---

## Metrics Evolution Tracking

Record after each chapter in `event-stream.md`:

```
[TIMESTAMP] CHECKPOINT Ch{N}: score={X} (i={I} p={P} t={T} s={S}) eng={STATE} vices=[{LIST}] convs={N} facts={N}
```

### Trajectory Analysis
- **Healthy**: Score trending upward across chapters, approaching next boss threshold
- **Stalling**: Score flat for 5+ exchanges → possible GAME_BALANCE issue
- **Declining**: Score dropping despite positive interactions → possible SCORING bug
- **Volatile**: Large swings (>5 points per exchange) → possible ENGAGEMENT multiplier issue

Flag for investigation if:
- Score decreased over 3+ consecutive exchanges in same chapter
- Score hasn't changed in 5+ exchanges (stalling)
- Score jumped >15 points in a single exchange (suspicious delta)

---

## Portal Accuracy Verification

### Using Vercel Browser Agent

For each portal route, verify data displayed matches the DB snapshot taken above.

**Authentication** (run once at simulation start):
1. Navigate to portal URL
2. Authenticate via OTP or existing session
3. Verify redirect to /dashboard

**Player Routes** (check every chapter):

| Route | DB Field to Compare | What to Check |
|-------|-------------------|---------------|
| `/dashboard` | `relationship_score`, `chapter`, `engagement_state` | Score value, chapter name, engagement badge |
| `/engagement` | `engagement_state` | State badge matches, history chart populated |
| `/vices` | `vices` (from snapshot) | Vice cards displayed for detected vices |
| `/conversations` | `conv_count` | Count matches, most recent conversation visible |
| `/diary` | N/A | Entries present (if pipeline has run summary stage) |
| `/settings` | User profile fields | Name, city, age, occupation correct |

**Admin Routes** (check at Ch1 and Ch5):

| Route | What to Check |
|-------|---------------|
| `/admin/users` | Test user row: score, chapter, status, last_interaction |
| `/admin/pipeline` | Last pipeline run visible with duration |
| `/admin/conversations/[id]` | Conversation messages + score delta displayed |

### Portal Accuracy Recording

```xml
<portal_check chapter="N">
  <route path="/dashboard">
    <field name="score" db="67.5" portal="67.5" match="true"/>
    <field name="chapter" db="3" portal="Investment" match="true"/>
    <field name="engagement" db="in_zone" portal="In Zone" match="true"/>
  </route>
  <route path="/conversations">
    <field name="count" db="12" portal="12" match="true"/>
  </route>
  <mismatches>none | [list of mismatches → PORTAL findings]</mismatches>
</portal_check>
```

---

## Schema Validation (Phase 00 only)

Run at prerequisites to verify DB schema hasn't changed:

```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'users'
  AND column_name IN ('id', 'relationship_score', 'chapter', 'game_status',
                       'boss_attempts', 'last_interaction_at', 'telegram_id')
ORDER BY column_name;
```

Expected: 7 rows. If fewer → schema changed, update SQL queries before proceeding.

Also verify critical tables exist:
```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('users', 'user_metrics', 'user_profiles', 'conversations',
                     'score_history', 'memory_facts', 'user_vice_preferences',
                     'engagement_state', 'pending_registrations', 'onboarding_states')
ORDER BY table_name;
```

Expected: 10 rows.

---

## Time Simulation Reference

For testing decay and time-dependent mechanics within a chapter:

```sql
-- Simulate N hours of inactivity (for decay testing)
UPDATE users
SET last_interaction_at = NOW() - INTERVAL '{N} hours'
WHERE id = '<USER_ID>';

-- Chapter-specific examples:
-- Ch1 (grace=8h): Set to 10h ago → 2h of decay at 0.8%/hr = 1.6% decay
-- Ch2 (grace=16h): Set to 20h ago → 4h of decay at 0.6%/hr = 2.4% decay
-- Ch3 (grace=24h): Set to 30h ago → 6h of decay at 0.4%/hr = 2.4% decay
-- Ch4 (grace=48h): Set to 50h ago → 2h of decay at 0.3%/hr = 0.6% decay
-- Ch5 (grace=72h): Set to 80h ago → 8h of decay at 0.2%/hr = 1.6% decay
```

After time manipulation, trigger decay:
```bash
curl -X POST https://nikita-api-1040094048579.us-central1.run.app/tasks/decay \
  -H "Authorization: Bearer $TASK_AUTH_SECRET" \
  -H "Content-Type: application/json"
```

Verify with: `SELECT * FROM score_history WHERE user_id = '<USER_ID>' AND event_type = 'decay' ORDER BY created_at DESC LIMIT 1;`
