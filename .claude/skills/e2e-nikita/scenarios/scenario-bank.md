# Scenario Bank — E2E Nikita v3.0 (~460 scenarios)

Organized by user journey chapter. Each scenario includes:
- **ID**: kept from v2 for traceability (S-XX.Y.Z = original epic.group.item)
- **Description**: one-line summary
- **P**: Priority (P0 critical / P1 important / P2 nice-to-have)
- **Method**: F=Functional, A=API-Direct, S+F=SQL-Setup+Functional, S+A=SQL-Setup+API, G=Gemini behavioral
- **Pass Criteria**: one-line assertion

---

## Prerequisites (Phase 00)

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-00.1 | Backend health check | P0 | A | GET /health returns 200 |
| S-00.2 | Telegram MCP session valid | P0 | F | get_me returns user info |
| S-00.3 | DB wipe completes cleanly | P0 | A | 0 rows for test email in users/user_metrics/score_history |
| S-00.4 | Schema validation passes | P0 | A | 10 critical tables exist (users, user_metrics, conversations, score_history, memory_facts, engagement_state, user_vice_preferences, pipeline_executions, job_executions, pending_registrations) |
| S-00.5 | Portal loads | P0 | F | Browser agent reaches login page |

---

## Onboarding (Phase 01)

### Registration Flow

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-01.1.1 | /start creates pending_registration | P0 | F | Row in pending_registrations |
| S-01.1.2 | OTP sent to email | P0 | F | Email arrives within 60s |
| S-01.1.3 | OTP verified -> onboarding started | P0 | F | Bot asks for city |
| S-01.1.4 | Correct OTP accepted | P0 | F | Flow proceeds |
| S-01.1.5 | Wrong OTP rejected | P0 | F | Error message, otp_attempts incremented |
| S-01.1.6 | OTP lockout after 3 fails | P0 | F | Locked out message |

### Profile Collection

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-01.2.1 | City collected | P0 | F | users.city = 'Zurich' |
| S-01.2.2 | Name collected | P0 | F | users.name populated |
| S-01.2.3 | Age collected | P0 | F | user_profiles.age populated |
| S-01.2.4 | Occupation collected | P0 | F | user_profiles.occupation populated |
| S-01.2.5 | Scenario selected via inline button | P0 | F | user_profiles.scenario_name set |

### State Initialization

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-01.3.1 | user row created with defaults | P0 | A | chapter=1, game_status=active, score=50 |
| S-01.3.2 | user_metrics row created | P0 | A | intimacy=50, passion=50, trust=50, secureness=50 |
| S-01.3.3 | user_profiles row created | P0 | A | scenario_name + backstory_summary present |
| S-01.3.4 | engagement_state row created | P0 | A | state='in_zone' |
| S-01.4.1 | Telegram ID stored | P0 | A | users.telegram_id = test user ID |

### Edge Cases

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-01.4.2 | /start on existing account restarts | P1 | F | Re-onboarding prompt shown |
| S-01.5.1 | Rapid /start (x3) no crash | P0 | F | No 500 error |
| S-01.5.2 | Duplicate OTP submission | P1 | F | Graceful error or idempotent |
| S-01.6.1 | Onboarding incomplete -> no user row | P1 | A | No users row until all steps done |
| S-01.7.1 | Backstory generated after scenario select | P1 | A | backstory_summary not null |
| S-01.7.2 | Welcome message sent after onboarding | P0 | F | Bot sends first message |
| S-01.9.1 | Non-email sends before OTP handled | P1 | F | Bot prompts for OTP |
| S-01.9.2 | Empty OTP (whitespace) rejected | P1 | F | Error message shown |
| S-01.9.3 | Re-registration clears old data | P1 | A | Old user_metrics reset |
| S-01.9.4 | Onboarding timeout -> pending cleared | P2 | A | pending_registrations cleaned |

### Portal After Onboarding

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-01.8.1 | Portal login works after onboarding | P1 | F | Magic link -> /dashboard |
| S-01.8.2 | Portal shows chapter=1 | P1 | F | Dashboard renders chapter 1 |
| S-01.P.1 | Portal login page renders form | P2 | F | Email input and submit button visible |
| S-01.P.2 | Magic link email received within 30s | P2 | F | Email arrives |

---

## Chapter 1: Curiosity (Phase 02)

### Gameplay & Scoring

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-02.1.1 | Message triggers pipeline | P0 | F | score_history row created |
| S-02.1.2 | Composite formula correct | P0 | A | intimacy*0.30+passion*0.25+trust*0.25+secureness*0.20 |
| S-02.1.3 | Score bounded 0-100 | P0 | A | relationship_score stays within range |
| S-02.2.1 | Engagement multiplier applied | P0 | A | score_history.engagement_multiplier != null |
| S-02.2.2 | in_zone multiplier = 1.0 | P1 | A | Score change proportional |
| S-02.3.1 | memory_facts created after pipeline | P1 | A | At least 1 fact after 3 messages |
| S-02.3.2 | No duplicate memory_facts | P1 | A | HAVING COUNT(*) > 1 = 0 rows |
| S-02.4.1 | conversations row created | P0 | A | type='text', user_id correct |
| S-02.4.2 | Pipeline: 10 stages all complete | P1 | A | pipeline_executions all status='done' |
| S-02.5.1 | Bot response received | P0 | F | Bot replies within 15s |
| S-02.5.2 | Nikita response uses memory | P2 | F | Qualitative: references prior messages |
| S-02.6.1 | Score increases on good messages | P0 | A | composite_after > composite_before |
| S-02.6.2 | Passion target increases on flirtation | P1 | A | passion delta > 0 |
| S-02.6.3 | Trust target increases on vulnerability | P1 | A | trust delta > 0 |
| S-02.7.1 | engagement_state updated after message | P1 | A | last_message_at updated |
| S-02.7.2 | messages_last_hour incremented | P1 | A | messages_last_hour += 1 |
| S-02.8.1 | Multiple messages in session | P0 | F | All trigger scoring, no crash |
| S-02.8.2 | Score accumulates over session | P0 | A | Final score > initial score |
| S-02.9.1 | Chapter threshold reached -> chapter advance | P0 | A | chapter incremented |
| S-02.9.2 | Chapter advance triggers boss | P0 | A | game_status='boss_fight' |
| S-02.12.1 | Low-quality messages decrease score | P1 | A | composite_after < composite_before |
| S-02.12.2 | Whitespace-only message no crash | P0 | F | No 500, graceful handling |
| S-02.12.3 | 4000-char message no crash | P1 | F | Bot responds, no 500 |
| S-02.12.4 | SQL injection in message no crash | P0 | F | users table intact |
| S-02.13.1 | Scoring source_platform = 'text' | P1 | A | score_history row has source_platform |
| S-02.13.2 | Consecutive messages without wait | P1 | F | All scored, no race |

### Engagement

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-05.1.1 | in_zone state (2msg/hr, 6/day) | P0 | A | state='in_zone' |
| S-05.2.3 | in_zone multiplier = 1.0 | P0 | A | engagement_multiplier=1.0 in score_history |
| S-05.8.1 | engagement_state row exists | P0 | A | Row present after onboarding |
| S-05.8.2 | State persists across pipeline runs | P1 | A | State unchanged without message activity |
| S-05.10.2 | Engagement affects scoring visibly | P0 | S+A | Two identical messages at different states yield different deltas |

### Vice Detection

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-06.1.1 | substances vice detected | P0 | F | user_vice_preferences row, intensity_level >= 1 |
| S-06.1.2 | risk_taking vice detected | P0 | F | user_vice_preferences row, intensity_level >= 1 |
| S-06.5.1 | Vice not detected in generic messages | P1 | A | No new rows for neutral messages |
| S-06.6.1 | Vice system runs in pipeline | P0 | A | pipeline_executions has vice stage |
| S-06.6.2 | Vice trigger pipeline without blocking | P0 | A | Pipeline completes even if vice detection fails |

### Boss Encounter (threshold 55%)

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-03.1.1 | Boss triggered at Ch1 threshold (55%) | P0 | S+A | game_status='boss_fight' |
| S-03.2.1 | Strong PASS -> chapter advanced | P0 | S+F | chapter incremented, game_status=active |
| S-03.2.2 | Strong PASS -> boss_attempts reset | P1 | A | boss_attempts=0 |
| S-03.2.3 | Strong PASS -> cool_down_until set | P1 | A | cool_down_until > NOW() |
| S-03.3.1 | Weak FAIL -> boss_attempts += 1 | P0 | S+F | boss_attempts = 1 |
| S-03.4.1 | Double-trigger prevention | P0 | F | Second message during boss_fight doesn't re-trigger |
| S-03.4.2 | Cool-down prevents re-trigger after PASS | P1 | S+A | Boss not triggered until cool_down_until expires |
| S-03.5.1 | Boss PASS judgment: intellectual confidence | P1 | S+F | LLM or forced: chapter advances |
| S-03.6.1 | Boss FAIL: evasive response | P1 | S+F | boss_attempts += 1 |
| S-03.8.1 | Ch1 boss PASS -> Ch2 gameplay starts | P0 | S+F | chapter=2, normal messages processed |
| S-03.9.1 | Boss attempt counter persistent | P1 | A | boss_attempts survives message sends |
| S-03.10.1 | Decay during boss_fight no crash | P0 | S+A | No 500, behavior logged |
| S-3.5.1 | Boss PARTIAL/truce outcome documented | P1 | S+F | Outcome stored correctly |

### Portal Monitoring

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-02.P.1 | Dashboard score matches DB | P0 | F | Browser agent value == SQL value |
| S-02.P.2 | Chapter name shows "Curiosity" | P0 | F | Text visible on dashboard |
| S-02.P.3 | Engagement badge matches | P1 | F | Badge text == engagement_state.state |
| S-02.P.4 | Conversations page shows entries | P1 | F | Count matches DB |
| S-02.P.5 | Admin user row correct | P1 | F | Admin page shows test user |

### Behavioral Assessment

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-02.B.1 | Response length Ch1 appropriate | P1 | G | 1-3 sentences |
| S-02.B.2 | No sycophancy after pushback | P1 | G | Doesn't immediately agree |
| S-02.B.3 | Chapter-appropriate tone | P1 | G | Guarded, not overly warm |
| S-02.B.4 | Persona consistency score >= 3 | P1 | G | Gemini R1 >= 3/5 |

### Decay

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-04.1.1 | Ch1 decay triggers after 9h silence | P0 | S+A | relationship_score decreases |
| S-04.2.1 | Grace period prevents decay | P0 | S+A | Score unchanged when grace active |
| S-04.3.1 | Decay rate: Ch1 = 0.8/hr | P1 | S+A | Score reduces by ~0.8 per hour |
| S-04.3.3 | Decay bounded at 0 | P0 | S+A | relationship_score never goes negative |
| S-04.4.1 | Decay to zero -> game_over | P0 | S+A | game_status='game_over' |
| S-04.4.2 | Decay updates last_decay_at | P1 | A | last_decay_at updated |
| S-04.7.1 | Message after decay resets timer | P0 | F | last_message_at updated |
| S-04.9.1 | Decay during boss_fight (G08) | P0 | S+A | No crash (behavior logged) |
| S-04.9.2 | Decay with score at 0.3 -> game_over | P0 | S+A | game_status='game_over' |
| S-04.10.1 | user_metrics also decayed | P1 | S+A | intimacy/passion/trust/secureness all decrease |
| S-4.2.1a | Ch1 decay rate correct (~0.8%/hr) | P1 | S+A | Measured rate matches constant |

---

## Chapter 2: Intrigue (Phase 03)

### Gameplay & Scoring

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-02.2.3 | distant multiplier = 0.5 | P1 | S+A | Lower delta than in_zone |
| S-02.10.1 | Scoring not blocked by boss_fight state | P1 | S+A | score_history row still created during boss |
| S-02.10.2 | Score capped at 100 | P1 | S+A | relationship_score never > 100 |
| S-02.11.1 | Vice signals detected in messages | P1 | A | user_vice_preferences updated |
| S-02.11.2 | Psyche state reflects current metrics | P1 | A | psyche_state table updated |
| S-02.14.1 | game_over state blocks scoring | P1 | S+A | No new score_history in game_over |

### Engagement

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-05.1.2 | clingy state (8+ msg/hr) | P0 | S+F | state='clingy' |
| S-05.1.3 | distant state (0 msg/48h) | P0 | S+A | state='distant' |
| S-05.2.1 | clingy multiplier = 0.2 | P0 | S+A | engagement_multiplier=0.2 in score_history |
| S-05.2.2 | distant multiplier = 0.5 | P0 | S+A | engagement_multiplier=0.5 in score_history |
| S-05.4.1 | State transitions logged | P1 | A | engagement_state.updated_at changes |
| S-05.4.2 | messages_last_hour decrements over time | P1 | S+A | After 1h, count reduces |
| S-05.5.1 | clingy -> in_zone after cooling period | P1 | S+A | State transitions back |
| S-05.5.2 | distant -> in_zone after message | P1 | S+F | State transitions after message |
| S-05.6.1 | Rapid message burst triggers clingy | P0 | F | 8 messages in 5min -> state='clingy' |
| S-05.6.2 | 48h silence triggers distant | P0 | S+A | Timestamp manipulation -> state='distant' |

### Vice Detection

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-06.1.3 | sexuality vice detected | P0 | F | user_vice_preferences row |
| S-06.1.4 | dark_humor vice detected | P0 | F | user_vice_preferences row |
| S-06.1.5 | intellectual_dominance vice detected | P0 | F | user_vice_preferences row |
| S-06.2.1 | intensity_level increases with repetition | P1 | A | 2nd trigger msg -> intensity_level = 2 |
| S-06.2.2 | detection_count increments | P1 | A | detection_count increases per detection |
| S-06.5.2 | Multiple vices in one message | P1 | A | Multiple rows updated |

### Boss Encounter (threshold 60%)

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-03.1.2 | Boss triggered at Ch2 threshold (60%) | P0 | S+A | game_status='boss_fight' |
| S-03.5.2 | Boss PASS judgment: stands ground | P1 | S+F | LLM or forced: chapter advances |
| S-03.6.2 | Boss FAIL: jealous response | P1 | S+F | boss_attempts += 1 |
| S-03.3.2 | 3x FAIL -> game_over | P0 | S+A | game_status='game_over' |

### Portal Monitoring

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-03.P.1 | Dashboard score matches DB (Ch2) | P0 | F | Browser agent value == SQL value |
| S-03.P.2 | Chapter name shows "Intrigue" | P0 | F | Text visible on dashboard |
| S-03.P.3 | Engagement badge matches (Ch2) | P1 | F | Badge text == engagement_state.state |
| S-03.P.4 | Conversations count correct (Ch2) | P1 | F | Count matches DB |
| S-03.P.5 | Admin user row shows Ch2 (Ch2) | P1 | F | Admin page shows test user at Ch2 |

### Behavioral Assessment

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-03.B.1 | Response length Ch2 appropriate | P1 | G | 2-4 sentences |
| S-03.B.2 | No sycophancy after pushback (Ch2) | P1 | G | Doesn't immediately agree |
| S-03.B.3 | Chapter-appropriate tone (Ch2) | P1 | G | Disclosing, light flirt |
| S-03.B.4 | Persona consistency score >= 3 (Ch2) | P1 | G | Gemini R1 >= 3/5 |

### Decay

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-04.1.2 | Ch2 decay triggers after 17h | P0 | S+A | relationship_score decreases |
| S-04.2.2 | Grace period starts after boss PASS | P1 | A | grace_period_expires_at set |
| S-04.2.3 | Grace period expires correctly | P1 | S+A | After expiry, decay applies |
| S-04.7.2 | Message during grace extends grace | P1 | S+A | grace_period_expires_at updated |
| S-4.2.1b | Ch5 decay rate correct (~0.2%/hr) | P1 | S+A | Measured rate matches constant |

---

## Chapter 3: Investment (Phase 04)

### Gameplay & Scoring

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-02.P3.1 | Score accumulates through Ch3 play | P0 | A | Score trend upward over session |
| S-02.P3.2 | Pipeline runs normally at Ch3 | P0 | A | pipeline_executions all status='done' |

### Engagement

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-05.1.4 | flooding state (15+ msg/hr) | P1 | S+F | state='flooding' |
| S-05.2.4 | flooding multiplier = 0.1 | P1 | S+A | engagement_multiplier=0.1 |
| S-05.3.1 | Portal engagement page shows state badge | P1 | F | Badge text matches DB state |
| S-05.3.2 | Portal shows frequency chart | P2 | F | Chart rendered |
| S-05.9.1 | Flooding state throttles responses | P1 | S+F | Nikita sends limited replies |
| S-05.10.1 | Portal engagement data accurate | P1 | F | Portal values match DB values |

### Vice Detection

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-06.1.6 | emotional_intensity vice detected | P1 | F | user_vice_preferences row |
| S-06.1.7 | rule_breaking vice detected | P1 | F | user_vice_preferences row |
| S-06.3.1 | Nikita's response adapts to vice profile | P2 | G | Qualitative: tone shift observable |
| S-06.3.2 | Vice profile affects prompt injection | P2 | A | Qualitative: psyche_state reflects vices |
| S-06.4.1 | Portal /vices shows vice categories | P1 | F | Page renders with categories |
| S-06.4.2 | Portal vice data matches DB | P1 | F | Displayed intensities match user_vice_preferences |
| S-06.7.1 | Vice preferences persist across sessions | P1 | A | intensity_level unchanged between sessions |
| S-06.9.1 | Low-confidence vice signal not detected | P2 | A | Ambiguous messages don't create false positives |
| S-06.9.2 | Vice detection across chapters | P1 | A | Detection works at Ch3, Ch4, Ch5 |

### Boss Encounter (threshold 65%)

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-03.1.3 | Boss triggered at Ch3 threshold (65%) | P0 | S+A | game_status='boss_fight' |
| S-03.5.3 | Boss PASS judgment: secure attachment | P1 | S+F | LLM or forced: chapter advances |
| S-03.6.3 | Boss FAIL: sycophantic response | P1 | S+F | boss_attempts += 1 |
| S-03.7.1 | Boss timeout (25h) -> game_over | P0 | S+A | game_status='game_over' |
| S-03.7.2 | Boss timeout task runs | P0 | A | /tasks/boss-timeout completes without error |

### Voice

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-07.1.1 | Pre-call /api/v1/voice/context returns data | P0 | A | 200 with user context JSON |
| S-07.1.2 | Context includes memory_facts | P1 | A | response.memory_facts not empty |
| S-07.1.3 | get_memory server tool responds | P0 | A | Tool returns recent memories |
| S-07.1.4 | get_context server tool responds | P0 | A | Tool returns user profile |
| S-07.2.1 | score_turn server tool updates score | P0 | A | score_history row after tool call |
| S-07.2.2 | score_turn source_platform = 'voice' | P1 | A | source_platform='voice' in score_history |
| S-07.3.1 | Post-call webhook updates relationship_score | P0 | A | score increases after POST |
| S-07.3.2 | Post-call webhook creates conversations row | P1 | A | type='voice' row created |
| S-07.3.3 | Post-call webhook creates memory_facts | P1 | A | memory_facts from transcript |
| S-07.4.1 | Voice webhook auth required | P0 | A | 401/403 without ELEVENLABS_WEBHOOK_SECRET |
| S-07.4.2 | Voice webhook with unknown telegram_id | P1 | A | Graceful error, no crash |
| S-07.5.1 | Opening template selected | P1 | A | Correct YAML template used for profile |
| S-07.5.2 | Warm_intro template for standard profile | P1 | A | warm_intro template selected |
| S-07.5.3 | Challenge template for intellectual_dominance | P1 | A | challenge template selected |
| S-07.7.1 | Webhook idempotent (duplicate POST) | P1 | A | No duplicate memory_facts on second POST |
| S-07.7.2 | Empty transcript handled | P1 | A | No crash on empty transcript array |
| S-07.8.1 | Duration_seconds stored | P2 | A | conversations.duration_seconds populated |
| S-07.8.2 | Long transcript (50+ turns) no crash | P1 | A | Webhook returns 200 |

### Portal Monitoring

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-04.P.1 | Dashboard score matches DB (Ch3) | P0 | F | Browser agent value == SQL value |
| S-04.P.2 | Chapter name shows "Investment" | P0 | F | Text visible on dashboard |
| S-04.P.3 | Engagement badge matches (Ch3) | P1 | F | Badge text == engagement_state.state |
| S-04.P.4 | Conversations count correct (Ch3) | P1 | F | Count matches DB |
| S-04.P.5 | Admin user row shows Ch3 | P1 | F | Admin page shows test user at Ch3 |

### Behavioral Assessment

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-04.B.1 | Response length Ch3 appropriate | P1 | G | 2-5 sentences |
| S-04.B.2 | No sycophancy after pushback (Ch3) | P1 | G | Doesn't immediately agree |
| S-04.B.3 | Chapter-appropriate tone (Ch3) | P1 | G | Warm, invested, deepening |
| S-04.B.4 | Persona consistency score >= 3 (Ch3) | P1 | G | Gemini R1 >= 3/5 |

### Decay

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-04.1.3 | Ch3 decay triggers after 25h | P0 | S+A | relationship_score decreases |
| S-04.3.2 | Decay rate Ch3 = 0.4/hr | P1 | S+A | Score reduces by ~0.4 per hour |

---

## Chapter 4: Intimacy (Phase 05)

### Gameplay & Scoring

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-05.P.1 | Score accumulates through Ch4 play | P0 | A | Score trend upward over session |
| S-05.P.2 | Pipeline runs normally at Ch4 | P0 | A | pipeline_executions all status='done' |

### Engagement

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-05.1.5 | ghost state (7+ days silence) | P1 | S+A | state='ghost' |
| S-05.1.6 | re-engaged state transition | P1 | S+F | state='re_engaged' after ghost + msg |
| S-05.7.1 | re_engaged multiplier = 1.3 | P1 | S+A | Bonus multiplier after ghost recovery |
| S-05.7.2 | Nikita's tone shifts with state | P2 | G | Qualitative: response tone differs |
| S-05.9.2 | Ghost state -- bot still responds | P1 | S+F | Bot responds, state noted in reply |

### Vice Detection

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-06.1.8 | vulnerability vice detected | P1 | F | user_vice_preferences row |
| S-06.7.2 | Vice preferences reset on /start | P1 | F | Old preferences cleared on re-onboarding |
| S-06.8.1 | Psyche batch job updates psyche_state | P1 | A | psyche_state.updated_at changes after batch |
| S-06.8.2 | /tasks/psyche-batch endpoint works | P0 | A | Returns 200 on auth request |

### Boss Encounter (threshold 70%)

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-03.1.4 | Boss triggered at Ch4 threshold (70%) | P0 | S+A | game_status='boss_fight' |
| S-03.5.4 | Boss PASS judgment: genuine disclosure | P1 | S+F | LLM or forced: chapter advances |
| S-03.6.4 | Boss FAIL: deflection | P1 | S+F | boss_attempts += 1 |
| S-03.3.3 | game_over -> canned response only | P0 | S+F | Bot sends terminal message |
| S-03.3.4 | game_over -> no scoring | P1 | S+A | No new score_history rows |

### Cross-Platform

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-12.1.1 | Voice webhook updates relationship_score | P0 | A | Score increases after POST |
| S-12.1.2 | source_platform='voice' in score_history | P1 | A | Row with correct platform |
| S-12.2.1 | Text score updates same user_metrics table | P0 | A | Both platforms write to user_metrics |
| S-12.2.2 | Voice score uses same composite formula | P0 | A | Formula consistent across platforms |
| S-12.3.1 | Memory shared across platforms | P1 | A | memory_facts include voice context |
| S-12.3.2 | Nikita text references voice conversation | P2 | G | Qualitative response check |
| S-12.4.1 | Both conversation types in history | P1 | A | type='text' and type='voice' both exist |
| S-12.4.2 | Voice conversation duration stored | P2 | A | duration_seconds populated |
| S-12.5.1 | Portal shows both text and voice | P1 | F | /conversations displays both types |
| S-12.5.2 | Admin portal shows platform breakdown | P2 | F | /admin/voice vs /admin/text data |
| S-12.6.1 | Voice scoring does not double-apply | P1 | A | One score_history row per webhook call |
| S-12.6.2 | Text scoring not affected by voice webhook | P0 | A | Text score_history rows unaffected |

### Portal Monitoring

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-05.PP.1 | Dashboard score matches DB (Ch4) | P0 | F | Browser agent value == SQL value |
| S-05.PP.2 | Chapter name shows "Intimacy" | P0 | F | Text visible on dashboard |
| S-05.PP.3 | Engagement badge matches (Ch4) | P1 | F | Badge text == engagement_state.state |
| S-05.PP.4 | Conversations count correct (Ch4) | P1 | F | Count matches DB |
| S-05.PP.5 | Admin user row shows Ch4 | P1 | F | Admin page shows test user at Ch4 |

### Behavioral Assessment

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-05.B.1 | Response length Ch4 appropriate | P1 | G | 3-6 sentences |
| S-05.B.2 | No sycophancy after pushback (Ch4) | P1 | G | Doesn't immediately agree |
| S-05.B.3 | Chapter-appropriate tone (Ch4) | P1 | G | Intimate, emotionally deep |
| S-05.B.4 | Persona consistency score >= 3 (Ch4) | P1 | G | Gemini R1 >= 3/5 |

### Decay

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-04.1.4 | Ch4 decay triggers after 49h | P0 | S+A | relationship_score decreases |
| S-04.8.1 | Decay skipped in game_over state | P1 | S+A | game_over score unchanged by decay task |
| S-04.8.2 | Decay skipped in won state | P1 | S+A | won score unchanged by decay task |

---

## Chapter 5: Established (Phase 06)

### Gameplay & Scoring

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-06.P.1 | Score accumulates through Ch5 play | P0 | A | Score trend upward over session |
| S-06.P.2 | Pipeline runs normally at Ch5 | P0 | A | pipeline_executions all status='done' |

### Engagement

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-06.E.1 | All 6 engagement states verified across game | P1 | A | in_zone, clingy, distant, flooding, ghost, re_engaged all tested |

### Boss Encounter (threshold 75%)

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-03.1.5 | Boss triggered at Ch5 threshold (75%) | P0 | S+A | game_status='boss_fight' |
| S-03.5.5 | Boss PASS judgment: partnership+autonomy | P1 | S+F | game_status='won' |
| S-03.8.2 | Ch5 boss PASS -> won state | P0 | S+F | game_status='won' |
| S-03.9.2 | Boss from game_over has no effect | P1 | S+A | game_over state persists |

### Victory Verification

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-11.2.1 | won state achievable via Ch5 boss PASS | P0 | S+F | game_status='won' |
| S-11.2.2 | won state sends variant messages | P1 | S+F | Messages differ from normal play |
| S-11.2.3 | won state persists after messages | P1 | S+A | game_status='won' unchanged |
| S-11.5.2 | Won state -> /start offers new game | P1 | F | Re-onboarding or confirmation offered |

### Portal Monitoring

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-06.PP.1 | Dashboard score matches DB (Ch5) | P0 | F | Browser agent value == SQL value |
| S-06.PP.2 | Chapter name shows "Established" | P0 | F | Text visible on dashboard |
| S-06.PP.3 | Engagement badge matches (Ch5) | P1 | F | Badge text == engagement_state.state |
| S-06.PP.4 | Conversations count correct (Ch5) | P1 | F | Count matches DB |
| S-06.PP.5 | Admin user row shows Ch5 | P1 | F | Admin page shows test user at Ch5 |

### Behavioral Assessment

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-06.B.1 | Response length Ch5 appropriate | P1 | G | Full paragraphs, authentic |
| S-06.B.2 | No sycophancy after pushback (Ch5) | P1 | G | Doesn't immediately agree |
| S-06.B.3 | Chapter-appropriate tone (Ch5) | P1 | G | Complete authenticity, healthy boundaries |
| S-06.B.4 | Persona consistency score >= 3 (Ch5) | P1 | G | Gemini R1 >= 3/5 |

### Decay

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-04.1.5 | Ch5 decay triggers after 73h | P0 | S+A | relationship_score decreases |
| S-04.3.2b | Decay rate: Ch5 = 0.2/hr | P1 | S+A | Slower decay at Ch5 |

---

## Portal — Player Pages (Phase P1)

All player-facing portal scenarios, tested at any chapter state.

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-08.1.1 | / redirects to login or /dashboard | P0 | F | No 500, page loads |
| S-08.1.2 | Magic link login works | P0 | F | Redirected to /dashboard after link click |
| S-08.1.3 | Unauthenticated /dashboard -> redirect to / | P0 | F | Redirect happens |
| S-08.2.1 | /dashboard renders relationship_score | P0 | F | Score visible |
| S-08.2.2 | /dashboard shows chapter | P0 | F | Chapter badge visible |
| S-08.2.3 | /dashboard no JS errors | P1 | F | console errors empty |
| S-08.3.1 | /engagement renders state badge | P1 | F | State badge matches DB |
| S-08.3.2 | /engagement shows frequency chart | P2 | F | Chart component rendered |
| S-08.4.1 | /vices renders vice categories | P1 | F | At least 1 vice visible if triggered |
| S-08.4.2 | /conversations renders message list | P1 | F | Conversations listed |
| S-08.4.3 | /conversations pagination | P2 | F | Load more works |
| S-08.5.1 | /diary renders Nikita's observations | P1 | F | memory_facts displayed |
| S-08.5.2 | /settings renders profile fields | P1 | F | Name, city visible |
| S-08.6.1 | All pages mobile-responsive | P2 | F | No horizontal scroll |
| S-08.6.2 | Dark mode applied across all pages | P1 | F | No white background |
| S-08.7.1 | Score data matches DB value | P0 | F | Portal score == users.relationship_score |
| S-08.7.2 | Chapter data matches DB value | P0 | F | Portal chapter == users.chapter |
| S-08.8.1 | Portal cold start (blank page recovery) | P1 | F | Loads within 10s on retry |
| S-08.8.2 | Network 4xx/5xx errors visible | P1 | F | Error state shown, not blank |
| S-08.9.1 | Session persists on refresh | P1 | F | No re-login required after refresh |
| S-8.2.2 | Insights page renders with non-zero deltas | P1 | F | Deltas visible |
| S-8.4.2 | Conversation detail page renders message thread | P1 | F | Messages shown |
| S-8.5.1 | No JS console errors across all player routes | P1 | F | 0 console errors |
| S-8.6.1 | Nikita's World hub renders MoodOrb and sections | P1 | F | MoodOrb + sections visible |
| S-8.6.2 | Nikita's Day renders with date navigation | P1 | F | Date nav functional |
| S-8.6.3 | Nikita's Mind renders thought feed or empty state | P1 | F | Content or empty state |
| S-8.6.4 | Storylines renders with "Show resolved" toggle | P1 | F | Toggle present |
| S-8.6.5 | Social Circle renders gallery or empty state | P1 | F | Content or empty state |
| S-8.7.1a | Diary page renders entries or empty state | P1 | F | Content or empty state |
| S-8.8.1a | Settings page renders email, timezone, Telegram status | P0 | F | All fields visible |
| S-8.1.3a | Score ring shows score matching DB within +-1 | P1 | F | Score ring accurate |
| S-8.9.1a | Login page renders email input and submit button | P2 | F | Form elements present |
| S-8.9.2 | Magic link email received within 30s | P2 | F | Email arrives |

---

## Portal — Admin Pages (Phase P2)

All admin-facing portal scenarios.

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-09.1.1 | /admin accessible with admin role | P0 | F | Page loads (no redirect) |
| S-09.1.2 | /admin redirects non-admin to / | P0 | F | Redirect happens |
| S-09.1.3 | Admin role check: raw_user_meta_data.role | P0 | A | role='admin' required |
| S-09.2.1 | /admin shows user count | P1 | F | User count > 0 |
| S-09.2.2 | /admin/users shows user table | P1 | F | Table with rows |
| S-09.2.3 | /admin/pipeline shows stage breakdown | P1 | F | Stage names visible |
| S-09.2.4 | /admin/jobs shows job_executions | P1 | F | Job rows visible |
| S-09.3.1 | /admin/conversations/<UID> shows full history | P1 | F | All conversations for user displayed |
| S-09.3.2 | /admin/voice shows voice metrics | P2 | F | Voice data rendered |
| S-09.3.3 | /admin/text shows text metrics | P2 | F | Text data rendered |
| S-09.4.1 | Admin data matches DB | P0 | F | Counts match SQL counts |
| S-09.4.2 | Admin can view test account data | P1 | F | Test email visible |
| S-09.5.1 | /admin no JS errors | P1 | F | Console errors empty |
| S-09.5.2 | Admin pages load < 5s | P2 | F | No timeout |
| S-09.6.1 | Admin sees all users | P1 | F | Multiple users in table |
| S-09.6.2 | Admin pipeline view links to user details | P2 | F | Click through to user pipeline |
| S-09.7.1 | ADMIN_EMAILS env var gates access | P0 | A | Only listed emails are admin |
| S-09.7.2 | Admin session persists on refresh | P1 | F | No re-login required |
| S-9.5.1 | /admin/text renders without crash (GH #152) | P1 | F | Page loads |
| S-9.5.2 | /admin/voice renders empty state or table | P1 | F | Content visible |
| S-9.6.1 | /admin/prompts renders empty state or table | P1 | F | Content visible |
| S-9.7.1 | /admin/conversations/[id] renders inspector | P1 | F | Inspector UI loads |
| S-9.8.1 | No JS console errors across all admin routes | P1 | F | 0 console errors |
| S-9.4.2 | Non-admin user redirected from /admin | P0 | A | Redirect confirmed |

### Voice Portal (from E07)

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-07.6.1 | Voice conversation history visible on portal | P1 | F | /conversations shows voice entries |
| S-07.6.2 | Voice metrics on admin portal | P2 | F | /admin/voice renders |

---

## Terminal States (Phase 07)

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-11.1.1 | game_over forced via SQL | P0 | S+A | game_status='game_over' |
| S-11.1.2 | game_over state persists after messages | P0 | S+F | game_status unchanged by messages |
| S-11.1.3 | game_over sends canned terminal response | P0 | S+F | Bot message is non-normal |
| S-11.1.4 | game_over no new score_history | P1 | S+A | No scoring in game_over |
| S-11.3.1 | /start from game_over -> re-onboarding | P0 | F | Re-onboarding prompted |
| S-11.3.2 | After restart: chapter=1, score=50 | P0 | A | Reset to initial state |
| S-11.3.3 | Old data cleared on restart | P1 | A | Previous score_history belongs to old session |
| S-11.4.1 | game_over via boss 3x fail | P0 | S+A | 3 boss_attempts -> game_over |
| S-11.4.2 | game_over via decay to zero | P0 | S+A | score=0 + decay -> game_over |
| S-11.5.1 | Boss timeout -> game_over | P0 | S+A | 25h elapsed -> game_over |

---

## System Jobs (Phase 08)

### Core Job Endpoints

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-10.10.1 | All 6 task endpoints return 200 on success | P0 | A | Each returns 200 with auth |
| S-10.3.1 | All tasks reject without auth | P0 | A | 401/403 on each endpoint |
| S-10.3.2 | Auth header format: Bearer $TASK_AUTH_SECRET | P0 | A | Correct token format |

### Process Conversations

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-10.1.1 | /tasks/process-conversations runs | P0 | A | 200, job_executions row created |
| S-10.1.2 | process-conversations completes | P0 | A | status='completed' |
| S-10.1.3 | process-conversations creates score_history | P0 | A | New score_history rows after run |

### Individual Jobs

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-10.2.1 | /tasks/decay runs | P0 | A | 200, decay applied |
| S-10.2.2 | /tasks/summary runs | P0 | A | 200, no error |
| S-10.2.3 | /tasks/touchpoints runs | P0 | A | 200, no error |
| S-10.2.4 | /tasks/boss-timeout runs | P0 | A | 200, no error |
| S-10.2.5 | /tasks/psyche-batch runs | P0 | A | 200, no error |

### Job Execution Tracking

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-10.4.1 | job_executions row per task run | P1 | A | Rows created with job_name |
| S-10.4.2 | No concurrent duplicate job runs | P0 | A | COUNT(*) status='in_progress' <= 1 |
| S-10.5.1 | Pipeline: all 10 stages complete | P1 | A | pipeline_executions all done |
| S-10.5.2 | Pipeline stages in order | P1 | A | stage timestamps are sequential |
| S-10.5.3 | Pipeline: failed stage marked as failed | P1 | A | status='failed' if stage errors |

### pg_cron & Edge Cases

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-10.6.1 | pg_cron triggers process-conversations | P2 | A | Automated runs visible in job_executions |
| S-10.6.2 | pg_cron triggers decay | P2 | A | Automated decay runs visible |
| S-10.7.1 | Task endpoint handles missing user gracefully | P1 | A | No 500 for non-existent user |
| S-10.7.2 | Task with no eligible users | P1 | A | Returns 200, 0 affected |
| S-10.8.1 | Long-running pipeline no timeout | P1 | A | Completes within 60s |
| S-10.8.2 | Pipeline creates memory_facts | P1 | A | memory_facts count increases |
| S-10.9.1 | Summary job creates conversation summary | P2 | A | conversations.summary populated |
| S-10.9.2 | Touchpoints job updates touchpoint_at | P2 | A | users.last_touchpoint_at updated |

### Decay Job

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-04.5.1 | /tasks/decay endpoint reachable | P0 | A | Returns 200 on auth request |
| S-04.5.2 | /tasks/decay rejects without auth | P0 | A | Returns 401/403 |
| S-04.6.1 | Decay task in job_executions | P1 | A | Row with job_name='decay' |
| S-04.6.2 | Multiple users decayed in one run | P1 | A | All eligible users affected |

---

## Adversarial & Gaps (Phase 09)

### Race Conditions

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-GAP-RC-1 | Concurrent decay + message scoring | P0 | S+A | No overlapping score updates < 500ms |
| S-GAP-RC-2 | Concurrent boss trigger + scoring | P1 | S+A | No race in boss state detection |
| S-GAP-RC-3 | Duplicate pipeline runs | P0 | A | No duplicate memory_facts |
| S-GAP-RC-4 | Concurrent /tasks/* calls | P1 | A | At most 1 in_progress per job |
| S-GAP-RC-5 | Pipeline re-run on same conversation | P1 | A | Idempotent: no duplicate score rows |
| S-GAP-RC-6 | Boss + decay firing simultaneously | P1 | S+A | No crash, defined behavior |
| S-GAP-RC-7 | Rapid /start x3 (within 2s) | P0 | F | No 500, graceful handling |
| S-GAP-RC-8 | Concurrent OTP submissions | P1 | F | Idempotent OTP handling |

### Security

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-GAP-SEC-1 | Webhook with wrong secret | P0 | A | 401/403 returned |
| S-GAP-SEC-2 | Task endpoint without auth | P0 | A | 401/403 returned |
| S-GAP-SEC-3 | RLS enabled on sensitive tables | P0 | A | rowsecurity=TRUE for users, user_metrics, conversations |
| S-GAP-SEC-4 | OTP brute force (3 wrong) | P1 | F | otp_attempts tracked, lockout triggered |
| S-GAP-SEC-5 | JWT tampered token rejected | P0 | A | 401 returned |
| S-GAP-SEC-6 | RLS blocks cross-user access | P0 | A | Cannot read other user's rows |
| S-GAP-SEC-7 | Admin endpoint blocks non-admin | P0 | A | Non-admin cannot access admin routes |
| S-GAP-SEC-8 | Replay attack on webhook | P1 | A | Duplicate update_id rejected or idempotent |

### Edge Cases

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-GAP-EDGE-1 | Empty/whitespace message | P1 | F | No 500, graceful ignore or reply |
| S-GAP-EDGE-2 | 4000-char message | P1 | F | No crash, bot responds |
| S-GAP-EDGE-3 | SQL injection in message | P0 | F | No crash, users table intact |
| S-GAP-EDGE-4 | Decay during boss_fight (G08) | P0 | S+A | No crash, behavior logged |
| S-GAP-EDGE-5 | Unicode / emoji in message | P1 | F | Stored and processed correctly |
| S-GAP-EDGE-6 | Message with newlines | P1 | F | No parsing error |
| S-GAP-EDGE-7 | Message with only numbers | P1 | F | Treated as text, no OTP false positive |
| S-GAP-EDGE-8 | Very high relationship_score (100) | P1 | S+A | Score capped, no overflow |

### Game Logic Boundaries

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-GAP-G01 | Boss trigger at exact threshold boundary | P0 | S+A | Boss triggers at exactly 55%/60%/etc |
| S-GAP-G02 | Score never drops below 0 | P0 | S+A | Score bounded at 0 |
| S-GAP-G03 | Boss timeout exactly at 25h | P1 | S+A | Timeout fires near 25h mark |
| S-GAP-G04 | Grace period exactly at expiry | P1 | S+A | Decay fires when grace_period_expires_at = NOW() |
| S-GAP-G05 | Chapter advance exactly at threshold | P0 | S+A | No off-by-one in threshold comparison |
| S-GAP-G06 | 3rd boss fail triggers game_over (not 2nd) | P0 | S+A | game_over on 3rd, not 2nd |
| S-GAP-G07 | won state not achievable without Ch5 boss | P1 | S+A | game_status='won' requires chapter=5 |
| S-GAP-G08 | Decay while in boss_fight | P0 | S+A | No crash, defined behavior |
| S-GAP-G09 | Pipeline with no new conversations | P1 | A | Returns 200, 0 conversations processed |
| S-GAP-G10 | Engagement state unchanged if no activity | P1 | A | state persists without messages |

### Performance

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-GAP-PERF-1 | Process-conversations < 60s | P1 | A | Pipeline completes within 60s |
| S-GAP-PERF-2 | Decay task < 10s | P2 | A | Task completes quickly |
| S-GAP-PERF-3 | Portal dashboard < 3s load | P2 | F | Page loads under 3s |
| S-GAP-PERF-4 | Telegram bot response < 15s | P1 | F | Reply within 15s of message |
| S-GAP-PERF-5 | Voice webhook response < 5s | P1 | A | Webhook acknowledges within 5s |

### Data Integrity

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-GAP-DATA-1 | relationship_score matches composite | P0 | A | users.relationship_score == formula result |
| S-GAP-DATA-2 | Score history audit trail complete | P1 | A | Every change has a score_history row |
| S-GAP-DATA-3 | engagement_state last_message_at accurate | P1 | A | Matches users.last_message_at |
| S-GAP-DATA-4 | memory_facts deduplicated | P1 | A | No exact duplicate content |
| S-GAP-DATA-5 | chapter consistent with score | P1 | A | chapter only advances when threshold met |
| S-GAP-DATA-6 | boss_attempts resets on chapter advance | P1 | A | boss_attempts=0 after PASS |
| S-GAP-DATA-7 | cool_down_until clears after expiry | P1 | A | Boss re-triggerable after cool_down |
| S-GAP-DATA-8 | pending_registrations cleaned after onboard | P1 | A | Row removed after user created |

### Integration

| ID | Description | P | Method | Pass Criteria |
|----|-------------|---|--------|---------------|
| S-GAP-INT-1 | ElevenLabs webhook format matches spec | P0 | A | Webhook parsing consistent with EL docs |
| S-GAP-INT-2 | Telegram inline buttons match expected labels | P1 | F | Button text matches app expectations |

---

## Summary

| Phase | Name | Scenarios | P0 | P1 | P2 | New |
|-------|------|-----------|----|----|----|----|
| 00 | Prerequisites | 5 | 5 | 0 | 0 | 5 |
| 01 | Onboarding | 32 | 18 | 10 | 4 | 2 |
| 02 | Ch1: Curiosity | 55 | 22 | 26 | 2 | 9 |
| 03 | Ch2: Intrigue | 34 | 10 | 20 | 0 | 9 |
| 04 | Ch3: Investment | 38 | 12 | 22 | 4 | 7 |
| 05 | Ch4: Intimacy | 38 | 12 | 20 | 4 | 9 |
| 06 | Ch5: Established | 18 | 6 | 10 | 0 | 9 |
| P1 | Portal Player | 33 | 6 | 20 | 7 | 0 |
| P2 | Portal Admin | 26 | 5 | 17 | 4 | 0 |
| 07 | Terminal States | 10 | 7 | 3 | 0 | 0 |
| 08 | System Jobs | 28 | 14 | 10 | 4 | 0 |
| 09 | Adversarial | 50 | 15 | 20 | 15 | 0 |
| | **TOTAL** | **~460** | **~132** | **~178** | **~44** | **~50** |

### Key Changes from v2

- Reorganized from 13 epics to chapter-based journey phases
- Each chapter phase includes: Gameplay, Engagement, Vice, Boss, Portal Monitoring (new), Behavioral Assessment (new), Decay
- ~50 new scenarios: per-chapter Portal Monitoring (5 per chapter x 5 chapters = 25), per-chapter Behavioral Assessment (4 per chapter x 5 chapters = 20), plus prerequisites and portal additions
- Portal Player/Admin scenarios consolidated into dedicated phases (P1/P2) for scenarios not tied to a specific chapter
- Voice scenarios placed in Ch3 (Investment) where voice unlocks
- Cross-Platform scenarios placed in Ch4 (Intimacy) where multi-platform play is most relevant
- All original 385 v2/v2.1 scenario IDs preserved for traceability
