# E07: Voice Interactions (24 scenarios)

> Epic: E07 | User Stories: 5 | Priority: P0=10, P1=8, P2=4, P3=0
> MCP Tools: Supabase MCP, gcloud CLI
> Source files: voice.py, availability.py, inbound.py, server_tools.py, scoring.py

---

## US-7.1: Voice Call Initiation
### MCP Tools: Supabase MCP, gcloud CLI

```gherkin
Scenario: S-7.1.1 - Check voice availability for active user in high chapter [P0-Critical]
  Given an active user in chapter 3 with game_status="active"
  When GET /api/v1/voice/availability/{user_id} is called
  Then response status is 200
  And response contains available (true or false based on 80% probability), chapter=3, availability_rate=0.8
  # Verify: Supabase MCP → SELECT chapter, game_status FROM users WHERE id = '{user_id}'
  # Verify: availability.py AVAILABILITY_RATES = {3: 0.8}

Scenario: S-7.1.2 - Availability denied for game_over user [P0-Critical]
  Given a user with game_status="game_over"
  When GET /api/v1/voice/availability/{user_id} is called
  Then response contains available=false, reason="Game is over. Nikita has moved on."
  # Verify: availability.py:80-82 blocks game_over
  # Verify: Supabase MCP → SELECT game_status FROM users WHERE id = '{user_id}'

Scenario: S-7.1.3 - Availability denied for game_won user [P1-High]
  Given a user with game_status="won"
  When GET /api/v1/voice/availability/{user_id} is called
  Then response contains available=false, reason="You've already won! Game complete."
  # Verify: availability.py:84-86 blocks won status

Scenario: S-7.1.4 - Initiate call returns signed connection params [P0-Critical]
  Given an active user in chapter 2 with game_status="active"
  When POST /api/v1/voice/initiate is called with {"user_id": "{user_id}"}
  Then response status is 200
  And response contains agent_id (non-empty string), signed_token (4-part colon-delimited), session_id (starts with "voice_")
  And response contains dynamic_variables with keys including user_name, chapter, relationship_score, engagement_state, nikita_mood
  And response contains conversation_config_override with tts.stability, tts.similarity_boost, tts.speed
  # Verify: voice.py:277 → VoiceService.initiate_call()
  # Verify: Supabase MCP → SELECT * FROM users WHERE id = '{user_id}'

Scenario: S-7.1.5 - Inbound call via pre-call endpoint for registered user [P0-Critical]
  Given a registered user with phone_number="+41787950009" and onboarding_status="completed"
  When POST /api/v1/voice/pre-call is called with {"caller_id": "+41787950009", "agent_id": "test", "called_number": "+41787950009", "call_sid": "CA123"}
  Then response contains type="conversation_initiation_client_data"
  And response contains dynamic_variables with secret__user_id matching the user's UUID
  And response contains dynamic_variables with secret__signed_token (HMAC token)
  And response contains conversation_config_override with agent.prompt and agent.first_message
  # Verify: inbound.py:199 → handle_incoming_call()
  # Verify: Supabase MCP → SELECT id, phone_number, onboarding_status FROM users WHERE phone_number = '+41787950009'
```

---

## US-7.2: Server Tools During Call
### MCP Tools: Supabase MCP, gcloud CLI

```gherkin
Scenario: S-7.2.1 - get_context returns full game state [P0-Critical]
  Given an active user in chapter 3 with relationship_score=65.5 and primary_vice="jealousy"
  And a valid signed_token for that user
  When POST /api/v1/voice/server-tool is called with {"tool_name": "get_context", "signed_token": "{token}", "data": {}}
  Then response contains success=true
  And response.data contains user_name, chapter=3, game_status="active", engagement_state
  And response.data contains relationship_score=65.5, intimacy, passion, trust, secureness (4 sub-metrics)
  And response.data contains primary_vice="jealousy", all_vices (list)
  And response.data contains nikita_mood (one of: distant, neutral, flirty, playful, vulnerable, annoyed)
  And response.data contains hours_since_last, time_of_day, day_of_week, nikita_activity, nikita_energy
  # Verify: server_tools.py:302 → _get_context()
  # Verify: Supabase MCP → SELECT * FROM users JOIN user_metrics ON users.id = user_metrics.user_id WHERE users.id = '{user_id}'

Scenario: S-7.2.2 - get_memory returns relevant facts and threads [P1-High]
  Given an active user with stored memory facts
  And a valid signed_token for that user
  When POST /api/v1/voice/server-tool is called with {"tool_name": "get_memory", "signed_token": "{token}", "data": {"query": "birthday", "limit": 5}}
  Then response contains success=true
  And response.data contains facts (list of strings, max 3)
  And response.data contains threads (list of {type, content} objects)
  # Verify: server_tools.py:817 → _get_memory()

Scenario: S-7.2.3 - score_turn applies metric deltas [P0-Critical]
  Given an active user in chapter 2 with known metric values
  And a valid signed_token for that user
  When POST /api/v1/voice/server-tool is called with {"tool_name": "score_turn", "signed_token": "{token}", "data": {"user_message": "I really missed talking to you", "nikita_response": "That's sweet of you to say"}}
  Then response contains success=true
  And response.data contains intimacy_delta, passion_delta, trust_delta, secureness_delta (all floats)
  And response.data contains analysis_summary (non-empty string)
  # Verify: server_tools.py:873 → _score_turn()
  # Verify: ScoreAnalyzer.analyze() returns ResponseAnalysis with MetricDeltas

Scenario: S-7.2.4 - update_memory stores new facts [P1-High]
  Given an active user
  And a valid signed_token for that user
  When POST /api/v1/voice/server-tool is called with {"tool_name": "update_memory", "signed_token": "{token}", "data": {"fact": "User's birthday is March 15", "category": "personal"}}
  Then response contains success=true
  And response.data contains stored=true, fact="User's birthday is March 15", category="personal"
  # Verify: server_tools.py:943 → _update_memory()
  # Verify: SupabaseMemory.add_user_fact() stores to pgVector

Scenario: S-7.2.5 - Server tool with invalid auth rejected [P0-Critical]
  Given an expired or tampered signed_token
  When POST /api/v1/voice/server-tool is called with {"tool_name": "get_context", "signed_token": "{bad_token}", "data": {}}
  Then response status is 401
  And response contains detail matching "Invalid" or "expired" or "Invalid token format"
  # Verify: voice.py:345 → _validate_signed_token() rejects invalid tokens
  # Verify: Token validity window is 1800 seconds (30 min)
```

---

## US-7.3: Call Completion
### MCP Tools: Supabase MCP, gcloud CLI

```gherkin
Scenario: S-7.3.1 - Webhook processes post_call_transcription event [P0-Critical]
  Given a valid HMAC signature for the webhook payload
  And a webhook payload with type="post_call_transcription" containing transcript data
  And data.conversation_initiation_client_data.dynamic_variables.secret__user_id is set to a valid user UUID
  When POST /api/v1/voice/webhook is called with the signed payload
  Then response status is 200
  And response contains status="processed"
  # Verify: voice.py:533 → _process_webhook_event()
  # Verify: Supabase MCP → SELECT * FROM conversations WHERE platform='voice' AND elevenlabs_session_id = '{session_id}' ORDER BY created_at DESC LIMIT 1

Scenario: S-7.3.2 - Transcript stored as conversation record [P0-Critical]
  Given a post_call_transcription webhook with transcript=[{"role":"user","message":"Hey"}, {"role":"agent","message":"Hi there!"}]
  When the webhook is processed
  Then a new conversation record is created with platform="voice"
  And conversation.messages contains parsed user/nikita turns
  And conversation.transcript_raw contains "user: Hey\nnikita: Hi there!"
  And conversation.elevenlabs_session_id matches the webhook conversation_id
  # Verify: Supabase MCP → SELECT id, platform, messages, transcript_raw, elevenlabs_session_id FROM conversations WHERE user_id = '{user_id}' AND platform = 'voice' ORDER BY created_at DESC LIMIT 1

Scenario: S-7.3.3 - Final score_delta calculated from full transcript [P1-High]
  Given a post_call_transcription webhook with 4 user-nikita exchange pairs
  When the webhook is processed and scoring completes
  Then conversation.score_delta is updated (non-zero Decimal)
  And score_history contains a new entry with event_type="voice_call"
  And score_history.event_details contains session_id, duration_seconds, deltas, explanation
  # Verify: scoring.py:130 → apply_score() writes to score_history
  # Verify: Supabase MCP → SELECT * FROM score_history WHERE user_id = '{user_id}' AND event_type = 'voice_call' ORDER BY created_at DESC LIMIT 1

Scenario: S-7.3.4 - HMAC signature verified on webhook [P0-Critical]
  Given a webhook payload with a valid elevenlabs-signature header in format "t={timestamp},v0={hash}"
  When POST /api/v1/voice/webhook is called
  Then signature verification passes (verify_elevenlabs_signature returns true)
  And the webhook is processed normally
  # Verify: voice.py:484 → verify_elevenlabs_signature() uses SHA256 HMAC
  # Verify: Timestamp tolerance is 300 seconds (5 min)

Scenario: S-7.3.5 - Invalid signature rejected with 401 [P0-Critical]
  Given a webhook payload with an invalid elevenlabs-signature header "t=123,v0=fakehash"
  When POST /api/v1/voice/webhook is called
  Then response status is 401
  And response contains detail="Invalid signature"
  # Verify: voice.py:871-876 raises HTTPException 401
```

---

## US-7.4: Voice Scoring
### MCP Tools: Supabase MCP

```gherkin
Scenario: S-7.4.1 - Positive voice interaction increases metrics [P0-Critical]
  Given an active user with relationship_score=55.0 and all metrics at 50.0
  And a voice call transcript with warm, intimate exchanges
  When VoiceCallScorer.score_call() and apply_score() are executed
  Then user_metrics shows increased values for intimacy, trust, and/or passion
  And relationship_score has increased
  # Verify: Supabase MCP → SELECT intimacy, passion, trust, secureness FROM user_metrics WHERE user_id = '{user_id}'
  # Verify: scoring.py:62 → score_call() returns CallScore with positive deltas

Scenario: S-7.4.2 - Negative voice interaction decreases metrics [P1-High]
  Given an active user with relationship_score=60.0
  And a voice call transcript with hostile or dismissive exchanges
  When VoiceCallScorer.score_call() and apply_score() are executed
  Then user_metrics shows decreased values for at least one metric
  And relationship_score has decreased or stayed same
  # Verify: ScoreAnalyzer.analyze_batch() produces negative MetricDeltas

Scenario: S-7.4.3 - Voice score uses same ScoreAnalyzer as text [P1-High]
  Given VoiceCallScorer internally uses ScoreAnalyzer() (engine/scoring/analyzer.py)
  When a voice transcript is scored
  Then the same LLM-based analysis runs as for text messages
  And MetricDeltas follow same scale (-5 to +5 per metric)
  # Verify: scoring.py:60 → self._analyzer = ScoreAnalyzer()
  # Verify: Text path also uses ScoreAnalyzer for consistency

Scenario: S-7.4.4 - Voice score_history entry created with event_type="voice_call" [P0-Critical]
  Given an active user
  When a voice call is scored and apply_score() completes
  Then score_history table has a new row with event_type="voice_call"
  And event_details JSON contains session_id, duration_seconds, deltas (per metric), explanation, behaviors
  # Verify: scoring.py:186-204 → history_repo.log_event(event_type="voice_call")
  # Verify: Supabase MCP → SELECT event_type, event_details FROM score_history WHERE user_id = '{user_id}' AND event_type = 'voice_call' ORDER BY created_at DESC LIMIT 1

Scenario: S-7.4.5 - Boss trigger from voice score crossing threshold [P1-High]
  Given an active user in chapter 2 with relationship_score just below BOSS_THRESHOLD[2] (e.g., 54.0)
  And boss threshold for chapter 2 is 55
  When a positive voice call pushes score above threshold
  Then boss encounter should be triggered (game_status transitions to boss_fight)
  # Verify: BOSS_THRESHOLDS in engine/constants.py
  # Verify: Supabase MCP → SELECT game_status FROM users WHERE id = '{user_id}'
  # Note: Boss trigger may happen via pipeline post-processing, not inline scoring
```

---

## US-7.5: Voice Edge Cases
### MCP Tools: Supabase MCP, gcloud CLI

```gherkin
Scenario: S-7.5.1 - Call drops mid-conversation triggers disconnect recovery [P1-High]
  Given an active voice session with session_id="voice_inbound_{user_id}_20260214"
  When VoiceSessionManager.handle_disconnect(session_id) is called
  Then session state transitions to "DISCONNECTED" with disconnected_at timestamp
  And if attempt_recovery() is called within 30 seconds, session returns to "ACTIVE"
  And if attempt_recovery() is called after 30 seconds, session transitions to "FINALIZED"
  # Verify: inbound.py:88-141 → handle_disconnect() and attempt_recovery()
  # Verify: RECOVERY_TIMEOUT_SECONDS = 30

Scenario: S-7.5.2 - Concurrent voice + text interactions both score [P2-Medium]
  Given an active user currently in a voice call
  When the user simultaneously sends a Telegram text message
  Then both interactions are scored independently
  And both create separate conversation records (one with platform="voice", one with platform="telegram")
  And user_metrics reflects combined deltas from both
  # Verify: Supabase MCP → SELECT id, platform FROM conversations WHERE user_id = '{user_id}' ORDER BY created_at DESC LIMIT 5

Scenario: S-7.5.3 - Voice during boss_fight always available [P0-Critical]
  Given a user with game_status="boss_fight"
  When GET /api/v1/voice/availability/{user_id} is called
  Then response contains available=true, reason containing "Boss encounter"
  And availability_rate is irrelevant (boss overrides probability check)
  # Verify: availability.py:88-91 → boss_fight always returns (True, "Boss encounter")
  # Verify: Supabase MCP → SELECT game_status FROM users WHERE id = '{user_id}'

Scenario: S-7.5.4 - Voice call for chapter 1 user has low availability [P2-Medium]
  Given an active user in chapter 1 (game_status="active")
  When GET /api/v1/voice/availability/{user_id} is called multiple times (10 attempts)
  Then approximately 10% of calls return available=true (rate=0.1)
  And unavailable responses include contextual excuses from UNAVAILABILITY_REASONS
  # Verify: availability.py:23 → AVAILABILITY_RATES = {1: 0.1}
  # Verify: UNAVAILABILITY_REASONS list has 8 excuses
```
