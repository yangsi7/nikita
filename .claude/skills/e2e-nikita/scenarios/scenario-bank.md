# Scenario Bank — E2E Nikita (363 scenarios)

Condensed reference. Full Gherkin in `specs/048-e2e-full-lifecycle/user-story-bank/`.
Format: ID | Description | Priority | Pass Criteria

---

## E01: Registration & Onboarding (28 scenarios)

| ID | Description | P | Pass Criteria |
|----|-------------|---|---------------|
| S-01.1.1 | /start creates pending_registration | P0 | Row in pending_registrations |
| S-01.1.2 | OTP sent to email | P0 | Email arrives within 60s |
| S-01.1.3 | OTP verified → onboarding started | P0 | Bot asks for city |
| S-01.1.4 | Correct OTP accepted | P0 | Flow proceeds |
| S-01.1.5 | Wrong OTP rejected | P0 | Error message, otp_attempts incremented |
| S-01.1.6 | OTP lockout after 3 fails | P0 | Locked out message |
| S-01.2.1 | City collected | P0 | users.city = 'Zurich' |
| S-01.2.2 | Name collected | P0 | users.name populated |
| S-01.2.3 | Age collected | P0 | user_profiles.age populated |
| S-01.2.4 | Occupation collected | P0 | user_profiles.occupation populated |
| S-01.2.5 | Scenario selected via inline button | P0 | user_profiles.scenario_name set |
| S-01.3.1 | user row created with defaults | P0 | chapter=1, game_status=active, score=50 |
| S-01.3.2 | user_metrics row created | P0 | intimacy=50, passion=50, trust=50, secureness=50 |
| S-01.3.3 | user_profiles row created | P0 | scenario_name + backstory_summary present |
| S-01.3.4 | engagement_state row created | P0 | state='in_zone' |
| S-01.4.1 | Telegram ID stored | P0 | users.telegram_id = 746410893 |
| S-01.4.2 | /start on existing account restarts | P1 | Re-onboarding prompt shown |
| S-01.5.1 | Rapid /start (x3) no crash | P0 | No 500 error |
| S-01.5.2 | Duplicate OTP submission | P1 | Graceful error or idempotent |
| S-01.6.1 | Onboarding incomplete → no user row | P1 | No users row until all steps done |
| S-01.7.1 | Backstory generated after scenario select | P1 | backstory_summary not null |
| S-01.7.2 | Welcome message sent after onboarding | P0 | Bot sends first message |
| S-01.8.1 | Portal login works after onboarding | P1 | Magic link → /dashboard |
| S-01.8.2 | Portal shows chapter=1 | P1 | Dashboard renders chapter 1 |
| S-01.9.1 | Non-email sends before OTP handled | P1 | Bot prompts for OTP |
| S-01.9.2 | Empty OTP (whitespace) rejected | P1 | Error message shown |
| S-01.9.3 | Re-registration clears old data | P1 | Old user_metrics reset |
| S-01.9.4 | Onboarding timeout → pending cleared | P2 | pending_registrations cleaned |

---

## E02: Gameplay & Scoring (32 scenarios)

| ID | Description | P | Pass Criteria |
|----|-------------|---|---------------|
| S-02.1.1 | Message triggers pipeline | P0 | score_history row created |
| S-02.1.2 | Composite formula correct | P0 | intimacy×0.30+passion×0.25+trust×0.25+secureness×0.20 |
| S-02.1.3 | Score bounded 0-100 | P0 | relationship_score stays within range |
| S-02.2.1 | Engagement multiplier applied | P0 | score_history.engagement_multiplier != null |
| S-02.2.2 | in_zone multiplier = 1.0 | P1 | Score change proportional |
| S-02.2.3 | distant multiplier = 0.5 | P1 | Lower delta than in_zone |
| S-02.3.1 | memory_facts created after pipeline | P1 | At least 1 fact after 3 messages |
| S-02.3.2 | No duplicate memory_facts | P1 | HAVING COUNT(*) > 1 = 0 rows |
| S-02.4.1 | conversations row created | P0 | type='text', user_id correct |
| S-02.4.2 | Pipeline: 10 stages all complete | P1 | pipeline_executions all status='done' |
| S-02.5.1 | Bot response received | P0 | Bot replies within 15s |
| S-02.5.2 | Nikita response uses memory | P2 | Qualitative: references prior messages |
| S-02.6.1 | Score increases on good messages | P0 | composite_after > composite_before |
| S-02.6.2 | Passion target increases on flirtation | P1 | passion delta > 0 |
| S-02.6.3 | Trust target increases on vulnerability | P1 | trust delta > 0 |
| S-02.7.1 | engagement_state updated after message | P1 | last_message_at updated |
| S-02.7.2 | messages_last_hour incremented | P1 | messages_last_hour += 1 |
| S-02.8.1 | Multiple messages in session | P0 | All trigger scoring, no crash |
| S-02.8.2 | Score accumulates over session | P0 | Final score > initial score |
| S-02.9.1 | Chapter threshold reached → chapter advance | P0 | chapter incremented |
| S-02.9.2 | Chapter advance triggers boss | P0 | game_status='boss_fight' |
| S-02.10.1 | Scoring not blocked by boss_fight state | P1 | score_history row still created during boss |
| S-02.10.2 | Score capped at 100 | P1 | relationship_score never > 100 |
| S-02.11.1 | Vice signals detected in messages | P1 | user_vice_preferences updated |
| S-02.11.2 | Psyche state reflects current metrics | P1 | psyche_state table updated |
| S-02.12.1 | Low-quality messages decrease score | P1 | composite_after < composite_before |
| S-02.12.2 | Whitespace-only message no crash | P0 | No 500, graceful handling |
| S-02.12.3 | 4000-char message no crash | P1 | Bot responds, no 500 |
| S-02.12.4 | SQL injection in message no crash | P0 | users table intact |
| S-02.13.1 | Scoring source_platform = 'text' | P1 | score_history row has source_platform |
| S-02.13.2 | Consecutive messages without wait | P1 | All scored, no race |
| S-02.14.1 | game_over state blocks scoring | P1 | No new score_history in game_over |

---

## E03: Boss Encounters (30 scenarios)

| ID | Description | P | Pass Criteria |
|----|-------------|---|---------------|
| S-03.1.1 | Boss triggered at Ch1 threshold (55%) | P0 | game_status='boss_fight' |
| S-03.1.2 | Boss triggered at Ch2 threshold (60%) | P0 | game_status='boss_fight' |
| S-03.1.3 | Boss triggered at Ch3 threshold (65%) | P0 | game_status='boss_fight' |
| S-03.1.4 | Boss triggered at Ch4 threshold (70%) | P0 | game_status='boss_fight' |
| S-03.1.5 | Boss triggered at Ch5 threshold (75%) | P0 | game_status='boss_fight' |
| S-03.2.1 | Strong PASS → chapter advanced | P0 | chapter incremented, game_status=active |
| S-03.2.2 | Strong PASS → boss_attempts reset | P1 | boss_attempts=0 |
| S-03.2.3 | Strong PASS → cool_down_until set | P1 | cool_down_until > NOW() |
| S-03.3.1 | Weak FAIL → boss_attempts += 1 | P0 | boss_attempts = 1 |
| S-03.3.2 | 3x FAIL → game_over | P0 | game_status='game_over' |
| S-03.3.3 | game_over → canned response only | P0 | Bot sends terminal message |
| S-03.3.4 | game_over → no scoring | P1 | No new score_history rows |
| S-03.4.1 | Double-trigger prevention | P0 | Second message during boss_fight doesn't re-trigger |
| S-03.4.2 | Cool-down prevents re-trigger after PASS | P1 | Boss not triggered until cool_down_until expires |
| S-03.5.1 | Boss PASS judgment: intellectual confidence | P1 | LLM or forced: chapter advances |
| S-03.5.2 | Boss PASS judgment: stands ground | P1 | LLM or forced: chapter advances |
| S-03.5.3 | Boss PASS judgment: secure attachment | P1 | LLM or forced: chapter advances |
| S-03.5.4 | Boss PASS judgment: genuine disclosure | P1 | LLM or forced: chapter advances |
| S-03.5.5 | Boss PASS judgment: partnership+autonomy | P1 | game_status='won' |
| S-03.6.1 | Boss FAIL: evasive response | P1 | boss_attempts += 1 |
| S-03.6.2 | Boss FAIL: jealous response | P1 | boss_attempts += 1 |
| S-03.6.3 | Boss FAIL: sycophantic response | P1 | boss_attempts += 1 |
| S-03.6.4 | Boss FAIL: deflection | P1 | boss_attempts += 1 |
| S-03.7.1 | Boss timeout (25h) → game_over | P0 | game_status='game_over' |
| S-03.7.2 | Boss timeout task runs | P0 | /tasks/boss-timeout completes without error |
| S-03.8.1 | Ch1 boss PASS → Ch2 gameplay starts | P0 | chapter=2, normal messages processed |
| S-03.8.2 | Ch5 boss PASS → won state | P0 | game_status='won' |
| S-03.9.1 | Boss attempt counter persistent | P1 | boss_attempts survives message sends |
| S-03.9.2 | Boss from game_over has no effect | P1 | game_over state persists |
| S-03.10.1 | Decay during boss_fight no crash | P0 | No 500, behavior logged |

---

## E04: Decay (24 scenarios)

| ID | Description | P | Pass Criteria |
|----|-------------|---|---------------|
| S-04.1.1 | Ch1 decay triggers after 9h silence | P0 | relationship_score decreases |
| S-04.1.2 | Ch2 decay triggers after 17h | P0 | relationship_score decreases |
| S-04.1.3 | Ch3 decay triggers after 25h | P0 | relationship_score decreases |
| S-04.1.4 | Ch4 decay triggers after 49h | P0 | relationship_score decreases |
| S-04.1.5 | Ch5 decay triggers after 73h | P0 | relationship_score decreases |
| S-04.2.1 | Grace period prevents decay | P0 | Score unchanged when grace active |
| S-04.2.2 | Grace period starts after boss PASS | P1 | grace_period_expires_at set |
| S-04.2.3 | Grace period expires correctly | P1 | After expiry, decay applies |
| S-04.3.1 | Decay rate: Ch1 = 0.8/hr | P1 | Score reduces by ~0.8 per hour |
| S-04.3.2 | Decay rate: Ch5 = 0.2/hr | P1 | Slower decay at Ch5 |
| S-04.3.3 | Decay bounded at 0 | P0 | relationship_score never goes negative |
| S-04.4.1 | Decay to zero → game_over | P0 | game_status='game_over' |
| S-04.4.2 | Decay updates last_decay_at | P1 | last_decay_at updated |
| S-04.5.1 | /tasks/decay endpoint reachable | P0 | Returns 200 on auth request |
| S-04.5.2 | /tasks/decay rejects without auth | P0 | Returns 401/403 |
| S-04.6.1 | Decay task in job_executions | P1 | Row with job_name='decay' |
| S-04.6.2 | Multiple users decayed in one run | P1 | All eligible users affected |
| S-04.7.1 | Message after decay resets timer | P0 | last_message_at updated |
| S-04.7.2 | Message during grace extends grace | P1 | grace_period_expires_at updated |
| S-04.8.1 | Decay skipped in game_over state | P1 | game_over score unchanged by decay task |
| S-04.8.2 | Decay skipped in won state | P1 | won score unchanged by decay task |
| S-04.9.1 | Decay during boss_fight (G08) | P0 | No crash (behavior logged) |
| S-04.9.2 | Decay with score at 0.3 → game_over | P0 | game_status='game_over' |
| S-04.10.1 | user_metrics also decayed | P1 | intimacy/passion/trust/secureness all decrease |

---

## E05: Engagement States (26 scenarios)

| ID | Description | P | Pass Criteria |
|----|-------------|---|---------------|
| S-05.1.1 | in_zone state (2msg/hr, 6/day) | P0 | state='in_zone' |
| S-05.1.2 | clingy state (8+ msg/hr) | P0 | state='clingy' |
| S-05.1.3 | distant state (0 msg/48h) | P0 | state='distant' |
| S-05.1.4 | flooding state (15+ msg/hr) | P1 | state='flooding' |
| S-05.1.5 | ghost state (7+ days silence) | P1 | state='ghost' |
| S-05.1.6 | re-engaged state transition | P1 | state='re_engaged' after ghost + msg |
| S-05.2.1 | clingy multiplier = 0.2 | P0 | engagement_multiplier=0.2 in score_history |
| S-05.2.2 | distant multiplier = 0.5 | P0 | engagement_multiplier=0.5 in score_history |
| S-05.2.3 | in_zone multiplier = 1.0 | P0 | engagement_multiplier=1.0 in score_history |
| S-05.2.4 | flooding multiplier = 0.1 | P1 | engagement_multiplier=0.1 |
| S-05.3.1 | Portal engagement page shows state badge | P1 | Badge text matches DB state |
| S-05.3.2 | Portal shows frequency chart | P2 | Chart rendered |
| S-05.4.1 | State transitions logged | P1 | engagement_state.updated_at changes |
| S-05.4.2 | messages_last_hour decrements over time | P1 | After 1h, count reduces |
| S-05.5.1 | clingy → in_zone after cooling period | P1 | State transitions back |
| S-05.5.2 | distant → in_zone after message | P1 | State transitions after message |
| S-05.6.1 | Rapid message burst triggers clingy | P0 | 8 messages in 5min → state='clingy' |
| S-05.6.2 | 48h silence triggers distant | P0 | Timestamp manipulation → state='distant' |
| S-05.7.1 | re_engaged multiplier = 1.3 | P1 | Bonus multiplier after ghost recovery |
| S-05.7.2 | Nikita's tone shifts with state | P2 | Qualitative: response tone differs |
| S-05.8.1 | engagement_state row exists | P0 | Row present after onboarding |
| S-05.8.2 | State persists across pipeline runs | P1 | State unchanged without message activity |
| S-05.9.1 | Flooding state throttles responses | P1 | Nikita sends limited replies |
| S-05.9.2 | Ghost state — bot still responds | P1 | Bot responds, state noted in reply |
| S-05.10.1 | Portal engagement data accurate | P1 | Portal values match DB values |
| S-05.10.2 | Engagement affects scoring visibly | P0 | Two identical messages at different states yield different deltas |

---

## E06: Vice System (24 scenarios)

| ID | Description | P | Pass Criteria |
|----|-------------|---|---------------|
| S-06.1.1 | substances vice detected | P0 | user_vice_preferences row, intensity_level >= 1 |
| S-06.1.2 | risk_taking vice detected | P0 | user_vice_preferences row, intensity_level >= 1 |
| S-06.1.3 | sexuality vice detected | P0 | user_vice_preferences row |
| S-06.1.4 | dark_humor vice detected | P0 | user_vice_preferences row |
| S-06.1.5 | intellectual_dominance vice detected | P0 | user_vice_preferences row |
| S-06.1.6 | emotional_intensity vice detected | P1 | user_vice_preferences row |
| S-06.1.7 | rule_breaking vice detected | P1 | user_vice_preferences row |
| S-06.1.8 | vulnerability vice detected | P1 | user_vice_preferences row |
| S-06.2.1 | intensity_level increases with repetition | P1 | 2nd trigger msg → intensity_level = 2 |
| S-06.2.2 | detection_count increments | P1 | detection_count increases per detection |
| S-06.3.1 | Nikita's response adapts to vice profile | P2 | Qualitative: tone shift observable |
| S-06.3.2 | Vice profile affects prompt injection | P2 | Qualitative: psyche_state reflects vices |
| S-06.4.1 | Portal /vices shows vice categories | P1 | Page renders with categories |
| S-06.4.2 | Portal vice data matches DB | P1 | Displayed intensities match user_vice_preferences |
| S-06.5.1 | Vice not detected in generic messages | P1 | No new rows for neutral messages |
| S-06.5.2 | Multiple vices in one message | P1 | Multiple rows updated |
| S-06.6.1 | Vice system runs in pipeline | P0 | pipeline_executions has vice stage |
| S-06.6.2 | Vice trigger pipeline without blocking | P0 | Pipeline completes even if vice detection fails |
| S-06.7.1 | Vice preferences persist across sessions | P1 | intensity_level unchanged between sessions |
| S-06.7.2 | Vice preferences reset on /start | P1 | Old preferences cleared on re-onboarding |
| S-06.8.1 | Psyche batch job updates psyche_state | P1 | psyche_state.updated_at changes after batch |
| S-06.8.2 | /tasks/psyche-batch endpoint works | P0 | Returns 200 on auth request |
| S-06.9.1 | Low-confidence vice signal not detected | P2 | Ambiguous messages don't create false positives |
| S-06.9.2 | Vice detection across chapters | P1 | Detection works at Ch3, Ch4, Ch5 |

---

## E07: Voice (20 scenarios)

| ID | Description | P | Pass Criteria |
|----|-------------|---|---------------|
| S-07.1.1 | Pre-call /api/v1/voice/context returns data | P0 | 200 with user context JSON |
| S-07.1.2 | Context includes memory_facts | P1 | response.memory_facts not empty |
| S-07.1.3 | get_memory server tool responds | P0 | Tool returns recent memories |
| S-07.1.4 | get_context server tool responds | P0 | Tool returns user profile |
| S-07.2.1 | score_turn server tool updates score | P0 | score_history row after tool call |
| S-07.2.2 | score_turn source_platform = 'voice' | P1 | source_platform='voice' in score_history |
| S-07.3.1 | Post-call webhook updates relationship_score | P0 | score increases after POST |
| S-07.3.2 | Post-call webhook creates conversations row | P1 | type='voice' row created |
| S-07.3.3 | Post-call webhook creates memory_facts | P1 | memory_facts from transcript |
| S-07.4.1 | Voice webhook auth required | P0 | 401/403 without ELEVENLABS_WEBHOOK_SECRET |
| S-07.4.2 | Voice webhook with unknown telegram_id | P1 | Graceful error, no crash |
| S-07.5.1 | Opening template selected | P1 | Correct YAML template used for profile |
| S-07.5.2 | Warm_intro template for standard profile | P1 | warm_intro template selected |
| S-07.5.3 | Challenge template for intellectual_dominance | P1 | challenge template selected |
| S-07.6.1 | Voice conversation history visible on portal | P1 | /conversations shows voice entries |
| S-07.6.2 | Voice metrics on admin portal | P2 | /admin/voice renders |
| S-07.7.1 | Webhook idempotent (duplicate POST) | P1 | No duplicate memory_facts on second POST |
| S-07.7.2 | Empty transcript handled | P1 | No crash on empty transcript array |
| S-07.8.1 | Duration_seconds stored | P2 | conversations.duration_seconds populated |
| S-07.8.2 | Long transcript (50+ turns) no crash | P1 | Webhook returns 200 |

---

## E08: Portal — Player (20 scenarios)

| ID | Description | P | Pass Criteria |
|----|-------------|---|---------------|
| S-08.1.1 | / redirects to login or /dashboard | P0 | No 500, page loads |
| S-08.1.2 | Magic link login works | P0 | Redirected to /dashboard after link click |
| S-08.1.3 | Unauthenticated /dashboard → redirect to / | P0 | Redirect happens |
| S-08.2.1 | /dashboard renders relationship_score | P0 | Score visible |
| S-08.2.2 | /dashboard shows chapter | P0 | Chapter badge visible |
| S-08.2.3 | /dashboard no JS errors | P1 | console errors empty |
| S-08.3.1 | /engagement renders state badge | P1 | State badge matches DB |
| S-08.3.2 | /engagement shows frequency chart | P2 | Chart component rendered |
| S-08.4.1 | /vices renders vice categories | P1 | At least 1 vice visible if triggered |
| S-08.4.2 | /conversations renders message list | P1 | Conversations listed |
| S-08.4.3 | /conversations pagination | P2 | Load more works |
| S-08.5.1 | /diary renders Nikita's observations | P1 | memory_facts displayed |
| S-08.5.2 | /settings renders profile fields | P1 | Name, city visible |
| S-08.6.1 | All pages mobile-responsive | P2 | No horizontal scroll |
| S-08.6.2 | Dark mode applied across all pages | P1 | No white background |
| S-08.7.1 | Score data matches DB value | P0 | Portal score == users.relationship_score |
| S-08.7.2 | Chapter data matches DB value | P0 | Portal chapter == users.chapter |
| S-08.8.1 | Portal cold start (blank page recovery) | P1 | Loads within 10s on retry |
| S-08.8.2 | Network 4xx/5xx errors visible | P1 | Error state shown, not blank |
| S-08.9.1 | Session persists on refresh | P1 | No re-login required after refresh |

---

## E09: Portal — Admin (18 scenarios)

| ID | Description | P | Pass Criteria |
|----|-------------|---|---------------|
| S-09.1.1 | /admin accessible with admin role | P0 | Page loads (no redirect) |
| S-09.1.2 | /admin redirects non-admin to / | P0 | Redirect happens |
| S-09.1.3 | Admin role check: raw_user_meta_data.role | P0 | role='admin' required |
| S-09.2.1 | /admin shows user count | P1 | User count > 0 |
| S-09.2.2 | /admin/users shows user table | P1 | Table with rows |
| S-09.2.3 | /admin/pipeline shows stage breakdown | P1 | Stage names visible |
| S-09.2.4 | /admin/jobs shows job_executions | P1 | Job rows visible |
| S-09.3.1 | /admin/conversations/<UID> shows full history | P1 | All conversations for user displayed |
| S-09.3.2 | /admin/voice shows voice metrics | P2 | Voice data rendered |
| S-09.3.3 | /admin/text shows text metrics | P2 | Text data rendered |
| S-09.4.1 | Admin data matches DB | P0 | Counts match SQL counts |
| S-09.4.2 | Admin can view test account data | P1 | simon.yang.ch@gmail.com visible |
| S-09.5.1 | /admin no JS errors | P1 | Console errors empty |
| S-09.5.2 | Admin pages load < 5s | P2 | No timeout |
| S-09.6.1 | Admin sees all users | P1 | Multiple users in table if DB has them |
| S-09.6.2 | Admin pipeline view links to user details | P2 | Click through to user pipeline |
| S-09.7.1 | ADMIN_EMAILS env var gates access | P0 | Only listed emails are admin |
| S-09.7.2 | Admin session persists on refresh | P1 | No re-login required |

---

## E10: Background Jobs (24 scenarios)

| ID | Description | P | Pass Criteria |
|----|-------------|---|---------------|
| S-10.1.1 | /tasks/process-conversations runs | P0 | 200, job_executions row created |
| S-10.1.2 | process-conversations completes | P0 | status='completed' |
| S-10.1.3 | process-conversations creates score_history | P0 | New score_history rows after run |
| S-10.2.1 | /tasks/decay runs | P0 | 200, decay applied |
| S-10.2.2 | /tasks/summary runs | P0 | 200, no error |
| S-10.2.3 | /tasks/touchpoints runs | P0 | 200, no error |
| S-10.2.4 | /tasks/boss-timeout runs | P0 | 200, no error |
| S-10.2.5 | /tasks/psyche-batch runs | P0 | 200, no error |
| S-10.3.1 | All tasks reject without auth | P0 | 401/403 on each endpoint |
| S-10.3.2 | Auth header format: Bearer $TASK_AUTH_SECRET | P0 | Correct token format |
| S-10.4.1 | job_executions row per task run | P1 | Rows created with job_name |
| S-10.4.2 | No concurrent duplicate job runs | P0 | COUNT(*) status='in_progress' <= 1 |
| S-10.5.1 | Pipeline: all 10 stages complete | P1 | pipeline_executions all done |
| S-10.5.2 | Pipeline stages in order | P1 | stage timestamps are sequential |
| S-10.5.3 | Pipeline: failed stage marked as failed | P1 | status='failed' if stage errors |
| S-10.6.1 | pg_cron triggers process-conversations | P2 | Automated runs visible in job_executions |
| S-10.6.2 | pg_cron triggers decay | P2 | Automated decay runs visible |
| S-10.7.1 | Task endpoint handles missing user gracefully | P1 | No 500 for non-existent user |
| S-10.7.2 | Task with no eligible users | P1 | Returns 200, 0 affected |
| S-10.8.1 | Long-running pipeline no timeout | P1 | Completes within 60s |
| S-10.8.2 | Pipeline creates memory_facts | P1 | memory_facts count increases |
| S-10.9.1 | Summary job creates conversation summary | P2 | conversations.summary populated |
| S-10.9.2 | Touchpoints job updates touchpoint_at | P2 | users.last_touchpoint_at updated |
| S-10.10.1 | All 6 task endpoints return 200 on success | P0 | Each returns 200 with auth |

---

## E11: Terminal States (14 scenarios)

See `workflows/11-terminal-states.md` for execution steps.

| ID | Description | P | Pass Criteria |
|----|-------------|---|---------------|
| S-11.1.1 | game_over forced via SQL | P0 | game_status='game_over' |
| S-11.1.2 | game_over state persists after messages | P0 | game_status unchanged by messages |
| S-11.1.3 | game_over sends canned terminal response | P0 | Bot message is non-normal |
| S-11.1.4 | game_over no new score_history | P1 | No scoring in game_over |
| S-11.2.1 | won state achievable via Ch5 boss PASS | P0 | game_status='won' |
| S-11.2.2 | won state sends variant messages | P1 | Messages differ from normal play |
| S-11.2.3 | won state persists after messages | P1 | game_status='won' unchanged |
| S-11.3.1 | /start from game_over → re-onboarding | P0 | Re-onboarding prompted |
| S-11.3.2 | After restart: chapter=1, score=50 | P0 | Reset to initial state |
| S-11.3.3 | Old data cleared on restart | P1 | Previous score_history belongs to old session |
| S-11.4.1 | game_over via boss 3x fail | P0 | 3 boss_attempts → game_over |
| S-11.4.2 | game_over via decay to zero | P0 | score=0 + decay → game_over |
| S-11.5.1 | Boss timeout → game_over | P0 | 25h elapsed → game_over |
| S-11.5.2 | Won state → /start offers new game | P1 | Re-onboarding or confirmation offered |

---

## E12: Cross-Platform (12 scenarios)

See `workflows/12-cross-platform.md` for execution steps.

| ID | Description | P | Pass Criteria |
|----|-------------|---|---------------|
| S-12.1.1 | Voice webhook updates relationship_score | P0 | Score increases after POST |
| S-12.1.2 | source_platform='voice' in score_history | P1 | Row with correct platform |
| S-12.2.1 | Text score updates same user_metrics table | P0 | Both platforms write to user_metrics |
| S-12.2.2 | Voice score uses same composite formula | P0 | Formula consistent across platforms |
| S-12.3.1 | Memory shared across platforms | P1 | memory_facts include voice context (qualitative) |
| S-12.3.2 | Nikita text references voice conversation | P2 | Qualitative response check |
| S-12.4.1 | Both conversation types in history | P1 | type='text' and type='voice' both exist |
| S-12.4.2 | Voice conversation duration stored | P2 | duration_seconds populated |
| S-12.5.1 | Portal shows both text and voice | P1 | /conversations displays both types |
| S-12.5.2 | Admin portal shows platform breakdown | P2 | /admin/voice vs /admin/text data |
| S-12.6.1 | Voice scoring does not double-apply | P1 | One score_history row per webhook call |
| S-12.6.2 | Text scoring not affected by voice webhook | P0 | Text score_history rows unaffected |

---

## E13: Gap Scenarios — Adversarial (50 scenarios)

| ID | Description | P | Pass Criteria |
|----|-------------|---|---------------|
| S-GAP-RC-1 | Concurrent decay + message scoring | P0 | No overlapping score updates < 500ms |
| S-GAP-RC-2 | Concurrent boss trigger + scoring | P1 | No race in boss state detection |
| S-GAP-RC-3 | Duplicate pipeline runs | P0 | No duplicate memory_facts |
| S-GAP-RC-4 | Concurrent /tasks/* calls | P1 | At most 1 in_progress per job |
| S-GAP-RC-5 | Pipeline re-run on same conversation | P1 | Idempotent: no duplicate score rows |
| S-GAP-RC-6 | Boss + decay firing simultaneously | P1 | No crash, defined behavior |
| S-GAP-RC-7 | Rapid /start x3 (within 2s) | P0 | No 500, graceful handling |
| S-GAP-RC-8 | Concurrent OTP submissions | P1 | Idempotent OTP handling |
| S-GAP-SEC-1 | Webhook with wrong secret | P0 | 401/403 returned |
| S-GAP-SEC-2 | Task endpoint without auth | P0 | 401/403 returned |
| S-GAP-SEC-3 | RLS enabled on sensitive tables | P0 | rowsecurity=TRUE for users, user_metrics, conversations |
| S-GAP-SEC-4 | OTP brute force (3 wrong) | P1 | otp_attempts tracked, lockout triggered |
| S-GAP-SEC-5 | JWT tampered token rejected | P0 | 401 returned |
| S-GAP-SEC-6 | RLS blocks cross-user access | P0 | Cannot read other user's rows |
| S-GAP-SEC-7 | Admin endpoint blocks non-admin | P0 | Non-admin cannot access admin routes |
| S-GAP-SEC-8 | Replay attack on webhook | P1 | Duplicate update_id rejected or idempotent |
| S-GAP-EDGE-1 | Empty/whitespace message | P1 | No 500, graceful ignore or reply |
| S-GAP-EDGE-2 | 4000-char message | P1 | No crash, bot responds |
| S-GAP-EDGE-3 | SQL injection in message | P0 | No crash, users table intact |
| S-GAP-EDGE-4 | Decay during boss_fight (G08) | P0 | No crash, behavior logged |
| S-GAP-EDGE-5 | Unicode / emoji in message | P1 | Stored and processed correctly |
| S-GAP-EDGE-6 | Message with newlines | P1 | No parsing error |
| S-GAP-EDGE-7 | Message with only numbers | P1 | Treated as text, no OTP false positive |
| S-GAP-EDGE-8 | Very high relationship_score (100) | P1 | Score capped, no overflow |
| S-GAP-G01 | Boss trigger at exact threshold boundary | P0 | Boss triggers at exactly 55%/60%/etc |
| S-GAP-G02 | Score never drops below 0 | P0 | Score bounded at 0 |
| S-GAP-G03 | Boss timeout exactly at 25h | P1 | Timeout fires near 25h mark |
| S-GAP-G04 | Grace period exactly at expiry | P1 | Decay fires when grace_period_expires_at = NOW() |
| S-GAP-G05 | Chapter advance exactly at threshold | P0 | No off-by-one in threshold comparison |
| S-GAP-G06 | 3rd boss fail triggers game_over (not 2nd) | P0 | game_over on 3rd, not 2nd |
| S-GAP-G07 | won state not achievable without Ch5 boss | P1 | game_status='won' requires chapter=5 |
| S-GAP-G08 | Decay while in boss_fight | P0 | No crash, defined behavior |
| S-GAP-G09 | Pipeline with no new conversations | P1 | Returns 200, 0 conversations processed |
| S-GAP-G10 | Engagement state unchanged if no activity | P1 | state persists without messages |
| S-GAP-PERF-1 | Process-conversations < 60s | P1 | Pipeline completes within 60s |
| S-GAP-PERF-2 | Decay task < 10s | P2 | Task completes quickly |
| S-GAP-PERF-3 | Portal dashboard < 3s load | P2 | Page loads under 3s |
| S-GAP-PERF-4 | Telegram bot response < 15s | P1 | Reply within 15s of message |
| S-GAP-PERF-5 | Voice webhook response < 5s | P1 | Webhook acknowledges within 5s |
| S-GAP-DATA-1 | relationship_score matches composite | P0 | users.relationship_score == formula result |
| S-GAP-DATA-2 | Score history audit trail complete | P1 | Every change has a score_history row |
| S-GAP-DATA-3 | engagement_state last_message_at accurate | P1 | Matches users.last_message_at |
| S-GAP-DATA-4 | memory_facts deduplicated | P1 | No exact duplicate content |
| S-GAP-DATA-5 | chapter consistent with score | P1 | chapter only advances when threshold met |
| S-GAP-DATA-6 | boss_attempts resets on chapter advance | P1 | boss_attempts=0 after PASS |
| S-GAP-DATA-7 | cool_down_until clears after expiry | P1 | Boss re-triggerable after cool_down |
| S-GAP-DATA-8 | pending_registrations cleaned after onboard | P1 | Row removed after user created |
| S-GAP-INT-1 | ElevenLabs webhook format matches spec | P0 | Webhook parsing consistent with EL docs |
| S-GAP-INT-2 | Telegram inline buttons match expected labels | P1 | Button text matches app expectations |

## E08 Additions (13 new scenarios — v2.1)
| ID | Priority | Description | Method |
|----|----------|-------------|--------|
| S-8.2.2 | P1 | Insights page renders with non-zero deltas | F |
| S-8.4.2 | P1 | Conversation detail page renders message thread | F |
| S-8.5.1 | P1 | No JS console errors across all player routes | F |
| S-8.6.1 | P1 | Nikita's World hub renders MoodOrb and sections | F |
| S-8.6.2 | P1 | Nikita's Day renders with date navigation | F |
| S-8.6.3 | P1 | Nikita's Mind renders thought feed or empty state | F |
| S-8.6.4 | P1 | Storylines renders with "Show resolved" toggle | F |
| S-8.6.5 | P1 | Social Circle renders gallery or empty state | F |
| S-8.7.1 | P1 | Diary page renders entries or empty state | F |
| S-8.8.1 | P0 | Settings page renders with email, timezone, Telegram status | F |
| S-8.1.3 | P1 | Score ring shows score matching DB within +-1 | F |
| S-8.9.1 | P2 | Login page renders email input and submit button | F |
| S-8.9.2 | P2 | Magic link email received within 30s | F |

## E09 Additions (6 new scenarios — v2.1)
| ID | Priority | Description | Method |
|----|----------|-------------|--------|
| S-9.5.1 | P1 | /admin/text renders without crash (GH #152 regression) | F |
| S-9.5.2 | P1 | /admin/voice renders empty state or table | F |
| S-9.6.1 | P1 | /admin/prompts renders empty state or table | F |
| S-9.7.1 | P1 | /admin/conversations/[id] renders inspector | F |
| S-9.8.1 | P1 | No JS console errors across all admin routes | F |
| S-9.4.2 | P0 | Non-admin user redirected from /admin | A |

## E03 Additions (1 new scenario — v2.1)
| ID | Priority | Description | Method |
|----|----------|-------------|--------|
| S-3.5.1 | P1 | Boss PARTIAL/truce outcome documented | S+F |

## E04 Additions (2 new scenarios — v2.1)
| ID | Priority | Description | Method |
|----|----------|-------------|--------|
| S-4.2.1a | P1 | Ch1 decay rate correct (~0.8%/hr) | S+A |
| S-4.2.1b | P1 | Ch5 decay rate correct (~0.2%/hr) | S+A |

**Updated Total**: ~385 scenarios (363 original + 22 new)
