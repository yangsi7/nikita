# E10: Background Jobs & Pipeline (39 scenarios)

> Epic: E10 | User Stories: 10 | Priority: P0=10, P1=15, P2=8, P3=0
> MCP Tools: Supabase MCP, Telegram MCP, gcloud CLI
> Source files: tasks.py, processor.py, calculator.py, orchestrator.py, session_detector.py, conversation_repository.py

---

## US-10.1: Decay Job
### MCP Tools: Supabase MCP, gcloud CLI

```gherkin
Scenario: S-10.1.1 - Hourly decay job processes eligible users past grace period [P0-Critical]
  Given 3 active users exist in the database:
    | user   | chapter | last_interaction_at         | relationship_score | game_status |
    | User_A | 1       | now() - interval '10 hours' | 60.00              | active      |
    | User_B | 1       | now() - interval '5 hours'  | 55.00              | active      |
    | User_C | 3       | now() - interval '25 hours' | 70.00              | active      |
  And Chapter 1 grace period is 8 hours with decay rate 0.8%/hr
  And Chapter 3 grace period is 24 hours with decay rate 0.4%/hr
  When POST /tasks/decay is called with valid Authorization: Bearer {TASK_AUTH_SECRET} header
  Then User_A score decreases (10h - 8h grace = 2h overdue * 0.8 = 1.6 points)
  And User_B score remains 55.00 (5h < 8h grace period, within grace)
  And User_C score decreases (25h - 24h grace = 1h overdue * 0.4 = 0.4 points)
  And response.status = "ok"
  And response.processed >= 2
  And response.decayed = 2
  And a job_executions record is created with job_name="decay" and status="completed"
  # Verify: Supabase MCP → SELECT relationship_score FROM users WHERE id IN (User_A_id, User_B_id, User_C_id)
  # Verify: Supabase MCP → SELECT * FROM score_history WHERE event_type='decay' AND recorded_at > now() - interval '1 minute'
  # Verify: Supabase MCP → SELECT * FROM job_executions WHERE job_name='decay' ORDER BY started_at DESC LIMIT 1
  # Source: nikita/engine/decay/calculator.py:66-72 (grace period check), nikita/engine/constants.py:147-162 (rates/periods)

Scenario: S-10.1.2 - No decay applied within grace period [P0-Critical]
  Given a user in Chapter 2 with last_interaction_at = now() - interval '15 hours' and relationship_score = 65.00
  And Chapter 2 grace period is 16 hours
  When POST /tasks/decay is called with valid Authorization header
  Then the user's relationship_score remains 65.00
  And response.decayed = 0
  And no score_history record with event_type='decay' is created for this user
  # Verify: Supabase MCP → SELECT relationship_score FROM users WHERE id = {user_id}
  # Verify: Supabase MCP → SELECT count(*) FROM score_history WHERE user_id = {user_id} AND event_type='decay' AND recorded_at > now() - interval '1 minute'
  # Source: nikita/engine/decay/calculator.py:70-72 (strictly past grace, boundary is safe)

Scenario: S-10.1.3 - Decay to score 0 triggers game_over [P0-Critical]
  Given a user in Chapter 1 with relationship_score = 0.50 and last_interaction_at = now() - interval '24 hours'
  And game_status = "active"
  When POST /tasks/decay is called with valid Authorization header
  Then the user's relationship_score becomes 0.00
  And the user's game_status changes to "game_over"
  And response.game_overs >= 1
  And a score_history record is created with event_type='decay' and the score_after = 0
  # Verify: Supabase MCP → SELECT game_status, relationship_score FROM users WHERE id = {user_id}
  # Verify: Supabase MCP → SELECT * FROM score_history WHERE user_id = {user_id} AND event_type='decay' ORDER BY recorded_at DESC LIMIT 1
  # Source: nikita/engine/decay/calculator.py:113 (game_over_triggered = score_after == 0)

Scenario: S-10.1.4 - Decay skips users in boss_fight, game_over, and won status [P1-High]
  Given 3 users exist:
    | user   | game_status | chapter | last_interaction_at         | relationship_score |
    | User_D | boss_fight  | 2       | now() - interval '20 hours' | 62.00              |
    | User_E | game_over   | 1       | now() - interval '48 hours' | 0.00               |
    | User_F | won         | 5       | now() - interval '100 hours'| 85.00              |
  When POST /tasks/decay is called with valid Authorization header
  Then User_D score remains 62.00
  And User_E score remains 0.00
  And User_F score remains 85.00
  And response.decayed = 0
  # Verify: Supabase MCP → SELECT relationship_score, game_status FROM users WHERE id IN (...)
  # Source: nikita/engine/decay/processor.py:21 SKIP_STATUSES = frozenset({"boss_fight", "game_over", "won"})

Scenario: S-10.1.5 - Invalid auth secret rejected with 401 [P0-Critical]
  Given TASK_AUTH_SECRET is configured in the environment
  When POST /tasks/decay is called with Authorization: Bearer wrong_secret_value
  Then response status is 401
  And response.detail = "Unauthorized"
  And no decay processing occurs
  And no job_executions record is created
  # Verify: gcloud CLI → curl -X POST {BACKEND_URL}/tasks/decay -H "Authorization: Bearer wrong_secret" -w "%{http_code}"
  # Source: nikita/api/routes/tasks.py:78-80 (verify_task_secret raises HTTPException 401)
```

---

## US-10.2: Deliver Job
### MCP Tools: Supabase MCP, Telegram MCP, gcloud CLI

```gherkin
Scenario: S-10.2.1 - Scheduled Telegram message delivered successfully [P0-Critical]
  Given a scheduled_event exists:
    | field        | value                                          |
    | user_id      | {active_user_id}                               |
    | platform     | telegram                                       |
    | event_type   | send_message                                   |
    | status       | pending                                        |
    | scheduled_at | now() - interval '1 minute'                    |
    | content      | {"chat_id": 12345, "text": "Hey, thinking..."} |
  When POST /tasks/deliver is called with valid Authorization header
  Then the Telegram message "Hey, thinking..." is sent to chat_id 12345
  And the scheduled_event status changes to "delivered"
  And response.delivered = 1
  And response.failed = 0
  And a job_executions record is created with job_name="deliver" and status="completed"
  # Verify: Telegram MCP → get_history(chat_id=12345, limit=1) — last message matches
  # Verify: Supabase MCP → SELECT status FROM scheduled_events WHERE id = {event_id}
  # Source: nikita/api/routes/tasks.py:306-331 (Telegram delivery branch)

Scenario: S-10.2.2 - Scheduled voice call logged (outbound not yet implemented) [P2-Medium]
  Given a scheduled_event exists with platform="voice" and content={"voice_prompt": "Check in on player", "agent_id": "abc123"}
  And scheduled_at <= now() and status = "pending"
  When POST /tasks/deliver is called with valid Authorization header
  Then the event is marked as "delivered" (logged, not actually called — Twilio integration pending)
  And response.delivered = 1
  And a log entry contains "would initiate call to user"
  # Verify: Supabase MCP → SELECT status FROM scheduled_events WHERE id = {event_id}
  # Source: nikita/api/routes/tasks.py:333-372 (voice branch — logs and marks delivered, TODO comment at line 363)

Scenario: S-10.2.3 - Event with missing content fields marked as failed [P1-High]
  Given a scheduled_event exists with platform="telegram" and content={"chat_id": 12345} (missing "text" field)
  And scheduled_at <= now() and status = "pending"
  When POST /tasks/deliver is called with valid Authorization header
  Then the event status changes to "failed"
  And the event error_message contains "Missing chat_id or text in content"
  And response.failed = 1
  And response.delivered = 0
  # Verify: Supabase MCP → SELECT status, error_message FROM scheduled_events WHERE id = {event_id}
  # Source: nikita/api/routes/tasks.py:313-319 (missing chat_id or text guard)

Scenario: S-10.2.4 - No events due returns delivered=0 [P2-Medium]
  Given no scheduled_events have status="pending" and scheduled_at <= now()
  When POST /tasks/deliver is called with valid Authorization header
  Then response.status = "ok"
  And response.delivered = 0
  And response.failed = 0
  And a job_executions record is created with status="completed"
  # Verify: Supabase MCP → SELECT count(*) FROM scheduled_events WHERE status='pending' AND scheduled_at <= now()
  # Source: nikita/api/routes/tasks.py:300 (get_due_events returns empty list)

Scenario: S-10.2.5 - Deliver respects event limit of 50 per cycle [P2-Medium]
  Given 60 pending scheduled_events with scheduled_at <= now()
  When POST /tasks/deliver is called with valid Authorization header
  Then at most 50 events are processed in this cycle
  And remaining 10 events stay with status="pending" for next cycle
  And response.delivered + response.failed <= 50
  # Verify: Supabase MCP → SELECT count(*) FROM scheduled_events WHERE status='pending'
  # Source: nikita/api/routes/tasks.py:300 (limit=50 parameter)
```

---

## US-10.3: Summary Job
### MCP Tools: Supabase MCP, gcloud CLI

```gherkin
Scenario: S-10.3.1 - Daily summary generated for user with conversations today [P0-Critical]
  Given an active user with 3 processed conversations today (status='processed')
  And no daily_summary exists for this user and today's date
  When POST /tasks/summary is called with valid Authorization header
  Then a daily_summary record is created with:
    | field               | constraint               |
    | user_id             | matches active user      |
    | summary_date        | today                    |
    | conversations_count | 3                        |
    | summary_text        | non-empty string         |
    | emotional_tone      | one of: warm, playful, tense, passionate, neutral, distant |
    | score_start         | numeric                  |
    | score_end           | numeric                  |
  And response.summaries_generated >= 1
  And a job_executions record is created with job_name="summary" and status="completed"
  # Verify: Supabase MCP → SELECT * FROM daily_summaries WHERE user_id = {user_id} AND summary_date = current_date
  # Verify: Supabase MCP → SELECT * FROM job_executions WHERE job_name='summary' ORDER BY started_at DESC LIMIT 1
  # Source: nikita/api/routes/tasks.py:554-576 (LLM summary generation + create_summary call)

Scenario: S-10.3.2 - Summary includes LLM-generated key moments [P1-High]
  Given an active user with 2 processed conversations today containing emotional exchanges
  When POST /tasks/summary is called with valid Authorization header
  Then the daily_summary.key_moments array contains 1-3 entries
  And each key moment is a brief string describing a notable interaction
  And daily_summary.summary_text is a 2-3 sentence first-person narrative from Nikita's perspective
  # Verify: Supabase MCP → SELECT key_moments, summary_text FROM daily_summaries WHERE user_id = {user_id} AND summary_date = current_date
  # Source: nikita/api/routes/tasks.py:145-163 (_build_summary_prompt format: SUMMARY/KEY_MOMENTS/EMOTIONAL_TONE)

Scenario: S-10.3.3 - No summary for users with no conversations today [P1-High]
  Given an active user with last conversation 3 days ago (no conversations with started_at = today)
  When POST /tasks/summary is called with valid Authorization header
  Then no daily_summary record is created for this user
  And the user is checked but skipped (counted in users_checked but not summaries_generated)
  # Verify: Supabase MCP → SELECT count(*) FROM daily_summaries WHERE user_id = {user_id} AND summary_date = current_date -- should be 0
  # Source: nikita/api/routes/tasks.py:503-505 (if not today_convs: continue)

Scenario: S-10.3.4 - Duplicate summary prevented (idempotent) [P1-High]
  Given a daily_summary already exists for user_id={user_id} and summary_date=today
  When POST /tasks/summary is called with valid Authorization header
  Then no duplicate daily_summary is created
  And the existing summary remains unchanged
  And response.summaries_generated does not include this user
  # Verify: Supabase MCP → SELECT count(*) FROM daily_summaries WHERE user_id = {user_id} AND summary_date = current_date -- should be 1
  # Source: nikita/api/routes/tasks.py:477-482 (existing check, continue if found)

Scenario: S-10.3.5 - Summary accessible from portal diary endpoint [P2-Medium]
  Given a daily_summary record exists for user_id and today's date
  When GET /api/v1/portal/diary/{user_id}?days=7 is called with valid Supabase JWT
  Then the response includes the daily summary for today
  And summary_text, key_moments, emotional_tone are present in the response entry
  # Verify: gcloud CLI → curl {BACKEND_URL}/api/v1/portal/diary/{user_id}?days=7 -H "Authorization: Bearer {JWT}"
  # Source: nikita/api/routes/portal.py (diary endpoint serves daily_summaries)
```

---

## US-10.4: Cleanup Job
### MCP Tools: Supabase MCP, gcloud CLI

```gherkin
Scenario: S-10.4.1 - Expired pending_registrations deleted [P0-Critical]
  Given 3 pending_registrations exist:
    | telegram_id | otp_state | expires_at                     |
    | 111         | code_sent | now() - interval '15 minutes'  |
    | 222         | pending   | now() - interval '30 minutes'  |
    | 333         | code_sent | now() + interval '5 minutes'   |
  And default expiry is 10 minutes
  When POST /tasks/cleanup is called with valid Authorization header
  Then pending_registrations for telegram_id 111 and 222 are deleted (expired)
  And pending_registration for telegram_id 333 is preserved (not yet expired)
  And response.cleaned_up = 2
  And response.status = "ok"
  # Verify: Supabase MCP → SELECT * FROM pending_registrations WHERE telegram_id IN (111, 222) -- should be empty
  # Verify: Supabase MCP → SELECT * FROM pending_registrations WHERE telegram_id = 333 -- should exist
  # Source: nikita/db/repositories/pending_registration_repository.py:26-27 (DEFAULT_EXPIRY_MINUTES = 10)

Scenario: S-10.4.2 - Active (non-expired) registrations preserved [P1-High]
  Given 2 pending_registrations exist, both with expires_at > now()
  When POST /tasks/cleanup is called with valid Authorization header
  Then both registrations remain in the database
  And response.cleaned_up = 0
  # Verify: Supabase MCP → SELECT count(*) FROM pending_registrations -- should be 2

Scenario: S-10.4.3 - Cleanup logs execution in job_executions [P2-Medium]
  Given some expired pending_registrations exist
  When POST /tasks/cleanup is called with valid Authorization header
  Then a job_executions record is created with job_name="cleanup"
  And the record has status="completed"
  And the record result contains {"cleaned_up": N}
  # Verify: Supabase MCP → SELECT * FROM job_executions WHERE job_name='cleanup' ORDER BY started_at DESC LIMIT 1
  # Source: nikita/api/routes/tasks.py:627-639 (JobName.CLEANUP, complete_execution)

Scenario: S-10.4.4 - Cleanup with no expired registrations returns 0 [P2-Medium]
  Given no pending_registrations exist in the database
  When POST /tasks/cleanup is called with valid Authorization header
  Then response.status = "ok"
  And response.cleaned_up = 0
  And a job_executions record is still created (tracks that the job ran)
  # Verify: Supabase MCP → SELECT * FROM job_executions WHERE job_name='cleanup' ORDER BY started_at DESC LIMIT 1
  # Source: nikita/api/routes/tasks.py:634 (cleaned = 0 when no expired records)
```

---

## US-10.5: Process-Conversations Job
### MCP Tools: Supabase MCP, gcloud CLI

```gherkin
Scenario: S-10.5.1 - Inactive conversation detected after 15 minutes [P0-Critical]
  Given a conversation exists with:
    | field              | value                          |
    | user_id            | {active_user_id}               |
    | status             | active                         |
    | last_message_at    | now() - interval '16 minutes'  |
    | processing_attempts| 0                              |
  When POST /tasks/process-conversations is called with valid Authorization header
  Then the conversation is detected as stale (16 min > 15 min timeout)
  And response.detected >= 1
  # Verify: Supabase MCP → SELECT status FROM conversations WHERE id = {conv_id}
  # Source: nikita/context/session_detector.py:128-131 (timeout_minutes=15 default)
  # Source: nikita/api/routes/tasks.py:685-689 (detect_stale_sessions call)

Scenario: S-10.5.2 - Pipeline post-processing stages execute on stale conversation [P0-Critical]
  Given a conversation is detected as stale with messages containing user facts
  And unified_pipeline_enabled = true (feature flag)
  When the pipeline orchestrator processes this conversation
  Then the extraction stage runs (extracts entities/facts from transcript)
  And the memory_update stage runs (stores facts to pgVector)
  And the summary stage runs (generates conversation summary)
  And the conversation status changes to "processed"
  And conversation.conversation_summary is populated
  And conversation.emotional_tone is populated
  And response.processed >= 1
  # Verify: Supabase MCP → SELECT status, conversation_summary, emotional_tone FROM conversations WHERE id = {conv_id}
  # Verify: Supabase MCP → SELECT * FROM memory_facts WHERE user_id = {user_id} ORDER BY created_at DESC LIMIT 5
  # Source: nikita/pipeline/orchestrator.py:39-49 (STAGE_DEFINITIONS: extraction, memory_update, ..., summary)
  # Source: nikita/api/routes/tasks.py:726-733 (mark_processed with summary, emotional_tone)

Scenario: S-10.5.3 - Facts extracted from conversation stored in memory_facts [P1-High]
  Given a conversation where user mentions "I work at Google as a software engineer"
  And the conversation becomes stale and is picked up by process-conversations
  When the extraction stage runs
  Then a memory_facts record is created with fact containing "works at Google" or similar
  And the fact has a valid embedding vector (pgVector)
  And fact_type indicates the category (e.g., "career", "personal")
  # Verify: Supabase MCP → SELECT fact, fact_type FROM memory_facts WHERE user_id = {user_id} AND fact ILIKE '%Google%'
  # Source: nikita/pipeline/stages/extraction.py (ExtractionStage)

Scenario: S-10.5.4 - Conversation status becomes "processed" after successful pipeline [P0-Critical]
  Given a stale conversation with status="active"
  When process-conversations job detects and processes it
  Then the conversation status becomes "processed"
  And conversation.processed_at is set to approximately now()
  And processing_attempts is incremented by 1
  # Verify: Supabase MCP → SELECT status, processed_at, processing_attempts FROM conversations WHERE id = {conv_id}
  # Source: nikita/db/repositories/conversation_repository.py:423-424 (status = "processed", processed_at = now)

Scenario: S-10.5.5 - Conversations with 3+ processing attempts are skipped [P1-High]
  Given a conversation with status="active" and processing_attempts = 3
  And last_message_at > 15 minutes ago
  When POST /tasks/process-conversations is called
  Then this conversation is NOT detected as stale (filtered by max_attempts)
  And response.detected does not include this conversation
  # Verify: Supabase MCP → SELECT processing_attempts, status FROM conversations WHERE id = {conv_id} -- still "active", attempts still 3
  # Source: nikita/db/repositories/conversation_repository.py:334 (.where(Conversation.processing_attempts < max_attempts))
```

---

## US-10.6: Pipeline Stages
### MCP Tools: Supabase MCP, gcloud CLI

```gherkin
Scenario: S-10.6.1 - Full 9-stage pipeline completes for text conversation [P0-Critical]
  Given a text conversation with 5 messages (user + Nikita exchanges)
  And the conversation has been inactive for 16 minutes (status="active")
  When the pipeline orchestrator processes this conversation
  Then all 9 stages execute in order:
    | stage_order | stage_name     | is_critical | expected_behavior                       |
    | 1           | extraction     | true        | Extracts entities and facts              |
    | 2           | memory_update  | true        | Stores facts to pgVector                 |
    | 3           | life_sim       | false       | Generates daily life events              |
    | 4           | emotional      | false       | Computes 4D emotional state              |
    | 5           | game_state     | false       | Updates game state metrics               |
    | 6           | conflict       | false       | Evaluates conflict level                 |
    | 7           | touchpoint     | false       | Schedules proactive messages             |
    | 8           | summary        | false       | Generates conversation summary           |
    | 9           | prompt_builder | false       | Builds prompt template for next message  |
  And result.success = true
  And conversation status = "processed"
  # Verify: Supabase MCP → SELECT status, conversation_summary, processed_at FROM conversations WHERE id = {conv_id}
  # Source: nikita/pipeline/orchestrator.py:39-49 (STAGE_DEFINITIONS list)

Scenario: S-10.6.2 - Pipeline completes for voice conversation [P1-High]
  Given a voice conversation with platform="voice" that ended 16 minutes ago
  When the pipeline orchestrator processes it with platform="voice"
  Then all 9 stages execute (same pipeline for voice and text)
  And extraction stage processes voice transcript the same as text
  And result.success = true
  And conversation status = "processed"
  # Verify: Supabase MCP → SELECT status, platform FROM conversations WHERE id = {conv_id} AND platform='voice'
  # Source: nikita/api/routes/tasks.py:719 (platform=conv.platform or "text")

Scenario: S-10.6.3 - Critical stage failure stops pipeline [P0-Critical]
  Given a conversation ready for post-processing
  And the extraction stage (critical=true) will fail due to LLM timeout
  When the pipeline orchestrator processes this conversation
  Then the pipeline stops after extraction failure
  And remaining stages (memory_update, life_sim, ...) do NOT execute
  And result.success = false
  And the conversation status is marked as "failed"
  # Verify: Supabase MCP → SELECT status FROM conversations WHERE id = {conv_id} -- should be "failed"
  # Source: nikita/pipeline/orchestrator.py:40 (extraction is_critical=True)
  # Source: nikita/api/routes/tasks.py:734 (mark_failed on !result.success)

Scenario: S-10.6.4 - Non-critical stage failure allows pipeline to continue [P1-High]
  Given a conversation ready for post-processing
  And the life_sim stage (critical=false) will fail
  When the pipeline orchestrator processes this conversation
  Then the pipeline continues past life_sim failure
  And subsequent stages (emotional, game_state, conflict, touchpoint, summary, prompt_builder) still execute
  And result.success = true (non-critical failures are logged but don't stop pipeline)
  And conversation status = "processed"
  # Verify: Supabase MCP → SELECT status FROM conversations WHERE id = {conv_id} -- should be "processed"
  # Source: nikita/pipeline/orchestrator.py:42 (life_sim is_critical=False)

Scenario: S-10.6.5 - Stuck conversation recovery after 30 minutes in "processing" [P1-High]
  Given a conversation stuck in status="processing" for 35 minutes
  And processing_started_at = now() - interval '35 minutes'
  When POST /tasks/detect-stuck is called with valid Authorization header
  Then the conversation is detected as stuck (35 min > 30 min threshold)
  And the conversation status is changed to "failed"
  And response.detected >= 1
  And response.marked_failed >= 1
  # Verify: Supabase MCP → SELECT status FROM conversations WHERE id = {conv_id} -- should be "failed"
  # Source: nikita/api/routes/tasks.py:817 (detect_stuck timeout_minutes=30)
  # Source: nikita/api/routes/tasks.py:827-829 (mark status="failed")

Scenario: S-10.6.6 - Admin can trigger pipeline manually for a conversation [P2-Medium]
  Given a processed conversation exists for user_id={user_id}
  And the admin wants to re-run the pipeline
  When POST /api/v1/admin/users/{user_id}/trigger-pipeline is called with valid admin JWT
  Then the pipeline is triggered for the specified user's latest conversation
  And the pipeline stages execute as normal
  And the response indicates pipeline trigger status
  # Verify: gcloud CLI → curl -X POST {BACKEND_URL}/api/v1/admin/users/{user_id}/trigger-pipeline -H "Authorization: Bearer {admin_jwt}"
```

---

## US-10.7: Boss Timeout Job
### MCP Tools: Supabase MCP, gcloud CLI

```gherkin
Scenario: S-10.7.1 - Stale boss_fight resolved after 24 hours (AFK user) [P1-High]
  Given a user with game_status="boss_fight" and updated_at = now() - interval '25 hours'
  And boss_attempts = 1
  When POST /tasks/boss-timeout is called with valid Authorization header
  Then the user's boss_attempts increments to 2
  And the user's game_status changes to "active" (< 3 attempts)
  And a score_history record is created with event_type="boss_timeout"
  And response.resolved >= 1
  # Verify: Supabase MCP → SELECT game_status, boss_attempts FROM users WHERE id = {user_id}
  # Verify: Supabase MCP → SELECT * FROM score_history WHERE user_id = {user_id} AND event_type='boss_timeout'
  # Source: nikita/api/routes/tasks.py:1014-1021 (boss_attempts increment, active if < 3)

Scenario: S-10.7.2 - 3rd boss timeout triggers game_over [P0-Critical]
  Given a user with game_status="boss_fight" and updated_at = now() - interval '25 hours'
  And boss_attempts = 2 (this will be the 3rd timeout)
  When POST /tasks/boss-timeout is called with valid Authorization header
  Then the user's boss_attempts increments to 3
  And the user's game_status changes to "game_over" (>= 3 attempts)
  And a score_history record is created with event_type="boss_timeout" and event_details.new_status="game_over"
  And response.resolved >= 1
  # Verify: Supabase MCP → SELECT game_status FROM users WHERE id = {user_id} -- should be "game_over"
  # Source: nikita/api/routes/tasks.py:1016-1018 (if boss_attempts >= 3: game_over)

Scenario: S-10.7.3 - Recent boss_fight not resolved (within 24h) [P1-High]
  Given a user with game_status="boss_fight" and updated_at = now() - interval '12 hours'
  When POST /tasks/boss-timeout is called with valid Authorization header
  Then the user's game_status remains "boss_fight" (12h < 24h cutoff)
  And response.resolved = 0
  # Verify: Supabase MCP → SELECT game_status FROM users WHERE id = {user_id} -- still "boss_fight"
  # Source: nikita/api/routes/tasks.py:1002 (cutoff = now - 24 hours)
```

---

## US-10.8: Touchpoint Job
### MCP Tools: Supabase MCP, Telegram MCP, gcloud CLI

```gherkin
Scenario: S-10.8.1 - Due touchpoint delivered via Telegram [P1-High]
  Given the TouchpointEngine evaluates eligible users
  And a touchpoint is due (morning slot, user hasn't been contacted today)
  When POST /tasks/touchpoints is called with valid Authorization header
  Then the touchpoint message is generated and delivered via Telegram
  And response.delivered >= 1
  And a job_executions record is created with job_name="touchpoints"
  # Verify: Telegram MCP → get_history for user's chat, check for Nikita-initiated message
  # Verify: Supabase MCP → SELECT * FROM job_executions WHERE job_name='touchpoints' ORDER BY started_at DESC LIMIT 1
  # Source: nikita/api/routes/tasks.py:887-888 (TouchpointEngine.deliver_due_touchpoints)

Scenario: S-10.8.2 - No eligible users returns evaluated=0 [P2-Medium]
  Given no users qualify for touchpoints (all contacted recently, all outside time windows)
  When POST /tasks/touchpoints is called with valid Authorization header
  Then response.status = "ok"
  And response.evaluated = 0
  And response.delivered = 0
  # Verify: Supabase MCP → SELECT * FROM job_executions WHERE job_name='touchpoints' ORDER BY started_at DESC LIMIT 1
  # Source: nikita/api/routes/tasks.py:891-893 (count successes from results list)
```

---

## US-10.9: Recover-Stuck Job
### MCP Tools: Supabase MCP, gcloud CLI

```gherkin
Scenario: S-10.9.1 - Stuck conversation recovered (reset to active) [P1-High]
  Given a conversation with status="processing" and processing_started_at = now() - interval '35 minutes'
  And processing_attempts = 1 (< max_attempts=3)
  When POST /tasks/recover-stuck is called with valid Authorization header
  Then the conversation is recovered (reset to a retryable state)
  And response.recovered >= 1
  # Verify: Supabase MCP → SELECT status, processing_attempts FROM conversations WHERE id = {conv_id}
  # Source: nikita/api/routes/tasks.py:944 (conv_repo.recover_stuck, timeout_minutes=30, max_attempts=3)

Scenario: S-10.9.2 - Conversation with max attempts not recovered [P1-High]
  Given a conversation with status="processing" and processing_started_at = now() - interval '35 minutes'
  And processing_attempts = 3 (>= max_attempts)
  When POST /tasks/recover-stuck is called with valid Authorization header
  Then the conversation is NOT recovered (exceeded max attempts)
  And response.recovered = 0
  # Verify: Supabase MCP → SELECT status FROM conversations WHERE id = {conv_id} -- still "processing"
  # Source: nikita/api/routes/tasks.py:944 (max_attempts=3 filter)
```

---

## US-10.10: Job Execution Logging (Cross-cutting)
### MCP Tools: Supabase MCP

```gherkin
Scenario: S-10.10.1 - All job endpoints create job_executions records [P1-High]
  Given the system is running with all pg_cron jobs active
  When each of the following endpoints is called in sequence:
    | endpoint                    | job_name              |
    | POST /tasks/decay           | decay                 |
    | POST /tasks/deliver         | deliver               |
    | POST /tasks/summary         | summary               |
    | POST /tasks/cleanup         | cleanup               |
    | POST /tasks/process-conversations | process-conversations |
    | POST /tasks/detect-stuck    | detect_stuck          |
    | POST /tasks/touchpoints     | touchpoints           |
    | POST /tasks/recover-stuck   | recover_stuck         |
    | POST /tasks/boss-timeout    | boss_timeout          |
  Then each creates a job_executions record with started_at, completed_at (or failed_at), and result JSON
  And all records have status="completed" (assuming no errors)
  # Verify: Supabase MCP → SELECT job_name, status, result FROM job_executions ORDER BY started_at DESC LIMIT 9
  # Source: nikita/api/routes/tasks.py (all endpoints use JobExecutionRepository.start_execution → complete_execution pattern)

Scenario: S-10.10.2 - Job failure logged in job_executions [P1-High]
  Given a task endpoint encounters an unhandled exception during processing
  When the exception is caught by the endpoint's try/except block
  Then a job_executions record is created with status="failed"
  And the result JSON contains the error message
  And the endpoint returns {"status": "error", "error": "..."} instead of raising HTTP 500
  # Verify: Supabase MCP → SELECT status, result FROM job_executions WHERE status='failed' ORDER BY started_at DESC LIMIT 1
  # Source: nikita/api/routes/tasks.py:260-265 (decay error handler pattern, replicated across all endpoints)
```
