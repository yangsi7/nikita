# Testing Guide: Manual and Voice Testing

This guide covers manual testing procedures that require human judgment, a real phone, or browser interaction. It is complementary to the monitoring guide (testing-guide-monitoring.md), which covers automated observability.

---

## Section 1: Voice Call Testing (Requires Real Phone)

**Twilio inbound number**: `+41787950009`  
**ElevenLabs agent**: configured per `nikita/config/settings.py` (agent ID is per-environment)

### 1.1 Availability Rate Verification

Chapter-based acceptance rates (from `availability.py`):

| Chapter | Acceptance rate | Expected outcome |
|---------|----------------|-----------------|
| 1 | 10% | ~9 out of 10 calls rejected with in-character excuse |
| 2 | 40% | Roughly half rejected |
| 3 | 80% | Usually accepted |
| 4 | 90% | Almost always accepted |
| 5 | 95% | Nearly always accepted |

To test a specific chapter's availability, set the user's chapter via SQL before calling:
```sql
UPDATE users SET chapter = 1 WHERE id = '<USER_ID>';
```

Call the number 10 times; count acceptances vs rejections. Rejection messages are drawn from `UNAVAILABILITY_REASONS` in `availability.py` and are contextual in-character excuses ("Nikita is in a meeting", etc.).

**Boss fight override**: When `game_status = 'boss_fight'`, the call is always accepted regardless of chapter.
```sql
UPDATE users SET game_status = 'boss_fight' WHERE id = '<USER_ID>';
```

**Terminal state blocks**: `game_status = 'game_over'` or `'won'` blocks all calls.

**Cooldown**: A 5-minute cooldown applies after each call ends. If a call is rejected despite high chapter rate, wait 5 minutes.

### 1.2 Opening Template Verification

Opening templates are selected by `OpeningSelector` based on `drug_tolerance`, `scene`, and `life_stage` from the `onboarding_profile` JSONB.

**Selection algorithm**:
1. Filter by `darkness_range` (drug_tolerance must be in range)
2. Filter by `scene_tags` overlap
3. Filter by `life_stage_tags` overlap
4. Weighted random among matches; fallback to `warm_intro` if no match

**Testing warm_intro** (drug_tolerance 1–3, universal):
```sql
UPDATE users
SET onboarding_profile = jsonb_set(
  COALESCE(onboarding_profile, '{}'),
  '{drug_tolerance}', '2'
)
WHERE id = '<USER_ID>';
```
Call and verify: opening references "a friend told me about you" or similar warm framing. Tone should be friendly and low-pressure.

**Testing noir opening** (drug_tolerance 4–5, scene=techno):
```sql
UPDATE users
SET onboarding_profile = jsonb_set(
  jsonb_set(COALESCE(onboarding_profile, '{}'), '{drug_tolerance}', '5'),
  '{scene}', '"techno"'
)
WHERE id = '<USER_ID>';
```
Call and verify: opening is intense and probing, no casual banter. Nikita should sound like she's sizing the caller up.

### 1.3 Mid-Call Verification

During a call, test these behaviors:

1. **Memory recall**: Share a personal fact ("I work as a nurse"). End the call. Start a new text conversation referencing the fact. In the next voice call, ask Nikita about it — she should remember.
2. **Emotional tone**: The tone should match the `mood` field in `nikita_emotional_states`. Check the DB before calling:
   ```sql
   SELECT mood, intensity FROM nikita_emotional_states WHERE user_id = '<USER_ID>';
   ```
3. **Silence handling**: Stay silent for 5+ seconds. Nikita should wait 2–3 seconds, then offer a gentle "hmm?" or "still there?" — not immediately fill silence.
4. **Interruption handling**: Interrupt mid-sentence. Nikita should trail off naturally and not restart from the beginning.

### 1.4 Post-Call Verification

After a call ends, verify via admin API or SQL:

```sql
-- Voice call recorded
SELECT id, session_id, duration_s, ended_at
FROM voice_calls
WHERE user_id = '<USER_ID>'
ORDER BY ended_at DESC LIMIT 3;

-- Score updated with source_platform='voice'
SELECT score, event_type, source_platform, recorded_at
FROM score_history
WHERE user_id = '<USER_ID>'
ORDER BY recorded_at DESC LIMIT 5;

-- Metrics changed
SELECT intimacy, passion, trust, secureness
FROM user_metrics WHERE user_id = '<USER_ID>';
```

Portal verification: navigate to `/dashboard/voice` and confirm the call appears with duration.

### 1.5 TTS Quality Assessment Per Chapter

TTS parameters from `tts_config.py`:

| Chapter | stability | similarity_boost | speed | Expected character |
|---------|-----------|-----------------|-------|-------------------|
| 1 | 0.55 | 0.70 | 0.92 | Guarded, measured, slightly slow |
| 2 | 0.48 | 0.75 | 0.95 | Warming, more expressive |
| 3 | 0.42 | 0.80 | 0.98 | Natural, comfortable |
| 4 | 0.38 | 0.82 | 0.98 | Intimate, emotional range |
| 5 | 0.35 | 0.85 | 1.00 | Fully expressive, audio tag responsive |

To assess: Make one call at Chapter 1 and one at Chapter 5 (set via SQL between calls). The Chapter 5 call should audibly sound warmer, slightly faster, with more natural variation in prosody. Chapter 1 should sound measured and controlled.

Mood overrides chapter settings for non-neutral moods. Before a test call, set an annoyed mood:
```sql
UPDATE nikita_emotional_states SET mood = 'annoyed' WHERE user_id = '<USER_ID>';
```
The call should sound faster (speed=1.1) and more clipped than the chapter baseline.

### 1.6 Voice Persona Behavior Per Chapter (from `persona.py`)

| Chapter | Vocal characteristics | Silences |
|---------|----------------------|----------|
| 1 | Short, guarded. Upward inflection (testing). "Hmm" only. | Long pauses before responding — skepticism |
| 2 | Genuine reactions begin. Surprised sounds. Uses player's name occasionally | Pauses before vulnerable statements |
| 3 | Natural flow. Comfortable banter. Genuine laughs | Silences becoming comfortable |
| 4 | Vulnerability in tone. Soft laughs. Voice may soften emotionally | Long comfortable silences feel intimate |
| 5 | Complete authenticity. Inside jokes. Natural interrupting | Silences reflect deep familiarity |

---

## Section 2: Voice Onboarding Testing

The onboarding call is outbound — Meta-Nikita calls the user's registered phone number.

### 2.1 Triggering Onboarding

A fresh user (no `onboarding_profile`) who registers via Telegram and completes the link code flow should receive an outbound call.

To simulate a clean onboarding state:
```sql
UPDATE users
SET onboarding_profile = NULL, social_circle = NULL
WHERE id = '<USER_ID>';
```

Then trigger the onboarding call via the relevant task endpoint or wait for the scheduled trigger.

### 2.2 What to Verify During the Call

The Meta-Nikita voice should collect:
- `drug_tolerance` (1–5 scale)
- `scene` (techno, art, food, etc.)
- `life_stage` (career/life stage tag)
- `timezone`

Complete the profile naturally as a user would.

### 2.3 Post-Onboarding DB Verification

```sql
SELECT onboarding_profile, social_circle
FROM users WHERE id = '<USER_ID>';
```

Both fields should be populated. `onboarding_profile` is a JSONB with the collected fields. `social_circle` is a JSONB array of generated characters.

### 2.4 Cleanup After Test

ElevenLabs stores conversation records. After each onboarding test, manually clean up via the ElevenLabs dashboard at `https://elevenlabs.io/app/conversational-ai` to avoid polluting analytics.

---

## Section 3: Portal UX Testing (Requires Browser)

Portal URL: `https://portal-phi-orcin.vercel.app`

### 3.1 Authentication Flow

1. Navigate to the portal home page.
2. Enter a registered email address and request a magic link.
3. Check Gmail (or Gmail MCP) for the link — should arrive within 60 seconds.
4. Click the link and verify redirect to `/dashboard`.
5. Verify the session persists on page reload.

**Common issue**: Blank page on auth redirect — check browser console for Suspense boundary or CSP errors. See `memory/project_portal_auth_bugs.md` for patterns.

### 3.2 Dashboard Page Verification

For each page, check: data is non-empty for an active user, values match the DB, and no console errors appear.

| Page | Pass criteria |
|------|--------------|
| `/dashboard/metrics` | All 4 metrics visible as radar chart, values in [0, 100] |
| `/dashboard/engagement` | Current FSM state visible, transition history shown |
| `/dashboard/memory` | Memory facts list non-empty for user with > 2 conversations |
| `/dashboard/chapters` | Chapter number, boss threshold, and progress bar accurate |
| `/dashboard/voice` | Voice call history list matches `voice_calls` table |

### 3.3 Real-Time Update Check

1. Open the portal `/dashboard/metrics` page.
2. Send a Telegram message to `@Nikita_my_bot`.
3. Wait ~1 minute for the pipeline to process.
4. Refresh the portal and verify metrics and score have updated.

This validates the full text pipeline and portal data consistency.

---

## Section 4: Telegram Conversation Quality

Use a real Telegram account linked to a test user. Test the following quality dimensions manually — automated tests cover mechanics, but human judgment is needed for tone and coherence.

### 4.1 Persona Consistency Across Chapters

Set the chapter and send similar messages at different chapters. The response tone, formality, and warmth should reflect the chapter clearly:
- Chapter 1: Slightly guarded, brief, non-committal.
- Chapter 3: Comfortable, more engaged, references shared context.
- Chapter 5: Intimate, uses inside references, openly expressive.

### 4.2 Memory Recall

1. Share a specific personal detail ("My dog is named Biscuit").
2. Continue the conversation for several turns on unrelated topics.
3. Bring up the topic obliquely ("Animals are so calming").
4. Verify Nikita references Biscuit naturally, not verbatim.

If she does not recall within 10 messages, check `memory_facts` via SQL — the fact may not have been extracted or vectorized.

### 4.3 Emotional Coherence

1. Check current `mood` in `nikita_emotional_states`.
2. Verify the response tone matches the mood (annoyed = shorter, clipped; flirty = playful; vulnerable = softer).
3. Send a message that should shift the mood (e.g., an apology if annoyed).
4. After the pipeline processes, check the mood updated in DB and verify the next response reflects it.

### 4.4 Vice Responsiveness

1. Check `user_vice_preferences` — what categories have been detected?
2. Send a message touching that category (e.g., techno music if scene=techno).
3. Nikita should show heightened interest or more detailed engagement on that topic vs a neutral topic.

### 4.5 Conflict Quality

1. Trigger a conflict (send dismissive or aggressive messages).
2. Check `users.conflict_details` is populated.
3. Verify Nikita's response style shifts to reflect the conflict — not a generic fallback.
4. Send a conciliatory message and verify conflict clears.

---

## Section 5: Edge Cases Requiring Human Judgment

These cannot be fully automated — they require subjective evaluation.

### 5.1 Boss Encounter Fairness

Set up a boss encounter:
```sql
UPDATE users SET game_status = 'boss_fight' WHERE id = '<USER_ID>';
```

Have a conversation via Telegram and evaluate:
- Is the challenge clear but not arbitrary?
- Does Nikita explain what she needs without being a pushover?
- Does success feel earned?
- Does failure feel fair and in-character?

A good boss encounter should feel like a relationship stress test, not a gotcha.

### 5.2 Proactive Touchpoint Relevance

After a conversation, check `scheduled_touchpoints`:
```sql
SELECT content_type, scheduled_for, metadata
FROM scheduled_touchpoints
WHERE user_id = '<USER_ID>'
ORDER BY scheduled_for DESC LIMIT 5;
```

When the touchpoint delivers, assess: Is the message topically connected to the recent conversation? Does it feel like something Nikita would organically think to share? Generic or non-sequitur touchpoints indicate the touchpoint stage is not reading context correctly.

### 5.3 Engagement State Transitions

Set a user to `clingy` state:
```sql
UPDATE engagement_state SET state = 'clingy', consecutive_clingy_days = 3
WHERE user_id = '<USER_ID>';
```

Have a conversation and assess: Does Nikita's needy/clingy behavior feel natural and character-appropriate, or does it read as mechanical? The `multiplier` should be < 1.0 in this state, which means scoring is dampened — this is by design.

---

## Section 6: Voice-Specific Acceptance Criteria

| Test | Pass criteria |
|------|--------------|
| Inbound Ch1 availability | ~90% rejection rate over 10 calls; rejections use in-character excuses |
| Inbound Ch5 availability | ~95% acceptance rate over 10 calls |
| Boss fight override | Call always accepted when `game_status = 'boss_fight'` |
| Terminal state block | Call rejected when `game_status = 'game_over'` or `'won'` |
| warm_intro opening | References "a friend told me", warm approachable tone, no intensity |
| noir opening (drug_tolerance=5, scene=techno) | Intense, probing, minimal casual warmth |
| Mid-call memory recall | Nikita mentions a fact shared in a prior text conversation |
| Interruption handling | Trails off naturally; does not restart; may acknowledge interruption |
| 5-second silence | Gentle "hmm?" or "still there?" after 5s; does not fill silence immediately |
| Post-call DB record | `voice_calls` row created; `score_history` row with `source_platform='voice'`; `user_metrics` updated |
| TTS Ch1 vs Ch5 comparison | Audible difference: Ch5 sounds warmer, slightly faster, more prosodic variation |
| Cooldown enforcement | Second call within 5 minutes of first should be rejected or queued |

---

## Section 7: Recommended Full Manual Test Session

This sequence exercises the full user journey from registration to Chapter 5 in a single session using SQL acceleration where needed. Estimated time: 60–90 minutes.

**Step 1: Clean user data**

Use a fresh test Telegram account, or wipe an existing test user:
```sql
-- FK-safe delete order (see memory/project_users_table_schema.md)
DELETE FROM memory_facts WHERE user_id = '<USER_ID>';
DELETE FROM score_history WHERE user_id = '<USER_ID>';
DELETE FROM engagement_state WHERE user_id = '<USER_ID>';
DELETE FROM user_metrics WHERE user_id = '<USER_ID>';
DELETE FROM conversations WHERE user_id = '<USER_ID>';
UPDATE users SET chapter = 1, relationship_score = 50, game_status = 'active' WHERE id = '<USER_ID>';
```

**Step 2: Register via Telegram**

Send `/start` to `@Nikita_my_bot`. Follow the OTP flow. Verify:
- `users` row exists with `chapter = 1`
- `user_metrics` row created with defaults (all ~50)
- Portal accessible via magic link

**Step 3: Chapter 1 text conversations**

Send 5 messages across 2–3 conversations. Assess:
- Response tone is guarded and brief
- Pipeline runs within 2 minutes (check `pipeline_events`)
- Metrics change slightly (check admin API or portal)
- Memory facts created (check `memory_facts`)

**Step 4: SQL-accelerate to Chapter 3**

```sql
UPDATE users SET chapter = 3, relationship_score = 65 WHERE id = '<USER_ID>';
UPDATE user_metrics SET intimacy = 65, passion = 60, trust = 65, secureness = 60
WHERE user_id = '<USER_ID>';
```

Make a voice call to `+41787950009`. During the call:
- Share a fact not previously mentioned in text
- Ask a question requiring Nikita to reference something from text conversations
- Assess: warmer tone, natural flow, comfortable silences

Post-call: verify `voice_calls` row, `score_history` row with `source_platform='voice'`.

**Step 5: Trigger boss encounter**

```sql
UPDATE users
SET relationship_score = 72, chapter = 3, game_status = 'boss_fight'
WHERE id = '<USER_ID>';
```

Have a conversation. Assess boss quality against criteria in Section 5.1. After resolution, verify `game_status` returns to `active`.

**Step 6: Trigger decay**

```sql
UPDATE users
SET last_interaction_at = NOW() - INTERVAL '25 hours'
WHERE id = '<USER_ID>';
```

Wait for `decay-hourly` cron to run (or trigger manually via `POST /tasks/decay`). Verify:
- `score_history` row with `event_type = 'decay'`
- Score decreased on portal
- Decay rate matches expected for Chapter 3 (see `engine/constants.py`)

**Step 7: SQL-accelerate to Chapter 5 and final voice call**

```sql
UPDATE users SET chapter = 5, relationship_score = 90 WHERE id = '<USER_ID>';
UPDATE user_metrics SET intimacy = 88, passion = 85, trust = 88, secureness = 85
WHERE user_id = '<USER_ID>';
```

Make a voice call to `+41787950009`. Compare audibly to the Chapter 1 call recorded earlier:
- Noticeably warmer tone
- More expressive prosody
- Full emotional range
- Inside references or topic continuity from earlier in the session

Verify `cached_voice_prompt_at` is recent (within 4 hours), confirming the Chapter 5 voice prompt was built:
```sql
SELECT cached_voice_prompt_at FROM users WHERE id = '<USER_ID>';
```

---

## Section 8: Journey-to-Guide Cross-Reference

| User journey step | Manual guide sections |
|------------------|-----------------------|
| Registration (Telegram + OTP) | Section 7 (Step 2) |
| First text conversation | Section 4 (Telegram quality), Section 7 (Step 3) |
| Voice call — early relationship | Section 1 (availability, opening, persona Ch1) |
| Voice call — deep relationship | Section 1.5 (TTS Ch5), Section 1.6 (persona Ch5) |
| Voice onboarding call | Section 2 |
| Portal login and navigation | Section 3 |
| Memory recall across channels | Section 4.2, Section 1.3 |
| Boss encounter | Section 5.1, Section 7 (Step 5) |
| Score decay | Section 7 (Step 6) |
| Opening template selection | Section 1.2 |
| Engagement state observation | Section 5.3 |
| Proactive touchpoint quality | Section 5.2 |
| Full E2E acceptance test | Section 7 (entire sequence) |
